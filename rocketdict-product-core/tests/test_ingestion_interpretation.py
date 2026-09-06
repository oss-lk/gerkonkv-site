from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from rocketdict.database import bootstrap_database, connect, database_path, project_summary
from rocketdict.importing.cli import import_source
from rocketdict.interpretation.cli import interpret_source


def test_database_import_and_txt_interpretation_are_durable_and_idempotent(tmp_path: Path) -> None:
    data = tmp_path / "data"
    source = tmp_path / "sample.txt"
    source.write_text("First sentence.\nSecond sentence 42.\n", encoding="utf-8")

    db = database_path(data)
    handle = bootstrap_database(db)
    handle.dispose()
    first_import = import_source(source, data_root=data)
    second_import = import_source(source, data_root=data)
    assert first_import["import_event_id"] == second_import["import_event_id"]
    assert first_import["cache_hit"] is False
    assert second_import["cache_hit"] is True
    assert first_import["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()

    first = interpret_source(
        int(first_import["import_event_id"]), data_root=data, declared_format="txt"
    )
    second = interpret_source(
        int(first_import["import_event_id"]), data_root=data, declared_format="txt"
    )
    assert first["document_version_id"] == second["document_version_id"]
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert first["selected_format"] == "txt"
    assert first["segment_count"] == 1

    with connect(db, readonly=True) as connection:
        row = connection.execute("SELECT * FROM document_versions").fetchone()
        assert row is not None
        assert row["content_text"] == source.read_text(encoding="utf-8")
        segment = connection.execute("SELECT * FROM document_segments").fetchone()
        assert segment["start_char"] == 0
        assert segment["end_char"] == len(row["content_text"])

    summary = project_summary(db)
    assert summary["import_event_count"] == 1
    assert summary["document_version_count"] == 1


def test_immutable_object_conflict_is_never_overwritten(tmp_path: Path) -> None:
    data = tmp_path / "data"
    source = tmp_path / "sample.txt"
    source.write_text("immutable", encoding="utf-8")
    imported = import_source(source, data_root=data)
    object_path = data / str(imported["object_path"])
    object_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(RuntimeError, match="different bytes"):
        import_source(source, data_root=data)


def test_srt_preserves_cue_times_and_never_degrades_to_txt(tmp_path: Path) -> None:
    data = tmp_path / "data"
    source = tmp_path / "sample.srt"
    source.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nHello <i>world</i>.\n\n"
        "2\n00:00:03,000 --> 00:00:05,000\nNumber 42.\n",
        encoding="utf-8",
    )
    imported = import_source(source, data_root=data)
    result = interpret_source(
        int(imported["import_event_id"]), data_root=data, declared_format="srt"
    )
    assert result["selected_format"] == "srt"
    assert result["segment_count"] == 2
    with connect(database_path(data), readonly=True) as connection:
        rows = connection.execute(
            "SELECT * FROM document_segments ORDER BY sequence_number"
        ).fetchall()
    assert [(r["start_ms"], r["end_ms"], r["text"]) for r in rows] == [
        (1000, 2500, "Hello world."),
        (3000, 5000, "Number 42."),
    ]


def test_invalid_subtitle_is_rejected_instead_of_silent_text_fallback(tmp_path: Path) -> None:
    data = tmp_path / "data"
    source = tmp_path / "bad.srt"
    source.write_text("this is not an SRT cue", encoding="utf-8")
    imported = import_source(source, data_root=data)
    with pytest.raises(RuntimeError, match="Invalid SRT"):
        interpret_source(
            int(imported["import_event_id"]), data_root=data, declared_format="srt"
        )


def test_vtt_and_ass_are_interpreted_with_durable_offsets(tmp_path: Path) -> None:
    data = tmp_path / "data"
    vtt = tmp_path / "a.vtt"
    vtt.write_text(
        "WEBVTT\n\ncue-1\n00:00:01.000 --> 00:00:02.000 align:start\nOne.\n",
        encoding="utf-8",
    )
    vi = import_source(vtt, data_root=data)
    vr = interpret_source(int(vi["import_event_id"]), data_root=data, declared_format="vtt")
    assert vr["selected_format"] == "vtt"
    assert vr["segment_count"] == 1

    ass = tmp_path / "b.ass"
    ass.write_text(
        "[Script Info]\nTitle: t\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:03.50,Default,{\\i1}Hello\\Nworld{\\i0}\n",
        encoding="utf-8",
    )
    ai = import_source(ass, data_root=data)
    ar = interpret_source(int(ai["import_event_id"]), data_root=data, declared_format="ass")
    assert ar["selected_format"] == "ass"
    with connect(database_path(data), readonly=True) as connection:
        row = connection.execute(
            "SELECT * FROM document_segments WHERE document_version_id=?",
            (ar["document_version_id"],),
        ).fetchone()
    assert row["start_ms"] == 1000
    assert row["end_ms"] == 3500
    assert row["text"] == "Hello\nworld"
