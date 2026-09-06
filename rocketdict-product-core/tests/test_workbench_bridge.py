from __future__ import annotations

from pathlib import Path
import sys

import pytest

from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_preflight import build_product_preflight
from rocketdict_workbench.project import WorkbenchProject


def test_workbench_can_create_project_import_source_and_read_live_registry(tmp_path: Path) -> None:
    core = RocketDictCore(python=sys.executable)
    doctor = core.doctor()
    assert doctor.available is True
    assert doctor.rocketdict_version == "1.0.0.dev1"
    assert doctor.api_version == "rocketdict-product-core/1"

    project = WorkbenchProject.create(tmp_path / "project", name="core-bridge", core=core)
    source = tmp_path / "sample.txt"
    source.write_text("Light passes through glass 42 times.\n", encoding="utf-8")
    imported = project.import_source(source)
    assert imported["interpretation"]["selected_format"] == "txt"
    assert int(imported["interpretation"]["document_version_id"]) > 0

    status = project.status(probe_runtime=True)
    assert status["core"]["available"] is True
    assert status["core_project"]["import_event_count"] == 1
    assert status["core_project"]["document_version_count"] == 1
    assert status["lab_summary"]["stage_count"] == 13


def test_dependency_light_preflight_refuses_missing_real_nlp_or_opus(tmp_path: Path, monkeypatch) -> None:
    # The core must never make dependency-light CI look like a product-ready
    # machine. In particular, absence of the verified OPUS asset is a hard
    # preflight blocker rather than a fake/identity translation fallback.
    monkeypatch.delenv("ROCKETDICT_OPUS_ASSET_DIR", raising=False)
    core = RocketDictCore(python=sys.executable)
    project = WorkbenchProject.create(tmp_path / "project", name="preflight", core=core)
    source = tmp_path / "sample.txt"
    source.write_text("A real translation is required.\n", encoding="utf-8")
    project.import_source(source)

    with pytest.raises(RuntimeError, match="not locally available") as error:
        build_product_preflight(project)
    message = str(error.value)
    assert "stage 8" in message or "stage 12" in message
