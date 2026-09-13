from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_combined_greek_rescue_stage as stage
from rocketdict.stages import StageExecutionError

SOURCE = "Then divide the Line _A[Greek: a]_ in such Proportion as the Numbers 1, 2, 3 denote."
BASE = "Затем разделите линию в такой пропорции, как числа 1, 2, 3 обозначают."
PREFIX_TARGET = "Тогда разделите линию"
SUFFIX_TARGET = "в таких долях, как обозначают числа 1, 2, 3."
EXPECTED = f"{PREFIX_TARGET} _A[Greek: a]_ {SUFFIX_TARGET}"


def _row(row_id: int, source: str, target: str, *, start: int = 0) -> dict[str, object]:
    return {
        "id": row_id,
        "sequence_number": row_id - 1,
        "kind": "translation_segment",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {"selected_rank": 0, "hypotheses": [{"rank": 0, "text": target}], "planner": {"source": "fixture", "split": False, "token_count": 20}},
    }


def _runtime() -> dict[str, object]:
    return {
        "available": True,
        "revision": "opus-2020-02-11",
        "source_archive_sha256": "a" * 64,
        "manifest_sha256": "b" * 64,
        "payload_tree_sha256": "c" * 64,
        "compute_type": "float32",
    }


def _patch_base(monkeypatch: pytest.MonkeyPatch, *, rows: list[dict[str, object]], content: str) -> None:
    base_output = {"translation_run_id": 59, "document_version_id": 7, "model_request_count": 600}
    base_run = {"id": 59, "output": base_output, "output_sha256": "d" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "e" * 64}
    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(stage, "get_run_items", lambda connection, run_id, *, kind: rows)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)


def test_source_plan_is_exact_and_generic() -> None:
    plan = stage.build_combined_greek_source_plan(SOURCE)
    assert plan is not None
    assert plan["prefix_source"] == "Then divide the Line"
    assert plan["left_separator_source"] == " "
    assert plan["technical_atom_source"] == "_A[Greek: a]_"
    assert plan["right_separator_source"] == " "
    assert plan["suffix_source"].startswith("in such Proportion")
    assert plan["created_before_mt"] is True
    assert plan["source_owned_technical_passthrough"] is True
    assert stage.build_combined_greek_source_plan("_A[Greek: a]_ alone") is None
    assert stage.build_combined_greek_source_plan("x _A[Greek: a]_ y _B[Greek: b]_ z") is None


def test_trigger_requires_lost_combined_atom_and_exact_source() -> None:
    row = _row(1, SOURCE, BASE)
    trigger = stage.evaluate_combined_greek_trigger(row, source_exact=True)
    assert trigger["eligible"] is True
    assert trigger["corpus_sequence_whitelist"] is False
    assert trigger["source_start_whitelist"] is False
    assert trigger["source_combined"] == [["A", "a"]]
    preserved = _row(2, SOURCE, EXPECTED)
    assert stage.evaluate_combined_greek_trigger(preserved, source_exact=True)["eligible"] is False
    assert stage.evaluate_combined_greek_trigger(row, source_exact=False)["eligible"] is False


def test_candidate_requires_strict_lexical_and_aggregate_preservation() -> None:
    plan = stage.build_combined_greek_source_plan(SOURCE)
    assert plan is not None
    good = stage.evaluate_combined_greek_candidate(SOURCE, base_target=BASE, plan=plan, prefix_target=PREFIX_TARGET, suffix_target=SUFFIX_TARGET)
    assert good["accepted"] is True
    assert good["candidate_target"] == EXPECTED
    assert good["aggregate_verdict"]["strictly_eligible"] is True
    assert good["aggregate_emphasis_markup"]["passed"] is True
    assert good["aggregate_critical_technical_tokens"]["passed"] is True
    bad = stage.evaluate_combined_greek_candidate(SOURCE, base_target=BASE, plan=plan, prefix_target=PREFIX_TARGET, suffix_target="в таких долях, как обозначают числа 1, 2.")
    assert bad["accepted"] is False


