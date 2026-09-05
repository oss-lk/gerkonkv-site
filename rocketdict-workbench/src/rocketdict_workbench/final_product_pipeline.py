from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .product_profile import PREFERRED_IMPLEMENTATIONS
from .quality_gate_execution import require_quality_gate_pass
from .unified_stage20 import _load_artifact
from .upstream_binding import _canonical_sha256, _load_verified_evidence, _operation_rows, _valid_sha256
from .upstream_pipeline import (
    EXECUTION_CONTRACT_ATTRIBUTE,
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    TRANSPORT,
    _OPERATION_CONTRACT_PROBE,
    _validate_result,
)

FINAL_PIPELINE_SCHEMA = "rocketdict-workbench-final-product-pipeline/1"
FINAL_STAGE_BINDING_SCHEMA = "rocketdict-workbench-final-stage-binding/1"
FINAL_STAGE_PROOF_SCHEMA = "rocketdict-workbench-final-stage-proof/1"
FINAL_STAGE_EXECUTION_SCHEMA = "rocketdict-workbench-final-stage-execution/1"
CARD_JOURNAL_SCHEMA = "rocketdict-workbench-stage24-card-journal/1"
SET_ASSEMBLY_DISCOVERY_SCHEMA = "rocketdict-workbench-card-set-assembly-discovery/1"
SET_ASSEMBLY_BINDING_SCHEMA = "rocketdict-workbench-card-set-assembly-binding/1"
SET_ASSEMBLY_EXECUTION_SCHEMA = "rocketdict-workbench-card-set-assembly-execution/1"
FINAL_CORE_STAGES = (24, 25)
DEFAULT_SET_NAME = "RocketDict Product output"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _profile_stage(preflight: dict[str, Any], stage_number: int) -> dict[str, Any]:
    row = (((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number)))
    if not isinstance(row, dict):
        raise RuntimeError(
            f"Product profile has no Stage {stage_number}; final Product output cannot be fabricated from an unavailable stage"
        )
    if int(row.get("stage_number") or 0) != stage_number:
        raise RuntimeError(f"Product Stage {stage_number} profile stage_number drift")
    preferred = PREFERRED_IMPLEMENTATIONS.get(stage_number)
    if preferred and str(row.get("implementation") or "") != preferred:
        raise RuntimeError(
            f"Product Stage {stage_number} selected {row.get('implementation')!r}, expected pinned preference {preferred!r}"
        )
    availability = row.get("availability")
    if not isinstance(availability, dict) or availability.get("available") is not True:
        raise RuntimeError(f"Product Stage {stage_number} is not locally available: {availability}")
    descriptor = str(row.get("adapter_descriptor_hash") or "").casefold()
    if not _valid_sha256(descriptor):
        raise RuntimeError(f"Product Stage {stage_number} lacks SHA-256 adapter descriptor identity")
    required = row.get("required_inputs")
    if not isinstance(required, list) or any(not isinstance(name, str) or not name for name in required):
        raise RuntimeError(f"Product Stage {stage_number} lacks valid live required_inputs")
    if len(set(required)) != len(required):
        raise RuntimeError(f"Product Stage {stage_number} has duplicate required_inputs")
    return dict(row)


def _expected_stage_contract(preflight: dict[str, Any], stage_number: int) -> dict[str, Any]:
    profile = _profile_stage(preflight, stage_number)
    expected = {
        "stage_number": stage_number,
        "stage_key": str(profile.get("stage_key") or ""),
        "implementation": str(profile.get("implementation") or ""),
        "adapter_descriptor_hash": str(profile.get("adapter_descriptor_hash") or "").casefold(),
        "parameters": dict(profile.get("parameters") or {}),
        "required_inputs": list(profile.get("required_inputs") or []),
    }
    if not expected["stage_key"] or not expected["implementation"]:
        raise RuntimeError(f"Product Stage {stage_number} lacks stage/implementation identity")
    expected["parameters_sha256"] = _canonical_sha256(expected["parameters"])
    expected["execution_contract_sha256"] = _canonical_sha256(
        {
            "stage_number": stage_number,
            "stage_key": expected["stage_key"],
            "implementation": expected["implementation"],
            "adapter_descriptor_hash": expected["adapter_descriptor_hash"],
            "parameters": expected["parameters"],
            "required_inputs": expected["required_inputs"],
        }
    )
    return expected


