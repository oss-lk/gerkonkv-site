from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .upstream_binding import (
    BINDING_SCHEMA,
    FIRST_UPSTREAM_STAGE,
    _canonical_sha256,
    _load_verified_evidence,
    _operation_rows,
    _required_inputs,
    _save,
    _selected_stage,
    _valid_sha256,
)

CHAIN_DISCOVERY_SCHEMA = "rocketdict-workbench-upstream-chain-discovery/1"
PRE_HARD_GATE_MAX_STAGE = 14


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ordered_required_stages(preflight: dict[str, Any]) -> list[int]:
    rows = (preflight.get("identity") or {}).get("required_core_stages") or {}
    numbers = sorted(int(key) for key in rows if str(key).isdigit())
    if FIRST_UPSTREAM_STAGE not in numbers:
        raise RuntimeError("Product preflight does not contain the first upstream stage")
    return numbers


def pre_gate_stages(preflight: dict[str, Any]) -> list[int]:
    """Stages executable before the separate Stage15 hard-quality boundary."""
    return [number for number in _ordered_required_stages(preflight) if number <= PRE_HARD_GATE_MAX_STAGE]


def _scalar_identity(value: Any, *, name: str, source: str) -> Any:
    if value is None or isinstance(value, bool) or isinstance(value, (dict, list)):
        raise RuntimeError(f"Durable input {name!r} from {source} is not a scalar identity")
    if isinstance(value, str) and not value:
        raise RuntimeError(f"Durable input {name!r} from {source} is empty")
    return value


