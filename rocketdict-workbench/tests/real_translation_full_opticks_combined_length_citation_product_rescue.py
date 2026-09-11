from __future__ import annotations

"""Persist and audit the composed opt-in length + citation rescue on full Opticks.

The immutable structural-label-v2 Product database is reused. Public
``product.stage12.run`` is called with the already-proven length-failure
whole-context rescue plus the narrow inline ``Sect.`` citation-pair rescue.
The audit proves that composition keeps source bytes immutable, preserves every
untouched base row exactly, persists only raw rank-0 targets for rescued pairs,
and eliminates the two residual citation-induced length failures without
regressing the maintained numeric/symbol or punctuation hard gates.

This is research/promotion evidence. Both rescue switches remain disabled by
default.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_citation_rescue_stage import (
    CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
    CITATION_BOUNDARY_PAIR_SELECTED_PHASE,
    CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
    DEFAULT_MAX_SOURCE_CHARS,
)
from rocketdict.translation_length_rescue_stage import (
    LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
    LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE,
    LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
)
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_rescue_stage import MAX_WHOLE_CONTEXT_NLP_TOKENS
from rocketdict.translation_stage import PLANNER_CONTRACT
from rocketdict_workbench.core import RocketDictCore

SCHEMA = "rocketdict-full-opticks-combined-length-citation-product-rescue-optin/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
BASELINE_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"
EXPECTED_LENGTH_CONTEXTS = [577, 629, 919]
EXPECTED_CITATION_SOURCE_STARTS = [24799, 151438]
EXPECTED_BASELINE_GATES = {"numeric_symbol": 30, "punctuation": 34, "length": 5}
EXPECTED_LENGTH_BASE_GATES = {"numeric_symbol": 29, "punctuation": 34, "length": 2}


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


def _call(core: RocketDictCore, database: Path, operation: str, **params: Any) -> dict[str, Any]:
    return dict(
        core.api(
            database,
            "call",
            operation,
            "--params",
            json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            timeout=7200,
        )
    )


def _ordered(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda row: int(row["sequence_number"]))


def _assert_source_coverage(items: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for expected_sequence, row in enumerate(_ordered(items)):
        if int(row["sequence_number"]) != expected_sequence:
            raise RuntimeError(f"{label} sequence numbering drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"{label} source coverage is not byte-exact")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} does not cover the complete immutable source")


def _hard_gate_inventory(items: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(items):
        sequence = int(row["sequence_number"])
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        if (verdict.get("numeric_symbol") or {}).get("passed") is not True:
            failures["numeric_symbol"].append(sequence)
            union.add(sequence)
        if verdict.get("punctuation_passed") is not True:
            failures["punctuation"].append(sequence)
            union.add(sequence)
        if verdict.get("length_passed") is not True:
            failures["length"].append(sequence)
            union.add(sequence)
    return {
        **failures,
        "counts": {key: len(value) for key, value in failures.items()},
        "unique_failure_count": len(union),
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_COMBINED_RESCUE_ROOT", "work/combined-rescue")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Combined rescue audit requires pinned baseline JSON and DB")
    if _sha(baseline_path) != BASELINE_JSON_SHA256:
        raise RuntimeError("Combined rescue baseline JSON identity drift")
    if _sha(database) != BASELINE_DATABASE_SHA256:
        raise RuntimeError("Combined rescue baseline database identity drift before execution")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise RuntimeError("Combined rescue baseline schema drift")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Combined rescue pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Combined rescue audit requires planner-v8 baseline")

    canonical_run_id = int(baseline["stage12"]["translation_run_id"])
    context_run_id = int(baseline["stage10"]["context_run_id"])
    document_version_id = int(baseline["document_version_id"])
    stage12_parameters = dict(baseline.get("stage12_parameters") or {})
    if stage12_parameters.get("enable_selective_resegmentation_rescue") is not False:
        raise RuntimeError("Canonical baseline unexpectedly enables semicolon rescue")
    if stage12_parameters.get("enable_whole_context_rescue") is not False:
        raise RuntimeError("Canonical baseline unexpectedly enables numeric whole-context rescue")

    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        canonical_run = get_run(connection, canonical_run_id)
        canonical_items = get_run_items(connection, canonical_run_id, kind="translation_segment")
    content = str(document["content_text"])
    canonical_output_sha = str(canonical_run.get("output_sha256") or "")
    _assert_source_coverage(canonical_items, content, label="canonical Stage12")
    canonical_gates = _hard_gate_inventory(canonical_items)
    if canonical_gates["counts"] != EXPECTED_BASELINE_GATES:
        raise RuntimeError(
            f"Canonical full hard-gate inventory drift: {canonical_gates['counts']!r}"
        )

    enabled_parameters = dict(stage12_parameters)
    enabled_parameters.update(
        {
            "enable_length_failure_whole_context_rescue": True,
            "length_failure_whole_context_rescue_contract": LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
            "length_failure_whole_context_rescue_selector_contract": LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
            "length_failure_whole_context_rescue_phase": LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE,
            "length_failure_whole_context_rescue_max_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
            "enable_citation_boundary_pair_rescue": True,
            "citation_boundary_pair_rescue_contract": CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
            "citation_boundary_pair_rescue_selector_contract": CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
            "citation_boundary_pair_rescue_phase": CITATION_BOUNDARY_PAIR_SELECTED_PHASE,
            "citation_boundary_pair_rescue_max_source_chars": DEFAULT_MAX_SOURCE_CHARS,
        }
    )
    enabled = _call(
        RocketDictCore(),
        database,
        "product.stage12.run",
        context_run_id=context_run_id,
        parameters=enabled_parameters,
        implementation="opus-en-ru-ct2",
    )
    enabled_run_id = int(enabled["translation_run_id"])
    length_base_run_id = int(enabled.get("base_translation_run_id") or 0)
    if enabled_run_id in {canonical_run_id, length_base_run_id}:
        raise RuntimeError("Combined rescue did not create a distinct persisted Stage12 run")
    if enabled.get("citation_boundary_pair_rescue_enabled") is not True:
        raise RuntimeError("Public Stage12 did not enable citation-boundary pair rescue")
    if enabled.get("citation_boundary_pair_rescue_contract") != CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT:
        raise RuntimeError("Public Stage12 citation rescue contract drift")

    with connect(database, readonly=True) as connection:
        length_base_run = get_run(connection, length_base_run_id)
        length_base_items = get_run_items(
            connection, length_base_run_id, kind="translation_segment"
        )
        enabled_run = get_run(connection, enabled_run_id)
        enabled_items = get_run_items(connection, enabled_run_id, kind="translation_segment")
    length_base_output = dict(length_base_run.get("output") or {})
    if length_base_output.get("length_failure_whole_context_rescue_enabled") is not True:
        raise RuntimeError("Citation wrapper base is not the requested length-rescue run")
    length_attempted = [
        int(value)
        for value in length_base_output.get(
            "length_failure_whole_context_rescue_attempted_context_sequences", []
        )
    ]
    length_accepted = [
        int(value)
        for value in length_base_output.get(
            "length_failure_whole_context_rescue_accepted_context_sequences", []
        )
    ]
    if length_attempted != EXPECTED_LENGTH_CONTEXTS or length_accepted != EXPECTED_LENGTH_CONTEXTS:
        raise RuntimeError(
            f"Composed length-rescue cohort drift: attempted={length_attempted}, accepted={length_accepted}"
        )
    _assert_source_coverage(length_base_items, content, label="length-rescue base Stage12")
    length_base_gates = _hard_gate_inventory(length_base_items)
    if length_base_gates["counts"] != EXPECTED_LENGTH_BASE_GATES:
        raise RuntimeError(
            f"Composed length-rescue hard-gate drift: {length_base_gates['counts']!r}"
        )

    attempted_pair_count = int(enabled.get("citation_boundary_pair_rescue_attempted_pair_count") or 0)
    accepted_pair_count = int(enabled.get("citation_boundary_pair_rescue_accepted_pair_count") or 0)
    rejected_pair_count = int(enabled.get("citation_boundary_pair_rescue_rejected_pair_count") or 0)
    accepted_starts = [
        int(value) for value in enabled.get("citation_boundary_pair_rescue_accepted_source_starts", [])
    ]
    if attempted_pair_count != 2 or accepted_pair_count != 2 or rejected_pair_count != 0:
        raise RuntimeError(
            "Citation pair cohort drift: "
            f"attempted={attempted_pair_count}, accepted={accepted_pair_count}, rejected={rejected_pair_count}"
        )
    if accepted_starts != EXPECTED_CITATION_SOURCE_STARTS:
        raise RuntimeError(f"Citation pair source-start cohort drift: {accepted_starts}")

    _assert_source_coverage(enabled_items, content, label="combined-rescue Stage12")
    base_by_id = {int(row["id"]): row for row in length_base_items}
    copied_base_count = 0
    applied_rows: list[dict[str, Any]] = []
    for row in enabled_items:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("citation_boundary_pair_rescue") or {})
        if rescue.get("contract") != CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT:
            raise RuntimeError("Selected row lacks citation-rescue contract provenance")
        if rescue.get("selector_contract") != CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT:
            raise RuntimeError("Selected row lacks citation-rescue selector provenance")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"Citation-rescue row violates {flag}=False")

        if rescue.get("applied") is True:
            hypotheses = list(payload.get("hypotheses") or [])
            if not hypotheses:
                raise RuntimeError("Applied citation-rescue row lacks raw hypotheses")
            raw_rank0 = str((hypotheses[0] or {}).get("text") or "")
            if str(row.get("target_text") or "") != raw_rank0:
                raise RuntimeError("Applied citation-rescue target is not exact raw rank0")
            if rescue.get("raw_model_rank0") is not True:
                raise RuntimeError("Applied citation-rescue row lost raw-rank0 provenance")
            if rescue.get("trigger") != "bare_roman_after_sect_length_failure":
                raise RuntimeError("Applied citation-rescue row lost source-defined trigger")
            if rescue.get("new_strict_debt"):
                raise RuntimeError("Applied citation-rescue row introduced new strict debt")
            applied_rows.append(row)
            continue

        if rescue.get("applied") is not False:
            raise RuntimeError("Citation-rescue applied state is ambiguous")
        base_id = int(rescue.get("base_translation_segment_id") or 0)
        base = base_by_id.get(base_id)
        if base is None:
            raise RuntimeError("Copied citation-rescue row references unknown length-base segment")
        for field in ("source_start", "source_end", "source_text", "target_text"):
            if row.get(field) != base.get(field):
                raise RuntimeError(f"Untouched row changed length-rescue base {field}")
        copied_base_count += 1

    if sorted(int(row["source_start"]) for row in applied_rows) != EXPECTED_CITATION_SOURCE_STARTS:
        raise RuntimeError("Persisted applied citation rows do not match expected source pairs")

    enabled_gates = _hard_gate_inventory(enabled_items)
    if enabled_gates["counts"]["length"] != 0:
        raise RuntimeError(
            f"Combined rescue must eliminate all five baseline length failures: {enabled_gates['counts']}"
        )
    if enabled_gates["counts"]["numeric_symbol"] > length_base_gates["counts"]["numeric_symbol"]:
        raise RuntimeError("Citation rescue regressed full numeric/symbol hard gate")
    if enabled_gates["counts"]["punctuation"] > length_base_gates["counts"]["punctuation"]:
        raise RuntimeError("Citation rescue regressed punctuation hard gate")
    if enabled_gates["unique_failure_count"] > length_base_gates["unique_failure_count"]:
        raise RuntimeError("Citation rescue increased unique hard-failing segments")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "public Product Stage12 composed opt-in length and inline-citation rescue over immutable full Opticks",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "document_version_id": document_version_id,
        "source_text_sha256": str(document["text_sha256"]),
        "source_char_count": len(content),
        "planner_contract": PLANNER_CONTRACT,
        "canonical_translation_run_id": canonical_run_id,
        "canonical_translation_output_sha256": canonical_output_sha,
        "length_base_translation_run_id": length_base_run_id,
        "length_base_translation_output_sha256": str(length_base_run.get("output_sha256") or ""),
        "enabled_translation_run_id": enabled_run_id,
        "enabled_translation_output_sha256": str(enabled_run.get("output_sha256") or ""),
        "length_rescue_contract": LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
        "citation_rescue_contract": CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
        "citation_selector_contract": CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
        "length_accepted_context_sequences": length_accepted,
        "citation_accepted_source_starts": accepted_starts,
        "canonical_hard_gate_counts": canonical_gates["counts"],
        "length_base_hard_gate_counts": length_base_gates["counts"],
        "enabled_hard_gate_counts": enabled_gates["counts"],
        "canonical_unique_hard_failure_count": canonical_gates["unique_failure_count"],
        "length_base_unique_hard_failure_count": length_base_gates["unique_failure_count"],
        "enabled_unique_hard_failure_count": enabled_gates["unique_failure_count"],
        "canonical_segment_count": len(canonical_items),
        "length_base_segment_count": len(length_base_items),
        "enabled_segment_count": len(enabled_items),
        "copied_length_base_row_count": copied_base_count,
        "applied_citation_pair_count": len(applied_rows),
        "source_coverage_byte_exact": True,
        "untouched_rows_base_exact": True,
        "applied_targets_exact_raw_rank0": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_sha256_before": BASELINE_DATABASE_SHA256,
        "database_sha256_after": _sha(database),
    }
    evidence = dict(payload)
    payload["evidence_sha256"] = _canonical_sha(evidence)
    output = root / "full-opticks-combined-length-citation-product-rescue-optin.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "canonical_hard_gate_counts": canonical_gates["counts"],
                "length_base_hard_gate_counts": length_base_gates["counts"],
                "enabled_hard_gate_counts": enabled_gates["counts"],
                "canonical_unique_hard_failure_count": canonical_gates["unique_failure_count"],
                "length_base_unique_hard_failure_count": length_base_gates["unique_failure_count"],
                "enabled_unique_hard_failure_count": enabled_gates["unique_failure_count"],
                "citation_accepted_source_starts": accepted_starts,
                "enabled_segment_count": len(enabled_items),
                "database_sha256_after": payload["database_sha256_after"],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
