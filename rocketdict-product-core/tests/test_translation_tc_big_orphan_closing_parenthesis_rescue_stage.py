from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_orphan_closing_parenthesis_rescue_stage as stage
from rocketdict.translation_tc_big_orphan_closing_parenthesis_rescue_stage import (
    BEAM_SIZE,
    DEFAULT_ENABLED,
    NUM_HYPOTHESES,
    TC_BIG_ORPHAN_CLOSING_PAREN_RESCUE_CONTRACT,
    TC_BIG_ORPHAN_CLOSING_PAREN_SELECTOR_CONTRACT,
    TC_BIG_ORPHAN_CLOSING_PAREN_TRIGGER_CONTRACT,
    _base_parameters,
    _eligible_rows,
    evaluate_tc_big_orphan_closing_parenthesis_candidate,
    evaluate_tc_big_orphan_closing_parenthesis_trigger,
)


def _row(
    row_id: int,
    source: str,
    target: str,
    *,
    source_start: int = 0,
    split: bool = True,
    planner_source: str = "nlp_sentence",
    context_start: int = 7,
    context_end: int = 7,
    context_count: int = 1,
    token_count: int = 8,
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
                "source": planner_source,
                "split": split,
                "context_sentence_start": context_start,
                "context_sentence_end": context_end,
                "context_sentence_count": context_count,
                "token_count": token_count,
            }
        },
    }


def test_contract_is_default_off_rank0_only_and_strips_only_own_controls() -> None:
    assert DEFAULT_ENABLED is False
    assert BEAM_SIZE == 6
    assert NUM_HYPOTHESES == 1
    parameters = {
        "enable_tc_big_boundary_pair_punctuation_rescue": True,
        "enable_tc_big_orphan_closing_parenthesis_rescue": True,
        "tc_big_orphan_closing_parenthesis_rescue_contract": (
            TC_BIG_ORPHAN_CLOSING_PAREN_RESCUE_CONTRACT
        ),
        "tc_big_orphan_closing_parenthesis_selector_contract": (
            TC_BIG_ORPHAN_CLOSING_PAREN_SELECTOR_CONTRACT
        ),
        "tc_big_orphan_closing_parenthesis_trigger_contract": (
            TC_BIG_ORPHAN_CLOSING_PAREN_TRIGGER_CONTRACT
        ),
    }
    assert _base_parameters(parameters) == {
        "enable_tc_big_boundary_pair_punctuation_rescue": True
    }


def test_trigger_accepts_only_exact_single_sentence_split_orphan_close() -> None:
    source = "The ratio of the same rings is 3 to 4."
    broken = _row(1, source, "Отношение тех же колец равно 3 к 4.)")
    trigger = evaluate_tc_big_orphan_closing_parenthesis_trigger(
        broken, source_exact=True
    )
    assert trigger["eligible"] is True
    assert trigger["split_fragment"]["eligible"] is True
    assert trigger["source_contains_no_parentheses"] is True
    assert trigger["target_orphan_closing_parenthesis_count"] == 1
    assert trigger["numeric_symbol_clean"] is True
    assert trigger["other_hard_punctuation_exact"] is True

    assert evaluate_tc_big_orphan_closing_parenthesis_trigger(
        broken, source_exact=False
    )["eligible"] is False
    assert evaluate_tc_big_orphan_closing_parenthesis_trigger(
        _row(2, source, "Отношение тех же колец равно 3 к 4.)", split=False),
        source_exact=True,
    )["eligible"] is False
    assert evaluate_tc_big_orphan_closing_parenthesis_trigger(
        _row(
            3,
            source,
            "Отношение тех же колец равно 3 к 4.)",
            context_start=7,
            context_end=8,
            context_count=2,
        ),
        source_exact=True,
    )["eligible"] is False


def test_trigger_rejects_balanced_parentheses_source_parentheses_and_other_debt() -> None:
    source = "The ratio is 3 to 4."
    balanced = _row(1, source, "(Отношение равно 3 к 4.)")
    assert evaluate_tc_big_orphan_closing_parenthesis_trigger(
        balanced, source_exact=True
    )["eligible"] is False

    source_parenthetical = _row(
        2,
        "The ratio (observed) is 3 to 4.",
        "Отношение (наблюдаемое) равно 3 к 4.)",
    )
    assert evaluate_tc_big_orphan_closing_parenthesis_trigger(
        source_parenthetical, source_exact=True
    )["eligible"] is False

    numeric_loss = _row(3, source, "Отношение равно 3.)")
    trigger = evaluate_tc_big_orphan_closing_parenthesis_trigger(
        numeric_loss, source_exact=True
    )
    assert trigger["numeric_symbol_clean"] is False
    assert trigger["eligible"] is False

    question_addition = _row(4, source, "Отношение равно 3 к 4?)")
    trigger = evaluate_tc_big_orphan_closing_parenthesis_trigger(
        question_addition, source_exact=True
    )
    assert trigger["other_hard_punctuation_exact"] is False
    assert trigger["eligible"] is False


