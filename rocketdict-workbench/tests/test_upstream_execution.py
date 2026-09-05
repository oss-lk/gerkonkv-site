from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.upstream_binding import verify_stage8_binding
from rocketdict_workbench.upstream_execution import (
    EXECUTION_PROOF_SCHEMA,
    EXECUTION_RECORD_SCHEMA,
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    execute_stage8,
    plan_stage8_execution,
    prove_stage8_execution_contract,
)


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _state() -> dict:
    descriptor = "d" * 64
    profile_stage = {
        "stage_number": 8,
        "stage_key": "nlp_analysis",
        "implementation": "en-sm",
        "parameters": {"batch_size": 32},
        "adapter_descriptor_hash": descriptor,
        "required_inputs": ["document_version_id"],
    }
    selected = {
        "stage_key": "nlp_analysis",
        "implementation": "en-sm",
        "adapter_descriptor_hash": descriptor,
        "parameters_sha256": _canon(profile_stage["parameters"]),
        "required_inputs": ["document_version_id"],
        "execution_contract_sha256": _canon(
            {
                "stage_number": 8,
                "stage_key": "nlp_analysis",
                "implementation": "en-sm",
                "adapter_descriptor_hash": descriptor,
                "parameters": profile_stage["parameters"],
                "required_inputs": ["document_version_id"],
            }
        ),
    }
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
    operation = {
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
        "binding_metadata": {
            "stage_number": 8,
            "stage_key": "nlp_analysis",
            "implementation_key": "en-sm",
            "adapter_descriptor_hash": descriptor,
            "required_inputs": ["document_version_id"],
        },
    }
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": "/tmp/db.sqlite", "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [{"module": "rocketdict.api.operations", "imported": True, "source_sha256": "c" * 64}],
        "parser_commands": ["call"],
        "callable_mapping_keys": ["product.stage8.run"],
        "callable_operations": [operation],
        "operation_candidates": ["call", "product.stage8.run"],
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


def _contract(*, replay_safe: bool = True) -> dict:
    return {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": "rocketdict.api.call/1",
        "replay_safe": replay_safe,
        "request": {
            "params": {
                "document_version_id": "input:document_version_id",
                "parameters": "profile:parameters",
                "implementation": "binding:implementation",
            }
        },
        "result": {
            "required_fields": ["schema", "nlp_run_id", "stage_result_id"],
            "identity_fields": ["nlp_run_id", "stage_result_id"],
            "schema_field": "schema",
            "schema_values": ["rocketdict-stage8-execution-result/1"],
        },
    }


class _Core:
    def __init__(self, *, contract: object = None, replay_safe: bool = True, source_sha: str = "b" * 64) -> None:
        self.contract = _contract(replay_safe=replay_safe) if contract is None else contract
        self.source_sha = source_sha
        self.probe_calls = 0
        self.api_calls: list[tuple] = []
        self.api_failures_remaining = 0
        self.api_result: object = {
            "schema": "rocketdict-stage8-execution-result/1",
            "nlp_run_id": 23,
            "stage_result_id": 24,
        }

    def _run(self, args, *, timeout=120.0, input_text=None):  # type: ignore[no-untyped-def]
        self.probe_calls += 1
        payload = {
            "schema": "rocketdict-workbench-operation-contract-probe/1",
            "database": {"path": "/tmp/db.sqlite", "exists": True},
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "mapping_module": "rocketdict.api.operations",
            "mapping_name": "OPERATIONS",
            "operation": "product.stage8.run",
            "callable_module": "rocketdict.api.operations",
            "callable_qualname": "run_product_stage8",
            "callable_source_sha256": self.source_sha,
            "contract_attribute": "rocketdict_execution_contract",
            "contract": self.contract,
        }
        return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=0)

    @staticmethod
    def _parse_json(text: str, *, context: str):  # type: ignore[no-untyped-def]
        return json.loads(text)

    def api(self, database, *args, timeout=300.0):  # type: ignore[no-untyped-def]
        self.api_calls.append((str(Path(database).resolve()), args, timeout))
        if self.api_failures_remaining:
            self.api_failures_remaining -= 1
            raise RuntimeError("simulated ambiguous dispatch failure")
        return self.api_result


def _bound_state(tmp_path: Path) -> Path:
    path = tmp_path / "product-run.json"
    path.write_text(json.dumps(_state()), encoding="utf-8")
    verify_stage8_binding(path, "product.stage8.run")
    return path


