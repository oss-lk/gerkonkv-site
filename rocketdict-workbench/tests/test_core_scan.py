from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from rocketdict_workbench.core_scan import (
    RecoveryScanError,
    discover_core_candidates,
    scan_core_candidates,
)


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _target() -> Path:
    return _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"


def _candidate(root: Path, version: str) -> Path:
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
    (pkg / "api" / "contracts.py").write_text('API_VERSION = "scan-test/1"\n', encoding="utf-8")
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


def test_discovery_finds_source_roots_and_zips_without_duplicate_nested_roots(tmp_path: Path) -> None:
    exact = _candidate(tmp_path / "nested" / "exact", "0.30.40")
    old = _candidate(tmp_path / "old", "0.30.29")
    (tmp_path / "archives").mkdir()
    archive = _zip(old, tmp_path / "archives" / "old.zip")

    found = discover_core_candidates(tmp_path)
    assert exact.resolve() in found
    assert old.resolve() in found
    assert archive.resolve() in found
    assert len(found) == 3


def test_batch_scan_ranks_exact_version_structural_candidate_before_old_base(tmp_path: Path) -> None:
    exact = _candidate(tmp_path / "exact", "0.30.40")
    old = _candidate(tmp_path / "old", "0.30.29")

    report = scan_core_candidates(tmp_path)

    assert report["status"] == "completed"
    assert report["promotion_allowed"] is False
    assert report["discovered_candidate_count"] == 2
    assert report["analyzed_candidate_count"] == 2
    assert report["error_count"] == 0
    assert report["probe_directories"] is False
    assert report["candidates"][0]["path"] == str(exact.resolve())
    assert report["candidates"][0]["candidate_report_status"] == "exact_version_structural_candidate"
    assert report["candidates"][0]["recovery_priority_rank"] == 1
    assert report["candidates"][1]["path"] == str(old.resolve())
    assert report["candidates"][1]["candidate_report_status"] == "base_candidate_requires_compatibility_proof"
    assert all(row["promotion_allowed"] is False for row in report["candidates"])
    assert len(report["identity"]["fingerprint"]) == 64


def test_batch_scan_runtime_probe_is_opt_in_for_directories(tmp_path: Path) -> None:
    exact = _candidate(tmp_path / "exact", "0.30.40")

    structural = scan_core_candidates(tmp_path)
    assert structural["candidates"][0]["runtime_probe_ok"] is False

    probed = scan_core_candidates(tmp_path, probe_directories=True)
    assert probed["candidates"][0]["path"] == str(exact.resolve())
    assert probed["candidates"][0]["runtime_probe_ok"] is True


def test_batch_scan_writes_hash_named_full_plan_sidecars(tmp_path: Path) -> None:
    _candidate(tmp_path / "exact", "0.30.40")
    reports = tmp_path / "reports"

    summary = scan_core_candidates(tmp_path / "exact", reports_dir=reports)
    fingerprint = summary["candidates"][0]["compatibility_plan_fingerprint"]
    sidecar = reports / f"{fingerprint[:16]}.json"
    assert sidecar.is_file()
    plan = json.loads(sidecar.read_text(encoding="utf-8"))
    assert plan["identity"]["fingerprint"] == fingerprint
    assert plan["promotion_allowed"] is False
    assert plan["writes_source"] is False


def test_invalid_zip_is_recorded_without_aborting_other_candidates(tmp_path: Path) -> None:
    _candidate(tmp_path / "good", "0.30.29")
    (tmp_path / "broken.zip").write_bytes(b"not a zip")

    report = scan_core_candidates(tmp_path)
    assert report["discovered_candidate_count"] == 2
    assert report["analyzed_candidate_count"] == 1
    assert report["error_count"] == 1
    assert report["errors"][0]["path"].endswith("broken.zip")
    assert report["candidates"][0]["path"].endswith("good")


def test_candidate_limit_fails_closed(tmp_path: Path) -> None:
    _candidate(tmp_path / "a", "0.30.29")
    _candidate(tmp_path / "b", "0.30.29")
    with pytest.raises(RecoveryScanError, match="exceeded"):
        discover_core_candidates(tmp_path, max_candidates=1)
