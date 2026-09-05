from __future__ import annotations

import json
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _load() -> dict:
    return json.loads(
        (_repo() / "rocketdict" / "recovered" / "search-exhaustion-2026-09-05.json").read_text(
            encoding="utf-8"
        )
    )


def test_core_recovery_search_exhaustion_is_machine_readable_and_fail_closed() -> None:
    report = _load()
    assert report["schema"] == "rocketdict-core-recovery-search-exhaustion/3"
    assert report["promotion_allowed"] is False
    assert report["complete_historical_core_recovered"] is False

    workspace = report["ephemeral_recovery_workspace"]
    assert workspace["top_level_zip_or_wheel_artifacts"] == 10
    assert workspace["top_level_wheels"] == 0
    assert workspace["exact_03034_zip_sha_match_count"] == 0
    assert workspace["exact_03034_wheel_sha_match_count"] == 0
    assert workspace["zip_with_any_rocketdict_package_init"] == 1
    assert workspace["zip_with_all_required_public_api_modules"] == 0
    assert workspace["zip_with_rocketdict_wheel"] == 0
    assert workspace["zip_with_nested_rocketdict_checkpoint_zip"] == 0
    assert workspace["complete_core_candidate_found"] is False
    assert workspace["only_package_root_hit"] == {
        "name": "stage8-overlay-prefix.zip",
        "sha256": "d56876cc23cc281ab9f9da36dedcff9536aca766ef7da7ad414addd57a2cf8d8",
        "classification": "known_truncated_0.30.40_overlay_prefix_evidence_only",
    }
    assert workspace["offline_opus_runtime"]["rocketdict_package_present"] is False
    assert workspace["offline_opus_runtime"]["rocketdict_api_present"] is False


def test_exact_stage6y_search_surfaces_are_recorded_without_claiming_bytes() -> None:
    report = _load()
    library = report["file_library"]["exact_stage6y_zip_search"]
    assert library["name"] == "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip"
    assert library["sha256"] == "3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387"
    assert library["date_navigation_checked"] == "2026-08-26"
    assert library["binary_object_recovered"] is False
    assert report["file_library"]["full_checkpoint_zip_bytes_recovered"] is False
    assert report["file_library"]["api_source_module_bytes_recovered"] is False

    assert report["google_drive"]["exact_artifact_result_count"] == 0
    assert report["google_drive"]["general_rocketdict_search_result_count"] == 0
    assert report["public_exact_search"]["exact_artifact_result_count"] == 0

    preferred = report["preferred_external_recovery_identity"]
    assert preferred["artifact_kind"] == "full_checkpoint_zip"
    assert preferred["name"] == "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip"
    assert preferred["sha256"] == "3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387"
    assert preferred["historical_bytes"] is None
    assert preferred["bytes_currently_recovered"] is False
    assert preferred["alternate_wheel"]["sha256"] == "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a"


def test_git_and_actions_recovery_searches_are_closed_without_claiming_core() -> None:
    report = _load()
    git = report["git_history"]
    assert git["parentless_upload_commit"]["sha"] == "442e09dbb2e0b48147837b2bc78b6454ce6dca35"
    assert git["parentless_upload_commit"]["result"] == "website_only_no_rocketdict_source_tree"
    assert {row["ref"] for row in git["deleted_refs_observed"]} == {
        "refs/heads/rocketdict-opus-gate-public",
        "refs/heads/rocketdict-pr-actions-run",
    }
    assert all(row["reachable_commits"] == 0 for row in git["likely_api_path_history_checks"])
    assert all(row["release_count"] == 0 for row in git["release_checks"])
    assert "sandbox/checkpoint artifacts" in git["stage6t_to_stage6y_commit_window"]["conclusion"]

    actions = report["github_actions_artifacts"]
    assert all(
        row["artifact_count"] == 0
        for row in actions["spacy_project_vault"]["rocketdict_real_opus_runs"]
    )
    assert actions["gerkonkv_site"]["workbench_upload_artifact_step_present"] is False
    assert actions["gerkonkv_site"]["deleted_public_opus_workflow"]["core_or_wheel_in_uploaded_paths"] is False


def test_exhaustion_record_explicitly_supersedes_the_old_wheel_first_claim() -> None:
    report = _load()
    assert "incorrectly treated the 0.30.34 wheel" in report["correction"]
    assert "full Stage6Y ZIP was created" in report["correction"]
    assert any("Stage6Y" in item for item in report["do_not_repeat_without_new_evidence"])
    assert any("Google Drive" in item for item in report["do_not_repeat_without_new_evidence"])
