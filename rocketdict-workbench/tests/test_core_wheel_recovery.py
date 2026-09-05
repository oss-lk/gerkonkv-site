from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from rocketdict_workbench.core_scan_artifacts import scan_core_artifacts
from rocketdict_workbench.core_wheel_recovery import (
    build_wheel_recovery_plan,
    inspect_wheel_candidate,
)


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _target() -> Path:
    return _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"


def _wheel(path: Path, *, version: str = "0.30.32") -> Path:
    package_root = (_target() / "src/rocketdict/__init__.py").read_bytes()
    package_root = package_root.replace(b"0.30.40", version.encode("ascii"))
    files = {
        "rocketdict/__init__.py": package_root,
        "rocketdict/nlp/registry.py": (
            _target() / "src/rocketdict/nlp/registry.py"
        ).read_bytes(),
        "rocketdict/api/__init__.py": b"",
        "rocketdict/api/contracts.py": b'API_VERSION = "wheel-test/1"\n',
        "rocketdict/api/client.py": b"class RocketDictAPI:\n    pass\n",
        "rocketdict/api/cli.py": b"",
        "rocketdict/database.py": b"def bootstrap_database(path):\n    return None\n",
        "rocketdict/importing/__init__.py": b"",
        "rocketdict/importing/cli.py": b"",
        "rocketdict/interpretation/__init__.py": b"",
        "rocketdict/interpretation/cli.py": b"",
        f"rocketdict-{version}.dist-info/METADATA": (
            f"Metadata-Version: 2.1\nName: rocketdict\nVersion: {version}\n"
        ).encode("utf-8"),
        f"rocketdict-{version}.dist-info/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, raw in files.items():
            zf.writestr(name, raw)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_wheel_candidate_exposes_packaged_core_without_execution(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.32-py3-none-any.whl")

    report = inspect_wheel_candidate(wheel)

    assert report["schema"] == "rocketdict-workbench-core-recovery-candidate/1"
    assert report["status"] == "base_candidate_requires_compatibility_proof"
    assert report["promotion_allowed"] is False
    assert report["candidate"]["kind"] == "wheel"
    assert report["candidate"]["artifact_format"] == "python-wheel"
    assert report["candidate"]["source_layout"] == "direct"
    assert report["observed"]["rocketdict_version"] == "0.30.32"
    assert report["observed"]["missing_required_modules"] == []
    assert report["runtime_probe"]["attempted"] is False
    assert report["runtime_probe"]["ok"] is False
    assert "wheel_not_installed_or_executed_by_recovery_verifier" in report[
        "promotion_blockers"
    ]


def test_wheel_builds_normal_fail_closed_base_to_03040_plan(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.32-py3-none-any.whl")

    plan = build_wheel_recovery_plan(wheel)

    assert plan["schema"] == "rocketdict-workbench-core-recovery-plan/1"
    assert plan["promotion_allowed"] is False
    assert plan["writes_source"] is False
    assert plan["candidate"]["source"]["kind"] == "wheel"
    assert plan["candidate"]["rocketdict_version"] == "0.30.32"
    assert plan["candidate"]["structural_complete_for_workbench_bridge"] is True
    assert plan["candidate"]["runtime_probe_ok"] is False
    assert plan["target"]["overlay_member_count"] == 19
    assert plan["target"]["exact_target_available_count"] == 2
    assert plan["target"]["exact_target_missing_count"] == 17
    assert plan["target"]["public_api_exact_bytes_recovered"] is False
    assert "missing_exact_overlay_targets:17" in plan["blockers"]
    assert "wheel_requires_isolated_installation_before_runtime_probe" in plan["blockers"]
    assert "exact_0.30.40_public_api_bytes_not_recovered" in plan["blockers"]


def test_unified_scan_discovers_wheel_and_exact_sha_catalog_identity(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.32-py3-none-any.whl")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "schema": "rocketdict-historical-checkpoint-catalog/1",
                "promotion_allowed": False,
                "entries": [
                    {
                        "id": "test-wheel",
                        "version": "0.30.32",
                        "stage": "test",
                        "archive_name_patterns": [],
                        "archive_sha256": None,
                        "archive_bytes": None,
                        "wheel_name_patterns": ["rocketdict-0.30.32-py3-none-any.whl"],
                        "wheel_sha256": _sha256(wheel),
                        "wheel_bytes": wheel.stat().st_size,
                        "candidate_role": "test",
                        "evidence_level": "exact_test_identity",
                        "promotion_allowed": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = scan_core_artifacts(wheel, checkpoint_catalog=catalog)

    assert report["schema"] == "rocketdict-workbench-core-recovery-scan/3"
    assert report["promotion_allowed"] is False
    assert report["supported_artifact_kinds"] == ["directory", "zip", "wheel"]
    assert report["discovered_candidate_count"] == 1
    assert report["discovered_wheel_count"] == 1
    assert report["analyzed_candidate_count"] == 1
    assert report["error_count"] == 0
    row = report["candidates"][0]
    assert row["kind"] == "wheel"
    assert row["historical_checkpoint_name_match"] is True
    assert row["historical_checkpoint_exact_identity_match"] is True
    match = row["historical_checkpoint_matches"][0]
    assert match["artifact_kind"] == "wheel"
    assert match["catalog_id"] == "test-wheel"
    assert match["exact_identity_match"] is True
    assert match["promotion_allowed"] is False


def test_wheel_name_match_with_wrong_sha_is_not_exact_identity(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.32-py3-none-any.whl")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "schema": "rocketdict-historical-checkpoint-catalog/1",
                "promotion_allowed": False,
                "entries": [
                    {
                        "id": "test-wheel",
                        "version": "0.30.32",
                        "stage": "test",
                        "archive_name_patterns": [],
                        "archive_sha256": None,
                        "archive_bytes": None,
                        "wheel_name_patterns": ["rocketdict-0.30.32-py3-none-any.whl"],
                        "wheel_sha256": "0" * 64,
                        "wheel_bytes": None,
                        "candidate_role": "test",
                        "evidence_level": "test",
                        "promotion_allowed": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    row = scan_core_artifacts(wheel, checkpoint_catalog=catalog)["candidates"][0]
    assert row["historical_checkpoint_name_match"] is True
    assert row["historical_checkpoint_exact_identity_match"] is False
    assert row["historical_checkpoint_matches"][0]["exact_identity_mismatch"] is True


def test_corrupt_wheel_is_isolated_from_valid_directory_candidate(tmp_path: Path) -> None:
    wheel = tmp_path / "broken.whl"
    wheel.write_bytes(b"not a wheel")

    # A directory-only scan path would be handled by the existing scanner; here
    # we assert that a bad single wheel produces one candidate error rather than
    # an exception that escapes the batch report.
    report = scan_core_artifacts(wheel)
    assert report["discovered_candidate_count"] == 1
    assert report["discovered_wheel_count"] == 1
    assert report["analyzed_candidate_count"] == 0
    assert report["error_count"] == 1
    assert report["errors"][0]["path"] == str(wheel.resolve())
    assert report["errors"][0]["kind"] == "wheel"