def test_stage8_execution_contract_is_proved_and_plan_freezes_request(tmp_path) -> None:
    path = _bound_state(tmp_path)
    core = _Core()

    proof = prove_stage8_execution_contract(core, "/tmp/db.sqlite", path)
    plan = plan_stage8_execution(path)

    assert proof["schema"] == EXECUTION_PROOF_SCHEMA
    assert proof["contract"]["replay_safe"] is True
    assert len(proof["contract_sha256"]) == 64
    assert plan["status"] == "ready"
    assert plan["request"]["operation"] == "product.stage8.run"
    assert plan["request"]["params"] == {
        "document_version_id": 11,
        "parameters": {"batch_size": 32},
        "implementation": "en-sm",
    }
    assert len(plan["request_sha256"]) == 64


def test_stage8_execution_uses_only_public_api_call_and_persists_result_identity(tmp_path) -> None:
    path = _bound_state(tmp_path)
    core = _Core()

    first = execute_stage8(core, "/tmp/db.sqlite", path)
    second = execute_stage8(core, "/tmp/db.sqlite", path)

    assert first["schema"] == EXECUTION_RECORD_SCHEMA
    assert first["status"] == "completed"
    assert first["durable_identities"] == {"nlp_run_id": 23, "stage_result_id": 24}
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert len(core.api_calls) == 1
    _database, args, timeout = core.api_calls[0]
    assert args[:3] == ("call", "product.stage8.run", "--params")
    assert json.loads(args[3]) == {
        "document_version_id": 11,
        "implementation": "en-sm",
        "parameters": {"batch_size": 32},
    }
    assert timeout == 1800

    persisted = json.loads(path.read_text(encoding="utf-8"))
    execution = persisted["steps"]["upstream_execution"]["executions"]["8"]
    assert execution["result_sha256"] == _canon(execution["result"])
    assert persisted["status"] == "stage8_completed_awaiting_next_upstream_binding"


def test_missing_public_execution_contract_blocks_before_dispatch(tmp_path) -> None:
    path = _bound_state(tmp_path)
    core = _Core(contract=None)
    core.contract = None

    with pytest.raises(RuntimeError, match="does not publish"):
        execute_stage8(core, "/tmp/db.sqlite", path)
    assert core.api_calls == []


def test_callable_source_drift_blocks_before_dispatch(tmp_path) -> None:
    path = _bound_state(tmp_path)
    core = _Core(source_sha="9" * 64)

    with pytest.raises(RuntimeError, match="callable identity drift"):
        execute_stage8(core, "/tmp/db.sqlite", path)
    assert core.api_calls == []


def test_invalid_result_is_persisted_as_ambiguous_failure(tmp_path) -> None:
    path = _bound_state(tmp_path)
    core = _Core()
    core.api_result = {"schema": "rocketdict-stage8-execution-result/1", "nlp_run_id": 23}

    with pytest.raises(RuntimeError, match="lacks required fields"):
        execute_stage8(core, "/tmp/db.sqlite", path)

    state = json.loads(path.read_text(encoding="utf-8"))
    record = state["steps"]["upstream_execution"]["executions"]["8"]
    assert record["status"] == "dispatch_failed_ambiguous"
    assert state["steps"]["upstream_execution"]["status"] == "stage8_retryable_after_ambiguous_failure"


def test_non_replay_safe_ambiguous_failure_cannot_dispatch_again(tmp_path) -> None:
    path = _bound_state(tmp_path)
    core = _Core(replay_safe=False)
    core.api_failures_remaining = 1

    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_stage8(core, "/tmp/db.sqlite", path)
    assert len(core.api_calls) == 1

    with pytest.raises(RuntimeError, match="manual/recovery reconciliation"):
        execute_stage8(core, "/tmp/db.sqlite", path)
    assert len(core.api_calls) == 1


def test_replay_safe_ambiguous_failure_can_retry_and_complete(tmp_path) -> None:
    path = _bound_state(tmp_path)
    core = _Core(replay_safe=True)
    core.api_failures_remaining = 1

    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_stage8(core, "/tmp/db.sqlite", path)
    completed = execute_stage8(core, "/tmp/db.sqlite", path)

    assert len(core.api_calls) == 2
    assert completed["status"] == "completed"
    assert completed["attempts"] == 2
