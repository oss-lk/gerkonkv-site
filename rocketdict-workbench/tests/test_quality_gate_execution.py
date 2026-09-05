from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_profile import QUALITY_GATES
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.quality_gate_execution import (
    PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
    QUALITY_GATE_EXECUTION_SCHEMA,
    discover_quality_gate_bindings,
    execute_quality_gates,
    require_quality_gate_pass,
    verify_quality_gate_bindings,
)
from rocketdict_workbench.upstream_execution import EXECUTION_RECORD_SCHEMA
from rocketdict_workbench.upstream_pipeline import PUBLIC_EXECUTION_CONTRACT_SCHEMA, TRANSPORT


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _completed(stage: int, identities: dict) -> dict:  # type: ignore[no-untyped-def]
    result = {"schema": f"stage{stage}-result/1", **identities}
    return {
        "schema": EXECUTION_RECORD_SCHEMA,
        "status": "completed",
        "stage_number": stage,
        "result": result,
        "result_sha256": _canon(result),
        "durable_identities": identities,
    }


def _state(database: Path) -> dict:
    stage_rows = {}
    profile_stages = {}
    for number in (8, 10, 12, 14, 16, 17, 19):
        required = ["document_version_id"] if number <= 14 else ["assembly_id"]
        descriptor = f"{number % 10}" * 64
        parameters = {"stage": number}
        row = {
            "stage_number": number,
            "stage_key": f"stage-{number}",
            "implementation": f"impl-{number}",
            "adapter_descriptor_hash": descriptor,
            "parameters_sha256": _canon(parameters),
            "required_inputs": required,
            "execution_contract_sha256": _canon(
                {
                    "stage_number": number,
                    "stage_key": f"stage-{number}",
                    "implementation": f"impl-{number}",
                    "adapter_descriptor_hash": descriptor,
                    "parameters": parameters,
                    "required_inputs": required,
                }
            ),
        }
        stage_rows[str(number)] = row
        profile_stages[str(number)] = {
            "stage_number": number,
            "stage_key": row["stage_key"],
            "implementation": row["implementation"],
            "adapter_descriptor_hash": descriptor,
            "parameters": parameters,
            "required_inputs": required,
        }

    frozen_gates = []
    profile_gates = []
    callable_rows = []
    for index, implementation in enumerate(QUALITY_GATES, 1):
        descriptor = str(index) * 64
        parameters = {"gate": index}
        gate = {
            "stage_number": 15,
            "stage_key": "quality_assessment",
            "implementation": implementation,
            "adapter_descriptor_hash": descriptor,
            "parameters_sha256": _canon(parameters),
            "required_inputs": ["assembly_id"],
            "execution_contract_sha256": _canon(
                {
                    "stage_number": 15,
                    "stage_key": "quality_assessment",
                    "implementation": implementation,
                    "adapter_descriptor_hash": descriptor,
                    "parameters": parameters,
                    "required_inputs": ["assembly_id"],
                }
            ),
            "hard_gate": True,
            "requires_reference": False,
        }
        frozen_gates.append(gate)
        profile_gates.append(
            {
                "stage_number": 15,
                "stage_key": "quality_assessment",
                "implementation": implementation,
                "adapter_descriptor_hash": descriptor,
                "parameters": parameters,
                "required_inputs": ["assembly_id"],
                "hard_gate": True,
                "requires_reference": False,
            }
        )
        callable_rows.append(
            {
                "mapping_module": "rocketdict.api.operations",
                "mapping_name": "OPERATIONS",
                "operation": f"quality.{index}.run",
                "callable_module": "rocketdict.api.operations",
                "callable_qualname": f"run_quality_{index}",
                "signature": "(**params)",
                "parameters": [{"name": "params", "kind": "VAR_KEYWORD", "required": False}],
                "source_sha256": str(index + 3) * 64,
                "binding_metadata": {
                    "stage_number": 15,
                    "stage_key": "quality_assessment",
                    "implementation_key": implementation,
                    "adapter_descriptor_hash": descriptor,
                    "required_inputs": ["assembly_id"],
                },
            }
        )

    gate_set = {
        "stage_number": 15,
        "implementations": list(QUALITY_GATES),
        "gates": frozen_gates,
    }
    preflight = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "ready",
        "identity": {
            "fingerprint": "f" * 64,
            "source": {
                "sha256": "a" * 64,
                "import_event_id": 7,
                "document_version_id": 11,
                "selected_format": "txt",
            },
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "registry_hash": "registry-1",
            "required_core_stages": stage_rows,
            "quality_gates": frozen_gates,
            "quality_gate_set_sha256": _canon(gate_set),
        },
        "profile": {"stages": profile_stages, "quality_gates": profile_gates},
    }
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": str(database.resolve()), "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [{"module": "rocketdict.api.operations", "imported": True, "source_sha256": "c" * 64}],
        "parser_commands": ["call"],
        "callable_mapping_keys": [row["operation"] for row in callable_rows],
        "callable_operations": callable_rows,
        "operation_candidates": [row["operation"] for row in callable_rows],
    }
    probe["fingerprint"] = _canon(probe)
    return {
        "schema": RUN_STATE_SCHEMA,
        "status": "pre_hard_gate_core_completed_awaiting_stage15_quality_gate",
        "root_identity": {"preflight_fingerprint": "f" * 64, "fingerprint": "e" * 64},
        "steps": {
            "preflight": {"status": "completed", "result": preflight, "result_sha256": _canon(preflight)},
            "upstream_contract_probe": {"status": "completed", "result": probe, "result_sha256": _canon(probe)},
            "upstream_execution": {
                "status": "pre_hard_gate_core_completed",
                "executions": {
                    "8": _completed(8, {"nlp_run_id": 8}),
                    "10": _completed(10, {"context_run_id": 10}),
                    "12": _completed(12, {"translation_run_id": 12}),
                    "14": _completed(14, {"assembly_id": 14}),
                },
            },
            "stage20_downstream": {"status": "pending"},
            "cards": {"status": "pending"},
            "export": {"status": "pending"},
        },
    }


