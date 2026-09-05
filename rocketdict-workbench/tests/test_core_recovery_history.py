from __future__ import annotations

import json
from pathlib import Path

from rocketdict_workbench.core_recovery import inspect_core_candidate


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def test_historical_overlay_contract_cannot_be_misread_as_full_core() -> None:
    repo = _repo()
    path = repo / "rocketdict" / "recovered" / "stage8-0.30.40" / "core-recovery-history.json"
    history = json.loads(path.read_text(encoding="utf-8"))

    assert history["schema"] == "rocketdict-stage8-core-recovery-history/1"
    assert history["promotion_allowed"] is False
    assert history["active_product_core_recovered"] is False

    contract = history["historical_materializer_contract"]
    assert contract["overlay_parts"] == 8
    assert contract["research_vault_parts"] == 11
    assert contract["expected_overlay_member_count"] == 19
    assert len(contract["expected_overlay_members"]) == 19
    assert contract["contains_rocketdict_api_package"] is False
    assert not any(
        member.startswith("src/rocketdict/api/")
        for member in contract["expected_overlay_members"]
    )

    health = history["historical_handoff_chain"]["health_commit"]["observation"]
    assert health["present_overlay_parts"] == [
        "rocketdict/payload/stage8-overlay/part-000.b64"
    ]
    assert health["missing_overlay_parts"] == 7
    assert health["missing_research_vault_parts"] == 11
    assert health["fresh_clone_materialization_possible"] is False


def test_actions_api_recovery_boundary_records_no_direct_api_source_hit() -> None:
    history = json.loads(
        (
            _repo()
            / "rocketdict"
            / "recovered"
            / "stage8-0.30.40"
            / "core-recovery-history.json"
        ).read_text(encoding="utf-8")
    )
    scan = history["actions_public_api_recovery_scan"]

    assert scan["scanner_schema"] == "rocketdict-stage8-api-artifact-recovery/3"
    assert scan["workflow_run_id"] == 33962396201
    assert scan["result_artifact_id"] == 9968352199
    assert scan["inventory_count"] == 120
    assert scan["downloaded_count"] == 96
    assert scan["expired_count"] == 17
    assert scan["over_size_limit_count"] == 7
    assert scan["direct_rocketdict_api_python_path_hits"] == 0
    assert scan["truncated_next_member"] == "src/rocketdict/lab/stage12_pilot.py"
    assert scan["truncated_member_errors"] == 6

    classified = scan["oversized_artifacts"]
    assert len(classified["stanza_model_bundles"]) == 4
    assert len(classified["offline_opus_runtime_bundles"]) == 3
    assert set(classified["stanza_model_bundles"]).isdisjoint(
        classified["offline_opus_runtime_bundles"]
    )


def test_documented_0308_archive_is_only_a_base_recovery_lead() -> None:
    history = json.loads(
        (
            _repo()
            / "rocketdict"
            / "recovered"
            / "stage8-0.30.40"
            / "core-recovery-history.json"
        ).read_text(encoding="utf-8")
    )
    lead = history["documented_historical_full_checkpoint_candidate"]

    assert lead["version"] == "0.30.8"
    assert lead["archive_name"] == "RocketDict_CURRENT_COMPACT.zip"
    assert lead["archive_bytes"] == 125875993
    assert lead["archive_sha256"] == "f948a9b59e4deb7b00a606fdb88973dd9a435c087c132f32f03d2d0c863b51ac"
    assert lead["manifest_files"] == 666
    assert lead["promotion_allowed"] is False
    assert "not recovered" in lead["current_byte_status"]


def test_actual_recovered_03040_namespace_is_explicitly_incomplete() -> None:
    root = _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"
    report = inspect_core_candidate(root, probe_runtime=False)

    assert report["status"] == "incomplete_candidate"
    assert report["promotion_allowed"] is False
    assert report["observed"]["rocketdict_version"] == "0.30.40"
    assert report["observed"]["exact_recovered_mismatch_paths"] == []
    assert "rocketdict.api.contracts" in report["observed"]["missing_required_modules"]
    assert "rocketdict.api.client" in report["observed"]["missing_required_modules"]
    assert "rocketdict.api.cli" in report["observed"]["missing_required_modules"]
