from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from rocketdict.api.client import RocketDictAPI
from rocketdict.api.contracts import (
    API_VERSION,
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
    TRANSPORT,
)
from rocketdict.api.operations import OPERATIONS
from rocketdict.api.registry import REGISTRY_HASH, descriptor_hash, lab_manifest
from rocketdict.database import bootstrap_database
from rocketdict.runtime import OPUS_ARCHIVE_SHA256, OPUS_REVISION, load_opus_asset, opus_status


def test_registry_is_static_identity_plus_dynamic_fail_closed_availability(monkeypatch) -> None:
    first = lab_manifest(probe_runtime=False)
    second = lab_manifest(probe_runtime=True)
    assert first["registry_hash"] == second["registry_hash"] == REGISTRY_HASH
    assert len(REGISTRY_HASH) == 64
    assert first["source_language"] == "en"
    assert first["target_language"] == "ru"
    stage_numbers = [int(row["number"]) for row in first["stages"]]
    assert stage_numbers == [8, 10, 12, 14, 15, 16, 17, 19, 21, 22, 23, 24, 25]
    for manifest in (first, second):
        for stage in manifest["stages"]:
            for implementation in stage["implementations"]:
                assert len(implementation["descriptor_hash"]) == 64
                assert isinstance(implementation["required_inputs"], list)
                assert "availability" in implementation
    # Dependency-light CI has no right to claim a real OPUS runtime without the
    # exact provisioned asset manifest even if libraries happen to be installed.
    monkeypatch.delenv("ROCKETDICT_OPUS_ASSET_DIR", raising=False)
    status = opus_status()
    assert status["available"] is False
    assert status["source_archive_sha256"] == OPUS_ARCHIVE_SHA256
    assert status["revision"] == OPUS_REVISION


def test_known_operation_metadata_exactly_matches_registry_descriptor() -> None:
    expectations = {
        "product.stage8.run": (8, "en-sm", ["document_version_id"]),
        "product.stage10.run": (10, "structural-entity-term-discourse-pronoun-v1", ["nlp_run_id"]),
        "product.stage12.run": (12, "opus-en-ru-ct2", ["context_run_id"]),
        "product.stage14.run": (14, "glossary_refinement-current", ["translation_run_id"]),
        "product.stage16.run": (16, "approve-if-clean-finalization", ["assembly_id"]),
        "product.stage17.run": (17, "deterministic-structural-global", ["translation_revision_id"]),
        "product.stage19.run": (19, "deterministic-context-target-graph", ["extraction_run_id"]),
    }
    for operation, (stage, implementation, required) in expectations.items():
        fn = OPERATIONS[operation]
        assert fn.stage_number == stage
        assert fn.implementation_key == implementation
        assert fn.required_inputs == required
        assert fn.adapter_descriptor_hash == descriptor_hash(stage, implementation)
        assert len(inspect.getsource(fn)) > 0
        contract = fn.rocketdict_execution_contract
        assert contract["schema"] == PUBLIC_EXECUTION_CONTRACT_SCHEMA
        assert contract["transport"] == TRANSPORT
        assert contract["replay_safe"] is True
        assert sorted(
            spec.removeprefix("input:")
            for spec in contract["request"]["params"].values()
            if spec.startswith("input:")
        ) == sorted(required)
        assert "profile:parameters" in contract["request"]["params"].values()


def test_quality_operations_publish_exact_hard_gate_semantics() -> None:
    operations = [
        "product.stage15.numeric-symbol",
        "product.stage15.punctuation",
        "product.stage15.length-ratio",
    ]
    for operation in operations:
        fn = OPERATIONS[operation]
        assert fn.stage_number == 15
        semantics = fn.rocketdict_quality_gate_semantics
        assert semantics == {
            "schema": PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
            "stage_number": 15,
            "hard_gate": True,
            "failure_blocks_downstream": True,
            "pass_condition": {"field": "passed", "equals": True},
        }
        contract = fn.rocketdict_execution_contract
        assert "passed" in contract["result"]["required_fields"]


def test_stage18_public_identity_is_explicit_but_not_misrepresented_as_registry_stage() -> None:
    fn = OPERATIONS["product.stage18.run"]
    assert fn.stage_number == 18
    assert fn.stage_key == "lexical_extraction"
    assert fn.implementation_key == "workbench-aligned-content-pos-v4"
    assert fn.required_inputs == ["alignment_run_id"]
    assert len(fn.adapter_descriptor_hash) == 64
    assert all(int(stage["number"]) != 18 for stage in lab_manifest()["stages"])


def test_api_client_project_dashboard_and_unknown_call(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    api = RocketDictAPI(db)
    assert api.project()["schema_version"] == 1
    dashboard = api.lab_dashboard(probe_runtime=True)
    assert dashboard["registry_hash"] == REGISTRY_HASH
    with pytest.raises(KeyError):
        api.call("does.not.exist")


def test_opus_manifest_rejects_wrong_archive_identity(tmp_path: Path, monkeypatch) -> None:
    asset = tmp_path / "asset"
    model = asset / "ct2"
    model.mkdir(parents=True)
    (model / "model.bin").write_bytes(b"model")
    (asset / "src.spm").write_bytes(b"spm")
    (asset / "tgt.spm").write_bytes(b"spm")
    (asset / "rocketdict-opus-asset.json").write_text(
        json.dumps(
            {
                "schema": "rocketdict-opus-asset/1",
                "revision": OPUS_REVISION,
                "source_archive_sha256": "0" * 64,
                "ct2_model_dir": "ct2",
                "source_sentencepiece": "src.spm",
                "target_sentencepiece": "tgt.spm",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ROCKETDICT_OPUS_ASSET_DIR", str(asset))
    with pytest.raises(RuntimeError, match="accepted official archive"):
        load_opus_asset()
