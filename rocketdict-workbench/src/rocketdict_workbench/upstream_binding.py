from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA

BINDING_SCHEMA = "rocketdict-workbench-upstream-binding/2"
DISCOVERY_SCHEMA = "rocketdict-workbench-stage8-binding-discovery/1"
FIRST_UPSTREAM_STAGE = 8
STAGE8_WORKBENCH_RESOLVABLE_INPUTS = ("document_version_id",)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").casefold()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _save(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _load_verified_evidence(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != RUN_STATE_SCHEMA:
        raise RuntimeError(f"Unsupported Product run state schema: {state.get('schema')!r}")
    steps = state.get("steps") or {}

    preflight_step = steps.get("preflight") or {}
    preflight = preflight_step.get("result")
    if preflight_step.get("status") != "completed" or not isinstance(preflight, dict):
        raise RuntimeError("Product run has no completed durable preflight evidence")
    if preflight_step.get("result_sha256") != _canonical_sha256(preflight):
        raise RuntimeError("Product run preflight evidence was mutated")
    identity = preflight.get("identity") or {}
    root = state.get("root_identity") or {}
    if str(identity.get("fingerprint") or "").casefold() != str(root.get("preflight_fingerprint") or "").casefold():
        raise RuntimeError("Product run root no longer matches its preflight fingerprint")

    probe_step = steps.get("upstream_contract_probe") or {}
    probe = probe_step.get("result")
    if probe_step.get("status") != "completed" or not isinstance(probe, dict):
        raise RuntimeError("Product run has no completed upstream API probe evidence")
    if probe_step.get("result_sha256") != _canonical_sha256(probe):
        raise RuntimeError("Product run upstream API probe evidence was mutated")
    if probe.get("schema") != API_PROBE_SCHEMA:
        raise RuntimeError(f"Upstream binding requires current probe schema {API_PROBE_SCHEMA!r}")
    probe_fingerprint = str(probe.get("fingerprint") or "").casefold()
    if not _valid_sha256(probe_fingerprint):
        raise RuntimeError("Upstream API probe lacks a valid fingerprint")
    observed_fingerprint = _canonical_sha256({key: value for key, value in probe.items() if key != "fingerprint"})
    if observed_fingerprint != probe_fingerprint:
        raise RuntimeError("Upstream API probe internal fingerprint does not match its evidence")

    expected_core = identity.get("core") or {}
    observed_core = probe.get("core") or {}
    for key in ("rocketdict_version", "api_version"):
        if str(observed_core.get(key) or "") != str(expected_core.get(key) or ""):
            raise RuntimeError(f"Upstream API probe {key} differs from Product preflight")
    return state, preflight, probe


