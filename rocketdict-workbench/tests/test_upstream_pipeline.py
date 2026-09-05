from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.upstream_chain import discover_upstream_stage, verify_upstream_stage_binding
from rocketdict_workbench.upstream_execution import PUBLIC_EXECUTION_CONTRACT_SCHEMA
from rocketdict_workbench.upstream_pipeline import (
    UPSTREAM_PIPELINE_SCHEMA,
    advance_pre_gate_upstream,
    execute_upstream_stage,
)


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _stage(number: int, key: str, implementation: str, required_inputs: list[str], descriptor_char: str) -> tuple[dict, dict]:
    descriptor = descriptor_char * 64
    parameters = {"quality": "product", "stage": number}
    profile = {
        "stage_number": number,
        "stage_key": key,
        "implementation": implementation,
        "parameters": parameters,
        "adapter_descriptor_hash": descriptor,
        "required_inputs": list(required_inputs),
    }
    selected = {
        "stage_key": key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters_sha256": _canon(parameters),
        "required_inputs": list(required_inputs),
        "execution_contract_sha256": _canon({
            "stage_number": number,
            "stage_key": key,
            "implementation": implementation,
            "adapter_descriptor_hash": descriptor,
            "parameters": parameters,
            "required_inputs": list(required_inputs),
        }),
    }
    return selected, profile


def _operation(number: int, selected: dict, operation: str, source_char: str) -> dict:
    return {
        "mapping_module": "rocketdict.api.operations",
        "mapping_name": "OPERATIONS",
        "operation": operation,
        "callable_module": "rocketdict.api.operations",
        "callable_qualname": f"run_stage_{number}",
        "signature": "(**kwargs)",
        "parameters": [{"name": "kwargs", "kind": "VAR_KEYWORD", "required": False}],
        "source_sha256": source_char * 64,
        "binding_metadata": {
            "stage_number": number,
            "stage_key": selected["stage_key"],
            "implementation_key": selected["implementation"],
            "adapter_descriptor_hash": selected["adapter_descriptor_hash"],
            "required_inputs": list(selected["required_inputs"]),
        },
    }


def _state(*, ambiguous_stage8: bool = False) -> dict:
    definitions = {
        8: ("nlp_analysis", "en-sm", ["document_version_id"], "d"),
        10: ("context_enrichment", "context-v1", ["nlp_run_id"], "e"),
        12: ("translation_baseline", "opus-en-ru-ct2", ["context_run_id"], "f"),
        14: ("refinement", "glossary_refinement-current", ["assembly_id"], "a"),
        16: ("finalization", "approve-if-clean-finalization", ["refinement_run_id"], "7"),
    }
    selected: dict[str, dict] = {}
    profiles: dict[str, dict] = {}
    operations = []
    for index, (number, (key, implementation, inputs, char)) in enumerate(definitions.items()):
        identity, profile = _stage(number, key, implementation, inputs, char)
        selected[str(number)] = identity
        profiles[str(number)] = profile
        operations.append(_operation(number, identity, f"product.stage{number}.run", str((index + 2) % 10)))
    if ambiguous_stage8:
        operations.append(_operation(8, selected["8"], "product.stage8.alternate", "9"))
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
            "required_core_stages": selected,
        },
        "profile": {"stages": profiles},
    }
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": "/tmp/db.sqlite", "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [{"module": "rocketdict.api.operations", "imported": True, "source_sha256": "8" * 64}],
        "parser_commands": ["call"],
        "callable_mapping_keys": [row["operation"] for row in operations],
        "callable_operations": operations,
        "operation_candidates": ["call", *[row["operation"] for row in operations]],
    }
    probe["fingerprint"] = _canon(probe)
    return {
        "schema": RUN_STATE_SCHEMA,
        "created_at": "2026-09-05T00:00:00+00:00",
        "updated_at": "2026-09-05T00:00:00+00:00",
        "status": "awaiting_upstream_binding",
        "root_identity": {"preflight_fingerprint": "5" * 64, "fingerprint": "6" * 64},
        "steps": {
            "preflight": {"status": "completed", "attempts": 1, "result_sha256": _canon(preflight), "result": preflight},
            "upstream_contract_probe": {"status": "completed", "attempts": 1, "result_sha256": _canon(probe), "result": probe},
            "upstream_execution": {"status": "pending", "attempts": 0},
            "stage20_downstream": {"status": "pending", "attempts": 0},
            "cards": {"status": "pending", "attempts": 0},
            "export": {"status": "pending", "attempts": 0},
        },
    }


