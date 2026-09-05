from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import rocketdict_workbench.unified_stage20 as unified
from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA
from rocketdict_workbench.product_profile import QUALITY_GATES
from rocketdict_workbench.product_run_state import API_PROBE_SCHEMA, RUN_STATE_SCHEMA
from rocketdict_workbench.quality_gate_execution import QUALITY_GATE_EXECUTION_SCHEMA, QUALITY_GATE_SET_RESULT_SCHEMA
from rocketdict_workbench.upstream_execution import EXECUTION_RECORD_SCHEMA


def _canon(value) -> str:  # type: ignore[no-untyped-def]
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _quality_pass(gate_set_sha: str) -> dict:
    executions = {}
    fingerprints = {}
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
        fingerprints[implementation] = record["fingerprint"]
    result = {
        "schema": QUALITY_GATE_SET_RESULT_SCHEMA,
        "status": "passed",
        "stage_number": 15,
        "quality_gate_set_sha256": gate_set_sha,
        "gate_execution_fingerprints": fingerprints,
        "all_hard_gates_passed": True,
    }
    result["fingerprint"] = _canon(result)
    return {"status": "passed", "executions": executions, "set_result": result}


def _stage19_record() -> dict:
    result = {"schema": "stage19-result/1", "sense_induction_run_id": 190, "stage_result_id": 191}
    record = {
        "schema": EXECUTION_RECORD_SCHEMA,
        "status": "completed",
        "stage_number": 19,
        "result": result,
        "result_sha256": _canon(result),
        "durable_identities": {"sense_induction_run_id": 190, "stage_result_id": 191},
    }
    record["fingerprint"] = _canon(record)
    return record


def _state(database: Path) -> dict:
    frozen_gates = [
        {
            "stage_number": 15,
            "stage_key": "quality",
            "implementation": implementation,
            "adapter_descriptor_hash": str(i) * 64,
            "parameters_sha256": _canon({}),
            "required_inputs": ["assembly_id"],
            "execution_contract_sha256": str(i + 3) * 64,
            "hard_gate": True,
            "requires_reference": False,
        }
        for i, implementation in enumerate(QUALITY_GATES, 1)
    ]
    gate_set = {"stage_number": 15, "implementations": list(QUALITY_GATES), "gates": frozen_gates}
    gate_set_sha = _canon(gate_set)
    preflight = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "ready",
        "identity": {
            "fingerprint": "f" * 64,
            "source": {"sha256": "a" * 64, "import_event_id": 7, "document_version_id": 11, "selected_format": "txt"},
            "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
            "registry_hash": "registry-1",
            "quality_gate_set_sha256": gate_set_sha,
        },
        "profile": {
            "workbench_stages": {
                "20_provider": {
                    "implementation": unified.STAGE20_PROVIDER_POLICY,
                    "selection": "lexical-primary-arbitration-v1 over aligned-local-consensus evidence",
                    "probe_policy": "pos-dependency-dictionary-shape-v3",
                    "retain_nbest_evidence": True,
                    "alignment_role": "context_and_occurrence_coverage_not_headword_form",
                }
            }
        },
    }
    probe = {
        "schema": API_PROBE_SCHEMA,
        "status": "observed",
        "database": {"path": str(database.resolve()), "exists": True},
        "core": {"rocketdict_version": "0.30.40", "api_version": "1"},
        "api_modules": [{"module": "rocketdict.api", "imported": True, "source_sha256": "c" * 64}],
        "callable_operations": [],
        "parser_commands": [],
        "callable_mapping_keys": [],
        "operation_candidates": [],
    }
    probe["fingerprint"] = _canon(probe)
    return {
        "schema": RUN_STATE_SCHEMA,
        "status": "stage19_completed_ready_for_stage20_provider",
        "root_identity": {"preflight_fingerprint": "f" * 64, "fingerprint": "e" * 64},
        "steps": {
            "preflight": {"status": "completed", "result": preflight, "result_sha256": _canon(preflight)},
            "upstream_contract_probe": {"status": "completed", "result": probe, "result_sha256": _canon(probe)},
            "upstream_execution": {
                "status": "stage19_completed",
                "executions": {"19": _stage19_record()},
                "quality_gate": _quality_pass(gate_set_sha),
            },
            "stage20_downstream": {"status": "pending", "attempts": 0},
            "cards": {"status": "pending", "attempts": 0},
            "export": {"status": "pending", "attempts": 0},
        },
    }


