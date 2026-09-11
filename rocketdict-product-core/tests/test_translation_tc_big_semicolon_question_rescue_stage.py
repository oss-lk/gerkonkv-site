from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_semicolon_question_rescue_stage as stage
from rocketdict.translation_tc_big_semicolon_question_rescue_stage import (
    TC_BIG_SEMICOLON_QUESTION_RESCUE_CONTRACT,
    TC_BIG_SEMICOLON_QUESTION_SELECTOR_CONTRACT,
    TC_BIG_SEMICOLON_QUESTION_TRIGGER_CONTRACT,
    _base_parameters,
    _eligible_rows,
    evaluate_tc_big_semicolon_question_candidate,
    evaluate_tc_big_semicolon_question_trigger,
)


def _row(
    row_id: int,
    source: str,
    target: str,
    *,
    source_start: int = 0,
    context_start: int = 0,
    context_end: int = 0,
) -> dict[str, object]:
    return {
        "id": row_id,
        "sequence_number": row_id - 1,
        "kind": "translation_segment",
        "source_start": source_start,
        "source_end": source_start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {
            "planner": {
                "source": "nlp_sentence",
                "context_sentence_start": context_start,
                "context_sentence_end": context_end,
            }
        },
    }


def test_base_parameters_strip_only_semicolon_question_controls() -> None:
    parameters = {
        "enable_tc_big_figure_reference_rescue": True,
        "enable_tc_big_semicolon_question_rescue": True,
        "tc_big_semicolon_question_rescue_contract": TC_BIG_SEMICOLON_QUESTION_RESCUE_CONTRACT,
        "tc_big_semicolon_question_selector_contract": TC_BIG_SEMICOLON_QUESTION_SELECTOR_CONTRACT,
        "tc_big_semicolon_question_trigger_contract": TC_BIG_SEMICOLON_QUESTION_TRIGGER_CONTRACT,
    }
    assert _base_parameters(parameters) == {"enable_tc_big_figure_reference_rescue": True}


def test_trigger_requires_semicolon_loss_question_addition_terminal_period_and_exact_context() -> None:
    source = "What kind of action this is; I do not here enquire."
    broken = _row(1, source, "Что это за действие? Я здесь не спрашиваю.")
    trigger = evaluate_tc_big_semicolon_question_trigger(
        broken, exact_stage10_context=True
    )
    assert trigger["eligible"] is True
    assert trigger["source_semicolon_count"] == 1
    assert trigger["target_semicolon_count"] == 0
    assert trigger["source_question_count"] == 0
    assert trigger["target_question_count"] == 1

    assert evaluate_tc_big_semicolon_question_trigger(
        broken, exact_stage10_context=False
    )["eligible"] is False

    fragment = _row(2, "And whence is it", "И откуда это?")
    assert evaluate_tc_big_semicolon_question_trigger(
        fragment, exact_stage10_context=True
    )["eligible"] is False

    source_question = _row(3, "What is this? I enquire.", "Что это? Я спрашиваю.")
    assert evaluate_tc_big_semicolon_question_trigger(
        source_question, exact_stage10_context=True
    )["eligible"] is False


def test_candidate_restores_semicolon_and_terminal_period_without_question() -> None:
    source = "What kind of action this is; I do not here enquire."
    target = "Что это за действие; я здесь не спрашиваю."
    selection = evaluate_tc_big_semicolon_question_candidate(source, target)
    assert selection["accepted"] is True
    assert selection["strictly_eligible"] is True
    assert selection["semicolon_count_preserved"] is True
    assert selection["question_count_preserved"] is True
    assert selection["terminal_period_preserved"] is True


def test_candidate_rejects_question_semicolon_loss_or_nonterminal_period() -> None:
    source = "What kind of action this is; I do not here enquire."
    added_question = evaluate_tc_big_semicolon_question_candidate(
        source, "Что это за действие? Я здесь не спрашиваю."
    )
    assert added_question["accepted"] is False

    lost_semicolon = evaluate_tc_big_semicolon_question_candidate(
        source, "Что это за действие, я здесь не спрашиваю."
    )
    assert lost_semicolon["semicolon_count_preserved"] is False
    assert lost_semicolon["accepted"] is False

    no_terminal_period = evaluate_tc_big_semicolon_question_candidate(
        source, "Что это за действие; я здесь не спрашиваю"
    )
    assert no_terminal_period["terminal_period_preserved"] is False
    assert no_terminal_period["accepted"] is False


