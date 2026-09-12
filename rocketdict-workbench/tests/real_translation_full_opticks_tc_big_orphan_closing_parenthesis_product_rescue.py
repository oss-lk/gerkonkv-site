from __future__ import annotations

"""Persist and audit the default-off orphan-closing-parenthesis rescue over run17."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.alternative_mt_runtime import load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_orphan_closing_parenthesis_rescue_stage import (
    TC_BIG_ORPHAN_CLOSING_PAREN_RESCUE_CONTRACT,
    TC_BIG_ORPHAN_CLOSING_PAREN_SELECTED_PHASE,
    TC_BIG_ORPHAN_CLOSING_PAREN_SELECTOR_CONTRACT,
    TC_BIG_ORPHAN_CLOSING_PAREN_TRIGGER_CONTRACT,
    run_stage12 as run_orphan_parenthesis_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-orphan-closing-parenthesis-rescue-optin/1"
BASE_DATABASE_SHA256 = "2cbf20b39168003e494b2fb73c9b9baea427283def04a076a673e5023d7346a4"
BASE_RUN_ID = 17
BASE_OUTPUT_SHA256 = "f7c04209d9e8d7ffab673a2987b0024c334f24fee59736466597ea99125f7ff1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 17, "length": 0, "unique": 36}
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 20, "punctuation": 16, "length": 0, "unique": 35}
BASE_SEGMENTS = 3343
EXPECTED_SOURCE_START = 417917
EXPECTED_SOURCE_END = 418111
EXPECTED_TARGET = (
    "Из ярких Колец, сделанных в этом Наблюдении более тонким Стеклом, "
    "3.4-1/6.5-1/8, к Диаметрам тех же самых Колец, сделанных в третьем из "
    "этих Наблюдений более толстым Стеклом 1-11/16, 2-3/8."
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
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
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
        flags = _hard_flags(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
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


def _semantic_review(source: str, target: str) -> dict[str, Any]:
    lowered = target.casefold()
    anchors = {
        "bright_rings": "ярк" in lowered and "кол" in lowered,
        "observation": "наблюден" in lowered,
        "thinner_glass": "тонк" in lowered and "стекл" in lowered,
        "diameters": "диаметр" in lowered,
        "same_rings": "тех же" in lowered and "кол" in lowered,
        "third_observation": "треть" in lowered and "наблюден" in lowered,
        "thicker_glass": "толст" in lowered and "стекл" in lowered,
    }
    verdict = evaluate_rescue_pair(source, target)
    return {
        "source": source,
        "target": target,
        "diagnostic_anchors": anchors,
        "all_diagnostic_anchors": all(anchors.values()),
        "numeric_symbol_clean": (verdict.get("numeric_symbol") or {}).get("passed") is True,
        "punctuation_clean": verdict.get("punctuation_passed") is True,
        "length_clean": verdict.get("length_passed") is True,
        "strict_research_clean": verdict.get("strict_research_passed") is True,
        "diagnostics_are_non_authoritative": True,
        "manual_semantic_review_still_required_for_product_promotion": True,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_ORPHAN_PAREN_PRODUCT_ROOT",
            "work/full-opticks-tc-big-orphan-closing-parenthesis-rescue",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("orphan-parenthesis replay requires exact persisted run17 database")

    asset = load_tc_big_asset()
    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        )
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        document = get_document(connection, int(base_output["document_version_id"]))

    if int(base_run.get("stage_number") or -1) != 12:
        raise RuntimeError("run17 is not a Stage12 run")
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run17 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run17 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run17 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run17 baseline drift: counts={base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    base_case = next(
        (row for row in base_rows if int(row["source_start"]) == EXPECTED_SOURCE_START),
        None,
    )
    if base_case is None or int(base_case["source_end"]) != EXPECTED_SOURCE_END:
        raise RuntimeError("expected orphan-parenthesis source span missing from run17")
    if str(base_case.get("source_text") or "").count("(") != 0 or str(
        base_case.get("source_text") or ""
    ).count(")") != 0:
        raise RuntimeError("run17 orphan-parenthesis source-shape drift")
    if str(base_case.get("target_text") or "").count("(") != 0 or str(
        base_case.get("target_text") or ""
    ).count(")") != 1:
        raise RuntimeError("run17 orphan-parenthesis target-shape drift")
    base_case_flags = _hard_flags(
        str(base_case.get("source_text") or ""), str(base_case.get("target_text") or "")
    )
    if base_case_flags != {"numeric_symbol": False, "punctuation": True, "length": False}:
        raise RuntimeError(f"run17 orphan-parenthesis base hard-family drift: {base_case_flags!r}")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_tc_big_orphan_closing_parenthesis_rescue": True,
            "tc_big_orphan_closing_parenthesis_rescue_contract": (
                TC_BIG_ORPHAN_CLOSING_PAREN_RESCUE_CONTRACT
            ),
            "tc_big_orphan_closing_parenthesis_selector_contract": (
                TC_BIG_ORPHAN_CLOSING_PAREN_SELECTOR_CONTRACT
            ),
            "tc_big_orphan_closing_parenthesis_trigger_contract": (
                TC_BIG_ORPHAN_CLOSING_PAREN_TRIGGER_CONTRACT
            ),
            "tc_big_orphan_closing_parenthesis_rescue_phase": (
                TC_BIG_ORPHAN_CLOSING_PAREN_SELECTED_PHASE
            ),
        }
    )
    enabled = run_orphan_parenthesis_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id == BASE_RUN_ID:
        raise RuntimeError("orphan-parenthesis wrapper did not create a distinct Stage12 run")
    if int(enabled.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("orphan-parenthesis wrapper did not compose directly over exact run17")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("orphan-parenthesis wrapper base output SHA drift")
    if enabled.get("tc_big_orphan_closing_parenthesis_rescue_attempt_count") != 1:
        raise RuntimeError("orphan-parenthesis attempt-count drift")
    if enabled.get("tc_big_orphan_closing_parenthesis_rescue_accepted_count") != 1:
        raise RuntimeError("orphan-parenthesis accepted-count drift")
    if enabled.get("tc_big_orphan_closing_parenthesis_rescue_rejected_count") != 0:
        raise RuntimeError("orphan-parenthesis rejected-count drift")
    if list(
        enabled.get("tc_big_orphan_closing_parenthesis_rescue_attempted_source_starts") or []
    ) != [EXPECTED_SOURCE_START]:
        raise RuntimeError("orphan-parenthesis attempt cohort drift")
    if list(
        enabled.get("tc_big_orphan_closing_parenthesis_rescue_accepted_source_starts") or []
    ) != [EXPECTED_SOURCE_START]:
        raise RuntimeError("orphan-parenthesis accepted cohort drift")
    if list(enabled.get("tc_big_orphan_closing_parenthesis_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("orphan-parenthesis selector did not use raw rank0")
    if list(enabled.get("tc_big_orphan_closing_parenthesis_rescue_selected_targets") or []) != [
        EXPECTED_TARGET
    ]:
        raise RuntimeError("orphan-parenthesis raw rank0 drift from prior read-only DOE")
    if enabled.get("base_segment_count") != BASE_SEGMENTS or enabled.get("segment_count") != BASE_SEGMENTS:
        raise RuntimeError("orphan-parenthesis changed Stage12 row count")

    runtime = dict(enabled.get("tc_big_orphan_closing_parenthesis_rescue_runtime") or {})
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
        final_rows = _ordered(
            get_run_items(connection, final_run_id, kind="translation_segment")
        )
    _coverage(final_rows, content, label="orphan-parenthesis final")
    final_inventory = _inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS or len(final_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"orphan-parenthesis final hard-gate drift: {final_inventory['counts']!r}, rows={len(final_rows)}"
        )

    base_by_start = {int(row["source_start"]): row for row in base_rows}
    changed_rows: list[dict[str, Any]] = []
    untouched = 0
    untouched_target_drift = 0
    for row in final_rows:
        start = int(row["source_start"])
        base = base_by_start.get(start)
        if base is None:
            raise RuntimeError(f"final row has new source start {start}")
        if (
            int(row["source_end"]) != int(base["source_end"])
            or str(row.get("source_text") or "") != str(base.get("source_text") or "")
        ):
            raise RuntimeError(f"source geometry changed at {start}")
        rescue = dict(
            (row.get("payload") or {}).get("tc_big_orphan_closing_parenthesis_rescue")
            or {}
        )
        if rescue.get("contract") != TC_BIG_ORPHAN_CLOSING_PAREN_RESCUE_CONTRACT:
            raise RuntimeError("orphan-parenthesis row contract drift")
        if rescue.get("selector_contract") != TC_BIG_ORPHAN_CLOSING_PAREN_SELECTOR_CONTRACT:
            raise RuntimeError("orphan-parenthesis row selector contract drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
            "corpus_specific_target_patches",
            "evaluator_weakened",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe orphan-parenthesis row flag: {flag}")

        if rescue.get("applied") is not True:
            untouched += 1
            if str(row.get("target_text") or "") != str(base.get("target_text") or ""):
                untouched_target_drift += 1
            continue

        if start != EXPECTED_SOURCE_START:
            raise RuntimeError("unexpected orphan-parenthesis applied row")
        if rescue.get("trigger_contract") != TC_BIG_ORPHAN_CLOSING_PAREN_TRIGGER_CONTRACT:
            raise RuntimeError("applied orphan-parenthesis trigger contract drift")
        if rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
            raise RuntimeError("applied orphan-parenthesis candidate is not raw rank0")
        trigger = dict(rescue.get("trigger") or {})
        selection = dict(rescue.get("selection") or {})
        if trigger.get("eligible") is not True:
            raise RuntimeError("applied orphan-parenthesis row lacks eligible trigger")
        if trigger.get("orphan_closing_parenthesis_shape") is not True:
            raise RuntimeError("applied row escaped orphan-parenthesis defect class")
        if (trigger.get("split_fragment") or {}).get("eligible") is not True:
            raise RuntimeError("applied row lacks split-fragment source geometry")
        if selection.get("accepted") is not True or selection.get("hard_punctuation_exact") is not True:
            raise RuntimeError("applied orphan-parenthesis selector evidence drift")
        if str(row.get("target_text") or "") != EXPECTED_TARGET:
            raise RuntimeError("applied row target differs from exact raw rank0")
        changed_rows.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": start,
                "source_end": int(row["source_end"]),
                "source_text": str(row.get("source_text") or ""),
                "base_target_text": str(base.get("target_text") or ""),
                "selected_target": str(row.get("target_text") or ""),
                "trigger": trigger,
                "selection": selection,
                "semantic_review": _semantic_review(
                    str(row.get("source_text") or ""), str(row.get("target_text") or "")
                ),
            }
        )

    if len(changed_rows) != 1 or untouched != BASE_SEGMENTS - 1:
        raise RuntimeError(
            f"orphan-parenthesis change cardinality drift: changed={len(changed_rows)}, untouched={untouched}"
        )
    if untouched_target_drift != 0:
        raise RuntimeError(
            f"orphan-parenthesis changed {untouched_target_drift} supposedly untouched targets"
        )
    semantic = changed_rows[0]["semantic_review"]
    if (
        semantic["all_diagnostic_anchors"] is not True
        or semantic["numeric_symbol_clean"] is not True
        or semantic["punctuation_clean"] is not True
        or semantic["length_clean"] is not True
        or semantic["strict_research_clean"] is not True
    ):
        raise RuntimeError("selected orphan-parenthesis rank0 failed semantic/mechanical audit")

    with sqlite3.connect(database) as connection:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError(
            f"final database integrity drift: integrity={integrity!r}, fk={fk_count}"
        )

    final_database_sha256 = _sha(database)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "persist and audit one default-off source-defined split-fragment orphan-closing-parenthesis "
            "raw TC-big rank0 rescue directly over exact run17"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "final_database_sha256": final_database_sha256,
        "final_translation_run_id": final_run_id,
        "final_output_sha256": str(final_run.get("output_sha256") or ""),
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_character_count": len(content),
        "base_segment_count": len(base_rows),
        "final_segment_count": len(final_rows),
        "base_hard_gate_counts": BASE_COUNTS,
        "final_hard_gate_counts": final_inventory["counts"],
        "base_failure_sequences": base_inventory["failures"],
        "final_failure_sequences": final_inventory["failures"],
        "attempt_count": enabled[
            "tc_big_orphan_closing_parenthesis_rescue_attempt_count"
        ],
        "accepted_count": enabled[
            "tc_big_orphan_closing_parenthesis_rescue_accepted_count"
        ],
        "rejected_count": enabled[
            "tc_big_orphan_closing_parenthesis_rescue_rejected_count"
        ],
        "attempted_source_starts": enabled[
            "tc_big_orphan_closing_parenthesis_rescue_attempted_source_starts"
        ],
        "accepted_source_starts": enabled[
            "tc_big_orphan_closing_parenthesis_rescue_accepted_source_starts"
        ],
        "selected_ranks": enabled[
            "tc_big_orphan_closing_parenthesis_rescue_selected_ranks"
        ],
        "selected_targets": enabled[
            "tc_big_orphan_closing_parenthesis_rescue_selected_targets"
        ],
        "changed_rows": changed_rows,
        "untouched_base_row_count": untouched,
        "untouched_target_drift_count": untouched_target_drift,
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "foreign_key_violation_count": fk_count,
        "tc_big_runtime": runtime,
        "tc_big_asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
            "repository": asset.repository,
            "revision": asset.revision,
            "model_safetensors_sha256": asset.model_safetensors_sha256,
            "license": asset.license,
        },
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    evidence_path = root / "full-opticks-tc-big-orphan-closing-parenthesis-rescue.json"
    evidence_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "base": BASE_COUNTS,
                "final": final_inventory["counts"],
                "attempted_source_starts": payload["attempted_source_starts"],
                "accepted_source_starts": payload["accepted_source_starts"],
                "selected_ranks": payload["selected_ranks"],
                "selected_target": payload["selected_targets"][0],
                "untouched_base_row_count": untouched,
                "untouched_target_drift_count": untouched_target_drift,
                "final_output_sha256": payload["final_output_sha256"],
                "final_database_sha256": final_database_sha256,
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
