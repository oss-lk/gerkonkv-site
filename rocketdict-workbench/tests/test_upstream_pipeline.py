from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.upstream_execution import EXECUTION_RECORD_SCHEMA, PUBLIC_EXECUTION_CONTRACT_SCHEMA
from rocketdict_workbench.upstream_pipeline import (
    UPSTREAM_DISCOVERY_SCHEMA,
    UPSTREAM_PIPELINE_SCHEMA,
    advance_product_upstream,
    build_upstream_identity_ledger,
    discover_upstream_bindings,
    execute_upstream_stage,
    verify_upstream_binding,
)


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _stage(number: int, key: str, implementation: str, required_inputs: list[str], descriptor_char: str) -> tuple[dict, dict]:
    descriptor = descriptor_char * 64
    profile = {
        "stage_number": number,
        "stage_key": key,
        "implementation": implementation,
        "parameters": {"quality": "product"},
        "adapter_descriptor_hash": descriptor,
        "required_inputs": list(required_inputs),
    }
    selected = {
        "stage_key": key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters_sha256": _canon(profile["parameters"]),
        "required_inputs": list(required_inputs),
        "execution_contract_sha256": _canon({
            "stage_number": number,
            "stage_key": key,
            "implementation": implementation,
            "adapter_descriptor_hash": descriptor,
            "parameters": profile["parameters"],
            "required_inputs": list(required_inputs),
        }),
    }
    return selected, profile


def _operation(number: int, key: str, implementation: str, required_inputs: list[str], descriptor_char: str, operation: str, source_char: str) -> dict:
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
            "stage_key": key,
            "implementation_key": implementation,
            "adapter_descriptor_hash": descriptor_char * 64,
            "required_inputs": list(required_inputs),
        },
    }