def _available_input_evidence(state: dict[str, Any], preflight: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Collect exact-name durable identities without semantic aliasing.

    The immutable source identity is authoritative for keys it actually exposes.
    Completed upstream executions contribute only their explicit durable_identities.
    If the same name has different values across evidence, resolution becomes
    ambiguous and the name is excluded rather than guessed.
    """
    candidates: dict[str, list[tuple[str, Any]]] = {}
    source = (preflight.get("identity") or {}).get("source") or {}
    for key, value in source.items():
        if key in {"copied_path", "source_name"}:
            continue
        if value is None or isinstance(value, (dict, list, bool)):
            continue
        if isinstance(value, str) and not value:
            continue
        candidates.setdefault(str(key), []).append(("preflight.source", value))

    upstream = ((state.get("steps") or {}).get("upstream_execution") or {})
    executions = upstream.get("executions") or {}
    for stage_key, record in sorted(
        executions.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else 10**9
    ):
        if not isinstance(record, dict) or record.get("status") != "completed":
            continue
        identities = record.get("durable_identities") or {}
        if not isinstance(identities, dict):
            raise RuntimeError(f"Completed upstream stage {stage_key} durable_identities is not an object")
        for name, value in identities.items():
            scalar = _scalar_identity(
                value, name=str(name), source=f"stage{stage_key}.durable_identities"
            )
            candidates.setdefault(str(name), []).append(
                (f"stage{stage_key}.durable_identities", scalar)
            )

    resolved: dict[str, dict[str, Any]] = {}
    for name, rows in candidates.items():
        unique: list[tuple[str, Any]] = []
        for source_name, value in rows:
            if not any(value == existing for _existing_source, existing in unique):
                unique.append((source_name, value))
        if len(unique) != 1:
            continue
        value = unique[0][1]
        resolved[name] = {
            "value": value,
            "evidence_sources": [
                source_name for source_name, row_value in rows if row_value == value
            ],
        }
    return resolved


def resolve_stage_inputs(
    state: dict[str, Any], preflight: dict[str, Any], stage_number: int
) -> dict[str, Any]:
    selected, _profile_stage = _selected_stage(preflight, stage_number)
    required = _required_inputs(
        selected.get("required_inputs"), context=f"Stage {stage_number} frozen identity"
    )
    available = _available_input_evidence(state, preflight)
    missing = [name for name in required if name not in available]
    if missing:
        raise RuntimeError(
            f"Stage {stage_number} required inputs are not uniquely resolvable from immutable source/prior completed stages: {missing}"
        )
    return {
        "required_inputs": required,
        "frozen_inputs": {name: available[name]["value"] for name in required},
        "input_evidence": {name: available[name]["evidence_sources"] for name in required},
    }


def _expected(preflight: dict[str, Any], stage_number: int) -> dict[str, Any]:
    selected, _profile_stage = _selected_stage(preflight, stage_number)
    return {
        "stage_number": stage_number,
        "stage_key": str(selected["stage_key"]),
        "implementation": str(selected["implementation"]),
        "adapter_descriptor_hash": str(selected["adapter_descriptor_hash"]).casefold(),
        "parameters_sha256": str(selected["parameters_sha256"]).casefold(),
        "required_inputs": _required_inputs(
            selected.get("required_inputs"), context=f"Stage {stage_number} frozen identity"
        ),
        "execution_contract_sha256": str(selected["execution_contract_sha256"]).casefold(),
    }


def _evaluate(row: dict[str, Any], expected: dict[str, Any]) -> list[str]:
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


def discover_upstream_stage(state_path: Path | str, stage_number: int) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    if stage_number not in pre_gate_stages(preflight):
        raise RuntimeError(
            f"Stage {stage_number} is outside the pre-hard-gate upstream chain {pre_gate_stages(preflight)}; "
            "Stage15 quality execution must be proved separately before post-gate stages are enabled"
        )
    expected = _expected(preflight, stage_number)
    try:
        input_resolution = resolve_stage_inputs(state, preflight, stage_number)
        input_status = "resolved"
        input_error = None
    except RuntimeError as exc:
        input_resolution = None
        input_status = "blocked"
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
            "exact_contract_match": not reasons,
            "mismatch_reasons": reasons,
        }
        candidates.append(candidate)
        if not reasons:
            exact.append(candidate)
    if input_status != "resolved":
        status = "input_resolution_blocked"
    elif len(exact) == 1:
        status = "unique_exact_match"
    elif not exact:
        status = "no_exact_match"
    else:
        status = "ambiguous_exact_matches"
    return {
        "schema": CHAIN_DISCOVERY_SCHEMA,
        "status": status,
        "state_path": str(path),
        "stage_number": stage_number,
        "expected_contract": expected,
        "input_status": input_status,
        "input_resolution": input_resolution,
        "input_error": input_error,
        "structured_callable_count": len(candidates),
        "exact_match_count": len(exact),
        "exact_matches": exact,
        "candidates": candidates,
        "product_run_root_fingerprint": str(state["root_identity"]["fingerprint"]).casefold(),
        "api_probe_fingerprint": str(probe["fingerprint"]).casefold(),
        "semantic_input_aliasing_allowed": False,
        "post_stage14_execution_allowed_by_this_module": False,
    }


def _verified_at(previous: Any, stage_number: int) -> str:
    if previous is None:
        return _now()
    if not isinstance(previous, dict) or previous.get("schema") != BINDING_SCHEMA:
        raise RuntimeError(
            f"Persisted Stage {stage_number} binding is missing/current-schema-incompatible"
        )
    fingerprint = str(previous.get("fingerprint") or "").casefold()
    expected = _canonical_sha256({key: value for key, value in previous.items() if key != "fingerprint"})
    if not _valid_sha256(fingerprint) or fingerprint != expected:
        raise RuntimeError(f"Persisted Stage {stage_number} binding evidence was mutated")
    value = str(previous.get("verified_at") or "")
    if not value:
        raise RuntimeError(f"Persisted Stage {stage_number} binding lacks verified_at")
    return value


def verify_upstream_stage_binding(
    state_path: Path | str, stage_number: int, operation_key: str
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    if stage_number not in pre_gate_stages(preflight):
        raise RuntimeError(
            f"Stage {stage_number} cannot be promoted by the pre-hard-gate chain; "
            "Stage15 quality execution is a mandatory separate boundary"
        )
    expected = _expected(preflight, stage_number)
    input_resolution = resolve_stage_inputs(state, preflight, stage_number)
    rows = [
        row for row in _operation_rows(probe) if str(row.get("operation") or "") == operation_key
    ]
    if len(rows) != 1:
        raise RuntimeError(
            f"Operation {operation_key!r} must occur exactly once as structured runtime evidence, observed {len(rows)}"
        )
    reasons = _evaluate(rows[0], expected)
    if reasons:
        raise RuntimeError(
            f"Operation {operation_key!r} does not match frozen Stage {stage_number} contract: {', '.join(reasons)}"
        )
    row = rows[0]
    identity = preflight["identity"]
    upstream = state["steps"]["upstream_execution"]
    bindings = upstream.setdefault("bindings", {})
    previous = bindings.get(str(stage_number))
    verified_at = _verified_at(previous, stage_number)
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
        "frozen_inputs": dict(input_resolution["frozen_inputs"]),
        "input_evidence": dict(input_resolution["input_evidence"]),
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
            "proof_mode": "live-registry-plus-exact-runtime-callable-v1",
            "input_resolution_mode": "exact-name-source-or-completed-durable-identity-v1",
        },
        "verified_at": verified_at,
    }
    binding["fingerprint"] = _canonical_sha256(binding)
    if previous is not None and str(previous.get("fingerprint") or "") != binding["fingerprint"]:
        raise RuntimeError(
            f"Stage {stage_number} already has a different verified binding in this immutable Product run"
        )
    bindings[str(stage_number)] = binding
    executions = upstream.get("executions") or {}
    if str(stage_number) not in executions:
        upstream["last_binding_verified_stage"] = stage_number
    _save(path, state)
    return {
        "schema": BINDING_SCHEMA,
        "status": "binding_verified",
        "state_path": str(path),
        "binding": binding,
    }
