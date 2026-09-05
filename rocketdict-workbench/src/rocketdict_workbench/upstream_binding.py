from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA

BINDING_SCHEMA = "rocketdict-workbench-upstream-binding/1"
FIRST_UPSTREAM_STAGE = 8
FIRST_STAGE_REQUIRED_INPUTS = ("document_version_id",)


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


def _selected_stage(preflight: dict[str, Any], stage_number: int) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = preflight.get("identity") or {}
    selected = (identity.get("required_core_stages") or {}).get(str(stage_number))
    profile_stage = ((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number))
    if not isinstance(selected, dict) or not isinstance(profile_stage, dict):
        raise RuntimeError(f"Product preflight does not contain selected core stage {stage_number}")
    implementation = str(selected.get("implementation") or "")
    descriptor_hash = str(selected.get("adapter_descriptor_hash") or "").casefold()
    if not implementation:
        raise RuntimeError(f"Product stage {stage_number} lacks implementation identity")
    if not _valid_sha256(descriptor_hash):
        raise RuntimeError(f"Product stage {stage_number} lacks a SHA-256 adapter descriptor identity")
    if str(profile_stage.get("implementation") or "") != implementation:
        raise RuntimeError(f"Product stage {stage_number} profile/identity implementation drift")
    if str(profile_stage.get("adapter_descriptor_hash") or "").casefold() != descriptor_hash:
        raise RuntimeError(f"Product stage {stage_number} profile/identity descriptor drift")
    return dict(selected), dict(profile_stage)


def _operation(probe: dict[str, Any], operation_key: str) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in (probe.get("callable_operations") or [])
        if isinstance(row, dict) and str(row.get("operation") or "") == operation_key
    ]
    if not rows:
        raise RuntimeError(
            f"Operation {operation_key!r} is not a structured callable observed by the exact runtime probe; "
            "parser/candidate strings are not sufficient proof"
        )
    if len(rows) != 1:
        raise RuntimeError(f"Operation {operation_key!r} is ambiguous across {len(rows)} callable mappings")
    row = rows[0]
    if not _valid_sha256(row.get("source_sha256")):
        raise RuntimeError(f"Operation {operation_key!r} has no inspectable SHA-256 source evidence")
    if not str(row.get("callable_module") or "") or not str(row.get("callable_qualname") or ""):
        raise RuntimeError(f"Operation {operation_key!r} lacks callable module/qualname evidence")
    if not isinstance(row.get("parameters"), list):
        raise RuntimeError(f"Operation {operation_key!r} lacks structured signature evidence")
    return row


def verify_stage8_binding(state_path: Path | str, operation_key: str) -> dict[str, Any]:
    """Promote one Stage8 API callable only when exact runtime metadata proves identity.

    An operation name alone never qualifies. The observed callable must explicitly
    publish Stage8, stage-key, implementation, descriptor and required-input metadata
    that exactly matches the frozen Product preflight. The first upstream contract is
    intentionally limited to document_version_id -> Stage8 NLP execution.
    """
    path = Path(state_path).expanduser().resolve()
    state, preflight, probe = _load_verified_evidence(path)
    selected, profile_stage = _selected_stage(preflight, FIRST_UPSTREAM_STAGE)
    row = _operation(probe, operation_key)
    metadata = row.get("binding_metadata") or {}
    if not isinstance(metadata, dict):
        raise RuntimeError(f"Operation {operation_key!r} lacks binding metadata")

    if int(metadata.get("stage_number") or 0) != FIRST_UPSTREAM_STAGE:
        raise RuntimeError(f"Operation {operation_key!r} does not explicitly identify Stage 8")
    expected_stage_key = str(profile_stage.get("stage_key") or "")
    if str(metadata.get("stage_key") or "") != expected_stage_key:
        raise RuntimeError(
            f"Operation {operation_key!r} stage key differs from Product profile: "
            f"{metadata.get('stage_key')!r} != {expected_stage_key!r}"
        )
    expected_implementation = str(selected["implementation"])
    if str(metadata.get("implementation_key") or "") != expected_implementation:
        raise RuntimeError(
            f"Operation {operation_key!r} implementation differs from Product profile: "
            f"{metadata.get('implementation_key')!r} != {expected_implementation!r}"
        )
    expected_descriptor = str(selected["adapter_descriptor_hash"]).casefold()
    if str(metadata.get("adapter_descriptor_hash") or "").casefold() != expected_descriptor:
        raise RuntimeError(f"Operation {operation_key!r} adapter descriptor identity differs from Product preflight")

    required_inputs = metadata.get("required_inputs")
    if not isinstance(required_inputs, list) or any(not isinstance(value, str) for value in required_inputs):
        raise RuntimeError(f"Operation {operation_key!r} lacks explicit required_inputs metadata")
    if tuple(required_inputs) != FIRST_STAGE_REQUIRED_INPUTS:
        raise RuntimeError(
            f"Stage8 binding requires exact inputs {FIRST_STAGE_REQUIRED_INPUTS}, observed {tuple(required_inputs)}"
        )

    identity = preflight["identity"]
    source = identity["source"]
    binding = {
        "schema": BINDING_SCHEMA,
        "status": "verified_not_executed",
        "stage_number": FIRST_UPSTREAM_STAGE,
        "stage_key": expected_stage_key,
        "implementation": expected_implementation,
        "adapter_descriptor_hash": expected_descriptor,
        "parameters_sha256": str(selected.get("parameters_sha256") or ""),
        "required_inputs": list(required_inputs),
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
            "proof_mode": "exact-runtime-callable-metadata-v1",
        },
        "verified_at": _now(),
    }
    binding["fingerprint"] = _canonical_sha256(binding)

    upstream = state["steps"]["upstream_execution"]
    bindings = upstream.setdefault("bindings", {})
    previous = bindings.get(str(FIRST_UPSTREAM_STAGE))
    if previous is not None:
        previous_fingerprint = str((previous or {}).get("fingerprint") or "")
        if previous_fingerprint != binding["fingerprint"]:
            raise RuntimeError("Stage8 already has a different verified binding in this immutable Product run")
        binding = dict(previous)
    else:
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
