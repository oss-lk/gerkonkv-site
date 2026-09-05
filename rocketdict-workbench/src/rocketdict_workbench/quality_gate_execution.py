from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .product_preflight import HARD_QUALITY_STAGE
from .product_profile import QUALITY_GATES
from .upstream_binding import (
    _canonical_sha256,
    _load_verified_evidence,
    _operation_rows,
    _valid_sha256,
)
from .upstream_chain import (
    _available_input_evidence,
    _verified_execution_identities,
    pre_gate_stages,
)
from .upstream_execution import EXECUTION_RECORD_SCHEMA
from .upstream_pipeline import (
    EXECUTION_CONTRACT_ATTRIBUTE,
    EXECUTION_PROOF_SCHEMA,
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    TRANSPORT,
    _OPERATION_CONTRACT_PROBE,
    _validate_public_contract,
    _validate_result,
)

QUALITY_GATE_BINDING_SCHEMA = "rocketdict-workbench-quality-gate-binding/1"
QUALITY_GATE_DISCOVERY_SCHEMA = "rocketdict-workbench-quality-gate-discovery/1"
QUALITY_GATE_SEMANTICS_ATTRIBUTE = "rocketdict_quality_gate_semantics"
PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA = "rocketdict-public-quality-gate/1"
QUALITY_GATE_PROOF_SCHEMA = "rocketdict-workbench-quality-gate-proof/1"
QUALITY_GATE_EXECUTION_SCHEMA = "rocketdict-workbench-quality-gate-execution/1"
QUALITY_GATE_SET_RESULT_SCHEMA = "rocketdict-workbench-quality-gate-set-result/1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _gate_rows(preflight: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    identity = preflight.get("identity") or {}
    frozen = identity.get("quality_gates")
    profile = (preflight.get("profile") or {}).get("quality_gates")
    if not isinstance(frozen, list) or not isinstance(profile, list):
        raise RuntimeError("Product preflight lacks frozen/profile Stage15 quality gates")
    if len(frozen) != len(QUALITY_GATES) or len(profile) != len(QUALITY_GATES):
        raise RuntimeError("Product preflight Stage15 quality gate set is incomplete")
    actual = tuple(str(row.get("implementation") or "") for row in frozen if isinstance(row, dict))
    if actual != QUALITY_GATES:
        raise RuntimeError(f"Frozen Stage15 quality gate identity changed: {actual!r} != {QUALITY_GATES!r}")

    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for index, implementation in enumerate(QUALITY_GATES):
        selected = frozen[index]
        profile_row = profile[index]
        if not isinstance(selected, dict) or not isinstance(profile_row, dict):
            raise RuntimeError(f"Stage15 gate {implementation!r} evidence is not an object")
        if int(selected.get("stage_number") or 0) != HARD_QUALITY_STAGE:
            raise RuntimeError(f"Stage15 gate {implementation!r} frozen stage_number drift")
        if str(selected.get("implementation") or "") != implementation:
            raise RuntimeError(f"Stage15 gate {implementation!r} frozen implementation drift")
        if str(profile_row.get("implementation") or "") != implementation:
            raise RuntimeError(f"Stage15 gate {implementation!r} profile implementation drift")
        if profile_row.get("hard_gate") is not True or profile_row.get("requires_reference") is not False:
            raise RuntimeError(f"Stage15 gate {implementation!r} lost hard/reference-free policy")
        for key in ("stage_key", "adapter_descriptor_hash", "required_inputs"):
            if profile_row.get(key) != selected.get(key):
                raise RuntimeError(f"Stage15 gate {implementation!r} profile/frozen {key} drift")
        parameters = dict(profile_row.get("parameters") or {})
        if str(selected.get("parameters_sha256") or "").casefold() != _canonical_sha256(parameters):
            raise RuntimeError(f"Stage15 gate {implementation!r} parameter hash drift")
        contract = {
            "stage_number": HARD_QUALITY_STAGE,
            "stage_key": selected.get("stage_key"),
            "implementation": implementation,
            "adapter_descriptor_hash": str(selected.get("adapter_descriptor_hash") or "").casefold(),
            "parameters": parameters,
            "required_inputs": list(selected.get("required_inputs") or []),
        }
        if str(selected.get("execution_contract_sha256") or "").casefold() != _canonical_sha256(contract):
            raise RuntimeError(f"Stage15 gate {implementation!r} execution contract hash drift")
        rows.append((dict(selected), dict(profile_row)))

    gate_set = {
        "stage_number": HARD_QUALITY_STAGE,
        "implementations": [row[0]["implementation"] for row in rows],
        "gates": [row[0] for row in rows],
    }
    if str(identity.get("quality_gate_set_sha256") or "").casefold() != _canonical_sha256(gate_set):
        raise RuntimeError("Stage15 quality gate set hash drift")
    return rows


