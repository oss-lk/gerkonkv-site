from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.aligned_lexical import POLICY_KEY
from rocketdict_workbench.post_gate_pipeline import (
    POST_GATE_PIPELINE_SCHEMA,
    advance_post_gate_pipeline,
    discover_post_gate_stage,
    execute_workbench_stage18,
)
from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_profile import QUALITY_GATES
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.quality_gate_execution import (
    QUALITY_GATE_EXECUTION_SCHEMA,
    QUALITY_GATE_SET_RESULT_SCHEMA,
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


def _quality_pass(quality_gate_set_sha256: str) -> dict:
    executions = {}
    fingerprints = {}
    for implementation in QUALITY_GATES:
        result = {"schema": "quality-result/1", "passed": True}
        record = {
            "schema": QUALITY_GATE_EXECUTION_SCHEMA,
            "status": "completed",
            "implementation": implementation,
            "result": result,
            "result_sha256": _canon(result),
            "passed": True,
        }
        record["fingerprint"] = _canon(record)
        executions[implementation] = record
        fingerprints[implementation] = record["fingerprint"]
    set_result = {
        "schema": QUALITY_GATE_SET_RESULT_SCHEMA,
        "status": "passed",
        "stage_number": 15,
        "quality_gate_set_sha256": quality_gate_set_sha256,
        "gate_execution_fingerprints": fingerprints,
        "all_hard_gates_passed": True,
    }
    set_result["fingerprint"] = _canon(set_result)
    return {"status": "passed", "executions": executions, "set_result": set_result}


def _stage(number: int, required_inputs: list[str]) -> tuple[dict, dict]:
    descriptor = f"{number % 10}" * 64
    parameters = {"stage": number}
    stage_key = {16: "finalization", 17: "alignment", 19: "sense_induction"}.get(number, f"stage-{number}")
    implementation = f"impl-{number}"
    contract = {
        "stage_number": number,
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters": parameters,
        "required_inputs": required_inputs,
    }
    selected = {
        "stage_number": number,
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters_sha256": _canon(parameters),
        "required_inputs": required_inputs,
        "execution_contract_sha256": _canon(contract),
    }
    profile = {
        "stage_number": number,
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters": parameters,
        "required_inputs": required_inputs,
    }
    return selected, profile


def _state(database: Path) -> dict:
    stage_inputs = {
        8: ["document_version_id"],
        10: ["document_version_id"],
        12: ["document_version_id"],
        14: ["document_version_id"],
        16: ["assembly_id"],
        17: ["translation_revision_id"],
        19: ["extraction_run_id"],
    }
    frozen = {}
    profiles = {}
    callables = []
    for number, inputs in stage_inputs.items():
        selected, profile = _stage(number, inputs)
        frozen[str(number)] = selected
        profiles[str(number)] = profile
        if number in {16, 17, 19}:
            callables.append(
                {
                    "mapping_module": "rocketdict.api.operations",
                    "mapping_name": "OPERATIONS",
                    "operation": f"product.stage{number}.run",
                    "callable_module": "rocketdict.api.operations",
                    "callable_qualname": f"run_stage_{number}",
                    "signature": "(**params)",
                    "parameters": [{"name": "params", "kind": "VAR_KEYWORD", "required": False}],
                    "source_sha256": str((number % 7) + 1) * 64,
                    "binding_metadata": {
                        "stage_number": number,
                        "stage_key": selected["stage_key"],
                        "implementation_key": selected["implementation"],
                        "adapter_descriptor_hash": selected["adapter_descriptor_hash"],
                        "required_inputs": inputs,
                    },
                }
            )
    frozen_gates = [
        {
            "stage_number": 15,
            "stage_key": "quality",
            "implementation": implementation,
            "adapter_descriptor_hash": str(index) * 64,
            "parameters_sha256": _canon({}),
            "required_inputs": ["assembly_id"],
            "execution_contract_sha256": _canon(
                {
                    "stage_number": 15,
                    "stage_key": "quality",
                    "implementation": implementation,
                    "adapter_descriptor_hash": str(index) * 64,
                    "parameters": {},
                    "required_inputs": ["assembly_id"],
                }
            ),
            "hard_gate": True,
            "requires_reference": False,
        }
        for index, implementation in enumerate(QUALITY_GATES, 1)
    ]
    gate_set = {"stage_number": 15, "implementations": list(QUALITY_GATES), "gates": frozen_gates}
    gate_set_sha = _canon(gate_set)
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
            "required_core_stages": frozen,
            "quality_gates": frozen_gates,
            "quality_gate_set_sha256": gate_set_sha,
        },
        "profile": {
            "stages": profiles,
            "quality_gates": [],
            "workbench_stages": {
                "18": {
                    "implementation": POLICY_KEY,
                    "policy": "alignment-aware product lexical extraction",
                    "requires_alignment": True,
                }
            },
        },
    }
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": str(database.resolve()), "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [{"module": "rocketdict.api.operations", "imported": True, "source_sha256": "c" * 64}],
        "parser_commands": ["call"],
        "callable_mapping_keys": [row["operation"] for row in callables],
        "callable_operations": callables,
        "operation_candidates": [row["operation"] for row in callables],
    }
    probe["fingerprint"] = _canon(probe)
    upstream = {
        "status": "stage15_passed",
        "executions": {
            "8": _completed(8, {"nlp_run_id": 8}),
            "10": _completed(10, {"context_run_id": 10}),
            "12": _completed(12, {"translation_run_id": 12}),
            "14": _completed(14, {"assembly_id": 14}),
        },
        "quality_gate": _quality_pass(gate_set_sha),
    }
    return {
        "schema": RUN_STATE_SCHEMA,
        "status": "stage15_hard_gates_passed_awaiting_stage16",
        "root_identity": {"preflight_fingerprint": "f" * 64, "fingerprint": "e" * 64},
        "steps": {
            "preflight": {"status": "completed", "result": preflight, "result_sha256": _canon(preflight)},
            "upstream_contract_probe": {"status": "completed", "result": probe, "result_sha256": _canon(probe)},
            "upstream_execution": upstream,
            "stage20_downstream": {"status": "pending"},
            "cards": {"status": "pending"},
            "export": {"status": "pending"},
        },
    }


