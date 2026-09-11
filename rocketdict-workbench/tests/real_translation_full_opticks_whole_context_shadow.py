from __future__ import annotations

"""Corpus-wide research shadow for long-unit semantic content loss.

The maintained Product rescue intentionally fires only when an isolated missing
numeric literal already proves that planner-v8 lost content.  That trigger is
safe but incomplete: a split long sentence can lose ordinary prose without
losing a number.  This shadow therefore translates *every* ordinary split
Stage10 sentence up to the Product rescue ceiling as one unchanged rank-0 OPUS
request and exports the comparison for semantic review.

The ceiling is evaluated with the exact Product planner token contract: Stage8
NLP tokens fully contained by the Stage10 source span, excluding ``is_space``
tokens.  Stage10's stored ``token_count`` is intentionally not used for this
bound because it includes whitespace tokens and would silently exclude Product-
eligible contexts near the limit.

Nothing in this file is a Product selector.  Positive alphabetic recovery,
mechanical cleanliness, similarity and the existing numeric trigger are review
signals only.  No source/target rewriting, placeholders, literal injection or
database writes are allowed.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import (
    evaluate_candidate_context,
    evaluate_primary_context_trigger,
)
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_full_opticks_whole_context_rescue import (  # noqa: E402
    MAX_WHOLE_CONTEXT_NLP_TOKENS,
    OPTICKS_SHA256,
    _context_sequence,
    _normalized_similarity,
    _rows_cover_context,
    _sha_file,
    _translate_batches,
)

SCHEMA = "rocketdict-full-opticks-whole-context-shadow/2"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
KNOWN_LONG_CONTENT_LOSS_SEQUENCE = 669
TOP_REVIEW_LIMIT = 100
TOKEN_COUNT_CONTRACT = "stage8-contained-non-space-nlp-tokens/1"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _alpha_count(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _review_priority(row: dict[str, Any]) -> tuple[float, int, float, int]:
    # Sorting only; these values are deliberately not acceptance thresholds.
    return (
        float(row["target_alpha_gain_fraction"]),
        int(row["target_alpha_gain"]),
        -float(row["target_similarity_to_primary"]),
        -int(row["context_sequence"]),
    )


def _non_space_tokens_in_span(
    nlp_tokens: list[dict[str, Any]], start: int, end: int
) -> list[dict[str, Any]]:
    return [
        token
        for token in nlp_tokens
        if int(token["source_start"]) >= start
        and int(token["source_end"]) <= end
        and not bool((token.get("payload") or {}).get("flags", {}).get("is_space"))
    ]


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    source_path = Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"]).resolve()
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Full Opticks Product baseline evidence is missing")
    if _sha_file(source_path) != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source hash drift")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"Unexpected full Opticks baseline schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Full Opticks baseline source identity drift")
    if baseline.get("actual_product_stage12_execution") is not True:
        raise RuntimeError("Whole-context shadow requires actual persisted Product Stage12")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Whole-context shadow requires current planner-v8 baseline")

    baseline_parameters = dict(baseline.get("stage12_parameters") or {})
    if baseline_parameters.get("enable_selective_resegmentation_rescue") is not False:
        raise RuntimeError("Whole-context shadow requires fail-closed selective-rescue baseline")
    if baseline_parameters.get("enable_whole_context_rescue") not in {None, False}:
        raise RuntimeError("Whole-context shadow requires fail-closed whole-context baseline")

    selected_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    nlp_run_id = int((baseline.get("stage8") or {})["nlp_run_id"])
    document_version_id = int(baseline["document_version_id"])

    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        selected_output = dict(selected_run.get("output") or {})
        primary_run_id = int(selected_output.get("primary_translation_run_id") or 0)
        if primary_run_id <= 0:
            raise RuntimeError("Product Stage12 baseline lacks immutable primary lineage")
        primary_run = get_run(connection, primary_run_id)
        primary_output = dict(primary_run.get("output") or {})
        if primary_output.get("planner_contract") != PLANNER_CONTRACT:
            raise RuntimeError("Whole-context shadow primary planner contract drift")
        primary_rows = get_run_items(connection, primary_run_id, kind="translation_segment")
        context_items = get_run_items(connection, context_run_id, kind="context_sentence")
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document = get_document(connection, document_version_id)

    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in primary_rows) != content:
        raise RuntimeError("Primary Stage12 rows do not byte-exactly cover immutable Opticks")

    primary_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in primary_rows:
        sequence = _context_sequence(row)
        if sequence is not None:
            primary_by_context[sequence].append(row)
    for rows in primary_by_context.values():
        rows.sort(key=lambda row: int(row["source_start"]))
    context_by_sequence = {
        int(row["sequence_number"]): row for row in context_items
    }

    shadow_inputs: list[dict[str, Any]] = []
    skipped_over_cap: list[int] = []
    stage10_whitespace_delta_context_count = 0
    for sequence, rows in sorted(primary_by_context.items()):
        if len(rows) < 2:
            continue
        context = context_by_sequence.get(sequence)
        if context is None:
            raise RuntimeError(f"Whole-context shadow lost Stage10 context {sequence}")
        start = int(context["source_start"])
        end = int(context["source_end"])
        source = str(context["source_text"])
        if content[start:end] != source:
            raise RuntimeError("Stage10 context differs from immutable source bytes")
        if not _rows_cover_context(rows, start=start, end=end, source=source):
            continue

        tokens = _non_space_tokens_in_span(nlp_tokens, start, end)
        token_count = len(tokens)
        if token_count <= 0:
            raise RuntimeError(f"Stage10 context {sequence} has no non-space NLP tokens")
        primary_planner_token_count = sum(
            int(((row.get("payload") or {}).get("planner") or {}).get("token_count") or 0)
            for row in rows
        )
        if primary_planner_token_count != token_count:
            raise RuntimeError(
                "Whole-context token contract differs from primary planner accounting: "
                f"context {sequence}: {primary_planner_token_count} != {token_count}"
            )
        stage10_token_count = int(((context.get("payload") or {}).get("token_count")) or 0)
        if stage10_token_count != token_count:
            stage10_whitespace_delta_context_count += 1

        if token_count > MAX_WHOLE_CONTEXT_NLP_TOKENS:
            skipped_over_cap.append(sequence)
            continue
        shadow_inputs.append(
            {
                "context_sequence": sequence,
                "source_start": start,
                "source_end": end,
                "source_text": source,
                "nlp_token_count": token_count,
                "stage10_token_count_including_space": stage10_token_count,
                "primary_rows": rows,
                "numeric_trigger": evaluate_primary_context_trigger(rows),
            }
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    max_tokens = max(
        (int(row["nlp_token_count"]) for row in shadow_inputs), default=0
    )
    generated = _translate_batches(
        translator,
        [str(row["source_text"]) for row in shadow_inputs],
        max_decoding_length=max(128, max_tokens * 8),
    ) if shadow_inputs else []

    candidates: list[dict[str, Any]] = []
    for attempt, hypotheses in zip(shadow_inputs, generated, strict=True):
        if not hypotheses:
            raise RuntimeError(
                f"Whole-context shadow returned no hypothesis for {attempt['context_sequence']}"
            )
        target = str(hypotheses[0].get("text") or "")
        if not target.strip():
            raise RuntimeError(
                f"Whole-context shadow returned empty rank-0 target for {attempt['context_sequence']}"
            )
        primary_target = "".join(
            str(row.get("target_text") or "") for row in attempt["primary_rows"]
        )
        selection = evaluate_candidate_context(
            list(attempt["primary_rows"]),
            [{"source_text": str(attempt["source_text"]), "target_text": target}],
        )
        primary_alpha = _alpha_count(primary_target)
        candidate_alpha = _alpha_count(target)
        alpha_gain = candidate_alpha - primary_alpha
        alpha_gain_fraction = alpha_gain / max(primary_alpha, 1)
        candidates.append(
            {
                "context_sequence": int(attempt["context_sequence"]),
                "source_start": int(attempt["source_start"]),
                "source_end": int(attempt["source_end"]),
                "nlp_token_count": int(attempt["nlp_token_count"]),
                "stage10_token_count_including_space": int(
                    attempt["stage10_token_count_including_space"]
                ),
                "source_text": str(attempt["source_text"]),
                "primary_rows": [
                    {
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                    }
                    for row in attempt["primary_rows"]
                ],
                "primary_target_concatenated": primary_target,
                "whole_context_rank0_target": target,
                "whole_context_rank0_score": hypotheses[0].get("score"),
                "selection": selection,
                "numeric_trigger": attempt["numeric_trigger"],
                "target_alpha_primary": primary_alpha,
                "target_alpha_candidate": candidate_alpha,
                "target_alpha_gain": alpha_gain,
                "target_alpha_gain_fraction": alpha_gain_fraction,
                "target_similarity_to_primary": _normalized_similarity(primary_target, target),
                "source_bytes_rewritten": False,
                "target_rewriting": False,
                "placeholders": False,
                "post_translation_literal_injection": False,
            }
        )

    if _sha_file(database) != database_sha_before:
        raise RuntimeError("Whole-context shadow mutated the persisted Product database")

    accepted = [row for row in candidates if (row["selection"] or {}).get("accepted") is True]
    positive_gain = [row for row in accepted if int(row["target_alpha_gain"]) > 0]
    ranked = sorted(positive_gain, key=_review_priority, reverse=True)
    review = ranked[:TOP_REVIEW_LIMIT]

    known = next(
        (row for row in candidates if row["context_sequence"] == KNOWN_LONG_CONTENT_LOSS_SEQUENCE),
        None,
    )
    if known is None:
        raise RuntimeError("Whole-context shadow lost the known long-unit content-loss context")
    if (known["selection"] or {}).get("accepted") is not True:
        raise RuntimeError("Known long-unit content-loss context is no longer mechanically accepted")
    if int(known["target_alpha_gain"]) <= 0:
        raise RuntimeError("Known long-unit content-loss context no longer restores alphabetic content")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only corpus-wide shadow for semantic content loss without requiring a numeric witness",
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "document_version_id": document_version_id,
        "selected_translation_run_id": selected_run_id,
        "selected_translation_output_sha256": str(selected_run.get("output_sha256") or ""),
        "primary_translation_run_id": primary_run_id,
        "primary_translation_output_sha256": str(primary_run.get("output_sha256") or ""),
        "primary_planner_contract": PLANNER_CONTRACT,
        "token_count_contract": TOKEN_COUNT_CONTRACT,
        "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        "generation": {"beam_size": 6, "num_hypotheses": 1},
        "split_context_count_within_cap": len(shadow_inputs),
        "split_context_count_over_cap": len(skipped_over_cap),
        "split_context_sequences_over_cap": skipped_over_cap,
        "stage10_whitespace_delta_context_count": stage10_whitespace_delta_context_count,
        "mechanically_accepted_context_count": len(accepted),
        "positive_alpha_gain_context_count": len(positive_gain),
        "numeric_triggered_context_count": sum(
            1 for row in candidates if (row["numeric_trigger"] or {}).get("eligible") is True
        ),
        "known_long_content_loss_sequence": KNOWN_LONG_CONTENT_LOSS_SEQUENCE,
        "known_long_content_loss_review_rank": (
            1 + next(
                index
                for index, row in enumerate(ranked)
                if row["context_sequence"] == KNOWN_LONG_CONTENT_LOSS_SEQUENCE
            )
        ),
        "review_priority_note": (
            "rank only; positive alphabetic recovery, similarity and mechanical cleanliness "
            "are not Product acceptance thresholds"
        ),
        "top_review_limit": TOP_REVIEW_LIMIT,
        "top_review_candidates": review,
        "all_candidates": candidates,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_unchanged": True,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-whole-context-shadow.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "token_count_contract": TOKEN_COUNT_CONTRACT,
                "split_context_count_within_cap": len(shadow_inputs),
                "split_context_count_over_cap": len(skipped_over_cap),
                "stage10_whitespace_delta_context_count": stage10_whitespace_delta_context_count,
                "mechanically_accepted_context_count": len(accepted),
                "positive_alpha_gain_context_count": len(positive_gain),
                "numeric_triggered_context_count": payload["numeric_triggered_context_count"],
                "known_long_content_loss_review_rank": payload["known_long_content_loss_review_rank"],
                "top_review_sequences": [row["context_sequence"] for row in review],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
