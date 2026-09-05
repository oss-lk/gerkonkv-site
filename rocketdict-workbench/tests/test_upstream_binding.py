from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rocketdict_workbench.cli import parser
from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.upstream_binding import (
    BINDING_SCHEMA,
    DISCOVERY_SCHEMA,
    discover_stage8_bindings,
    verify_stage8_binding,
)


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _stage8_contract(*, required_inputs: list[str] | None = None) -> tuple[dict, dict]:
    descriptor = "d" * 64
    inputs = list(required_inputs or ["document_version_id"])
    profile_stage = {
        "stage_number": 8,
        "stage_key": "nlp_analysis",
        "implementation": "en-sm",
        "parameters": {},
        "adapter_descriptor_hash": descriptor,
        "required_inputs": inputs,
    }
    selected = {
        "stage_key": "nlp_analysis",
        "implementation": "en-sm",
        "adapter_descriptor_hash": descriptor,
        "parameters_sha256": _canon({}),
        "required_inputs": inputs,
        "execution_contract_sha256": _canon(
            {
                "stage_number": 8,
                "stage_key": "nlp_analysis",
                "implementation": "en-sm",
                "adapter_descriptor_hash": descriptor,
                "parameters": {},
                "required_inputs": inputs,
            }
        ),
    }
    return selected, profile_stage


