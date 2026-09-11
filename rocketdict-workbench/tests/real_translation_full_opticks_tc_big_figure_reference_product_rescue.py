from __future__ import annotations

"""Persist and independently audit the TC-big figure-reference rescue over run 11."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.alternative_mt_runtime import load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_figure_reference_rescue_stage import (
    TC_BIG_FIGURE_RESCUE_CONTRACT,
    TC_BIG_FIGURE_SELECTED_PHASE,
    TC_BIG_FIGURE_SELECTOR_CONTRACT,
    TC_BIG_FIGURE_TRIGGER_CONTRACT,
    run_stage12 as run_figure_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-figure-reference-product-rescue-optin/1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "329ed0cebe7b3af42b88b50f602c3bba3227fd75704e1e48fea4b1651169ded8"
BASE_RUN_ID = 11
BASE_OUTPUT_SHA256 = "ef38b21e7e7e384a00310123fd9f16ec10045b0741605867ad15f559f15c08c3"
BASE_COUNTS = {"numeric_symbol": 24, "punctuation": 20, "length": 0, "unique": 42}
ENABLED_COUNTS = {"numeric_symbol": 23, "punctuation": 19, "length": 0, "unique": 41}
BASE_SEGMENTS = 3344
ENABLED_SEGMENTS = 3344
EXPECTED_ATTEMPT_STARTS = [54796, 228046]
EXPECTED_ACCEPTED_STARTS = [228046]
EXPECTED_ACCEPTED_FIGURES = ["15"]
EXPECTED_UNTOUCHED = 3343


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
        if start != cursor or end <= start:
            raise RuntimeError(f"{label} source span drift at {sequence}")
        if content[start:end] != str(row.get("source_text") or ""):
            raise RuntimeError(f"{label} source bytes drift at {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage: {cursor} != {len(content)}")


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
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
        "counts": {
            "numeric_symbol": len(failures["numeric_symbol"]),
            "punctuation": len(failures["punctuation"]),
            "length": len(failures["length"]),
            "unique": len(union),
        },
    }


def _row_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
        str(row.get("target_text") or ""),
    )


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TC_BIG_FIGURE_PRODUCT_ROOT",
            "work/tc-big-figure-product-rescue",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("TC-big figure audit requires exact persisted run-11 database")
    asset = load_tc_big_asset()

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-11 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-11 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run-11 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run-11 baseline drift: {base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_tc_big_figure_reference_rescue": True,
            "tc_big_figure_reference_rescue_contract": TC_BIG_FIGURE_RESCUE_CONTRACT,
            "tc_big_figure_reference_selector_contract": TC_BIG_FIGURE_SELECTOR_CONTRACT,
            "tc_big_figure_reference_trigger_contract": TC_BIG_FIGURE_TRIGGER_CONTRACT,
            "tc_big_figure_reference_rescue_phase": TC_BIG_FIGURE_SELECTED_PHASE,
        }
    )
    enabled = run_figure_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    run_id = int(enabled["translation_run_id"])
    if run_id == BASE_RUN_ID or enabled.get("base_translation_run_id") != BASE_RUN_ID:
        raise RuntimeError("figure wrapper did not compose over exact run 11")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("figure wrapper base output SHA drift")

    attempts = list(enabled.get("tc_big_figure_reference_rescue_attempted_source_starts") or [])
    accepted = list(enabled.get("tc_big_figure_reference_rescue_accepted_source_starts") or [])
    if attempts != EXPECTED_ATTEMPT_STARTS:
        raise RuntimeError(f"figure attempt cohort drift: {attempts!r}")
    if accepted != EXPECTED_ACCEPTED_STARTS:
        raise RuntimeError(f"figure accepted cohort drift: {accepted!r}")
    if enabled.get("tc_big_figure_reference_rescue_attempt_count") != 2:
        raise RuntimeError("figure attempt-count drift")
    if enabled.get("tc_big_figure_reference_rescue_accepted_count") != 1:
        raise RuntimeError("figure accepted-count drift")
    if enabled.get("tc_big_figure_reference_rescue_rejected_count") != 1:
        raise RuntimeError("figure rejected-count drift")
    if enabled.get("base_segment_count") != BASE_SEGMENTS:
        raise RuntimeError("figure base segment-count drift")
    if enabled.get("segment_count") != ENABLED_SEGMENTS:
        raise RuntimeError("figure enabled segment-count drift")

    runtime = dict(enabled.get("tc_big_figure_reference_rescue_runtime") or {})
    if runtime.get("available") is not True:
        raise RuntimeError(f"figure persisted TC-big runtime unavailable: {runtime!r}")
    if runtime.get("asset_manifest_sha256") != asset.manifest_sha256:
        raise RuntimeError("figure persisted manifest identity drift")
    if runtime.get("asset_payload_tree_sha256") != asset.payload_tree_sha256:
        raise RuntimeError("figure persisted payload-tree identity drift")
    if runtime.get("asset_payload_file_count") != asset.payload_file_count:
        raise RuntimeError("figure persisted payload file-count drift")
    if runtime.get("asset_payload_bytes") != asset.payload_bytes:
        raise RuntimeError("figure persisted payload byte-count drift")
    if runtime.get("torch_required_for_inference") is not False:
        raise RuntimeError("figure persisted runtime unexpectedly requires Torch")
    if runtime.get("offline") is not True or runtime.get("compute_type") != "float32":
        raise RuntimeError("figure persisted runtime offline/compute drift")

    with connect(database, readonly=True) as connection:
        persisted = get_run(connection, run_id)
        rows = get_run_items(connection, run_id, kind="translation_segment")
    _coverage(rows, content, label="figure enabled")
    inventory = _inventory(rows)
    if inventory["counts"] != ENABLED_COUNTS or len(rows) != ENABLED_SEGMENTS:
        raise RuntimeError(
            f"figure gate drift: {inventory['counts']!r}, rows={len(rows)}"
        )

    base_by_start = {int(row["source_start"]): row for row in base_rows}
    untouched = 0
    applied_cases: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("tc_big_figure_reference_rescue") or {})
        if rescue.get("contract") != TC_BIG_FIGURE_RESCUE_CONTRACT:
            raise RuntimeError("figure row rescue contract drift")
        if rescue.get("selector_contract") != TC_BIG_FIGURE_SELECTOR_CONTRACT:
            raise RuntimeError("figure row selector contract drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
            "corpus_specific_target_patches",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe figure row flag: {flag}")

        base = base_by_start.get(int(row["source_start"]))
        if base is None:
            raise RuntimeError("figure output has unknown source start")
        if rescue.get("applied") is not True:
            if _row_identity(row) != _row_identity(base):
                raise RuntimeError("untouched figure row differs from exact run 11")
            untouched += 1
            continue

        figure_number = str(rescue.get("source_figure_number") or "")
        selected_rank = int(payload["selected_rank"])
        target = str(row.get("target_text") or "")
        hypotheses = list(payload.get("hypotheses") or [])
        selected_hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if int(hypothesis.get("rank", -1)) == selected_rank
        ]
        if len(selected_hypotheses) != 1:
            raise RuntimeError("figure selected rank is not unique in raw hypotheses")
        if str(selected_hypotheses[0].get("text") or "") != target:
            raise RuntimeError("figure target is not exact raw selected hypothesis")
        selection = dict(rescue.get("selection") or {})
        if selection.get("accepted") is not True or selection.get("strictly_eligible") is not True:
            raise RuntimeError("figure selected hypothesis fails strict persisted selector")
        if (selection.get("emphasis_markup") or {}).get("passed") is not True:
            raise RuntimeError("figure selected hypothesis loses Gutenberg emphasis")
        lead = dict(selection.get("target_reference_lead") or {})
        if lead.get("passed") is not True:
            raise RuntimeError("figure selected hypothesis loses source-owned reference lead")
        if lead.get("figure_number_preserved_in_lead") is not True:
            raise RuntimeError("figure selected hypothesis loses figure number in lead")
        if selection.get("source_alpha_ratio_passed") is not True:
            raise RuntimeError("figure selected hypothesis violates source-relative alpha bound")
        applied_cases.append(
            {
                "source_start": int(row["source_start"]),
                "source_figure_number": figure_number,
                "source_text": str(row.get("source_text") or ""),
                "base_target": str(base.get("target_text") or ""),
                "selected_rank": selected_rank,
                "selected_target": target,
                "selection": selection,
            }
        )

    applied_cases.sort(key=lambda case: case["source_start"])
    if [case["source_start"] for case in applied_cases] != EXPECTED_ACCEPTED_STARTS:
        raise RuntimeError("figure persisted accepted start drift")
    if [case["source_figure_number"] for case in applied_cases] != EXPECTED_ACCEPTED_FIGURES:
        raise RuntimeError("figure persisted source figure-number drift")
    if untouched != EXPECTED_UNTOUCHED:
        raise RuntimeError(f"figure untouched-row count drift: {untouched}")

    with sqlite3.connect(database) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign:
        raise RuntimeError(f"SQLite integrity drift: {integrity!r}, {foreign[:10]!r}")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off Product audit for TC-big leading Gutenberg figure-reference rescue",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "public_stage12_surface_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "persisted_database_sha256": _sha(database),
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "enabled_translation_run_id": run_id,
        "enabled_translation_output_sha256": str(persisted.get("output_sha256") or ""),
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_segment_count": BASE_SEGMENTS,
        "enabled_segment_count": len(rows),
        "base_hard_gate_counts": base_inventory["counts"],
        "enabled_hard_gate_counts": inventory["counts"],
        "attempt_count": 2,
        "accepted_count": 1,
        "rejected_count": 1,
        "attempted_source_starts": attempts,
        "accepted_source_starts": accepted,
        "selected_ranks": list(enabled.get("tc_big_figure_reference_rescue_selected_ranks") or []),
        "selected_targets": list(enabled.get("tc_big_figure_reference_rescue_selected_targets") or []),
        "untouched_base_exact_count": untouched,
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
        "applied_cases": applied_cases,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-tc-big-figure-reference-product-rescue-optin.json"
    destination.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "base_run_id": BASE_RUN_ID,
                "enabled_run_id": run_id,
                "base_counts": base_inventory["counts"],
                "enabled_counts": inventory["counts"],
                "attempted_source_starts": attempts,
                "accepted_source_starts": accepted,
                "selected_ranks": evidence["selected_ranks"],
                "selected_targets": evidence["selected_targets"],
                "persisted_database_sha256": evidence["persisted_database_sha256"],
                "enabled_output_sha256": evidence["enabled_translation_output_sha256"],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
