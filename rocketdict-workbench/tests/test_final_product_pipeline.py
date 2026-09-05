from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.final_product_pipeline import (
    DEFAULT_SET_NAME,
    FINAL_PIPELINE_SCHEMA,
    advance_final_product,
    discover_set_assembly,
    execute_set_assembly,
    execute_stage24_cards,
    execute_stage25_export,
)
from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_profile import QUALITY_GATES
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.quality_gate_execution import QUALITY_GATE_EXECUTION_SCHEMA, QUALITY_GATE_SET_RESULT_SCHEMA
from rocketdict_workbench.upstream_pipeline import PUBLIC_EXECUTION_CONTRACT_SCHEMA, TRANSPORT


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _quality(gate_set_sha: str) -> dict:
    executions = {}
    fps = {}
    for implementation in QUALITY_GATES:
        result = {"passed": True}
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
        fps[implementation] = record["fingerprint"]
    aggregate = {
        "schema": QUALITY_GATE_SET_RESULT_SCHEMA,
        "status": "passed",
        "stage_number": 15,
        "quality_gate_set_sha256": gate_set_sha,
        "gate_execution_fingerprints": fps,
        "all_hard_gates_passed": True,
    }
    aggregate["fingerprint"] = _canon(aggregate)
    return {"status": "passed", "executions": executions, "set_result": aggregate}


def _write_artifact(path: Path, payload: dict) -> dict:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(path.resolve()),
        "sha256": _file_sha(path),
        "payload_sha256": _canon(payload),
        "byte_size": path.stat().st_size,
    }


def _stage_profile(number: int, implementation: str, required: list[str], descriptor_digit: str) -> dict:
    return {
        "stage_number": number,
        "stage_key": "cards" if number == 24 else "final_exports",
        "implementation": implementation,
        "parameters": {},
        "adapter_descriptor_hash": descriptor_digit * 64,
        "required_inputs": required,
        "availability": {"available": True},
    }


def _callable(number: int, operation: str, implementation: str, required: list[str], descriptor_digit: str) -> dict:
    return {
        "mapping_module": "rocketdict.api.operations",
        "mapping_name": "OPERATIONS",
        "operation": operation,
        "callable_module": "rocketdict.api.operations",
        "callable_qualname": operation.replace(".", "_"),
        "signature": "(**params)",
        "parameters": [{"name": "params", "kind": "VAR_KEYWORD", "required": False}],
        "source_sha256": str((number % 7) + 1) * 64,
        "binding_metadata": {
            "stage_number": number,
            "stage_key": "cards" if number == 24 else "final_exports",
            "implementation_key": implementation,
            "adapter_descriptor_hash": descriptor_digit * 64,
            "required_inputs": required,
        },
    }


def _state(tmp_path: Path, database: Path) -> tuple[dict, dict[str, Path]]:
    stage24 = _stage_profile(24, "cards-current", ["lexical_sense_id"], "4")
    stage25 = _stage_profile(25, "export-json", ["set_revision_id"], "5")
    profile = {
        "stages": {"24": stage24, "25": stage25},
        "quality_gates": [],
        "workbench_stages": {},
    }
    frozen_gates = [
        {
            "stage_number": 15,
            "stage_key": "quality",
            "implementation": implementation,
            "adapter_descriptor_hash": str(index) * 64,
            "parameters_sha256": _canon({}),
            "required_inputs": ["assembly_id"],
            "execution_contract_sha256": str(index + 3) * 64,
            "hard_gate": True,
            "requires_reference": False,
        }
        for index, implementation in enumerate(QUALITY_GATES, 1)
    ]
    gate_set_sha = _canon({"stage_number": 15, "implementations": list(QUALITY_GATES), "gates": frozen_gates})
    preflight = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "ready",
        "identity": {
            "fingerprint": "f" * 64,
            "profile_sha256": _canon(profile),
            "source": {"sha256": "a" * 64, "import_event_id": 7, "document_version_id": 11, "selected_format": "txt"},
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "registry_hash": "registry-1",
            "quality_gate_set_sha256": gate_set_sha,
        },
        "profile": profile,
    }
    callables = [
        _callable(24, "product.cards.run", "cards-current", ["lexical_sense_id"], "4"),
        {
            "mapping_module": "rocketdict.api.operations",
            "mapping_name": "OPERATIONS",
            "operation": "product.cards.assemble_set",
            "callable_module": "rocketdict.api.operations",
            "callable_qualname": "assemble_set",
            "signature": "(**params)",
            "parameters": [{"name": "params", "kind": "VAR_KEYWORD", "required": False}],
            "source_sha256": "6" * 64,
            "binding_metadata": {},
        },
        _callable(25, "product.export.run", "export-json", ["set_revision_id"], "5"),
    ]
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

    provider = {"schema": "provider", "entries_sha256": "d" * 64}
    stage20 = {
        "results": [
            {"sense_id": 1, "entry_id": 11},
            {"sense_id": 2, "entry_id": 12},
            {"sense_id": 3, "entry_id": 13},
        ]
    }
    provider_path = tmp_path / "provider.json"
    stage20_path = tmp_path / "stage20.json"
    downstream_path = tmp_path / "downstream.json"
    downstream_path.write_text(json.dumps({"status": "completed"}) + "\n", encoding="utf-8")
    refs = {
        "provider": provider_path,
        "stage20": stage20_path,
        "downstream": downstream_path,
    }
    stage20_step = {
        "status": "completed_through_stage23",
        "provider": {"artifact": _write_artifact(provider_path, provider)},
        "stage20": {"artifact": _write_artifact(stage20_path, stage20)},
        "stage20_through_stage23": {
            "status": "completed",
            "runner_state_path": str(downstream_path.resolve()),
            "runner_state_sha256": _file_sha(downstream_path),
            "runner_input_fingerprint": "b" * 64,
        },
    }
    return {
        "schema": RUN_STATE_SCHEMA,
        "status": "stage23_completed_awaiting_stage24_cards",
        "root_identity": {"preflight_fingerprint": "f" * 64, "fingerprint": "e" * 64},
        "steps": {
            "preflight": {"status": "completed", "result": preflight, "result_sha256": _canon(preflight)},
            "upstream_contract_probe": {"status": "completed", "result": probe, "result_sha256": _canon(probe)},
            "upstream_execution": {"quality_gate": _quality(gate_set_sha)},
            "stage20_downstream": stage20_step,
            "cards": {"status": "pending", "attempts": 0},
            "export": {"status": "pending", "attempts": 0},
        },
    }, refs


