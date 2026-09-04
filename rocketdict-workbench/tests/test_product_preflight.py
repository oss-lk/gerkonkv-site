from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from rocketdict_workbench.cli import parser
import rocketdict_workbench.product_preflight as preflight


@dataclass
class _Paths:
    root: Path


class _Core:
    def doctor(self):  # type: ignore[no-untyped-def]
        return SimpleNamespace(
            available=True,
            python="python",
            rocketdict_version="0.30.40",
            api_version="1",
            capabilities={},
            error=None,
        )


class _Project:
    def __init__(self, root: Path, inputs: list[dict], manifest: dict | None = None) -> None:
        self.paths = _Paths(root=root)
        self.core = _Core()
        self._inputs = inputs
        self._manifest = manifest or {"registry_hash": "registry-1"}
        self.probe_runtime = None

    def metadata(self) -> dict:
        return {"inputs": self._inputs}

    def lab_catalog(self, *, probe_runtime: bool = False) -> dict:
        self.probe_runtime = probe_runtime
        return self._manifest


def _source(root: Path, text: str = "Hello world") -> dict:
    uploads = root / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    path = uploads / f"{sha[:16]}-input.txt"
    path.write_bytes(data)
    return {
        "source_name": "input.txt",
        "copied_path": str(path.relative_to(root).as_posix()),
        "sha256": sha,
        "byte_size": len(data),
        "suffix": ".txt",
        "import": {"import_event_id": 7},
        "interpretation": {"document_version_id": 11, "selected_format": "txt"},
    }


def _profile(*, unavailable_stage: int | None = None) -> dict:
    stages = {}
    for number in preflight.REQUIRED_CORE_STAGES:
        stages[str(number)] = {
            "implementation": "opus-en-ru-ct2" if number == 12 else f"stage-{number}",
            "parameters": {"compute_type": "float32"} if number == 12 else {},
            "adapter_descriptor_hash": f"descriptor-{number}",
            "availability": {"available": number != unavailable_stage},
        }
    return {
        "schema": preflight.PROFILE_SCHEMA,
        "source_kind": "text",
        "registry_hash": "registry-1",
        "stages": stages,
        "quality_gates": [
            {
                "implementation": key,
                "parameters": {},
                "adapter_descriptor_hash": f"gate-{index}",
            }
            for index, key in enumerate(preflight.QUALITY_GATES)
        ],
    }


def _install_profile_stubs(monkeypatch, *, unavailable_stage: int | None = None) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(preflight, "build_product_profile", lambda manifest, source_kind: _profile(unavailable_stage=unavailable_stage))
    monkeypatch.setattr(preflight, "validate_product_configuration", lambda config, manifest: [])


def test_product_preflight_freezes_source_runtime_and_profile(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _install_profile_stubs(monkeypatch)
    source = _source(tmp_path)
    project = _Project(tmp_path, [source])

    first = preflight.build_product_preflight(project)
    second = preflight.build_product_preflight(project)

    assert first["status"] == "ready"
    assert first["schema"] == preflight.PREFLIGHT_SCHEMA
    assert first["identity"]["source"]["sha256"] == source["sha256"]
    assert first["identity"]["source_kind"] == "text"
    assert first["identity"]["registry_hash"] == "registry-1"
    assert first["identity"]["core"]["rocketdict_version"] == "0.30.40"
    assert first["identity"]["fingerprint"] == second["identity"]["fingerprint"]
    assert project.probe_runtime is True
    assert first["fake_or_identity_mt_allowed"] is False
    assert first["network_required_during_processing"] is False


def test_product_preflight_rejects_mutated_immutable_source(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _install_profile_stubs(monkeypatch)
    source = _source(tmp_path)
    copied = tmp_path / source["copied_path"]
    copied.write_text("mutated", encoding="utf-8")

    with pytest.raises(RuntimeError, match="SHA changed"):
        preflight.build_product_preflight(_Project(tmp_path, [source]))


def test_product_preflight_requires_explicit_source_when_project_has_multiple(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _install_profile_stubs(monkeypatch)
    first = _source(tmp_path, "one")
    second = _source(tmp_path, "two")
    project = _Project(tmp_path, [first, second])

    with pytest.raises(RuntimeError, match="multiple imported sources"):
        preflight.build_product_preflight(project)

    selected = preflight.build_product_preflight(project, source_sha256=second["sha256"])
    assert selected["identity"]["source"]["sha256"] == second["sha256"]


def test_product_preflight_fails_closed_on_unavailable_required_stage(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _install_profile_stubs(monkeypatch, unavailable_stage=12)
    source = _source(tmp_path)

    with pytest.raises(RuntimeError, match="stage 12.*not locally available"):
        preflight.build_product_preflight(_Project(tmp_path, [source]))


def test_product_preflight_rejects_source_kind_mismatch(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _install_profile_stubs(monkeypatch)
    source = _source(tmp_path)
    with pytest.raises(RuntimeError, match="conflicts with imported"):
        preflight.build_product_preflight(_Project(tmp_path, [source]), source_kind="subtitle")


def test_product_preflight_cli_exposes_source_identity_controls() -> None:
    args = parser().parse_args([
        "product-preflight",
        "/tmp/project",
        "--source-sha256",
        "a" * 64,
        "--source-kind",
        "text",
        "--output",
        "/tmp/preflight.json",
    ])
    assert args.command == "product-preflight"
    assert args.source_sha256 == "a" * 64
    assert args.source_kind == "text"
    assert args.output == Path("/tmp/preflight.json")
