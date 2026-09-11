from __future__ import annotations

"""Persist and audit the default-off TC-big punctuation-only boundary-pair rescue over run 16."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.alternative_mt_runtime import load_tc_big_asset
from rocketdict.context_sentence_boundaries import STAGE10_CONTEXT_IMPLEMENTATION_V1
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_boundary_pair_punctuation_rescue_stage import (
    TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT,
    TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTED_PHASE,
    TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT,
    TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT,
    run_stage12 as run_boundary_pair_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-boundary-pair-punctuation-rescue-optin/1"
BASE_DATABASE_SHA256 = "573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11"
BASE_RUN_ID = 16
BASE_OUTPUT_SHA256 = "767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 18, "length": 0, "unique": 37}
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 20, "punctuation": 17, "length": 0, "unique": 36}
BASE_SEGMENTS = 3344
EXPECTED_FINAL_SEGMENTS = 3343
EXPECTED_BOUNDARY = 522572
EXPECTED_LEFT_START = 522555
EXPECTED_TARGET = (
    "И откуда, кроме как от этой притягательной силы, та вода, которая одна только "
    "источает мягкую теплую жару, не будет источать из соли татарской без большой жары?"
)


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


def _coverage(rows: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for sequence, row in enumerate(_ordered(rows)):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError(f"{label} sequence drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        if start != cursor or end <= start or content[start:end] != str(row.get("source_text") or ""):
            raise RuntimeError(f"{label} source coverage drift at sequence {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage: {cursor} != {len(content)}")


def _hard_flags(source: str, target: str) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(source, target)
    return {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
        sequence = int(row["sequence_number"])
        flags = _hard_flags(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        for key, failed in flags.items():
            if failed:
                failures[key].append(sequence)
                union.add(sequence)
    return {
        "counts": {
            "numeric_symbol": len(failures["numeric_symbol"]),
            "punctuation": len(failures["punctuation"]),
            "length": len(failures["length"]),
            "unique": len(union),
        },
        "failures": failures,
    }


def _identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
        str(row.get("target_text") or ""),
    )


def _semantic_review(source: str, target: str) -> dict[str, Any]:
    """Diagnostic record for the single accepted pair; never selector input."""
    lowered = target.casefold()
    anchors = {
        "relation": "откуда" in lowered or "как не" in lowered,
        "attractive_power": "притяг" in lowered or "привлек" in lowered,
        "water": "вод" in lowered,
        "salt": "сол" in lowered,
        "heat": "тепл" in lowered or "жар" in lowered,
    }
    return {
        "source": source,
        "target": target,
        "diagnostic_anchors": anchors,
        "all_diagnostic_anchors": all(anchors.values()),
        "diagnostics_are_non_authoritative": True,
        "manual_semantic_review_still_required_for_product_promotion": True,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_BOUNDARY_PAIR_PRODUCT_ROOT",
            "work/full-opticks-tc-big-boundary-pair-punctuation-rescue",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("boundary-pair replay requires exact persisted run-16 database")

    asset = load_tc_big_asset()
    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        context_run = get_run(connection, context_run_id)
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-16 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-16 source identity drift")
    if str(context_run.get("implementation") or "") != STAGE10_CONTEXT_IMPLEMENTATION_V1:
        raise RuntimeError("run-16 is not based on Stage10 V1")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run-16 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run-16 baseline drift: counts={base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_tc_big_boundary_pair_punctuation_rescue": True,
            "tc_big_boundary_pair_punctuation_rescue_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT,
            "tc_big_boundary_pair_punctuation_selector_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT,
            "tc_big_boundary_pair_punctuation_trigger_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT,
            "tc_big_boundary_pair_punctuation_rescue_phase": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTED_PHASE,
        }
    )
    enabled = run_boundary_pair_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id == BASE_RUN_ID:
        raise RuntimeError("boundary-pair wrapper did not create a distinct Stage12 run")
    if int(enabled.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("boundary-pair wrapper did not compose directly over exact run 16")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("boundary-pair base output SHA drift")

    if enabled.get("tc_big_boundary_pair_punctuation_rescue_attempt_count") != 1:
        raise RuntimeError("boundary-pair attempt-count drift")
    if enabled.get("tc_big_boundary_pair_punctuation_rescue_accepted_count") != 1:
        raise RuntimeError("boundary-pair accepted-count drift")
    if enabled.get("tc_big_boundary_pair_punctuation_rescue_rejected_count") != 0:
        raise RuntimeError("boundary-pair rejected-count drift")
    if list(enabled.get("tc_big_boundary_pair_punctuation_rescue_attempted_boundaries") or []) != [EXPECTED_BOUNDARY]:
        raise RuntimeError("boundary-pair attempt cohort drift")
    if list(enabled.get("tc_big_boundary_pair_punctuation_rescue_accepted_boundaries") or []) != [EXPECTED_BOUNDARY]:
        raise RuntimeError("boundary-pair accepted boundary drift")
    if list(enabled.get("tc_big_boundary_pair_punctuation_rescue_accepted_source_starts") or []) != [EXPECTED_LEFT_START]:
        raise RuntimeError("boundary-pair accepted source-start drift")
    if list(enabled.get("tc_big_boundary_pair_punctuation_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("boundary-pair selector did not deterministically use raw rank0")
    if list(enabled.get("tc_big_boundary_pair_punctuation_rescue_selected_targets") or []) != [EXPECTED_TARGET]:
        raise RuntimeError("boundary-pair selected target drift")
    if enabled.get("base_segment_count") != BASE_SEGMENTS or enabled.get("segment_count") != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("boundary-pair segment-count drift")

    runtime = dict(enabled.get("tc_big_boundary_pair_punctuation_rescue_runtime") or {})
    if runtime.get("available") is not True:
        raise RuntimeError(f"TC-big runtime unavailable: {runtime!r}")
    if (
        runtime.get("asset_manifest_sha256") != asset.manifest_sha256
        or runtime.get("asset_payload_tree_sha256") != asset.payload_tree_sha256
        or runtime.get("asset_payload_file_count") != asset.payload_file_count
        or runtime.get("asset_payload_bytes") != asset.payload_bytes
    ):
        raise RuntimeError("TC-big asset provenance drift")
    if runtime.get("torch_required_for_inference") is not False or runtime.get("offline") is not True:
        raise RuntimeError("TC-big inference runtime contract drift")

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = _ordered(get_run_items(connection, final_run_id, kind="translation_segment"))
    _coverage(final_rows, content, label="boundary-pair final")
    final_inventory = _inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS or len(final_rows) != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError(
            f"boundary-pair final hard-gate drift: {final_inventory['counts']!r}, rows={len(final_rows)}"
        )

    base_by_start = {int(row["source_start"]): row for row in base_rows}
    applied: list[dict[str, Any]] = []
    untouched = 0
    for row in final_rows:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("tc_big_boundary_pair_punctuation_rescue") or {})
        if rescue.get("contract") != TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT:
            raise RuntimeError("boundary-pair row rescue contract drift")
        if rescue.get("selector_contract") != TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT:
            raise RuntimeError("boundary-pair row selector contract drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
            "corpus_specific_target_patches",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe boundary-pair row flag: {flag}")

        if rescue.get("applied") is not True:
            base = base_by_start.get(int(row["source_start"]))
            if base is None or _identity(row) != _identity(base):
                raise RuntimeError("untouched boundary-pair row differs from exact run16 row")
            untouched += 1
            continue

        if int(row["source_start"]) != EXPECTED_LEFT_START:
            raise RuntimeError("unexpected applied boundary-pair source start")
        if rescue.get("trigger_contract") != TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT:
            raise RuntimeError("applied boundary-pair trigger contract drift")
        if rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
            raise RuntimeError("applied boundary-pair row is not raw TC-big rank0")
        trigger = dict(rescue.get("trigger") or {})
        selection = dict(rescue.get("selection") or {})
        if trigger.get("eligible") is not True or trigger.get("stage10_v2_boundary_proven") is not True:
            raise RuntimeError("applied pair lacks independent Stage10-v2 source proof")
        if trigger.get("punctuation_only_hard_family") is not True:
            raise RuntimeError("applied pair escaped punctuation-only defect family")
        if trigger.get("base_pair_failure_counts") != {
            "numeric_symbol": 0,
            "punctuation": 1,
            "length": 0,
        }:
            raise RuntimeError("applied pair base hard-failure shape drift")
        if selection.get("accepted") is not True or selection.get("strictly_eligible") is not True:
            raise RuntimeError("applied pair selector evidence drift")
        if str(row.get("target_text") or "") != EXPECTED_TARGET:
            raise RuntimeError("applied pair target does not equal exact raw rank0")

        base_ids = list(rescue.get("base_translation_segment_ids") or [])
        if len(base_ids) != 2:
            raise RuntimeError("applied pair does not identify exactly two base rows")
        wanted_ids = {int(value) for value in base_ids}
        base_pair = [base for base in base_rows if int(base["id"]) in wanted_ids]
        base_pair.sort(key=lambda base: int(base["source_start"]))
        if len(base_pair) != 2:
            raise RuntimeError("applied pair base-row identity drift")
        combined_source = "".join(str(base.get("source_text") or "") for base in base_pair)
        if combined_source != str(row.get("source_text") or ""):
            raise RuntimeError("applied pair changed immutable source bytes")
        semantic = _semantic_review(combined_source, str(row.get("target_text") or ""))
        if semantic["all_diagnostic_anchors"] is not True:
            raise RuntimeError("accepted pair failed non-authoritative semantic diagnostics")
        applied.append(
            {
                "source_start": int(row["source_start"]),
                "boundary_offset": int(trigger["boundary_offset"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "base_targets": list(rescue.get("base_targets") or []),
                "selected_target": str(row["target_text"]),
                "trigger": trigger,
                "selection": selection,
                "semantic_review": semantic,
            }
        )

    if untouched != BASE_SEGMENTS - 2 or len(applied) != 1:
        raise RuntimeError(
            f"boundary-pair provenance count drift: untouched={untouched}, applied={len(applied)}"
        )

    with sqlite3.connect(database) as raw:
        integrity = str(raw.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = len(raw.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or foreign_keys != 0:
        raise RuntimeError(
            f"database integrity drift: integrity={integrity!r}, foreign_keys={foreign_keys}"
        )

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_run_id": BASE_RUN_ID,
        "base_output_sha256": BASE_OUTPUT_SHA256,
        "final_database_sha256": _sha(database),
        "final_run_id": final_run_id,
        "final_output_sha256": str(final_run.get("output_sha256") or ""),
        "base_segment_count": BASE_SEGMENTS,
        "final_segment_count": len(final_rows),
        "base_hard_gate_counts": base_inventory["counts"],
        "final_hard_gate_counts": final_inventory["counts"],
        "accepted_pair_count": len(applied),
        "accepted_pairs": applied,
        "untouched_base_row_count": untouched,
        "untouched_target_drift_count": 0,
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "foreign_key_violation_count": foreign_keys,
        "runtime": runtime,
        "asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
        },
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "public_stage12_surface_allowed": False,
        "semantic_review_required": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    report_path = root / "full-opticks-tc-big-boundary-pair-punctuation-rescue.json"
    report_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "base_counts": base_inventory["counts"],
                "final_counts": final_inventory["counts"],
                "accepted_boundaries": [row["boundary_offset"] for row in applied],
                "untouched_base_rows": untouched,
                "final_run_id": final_run_id,
                "final_output_sha256": evidence["final_output_sha256"],
                "final_database_sha256": evidence["final_database_sha256"],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
