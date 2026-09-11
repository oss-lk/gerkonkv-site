from __future__ import annotations

"""Persist and independently audit TC-big semicolon-question rescue over run 12."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.alternative_mt_runtime import load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_semicolon_question_rescue_stage import (
    TC_BIG_SEMICOLON_QUESTION_RESCUE_CONTRACT,
    TC_BIG_SEMICOLON_QUESTION_SELECTED_PHASE,
    TC_BIG_SEMICOLON_QUESTION_SELECTOR_CONTRACT,
    TC_BIG_SEMICOLON_QUESTION_TRIGGER_CONTRACT,
    run_stage12 as run_semicolon_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-semicolon-question-product-rescue-optin/1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "9d8f277651e1b6fef26de70479a088afbe9e0f8bd8c743ec3a4742914c0d217d"
BASE_RUN_ID = 12
BASE_OUTPUT_SHA256 = "57a8d2d519bf236c04b91d75b775a22b12f2a4c429cfc278ce6dba05c74a4063"
BASE_COUNTS = {"numeric_symbol": 23, "punctuation": 19, "length": 0, "unique": 41}
ENABLED_COUNTS = {"numeric_symbol": 23, "punctuation": 18, "length": 0, "unique": 40}
BASE_SEGMENTS = 3344
EXPECTED_START = 382298
EXPECTED_UNTOUCHED = 3343


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _coverage(rows: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for sequence, row in enumerate(_ordered(rows)):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError(f"{label} sequence drift")
        start = int(row["source_start"]); end = int(row["source_end"])
        if start != cursor or end <= start or content[start:end] != str(row.get("source_text") or ""):
            raise RuntimeError(f"{label} source coverage drift at {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage")


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
        sequence = int(row["sequence_number"])
        verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        if (verdict.get("numeric_symbol") or {}).get("passed") is not True:
            failures["numeric_symbol"].append(sequence); union.add(sequence)
        if verdict.get("punctuation_passed") is not True:
            failures["punctuation"].append(sequence); union.add(sequence)
        if verdict.get("length_passed") is not True:
            failures["length"].append(sequence); union.add(sequence)
    return {**failures, "counts": {"numeric_symbol": len(failures["numeric_symbol"]), "punctuation": len(failures["punctuation"]), "length": len(failures["length"]), "unique": len(union)}}


def _identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (int(row["source_start"]), int(row["source_end"]), str(row.get("source_text") or ""), str(row.get("target_text") or ""))


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_TC_BIG_SEMICOLON_PRODUCT_ROOT", "work/tc-big-semicolon-product-rescue")).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("TC-big semicolon audit requires exact persisted run-12 database")
    asset = load_tc_big_asset()

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-12 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-12 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run-12 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(f"run-12 baseline drift: {base_inventory['counts']!r}, rows={len(base_rows)}")

    parameters = dict(base_parameters)
    parameters.update({
        "enable_tc_big_semicolon_question_rescue": True,
        "tc_big_semicolon_question_rescue_contract": TC_BIG_SEMICOLON_QUESTION_RESCUE_CONTRACT,
        "tc_big_semicolon_question_selector_contract": TC_BIG_SEMICOLON_QUESTION_SELECTOR_CONTRACT,
        "tc_big_semicolon_question_trigger_contract": TC_BIG_SEMICOLON_QUESTION_TRIGGER_CONTRACT,
        "tc_big_semicolon_question_rescue_phase": TC_BIG_SEMICOLON_QUESTION_SELECTED_PHASE,
    })
    enabled = run_semicolon_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    run_id = int(enabled["translation_run_id"])
    if run_id == BASE_RUN_ID or enabled.get("base_translation_run_id") != BASE_RUN_ID:
        raise RuntimeError("semicolon wrapper did not compose over exact run 12")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("semicolon wrapper base output SHA drift")
    if enabled.get("tc_big_semicolon_question_rescue_attempt_count") != 1:
        raise RuntimeError("semicolon attempt-count drift")
    if enabled.get("tc_big_semicolon_question_rescue_accepted_count") != 1:
        raise RuntimeError("semicolon accepted-count drift")
    if enabled.get("tc_big_semicolon_question_rescue_rejected_count") != 0:
        raise RuntimeError("semicolon rejected-count drift")
    if list(enabled.get("tc_big_semicolon_question_rescue_attempted_source_starts") or []) != [EXPECTED_START]:
        raise RuntimeError("semicolon attempt cohort drift")
    if list(enabled.get("tc_big_semicolon_question_rescue_accepted_source_starts") or []) != [EXPECTED_START]:
        raise RuntimeError("semicolon accepted cohort drift")
    if enabled.get("base_segment_count") != BASE_SEGMENTS or enabled.get("segment_count") != BASE_SEGMENTS:
        raise RuntimeError("semicolon segment-count drift")

    runtime = dict(enabled.get("tc_big_semicolon_question_rescue_runtime") or {})
    if runtime.get("available") is not True:
        raise RuntimeError(f"semicolon TC-big runtime unavailable: {runtime!r}")
    if runtime.get("asset_manifest_sha256") != asset.manifest_sha256 or runtime.get("asset_payload_tree_sha256") != asset.payload_tree_sha256:
        raise RuntimeError("semicolon TC-big asset provenance drift")
    if runtime.get("asset_payload_file_count") != asset.payload_file_count or runtime.get("asset_payload_bytes") != asset.payload_bytes:
        raise RuntimeError("semicolon TC-big payload identity drift")
    if runtime.get("torch_required_for_inference") is not False or runtime.get("offline") is not True or runtime.get("compute_type") != "float32":
        raise RuntimeError("semicolon runtime contract drift")

    with connect(database, readonly=True) as connection:
        persisted = get_run(connection, run_id)
        rows = get_run_items(connection, run_id, kind="translation_segment")
    _coverage(rows, content, label="semicolon enabled")
    inventory = _inventory(rows)
    if inventory["counts"] != ENABLED_COUNTS or len(rows) != BASE_SEGMENTS:
        raise RuntimeError(f"semicolon gate drift: {inventory['counts']!r}, rows={len(rows)}")

    base_by_start = {int(row["source_start"]): row for row in base_rows}
    untouched = 0
    applied: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("tc_big_semicolon_question_rescue") or {})
        if rescue.get("contract") != TC_BIG_SEMICOLON_QUESTION_RESCUE_CONTRACT or rescue.get("selector_contract") != TC_BIG_SEMICOLON_QUESTION_SELECTOR_CONTRACT:
            raise RuntimeError("semicolon row provenance contract drift")
        for flag in ("source_bytes_rewritten", "target_rewriting", "placeholders", "post_translation_literal_injection", "corpus_specific_target_patches"):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe semicolon row flag: {flag}")
        base = base_by_start.get(int(row["source_start"]))
        if base is None:
            raise RuntimeError("semicolon output has unknown source start")
        if rescue.get("applied") is not True:
            if _identity(row) != _identity(base):
                raise RuntimeError("untouched semicolon row differs from exact run 12")
            untouched += 1
            continue
        selected_rank = int(payload["selected_rank"])
        target = str(row.get("target_text") or "")
        matches = [h for h in list(payload.get("hypotheses") or []) if int(h.get("rank", -1)) == selected_rank]
        if len(matches) != 1 or str(matches[0].get("text") or "") != target:
            raise RuntimeError("semicolon selected target is not exact raw hypothesis")
        selection = dict(rescue.get("selection") or {})
        if selection.get("accepted") is not True or selection.get("strictly_eligible") is not True:
            raise RuntimeError("semicolon selected candidate fails strict selector")
        if selection.get("semicolon_count_preserved") is not True or selection.get("question_count_preserved") is not True or selection.get("terminal_period_preserved") is not True:
            raise RuntimeError("semicolon selected candidate loses source punctuation contract")
        if (selection.get("emphasis_markup") or {}).get("passed") is not True or selection.get("source_alpha_ratio_passed") is not True:
            raise RuntimeError("semicolon selected candidate fails emphasis/ratio veto")
        applied.append({
            "source_start": int(row["source_start"]),
            "source_text": str(row.get("source_text") or ""),
            "base_target": str(base.get("target_text") or ""),
            "selected_rank": selected_rank,
            "selected_target": target,
            "selection": selection,
        })

    if [case["source_start"] for case in applied] != [EXPECTED_START]:
        raise RuntimeError("semicolon persisted applied cohort drift")
    if untouched != EXPECTED_UNTOUCHED:
        raise RuntimeError(f"semicolon untouched-row count drift: {untouched}")

    with sqlite3.connect(database) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign:
        raise RuntimeError(f"SQLite integrity drift: {integrity!r}, {foreign[:10]!r}")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off Product audit for TC-big semicolon-to-question substitution rescue",
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
        "attempt_count": 1,
        "accepted_count": 1,
        "rejected_count": 0,
        "attempted_source_starts": [EXPECTED_START],
        "accepted_source_starts": [EXPECTED_START],
        "selected_ranks": list(enabled.get("tc_big_semicolon_question_rescue_selected_ranks") or []),
        "selected_targets": list(enabled.get("tc_big_semicolon_question_rescue_selected_targets") or []),
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
        "applied_cases": applied,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-tc-big-semicolon-question-product-rescue-optin.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "base_run_id": BASE_RUN_ID,
        "enabled_run_id": run_id,
        "base_counts": base_inventory["counts"],
        "enabled_counts": inventory["counts"],
        "selected_ranks": evidence["selected_ranks"],
        "selected_targets": evidence["selected_targets"],
        "persisted_database_sha256": evidence["persisted_database_sha256"],
        "enabled_output_sha256": evidence["enabled_translation_output_sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
