from __future__ import annotations

import base64
import csv
import hashlib
import io
from pathlib import Path
import zipfile

from rocketdict_workbench.core_wheel_integrity import inspect_wheel_integrity


def _record_digest(raw: bytes) -> str:
    digest = hashlib.sha256(raw).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _wheel(
    path: Path,
    *,
    version: str = "0.30.34",
    metadata_version: str | None = None,
    corrupt_record: bool = False,
) -> Path:
    metadata_version = metadata_version or version
    files: dict[str, bytes] = {
        "rocketdict/__init__.py": f'__version__ = "{version}"\n'.encode(),
        "rocketdict/api/__init__.py": b"",
        "rocketdict/api/contracts.py": b'API_VERSION = "integrity-test/1"\n',
        f"rocketdict-{version}.dist-info/METADATA": (
            "Metadata-Version: 2.1\n"
            "Name: rocketdict\n"
            f"Version: {metadata_version}\n"
            "Requires-Python: >=3.11\n"
            "Requires-Dist: SQLAlchemy>=2\n"
            "Requires-Dist: typer>=0.12\n"
        ).encode("utf-8"),
        f"rocketdict-{version}.dist-info/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: rocketdict-test\n"
            "Root-Is-Purelib: true\n"
            "Tag: py3-none-any\n"
        ).encode("utf-8"),
    }
    record_name = f"rocketdict-{version}.dist-info/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for member, raw in sorted(files.items()):
        digest = _record_digest(raw)
        if corrupt_record and member == "rocketdict/api/contracts.py":
            digest = "sha256=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        writer.writerow([member, digest, str(len(raw))])
    writer.writerow([record_name, "", ""])
    files[record_name] = output.getvalue().encode("utf-8")

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member, raw in files.items():
            zf.writestr(member, raw)
    return path


def test_wheel_metadata_and_record_are_verified_read_only(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.34-py3-none-any.whl")

    report = inspect_wheel_integrity(wheel)

    assert report["schema"] == "rocketdict-workbench-wheel-integrity/1"
    assert report["status"] == "wheel_integrity_verified"
    assert report["ok"] is True
    assert report["promotion_allowed"] is False
    assert report["zip_crc_ok"] is True
    assert report["distribution_is_rocketdict"] is True
    assert report["filename_metadata_name_consistent"] is True
    assert report["filename_metadata_version_consistent"] is True
    assert report["py3_none_any_tag_present"] is True
    assert report["metadata"]["name"] == "rocketdict"
    assert report["metadata"]["version"] == "0.30.34"
    assert report["metadata"]["requires_python"] == ">=3.11"
    assert report["metadata"]["requires_dist"] == ["SQLAlchemy>=2", "typer>=0.12"]
    assert report["record"]["available"] is True
    assert report["record"]["verified"] is True
    assert report["record"]["status"] == "record_verified"
    assert report["record"]["hash_mismatches"] == []
    assert report["record"]["size_mismatches"] == []
    assert report["record"]["unrecorded_members"] == []
    assert len(report["wheel_sha256"]) == 64
    assert report["wheel_bytes"] == wheel.stat().st_size
    assert len(report["identity"]["fingerprint"]) == 64


def test_corrupt_record_hash_fails_integrity_without_executing_wheel(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "rocketdict-0.30.34-py3-none-any.whl",
        corrupt_record=True,
    )

    report = inspect_wheel_integrity(wheel)

    assert report["ok"] is False
    assert report["status"] == "wheel_integrity_failed"
    assert "wheel_record_verification_failed" in report["hard_failures"]
    assert report["record"]["verified"] is False
    assert len(report["record"]["hash_mismatches"]) == 1
    assert report["record"]["hash_mismatches"][0]["path"] == "rocketdict/api/contracts.py"
    assert report["promotion_allowed"] is False


def test_filename_metadata_version_drift_is_hard_failure(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "rocketdict-0.30.34-py3-none-any.whl",
        metadata_version="0.30.33",
    )

    report = inspect_wheel_integrity(wheel)

    assert report["record"]["verified"] is True
    assert report["filename_metadata_version_consistent"] is False
    assert "filename_metadata_version_mismatch" in report["hard_failures"]
    assert report["ok"] is False
    assert report["promotion_allowed"] is False


def test_missing_record_is_visible_but_not_invented(tmp_path: Path) -> None:
    wheel = tmp_path / "rocketdict-0.30.34-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("rocketdict/__init__.py", '__version__ = "0.30.34"\n')
        zf.writestr(
            "rocketdict-0.30.34.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: rocketdict\nVersion: 0.30.34\n",
        )
        zf.writestr(
            "rocketdict-0.30.34.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )

    report = inspect_wheel_integrity(wheel)

    assert report["record"]["available"] is False
    assert report["record"]["verified"] is False
    assert report["record"]["status"] == "record_unavailable"
    assert "wheel_record_verification_failed" not in report["hard_failures"]
    assert report["ok"] is True