def _contract(stage: int, input_name: str, identity_name: str, *, replay_safe: bool = True) -> dict:
    return {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": "rocketdict.api.call/1",
        "replay_safe": replay_safe,
        "request": {"params": {
            input_name: f"input:{input_name}",
            "parameters": "profile:parameters",
            "implementation": "binding:implementation",
        }},
        "result": {
            "required_fields": ["schema", identity_name],
            "identity_fields": [identity_name],
            "schema_field": "schema",
            "schema_values": [f"stage{stage}-result/1"],
        },
    }


class _Core:
    def __init__(self) -> None:
        self.contracts = {
            "product.stage8.run": _contract(8, "document_version_id", "nlp_run_id"),
            "product.stage10.run": _contract(10, "nlp_run_id", "context_run_id"),
            "product.stage12.run": _contract(12, "context_run_id", "assembly_id"),
            "product.stage14.run": _contract(14, "assembly_id", "refinement_run_id"),
            "product.stage16.run": _contract(16, "refinement_run_id", "translation_revision_id"),
        }
        self.sources = {
            "product.stage8.run": "2" * 64,
            "product.stage10.run": "3" * 64,
            "product.stage12.run": "4" * 64,
            "product.stage14.run": "5" * 64,
            "product.stage16.run": "6" * 64,
        }
        self.results = {
            "product.stage8.run": {"schema": "stage8-result/1", "nlp_run_id": 101},
            "product.stage10.run": {"schema": "stage10-result/1", "context_run_id": 202},
            "product.stage12.run": {"schema": "stage12-result/1", "assembly_id": 303},
            "product.stage14.run": {"schema": "stage14-result/1", "refinement_run_id": 404},
            "product.stage16.run": {"schema": "stage16-result/1", "translation_revision_id": 505},
        }
        self.api_calls: list[str] = []
        self.fail_operation: str | None = None

    def _run(self, args, *, timeout=120.0, input_text=None):  # type: ignore[no-untyped-def]
        operation = args[4]
        stage = int(operation.split("stage", 1)[1].split(".", 1)[0])
        payload = {
            "schema": "rocketdict-workbench-operation-contract-probe/1",
            "database": {"path": "/tmp/db.sqlite", "exists": True},
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "mapping_module": "rocketdict.api.operations",
            "mapping_name": "OPERATIONS",
            "operation": operation,
            "callable_module": "rocketdict.api.operations",
            "callable_qualname": f"run_stage_{stage}",
            "callable_source_sha256": self.sources[operation],
            "contract_attribute": "rocketdict_execution_contract",
            "contract": self.contracts.get(operation),
        }
        return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=0)

    @staticmethod
    def _parse_json(text: str, *, context: str):  # type: ignore[no-untyped-def]
        return json.loads(text)

    def api(self, database, *args, timeout=300.0):  # type: ignore[no-untyped-def]
        operation = args[1]
        self.api_calls.append(operation)
        if operation == self.fail_operation:
            raise RuntimeError("simulated ambiguous failure")
        return self.results[operation]


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "product-run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_stage10_is_unresolvable_until_stage8_returns_exact_named_identity(tmp_path) -> None:
    path = _write(tmp_path, _state())
    discovery = discover_upstream_stage(path, 10)
    assert discovery["status"] == "input_resolution_blocked"
    assert "nlp_run_id" in discovery["input_error"]


