from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .product_run_state import RUN_STATE_SCHEMA
from .upstream_binding import (
    BINDING_SCHEMA,
    FIRST_UPSTREAM_STAGE,
    _canonical_sha256,
    _load_verified_evidence,
)

EXECUTION_CONTRACT_ATTRIBUTE = "rocketdict_execution_contract"
PUBLIC_EXECUTION_CONTRACT_SCHEMA = "rocketdict-public-operation-execution/1"
EXECUTION_PROOF_SCHEMA = "rocketdict-workbench-upstream-execution-proof/1"
EXECUTION_RECORD_SCHEMA = "rocketdict-workbench-upstream-execution/1"
TRANSPORT = "rocketdict.api.call/1"
MAX_PERSISTED_RESULT_BYTES = 8 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").casefold()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _binding_fingerprint(binding: dict[str, Any]) -> str:
    fingerprint = str(binding.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({key: value for key, value in binding.items() if key != "fingerprint"})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted Stage8 binding evidence was mutated")
    return fingerprint


def _load_stage8_context(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    state, preflight, probe = _load_verified_evidence(path)
    if state.get("schema") != RUN_STATE_SCHEMA:
        raise RuntimeError(f"Unsupported Product run state schema: {state.get('schema')!r}")
    upstream = (state.get("steps") or {}).get("upstream_execution") or {}
    bindings = upstream.get("bindings") or {}
    binding = bindings.get(str(FIRST_UPSTREAM_STAGE))
    if not isinstance(binding, dict):
        raise RuntimeError("Stage8 has no verified runtime binding")
    if binding.get("schema") != BINDING_SCHEMA:
        raise RuntimeError(
            f"Stage8 binding proof schema {binding.get('schema')!r} is not current {BINDING_SCHEMA!r}; re-verify the binding"
        )
    _binding_fingerprint(binding)
    if int(binding.get("stage_number") or 0) != FIRST_UPSTREAM_STAGE:
        raise RuntimeError("Persisted upstream binding is not Stage8")

    identity = preflight.get("identity") or {}
    proof = binding.get("proof") or {}
    exact = {
        "preflight_fingerprint": str(identity.get("fingerprint") or "").casefold(),
        "product_run_root_fingerprint": str((state.get("root_identity") or {}).get("fingerprint") or "").casefold(),
        "registry_hash": str(identity.get("registry_hash") or ""),
        "rocketdict_version": str((identity.get("core") or {}).get("rocketdict_version") or ""),
        "api_version": str((identity.get("core") or {}).get("api_version") or ""),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "execution_contract_sha256": str(binding.get("execution_contract_sha256") or "").casefold(),
    }
    for key, value in exact.items():
        if str(proof.get(key) or "").casefold() != str(value).casefold():
            raise RuntimeError(f"Stage8 binding proof drift for {key}")

    profile_stage = (((preflight.get("profile") or {}).get("stages") or {}).get(str(FIRST_UPSTREAM_STAGE)))
    if not isinstance(profile_stage, dict):
        raise RuntimeError("Product preflight lost its Stage8 profile")
    parameters = dict(profile_stage.get("parameters") or {})
    if str(binding.get("parameters_sha256") or "").casefold() != _canonical_sha256(parameters):
        raise RuntimeError("Stage8 binding parameter hash no longer matches Product preflight")

    required_inputs = binding.get("required_inputs")
    frozen_inputs = binding.get("frozen_inputs")
    if not isinstance(required_inputs, list) or not required_inputs:
        raise RuntimeError("Stage8 binding lacks required_inputs")
    if not isinstance(frozen_inputs, dict) or set(frozen_inputs) != set(required_inputs):
        raise RuntimeError("Stage8 binding frozen inputs do not exactly cover required_inputs")
    return state, preflight, probe, binding, profile_stage


_OPERATION_CONTRACT_PROBE = r'''
import hashlib
import importlib
import inspect
import json
import sys
from pathlib import Path

import rocketdict
from rocketdict.api.contracts import API_VERSION

mapping_module,mapping_name,operation,database,attribute=sys.argv[1:6]
mod=importlib.import_module(mapping_module)
mapping=getattr(mod,mapping_name)
if not isinstance(mapping,dict):
    raise TypeError(f"{mapping_module}.{mapping_name} is not a dict")
if operation not in mapping:
    raise KeyError(operation)
fn=mapping[operation]
if not callable(fn):
    raise TypeError(f"{operation} is not callable")
try:
    source=inspect.getsource(fn)
except Exception as exc:
    raise RuntimeError(f"callable source is not inspectable: {exc}") from exc
contract=getattr(fn,attribute,None)
try:
    json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
except Exception as exc:
    raise RuntimeError(f"{attribute} is not canonical JSON metadata: {exc}") from exc
print(json.dumps({
    "schema":"rocketdict-workbench-operation-contract-probe/1",
    "database":{"path":str(Path(database).resolve()),"exists":Path(database).is_file()},
    "core":{"rocketdict_version":str(getattr(rocketdict,"__version__","")),"api_version":str(API_VERSION)},
    "mapping_module":mapping_module,
    "mapping_name":mapping_name,
    "operation":operation,
    "callable_module":str(getattr(fn,"__module__","") or ""),
    "callable_qualname":str(getattr(fn,"__qualname__",getattr(fn,"__name__",type(fn).__name__))),
    "callable_source_sha256":hashlib.sha256(source.encode("utf-8")).hexdigest(),
    "contract_attribute":attribute,
    "contract":contract,
},ensure_ascii=False,sort_keys=True))
'''


def _validate_string_list(value: Any, *, context: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RuntimeError(f"{context} must be a JSON list of non-empty strings")
    if not allow_empty and not value:
        raise RuntimeError(f"{context} must not be empty")
    if len(set(value)) != len(value):
        raise RuntimeError(f"{context} contains duplicates")
    return list(value)


def _validate_execution_contract(contract: Any, binding: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise RuntimeError(
            f"Stage8 callable does not publish {EXECUTION_CONTRACT_ATTRIBUTE!r}; execution is blocked before database mutation"
        )
    if contract.get("schema") != PUBLIC_EXECUTION_CONTRACT_SCHEMA:
        raise RuntimeError(
            f"Unsupported Stage8 public execution contract schema: {contract.get('schema')!r}; "
            f"expected {PUBLIC_EXECUTION_CONTRACT_SCHEMA!r}"
        )
    if contract.get("transport") != TRANSPORT:
        raise RuntimeError(f"Unsupported Stage8 execution transport: {contract.get('transport')!r}")
    replay_safe = contract.get("replay_safe")
    if not isinstance(replay_safe, bool):
        raise RuntimeError("Stage8 public execution contract must explicitly declare replay_safe as boolean")

    request = contract.get("request")
    if not isinstance(request, dict):
        raise RuntimeError("Stage8 public execution contract lacks request object")
    params = request.get("params")
    if not isinstance(params, dict) or not params:
        raise RuntimeError("Stage8 public execution contract request.params must be a non-empty JSON object")
    if any(not isinstance(key, str) or not key or not isinstance(spec, str) or not spec for key, spec in params.items()):
        raise RuntimeError("Stage8 public execution contract request.params must map non-empty names to source strings")

    required_inputs = _validate_string_list(binding.get("required_inputs"), context="Stage8 binding required_inputs")
    input_specs = [spec.removeprefix("input:") for spec in params.values() if spec.startswith("input:")]
    if sorted(input_specs) != sorted(required_inputs):
        raise RuntimeError(
            "Stage8 execution contract must map every frozen required input exactly once: "
            f"{input_specs!r} != {required_inputs!r}"
        )
    allowed_specs = {
        *(f"input:{name}" for name in required_inputs),
        "profile:parameters",
        "binding:implementation",
        "binding:stage_number",
        "binding:stage_key",
    }
    unknown = sorted(set(params.values()) - allowed_specs)
    if unknown:
        raise RuntimeError(f"Stage8 execution contract contains unsupported request sources: {unknown}")
    if "profile:parameters" not in params.values():
        raise RuntimeError("Stage8 execution contract must explicitly map frozen Product parameters")

    result = contract.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Stage8 public execution contract lacks result object")
    required_fields = _validate_string_list(result.get("required_fields"), context="Stage8 result.required_fields")
    identity_fields = _validate_string_list(result.get("identity_fields"), context="Stage8 result.identity_fields")
    if not set(identity_fields).issubset(required_fields):
        raise RuntimeError("Stage8 result identity_fields must be a subset of required_fields")
    schema_field = result.get("schema_field")
    schema_values = result.get("schema_values")
    if schema_field is not None:
        if not isinstance(schema_field, str) or not schema_field:
            raise RuntimeError("Stage8 result.schema_field must be a non-empty string")
        values = _validate_string_list(schema_values, context="Stage8 result.schema_values")
        if schema_field not in required_fields:
            raise RuntimeError("Stage8 result.schema_field must also be required")
        result = {**result, "schema_values": values}
    elif schema_values is not None:
        raise RuntimeError("Stage8 result.schema_values requires result.schema_field")

    normalized = {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": TRANSPORT,
        "replay_safe": replay_safe,
        "request": {"params": dict(params)},
        "result": {
            "required_fields": required_fields,
            "identity_fields": identity_fields,
            **({"schema_field": schema_field, "schema_values": list(result["schema_values"])} if schema_field is not None else {}),
        },
    }
    if normalized != contract:
        raise RuntimeError(
            "Stage8 public execution contract contains unsupported/unfrozen fields; "
            "publish only the canonical v1 contract surface"
        )
    return normalized


def probe_stage8_execution_contract(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    _state, preflight, probe, binding, _profile_stage = _load_stage8_context(path)
    callable_row = binding.get("callable") or {}
    mapping_module = str(callable_row.get("mapping_module") or "")
    mapping_name = str(callable_row.get("mapping_name") or "")
    operation = str(binding.get("operation") or "")
    if not mapping_module or not mapping_name or not operation:
        raise RuntimeError("Stage8 binding lacks exact callable mapping identity")

    observed_probe_db = Path(str((probe.get("database") or {}).get("path") or "")).expanduser().resolve()
    if observed_probe_db != database_path:
        raise RuntimeError(f"Stage8 execution database differs from API probe database: {database_path} != {observed_probe_db}")

    result = core._run(
        [
            "-c",
            _OPERATION_CONTRACT_PROBE,
            mapping_module,
            mapping_name,
            operation,
            str(database_path),
            EXECUTION_CONTRACT_ATTRIBUTE,
        ],
        timeout=120,
    )
    payload = core._parse_json(result.stdout, context="Stage8 public execution-contract probe")
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected Stage8 execution-contract probe payload: {payload!r}")
    if payload.get("schema") != "rocketdict-workbench-operation-contract-probe/1":
        raise RuntimeError(f"Unexpected Stage8 execution-contract probe schema: {payload.get('schema')!r}")

    identity = preflight.get("identity") or {}
    expected_core = identity.get("core") or {}
    observed_core = payload.get("core") or {}
    for key in ("rocketdict_version", "api_version"):
        if str(observed_core.get(key) or "") != str(expected_core.get(key) or ""):
            raise RuntimeError(f"Stage8 execution-contract probe {key} differs from Product preflight")
    expected_callable = binding.get("callable") or {}
    exact_callable = {
        "mapping_module": mapping_module,
        "mapping_name": mapping_name,
        "operation": operation,
        "callable_module": str(expected_callable.get("module") or ""),
        "callable_qualname": str(expected_callable.get("qualname") or ""),
        "callable_source_sha256": str(expected_callable.get("source_sha256") or "").casefold(),
    }
    for key, expected in exact_callable.items():
        if str(payload.get(key) or "").casefold() != str(expected).casefold():
            raise RuntimeError(f"Stage8 callable identity drift during execution-contract probe: {key}")

    contract = _validate_execution_contract(payload.get("contract"), binding)
    return {
        "schema": EXECUTION_PROOF_SCHEMA,
        "stage_number": FIRST_UPSTREAM_STAGE,
        "binding_fingerprint": _binding_fingerprint(binding),
        "preflight_fingerprint": str(identity.get("fingerprint") or "").casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "database": str(database_path),
        "core": dict(observed_core),
        "callable": exact_callable,
        "contract_attribute": EXECUTION_CONTRACT_ATTRIBUTE,
        "contract": contract,
        "contract_sha256": _canonical_sha256(contract),
    }


def _proof_fingerprint(proof: dict[str, Any]) -> str:
    fingerprint = str(proof.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({key: value for key, value in proof.items() if key not in {"fingerprint", "verified_at"}})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted Stage8 execution-contract proof was mutated")
    return fingerprint


def prove_stage8_execution_contract(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, _preflight, _probe, _binding, _profile_stage = _load_stage8_context(path)
    observed = probe_stage8_execution_contract(core, database, path)
    upstream = state["steps"]["upstream_execution"]
    proofs = upstream.setdefault("execution_contracts", {})
    previous = proofs.get(str(FIRST_UPSTREAM_STAGE))
    verified_at = _now()
    if previous is not None:
        if not isinstance(previous, dict):
            raise RuntimeError("Persisted Stage8 execution-contract proof is not a JSON object")
        _proof_fingerprint(previous)
        verified_at = str(previous.get("verified_at") or "")
        if not verified_at:
            raise RuntimeError("Persisted Stage8 execution-contract proof lacks verified_at")

    proof = {**observed, "verified_at": verified_at}
    proof["fingerprint"] = _canonical_sha256({key: value for key, value in proof.items() if key != "verified_at"})
    if previous is not None and str(previous.get("fingerprint") or "") != proof["fingerprint"]:
        raise RuntimeError("Exact Stage8 public execution contract changed inside the immutable Product run")
    proofs[str(FIRST_UPSTREAM_STAGE)] = proof
    upstream["status"] = "execution_contract_verified"
    upstream["blocked_reason"] = "verified_stage8_execution_contract_not_yet_dispatched"
    state["status"] = "ready_for_stage8_execution"
    _save(path, state)
    return proof


def _load_execution_proof(state: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    upstream = state["steps"]["upstream_execution"]
    proof = (upstream.get("execution_contracts") or {}).get(str(FIRST_UPSTREAM_STAGE))
    if not isinstance(proof, dict):
        raise RuntimeError("Stage8 has no verified public execution contract")
    if proof.get("schema") != EXECUTION_PROOF_SCHEMA:
        raise RuntimeError(f"Unsupported Stage8 execution proof schema: {proof.get('schema')!r}")
    _proof_fingerprint(proof)
    if str(proof.get("binding_fingerprint") or "") != _binding_fingerprint(binding):
        raise RuntimeError("Stage8 execution proof belongs to a different binding")
    contract = _validate_execution_contract(proof.get("contract"), binding)
    if str(proof.get("contract_sha256") or "") != _canonical_sha256(contract):
        raise RuntimeError("Stage8 execution contract hash drift")
    return proof


def _render_request(binding: dict[str, Any], profile_stage: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    frozen_inputs = dict(binding["frozen_inputs"])
    parameters = dict(profile_stage.get("parameters") or {})
    if str(binding.get("parameters_sha256") or "").casefold() != _canonical_sha256(parameters):
        raise RuntimeError("Stage8 Product parameters changed after binding")

    values: dict[str, Any] = {}
    for key, spec in contract["request"]["params"].items():
        if spec.startswith("input:"):
            input_name = spec.removeprefix("input:")
            if input_name not in frozen_inputs:
                raise RuntimeError(f"Stage8 request references unfrozen input {input_name!r}")
            values[key] = frozen_inputs[input_name]
        elif spec == "profile:parameters":
            values[key] = parameters
        elif spec == "binding:implementation":
            values[key] = binding["implementation"]
        elif spec == "binding:stage_number":
            values[key] = int(binding["stage_number"])
        elif spec == "binding:stage_key":
            values[key] = binding["stage_key"]
        else:  # protected again even after contract validation
            raise RuntimeError(f"Unsupported Stage8 request source {spec!r}")
    return values


def plan_stage8_execution(state_path: Path | str) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe, binding, profile_stage = _load_stage8_context(path)
    proof = _load_execution_proof(state, binding)
    contract = proof["contract"]
    params = _render_request(binding, profile_stage, contract)
    request = {
        "transport": TRANSPORT,
        "operation": binding["operation"],
        "params": params,
    }
    return {
        "schema": "rocketdict-workbench-stage8-execution-plan/1",
        "status": "ready",
        "stage_number": FIRST_UPSTREAM_STAGE,
        "binding_fingerprint": binding["fingerprint"],
        "execution_contract_fingerprint": proof["fingerprint"],
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "request": request,
        "request_sha256": _canonical_sha256(request),
        "result_contract": dict(contract["result"]),
        "replay_safe": bool(contract["replay_safe"]),
        "database": str(proof["database"]),
    }


def _validate_result(result: Any, contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(result, dict):
        raise RuntimeError(f"Stage8 public API returned non-object result: {type(result).__name__}")
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    if len(raw) > MAX_PERSISTED_RESULT_BYTES:
        raise RuntimeError(
            f"Stage8 public API result is unexpectedly large ({len(raw)} bytes > {MAX_PERSISTED_RESULT_BYTES}); "
            "the public execution operation must return compact durable identities, not the full NLP payload"
        )
    result_contract = contract["result"]
    missing = [field for field in result_contract["required_fields"] if field not in result]
    if missing:
        raise RuntimeError(f"Stage8 public API result lacks required fields: {missing}")
    schema_field = result_contract.get("schema_field")
    if schema_field is not None and result.get(schema_field) not in result_contract["schema_values"]:
        raise RuntimeError(
            f"Stage8 public API result {schema_field}={result.get(schema_field)!r} is outside verified schema values "
            f"{result_contract['schema_values']!r}"
        )
    identities: dict[str, Any] = {}
    for field in result_contract["identity_fields"]:
        value = result.get(field)
        if value is None or isinstance(value, bool) or isinstance(value, (dict, list)) or (isinstance(value, str) and not value):
            raise RuntimeError(f"Stage8 public API result has invalid durable identity {field}={value!r}")
        identities[field] = value
    return dict(result), identities


def _execution_fingerprint(record: dict[str, Any]) -> str:
    fingerprint = str(record.get("fingerprint") or "").casefold()
    immutable = {
        key: value
        for key, value in record.items()
        if key not in {"fingerprint", "started_at", "completed_at", "failed_at", "error", "attempts", "cache_hit"}
    }
    expected = _canonical_sha256(immutable)
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted Stage8 execution record was mutated")
    return fingerprint


def execute_stage8(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
) -> dict[str, Any]:
    """Execute only a fully proven Stage8 public operation and persist compact evidence.

    The exact callable contract is re-probed immediately before dispatch. Completed
    results are reused byte-for-byte by request/result hashes. A failed dispatch is
    treated as potentially mutating; replay is allowed only when the callable's
    public contract explicitly declares replay_safe=true.
    """
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    prove_stage8_execution_contract(core, database_path, path)
    plan = plan_stage8_execution(path)
    if Path(plan["database"]).resolve() != database_path:
        raise RuntimeError("Stage8 execution plan belongs to a different database")

    state, _preflight, _probe, binding, _profile_stage = _load_stage8_context(path)
    proof = _load_execution_proof(state, binding)
    contract = proof["contract"]
    upstream = state["steps"]["upstream_execution"]
    executions = upstream.setdefault("executions", {})
    previous = executions.get(str(FIRST_UPSTREAM_STAGE))
    if previous is not None:
        if not isinstance(previous, dict):
            raise RuntimeError("Persisted Stage8 execution record is not a JSON object")
        if previous.get("schema") != EXECUTION_RECORD_SCHEMA:
            raise RuntimeError(f"Unsupported Stage8 execution record schema: {previous.get('schema')!r}")
        if previous.get("status") == "completed":
            _execution_fingerprint(previous)
            if previous.get("request_sha256") != plan["request_sha256"]:
                raise RuntimeError("Completed Stage8 execution belongs to a different immutable request")
            result = previous.get("result")
            if previous.get("result_sha256") != _canonical_sha256(result):
                raise RuntimeError("Completed Stage8 result payload was mutated")
            return {**previous, "cache_hit": True, "state_path": str(path)}
        if previous.get("status") in {"dispatch_failed_ambiguous", "dispatching"} and not bool(contract["replay_safe"]):
            raise RuntimeError(
                "Previous Stage8 dispatch may have mutated the database and the verified public contract is not replay-safe; "
                "manual/recovery reconciliation is required before another dispatch"
            )

    attempts = int(previous.get("attempts") or 0) + 1 if isinstance(previous, dict) else 1
    record: dict[str, Any] = {
        "schema": EXECUTION_RECORD_SCHEMA,
        "status": "dispatching",
        "stage_number": FIRST_UPSTREAM_STAGE,
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
    executions[str(FIRST_UPSTREAM_STAGE)] = record
    upstream["status"] = "stage8_dispatching"
    upstream["blocked_reason"] = None
    state["status"] = "executing_stage8"
    _save(path, state)

    params_json = json.dumps(plan["request"]["params"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        raw_result = core.api(database_path, "call", str(binding["operation"]), "--params", params_json, timeout=1800)
        result, identities = _validate_result(raw_result, contract)
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
        upstream["status"] = "stage8_retryable_after_ambiguous_failure" if contract["replay_safe"] else "stage8_ambiguous_non_replay_safe"
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
        {
            key: value
            for key, value in record.items()
            if key not in {"fingerprint", "started_at", "completed_at", "attempts"}
        }
    )
    upstream["status"] = "stage8_completed"
    upstream["blocked_reason"] = "next_upstream_binding_not_yet_verified"
    state["status"] = "stage8_completed_awaiting_next_upstream_binding"
    _save(path, state)
    return {**record, "cache_hit": False, "state_path": str(path)}
