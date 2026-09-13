from __future__ import annotations

"""Read-only exact-row rank0 screening for run56 punctuation residuals.

This DOE does not define or promote a rescue.  It authenticates the current
full-Opticks forward parent, derives the punctuation-failure cohort from the
maintained evaluator, then asks pinned OPUS and pinned TC-big for exactly one
raw rank0 hypothesis for each immutable current source row.  Candidate evidence
is retained only to discover source-defined families worth a narrower DOE.

No source rewriting, target rewriting, placeholders, literal injection,
evaluator changes, or n-best selection are performed.  The database is opened
read-only and its byte identity is checked before and after the experiment.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run56-punctuation-exact-row-rank0-screening/1"
BASE_DATABASE_SHA256 = "cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56"
BASE_RUN_ID = 56
BASE_OUTPUT_SHA256 = "2971fb099674aa81c14e0b75590c5fbcb943d1ea3477efb0ceedbd81bd69fbc5"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SEGMENT_COUNT = 3335
EXPECTED_PUNCTUATION_FAILURE_COUNT = 14
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1536
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.55
HARD_PUNCTUATION = "()[]{}?!"


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
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


def _alpha(text: str) -> int:
    return sum(character.isalpha() for character in text)


def _punctuation_counts(text: str) -> dict[str, int]:
    return {symbol: text.count(symbol) for symbol in HARD_PUNCTUATION}


def _source_shape(source: str, target: str) -> dict[str, Any]:
    source_counts = _punctuation_counts(source)
    target_counts = _punctuation_counts(target)
    missing = {
        symbol: source_counts[symbol] - target_counts[symbol]
        for symbol in HARD_PUNCTUATION
        if source_counts[symbol] > target_counts[symbol]
    }
    added = {
        symbol: target_counts[symbol] - source_counts[symbol]
        for symbol in HARD_PUNCTUATION
        if target_counts[symbol] > source_counts[symbol]
    }
    return {
        "source_hard_punctuation": source_counts,
        "base_target_hard_punctuation": target_counts,
        "missing_hard_punctuation": missing,
        "added_hard_punctuation": added,
        "source_round_pair_count": min(source_counts["("], source_counts[")"]),
        "source_square_pair_count": min(source_counts["["], source_counts["]"]),
        "source_question_count": source_counts["?"],
        "source_exclamation_count": source_counts["!"],
        "source_char_count": len(source),
        "source_alpha_count": _alpha(source),
    }


def _rank0_batch(translator: Any, sources: list[str]) -> list[dict[str, Any]]:
    generated = translator.translate(
        sources,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != len(sources):
        raise RuntimeError("rank0 screening model batch cardinality drift")
    output: list[dict[str, Any]] = []
    for source, hypotheses in zip(sources, generated, strict=True):
        if len(hypotheses) != 1:
            raise RuntimeError(f"rank0 screening hypothesis cardinality drift for {source[:80]!r}")
        hypothesis = dict(hypotheses[0])
        if int(hypothesis.get("rank", -1)) != 0:
            raise RuntimeError("rank0 screening received non-rank0 hypothesis")
        target = str(hypothesis.get("text") or "")
        if not target.strip():
            raise RuntimeError("rank0 screening received empty target")
        output.append(
            {
                "rank": 0,
                "text": target,
                "score": hypothesis.get("score"),
            }
        )
    return output


def _candidate(source: str, target: str, *, base_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_counts = _punctuation_counts(source)
    target_counts = _punctuation_counts(target)
    hard_punctuation_exact = source_counts == target_counts
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    alpha_ratio = target_alpha / source_alpha if source_alpha else 1.0
    alpha_ratio_passed = MIN_SOURCE_ALPHA_RATIO <= alpha_ratio <= MAX_SOURCE_ALPHA_RATIO
    base_alpha_retention = target_alpha >= base_alpha
    screening_passed = bool(
        verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and hard_punctuation_exact
        and alpha_ratio_passed
        and base_alpha_retention
    )
    return {
        "screening_passed": screening_passed,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_hard_punctuation": source_counts,
        "target_hard_punctuation": target_counts,
        "hard_punctuation_exact": hard_punctuation_exact,
        "source_alpha_ratio": alpha_ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": alpha_ratio_passed,
        "base_alpha_count": base_alpha,
        "candidate_alpha_count": target_alpha,
        "base_alpha_retained": base_alpha_retention,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN56_PUNCTUATION_SCREENING_ROOT",
            "work/run56-punctuation-rank0-screening",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(
        os.environ.get(
            "ROCKETDICT_RUN56_PUNCTUATION_SCREENING_DB",
            root / "rocketdict.sqlite",
        )
    ).resolve()
    if not database.is_file():
        raise RuntimeError(f"run56 screening database is missing: {database}")
    database_sha_before = _sha(database)
    if database_sha_before != BASE_DATABASE_SHA256:
        raise RuntimeError(f"run56 screening database identity drift: {database_sha_before}")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        run_output = dict(run.get("output") or {})
        document = get_document(connection, int(run_output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run56 screening output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run56 screening source identity drift")
    if len(rows) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError(f"run56 screening segment-count drift: {len(rows)}")

    content = str(document["content_text"])
    cursor = 0
    cohort: list[dict[str, Any]] = []
    for sequence, row in enumerate(rows):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError("run56 screening translation sequence drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"run56 screening source coverage drift at {sequence}")
        cursor = end
        verdict = evaluate_rescue_pair(source, target)
        if verdict.get("punctuation_passed") is not True:
            cohort.append(
                {
                    "row": row,
                    "base_verdict": verdict,
                    "source_shape": _source_shape(source, target),
                }
            )
    if cursor != len(content):
        raise RuntimeError("run56 screening incomplete source coverage")
    if len(cohort) != EXPECTED_PUNCTUATION_FAILURE_COUNT:
        raise RuntimeError(
            f"run56 punctuation cohort drift: {len(cohort)} != {EXPECTED_PUNCTUATION_FAILURE_COUNT}"
        )

    sources = [str(item["row"]["source_text"]) for item in cohort]
    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    opus_rank0 = _rank0_batch(opus, sources)
    tc_big_rank0 = _rank0_batch(tc_big, sources)

    cases: list[dict[str, Any]] = []
    model_pass_counts: Counter[str] = Counter()
    source_shape_passes: dict[str, list[int]] = {}
    for item, opus_raw, tc_raw in zip(cohort, opus_rank0, tc_big_rank0, strict=True):
        row = item["row"]
        source = str(row["source_text"])
        base_target = str(row["target_text"])
        opus_candidate = {
            "model": "opus",
            "raw_rank": 0,
            "raw_score": opus_raw.get("score"),
            "raw_target": str(opus_raw["text"]),
            **_candidate(source, str(opus_raw["text"]), base_target=base_target),
        }
        tc_candidate = {
            "model": "tc_big",
            "raw_rank": 0,
            "raw_score": tc_raw.get("score"),
            "raw_target": str(tc_raw["text"]),
            **_candidate(source, str(tc_raw["text"]), base_target=base_target),
        }
        for candidate in (opus_candidate, tc_candidate):
            if candidate["screening_passed"] is True:
                model_pass_counts[str(candidate["model"])] += 1
        shape = dict(item["source_shape"])
        shape_key = json.dumps(
            {
                "missing": shape["missing_hard_punctuation"],
                "added": shape["added_hard_punctuation"],
                "round_pairs": shape["source_round_pair_count"],
                "square_pairs": shape["source_square_pair_count"],
                "questions": shape["source_question_count"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        passing_models = [
            candidate["model"]
            for candidate in (opus_candidate, tc_candidate)
            if candidate["screening_passed"] is True
        ]
        if passing_models:
            source_shape_passes.setdefault(shape_key, []).append(int(row["sequence_number"]))
        cases.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "base_target": base_target,
                "base_verdict": item["base_verdict"],
                "source_shape": shape,
                "opus": opus_candidate,
                "tc_big": tc_candidate,
                "screening_passing_models": passing_models,
            }
        )

    if _sha(database) != database_sha_before:
        raise RuntimeError("read-only run56 punctuation screening mutated database")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only exact-row raw-rank0 screening of run56 punctuation residuals for narrower source-defined DOE discovery",
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "translation_segment_count": len(rows),
        "punctuation_failure_count": len(cohort),
        "punctuation_failure_sequences": [
            int(item["row"]["sequence_number"]) for item in cohort
        ],
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "selection_authorized_ranks": [0],
        "model_screening_pass_counts": dict(sorted(model_pass_counts.items())),
        "source_shape_passing_sequences": source_shape_passes,
        "cases": cases,
        "database_unchanged": True,
        "source_coverage_byte_exact": True,
        "raw_rank0_only": True,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "narrow_source_defined_followup_required": True,
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
    evidence_path = root / "run56-punctuation-exact-row-rank0-screening.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "punctuation_failure_count": len(cohort),
        "model_screening_pass_counts": evidence["model_screening_pass_counts"],
        "passing_cases": [
            {
                "sequence_number": case["sequence_number"],
                "source_start": case["source_start"],
                "passing_models": case["screening_passing_models"],
                "missing_hard_punctuation": case["source_shape"]["missing_hard_punctuation"],
                "added_hard_punctuation": case["source_shape"]["added_hard_punctuation"],
            }
            for case in cases
            if case["screening_passing_models"]
        ],
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
