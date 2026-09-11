from __future__ import annotations

"""Persist and audit opt-in length-failure whole-context rescue on full Opticks.

The immutable structural-label-v2 Product database is reused.  Public
``product.stage12.run`` is invoked with only the dedicated length-failure
whole-context research flag.  The audit proves exact source coverage, unchanged
non-rescued rows, raw rank-0 provenance, trigger/selector identity and full
maintained hard-gate deltas over the persisted selected rows.

This is promotion evidence only; Product defaults remain unchanged.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_length_rescue_stage import (
    LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
    LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
    LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE,
)
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_rescue_stage import MAX_WHOLE_CONTEXT_NLP_TOKENS
from rocketdict.translation_stage import PLANNER_CONTRACT
from rocketdict_workbench.core import RocketDictCore

SCHEMA = "rocketdict-full-opticks-length-failure-product-rescue-optin/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
BASELINE_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"
EXPECTED_CONTEXTS = [577, 629, 919]
EXPECTED_ALPHA_RELAXED = [577, 629]
EXPECTED_BASELINE_GATES = {"numeric_symbol": 30, "punctuation": 34, "length": 5}


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
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
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
        "numeric_symbol": failures["numeric_symbol"],
        "punctuation": failures["punctuation"],
        "length": failures["length"],
        "counts": {key: len(value) for key, value in failures.items()},
        "unique_failure_count": len(union),
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_LENGTH_PRODUCT_ROOT", "work/length-product")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Length-rescue Product audit requires pinned baseline JSON and DB")
    if _sha(baseline_path) != BASELINE_JSON_SHA256:
        raise RuntimeError("Length-rescue baseline JSON identity drift")
    if _sha(database) != BASELINE_DATABASE_SHA256:
        raise RuntimeError("Length-rescue baseline database identity drift before execution")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise RuntimeError("Length-rescue baseline schema drift")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Length-rescue pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Length-rescue audit requires planner-v8 baseline")

    base_run_id = int(baseline["stage12"]["translation_run_id"])
    context_run_id = int(baseline["stage10"]["context_run_id"])
    document_version_id = int(baseline["document_version_id"])
    stage12_parameters = dict(baseline.get("stage12_parameters") or {})
    if stage12_parameters.get("enable_selective_resegmentation_rescue") is not False:
        raise RuntimeError("Canonical baseline unexpectedly enables semicolon rescue")
    if stage12_parameters.get("enable_whole_context_rescue") is not False:
        raise RuntimeError("Canonical baseline unexpectedly enables numeric whole-context rescue")

    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        base_run = get_run(connection, base_run_id)
        base_items = get_run_items(connection, base_run_id, kind="translation_segment")
    content = str(document["content_text"])
    base_output_sha = str(base_run.get("output_sha256") or "")
    if not base_output_sha:
        raise RuntimeError("Canonical baseline lacks selected Stage12 output identity")
    _assert_source_coverage(base_items, content, label="baseline Stage12")
    baseline_gates = _hard_gate_inventory(base_items)
    if baseline_gates["counts"] != EXPECTED_BASELINE_GATES:
        raise RuntimeError(
            f"Baseline full hard-gate inventory drift: {baseline_gates['counts']!r}"
        )

    enabled_parameters = dict(stage12_parameters)
    enabled_parameters.update(
        {
            "enable_length_failure_whole_context_rescue": True,
            "length_failure_whole_context_rescue_contract": (
                LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
            ),
            "length_failure_whole_context_rescue_selector_contract": (
                LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
            ),
            "length_failure_whole_context_rescue_phase": (
                LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE
            ),
            "length_failure_whole_context_rescue_max_nlp_tokens": (
                MAX_WHOLE_CONTEXT_NLP_TOKENS
            ),
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
    if enabled_run_id == base_run_id:
        raise RuntimeError("Opt-in length rescue incorrectly reused disabled Stage12 run")
    if enabled.get("length_failure_whole_context_rescue_enabled") is not True:
        raise RuntimeError("Public Stage12 did not enable length-failure rescue")
    if int(enabled.get("base_translation_run_id") or 0) != base_run_id:
        raise RuntimeError("Length-rescue wrapper did not reuse canonical selected Stage12 base")
    if str(enabled.get("base_translation_output_sha256") or "") != base_output_sha:
        raise RuntimeError("Length-rescue wrapper changed canonical selected Stage12 base output")

    attempted = [
        int(value)
        for value in enabled.get(
            "length_failure_whole_context_rescue_attempted_context_sequences", []
        )
    ]
    accepted = [
        int(value)
        for value in enabled.get(
            "length_failure_whole_context_rescue_accepted_context_sequences", []
        )
    ]
    rejected = [
        int(value)
        for value in enabled.get(
            "length_failure_whole_context_rescue_rejected_context_sequences", []
        )
    ]
    skipped = [
        int(value)
        for value in enabled.get(
            "length_failure_whole_context_rescue_skipped_over_cap_context_sequences", []
        )
    ]
    alpha_relaxed = [
        int(value)
        for value in enabled.get(
            "length_failure_whole_context_rescue_alpha_relaxed_context_sequences", []
        )
    ]
    if attempted != EXPECTED_CONTEXTS or accepted != EXPECTED_CONTEXTS:
        raise RuntimeError(
            f"Length-rescue Product cohort drift: attempted={attempted}, accepted={accepted}"
        )
    if rejected or skipped:
        raise RuntimeError(
            f"Length-rescue expected no rejected/over-cap cases: rejected={rejected}, skipped={skipped}"
        )
    if alpha_relaxed != EXPECTED_ALPHA_RELAXED:
        raise RuntimeError(f"Length-rescue alpha-relaxed cohort drift: {alpha_relaxed}")

    with connect(database, readonly=True) as connection:
        enabled_run = get_run(connection, enabled_run_id)
        enabled_items = get_run_items(connection, enabled_run_id, kind="translation_segment")
    _assert_source_coverage(enabled_items, content, label="length-rescued Stage12")

    applied_contexts: list[int] = []
    copied_base_count = 0
    base_by_id = {int(row["id"]): row for row in base_items}
    for row in enabled_items:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("length_failure_whole_context_rescue") or {})
        if rescue.get("contract") != LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT:
            raise RuntimeError("Selected row lacks length-rescue contract provenance")
        if rescue.get("selector_contract") != LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT:
            raise RuntimeError("Selected row lacks length-rescue selector provenance")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"Length-rescue row violates {flag}=False")

        if rescue.get("applied") is True:
            context_sequence = int(rescue["context_sequence"])
            applied_contexts.append(context_sequence)
            hypotheses = list(payload.get("hypotheses") or [])
            if not hypotheses:
                raise RuntimeError("Applied length-rescue row lacks raw hypotheses")
            raw_rank0 = str((hypotheses[0] or {}).get("text") or "")
            if str(row.get("target_text") or "") != raw_rank0:
                raise RuntimeError("Applied length-rescue target is not exact raw rank0")
            if rescue.get("raw_model_rank0") is not True:
                raise RuntimeError("Applied length-rescue row lost raw-rank0 provenance")
            if rescue.get("trigger") != "primary_length_ratio_failure":
                raise RuntimeError("Applied length-rescue row lost source-defined trigger")
            continue

        if rescue.get("applied") is not False:
            raise RuntimeError("Length-rescue applied state is ambiguous")
        base_id = int(rescue.get("base_translation_segment_id") or 0)
        base = base_by_id.get(base_id)
        if base is None:
            raise RuntimeError("Copied length-rescue row references unknown base segment")
        for field in ("source_start", "source_end", "source_text", "target_text"):
            if row.get(field) != base.get(field):
                raise RuntimeError(f"Non-rescued row changed canonical base {field}")
        copied_base_count += 1

    if sorted(applied_contexts) != EXPECTED_CONTEXTS:
        raise RuntimeError(f"Applied length-rescue context provenance drift: {applied_contexts}")

    enabled_gates = _hard_gate_inventory(enabled_items)
    if enabled_gates["counts"]["length"] != 2:
        raise RuntimeError(
            f"Length-rescue must remove exactly three baseline length failures: {enabled_gates['counts']}"
        )
    if enabled_gates["counts"]["numeric_symbol"] > baseline_gates["counts"]["numeric_symbol"]:
        raise RuntimeError("Length-rescue regressed full numeric/symbol hard gate")
    if enabled_gates["counts"]["punctuation"] > baseline_gates["counts"]["punctuation"]:
        raise RuntimeError("Length-rescue regressed punctuation hard gate")
    if enabled_gates["unique_failure_count"] > baseline_gates["unique_failure_count"]:
        raise RuntimeError("Length-rescue increased unique hard-failing segments")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "actual public Product Stage12 opt-in length-failure whole-context rescue "
            "over immutable full Opticks baseline"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "document_version_id": document_version_id,
        "source_text_sha256": str(document["text_sha256"]),
        "source_char_count": len(content),
        "planner_contract": PLANNER_CONTRACT,
        "rescue_contract": LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
        "selector_contract": LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
        "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        "baseline_translation_run_id": base_run_id,
        "baseline_translation_output_sha256": base_output_sha,
        "enabled_translation_run_id": enabled_run_id,
        "attempted_context_sequences": attempted,
        "accepted_context_sequences": accepted,
        "rejected_context_sequences": rejected,
        "skipped_over_cap_context_sequences": skipped,
        "alpha_relaxed_context_sequences": alpha_relaxed,
        "baseline_hard_gate_counts": baseline_gates["counts"],
        "enabled_hard_gate_counts": enabled_gates["counts"],
        "baseline_unique_hard_failure_count": baseline_gates["unique_failure_count"],
        "enabled_unique_hard_failure_count": enabled_gates["unique_failure_count"],
        "hard_gate_count_delta": {
            key: enabled_gates["counts"][key] - baseline_gates["counts"][key]
            for key in EXPECTED_BASELINE_GATES
        },
        "baseline_segment_count": len(base_items),
        "enabled_segment_count": len(enabled_items),
        "copied_base_row_count": copied_base_count,
        "applied_rescue_row_count": len(applied_contexts),
        "source_coverage_byte_exact": True,
        "non_rescued_rows_base_exact": True,
        "applied_targets_exact_raw_rank0": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-length-failure-product-rescue-optin.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "attempted_context_sequences": attempted,
                "accepted_context_sequences": accepted,
                "alpha_relaxed_context_sequences": alpha_relaxed,
                "baseline_hard_gate_counts": baseline_gates["counts"],
                "enabled_hard_gate_counts": enabled_gates["counts"],
                "baseline_unique_hard_failure_count": baseline_gates["unique_failure_count"],
                "enabled_unique_hard_failure_count": enabled_gates["unique_failure_count"],
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
