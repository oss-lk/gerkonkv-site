from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from rocketdict_workbench.core_compatibility import (
    RecoveryCompatibilityError,
    build_core_recovery_plan,
)


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _target_root() -> Path:
    return _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"


def _history() -> dict:
    return json.loads((_target_root() / "core-recovery-history.json").read_text(encoding="utf-8"))


def _build_full_base(root: Path, *, version: str = "0.30.29") -> Path:
    repo = _repo()
    target = _target_root()
    source_root = root / "src"
    pkg = source_root / "rocketdict"

    history = _history()
    members = history["historical_materializer_contract"]["expected_overlay_members"]
    for logical in members:
        path = root / logical
        path.parent.mkdir(parents=True, exist_ok=True)
        if logical == "src/rocketdict/__init__.py":
            raw = (target / logical).read_bytes().replace(b"0.30.40", version.encode("ascii"))
            path.write_bytes(raw)
        elif logical == "src/rocketdict/nlp/registry.py":
            path.write_bytes((target / logical).read_bytes())
        else:
            path.write_text(f"# historical base placeholder for {logical}\n", encoding="utf-8")

    # Public/base modules are deliberately outside the Stage8 overlay contract.
    for path in (
        pkg / "api" / "__init__.py",
        pkg / "api" / "cli.py",
        pkg / "importing" / "__init__.py",
        pkg / "importing" / "cli.py",
        pkg / "interpretation" / "__init__.py",
        pkg / "interpretation" / "cli.py",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    (pkg / "api" / "contracts.py").write_text(
        'API_VERSION = "historical-test-api/1"\n', encoding="utf-8"
    )
    (pkg / "api" / "client.py").write_text(
        "class RocketDictAPI:\n    pass\n", encoding="utf-8"
    )
    (pkg / "database.py").write_text(
        "def bootstrap_database(path):\n    return None\n", encoding="utf-8"
    )
    return root


def test_old_full_base_plan_requires_17_missing_target_overlay_members(tmp_path: Path) -> None:
    base = _build_full_base(tmp_path / "base")
    report = build_core_recovery_plan(base)

    assert report["schema"] == "rocketdict-workbench-core-recovery-plan/1"
    assert report["status"] == "blocked_missing_exact_overlay_bytes"
    assert report["promotion_allowed"] is False
    assert report["writes_source"] is False
    assert report["candidate"]["rocketdict_version"] == "0.30.29"
    assert report["candidate"]["structural_complete_for_workbench_bridge"] is True
    assert report["candidate"]["runtime_probe_ok"] is True
    assert report["target"]["overlay_member_count"] == 19
    assert report["target"]["exact_target_available_count"] == 2
    assert report["target"]["exact_target_missing_count"] == 17
    assert report["target"]["exact_target_already_present_count"] == 1
    assert report["target"]["exact_replacement_available_count"] == 1
    assert "missing_exact_overlay_targets:17" in report["blockers"]
    assert "exact_0.30.40_public_api_bytes_not_recovered" in report["blockers"]

    by_path = {row["path"]: row for row in report["overlay_plan"]}
    assert by_path["src/rocketdict/__init__.py"]["action"] == "exact_replacement_available"
    assert by_path["src/rocketdict/nlp/registry.py"]["action"] == "exact_target_already_present"
    assert by_path["src/rocketdict/lab/stage12_pilot.py"]["action"] == "replacement_required_but_target_missing"
    assert by_path["tests/test_stage8_integrity_research.py"]["action"] == "replacement_required_but_target_missing"

    for name, row in report["base_api_dependencies"].items():
        assert name.startswith("rocketdict.api.")
        assert row["candidate_available"] is True
        assert row["target_03040_exact_bytes_recovered"] is False
        assert row["compatibility"] == "unproven_against_exact_0.30.40"


def test_unmanifested_target_file_never_becomes_exact_recovery_evidence(tmp_path: Path) -> None:
    base = _build_full_base(tmp_path / "base")
    evidence = tmp_path / "evidence"
    shutil.copytree(_target_root(), evidence)
    extra = evidence / "src/rocketdict/lab/stage12_pilot.py"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("# tempting but unmanifested target bytes\n", encoding="utf-8")

    report = build_core_recovery_plan(base, target_evidence_root=evidence)
    row = next(
        row for row in report["overlay_plan"]
        if row["path"] == "src/rocketdict/lab/stage12_pilot.py"
    )
    assert row["target"]["available"] is False
    assert row["target"]["manifested_exact_target"] is False
    assert row["target"]["reason"] == "no_exact_recovery_manifest_identity"
    assert row["action"] == "replacement_required_but_target_missing"
    assert report["target"]["exact_target_missing_count"] == 17


def test_manifested_target_byte_drift_fails_closed(tmp_path: Path) -> None:
    base = _build_full_base(tmp_path / "base")
    evidence = tmp_path / "evidence"
    shutil.copytree(_target_root(), evidence)
    target = evidence / "src/rocketdict/nlp/registry.py"
    target.write_bytes(target.read_bytes() + b"\n# drift\n")

    with pytest.raises(RecoveryCompatibilityError, match="drifted"):
        build_core_recovery_plan(base, target_evidence_root=evidence)


def test_current_two_file_recovery_namespace_is_not_a_reconstructable_base() -> None:
    report = build_core_recovery_plan(_target_root(), probe_runtime=False)

    assert report["status"] == "blocked_missing_exact_overlay_bytes"
    assert report["promotion_allowed"] is False
    assert report["candidate"]["rocketdict_version"] == "0.30.40"
    assert report["candidate"]["structural_complete_for_workbench_bridge"] is False
    assert report["target"]["exact_target_available_count"] == 2
    assert report["target"]["exact_target_missing_count"] == 17
    assert "base_required_workbench_modules_missing" in report["blockers"]


def test_recovery_plan_fingerprint_is_deterministic(tmp_path: Path) -> None:
    base = _build_full_base(tmp_path / "base")
    first = build_core_recovery_plan(base)
    second = build_core_recovery_plan(base)
    assert first["identity"]["fingerprint"] == second["identity"]["fingerprint"]
    assert len(first["identity"]["fingerprint"]) == 64


def test_zip_candidate_remains_structural_and_never_becomes_promotional(tmp_path: Path) -> None:
    import zipfile

    base = _build_full_base(tmp_path / "base")
    archive = tmp_path / "candidate.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            zf.write(path, "checkpoint/" + path.relative_to(base).as_posix())

    report = build_core_recovery_plan(archive)
    assert report["promotion_allowed"] is False
    assert report["candidate"]["source"]["kind"] == "zip"
    assert report["candidate"]["runtime_probe_ok"] is False
    assert report["candidate"]["documented_archive_identity"]["applicable"] is True
    assert report["candidate"]["documented_archive_identity"]["match"] is False
    assert "base_runtime_import_probe_not_proven" in report["blockers"]
