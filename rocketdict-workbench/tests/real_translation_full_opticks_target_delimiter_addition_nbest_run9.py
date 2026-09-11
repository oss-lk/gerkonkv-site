from __future__ import annotations

"""Research-only raw n-best screening for target-only delimiter additions on run 9.

The cohort is defined mechanically from the persisted output: the immutable
source row contains no round/square/curly delimiter characters while the current
target introduces at least one, and the maintained punctuation hard gate fails.
No target cleanup is performed.  We ask only whether the same exact source has
an unmodified pinned-OPUS n-best hypothesis that passes the existing strict
selector plus Gutenberg emphasis preservation.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-target-delimiter-addition-nbest-run9/1"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
RUN_OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
EXPECTED_SEQUENCES = [3, 1864, 1878, 2219, 2382, 2862, 3220]
EXPECTED_STARTS = [488, 326217, 329423, 388656, 417917, 501398, 569170]
DELIMITERS = "()[]{}"


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    unique: set[int] = set()
    for row in _ordered(rows):
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
        seq = int(row["sequence_number"])
        failures = {
            "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key, failed in failures.items():
            if failed:
                counts[key] += 1
                unique.add(seq)
    return {**counts, "unique": len(unique)}


def _target_only_delimiter_addition(row: dict[str, Any]) -> bool:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    if any(source.count(char) for char in DELIMITERS):
        return False
    if not any(target.count(char) for char in DELIMITERS):
        return False
    verdict = evaluate_rescue_pair(source, target)
    return verdict.get("punctuation_passed") is not True


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TARGET_DELIMITER_NBEST_ROOT",
            "work/target-delimiter-addition-nbest-run9",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != DB_SHA:
        raise RuntimeError("run9 database identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN_ID)
        rows = get_run_items(connection, RUN_ID, kind="translation_segment")
        document = get_document(
            connection, int(dict(run.get("output") or {})["document_version_id"])
        )
    if str(run.get("output_sha256") or "") != RUN_OUTPUT_SHA:
        raise RuntimeError("run9 output identity drift")
    if str(document.get("text_sha256") or "") != TEXT_SHA:
        raise RuntimeError("run9 source identity drift")
    content = str(document["content_text"])
    rows = _ordered(rows)
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run9 source coverage drift")
    if _inventory(rows) != BASE:
        raise RuntimeError(f"run9 hard-gate drift: {_inventory(rows)!r}")

    cohort = [row for row in rows if _target_only_delimiter_addition(row)]
    sequences = [int(row["sequence_number"]) for row in cohort]
    starts = [int(row["source_start"]) for row in cohort]
    if sequences != EXPECTED_SEQUENCES or starts != EXPECTED_STARTS:
        raise RuntimeError(
            f"target-only delimiter cohort drift: seq={sequences!r} starts={starts!r}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [str(row.get("source_text") or "") for row in cohort],
        beam_size=6,
        num_hypotheses=6,
        max_decoding_length=512,
    )
    if len(generated) != len(cohort) or any(len(group) != 6 for group in generated):
        raise RuntimeError("target-delimiter n-best cardinality drift")

    cases: list[dict[str, Any]] = []
    replacements: dict[int, dict[str, Any]] = {}
    for row, hypotheses in zip(cohort, generated, strict=True):
        candidates: list[dict[str, Any]] = []
        first_admissible: int | None = None
        source = str(row.get("source_text") or "")
        for rank, hypothesis in enumerate(hypotheses):
            target = str(hypothesis.get("text") or "")
            verdict = evaluate_rescue_pair(source, target)
            emphasis = compare_emphasis_markup_preservation(source, target)
            admissible = (
                verdict.get("strictly_eligible") is True
                and emphasis.get("passed") is True
            )
            candidates.append(
                {
                    "rank": rank,
                    "target_text": target,
                    "score": hypothesis.get("score"),
                    "verdict": verdict,
                    "emphasis_markup": emphasis,
                    "mechanically_admissible": admissible,
                }
            )
            if first_admissible is None and admissible:
                first_admissible = rank
        if first_admissible is not None:
            replacements[int(row["id"])] = {
                **dict(row),
                "target_text": str(candidates[first_admissible]["target_text"]),
                "payload": {
                    **dict(row.get("payload") or {}),
                    "research_target_delimiter_addition_nbest": {
                        "selected_rank": first_admissible,
                        "raw_model_candidate": True,
                    },
                },
            }
        cases.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "base_target_text": str(row.get("target_text") or ""),
                "base_target_delimiter_counts": {
                    char: str(row.get("target_text") or "").count(char)
                    for char in DELIMITERS
                    if str(row.get("target_text") or "").count(char)
                },
                "candidates": candidates,
                "first_mechanically_admissible_rank": first_admissible,
                "first_mechanically_admissible_target": (
                    None
                    if first_admissible is None
                    else candidates[first_admissible]["target_text"]
                ),
            }
        )

    candidate_rows = [
        dict(replacements.get(int(row["id"]), row))
        for row in rows
    ]
    for sequence, row in enumerate(candidate_rows):
        row["sequence_number"] = sequence
    if "".join(str(row.get("source_text") or "") for row in candidate_rows) != content:
        raise RuntimeError("target-delimiter counterfactual source coverage drift")
    counterfactual = _inventory(candidate_rows)
    if any(counterfactual[key] > BASE[key] for key in BASE):
        raise RuntimeError(f"target-delimiter counterfactual regression: {counterfactual!r}")
    if _sha(database) != DB_SHA:
        raise RuntimeError("target-delimiter n-best research mutated run9 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only exact-source raw OPUS n-best screening for existing target-only "
            "delimiter additions; no target cleanup or delimiter deletion"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": RUN_OUTPUT_SHA,
        "cohort_definition": (
            "source has zero ()[]{} characters; current target introduces >=1; "
            "maintained punctuation hard gate fails"
        ),
        "attempted_sequences": sequences,
        "attempted_source_starts": starts,
        "attempt_count": len(cohort),
        "selected_sequences": [
            case["sequence_number"]
            for case in cases
            if case["first_mechanically_admissible_rank"] is not None
        ],
        "base_hard_gate_counts": BASE,
        "counterfactual_hard_gate_counts": counterfactual,
        "cases": cases,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    out = root / "full-opticks-target-delimiter-addition-nbest-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "selected_sequences": payload["selected_sequences"],
                "selected": [
                    (case["sequence_number"], case["first_mechanically_admissible_rank"], case["first_mechanically_admissible_target"])
                    for case in cases
                ],
                "counterfactual_hard_gate_counts": counterfactual,
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