def _contract(operation: str, *, replay_safe: bool = True) -> dict:
    if operation == "product.cards.run":
        return {
            "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
            "transport": TRANSPORT,
            "replay_safe": replay_safe,
            "request": {"params": {"lexical_sense_id": "input:lexical_sense_id", "parameters": "profile:parameters", "implementation": "binding:implementation"}},
            "result": {"required_fields": ["schema", "card_revision_id"], "identity_fields": ["card_revision_id"], "schema_field": "schema", "schema_values": ["card-result/1"]},
        }
    if operation == "product.cards.assemble_set":
        return {
            "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
            "transport": TRANSPORT,
            "replay_safe": replay_safe,
            "request": {"params": {"card_revision_ids": "input:card_revision_ids", "set_name": "input:set_name"}},
            "result": {"required_fields": ["schema", "set_revision_id"], "identity_fields": ["set_revision_id"], "schema_field": "schema", "schema_values": ["set-result/1"]},
        }
    if operation == "product.export.run":
        return {
            "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
            "transport": TRANSPORT,
            "replay_safe": replay_safe,
            "request": {"params": {"set_revision_id": "input:set_revision_id", "implementation": "binding:implementation"}},
            "result": {"required_fields": ["schema", "export_run_id"], "identity_fields": ["export_run_id"], "schema_field": "schema", "schema_values": ["export-result/1"]},
        }
    raise AssertionError(operation)


class _Core:
    def __init__(self, state: dict, *, cards_replay_safe: bool = True, expose_set_contract: bool = True) -> None:
        rows = state["steps"]["upstream_contract_probe"]["result"]["callable_operations"]
        self.rows = {row["operation"]: row for row in rows}
        self.cards_replay_safe = cards_replay_safe
        self.expose_set_contract = expose_set_contract
        self.calls: list[tuple[str, dict]] = []
        self.fail_next_card = False

    def _run(self, args, *, timeout=120.0, input_text=None):  # type: ignore[no-untyped-def]
        operation = args[4]
        row = self.rows[operation]
        if operation == "product.cards.assemble_set" and not self.expose_set_contract:
            contract = None
        else:
            contract = _contract(
                operation,
                replay_safe=self.cards_replay_safe if operation == "product.cards.run" else True,
            )
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
            "contract": contract,
        }
        return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=0)

    @staticmethod
    def _parse_json(text: str, *, context: str):  # type: ignore[no-untyped-def]
        return json.loads(text)

    def api(self, database, *args, timeout=300.0):  # type: ignore[no-untyped-def]
        operation = str(args[1])
        params = json.loads(args[3])
        self.calls.append((operation, params))
        if operation == "product.cards.run":
            if self.fail_next_card:
                self.fail_next_card = False
                raise RuntimeError("simulated ambiguous Stage24 card failure")
            sense_id = int(params["lexical_sense_id"])
            return {"schema": "card-result/1", "card_revision_id": 2400 + sense_id}
        if operation == "product.cards.assemble_set":
            assert params["set_name"] == DEFAULT_SET_NAME
            assert params["card_revision_ids"] == [2401, 2402, 2403]
            return {"schema": "set-result/1", "set_revision_id": 2499}
        if operation == "product.export.run":
            assert params["set_revision_id"] == 2499
            return {"schema": "export-result/1", "export_run_id": 2501}
        raise AssertionError(operation)


