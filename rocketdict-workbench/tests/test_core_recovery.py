from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from rocketdict_workbench.core_recovery import (
    EXACT_PRODUCT_VERSION,
    RecoveryCandidateError,
    inspect_core_candidate,
)


def _recovered(repo: Path, relative: str) -> bytes:
    return (
        repo
        / "rocketdict"
        / "recovered"
        / "stage8-0.30.40"
        / relative
    ).read_bytes()


def _write_candidate(root: Path, repo: Path, *, version: str = EXACT_PRODUCT_VERSION) -> Path:
    src = root / "src"
    pkg = src / "rocketdict"
    (pkg / "api").mkdir(parents=True)
    (pkg / "importing").mkdir()
    (pkg / "interpretation").mkdir()
    (pkg / "nlp").mkdir()

    package_root = _recovered(repo, "src/rocketdict/__init__.py")
    if version != EXACT_PRODUCT_VERSION:
        package_root = package_root.replace(EXACT_PRODUCT_VERSION.encode(), version.encode())
    (pkg / "__init__.py").write_bytes(package_root)
    (pkg / "nlp" / "registry.py").write_bytes(
        _recovered(repo, "src/rocketdict/nlp/registry.py")
    )
    (pkg / "api" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "api" / "contracts.py").write_text(
        'API_VERSION = "candidate-test-api/1"\n', encoding="utf-8"
    )
    (pkg / "api" / "client.py").write_text(
        "class RocketDictAPI:\n    pass\n", encoding="utf-8"
    )
    (pkg / "api" / "cli.py").write_text("", encoding="utf-8")
    (pkg / "database.py").write_text(
        "def bootstrap_database(path):\n    return None\n", encoding="utf-8"
    )
    (pkg / "importing" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "importing" / "cli.py").write_text("", encoding="utf-8")
    (pkg / "interpretation" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "interpretation" / "cli.py").write_text("", encoding="utf-8")
    return root


def test_exact_version_directory_candidate_is_still_non_promotional(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    root = _write_candidate(tmp_path / "candidate", repo)
    result = inspect_core_candidate(root)

    assert result["status"] == "exact_version_structural_candidate"
    assert result["promotion_allowed"] is False
    assert result["observed"]["rocketdict_version"] == "0.30.40"
    assert result["observed"]["missing_required_modules"] == []
    assert result["observed"]["exact_recovered_mismatch_paths"] == []
    assert result["runtime_probe"]["ok"] is True
    assert result["runtime_probe"]["api_version"] == "candidate-test-api/1"
    assert result["runtime_probe"]["outside_candidate_source_root"] == {}
    assert (
        "live_product_preflight_api_probe_and_execution_binding_not_run"
        in result["promotion_blockers"]
    )
    assert len(result["identity"]["fingerprint"]) == 64


def test_older_full_core_is_only_base_candidate(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    root = _write_candidate(tmp_path / "candidate", repo, version="0.30.29")
    result = inspect_core_candidate(root)

    assert result["status"] == "base_candidate_requires_compatibility_proof"
    assert result["runtime_probe"]["ok"] is True
    assert "candidate_is_not_exact_0.30.40" in result["promotion_blockers"]
    assert (
        "src/rocketdict/__init__.py"
        in result["observed"]["exact_recovered_mismatch_paths"]
    )
    assert result["promotion_allowed"] is False


def test_missing_public_api_is_incomplete_even_when_version_matches(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    pkg = tmp_path / "candidate" / "src" / "rocketdict"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_bytes(
        _recovered(repo, "src/rocketdict/__init__.py")
    )
    result = inspect_core_candidate(tmp_path / "candidate", probe_runtime=False)

    assert result["status"] == "incomplete_candidate"
    assert "rocketdict.api.contracts" in result["observed"]["missing_required_modules"]
    assert "required_workbench_bridge_modules_missing" in result["promotion_blockers"]


def test_zip_candidate_is_read_only_structural_evidence(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    root = _write_candidate(tmp_path / "candidate", repo)
    archive = tmp_path / "checkpoint.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in sorted((root / "src").rglob("*.py")):
            zf.write(path, "checkpoint/" + path.relative_to(root).as_posix())

    result = inspect_core_candidate(archive)

    assert result["candidate"]["kind"] == "zip"
    assert result["candidate"]["archive_prefix"] == "checkpoint"
    assert result["candidate"]["source_layout"] == "src"
    assert result["runtime_probe"]["attempted"] is False
    assert result["runtime_probe"]["reason"].startswith("zip_is_structural_evidence_only")
    assert result["status"] == "exact_version_structural_candidate"
    assert result["promotion_allowed"] is False


def test_archive_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../src/rocketdict/__init__.py", '__version__ = "0.30.40"\n')
    with pytest.raises(RecoveryCandidateError, match="unsafe"):
        inspect_core_candidate(archive)


def test_ambiguous_directory_layout_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "src" / "rocketdict").mkdir(parents=True)
    (tmp_path / "src" / "rocketdict" / "__init__.py").write_text(
        '__version__ = "0.30.40"\n', encoding="utf-8"
    )
    (tmp_path / "rocketdict").mkdir()
    (tmp_path / "rocketdict" / "__init__.py").write_text(
        '__version__ = "0.30.40"\n', encoding="utf-8"
    )
    with pytest.raises(RecoveryCandidateError, match="ambiguous"):
        inspect_core_candidate(tmp_path)
