from __future__ import annotations

"""Read-only run18 DOE for capped split-question Stage10 contexts.

This experiment targets a source-defined defect family, not particular corpus
strings: one exact Stage10 question is split across multiple current Stage12
rows, at least one non-final row contains a target-only ``?``, the aggregate
current target has exactly one extra question mark, every other Product hard
family is clean, and the complete Stage10 source context is at most the
maintained 160-NLP-token whole-context cap.

Both the pinned primary OPUS model and the independently pinned TC-big model are
screened with raw beam-6 n-best output.  No Product rows are changed, no target
bytes are repaired, and mechanical eligibility is explicitly not promotion.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run18-capped-question-context-doe/1"
BASE_DATABASE_SHA256 = "803a2cbccb287ad0fadf4b14d932e1e33ebafef2ec5406619b0caf0898525143"
BASE_RUN_ID = 18
BASE_OUTPUT_SHA256 = "666e8a2cae0bb6ff6f25b95475c2335ee5e3c98f7f2d6ab7deb9be92295be290"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 16, "length": 0, "unique": 35}
WHOLE_CONTEXT_TOKEN_CAP = 160
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50
EXPECTED_CONTEXTS = {
    2462: {"source_start": 477054, "source_end": 477373, "nlp_tokens": 71, "member_count": 2},
    2726: {"source_start": 528499, "source_end": 529167, "nlp_tokens": 157, "member_count": 3},
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["source_start"]))


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    union: set[int] = set()
    for row in _ordered(rows):
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
        sequence = int(row["sequence_number"])
        failures = {
            "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key, failed in failures.items():
            if failed:
                counts[key] += 1
                union.add(sequence)
    return {**counts, "unique": len(union)}


def _planner_context(row: dict[str, Any]) -> tuple[int, int] | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
    except (KeyError, TypeError, ValueError):
        return None
    return first, last


def _alpha_ratio(source: str, target: str) -> float:
    source_alpha = sum(ch.isalpha() for ch in source)
    target_alpha = sum(ch.isalpha() for ch in target)
    if source_alpha <= 0:
        return 1.0 if target_alpha == 0 else float("inf")
    return target_alpha / source_alpha


def _non_question_punctuation_exact(source: str, target: str) -> bool:
    for left, right in (("(", ")"), ("[", "]"), ("{", "}")):
        if source.count(left) != target.count(left) or source.count(right) != target.count(right):
            return False
    return source.count("!") == target.count("!")


def _candidate(source: str, target: str, *, rank: int, score: Any) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    mechanically_admissible = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and ratio_passed
        and target.count("?") == source.count("?")
    )
    return {
        "rank": int(rank),
        "score": score,
        "target_text": target,
        "mechanically_admissible": mechanically_admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "source_question_marks": source.count("?"),
        "target_question_marks": target.count("?"),
    }


def _replace_contexts(
    base_rows: list[dict[str, Any]],
    selections: dict[int, str],
    prepared: dict[int, dict[str, Any]],
    content: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    removed_ids = {
        int(row["id"])
        for context_sequence in selections
        for row in prepared[context_sequence]["member_rows"]
    }
    output = [dict(row) for row in base_rows if int(row["id"]) not in removed_ids]
    for context_sequence, target in selections.items():
        case = prepared[context_sequence]
        output.append(
            {
                "id": -context_sequence,
                "sequence_number": 0,
                "kind": "translation_segment",
                "source_start": int(case["source_start"]),
                "source_end": int(case["source_end"]),
                "source_text": str(case["source_text"]),
                "target_text": str(target),
                "payload": {"research_question_context_replacement": True},
            }
        )
    output.sort(key=lambda row: int(row["source_start"]))
    for sequence, row in enumerate(output):
        row["sequence_number"] = sequence
    if "".join(str(row.get("source_text") or "") for row in output) != content:
        raise RuntimeError("question-context counterfactual source coverage drift")
    return output, _inventory(output)


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN18_QUESTION_CONTEXT_ROOT",
            "work/full-opticks-run18-capped-question-context-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("question-context DOE requires exact persisted run18 database")

    database_sha_before = _sha(database)
    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        base_output = dict(base_run.get("output") or {})
        context_run_id = int(base_output["context_run_id"])
        context_run = get_run(connection, context_run_id)
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        nlp_run_id = int(dict(context_run.get("output") or {})["nlp_run_id"])
        nlp_rows = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run18 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run18 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("run18 rows do not byte-exactly cover immutable source")
    if _inventory(base_rows) != BASE_COUNTS:
        raise RuntimeError(f"run18 hard-gate drift: {_inventory(base_rows)!r}")

    context_by_sequence = {int(row["sequence_number"]): row for row in context_rows}
    nlp_token_counts = Counter()
    for row in nlp_rows:
        payload = dict(row.get("payload") or {})
        nlp_token_counts[int(payload["sentence_index"])] += 1

    prepared: dict[int, dict[str, Any]] = {}
    for context_sequence, expected in EXPECTED_CONTEXTS.items():
        context = context_by_sequence.get(context_sequence)
        if context is None:
            raise RuntimeError(f"Stage10 context missing: {context_sequence}")
        start = int(context["source_start"])
        end = int(context["source_end"])
        source = str(context.get("source_text") or "")
        if [start, end] != [expected["source_start"], expected["source_end"]]:
            raise RuntimeError(f"context span drift: {context_sequence}")
        if content[start:end] != source:
            raise RuntimeError(f"context source drift: {context_sequence}")
        token_count = int(nlp_token_counts[context_sequence])
        if token_count != expected["nlp_tokens"] or token_count > WHOLE_CONTEXT_TOKEN_CAP:
            raise RuntimeError(f"context token/cap drift: {context_sequence} -> {token_count}")
        if source.count("?") != 1 or not source.rstrip().endswith("?"):
            raise RuntimeError(f"context is no longer one terminal question: {context_sequence}")

        members = [row for row in base_rows if _planner_context(row) == (context_sequence, context_sequence)]
        members = _ordered(members)
        if len(members) != expected["member_count"]:
            raise RuntimeError(f"context member-count drift: {context_sequence}")
        if "".join(str(row.get("source_text") or "") for row in members) != source:
            raise RuntimeError(f"context rows do not exactly cover source: {context_sequence}")
        aggregate_target = "".join(str(row.get("target_text") or "") for row in members)
        if aggregate_target.count("?") != 2:
            raise RuntimeError(f"context aggregate target question-count drift: {context_sequence}")

        premature_rows: list[int] = []
        for row in members:
            row_source = str(row.get("source_text") or "")
            row_target = str(row.get("target_text") or "")
            verdict = evaluate_rescue_pair(row_source, row_target)
            if (verdict.get("numeric_symbol") or {}).get("passed") is not True:
                raise RuntimeError(f"question context has numeric debt: {context_sequence}")
            if verdict.get("length_passed") is not True:
                raise RuntimeError(f"question context has length debt: {context_sequence}")
            if not _non_question_punctuation_exact(row_source, row_target):
                raise RuntimeError(f"question context has non-question punctuation debt: {context_sequence}")
            if row_source.count("?") == 0 and row_target.count("?") > 0:
                premature_rows.append(int(row["sequence_number"]))
        if len(premature_rows) != 1:
            raise RuntimeError(f"expected one premature question row: {context_sequence}")

        prepared[context_sequence] = {
            "context_sequence": context_sequence,
            "source_start": start,
            "source_end": end,
            "source_text": source,
            "nlp_token_count": token_count,
            "member_rows": members,
            "member_sequences": [int(row["sequence_number"]) for row in members],
            "premature_question_sequences": premature_rows,
            "aggregate_base_target": aggregate_target,
            "aggregate_source_question_marks": source.count("?"),
            "aggregate_base_target_question_marks": aggregate_target.count("?"),
        }

    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big_asset = load_tc_big_asset()
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    ordered_contexts = [prepared[key] for key in sorted(prepared)]
    sources = [str(case["source_text"]) for case in ordered_contexts]
    opus_generated = opus.translate(
        sources,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    tc_generated = tc_big.translate(
        sources,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if any(len(group) != NUM_HYPOTHESES for group in opus_generated + tc_generated):
        raise RuntimeError("question-context n-best cardinality drift")

    cases: list[dict[str, Any]] = []
    strategies: dict[str, dict[int, str]] = {
        "opus_rank0": {},
        "tc_big_rank0": {},
        "opus_first_admissible": {},
        "tc_big_first_admissible": {},
    }
    for case, opus_hypotheses, tc_hypotheses in zip(
        ordered_contexts, opus_generated, tc_generated, strict=True
    ):
        source = str(case["source_text"])
        model_results: dict[str, Any] = {}
        for model_name, hypotheses in (("opus", opus_hypotheses), ("tc_big", tc_hypotheses)):
            candidates = [
                _candidate(
                    source,
                    str(hypothesis.get("text") or ""),
                    rank=rank,
                    score=hypothesis.get("score"),
                )
                for rank, hypothesis in enumerate(hypotheses)
            ]
            admissible = [row for row in candidates if row["mechanically_admissible"]]
            first = None if not admissible else int(admissible[0]["rank"])
            rank0 = bool(candidates[0]["mechanically_admissible"])
            if rank0:
                strategies[f"{model_name}_rank0"][int(case["context_sequence"])] = str(
                    candidates[0]["target_text"]
                )
            if first is not None:
                strategies[f"{model_name}_first_admissible"][int(case["context_sequence"])] = str(
                    candidates[first]["target_text"]
                )
            model_results[model_name] = {
                "candidates": candidates,
                "rank0_mechanically_admissible": rank0,
                "first_mechanically_admissible_rank": first,
                "mechanically_admissible_ranks": [int(row["rank"]) for row in admissible],
            }
        cases.append({
            **{key: value for key, value in case.items() if key != "member_rows"},
            "models": model_results,
        })

    counterfactuals: dict[str, Any] = {}
    for name, selected in strategies.items():
        rows, counts = _replace_contexts(base_rows, selected, prepared, content)
        if any(counts[key] > BASE_COUNTS[key] for key in BASE_COUNTS):
            raise RuntimeError(f"question-context counterfactual regression: {name} -> {counts!r}")
        counterfactuals[name] = {
            "selected_context_sequences": sorted(selected),
            "selected_context_count": len(selected),
            "hard_gate_counts": counts,
            "segment_count": len(rows),
        }

    if _sha(database) != database_sha_before:
        raise RuntimeError("question-context DOE mutated persisted run18 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only exact-run18 OPUS/TC-big n-best DOE for <=160-token split Stage10 questions with premature target question marks",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "whole_context_token_cap": WHOLE_CONTEXT_TOKEN_CAP,
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "max_decoding_length": MAX_DECODING_LENGTH,
        "base_hard_gate_counts": BASE_COUNTS,
        "context_sequences": sorted(prepared),
        "cases": cases,
        "counterfactuals": counterfactuals,
        "tc_big_asset": {
            "repository": tc_big_asset.repository,
            "revision": tc_big_asset.revision,
            "model_safetensors_sha256": tc_big_asset.model_safetensors_sha256,
            "license": tc_big_asset.license,
            "manifest_sha256": tc_big_asset.manifest_sha256,
            "payload_tree_sha256": tc_big_asset.payload_tree_sha256,
        },
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-run18-capped-question-context-doe.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "contexts": sorted(prepared),
                "counterfactuals": counterfactuals,
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
