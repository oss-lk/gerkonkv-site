from __future__ import annotations

"""Classify every raw Stage10-v2 merge against the exact run-16 Stage12 geometry.

This is a planning-only audit: it reuses immutable run-16 Stage8 evidence, creates
Stage10 v2 in a copy of the persisted database, and runs the maintained Stage12
planner without invoking either MT backend.  It answers whether each raw spaCy
boundary was still an MT/source-unit boundary after Stage12 source-structure
planning (ASCII tables, structural labels, section identifiers and protected
spans), and exactly how V2 changes that geometry.
"""

from bisect import bisect_right
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from rocketdict.context_sentence_boundaries import (
    STAGE10_BOUNDARY_POLICY,
    STAGE10_CONTEXT_IMPLEMENTATION_V1,
    STAGE10_CONTEXT_IMPLEMENTATION_V2,
)
from rocketdict.database import (
    connect,
    get_document,
    get_document_segments,
    get_run,
    get_run_items,
)
from rocketdict.stages import run_stage10
from rocketdict.table_structure import detect_ascii_table_blocks
from rocketdict.translation_stage import segment_translation_units

SCHEMA = "rocketdict-full-opticks-stage10-v2-planner-impact/1"
BASE_DATABASE_SHA256 = "573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11"
BASE_RUN_ID = 16
BASE_OUTPUT_SHA256 = "767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_RAW_MERGE_COUNT = 38
WHENCE_BOUNDARY_OFFSET = 522572


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


def _ordered(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _unit_geometry(row: dict[str, Any]) -> tuple[int, int, str]:
    return int(row["start"]), int(row["end"]), str(row["text"])


def _translation_geometry(row: dict[str, Any]) -> tuple[int, int, str]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
    )


