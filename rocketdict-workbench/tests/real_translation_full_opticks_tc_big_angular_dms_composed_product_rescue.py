from __future__ import annotations

"""Persist and independently audit angular-minute + short-DMS TC-big composition over run 14."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.alternative_mt_runtime import load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_angular_minute_rescue_stage import (
    TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT,
    TC_BIG_ANGULAR_MINUTE_SELECTED_PHASE,
    TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
    TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT,
)
from rocketdict.translation_tc_big_short_angular_dms_rescue_stage import (
    TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
    TC_BIG_SHORT_ANGULAR_DMS_SELECTED_PHASE,
    TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
    TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
    run_stage12 as run_dms_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-angular-dms-composed-product-rescue-optin/1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304"
BASE_RUN_ID = 14
BASE_OUTPUT_SHA256 = "12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44"
BASE_COUNTS = {"numeric_symbol": 22, "punctuation": 18, "length": 0, "unique": 39}
ANGULAR_OUTPUT_SHA256 = "0e0ebb851e43079b3029a2a2638d0dc0ff5eb45bebd6c91895cb04483349fb45"
ANGULAR_COUNTS = {"numeric_symbol": 21, "punctuation": 18, "length": 0, "unique": 38}
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 20, "punctuation": 18, "length": 0, "unique": 37}
BASE_SEGMENTS = 3344
ANGULAR_START = 431358
ANGULAR_TARGET = "В то же время появляется гало на расстоянии около 22 градусов 35' от центра Луны."
DMS_START = 110881
DMS_SOURCE = "Whence this Angle is 2 deg. 0'. 7''. "
DMS_BASE_TARGET = "Откуда угол 2 градуса. 0 футов 7 футов."
DMS_TARGET = "Откуда этот угол 2 град. 0'. 7''."
DMS_SELECTED_RANK = 2
EXPECTED_DMS = {"degrees": "2", "minutes": "0", "seconds": "7"}


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
        if (
            start != cursor
            or end <= start
            or content[start:end] != str(row.get("source_text") or "")
        ):
            raise RuntimeError(f"{label} source coverage drift at {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage")


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
        sequence = int(row["sequence_number"])
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
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
        "counts": {
            "numeric_symbol": len(failures["numeric_symbol"]),
            "punctuation": len(failures["punctuation"]),
            "length": len(failures["length"]),
            "unique": len(union),
        },
    }


def _identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
        str(row.get("target_text") or ""),
    )


def _by_start(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row["source_start"]): row for row in rows}


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TC_BIG_ANGULAR_DMS_PRODUCT_ROOT",
            "work/tc-big-angular-dms-composed-product-rescue",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("angular+DMS audit requires exact persisted run-14 database")
    asset = load_tc_big_asset()

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-14 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-14 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run-14 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run-14 baseline drift: {base_inventory['counts']!r}, rows={len(base_rows)}"
        )
    base_by_start = _by_start(base_rows)
    if str(base_by_start[DMS_START].get("source_text") or "") != DMS_SOURCE:
        raise RuntimeError("run-14 DMS source identity drift")
    if str(base_by_start[DMS_START].get("target_text") or "") != DMS_BASE_TARGET:
        raise RuntimeError("run-14 DMS target identity drift")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_tc_big_angular_minute_rescue": True,
            "tc_big_angular_minute_rescue_contract": TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT,
            "tc_big_angular_minute_selector_contract": TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
            "tc_big_angular_minute_trigger_contract": TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT,
            "tc_big_angular_minute_rescue_phase": TC_BIG_ANGULAR_MINUTE_SELECTED_PHASE,
            "enable_tc_big_short_angular_dms_rescue": True,
            "tc_big_short_angular_dms_rescue_contract": TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
            "tc_big_short_angular_dms_selector_contract": TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
            "tc_big_short_angular_dms_trigger_contract": TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
            "tc_big_short_angular_dms_rescue_phase": TC_BIG_SHORT_ANGULAR_DMS_SELECTED_PHASE,
        }
    )
    enabled = run_dms_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    angular_run_id = int(enabled["base_translation_run_id"])
    if final_run_id in {BASE_RUN_ID, angular_run_id} or angular_run_id == BASE_RUN_ID:
        raise RuntimeError("angular+DMS wrapper composition did not create distinct runs")
    if str(enabled.get("base_translation_output_sha256") or "") != ANGULAR_OUTPUT_SHA256:
        raise RuntimeError("DMS wrapper did not compose over the expected angular-minute output")

    with connect(database, readonly=True) as connection:
        angular_run = get_run(connection, angular_run_id)
        angular_rows = get_run_items(connection, angular_run_id, kind="translation_segment")
        final_run = get_run(connection, final_run_id)
        final_rows = get_run_items(connection, final_run_id, kind="translation_segment")

    if str(angular_run.get("output_sha256") or "") != ANGULAR_OUTPUT_SHA256:
        raise RuntimeError("angular-minute intermediate output identity drift")
    angular_output = dict(angular_run.get("output") or {})
    if angular_output.get("base_translation_run_id") != BASE_RUN_ID:
        raise RuntimeError("angular-minute intermediate did not compose over exact run 14")
    if str(angular_output.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("angular-minute intermediate base SHA drift")
    if angular_output.get("tc_big_angular_minute_rescue_attempt_count") != 1:
        raise RuntimeError("angular-minute attempt-count drift")
    if angular_output.get("tc_big_angular_minute_rescue_accepted_count") != 1:
        raise RuntimeError("angular-minute accepted-count drift")
    if list(angular_output.get("tc_big_angular_minute_rescue_attempted_source_starts") or []) != [ANGULAR_START]:
        raise RuntimeError("angular-minute attempt cohort drift")
    if list(angular_output.get("tc_big_angular_minute_rescue_accepted_source_starts") or []) != [ANGULAR_START]:
        raise RuntimeError("angular-minute accepted cohort drift")
    if list(angular_output.get("tc_big_angular_minute_rescue_selected_targets") or []) != [ANGULAR_TARGET]:
        raise RuntimeError("angular-minute selected target drift")
    _coverage(angular_rows, content, label="angular-minute intermediate")
    angular_inventory = _inventory(angular_rows)
    if angular_inventory["counts"] != ANGULAR_COUNTS or len(angular_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"angular-minute intermediate gate drift: {angular_inventory['counts']!r}, rows={len(angular_rows)}"
        )

    if enabled.get("tc_big_short_angular_dms_rescue_attempt_count") != 1:
        raise RuntimeError("DMS attempt-count drift")
    if enabled.get("tc_big_short_angular_dms_rescue_accepted_count") != 1:
        raise RuntimeError("DMS accepted-count drift")
    if enabled.get("tc_big_short_angular_dms_rescue_rejected_count") != 0:
        raise RuntimeError("DMS rejected-count drift")
    if list(enabled.get("tc_big_short_angular_dms_rescue_attempted_source_starts") or []) != [DMS_START]:
        raise RuntimeError("DMS attempt cohort drift")
    if list(enabled.get("tc_big_short_angular_dms_rescue_accepted_source_starts") or []) != [DMS_START]:
        raise RuntimeError("DMS accepted cohort drift")
    if list(enabled.get("tc_big_short_angular_dms_rescue_selected_ranks") or []) != [DMS_SELECTED_RANK]:
        raise RuntimeError("DMS selected-rank drift")
    if list(enabled.get("tc_big_short_angular_dms_rescue_selected_targets") or []) != [DMS_TARGET]:
        raise RuntimeError("DMS selected-target drift")
    if enabled.get("base_segment_count") != BASE_SEGMENTS or enabled.get("segment_count") != BASE_SEGMENTS:
        raise RuntimeError("DMS segment-count drift")

    runtime = dict(enabled.get("tc_big_short_angular_dms_rescue_runtime") or {})
    if runtime.get("available") is not True:
        raise RuntimeError(f"DMS TC-big runtime unavailable: {runtime!r}")
    if (
        runtime.get("asset_manifest_sha256") != asset.manifest_sha256
        or runtime.get("asset_payload_tree_sha256") != asset.payload_tree_sha256
        or runtime.get("asset_payload_file_count") != asset.payload_file_count
        or runtime.get("asset_payload_bytes") != asset.payload_bytes
    ):
        raise RuntimeError("DMS TC-big asset provenance drift")
    if (
        runtime.get("torch_required_for_inference") is not False
        or runtime.get("offline") is not True
        or runtime.get("compute_type") != "float32"
    ):
        raise RuntimeError("DMS runtime contract drift")

    _coverage(final_rows, content, label="angular+DMS final")
    final_inventory = _inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS or len(final_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"angular+DMS final gate drift: {final_inventory['counts']!r}, rows={len(final_rows)}"
        )

    angular_by_start = _by_start(angular_rows)
    final_by_start = _by_start(final_rows)
    if str(final_by_start[ANGULAR_START].get("target_text") or "") != ANGULAR_TARGET:
        raise RuntimeError("DMS composition regressed angular-minute selected target")

    untouched = 0
    applied: list[dict[str, Any]] = []
    for row in final_rows:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("tc_big_short_angular_dms_rescue") or {})
        if (
            rescue.get("contract") != TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT
            or rescue.get("selector_contract") != TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT
        ):
            raise RuntimeError("DMS row provenance contract drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
            "corpus_specific_target_patches",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe DMS row flag: {flag}")
        angular_base = angular_by_start.get(int(row["source_start"]))
        if angular_base is None:
            raise RuntimeError("DMS output has unknown source start")
        if rescue.get("applied") is not True:
            if _identity(row) != _identity(angular_base):
                raise RuntimeError("untouched DMS row differs from exact angular intermediate")
            untouched += 1
            continue

        if rescue.get("trigger_contract") != TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT:
            raise RuntimeError("DMS applied trigger-contract provenance drift")
        selected_rank = int(payload["selected_rank"])
        target = str(row.get("target_text") or "")
        matches = [
            hypothesis
            for hypothesis in list(payload.get("hypotheses") or [])
            if int(hypothesis.get("rank", -1)) == selected_rank
        ]
        if len(matches) != 1 or str(matches[0].get("text") or "") != target:
            raise RuntimeError("DMS selected target is not the exact raw hypothesis")
        selection = dict(rescue.get("selection") or {})
        trigger = dict(rescue.get("trigger") or {})
        if selection.get("accepted") is not True or selection.get("strictly_eligible") is not True:
            raise RuntimeError("DMS selected candidate fails strict selector")
        if selection.get("semantic_dms_preserved") is not True:
            raise RuntimeError("DMS selected candidate fails semantic DMS anchor")
        if (selection.get("prime_notation") or {}).get("passed") is not True:
            raise RuntimeError("DMS selected candidate fails prime preservation")
        if (
            (selection.get("emphasis_markup") or {}).get("passed") is not True
            or selection.get("source_alpha_ratio_passed") is not True
        ):
            raise RuntimeError("DMS selected candidate fails emphasis/ratio veto")
        if (
            trigger.get("eligible") is not True
            or trigger.get("exact_stage10_single_row_context") is not True
            or trigger.get("source_dms") != EXPECTED_DMS
            or trigger.get("source_contains_angle_word") is not True
            or trigger.get("source_exact_dms_prime_shape") is not True
        ):
            raise RuntimeError("DMS persisted trigger provenance drift")
        if (
            int(row["source_start"]) != DMS_START
            or str(row.get("source_text") or "") != DMS_SOURCE
            or target != DMS_TARGET
            or selected_rank != DMS_SELECTED_RANK
        ):
            raise RuntimeError("DMS persisted selected case drift")
        applied.append(
            {
                "source_start": int(row["source_start"]),
                "source_text": str(row.get("source_text") or ""),
                "base_target": str(angular_base.get("target_text") or ""),
                "selected_rank": selected_rank,
                "selected_target": target,
                "selection": selection,
                "trigger": trigger,
            }
        )

    if [case["source_start"] for case in applied] != [DMS_START]:
        raise RuntimeError("DMS persisted applied cohort drift")
    if untouched != BASE_SEGMENTS - 1:
        raise RuntimeError(f"DMS untouched-row count drift: {untouched}")

    # Independently prove that the intermediate angular layer changed exactly its one expected row.
    angular_changed = [
        start
        for start, row in angular_by_start.items()
        if _identity(row) != _identity(base_by_start[start])
    ]
    if angular_changed != [ANGULAR_START]:
        raise RuntimeError(f"angular-minute changed-row cohort drift: {angular_changed!r}")

    with sqlite3.connect(database) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign:
        raise RuntimeError(f"SQLite integrity drift: {integrity!r}, {foreign[:10]!r}")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off Product audit for composed angular-minute plus short-DMS TC-big rescues",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "public_stage12_surface_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "persisted_database_sha256": _sha(database),
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "angular_translation_run_id": angular_run_id,
        "angular_translation_output_sha256": str(angular_run.get("output_sha256") or ""),
        "final_translation_run_id": final_run_id,
        "final_translation_output_sha256": str(final_run.get("output_sha256") or ""),
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "segment_count": len(final_rows),
        "base_hard_gate_counts": base_inventory["counts"],
        "angular_hard_gate_counts": angular_inventory["counts"],
        "final_hard_gate_counts": final_inventory["counts"],
        "angular_changed_source_starts": angular_changed,
        "dms_attempt_count": 1,
        "dms_accepted_count": 1,
        "dms_rejected_count": 0,
        "dms_attempted_source_starts": [DMS_START],
        "dms_accepted_source_starts": [DMS_START],
        "dms_selected_ranks": [DMS_SELECTED_RANK],
        "dms_selected_targets": [DMS_TARGET],
        "dms_applied_cases": applied,
        "dms_untouched_angular_exact_count": untouched,
        "source_coverage_byte_exact": True,
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violation_count": len(foreign),
        "runtime": runtime,
        "asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
        },
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-tc-big-angular-dms-composed-product-rescue.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "angular_run_id": angular_run_id,
                "final_run_id": final_run_id,
                "base_counts": base_inventory["counts"],
                "angular_counts": angular_inventory["counts"],
                "final_counts": final_inventory["counts"],
                "dms_selected_rank": DMS_SELECTED_RANK,
                "dms_selected_target": DMS_TARGET,
                "persisted_database_sha256": evidence["persisted_database_sha256"],
                "final_translation_output_sha256": evidence["final_translation_output_sha256"],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