def _state(
    *,
    metadata: dict | None = None,
    callable_present: bool = True,
    frozen_required_inputs: list[str] | None = None,
) -> dict:
    descriptor = "d" * 64
    selected, profile_stage = _stage8_contract(required_inputs=frozen_required_inputs)
    preflight = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "ready",
        "identity": {
            "fingerprint": "5" * 64,
            "source": {
                "sha256": "1" * 64,
                "import_event_id": 7,
                "document_version_id": 11,
                "selected_format": "txt",
            },
            "core": {"python": "python", "rocketdict_version": "0.30.40", "api_version": "1"},
            "registry_hash": "registry-1",
            "required_core_stages": {"8": selected},
        },
        "profile": {"stages": {"8": profile_stage}},
    }
    binding_metadata = metadata if metadata is not None else {
        "stage_number": 8,
        "stage_key": "nlp_analysis",
        "implementation_key": "en-sm",
        "adapter_descriptor_hash": descriptor,
        "required_inputs": ["document_version_id"],
    }
    operations = []
    if callable_present:
        operations.append(
            {
                "mapping_module": "rocketdict.api.operations",
                "mapping_name": "OPERATIONS",
                "operation": "product.stage8.run",
                "callable_module": "rocketdict.api.operations",
                "callable_qualname": "run_product_stage8",
                "signature": "(*, database, document_version_id, parameters)",
                "parameters": [
                    {"name": "database", "kind": "KEYWORD_ONLY", "required": True},
                    {"name": "document_version_id", "kind": "KEYWORD_ONLY", "required": True},
                    {"name": "parameters", "kind": "KEYWORD_ONLY", "required": True},
                ],
                "source_sha256": "b" * 64,
                "binding_metadata": binding_metadata,
            }
        )
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": "/tmp/db.sqlite", "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [{"module": "rocketdict.api.operations", "imported": True, "source_sha256": "c" * 64}],
        "parser_commands": ["call"],
        "callable_mapping_keys": ["product.stage8.run"],
        "callable_operations": operations,
        "operation_candidates": ["call", "product.stage8.run"],
    }
    probe["fingerprint"] = _canon(probe)
    return {
        "schema": RUN_STATE_SCHEMA,
        "created_at": "2026-09-05T00:00:00+00:00",
        "updated_at": "2026-09-05T00:00:00+00:00",
        "status": "awaiting_upstream_binding",
        "root_identity": {
            "preflight_fingerprint": "5" * 64,
            "fingerprint": "6" * 64,
        },
        "steps": {
            "preflight": {
                "status": "completed",
                "attempts": 1,
                "result_sha256": _canon(preflight),
                "result": preflight,
            },
            "upstream_contract_probe": {
                "status": "completed",
                "attempts": 1,
                "result_sha256": _canon(probe),
                "result": probe,
            },
            "upstream_execution": {"status": "pending", "attempts": 0},
            "stage20_downstream": {"status": "pending", "attempts": 0},
            "cards": {"status": "pending", "attempts": 0},
            "export": {"status": "pending", "attempts": 0},
        },
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "product-run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_stage8_discovery_finds_unique_exact_runtime_match(tmp_path) -> None:
    path = _write(tmp_path, _state())
    result = discover_stage8_bindings(path)

    assert result["schema"] == DISCOVERY_SCHEMA
    assert result["status"] == "unique_exact_match"
    assert result["exact_match_count"] == 1
    assert result["exact_matches"][0]["operation"] == "product.stage8.run"
    assert result["expected_stage8_contract"]["required_inputs"] == ["document_version_id"]
    assert result["parser_or_string_candidates_are_execution_proof"] is False


def test_stage8_binding_requires_exact_runtime_callable_metadata(tmp_path) -> None:
    path = _write(tmp_path, _state())

    first = verify_stage8_binding(path, "product.stage8.run")
    second = verify_stage8_binding(path, "product.stage8.run")

    assert first["schema"] == BINDING_SCHEMA
    assert first["status"] == "ready_for_stage8_execution"
    assert first["binding"]["stage_number"] == 8
    assert first["binding"]["implementation"] == "en-sm"
    assert first["binding"]["required_inputs"] == ["document_version_id"]
    assert first["binding"]["frozen_inputs"] == {"document_version_id": 11}
    assert first["binding"]["proof"]["proof_mode"] == "live-registry-plus-exact-runtime-callable-v1"
    assert len(first["binding"]["execution_contract_sha256"]) == 64
    assert first["binding"]["fingerprint"] == second["binding"]["fingerprint"]

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["status"] == "ready_for_stage8_execution"
    assert persisted["steps"]["upstream_execution"]["status"] == "binding_verified"
    assert persisted["steps"]["upstream_execution"]["blocked_reason"] == "verified_stage8_binding_not_yet_executed"


def test_parser_candidate_alone_cannot_be_promoted_to_stage8_binding(tmp_path) -> None:
    path = _write(tmp_path, _state(callable_present=False))
    discovery = discover_stage8_bindings(path)
    assert discovery["status"] == "no_exact_match"
    assert discovery["structured_callable_count"] == 0
    with pytest.raises(RuntimeError, match="parser/candidate strings are not sufficient proof"):
        verify_stage8_binding(path, "product.stage8.run")


def test_stage8_discovery_explains_descriptor_drift(tmp_path) -> None:
    metadata = {
        "stage_number": 8,
        "stage_key": "nlp_analysis",
        "implementation_key": "en-sm",
        "adapter_descriptor_hash": "9" * 64,
        "required_inputs": ["document_version_id"],
    }
    path = _write(tmp_path, _state(metadata=metadata))
    result = discover_stage8_bindings(path)
    assert result["status"] == "no_exact_match"
    assert result["candidates"][0]["mismatch_reasons"] == ["adapter_descriptor_hash_mismatch"]
    with pytest.raises(RuntimeError, match="adapter_descriptor_hash_mismatch"):
        verify_stage8_binding(path, "product.stage8.run")


def test_stage8_binding_rejects_callable_required_input_drift(tmp_path) -> None:
    metadata = {
        "stage_number": 8,
        "stage_key": "nlp_analysis",
        "implementation_key": "en-sm",
        "adapter_descriptor_hash": "d" * 64,
        "required_inputs": ["document_version_id", "invented_context_id"],
    }
    path = _write(tmp_path, _state(metadata=metadata))
    with pytest.raises(RuntimeError, match="required_inputs_mismatch"):
        verify_stage8_binding(path, "product.stage8.run")


def test_stage8_binding_rejects_unresolvable_live_registry_contract(tmp_path) -> None:
    path = _write(tmp_path, _state(frozen_required_inputs=["document_version_id", "context_id"]))
    with pytest.raises(RuntimeError, match="live Stage8 registry contract cannot yet be resolved"):
        discover_stage8_bindings(path)


def test_stage8_binding_rejects_probe_internal_fingerprint_drift(tmp_path) -> None:
    payload = _state()
    probe = payload["steps"]["upstream_contract_probe"]["result"]
    probe["callable_operations"][0]["callable_qualname"] = "mutated"
    payload["steps"]["upstream_contract_probe"]["result_sha256"] = _canon(probe)
    path = _write(tmp_path, payload)
    with pytest.raises(RuntimeError, match="internal fingerprint"):
        verify_stage8_binding(path, "product.stage8.run")


def test_stage8_binding_rejects_mutated_persisted_binding(tmp_path) -> None:
    path = _write(tmp_path, _state())
    verify_stage8_binding(path, "product.stage8.run")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["steps"]["upstream_execution"]["bindings"]["8"]["operation"] = "mutated.operation"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="binding evidence was mutated"):
        verify_stage8_binding(path, "product.stage8.run")


def test_stage8_discovery_cli_exposes_state_control() -> None:
    args = parser().parse_args([
        "product-run-discover-stage8",
        "/tmp/project",
        "--state",
        "/tmp/product-run.json",
    ])
    assert args.command == "product-run-discover-stage8"
    assert args.state == Path("/tmp/product-run.json")
