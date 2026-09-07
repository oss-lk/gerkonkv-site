from __future__ import annotations

"""Rescore stored full-Opticks rank-0 numeric failures without rerunning MT.

The input is the primary JSON from workflow run 34160613314.  It already stores
source/rank-0 target text for every unit that failed maintained numeric-v3.
Evaluator-only changes must be measured against those immutable translations;
rerunning OPUS would add generation noise and unnecessary compute.
"""

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from rocketdict.numeric_integrity import CONTRACT, evaluate_numeric_symbol_pair

SCHEMA = "rocketdict-full-opticks-numeric-rescore/1"
EXPECTED_INPUT_SCHEMA = "rocketdict-full-opticks-numeric-stress/1"
EXPECTED_INPUT_JSON_SHA256 = "0bc98070eacfd41448605261bc2c472165ed5d5938c6e26c3fdf34a7e25bf40f"
EXPECTED_INPUT_EVIDENCE_SHA256 = "56a34e2988786c285d5febe143b0e40562db27929fc212b4938ab4977e0ca130"
EXPECTED_SOURCE_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
SOURCE_ARTIFACT = {
    "workflow_run_id": 34160613314,
    "artifact_id": 10032753601,
    "artifact_zip_digest": "sha256:00b8e747483eea2b0ee1fc46101a1b5b6d32d830ae146ee4677cf423a60a5e1c",
}


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


def _diagnostic_flags(row: dict[str, Any]) -> list[str]:
    source = str(row.get("source_text") or "")
    verdict = dict(row.get("rank0_verdict") or {})
    flags: list[str] = []
    if re.search(r"\[(?:Illustration|Greek):", source, re.IGNORECASE) or re.search(
        r"_(?:Exper|Obs|Qu|Fig)\._", source, re.IGNORECASE
    ):
        flags.append("structural_label")
    if re.search(r"(?<![A-Za-z0-9])\d+(?:\.[A-Za-z]+)+\.\d+\.(?![A-Za-z0-9])", source):
        flags.append("section_id")
    if re.search(r"\b\d+[A-Z]\b", source) or re.search(r"\b[A-Z]\d+\b", source):
        flags.append("technical_coordinate_or_identifier")
    if any(len(value) >= 7 for value in re.findall(r"\d+", source)):
        flags.append("extreme_literal")
    if len(source.splitlines()) >= 3 and sum(char.isdigit() for char in source) >= 5:
        flags.append("table_like")
    if list(verdict.get("length_issues") or []):
        flags.append("length_failure")
    if list(verdict.get("punctuation_issues") or []):
        flags.append("punctuation_failure")
    if (verdict.get("critical_technical_tokens") or {}).get("passed") is False:
        flags.append("critical_token_failure")
    if (verdict.get("output_artifacts") or {}).get("passed") is False:
        flags.append("output_artifact_failure")
    selected = row.get("selected_strict_candidate")
    if isinstance(selected, dict):
        flags.append("strict_nbest_rescuable")
        if float(selected.get("similarity_to_rank0") or 0.0) >= 0.98:
            flags.append("strict_nbest_locality_ge_0_98")
    return flags


def rescore(input_path: Path) -> dict[str, Any]:
    input_sha = _sha_file(input_path)
    if input_sha != EXPECTED_INPUT_JSON_SHA256:
        raise RuntimeError(
            f"Full-Opticks stress JSON drift: {input_sha} != {EXPECTED_INPUT_JSON_SHA256}"
        )
    source = json.loads(input_path.read_text(encoding="utf-8"))
    if source.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise RuntimeError("Unexpected full-Opticks stress schema")
    if source.get("evidence_sha256") != EXPECTED_INPUT_EVIDENCE_SHA256:
        raise RuntimeError("Full-Opticks stress evidence identity drift")
    if source.get("source_sha256") != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")

    old_failures = list(source.get("numeric_failures") or [])
    changed_to_pass: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    routing_counts: Counter[str] = Counter()
    for row in old_failures:
        old_numeric = dict(
            ((row.get("rank0_verdict") or {}).get("numeric_symbol") or {}).get("numeric") or {}
        )
        current = evaluate_numeric_symbol_pair(
            str(row.get("source_text") or ""),
            str(row.get("rank0_target_text") or ""),
        )
        record = {
            "planned_sequence": int(row["planned_sequence"]),
            "old_missing": dict(old_numeric.get("missing") or {}),
            "ordinal_credit": dict((current.get("numeric") or {}).get("target_russian_ordinal_credit") or {}),
            "new_missing": dict((current.get("numeric") or {}).get("missing") or {}),
            "passed_current": current.get("passed") is True,
        }
        if current.get("passed") is True:
            changed_to_pass.append(record)
        else:
            remaining.append(record)
            routing_counts.update(_diagnostic_flags(row))

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "source_artifact": {
            **SOURCE_ARTIFACT,
            "stress_json_sha256": input_sha,
            "stress_evidence_sha256": str(source.get("evidence_sha256") or ""),
            "source_sha256": str(source.get("source_sha256") or ""),
            "planner_contract": source.get("stage12_planner_contract"),
        },
        "old_numeric_contract": "rocketdict-maintained-numeric-integrity/3",
        "new_numeric_contract": CONTRACT,
        "rescore_only": True,
        "mt_rerun_required": False,
        "old_rank0_numeric_failure_count": len(old_failures),
        "new_rank0_numeric_failure_count": len(remaining),
        "evaluator_only_false_positive_count": len(changed_to_pass),
        "evaluator_only_false_positive_sequences": [
            int(row["planned_sequence"]) for row in changed_to_pass
        ],
        "evaluator_only_changes": changed_to_pass,
        "remaining_failure_sequences": [int(row["planned_sequence"]) for row in remaining],
        "remaining_overlapping_diagnostic_counts": dict(sorted(routing_counts.items())),
        "note": "Remaining diagnostic counts overlap and are routing evidence, not a partition.",
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = rescore(args.input.expanduser().resolve())
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