def _execution_contract(*, replay_safe: bool = True, require_pass_field: bool = True) -> dict:
    required_fields = ["schema", "quality_result_id"]
    if require_pass_field:
        required_fields.append("passed")
    return {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": TRANSPORT,
        "replay_safe": replay_safe,
        "request": {
            "params": {
                "assembly_id": "input:assembly_id",
                "parameters": "profile:parameters",
                "implementation": "binding:implementation",
            }
        },
        "result": {
            "required_fields": required_fields,
            "identity_fields": ["quality_result_id"],
            "schema_field": "schema",
            "schema_values": ["quality-gate-result/1"],
        },
    }


def _semantics() -> dict:
    return {
        "schema": PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
        "stage_number": 15,
        "hard_gate": True,
        "failure_blocks_downstream": True,
        "pass_condition": {"field": "passed", "equals": True},
    }


class _Core:
    def __init__(
        self,
        state: dict,
        *,
        failed_gate: str | None = None,
        missing_semantics_gate: str | None = None,
        replay_safe: bool = True,
        require_pass_field: bool = True,
    ) -> None:
        probe = state["steps"]["upstream_contract_probe"]["result"]
        self.rows = {row["operation"]: row for row in probe["callable_operations"]}
        self.failed_gate = failed_gate
        self.missing_semantics_gate = missing_semantics_gate
        self.replay_safe = replay_safe
        self.require_pass_field = require_pass_field
        self.api_calls: list[str] = []
        self.fail_dispatch_once = False

    def _run(self, args, *, timeout=120.0, input_text=None):  # type: ignore[no-untyped-def]
        operation = args[4]
        attribute = args[6]
        row = self.rows[operation]
        implementation = row["binding_metadata"]["implementation_key"]
        if attribute == "rocketdict_execution_contract":
            contract = _execution_contract(replay_safe=self.replay_safe, require_pass_field=self.require_pass_field)
        elif attribute == "rocketdict_quality_gate_semantics":
            contract = None if implementation == self.missing_semantics_gate else _semantics()
        else:
            raise AssertionError(attribute)
        payload = {
            "schema": "rocketdict-workbench-operation-contract-probe/1",
            "database": {"path": args[5], "exists": True},
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "mapping_module": row["mapping_module"],
            "mapping_name": row["mapping_name"],
            "operation": operation,
            "callable_module": row["callable_module"],
            "callable_qualname": row["callable_qualname"],
            "callable_source_sha256": row["source_sha256"],
            "contract_attribute": attribute,
            "contract": contract,
        }
        return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=0)

    @staticmethod
    def _parse_json(text: str, *, context: str):  # type: ignore[no-untyped-def]
        return json.loads(text)

    def api(self, database, *args, timeout=300.0):  # type: ignore[no-untyped-def]
        operation = str(args[1])
        self.api_calls.append(operation)
        if self.fail_dispatch_once:
            self.fail_dispatch_once = False
            raise RuntimeError("simulated ambiguous gate dispatch")
        row = self.rows[operation]
        implementation = row["binding_metadata"]["implementation_key"]
        index = list(QUALITY_GATES).index(implementation) + 1
        return {
            "schema": "quality-gate-result/1",
            "quality_result_id": 100 + index,
            "passed": implementation != self.failed_gate,
        }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_quality_gate_discovery_and_binding_require_all_three_exact_callables(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)

    discovery = discover_quality_gate_bindings(path)
    assert discovery["status"] == "all_unique_exact_matches"
    assert [row["implementation"] for row in discovery["gates"]] == list(QUALITY_GATES)
    assert all(row["input_resolution"]["frozen_inputs"] == {"assembly_id": 14} for row in discovery["gates"])

    bound = verify_quality_gate_bindings(path)
    assert bound["status"] == "bindings_verified"
    assert set(bound["bindings"]) == set(QUALITY_GATES)


