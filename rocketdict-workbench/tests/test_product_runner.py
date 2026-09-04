from __future__ import annotations

import json

import pytest

import rocketdict_workbench.product_runner as runner


def _provider(sha: str = "a" * 64) -> dict:
    return {"entries_sha256": sha, "snapshot": {"entries": {"plane": [{"translation": "плоскость"}]}}}


def _stage20() -> dict:
    return {
        "results": [
            {
                "sense_id": 17,
                "entry_id": 4,
                "selection_revision_id": 31,
                "generation_run_id": 8,
                "normalized_lemma": "plane",
            }
        ]
    }


def _install_success_stubs(monkeypatch, calls: dict[str, int], *, example_revision: int = 44) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        runner,
        "verify_cefrj_asset",
        lambda path: {"sha256": "b" * 64, "path": str(path)},
    )

    def arbitration(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["arbitration"] += 1
        return {
            "policy": "lexical-primary-arbitration-v1",
            "results": [
                {
                    "sense_id": 17,
                    "selection_revision_id": 44,
                    "translation": "плоскость",
                    "status": "approved",
                }
            ],
        }

    def cefr(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["cefr"] += 1
        return {"source_sha256": "b" * 64, "results": [{"sense_id": 17, "approval_status": "approved"}]}

    def pronunciation(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["pronunciation"] += 1
        return {
            "generated_fallback_allowed": False,
            "results": [{"entry_id": 4, "unknown": False, "generated_fallback": False, "approval_status": "approved"}],
        }

    def examples(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["examples"] += 1
        return {
            "scope_contract": "stage23-sense-scope-v2",
            "results": [
                {
                    "sense_id": 17,
                    "approved_sense_translation_revision_id": example_revision,
                    "approval_status": "approved",
                }
            ],
        }

    monkeypatch.setattr(runner, "arbitrate_lexical_primaries", arbitration)
    monkeypatch.setattr(runner, "assess_product_cefr", cefr)
    monkeypatch.setattr(runner, "generate_product_pronunciations", pronunciation)
    monkeypatch.setattr(runner, "select_product_examples", examples)


def test_downstream_runner_persists_and_resumes_completed_steps(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls = {"arbitration": 0, "cefr": 0, "pronunciation": 0, "examples": 0}
    _install_success_stubs(monkeypatch, calls)
    state_path = tmp_path / "product-run.json"

    first = runner.resume_product_downstream(
        object(),
        tmp_path / "rocketdict.sqlite",
        _provider(),
        _stage20(),
        cefrj_asset=tmp_path / "cefr.csv",
        state_path=state_path,
    )
    assert first["status"] == "completed"
    assert first["cache_hits"] == {
        "stage20_arbitration": False,
        "cefrj": False,
        "pronunciation": False,
        "examples": False,
    }
    assert calls == {"arbitration": 1, "cefr": 1, "pronunciation": 1, "examples": 1}

    second = runner.resume_product_downstream(
        object(),
        tmp_path / "rocketdict.sqlite",
        _provider(),
        _stage20(),
        cefrj_asset=tmp_path / "cefr.csv",
        state_path=state_path,
    )
    assert second["cache_hits"] == {
        "stage20_arbitration": True,
        "cefrj": True,
        "pronunciation": True,
        "examples": True,
    }
    assert calls == {"arbitration": 1, "cefr": 1, "pronunciation": 1, "examples": 1}
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["schema"] == runner.STATE_SCHEMA
    assert saved["status"] == "completed"
    assert all(saved["steps"][name]["status"] == "completed" for name in runner.STEP_ORDER)


def test_downstream_runner_rejects_state_reuse_for_different_provider(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls = {"arbitration": 0, "cefr": 0, "pronunciation": 0, "examples": 0}
    _install_success_stubs(monkeypatch, calls)
    state_path = tmp_path / "product-run.json"
    runner.resume_product_downstream(
        object(), tmp_path / "db.sqlite", _provider(), _stage20(),
        cefrj_asset=tmp_path / "cefr.csv", state_path=state_path,
    )
    with pytest.raises(RuntimeError, match="different immutable inputs"):
        runner.resume_product_downstream(
            object(), tmp_path / "db.sqlite", _provider("c" * 64), _stage20(),
            cefrj_asset=tmp_path / "cefr.csv", state_path=state_path,
        )


def test_downstream_runner_fails_on_stage23_revision_drift(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls = {"arbitration": 0, "cefr": 0, "pronunciation": 0, "examples": 0}
    _install_success_stubs(monkeypatch, calls, example_revision=45)
    state_path = tmp_path / "product-run.json"
    with pytest.raises(RuntimeError, match="Stage23 review identity drift"):
        runner.resume_product_downstream(
            object(), tmp_path / "db.sqlite", _provider(), _stage20(),
            cefrj_asset=tmp_path / "cefr.csv", state_path=state_path,
        )
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["status"] == "failed"
    assert saved["steps"]["examples"]["status"] == "failed"
    assert saved["steps"]["stage20_arbitration"]["status"] == "completed"
    assert saved["steps"]["cefrj"]["status"] == "completed"
    assert saved["steps"]["pronunciation"]["status"] == "completed"


def test_stage20_identity_rejects_duplicate_senses() -> None:
    duplicated = _stage20()
    duplicated["results"] = [*duplicated["results"], dict(duplicated["results"][0], entry_id=5)]
    with pytest.raises(RuntimeError, match="Duplicate Stage20 sense id"):
        runner._stage20_identity(duplicated)