def _ensure_pre_gate_complete(state: dict[str, Any], preflight: dict[str, Any]) -> None:
    executions = (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {})
    if not isinstance(executions, dict):
        raise RuntimeError("Persisted upstream executions are not an object")
    for stage_number in pre_gate_stages(preflight):
        record = executions.get(str(stage_number))
        if not isinstance(record, dict) or record.get("status") != "completed":
            raise RuntimeError(f"Stage15 cannot run before completed Stage {stage_number}")
        _verified_execution_identities(str(stage_number), record)


def _resolve_gate_inputs(
    state: dict[str, Any], preflight: dict[str, Any], gate: dict[str, Any]
) -> dict[str, Any]:
    required = gate.get("required_inputs")
    if not isinstance(required, list) or not required or any(not isinstance(name, str) or not name for name in required):
        raise RuntimeError(f"Stage15 gate {gate.get('implementation')!r} lacks valid required_inputs")
    if len(set(required)) != len(required):
        raise RuntimeError(f"Stage15 gate {gate.get('implementation')!r} has duplicate required_inputs")
    available = _available_input_evidence(state, preflight)
    missing = [name for name in required if name not in available]
    if missing:
        raise RuntimeError(
            f"Stage15 gate {gate.get('implementation')!r} inputs are not uniquely resolvable from immutable/completed evidence: {missing}"
        )
    return {
        "required_inputs": list(required),
        "frozen_inputs": {name: available[name]["value"] for name in required},
        "input_evidence": {name: available[name]["evidence_sources"] for name in required},
    }


