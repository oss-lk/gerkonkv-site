from __future__ import annotations

"""Research-only pair-level rescue probe for the two residual Opticks length failures.

The maintained Product planner must not classify bare ``IV.``/``II.`` fragments as
headings: in the pinned Opticks source they are the continuation of an inline
``Sect.`` citation.  This experiment therefore leaves source segmentation and the
Product database unchanged.  It takes the immutable Product Stage12 row ending in
``Sect. `` plus the immediately following bare Roman row, translates that exact
contiguous source pair once with pinned real OPUS, and evaluates the raw rank-0
candidate with the maintained rescue evaluator.

The report deliberately distinguishes Product hard-gate cleanliness from stricter
research debt.  A candidate is only marked mechanically promising when it clears
all Product hard gates, repairs the bare-Roman length failure, and introduces no
new strict-debt category relative to the two primary rows.  Nothing is promoted
or persisted by this script.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-citation-pair-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
EXPECTED_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"

EXPECTED_CASES = (
    {
        "case": "sect-iv",
        "sequence_number": 157,
        "source_text": "IV. ",
        "previous_sequence_number": 156,
        "previous_source_suffix": "_Lectures of Light and Colours_, Sect. ",
    },
    {
        "case": "sect-ii",
        "sequence_number": 864,
        "source_text": "II. ",
        "previous_sequence_number": 863,
        "previous_source_suffix": "_Lectures of Light and Colours_, Part I. Sect. ",
    },
)


def _sha_file(path: Path) -> str:
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


def _strict_debt(verdict: dict[str, Any]) -> set[str]:
    debt: set[str] = set()
    if verdict.get("numeric_symbol", {}).get("passed") is not True:
        debt.add("numeric_symbol")
    if verdict.get("punctuation_passed") is not True:
        debt.add("punctuation")
    if verdict.get("length_passed") is not True:
        debt.add("length")
    if verdict.get("numeric_order", {}).get("passed") is not True:
        debt.add("numeric_order")
    if verdict.get("delimiter_preservation", {}).get("passed") is not True:
        debt.add("delimiter_preservation")
    for name in verdict.get("critical_technical_tokens", {}).get("failed_checks") or []:
        debt.add(f"critical:{name}")
    if verdict.get("output_artifacts", {}).get("passed") is not True:
        debt.add("output_artifacts")
    return debt


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_CITATION_PAIR_ROOT", "work/citation-pair")).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Citation pair feasibility immutable baseline inputs are missing")
    if _sha_file(baseline_path) != EXPECTED_BASELINE_JSON_SHA256:
        raise RuntimeError("Citation pair feasibility baseline JSON identity drift")
    if _sha_file(database) != EXPECTED_DATABASE_SHA256:
        raise RuntimeError("Citation pair feasibility Product database identity drift")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("Citation pair feasibility baseline schema drift")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Citation pair feasibility source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Citation pair feasibility requires planner-v8 baseline")

    selected_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    document_version_id = int(baseline["document_version_id"])
    with connect(database, readonly=True) as connection:
        rows = get_run_items(connection, selected_run_id, kind="translation_segment")
        document = get_document(connection, document_version_id)
    content = str(document["content_text"])
    if str(document["text_sha256"]) != str(baseline["source_text_sha256"]):
        raise RuntimeError("Citation pair feasibility persisted source text identity drift")
    ordered = sorted(rows, key=lambda row: int(row["sequence_number"]))
    by_sequence = {int(row["sequence_number"]): row for row in ordered}
    if "".join(str(row.get("source_text") or "") for row in ordered) != content:
        raise RuntimeError("Citation pair feasibility Stage12 source coverage drift")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    cases: list[dict[str, Any]] = []
    for expected in EXPECTED_CASES:
        current = by_sequence[int(expected["sequence_number"])]
        previous = by_sequence[int(expected["previous_sequence_number"])]
        current_source = str(current.get("source_text") or "")
        previous_source = str(previous.get("source_text") or "")
        if current_source != expected["source_text"]:
            raise RuntimeError(f"Pinned {expected['case']} current source drift")
        if not previous_source.endswith(str(expected["previous_source_suffix"])):
            raise RuntimeError(f"Pinned {expected['case']} previous citation prefix drift")
        if int(previous["source_end"]) != int(current["source_start"]):
            raise RuntimeError(f"Pinned {expected['case']} rows are no longer contiguous")

        start = int(previous["source_start"])
        end = int(current["source_end"])
        pair_source = content[start:end]
        if pair_source != previous_source + current_source:
            raise RuntimeError(f"Pinned {expected['case']} pair differs from immutable source")

        generated = translator.translate(
            [pair_source],
            beam_size=6,
            num_hypotheses=1,
            max_decoding_length=256,
        )
        if len(generated) != 1 or not generated[0]:
            raise RuntimeError(f"Pinned {expected['case']} OPUS cardinality drift")
        hypothesis = generated[0][0]
        target = str(hypothesis.get("text") or "")
        if not target.strip():
            raise RuntimeError(f"Pinned {expected['case']} OPUS returned empty rank-0 target")

        previous_verdict = evaluate_rescue_pair(previous_source, str(previous.get("target_text") or ""))
        current_verdict = evaluate_rescue_pair(current_source, str(current.get("target_text") or ""))
        candidate_verdict = evaluate_rescue_pair(pair_source, target)
        primary_debt = _strict_debt(previous_verdict) | _strict_debt(current_verdict)
        candidate_debt = _strict_debt(candidate_verdict)
        new_debt = candidate_debt - primary_debt
        mechanically_promising = (
            current_verdict.get("length_passed") is not True
            and candidate_verdict.get("product_hard_passed") is True
            and candidate_verdict.get("length_passed") is True
            and not new_debt
        )
        cases.append(
            {
                "case": expected["case"],
                "previous_sequence_number": int(previous["sequence_number"]),
                "sequence_number": int(current["sequence_number"]),
                "source_start": start,
                "source_end": end,
                "source_text": pair_source,
                "primary_rows": [
                    {
                        "sequence_number": int(previous["sequence_number"]),
                        "source_text": previous_source,
                        "target_text": str(previous.get("target_text") or ""),
                        "verdict": previous_verdict,
                    },
                    {
                        "sequence_number": int(current["sequence_number"]),
                        "source_text": current_source,
                        "target_text": str(current.get("target_text") or ""),
                        "verdict": current_verdict,
                    },
                ],
                "candidate": {
                    "target_text": target,
                    "rank": int(hypothesis.get("rank") or 0),
                    "score": hypothesis.get("score"),
                    "verdict": candidate_verdict,
                },
                "primary_strict_debt": sorted(primary_debt),
                "candidate_strict_debt": sorted(candidate_debt),
                "new_strict_debt": sorted(new_debt),
                "mechanically_promising": mechanically_promising,
                "source_bytes_rewritten": False,
                "target_rewriting": False,
                "placeholders": False,
                "post_translation_literal_injection": False,
            }
        )

    report = {
        "schema": SCHEMA,
        "purpose": "research-only pair-level rescue feasibility for residual inline citation length failures",
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "baseline_json_sha256": _sha_file(baseline_path),
        "baseline_database_sha256": _sha_file(database),
        "selected_translation_run_id": selected_run_id,
        "case_count": len(cases),
        "mechanically_promising_count": sum(bool(case["mechanically_promising"]) for case in cases),
        "strict_clean_candidate_count": sum(
            case["candidate"]["verdict"].get("strict_research_passed") is True for case in cases
        ),
        "cases": cases,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_unchanged": _sha_file(database) == EXPECTED_DATABASE_SHA256,
    }
    evidence = dict(report)
    report["evidence_sha256"] = _canonical_sha(evidence)
    output = root / "full-opticks-citation-pair-feasibility.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if report["database_unchanged"] is not True:
        raise RuntimeError("Citation pair feasibility mutated the Product database")
    if report["case_count"] != len(EXPECTED_CASES):
        raise RuntimeError("Citation pair feasibility case count drift")

    print(json.dumps({
        "schema": SCHEMA,
        "case_count": report["case_count"],
        "mechanically_promising_count": report["mechanically_promising_count"],
        "strict_clean_candidate_count": report["strict_clean_candidate_count"],
        "cases": [
            {
                "case": case["case"],
                "candidate_target": case["candidate"]["target_text"],
                "candidate_product_hard_passed": case["candidate"]["verdict"].get("product_hard_passed"),
                "candidate_strict_research_passed": case["candidate"]["verdict"].get("strict_research_passed"),
                "primary_strict_debt": case["primary_strict_debt"],
                "candidate_strict_debt": case["candidate_strict_debt"],
                "new_strict_debt": case["new_strict_debt"],
                "mechanically_promising": case["mechanically_promising"],
            }
            for case in cases
        ],
        "evidence_sha256": report["evidence_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
