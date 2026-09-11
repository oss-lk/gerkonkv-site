from __future__ import annotations

"""Persist/audit the opt-in illustration-label Product rescue over immutable run 8."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_illustration_rescue_stage import (
    ILLUSTRATION_LABEL_RESCUE_CONTRACT,
    ILLUSTRATION_LABEL_SELECTED_PHASE,
    ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
    ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
    run_stage12 as run_illustration_stage12,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-illustration-label-product-rescue-optin/1"
SOURCE_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2"
BASE_RUN_ID = 8
BASE_OUTPUT_SHA256 = "d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346"
EXPECTED_STARTS = [72401, 90105, 203786]
EXPECTED_RANKS = [3, 3, 0]
EXPECTED_TARGETS = ["Иллюстрация.", "Иллюстрация.", "С центром O"]
BASE_COUNTS = {"numeric_symbol": 25, "punctuation": 33, "length": 0, "unique": 55}
ENABLED_COUNTS = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
BASE_SEGMENTS = 3343
ENABLED_SEGMENTS = 3346
RESEARCH_V3 = {
    "workflow_run_id": 34609890716,
    "artifact_id": 10267328730,
    "artifact_digest_sha256": "2c5a8b0d11c5924e370076cf4dc5d00b26ad8c4e580f8ca14e2faf642bf7b6e2",
    "evidence_file_sha256": "c4ec0adc18f4fa7e2fb0cba4d5df3e28c85e5cacdc87e6626646dad398d9c394",
    "evidence_sha256": "5a24353ab6996ed9d31cc474c76c8896464a5b9b20b0909328fba91277829e93",
}


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


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_ILLUSTRATION_PRODUCT_ROOT",
            "work/illustration-product-rescue",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file():
        raise RuntimeError("Illustration Product rescue requires run-8 database")
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("Illustration Product base database identity drift")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-8 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-8 normalized source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run-8 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS:
        raise RuntimeError(f"run-8 gate drift: {base_inventory['counts']!r}")
    if len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError("run-8 segment-count drift")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_illustration_label_rescue": True,
            "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
            "illustration_label_rescue_selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
            "illustration_word_target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
            "illustration_label_rescue_phase": ILLUSTRATION_LABEL_SELECTED_PHASE,
        }
    )
    enabled = run_illustration_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    enabled_run_id = int(enabled["translation_run_id"])
    if enabled_run_id == BASE_RUN_ID:
        raise RuntimeError("illustration rescue did not persist a distinct Stage12 run")
    if int(enabled.get("base_translation_run_id") or 0) != BASE_RUN_ID:
        raise RuntimeError("illustration wrapper did not compose over exact run 8")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("illustration wrapper base output SHA drift")
    if enabled.get("illustration_label_rescue_enabled") is not True:
        raise RuntimeError("illustration rescue not enabled")
    if enabled.get("illustration_label_rescue_generation_supported") is not True:
        raise RuntimeError("illustration rescue generation unexpectedly unsupported")
    if enabled.get("illustration_label_rescue_contract") != ILLUSTRATION_LABEL_RESCUE_CONTRACT:
        raise RuntimeError("illustration rescue contract drift")
    if enabled.get("illustration_label_rescue_selector_contract") != ILLUSTRATION_LABEL_SELECTOR_CONTRACT:
        raise RuntimeError("illustration selector contract drift")
    if enabled.get("illustration_word_target_form_contract") != ILLUSTRATION_WORD_TARGET_FORM_CONTRACT:
        raise RuntimeError("illustration target-form contract drift")
    if list(enabled.get("illustration_label_rescue_attempted_source_starts") or []) != EXPECTED_STARTS:
        raise RuntimeError("illustration attempted cohort drift")
    if list(enabled.get("illustration_label_rescue_accepted_source_starts") or []) != EXPECTED_STARTS:
        raise RuntimeError("illustration accepted cohort drift")
    if list(enabled.get("illustration_label_rescue_rejected_source_starts") or []) != []:
        raise RuntimeError("illustration unexpected rejected cohort")
    if list(enabled.get("illustration_label_rescue_selected_ranks") or []) != EXPECTED_RANKS:
        raise RuntimeError("illustration selected ranks drift")
    if list(enabled.get("illustration_label_rescue_selected_targets") or []) != EXPECTED_TARGETS:
        raise RuntimeError("illustration selected targets drift")
    if list(enabled.get("illustration_label_rescue_normalized_model_input_source_starts") or []) != EXPECTED_STARTS[:2]:
        raise RuntimeError("illustration normalized-input scope drift")
    if int(enabled.get("base_segment_count") or 0) != BASE_SEGMENTS:
        raise RuntimeError("illustration base segment-count drift")
    if int(enabled.get("segment_count") or 0) != ENABLED_SEGMENTS:
        raise RuntimeError("illustration enabled segment-count drift")
    for flag in (
        "source_bytes_rewritten",
        "target_rewriting",
        "placeholders",
        "post_translation_literal_injection",
    ):
        if enabled.get(flag) is not False:
            raise RuntimeError(f"illustration unsafe output flag {flag}={enabled.get(flag)!r}")

    with connect(database, readonly=True) as connection:
        persisted = get_run(connection, enabled_run_id)
        enabled_rows = get_run_items(connection, enabled_run_id, kind="translation_segment")
    _coverage(enabled_rows, content, label="illustration enabled")
    inventory = _inventory(enabled_rows)
    if inventory["counts"] != ENABLED_COUNTS:
        raise RuntimeError(f"illustration gate result drift: {inventory['counts']!r}")
    if len(enabled_rows) != ENABLED_SEGMENTS:
        raise RuntimeError("illustration persisted segment-count drift")

    base_by_id = {int(row["id"]): row for row in base_rows}
    untouched = 0
    applied_by_base: dict[int, list[dict[str, Any]]] = {}
    for row in enabled_rows:
        rescue = dict((row.get("payload") or {}).get("illustration_label_rescue") or {})
        if rescue.get("contract") != ILLUSTRATION_LABEL_RESCUE_CONTRACT:
            raise RuntimeError("illustration row provenance contract drift")
        if rescue.get("selector_contract") != ILLUSTRATION_LABEL_SELECTOR_CONTRACT:
            raise RuntimeError("illustration row selector provenance drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"illustration row violates {flag}=False")
        base_id = int(rescue["base_translation_segment_id"])
        base = base_by_id.get(base_id)
        if base is None:
            raise RuntimeError("illustration row references unknown base row")
        if rescue.get("applied") is not True:
            actual = (
                int(row["source_start"]),
                int(row["source_end"]),
                str(row.get("source_text") or ""),
                str(row.get("target_text") or ""),
            )
            expected = (
                int(base["source_start"]),
                int(base["source_end"]),
                str(base.get("source_text") or ""),
                str(base.get("target_text") or ""),
            )
            if actual != expected:
                raise RuntimeError("untouched illustration row is not base-exact")
            untouched += 1
        else:
            applied_by_base.setdefault(base_id, []).append(row)

    if untouched != BASE_SEGMENTS - len(EXPECTED_STARTS):
        raise RuntimeError(f"untouched base-exact count drift: {untouched}")
    if len(applied_by_base) != len(EXPECTED_STARTS):
        raise RuntimeError("illustration applied base-row count drift")

    applied_cases: list[dict[str, Any]] = []
    for base_id, parts in sorted(
        applied_by_base.items(), key=lambda item: int(base_by_id[item[0]]["source_start"])
    ):
        base = base_by_id[base_id]
        parts = sorted(parts, key=lambda row: int(row["source_start"]))
        if len(parts) != 2:
            raise RuntimeError("illustration accepted base row did not split into two rows")
        if "".join(str(row.get("source_text") or "") for row in parts) != str(base.get("source_text") or ""):
            raise RuntimeError("illustration applied source is not exact base source")
        structural, remainder = parts
        structural_rescue = dict((structural.get("payload") or {}).get("illustration_label_rescue") or {})
        remainder_payload = dict(remainder.get("payload") or {})
        remainder_rescue = dict(remainder_payload.get("illustration_label_rescue") or {})
        if structural_rescue.get("role") != "source_owned_prefix":
            raise RuntimeError("illustration structural role drift")
        if structural_rescue.get("source_owned_passthrough") is not True:
            raise RuntimeError("illustration structural passthrough evidence drift")
        if str(structural.get("target_text") or "") != str(structural.get("source_text") or ""):
            raise RuntimeError("illustration source-owned prefix target drift")
        if remainder_rescue.get("role") != "linguistic_remainder":
            raise RuntimeError("illustration remainder role drift")
        if remainder_rescue.get("source_owned_passthrough") is not False:
            raise RuntimeError("illustration remainder passthrough evidence drift")
        hypotheses = list(remainder_payload.get("hypotheses") or [])
        rank = int(remainder_payload["selected_rank"])
        if str(remainder.get("target_text") or "") != str(hypotheses[rank].get("text") or ""):
            raise RuntimeError("illustration remainder target is not exact raw selected hypothesis")
        applied_cases.append(
            {
                "base_translation_segment_id": base_id,
                "source_start": int(base["source_start"]),
                "source_end": int(base["source_end"]),
                "base_source": str(base.get("source_text") or ""),
                "base_target": str(base.get("target_text") or ""),
                "structural_source": str(structural.get("source_text") or ""),
                "remainder_source": str(remainder.get("source_text") or ""),
                "remainder_target": str(remainder.get("target_text") or ""),
                "selected_rank": rank,
                "model_input": remainder_rescue.get("model_input"),
                "source_model_input_normalized": remainder_rescue.get("source_model_input_normalized"),
                "generation": remainder_rescue.get("generation"),
                "selection": remainder_rescue.get("selection"),
            }
        )

    starts = [case["source_start"] for case in applied_cases]
    ranks = [case["selected_rank"] for case in applied_cases]
    targets = [case["remainder_target"] for case in applied_cases]
    if starts != EXPECTED_STARTS or ranks != EXPECTED_RANKS or targets != EXPECTED_TARGETS:
        raise RuntimeError(
            f"illustration applied-case identity drift: {starts!r} {ranks!r} {targets!r}"
        )

    with sqlite3.connect(database) as raw:
        integrity = raw.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = raw.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != [("ok",)] or foreign_keys:
        raise RuntimeError(
            f"illustration persisted database integrity failure: {integrity!r} {foreign_keys!r}"
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted full-Opticks Product-wrapper audit of default-OFF standalone illustration-label rescue",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "public_stage12_surface_allowed": False,
        "semantic_review_required": True,
        "source_sha256": SOURCE_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "research_v3": RESEARCH_V3,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_hard_gate_counts": base_inventory["counts"],
        "base_segment_count": len(base_rows),
        "enabled_translation_run_id": enabled_run_id,
        "enabled_translation_output_sha256": str(persisted.get("output_sha256") or ""),
        "enabled_hard_gate_counts": inventory["counts"],
        "enabled_segment_count": len(enabled_rows),
        "attempted_source_starts": list(enabled["illustration_label_rescue_attempted_source_starts"]),
        "accepted_source_starts": list(enabled["illustration_label_rescue_accepted_source_starts"]),
        "selected_ranks": list(enabled["illustration_label_rescue_selected_ranks"]),
        "selected_targets": list(enabled["illustration_label_rescue_selected_targets"]),
        "applied_cases": applied_cases,
        "untouched_base_exact_count": untouched,
        "source_coverage_byte_exact": True,
        "database_integrity_check": "ok",
        "foreign_key_check": [],
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_sha256_after": _sha(database),
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-illustration-label-product-rescue-optin.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "enabled_translation_run_id": enabled_run_id,
                "enabled_translation_output_sha256": payload["enabled_translation_output_sha256"],
                "base_hard_gate_counts": payload["base_hard_gate_counts"],
                "enabled_hard_gate_counts": payload["enabled_hard_gate_counts"],
                "accepted_source_starts": payload["accepted_source_starts"],
                "selected_ranks": payload["selected_ranks"],
                "selected_targets": payload["selected_targets"],
                "database_sha256_after": payload["database_sha256_after"],
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
