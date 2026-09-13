from __future__ import annotations

"""Forensic public-Stage12 replay of run59 combined-Greek source-plan rescue.

The script persists a candidate run60 through the public Product Stage12 API.
A single replay never authorizes parent replacement; cross-runner agreement and
a later no-inference canonical verifier own that authority.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
from typing import Any

from rocketdict.api.operations import run_stage12 as run_product_stage12
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_combined_greek_rescue_stage import (
    BEAM_SIZE,
    COMBINED_GREEK_RESCUE_CONTRACT,
    COMBINED_GREEK_SELECTED_PHASE,
    COMBINED_GREEK_SELECTOR_CONTRACT,
    COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
    COMBINED_GREEK_TRIGGER_CONTRACT,
    MAX_DECODING_LENGTH,
    NUM_HYPOTHESES,
)

SCHEMA = "rocketdict-run59-combined-greek-public-replay/1"
BASE_RUN_ID = 59
PROMOTED_RUN_ID = 60
BASE_OUTPUT_SHA256 = "5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1"
BASE_PARAMETERS_SHA256 = "5b1ea478963221869b64ebca2c9a60f8e9838c41e4616b9b737aa648436b4878"
BASE_DATABASE_SHA256 = "41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_CONTEXT_RUN_ID = 2
EXPECTED_SOURCE_START = 301051
EXPECTED_SEQUENCE_NUMBER = 1753
EXPECTED_SEGMENT_COUNT = 3335
EXPECTED_TARGET_SHA256 = "c53660ded405267f6346d0611fa41edf4bfde8fb86155ca40289669c6c2a6f51"
EXPECTED_PREFIX_TARGET_SHA256 = "e8d5b27cd3ce22898f5d443aca5b578af85b5a67885e944607e9f10527c8bf7e"
EXPECTED_PREFIX_TOKENS_SHA256 = "bf1994714366cb1b57949a493932d4d1432c78dc089bcc7db2180189ea3fec7e"
EXPECTED_SUFFIX_TARGET_SHA256 = "603757cfe250ed5f95f8bec0f1c9649599a008e2cf8e7eb37853358b438d3086"
EXPECTED_SUFFIX_TOKENS_SHA256 = "1f95a6c89f8aa6a99d408d90862079f57cf4ddb4b71a0faeee1d2ea679805ae5"
EXPECTED_OPUS_REVISION = "opus-2020-02-11"
EXPECTED_OPUS_ARCHIVE_SHA256 = "798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677"
EXPECTED_OPUS_MANIFEST_SHA256 = "0c1720b41db19d262899133e400a94e2657b806affc1126cf8da8ca00569a001"
EXPECTED_OPUS_PAYLOAD_TREE_SHA256 = "35c5982497fadf88d1748a67f969d4fd8d3ed8babc3c9bc1141223dbfaf0f3ce"

COMBINED_KEYS = {
    "enable_combined_greek_source_plan_rescue",
    "combined_greek_source_plan_rescue_contract",
    "combined_greek_source_plan_selector_contract",
    "combined_greek_source_plan_trigger_contract",
    "combined_greek_source_plan_contract",
    "combined_greek_source_plan_rescue_phase",
}
SAFETY_FLAGS = (
    "source_bytes_rewritten",
    "model_input_source_rewritten",
    "target_rewriting",
    "placeholders",
    "post_translation_literal_injection",
    "corpus_specific_target_patches",
    "evaluator_weakened",
    "n_best_cherry_picking",
    "automatic_n_best_cherry_picking",
)


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _canonical_sha(value: Any) -> str:
    return _sha_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _host_identity() -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_arch": os.environ.get("RUNNER_ARCH"),
        "runner_name": os.environ.get("RUNNER_NAME"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_job": os.environ.get("GITHUB_JOB"),
        "github_sha": os.environ.get("GITHUB_SHA"),
    }
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        first: dict[str, str] = {}
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                if first:
                    break
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                first[key.strip()] = value.strip()
        result.update(
            {
                "cpu_vendor_id": first.get("vendor_id"),
                "cpu_model_name": first.get("model name"),
                "cpu_family": first.get("cpu family"),
                "cpu_model": first.get("model"),
                "cpu_stepping": first.get("stepping"),
            }
        )
    return result


def _write(root: Path, evidence: dict[str, Any]) -> None:
    canonical = dict(evidence)
    canonical.pop("evidence_sha256", None)
    evidence["evidence_sha256"] = _canonical_sha(canonical)
    path = root / "run59-combined-greek-public-replay.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"replay_evidence": evidence}, ensure_ascii=False, sort_keys=True))


def _assert_base(database: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if _sha_bytes(database.read_bytes()) != BASE_DATABASE_SHA256:
        raise RuntimeError("run59 canonical database SHA drift")
    with connect(database, readonly=True) as connection:
        base = get_run(connection, BASE_RUN_ID)
        output = dict(base.get("output") or {})
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(output["document_version_id"]))
    if str(base.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run59 output identity drift")
    if str(base.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("run59 parameters identity drift")
    identity = dict(base.get("input_identity") or {})
    if int(identity.get("context_run_id") or -1) != EXPECTED_CONTEXT_RUN_ID:
        raise RuntimeError(f"run59 context ancestry drift: {identity!r}")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run59 immutable source identity drift")
    if len(rows) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError("run59 segment cardinality drift")
    selected = rows[EXPECTED_SEQUENCE_NUMBER]
    if (
        int(selected["sequence_number"]) != EXPECTED_SEQUENCE_NUMBER
        or int(selected["source_start"]) != EXPECTED_SOURCE_START
    ):
        raise RuntimeError("run59 combined-Greek row identity drift")
    return base, rows, document


def _translated_piece(piece: dict[str, Any], role: str) -> dict[str, Any]:
    if piece.get("role") != role or piece.get("kind") != "translate":
        raise RuntimeError(f"{role} source-plan piece drift")
    hypothesis = dict(piece.get("hypothesis") or {})
    if int(piece.get("selected_rank", -1)) != 0 or int(hypothesis.get("rank", -1)) != 0:
        raise RuntimeError(f"{role} is not raw rank0")
    if piece.get("model_input") != piece.get("source_text"):
        raise RuntimeError(f"{role} model input differs from immutable planned source")
    if piece.get("selected_target") != hypothesis.get("text"):
        raise RuntimeError(f"{role} persisted selection differs from raw rank0")
    return hypothesis


def _run(root: Path, database: Path) -> dict[str, Any]:
    base, base_rows, document = _assert_base(database)
    base_parameters = dict(base.get("parameters") or {})
    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_combined_greek_source_plan_rescue": True,
            "combined_greek_source_plan_rescue_contract": COMBINED_GREEK_RESCUE_CONTRACT,
            "combined_greek_source_plan_selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
            "combined_greek_source_plan_trigger_contract": COMBINED_GREEK_TRIGGER_CONTRACT,
            "combined_greek_source_plan_contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
        }
    )
    promoted = run_product_stage12(
        database=database,
        context_run_id=EXPECTED_CONTEXT_RUN_ID,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    promoted_run_id = int(promoted["translation_run_id"])
    with connect(database, readonly=True) as connection:
        promoted_run = get_run(connection, promoted_run_id)
        promoted_rows = sorted(
            get_run_items(connection, promoted_run_id, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )

    if promoted_run_id != PROMOTED_RUN_ID:
        raise RuntimeError(
            f"exact cache ancestry lost: combined-Greek result is run {promoted_run_id}, expected {PROMOTED_RUN_ID}"
        )
    promoted_parameters = dict(promoted_run.get("parameters") or {})
    stripped_parameters = {
        key: value for key, value in promoted_parameters.items() if key not in COMBINED_KEYS
    }
    if stripped_parameters != base_parameters:
        raise RuntimeError("combined-Greek wrapper changed lower Stage12 parameters")
    if len(promoted_rows) != len(base_rows) or len(base_rows) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError("promoted segment cardinality drift")

    changed_sequences: list[int] = []
    unchanged_exact_count = 0
    for base_row, promoted_row in zip(base_rows, promoted_rows, strict=True):
        if (
            int(base_row["sequence_number"]) != int(promoted_row["sequence_number"])
            or int(base_row["source_start"]) != int(promoted_row["source_start"])
            or int(base_row["source_end"]) != int(promoted_row["source_end"])
            or str(base_row.get("source_text") or "") != str(promoted_row.get("source_text") or "")
        ):
            raise RuntimeError("run59/run60 immutable source-row ancestry drift")
        if str(base_row.get("target_text") or "") != str(promoted_row.get("target_text") or ""):
            changed_sequences.append(int(promoted_row["sequence_number"]))
        else:
            unchanged_exact_count += 1
    if changed_sequences != [EXPECTED_SEQUENCE_NUMBER]:
        raise RuntimeError(f"changed-target drift: {changed_sequences}")

    selected = promoted_rows[EXPECTED_SEQUENCE_NUMBER]
    target = str(selected.get("target_text") or "")
    if _sha_text(target) != EXPECTED_TARGET_SHA256:
        raise RuntimeError("promoted combined-Greek target differs from read-only DOE rank0 result")
    payload = dict(selected.get("payload") or {})
    rescue = dict(payload.get("combined_greek_source_plan_rescue") or {})
    if rescue.get("applied") is not True:
        raise RuntimeError("combined-Greek rescue was not persisted on selected row")
    if rescue.get("contract") != COMBINED_GREEK_RESCUE_CONTRACT:
        raise RuntimeError("combined-Greek rescue contract drift")
    if rescue.get("source_plan_contract") != COMBINED_GREEK_SOURCE_PLAN_CONTRACT:
        raise RuntimeError("combined-Greek source-plan contract drift")
    if int(rescue.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("selected row base-run ancestry drift")
    trigger = dict(rescue.get("trigger") or {})
    if trigger.get("corpus_sequence_whitelist") is not False or trigger.get("source_start_whitelist") is not False:
        raise RuntimeError("combined-Greek trigger became corpus-position specific")
    selection = dict(rescue.get("selection") or {})
    if selection.get("accepted") is not True:
        raise RuntimeError("persisted combined-Greek selector did not accept candidate")
    source_plan = dict(rescue.get("source_plan") or {})
    if (
        source_plan.get("contract") != COMBINED_GREEK_SOURCE_PLAN_CONTRACT
        or source_plan.get("created_before_mt") is not True
    ):
        raise RuntimeError("persisted source plan contract/order drift")
    pieces = list(source_plan.get("pieces") or [])
    if len(pieces) != 5 or [piece.get("role") for piece in pieces] != [
        "prefix",
        "left_separator",
        "technical_atom",
        "right_separator",
        "suffix",
    ]:
        raise RuntimeError("persisted combined-Greek source-plan piece order drift")
    if "".join(str(piece.get("source_text") or "") for piece in pieces) != str(selected.get("source_text") or ""):
        raise RuntimeError("combined-Greek planned source coverage is not byte-exact")
    for piece in pieces[1:4]:
        if (
            piece.get("kind") != "preserve_source_structure"
            or piece.get("source_owned") is not True
            or piece.get("rendered_text") != piece.get("source_text")
        ):
            raise RuntimeError(f"source-owned structural piece drift: {piece!r}")
    if str(pieces[2].get("source_text") or "") != "_A[Greek: a]_":
        raise RuntimeError("combined-Greek technical atom identity drift")
    prefix_h = _translated_piece(dict(pieces[0]), "prefix")
    suffix_h = _translated_piece(dict(pieces[4]), "suffix")
    if _sha_text(str(prefix_h.get("text") or "")) != EXPECTED_PREFIX_TARGET_SHA256:
        raise RuntimeError("prefix raw rank0 target SHA drift")
    if _canonical_sha(list(prefix_h.get("tokens") or [])) != EXPECTED_PREFIX_TOKENS_SHA256:
        raise RuntimeError("prefix raw rank0 token SHA drift")
    if _sha_text(str(suffix_h.get("text") or "")) != EXPECTED_SUFFIX_TARGET_SHA256:
        raise RuntimeError("suffix raw rank0 target SHA drift")
    if _canonical_sha(list(suffix_h.get("tokens") or [])) != EXPECTED_SUFFIX_TOKENS_SHA256:
        raise RuntimeError("suffix raw rank0 token SHA drift")

    runtime = dict(promoted.get("combined_greek_source_plan_rescue_runtime") or {})
    runtime_identity = dict(rescue.get("runtime_identity") or {})
    expected_runtime_identity = {
        "revision": EXPECTED_OPUS_REVISION,
        "source_archive_sha256": EXPECTED_OPUS_ARCHIVE_SHA256,
        "manifest_sha256": EXPECTED_OPUS_MANIFEST_SHA256,
        "payload_tree_sha256": EXPECTED_OPUS_PAYLOAD_TREE_SHA256,
        "compute_type": "float32",
    }
    if runtime_identity != expected_runtime_identity:
        raise RuntimeError(f"persisted OPUS runtime identity drift: {runtime_identity!r}")
    for key, expected in expected_runtime_identity.items():
        if runtime.get(key) != expected:
            raise RuntimeError(f"full OPUS runtime {key} drift: {runtime.get(key)!r}")

    source_exact = "".join(str(row.get("source_text") or "") for row in promoted_rows) == str(
        document["content_text"]
    )
    con = sqlite3.connect(database)
    integrity = str(con.execute("PRAGMA integrity_check").fetchone()[0])
    foreign_keys = len(con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()
    expected_generation = {
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "max_decoding_length": MAX_DECODING_LENGTH,
        "selected_rank": 0,
    }
    generation = dict(rescue.get("generation") or {})
    ready = bool(
        promoted.get("base_translation_run_id") == BASE_RUN_ID
        and promoted.get("base_translation_output_sha256") == BASE_OUTPUT_SHA256
        and promoted.get("combined_greek_source_plan_rescue_attempt_count") == 1
        and promoted.get("combined_greek_source_plan_rescue_accepted_count") == 1
        and promoted.get("combined_greek_source_plan_rescue_rejected_count") == 0
        and promoted.get("combined_greek_source_plan_rescue_attempted_source_starts")
        == [EXPECTED_SOURCE_START]
        and promoted.get("combined_greek_source_plan_rescue_accepted_source_starts")
        == [EXPECTED_SOURCE_START]
        and generation == expected_generation
        and changed_sequences == [EXPECTED_SEQUENCE_NUMBER]
        and unchanged_exact_count == EXPECTED_SEGMENT_COUNT - 1
        and source_exact
        and len(promoted_rows) == EXPECTED_SEGMENT_COUNT
        and integrity == "ok"
        and foreign_keys == 0
        and all(promoted.get(flag) is False for flag in SAFETY_FLAGS)
        and all(rescue.get(flag) is False for flag in SAFETY_FLAGS)
    )
    return {
        "schema": SCHEMA,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "parent_replacement_allowed": False,
        "replay_ready_for_aggregation": ready,
        "public_stage12_entrypoint": "rocketdict.api.operations.run_stage12",
        "repository_head_sha": os.environ.get("GITHUB_SHA"),
        "host": _host_identity(),
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_parameters_sha256": BASE_PARAMETERS_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "context_run_id": EXPECTED_CONTEXT_RUN_ID,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_start": EXPECTED_SOURCE_START,
        "sequence_number": EXPECTED_SEQUENCE_NUMBER,
        "rescue_contract": COMBINED_GREEK_RESCUE_CONTRACT,
        "rescue_phase": COMBINED_GREEK_SELECTED_PHASE,
        "selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
        "trigger_contract": COMBINED_GREEK_TRIGGER_CONTRACT,
        "source_plan_contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
        "attempt_count": promoted.get("combined_greek_source_plan_rescue_attempt_count"),
        "accepted_count": promoted.get("combined_greek_source_plan_rescue_accepted_count"),
        "rejected_count": promoted.get("combined_greek_source_plan_rescue_rejected_count"),
        "attempted_source_starts": promoted.get(
            "combined_greek_source_plan_rescue_attempted_source_starts"
        ),
        "accepted_source_starts": promoted.get(
            "combined_greek_source_plan_rescue_accepted_source_starts"
        ),
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": str(promoted_run.get("output_sha256") or ""),
        "promoted_parameters_sha256": str(promoted_run.get("parameters_sha256") or ""),
        "persisted_database_sha256": _sha_bytes(database.read_bytes()),
        "translation_segment_count": len(promoted_rows),
        "changed_target_sequences": changed_sequences,
        "unchanged_target_row_count": unchanged_exact_count,
        "source_coverage_byte_exact": source_exact,
        "candidate_target_sha256": _sha_text(target),
        "prefix_rank0_target_sha256": _sha_text(str(prefix_h.get("text") or "")),
        "prefix_rank0_tokens_sha256": _canonical_sha(list(prefix_h.get("tokens") or [])),
        "suffix_rank0_target_sha256": _sha_text(str(suffix_h.get("text") or "")),
        "suffix_rank0_tokens_sha256": _canonical_sha(list(suffix_h.get("tokens") or [])),
        "runtime_identity": runtime_identity,
        "generation": generation,
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violations": foreign_keys,
        **{flag: bool(promoted.get(flag)) for flag in SAFETY_FLAGS},
    }


def main() -> int:
    root = Path(os.environ["ROCKETDICT_COMBINED_GREEK_REPLAY_ROOT"]).resolve()
    database = Path(os.environ["ROCKETDICT_COMBINED_GREEK_REPLAY_DB"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        evidence = _run(root, database)
    except Exception as exc:
        evidence = {
            "schema": SCHEMA,
            "promotion_allowed": False,
            "automatic_product_default_allowed": False,
            "parent_replacement_allowed": False,
            "replay_ready_for_aggregation": False,
            "repository_head_sha": os.environ.get("GITHUB_SHA"),
            "host": _host_identity(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "persisted_database_sha256": _sha_bytes(database.read_bytes())
            if database.is_file()
            else None,
        }
    _write(root, evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