def _evaluate_callable(row: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    reasons = []
    if not str(row.get("operation") or ""):
        reasons.append("missing_operation_key")
    if not _valid_sha256(row.get("source_sha256")):
        reasons.append("missing_callable_source_sha256")
    metadata = row.get("binding_metadata")
    if not isinstance(metadata, dict):
        reasons.append("missing_binding_metadata")
        return reasons
    if int(metadata.get("stage_number") or 0) != expected["stage_number"]:
        reasons.append("stage_number_mismatch")
    if str(metadata.get("stage_key") or "") != expected["stage_key"]:
        reasons.append("stage_key_mismatch")
    if str(metadata.get("implementation_key") or "") != expected["implementation"]:
        reasons.append("implementation_mismatch")
    descriptor = metadata.get("adapter_descriptor_hash", metadata.get("descriptor_hash"))
    if str(descriptor or "").casefold() != expected["adapter_descriptor_hash"]:
        reasons.append("adapter_descriptor_hash_mismatch")
    required = metadata.get("required_inputs")
    if not isinstance(required, list) or list(required) != expected["required_inputs"]:
        reasons.append("required_inputs_mismatch")
    return reasons


def _unique_stage_callable(probe: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    exact = []
    diagnostics = []
    for row in _operation_rows(probe):
        reasons = _evaluate_callable(row, expected)
        diagnostics.append({"operation": row.get("operation"), "mismatch_reasons": reasons})
        if not reasons:
            exact.append(row)
    if len(exact) != 1:
        raise RuntimeError(
            f"Product Stage {expected['stage_number']} requires exactly one exact structured callable; observed {len(exact)}; diagnostics={diagnostics}"
        )
    return dict(exact[0])


def _stage23_lineage(state: dict[str, Any]) -> dict[str, Any]:
    step = (state.get("steps") or {}).get("stage20_downstream") or {}
    if step.get("status") != "completed_through_stage23":
        raise RuntimeError("Stage24 requires completed unified Product Stage20-through-Stage23")
    provider_ref = (step.get("provider") or {}).get("artifact")
    stage20_ref = (step.get("stage20") or {}).get("artifact")
    provider = _load_artifact(provider_ref, context="Stage24 provider lineage")
    stage20 = _load_artifact(stage20_ref, context="Stage24 Stage20 lineage")
    rows = list(stage20.get("results") or [])
    sense_ids = [int(row.get("sense_id") or 0) for row in rows]
    if not sense_ids or any(value <= 0 for value in sense_ids) or len(set(sense_ids)) != len(sense_ids):
        raise RuntimeError("Stage24 lineage has invalid/duplicate Stage20 lexical_sense_ids")
    downstream = step.get("stage20_through_stage23") or {}
    runner_path = Path(str(downstream.get("runner_state_path") or "")).expanduser().resolve()
    if not runner_path.is_file():
        raise RuntimeError("Stage24 downstream runner state is missing")
    runner_sha = str(downstream.get("runner_state_sha256") or "").casefold()
    if not _valid_sha256(runner_sha):
        raise RuntimeError("Stage24 downstream runner state lacks SHA-256")
    actual = _file_sha256(runner_path)
    if actual != runner_sha:
        raise RuntimeError("Stage24 downstream runner state bytes were mutated")
    return {
        "sense_ids": sense_ids,
        "sense_ids_sha256": _canonical_sha256(sense_ids),
        "provider_entries_sha256": str(provider.get("entries_sha256") or "").casefold(),
        "stage20_artifact_sha256": str(stage20_ref.get("sha256") or "").casefold(),
        "stage23_runner_state_path": str(runner_path),
        "stage23_runner_state_sha256": runner_sha,
        "stage23_runner_input_fingerprint": str(downstream.get("runner_input_fingerprint") or ""),
    }


def _file_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _binding(
    state: dict[str, Any],
    preflight: dict[str, Any],
    probe: dict[str, Any],
    stage_number: int,
    *,
    lineage_fingerprint: str,
) -> dict[str, Any]:
    expected = _expected_stage_contract(preflight, stage_number)
    row = _unique_stage_callable(probe, expected)
    binding = {
        "schema": FINAL_STAGE_BINDING_SCHEMA,
        "stage_number": stage_number,
        "stage_key": expected["stage_key"],
        "implementation": expected["implementation"],
        "adapter_descriptor_hash": expected["adapter_descriptor_hash"],
        "parameters_sha256": expected["parameters_sha256"],
        "required_inputs": expected["required_inputs"],
        "execution_contract_sha256": expected["execution_contract_sha256"],
        "lineage_fingerprint": lineage_fingerprint,
        "operation": str(row["operation"]),
        "callable": {
            "mapping_module": row.get("mapping_module"),
            "mapping_name": row.get("mapping_name"),
            "module": row.get("callable_module"),
            "qualname": row.get("callable_qualname"),
            "source_sha256": str(row.get("source_sha256") or "").casefold(),
        },
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "product_run_root_fingerprint": str((state.get("root_identity") or {}).get("fingerprint") or "").casefold(),
    }
    binding["fingerprint"] = _canonical_sha256(binding)
    return binding


def _probe_execution_contract(
    core: RocketDictCore,
    database: Path,
    binding: dict[str, Any],
    stage_number: int,
) -> dict[str, Any]:
    callable_row = binding["callable"]
    raw = core._run(
        [
            "-c",
            _OPERATION_CONTRACT_PROBE,
            str(callable_row.get("mapping_module") or ""),
            str(callable_row.get("mapping_name") or ""),
            str(binding["operation"]),
            str(database),
            EXECUTION_CONTRACT_ATTRIBUTE,
        ],
        timeout=120,
    )
    payload = core._parse_json(raw.stdout, context=f"Stage {stage_number} final execution-contract probe")
    if not isinstance(payload, dict) or payload.get("schema") != "rocketdict-workbench-operation-contract-probe/1":
        raise RuntimeError(f"Unexpected Stage {stage_number} execution-contract probe")
    expected_identity = {
        "mapping_module": str(callable_row.get("mapping_module") or ""),
        "mapping_name": str(callable_row.get("mapping_name") or ""),
        "operation": str(binding["operation"]),
        "callable_module": str(callable_row.get("module") or ""),
        "callable_qualname": str(callable_row.get("qualname") or ""),
        "callable_source_sha256": str(callable_row.get("source_sha256") or "").casefold(),
        "contract_attribute": EXECUTION_CONTRACT_ATTRIBUTE,
    }
    for key, value in expected_identity.items():
        if str(payload.get(key) or "").casefold() != str(value).casefold():
            raise RuntimeError(f"Stage {stage_number} callable identity drift during contract probe: {key}")
    contract = payload.get("contract")
    if not isinstance(contract, dict) or contract.get("schema") != PUBLIC_EXECUTION_CONTRACT_SCHEMA:
        raise RuntimeError(f"Stage {stage_number} callable does not publish current public execution contract")
    if contract.get("transport") != TRANSPORT or not isinstance(contract.get("replay_safe"), bool):
        raise RuntimeError(f"Stage {stage_number} execution contract has invalid transport/replay policy")
    request = contract.get("request")
    result = contract.get("result")
    if not isinstance(request, dict) or set(request) != {"params"} or not isinstance(request.get("params"), dict):
        raise RuntimeError(f"Stage {stage_number} execution request contract is invalid")
    params = request["params"]
    allowed = {f"input:{name}" for name in binding["required_inputs"]} | {
        "profile:parameters",
        "binding:implementation",
        "binding:stage_number",
        "binding:stage_key",
    }
    if any(not isinstance(value, str) or value not in allowed for value in params.values()):
        raise RuntimeError(f"Stage {stage_number} execution request uses unsupported sources")
    used_inputs = sorted(value.removeprefix("input:") for value in params.values() if value.startswith("input:"))
    if sorted(binding["required_inputs"]) != used_inputs:
        raise RuntimeError(f"Stage {stage_number} execution contract does not consume exact frozen required_inputs")
    if not isinstance(result, dict) or set(result) != {"required_fields", "identity_fields", "schema_field", "schema_values"}:
        raise RuntimeError(f"Stage {stage_number} execution result contract is invalid")
    required_fields = result["required_fields"]
    identity_fields = result["identity_fields"]
    schema_values = result["schema_values"]
    if not isinstance(required_fields, list) or not isinstance(identity_fields, list) or not isinstance(schema_values, list):
        raise RuntimeError(f"Stage {stage_number} result contract lists are invalid")
    if not identity_fields or any(field not in required_fields for field in identity_fields):
        raise RuntimeError(f"Stage {stage_number} identity fields are not required result fields")
    if not isinstance(result.get("schema_field"), str) or not result["schema_field"] or not schema_values:
        raise RuntimeError(f"Stage {stage_number} result schema contract is incomplete")
    return contract


def _render_request(
    binding: dict[str, Any],
    contract: dict[str, Any],
    profile: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    params = {}
    for key, source in contract["request"]["params"].items():
        if source.startswith("input:"):
            name = source.removeprefix("input:")
            if name not in inputs:
                raise RuntimeError(f"Final stage request references unavailable exact input {name!r}")
            params[key] = inputs[name]
        elif source == "profile:parameters":
            params[key] = dict(profile.get("parameters") or {})
        elif source == "binding:implementation":
            params[key] = binding["implementation"]
        elif source == "binding:stage_number":
            params[key] = binding["stage_number"]
        elif source == "binding:stage_key":
            params[key] = binding["stage_key"]
        else:
            raise RuntimeError(f"Unsupported final stage request source {source!r}")
    return params


def _journal_paths(state_path: Path) -> tuple[Path, Path]:
    root = state_path.parent / f"{state_path.stem}.artifacts"
    return root / "stage24-cards.jsonl", root / "stage24-cards-manifest.json"


def _journal_line_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k != "record_sha256"}


def _append_journal(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(record)
    record["record_sha256"] = _canonical_sha256(_journal_line_payload(record))
    data = (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    with path.open("ab") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


def _read_journal(path: Path, expected_sense_ids: list[int]) -> tuple[list[dict[str, Any]], str | None]:
    if not path.is_file():
        return [], None
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    records = []
    previous_sha = None
    seen = set()
    for index, line in enumerate(lines):
        if not line.endswith(b"\n"):
            # The sole incomplete tail is ignored: no durable success was committed for it.
            if index != len(lines) - 1:
                raise RuntimeError("Stage24 card journal has non-tail truncated record")
            break
        try:
            record = json.loads(line.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Stage24 card journal line {index + 1} is invalid JSON") from exc
        if not isinstance(record, dict) or record.get("schema") != CARD_JOURNAL_SCHEMA:
            raise RuntimeError(f"Stage24 card journal line {index + 1} schema drift")
        sha = str(record.get("record_sha256") or "").casefold()
        if not _valid_sha256(sha) or sha != _canonical_sha256(_journal_line_payload(record)):
            raise RuntimeError(f"Stage24 card journal line {index + 1} hash mismatch")
        if record.get("previous_record_sha256") != previous_sha:
            raise RuntimeError(f"Stage24 card journal line {index + 1} hash chain mismatch")
        sense_id = int(record.get("lexical_sense_id") or 0)
        if sense_id not in expected_sense_ids or sense_id in seen:
            raise RuntimeError(f"Stage24 card journal has unexpected/duplicate lexical_sense_id {sense_id}")
        result = record.get("result")
        if not isinstance(result, dict) or record.get("result_sha256") != _canonical_sha256(result):
            raise RuntimeError(f"Stage24 card journal result for sense {sense_id} was mutated")
        card_revision_id = record.get("card_revision_id")
        if isinstance(card_revision_id, bool) or not isinstance(card_revision_id, int) or card_revision_id <= 0:
            raise RuntimeError(f"Stage24 card journal sense {sense_id} lacks positive card_revision_id")
        if result.get("card_revision_id") != card_revision_id:
            raise RuntimeError(f"Stage24 card_revision_id for sense {sense_id} is not backed by hashed result")
        records.append(record)
        seen.add(sense_id)
        previous_sha = sha
    expected_prefix = expected_sense_ids[: len(records)]
    actual = [int(record["lexical_sense_id"]) for record in records]
    if actual != expected_prefix:
        raise RuntimeError(f"Stage24 card journal order/coverage drift: {actual[:10]} != {expected_prefix[:10]}")
    return records, previous_sha


def _stage24_context(
    state_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    state, preflight, probe = _load_verified_evidence(state_path)
    pass_evidence = require_quality_gate_pass(state_path)
    lineage = _stage23_lineage(state)
    profile = _profile_stage(preflight, 24)
    if profile["required_inputs"] != ["lexical_sense_id"]:
        raise RuntimeError(
            f"Current Stage24 live contract is not the supported exact fan-out contract ['lexical_sense_id']: {profile['required_inputs']}"
        )
    lineage_fingerprint = _canonical_sha256(
        {
            "stage15_pass_fingerprint": pass_evidence["fingerprint"],
            "stage23": lineage,
            "profile_sha256": str((preflight.get("identity") or {}).get("profile_sha256") or "").casefold(),
        }
    )
    binding = _binding(state, preflight, probe, 24, lineage_fingerprint=lineage_fingerprint)
    return state, preflight, probe, lineage, profile, binding


def execute_stage24_cards(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    max_new_cards: int | None = None,
) -> dict[str, Any]:
    if max_new_cards is not None and max_new_cards <= 0:
        raise ValueError("max_new_cards must be positive")
    state_path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe, lineage, profile, binding = _stage24_context(state_path)
    probe_db = Path(str((probe.get("database") or {}).get("path") or "")).expanduser().resolve()
    if probe_db != database_path:
        raise RuntimeError("Stage24 database differs from immutable API probe database")
    contract = _probe_execution_contract(core, database_path, binding, 24)
    if "card_revision_id" not in contract["result"]["identity_fields"]:
        raise RuntimeError("Stage24 public result contract does not expose card_revision_id as durable identity")
    journal_path, manifest_path = _journal_paths(state_path)
    records, previous_sha = _read_journal(journal_path, lineage["sense_ids"])
    completed = {int(record["lexical_sense_id"]): record for record in records}
    final_step = state["steps"]["cards"]
    input_identity = {
        "stage24_binding_fingerprint": binding["fingerprint"],
        "execution_contract_sha256": _canonical_sha256(contract),
        "stage23_lineage": lineage,
    }
    input_identity["fingerprint"] = _canonical_sha256(input_identity)
    existing = final_step.get("input_identity")
    if existing is not None and (not isinstance(existing, dict) or existing.get("fingerprint") != input_identity["fingerprint"]):
        raise RuntimeError("Stage24 state belongs to different immutable Stage23/binding inputs")
    final_step["input_identity"] = input_identity
    inflight = final_step.get("inflight")
    if isinstance(inflight, dict):
        sense_id = int(inflight.get("lexical_sense_id") or 0)
        if sense_id not in completed:
            if not contract["replay_safe"]:
                raise RuntimeError(
                    f"Stage24 sense {sense_id} may have mutated the database and public contract is not replay-safe; manual reconciliation required"
                )
        final_step.pop("inflight", None)
    new_count = 0
    for sense_id in lineage["sense_ids"]:
        if sense_id in completed:
            continue
        if max_new_cards is not None and new_count >= max_new_cards:
            break
        params = _render_request(binding, contract, profile, {"lexical_sense_id": sense_id})
        request = {"transport": TRANSPORT, "operation": binding["operation"], "params": params}
        final_step["status"] = "running"
        final_step["inflight"] = {
            "lexical_sense_id": sense_id,
            "request_sha256": _canonical_sha256(request),
            "replay_safe": contract["replay_safe"],
            "started_at": _now(),
        }
        state["status"] = "executing_stage24_cards"
        _save_state(state_path, state)
        params_json = json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        try:
            raw = core.api(database_path, "call", binding["operation"], "--params", params_json, timeout=1800)
            result, identities = _validate_result(raw, contract, 24)
        except Exception as exc:
            final_step["status"] = "ambiguous_failure"
            final_step["error"] = {"type": type(exc).__name__, "message": str(exc)}
            final_step["blocked_reason"] = (
                "retry_explicitly_allowed_by_verified_public_contract"
                if contract["replay_safe"]
                else "manual_reconciliation_required_before_stage24_replay"
            )
            state["status"] = "failed"
            _save_state(state_path, state)
            raise
        card_revision_id = identities.get("card_revision_id")
        if isinstance(card_revision_id, bool) or not isinstance(card_revision_id, int) or card_revision_id <= 0:
            raise RuntimeError(f"Stage24 sense {sense_id} returned invalid card_revision_id")
        journal_record = {
            "schema": CARD_JOURNAL_SCHEMA,
            "lexical_sense_id": sense_id,
            "previous_record_sha256": previous_sha,
            "request_sha256": _canonical_sha256(request),
            "result": result,
            "result_sha256": _canonical_sha256(result),
            "card_revision_id": card_revision_id,
            "completed_at": _now(),
        }
        _append_journal(journal_path, journal_record)
        records, previous_sha = _read_journal(journal_path, lineage["sense_ids"])
        completed[sense_id] = records[-1]
        final_step.pop("inflight", None)
        final_step.pop("error", None)
        final_step["completed_card_count"] = len(records)
        final_step["expected_card_count"] = len(lineage["sense_ids"])
        _save_state(state_path, state)
        new_count += 1

    records, last_sha = _read_journal(journal_path, lineage["sense_ids"])
    complete = len(records) == len(lineage["sense_ids"])
    manifest = {
        "schema": "rocketdict-workbench-stage24-card-manifest/1",
        "input_fingerprint": input_identity["fingerprint"],
        "journal_path": str(journal_path),
        "journal_sha256": _file_sha256(journal_path) if journal_path.is_file() else None,
        "last_record_sha256": last_sha,
        "expected_sense_ids_sha256": lineage["sense_ids_sha256"],
        "expected_card_count": len(lineage["sense_ids"]),
        "completed_card_count": len(records),
        "card_revision_ids": [int(record["card_revision_id"]) for record in records],
        "complete": complete,
    }
    manifest["fingerprint"] = _canonical_sha256(manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(manifest_path)
    final_step["manifest_path"] = str(manifest_path)
    final_step["manifest_sha256"] = _file_sha256(manifest_path)
    final_step["status"] = "cards_complete_awaiting_set_assembly" if complete else "partial"
    state["status"] = "stage24_cards_complete_awaiting_set_assembly" if complete else "stage24_cards_partial"
    _save_state(state_path, state)
    return {
        "schema": FINAL_PIPELINE_SCHEMA,
        "status": final_step["status"],
        "completed_now": new_count,
        "completed_card_count": len(records),
        "expected_card_count": len(lineage["sense_ids"]),
        "manifest": manifest,
        "state_path": str(state_path),
    }


def _load_complete_card_manifest(state_path: Path, state: dict[str, Any]) -> dict[str, Any]:
    step = (state.get("steps") or {}).get("cards") or {}
    path = Path(str(step.get("manifest_path") or "")).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError("Stage24 complete card manifest is missing")
    if str(step.get("manifest_sha256") or "").casefold() != _file_sha256(path):
        raise RuntimeError("Stage24 card manifest bytes were mutated")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("complete") is not True:
        raise RuntimeError("Stage24 card manifest is incomplete")
    fp = str(manifest.get("fingerprint") or "").casefold()
    if not _valid_sha256(fp) or fp != _canonical_sha256({k: v for k, v in manifest.items() if k != "fingerprint"}):
        raise RuntimeError("Stage24 card manifest fingerprint mismatch")
    journal_path = Path(str(manifest.get("journal_path") or "")).expanduser().resolve()
    if not journal_path.is_file() or str(manifest.get("journal_sha256") or "").casefold() != _file_sha256(journal_path):
        raise RuntimeError("Stage24 card journal bytes changed after manifest completion")
    card_ids = manifest.get("card_revision_ids")
    if not isinstance(card_ids, list) or not card_ids or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in card_ids):
        raise RuntimeError("Stage24 complete manifest has invalid card_revision_ids")
    return manifest


def _probe_generic_contract(
    core: RocketDictCore,
    database: Path,
    row: dict[str, Any],
) -> dict[str, Any] | None:
    if not _valid_sha256(row.get("source_sha256")):
        return None
    raw = core._run(
        [
            "-c",
            _OPERATION_CONTRACT_PROBE,
            str(row.get("mapping_module") or ""),
            str(row.get("mapping_name") or ""),
            str(row.get("operation") or ""),
            str(database),
            EXECUTION_CONTRACT_ATTRIBUTE,
        ],
        timeout=120,
    )
    payload = core._parse_json(raw.stdout, context="card-set assembly execution-contract discovery")
    if not isinstance(payload, dict) or payload.get("schema") != "rocketdict-workbench-operation-contract-probe/1":
        return None
    if str(payload.get("callable_source_sha256") or "").casefold() != str(row.get("source_sha256") or "").casefold():
        raise RuntimeError(f"Set-assembly candidate {row.get('operation')!r} callable source drift")
    contract = payload.get("contract")
    if not isinstance(contract, dict) or contract.get("schema") != PUBLIC_EXECUTION_CONTRACT_SCHEMA:
        return None
    return contract


def discover_set_assembly(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    set_name: str = DEFAULT_SET_NAME,
) -> dict[str, Any]:
    state_path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(state_path)
    require_quality_gate_pass(state_path)
    manifest = _load_complete_card_manifest(state_path, state)
    available = {
        "card_revision_ids": list(manifest["card_revision_ids"]),
        "set_name": str(set_name),
        "product_run_root_fingerprint": str((state.get("root_identity") or {}).get("fingerprint") or "").casefold(),
        "stage24_manifest_fingerprint": str(manifest["fingerprint"]).casefold(),
    }
    candidates = []
    exact = []
    for row in _operation_rows(probe):
        operation = str(row.get("operation") or "")
        if not operation:
            continue
        contract = _probe_generic_contract(core, database_path, row)
        reasons = []
        if contract is None:
            reasons.append("no_public_execution_contract")
        else:
            request = contract.get("request")
            result = contract.get("result")
            params = request.get("params") if isinstance(request, dict) else None
            if contract.get("transport") != TRANSPORT or not isinstance(contract.get("replay_safe"), bool):
                reasons.append("invalid_transport_or_replay_policy")
            if not isinstance(params, dict):
                reasons.append("invalid_request_params")
            else:
                sources = list(params.values())
                if "input:card_revision_ids" not in sources:
                    reasons.append("does_not_consume_card_revision_ids")
                for source in sources:
                    if not isinstance(source, str) or not source.startswith("input:"):
                        reasons.append("unsupported_non_input_request_source")
                        continue
                    if source.removeprefix("input:") not in available:
                        reasons.append(f"unresolvable_input:{source.removeprefix('input:')}")
            if not isinstance(result, dict):
                reasons.append("invalid_result_contract")
            else:
                required_fields = result.get("required_fields")
                identity_fields = result.get("identity_fields")
                if not isinstance(required_fields, list) or "set_revision_id" not in required_fields:
                    reasons.append("set_revision_id_not_required")
                if not isinstance(identity_fields, list) or "set_revision_id" not in identity_fields:
                    reasons.append("set_revision_id_not_identity")
        candidate = {"operation": operation, "reasons": reasons, "contract": contract if not reasons else None}
        candidates.append(candidate)
        if not reasons:
            exact.append(candidate)
    return {
        "schema": SET_ASSEMBLY_DISCOVERY_SCHEMA,
        "status": "unique_exact_match" if len(exact) == 1 else ("no_exact_match" if not exact else "ambiguous_exact_matches"),
        "available_inputs": available,
        "exact_matches": exact,
        "candidates": candidates,
        "stage24_manifest_fingerprint": manifest["fingerprint"],
        "state_path": str(state_path),
    }


def execute_set_assembly(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    set_name: str = DEFAULT_SET_NAME,
) -> dict[str, Any]:
    state_path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    discovery = discover_set_assembly(core, database_path, state_path, set_name=set_name)
    if discovery["status"] != "unique_exact_match":
        raise RuntimeError(f"Card-set assembly public contract is not uniquely proven: {discovery['status']}")
    state, preflight, probe = _load_verified_evidence(state_path)
    candidate = discovery["exact_matches"][0]
    operation = candidate["operation"]
    contract = candidate["contract"]
    row = [row for row in _operation_rows(probe) if str(row.get("operation") or "") == operation][0]
    binding = {
        "schema": SET_ASSEMBLY_BINDING_SCHEMA,
        "operation": operation,
        "callable_source_sha256": str(row.get("source_sha256") or "").casefold(),
        "execution_contract_sha256": _canonical_sha256(contract),
        "stage24_manifest_fingerprint": discovery["stage24_manifest_fingerprint"],
        "available_inputs_sha256": _canonical_sha256(discovery["available_inputs"]),
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
    }
    binding["fingerprint"] = _canonical_sha256(binding)
    step = state["steps"]["cards"]
    previous_binding = step.get("set_assembly_binding")
    if previous_binding is not None and previous_binding != binding:
        raise RuntimeError("Card-set assembly binding changed inside immutable Product run")
    step["set_assembly_binding"] = binding
    previous = step.get("set_assembly")
    if isinstance(previous, dict) and previous.get("status") == "completed":
        result = previous.get("result")
        if not isinstance(result, dict) or previous.get("result_sha256") != _canonical_sha256(result):
            raise RuntimeError("Completed card-set assembly result was mutated")
        if previous.get("binding_fingerprint") != binding["fingerprint"]:
            raise RuntimeError("Completed card-set assembly belongs to different binding")
        return {**previous, "cache_hit": True, "state_path": str(state_path)}
    if isinstance(previous, dict) and previous.get("status") in {"dispatching", "ambiguous_failure"} and not contract["replay_safe"]:
        raise RuntimeError("Previous card-set assembly may have mutated database and is not replay-safe")
    params = {}
    for key, source in contract["request"]["params"].items():
        name = source.removeprefix("input:")
        params[key] = discovery["available_inputs"][name]
    request = {"transport": TRANSPORT, "operation": operation, "params": params}
    record = {
        "schema": SET_ASSEMBLY_EXECUTION_SCHEMA,
        "status": "dispatching",
        "binding_fingerprint": binding["fingerprint"],
        "request_sha256": _canonical_sha256(request),
        "replay_safe": contract["replay_safe"],
        "started_at": _now(),
    }
    step["set_assembly"] = record
    step["status"] = "assembling_set"
    state["status"] = "executing_stage24_set_assembly"
    _save_state(state_path, state)
    try:
        raw = core.api(
            database_path,
            "call",
            operation,
            "--params",
            json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            timeout=1800,
        )
        result, identities = _validate_result(raw, contract, 24)
    except Exception as exc:
        record["status"] = "ambiguous_failure"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        record["failed_at"] = _now()
        step["status"] = "set_assembly_failed"
        state["status"] = "failed"
        _save_state(state_path, state)
        raise
    set_revision_id = identities.get("set_revision_id")
    if isinstance(set_revision_id, bool) or not isinstance(set_revision_id, int) or set_revision_id <= 0:
        raise RuntimeError("Card-set assembly returned invalid set_revision_id")
    record.update(
        {
            "status": "completed",
            "completed_at": _now(),
            "result": result,
            "result_sha256": _canonical_sha256(result),
            "durable_identities": identities,
            "set_revision_id": set_revision_id,
        }
    )
    step["set_assembly"] = record
    step["status"] = "completed"
    state["status"] = "stage24_completed_awaiting_stage25_export"
    _save_state(state_path, state)
    return {**record, "cache_hit": False, "state_path": str(state_path)}


def execute_stage25_export(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
) -> dict[str, Any]:
    state_path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(state_path)
    require_quality_gate_pass(state_path)
    cards = (state.get("steps") or {}).get("cards") or {}
    assembly = cards.get("set_assembly")
    if not isinstance(assembly, dict) or assembly.get("status") != "completed":
        raise RuntimeError("Stage25 export requires completed Stage24 set assembly")
    result = assembly.get("result")
    if not isinstance(result, dict) or assembly.get("result_sha256") != _canonical_sha256(result):
        raise RuntimeError("Stage24 set assembly result was mutated before Stage25")
    set_revision_id = assembly.get("set_revision_id")
    if result.get("set_revision_id") != set_revision_id:
        raise RuntimeError("Stage24 set_revision_id is not backed by hashed assembly result")
    profile = _profile_stage(preflight, 25)
    if profile["required_inputs"] != ["set_revision_id"]:
        raise RuntimeError(
            f"Current Stage25 live contract is not the supported exact export contract ['set_revision_id']: {profile['required_inputs']}"
        )
    lineage_fingerprint = _canonical_sha256(
        {
            "stage24_manifest_fingerprint": (_load_complete_card_manifest(state_path, state))["fingerprint"],
            "set_assembly_result_sha256": assembly["result_sha256"],
            "set_revision_id": set_revision_id,
        }
    )
    binding = _binding(state, preflight, probe, 25, lineage_fingerprint=lineage_fingerprint)
    contract = _probe_execution_contract(core, database_path, binding, 25)
    params = _render_request(binding, contract, profile, {"set_revision_id": set_revision_id})
    request = {"transport": TRANSPORT, "operation": binding["operation"], "params": params}
    step = state["steps"]["export"]
    previous = step.get("execution")
    if isinstance(previous, dict) and previous.get("status") == "completed":
        previous_result = previous.get("result")
        if not isinstance(previous_result, dict) or previous.get("result_sha256") != _canonical_sha256(previous_result):
            raise RuntimeError("Completed Stage25 export result was mutated")
        if previous.get("request_sha256") != _canonical_sha256(request):
            raise RuntimeError("Completed Stage25 export belongs to different set revision/request")
        return {**previous, "cache_hit": True, "state_path": str(state_path)}
    if isinstance(previous, dict) and previous.get("status") in {"dispatching", "ambiguous_failure"} and not contract["replay_safe"]:
        raise RuntimeError("Previous Stage25 export may have mutated database and is not replay-safe")
    record = {
        "schema": FINAL_STAGE_EXECUTION_SCHEMA,
        "status": "dispatching",
        "stage_number": 25,
        "binding_fingerprint": binding["fingerprint"],
        "execution_contract_sha256": _canonical_sha256(contract),
        "request": request,
        "request_sha256": _canonical_sha256(request),
        "replay_safe": contract["replay_safe"],
        "started_at": _now(),
    }
    step["status"] = "running"
    step["execution"] = record
    state["status"] = "executing_stage25_export"
    _save_state(state_path, state)
    try:
        raw = core.api(
            database_path,
            "call",
            binding["operation"],
            "--params",
            json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            timeout=1800,
        )
        export_result, identities = _validate_result(raw, contract, 25)
    except Exception as exc:
        record["status"] = "ambiguous_failure"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        record["failed_at"] = _now()
        step["status"] = "failed"
        state["status"] = "failed"
        _save_state(state_path, state)
        raise
    record.update(
        {
            "status": "completed",
            "completed_at": _now(),
            "result": export_result,
            "result_sha256": _canonical_sha256(export_result),
            "durable_identities": identities,
        }
    )
    record["fingerprint"] = _canonical_sha256(
        {k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "completed_at"}}
    )
    step["status"] = "completed"
    step["execution"] = record
    state["status"] = "product_complete_exported"
    _save_state(state_path, state)
    return {**record, "cache_hit": False, "state_path": str(state_path)}


def advance_final_product(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    set_name: str = DEFAULT_SET_NAME,
    max_new_cards: int | None = None,
) -> dict[str, Any]:
    state_path = Path(state_path).expanduser().resolve()
    cards = execute_stage24_cards(
        core,
        database,
        state_path,
        max_new_cards=max_new_cards,
    )
    if cards["status"] != "cards_complete_awaiting_set_assembly":
        return {
            "schema": FINAL_PIPELINE_SCHEMA,
            "status": "stage24_partial",
            "cards": cards,
            "state_path": str(state_path),
        }
    assembly = execute_set_assembly(core, database, state_path, set_name=set_name)
    export = execute_stage25_export(core, database, state_path)
    return {
        "schema": FINAL_PIPELINE_SCHEMA,
        "status": "product_complete_exported",
        "cards": cards,
        "set_assembly": assembly,
        "export": export,
        "state_path": str(state_path),
    }
