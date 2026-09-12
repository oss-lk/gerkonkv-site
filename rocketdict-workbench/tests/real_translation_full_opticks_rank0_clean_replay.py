from __future__ import annotations

"""Rebuild the post-run8 full-Opticks rescue lineage under current rank0-only contracts.

The exact historical run23 SQLite is copied byte-for-byte by CI.  Runs 1..23 are
immutable historical evidence.  This replay intentionally starts from the cached
run8 boundary (citation + length + numeric-hard rescues), then re-executes every
later enabled wrapper with current contracts.  Any lower-ranked beam may remain
in diagnostic evidence, but no rescue may persist it.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_emphasized_modifier_boundary_rescue_stage import (
    run_stage12 as run_final_stage12,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-rank0-clean-lineage-replay/1"
HISTORICAL_DATABASE_SHA256 = "75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
HISTORICAL_FINAL_RUN_ID = 23
HISTORICAL_FINAL_OUTPUT_SHA256 = "976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493"
CLEAN_START_RUN_ID = 8
CLEAN_START_OUTPUT_SHA256 = "d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346"
EXPECTED_NEW_RUN_COUNT = 15
HISTORICAL_COUNTS = {"numeric_symbol": 17, "punctuation": 14, "length": 0, "unique": 30}
HISTORICAL_SEGMENT_COUNT = 3337

# These are the three historical rescue regions proven to have persisted rank>0.
AUDIT_SPANS = {
    "illustration_fig21": [72401, 72443],
    "illustration_fig24": [90105, 90147],
    "short_dms": [110881, 110918],
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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
    return sorted(rows, key=lambda row: int(row["source_start"]))


def _coverage(rows: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for sequence, row in enumerate(_ordered(rows)):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError(f"{label}: sequence drift at {sequence}")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"{label}: source coverage drift at {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label}: incomplete source coverage {cursor} != {len(content)}")


def _hard_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    unique = 0
    for row in _ordered(rows):
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        failed = False
        if dict(verdict.get("numeric_symbol") or {}).get("passed") is not True:
            counts["numeric_symbol"] += 1
            failed = True
        if verdict.get("punctuation_passed") is not True:
            counts["punctuation"] += 1
            failed = True
        if verdict.get("length_passed") is not True:
            counts["length"] += 1
            failed = True
        if failed:
            unique += 1
    return {**counts, "unique": unique}


def _span_target(rows: list[dict[str, Any]], start: int, end: int) -> tuple[str, list[dict[str, Any]]]:
    members = [
        row
        for row in _ordered(rows)
        if start <= int(row["source_start"]) and int(row["source_end"]) <= end
    ]
    if not members:
        raise RuntimeError(f"no rows found for audit span {start}:{end}")
    if int(members[0]["source_start"]) != start or int(members[-1]["source_end"]) != end:
        raise RuntimeError(f"audit span is not exactly reconstructible: {start}:{end}")
    source_cursor = start
    for row in members:
        if int(row["source_start"]) != source_cursor:
            raise RuntimeError(f"audit span has a source gap: {start}:{end}")
        source_cursor = int(row["source_end"])
    if source_cursor != end:
        raise RuntimeError(f"audit span ends early: {start}:{end}")
    return (
        "".join(str(row.get("target_text") or "") for row in members),
        members,
    )


def _sanitize_historical_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Keep source/model/cap settings but let every wrapper bind its current contract."""

    clean = dict(parameters)
    for key in list(clean):
        if key.endswith("_phase"):
            clean.pop(key)
            continue
        if any(
            marker in key
            for marker in (
                "_rescue_contract",
                "_selector_contract",
                "_trigger_contract",
                "_source_contract",
            )
        ):
            clean.pop(key)
    return clean


