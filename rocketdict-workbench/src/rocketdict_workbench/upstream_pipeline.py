from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .product_preflight import REQUIRED_CORE_STAGES
from .upstream_binding import (
    BINDING_SCHEMA,
    _canonical_sha256,
    _load_verified_evidence,
    _operation_rows,
    _selected_stage,
    _valid_sha256,
)
from .upstream_execution import (
    EXECUTION_CONTRACT_ATTRIBUTE,
    EXECUTION_PROOF_SCHEMA,
    EXECUTION_RECORD_SCHEMA,
    MAX_PERSISTED_RESULT_BYTES,
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    TRANSPORT,
)

UPSTREAM_PIPELINE_SCHEMA = "rocketdict-workbench-upstream-pipeline/1"
UPSTREAM_DISCOVERY_SCHEMA = "rocketdict-workbench-upstream-binding-discovery/1"
UPSTREAM_STAGE_ORDER = tuple(REQUIRED_CORE_STAGES)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _scalar_identity(value: Any) -> bool:
    return value is not None and not isinstance(value, bool) and isinstance(value, (str, int)) and (
        not isinstance(value, str) or bool(value)
    )


def _merge_identity(
    ledger: dict[str, Any], origins: dict[str, str], name: str, value: Any, origin: str
) -> None:
    if not isinstance(name, str) or not name:
        raise RuntimeError(f"Durable identity from {origin} has an invalid name")
    if not _scalar_identity(value):
        raise RuntimeError(f"Durable identity {name!r} from {origin} is not a non-empty scalar")
    if name in ledger and ledger[name] != value:
        raise RuntimeError(
            f"Durable identity collision for {name!r}: {ledger[name]!r} from {origins[name]} != {value!r} from {origin}"
        )
    ledger[name] = value
    origins.setdefault(name, origin)


