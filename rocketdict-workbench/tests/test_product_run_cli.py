from __future__ import annotations

import json
from pathlib import Path

import rocketdict_workbench.product_run_cli as product_cli


def _completed_record() -> dict:
    return {"status": "completed"}


def _state(*, stage19: bool = True, downstream_status: str = "pending") -> dict:
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
        executions["19"] = _completed_record()
    return {
        "steps": {
            "upstream_execution": {"executions": executions},
            "stage20_downstream": {"status": downstream_status},
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
        "--model-path",
        "/tmp/opus",
        "--cefrj-asset",
        "/tmp/cefr.csv",
        "--max-new-cards",
        "1000",
    ])
    assert advance.command == "advance"
    assert advance.model_path == Path("/tmp/opus")
    assert advance.cefrj_asset == Path("/tmp/cefr.csv")
    assert advance.max_new_cards == 1000

    status = product_cli.parser().parse_args([
        "status",
        "/tmp/project",
        "--state",
        "/tmp/run.json",
    ])
    assert status.command == "status"


def test_advance_reports_exact_model_asset_blocker_after_stage19(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True, downstream_status="pending"))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})

    result = product_cli.advance_product_run(object(), database, state_path)

    assert result["status"] == "blocked"
    assert result["blocked_phase"] == "stage20"
    assert result["required"] == "--model-path"
    assert result["reason"] == "pinned_offline_opus_model_path_required"
    assert result["checkpoints"] == []


def test_advance_reports_cefr_asset_blocker_after_completed_stage20(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True, downstream_status="stage20_completed"))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})

    result = product_cli.advance_product_run(object(), database, state_path, model_path=tmp_path / "unused")

    assert result["status"] == "blocked"
    assert result["blocked_phase"] == "stage20_through_stage23"
    assert result["required"] == "--cefrj-asset"
    assert result["reason"] == "pinned_cefrj_1_5_asset_required"


def test_advance_resumes_post_gate_when_stage19_missing(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=False, downstream_status="pending"))
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


def test_advance_passes_card_batch_limit_to_final_pipeline(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True, downstream_status="completed_through_stage23"))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})
    observed = {}

    def final(core, db, path, *, set_name, max_new_cards):  # type: ignore[no-untyped-def]
        observed["set_name"] = set_name
        observed["max_new_cards"] = max_new_cards
        return {"status": "stage24_partial", "completed_card_count": 500}

    monkeypatch.setattr(product_cli, "advance_final_product", final)
    result = product_cli.advance_product_run(
        object(),
        database,
        state_path,
        set_name="My dictionary",
        max_new_cards=500,
    )

    assert observed == {"set_name": "My dictionary", "max_new_cards": 500}
    assert result["status"] == "progressed"
    assert result["checkpoints"][-1]["phase"] == "stage24_25"


def test_advance_can_finish_product_from_completed_stage23(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = _write(tmp_path, _state(stage19=True, downstream_status="completed_through_stage23"))
    monkeypatch.setattr(product_cli, "require_quality_gate_pass", lambda path: {"status": "passed"})
    monkeypatch.setattr(
        product_cli,
        "advance_final_product",
        lambda *args, **kwargs: {"status": "product_complete_exported", "export": {"export_run_id": 25}},
    )

    result = product_cli.advance_product_run(object(), database, state_path)

    assert result["status"] == "product_complete_exported"
    assert result["checkpoints"][-1]["result"]["export"]["export_run_id"] == 25