def test_all_three_hard_gates_must_pass_before_stage16_is_unblocked(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state)

    result = execute_quality_gates(core, database, path)
    assert result["status"] == "passed"
    assert result["all_hard_gates_passed"] is True
    assert len(core.api_calls) == 3
    assert result["completed_now"] == list(QUALITY_GATES)

    pass_evidence = require_quality_gate_pass(path)
    assert pass_evidence["fingerprint"] == result["fingerprint"]
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["status"] == "stage15_hard_gates_passed_awaiting_stage16"
    assert set(persisted["steps"]["upstream_execution"]["quality_gate"]["executions"]) == set(QUALITY_GATES)


def test_hard_gate_failure_is_terminal_and_later_gate_is_not_dispatched(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    failed = QUALITY_GATES[1]
    core = _Core(state, failed_gate=failed)

    result = execute_quality_gates(core, database, path)
    assert result["status"] == "failed"
    assert result["failed_gate"] == failed
    assert len(core.api_calls) == 2
    with pytest.raises(RuntimeError, match="no aggregate hard-gate PASS|did not all pass"):
        require_quality_gate_pass(path)


def test_missing_quality_semantics_blocks_before_any_gate_dispatch(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state, missing_semantics_gate=QUALITY_GATES[2])

    with pytest.raises(RuntimeError, match="does not publish"):
        execute_quality_gates(core, database, path)
    assert core.api_calls == []


def test_pass_field_must_be_required_by_public_result_contract(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state, require_pass_field=False)

    with pytest.raises(RuntimeError, match="pass field is not required"):
        execute_quality_gates(core, database, path)
    assert core.api_calls == []


def test_non_replay_safe_ambiguous_gate_dispatch_cannot_be_replayed(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state, replay_safe=False)
    core.fail_dispatch_once = True

    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_quality_gates(core, database, path)
    assert len(core.api_calls) == 1
    with pytest.raises(RuntimeError, match="not replay-safe"):
        execute_quality_gates(core, database, path)
    assert len(core.api_calls) == 1


def test_mutated_completed_gate_result_invalidates_aggregate_pass(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state)
    execute_quality_gates(core, database, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    first = payload["steps"]["upstream_execution"]["quality_gate"]["executions"][QUALITY_GATES[0]]
    first["result"]["passed"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="result was mutated"):
        require_quality_gate_pass(path)
