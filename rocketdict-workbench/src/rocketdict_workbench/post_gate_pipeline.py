from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from .aligned_lexical import POLICY_KEY, _helper_code, run_product_aligned_lexical_extraction
from .core import RocketDictCore
from .quality_gate_execution import require_quality_gate_pass
from .upstream_binding import (
    BINDING_SCHEMA,
    _canonical_sha256,
    _load_verified_evidence,
    _operation_rows,
    _save,
    _valid_sha256,
)
from .upstream_chain import _available_input_evidence, _evaluate, _expected, resolve_stage_inputs
from .upstream_execution import EXECUTION_PROOF_SCHEMA, EXECUTION_RECORD_SCHEMA
from .upstream_pipeline import (
    EXECUTION_CONTRACT_ATTRIBUTE,
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    TRANSPORT,
    _OPERATION_CONTRACT_PROBE,
    _record_fingerprint,
    _validate_public_contract,
    _validate_result,
)

POST_GATE_CORE_STAGES = (16, 17, 19)
POST_GATE_ORDER = (16, 17, 18, 19)
POST_GATE_DISCOVERY_SCHEMA = "rocketdict-workbench-post-gate-discovery/1"
POST_GATE_PIPELINE_SCHEMA = "rocketdict-workbench-post-gate-pipeline/1"
POST_GATE_PLAN_SCHEMA = "rocketdict-workbench-post-gate-execution-plan/1"
STAGE18_POLICY_SCHEMA = "rocketdict-workbench-stage18-policy/1"
STAGE18_EXECUTION_SCHEMA = EXECUTION_RECORD_SCHEMA


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stage18_runner_sha256() -> str:
    try:
        source = inspect.getsource(run_product_aligned_lexical_extraction)
    except Exception as exc:  # pragma: no cover - installed source should remain inspectable
        raise RuntimeError(f"Workbench Stage18 runner source is not inspectable: {exc}") from exc
    return hashlib.sha256((source + "\n" + _helper_code()).encode("utf-8")).hexdigest()


def _quality_fingerprint(path: Path) -> str:
    evidence = require_quality_gate_pass(path)
    value = str(evidence.get("fingerprint") or "").casefold()
    if not _valid_sha256(value):
        raise RuntimeError("Stage15 aggregate PASS evidence lacks a valid fingerprint")
    return value