def _evaluate_callable(row: dict[str, Any], gate: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not str(row.get("operation") or ""):
        reasons.append("missing_operation_key")
    if not _valid_sha256(row.get("source_sha256")):
        reasons.append("missing_inspectable_callable_source_sha256")
    if not str(row.get("callable_module") or "") or not str(row.get("callable_qualname") or ""):
        reasons.append("missing_callable_identity")
    if not isinstance(row.get("parameters"), list):
        reasons.append("missing_structured_signature_parameters")
    metadata = row.get("binding_metadata")
    if not isinstance(metadata, dict):
        reasons.append("missing_binding_metadata")
        return reasons
    if int(metadata.get("stage_number") or 0) != HARD_QUALITY_STAGE:
        reasons.append("stage_number_mismatch")
    if str(metadata.get("stage_key") or "") != str(gate.get("stage_key") or ""):
        reasons.append("stage_key_mismatch")
    if str(metadata.get("implementation_key") or "") != str(gate.get("implementation") or ""):
        reasons.append("implementation_mismatch")
    descriptor = metadata.get("adapter_descriptor_hash", metadata.get("descriptor_hash"))
    if str(descriptor or "").casefold() != str(gate.get("adapter_descriptor_hash") or "").casefold():
        reasons.append("adapter_descriptor_hash_mismatch")
    required = metadata.get("required_inputs")
    if not isinstance(required, list) or any(not isinstance(name, str) or not name for name in required):
        reasons.append("missing_or_invalid_required_inputs")
    elif list(required) != list(gate.get("required_inputs") or []):
        reasons.append("required_inputs_mismatch")
    return reasons


def discover_quality_gate_bindings(state_path: Path | str) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    _ensure_pre_gate_complete(state, preflight)
    gates = _gate_rows(preflight)
    discoveries = []
    all_unique = True
    for gate, _profile_row in gates:
        try:
            resolution = _resolve_gate_inputs(state, preflight, gate)
            input_error = None
        except RuntimeError as exc:
            resolution = None
            input_error = str(exc)
        candidates = []
        exact = []
        for row in _operation_rows(probe):
            reasons = _evaluate_callable(row, gate)
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
                exact.append(candidate)
        if input_error is not None:
            status = "input_resolution_blocked"
        elif len(exact) == 1:
            status = "unique_exact_match"
        elif not exact:
            status = "no_exact_match"
        else:
            status = "ambiguous_exact_matches"
        all_unique = all_unique and status == "unique_exact_match"
        discoveries.append(
            {
                "implementation": gate["implementation"],
                "status": status,
                "expected_contract": gate,
                "input_resolution": resolution,
                "input_error": input_error,
                "exact_matches": exact,
                "candidates": candidates,
            }
        )
    return {
        "schema": QUALITY_GATE_DISCOVERY_SCHEMA,
        "status": "all_unique_exact_matches" if all_unique else "blocked",
        "stage_number": HARD_QUALITY_STAGE,
        "quality_gate_set_sha256": str((preflight.get("identity") or {}).get("quality_gate_set_sha256") or "").casefold(),
        "gates": discoveries,
        "state_path": str(path),
        "parser_or_string_candidates_are_execution_proof": False,
    }


def verify_quality_gate_bindings(state_path: Path | str) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    discovery = discover_quality_gate_bindings(path)
    if discovery["status"] != "all_unique_exact_matches":
        raise RuntimeError("Stage15 hard-gate binding discovery is not uniquely satisfied")
    gate_rows = {row["implementation"]: row for row, _profile in _gate_rows(preflight)}
    upstream = state["steps"]["upstream_execution"]
    quality = upstream.setdefault("quality_gate", {})
    bindings = quality.setdefault("bindings", {})
    output = {}
    for row in discovery["gates"]:
        implementation = row["implementation"]
        gate = gate_rows[implementation]
        operation_key = str(row["exact_matches"][0]["operation"])
        runtime_rows = [r for r in _operation_rows(probe) if str(r.get("operation") or "") == operation_key]
        if len(runtime_rows) != 1:
            raise RuntimeError(f"Stage15 gate {implementation!r} operation evidence is not unique")
        runtime = runtime_rows[0]
        resolution = row["input_resolution"]
        previous = bindings.get(implementation)
        verified_at = _now()
        if previous is not None:
            if not isinstance(previous, dict) or previous.get("schema") != QUALITY_GATE_BINDING_SCHEMA:
                raise RuntimeError(f"Persisted Stage15 gate {implementation!r} binding schema drift")
            old_fp = str(previous.get("fingerprint") or "").casefold()
            expected_old = _canonical_sha256({k: v for k, v in previous.items() if k != "fingerprint"})
            if not _valid_sha256(old_fp) or old_fp != expected_old:
                raise RuntimeError(f"Persisted Stage15 gate {implementation!r} binding was mutated")
            verified_at = str(previous.get("verified_at") or "")
        binding = {
            "schema": QUALITY_GATE_BINDING_SCHEMA,
            "stage_number": HARD_QUALITY_STAGE,
            "implementation": implementation,
            "stage_key": gate["stage_key"],
            "adapter_descriptor_hash": str(gate["adapter_descriptor_hash"]).casefold(),
            "parameters_sha256": str(gate["parameters_sha256"]).casefold(),
            "required_inputs": list(gate["required_inputs"]),
            "execution_contract_sha256": str(gate["execution_contract_sha256"]).casefold(),
            "frozen_inputs": dict(resolution["frozen_inputs"]),
            "input_evidence": dict(resolution["input_evidence"]),
            "operation": operation_key,
            "callable": {
                "mapping_module": runtime.get("mapping_module"),
                "mapping_name": runtime.get("mapping_name"),
                "module": runtime.get("callable_module"),
                "qualname": runtime.get("callable_qualname"),
                "signature": runtime.get("signature"),
                "parameters": list(runtime.get("parameters") or []),
                "source_sha256": str(runtime.get("source_sha256") or "").casefold(),
            },
            "proof": {
                "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
                "product_run_root_fingerprint": str((state.get("root_identity") or {}).get("fingerprint") or "").casefold(),
                "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
                "quality_gate_set_sha256": str((preflight.get("identity") or {}).get("quality_gate_set_sha256") or "").casefold(),
            },
            "verified_at": verified_at,
        }
        binding["fingerprint"] = _canonical_sha256(binding)
        if previous is not None and previous.get("fingerprint") != binding["fingerprint"]:
            raise RuntimeError(f"Stage15 gate {implementation!r} binding changed inside immutable Product run")
        bindings[implementation] = binding
        output[implementation] = binding
    quality["status"] = "bindings_verified"
    quality["quality_gate_set_sha256"] = str((preflight.get("identity") or {}).get("quality_gate_set_sha256") or "").casefold()
    _save(path, state)
    return {"status": "bindings_verified", "bindings": output, "state_path": str(path)}


def _validate_semantics(contract: Any, execution_contract: dict[str, Any], implementation: str) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise RuntimeError(
            f"Stage15 gate {implementation!r} does not publish {QUALITY_GATE_SEMANTICS_ATTRIBUTE!r}"
        )
    if contract.get("schema") != PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA:
        raise RuntimeError(f"Stage15 gate {implementation!r} publishes unsupported quality semantics schema")
    if int(contract.get("stage_number") or 0) != HARD_QUALITY_STAGE:
        raise RuntimeError(f"Stage15 gate {implementation!r} quality semantics stage_number drift")
    if contract.get("hard_gate") is not True or contract.get("failure_blocks_downstream") is not True:
        raise RuntimeError(f"Stage15 gate {implementation!r} semantics must be fail-closed hard gate")
    condition = contract.get("pass_condition")
    if not isinstance(condition, dict) or set(condition) != {"field", "equals"}:
        raise RuntimeError(f"Stage15 gate {implementation!r} pass_condition must contain exactly field/equals")
    field = condition.get("field")
    expected = condition.get("equals")
    if not isinstance(field, str) or not field:
        raise RuntimeError(f"Stage15 gate {implementation!r} pass field is invalid")
    if expected is None or isinstance(expected, (dict, list, float)):
        raise RuntimeError(f"Stage15 gate {implementation!r} pass value must be an exact bool/int/string scalar")
    if isinstance(expected, int) and not isinstance(expected, bool) and abs(expected) > 2**53:
        raise RuntimeError(f"Stage15 gate {implementation!r} pass integer is outside canonical JSON-safe range")
    required_fields = execution_contract["result"]["required_fields"]
    if field not in required_fields:
        raise RuntimeError(f"Stage15 gate {implementation!r} pass field is not required by execution result contract")
    normalized = {
        "schema": PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
        "stage_number": HARD_QUALITY_STAGE,
        "hard_gate": True,
        "failure_blocks_downstream": True,
        "pass_condition": {"field": field, "equals": expected},
    }
    if normalized != contract:
        raise RuntimeError(f"Stage15 gate {implementation!r} quality semantics contains unsupported fields")
    return normalized


def _probe_attribute(
    core: RocketDictCore,
    database: Path,
    binding: dict[str, Any],
    attribute: str,
    *,
    context: str,
) -> dict[str, Any]:
    callable_row = binding.get("callable") or {}
    args = [
        "-c",
        _OPERATION_CONTRACT_PROBE,
        str(callable_row.get("mapping_module") or ""),
        str(callable_row.get("mapping_name") or ""),
        str(binding.get("operation") or ""),
        str(database),
        attribute,
    ]
    raw = core._run(args, timeout=120)
    payload = core._parse_json(raw.stdout, context=context)
    if not isinstance(payload, dict) or payload.get("schema") != "rocketdict-workbench-operation-contract-probe/1":
        raise RuntimeError(f"Unexpected {context} payload")
    expected = {
        "mapping_module": str(callable_row.get("mapping_module") or ""),
        "mapping_name": str(callable_row.get("mapping_name") or ""),
        "operation": str(binding.get("operation") or ""),
        "callable_module": str(callable_row.get("module") or ""),
        "callable_qualname": str(callable_row.get("qualname") or ""),
        "callable_source_sha256": str(callable_row.get("source_sha256") or "").casefold(),
        "contract_attribute": attribute,
    }
    for key, value in expected.items():
        if str(payload.get(key) or "").casefold() != str(value).casefold():
            raise RuntimeError(f"{context} callable/attribute identity drift: {key}")
    return payload


def prove_quality_gate_contracts(
    core: RocketDictCore, database: Path | str, state_path: Path | str
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    _ensure_pre_gate_complete(state, preflight)
    verify_quality_gate_bindings(path)
    state, preflight, probe = _load_verified_evidence(path)
    probe_database = Path(str((probe.get("database") or {}).get("path") or "")).expanduser().resolve()
    if probe_database != database_path:
        raise RuntimeError("Stage15 quality gate database differs from API probe database")
    expected_core = (preflight.get("identity") or {}).get("core") or {}
    quality = state["steps"]["upstream_execution"].setdefault("quality_gate", {})
    bindings = quality.get("bindings") or {}
    proofs = quality.setdefault("proofs", {})
    output = {}
    for implementation in QUALITY_GATES:
        binding = bindings.get(implementation)
        if not isinstance(binding, dict):
            raise RuntimeError(f"Stage15 gate {implementation!r} lacks verified binding")
        execution_payload = _probe_attribute(
            core,
            database_path,
            binding,
            EXECUTION_CONTRACT_ATTRIBUTE,
            context=f"Stage15 gate {implementation} execution-contract probe",
        )
        semantics_payload = _probe_attribute(
            core,
            database_path,
            binding,
            QUALITY_GATE_SEMANTICS_ATTRIBUTE,
            context=f"Stage15 gate {implementation} quality-semantics probe",
        )
        for payload in (execution_payload, semantics_payload):
            observed_core = payload.get("core") or {}
            for key in ("rocketdict_version", "api_version"):
                if str(observed_core.get(key) or "") != str(expected_core.get(key) or ""):
                    raise RuntimeError(f"Stage15 gate {implementation!r} {key} differs from Product preflight")
        execution_contract = _validate_public_contract(execution_payload.get("contract"), binding, HARD_QUALITY_STAGE)
        semantics = _validate_semantics(semantics_payload.get("contract"), execution_contract, implementation)
        previous = proofs.get(implementation)
        verified_at = _now()
        if previous is not None:
            if not isinstance(previous, dict) or previous.get("schema") != QUALITY_GATE_PROOF_SCHEMA:
                raise RuntimeError(f"Persisted Stage15 gate {implementation!r} proof schema drift")
            old_fp = str(previous.get("fingerprint") or "").casefold()
            expected_old = _canonical_sha256({k: v for k, v in previous.items() if k not in {"fingerprint", "verified_at"}})
            if not _valid_sha256(old_fp) or old_fp != expected_old:
                raise RuntimeError(f"Persisted Stage15 gate {implementation!r} proof was mutated")
            verified_at = str(previous.get("verified_at") or "")
        proof = {
            "schema": QUALITY_GATE_PROOF_SCHEMA,
            "stage_number": HARD_QUALITY_STAGE,
            "implementation": implementation,
            "binding_fingerprint": binding["fingerprint"],
            "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
            "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
            "database": str(database_path),
            "execution_contract": execution_contract,
            "execution_contract_sha256": _canonical_sha256(execution_contract),
            "quality_semantics": semantics,
            "quality_semantics_sha256": _canonical_sha256(semantics),
            "verified_at": verified_at,
        }
        proof["fingerprint"] = _canonical_sha256({k: v for k, v in proof.items() if k != "verified_at"})
        if previous is not None and previous.get("fingerprint") != proof["fingerprint"]:
            raise RuntimeError(f"Stage15 gate {implementation!r} public contracts changed inside immutable Product run")
        proofs[implementation] = proof
        output[implementation] = proof
    quality["status"] = "contracts_verified"
    _save(path, state)
    return {"status": "contracts_verified", "proofs": output, "state_path": str(path)}


def _render_gate_request(binding: dict[str, Any], profile_row: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(profile_row.get("parameters") or {})
    if str(binding.get("parameters_sha256") or "").casefold() != _canonical_sha256(parameters):
        raise RuntimeError(f"Stage15 gate {binding.get('implementation')!r} parameters changed after binding")
    frozen_inputs = dict(binding.get("frozen_inputs") or {})
    rendered: dict[str, Any] = {}
    for key, spec in contract["request"]["params"].items():
        if spec.startswith("input:"):
            name = spec.removeprefix("input:")
            if name not in frozen_inputs:
                raise RuntimeError(f"Stage15 gate request references unfrozen input {name!r}")
            rendered[key] = frozen_inputs[name]
        elif spec == "profile:parameters":
            rendered[key] = parameters
        elif spec == "binding:implementation":
            rendered[key] = binding["implementation"]
        elif spec == "binding:stage_number":
            rendered[key] = HARD_QUALITY_STAGE
        elif spec == "binding:stage_key":
            rendered[key] = binding["stage_key"]
        else:
            raise RuntimeError(f"Unsupported Stage15 gate request source {spec!r}")
    return rendered


def _validate_completed_gate_record(record: dict[str, Any], implementation: str) -> bool:
    if record.get("schema") != QUALITY_GATE_EXECUTION_SCHEMA or record.get("status") != "completed":
        raise RuntimeError(f"Persisted Stage15 gate {implementation!r} execution record is not completed/current")
    result = record.get("result")
    if not isinstance(result, dict) or record.get("result_sha256") != _canonical_sha256(result):
        raise RuntimeError(f"Persisted Stage15 gate {implementation!r} result was mutated")
    fp = str(record.get("fingerprint") or "").casefold()
    immutable = {k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "completed_at", "failed_at", "error", "attempts", "cache_hit"}}
    if not _valid_sha256(fp) or fp != _canonical_sha256(immutable):
        raise RuntimeError(f"Persisted Stage15 gate {implementation!r} execution evidence was mutated")
    return bool(record.get("passed"))


def execute_quality_gates(
    core: RocketDictCore, database: Path | str, state_path: Path | str
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    # Two-phase safety: prove all three bindings/contracts before the first dispatch.
    prove_quality_gate_contracts(core, database_path, path)
    state, preflight, _probe = _load_verified_evidence(path)
    _ensure_pre_gate_complete(state, preflight)
    quality = state["steps"]["upstream_execution"].setdefault("quality_gate", {})
    bindings = quality.get("bindings") or {}
    proofs = quality.get("proofs") or {}
    executions = quality.setdefault("executions", {})
    profile_rows = {
        str(row.get("implementation") or ""): row
        for row in ((preflight.get("profile") or {}).get("quality_gates") or [])
        if isinstance(row, dict)
    }
    completed_now: list[str] = []
    for implementation in QUALITY_GATES:
        binding = bindings.get(implementation)
        proof = proofs.get(implementation)
        profile_row = profile_rows.get(implementation)
        if not isinstance(binding, dict) or not isinstance(proof, dict) or not isinstance(profile_row, dict):
            raise RuntimeError(f"Stage15 gate {implementation!r} lost binding/proof/profile evidence")
        previous = executions.get(implementation)
        if isinstance(previous, dict) and previous.get("status") == "completed":
            passed = _validate_completed_gate_record(previous, implementation)
            if not passed:
                quality["status"] = "failed"
                state["status"] = "stage15_hard_gate_failed"
                _save(path, state)
                return {
                    "schema": QUALITY_GATE_SET_RESULT_SCHEMA,
                    "status": "failed",
                    "failed_gate": implementation,
                    "completed_now": completed_now,
                    "state_path": str(path),
                }
            continue
        execution_contract = proof.get("execution_contract")
        semantics = proof.get("quality_semantics")
        if not isinstance(execution_contract, dict) or not isinstance(semantics, dict):
            raise RuntimeError(f"Stage15 gate {implementation!r} proof lost public contracts")
        params = _render_gate_request(binding, profile_row, execution_contract)
        request = {"transport": TRANSPORT, "operation": binding["operation"], "params": params}
        request_sha = _canonical_sha256(request)
        if isinstance(previous, dict) and previous.get("status") in {"dispatching", "dispatch_failed_ambiguous"} and not execution_contract["replay_safe"]:
            raise RuntimeError(
                f"Previous Stage15 gate {implementation!r} dispatch may have mutated the database and is not replay-safe"
            )
        attempts = int(previous.get("attempts") or 0) + 1 if isinstance(previous, dict) else 1
        record: dict[str, Any] = {
            "schema": QUALITY_GATE_EXECUTION_SCHEMA,
            "status": "dispatching",
            "stage_number": HARD_QUALITY_STAGE,
            "implementation": implementation,
            "binding_fingerprint": binding["fingerprint"],
            "proof_fingerprint": proof["fingerprint"],
            "request": request,
            "request_sha256": request_sha,
            "replay_safe": bool(execution_contract["replay_safe"]),
            "attempts": attempts,
            "started_at": _now(),
        }
        record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "attempts"}})
        executions[implementation] = record
        quality["status"] = f"dispatching:{implementation}"
        state["status"] = "executing_stage15_hard_quality_gates"
        _save(path, state)
        params_json = json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        try:
            raw = core.api(database_path, "call", str(binding["operation"]), "--params", params_json, timeout=1800)
            result, identities = _validate_result(raw, execution_contract, HARD_QUALITY_STAGE)
        except Exception as exc:
            record["status"] = "dispatch_failed_ambiguous"
            record["failed_at"] = _now()
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
            record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "failed_at", "error", "attempts"}})
            quality["status"] = "ambiguous_failure"
            quality["blocked_reason"] = (
                "retry_explicitly_allowed_by_verified_public_contract"
                if execution_contract["replay_safe"]
                else "manual_reconciliation_required_before_replay"
            )
            state["status"] = "failed"
            _save(path, state)
            raise
        condition = semantics["pass_condition"]
        passed = result.get(condition["field"]) == condition["equals"]
        record.update(
            {
                "status": "completed",
                "completed_at": _now(),
                "result": result,
                "result_sha256": _canonical_sha256(result),
                "durable_identities": identities,
                "passed": passed,
                "pass_field": condition["field"],
                "pass_expected": condition["equals"],
                "pass_observed": result.get(condition["field"]),
            }
        )
        record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "completed_at", "attempts"}})
        executions[implementation] = record
        completed_now.append(implementation)
        _save(path, state)
        if not passed:
            quality["status"] = "failed"
            quality["failed_gate"] = implementation
            quality["blocked_reason"] = "hard_quality_gate_returned_non_pass_value"
            state["status"] = "stage15_hard_gate_failed"
            _save(path, state)
            return {
                "schema": QUALITY_GATE_SET_RESULT_SCHEMA,
                "status": "failed",
                "failed_gate": implementation,
                "completed_now": completed_now,
                "observed": result.get(condition["field"]),
                "expected": condition["equals"],
                "state_path": str(path),
            }

    state, preflight, _probe = _load_verified_evidence(path)
    quality = state["steps"]["upstream_execution"].setdefault("quality_gate", {})
    executions = quality.get("executions") or {}
    record_hashes: dict[str, str] = {}
    for implementation in QUALITY_GATES:
        record = executions.get(implementation)
        if not isinstance(record, dict) or not _validate_completed_gate_record(record, implementation):
            raise RuntimeError(f"Stage15 gate {implementation!r} did not produce verified PASS evidence")
        record_hashes[implementation] = str(record["fingerprint"]).casefold()
    set_result = {
        "schema": QUALITY_GATE_SET_RESULT_SCHEMA,
        "status": "passed",
        "stage_number": HARD_QUALITY_STAGE,
        "quality_gate_set_sha256": str((preflight.get("identity") or {}).get("quality_gate_set_sha256") or "").casefold(),
        "gate_execution_fingerprints": record_hashes,
        "all_hard_gates_passed": True,
    }
    set_result["fingerprint"] = _canonical_sha256(set_result)
    previous_set = quality.get("set_result")
    if previous_set is not None and previous_set != set_result:
        raise RuntimeError("Stage15 aggregate PASS evidence changed inside immutable Product run")
    quality["set_result"] = set_result
    quality["status"] = "passed"
    quality["blocked_reason"] = None
    state["status"] = "stage15_hard_gates_passed_awaiting_stage16"
    _save(path, state)
    return {**set_result, "completed_now": completed_now, "state_path": str(path)}