def _contract(stage: int, *, replay_safe: bool = True) -> dict:
    spec = {
        16: ("assembly_id", ["translation_revision_id", "stage_result_id"]),
        17: ("translation_revision_id", ["alignment_run_id", "stage_result_id"]),
        19: ("extraction_run_id", ["sense_induction_run_id", "stage_result_id"]),
    }[stage]
    input_name, identities = spec
    return {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": TRANSPORT,
        "replay_safe": replay_safe,
        "request": {
            "params": {
                input_name: f"input:{input_name}",
                "parameters": "profile:parameters",
                "implementation": "binding:implementation",
            }
        },
        "result": {
            "required_fields": ["schema", *identities],
            "identity_fields": identities,
            "schema_field": "schema",
            "schema_values": [f"stage{stage}-result/1"],
        },
    }


class _Core:
    def __init__(self, state: dict, *, stage18_incomplete: bool = False) -> None:
        rows = state["steps"]["upstream_contract_probe"]["result"]["callable_operations"]
        self.rows = {row["operation"]: row for row in rows}
        self.api_calls: list[int] = []
        self.stage18_calls = 0
        self.stage18_incomplete = stage18_incomplete
        self.stage18_fail_once = False

    def _run(self, args, *, timeout=120.0, input_text=None):  # type: ignore[no-untyped-def]
        if len(args) >= 7 and args[2] == "rocketdict.api.operations":
            operation = args[4]
            row = self.rows[operation]
            stage = int(row["binding_metadata"]["stage_number"])
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
                "contract_attribute": args[6],
                "contract": _contract(stage),
            }
            return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=0)
        self.stage18_calls += 1
        if self.stage18_fail_once:
            self.stage18_fail_once = False
            raise RuntimeError("simulated ambiguous Stage18 failure")
        alignment_run_id = int(args[3])
        payload = {
            "policy": POLICY_KEY,
            "extraction_run_id": 180,
            "stage_result_id": 181,
            "alignment_run_id": alignment_run_id,
            "nlp_run_id": 8,
            "source_mode": "aligned",
            "candidate_count": 20,
            "selected_candidate_count": 15,
            "occurrence_count": 15,
            "lexical_entry_count": 12,
            "coverage_complete": not self.stage18_incomplete,
            "uncovered_token_count": 1 if self.stage18_incomplete else 0,
            "cache_hit": False,
            "target_evidence_occurrence_count": 10,
            "occurrences": [{"occurrence_id": 1, "entry_id": 2}],
        }
        return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=0)

    @staticmethod
    def _parse_json(text: str, *, context: str):  # type: ignore[no-untyped-def]
        return json.loads(text)

    def api(self, database, *args, timeout=300.0):  # type: ignore[no-untyped-def]
        operation = str(args[1])
        stage = int(operation.split("stage", 1)[1].split(".", 1)[0])
        self.api_calls.append(stage)
        if stage == 16:
            return {"schema": "stage16-result/1", "translation_revision_id": 160, "stage_result_id": 161}
        if stage == 17:
            return {"schema": "stage17-result/1", "alignment_run_id": 170, "stage_result_id": 171}
        if stage == 19:
            return {"schema": "stage19-result/1", "sense_induction_run_id": 190, "stage_result_id": 191}
        raise AssertionError(stage)


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_post_gate_stage16_is_impossible_without_aggregate_stage15_pass(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    state["steps"]["upstream_execution"]["quality_gate"].pop("set_result")
    path = _write(tmp_path, state)

    with pytest.raises(RuntimeError, match="no aggregate hard-gate PASS"):
        discover_post_gate_stage(path, 16)


def test_full_post_gate_pipeline_runs_16_17_workbench18_19_in_order(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state)

    result = advance_post_gate_pipeline(core, database, path)

    assert result["schema"] == POST_GATE_PIPELINE_SCHEMA
    assert result["status"] == "stage19_completed"
    assert result["completed_now"] == [16, 17, 18, 19]
    assert core.api_calls == [16, 17, 19]
    assert core.stage18_calls == 1
    persisted = json.loads(path.read_text(encoding="utf-8"))
    executions = persisted["steps"]["upstream_execution"]["executions"]
    assert executions["16"]["durable_identities"]["translation_revision_id"] == 160
    assert executions["17"]["durable_identities"]["alignment_run_id"] == 170
    assert executions["18"]["durable_identities"]["extraction_run_id"] == 180
    assert executions["18"]["result"]["occurrences_sha256"] == _canon([{"occurrence_id": 1, "entry_id": 2}])
    assert "occurrences" not in executions["18"]["result"]
    assert executions["19"]["durable_identities"]["sense_induction_run_id"] == 190
    assert persisted["status"] == "stage19_completed_ready_for_stage20_provider"


def test_stage19_input_is_bound_only_to_hash_verified_stage18_extraction_identity(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state)
    advance_post_gate_pipeline(core, database, path, max_steps=3)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["steps"]["upstream_execution"]["executions"]["18"]["result"]["extraction_run_id"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")

    discovery = discover_post_gate_stage(path, 19)
    assert discovery["status"] == "input_resolution_blocked"
    assert "mutated" in discovery["input_error"]


def test_incomplete_workbench_stage18_coverage_blocks_before_stage19(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state, stage18_incomplete=True)

    with pytest.raises(RuntimeError, match="coverage is incomplete"):
        advance_post_gate_pipeline(core, database, path)
    assert core.api_calls == [16, 17]
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["steps"]["upstream_execution"]["executions"]["18"]["status"] == "dispatch_failed_ambiguous"
    assert "19" not in persisted["steps"]["upstream_execution"]["executions"]


def test_workbench_stage18_ambiguous_failure_is_not_automatically_replayed(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state)
    advance_post_gate_pipeline(core, database, path, max_steps=2)
    core.stage18_fail_once = True

    with pytest.raises(RuntimeError, match="simulated ambiguous Stage18"):
        execute_workbench_stage18(core, database, path)
    calls = core.stage18_calls
    with pytest.raises(RuntimeError, match="manual reconciliation"):
        execute_workbench_stage18(core, database, path)
    assert core.stage18_calls == calls


def test_completed_workbench_stage18_is_cache_reused_without_reexecution(tmp_path) -> None:
    database = tmp_path / "db.sqlite"
    database.touch()
    state = _state(database)
    path = _write(tmp_path, state)
    core = _Core(state)
    advance_post_gate_pipeline(core, database, path, max_steps=3)
    calls = core.stage18_calls

    cached = execute_workbench_stage18(core, database, path)
    assert cached["cache_hit"] is True
    assert core.stage18_calls == calls