def _required_inputs(value: Any, *, context: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RuntimeError(f"{context} lacks a valid required_inputs execution contract")
    if len(set(value)) != len(value):
        raise RuntimeError(f"{context} has duplicate required_inputs")
    return list(value)


def _selected_stage(preflight: dict[str, Any], stage_number: int) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = preflight.get("identity") or {}
    selected = (identity.get("required_core_stages") or {}).get(str(stage_number))
    profile_stage = ((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number))
    if not isinstance(selected, dict) or not isinstance(profile_stage, dict):
        raise RuntimeError(f"Product preflight does not contain selected core stage {stage_number}")

    implementation = str(selected.get("implementation") or "")
    descriptor_hash = str(selected.get("adapter_descriptor_hash") or "").casefold()
    stage_key = str(selected.get("stage_key") or "")
    if not implementation:
        raise RuntimeError(f"Product stage {stage_number} lacks implementation identity")
    if not stage_key:
        raise RuntimeError(f"Product stage {stage_number} lacks frozen stage_key execution identity")
    if not _valid_sha256(descriptor_hash):
        raise RuntimeError(f"Product stage {stage_number} lacks a SHA-256 adapter descriptor identity")
    if str(profile_stage.get("implementation") or "") != implementation:
        raise RuntimeError(f"Product stage {stage_number} profile/identity implementation drift")
    if str(profile_stage.get("stage_key") or "") != stage_key:
        raise RuntimeError(f"Product stage {stage_number} profile/identity stage_key drift")
    if str(profile_stage.get("adapter_descriptor_hash") or "").casefold() != descriptor_hash:
        raise RuntimeError(f"Product stage {stage_number} profile/identity descriptor drift")

    selected_inputs = _required_inputs(selected.get("required_inputs"), context=f"Product stage {stage_number} frozen identity")
    profile_inputs = _required_inputs(profile_stage.get("required_inputs"), context=f"Product stage {stage_number} profile")
    if selected_inputs != profile_inputs:
        raise RuntimeError(f"Product stage {stage_number} profile/identity required_inputs drift")

    contract = {
        "stage_number": stage_number,
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor_hash,
        "parameters": profile_stage.get("parameters") or {},
        "required_inputs": selected_inputs,
    }
    expected_contract_sha = _canonical_sha256(contract)
    if str(selected.get("execution_contract_sha256") or "").casefold() != expected_contract_sha:
        raise RuntimeError(f"Product stage {stage_number} execution contract hash drift")
    if str(selected.get("parameters_sha256") or "").casefold() != _canonical_sha256(profile_stage.get("parameters") or {}):
        raise RuntimeError(f"Product stage {stage_number} parameter hash drift")
    return dict(selected), dict(profile_stage)


def _stage8_expected(preflight: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    selected, profile_stage = _selected_stage(preflight, FIRST_UPSTREAM_STAGE)
    required_inputs = _required_inputs(selected.get("required_inputs"), context="Frozen Stage8 identity")
    if tuple(required_inputs) != STAGE8_WORKBENCH_RESOLVABLE_INPUTS:
        raise RuntimeError(
            "Current live Stage8 registry contract cannot yet be resolved by Workbench: "
            f"expected resolvable inputs {STAGE8_WORKBENCH_RESOLVABLE_INPUTS}, live registry froze {tuple(required_inputs)}"
        )
    expected = {
        "stage_number": FIRST_UPSTREAM_STAGE,
        "stage_key": str(selected["stage_key"]),
        "implementation": str(selected["implementation"]),
        "adapter_descriptor_hash": str(selected["adapter_descriptor_hash"]).casefold(),
        "parameters_sha256": str(selected["parameters_sha256"]).casefold(),
        "required_inputs": required_inputs,
        "execution_contract_sha256": str(selected["execution_contract_sha256"]).casefold(),
    }
    return selected, profile_stage, expected


def _operation_rows(probe: dict[str, Any]) -> list[dict[str, Any]]:
    rows = probe.get("callable_operations") or []
    if not isinstance(rows, list):
        raise RuntimeError("Upstream API probe callable_operations is not a JSON list")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _evaluate_stage8_operation(row: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    operation = str(row.get("operation") or "")
    if not operation:
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
    if int(metadata.get("stage_number") or 0) != FIRST_UPSTREAM_STAGE:
        reasons.append("stage_number_mismatch")
    if str(metadata.get("stage_key") or "") != expected["stage_key"]:
        reasons.append("stage_key_mismatch")
    if str(metadata.get("implementation_key") or "") != expected["implementation"]:
        reasons.append("implementation_mismatch")
    descriptor = metadata.get("adapter_descriptor_hash", metadata.get("descriptor_hash"))
    if str(descriptor or "").casefold() != expected["adapter_descriptor_hash"]:
        reasons.append("adapter_descriptor_hash_mismatch")
    required_inputs = metadata.get("required_inputs")
    if not isinstance(required_inputs, list) or any(not isinstance(item, str) or not item for item in required_inputs):
        reasons.append("missing_or_invalid_required_inputs")
    elif list(required_inputs) != expected["required_inputs"]:
        reasons.append("required_inputs_mismatch")
    return reasons


def discover_stage8_bindings(state_path: Path | str) -> dict[str, Any]:
    """Explain which exact-runtime callable rows can or cannot bind frozen Stage8."""
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    _selected, _profile_stage, expected = _stage8_expected(preflight)
    candidates = []
    exact_rows = []
    for row in _operation_rows(probe):
        reasons = _evaluate_stage8_operation(row, expected)
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
    if len(exact_rows) == 1:
        status = "unique_exact_match"
    elif not exact_rows:
        status = "no_exact_match"
    else:
        status = "ambiguous_exact_matches"
    return {
        "schema": DISCOVERY_SCHEMA,
        "status": status,
        "state_path": str(path),
        "product_run_root_fingerprint": str(state["root_identity"]["fingerprint"]).casefold(),
        "api_probe_fingerprint": str(probe["fingerprint"]).casefold(),
        "expected_stage8_contract": expected,
        "structured_callable_count": len(candidates),
        "exact_match_count": len(exact_rows),
        "exact_matches": exact_rows,
        "candidates": candidates,
        "parser_or_string_candidates_are_execution_proof": False,
    }


def _operation(probe: dict[str, Any], operation_key: str, expected: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in _operation_rows(probe) if str(row.get("operation") or "") == operation_key]
    if not rows:
        raise RuntimeError(
            f"Operation {operation_key!r} is not a structured callable observed by the exact runtime probe; "
            "parser/candidate strings are not sufficient proof"
        )
    if len(rows) != 1:
        raise RuntimeError(f"Operation {operation_key!r} is ambiguous across {len(rows)} callable mappings")
    reasons = _evaluate_stage8_operation(rows[0], expected)
    if reasons:
        raise RuntimeError(f"Operation {operation_key!r} does not match frozen Stage8 execution contract: {', '.join(reasons)}")
    return rows[0]


def _verified_at_from_previous(previous: Any) -> str:
    if previous is None:
        return _now()
    if not isinstance(previous, dict):
        raise RuntimeError("Persisted Stage8 binding is not a JSON object")
    if previous.get("schema") != BINDING_SCHEMA:
        raise RuntimeError(
            f"Persisted Stage8 binding uses obsolete proof schema {previous.get('schema')!r}; "
            f"current verifier requires {BINDING_SCHEMA!r}"
        )
    fingerprint = str(previous.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({key: value for key, value in previous.items() if key != "fingerprint"})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError("Persisted Stage8 binding evidence was mutated")
    verified_at = str(previous.get("verified_at") or "")
    if not verified_at:
        raise RuntimeError("Persisted Stage8 binding lacks verified_at")
    return verified_at


def verify_stage8_binding(state_path: Path | str, operation_key: str) -> dict[str, Any]:
    """Promote one Stage8 API callable only when live-registry and runtime proof agree."""
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    selected, _profile_stage, expected = _stage8_expected(preflight)
    row = _operation(probe, operation_key, expected)

    upstream = state["steps"]["upstream_execution"]
    bindings = upstream.setdefault("bindings", {})
    previous = bindings.get(str(FIRST_UPSTREAM_STAGE))
    verified_at = _verified_at_from_previous(previous)

    identity = preflight["identity"]
    source = identity["source"]
    binding = {
        "schema": BINDING_SCHEMA,
        "status": "verified_not_executed",
        "stage_number": FIRST_UPSTREAM_STAGE,
        "stage_key": expected["stage_key"],
        "implementation": expected["implementation"],
        "adapter_descriptor_hash": expected["adapter_descriptor_hash"],
        "parameters_sha256": expected["parameters_sha256"],
        "required_inputs": list(expected["required_inputs"]),
        "execution_contract_sha256": expected["execution_contract_sha256"],
        "frozen_inputs": {"document_version_id": int(source["document_version_id"])},
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
            "execution_contract_sha256": str(selected["execution_contract_sha256"]).casefold(),
            "proof_mode": "live-registry-plus-exact-runtime-callable-v1",
        },
        "verified_at": verified_at,
    }
    binding["fingerprint"] = _canonical_sha256(binding)

    if previous is not None and str(previous.get("fingerprint") or "") != binding["fingerprint"]:
        raise RuntimeError("Stage8 already has a different verified binding in this immutable Product run")
    bindings[str(FIRST_UPSTREAM_STAGE)] = binding
    upstream["status"] = "binding_verified"
    upstream["blocked_reason"] = "verified_stage8_binding_not_yet_executed"
    state["status"] = "ready_for_stage8_execution"
    _save(path, state)
    return {
        "schema": BINDING_SCHEMA,
        "status": state["status"],
        "state_path": str(path),
        "binding": binding,
        "upstream_execution": dict(upstream),
    }