def require_quality_gate_pass(state_path: Path | str) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, _probe = _load_verified_evidence(path)
    quality = (((state.get("steps") or {}).get("upstream_execution") or {}).get("quality_gate") or {})
    set_result = quality.get("set_result")
    if not isinstance(set_result, dict) or set_result.get("schema") != QUALITY_GATE_SET_RESULT_SCHEMA:
        raise RuntimeError("Stage16 is blocked: Stage15 has no aggregate hard-gate PASS evidence")
    fp = str(set_result.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({k: v for k, v in set_result.items() if k != "fingerprint"})
    if not _valid_sha256(fp) or fp != expected:
        raise RuntimeError("Stage15 aggregate hard-gate PASS evidence was mutated")
    if set_result.get("status") != "passed" or set_result.get("all_hard_gates_passed") is not True:
        raise RuntimeError("Stage16 is blocked: Stage15 hard gates did not all pass")
    expected_set_sha = str((preflight.get("identity") or {}).get("quality_gate_set_sha256") or "").casefold()
    if str(set_result.get("quality_gate_set_sha256") or "").casefold() != expected_set_sha:
        raise RuntimeError("Stage15 PASS evidence belongs to a different frozen quality-gate set")
    fingerprints = set_result.get("gate_execution_fingerprints")
    executions = quality.get("executions") or {}
    if not isinstance(fingerprints, dict) or set(fingerprints) != set(QUALITY_GATES):
        raise RuntimeError("Stage15 aggregate PASS evidence does not cover the complete hard-gate set")
    for implementation in QUALITY_GATES:
        record = executions.get(implementation)
        if not isinstance(record, dict) or not _validate_completed_gate_record(record, implementation):
            raise RuntimeError(f"Stage15 gate {implementation!r} PASS evidence is missing/mutated")
        if str(record.get("fingerprint") or "").casefold() != str(fingerprints[implementation]).casefold():
            raise RuntimeError(f"Stage15 gate {implementation!r} aggregate fingerprint drift")
    return set_result
