from pathlib import Path
from rocketdict_workbench.project import SUPPORTED_SOURCE_SUFFIXES, paths


def test_project_layout_and_supported_subtitles(tmp_path: Path) -> None:
    p = paths(tmp_path / "p")
    assert p.database.name == "rocketdict.sqlite"
    assert {".srt", ".vtt", ".ass", ".ssa", ".txt"} <= SUPPORTED_SOURCE_SUFFIXES
