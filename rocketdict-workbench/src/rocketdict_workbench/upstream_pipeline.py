from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .upstream_binding import BINDING_SCHEMA, _canonical_sha256, _load_verified_evidence, _valid_sha256
from .upstream_chain import discover_upstream_stage, pre_gate_stages, verify_upstream_stage_binding
from .upstream_execution import (
    EXECUTION_CONTRACT_ATTRIBUTE,
    EXECUTION_PROOF_SCHEMA,
    EXECUTION_RECORD_SCHEMA,
    MAX_PERSISTED_RESULT_BYTES,
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    TRANSPORT,
)

UPSTREAM_PIPELINE_SCHEMA = "rocketdict-workbench-pre-gate-upstream-pipeline/1"
UPSTREAM_PLAN_SCHEMA = "rocketdict-workbench-upstream-execution-plan/1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _binding(state: dict[str, Any], stage_number: int) -> dict[str, Any]:
    row = ((((state.get("steps") or {}).get("upstream_execution") or {}).get("bindings") or {}).get(str(stage_number)))
    if not isinstance(row, dict) or row.get("schema") != BINDING_SCHEMA:
        raise RuntimeError(f"Stage {stage_number} has no current verified runtime binding")
    fingerprint = str(row.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({key: value for key, value in row.items() if key != "fingerprint"})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError(f"Persisted Stage {stage_number} binding evidence was mutated")
    return row


def _profile_stage(preflight: dict[str, Any], stage_number: int) -> dict[str, Any]:
    row = (((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number)))
    if not isinstance(row, dict):
        raise RuntimeError(f"Product preflight lost Stage {stage_number} profile")
    return row


def _string_list(value: Any, *, context: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise RuntimeError(f"{context} must be a non-empty list of strings")
    if len(set(value)) != len(value):
        raise RuntimeError(f"{context} contains duplicates")
    return list(value)


def _validate_public_contract(contract: Any, binding: dict[str, Any], stage_number: int) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise RuntimeError(f"Stage {stage_number} callable does not publish {EXECUTION_CONTRACT_ATTRIBUTE!r}")
    if contract.get("schema") != PUBLIC_EXECUTION_CONTRACT_SCHEMA:
        raise RuntimeError(f"Unsupported Stage {stage_number} public execution contract schema: {contract.get('schema')!r}")
    if contract.get("transport") != TRANSPORT:
        raise RuntimeError(f"Unsupported Stage {stage_number} execution transport: {contract.get('transport')!r}")
    if not isinstance(contract.get("replay_safe"), bool):
        raise RuntimeError(f"Stage {stage_number} public execution contract must declare replay_safe")
    request = contract.get("request")
    params = request.get("params") if isinstance(request, dict) else None
    if not isinstance(params, dict) or not params:
        raise RuntimeError(f"Stage {stage_number} public execution contract request.params must be a non-empty object")
    if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in params.items()):
        raise RuntimeError(f"Stage {stage_number} request.params must map non-empty strings to symbolic sources")
    required_inputs = list(binding.get("required_inputs") or [])
    mapped_inputs = [spec.removeprefix("input:") for spec in params.values() if spec.startswith("input:")]
    if sorted(mapped_inputs) != sorted(required_inputs):
        raise RuntimeError(f"Stage {stage_number} execution contract does not map frozen required inputs exactly")
    allowed = {
        *(f"input:{name}" for name in required_inputs),
        "profile:parameters",
        "binding:implementation",
        "binding:stage_number",
        "binding:stage_key",
    }
    unknown = sorted(set(params.values()) - allowed)
    if unknown:
        raise RuntimeError(f"Stage {stage_number} execution contract has unsupported request sources: {unknown}")
    if "profile:parameters" not in params.values():
        raise RuntimeError(f"Stage {stage_number} execution contract must map frozen Product parameters")
    result = contract.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Stage {stage_number} public execution contract lacks result object")
    required_fields = _string_list(result.get("required_fields"), context=f"Stage {stage_number} result.required_fields")
    identity_fields = _string_list(result.get("identity_fields"), context=f"Stage {stage_number} result.identity_fields")
    if not set(identity_fields).issubset(required_fields):
        raise RuntimeError(f"Stage {stage_number} result identity_fields must be a subset of required_fields")
    normalized_result: dict[str, Any] = {"required_fields": required_fields, "identity_fields": identity_fields}
    schema_field = result.get("schema_field")
    if schema_field is not None:
        if not isinstance(schema_field, str) or not schema_field or schema_field not in required_fields:
            raise RuntimeError(f"Stage {stage_number} result.schema_field is invalid")
        normalized_result["schema_field"] = schema_field
        normalized_result["schema_values"] = _string_list(
            result.get("schema_values"), context=f"Stage {stage_number} result.schema_values"
        )
    elif result.get("schema_values") is not None:
        raise RuntimeError(f"Stage {stage_number} result.schema_values requires schema_field")
    normalized = {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": TRANSPORT,
        "replay_safe": bool(contract["replay_safe"]),
        "request": {"params": dict(params)},
        "result": normalized_result,
    }
    if normalized != contract:
        raise RuntimeError(f"Stage {stage_number} public execution contract contains unsupported/unfrozen fields")
    return normalized


_OPERATION_CONTRACT_PROBE = r'''
import hashlib,importlib,inspect,json,sys
from pathlib import Path
import rocketdict
from rocketdict.api.contracts import API_VERSION
mapping_module,mapping_name,operation,database,attribute=sys.argv[1:6]
mod=importlib.import_module(mapping_module); mapping=getattr(mod,mapping_name)
if not isinstance(mapping,dict): raise TypeError(f"{mapping_module}.{mapping_name} is not a dict")
if operation not in mapping: raise KeyError(operation)
fn=mapping[operation]
if not callable(fn): raise TypeError(f"{operation} is not callable")
try: source=inspect.getsource(fn)
except Exception as exc: raise RuntimeError(f"callable source is not inspectable: {exc}") from exc
contract=getattr(fn,attribute,None)
json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
print(json.dumps({
 "schema":"rocketdict-workbench-operation-contract-probe/1",
 "database":{"path":str(Path(database).resolve()),"exists":Path(database).is_file()},
 "core":{"rocketdict_version":str(getattr(rocketdict,"__version__","")),"api_version":str(API_VERSION)},
 "mapping_module":mapping_module,"mapping_name":mapping_name,"operation":operation,
 "callable_module":str(getattr(fn,"__module__","") or ""),
 "callable_qualname":str(getattr(fn,"__qualname__",getattr(fn,"__name__",type(fn).__name__))),
 "callable_source_sha256":hashlib.sha256(source.encode("utf-8")).hexdigest(),
 "contract_attribute":attribute,"contract":contract,
},ensure_ascii=False,sort_keys=True))
'''


def probe_upstream_execution_contract(
    core: RocketDictCore, database: Path | str, state_path: Path | str, stage_number: int
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    if stage_number not in pre_gate_stages(preflight):
        raise RuntimeError(f"Stage {stage_number} is behind the mandatory Stage15 hard-quality boundary")
    binding = _binding(state, stage_number)
    callable_row = binding.get("callable") or {}
    mapping_module = str(callable_row.get("mapping_module") or "")
    mapping_name = str(callable_row.get("mapping_name") or "")
    operation = str(binding.get("operation") or "")
    probe_database = Path(str((probe.get("database") or {}).get("path") or "")).expanduser().resolve()
    if probe_database != database_path:
        raise RuntimeError(f"Stage {stage_number} execution database differs from API probe database")
    result = core._run(
        ["-c", _OPERATION_CONTRACT_PROBE, mapping_module, mapping_name, operation, str(database_path), EXECUTION_CONTRACT_ATTRIBUTE],
        timeout=120,
    )
    payload = core._parse_json(result.stdout, context=f"Stage {stage_number} public execution-contract probe")
    if not isinstance(payload, dict) or payload.get("schema") != "rocketdict-workbench-operation-contract-probe/1":
        raise RuntimeError(f"Unexpected Stage {stage_number} execution-contract probe payload")
    expected_core = (preflight.get("identity") or {}).get("core") or {}
    for key in ("rocketdict_version", "api_version"):
        if str((payload.get("core") or {}).get(key) or "") != str(expected_core.get(key) or ""):
            raise RuntimeError(f"Stage {stage_number} execution-contract probe {key} differs from Product preflight")
    exact = {
        "mapping_module": mapping_module,
        "mapping_name": mapping_name,
        "operation": operation,
        "callable_module": str(callable_row.get("module") or ""),
        "callable_qualname": str(callable_row.get("qualname") or ""),
        "callable_source_sha256": str(callable_row.get("source_sha256") or "").casefold(),
    }
    for key, expected_value in exact.items():
        if str(payload.get(key) or "").casefold() != str(expected_value).casefold():
            raise RuntimeError(f"Stage {stage_number} callable identity drift during execution-contract probe: {key}")
    contract = _validate_public_contract(payload.get("contract"), binding, stage_number)
    return {
        "schema": EXECUTION_PROOF_SCHEMA,
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "database": str(database_path),
        "core": dict(payload.get("core") or {}),
        "callable": exact,
        "contract_attribute": EXECUTION_CONTRACT_ATTRIBUTE,
        "contract": contract,
        "contract_sha256": _canonical_sha256(contract),
    }


def _proof_fingerprint(proof: dict[str, Any]) -> str:
    fingerprint = str(proof.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({key: value for key, value in proof.items() if key not in {"fingerprint", "verified_at"}})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted upstream execution-contract proof was mutated")
    return fingerprint


def prove_upstream_execution_contract(
    core: RocketDictCore, database: Path | str, state_path: Path | str, stage_number: int
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, _preflight, _probe = _load_verified_evidence(path)
    observed = probe_upstream_execution_contract(core, database, path, stage_number)
    upstream = state["steps"]["upstream_execution"]
    proofs = upstream.setdefault("execution_contracts", {})
    previous = proofs.get(str(stage_number))
    verified_at = _now()
    if previous is not None:
        if not isinstance(previous, dict):
            raise RuntimeError(f"Persisted Stage {stage_number} execution proof is not an object")
        _proof_fingerprint(previous)
        verified_at = str(previous.get("verified_at") or "")
    proof = {**observed, "verified_at": verified_at}
    proof["fingerprint"] = _canonical_sha256({key: value for key, value in proof.items() if key != "verified_at"})
    if previous is not None and str(previous.get("fingerprint") or "") != proof["fingerprint"]:
        raise RuntimeError(f"Exact Stage {stage_number} public execution contract changed inside immutable Product run")
    proofs[str(stage_number)] = proof
    upstream["last_execution_contract_verified_stage"] = stage_number
    _save(path, state)
    return proof


def _load_proof(state: dict[str, Any], binding: dict[str, Any], stage_number: int) -> dict[str, Any]:
    proof = (((((state.get("steps") or {}).get("upstream_execution") or {}).get("execution_contracts") or {}).get(str(stage_number))))
    if not isinstance(proof, dict) or proof.get("schema") != EXECUTION_PROOF_SCHEMA:
        raise RuntimeError(f"Stage {stage_number} has no verified public execution contract")
    _proof_fingerprint(proof)
    if str(proof.get("binding_fingerprint") or "") != str(binding.get("fingerprint") or ""):
        raise RuntimeError(f"Stage {stage_number} execution proof belongs to a different binding")
    contract = _validate_public_contract(proof.get("contract"), binding, stage_number)
    if str(proof.get("contract_sha256") or "") != _canonical_sha256(contract):
        raise RuntimeError(f"Stage {stage_number} execution contract hash drift")
    return proof


def plan_upstream_execution(state_path: Path | str, stage_number: int) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    if stage_number not in pre_gate_stages(preflight):
        raise RuntimeError(f"Stage {stage_number} cannot execute before Stage15 hard-quality proof")
    binding = _binding(state, stage_number)
    proof = _load_proof(state, binding, stage_number)
    profile_stage = _profile_stage(preflight, stage_number)
    parameters = dict(profile_stage.get("parameters") or {})
    if str(binding.get("parameters_sha256") or "").casefold() != _canonical_sha256(parameters):
        raise RuntimeError(f"Stage {stage_number} Product parameters changed after binding")
    frozen_inputs = dict(binding.get("frozen_inputs") or {})
    params: dict[str, Any] = {}
    for key, spec in proof["contract"]["request"]["params"].items():
        if spec.startswith("input:"):
            name = spec.removeprefix("input:")
            if name not in frozen_inputs:
                raise RuntimeError(f"Stage {stage_number} request references unfrozen input {name!r}")
            params[key] = frozen_inputs[name]
        elif spec == "profile:parameters":
            params[key] = parameters
        elif spec == "binding:implementation":
            params[key] = binding["implementation"]
        elif spec == "binding:stage_number":
            params[key] = stage_number
        elif spec == "binding:stage_key":
            params[key] = binding["stage_key"]
        else:
            raise RuntimeError(f"Unsupported Stage {stage_number} request source {spec!r}")
    request = {"transport": TRANSPORT, "operation": binding["operation"], "params": params}
    return {
        "schema": UPSTREAM_PLAN_SCHEMA,
        "status": "ready",
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "execution_contract_fingerprint": proof["fingerprint"],
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "request": request,
        "request_sha256": _canonical_sha256(request),
        "result_contract": dict(proof["contract"]["result"]),
        "replay_safe": bool(proof["contract"]["replay_safe"]),
        "database": str(proof["database"]),
    }


def _validate_result(result: Any, contract: dict[str, Any], stage_number: int) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(result, dict):
        raise RuntimeError(f"Stage {stage_number} public API returned non-object result")
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    if len(raw) > MAX_PERSISTED_RESULT_BYTES:
        raise RuntimeError(f"Stage {stage_number} public API result is unexpectedly large")
    rc = contract["result"]
    missing = [field for field in rc["required_fields"] if field not in result]
    if missing:
        raise RuntimeError(f"Stage {stage_number} public API result lacks required fields: {missing}")
    schema_field = rc.get("schema_field")
    if schema_field is not None and result.get(schema_field) not in rc["schema_values"]:
        raise RuntimeError(f"Stage {stage_number} public API result schema is outside verified values")
    identities: dict[str, Any] = {}
    for field in rc["identity_fields"]:
        value = result.get(field)
        if value is None or isinstance(value, (bool, dict, list)) or (isinstance(value, str) and not value):
            raise RuntimeError(f"Stage {stage_number} public API result has invalid durable identity {field}={value!r}")
        identities[field] = value
    return dict(result), identities


def _record_fingerprint(record: dict[str, Any]) -> str:
    fingerprint = str(record.get("fingerprint") or "").casefold()
    immutable = {
        key: value
        for key, value in record.items()
        if key not in {"fingerprint", "started_at", "completed_at", "failed_at", "error", "attempts", "cache_hit"}
    }
    expected = _canonical_sha256(immutable)
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted upstream execution record was mutated")
    return fingerprint


def execute_upstream_stage(
    core: RocketDictCore, database: Path | str, state_path: Path | str, stage_number: int
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    prove_upstream_execution_contract(core, database_path, path, stage_number)
    plan = plan_upstream_execution(path, stage_number)
    state, _preflight, _probe = _load_verified_evidence(path)
    binding = _binding(state, stage_number)
    proof = _load_proof(state, binding, stage_number)
    contract = proof["contract"]
    upstream = state["steps"]["upstream_execution"]
    executions = upstream.setdefault("executions", {})
    previous = executions.get(str(stage_number))
    if isinstance(previous, dict) and previous.get("status") == "completed":
        _record_fingerprint(previous)
        if previous.get("request_sha256") != plan["request_sha256"]:
            raise RuntimeError(f"Completed Stage {stage_number} belongs to a different request")
        if previous.get("result_sha256") != _canonical_sha256(previous.get("result")):
            raise RuntimeError(f"Completed Stage {stage_number} result was mutated")
        return {**previous, "cache_hit": True, "state_path": str(path)}
    if isinstance(previous, dict) and previous.get("status") in {"dispatch_failed_ambiguous", "dispatching"} and not contract["replay_safe"]:
        raise RuntimeError(f"Previous Stage {stage_number} dispatch may have mutated the database and is not replay-safe")
    attempts = int(previous.get("attempts") or 0) + 1 if isinstance(previous, dict) else 1
    record: dict[str, Any] = {
        "schema": EXECUTION_RECORD_SCHEMA,
        "status": "dispatching",
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "execution_contract_fingerprint": proof["fingerprint"],
        "request": plan["request"],
        "request_sha256": plan["request_sha256"],
        "replay_safe": bool(contract["replay_safe"]),
        "attempts": attempts,
        "started_at": _now(),
    }
    record["fingerprint"] = _canonical_sha256(
        {key: value for key, value in record.items() if key not in {"fingerprint", "started_at", "attempts"}}
    )
    executions[str(stage_number)] = record
    upstream["status"] = f"stage{stage_number}_dispatching"
    state["status"] = f"executing_stage{stage_number}"
    _save(path, state)
    params_json = json.dumps(plan["request"]["params"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        raw = core.api(database_path, "call", str(binding["operation"]), "--params", params_json, timeout=1800)
        result, identities = _validate_result(raw, contract, stage_number)
    except Exception as exc:
        record["status"] = "dispatch_failed_ambiguous"
        record["failed_at"] = _now()
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        record["fingerprint"] = _canonical_sha256(
            {
                key: value
                for key, value in record.items()
                if key not in {"fingerprint", "started_at", "failed_at", "error", "attempts"}
            }
        )
        upstream["status"] = (
            f"stage{stage_number}_retryable_after_ambiguous_failure"
            if contract["replay_safe"]
            else f"stage{stage_number}_ambiguous_non_replay_safe"
        )
        upstream["blocked_reason"] = (
            "retry_explicitly_allowed_by_verified_public_contract"
            if contract["replay_safe"]
            else "manual_reconciliation_required_before_replay"
        )
        state["status"] = "failed"
        _save(path, state)
        raise
    record.update(
        {
            "status": "completed",
            "completed_at": _now(),
            "result": result,
            "result_sha256": _canonical_sha256(result),
            "durable_identities": identities,
        }
    )
    record["fingerprint"] = _canonical_sha256(
        {key: value for key, value in record.items() if key not in {"fingerprint", "started_at", "completed_at", "attempts"}}
    )
    upstream["status"] = f"stage{stage_number}_completed"
    upstream["blocked_reason"] = "next_pre_gate_binding_not_yet_verified"
    state["status"] = f"stage{stage_number}_completed_awaiting_next_upstream_binding"
    _save(path, state)
    return {**record, "cache_hit": False, "state_path": str(path)}


def _persist_block(path: Path, state: dict[str, Any], stage_number: int, reason: str, diagnostic: Any) -> None:
    upstream = state["steps"]["upstream_execution"]
    block = {"stage_number": stage_number, "reason": reason, "diagnostic": diagnostic}
    block["fingerprint"] = _canonical_sha256(block)
    upstream.setdefault("blocks", {})[str(stage_number)] = block
    upstream["status"] = f"stage{stage_number}_blocked"
    upstream["blocked_reason"] = reason
    state["status"] = f"blocked_before_stage{stage_number}"
    _save(path, state)


def advance_pre_gate_upstream(
    core: RocketDictCore, database: Path | str, state_path: Path | str, *, max_stages: int | None = None
) -> dict[str, Any]:
    """Advance Stage8/10/12/14 only; Stage15 remains a mandatory hard stop."""
    path = Path(state_path).expanduser().resolve()
    if max_stages is not None and max_stages <= 0:
        raise ValueError("max_stages must be positive")
    completed_now: list[int] = []
    state, preflight, _probe = _load_verified_evidence(path)
    stages = pre_gate_stages(preflight)
    for stage_number in stages:
        state, _preflight, _probe = _load_verified_evidence(path)
        current = (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {}).get(str(stage_number))
        if isinstance(current, dict) and current.get("status") == "completed":
            continue
        if max_stages is not None and len(completed_now) >= max_stages:
            break
        discovery = discover_upstream_stage(path, stage_number)
        if discovery["status"] != "unique_exact_match":
            reason = str(discovery["status"])
            _persist_block(path, state, stage_number, reason, discovery)
            return {
                "schema": UPSTREAM_PIPELINE_SCHEMA,
                "status": "blocked",
                "completed_now": completed_now,
                "blocked_stage": stage_number,
                "reason": reason,
                "diagnostic": discovery,
                "state_path": str(path),
            }
        operation = str(discovery["exact_matches"][0]["operation"])
        verify_upstream_stage_binding(path, stage_number, operation)
        try:
            result = execute_upstream_stage(core, database, path, stage_number)
        except RuntimeError as exc:
            state, _preflight, _probe = _load_verified_evidence(path)
            current = (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {}).get(str(stage_number))
            if not isinstance(current, dict) or current.get("status") != "dispatch_failed_ambiguous":
                diagnostic = {"operation": operation, "error_type": type(exc).__name__, "error": str(exc)}
                _persist_block(path, state, stage_number, "public_execution_contract_unproven", diagnostic)
                return {
                    "schema": UPSTREAM_PIPELINE_SCHEMA,
                    "status": "blocked",
                    "completed_now": completed_now,
                    "blocked_stage": stage_number,
                    "reason": "public_execution_contract_unproven",
                    "diagnostic": diagnostic,
                    "state_path": str(path),
                }
            raise
        if not result.get("cache_hit"):
            completed_now.append(stage_number)
    state, preflight, _probe = _load_verified_evidence(path)
    executions = (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {})
    remaining = [
        number
        for number in pre_gate_stages(preflight)
        if not isinstance(executions.get(str(number)), dict)
        or executions[str(number)].get("status") != "completed"
    ]
    if remaining:
        return {
            "schema": UPSTREAM_PIPELINE_SCHEMA,
            "status": "progressed",
            "completed_now": completed_now,
            "next_stage": remaining[0],
            "state_path": str(path),
        }
    upstream = state["steps"]["upstream_execution"]
    upstream["status"] = "pre_hard_gate_core_completed"
    upstream["blocked_reason"] = "stage15_hard_quality_gate_execution_not_yet_proven"
    state["status"] = "pre_hard_gate_core_completed_awaiting_stage15_quality_gate"
    _save(path, state)
    return {
        "schema": UPSTREAM_PIPELINE_SCHEMA,
        "status": "pre_hard_gate_core_completed",
        "completed_now": completed_now,
        "next_stage": 15,
        "hard_stop": "stage15_quality_gate",
        "post_gate_stages_executed": False,
        "state_path": str(path),
    }
