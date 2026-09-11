from __future__ import annotations

"""Persist and audit the opt-in TC-big delimiter-context rescue over immutable run 9.

The audit deliberately invokes the non-public Stage12 wrapper directly.  It
proves exact composition over persisted run 9, raw alternative-MT selection,
byte-exact source coverage, unchanged non-replaced rows, exact offline asset
identity, and independent hard-gate / SQLite integrity results.  It does not
authorize public or default promotion.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.alternative_mt_runtime import (
    TC_BIG_LICENSE,
    TC_BIG_MODEL_SAFETENSORS_SHA256,
    TC_BIG_REPOSITORY,
    TC_BIG_REVISION,
    load_tc_big_asset,
)
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_delimiter_rescue_stage import (
    TC_BIG_DELIMITER_RESCUE_CONTRACT,
    TC_BIG_DELIMITER_SELECTED_PHASE,
    TC_BIG_DELIMITER_SELECTOR_CONTRACT,
    TC_BIG_DELIMITER_TRIGGER_CONTRACT,
    run_stage12 as run_tc_big_delimiter_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-delimiter-product-rescue-optin/1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
BASE_RUN_ID = 9
BASE_OUTPUT_SHA256 = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
BASE_COUNTS = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
ENABLED_COUNTS = {"numeric_symbol": 24, "punctuation": 25, "length": 0, "unique": 47}
BASE_SEGMENTS = 3346
ENABLED_SEGMENTS = 3344
EXPECTED_ATTEMPT_STARTS = [488, 325892, 329077, 388656, 417625, 501398, 569170]
EXPECTED_ACCEPTED_STARTS = [488, 325892, 329077, 388656, 501398]
EXPECTED_REPLACED_BASE_ROW_COUNT = 7
EXPECTED_UNTOUCHED_BASE_COUNT = 3339
FEASIBILITY = {
    "workflow_run_id": 34627371508,
    "artifact_id": 10275510035,
    "artifact_digest_sha256": "5c76d7db662c66d86f073c36ab3baf99d739da0c200d7c88e38027b01b2947f6",
    "evidence_file_sha256": "46e901c87730d1f5ff7d8fa2ae893500b41ea37fd6cc4a691ab573c910b34f13",
    "evidence_sha256": "ef22c81ecfda624787c61fed7be66ddb39e9ae2c6a426e842a22dc03fb6d2cb9",
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
        if start != cursor or end <= start:
            raise RuntimeError(f"{label} source span drift at {sequence}")
        if content[start:end] != source:
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


def _same_translation_row(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return (
        int(actual["source_start"]),
        int(actual["source_end"]),
        str(actual.get("source_text") or ""),
        str(actual.get("target_text") or ""),
    ) == (
        int(expected["source_start"]),
        int(expected["source_end"]),
        str(expected.get("source_text") or ""),
        str(expected.get("target_text") or ""),
    )


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TC_BIG_DELIMITER_PRODUCT_ROOT",
            "work/tc-big-delimiter-product-rescue",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file():
        raise RuntimeError("TC-big delimiter Product audit requires immutable run-9 database")
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("TC-big delimiter Product base database identity drift")

    asset = load_tc_big_asset()
    if asset.repository != TC_BIG_REPOSITORY or asset.revision != TC_BIG_REVISION:
        raise RuntimeError("TC-big Product asset repository/revision drift")
    if asset.model_safetensors_sha256 != TC_BIG_MODEL_SAFETENSORS_SHA256:
        raise RuntimeError("TC-big Product asset source-weight identity drift")
    if asset.license != TC_BIG_LICENSE:
        raise RuntimeError("TC-big Product asset license drift")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-9 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-9 normalized source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run-9 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS:
        raise RuntimeError(f"run-9 gate drift: {base_inventory['counts']!r}")
    if len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(f"run-9 segment drift: {len(base_rows)}")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_tc_big_target_delimiter_rescue": True,
            "tc_big_target_delimiter_rescue_contract": TC_BIG_DELIMITER_RESCUE_CONTRACT,
            "tc_big_target_delimiter_selector_contract": TC_BIG_DELIMITER_SELECTOR_CONTRACT,
            "tc_big_target_delimiter_trigger_contract": TC_BIG_DELIMITER_TRIGGER_CONTRACT,
            "tc_big_target_delimiter_rescue_phase": TC_BIG_DELIMITER_SELECTED_PHASE,
        }
    )
    enabled = run_tc_big_delimiter_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    enabled_run_id = int(enabled["translation_run_id"])
    if enabled_run_id == BASE_RUN_ID:
        raise RuntimeError("TC-big delimiter rescue did not persist a distinct Stage12 run")
    if int(enabled.get("base_translation_run_id") or 0) != BASE_RUN_ID:
        raise RuntimeError("TC-big delimiter wrapper did not compose over exact run 9")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("TC-big delimiter wrapper base output SHA drift")
    if enabled.get("tc_big_target_delimiter_rescue_enabled") is not True:
        raise RuntimeError("TC-big delimiter rescue not enabled")
    if enabled.get("tc_big_target_delimiter_rescue_contract") != TC_BIG_DELIMITER_RESCUE_CONTRACT:
        raise RuntimeError("TC-big delimiter rescue contract drift")
    if enabled.get("tc_big_target_delimiter_selector_contract") != TC_BIG_DELIMITER_SELECTOR_CONTRACT:
        raise RuntimeError("TC-big delimiter selector contract drift")
    if enabled.get("tc_big_target_delimiter_trigger_contract") != TC_BIG_DELIMITER_TRIGGER_CONTRACT:
        raise RuntimeError("TC-big delimiter trigger contract drift")
    if int(enabled.get("tc_big_target_delimiter_rescue_attempt_count") or -1) != len(EXPECTED_ATTEMPT_STARTS):
        raise RuntimeError("TC-big delimiter attempt-count drift")
    if int(enabled.get("tc_big_target_delimiter_rescue_accepted_count") or -1) != len(EXPECTED_ACCEPTED_STARTS):
        raise RuntimeError("TC-big delimiter accepted-count drift")
    if int(enabled.get("tc_big_target_delimiter_rescue_rejected_count") or -1) != 2:
        raise RuntimeError("TC-big delimiter rejected-count drift")
    if list(enabled.get("tc_big_target_delimiter_rescue_attempted_source_starts") or []) != EXPECTED_ATTEMPT_STARTS:
        raise RuntimeError("TC-big delimiter attempted cohort drift")
    if list(enabled.get("tc_big_target_delimiter_rescue_accepted_source_starts") or []) != EXPECTED_ACCEPTED_STARTS:
        raise RuntimeError("TC-big delimiter accepted cohort drift")
    if int(enabled.get("base_segment_count") or 0) != BASE_SEGMENTS:
        raise RuntimeError("TC-big delimiter base segment-count drift")
    if int(enabled.get("segment_count") or 0) != ENABLED_SEGMENTS:
        raise RuntimeError("TC-big delimiter enabled segment-count drift")

    runtime = dict(enabled.get("tc_big_target_delimiter_rescue_runtime") or {})
    if runtime.get("available") is not True or runtime.get("asset_configured") is not True:
        raise RuntimeError(f"TC-big persisted runtime unavailable: {runtime!r}")
    if runtime.get("repository") != TC_BIG_REPOSITORY or runtime.get("revision") != TC_BIG_REVISION:
        raise RuntimeError("TC-big persisted runtime repository/revision drift")
    if runtime.get("model_safetensors_sha256") != TC_BIG_MODEL_SAFETENSORS_SHA256:
        raise RuntimeError("TC-big persisted runtime weights drift")
    if str(runtime.get("license") or "").casefold() != TC_BIG_LICENSE:
        raise RuntimeError("TC-big persisted runtime license drift")
    if runtime.get("offline") is not True or runtime.get("compute_type") != "float32":
        raise RuntimeError("TC-big persisted runtime offline/compute identity drift")
    if runtime.get("torch_required_for_inference") is not False:
        raise RuntimeError("TC-big persisted runtime unexpectedly requires Torch")
    if runtime.get("asset_manifest_sha256") != asset.manifest_sha256:
        raise RuntimeError("TC-big persisted manifest identity drift")
    if runtime.get("asset_payload_tree_sha256") != asset.payload_tree_sha256:
        raise RuntimeError("TC-big persisted payload-tree identity drift")
    if int(runtime.get("asset_payload_file_count") or 0) != asset.payload_file_count:
        raise RuntimeError("TC-big persisted payload file-count drift")
    if int(runtime.get("asset_payload_bytes") or 0) != asset.payload_bytes:
        raise RuntimeError("TC-big persisted payload byte-count drift")

    for flag in (
        "source_bytes_rewritten",
        "target_rewriting",
        "placeholders",
        "post_translation_literal_injection",
        "corpus_specific_target_patches",
    ):
        if enabled.get(flag) is not False:
            raise RuntimeError(f"TC-big delimiter unsafe output flag {flag}={enabled.get(flag)!r}")

    with connect(database, readonly=True) as connection:
        persisted = get_run(connection, enabled_run_id)
        enabled_rows = get_run_items(connection, enabled_run_id, kind="translation_segment")
    _coverage(enabled_rows, content, label="TC-big delimiter enabled")
    inventory = _inventory(enabled_rows)
    if inventory["counts"] != ENABLED_COUNTS:
        raise RuntimeError(f"TC-big delimiter gate result drift: {inventory['counts']!r}")
    if len(enabled_rows) != ENABLED_SEGMENTS:
        raise RuntimeError("TC-big delimiter persisted segment-count drift")

    base_by_id = {int(row["id"]): row for row in base_rows}
    replaced_base_ids: set[int] = set()
    untouched = 0
    applied_cases: list[dict[str, Any]] = []
    for row in enabled_rows:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("tc_big_target_delimiter_rescue") or {})
        if rescue.get("contract") != TC_BIG_DELIMITER_RESCUE_CONTRACT:
            raise RuntimeError("TC-big delimiter row provenance contract drift")
        if rescue.get("selector_contract") != TC_BIG_DELIMITER_SELECTOR_CONTRACT:
            raise RuntimeError("TC-big delimiter row selector provenance drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
            "corpus_specific_target_patches",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"TC-big delimiter row violates {flag}=False")

        if rescue.get("applied") is not True:
            base_id = int(rescue["base_translation_segment_id"])
            base = base_by_id.get(base_id)
            if base is None or not _same_translation_row(row, base):
                raise RuntimeError("untouched TC-big delimiter row is not exact run-9 source/target/span")
            untouched += 1
            continue

        member_ids = [int(value) for value in rescue.get("base_translation_segment_ids") or []]
        if not member_ids:
            raise RuntimeError("TC-big delimiter applied row lacks base member IDs")
        if len(member_ids) != len(set(member_ids)):
            raise RuntimeError("TC-big delimiter applied row repeats a base member ID")
        if any(member_id in replaced_base_ids for member_id in member_ids):
            raise RuntimeError("TC-big delimiter base row replaced by more than one context")
        members = [base_by_id.get(member_id) for member_id in member_ids]
        if any(member is None for member in members):
            raise RuntimeError("TC-big delimiter applied row references unknown base member")
        members = sorted(members, key=lambda item: int(item["source_start"]))  # type: ignore[arg-type]
        source = "".join(str(member.get("source_text") or "") for member in members)
        if source != str(row.get("source_text") or ""):
            raise RuntimeError("TC-big delimiter applied source is not exact concatenated base source")
        if int(members[0]["source_start"]) != int(row["source_start"]) or int(members[-1]["source_end"]) != int(row["source_end"]):
            raise RuntimeError("TC-big delimiter applied source span differs from base-member envelope")
        hypotheses = list(payload.get("hypotheses") or [])
        rank = int(payload["selected_rank"])
        if rank < 0 or rank >= len(hypotheses):
            raise RuntimeError("TC-big delimiter selected rank outside persisted hypotheses")
        raw_target = str(hypotheses[rank].get("text") or "")
        if str(row.get("target_text") or "") != raw_target:
            raise RuntimeError("TC-big delimiter target is not exact raw selected hypothesis")
        selection = dict(rescue.get("selection") or {})
        if selection.get("accepted") is not True:
            raise RuntimeError("TC-big delimiter persisted selected hypothesis no longer records acceptance")
        if selection.get("strictly_eligible") is not True:
            raise RuntimeError("TC-big delimiter persisted selected hypothesis is not strict-clean")
        if (selection.get("emphasis_markup") or {}).get("passed") is not True:
            raise RuntimeError("TC-big delimiter persisted selected hypothesis loses emphasis shape")
        if selection.get("target_only_delimiter_additions"):
            raise RuntimeError("TC-big delimiter persisted selected hypothesis retains delimiter debt")
        if selection.get("source_alpha_ratio_passed") is not True:
            raise RuntimeError("TC-big delimiter persisted selected hypothesis violates source-relative completeness")
        replaced_base_ids.update(member_ids)
        applied_cases.append(
            {
                "context_sentence_start": int((payload.get("planner") or {})["context_sentence_start"]),
                "context_sentence_end": int((payload.get("planner") or {})["context_sentence_end"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "base_translation_segment_ids": member_ids,
                "base_targets": [str(member.get("target_text") or "") for member in members],
                "source_text": str(row.get("source_text") or ""),
                "selected_rank": rank,
                "selected_target": raw_target,
                "selection": selection,
            }
        )

    applied_cases.sort(key=lambda item: item["source_start"])
    if [case["source_start"] for case in applied_cases] != EXPECTED_ACCEPTED_STARTS:
        raise RuntimeError("TC-big delimiter persisted applied cohort drift")
    if len(replaced_base_ids) != EXPECTED_REPLACED_BASE_ROW_COUNT:
        raise RuntimeError(f"TC-big delimiter replaced-base count drift: {len(replaced_base_ids)}")
    if untouched != EXPECTED_UNTOUCHED_BASE_COUNT:
        raise RuntimeError(f"TC-big delimiter untouched base-exact count drift: {untouched}")
    if untouched + len(replaced_base_ids) != BASE_SEGMENTS:
        raise RuntimeError("TC-big delimiter base-row accounting is incomplete")

    with sqlite3.connect(database) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise RuntimeError(f"SQLite integrity drift: {integrity!r}, foreign_keys={foreign_keys[:10]!r}")

    final_database_sha256 = _sha(database)
    output_sha256 = str(persisted.get("output_sha256") or "")
    if not output_sha256:
        raise RuntimeError("persisted TC-big delimiter Stage12 run lacks output SHA")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off Product audit for TC-big target-only delimiter Stage10-context rescue",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "public_stage12_surface_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "persisted_database_sha256": final_database_sha256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "enabled_translation_run_id": enabled_run_id,
        "enabled_translation_output_sha256": output_sha256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_segment_count": BASE_SEGMENTS,
        "enabled_segment_count": len(enabled_rows),
        "base_hard_gate_counts": base_inventory["counts"],
        "enabled_hard_gate_counts": inventory["counts"],
        "attempted_source_starts": list(enabled.get("tc_big_target_delimiter_rescue_attempted_source_starts") or []),
        "accepted_source_starts": list(enabled.get("tc_big_target_delimiter_rescue_accepted_source_starts") or []),
        "selected_ranks": list(enabled.get("tc_big_target_delimiter_rescue_selected_ranks") or []),
        "selected_targets": list(enabled.get("tc_big_target_delimiter_rescue_selected_targets") or []),
        "replaced_base_row_count": len(replaced_base_ids),
        "untouched_base_exact_count": untouched,
        "source_coverage_byte_exact": True,
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violation_count": len(foreign_keys),
        "runtime": runtime,
        "asset": {
            "repository": asset.repository,
            "revision": asset.revision,
            "model_safetensors_sha256": asset.model_safetensors_sha256,
            "license": asset.license,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
        },
        "applied_cases": applied_cases,
        "feasibility": FEASIBILITY,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-tc-big-delimiter-product-rescue-optin.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "schema": SCHEMA,
        "base_run_id": BASE_RUN_ID,
        "enabled_run_id": enabled_run_id,
        "base_counts": base_inventory["counts"],
        "enabled_counts": inventory["counts"],
        "accepted_source_starts": evidence["accepted_source_starts"],
        "selected_ranks": evidence["selected_ranks"],
        "persisted_database_sha256": final_database_sha256,
        "enabled_output_sha256": output_sha256,
        "evidence_sha256": evidence["evidence_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
