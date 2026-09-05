from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.upstream_chain import (
    discover_upstream_stage,
    pre_gate_stages,
    resolve_stage_inputs,
    verify_upstream_stage_binding,
)


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _stage(number: int, required_inputs: list[str]) -> tuple[dict, dict]:
    descriptor = f"{number:02x}" * 32
    parameters = {"stage": number}
    stage_key = {8: "nlp_analysis", 10: "context", 12: "translation_baseline", 14: "refinement", 16: "finalization"}[number]
    implementation = f"impl-{number}"
    profile = {
        "stage_number": number,
        "stage_key": stage_key,
        "implementation": implementation,
        "parameters": parameters,
        "adapter_descriptor_hash": descriptor,
        "required_inputs": required_inputs,
    }
    contract = {
        "stage_number": number,
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters": parameters,
        "required_inputs": required_inputs,
    }
    selected = {
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters_sha256": _canon(parameters),
        "required_inputs": required_inputs,
        "execution_contract_sha256": _canon(contract),
    }
    return selected, profile


def _callable(number: int, selected: dict) -> dict:
    return {
        "mapping_module": "rocketdict.api.operations",
        "mapping_name": "OPERATIONS",
        "operation": f"product.stage{number}.run",
        "callable_module": "rocketdict.api.operations",
        "callable_qualname": f"run_stage_{number}",
        "signature": "(**params)",
        "parameters": [{"name": "params", "kind": "VAR_KEYWORD", "required": False}],
        "source_sha256": f"{number % 10}" * 64,
        "binding_metadata": {
            "stage_number": number,
            "stage_key": selected["stage_key"],
            "implementation_key": selected["implementation"],
            "adapter_descriptor_hash": selected["adapter_descriptor_hash"],
            "required_inputs": list(selected["required_inputs"]),
        },
    }


def _state(*, stage12_input: str = "nlp_run_id", completed_stage8: bool = True, source_extra: dict | None = None) -> dict:
    stage_defs = {
        8: ["document_version_id"],
        10: ["document_version_id"],
        12: [stage12_input],
        14: ["document_version_id"],
        16: ["assembly_id"],
    }
    selected: dict[str, dict] = {}
    profiles: dict[str, dict] = {}
    callables = []
    for number, inputs in stage_defs.items():
        identity, profile = _stage(number, inputs)
        selected[str(number)] = identity
        profiles[str(number)] = profile
        callables.append(_callable(number, identity))
    source = {
        "sha256": "a" * 64,
        "import_event_id": 7,
        "document_version_id": 11,
        "selected_format": "txt",
        **(source_extra or {}),
    }
    preflight = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "ready",
        "identity": {
            "fingerprint": "5" * 64,
            "source": source,
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "registry_hash": "registry-1",
            "required_core_stages": selected,
        },
        "profile": {"stages": profiles},
    }
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": "/tmp/db.sqlite", "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [],
        "parser_commands": ["call"],
        "callable_mapping_keys": [row["operation"] for row in callables],
        "callable_operations": callables,
        "operation_candidates": [row["operation"] for row in callables],
    }
    probe["fingerprint"] = _canon(probe)
    upstream = {"status": "pending", "attempts": 0}
    if completed_stage8:
        upstream["executions"] = {
            "8": {
                "status": "completed",
                "durable_identities": {"nlp_run_id": 23, "stage_result_id": 24},
            }
        }
    return {
        "schema": RUN_STATE_SCHEMA,
        "status": "stage8_completed_awaiting_next_upstream_binding" if completed_stage8 else "awaiting_upstream_binding",
        "root_identity": {"preflight_fingerprint": "5" * 64, "fingerprint": "6" * 64},
        "steps": {
            "preflight": {"status": "completed", "result_sha256": _canon(preflight), "result": preflight},
            "upstream_contract_probe": {"status": "completed", "result_sha256": _canon(probe), "result": probe},
            "upstream_execution": upstream,
            "stage20_downstream": {"status": "pending"},
            "cards": {"status": "pending"},
            "export": {"status": "pending"},
        },
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_pre_gate_chain_stops_before_stage15_quality_boundary() -> None:
    payload = _state()
    preflight = payload["steps"]["preflight"]["result"]
    assert pre_gate_stages(preflight) == [8, 10, 12, 14]


def test_stage10_resolves_exact_source_identity_by_name(tmp_path) -> None:
    payload = _state()
    preflight = payload["steps"]["preflight"]["result"]
    resolved = resolve_stage_inputs(payload, preflight, 10)
    assert resolved["frozen_inputs"] == {"document_version_id": 11}
    assert resolved["input_evidence"]["document_version_id"] == ["preflight.source"]

    discovery = discover_upstream_stage(_write(tmp_path, payload), 10)
    assert discovery["status"] == "unique_exact_match"
    assert discovery["exact_matches"][0]["operation"] == "product.stage10.run"


def test_stage12_can_resolve_prior_completed_durable_identity_without_aliasing(tmp_path) -> None:
    path = _write(tmp_path, _state())
    discovery = discover_upstream_stage(path, 12)
    assert discovery["status"] == "unique_exact_match"
    assert discovery["input_resolution"]["frozen_inputs"] == {"nlp_run_id": 23}
    assert discovery["input_resolution"]["input_evidence"]["nlp_run_id"] == ["stage8.durable_identities"]

    binding = verify_upstream_stage_binding(path, 12, "product.stage12.run")["binding"]
    assert binding["frozen_inputs"] == {"nlp_run_id": 23}
    assert binding["proof"]["input_resolution_mode"] == "exact-name-source-or-completed-durable-identity-v1"
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["status"] == "stage8_completed_awaiting_next_upstream_binding"


def test_unresolved_input_blocks_binding_even_when_callable_matches(tmp_path) -> None:
    path = _write(tmp_path, _state(completed_stage8=False))
    discovery = discover_upstream_stage(path, 12)
    assert discovery["status"] == "input_resolution_blocked"
    with pytest.raises(RuntimeError, match="not uniquely resolvable"):
        verify_upstream_stage_binding(path, 12, "product.stage12.run")


def test_conflicting_same_name_identity_is_not_guessed(tmp_path) -> None:
    path = _write(tmp_path, _state(source_extra={"nlp_run_id": 99}))
    discovery = discover_upstream_stage(path, 12)
    assert discovery["status"] == "input_resolution_blocked"
    assert "nlp_run_id" in discovery["input_error"]


def test_post_gate_stage_is_rejected_by_pre_gate_chain(tmp_path) -> None:
    path = _write(tmp_path, _state())
    with pytest.raises(RuntimeError, match="outside the pre-hard-gate"):
        discover_upstream_stage(path, 16)
    with pytest.raises(RuntimeError, match="Stage15 quality execution"):
        verify_upstream_stage_binding(path, 16, "product.stage16.run")
