from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_question_context_rescue_stage as stage
from rocketdict.translation_question_context_rescue_stage import (
    MAX_CONTEXT_NLP_TOKENS,
    QUESTION_CONTEXT_RESCUE_CONTRACT,
    QUESTION_CONTEXT_SELECTOR_CONTRACT,
    QUESTION_CONTEXT_TRIGGER_CONTRACT,
    _base_parameters,
    evaluate_question_context_candidate,
    evaluate_question_context_trigger,
)


def _row(
    row_id: int,
    source: str,
    target: str,
    *,
    source_start: int,
    context_sequence: int = 0,
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
                "context_sentence_start": context_sequence,
                "context_sentence_end": context_sequence,
                "context_sentence_count": 1,
                "split": True,
                "token_count": 10,
                "planner_contract": "rocketdict-stage12-protected-split/8",
            }
        },
    }


def _context(source: str, *, sequence: int = 0, token_count: int = 20) -> dict[str, object]:
    return {
        "id": 100 + sequence,
        "sequence_number": sequence,
        "kind": "context_sentence",
        "source_start": 0,
        "source_end": len(source),
        "source_text": source,
        "target_text": "",
        "payload": {"sentence_index": sequence, "token_count": token_count},
    }


def _good_fixture() -> tuple[str, dict[str, object], list[dict[str, object]]]:
    first_source = "When coal moves around a circle, "
    second_source = "does it return home? "
    source = first_source + second_source
    rows = [
        _row(1, first_source, "Когда уголь движется по кругу? ", source_start=0),
        _row(
            2,
            second_source,
            "возвращается ли он домой? ",
            source_start=len(first_source),
        ),
    ]
    return source, _context(source), rows


def test_base_parameters_strip_only_question_context_controls() -> None:
    parameters = {
        "enable_tc_big_orphan_closing_parenthesis_rescue": True,
        "enable_question_mark_whole_context_rescue": True,
        "question_mark_whole_context_rescue_contract": QUESTION_CONTEXT_RESCUE_CONTRACT,
        "question_mark_whole_context_selector_contract": QUESTION_CONTEXT_SELECTOR_CONTRACT,
        "question_mark_whole_context_trigger_contract": QUESTION_CONTEXT_TRIGGER_CONTRACT,
        "question_mark_whole_context_max_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
    }
    assert _base_parameters(parameters) == {
        "enable_tc_big_orphan_closing_parenthesis_rescue": True
    }


def test_trigger_accepts_only_bounded_isolated_premature_question_shape() -> None:
    source, context, rows = _good_fixture()
    trigger = evaluate_question_context_trigger(
        content=source,
        context=context,
        primary_rows=rows,
    )
    assert trigger["eligible"] is True
    assert trigger["source_single_terminal_question"] is True
    assert trigger["aggregate_source_question_marks"] == 1
    assert trigger["aggregate_target_question_marks"] == 2
    assert trigger["premature_target_question_sequences"] == [0]
    assert trigger["punctuation_failure_count"] == 1
    assert trigger["within_context_nlp_token_cap"] is True

    over_cap = {**context, "payload": {"sentence_index": 0, "token_count": 161}}
    assert evaluate_question_context_trigger(
        content=source,
        context=over_cap,
        primary_rows=rows,
    )["eligible"] is False

    missing_terminal = [
        rows[0],
        {**rows[1], "target_text": "возвращается ли он домой. "},
    ]
    assert evaluate_question_context_trigger(
        content=source,
        context=context,
        primary_rows=missing_terminal,
    )["eligible"] is False


def test_trigger_rejects_other_hard_punctuation_debt() -> None:
    source, context, rows = _good_fixture()
    broken = [
        {**rows[0], "target_text": "(Когда уголь движется по кругу? "},
        rows[1],
    ]
    trigger = evaluate_question_context_trigger(
        content=source,
        context=context,
        primary_rows=broken,
    )
    assert trigger["member_non_question_punctuation_exact"] is False
    assert trigger["eligible"] is False


def test_candidate_accepts_clean_rank0_without_alpha_loss() -> None:
    source = "When coal moves around a circle, does it return home?"
    primary = "Когда уголь движется по кругу? возвращается ли он домой?"
    target = "Когда уголь движется по кругу, возвращается ли он домой?"
    selection = evaluate_question_context_candidate(
        source,
        target,
        primary_target=primary,
    )
    assert selection["accepted"] is True
    assert selection["strictly_eligible"] is True
    assert selection["hard_punctuation_exact"] is True
    assert selection["emphasis_markup"]["passed"] is True
    assert selection["target_alpha_non_decreasing"] is True


def test_candidate_rejects_extra_question_and_emphasis_geometry_change() -> None:
    source = "When coal moves around a circle, does it return home?"
    primary = "Когда уголь движется по кругу? возвращается ли он домой?"
    extra = evaluate_question_context_candidate(
        source,
        "Когда уголь движется по кругу? возвращается ли он домой?",
        primary_target=primary,
    )
    assert extra["hard_punctuation_exact"] is False
    assert extra["accepted"] is False

    emphasis_source = "Does _A_ compare with _B?"
    emphasis = evaluate_question_context_candidate(
        emphasis_source,
        "Сравнивается ли _A_ с _B_?",
        primary_target="Сравнивается ли _A_ с _B_?",
    )
    assert emphasis["emphasis_markup"]["passed"] is False
    assert emphasis["accepted"] is False


def test_disabled_run_delegates_without_opus_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 18}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "OpusTranslator",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("OPUS runtime must not be constructed")
        ),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_orphan_closing_parenthesis_rescue": True,
            "enable_question_mark_whole_context_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {
        "enable_tc_big_orphan_closing_parenthesis_rescue": True
    }


def test_enabled_run_persists_raw_rank0_and_merges_only_accepted_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    source, context, rows = _good_fixture()
    base_output = {
        "translation_run_id": 18,
        "document_version_id": 7,
        "model_request_count": 500,
    }
    base_run = {"id": 18, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": source, "text_sha256": "b" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)

    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 18 and kind == "translation_segment":
            return rows
        if int(run_id) == 2 and kind == "context_sentence":
            return [context]
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (19, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    raw_target = "Когда уголь движется по кругу, возвращается ли он домой?"

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [source]
            assert beam_size == 6 and num_hypotheses == 1
            return [[{"rank": 0, "text": raw_target, "score": -0.1}]]

    monkeypatch.setattr(stage, "OpusTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_question_mark_whole_context_rescue": True},
    )
    assert result["translation_run_id"] == 19
    assert result["base_translation_run_id"] == 18
    assert result["question_mark_whole_context_rescue_attempt_count"] == 1
    assert result["question_mark_whole_context_rescue_accepted_count"] == 1
    assert result["question_mark_whole_context_rescue_rejected_count"] == 0
    assert result["question_mark_whole_context_rescue_accepted_context_sequences"] == [0]
    assert result["question_mark_whole_context_rescue_selected_ranks"] == [0]
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 1
    assert items[0]["source_text"] == source
    assert items[0]["target_text"] == raw_target
    rescue = items[0]["payload"]["question_mark_whole_context_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["raw_model_rank"] == 0
    assert rescue["base_translation_segment_ids"] == [1, 2]
    assert items[0]["payload"]["hypotheses"][0]["text"] == raw_target