def _coverage_units(units: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for index, row in enumerate(units):
        start, end, text = _unit_geometry(row)
        if start != cursor or end <= start or content[start:end] != text:
            raise RuntimeError(
                f"{label} coverage drift at {index}: cursor={cursor}, start={start}, end={end}"
            )
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage: {cursor} != {len(content)}")


def _coverage_translation_rows(
    rows: list[dict[str, Any]], content: str, *, label: str
) -> None:
    cursor = 0
    for index, row in enumerate(_ordered(rows)):
        start, end, text = _translation_geometry(row)
        if start != cursor or end <= start or content[start:end] != text:
            raise RuntimeError(
                f"{label} coverage drift at {index}: cursor={cursor}, start={start}, end={end}"
            )
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage: {cursor} != {len(content)}")


def _boundary_set_for_units(units: list[dict[str, Any]]) -> set[int]:
    return {int(row["start"]) for row in units[1:]}


def _boundary_set_for_translation(rows: list[dict[str, Any]]) -> set[int]:
    ordered = _ordered(rows)
    return {int(row["source_start"]) for row in ordered[1:]}


def _neighbor_units(units: list[dict[str, Any]], offset: int) -> dict[str, Any]:
    left: dict[str, Any] | None = None
    right: dict[str, Any] | None = None
    containing: dict[str, Any] | None = None
    for row in units:
        start = int(row["start"])
        end = int(row["end"])
        if end == offset:
            left = row
        if start == offset:
            right = row
        if start < offset < end:
            containing = row
            break
    def view(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        metadata = dict(row.get("metadata") or {})
        return {
            "start": int(row["start"]),
            "end": int(row["end"]),
            "metadata": metadata,
            "source": metadata.get("source"),
            "text_excerpt": str(row["text"])[-180:] if int(row["end"]) <= offset else str(row["text"])[:240],
        }
    return {"left": view(left), "right": view(right), "containing": view(containing)}


def _neighbor_translation_rows(
    rows: list[dict[str, Any]], offset: int
) -> dict[str, Any]:
    left: dict[str, Any] | None = None
    right: dict[str, Any] | None = None
    containing: dict[str, Any] | None = None
    for row in _ordered(rows):
        start = int(row["source_start"])
        end = int(row["source_end"])
        if end == offset:
            left = row
        if start == offset:
            right = row
        if start < offset < end:
            containing = row
            break
    def view(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        payload = dict(row.get("payload") or {})
        planner = dict(payload.get("planner") or {})
        return {
            "sequence_number": int(row["sequence_number"]),
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "planner_source": planner.get("source"),
            "planner": planner,
        }
    return {"left": view(left), "right": view(right), "containing": view(containing)}


def _line_starts(content: str) -> list[int]:
    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(content) if char == "\n")
    return starts


def _line_context(content: str, starts: list[int], offset: int) -> dict[str, Any]:
    line_index = bisect_right(starts, offset) - 1
    line_start = starts[line_index]
    next_start = starts[line_index + 1] if line_index + 1 < len(starts) else len(content)
    previous_start = starts[line_index - 1] if line_index > 0 else line_start
    following_end = (
        starts[line_index + 2]
        if line_index + 2 < len(starts)
        else len(content)
    )
    return {
        "line_index_zero_based": line_index,
        "line_number_one_based": line_index + 1,
        "line_start": line_start,
        "line_end": next_start,
        "line_text": content[line_start:next_start],
        "previous_line_text": content[previous_start:line_start] if line_index > 0 else "",
        "next_line_text": content[next_start:following_end] if next_start < len(content) else "",
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_STAGE10_V2_PLANNER_IMPACT_ROOT",
            "work/full-opticks-stage10-v2-planner-impact",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("Stage10 planner-impact audit requires exact persisted run-16 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        old_context_run_id = int(base_output["context_run_id"])
        old_context_run = get_run(connection, old_context_run_id)
        old_context_rows = get_run_items(connection, old_context_run_id, kind="context_sentence")
        old_context_output = dict(old_context_run.get("output") or {})
        nlp_run_id = int(old_context_output["nlp_run_id"])
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document_version_id = int(base_output["document_version_id"])
        document = get_document(connection, document_version_id)
        document_segments = get_document_segments(connection, document_version_id)

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-16 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-16 source identity drift")
    if str(old_context_run.get("implementation") or "") != STAGE10_CONTEXT_IMPLEMENTATION_V1:
        raise RuntimeError("run-16 Stage10 context is not the expected V1 implementation")

    content = str(document["content_text"])
    selected_format = str(document["selected_format"])
    if selected_format != "txt":
        raise RuntimeError(f"full Opticks selected-format drift: {selected_format!r}")
    preferred = int(base_parameters.get("plan_preferred_unit_tokens") or 64)
    _coverage_translation_rows(base_rows, content, label="run-16 Stage12")

    v1_units = segment_translation_units(
        content,
        document_segments,
        old_context_rows,
        nlp_tokens,
        selected_format=selected_format,
        preferred_tokens=preferred,
    )
    _coverage_units(v1_units, content, label="Stage12 planner over Stage10 v1")

    v2_output = run_stage10(
        database,
        nlp_run_id=nlp_run_id,
        parameters=dict(old_context_run.get("parameters") or {}),
        implementation=STAGE10_CONTEXT_IMPLEMENTATION_V2,
    )
    v2_context_run_id = int(v2_output["context_run_id"])
    with connect(database, readonly=True) as connection:
        v2_context_run = get_run(connection, v2_context_run_id)
        v2_context_rows = get_run_items(connection, v2_context_run_id, kind="context_sentence")
    stored_v2 = dict(v2_context_run.get("output") or {})
    if stored_v2.get("boundary_policy") != STAGE10_BOUNDARY_POLICY:
        raise RuntimeError("Stage10 v2 boundary policy drift")
    if int(stored_v2.get("coalesced_boundary_count") or -1) != EXPECTED_RAW_MERGE_COUNT:
        raise RuntimeError(
            f"Stage10 v2 raw merge census drift: {stored_v2.get('coalesced_boundary_count')!r}"
        )

    v2_units = segment_translation_units(
        content,
        document_segments,
        v2_context_rows,
        nlp_tokens,
        selected_format=selected_format,
        preferred_tokens=preferred,
    )
    _coverage_units(v2_units, content, label="Stage12 planner over Stage10 v2")

    decisions: list[dict[str, Any]] = []
    for context_row in _ordered(v2_context_rows):
        payload = dict(context_row.get("payload") or {})
        for raw in list(payload.get("coalesced_boundaries") or []):
            row = dict(raw)
            row["stage10_v2_context_sequence_number"] = int(context_row["sequence_number"])
            row["stage10_v2_context_source_start"] = int(context_row["source_start"])
            row["stage10_v2_context_source_end"] = int(context_row["source_end"])
            decisions.append(row)
    decisions.sort(key=lambda row: int(row["source_offset"]))
    if len(decisions) != EXPECTED_RAW_MERGE_COUNT:
        raise RuntimeError(f"persisted Stage10 v2 decision count drift: {len(decisions)}")

    table_blocks = detect_ascii_table_blocks(content)
    v1_boundaries = _boundary_set_for_units(v1_units)
    v2_boundaries = _boundary_set_for_units(v2_units)
    run16_boundaries = _boundary_set_for_translation(base_rows)
    line_starts = _line_starts(content)

    classified: list[dict[str, Any]] = []
    for decision in decisions:
        offset = int(decision["source_offset"])
        tables = [
            {
                "start": int(block.start),
                "end": int(block.end),
                "first_line": int(block.first_line),
                "last_line": int(block.last_line),
                "pipe_line_count": int(block.pipe_line_count),
                "separator_line_count": int(block.separator_line_count),
            }
            for block in table_blocks
            if int(block.start) < offset < int(block.end)
        ]
        gap = str(decision.get("gap") or "")
        item = {
            **decision,
            "source_offset": offset,
            "gap_repr": repr(gap),
            "gap_newline_count": gap.count("\n"),
            "gap_carriage_return_count": gap.count("\r"),
            "inside_detected_ascii_table": bool(tables),
            "detected_ascii_tables": tables,
            "v1_stage12_plan_boundary": offset in v1_boundaries,
            "v2_stage12_plan_boundary": offset in v2_boundaries,
            "run16_final_translation_boundary": offset in run16_boundaries,
            "v1_plan_neighbors": _neighbor_units(v1_units, offset),
            "v2_plan_neighbors": _neighbor_units(v2_units, offset),
            "run16_translation_neighbors": _neighbor_translation_rows(base_rows, offset),
            "physical_line": _line_context(content, line_starts, offset),
        }
        item["stage12_plan_boundary_removed_by_v2"] = bool(
            item["v1_stage12_plan_boundary"] and not item["v2_stage12_plan_boundary"]
        )
        classified.append(item)

    v1_geometry = {_unit_geometry(row) for row in v1_units}
    v2_geometry = {_unit_geometry(row) for row in v2_units}
    v1_only = sorted(v1_geometry - v2_geometry)
    v2_only = sorted(v2_geometry - v1_geometry)

    summary = {
        "raw_stage10_merge_count": len(classified),
        "inside_ascii_table_count": sum(row["inside_detected_ascii_table"] for row in classified),
        "v1_stage12_plan_boundary_count": sum(row["v1_stage12_plan_boundary"] for row in classified),
        "v2_stage12_plan_boundary_count": sum(row["v2_stage12_plan_boundary"] for row in classified),
        "run16_final_translation_boundary_count": sum(row["run16_final_translation_boundary"] for row in classified),
        "stage12_plan_boundary_removed_by_v2_count": sum(row["stage12_plan_boundary_removed_by_v2"] for row in classified),
        "v1_plan_unit_count": len(v1_units),
        "v2_plan_unit_count": len(v2_units),
        "v1_only_plan_geometry_count": len(v1_only),
        "v2_only_plan_geometry_count": len(v2_only),
    }

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "planning-only impact audit of all Stage10-v2 raw merges over exact run-16 evidence",
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "selected_format": selected_format,
        "preferred_translation_unit_tokens": preferred,
        "base_context_run_id": old_context_run_id,
        "base_context_output_sha256": str(old_context_run.get("output_sha256") or ""),
        "stage10_v2_context_run_id": v2_context_run_id,
        "stage10_v2_context_output_sha256": str(v2_context_run.get("output_sha256") or ""),
        "stage10_v2_boundary_policy": STAGE10_BOUNDARY_POLICY,
        "stage10_v2_raw_merge_count": int(stored_v2["coalesced_boundary_count"]),
        "summary": summary,
        "raw_merge_offsets": [int(row["source_offset"]) for row in classified],
        "ascii_table_offsets": [int(row["source_offset"]) for row in classified if row["inside_detected_ascii_table"]],
        "v1_stage12_plan_boundary_offsets": [int(row["source_offset"]) for row in classified if row["v1_stage12_plan_boundary"]],
        "run16_final_translation_boundary_offsets": [int(row["source_offset"]) for row in classified if row["run16_final_translation_boundary"]],
        "stage12_plan_boundaries_removed_by_v2": [int(row["source_offset"]) for row in classified if row["stage12_plan_boundary_removed_by_v2"]],
        "known_whence_boundary": next(row for row in classified if int(row["source_offset"]) == WHENCE_BOUNDARY_OFFSET),
        "classifications": classified,
        "v1_only_plan_geometry": [
            {"start": start, "end": end, "text": text} for start, end, text in v1_only
        ],
        "v2_only_plan_geometry": [
            {"start": start, "end": end, "text": text} for start, end, text in v2_only
        ],
        "database_mutated_only_by_new_stage10_v2_evidence": True,
        "mt_backend_invoked": False,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "evaluator_weakened": False,
    }
    evidence["persisted_database_sha256"] = _sha(database)
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-stage10-v2-planner-impact.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "summary": summary,
                "raw_merge_offsets": evidence["raw_merge_offsets"],
                "ascii_table_offsets": evidence["ascii_table_offsets"],
                "v1_stage12_plan_boundary_offsets": evidence["v1_stage12_plan_boundary_offsets"],
                "run16_final_translation_boundary_offsets": evidence["run16_final_translation_boundary_offsets"],
                "stage12_plan_boundaries_removed_by_v2": evidence["stage12_plan_boundaries_removed_by_v2"],
                "known_whence_boundary": {
                    key: evidence["known_whence_boundary"][key]
                    for key in (
                        "source_offset",
                        "gap_repr",
                        "inside_detected_ascii_table",
                        "v1_stage12_plan_boundary",
                        "v2_stage12_plan_boundary",
                        "run16_final_translation_boundary",
                        "stage12_plan_boundary_removed_by_v2",
                    )
                },
                "persisted_database_sha256": evidence["persisted_database_sha256"],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