def test_eligible_rows_skip_non_exact_geometry() -> None:
    source = "What kind of action this is; I do not here enquire. "
    content = source + "Tail."
    row = _row(
        1,
        source,
        "Что это за действие? Я здесь не спрашиваю. ",
        source_start=0,
        context_start=0,
        context_end=0,
    )
    exact = [
        {
            "id": 100,
            "sequence_number": 0,
            "kind": "context_sentence",
            "source_start": 0,
            "source_end": len(source),
            "source_text": source,
            "target_text": "",
            "payload": {},
        }
    ]
    assert len(_eligible_rows(content=content, base_rows=[row], context_rows=exact)) == 1

    cut = [{**exact[0], "source_end": len(source) - 1, "source_text": source[:-1]}]
    assert _eligible_rows(content=content, base_rows=[row], context_rows=cut) == []


def test_disabled_run_delegates_without_tc_big_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 12, "sentinel": "base"}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "tc_big_status",
        lambda: (_ for _ in ()).throw(
            AssertionError("TC-big must not be probed while semicolon-question rescue is disabled")
        ),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_figure_reference_rescue": True,
            "enable_tc_big_semicolon_question_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_tc_big_figure_reference_rescue": True}


def test_enabled_run_persists_raw_candidate_and_exact_untouched_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    first_source = "What kind of action this is; I do not here enquire. "
    second_source = "Clean row."
    content = first_source + second_source
    first = _row(
        11,
        first_source,
        "Что это за действие? Я здесь не спрашиваю. ",
        source_start=0,
        context_start=0,
        context_end=0,
    )
    second = _row(
        12,
        second_source,
        "Чистая строка.",
        source_start=len(first_source),
        context_start=1,
        context_end=1,
    )
    context_rows = [
        {
            "id": 101,
            "sequence_number": 0,
            "kind": "context_sentence",
            "source_start": 0,
            "source_end": len(first_source),
            "source_text": first_source,
            "target_text": "",
            "payload": {},
        },
        {
            "id": 102,
            "sequence_number": 1,
            "kind": "context_sentence",
            "source_start": len(first_source),
            "source_end": len(content),
            "source_text": second_source,
            "target_text": "",
            "payload": {},
        },
    ]
    base_output = {"translation_run_id": 12, "document_version_id": 7, "model_request_count": 300}
    base_run = {"id": 12, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)

    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 12 and kind == "translation_segment":
            return [first, second]
        if int(run_id) == 2 and kind == "context_sentence":
            return context_rows
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (13, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    raw_target = "Что это за действие; я здесь не спрашиваю."

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [first_source]
            return [[
                {"rank": 0, "text": raw_target, "score": -0.1},
                {"rank": 1, "text": "Что это?", "score": -0.2},
                {"rank": 2, "text": raw_target, "score": -0.3},
                {"rank": 3, "text": raw_target, "score": -0.4},
                {"rank": 4, "text": raw_target, "score": -0.5},
                {"rank": 5, "text": raw_target, "score": -0.6},
            ]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_semicolon_question_rescue": True},
    )
    assert result["translation_run_id"] == 13
    assert result["base_translation_run_id"] == 12
    assert result["tc_big_semicolon_question_rescue_attempt_count"] == 1
    assert result["tc_big_semicolon_question_rescue_accepted_count"] == 1
    assert result["tc_big_semicolon_question_rescue_rejected_count"] == 0
    assert result["tc_big_semicolon_question_rescue_selected_ranks"] == [0]

    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    rescued, untouched = items
    assert rescued["target_text"] == raw_target
    rescue = rescued["payload"]["tc_big_semicolon_question_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescued["payload"]["hypotheses"][0]["text"] == raw_target
    assert untouched["target_text"] == second["target_text"]
    assert untouched["payload"]["tc_big_semicolon_question_rescue"]["applied"] is False
    assert "".join(str(item["source_text"]) for item in items) == content