def _post_gate_context(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    state, preflight, probe = _load_verified_evidence(path)
    pass_fingerprint = _quality_fingerprint(path)
    return state, preflight, probe, pass_fingerprint


def discover_post_gate_stage(state_path: Path | str, stage_number: int) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    if stage_number not in POST_GATE_CORE_STAGES:
        raise RuntimeError(f"Stage {stage_number} is not a post-gate core stage {POST_GATE_CORE_STAGES}")
    state, preflight, probe, pass_fingerprint = _post_gate_context(path)
    expected = _expected(preflight, stage_number)
    try:
        resolution = resolve_stage_inputs(state, preflight, stage_number)
        input_error = None
    except RuntimeError as exc:
        resolution = None
        input_error = str(exc)
    candidates = []
    exact = []
    for row in _operation_rows(probe):
        reasons = _evaluate(row, expected)
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
    return {
        "schema": POST_GATE_DISCOVERY_SCHEMA,
        "status": status,
        "stage_number": stage_number,
        "expected_contract": expected,
        "input_resolution": resolution,
        "input_error": input_error,
        "exact_matches": exact,
        "candidates": candidates,
        "quality_gate_pass_fingerprint": pass_fingerprint,
        "state_path": str(path),
    }


def _stable_verified_at(previous: Any, stage_number: int) -> str:
    if previous is None:
        return _now()
    if not isinstance(previous, dict) or previous.get("schema") != BINDING_SCHEMA:
        raise RuntimeError(f"Persisted Stage {stage_number} binding schema drift")
    fingerprint = str(previous.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({k: v for k, v in previous.items() if k != "fingerprint"})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError(f"Persisted Stage {stage_number} binding evidence was mutated")
    return str(previous.get("verified_at") or "")


def verify_post_gate_binding(
    state_path: Path | str, stage_number: int, operation_key: str
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe, pass_fingerprint = _post_gate_context(path)
    discovery = discover_post_gate_stage(path, stage_number)
    if discovery["status"] != "unique_exact_match":
        raise RuntimeError(f"Stage {stage_number} post-gate binding is not uniquely discoverable: {discovery['status']}")
    exact_operation = str(discovery["exact_matches"][0]["operation"])
    if operation_key != exact_operation:
        raise RuntimeError(f"Stage {stage_number} requested operation differs from unique exact runtime match")
    runtime_rows = [row for row in _operation_rows(probe) if str(row.get("operation") or "") == operation_key]
    if len(runtime_rows) != 1:
        raise RuntimeError(f"Stage {stage_number} structured runtime operation evidence is not unique")
    expected = discovery["expected_contract"]
    resolution = discovery["input_resolution"]
    row = runtime_rows[0]
    upstream = state["steps"]["upstream_execution"]
    bindings = upstream.setdefault("bindings", {})
    previous = bindings.get(str(stage_number))
    verified_at = _stable_verified_at(previous, stage_number)
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
        "frozen_inputs": dict(resolution["frozen_inputs"]),
        "input_evidence": dict(resolution["input_evidence"]),
        "operation": operation_key,
        "callable": {
            "mapping_module": row.get("mapping_module"),
            "mapping_name": row.get("mapping_name"),
            "module": row.get("callable_module"),
            "qualname": row.get("callable_qualname"),
            "signature": row.get("signature"),
            "parameters": list(row.get("parameters") or []),
            "source_sha256": str(row.get("source_sha256") or "").casefold(),
        },
        "proof": {
            "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
            "product_run_root_fingerprint": str((state.get("root_identity") or {}).get("fingerprint") or "").casefold(),
            "registry_hash": str((preflight.get("identity") or {}).get("registry_hash") or ""),
            "rocketdict_version": str(((preflight.get("identity") or {}).get("core") or {}).get("rocketdict_version") or ""),
            "api_version": str(((preflight.get("identity") or {}).get("core") or {}).get("api_version") or ""),
            "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
            "execution_contract_sha256": expected["execution_contract_sha256"],
            "quality_gate_pass_fingerprint": pass_fingerprint,
            "proof_mode": "stage15-pass-plus-live-registry-plus-exact-runtime-callable-v1",
            "input_resolution_mode": "exact-name-source-or-hash-verified-completed-identity-v2",
        },
        "verified_at": verified_at,
    }
    binding["fingerprint"] = _canonical_sha256(binding)
    if previous is not None and previous.get("fingerprint") != binding["fingerprint"]:
        raise RuntimeError(f"Stage {stage_number} binding changed inside immutable Product run")
    bindings[str(stage_number)] = binding
    _save(path, state)
    return {"status": "binding_verified", "binding": binding, "state_path": str(path)}


def _binding(state: dict[str, Any], stage_number: int, pass_fingerprint: str) -> dict[str, Any]:
    row = ((((state.get("steps") or {}).get("upstream_execution") or {}).get("bindings") or {}).get(str(stage_number)))
    if not isinstance(row, dict) or row.get("schema") != BINDING_SCHEMA:
        raise RuntimeError(f"Stage {stage_number} has no current post-gate binding")
    fp = str(row.get("fingerprint") or "").casefold()
    if not _valid_sha256(fp) or fp != _canonical_sha256({k: v for k, v in row.items() if k != "fingerprint"}):
        raise RuntimeError(f"Stage {stage_number} binding evidence was mutated")
    if str((row.get("proof") or {}).get("quality_gate_pass_fingerprint") or "").casefold() != pass_fingerprint:
        raise RuntimeError(f"Stage {stage_number} binding belongs to different Stage15 PASS evidence")
    return row


def _profile_stage(preflight: dict[str, Any], stage_number: int) -> dict[str, Any]:
    row = (((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number)))
    if not isinstance(row, dict):
        raise RuntimeError(f"Product preflight lost Stage {stage_number} profile")
    return row


def prove_post_gate_execution_contract(
    core: RocketDictCore, database: Path | str, state_path: Path | str, stage_number: int
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe, pass_fingerprint = _post_gate_context(path)
    binding = _binding(state, stage_number, pass_fingerprint)
    callable_row = binding["callable"]
    probe_database = Path(str((probe.get("database") or {}).get("path") or "")).expanduser().resolve()
    if probe_database != database_path:
        raise RuntimeError(f"Stage {stage_number} execution database differs from API probe database")
    raw = core._run(
        [
            "-c",
            _OPERATION_CONTRACT_PROBE,
            str(callable_row.get("mapping_module") or ""),
            str(callable_row.get("mapping_name") or ""),
            str(binding.get("operation") or ""),
            str(database_path),
            EXECUTION_CONTRACT_ATTRIBUTE,
        ],
        timeout=120,
    )
    payload = core._parse_json(raw.stdout, context=f"Stage {stage_number} public execution-contract probe")
    if not isinstance(payload, dict) or payload.get("schema") != "rocketdict-workbench-operation-contract-probe/1":
        raise RuntimeError(f"Unexpected Stage {stage_number} execution-contract probe payload")
    expected_core = (preflight.get("identity") or {}).get("core") or {}
    for key in ("rocketdict_version", "api_version"):
        if str((payload.get("core") or {}).get(key) or "") != str(expected_core.get(key) or ""):
            raise RuntimeError(f"Stage {stage_number} execution-contract probe {key} differs from Product preflight")
    exact = {
        "mapping_module": str(callable_row.get("mapping_module") or ""),
        "mapping_name": str(callable_row.get("mapping_name") or ""),
        "operation": str(binding.get("operation") or ""),
        "callable_module": str(callable_row.get("module") or ""),
        "callable_qualname": str(callable_row.get("qualname") or ""),
        "callable_source_sha256": str(callable_row.get("source_sha256") or "").casefold(),
        "contract_attribute": EXECUTION_CONTRACT_ATTRIBUTE,
    }
    for key, value in exact.items():
        if str(payload.get(key) or "").casefold() != str(value).casefold():
            raise RuntimeError(f"Stage {stage_number} callable identity drift during execution-contract probe: {key}")
    contract = _validate_public_contract(payload.get("contract"), binding, stage_number)
    observed = {
        "schema": EXECUTION_PROOF_SCHEMA,
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "quality_gate_pass_fingerprint": pass_fingerprint,
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
        "api_probe_fingerprint": str(probe.get("fingerprint") or "").casefold(),
        "database": str(database_path),
        "core": dict(payload.get("core") or {}),
        "callable": {k: v for k, v in exact.items() if k != "contract_attribute"},
        "contract_attribute": EXECUTION_CONTRACT_ATTRIBUTE,
        "contract": contract,
        "contract_sha256": _canonical_sha256(contract),
    }
    upstream = state["steps"]["upstream_execution"]
    proofs = upstream.setdefault("execution_contracts", {})
    previous = proofs.get(str(stage_number))
    verified_at = _now()
    if previous is not None:
        if not isinstance(previous, dict):
            raise RuntimeError(f"Persisted Stage {stage_number} execution proof is invalid")
        old_fp = str(previous.get("fingerprint") or "").casefold()
        expected_old = _canonical_sha256({k: v for k, v in previous.items() if k not in {"fingerprint", "verified_at"}})
        if not _valid_sha256(old_fp) or old_fp != expected_old:
            raise RuntimeError(f"Persisted Stage {stage_number} execution proof was mutated")
        verified_at = str(previous.get("verified_at") or "")
    proof = {**observed, "verified_at": verified_at}
    proof["fingerprint"] = _canonical_sha256({k: v for k, v in proof.items() if k != "verified_at"})
    if previous is not None and previous.get("fingerprint") != proof["fingerprint"]:
        raise RuntimeError(f"Stage {stage_number} public execution contract changed inside immutable Product run")
    proofs[str(stage_number)] = proof
    _save(path, state)
    return proof


def _proof(state: dict[str, Any], binding: dict[str, Any], stage_number: int, pass_fingerprint: str) -> dict[str, Any]:
    row = (((((state.get("steps") or {}).get("upstream_execution") or {}).get("execution_contracts") or {}).get(str(stage_number))))
    if not isinstance(row, dict) or row.get("schema") != EXECUTION_PROOF_SCHEMA:
        raise RuntimeError(f"Stage {stage_number} has no verified public execution contract")
    fp = str(row.get("fingerprint") or "").casefold()
    if not _valid_sha256(fp) or fp != _canonical_sha256({k: v for k, v in row.items() if k not in {"fingerprint", "verified_at"}}):
        raise RuntimeError(f"Stage {stage_number} execution proof was mutated")
    if row.get("binding_fingerprint") != binding.get("fingerprint"):
        raise RuntimeError(f"Stage {stage_number} execution proof belongs to different binding")
    if str(row.get("quality_gate_pass_fingerprint") or "").casefold() != pass_fingerprint:
        raise RuntimeError(f"Stage {stage_number} execution proof belongs to different Stage15 PASS")
    contract = _validate_public_contract(row.get("contract"), binding, stage_number)
    if row.get("contract_sha256") != _canonical_sha256(contract):
        raise RuntimeError(f"Stage {stage_number} execution contract hash drift")
    return row


def plan_post_gate_execution(state_path: Path | str, stage_number: int) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe, pass_fingerprint = _post_gate_context(path)
    binding = _binding(state, stage_number, pass_fingerprint)
    proof = _proof(state, binding, stage_number, pass_fingerprint)
    profile = _profile_stage(preflight, stage_number)
    parameters = dict(profile.get("parameters") or {})
    if binding.get("parameters_sha256") != _canonical_sha256(parameters):
        raise RuntimeError(f"Stage {stage_number} Product parameters changed after binding")
    params: dict[str, Any] = {}
    for key, spec in proof["contract"]["request"]["params"].items():
        if spec.startswith("input:"):
            name = spec.removeprefix("input:")
            if name not in binding["frozen_inputs"]:
                raise RuntimeError(f"Stage {stage_number} request references unfrozen input {name!r}")
            params[key] = binding["frozen_inputs"][name]
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
        "schema": POST_GATE_PLAN_SCHEMA,
        "status": "ready",
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "execution_contract_fingerprint": proof["fingerprint"],
        "quality_gate_pass_fingerprint": pass_fingerprint,
        "request": request,
        "request_sha256": _canonical_sha256(request),
        "database": proof["database"],
        "replay_safe": bool(proof["contract"]["replay_safe"]),
    }


def execute_post_gate_core_stage(
    core: RocketDictCore, database: Path | str, state_path: Path | str, stage_number: int
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    prove_post_gate_execution_contract(core, database_path, path, stage_number)
    plan = plan_post_gate_execution(path, stage_number)
    state, _preflight, _probe, pass_fingerprint = _post_gate_context(path)
    binding = _binding(state, stage_number, pass_fingerprint)
    proof = _proof(state, binding, stage_number, pass_fingerprint)
    contract = proof["contract"]
    upstream = state["steps"]["upstream_execution"]
    executions = upstream.setdefault("executions", {})
    previous = executions.get(str(stage_number))
    if isinstance(previous, dict) and previous.get("status") == "completed":
        _record_fingerprint(previous)
        if previous.get("request_sha256") != plan["request_sha256"]:
            raise RuntimeError(f"Completed Stage {stage_number} belongs to different request")
        if previous.get("result_sha256") != _canonical_sha256(previous.get("result")):
            raise RuntimeError(f"Completed Stage {stage_number} result was mutated")
        return {**previous, "cache_hit": True, "state_path": str(path)}
    if isinstance(previous, dict) and previous.get("status") in {"dispatching", "dispatch_failed_ambiguous"} and not contract["replay_safe"]:
        raise RuntimeError(f"Previous Stage {stage_number} dispatch may have mutated the database and is not replay-safe")
    attempts = int(previous.get("attempts") or 0) + 1 if isinstance(previous, dict) else 1
    record: dict[str, Any] = {
        "schema": EXECUTION_RECORD_SCHEMA,
        "status": "dispatching",
        "stage_number": stage_number,
        "binding_fingerprint": binding["fingerprint"],
        "execution_contract_fingerprint": proof["fingerprint"],
        "quality_gate_pass_fingerprint": pass_fingerprint,
        "request": plan["request"],
        "request_sha256": plan["request_sha256"],
        "replay_safe": bool(contract["replay_safe"]),
        "attempts": attempts,
        "started_at": _now(),
    }
    record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "attempts"}})
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
        record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "failed_at", "error", "attempts"}})
        upstream["status"] = f"stage{stage_number}_ambiguous_failure"
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
    record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "completed_at", "attempts"}})
    executions[str(stage_number)] = record
    upstream["status"] = f"stage{stage_number}_completed"
    upstream["blocked_reason"] = None
    state["status"] = f"stage{stage_number}_completed"
    _save(path, state)
    return {**record, "cache_hit": False, "state_path": str(path)}