def test_default_off_delegates_without_runtime_probe(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    expected = {"translation_run_id": 59}
    observed: dict[str, object] = {}
    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected
    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(stage, "opus_status", lambda: (_ for _ in ()).throw(AssertionError("runtime probe")))
    result = stage.run_stage12(tmp_path / "rocketdict.sqlite", context_run_id=2, parameters={"enable_m2m100_arithmetic_rescue": True, "enable_combined_greek_source_plan_rescue": False})
    assert result is expected
    assert observed["parameters"] == {"enable_m2m100_arithmetic_rescue": True}


def test_enabled_run_persists_one_source_planned_semantic_carrier(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    clean_source = "Clean row."
    clean_target = "Чистая строка."
    rows = [_row(31, SOURCE, BASE), _row(32, clean_source, clean_target, start=len(SOURCE))]
    _patch_base(monkeypatch, rows=rows, content=SOURCE + clean_source)
    monkeypatch.setattr(stage, "opus_status", lambda: dict(_runtime()))
    captured_identity: dict[str, object] = {}
    def fake_start(database, *, stage_number, implementation, input_identity, parameters):  # type: ignore[no-untyped-def]
        captured_identity.update(input_identity)
        return 60, None
    monkeypatch.setattr(stage, "_start", fake_start)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    completed: dict[str, object] = {}
    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output
    monkeypatch.setattr(stage, "_complete", fake_complete)
    observed: dict[str, object] = {}
    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"
        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            observed["texts"] = list(texts)
            return [
                [{"rank": 0, "text": PREFIX_TARGET, "tokens": ["prefix"], "score": -0.1}],
                [{"rank": 0, "text": SUFFIX_TARGET, "tokens": ["suffix"], "score": -0.2}],
            ]
    monkeypatch.setattr(stage, "OpusTranslator", FakeTranslator)
    result = stage.run_stage12(tmp_path / "rocketdict.sqlite", context_run_id=2, parameters={"enable_combined_greek_source_plan_rescue": True})
    assert result["translation_run_id"] == 60
    assert result["base_translation_run_id"] == 59
    assert result["combined_greek_source_plan_rescue_attempt_count"] == 1
    assert result["combined_greek_source_plan_rescue_accepted_count"] == 1
    assert result["combined_greek_source_plan_rescue_model_request_count"] == 2
    assert observed["texts"] == ["Then divide the Line", "in such Proportion as the Numbers 1, 2, 3 denote."]
    assert captured_identity["base_translation_run_id"] == 59
    assert captured_identity["combined_greek_opus_runtime_identity"]["payload_tree_sha256"] == "c" * 64
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["source_text"] == SOURCE and items[0]["target_text"] == EXPECTED
    rescue = items[0]["payload"]["combined_greek_source_plan_rescue"]
    assert rescue["rendering"] == "source_planned_semantic_carrier"
    assert rescue["source_plan"]["created_before_mt"] is True
    assert rescue["source_plan"]["pieces"][2]["source_owned"] is True
    assert rescue["source_plan"]["pieces"][2]["rendered_text"] == "_A[Greek: a]_"
    assert rescue["post_translation_literal_injection"] is False
    assert items[1]["target_text"] == clean_target
    assert items[1]["payload"]["combined_greek_source_plan_rescue"]["applied"] is False
    assert "".join(str(item["source_text"]) for item in items) == SOURCE + clean_source


def test_rejected_candidate_leaves_base_exact(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    row = _row(41, SOURCE, BASE)
    _patch_base(monkeypatch, rows=[row], content=SOURCE)
    monkeypatch.setattr(stage, "opus_status", lambda: dict(_runtime()))
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (60, None))
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    completed: dict[str, object] = {}
    monkeypatch.setattr(stage, "_complete", lambda database, run_id, output, *, items: completed.setdefault("items", items) or output)
    class BadTranslator:
        def __init__(self, **kwargs) -> None: pass  # type: ignore[no-untyped-def]
        def translate(self, texts, **kwargs):  # type: ignore[no-untyped-def]
            return [
                [{"rank": 0, "text": PREFIX_TARGET, "tokens": ["prefix"], "score": -0.1}],
                [{"rank": 0, "text": "в таких долях, как числа 1, 2.", "tokens": ["bad"], "score": -0.2}],
            ]
    monkeypatch.setattr(stage, "OpusTranslator", BadTranslator)
    result = stage.run_stage12(tmp_path / "rocketdict.sqlite", context_run_id=2, parameters={"enable_combined_greek_source_plan_rescue": True})
    assert result["combined_greek_source_plan_rescue_accepted_count"] == 0
    assert result["combined_greek_source_plan_rescue_rejected_count"] == 1
    items = completed["items"]
    assert items[0]["target_text"] == BASE


def test_controls_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    with pytest.raises(StageExecutionError, match="must be boolean"):
        stage.run_stage12(tmp_path / "rocketdict.sqlite", context_run_id=2, parameters={"enable_combined_greek_source_plan_rescue": "yes"})
    with pytest.raises(StageExecutionError, match="Unsupported combined Greek rescue contract"):
        stage.run_stage12(tmp_path / "rocketdict.sqlite", context_run_id=2, parameters={"enable_combined_greek_source_plan_rescue": True, "combined_greek_source_plan_rescue_contract": "wrong"})
    with pytest.raises(StageExecutionError, match="internal"):
        stage.run_stage12(tmp_path / "rocketdict.sqlite", context_run_id=2, parameters={"enable_combined_greek_source_plan_rescue": True, "combined_greek_source_plan_rescue_phase": "wrong"})
