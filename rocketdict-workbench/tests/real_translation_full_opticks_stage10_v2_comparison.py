from __future__ import annotations

"""Replay exact full-Opticks run-16 evidence through Stage10 v2.

The experiment starts from the immutable persisted run-16 SQLite database, reuses
its exact Stage8 NLP evidence and run-16 Stage12 parameters, creates a new Stage10
v2 run, and then replays the same maintained Stage12 + default-off research
rescue composition.  The old run is never mutated.  The audit is fail-closed on
source drift, boundary-census drift, hard-gate regression, or target drift for
translation rows whose source geometry is unchanged.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.context_sentence_boundaries import (
    STAGE10_BOUNDARY_POLICY,
    STAGE10_CONTEXT_IMPLEMENTATION_V1,
    STAGE10_CONTEXT_IMPLEMENTATION_V2,
)
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.stages import run_stage10
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_short_angular_dms_rescue_stage import (
    run_stage12 as run_composed_stage12,
)

SCHEMA = "rocketdict-full-opticks-stage10-v2-comparison/1"
BASE_DATABASE_SHA256 = "573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11"
BASE_RUN_ID = 16
BASE_OUTPUT_SHA256 = "767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
SOURCE_CHAR_COUNT = 586543
BASE_SEGMENTS = 3344
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 18, "length": 0, "unique": 37}
EXPECTED_COALESCED_BOUNDARIES = 38
EXPECTED_BOUNDARY_OFFSETS = (
    655,
    10277,
    18355,
    23464,
    50306,
    54796,
    63563,
    64046,
    64118,
    89748,
    92716,
    106061,
    112001,
    132089,
    137981,
    146358,
    155895,
    166588,
    168067,
    180246,
    189201,
    203830,
    220080,
    223062,
    228046,
    247799,
    266720,
    301082,
    349036,
    355851,
    412197,
    434836,
    455648,
    507039,
    522572,
    545343,
    548282,
    556573,
)
WHENCE_FIRST_START = 522555
WHENCE_BOUNDARY_OFFSET = 522572
REQUIRED_RESCUE_FLAGS = (
    "enable_tc_big_target_delimiter_rescue",
    "enable_tc_big_footnote_reference_rescue",
    "enable_tc_big_figure_reference_rescue",
    "enable_tc_big_semicolon_question_rescue",
    "enable_tc_big_equals_addition_rescue",
    "enable_tc_big_angular_minute_rescue",
    "enable_tc_big_short_angular_dms_rescue",
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
            raise RuntimeError(f"{label} sequence drift at {sequence}")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(
                f"{label} source coverage drift at {sequence}: "
                f"cursor={cursor}, start={start}, end={end}"
            )
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage: {cursor} != {len(content)}")


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures: dict[str, list[int]] = {
        "numeric_symbol": [],
        "punctuation": [],
        "length": [],
    }
    failure_source_starts: dict[str, list[int]] = {
        "numeric_symbol": [],
        "punctuation": [],
        "length": [],
    }
    union: set[int] = set()
    for row in _ordered(rows):
        sequence = int(row["sequence_number"])
        start = int(row["source_start"])
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        if (verdict.get("numeric_symbol") or {}).get("passed") is not True:
            failures["numeric_symbol"].append(sequence)
            failure_source_starts["numeric_symbol"].append(start)
            union.add(sequence)
        if verdict.get("punctuation_passed") is not True:
            failures["punctuation"].append(sequence)
            failure_source_starts["punctuation"].append(start)
            union.add(sequence)
        if verdict.get("length_passed") is not True:
            failures["length"].append(sequence)
            failure_source_starts["length"].append(start)
            union.add(sequence)
    return {
        **failures,
        "failure_source_starts": failure_source_starts,
        "counts": {
            "numeric_symbol": len(failures["numeric_symbol"]),
            "punctuation": len(failures["punctuation"]),
            "length": len(failures["length"]),
            "unique": len(union),
        },
    }


def _geometry_key(row: dict[str, Any]) -> tuple[int, int, str]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
    )


def _row_evidence(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    return {
        "sequence_number": int(row["sequence_number"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": source,
        "target_text": target,
        "hard_verdict": evaluate_rescue_pair(source, target),
    }


def _overlapping_rows(rows: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    return [
        row
        for row in _ordered(rows)
        if int(row["source_end"]) > start and int(row["source_start"]) < end
    ]


def _aggregate_target(rows: list[dict[str, Any]]) -> str:
    return " ".join(str(row.get("target_text") or "").strip() for row in rows).strip()


def _semantic_anchors(target: str) -> dict[str, bool]:
    lowered = target.casefold()
    return {
        "whence_relation": any(token in lowered for token in ("откуда", "как не", "из чего")),
        "attractive_power": any(token in lowered for token in ("притяг", "привлек")),
        "water": "вод" in lowered,
        "salt": "сол" in lowered,
        "heat": "тепл" in lowered or "жар" in lowered,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_STAGE10_V2_COMPARISON_ROOT",
            "work/full-opticks-stage10-v2-comparison",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    initial_database_sha = _sha(database) if database.is_file() else ""
    if initial_database_sha != BASE_DATABASE_SHA256:
        raise RuntimeError(
            "Stage10 v2 comparison requires exact persisted run-16 database: "
            f"{initial_database_sha!r} != {BASE_DATABASE_SHA256!r}"
        )

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
        nlp_run = get_run(connection, nlp_run_id)
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-16 output identity drift")
    if int(base_run["stage_number"]) != 12 or base_run["status"] != "completed":
        raise RuntimeError("run-16 base is not a completed Stage12 run")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-16 source identity drift")
    content = str(document["content_text"])
    if len(content) != SOURCE_CHAR_COUNT:
        raise RuntimeError(f"Opticks source length drift: {len(content)} != {SOURCE_CHAR_COUNT}")
    if int(nlp_run["stage_number"]) != 8 or nlp_run["status"] != "completed":
        raise RuntimeError("run-16 lineage does not contain a completed Stage8 run")
    if int(old_context_run["stage_number"]) != 10 or old_context_run["status"] != "completed":
        raise RuntimeError("run-16 lineage does not contain a completed Stage10 run")
    if str(old_context_run.get("implementation") or "") != STAGE10_CONTEXT_IMPLEMENTATION_V1:
        raise RuntimeError(
            "run-16 Stage10 implementation drift: "
            f"{old_context_run.get('implementation')!r}"
        )

    _coverage(old_context_rows, content, label="run-16 Stage10 v1")
    _coverage(base_rows, content, label="run-16 Stage12")
    if len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(f"run-16 segment-count drift: {len(base_rows)} != {BASE_SEGMENTS}")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS:
        raise RuntimeError(f"run-16 hard-gate drift: {base_inventory['counts']!r}")

    missing_enabled = [flag for flag in REQUIRED_RESCUE_FLAGS if base_parameters.get(flag) is not True]
    if missing_enabled:
        raise RuntimeError(f"run-16 research rescue parameter drift: {missing_enabled!r}")

    v2_output = run_stage10(
        database,
        nlp_run_id=nlp_run_id,
        parameters=dict(old_context_run.get("parameters") or {}),
        implementation=STAGE10_CONTEXT_IMPLEMENTATION_V2,
    )
    v2_context_run_id = int(v2_output["context_run_id"])
    if v2_context_run_id == old_context_run_id:
        raise RuntimeError("Stage10 v2 unexpectedly reused the V1 run")

    with connect(database, readonly=True) as connection:
        v2_context_run = get_run(connection, v2_context_run_id)
        v2_context_rows = get_run_items(connection, v2_context_run_id, kind="context_sentence")
    stored_v2_output = dict(v2_context_run.get("output") or {})
    if stored_v2_output.get("schema") != "rocketdict-product-stage10/2":
        raise RuntimeError(f"Stage10 v2 schema drift: {stored_v2_output.get('schema')!r}")
    if stored_v2_output.get("boundary_policy") != STAGE10_BOUNDARY_POLICY:
        raise RuntimeError("Stage10 v2 boundary-policy drift")
    if int(stored_v2_output.get("coalesced_boundary_count") or -1) != EXPECTED_COALESCED_BOUNDARIES:
        raise RuntimeError(
            "full-Opticks Stage10 v2 boundary census drift: "
            f"{stored_v2_output.get('coalesced_boundary_count')!r}"
        )
    if (
        int(stored_v2_output.get("spacy_sentence_count") or -1)
        - int(stored_v2_output.get("sentence_count") or -1)
        != EXPECTED_COALESCED_BOUNDARIES
    ):
        raise RuntimeError("Stage10 v2 sentence-count delta does not equal the exact full-corpus merge census")
    _coverage(v2_context_rows, content, label="Stage10 v2")

    boundary_decisions: list[dict[str, Any]] = []
    for row in _ordered(v2_context_rows):
        payload = dict(row.get("payload") or {})
        for decision in list(payload.get("coalesced_boundaries") or []):
            normalized = dict(decision)
            offset = int(normalized["source_offset"])
            normalized["context_sequence_number"] = int(row["sequence_number"])
            normalized["context_source_start"] = int(row["source_start"])
            normalized["context_source_end"] = int(row["source_end"])
            normalized["source_excerpt"] = content[max(0, offset - 100):min(len(content), offset + 140)]
            boundary_decisions.append(normalized)
    boundary_decisions.sort(key=lambda row: int(row["source_offset"]))
    boundary_offsets = [int(row["source_offset"]) for row in boundary_decisions]
    if boundary_offsets != list(EXPECTED_BOUNDARY_OFFSETS):
        raise RuntimeError(
            f"Stage10 v2 exact boundary-offset census drift: {boundary_offsets!r}"
        )
    if len(boundary_decisions) != EXPECTED_COALESCED_BOUNDARIES:
        raise RuntimeError(f"persisted Stage10 merge-decision drift: {len(boundary_decisions)}")
    if len(set(boundary_offsets)) != EXPECTED_COALESCED_BOUNDARIES:
        raise RuntimeError(f"Stage10 v2 merge offsets are not unique: {boundary_offsets!r}")
    if WHENCE_BOUNDARY_OFFSET not in boundary_offsets:
        raise RuntimeError(f"known whence boundary missing from Stage10 v2 census: {boundary_offsets!r}")
    for decision in boundary_decisions:
        if (
            decision.get("policy") != STAGE10_BOUNDARY_POLICY
            or decision.get("merge") is not True
            or decision.get("reason") != "lowercase_continuation_without_terminal"
            or decision.get("whitespace_only_gap") is not True
            or decision.get("paragraph_break") is not False
            or decision.get("source_terminal_punctuation") is not False
            or decision.get("lowercase_continuation") is not True
            or decision.get("consecutive_parser_indices") is not True
        ):
            raise RuntimeError(f"unsafe or unexplained Stage10 v2 merge decision: {decision!r}")

    replay_output = run_composed_stage12(
        database,
        context_run_id=v2_context_run_id,
        parameters=base_parameters,
        implementation="opus-en-ru-ct2",
    )
    replay_run_id = int(replay_output["translation_run_id"])
    if replay_run_id == BASE_RUN_ID:
        raise RuntimeError("Stage10 v2 replay unexpectedly reused run 16")

    with connect(database, readonly=True) as connection:
        replay_run = get_run(connection, replay_run_id)
        replay_rows = get_run_items(connection, replay_run_id, kind="translation_segment")
    if replay_run["status"] != "completed" or int(replay_run["stage_number"]) != 12:
        raise RuntimeError("Stage10 v2 replay is not a completed Stage12 run")
    stored_replay_output = dict(replay_run.get("output") or {})
    if int(stored_replay_output.get("context_run_id") or -1) != v2_context_run_id:
        raise RuntimeError("Stage10 v2 replay points at the wrong context run")
    if stored_replay_output.get("real_mt") is not True:
        raise RuntimeError("Stage10 v2 replay is not explicitly real MT")
    if stored_replay_output.get("network_used") is not False:
        raise RuntimeError("Stage10 v2 replay unexpectedly reports network-backed MT inference")

    _coverage(replay_rows, content, label="Stage10 v2 Stage12 replay")
    replay_inventory = _inventory(replay_rows)
    hard_gate_non_regression = all(
        int(replay_inventory["counts"][key]) <= int(BASE_COUNTS[key])
        for key in ("numeric_symbol", "punctuation", "length", "unique")
    )

    base_by_geometry = {_geometry_key(row): row for row in base_rows}
    replay_by_geometry = {_geometry_key(row): row for row in replay_rows}
    if len(base_by_geometry) != len(base_rows) or len(replay_by_geometry) != len(replay_rows):
        raise RuntimeError("duplicate translation source geometry prevents exact comparison")
    common_geometry = sorted(set(base_by_geometry) & set(replay_by_geometry))
    untouched_target_drifts: list[dict[str, Any]] = []
    untouched_target_exact = 0
    for key in common_geometry:
        base_row = base_by_geometry[key]
        replay_row = replay_by_geometry[key]
        base_target = str(base_row.get("target_text") or "")
        replay_target = str(replay_row.get("target_text") or "")
        if base_target == replay_target:
            untouched_target_exact += 1
        else:
            untouched_target_drifts.append(
                {
                    "source_start": key[0],
                    "source_end": key[1],
                    "source_text": key[2],
                    "base_target": base_target,
                    "v2_target": replay_target,
                }
            )

    base_only_keys = sorted(set(base_by_geometry) - set(replay_by_geometry))
    replay_only_keys = sorted(set(replay_by_geometry) - set(base_by_geometry))
    base_changed_rows = [_row_evidence(base_by_geometry[key]) for key in base_only_keys]
    replay_changed_rows = [_row_evidence(replay_by_geometry[key]) for key in replay_only_keys]

    base_by_start = {int(row["source_start"]): row for row in base_rows}
    first_whence = base_by_start.get(WHENCE_FIRST_START)
    second_whence = base_by_start.get(WHENCE_BOUNDARY_OFFSET)
    if first_whence is None or second_whence is None:
        raise RuntimeError("run-16 whence pair source geometry drift")
    if int(first_whence["source_end"]) != WHENCE_BOUNDARY_OFFSET:
        raise RuntimeError("run-16 whence pair is not contiguous at the known false boundary")
    whence_end = int(second_whence["source_end"])
    whence_source = content[WHENCE_FIRST_START:whence_end]
    if (
        str(first_whence.get("source_text") or "")
        + str(second_whence.get("source_text") or "")
        != whence_source
    ):
        raise RuntimeError("run-16 whence pair is not byte-exact")
    replay_whence_rows = _overlapping_rows(
        replay_rows, WHENCE_FIRST_START, whence_end
    )
    if not replay_whence_rows:
        raise RuntimeError("Stage10 v2 replay contains no whence replacement row")
    if (
        int(replay_whence_rows[0]["source_start"]) != WHENCE_FIRST_START
        or int(replay_whence_rows[-1]["source_end"]) != whence_end
        or "".join(str(row.get("source_text") or "") for row in replay_whence_rows)
        != whence_source
    ):
        raise RuntimeError("Stage10 v2 whence replacement does not preserve exact source geometry")
    base_whence_target = _aggregate_target([first_whence, second_whence])
    replay_whence_target = _aggregate_target(replay_whence_rows)
    base_whence_verdict = evaluate_rescue_pair(whence_source, base_whence_target)
    replay_whence_verdict = evaluate_rescue_pair(whence_source, replay_whence_target)
    whence_punctuation_repaired = replay_whence_verdict.get("punctuation_passed") is True
    whence_semantic_anchors = _semantic_anchors(replay_whence_target)

    with sqlite3.connect(database) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()

    validation = {
        "stage10_v2_boundary_count_exact": len(boundary_decisions) == EXPECTED_COALESCED_BOUNDARIES,
        "known_whence_boundary_merged": WHENCE_BOUNDARY_OFFSET in boundary_offsets,
        "source_coverage_byte_exact": True,
        "hard_gate_non_regression": hard_gate_non_regression,
        "unchanged_geometry_target_drift_zero": not untouched_target_drifts,
        "whence_punctuation_repaired": whence_punctuation_repaired,
        "sqlite_integrity_ok": integrity == "ok" and not foreign,
    }

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "exact run-16 Stage8 -> Stage10-v2 -> maintained composed Stage12 full-Opticks comparison",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "public_stage12_surface_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "persisted_database_sha256": _sha(database),
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_context_run_id": old_context_run_id,
        "base_context_implementation": str(old_context_run.get("implementation") or ""),
        "base_context_output_sha256": str(old_context_run.get("output_sha256") or ""),
        "nlp_run_id": nlp_run_id,
        "nlp_output_sha256": str(nlp_run.get("output_sha256") or ""),
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_character_count": len(content),
        "stage10_v2_context_run_id": v2_context_run_id,
        "stage10_v2_context_output_sha256": str(v2_context_run.get("output_sha256") or ""),
        "stage10_v2_schema": stored_v2_output.get("schema"),
        "stage10_v2_implementation": str(v2_context_run.get("implementation") or ""),
        "stage10_v2_boundary_policy": stored_v2_output.get("boundary_policy"),
        "stage10_v2_spacy_sentence_count": int(stored_v2_output["spacy_sentence_count"]),
        "stage10_v2_sentence_count": int(stored_v2_output["sentence_count"]),
        "stage10_v2_coalesced_boundary_count": int(stored_v2_output["coalesced_boundary_count"]),
        "stage10_v2_coalesced_context_count": int(stored_v2_output["coalesced_context_count"]),
        "stage10_v2_boundary_offsets": boundary_offsets,
        "stage10_v2_boundary_decisions": boundary_decisions,
        "replay_translation_run_id": replay_run_id,
        "replay_translation_output_sha256": str(replay_run.get("output_sha256") or ""),
        "base_segment_count": len(base_rows),
        "replay_segment_count": len(replay_rows),
        "base_hard_gate_counts": base_inventory["counts"],
        "replay_hard_gate_counts": replay_inventory["counts"],
        "hard_gate_delta": {
            key: int(replay_inventory["counts"][key]) - int(BASE_COUNTS[key])
            for key in ("numeric_symbol", "punctuation", "length", "unique")
        },
        "base_failure_source_starts": base_inventory["failure_source_starts"],
        "replay_failure_source_starts": replay_inventory["failure_source_starts"],
        "common_source_geometry_count": len(common_geometry),
        "unchanged_geometry_target_exact_count": untouched_target_exact,
        "unchanged_geometry_target_drift_count": len(untouched_target_drifts),
        "unchanged_geometry_target_drifts": untouched_target_drifts,
        "base_only_geometry_count": len(base_only_keys),
        "replay_only_geometry_count": len(replay_only_keys),
        "base_changed_rows": base_changed_rows,
        "replay_changed_rows": replay_changed_rows,
        "whence_case": {
            "first_source_start": WHENCE_FIRST_START,
            "boundary_offset": WHENCE_BOUNDARY_OFFSET,
            "source_end": whence_end,
            "source_text": whence_source,
            "base_row_count": 2,
            "replay_row_count": len(replay_whence_rows),
            "base_target": base_whence_target,
            "replay_target": replay_whence_target,
            "base_hard_verdict": base_whence_verdict,
            "replay_hard_verdict": replay_whence_verdict,
            "replay_semantic_anchors": whence_semantic_anchors,
            "all_recorded_semantic_anchors": all(whence_semantic_anchors.values()),
            "semantic_anchor_result_is_diagnostic_only": True,
        },
        "required_research_rescue_flags": list(REQUIRED_RESCUE_FLAGS),
        "validation": validation,
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violation_count": len(foreign),
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-stage10-v2-comparison.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "stage10_v2_context_run_id": v2_context_run_id,
                "stage10_v2_boundary_offsets": boundary_offsets,
                "replay_translation_run_id": replay_run_id,
                "base_hard_gate_counts": base_inventory["counts"],
                "replay_hard_gate_counts": replay_inventory["counts"],
                "hard_gate_delta": evidence["hard_gate_delta"],
                "unchanged_geometry_target_drift_count": len(untouched_target_drifts),
                "whence_punctuation_repaired": whence_punctuation_repaired,
                "persisted_database_sha256": evidence["persisted_database_sha256"],
                "replay_translation_output_sha256": evidence["replay_translation_output_sha256"],
                "evidence_sha256": evidence["evidence_sha256"],
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    failed = [name for name, passed in validation.items() if passed is not True]
    if failed:
        raise RuntimeError(f"Stage10 v2 full-Opticks comparison failed: {failed!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
