from __future__ import annotations

"""Forensic public-Stage12 replay of the sole run58 M2M100 arithmetic case.

The script is intentionally diagnostic: selector rejection is recorded as data
instead of becoming an exception so workflow artifacts survive either verdict.
Promotion authority belongs to the separate cross-replica aggregator.
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
from rocketdict.translation_m2m100_arithmetic_rescue_stage import (
    BEAM_SIZE,
    MAX_DECODING_LENGTH,
    M2M100_ARITHMETIC_RESCUE_CONTRACT,
    M2M100_ARITHMETIC_SELECTED_PHASE,
    NUM_HYPOTHESES,
)
from rocketdict.translation_m2m100_arithmetic_rules import (
    M2M100_ARITHMETIC_SELECTOR_CONTRACT,
    M2M100_ARITHMETIC_TRIGGER_CONTRACT,
)

SCHEMA = "rocketdict-run58-m2m100-arithmetic-public-replay/1"
BASE_RUN_ID = 58
BASE_OUTPUT_SHA256 = "60349256eac118e9af7aa1366761342cd2041bb6ade4db04b45c78b46a8c6e5d"
BASE_PARAMETERS_SHA256 = "1cf60c7b582640c3923ea685ed329eb685a7b80e502e11507d99c752e6342315"
BASE_DATABASE_SHA256 = "a24f35d6f8bb4747a4fc301511f383b8b866846a3c448655fce1b9359cc0ac94"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SOURCE_START = 483234
EXPECTED_SEQUENCE_NUMBER = 2739
EXPECTED_TARGET_SHA256 = "258bc3a57d933b23317cf946af2f9e851fd266c6501a5b51813806b3294081d6"
EXPECTED_TOKENS_SHA256 = "599b77feba47448aff917fee3ea7d5e6e4a2c607378af906eaa63ca3ff37373d"
EXPECTED_CTRANSLATE2_VERSION = "4.8.2"

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
                key, val = line.split(":", 1)
                first[key.strip()] = val.strip()
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
    path = root / "run58-m2m100-arithmetic-public-replay.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"replay_evidence": evidence}, ensure_ascii=False, sort_keys=True))


def _extract_raw(
    *,
    promoted: dict[str, Any],
    promoted_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted = int(promoted.get("m2m100_arithmetic_rescue_accepted_count") or 0)
    rejected = int(promoted.get("m2m100_arithmetic_rescue_rejected_count") or 0)
    if accepted == 1 and rejected == 0:
        matches = [
            row
            for row in promoted_rows
            if int(row.get("source_start") or -1) == EXPECTED_SOURCE_START
        ]
        if len(matches) != 1:
            raise RuntimeError("accepted arithmetic row cardinality drift")
        payload = dict(matches[0].get("payload") or {})
        rescue = dict(payload.get("m2m100_arithmetic_rescue") or {})
        hypotheses = list(payload.get("hypotheses") or [])
        if len(hypotheses) != 1 or int(hypotheses[0].get("rank", -1)) != 0:
            raise RuntimeError("accepted raw rank0 provenance drift")
        hypothesis = dict(hypotheses[0])
        return {
            "verdict": "accepted",
            "rank0_target": str(hypothesis.get("text") or ""),
            "rank0_tokens": list(hypothesis.get("tokens") or []),
            "rank0_score": hypothesis.get("score"),
            "selection": dict(rescue.get("selection") or {}),
            "trigger": dict(rescue.get("trigger") or {}),
            "generation": dict(rescue.get("generation") or {}),
            "runtime_identity": dict(rescue.get("runtime_identity") or {}),
            "raw_model_selected": rescue.get("raw_model_selected"),
            "raw_model_rank": rescue.get("raw_model_rank"),
        }
    if accepted == 0 and rejected == 1:
        rows = list(promoted.get("m2m100_arithmetic_rescue_rejected") or [])
        if len(rows) != 1:
            raise RuntimeError("rejected arithmetic evidence cardinality drift")
        row = dict(rows[0])
        return {
            "verdict": "rejected",
            "rank0_target": str(row.get("rank0_target") or ""),
            "rank0_tokens": list(row.get("rank0_tokens") or []),
            "rank0_score": row.get("rank0_score"),
            "selection": dict(row.get("selection") or {}),
            "trigger": dict(row.get("trigger") or {}),
            "generation": dict(row.get("generation") or {}),
            "runtime_identity": dict(row.get("runtime_identity") or {}),
            "raw_model_selected": False,
            "raw_model_rank": 0,
        }
    raise RuntimeError(
        f"unexpected arithmetic verdict cardinality: accepted={accepted} rejected={rejected}"
    )


def _run(root: Path, database: Path) -> dict[str, Any]:
    initial_db_sha = _sha_bytes(database.read_bytes())
    if initial_db_sha != BASE_DATABASE_SHA256:
        raise RuntimeError(f"run58 DB identity drift: {initial_db_sha}")

    with connect(database, readonly=True) as connection:
        base = get_run(connection, BASE_RUN_ID)
        base_output = dict(base.get("output") or {})
        base_rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run58 output identity drift")
    if str(base.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("run58 parameters identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run58 source identity drift")
    base_matches = [
        row for row in base_rows if int(row.get("source_start") or -1) == EXPECTED_SOURCE_START
    ]
    if len(base_matches) != 1:
        raise RuntimeError("run58 arithmetic row cardinality drift")
    if int(base_matches[0].get("sequence_number") or -1) != EXPECTED_SEQUENCE_NUMBER:
        raise RuntimeError("run58 arithmetic sequence identity drift")

    parameters = dict(base.get("parameters") or {})
    parameters.update(
        {
            "enable_m2m100_arithmetic_rescue": True,
            "m2m100_arithmetic_rescue_contract": M2M100_ARITHMETIC_RESCUE_CONTRACT,
            "m2m100_arithmetic_selector_contract": M2M100_ARITHMETIC_SELECTOR_CONTRACT,
            "m2m100_arithmetic_trigger_contract": M2M100_ARITHMETIC_TRIGGER_CONTRACT,
        }
    )
    promoted = run_product_stage12(
        database=database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    promoted_run_id = int(promoted["translation_run_id"])
    with connect(database, readonly=True) as connection:
        promoted_run = get_run(connection, promoted_run_id)
        promoted_rows = get_run_items(connection, promoted_run_id, kind="translation_segment")

    raw = _extract_raw(promoted=promoted, promoted_rows=promoted_rows)
    raw_target = str(raw["rank0_target"])
    raw_tokens = list(raw["rank0_tokens"])
    runtime = dict(promoted.get("m2m100_arithmetic_rescue_runtime") or {})

    base_by_start = {
        int(row["source_start"]): str(row.get("target_text") or "") for row in base_rows
    }
    changed_sequences = [
        int(row["sequence_number"])
        for row in promoted_rows
        if str(row.get("target_text") or "")
        != base_by_start.get(int(row["source_start"]), "")
    ]
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
    }
    replay_ready = bool(
        promoted.get("base_translation_run_id") == BASE_RUN_ID
        and promoted.get("base_translation_output_sha256") == BASE_OUTPUT_SHA256
        and promoted.get("m2m100_arithmetic_rescue_attempt_count") == 1
        and promoted.get("m2m100_arithmetic_rescue_attempted_source_starts")
        == [EXPECTED_SOURCE_START]
        and raw["verdict"] == "accepted"
        and raw.get("raw_model_selected") is True
        and raw.get("raw_model_rank") == 0
        and raw_target
        and raw_tokens
        and _sha_text(raw_target) == EXPECTED_TARGET_SHA256
        and _canonical_sha(raw_tokens) == EXPECTED_TOKENS_SHA256
        and raw.get("generation") == expected_generation
        and raw.get("runtime_identity", {}).get("ctranslate2_version")
        == EXPECTED_CTRANSLATE2_VERSION
        and runtime.get("ctranslate2_version") == EXPECTED_CTRANSLATE2_VERSION
        and runtime.get("ctranslate2_version_matches") is True
        and raw.get("selection", {}).get("accepted") is True
        and changed_sequences == [EXPECTED_SEQUENCE_NUMBER]
        and source_exact
        and len(promoted_rows) == len(base_rows) == 3335
        and integrity == "ok"
        and foreign_keys == 0
        and all(promoted.get(flag) is False for flag in SAFETY_FLAGS)
    )

    return {
        "schema": SCHEMA,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "replay_ready_for_aggregation": replay_ready,
        "public_stage12_entrypoint": "rocketdict.api.operations.run_stage12",
        "repository_head_sha": os.environ.get("GITHUB_SHA"),
        "host": _host_identity(),
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_parameters_sha256": BASE_PARAMETERS_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_start": EXPECTED_SOURCE_START,
        "sequence_number": EXPECTED_SEQUENCE_NUMBER,
        "rescue_contract": M2M100_ARITHMETIC_RESCUE_CONTRACT,
        "rescue_phase": M2M100_ARITHMETIC_SELECTED_PHASE,
        "selector_contract": M2M100_ARITHMETIC_SELECTOR_CONTRACT,
        "trigger_contract": M2M100_ARITHMETIC_TRIGGER_CONTRACT,
        "attempt_count": promoted.get("m2m100_arithmetic_rescue_attempt_count"),
        "accepted_count": promoted.get("m2m100_arithmetic_rescue_accepted_count"),
        "rejected_count": promoted.get("m2m100_arithmetic_rescue_rejected_count"),
        "attempted_source_starts": promoted.get(
            "m2m100_arithmetic_rescue_attempted_source_starts"
        ),
        "accepted_source_starts": promoted.get(
            "m2m100_arithmetic_rescue_accepted_source_starts"
        ),
        "raw_rank0": raw,
        "rank0_target_sha256": _sha_text(raw_target) if raw_target else None,
        "rank0_tokens_sha256": _canonical_sha(raw_tokens) if raw_tokens else None,
        "runtime": runtime,
        "generation": expected_generation,
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": str(promoted_run.get("output_sha256") or ""),
        "promoted_parameters_sha256": str(promoted_run.get("parameters_sha256") or ""),
        "persisted_database_sha256": _sha_bytes(database.read_bytes()),
        "translation_segment_count": len(promoted_rows),
        "changed_target_sequences": changed_sequences,
        "source_coverage_exact": source_exact,
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violations": foreign_keys,
        **{flag: bool(promoted.get(flag)) for flag in SAFETY_FLAGS},
    }


def main() -> int:
    root = Path(os.environ["ROCKETDICT_M2M100_ARITHMETIC_REPLAY_ROOT"]).resolve()
    database = Path(os.environ["ROCKETDICT_M2M100_ARITHMETIC_REPLAY_DB"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        evidence = _run(root, database)
    except Exception as exc:
        evidence = {
            "schema": SCHEMA,
            "promotion_allowed": False,
            "automatic_product_default_allowed": False,
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