def build_upstream_identity_ledger(state: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    """Return only immutable source values plus identities from completed upstream results."""
    source = (preflight.get("identity") or {}).get("source") or {}
    ledger: dict[str, Any] = {}
    origins: dict[str, str] = {}
    for name, value in source.items():
        if _scalar_identity(value):
            _merge_identity(ledger, origins, str(name), value, "preflight.source")

    upstream = ((state.get("steps") or {}).get("upstream_execution") or {})
    executions = upstream.get("executions") or {}
    if not isinstance(executions, dict):
        raise RuntimeError("Persisted upstream executions are not a JSON object")
    for stage_number in UPSTREAM_STAGE_ORDER:
        record = executions.get(str(stage_number))
        if record is None:
            continue
        if not isinstance(record, dict):
            raise RuntimeError(f"Persisted Stage{stage_number} execution record is not a JSON object")
        if record.get("schema") != EXECUTION_RECORD_SCHEMA:
            raise RuntimeError(
                f"Unsupported Stage{stage_number} execution record schema: {record.get('schema')!r}"
            )
        if record.get("status") != "completed":
            continue
        result = record.get("result")
        if record.get("result_sha256") != _canonical_sha256(result):
            raise RuntimeError(f"Completed Stage{stage_number} result payload was mutated")
        identities = record.get("durable_identities")
        if not isinstance(identities, dict) or not identities:
            raise RuntimeError(f"Completed Stage{stage_number} has no durable identity evidence")
        for name, value in identities.items():
            _merge_identity(ledger, origins, str(name), value, f"stage{stage_number}.result")
    identity = {"values": ledger, "origins": origins}
    return {**identity, "fingerprint": _canonical_sha256(identity)}


def _expected_stage(preflight: dict[str, Any], stage_number: int) -> dict[str, Any]:
    if stage_number not in UPSTREAM_STAGE_ORDER:
        raise RuntimeError(
            f"Stage {stage_number} is not in the frozen Product upstream order {UPSTREAM_STAGE_ORDER}"
        )
    selected, profile_stage = _selected_stage(preflight, stage_number)
    return {
        "stage_number": stage_number,
        "stage_key": str(selected["stage_key"]),
        "implementation": str(selected["implementation"]),
        "adapter_descriptor_hash": str(selected["adapter_descriptor_hash"]).casefold(),
        "parameters_sha256": str(selected["parameters_sha256"]).casefold(),
        "required_inputs": list(selected["required_inputs"]),
        "execution_contract_sha256": str(selected["execution_contract_sha256"]).casefold(),
        "parameters": dict(profile_stage.get("parameters") or {}),
    }


def _evaluate_operation(row: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not str(row.get("operation") or ""):
        reasons.append("missing_operation_key")
    if not _valid_sha256(row.get("source_sha256")):
        reasons.append("missing_inspectable_callable_source_sha256")
    if not str(row.get("callable_module") or ""):
        reasons.append("missing_callable_module")
    if not str(row.get("callable_qualname") or ""):
        reasons.append("missing_callable_qualname")
    if not isinstance(row.get("parameters"), list):
        reasons.append("missing_structured_signature_parameters")

    metadata = row.get("binding_metadata")
    if not isinstance(metadata, dict):
        reasons.append("missing_binding_metadata")
        return reasons
    if int(metadata.get("stage_number") or 0) != int(expected["stage_number"]):
        reasons.append("stage_number_mismatch")
    if str(metadata.get("stage_key") or "") != expected["stage_key"]:
        reasons.append("stage_key_mismatch")
    if str(metadata.get("implementation_key") or "") != expected["implementation"]:
        reasons.append("implementation_mismatch")
    descriptor = metadata.get("adapter_descriptor_hash", metadata.get("descriptor_hash"))
    if str(descriptor or "").casefold() != expected["adapter_descriptor_hash"]:
        reasons.append("adapter_descriptor_hash_mismatch")
    required_inputs = metadata.get("required_inputs")
    if not isinstance(required_inputs, list) or any(
        not isinstance(item, str) or not item for item in required_inputs
    ):
        reasons.append("missing_or_invalid_required_inputs")
    elif list(required_inputs) != expected["required_inputs"]:
        reasons.append("required_inputs_mismatch")
    return reasons


def _execution_record(state: dict[str, Any], stage_number: int) -> dict[str, Any] | None:
    upstream = ((state.get("steps") or {}).get("upstream_execution") or {})
    record = (upstream.get("executions") or {}).get(str(stage_number))
    return dict(record) if isinstance(record, dict) else None


def discover_upstream_bindings(state_path: Path | str, stage_number: int) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    expected = _expected_stage(preflight, stage_number)
    ledger = build_upstream_identity_ledger(state, preflight)
    missing_inputs = [name for name in expected["required_inputs"] if name not in ledger["values"]]
    candidates: list[dict[str, Any]] = []
    exact_rows: list[dict[str, Any]] = []
    for row in _operation_rows(probe):
        reasons = _evaluate_operation(row, expected)
        candidate = {
            "operation": row.get("operation"),
            "callable_module": row.get("callable_module"),
            "callable_qualname": row.get("callable_qualname"),
            "source_sha256": row.get("source_sha256"),
            "exact_match": not reasons,
            "mismatch_reasons": reasons,
        }
        candidates.append(candidate)
        if not reasons:
            exact_rows.append(candidate)

    completed = _execution_record(state, stage_number)
    if completed and completed.get("status") == "completed":
        status = "completed"
    elif missing_inputs:
        status = "unresolved_required_inputs"
    elif len(exact_rows) == 1:
        status = "unique_exact_match"
    elif not exact_rows:
        status = "no_exact_match"
    else:
        status = "ambiguous_exact_matches"
    return {
        "schema": UPSTREAM_DISCOVERY_SCHEMA,
        "status": status,
        "state_path": str(path),
        "stage_number": stage_number,
        "expected_contract": {key: value for key, value in expected.items() if key != "parameters"},
        "identity_ledger_fingerprint": ledger["fingerprint"],
        "resolved_inputs": {
            name: ledger["values"][name]
            for name in expected["required_inputs"]
            if name in ledger["values"]
        },
        "input_origins": {
            name: ledger["origins"][name]
            for name in expected["required_inputs"]
            if name in ledger["origins"]
        },
        "missing_inputs": missing_inputs,
        "structured_callable_count": len(candidates),
        "exact_match_count": len(exact_rows),
        "exact_matches": exact_rows,
        "candidates": candidates,
        "parser_or_string_candidates_are_execution_proof": False,
    }


def _verified_at(previous: Any) -> str:
    if previous is None:
        return _now()
    if not isinstance(previous, dict) or previous.get("schema") != BINDING_SCHEMA:
        raise RuntimeError("Persisted upstream binding uses an unsupported proof schema")
    fingerprint = str(previous.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({key: value for key, value in previous.items() if key != "fingerprint"})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted upstream binding evidence was mutated")
    value = str(previous.get("verified_at") or "")
    if not value:
        raise RuntimeError("Persisted upstream binding lacks verified_at")
    return value


def verify_upstream_binding(
    state_path: Path | str, stage_number: int, operation_key: str
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    expected = _expected_stage(preflight, stage_number)
    ledger = build_upstream_identity_ledger(state, preflight)
    missing = [name for name in expected["required_inputs"] if name not in ledger["values"]]
    if missing:
        raise RuntimeError(f"Stage{stage_number} required inputs are not yet durably resolved: {missing}")
    rows = [
        row for row in _operation_rows(probe) if str(row.get("operation") or "") == operation_key
    ]
    if not rows:
        raise RuntimeError(
            f"Operation {operation_key!r} is not a structured callable observed by the exact runtime probe"
        )
    if len(rows) != 1:
        raise RuntimeError(f"Operation {operation_key!r} is ambiguous across {len(rows)} callable mappings")
    reasons = _evaluate_operation(rows[0], expected)
    if reasons:
        raise RuntimeError(
            f"Operation {operation_key!r} does not match frozen Stage{stage_number} contract: {', '.join(reasons)}"
        )
    row = rows[0]
    upstream = state["steps"]["upstream_execution"]
    bindings = upstream.setdefault("bindings", {})
    previous = bindings.get(str(stage_number))
    verified_at = _verified_at(previous)
    identity = preflight["identity"]
    binding = {
        "schema": BINDING_SCHEMA,
        "status": "verified_not_executed",
        "stage_number": stage_number,
        "stage_key": expected["stage_key"],
        "implementation": expected["implementation"],
        "adapter_descriptor_hash": expected["adapter_descriptor_hash"],
        "parameters_sha256": expected["parameters_sha256"],
        "required_inputs": list(expected["required_inputs"]),
        "execution_contract_sha256": expected["execution_contract_sha256"],
        "frozen_inputs": {name: ledger["values"][name] for name in expected["required_inputs"]},
        "input_origins": {name: ledger["origins"][name] for name in expected["required_inputs"]},
        "identity_ledger_fingerprint": ledger["fingerprint"],
        "operation": operation_key,
        "callable": {
            "mapping_module": row.get("mapping_module"),
            "mapping_name": row.get("mapping_name"),
            "module": row.get("callable_module"),
            "qualname": row.get("callable_qualname"),
            "signature": row.get("signature"),
            "parameters": list(row.get("parameters") or []),
            "source_sha256": str(row["source_sha256"]).casefold(),
        },
        "proof": {
            "preflight_fingerprint": str(identity["fingerprint"]).casefold(),
            "product_run_root_fingerprint": str(state["root_identity"]["fingerprint"]).casefold(),
            "registry_hash": str(identity["registry_hash"]),
            "rocketdict_version": str(identity["core"]["rocketdict_version"]),
            "api_version": str(identity["core"]["api_version"]),
            "api_probe_fingerprint": str(probe["fingerprint"]).casefold(),
            "execution_contract_sha256": expected["execution_contract_sha256"],
            "identity_ledger_fingerprint": ledger["fingerprint"],
            "proof_mode": "live-registry-plus-exact-runtime-callable-v2",
        },
        "verified_at": verified_at,
    }
    binding["fingerprint"] = _canonical_sha256(binding)
    if previous is not None and str(previous.get("fingerprint") or "") != binding["fingerprint"]:
        raise RuntimeError(
            f"Stage{stage_number} already has a different verified binding in this immutable Product run"
        )
    bindings[str(stage_number)] = binding
    upstream["status"] = f"stage{stage_number}_binding_verified"
    upstream["blocked_reason"] = f"verified_stage{stage_number}_binding_not_yet_executed"
    state["status"] = f"ready_for_stage{stage_number}_execution"
    _save(path, state)
    return binding


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
if not isinstance(mapping,dict): raise TypeError(f"{mapping_module}.{mapping_name} is not a dict")
if operation not in mapping: raise KeyError(operation)
fn=mapping[operation]
if not callable(fn): raise TypeError(f"{operation} is not callable")
try: source=inspect.getsource(fn)
except Exception as exc: raise RuntimeError(f"callable source is not inspectable: {exc}") from exc
contract=getattr(fn,attribute,None)
try: json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
except Exception as exc: raise RuntimeError(f"{attribute} is not canonical JSON metadata: {exc}") from exc
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


def _string_list(value: Any, *, context: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise RuntimeError(f"{context} must be a non-empty list of strings")
    if len(set(value)) != len(value):
        raise RuntimeError(f"{context} contains duplicates")
    return list(value)


def _validate_public_contract(
    contract: Any, binding: dict[str, Any], stage_number: int
) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise RuntimeError(
            f"Stage{stage_number} callable does not publish {EXECUTION_CONTRACT_ATTRIBUTE!r}"
        )
    if contract.get("schema") != PUBLIC_EXECUTION_CONTRACT_SCHEMA:
        raise RuntimeError(
            f"Unsupported Stage{stage_number} public execution contract schema: {contract.get('schema')!r}"
        )
    if contract.get("transport") != TRANSPORT:
        raise RuntimeError(
            f"Unsupported Stage{stage_number} execution transport: {contract.get('transport')!r}"
        )
    if not isinstance(contract.get("replay_safe"), bool):
        raise RuntimeError(f"Stage{stage_number} public execution contract must declare replay_safe")
    request = contract.get("request")
    params = request.get("params") if isinstance(request, dict) else None
    if not isinstance(params, dict) or not params:
        raise RuntimeError(
            f"Stage{stage_number} public execution contract request.params must be a non-empty object"
        )
    if any(
        not isinstance(key, str)
        or not key
        or not isinstance(value, str)
        or not value
        for key, value in params.items()
    ):
        raise RuntimeError(
            f"Stage{stage_number} request.params must map non-empty strings to symbolic sources"
        )
    required_inputs = list(binding["required_inputs"])
    input_specs = [
        spec.removeprefix("input:") for spec in params.values() if spec.startswith("input:")
    ]
    if sorted(input_specs) != sorted(required_inputs):
        raise RuntimeError(
            f"Stage{stage_number} execution contract does not map frozen required inputs exactly"
        )
    allowed = {
        *(f"input:{name}" for name in required_inputs),
        "profile:parameters",
        "binding:implementation",
        "binding:stage_number",
        "binding:stage_key",
    }
    unknown = sorted(set(params.values()) - allowed)
    if unknown:
        raise RuntimeError(
            f"Stage{stage_number} execution contract has unsupported request sources: {unknown}"
        )
    if "profile:parameters" not in params.values():
        raise RuntimeError(
            f"Stage{stage_number} execution contract must map frozen Product parameters"
        )
    result = contract.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Stage{stage_number} public execution contract lacks result object")
    required_fields = _string_list(
        result.get("required_fields"), context=f"Stage{stage_number} result.required_fields"
    )
    identity_fields = _string_list(
        result.get("identity_fields"), context=f"Stage{stage_number} result.identity_fields"
    )
    if not set(identity_fields).issubset(required_fields):
        raise RuntimeError(
            f"Stage{stage_number} result identity_fields must be a subset of required_fields"
        )
    normalized_result: dict[str, Any] = {
        "required_fields": required_fields,
        "identity_fields": identity_fields,
    }
    schema_field = result.get("schema_field")
    if schema_field is not None:
        if (
            not isinstance(schema_field, str)
            or not schema_field
            or schema_field not in required_fields
        ):
            raise RuntimeError(f"Stage{stage_number} result.schema_field is invalid")
        schema_values = _string_list(
            result.get("schema_values"), context=f"Stage{stage_number} result.schema_values"
        )
        normalized_result.update(
            {"schema_field": schema_field, "schema_values": schema_values}
        )
    elif result.get("schema_values") is not None:
        raise RuntimeError(f"Stage{stage_number} result.schema_values requires schema_field")
    normalized = {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": TRANSPORT,
        "replay_safe": bool(contract["replay_safe"]),
        "request": {"params": dict(params)},
        "result": normalized_result,
    }
    if normalized != contract:
        raise RuntimeError(
            f"Stage{stage_number} public execution contract contains unsupported/unfrozen fields"
        )
    return normalized


def _binding(state: dict[str, Any], stage_number: int) -> dict[str, Any]:
    binding = (
        (((state.get("steps") or {}).get("upstream_execution") or {}).get("bindings") or {}).get(
            str(stage_number)
        )
    )
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        raise RuntimeError(f"Stage{stage_number} has no current verified runtime binding")
    fingerprint = str(binding.get("fingerprint") or "")
    expected = _canonical_sha256({key: value for key, value in binding.items() if key != "fingerprint"})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError(f"Persisted Stage{stage_number} binding evidence was mutated")
    return binding


def probe_upstream_execution_contract(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    stage_number: int,
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    binding = _binding(state, stage_number)
    callable_row = binding.get("callable") or {}
    mapping_module = str(callable_row.get("mapping_module") or "")
    mapping_name = str(callable_row.get("mapping_name") or "")
    operation = str(binding.get("operation") or "")
    observed_probe_db = Path(
        str((probe.get("database") or {}).get("path") or "")
    ).expanduser().resolve()
    if observed_probe_db != database_path:
        raise RuntimeError(
            f"Stage{stage_number} execution database differs from API probe database"
        )
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
    payload = core._parse_json(
        result.stdout, context=f"Stage{stage_number} public execution-contract probe"
    )
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "rocketdict-workbench-operation-contract-probe/1"
    ):
        raise RuntimeError(f"Unexpected Stage{stage_number} execution-contract probe payload")
    expected_core = (preflight.get("identity") or {}).get("core") or {}
    observed_core = payload.get("core") or {}
    for key in ("rocketdict_version", "api_version"):
        if str(observed_core.get(key) or "") != str(expected_core.get(key) or ""):
            raise RuntimeError(
                f"Stage{stage_number} execution-contract probe {key} differs from Product preflight"
            )
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
            raise RuntimeError(
                f"Stage{stage_number} callable identity drift during execution-contract probe: {key}"
            )
    contract = _validate_public_contract(payload.get("contract"), binding, stage_number)
    return {
        "schema": EXECUTION_PROOF_SCHEMA,
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "preflight_fingerprint": str(
            (preflight.get("identity") or {}).get("fingerprint") or ""
        ).casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "database": str(database_path),
        "core": dict(observed_core),
        "callable": exact,
        "contract_attribute": EXECUTION_CONTRACT_ATTRIBUTE,
        "contract": contract,
        "contract_sha256": _canonical_sha256(contract),
    }


def _proof_fingerprint(proof: dict[str, Any]) -> str:
    fingerprint = str(proof.get("fingerprint") or "").casefold()
    expected = _canonical_sha256(
        {key: value for key, value in proof.items() if key not in {"fingerprint", "verified_at"}}
    )
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted upstream execution-contract proof was mutated")
    return fingerprint


def prove_upstream_execution_contract(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    stage_number: int,
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
            raise RuntimeError(f"Persisted Stage{stage_number} execution proof is not an object")
        _proof_fingerprint(previous)
        verified_at = str(previous.get("verified_at") or "")
        if not verified_at:
            raise RuntimeError(f"Persisted Stage{stage_number} execution proof lacks verified_at")
    proof = {**observed, "verified_at": verified_at}
    proof["fingerprint"] = _canonical_sha256(
        {key: value for key, value in proof.items() if key != "verified_at"}
    )
    if previous is not None and str(previous.get("fingerprint") or "") != proof["fingerprint"]:
        raise RuntimeError(
            f"Exact Stage{stage_number} public execution contract changed inside immutable Product run"
        )
    proofs[str(stage_number)] = proof
    upstream["status"] = f"stage{stage_number}_execution_contract_verified"
    upstream["blocked_reason"] = (
        f"verified_stage{stage_number}_execution_contract_not_yet_dispatched"
    )
    state["status"] = f"ready_for_stage{stage_number}_execution"
    _save(path, state)
    return proof


def _load_proof(
    state: dict[str, Any], binding: dict[str, Any], stage_number: int
) -> dict[str, Any]:
    proof = (
        ((((state.get("steps") or {}).get("upstream_execution") or {}).get("execution_contracts") or {}).get(
            str(stage_number)
        ))
    )
    if not isinstance(proof, dict) or proof.get("schema") != EXECUTION_PROOF_SCHEMA:
        raise RuntimeError(f"Stage{stage_number} has no verified public execution contract")
    _proof_fingerprint(proof)
    if str(proof.get("binding_fingerprint") or "") != str(binding.get("fingerprint") or ""):
        raise RuntimeError(f"Stage{stage_number} execution proof belongs to a different binding")
    contract = _validate_public_contract(proof.get("contract"), binding, stage_number)
    if str(proof.get("contract_sha256") or "") != _canonical_sha256(contract):
        raise RuntimeError(f"Stage{stage_number} execution contract hash drift")
    return proof


def _render_request(
    binding: dict[str, Any],
    profile_stage: dict[str, Any],
    contract: dict[str, Any],
    stage_number: int,
) -> dict[str, Any]:
    parameters = dict(profile_stage.get("parameters") or {})
    if str(binding.get("parameters_sha256") or "").casefold() != _canonical_sha256(parameters):
        raise RuntimeError(f"Stage{stage_number} Product parameters changed after binding")
    values: dict[str, Any] = {}
    frozen_inputs = dict(binding["frozen_inputs"])
    for key, spec in contract["request"]["params"].items():
        if spec.startswith("input:"):
            name = spec.removeprefix("input:")
            if name not in frozen_inputs:
                raise RuntimeError(f"Stage{stage_number} request references unfrozen input {name!r}")
            values[key] = frozen_inputs[name]
        elif spec == "profile:parameters":
            values[key] = parameters
        elif spec == "binding:implementation":
            values[key] = binding["implementation"]
        elif spec == "binding:stage_number":
            values[key] = stage_number
        elif spec == "binding:stage_key":
            values[key] = binding["stage_key"]
        else:
            raise RuntimeError(f"Unsupported Stage{stage_number} request source {spec!r}")
    return values


def plan_upstream_execution(state_path: Path | str, stage_number: int) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    binding = _binding(state, stage_number)
    proof = _load_proof(state, binding, stage_number)
    profile_stage = (((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number)))
    if not isinstance(profile_stage, dict):
        raise RuntimeError(f"Product preflight lost Stage{stage_number} profile")
    params = _render_request(binding, profile_stage, proof["contract"], stage_number)
    request = {"transport": TRANSPORT, "operation": binding["operation"], "params": params}
    return {
        "schema": "rocketdict-workbench-upstream-execution-plan/1",
        "status": "ready",
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "execution_contract_fingerprint": proof["fingerprint"],
        "preflight_fingerprint": str(
            (preflight.get("identity") or {}).get("fingerprint") or ""
        ).casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "request": request,
        "request_sha256": _canonical_sha256(request),
        "result_contract": dict(proof["contract"]["result"]),
        "replay_safe": bool(proof["contract"]["replay_safe"]),
        "database": str(proof["database"]),
    }


def _validate_result(
    result: Any, contract: dict[str, Any], stage_number: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(result, dict):
        raise RuntimeError(f"Stage{stage_number} public API returned non-object result")
    raw = json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    if len(raw) > MAX_PERSISTED_RESULT_BYTES:
        raise RuntimeError(f"Stage{stage_number} public API result is unexpectedly large")
    result_contract = contract["result"]
    missing = [field for field in result_contract["required_fields"] if field not in result]
    if missing:
        raise RuntimeError(f"Stage{stage_number} public API result lacks required fields: {missing}")
    schema_field = result_contract.get("schema_field")
    if (
        schema_field is not None
        and result.get(schema_field) not in result_contract["schema_values"]
    ):
        raise RuntimeError(
            f"Stage{stage_number} public API result schema is outside verified values"
        )
    identities: dict[str, Any] = {}
    for field in result_contract["identity_fields"]:
        value = result.get(field)
        if not _scalar_identity(value):
            raise RuntimeError(
                f"Stage{stage_number} public API result has invalid durable identity {field}={value!r}"
            )
        identities[field] = value
    return dict(result), identities


def _record_fingerprint(record: dict[str, Any]) -> str:
    fingerprint = str(record.get("fingerprint") or "").casefold()
    immutable = {
        key: value
        for key, value in record.items()
        if key
        not in {
            "fingerprint",
            "started_at",
            "completed_at",
            "failed_at",
            "error",
            "attempts",
            "cache_hit",
        }
    }
    expected = _canonical_sha256(immutable)
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted upstream execution record was mutated")
    return fingerprint


def execute_upstream_stage(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    stage_number: int,
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    prove_upstream_execution_contract(core, database_path, path, stage_number)
    plan = plan_upstream_execution(path, stage_number)
    if Path(plan["database"]).resolve() != database_path:
        raise RuntimeError(f"Stage{stage_number} execution plan belongs to a different database")
    state, preflight, _probe = _load_verified_evidence(path)
    binding = _binding(state, stage_number)
    proof = _load_proof(state, binding, stage_number)
    contract = proof["contract"]
    upstream = state["steps"]["upstream_execution"]
    executions = upstream.setdefault("executions", {})
    previous = executions.get(str(stage_number))
    if previous is not None:
        if not isinstance(previous, dict) or previous.get("schema") != EXECUTION_RECORD_SCHEMA:
            raise RuntimeError(f"Persisted Stage{stage_number} execution record is invalid")
        if previous.get("status") == "completed":
            _record_fingerprint(previous)
            if previous.get("request_sha256") != plan["request_sha256"]:
                raise RuntimeError(
                    f"Completed Stage{stage_number} execution belongs to a different request"
                )
            if previous.get("result_sha256") != _canonical_sha256(previous.get("result")):
                raise RuntimeError(f"Completed Stage{stage_number} result was mutated")
            return {**previous, "cache_hit": True, "state_path": str(path)}
        if (
            previous.get("status") in {"dispatch_failed_ambiguous", "dispatching"}
            and not bool(contract["replay_safe"])
        ):
            raise RuntimeError(
                f"Previous Stage{stage_number} dispatch may have mutated the database and is not replay-safe"
            )

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
        {
            key: value
            for key, value in record.items()
            if key not in {"fingerprint", "started_at", "attempts"}
        }
    )
    executions[str(stage_number)] = record
    upstream["status"] = f"stage{stage_number}_dispatching"
    upstream["blocked_reason"] = None
    state["status"] = f"executing_stage{stage_number}"
    _save(path, state)

    params_json = json.dumps(
        plan["request"]["params"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    try:
        raw_result = core.api(
            database_path,
            "call",
            str(binding["operation"]),
            "--params",
            params_json,
            timeout=1800,
        )
        result, identities = _validate_result(raw_result, contract, stage_number)
        prior_ledger = build_upstream_identity_ledger(state, preflight)
        for name, value in identities.items():
            if name in prior_ledger["values"] and prior_ledger["values"][name] != value:
                raise RuntimeError(
                    f"Stage{stage_number} returned conflicting durable identity {name!r}"
                )
    except Exception as exc:
        record["status"] = "dispatch_failed_ambiguous"
        record["failed_at"] = _now()
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        record["fingerprint"] = _canonical_sha256(
            {
                key: value
                for key, value in record.items()
                if key
                not in {"fingerprint", "started_at", "failed_at", "error", "attempts"}
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
        {
            key: value
            for key, value in record.items()
            if key not in {"fingerprint", "started_at", "completed_at", "attempts"}
        }
    )
    upstream["status"] = f"stage{stage_number}_completed"
    upstream["blocked_reason"] = "next_upstream_binding_not_yet_verified"
    state["status"] = f"stage{stage_number}_completed_awaiting_next_upstream_binding"
    _save(path, state)
    return {**record, "cache_hit": False, "state_path": str(path)}


def _persist_block(
    path: Path,
    state: dict[str, Any],
    stage_number: int,
    reason: str,
    diagnostic: dict[str, Any],
) -> None:
    upstream = state["steps"]["upstream_execution"]
    blocks = upstream.setdefault("blocks", {})
    block = {"stage_number": stage_number, "reason": reason, "diagnostic": diagnostic}
    block["fingerprint"] = _canonical_sha256(block)
    blocks[str(stage_number)] = block
    upstream["status"] = f"stage{stage_number}_blocked"
    upstream["blocked_reason"] = reason
    state["status"] = f"blocked_before_stage{stage_number}"
    _save(path, state)


def next_pending_upstream_stage(state_path: Path | str) -> int | None:
    path = Path(state_path).expanduser().resolve()
    state, _preflight, _probe = _load_verified_evidence(path)
    executions = (
        (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {})
    )
    for number in UPSTREAM_STAGE_ORDER:
        record = executions.get(str(number))
        if not isinstance(record, dict) or record.get("status") != "completed":
            return number
    return None


def advance_product_upstream(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    max_stages: int | None = None,
) -> dict[str, Any]:
    """Advance all provable frozen core stages; stop before mutation on ambiguity."""
    path = Path(state_path).expanduser().resolve()
    if max_stages is not None and max_stages <= 0:
        raise ValueError("max_stages must be positive")
    completed_now: list[int] = []
    cache_hits: list[int] = []
    for stage_number in UPSTREAM_STAGE_ORDER:
        state, _preflight, _probe = _load_verified_evidence(path)
        existing = _execution_record(state, stage_number)
        if existing and existing.get("status") == "completed":
            continue
        if max_stages is not None and len(completed_now) >= max_stages:
            break
        discovery = discover_upstream_bindings(path, stage_number)
        if discovery["status"] == "unresolved_required_inputs":
            _persist_block(path, state, stage_number, "unresolved_required_inputs", discovery)
            return {
                "schema": UPSTREAM_PIPELINE_SCHEMA,
                "status": "blocked",
                "completed_now": completed_now,
                "blocked_stage": stage_number,
                "reason": "unresolved_required_inputs",
                "diagnostic": discovery,
                "state_path": str(path),
            }
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
        verify_upstream_binding(path, stage_number, operation)
        try:
            result = execute_upstream_stage(core, database, path, stage_number)
        except RuntimeError as exc:
            state, _preflight, _probe = _load_verified_evidence(path)
            current = _execution_record(state, stage_number)
            if current is None or current.get("status") != "dispatch_failed_ambiguous":
                diagnostic = {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "operation": operation,
                }
                _persist_block(
                    path,
                    state,
                    stage_number,
                    "public_execution_contract_unproven",
                    diagnostic,
                )
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
        if result.get("cache_hit"):
            cache_hits.append(stage_number)
        else:
            completed_now.append(stage_number)

    remaining = next_pending_upstream_stage(path)
    state, _preflight, _probe = _load_verified_evidence(path)
    if remaining is None:
        upstream = state["steps"]["upstream_execution"]
        upstream["status"] = "upstream_core_completed"
        upstream["blocked_reason"] = "workbench_stage18_bridge_not_yet_executed"
        state["status"] = "upstream_core_completed_awaiting_workbench_stage18_bridge"
        _save(path, state)
        status = "upstream_core_completed"
    else:
        status = "progressed"
    return {
        "schema": UPSTREAM_PIPELINE_SCHEMA,
        "status": status,
        "completed_now": completed_now,
        "cache_hits": cache_hits,
        "next_stage": remaining,
        "state_path": str(path),
    }
