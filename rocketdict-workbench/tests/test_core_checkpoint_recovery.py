from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import tomllib
import zipfile

import pytest

from rocketdict_workbench.core_checkpoint_recovery import inspect_full_checkpoint
from rocketdict_workbench.core_recovery import RecoveryCandidateError
from rocketdict_workbench.core_scan_pipeline import scan_recovery_pipeline


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _target() -> Path:
    return _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"


def _digest(raw: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode("ascii")


def _package(version: str = "0.30.34") -> dict[str, bytes]:
    init = (_target() / "src/rocketdict/__init__.py").read_bytes()
    init = init.replace(b"0.30.40", version.encode("ascii"))
    return {
        "rocketdict/__init__.py": init,
        "rocketdict/nlp/__init__.py": b"",
        "rocketdict/nlp/registry.py": (_target() / "src/rocketdict/nlp/registry.py").read_bytes(),
        "rocketdict/api/__init__.py": b"",
        "rocketdict/api/contracts.py": b'API_VERSION = "checkpoint-test/1"\n',
        "rocketdict/api/client.py": b"class RocketDictAPI:\n    pass\n",
        "rocketdict/api/cli.py": b"",
        "rocketdict/database.py": b"def bootstrap_database(path):\n    return None\n",
        "rocketdict/importing/__init__.py": b"",
        "rocketdict/importing/cli.py": b"",
        "rocketdict/interpretation/__init__.py": b"",
        "rocketdict/interpretation/cli.py": b"",
        "rocketdict/data/sample.txt": b"package-data\n",
    }


def _wheel(package: dict[str, bytes], *, version: str = "0.30.34") -> bytes:
    files = dict(package)
    metadata = (
        "Metadata-Version: 2.1\n"
        "Name: rocketdict\n"
        f"Version: {version}\n"
        "Requires-Python: >=3.11\n"
    ).encode("utf-8")
    wheel_meta = (
        "Wheel-Version: 1.0\n"
        "Generator: checkpoint-test\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    ).encode("utf-8")
    files[f"rocketdict-{version}.dist-info/METADATA"] = metadata
    files[f"rocketdict-{version}.dist-info/WHEEL"] = wheel_meta
    record_name = f"rocketdict-{version}.dist-info/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for name, raw in sorted(files.items()):
        writer.writerow([name, _digest(raw), str(len(raw))])
    writer.writerow([record_name, "", ""])
    files[record_name] = output.getvalue().encode("utf-8")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, raw in files.items():
            zf.writestr(name, raw)
    return buffer.getvalue()


def _checkpoint(
    path: Path,
    *,
    package: dict[str, bytes] | None = None,
    wheel_package: dict[str, bytes] | None = None,
    unsafe_member: bool = False,
) -> Path:
    package = package or _package()
    wheel_package = wheel_package or package
    nested_wheel = _wheel(wheel_package)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, raw in package.items():
            zf.writestr("checkpoint/src/" + name, raw)
        zf.writestr(
            "checkpoint/dist/rocketdict-0.30.34-py3-none-any.whl",
            nested_wheel,
        )
        zf.writestr("checkpoint/README.md", "# Stage6Y checkpoint\n")
        zf.writestr("checkpoint/STAGE6Y_REPORT_RU.md", "301 packaged runtime files matched source byte-for-byte\n")
        zf.writestr("checkpoint/MANIFEST.json", '{"version":"0.30.34"}\n')
        if unsafe_member:
            zf.writestr("../escape.txt", "unsafe")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _nested_wheel_bytes(checkpoint: Path) -> bytes:
    with zipfile.ZipFile(checkpoint) as zf:
        return zf.read("checkpoint/dist/rocketdict-0.30.34-py3-none-any.whl")


def _catalog(
    path: Path,
    checkpoint: Path,
    *,
    expected_sha: str | None = None,
    expected_wheel_sha: str | None = None,
) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "rocketdict-historical-checkpoint-catalog/1",
                "promotion_allowed": False,
                "entries": [
                    {
                        "id": "stage6y-test",
                        "version": "0.30.34",
                        "stage": "LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE",
                        "archive_name_patterns": [checkpoint.name],
                        "archive_sha256": expected_sha or _sha(checkpoint),
                        "archive_bytes": None,
                        "wheel_name_patterns": ["rocketdict-0.30.34-py3-none-any.whl"],
                        "wheel_sha256": expected_wheel_sha,
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
    return path


def test_exact_full_checkpoint_proves_source_nested_wheel_api_parity_and_catalog_binding(tmp_path: Path) -> None:
    checkpoint = _checkpoint(
        tmp_path / "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip"
    )
    nested = _nested_wheel_bytes(checkpoint)
    catalog = _catalog(
        tmp_path / "catalog.json",
        checkpoint,
        expected_wheel_sha=hashlib.sha256(nested).hexdigest(),
    )

    report = inspect_full_checkpoint(checkpoint, checkpoint_catalog=catalog)

    assert report["schema"] == "rocketdict-workbench-full-checkpoint-recovery/2"
    assert report["status"] == "exact_historical_checkpoint_candidate"
    assert report["promotion_allowed"] is False
    assert report["product_execution_allowed"] is False
    assert report["checkpoint"]["sha256"] == _sha(checkpoint)
    assert report["checkpoint"]["bytes"] == checkpoint.stat().st_size
    assert report["checkpoint"]["zip_crc_ok"] is True
    assert report["historical_checkpoint_exact_identity_match"] is True
    assert report["source_root_unique"] is True
    assert report["source_roots"] == [{"prefix": "checkpoint", "layout": "src"}]
    assert report["source"]["version"] == "0.30.34"
    assert report["source"]["package_file_count"] == len(_package())
    assert report["source"]["api_complete"] is True

    source_api = report["source"]["api_inventory"]
    assert all(row["present"] for row in source_api.values())
    assert source_api["src/rocketdict/api/contracts.py"]["sha256"] == hashlib.sha256(
        b'API_VERSION = "checkpoint-test/1"\n'
    ).hexdigest()

    assert report["nested_rocketdict_wheel_count"] == 1
    assert report["nested_rocketdict_wheel_integrity_ok_count"] == 1
    assert report["nested_rocketdict_wheel_catalog_exact_match_count"] == 1
    assert report["nested_rocketdict_wheel_catalog_exact_mismatch_count"] == 0
    assert report["source_wheel_parity_complete_count"] == 1
    wheel = report["nested_rocketdict_wheels"][0]
    assert wheel["ok"] is True
    assert wheel["metadata"]["name"] == "rocketdict"
    assert wheel["metadata"]["version"] == "0.30.34"
    assert wheel["record"]["verified"] is True
    assert wheel["historical_catalog_name_match"] is True
    assert wheel["historical_catalog_exact_identity_match"] is True
    assert wheel["historical_catalog_exact_identity_mismatch"] is False
    wheel_match = wheel["historical_catalog_matches"][0]
    assert wheel_match["sha256_match"] is True
    assert wheel_match["size_constraint_available"] is False
    assert wheel_match["exact_identity_match"] is True
    assert wheel["source_parity"]["complete"] is True
    assert wheel["source_parity"]["source_file_count"] == len(_package())
    assert wheel["source_parity"]["wheel_file_count"] == len(_package())
    assert wheel["source_parity"]["content_mismatch_count"] == 0
    assert wheel["api_complete"] is True
    assert all(row["present"] for row in wheel["api_inventory"].values())

    evidence_paths = {row["path"] for row in report["evidence_inventory"]}
    assert "checkpoint/README.md" in evidence_paths
    assert "checkpoint/STAGE6Y_REPORT_RU.md" in evidence_paths
    assert "checkpoint/MANIFEST.json" in evidence_paths

    plan = report["compatibility_plan"]
    assert plan is not None
    assert plan["promotion_allowed"] is False
    assert plan["candidate"]["rocketdict_version"] == "0.30.34"
    assert plan["target"]["overlay_member_count"] == 19
    assert plan["target"]["exact_target_available_count"] == 2
    assert plan["target"]["exact_target_missing_count"] == 17
    assert "missing_exact_overlay_targets:17" in plan["blockers"]
    assert report["blockers"] == []
    assert len(report["identity"]["fingerprint"]) == 64


def test_full_checkpoint_detects_source_wheel_content_drift(tmp_path: Path) -> None:
    source = _package()
    wheel_package = dict(source)
    wheel_package["rocketdict/api/client.py"] = b"class RocketDictAPI:\n    changed = True\n"
    checkpoint = _checkpoint(
        tmp_path / "checkpoint.zip",
        package=source,
        wheel_package=wheel_package,
    )

    report = inspect_full_checkpoint(checkpoint)
    parity = report["nested_rocketdict_wheels"][0]["source_parity"]
    assert report["status"] == "blocked_checkpoint_candidate"
    assert "source_wheel_parity_incomplete" in report["blockers"]
    assert parity["complete"] is False
    assert parity["source_only_count"] == 0
    assert parity["wheel_only_count"] == 0
    assert parity["content_mismatch_count"] == 1
    mismatch = parity["content_mismatches"][0]
    assert mismatch["path"] == "src/rocketdict/api/client.py"
    assert mismatch["source_sha256"] != mismatch["wheel_sha256"]
    assert report["promotion_allowed"] is False


def test_known_full_checkpoint_name_with_wrong_sha_is_explicitly_blocked(tmp_path: Path) -> None:
    checkpoint = _checkpoint(
        tmp_path / "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip"
    )
    catalog = _catalog(tmp_path / "catalog.json", checkpoint, expected_sha="0" * 64)

    report = inspect_full_checkpoint(checkpoint, checkpoint_catalog=catalog)

    assert report["status"] == "blocked_checkpoint_candidate"
    assert report["historical_checkpoint_name_match"] is True
    assert report["historical_checkpoint_exact_identity_match"] is False
    assert "historical_catalog_exact_identity_mismatch" in report["blockers"]
    match = report["historical_checkpoint_matches"][0]
    assert match["sha256_match"] is False
    assert match["size_constraint_available"] is False
    assert match["exact_identity_mismatch"] is True
    assert report["promotion_allowed"] is False


def test_nested_known_wheel_with_wrong_catalog_sha_blocks_checkpoint(tmp_path: Path) -> None:
    checkpoint = _checkpoint(
        tmp_path / "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip"
    )
    catalog = _catalog(
        tmp_path / "catalog.json",
        checkpoint,
        expected_wheel_sha="0" * 64,
    )

    report = inspect_full_checkpoint(checkpoint, checkpoint_catalog=catalog)

    assert report["historical_checkpoint_exact_identity_match"] is True
    assert report["status"] == "blocked_checkpoint_candidate"
    assert report["nested_rocketdict_wheel_catalog_exact_match_count"] == 0
    assert report["nested_rocketdict_wheel_catalog_exact_mismatch_count"] == 1
    assert "nested_rocketdict_wheel_historical_catalog_exact_identity_mismatch" in report["blockers"]
    wheel = report["nested_rocketdict_wheels"][0]
    assert wheel["historical_catalog_exact_identity_match"] is False
    assert wheel["historical_catalog_exact_identity_mismatch"] is True
    assert wheel["historical_catalog_matches"][0]["sha256_match"] is False


def test_checkpoint_rejects_unsafe_outer_member_names(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path / "unsafe.zip", unsafe_member=True)
    with pytest.raises(RecoveryCandidateError, match="unsafe member names"):
        inspect_full_checkpoint(checkpoint)


def test_checkpoint_without_source_root_is_blocked_but_evidence_remains_visible(tmp_path: Path) -> None:
    checkpoint = tmp_path / "reports-only.zip"
    with zipfile.ZipFile(checkpoint, "w") as zf:
        zf.writestr("README.md", "report only")
        zf.writestr("MANIFEST.json", "{}")

    report = inspect_full_checkpoint(checkpoint)
    assert report["status"] == "blocked_checkpoint_candidate"
    assert report["source_root_unique"] is False
    assert report["source_roots"] == []
    assert "rocketdict_source_root_missing" in report["blockers"]
    assert report["compatibility_plan"] is None
    assert report["evidence_inventory_count"] == 2
    assert report["promotion_allowed"] is False


def test_unified_scan_attaches_full_checkpoint_proof_and_counters(tmp_path: Path) -> None:
    checkpoint = _checkpoint(
        tmp_path / "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip"
    )
    nested = _nested_wheel_bytes(checkpoint)
    catalog = _catalog(
        tmp_path / "catalog.json",
        checkpoint,
        expected_wheel_sha=hashlib.sha256(nested).hexdigest(),
    )

    report = scan_recovery_pipeline(tmp_path, checkpoint_catalog=catalog)

    assert report["schema"] == "rocketdict-workbench-core-recovery-scan/8"
    assert report["promotion_allowed"] is False
    assert report["product_execution_allowed"] is False
    assert report["checkpoint_pipeline_count"] == 1
    assert report["checkpoint_exact_identity_match_count"] == 1
    assert report["checkpoint_blocked_count"] == 0
    assert report["checkpoint_source_api_complete_count"] == 1
    assert report["checkpoint_nested_wheel_count"] == 1
    assert report["checkpoint_nested_wheel_integrity_ok_count"] == 1
    assert report["checkpoint_nested_wheel_catalog_exact_match_count"] == 1
    assert report["checkpoint_nested_wheel_catalog_exact_mismatch_count"] == 0
    assert report["checkpoint_source_wheel_parity_complete_count"] == 1
    assert report["wheel_pipeline_count"] == 0
    assert report["error_count"] == 0
    row = report["candidates"][0]
    assert row["kind"] == "zip"
    assert row["checkpoint_recovery_status"] == "exact_historical_checkpoint_candidate"
    assert row["checkpoint_exact_identity_match"] is True
    assert row["checkpoint_source_api_complete"] is True
    assert row["checkpoint_nested_rocketdict_wheel_count"] == 1
    assert row["checkpoint_source_wheel_parity_complete_count"] == 1
    assert row["checkpoint_recovery"]["source"]["version"] == "0.30.34"


def test_pyproject_exposes_full_checkpoint_cli() -> None:
    project = tomllib.loads(
        (_repo() / "rocketdict-workbench" / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert project["project"]["scripts"]["rocketdict-recover-checkpoint"] == (
        "rocketdict_workbench.core_checkpoint_recovery:main"
    )