def test_candidate_requires_exact_punctuation_numeric_and_emphasis_integrity() -> None:
    source = "The _same_ ratio is 3 to 4."
    clean = "То же _отношение_ равно 3 к 4."
    selection = evaluate_tc_big_orphan_closing_parenthesis_candidate(source, clean)
    assert selection["accepted"] is True
    assert selection["hard_punctuation_exact"] is True
    assert selection["emphasis_markup"]["passed"] is True
    assert selection["mechanical_verdict"]["numeric_symbol"]["passed"] is True

    orphan = evaluate_tc_big_orphan_closing_parenthesis_candidate(
        source, "То же _отношение_ равно 3 к 4.)"
    )
    assert orphan["hard_punctuation_exact"] is False
    assert orphan["accepted"] is False

    numeric = evaluate_tc_big_orphan_closing_parenthesis_candidate(
        source, "То же _отношение_ равно 3."
    )
    assert numeric["mechanical_verdict"]["numeric_symbol"]["passed"] is False
    assert numeric["accepted"] is False

    emphasis = evaluate_tc_big_orphan_closing_parenthesis_candidate(
        source, "То же отношение равно 3 к 4."
    )
    assert emphasis["emphasis_markup"]["passed"] is False
    assert emphasis["accepted"] is False


def test_eligible_rows_require_byte_exact_document_slice_and_complexity_cap() -> None:
    source = "The ratio is 3 to 4. "
    row = _row(1, source, "Отношение равно 3 к 4.) ")
    assert len(_eligible_rows(content=source, base_rows=[row])) == 1
    assert _eligible_rows(content="X" + source[1:], base_rows=[row]) == []

    long_source = " ".join(["word"] * 41) + "."
    long_row = _row(2, long_source, "слово " * 40 + "слово.)")
    trigger = evaluate_tc_big_orphan_closing_parenthesis_trigger(
        long_row, source_exact=True
    )
    assert trigger["source_complexity_passed"] is False
    assert trigger["eligible"] is False


def test_disabled_run_delegates_without_tc_big_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 17}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "tc_big_status",
        lambda: (_ for _ in ()).throw(AssertionError("runtime must not be probed")),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_boundary_pair_punctuation_rescue": True,
            "enable_tc_big_orphan_closing_parenthesis_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {
        "enable_tc_big_boundary_pair_punctuation_rescue": True
    }


def test_enabled_run_uses_only_raw_rank0_and_leaves_other_targets_exact(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    first_source = "The ratio of the same rings is 3 to 4. "
    second_source = "Clean row."
    content = first_source + second_source
    first = _row(
        21,
        first_source,
        "Отношение тех же колец равно 3 к 4.) ",
        source_start=0,
    )
    second = _row(
        22,
        second_source,
        "Чистая строка.",
        source_start=len(first_source),
        split=False,
        context_start=8,
        context_end=8,
    )
    base_output = {
        "translation_run_id": 17,
        "document_version_id": 7,
        "model_request_count": 500,
    }
    base_run = {"id": 17, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(
        stage,
        "get_run_items",
        lambda connection, run_id, *, kind: [first, second]
        if int(run_id) == 17 and kind == "translation_segment"
        else (_ for _ in ()).throw(AssertionError((run_id, kind))),
    )
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (18, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    raw_rank0 = "Отношение тех же колец равно 3 к 4."

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [first_source]
            assert beam_size == 6
            assert num_hypotheses == 1
            return [[{"rank": 0, "text": raw_rank0, "score": -0.1}]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_orphan_closing_parenthesis_rescue": True},
    )
    assert result["translation_run_id"] == 18
    assert result["base_translation_run_id"] == 17
    assert result["tc_big_orphan_closing_parenthesis_rescue_attempt_count"] == 1
    assert result["tc_big_orphan_closing_parenthesis_rescue_accepted_count"] == 1
    assert result["tc_big_orphan_closing_parenthesis_rescue_rejected_count"] == 0
    assert result["tc_big_orphan_closing_parenthesis_rescue_selected_ranks"] == [0]
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["target_text"] == raw_rank0
    rescue = items[0]["payload"]["tc_big_orphan_closing_parenthesis_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["raw_model_rank"] == 0
    assert items[0]["payload"]["hypotheses"][0]["text"] == raw_rank0
    assert items[1]["target_text"] == second["target_text"]
    assert items[1]["payload"]["tc_big_orphan_closing_parenthesis_rescue"]["applied"] is False
    assert "".join(str(item["source_text"]) for item in items) == content