def _stage18_policy_identity(preflight: dict[str, Any], pass_fingerprint: str) -> dict[str, Any]:
    policy = (((preflight.get("profile") or {}).get("workbench_stages") or {}).get("18"))
    if not isinstance(policy, dict):
        raise RuntimeError("Product profile lacks Workbench Stage18 policy")
    if str(policy.get("implementation") or "") != POLICY_KEY:
        raise RuntimeError(f"Workbench Stage18 policy drift: {policy.get('implementation')!r} != {POLICY_KEY!r}")
    identity = {
        "schema": STAGE18_POLICY_SCHEMA,
        "stage_number": 18,
        "implementation": POLICY_KEY,
        "profile_policy_sha256": _canonical_sha256(policy),
        "runner_source_sha256": _stage18_runner_sha256(),
        "quality_gate_pass_fingerprint": pass_fingerprint,
    }
    identity["fingerprint"] = _canonical_sha256(identity)
    return identity


def _resolve_stage18_alignment(state: dict[str, Any], preflight: dict[str, Any]) -> tuple[Any, list[str]]:
    available = _available_input_evidence(state, preflight)
    row = available.get("alignment_run_id")
    if not isinstance(row, dict):
        raise RuntimeError("Workbench Stage18 requires uniquely resolved alignment_run_id from completed Stage17")
    return row["value"], list(row["evidence_sources"])