def _state(*, ambiguous_stage8: bool = False) -> dict:
    s8, p8 = _stage(8, "nlp_analysis", "en-sm", ["document_version_id"], "d")
    s10, p10 = _stage(10, "context_enrichment", "context-v1", ["nlp_run_id"], "e")
    operations = [
        _operation(8, "nlp_analysis", "en-sm", ["document_version_id"], "d", "product.stage8.run", "b"),
        _operation(10, "context_enrichment", "context-v1", ["nlp_run_id"], "e", "product.stage10.run", "c"),
    ]
    if ambiguous_stage8:
        operations.append(_operation(8, "nlp_analysis", "en-sm", ["document_version_id"], "d", "product.stage8.alternate", "a"))
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
            "required_core_stages": {"8": s8, "10": s10},
        },
        "profile": {"stages": {"8": p8, "10": p10}},
    }
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": "/tmp/db.sqlite", "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [{"module": "rocketdict.api.operations", "imported": True, "source_sha256": "9" * 64}],
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
        "request": {"params": {input_name: f"input:{input_name}", "parameters": "profile:parameters", "implementation": "binding:implementation"}},
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
        }
        self.sources = {"product.stage8.run": "b" * 64, "product.stage10.run": "c" * 64}
        self.results = {
            "product.stage8.run": {"schema": "stage8-result/1", "nlp_run_id": 101},
            "product.stage10.run": {"schema": "stage10-result/1", "context_run_id": 202},
        }
        self.api_calls: list[str] = []
        self.fail_operation: str | None = None

    def _run(self, args, *, timeout=120.0, input_text=None):  # type: ignore[no-untyped-def]
        operation = args[4]
        payload = {
            "schema": "rocketdict-workbench-operation-contract-probe/1",
            "database": {"path": "/tmp/db.sqlite", "exists": True},
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "mapping_module": "rocketdict.api.operations",
            "mapping_name": "OPERATIONS",
            "operation": operation,
            "callable_module": "rocketdict.api.operations",
            "callable_qualname": "run_stage_8" if operation.endswith("stage8.run") else "run_stage_10",
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


def test_stage10_is_unresolvable_until_stage8_returns_nlp_identity(tmp_path) -> None:
    path = _write(tmp_path, _state())
    discovery = discover_upstream_bindings(path, 10)
    assert discovery["schema"] == UPSTREAM_DISCOVERY_SCHEMA
    assert discovery["status"] == "unresolved_required_inputs"
    assert discovery["missing_inputs"] == ["nlp_run_id"]


def test_auto_advance_executes_stage8_then_stage10_from_durable_identity_ledger(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    result = advance_product_upstream(core, "/tmp/db.sqlite", path, max_stages=2)
    assert result["schema"] == UPSTREAM_PIPELINE_SCHEMA
    assert result["status"] == "progressed"
    assert result["completed_now"] == [8, 10]
    assert result["next_stage"] == 12
    assert core.api_calls == ["product.stage8.run", "product.stage10.run"]

    persisted = json.loads(path.read_text(encoding="utf-8"))
    executions = persisted["steps"]["upstream_execution"]["executions"]
    assert executions["8"]["durable_identities"] == {"nlp_run_id": 101}
    assert executions["10"]["request"]["params"]["nlp_run_id"] == 101
    assert executions["10"]["durable_identities"] == {"context_run_id": 202}
    ledger = build_upstream_identity_ledger(persisted, persisted["steps"]["preflight"]["result"])
    assert ledger["values"]["document_version_id"] == 11
    assert ledger["values"]["nlp_run_id"] == 101
    assert ledger["values"]["context_run_id"] == 202


def test_ambiguous_exact_runtime_operations_stop_before_database_mutation(tmp_path) -> None:
    path = _write(tmp_path, _state(ambiguous_stage8=True))
    core = _Core()
    result = advance_product_upstream(core, "/tmp/db.sqlite", path)
    assert result["status"] == "blocked"
    assert result["blocked_stage"] == 8
    assert result["reason"] == "ambiguous_exact_matches"
    assert core.api_calls == []
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["status"] == "blocked_before_stage8"


def test_missing_public_execution_contract_stops_before_dispatch(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    core.contracts["product.stage8.run"] = None
    result = advance_product_upstream(core, "/tmp/db.sqlite", path)
    assert result["status"] == "blocked"
    assert result["blocked_stage"] == 8
    assert result["reason"] == "public_execution_contract_unproven"
    assert core.api_calls == []


def test_generic_binding_freezes_prior_stage_identity_origin(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    advance_product_upstream(core, "/tmp/db.sqlite", path, max_stages=1)
    binding = verify_upstream_binding(path, 10, "product.stage10.run")
    assert binding["frozen_inputs"] == {"nlp_run_id": 101}
    assert binding["input_origins"] == {"nlp_run_id": "stage8.result"}
    assert binding["proof"]["proof_mode"] == "live-registry-plus-exact-runtime-callable-v2"


def test_durable_identity_collision_fails_closed(tmp_path) -> None:
    payload = _state()
    result = {"schema": "stage8-result/1", "document_version_id": 999}
    payload["steps"]["upstream_execution"]["executions"] = {
        "8": {
            "schema": EXECUTION_RECORD_SCHEMA,
            "status": "completed",
            "stage_number": 8,
            "result": result,
            "result_sha256": _canon(result),
            "durable_identities": {"document_version_id": 999},
        }
    }
    path = _write(tmp_path, payload)
    state = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(RuntimeError, match="Durable identity collision"):
        build_upstream_identity_ledger(state, state["steps"]["preflight"]["result"])


def test_ambiguous_dispatch_is_persisted_and_replay_safe_retry_can_complete(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    verify_upstream_binding(path, 8, "product.stage8.run")
    core.fail_operation = "product.stage8.run"
    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    state = json.loads(path.read_text(encoding="utf-8"))
    assert state["steps"]["upstream_execution"]["executions"]["8"]["status"] == "dispatch_failed_ambiguous"
    core.fail_operation = None
    completed = execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    assert completed["status"] == "completed"
    assert completed["attempts"] == 2


def test_non_replay_safe_ambiguous_dispatch_is_not_automatically_replayed(tmp_path) -> None:
    path = _write(tmp_path, _state())
    core = _Core()
    core.contracts["product.stage8.run"] = _contract(8, "document_version_id", "nlp_run_id", replay_safe=False)
    verify_upstream_binding(path, 8, "product.stage8.run")
    core.fail_operation = "product.stage8.run"
    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    core.fail_operation = None
    with pytest.raises(RuntimeError, match="not replay-safe"):
        execute_upstream_stage(core, "/tmp/db.sqlite", path, 8)
    assert core.api_calls == ["product.stage8.run"]