def _write_state(tmp_path: Path, database: Path) -> tuple[Path, dict]:
    payload, _refs = _state(tmp_path, database)
    path = tmp_path / "product-run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def test_full_final_product_runs_cards_set_assembly_and_export(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path, payload = _write_state(tmp_path, database)
    core = _Core(payload)

    result = advance_final_product(core, database, state_path)

    assert result["schema"] == FINAL_PIPELINE_SCHEMA
    assert result["status"] == "product_complete_exported"
    assert result["cards"]["completed_card_count"] == 3
    assert result["set_assembly"]["set_revision_id"] == 2499
    assert result["export"]["durable_identities"]["export_run_id"] == 2501
    assert [name for name, _params in core.calls] == [
        "product.cards.run", "product.cards.run", "product.cards.run",
        "product.cards.assemble_set", "product.export.run",
    ]
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "product_complete_exported"


def test_stage24_fanout_is_resumable_without_duplicate_card_calls(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path, payload = _write_state(tmp_path, database)
    core = _Core(payload)

    partial = advance_final_product(core, database, state_path, max_new_cards=1)
    assert partial["status"] == "stage24_partial"
    assert partial["cards"]["completed_card_count"] == 1
    completed = advance_final_product(core, database, state_path)
    assert completed["status"] == "product_complete_exported"
    card_calls = [params["lexical_sense_id"] for name, params in core.calls if name == "product.cards.run"]
    assert card_calls == [1, 2, 3]


def test_stage24_journal_hash_mutation_fails_closed(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path, payload = _write_state(tmp_path, database)
    core = _Core(payload)
    execute_stage24_cards(core, database, state_path, max_new_cards=1)
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    manifest_path = Path(persisted["steps"]["cards"]["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    journal = Path(manifest["journal_path"])
    text = journal.read_text(encoding="utf-8").replace("2401", "9999", 1)
    journal.write_text(text, encoding="utf-8")

    with pytest.raises(RuntimeError, match="hash mismatch|mutated"):
        execute_stage24_cards(core, database, state_path)


def test_truncated_tail_is_ignored_and_removed_before_next_stage24_append(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path, payload = _write_state(tmp_path, database)
    core = _Core(payload)
    execute_stage24_cards(core, database, state_path, max_new_cards=1)
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    manifest = json.loads(Path(persisted["steps"]["cards"]["manifest_path"]).read_text(encoding="utf-8"))
    journal = Path(manifest["journal_path"])
    with journal.open("ab") as fh:
        fh.write(b'{"schema":"rocketdict-workbench-stage24-card-journal/1","lexical_sense_id":2')

    result = execute_stage24_cards(core, database, state_path)
    assert result["completed_card_count"] == 3
    lines = journal.read_bytes().splitlines(keepends=True)
    assert all(line.endswith(b"\n") for line in lines)
    assert len(lines) == 3


def test_non_replay_safe_ambiguous_card_blocks_automatic_retry(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path, payload = _write_state(tmp_path, database)
    core = _Core(payload, cards_replay_safe=False)
    core.fail_next_card = True

    with pytest.raises(RuntimeError, match="simulated ambiguous"):
        execute_stage24_cards(core, database, state_path)
    calls = len(core.calls)
    with pytest.raises(RuntimeError, match="manual reconciliation"):
        execute_stage24_cards(core, database, state_path)
    assert len(core.calls) == calls


def test_set_assembly_requires_unique_public_contract_not_operation_name_guess(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path, payload = _write_state(tmp_path, database)
    core = _Core(payload, expose_set_contract=False)
    execute_stage24_cards(core, database, state_path)

    discovery = discover_set_assembly(core, database, state_path)
    assert discovery["status"] == "no_exact_match"
    with pytest.raises(RuntimeError, match="not uniquely proven"):
        execute_set_assembly(core, database, state_path)


def test_stage25_rejects_mutated_set_revision_evidence(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path, payload = _write_state(tmp_path, database)
    core = _Core(payload)
    execute_stage24_cards(core, database, state_path)
    execute_set_assembly(core, database, state_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["steps"]["cards"]["set_assembly"]["result"]["set_revision_id"] = 9999
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(RuntimeError, match="mutated"):
        execute_stage25_export(core, database, state_path)
