from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_short_angular_dms_rescue_stage as stage
from rocketdict.translation_tc_big_short_angular_dms_rescue_stage import (
    MAX_SOURCE_ALPHA_WORDS,
    TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
    TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
    TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
    _alpha_word_count,
    _base_parameters,
    _eligible_rows,
    _source_dms,
    evaluate_tc_big_short_angular_dms_candidate,
    evaluate_tc_big_short_angular_dms_trigger,
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


def test_source_dms_and_word_cap_are_source_defined() -> None:
    assert _source_dms("Whence this Angle is 2 deg. 0'. 7''. ") == {
        "degrees": "2",
        "minutes": "0",
        "seconds": "7",
    }
    assert _source_dms("2 deg. 0'. 7'' and 3 deg. 1'. 8''.") is None
    assert _alpha_word_count("Whence this Angle is 2 deg. 0'. 7''.") == 5
    assert MAX_SOURCE_ALPHA_WORDS == 12


def test_trigger_rejects_long_dms_context_even_when_prime_is_broken() -> None:
    short_source = "Whence this Angle is 2 deg. 0'. 7''. "
    short = _row(1, short_source, "Откуда угол 2 градуса. 0 футов 7 футов. ")
    trigger = evaluate_tc_big_short_angular_dms_trigger(short, exact_stage10_context=True)
    assert trigger["eligible"] is True
    assert trigger["source_dms"] == {"degrees": "2", "minutes": "0", "seconds": "7"}
    assert trigger["source_alpha_word_count"] == 5

    long_source = (
        "For the distance between the Image and the Prism where this Angle is made, "
        "the Chord subtends an Angle of 2 deg. 0'. 7''. "
    )
    assert _alpha_word_count(long_source) > MAX_SOURCE_ALPHA_WORDS
    long_row = _row(2, long_source, "Расстояние даёт угол 2 градуса 0 футов 7 футов. ")
    long_trigger = evaluate_tc_big_short_angular_dms_trigger(
        long_row, exact_stage10_context=True
    )
    assert long_trigger["eligible"] is False

    assert evaluate_tc_big_short_angular_dms_trigger(
        short, exact_stage10_context=False
    )["eligible"] is False


def test_candidate_needs_exact_dms_and_russian_angle_semantics() -> None:
    source = "Whence this Angle is 2 deg. 0'. 7''. "
    good = evaluate_tc_big_short_angular_dms_candidate(
        source, "Откуда этот угол 2 град. 0'. 7''."
    )
    assert good["accepted"] is True
    assert good["strictly_eligible"] is True
    assert good["semantic_dms_preserved"] is True
    assert good["prime_notation"]["passed"] is True

    no_angle_word = evaluate_tc_big_short_angular_dms_candidate(
        source, "Отсюда 2 град. 0'. 7''."
    )
    assert no_angle_word["accepted"] is False
    assert no_angle_word["semantic_dms_preserved"] is False

    no_degree_semantics = evaluate_tc_big_short_angular_dms_candidate(
        source, "Откуда этот угол 2 дел. 0'. 7''."
    )
    assert no_degree_semantics["strictly_eligible"] is True
    assert no_degree_semantics["semantic_dms_preserved"] is False
    assert no_degree_semantics["accepted"] is False

    broken_seconds = evaluate_tc_big_short_angular_dms_candidate(
        source, "Откуда этот угол 2 град. 0'. 7'."
    )
    assert broken_seconds["accepted"] is False


def test_eligible_rows_require_exact_stage10_context() -> None:
    source = "Whence this Angle is 2 deg. 0'. 7''. "
    row = _row(
        1,
        source,
        "Откуда угол 2 градуса. 0 футов 7 футов. ",
        context_start=0,
        context_end=0,
    )
    context = [{
        "id": 100,
        "sequence_number": 0,
        "kind": "context_sentence",
        "source_start": 0,
        "source_end": len(source),
        "source_text": source,
        "target_text": "",
        "payload": {},
    }]
    assert len(_eligible_rows(content=source, base_rows=[row], context_rows=context)) == 1
    cut = [{**context[0], "source_end": len(source) - 1, "source_text": source[:-1]}]
    assert _eligible_rows(content=source, base_rows=[row], context_rows=cut) == []


def test_disabled_run_delegates_without_model_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 15}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "tc_big_status",
        lambda: (_ for _ in ()).throw(AssertionError("TC-big must not be probed")),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_angular_minute_rescue": True,
            "enable_tc_big_short_angular_dms_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_tc_big_angular_minute_rescue": True}


def test_enabled_run_selects_first_raw_dms_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    first_source = "Whence this Angle is 2 deg. 0'. 7''. "
    second_source = "Clean row."
    content = first_source + second_source
    first = _row(
        11,
        first_source,
        "Откуда угол 2 градуса. 0 футов 7 футов. ",
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
    contexts = [
        {"id":101,"sequence_number":0,"kind":"context_sentence","source_start":0,"source_end":len(first_source),"source_text":first_source,"target_text":"","payload":{}},
        {"id":102,"sequence_number":1,"kind":"context_sentence","source_start":len(first_source),"source_end":len(content),"source_text":second_source,"target_text":"","payload":{}},
    ]
    base_output = {"translation_run_id": 15, "document_version_id": 7, "model_request_count": 500}
    base_run = {"id": 15, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}
    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)

    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 15 and kind == "translation_segment":
            return [first, second]
        if int(run_id) == 2 and kind == "context_sentence":
            return contexts
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (16, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    bad_rank0 = "Откуда этот угол 2 град. 0'. 7'."
    raw_rank1 = "Откуда этот угол 2 град. 0'. 7''."

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [first_source]
            return [[
                {"rank":0,"text":bad_rank0,"score":-0.1},
                {"rank":1,"text":raw_rank1,"score":-0.2},
                {"rank":2,"text":raw_rank1,"score":-0.3},
                {"rank":3,"text":raw_rank1,"score":-0.4},
                {"rank":4,"text":raw_rank1,"score":-0.5},
                {"rank":5,"text":raw_rank1,"score":-0.6},
            ]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_short_angular_dms_rescue": True},
    )
    assert result["translation_run_id"] == 16
    assert result["base_translation_run_id"] == 15
    assert result["tc_big_short_angular_dms_rescue_attempt_count"] == 1
    assert result["tc_big_short_angular_dms_rescue_accepted_count"] == 1
    assert result["tc_big_short_angular_dms_rescue_selected_ranks"] == [1]
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["target_text"] == raw_rank1
    rescue = items[0]["payload"]["tc_big_short_angular_dms_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["selection"]["semantic_dms_preserved"] is True
    assert items[0]["payload"]["hypotheses"][1]["text"] == raw_rank1
    assert items[1]["target_text"] == second["target_text"]
    assert items[1]["payload"]["tc_big_short_angular_dms_rescue"]["applied"] is False
    assert "".join(str(item["source_text"]) for item in items) == content


def test_base_parameters_strip_only_dms_controls() -> None:
    parameters = {
        "enable_tc_big_angular_minute_rescue": True,
        "enable_tc_big_short_angular_dms_rescue": True,
        "tc_big_short_angular_dms_rescue_contract": TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
        "tc_big_short_angular_dms_selector_contract": TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
        "tc_big_short_angular_dms_trigger_contract": TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
    }
    assert _base_parameters(parameters) == {"enable_tc_big_angular_minute_rescue": True}