def _provider() -> dict:
    entries = {
        "glass": [{"translation": "стекло", "confidence": 0.95}],
        "light": [{"translation": "свет", "confidence": 0.96}],
    }
    return {
        "schema": unified.PROVIDER_SCHEMA,
        "provider": unified.STAGE20_PROVIDER_POLICY,
        "snapshot": {
            "revision": unified.OFFICIAL_OPUS_REVISION,
            "sha256": unified.OFFICIAL_OPUS_ARCHIVE_SHA256,
            "source_uri": unified.OFFICIAL_OPUS_SOURCE_URI,
            "network_access": False,
            "is_smoke": False,
            "entries": entries,
        },
        "entries_sha256": hashlib.sha256(
            json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "summary": {"sense_count": 2, "entry_count": 2, "candidate_count": 2, "backend_compute_type": "float32"},
        "probe_meta": [],
        "evidence": [],
    }


def _stage20(*, coverage: bool = True) -> dict:
    return {
        "source_policy": "aligned-local-consensus",
        "results": [
            {
                "sense_id": 1,
                "entry_id": 11,
                "selection_revision_id": 101,
                "generation_run_id": 201,
                "coverage_complete": coverage,
                "selected": [{"translation": "стекло", "candidate_id": 301}],
            },
            {
                "sense_id": 2,
                "entry_id": 12,
                "selection_revision_id": 102,
                "generation_run_id": 202,
                "coverage_complete": True,
                "selected": [{"translation": "свет", "candidate_id": 302}],
            },
        ],
    }


def _write_state(tmp_path: Path, database: Path) -> Path:
    path = tmp_path / "product-run.json"
    path.write_text(json.dumps(_state(database)), encoding="utf-8")
    return path


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    root.mkdir()
    (root / "model.bin").write_bytes(b"model-bytes")
    (root / "source.spm").write_bytes(b"source-spm")
    (root / "target.spm").write_bytes(b"target-spm")
    return root


def test_stage20_input_binds_exact_local_model_tree_and_official_release(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path = _write_state(tmp_path, database)
    model = _model(tmp_path)

    first = unified.build_stage20_input_identity(state_path, model_path=model)
    second = unified.build_stage20_input_identity(state_path, model_path=model)
    assert first["fingerprint"] == second["fingerprint"]
    assert first["model"]["archive_sha256"] == unified.OFFICIAL_OPUS_ARCHIVE_SHA256
    assert first["model"]["local_file_count"] == 3
    assert len(first["model"]["local_tree_sha256"]) == 64

    (model / "model.bin").write_bytes(b"mutated")
    changed = unified.build_stage20_input_identity(state_path, model_path=model)
    assert changed["fingerprint"] != first["fingerprint"]


def test_product_stage20_rejects_unpinned_archive_metadata(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path = _write_state(tmp_path, database)
    model = _model(tmp_path)
    with pytest.raises(RuntimeError, match="archive SHA-256"):
        unified.build_stage20_input_identity(state_path, model_path=model, archive_sha256="0" * 64)
    with pytest.raises(RuntimeError, match="revision"):
        unified.build_stage20_input_identity(state_path, model_path=model, revision="other")


def test_unified_stage20_persists_provider_and_stage20_as_hash_verified_artifacts(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"; database.touch()
    state_path = _write_state(tmp_path, database)
    model = _model(tmp_path)
    calls = {"provider": 0, "stage20": 0}

    def provider(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["provider"] += 1
        return _provider()

    def stage20(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["stage20"] += 1
        return _stage20()

    monkeypatch.setattr(unified, "build_opus_lexical_snapshot", provider)
    monkeypatch.setattr(unified, "run_stage20_with_snapshot", stage20)
    core = object()

    first = unified.run_unified_stage20(core, database, state_path, model_path=model)
    second = unified.run_unified_stage20(core, database, state_path, model_path=model)

    assert first["status"] == "stage20_completed"
    assert first["stage20_identity"]["sense_ids"] == [1, 2]
    assert first["cache_hits"] == {"provider": False, "stage20": False}
    assert second["cache_hits"] == {"provider": True, "stage20": True}
    assert calls == {"provider": 1, "stage20": 1}
    assert Path(first["provider_artifact"]["path"]).is_file()
    assert Path(first["stage20_artifact"]["path"]).is_file()
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "stage20_completed_awaiting_arbitration_cefr_pronunciation_examples"


def test_stage20_provider_artifact_mutation_fails_closed(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"; database.touch()
    state_path = _write_state(tmp_path, database)
    model = _model(tmp_path)
    monkeypatch.setattr(unified, "build_opus_lexical_snapshot", lambda *a, **k: _provider())
    monkeypatch.setattr(unified, "run_stage20_with_snapshot", lambda *a, **k: _stage20())
    result = unified.run_unified_stage20(object(), database, state_path, model_path=model)
    provider_path = Path(result["provider_artifact"]["path"])
    provider_path.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="artifact bytes were mutated"):
        unified.run_unified_stage20(object(), database, state_path, model_path=model)


def test_incomplete_stage20_coverage_is_ambiguous_and_not_auto_replayed(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"; database.touch()
    state_path = _write_state(tmp_path, database)
    model = _model(tmp_path)
    calls = {"stage20": 0}
    monkeypatch.setattr(unified, "build_opus_lexical_snapshot", lambda *a, **k: _provider())

    def bad_stage20(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["stage20"] += 1
        return _stage20(coverage=False)

    monkeypatch.setattr(unified, "run_stage20_with_snapshot", bad_stage20)
    with pytest.raises(RuntimeError, match="does not have complete"):
        unified.run_unified_stage20(object(), database, state_path, model_path=model)
    assert calls["stage20"] == 1
    with pytest.raises(RuntimeError, match="manual reconciliation"):
        unified.run_unified_stage20(object(), database, state_path, model_path=model)
    assert calls["stage20"] == 1


def test_stage20_requires_hash_verified_completed_stage19(tmp_path) -> None:
    database = tmp_path / "db.sqlite"; database.touch()
    state_path = _write_state(tmp_path, database)
    model = _model(tmp_path)
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload["steps"]["upstream_execution"]["executions"].pop("19")
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="completed Stage19"):
        unified.build_stage20_input_identity(state_path, model_path=model)


def test_unified_stage20_continues_through_existing_stage23_runner(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"; database.touch()
    state_path = _write_state(tmp_path, database)
    model = _model(tmp_path)
    cefr = tmp_path / "cefr.csv"; cefr.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(unified, "build_opus_lexical_snapshot", lambda *a, **k: _provider())
    monkeypatch.setattr(unified, "run_stage20_with_snapshot", lambda *a, **k: _stage20())
    unified.run_unified_stage20(object(), database, state_path, model_path=model)
    observed = {}

    def downstream(core, db, provider, stage20, *, cefrj_asset, state_path, include_russian_pronunciation_hint):  # type: ignore[no-untyped-def]
        observed["provider_sha"] = provider["entries_sha256"]
        observed["stage20_count"] = len(stage20["results"])
        observed["hint"] = include_russian_pronunciation_hint
        state_path = Path(state_path)
        state_path.write_text(json.dumps({"schema": "fake-downstream", "status": "completed"}), encoding="utf-8")
        return {
            "status": "completed",
            "input_identity": {"fingerprint": "d" * 64},
            "cache_hits": {"stage20_arbitration": False, "cefrj": False, "pronunciation": False, "examples": False},
        }

    monkeypatch.setattr(unified, "resume_product_downstream", downstream)
    result = unified.continue_unified_stage20_through_stage23(
        object(), database, state_path, cefrj_asset=cefr
    )
    assert result["status"] == "completed_through_stage23"
    assert observed["stage20_count"] == 2
    assert observed["hint"] is False
    assert len(result["downstream"]["runner_state_sha256"]) == 64
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "stage23_completed_awaiting_stage24_cards"
