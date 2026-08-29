from pathlib import Path
import os
import pytest
from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.project import WorkbenchProject

CORE = os.environ.get("ROCKETDICT_TEST_CORE")


@pytest.mark.skipif(not CORE, reason="ROCKETDICT_TEST_CORE not set")
def test_real_core_project_and_source_import(tmp_path: Path) -> None:
    core = RocketDictCore(pythonpath=[CORE])
    doctor = core.doctor()
    assert doctor.available
    assert doctor.rocketdict_version
    project = WorkbenchProject.create(tmp_path / "project", name="smoke", core=core)

    # TXT is the dependency-light smoke path. Subtitle formats are separately
    # fail-closed and require the real subtitle runtime (pysubs2 in core 0.30.34).
    source = tmp_path / "sample.txt"
    source.write_text("The glass is 5/62 inch thick.\nLook at Fig. 2.\n", encoding="utf-8")
    record = project.import_source(source)
    assert record["import"]["byte_size"] > 0
    assert record["interpretation"]["document_version_id"] > 0

    catalog = project.lab_catalog(probe_runtime=False)
    assert catalog["summary"]["stage_count"] >= 25
    assert catalog["summary"]["implementation_count"] >= 30
    config_path = project.save_default_configuration()
    assert config_path.is_file()
