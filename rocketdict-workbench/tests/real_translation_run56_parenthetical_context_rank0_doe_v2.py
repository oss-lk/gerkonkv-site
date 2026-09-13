from __future__ import annotations

"""Read-only v2 DOE for source-defined run56 parenthetical mismatch contexts.

V1 incorrectly walked every split Stage10 context and aborted on unrelated
fragmentary planner coverage before it ever reached the residual cohort.  V2
starts from the actual run56 punctuation failures, selects only residual rows
whose own round-parenthesis counts differ and whose planner maps them to one
split ``nlp_sentence`` context, then reconstructs that complete context from all
current rows carrying the same planner identity.

The selected complete context is translated unchanged with unique raw rank0
from pinned OPUS and pinned TC-big.  This remains discovery evidence only: no
candidate is persisted and no Product promotion is authorized.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

from real_translation_run56_parenthetical_context_rank0_doe import (
    BASE_DATABASE_SHA256,
    BASE_OUTPUT_SHA256,
    BASE_RUN_ID,
    BEAM_SIZE,
    MAX_CONTEXT_NLP_TOKENS,
    MAX_DECODING_LENGTH,
    MAX_PARENTHESES_ALPHA_WORDS,
    MAX_PARENTHESES_PAIRS,
    NUM_HYPOTHESES,
    SOURCE_TEXT_SHA256,
    _aggregate_research_clean_except_round,
    _candidate,
    _canonical_sha,
    _context_token_count,
    _parenthetical_payloads,
    _planner,
    _rank0_batch,
    _sha,
)

SCHEMA = "rocketdict-run56-bounded-parenthetical-context-rank0-doe/2"
EXPECTED_PUNCTUATION_FAILURE_COUNT = 14


def _single_split_context(row: dict[str, Any]) -> int | None:
    planner = _planner(row)
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
        count = int(planner.get("context_sentence_count", last - first + 1))
    except (KeyError, TypeError, ValueError):
        return None
    if (
        planner.get("source") != "nlp_sentence"
        or planner.get("split") is not True
        or first < 0
        or first != last
        or count != 1
    ):
        return None
    return first


def _round_counts(text: str) -> tuple[int, int]:
    return text.count("("), text.count(")")


def _rows_cover_context(
    rows: list[dict[str, Any]], *, start: int, end: int, source: str
) -> bool:
    if len(rows) < 2 or start < 0 or end <= start or len(source) != end - start:
        return False
    cursor = start
    for row in sorted(rows, key=lambda item: int(item["source_start"])):
        row_start = int(row["source_start"])
        row_end = int(row["source_end"])
        row_source = str(row.get("source_text") or "")
        if row_start != cursor or row_end <= row_start or row_end > end:
            return False
        if source[row_start - start : row_end - start] != row_source:
            return False
        cursor = row_end
    return cursor == end


def _punctuation_failures(base_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in base_rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        if verdict.get("punctuation_passed") is not True:
            failures.append(row)
    return failures


def _candidate_context_sequences(
    punctuation_failures: list[dict[str, Any]],
) -> list[int]:
    sequences: set[int] = set()
    for row in punctuation_failures:
        sequence = _single_split_context(row)
        if sequence is None:
            continue
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        if _round_counts(source) != _round_counts(target):
            sequences.add(sequence)
    return sorted(sequences)


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN56_PARENTHETICAL_DOE_V2_ROOT",
            "work/run56-parenthetical-context-rank0-doe-v2",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(
        os.environ.get(
            "ROCKETDICT_RUN56_PARENTHETICAL_DOE_V2_DB",
            root / "rocketdict.sqlite",
        )
    ).resolve()
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("parenthetical DOE v2 requires exact run56 database")
    database_sha_before = _sha(database)

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        base_rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["source_start"]),
        )
        run_output = dict(run.get("output") or {})
        context_rows = sorted(
            get_run_items(
                connection,
                int(run_output["context_run_id"]),
                kind="context_sentence",
            ),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(run_output["document_version_id"]))

    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("parenthetical DOE v2 run56 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("parenthetical DOE v2 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("parenthetical DOE v2 run56 source coverage drift")

    punctuation_failures = _punctuation_failures(base_rows)
    if len(punctuation_failures) != EXPECTED_PUNCTUATION_FAILURE_COUNT:
        raise RuntimeError(
            "parenthetical DOE v2 punctuation cohort drift: "
            f"{len(punctuation_failures)} != {EXPECTED_PUNCTUATION_FAILURE_COUNT}"
        )
    punctuation_failure_sequences = [
        int(row["sequence_number"]) for row in punctuation_failures
    ]
    candidate_sequences = _candidate_context_sequences(punctuation_failures)

    contexts = {int(row["sequence_number"]): row for row in context_rows}
    by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in base_rows:
        sequence = _single_split_context(row)
        if sequence is not None:
            by_context[sequence].append(row)

    attempts: list[dict[str, Any]] = []
    selection_rejections: list[dict[str, Any]] = []
    skipped_over_cap: list[int] = []

    for sequence in candidate_sequences:
        context = contexts.get(sequence)
        if context is None:
            selection_rejections.append(
                {"context_sequence": sequence, "reason": "missing_context_row"}
            )
            continue
        members = sorted(
            by_context.get(sequence, []), key=lambda row: int(row["source_start"])
        )
        source = str(context.get("source_text") or "")
        start = int(context["source_start"])
        end = int(context["source_end"])
        if not (0 <= start < end <= len(content) and content[start:end] == source):
            selection_rejections.append(
                {"context_sequence": sequence, "reason": "immutable_context_source_mismatch"}
            )
            continue
        if not _rows_cover_context(members, start=start, end=end, source=source):
            selection_rejections.append(
                {
                    "context_sequence": sequence,
                    "reason": "incomplete_current_row_coverage",
                    "member_sequences": [int(row["sequence_number"]) for row in members],
                }
            )
            continue

        token_count = _context_token_count(context)
        if token_count <= 0:
            selection_rejections.append(
                {"context_sequence": sequence, "reason": "missing_context_token_count"}
            )
            continue
        if token_count > MAX_CONTEXT_NLP_TOKENS:
            skipped_over_cap.append(sequence)
            continue

        parenthetical_payloads = _parenthetical_payloads(source)
        if parenthetical_payloads is None:
            selection_rejections.append(
                {"context_sequence": sequence, "reason": "parenthetical_shape_outside_contract"}
            )
            continue

        primary_target = "".join(str(row.get("target_text") or "") for row in members)
        source_round = list(_round_counts(source))
        target_round = list(_round_counts(primary_target))
        if source_round == target_round:
            selection_rejections.append(
                {"context_sequence": sequence, "reason": "aggregate_round_counts_already_exact"}
            )
            continue

        aggregate_clean, base_verdict = _aggregate_research_clean_except_round(
            source, primary_target
        )
        if not aggregate_clean:
            selection_rejections.append(
                {"context_sequence": sequence, "reason": "aggregate_non_round_gate_failure"}
            )
            continue

        member_punctuation_failures: list[int] = []
        for row in members:
            verdict = evaluate_rescue_pair(
                str(row.get("source_text") or ""),
                str(row.get("target_text") or ""),
            )
            if verdict.get("punctuation_passed") is not True:
                member_punctuation_failures.append(int(row["sequence_number"]))
        if not member_punctuation_failures:
            selection_rejections.append(
                {"context_sequence": sequence, "reason": "no_member_punctuation_failure"}
            )
            continue

        attempts.append(
            {
                "context": context,
                "members": members,
                "source_text": source,
                "primary_target": primary_target,
                "source_round_parentheses": source_round,
                "target_round_parentheses": target_round,
                "parenthetical_payloads": parenthetical_payloads,
                "parenthetical_alpha_word_counts": [
                    len(__import__("re").findall(r"[A-Za-z]+", payload))
                    for payload in parenthetical_payloads
                ],
                "token_count": token_count,
                "member_punctuation_failures": member_punctuation_failures,
                "base_aggregate_verdict": base_verdict,
            }
        )

    sources = [str(attempt["source_text"]) for attempt in attempts]
    opus_rank0 = _rank0_batch(
        OpusTranslator(device="cpu", compute_type="float32"), sources
    )
    tc_rank0 = _rank0_batch(
        TcBigTranslator(device="cpu", compute_type="float32"), sources
    )

    cases: list[dict[str, Any]] = []
    for attempt, opus_raw, tc_raw in zip(
        attempts, opus_rank0, tc_rank0, strict=True
    ):
        source = str(attempt["source_text"])
        primary_target = str(attempt["primary_target"])
        model_results: dict[str, Any] = {}
        for model, raw in (("opus", opus_raw), ("tc_big", tc_raw)):
            target = str(raw["text"])
            model_results[model] = {
                "model": model,
                "model_input": source,
                "model_input_equals_context_source": True,
                "raw_rank": 0,
                "raw_score": raw.get("score"),
                "raw_target": target,
                **_candidate(source, target, primary_target=primary_target),
            }
        context = attempt["context"]
        cases.append(
            {
                "context_sequence": int(context["sequence_number"]),
                "source_start": int(context["source_start"]),
                "source_end": int(context["source_end"]),
                "source_text": source,
                "primary_target": primary_target,
                "source_round_parentheses": attempt["source_round_parentheses"],
                "target_round_parentheses": attempt["target_round_parentheses"],
                "parenthetical_payloads": attempt["parenthetical_payloads"],
                "parenthetical_alpha_word_counts": attempt[
                    "parenthetical_alpha_word_counts"
                ],
                "context_nlp_token_count": attempt["token_count"],
                "member_sequences": [
                    int(row["sequence_number"]) for row in attempt["members"]
                ],
                "member_punctuation_failure_sequences": attempt[
                    "member_punctuation_failures"
                ],
                "base_aggregate_verdict": attempt["base_aggregate_verdict"],
                "opus": model_results["opus"],
                "tc_big": model_results["tc_big"],
                "screening_passing_models": [
                    model
                    for model in ("opus", "tc_big")
                    if model_results[model]["screening_passed"] is True
                ],
            }
        )

    if _sha(database) != database_sha_before:
        raise RuntimeError("read-only parenthetical DOE v2 mutated run56 database")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only residual-derived whole-context rank0 DOE for bounded split parenthetical mismatch geometries",
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "punctuation_failure_count": len(punctuation_failures),
        "punctuation_failure_sequences": punctuation_failure_sequences,
        "candidate_context_sequences": candidate_sequences,
        "selection_rejections": selection_rejections,
        "skipped_over_cap_context_sequences": skipped_over_cap,
        "max_context_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
        "max_parentheses_pairs": MAX_PARENTHESES_PAIRS,
        "max_parentheses_alpha_words": MAX_PARENTHESES_ALPHA_WORDS,
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "max_decoding_length": MAX_DECODING_LENGTH,
        "case_count": len(cases),
        "case_context_sequences": [case["context_sequence"] for case in cases],
        "cases": cases,
        "passing_contexts": {
            model: [
                case["context_sequence"]
                for case in cases
                if case[model]["screening_passed"] is True
            ]
            for model in ("opus", "tc_big")
        },
        "database_unchanged": True,
        "source_coverage_byte_exact": True,
        "residual_derived_candidate_selection": True,
        "complete_context_row_coverage_required": True,
        "model_input_equals_immutable_context_source": True,
        "raw_rank0_only": True,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "run56-bounded-parenthetical-context-rank0-doe-v2.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "punctuation_failure_count": len(punctuation_failures),
        "candidate_context_sequences": candidate_sequences,
        "skipped_over_cap_context_sequences": skipped_over_cap,
        "selection_rejections": selection_rejections,
        "case_count": len(cases),
        "case_context_sequences": [case["context_sequence"] for case in cases],
        "passing_contexts": evidence["passing_contexts"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