def test_auto_advance_executes_8_10_12_14_then_hard_stops_before_stage16(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    result = advance_pre_gate_upstream(core, "/tmp/db.sqlite", path)

    assert result["schema"] == UPSTREAM_PIPELINE_SCHEMA
    assert result["status"] == "pre_hard_gate_core_completed"
    assert result["completed_now"] == [8, 10, 12, 14]
    assert result["next_stage"] == 15
    assert result["post_gate_stages_executed"] is False
    assert core.api_calls == [
        "product.stage8.run",
        "product.stage10.run",
        "product.stage12.run",
        "product.stage14.run",
    ]
    assert "product.stage16.run" not in core.api_calls

    state = json.loads(path.read_text(encoding="utf-8"))
    executions = state["steps"]["upstream_execution"]["executions"]
    assert executions["10"]["request"]["params"]["nlp_run_id"] == 101
    assert executions["12"]["request"]["params"]["context_run_id"] == 202
    assert executions["14"]["request"]["params"]["assembly_id"] == 303
    assert state["status"] == "pre_hard_gate_core_completed_awaiting_stage15_quality_gate"
    assert state["steps"]["upstream_execution"]["blocked_reason"] == "stage15_hard_quality_gate_execution_not_yet_proven"


def test_max_stages_supports_resumable_pre_gate_progress(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    first = advance_pre_gate_upstream(core, "/tmp/db.sqlite", path, max_stages=2)
    assert first["status"] == "progressed"
    assert first["completed_now"] == [8, 10]
    assert first["next_stage"] == 12
    second = advance_pre_gate_upstream(core, "/tmp/db.sqlite", path)
    assert second["status"] == "pre_hard_gate_core_completed"
    assert second["completed_now"] == [12, 14]
    assert core.api_calls == [
        "product.stage8.run",
        "product.stage10.run",
        "product.stage12.run",
        "product.stage14.run",
    ]


def test_ambiguous_exact_callable_stops_before_any_mutation(tmp_path) -> None:
    path = _write(tmp_path, _state(ambiguous_stage8=True))
    core = _Core()
    result = advance_pre_gate_upstream(core, "/tmp/db.sqlite", path)
    assert result["status"] == "blocked"
    assert result["blocked_stage"] == 8
    assert result["reason"] == "ambiguous_exact_matches"
    assert core.api_calls == []


def test_missing_execution_contract_stops_before_dispatch(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    core.contracts["product.stage8.run"] = None
    result = advance_pre_gate_upstream(core, "/tmp/db.sqlite", path)
    assert result["status"] == "blocked"
    assert result["reason"] == "public_execution_contract_unproven"
    assert core.api_calls == []


def test_replay_safe_ambiguous_dispatch_can_resume(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    verify_upstream_stage_binding(path, 8, "product.stage8.run")
    core.fail_operation = "product.stage8.run"
    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    core.fail_operation = None
    completed = execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    assert completed["status"] == "completed"
    assert completed["attempts"] == 2


def test_non_replay_safe_ambiguous_dispatch_requires_reconciliation(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    core.contracts["product.stage8.run"] = _contract(
        8, "document_version_id", "nlp_run_id", replay_safe=False
    )
    verify_upstream_stage_binding(path, 8, "product.stage8.run")
    core.fail_operation = "product.stage8.run"
    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    core.fail_operation = None
    with pytest.raises(RuntimeError, match="not replay-safe"):
        execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    assert core.api_calls == ["product.stage8.run"]


def test_stage16_manual_discovery_is_rejected_before_quality_gate_proof(tmp_path) -> None:
    path = _write(tmp_path, _state())
    with pytest.raises(RuntimeError, match="outside the pre-hard-gate"):
        discover_upstream_stage(path, 16)