def execute_workbench_stage18(
    core: RocketDictCore, database: Path | str, state_path: Path | str
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, preflight, probe, pass_fingerprint = _post_gate_context(path)
    probe_database = Path(str((probe.get("database") or {}).get("path") or "")).expanduser().resolve()
    if probe_database != database_path:
        raise RuntimeError("Workbench Stage18 database differs from immutable API-probe database")
    alignment_run_id, evidence_sources = _resolve_stage18_alignment(state, preflight)
    if isinstance(alignment_run_id, bool) or not isinstance(alignment_run_id, (int, str)):
        raise RuntimeError("Workbench Stage18 alignment_run_id is not a scalar identity")
    try:
        alignment_id_int = int(alignment_run_id)
    except Exception as exc:
        raise RuntimeError("Workbench Stage18 alignment_run_id is not integer-compatible") from exc
    if alignment_id_int <= 0:
        raise RuntimeError("Workbench Stage18 alignment_run_id must be positive")
    policy_identity = _stage18_policy_identity(preflight, pass_fingerprint)
    request = {
        "stage_number": 18,
        "implementation": POLICY_KEY,
        "alignment_run_id": alignment_id_int,
        "settings": {},
        "policy_fingerprint": policy_identity["fingerprint"],
    }
    request_sha = _canonical_sha256(request)
    upstream = state["steps"]["upstream_execution"]
    executions = upstream.setdefault("executions", {})
    previous = executions.get("18")
    if isinstance(previous, dict) and previous.get("status") == "completed":
        _record_fingerprint(previous)
        if previous.get("request_sha256") != request_sha:
            raise RuntimeError("Completed Workbench Stage18 belongs to different request")
        if previous.get("result_sha256") != _canonical_sha256(previous.get("result")):
            raise RuntimeError("Completed Workbench Stage18 result was mutated")
        return {**previous, "cache_hit": True, "state_path": str(path)}
    if isinstance(previous, dict) and previous.get("status") in {"dispatching", "dispatch_failed_ambiguous"}:
        raise RuntimeError(
            "Previous Workbench Stage18 dispatch may have mutated the database; no replay-safety claim exists, manual reconciliation is required"
        )
    record: dict[str, Any] = {
        "schema": STAGE18_EXECUTION_SCHEMA,
        "status": "dispatching",
        "stage_number": 18,
        "workbench_policy": policy_identity,
        "quality_gate_pass_fingerprint": pass_fingerprint,
        "input_evidence": {"alignment_run_id": evidence_sources},
        "request": request,
        "request_sha256": request_sha,
        "replay_safe": False,
        "attempts": 1,
        "started_at": _now(),
    }
    record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "attempts"}})
    executions["18"] = record
    upstream["status"] = "stage18_dispatching"
    state["status"] = "executing_workbench_stage18"
    _save(path, state)
    try:
        payload = run_product_aligned_lexical_extraction(core, database_path, alignment_id_int, settings={})
        if str(payload.get("policy") or "") != POLICY_KEY:
            raise RuntimeError("Workbench Stage18 result policy identity drift")
        if int(payload.get("alignment_run_id") or 0) != alignment_id_int:
            raise RuntimeError("Workbench Stage18 result belongs to different alignment_run_id")
        if payload.get("coverage_complete") is not True or int(payload.get("uncovered_token_count") or 0) != 0:
            raise RuntimeError("Workbench Stage18 lexical coverage is incomplete")
        if payload.get("source_mode") != "aligned":
            raise RuntimeError("Workbench Stage18 lost aligned source mode")
        identities = {}
        for name in ("extraction_run_id", "stage_result_id", "alignment_run_id", "nlp_run_id"):
            value = payload.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise RuntimeError(f"Workbench Stage18 result has invalid durable identity {name}={value!r}")
            identities[name] = value
        occurrences = payload.get("occurrences")
        occurrences_sha = _canonical_sha256(occurrences) if isinstance(occurrences, list) else None
        compact = {k: v for k, v in payload.items() if k != "occurrences"}
        compact["occurrences_sha256"] = occurrences_sha
        compact["full_result_sha256"] = _canonical_sha256(payload)
    except Exception as exc:
        record["status"] = "dispatch_failed_ambiguous"
        record["failed_at"] = _now()
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "failed_at", "error", "attempts"}})
        upstream["status"] = "stage18_ambiguous_non_replay_safe"
        upstream["blocked_reason"] = "manual_reconciliation_required_before_stage18_replay"
        state["status"] = "failed"
        _save(path, state)
        raise
    record.update(
        {
            "status": "completed",
            "completed_at": _now(),
            "result": compact,
            "result_sha256": _canonical_sha256(compact),
            "durable_identities": identities,
        }
    )
    record["fingerprint"] = _canonical_sha256({k: v for k, v in record.items() if k not in {"fingerprint", "started_at", "completed_at", "attempts"}})
    executions["18"] = record
    upstream["status"] = "stage18_completed"
    state["status"] = "stage18_completed_awaiting_stage19"
    _save(path, state)
    return {**record, "cache_hit": False, "state_path": str(path)}


