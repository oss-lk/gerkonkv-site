from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from rocketdict_workbench.core_scan import RecoveryScanError, scan_core_candidates


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _target() -> Path:
    return _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"


def _candidate(root: Path, version: str = "0.30.34") -> Path:
    pkg = root / "src" / "rocketdict"
    (pkg / "api").mkdir(parents=True)
    (pkg / "importing").mkdir()
    (pkg / "interpretation").mkdir()
    (pkg / "nlp").mkdir()
    init = (_target() / "src/rocketdict/__init__.py").read_bytes()
    (pkg / "__init__.py").write_bytes(init.replace(b"0.30.40", version.encode("ascii")))
    (pkg / "nlp" / "registry.py").write_bytes(
        (_target() / "src/rocketdict/nlp/registry.py").read_bytes()
    )
    (pkg / "api" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "api" / "contracts.py").write_text('API_VERSION = "scan-sha-test/1"\n', encoding="utf-8")
    (pkg / "api" / "client.py").write_text("class RocketDictAPI:\n    pass\n", encoding="utf-8")
    (pkg / "api" / "cli.py").write_text("", encoding="utf-8")
    (pkg / "database.py").write_text("", encoding="utf-8")
    (pkg / "importing" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "importing" / "cli.py").write_text("", encoding="utf-8")
    (pkg / "interpretation" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "interpretation" / "cli.py").write_text("", encoding="utf-8")
    return root


def _zip(source: Path, destination: Path) -> Path:
    with zipfile.ZipFile(destination, "w") as zf:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            zf.write(path, "payload/" + path.relative_to(source).as_posix())
    return destination


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _catalog(path: Path, archive: Path, *, expected_sha: str, expected_bytes: int | None) -> Path:
    payload = {
        "schema": "rocketdict-historical-checkpoint-catalog/1",
        "promotion_allowed": False,
        "entries": [
            {
                "id": "stage6y-test",
                "version": "0.30.34",
                "stage": "LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE",
                "archive_name_patterns": [archive.name],
                "archive_sha256": expected_sha,
                "archive_bytes": expected_bytes,
                "wheel_name_patterns": [],
                "wheel_sha256": None,
                "wheel_bytes": None,
                "candidate_role": "test",
                "evidence_level": "test",
                "promotion_allowed": False,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_exact_zip_sha_is_sufficient_when_historical_size_is_unknown(tmp_path: Path) -> None:
    source = _candidate(tmp_path / "source")
    archive = _zip(
        source,
        tmp_path / "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip",
    )
    catalog = _catalog(
        tmp_path / "catalog.json",
        archive,
        expected_sha=_sha(archive),
        expected_bytes=None,
    )

    report = scan_core_candidates(archive, checkpoint_catalog=catalog)
    row = report["candidates"][0]
    match = row["historical_checkpoint_matches"][0]

    assert report["schema"] == "rocketdict-workbench-core-recovery-scan/3"
    assert row["historical_checkpoint_exact_identity_match"] is True
    assert match["exact_identity_available"] is True
    assert match["exact_identity_match"] is True
    assert match["sha256_match"] is True
    assert match["size_constraint_available"] is False
    assert match["size_match"] is True
    assert match["expected_archive_bytes"] is None
    assert match["promotion_allowed"] is False


def test_wrong_sha_is_rejected_even_when_size_is_unknown(tmp_path: Path) -> None:
    source = _candidate(tmp_path / "source")
    archive = _zip(
        source,
        tmp_path / "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip",
    )
    catalog = _catalog(
        tmp_path / "catalog.json",
        archive,
        expected_sha="0" * 64,
        expected_bytes=None,
    )

    match = scan_core_candidates(archive, checkpoint_catalog=catalog)["candidates"][0][
        "historical_checkpoint_matches"
    ][0]
    assert match["sha256_match"] is False
    assert match["size_constraint_available"] is False
    assert match["exact_identity_match"] is False
    assert match["exact_identity_mismatch"] is True


def test_known_size_remains_mandatory_additional_identity_guard(tmp_path: Path) -> None:
    source = _candidate(tmp_path / "source")
    archive = _zip(
        source,
        tmp_path / "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip",
    )
    catalog = _catalog(
        tmp_path / "catalog.json",
        archive,
        expected_sha=_sha(archive),
        expected_bytes=archive.stat().st_size + 1,
    )

    match = scan_core_candidates(archive, checkpoint_catalog=catalog)["candidates"][0][
        "historical_checkpoint_matches"
    ][0]
    assert match["sha256_match"] is True
    assert match["size_constraint_available"] is True
    assert match["size_match"] is False
    assert match["exact_identity_match"] is False
    assert match["exact_identity_mismatch"] is True


def test_catalog_rejects_archive_size_without_sha(tmp_path: Path) -> None:
    source = _candidate(tmp_path / "source")
    archive = _zip(source, tmp_path / "candidate.zip")
    catalog = _catalog(
        tmp_path / "catalog.json",
        archive,
        expected_sha="0" * 64,
        expected_bytes=archive.stat().st_size,
    )
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    payload["entries"][0]["archive_sha256"] = None
    catalog.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RecoveryScanError, match="byte size lacks SHA-256"):
        scan_core_candidates(archive, checkpoint_catalog=catalog)
