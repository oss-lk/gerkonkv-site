from __future__ import annotations

import json
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def test_core_recovery_search_exhaustion_is_machine_readable_and_fail_closed() -> None:
    path = _repo() / "rocketdict" / "recovered" / "search-exhaustion-2026-09-05.json"
    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["schema"] == "rocketdict-core-recovery-search-exhaustion/1"
    assert report["promotion_allowed"] is False
    assert report["complete_historical_core_recovered"] is False

    summary = report["workspace_inventory_summary"]
    assert summary == {
        "zip_count": 10,
        "zip_with_any_rocketdict_package_init": 1,
        "zip_with_all_required_public_api_modules": 0,
        "zip_with_rocketdict_wheel": 0,
        "zip_with_nested_rocketdict_checkpoint_zip": 0,
        "complete_core_candidate_found": False,
    }

    rows = report["ephemeral_recovery_workspace_zip_inventory"]
    assert len(rows) == 10
    assert len({row["name"] for row in rows}) == 10
    assert all(len(row["sha256"]) == 64 for row in rows)
    assert all(row["rocketdict_api_required_hits"] == 0 for row in rows)
    assert all(row["rocketdict_wheel_hits"] == 0 for row in rows)
    assert all(row["nested_rocketdict_zip_hits"] == 0 for row in rows)

    init_rows = [row for row in rows if row["rocketdict_package_init_hits"]]
    assert len(init_rows) == 1
    assert init_rows[0]["name"] == "stage8-overlay-prefix.zip"
    assert init_rows[0]["classification"] == "known_truncated_0.30.40_overlay_prefix_evidence_only"
    assert init_rows[0]["rocketdict_package_init_paths"] == [
        "members/src/rocketdict/__init__.py"
    ]


def test_git_recovery_search_records_closed_storage_paths_without_claiming_core() -> None:
    report = json.loads(
        (_repo() / "rocketdict" / "recovered" / "search-exhaustion-2026-09-05.json").read_text(
            encoding="utf-8"
        )
    )
    git = report["git_history"]

    assert git["parentless_upload_commit"]["sha"] == "442e09dbb2e0b48147837b2bc78b6454ce6dca35"
    assert git["parentless_upload_commit"]["result"] == "website_only_no_rocketdict_source_tree"
    assert {row["ref"] for row in git["deleted_refs_observed"]} == {
        "refs/heads/rocketdict-opus-gate-public",
        "refs/heads/rocketdict-pr-actions-run",
    }
    assert all(row["reachable_commits"] == 0 for row in git["likely_api_path_history_checks"])
    assert all(row["release_count"] == 0 for row in git["release_checks"])
    assert report["file_library"]["full_checkpoint_zip_bytes_recovered"] is False
    assert report["file_library"]["api_source_module_bytes_recovered"] is False
