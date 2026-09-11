from __future__ import annotations

"""Persist and independently audit the TC-big footnote-reference rescue over run 10."""

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
            "ROCKETDICT_TC_BIG_FOOTNOTE_PRODUCT_ROOT",
            "work/tc-big-footnote-product-rescue",
        )
    ).resolve()
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
        raise RuntimeError(
            f"run-10 baseline drift: {base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_tc_big_footnote_reference_rescue": True,
            "tc_big_footnote_reference_rescue_contract": TC_BIG_FOOTNOTE_RESCUE_CONTRACT,
            "tc_big_footnote_reference_selector_contract": TC_BIG_FOOTNOTE_SELECTOR_CONTRACT,
            "tc_big_footnote_reference_trigger_contract": TC_BIG_FOOTNOTE_TRIGGER_CONTRACT,
            "tc_big_footnote_reference_rescue_phase": TC_BIG_FOOTNOTE_SELECTED_PHASE,
        }
    )
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

    accepted_count = enabled.get("tc_big_footnote_reference_rescue_accepted_count")
    rejected_count = enabled.get("tc_big_footnote_reference_rescue_rejected_count")
    if accepted_count != 5 or rejected_count != 0:
        raise RuntimeError(
            f"footnote acceptance-count drift: accepted={accepted_count!r}, rejected={rejected_count!r}"
        )
    if int(enabled.get("base_segment_count") or 0) != BASE_SEGMENTS:
        raise RuntimeError("footnote base segment-count drift")
    if int(enabled.get("segment_count") or 0) != ENABLED_SEGMENTS:
        raise RuntimeError("footnote enabled segment-count drift")

    runtime = dict(enabled.get("tc_big_footnote_reference_rescue_runtime") or {})
    if runtime.get("available") is not True:
        raise RuntimeError(f"footnote persisted TC-big runtime unavailable: {runtime!r}")
    if runtime.get("asset_manifest_sha256") != asset.manifest_sha256:
        raise RuntimeError("footnote persisted manifest identity drift")
    if runtime.get("asset_payload_tree_sha256") != asset.payload_tree_sha256:
        raise RuntimeError("footnote persisted payload-tree identity drift")
    if int(runtime.get("asset_payload_file_count") or 0) != asset.payload_file_count:
        raise RuntimeError("footnote persisted payload file-count drift")
    if int(runtime.get("asset_payload_bytes") or 0) != asset.payload_bytes:
        raise RuntimeError("footnote persisted payload byte-count drift")
    if runtime.get("torch_required_for_inference") is not False:
        raise RuntimeError("footnote persisted runtime unexpectedly requires Torch")
    if runtime.get("offline") is not True or runtime.get("compute_type") != "float32":
        raise RuntimeError("footnote persisted runtime offline/compute drift")

    with connect(database, readonly=True) as connection:
        persisted = get_run(connection, run_id)
        rows = get_run_items(connection, run_id, kind="translation_segment")
    _coverage(rows, content, label="footnote enabled")
    inventory = _inventory(rows)
    if inventory["counts"] != ENABLED_COUNTS or len(rows) != ENABLED_SEGMENTS:
        raise RuntimeError(
            f"footnote gate drift: {inventory['counts']!r}, rows={len(rows)}"
        )

    base_by_start = {int(row["source_start"]): row for row in base_rows}
    untouched = 0
    applied: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("tc_big_footnote_reference_rescue") or {})
        if rescue.get("contract") != TC_BIG_FOOTNOTE_RESCUE_CONTRACT:
            raise RuntimeError("footnote row rescue contract drift")
        if rescue.get("selector_contract") != TC_BIG_FOOTNOTE_SELECTOR_CONTRACT:
            raise RuntimeError("footnote row selector contract drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
            "corpus_specific_target_patches",
        ):
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
        selected_rank = int(payload["selected_rank"])
        target = str(row.get("target_text") or "")
        hypotheses = list(payload.get("hypotheses") or [])
        selected_hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if int(hypothesis.get("rank", -1)) == selected_rank
        ]
        if len(selected_hypotheses) != 1:
            raise RuntimeError("footnote selected rank is not unique in raw hypotheses")
        if str(selected_hypotheses[0].get("text") or "") != target:
            raise RuntimeError("footnote target is not the exact raw selected hypothesis")

        selection = dict(rescue.get("selection") or {})
        if selection.get("accepted") is not True:
            raise RuntimeError("footnote persisted selector did not accept selected hypothesis")
        if selection.get("strictly_eligible") is not True:
            raise RuntimeError("footnote selected hypothesis is not strict-clean")
        if selection.get("exact_ascii_marker_preserved") is not True:
            raise RuntimeError("footnote selected hypothesis loses exact ASCII marker")
        if selection.get("target_reference_lead_shape") is not True:
            raise RuntimeError("footnote selected hypothesis loses reference-lead shape")
        if selection.get("source_alpha_ratio_passed") is not True:
            raise RuntimeError("footnote selected hypothesis violates source-relative alpha bound")
        if (selection.get("emphasis_markup") or {}).get("passed") is not True:
            raise RuntimeError("footnote selected hypothesis loses Gutenberg emphasis")

        applied.append(
            {
                "source_start": int(row["source_start"]),
                "source_marker": marker,
                "source_text": str(row.get("source_text") or ""),
                "base_target": str(base.get("target_text") or ""),
                "selected_rank": selected_rank,
                "selected_target": target,
                "selection": selection,
            }
        )

    applied.sort(key=lambda item: item["source_start"])
    if [item["source_start"] for item in applied] != EXPECTED_STARTS:
        raise RuntimeError("footnote persisted source-start cohort drift")
    if [item["source_marker"] for item in applied] != EXPECTED_MARKERS:
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
        "attempt_count": accepted_count + rejected_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "attempted_source_starts": list(
            enabled.get("tc_big_footnote_reference_rescue_attempted_source_starts") or []
        ),
        "accepted_source_starts": list(
            enabled.get("tc_big_footnote_reference_rescue_accepted_source_starts") or []
        ),
        "selected_ranks": list(
            enabled.get("tc_big_footnote_reference_rescue_selected_ranks") or []
        ),
        "selected_targets": list(
            enabled.get("tc_big_footnote_reference_rescue_selected_targets") or []
        ),
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
    destination = root / "full-opticks-tc-big-footnote-reference-product-rescue-optin.json"
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
                "accepted_count": accepted_count,
                "rejected_count": rejected_count,
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