def _selected_rank_audit(output: dict[str, Any]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for key, value in sorted(output.items()):
        if not key.endswith("_selected_ranks"):
            continue
        if not isinstance(value, list):
            raise RuntimeError(f"selected-rank output is not a list: {key}")
        ranks = [int(rank) for rank in value]
        if any(rank != 0 for rank in ranks):
            raise RuntimeError(f"rank0-clean replay selected a later beam: {key}={ranks!r}")
        result[key] = ranks
    return result


def _new_lineage(database: Path, *, first_new_run_id: int, final_run_id: int) -> list[dict[str, Any]]:
    lineage: list[dict[str, Any]] = []
    expected_base = CLEAN_START_RUN_ID
    with connect(database, readonly=True) as connection:
        for run_id in range(first_new_run_id, final_run_id + 1):
            run = get_run(connection, run_id)
            output = dict(run.get("output") or {})
            base_run_id = int(output.get("base_translation_run_id") or -1)
            if base_run_id != expected_base:
                raise RuntimeError(
                    f"rank0-clean lineage break at run {run_id}: base={base_run_id}, expected={expected_base}"
                )
            rank_audit = _selected_rank_audit(output)
            unsafe_true = {
                key: output.get(key)
                for key in (
                    "source_bytes_rewritten",
                    "target_rewriting",
                    "placeholders",
                    "post_translation_literal_injection",
                    "corpus_specific_target_patches",
                    "evaluator_weakened",
                    "n_best_cherry_picking",
                    "automatic_n_best_cherry_picking",
                )
                if key in output and output.get(key) is not False
            }
            if unsafe_true:
                raise RuntimeError(f"unsafe replay flags at run {run_id}: {unsafe_true!r}")
            lineage.append(
                {
                    "run_id": run_id,
                    "base_translation_run_id": base_run_id,
                    "output_sha256": str(run.get("output_sha256") or ""),
                    "selected_rank_outputs": rank_audit,
                    "parameters": dict(run.get("parameters") or {}),
                }
            )
            expected_base = run_id
    return lineage


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RANK0_CLEAN_REPLAY_ROOT",
            "work/full-opticks-rank0-clean-replay",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != HISTORICAL_DATABASE_SHA256:
        raise RuntimeError("rank0-clean replay requires exact historical run23 SQLite")

    with connect(database, readonly=True) as connection:
        historical_run = get_run(connection, HISTORICAL_FINAL_RUN_ID)
        historical_output = dict(historical_run.get("output") or {})
        historical_rows = get_run_items(
            connection, HISTORICAL_FINAL_RUN_ID, kind="translation_segment"
        )
        clean_start_run = get_run(connection, CLEAN_START_RUN_ID)
        clean_start_output = dict(clean_start_run.get("output") or {})
        clean_start_rows = get_run_items(
            connection, CLEAN_START_RUN_ID, kind="translation_segment"
        )
        document = get_document(
            connection, int(historical_output["document_version_id"])
        )

    if str(historical_run.get("output_sha256") or "") != HISTORICAL_FINAL_OUTPUT_SHA256:
        raise RuntimeError("historical run23 output identity drift")
    if str(clean_start_run.get("output_sha256") or "") != CLEAN_START_OUTPUT_SHA256:
        raise RuntimeError("clean-start run8 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("immutable source identity drift")
    content = str(document["content_text"])
    _coverage(historical_rows, content, label="historical run23")
    _coverage(clean_start_rows, content, label="clean-start run8")
    if _hard_counts(historical_rows) != HISTORICAL_COUNTS:
        raise RuntimeError("historical run23 hard-gate census drift")
    if len(historical_rows) != HISTORICAL_SEGMENT_COUNT:
        raise RuntimeError("historical run23 segment-count drift")

    historical_parameters = dict(historical_run.get("parameters") or {})
    parameters = _sanitize_historical_parameters(historical_parameters)
    if parameters.get("enable_illustration_label_rescue") is not True:
        raise RuntimeError("historical replay parameters lost illustration rescue enable")
    if parameters.get("enable_emphasized_modifier_boundary_rescue") is not True:
        raise RuntimeError("historical replay parameters lost final wrapper enable")

    max_run_before = HISTORICAL_FINAL_RUN_ID
    enabled = run_final_stage12(
        database,
        context_run_id=int(historical_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id <= max_run_before:
        raise RuntimeError("rank0-clean replay unexpectedly resolved to historical cache")
    new_run_count = final_run_id - max_run_before
    if new_run_count != EXPECTED_NEW_RUN_COUNT:
        raise RuntimeError(
            f"rank0-clean replay created {new_run_count} runs, expected {EXPECTED_NEW_RUN_COUNT}"
        )
    first_new_run_id = max_run_before + 1
    lineage = _new_lineage(
        database,
        first_new_run_id=first_new_run_id,
        final_run_id=final_run_id,
    )
    if lineage[0]["base_translation_run_id"] != CLEAN_START_RUN_ID:
        raise RuntimeError("first recomputed wrapper did not reuse exact clean-start run8")
    first_params = lineage[0]["parameters"]
    if first_params.get("illustration_label_rescue_contract") != "rocketdict-stage12-illustration-label-rescue/2":
        raise RuntimeError("first recomputed wrapper is not illustration rescue /2")

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = get_run_items(connection, final_run_id, kind="translation_segment")
    _coverage(final_rows, content, label="rank0-clean final")
    final_counts = _hard_counts(final_rows)
    final_selected_ranks = _selected_rank_audit(dict(final_run.get("output") or {}))

    span_audit: dict[str, Any] = {}
    for name, (start, end) in AUDIT_SPANS.items():
        old_target, old_members = _span_target(historical_rows, start, end)
        new_target, new_members = _span_target(final_rows, start, end)
        source = content[start:end]
        span_audit[name] = {
            "source_span": [start, end],
            "source_text": source,
            "historical_target_text": old_target,
            "rank0_clean_target_text": new_target,
            "target_changed": old_target != new_target,
            "historical_member_count": len(old_members),
            "rank0_clean_member_count": len(new_members),
            "historical_verdict": evaluate_rescue_pair(source, old_target),
            "rank0_clean_verdict": evaluate_rescue_pair(source, new_target),
        }

    final_text = "".join(str(row.get("target_text") or "") for row in _ordered(final_rows))
    final_text_path = root / "full-opticks-rank0-clean-replay.txt"
    final_text_path.write_text(final_text, encoding="utf-8")

    with sqlite3.connect(database) as raw:
        integrity = str(raw.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_key_violations = raw.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_key_violations:
        raise RuntimeError("rank0-clean replay database integrity failure")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted full-Opticks post-run8 replay under current rank0-only rescue contracts",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "historical_database_sha256": HISTORICAL_DATABASE_SHA256,
        "historical_translation_run_id": HISTORICAL_FINAL_RUN_ID,
        "historical_translation_output_sha256": HISTORICAL_FINAL_OUTPUT_SHA256,
        "historical_hard_gate_counts": HISTORICAL_COUNTS,
        "historical_segment_count": HISTORICAL_SEGMENT_COUNT,
        "clean_start_run_id": CLEAN_START_RUN_ID,
        "clean_start_output_sha256": CLEAN_START_OUTPUT_SHA256,
        "clean_start_reused_exactly": True,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "first_new_run_id": first_new_run_id,
        "final_translation_run_id": final_run_id,
        "final_translation_output_sha256": str(final_run.get("output_sha256") or ""),
        "new_run_count": new_run_count,
        "new_lineage": lineage,
        "final_selected_rank_outputs": final_selected_ranks,
        "final_hard_gate_counts": final_counts,
        "final_segment_count": len(final_rows),
        "historical_rank_gt0_span_audit": span_audit,
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "foreign_key_violation_count": len(foreign_key_violations),
        "final_database_sha256": _sha(database),
        "final_text_sha256": _sha(final_text_path),
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "full-opticks-rank0-clean-replay.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "clean_start_run_id": CLEAN_START_RUN_ID,
        "first_new_run_id": first_new_run_id,
        "final_translation_run_id": final_run_id,
        "new_run_count": new_run_count,
        "historical_hard_gate_counts": HISTORICAL_COUNTS,
        "final_hard_gate_counts": final_counts,
        "final_segment_count": len(final_rows),
        "selected_rank_outputs": final_selected_ranks,
        "changed_historical_rank_gt0_spans": [
            name for name, item in span_audit.items() if item["target_changed"]
        ],
        "final_database_sha256": evidence["final_database_sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
