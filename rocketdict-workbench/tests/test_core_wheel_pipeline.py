from __future__ import annotations

import base64
import csv
import hashlib
import io
from pathlib import Path
import sys
import zipfile

from rocketdict_workbench.core_scan_pipeline import scan_recovery_pipeline
from rocketdict_workbench.core_wheel_pipeline import recover_wheel_candidate


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _target() -> Path:
    return _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"


def _record_digest(raw: bytes) -> str:
    digest = hashlib.sha256(raw).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _wheel(path: Path, *, corrupt_record: bool = False) -> Path:
    version = "0.30.34"
    init = (_target() / "src/rocketdict/__init__.py").read_bytes().replace(
        b"0.30.40", b"0.30.34"
    )
    files: dict[str, bytes] = {
        "rocketdict/__init__.py": init,
        "rocketdict/nlp/__init__.py": b"",
        "rocketdict/nlp/registry.py": (
            _target() / "src/rocketdict/nlp/registry.py"
        ).read_bytes(),
        "rocketdict/api/__init__.py": b"",
        "rocketdict/api/contracts.py": b'API_VERSION = "pipeline-test/1"\n',
        "rocketdict/api/client.py": b"class RocketDictAPI:\n    pass\n",
        "rocketdict/api/cli.py": b"",
        "rocketdict/database.py": b"def bootstrap_database(path):\n    return None\n",
        "rocketdict/importing/__init__.py": b"",
        "rocketdict/importing/cli.py": b"",
        "rocketdict/interpretation/__init__.py": b"",
        "rocketdict/interpretation/cli.py": b"",
        f"rocketdict-{version}.dist-info/METADATA": (
            "Metadata-Version: 2.1\n"
            "Name: rocketdict\n"
            f"Version: {version}\n"
            "Requires-Python: >=3.11\n"
        ).encode("utf-8"),
        f"rocketdict-{version}.dist-info/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: pipeline-test\n"
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


def test_valid_wheel_builds_full_read_only_proof_without_runtime_by_default(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.34-py3-none-any.whl")

    report = recover_wheel_candidate(wheel, probe_runtime=False)

    assert report["schema"] == "rocketdict-workbench-core-wheel-recovery/4"
    assert report["status"] == "verified_structural_base_candidate"
    assert report["promotion_allowed"] is False
    assert report["product_execution_allowed"] is False
    assert report["integrity"]["schema"] == "rocketdict-workbench-wheel-integrity/2"
    assert report["integrity"]["ok"] is True
    assert report["structural_candidate"]["observed"]["rocketdict_version"] == "0.30.34"
    assert report["compatibility_plan"]["target"]["exact_target_missing_count"] == 17
    assert report["runtime_probe"]["status"] == "not_requested"
    assert report["runtime_probe"]["attempted"] is False
    assert report["runtime_proven"] is False
    assert report["artifact"]["artifact_identity_consistent"] is True
    assert report["artifact"]["version_consistent"] is True
    assert len(report["identity"]["fingerprint"]) == 64


def test_valid_wheel_can_add_runtime_proof_but_never_promote_product(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.34-py3-none-any.whl")

    report = recover_wheel_candidate(
        wheel,
        probe_runtime=True,
        python=sys.executable,
    )

    assert report["status"] == "runtime_proven_base_candidate"
    assert report["runtime_probe"]["attempted"] is True
    assert report["runtime_probe"]["ok"] is True
    assert report["runtime_probe"]["status"] == "runtime_import_proven"
    assert report["runtime_proven"] is True
    assert report["artifact"]["sha256"] == report["runtime_probe"]["wheel_sha256"]
    assert report["promotion_allowed"] is False
    assert report["product_execution_allowed"] is False
    assert "missing_exact_0.30.40_overlay_and_public_api_compatibility_proof" in report[
        "remaining_product_blockers"
    ]


def test_corrupt_record_blocks_runtime_even_when_explicitly_requested(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "rocketdict-0.30.34-py3-none-any.whl",
        corrupt_record=True,
    )

    report = recover_wheel_candidate(
        wheel,
        probe_runtime=True,
        python=sys.executable,
    )

    assert report["status"] == "blocked_wheel_integrity"
    assert report["integrity"]["ok"] is False
    assert "wheel_record_verification_failed" in report["integrity"]["hard_failures"]
    assert report["runtime_probe"]["status"] == "blocked_by_wheel_integrity"
    assert report["runtime_probe"]["attempted"] is False
    assert report["runtime_probe"]["ok"] is False
    assert report["runtime_proven"] is False
    assert "wheel_integrity:wheel_record_verification_failed" in report[
        "remaining_product_blockers"
    ]
    assert report["promotion_allowed"] is False


def test_batch_scan_preserves_corrupt_wheel_but_never_executes_it(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "rocketdict-0.30.34-py3-none-any.whl",
        corrupt_record=True,
    )

    report = scan_recovery_pipeline(
        wheel,
        probe_wheels=True,
        python=sys.executable,
    )

    assert report["schema"] == "rocketdict-workbench-core-recovery-scan/6"
    assert report["promotion_allowed"] is False
    assert report["product_execution_allowed"] is False
    assert report["wheel_pipeline_count"] == 1
    assert report["wheel_integrity_ok_count"] == 0
    assert report["wheel_runtime_attempted_count"] == 0
    assert report["wheel_runtime_proven_count"] == 0
    assert report["analyzed_candidate_count"] == 1
    row = report["candidates"][0]
    assert row["path"] == str(wheel.resolve())
    assert row["wheel_recovery_status"] == "blocked_wheel_integrity"
    assert row["wheel_integrity_ok"] is False
    assert row["runtime_probe_ok"] is False
    assert row["runtime_proof_status"] == "blocked_by_wheel_integrity"
    assert row["promotion_allowed"] is False


def test_batch_scan_valid_wheel_proves_runtime_only_after_integrity(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.34-py3-none-any.whl")

    report = scan_recovery_pipeline(
        wheel,
        probe_wheels=True,
        python=sys.executable,
    )

    assert report["wheel_pipeline_count"] == 1
    assert report["wheel_integrity_ok_count"] == 1
    assert report["wheel_runtime_attempted_count"] == 1
    assert report["wheel_runtime_proven_count"] == 1
    row = report["candidates"][0]
    assert row["wheel_integrity_ok"] is True
    assert row["runtime_probe_ok"] is True
    assert row["runtime_proof_status"] == "runtime_import_proven"
    assert row["cross_layer_artifact_identity_consistent"] is True
    assert len(row["wheel_recovery_fingerprint"]) == 64
    assert row["promotion_allowed"] is False
