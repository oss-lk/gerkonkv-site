from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.cli import parser
import rocketdict_workbench.product_run_state as run_state
from rocketdict_workbench.product_preflight import PREFLIGHT_SCHEMA


class _Core:
    def __init__(self, *, version: str = "0.30.40", api_version: str = "1") -> None:
        self.version = version
        self.api_version = api_version
        self.calls = 0

    def _run(self, args, timeout=120):  # type: ignore[no-untyped-def]
        self.calls += 1
        payload = {
            "schema": run_state.API_PROBE_SCHEMA,
            "status": "observed",
            "database": {"path": args[-1], "exists": True},
            "core": {"rocketdict_version": self.version, "api_version": self.api_version},
            "api_modules": [{"module": "rocketdict.api.cli", "imported": True, "source_sha256": "b" * 64}],
            "parser_commands": ["call", "experiments run"],
            "callable_mapping_keys": ["lab.config.validate"],
            "operation_candidates": ["call", "experiments run", "lab.config.validate"],
            "fingerprint": "a" * 64,
        }
        return SimpleNamespace(stdout=json.dumps(payload))

    @staticmethod
    def _parse_json(text: str, *, context: str):  # type: ignore[no-untyped-def]
        return json.loads(text)


def _preflight(*, source_sha: str = "1" * 64, registry_hash: str = "registry-1") -> dict:
    identity = {
        "source": {
            "sha256": source_sha,
            "byte_size": 100,
            "suffix": ".txt",
            "copied_path": "uploads/source.txt",
            "source_name": "source.txt",
            "import_event_id": 7,
            "document_version_id": 11,
            "selected_format": "txt",
            "import_identity_sha256": "2" * 64,
            "interpretation_identity_sha256": "3" * 64,
        },
        "source_kind": "text",
        "core": {"python": "python", "rocketdict_version": "0.30.40", "api_version": "1"},
        "registry_hash": registry_hash,
        "required_core_stages": {},
        "quality_gates": [],
        "profile_sha256": "4" * 64,
        "fingerprint": "5" * 64,
    }
    return {
        "schema": PREFLIGHT_SCHEMA,
        "status": "ready",
        "identity": identity,
        "profile": {"schema": "profile"},
        "policy_warnings": [],
        "network_required_during_processing": False,
        "fake_or_identity_mt_allowed": False,
    }


def test_initialize_product_run_binds_preflight_root_and_caches_probe(tmp_path) -> None:
    core = _Core()
    state_path = tmp_path / "product-run.json"
    database = tmp_path / "rocketdict.sqlite"
    database.write_bytes(b"db")

    first = run_state.initialize_product_run(core, database, _preflight(), state_path=state_path)
    second = run_state.initialize_product_run(core, database, _preflight(), state_path=state_path)

    assert first["schema"] == run_state.RUN_STATE_SCHEMA
    assert first["status"] == "awaiting_upstream_binding"
    assert first["root_identity"]["preflight_fingerprint"] == "5" * 64
    assert first["root_identity"]["document_version_id"] == 11
    assert first["operation_candidates"] == ["call", "experiments run", "lab.config.validate"]
    assert first["upstream_execution"]["status"] == "pending"
    assert first["upstream_execution"]["blocked_reason"] == "no_verified_stage8_19_operation_binding"
    assert first["probe_cache_hit"] is False
    assert second["probe_cache_hit"] is True
    assert core.calls == 1

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["steps"]["preflight"]["status"] == "completed"
    assert persisted["steps"]["upstream_contract_probe"]["status"] == "completed"
    assert persisted["steps"]["upstream_execution"]["status"] == "pending"


def test_product_run_rejects_different_preflight_root(tmp_path) -> None:
    core = _Core()
    state_path = tmp_path / "product-run.json"
    database = tmp_path / "rocketdict.sqlite"
    database.write_bytes(b"db")
    run_state.initialize_product_run(core, database, _preflight(), state_path=state_path)

    changed = _preflight(source_sha="9" * 64)
    changed["identity"]["fingerprint"] = "8" * 64
    with pytest.raises(RuntimeError, match="different immutable preflight inputs"):
        run_state.initialize_product_run(core, database, changed, state_path=state_path)


def test_product_run_probe_fails_closed_on_core_version_drift(tmp_path) -> None:
    core = _Core(version="0.30.41")
    state_path = tmp_path / "product-run.json"
    database = tmp_path / "rocketdict.sqlite"
    database.write_bytes(b"db")

    with pytest.raises(RuntimeError, match="core version drift"):
        run_state.initialize_product_run(core, database, _preflight(), state_path=state_path)

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "failed"
    assert persisted["steps"]["upstream_contract_probe"]["status"] == "failed"


def test_product_run_requires_durable_source_revision_identity(tmp_path) -> None:
    payload = _preflight()
    del payload["identity"]["source"]["document_version_id"]
    with pytest.raises(RuntimeError, match="document_version_id"):
        run_state.initialize_product_run(_Core(), tmp_path / "db.sqlite", payload, state_path=tmp_path / "state.json")


def test_completed_probe_evidence_mutation_is_detected(tmp_path) -> None:
    core = _Core()
    state_path = tmp_path / "product-run.json"
    database = tmp_path / "rocketdict.sqlite"
    database.write_bytes(b"db")
    run_state.initialize_product_run(core, database, _preflight(), state_path=state_path)

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    persisted["steps"]["upstream_contract_probe"]["result"]["operation_candidates"].append("invented.operation")
    state_path.write_text(json.dumps(persisted), encoding="utf-8")

    with pytest.raises(RuntimeError, match="evidence was mutated"):
        run_state.initialize_product_run(core, database, _preflight(), state_path=state_path)


def test_product_run_init_cli_exposes_root_identity_controls() -> None:
    args = parser().parse_args([
        "product-run-init",
        "/tmp/project",
        "--source-sha256",
        "a" * 64,
        "--source-kind",
        "text",
        "--state",
        "/tmp/product-run.json",
    ])
    assert args.command == "product-run-init"
    assert args.source_sha256 == "a" * 64
    assert args.source_kind == "text"
    assert args.state == Path("/tmp/product-run.json")
