from __future__ import annotations

"""Persist and audit the narrow TC-big footnote-reference lead rescue over run 10."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.alternative_mt_runtime import load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_footnote_reference_rescue_stage import (
    TC_BIG_FOOTNOTE_RESCUE_CONTRACT,
    TC_BIG_FOOTNOTE_SELECTED_PHASE,
    TC_BIG_FOOTNOTE_SELECTOR_CONTRACT,
    TC_BIG_FOOTNOTE_TRIGGER_CONTRACT,
    run_stage12 as run_footnote_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-footnote-reference-product-rescue-optin/1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "4a5bd2159c1aca0b5bcf5580d7aa0d767f0faedd2b1dcdaef92dab96a36d3087"
BASE_RUN_ID = 10
BASE_OUTPUT_SHA256 = "6dec2080a8fe21716587e4f4ffbe1f8ebf816911b542ab99ac598a8462ed01df"
BASE_COUNTS = {"numeric_symbol": 24, "punctuation": 25, "length": 0, "unique": 47}
ENABLED_COUNTS = {"numeric_symbol": 24, "punctuation": 20, "length": 0, "unique": 42}
BASE_SEGMENTS = 3344
ENABLED_SEGMENTS = 3344
EXPECTED_STARTS = [151466, 151557, 253849, 253919, 254102]
EXPECTED_MARKERS = ["G", "H", "J", "K", "M"]
EXPECTED_UNTOUCHED = 3339


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


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
    buckets = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
        seq = int(row["sequence_number"])
        verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        if (verdict.get("numeric_symbol") or {}).get("passed") is not True:
            buckets["numeric_symbol"].append(seq); union.add(seq)
        if verdict.get("punctuation_passed") is not True:
            buckets["punctuation"].append(seq); union.add(seq)
        if verdict.get("length_passed") is not True:
            buckets["length"].append(seq); union.add(seq)
    return {**buckets, "counts": {"numeric_symbol": len(buckets["numeric_symbol"]), "punctuation": len(buckets["punctuation"]), "length": len(buckets["length"]), "unique": len(union)}}


def _row_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (int(row["source_start"]), int(row["source_end"]), str(row.get("source_text") or ""), str(row.get("target_text") or ""))


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_TC_BIG_FOOTNOTE_PRODUCT_ROOT", "work/tc-big-footnote-product-rescue")).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("TC-big footnote audit requires exact persisted run-10 database")
    asset = load_tc_big_asset()

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-10 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-10 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run-10 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(f"run-10 baseline drift: {base_inventory['counts']!r}, rows={len(base_rows)}")

    parameters = dict(base_parameters)
    parameters.update({
        "enable_tc_big_footnote_reference_rescue": True,
        "tc_big_footnote_reference_rescue_contract": TC_BIG_FOOTNOTE_RESCUE_CONTRACT,
        "tc_big_footnote_reference_selector_contract": TC_BIG_FOOTNOTE_SELECTOR_CONTRACT,
        "tc_big_footnote_reference_trigger_contract": TC_BIG_FOOTNOTE_TRIGGER_CONTRACT,
        "tc_big_footnote_reference_rescue_phase": TC_BIG_FOOTNOTE_SELECTED_PHASE,
    })
    enabled = run_footnote_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    run_id = int(enabled["translation_run_id"])
    if run_id == BASE_RUN_ID or int(enabled.get("base_translation_run_id") or 0) != BASE_RUN_ID:
        raise RuntimeError("footnote wrapper did not compose over exact run 10")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("footnote wrapper base output SHA drift")
    if list(enabled.get("tc_big_footnote_reference_rescue_attempted_source_starts") or []) != EXPECTED_STARTS:
        raise RuntimeError("footnote attempt cohort drift")
    if list(enabled.get("tc_big_footnote_reference_rescue_accepted_source_starts") or []) != EXPECTED_STARTS:
        raise RuntimeError("footnote accepted cohort drift")
    if int(enabled.get("tc_big_footnote_reference_rescue_accepted_count") or -1) != 5 or int(enabled.get("tc_big_footnote_reference_rescue_rejected_count") or -1) != 0:
        raise RuntimeError("footnote acceptance-count drift")
    if int(enabled.get("base_segment_count") or 0) != BASE_SEGMENTS or int(enabled.get("segment_count") or 0) != ENABLED_SEGMENTS:
        raise RuntimeError("footnote segment-count drift")

    runtime = dict(enabled.get("tc_big_footnote_reference_rescue_runtime") or {})
    if runtime.get("available") is not True or runtime.get("asset_manifest_sha256") != asset.manifest_sha256 or runtime.get("asset_payload_tree_sha256") != asset.payload_tree_sha256:
        raise RuntimeError("footnote persisted TC-big asset provenance drift")
    if runtime.get("torch_required_for_inference") is not False or runtime.get("offline") is not True or runtime.get("compute_type") != "float32":
        raise RuntimeError("footnote persisted runtime contract drift")

    with connect(database, readonly=True) as connection:
        persisted = get_run(connection, run_id)
        rows = get_run_items(connection, run_id, kind="translation_segment")
    _coverage(rows, content, label="footnote enabled")
    inventory = _inventory(rows)
    if inventory["counts"] != ENABLED_COUNTS or len(rows) != ENABLED_SEGMENTS:
        raise RuntimeError(f"footnote gate drift: {inventory['counts']!r}, rows={len(rows)}")

    base_by_start = {int(row["source_start"]): row for row in base_rows}
    untouched = 0
    applied: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("tc_big_footnote_reference_rescue") or {})
        if rescue.get("contract") != TC_BIG_FOOTNOTE_RESCUE_CONTRACT or rescue.get("selector_contract") != TC_BIG_FOOTNOTE_SELECTOR_CONTRACT:
            raise RuntimeError("footnote row provenance contract drift")
        for flag in ("source_bytes_rewritten", "target_rewriting", "placeholders", "post_translation_literal_injection", "corpus_specific_target_patches"):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe footnote row flag: {flag}")
        base = base_by_start.get(int(row["source_start"]))
        if base is None:
            raise RuntimeError("footnote output has unknown source start")
        if rescue.get("applied") is not True:
            if _row_identity(row) != _row_identity(base):
                raise RuntimeError("untouched footnote row differs from exact run 10")
            untouched += 1
            continue
        marker = str(rescue.get("source_marker") or "")
        hypotheses = list(payload.get("hypotheses") or [])
        rank = int(payload["selected_rank"])
        target = str(row.get("target_text") or "")
        if rank < 0 or rank >= len(hypotheses) or str(hypotheses[rank].get("text") or "") != target:
            raise RuntimeError("footnote target is not exact raw selected hypothesis")
        selection = dict(rescue.get("selection") or {})
        if selection.get("accepted") is not True or selection.get("strictly_eligible") is not True or selection.get("exact_ascii_marker_preserved") is not True or selection.get("target_reference_lead_shape") is not True or selection.get("source_alpha_ratio_passed") is not True:
            raise RuntimeError("footnote selected hypothesis fails persisted selector evidence")
        if (selection.get("emphasis_markup") or {}).get("passed") is not True:
            raise RuntimeError("footnote selected hypothesis loses emphasis")
        applied.append({
            "source_start": int(row["source_start"]),
            "source_marker": marker,
            "source_text": str(row.get("source_text") or ""),
            "base_target": str(base.get("target_text") or ""),
            "selected_rank": rank,
            "selected_target": target,
            "selection": selection,
        })

    applied.sort(key=lambda item: item["source_start"])
    if [item["source_start"] for item in applied] != EXPECTED_STARTS or [item["source_marker"] for item in applied] != EXPECTED_MARKERS:
        raise RuntimeError("footnote persisted marker cohort drift")
    if untouched != EXPECTED_UNTOUCHED:
        raise RuntimeError(f"footnote untouched-row count drift: {untouched}")

    with sqlite3.connect(database) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign:
        raise RuntimeError(f"SQLite integrity drift: {integrity!r}, {foreign[:10]!r}")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off Product audit for TC-big Gutenberg footnote-reference lead rescue",
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
        "attempted_source_starts": list(enabled.get("tc_big_footnote_reference_rescue_attempted_source_starts") or []),
        "accepted_source_starts": list(enabled.get("tc_big_footnote_reference_rescue_accepted_source_starts") or []),
        "selected_ranks": list(enabled.get("tc_big_footnote_reference_rescue_selected_ranks") or []),
        "selected_targets": list(enabled.get("tc_big_footnote_reference_rescue_selected_targets") or []),
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
    dest = root / "full-opticks-tc-big-footnote-reference-product-rescue-optin.json"
    dest.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
