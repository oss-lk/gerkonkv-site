from __future__ import annotations

import json
from pathlib import Path

import rocketdict_workbench.product_run_cli as product_cli


def _completed_record(result: dict | None = None) -> dict:
    row = {"status": "completed"}
    if result is not None:
        row["result"] = result
    return row


def _state(*, stage19: bool = True) -> dict:
    executions = {
        "8": _completed_record(),
        "10": _completed_record(),
        "12": _completed_record(),
        "14": _completed_record(),
        "16": _completed_record(),
        "17": _completed_record(),
        "18": _completed_record(),
    }
    if stage19:
        executions["19"] = _completed_record({"sense_induction_run_id": 190})
    return {
        "steps": {
            "upstream_execution": {"executions": executions},
            "stage20_downstream": {"status": "pending"},
        }
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_product_run_cli_parser_exposes_init_advance_and_status() -> None:
    init = product_cli.parser().parse_args([
        "init",
        "/tmp/project",
        "--source-sha256",
        "a" * 64,
        "--source-kind",
        "text",
        "--state",
        "/tmp/run.json",
    ])
    assert init.command == "init"
    assert init.source_sha256 == "a" * 64
    assert init.source_kind == "text"
    assert init.state == Path("/tmp/run.json")

    advance = product_cli.parser().parse_args([
        "advance",
        "/tmp/project",
        "--state",
        "/tmp/run.json",
        "--opus-asset",
        "/tmp/opus",
        "--cefrj-asset",
        "/tmp/cefr.csv",
        "--max-new-cards",
        "1000",
    ])
    assert advance.command == "advance"
    assert advance.opus_asset == Path("/tmp/opus")
    assert advance.cefrj_asset == Path("/tmp/cefr.csv")
    assert advance.max_new_cards == 1000

    legacy = product_cli.parser().parse_args([
        "advance",
        "/tmp/project",
        "--state",
        "/tmp/run.json",
        "--model-path",
        "/tmp/legacy-opus",
    ])
    assert legacy.opus_asset == Path("/tmp/legacy-opus")

    status = product_cli.parser().parse_args([
        "status",
        "/tmp/project",
        "--state",
        "/tmp/run.json",
    ])
    assert status.command == "status"


def test_advance_delegates_stage20_25_to_maintained_pipeline(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})
    observed = {}

    def maintained(core, db, path, **kwargs):  # type: ignore[no-untyped-def]
        observed.update(kwargs)
        assert db == database.resolve()
        assert path == state_path.resolve()
        return {
            "status": "product_complete_exported",
            "export": {"export_run_id": 25, "export_sha256": "a" * 64},
        }

    monkeypatch.setattr(product_cli, "advance_maintained_downstream", maintained)
    result = product_cli.advance_product_run(
        object(),
        database,
        state_path,
        opus_asset=tmp_path / "opus",
        cefrj_asset=tmp_path / "cefr.csv",
        set_name="My dictionary",
        max_new_cards=500,
    )

    assert result["status"] == "product_complete_exported"
    assert result["export"]["export_run_id"] == 25
    assert result["checkpoints"][-1]["phase"] == "maintained_stage20_25"
    assert observed["opus_asset"] == tmp_path / "opus"
    assert observed["cefrj_asset"] == tmp_path / "cefr.csv"
    assert observed["set_name"] == "My dictionary"
    assert observed["max_new_cards"] == 500


def test_advance_preserves_legacy_model_path_as_opus_asset_alias(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})
    observed = {}

    def maintained(core, db, path, **kwargs):  # type: ignore[no-untyped-def]
        observed.update(kwargs)
        return {"status": "blocked", "blocked_phase": "stage21", "required": "cefr", "reason": "missing"}

    monkeypatch.setattr(product_cli, "advance_maintained_downstream", maintained)
    legacy = tmp_path / "legacy-opus"
    result = product_cli.advance_product_run(object(), database, state_path, model_path=legacy)

    assert observed["opus_asset"] == legacy
    assert result["status"] == "blocked"
    assert result["blocked_phase"] == "stage21"


def test_advance_resumes_post_gate_when_stage19_missing(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=False))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})
    calls = []

    def post(core, db, path):  # type: ignore[no-untyped-def]
        calls.append("post")
        return {"status": "blocked", "blocked_stage": 16}

    monkeypatch.setattr(product_cli, "advance_post_gate_pipeline", post)
    result = product_cli.advance_product_run(object(), database, state_path)

    assert calls == ["post"]
    assert result["status"] == "blocked"
    assert result["blocked_phase"] == "post_gate"


def test_advance_maps_maintained_partial_cards_to_progressed(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})
    monkeypatch.setattr(
        product_cli,
        "advance_maintained_downstream",
        lambda *args, **kwargs: {"status": "progressed", "checkpoints": [{"phase": "stage24", "completed": 500}]},
    )

    result = product_cli.advance_product_run(object(), database, state_path, max_new_cards=500)

    assert result["status"] == "progressed"
    assert result["blocked_phase"] is None
    assert result["checkpoints"][-1]["phase"] == "maintained_stage20_25"


def test_advance_surfaces_maintained_asset_blocker(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})
    monkeypatch.setattr(
        product_cli,
        "advance_maintained_downstream",
        lambda *args, **kwargs: {
            "status": "blocked",
            "blocked_phase": "stage20",
            "required": "--opus-asset or ROCKETDICT_OPUS_ASSET_DIR",
            "reason": "verified_offline_opus_asset_required",
        },
    )

    result = product_cli.advance_product_run(object(), database, state_path)

    assert result["status"] == "blocked"
    assert result["blocked_phase"] == "stage20"
    assert "ROCKETDICT_OPUS_ASSET_DIR" in result["required"]
