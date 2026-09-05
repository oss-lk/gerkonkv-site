from __future__ import annotations

import json
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _load(name: str) -> dict:
    return json.loads(
        (_repo() / "rocketdict" / "recovered" / name).read_text(encoding="utf-8")
    )


def test_late_stage6_exact_artifact_identity_record_is_fail_closed() -> None:
    report = _load("late-stage6-artifact-identities-2026-09-05.json")
    assert report["schema"] == "rocketdict-late-stage6-artifact-identities/1"
    assert report["promotion_allowed"] is False
    assert report["bytes_currently_recovered"] is False
    rows = {row["version"]: row for row in report["entries"]}
    assert list(rows) == ["0.30.29", "0.30.30", "0.30.31", "0.30.32", "0.30.33", "0.30.34"]
    assert all(row["promotion_allowed"] is False for row in rows.values())

    assert rows["0.30.29"]["archive"] == {
        "name": "RocketDict_0.30.29_LAB_STAGE6T_LEASE_PREFLIGHT_LIVENESS_COMPLETE.zip",
        "bytes": 135746615,
        "sha256": "199e44f5ef1584565d2c57d771e5723423f274131f686024c541754802a09fa3",
        "identity": "exact",
    }
    assert rows["0.30.33"]["archive"]["sha256"] == "405d4339fc12b8046da4f5cb73c799b2d5c957a9b53dffdf8e2ed9a79cbeb152"
    assert rows["0.30.33"]["wheel"]["sha256"] == "4c64deb9cc48b68be1408ad52b4458b843453f89f60c84a72c688b5cb3f042c1"
    assert rows["0.30.34"]["archive"] is None
    assert rows["0.30.34"]["release_zip_packaging_completed"] is False
    assert rows["0.30.34"]["wheel"] == {
        "name": "rocketdict-0.30.34-py3-none-any.whl",
        "bytes": None,
        "sha256": "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a",
        "identity": "exact_sha256",
    }
    assert len(rows["0.30.34"]["wheel"]["sha256"]) == 64


def test_checkpoint_catalog_ranks_03034_wheel_without_inventing_release_zip() -> None:
    catalog = _load("checkpoint-catalog.json")
    rows = {row["version"]: row for row in catalog["entries"] if row.get("version")}
    x = rows["0.30.33"]
    y = rows["0.30.34"]

    assert x["archive_name_patterns"] == [
        "RocketDict_0.30.33_LAB_STAGE6X_COMPACTION_HARD_CRASH_RECOVERY_COMPLETE.zip"
    ]
    assert x["archive_bytes"] == 135522258
    assert x["archive_sha256"] == "405d4339fc12b8046da4f5cb73c799b2d5c957a9b53dffdf8e2ed9a79cbeb152"
    assert x["wheel_sha256"] == "4c64deb9cc48b68be1408ad52b4458b843453f89f60c84a72c688b5cb3f042c1"

    assert y["archive_name_patterns"] == []
    assert y["archive_sha256"] is None
    assert y["archive_bytes"] is None
    assert y["wheel_name_patterns"] == ["rocketdict-0.30.34-py3-none-any.whl"]
    assert y["wheel_sha256"] == "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a"
    assert len(y["wheel_sha256"]) == 64
    assert y["candidate_role"] == "highest_known_late_packaged_core_candidate"
    assert y["promotion_allowed"] is False


def test_recovery_priority_is_monotone_toward_latest_packaged_core() -> None:
    report = _load("late-stage6-artifact-identities-2026-09-05.json")
    rows = {row["version"]: row for row in report["entries"]}
    assert [rows[v]["candidate_priority"] for v in ["0.30.34", "0.30.33", "0.30.32", "0.30.31", "0.30.30", "0.30.29"]] == [1, 2, 3, 4, 5, 6]