def advance_post_gate_pipeline(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    max_steps: int | None = None,
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    if max_steps is not None and max_steps <= 0:
        raise ValueError("max_steps must be positive")
    require_quality_gate_pass(path)
    completed_now: list[int] = []
    for stage_number in POST_GATE_ORDER:
        state, _preflight, _probe, _pass = _post_gate_context(path)
        current = ((((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {}).get(str(stage_number)))
        if isinstance(current, dict) and current.get("status") == "completed":
            continue
        if max_steps is not None and len(completed_now) >= max_steps:
            return {
                "schema": POST_GATE_PIPELINE_SCHEMA,
                "status": "progressed",
                "completed_now": completed_now,
                "next_stage": stage_number,
                "state_path": str(path),
            }
        if stage_number == 18:
            execute_workbench_stage18(core, database, path)
            completed_now.append(18)
            continue
        discovery = discover_post_gate_stage(path, stage_number)
        if discovery["status"] != "unique_exact_match":
            state["steps"]["upstream_execution"]["status"] = f"stage{stage_number}_blocked"
            state["steps"]["upstream_execution"]["blocked_reason"] = str(discovery["status"])
            state["status"] = f"blocked_before_stage{stage_number}"
            _save(path, state)
            return {
                "schema": POST_GATE_PIPELINE_SCHEMA,
                "status": "blocked",
                "blocked_stage": stage_number,
                "reason": discovery["status"],
                "diagnostic": discovery,
                "completed_now": completed_now,
                "state_path": str(path),
            }
        operation = str(discovery["exact_matches"][0]["operation"])
        verify_post_gate_binding(path, stage_number, operation)
        execute_post_gate_core_stage(core, database, path, stage_number)
        completed_now.append(stage_number)

    state, _preflight, _probe, pass_fingerprint = _post_gate_context(path)
    upstream = state["steps"]["upstream_execution"]
    upstream["status"] = "stage19_completed"
    upstream["blocked_reason"] = "stage20_lexical_provider_not_yet_bound_to_unified_product_run"
    state["status"] = "stage19_completed_ready_for_stage20_provider"
    _save(path, state)
    return {
        "schema": POST_GATE_PIPELINE_SCHEMA,
        "status": "stage19_completed",
        "completed_now": completed_now,
        "quality_gate_pass_fingerprint": pass_fingerprint,
        "next_stage": 20,
        "stage20_ready": True,
        "state_path": str(path),
    }
