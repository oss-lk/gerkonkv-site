from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_angular_minute_rescue_stage as stage
from rocketdict.translation_tc_big_angular_minute_rescue_stage import (
    TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT,
    TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
    TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT,
    _base_parameters,
    _eligible_rows,
    _source_angle,
    evaluate_tc_big_angular_minute_candidate,
    evaluate_tc_big_angular_minute_trigger,
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


def test_base_parameters_strip_only_angular_controls() -> None:
    parameters = {
        "enable_tc_big_equals_addition_rescue": True,
        "enable_tc_big_angular_minute_rescue": True,
        "tc_big_angular_minute_rescue_contract": TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT,
        "tc_big_angular_minute_selector_contract": TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
        "tc_big_angular_minute_trigger_contract": TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT,
    }
    assert _base_parameters(parameters) == {"enable_tc_big_equals_addition_rescue": True}


def test_source_angle_requires_exactly_one_degree_minute_phrase() -> None:
    assert _source_angle("Halo about 22 Degrees\n35' distant.") == {
        "degrees": "22",
        "minutes": "35",
    }
    assert _source_angle("Halo about 1 Degree 5' distant.") == {
        "degrees": "1",
        "minutes": "5",
    }
    assert _source_angle("No angular phrase here.") is None
    assert _source_angle("22 Degrees 35' and 20 Degrees 4'.") is None


def test_trigger_requires_exact_context_hard_prime_failure_and_single_angle() -> None:
    source = "The Halo was about 22 Degrees 35' distant."
    broken = _row(1, source, "Гало было примерно в 22 градусах 35 футах.")
    trigger = evaluate_tc_big_angular_minute_trigger(
        broken, exact_stage10_context=True
    )
    assert trigger["eligible"] is True
    assert trigger["source_angle"] == {"degrees": "22", "minutes": "35"}
    assert trigger["source_single_minute_prime_shape"] is True
    assert trigger["current_prime_notation_passed"] is False

    assert evaluate_tc_big_angular_minute_trigger(
        broken, exact_stage10_context=False
    )["eligible"] is False

    clean = _row(2, source, "Гало было на расстоянии 22 градусов 35'.")
    assert evaluate_tc_big_angular_minute_trigger(
        clean, exact_stage10_context=True
    )["eligible"] is False

    ambiguous = _row(
        3,
        "Angles 22 Degrees 35' and 20 Degrees 4'.",
        "Углы 22 градусов 35 футов и 20 градусов 4 фута.",
    )
    assert evaluate_tc_big_angular_minute_trigger(
        ambiguous, exact_stage10_context=True
    )["eligible"] is False


def test_candidate_requires_prime_and_russian_degree_semantic_anchor() -> None:
    source = "The Halo was about 22 Degrees 35' distant."
    good = evaluate_tc_big_angular_minute_candidate(
        source, "Гало находилось на расстоянии около 22 градусов 35'."
    )
    assert good["accepted"] is True
    assert good["strictly_eligible"] is True
    assert good["semantic_angle_preserved"] is True
    assert good["prime_notation"]["passed"] is True

    lost_prime = evaluate_tc_big_angular_minute_candidate(
        source, "Гало находилось на расстоянии около 22 градусов 35 минут."
    )
    assert lost_prime["accepted"] is False

    wrong_unit = evaluate_tc_big_angular_minute_candidate(
        source, "Гало находилось на расстоянии около 22 ступеней 35'."
    )
    assert wrong_unit["strictly_eligible"] is True
    assert wrong_unit["semantic_angle_preserved"] is False
    assert wrong_unit["accepted"] is False

    wrong_values = evaluate_tc_big_angular_minute_candidate(
        source, "Гало находилось на расстоянии около 22 градусов 36'."
    )
    assert wrong_values["accepted"] is False


def test_eligible_rows_require_exact_stage10_geometry() -> None:
    source = "The Halo was about 22 Degrees 35' distant. "
    content = source + "Tail."
    row = _row(
        1,
        source,
        "Гало было примерно в 22 градусах 35 футах. ",
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
    expected = {"translation_run_id": 14}
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
            "enable_tc_big_equals_addition_rescue": True,
            "enable_tc_big_angular_minute_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_tc_big_equals_addition_rescue": True}


def test_enabled_run_persists_first_raw_semantically_anchored_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    first_source = "The Halo was about 22 Degrees 35' distant. "
    second_source = "Clean row."
    content = first_source + second_source
    first = _row(
        11,
        first_source,
        "Гало было примерно в 22 градусах 35 футах. ",
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
    contexts = [
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
    base_output = {"translation_run_id": 14, "document_version_id": 7, "model_request_count": 400}
    base_run = {"id": 14, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)

    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 14 and kind == "translation_segment":
            return [first, second]
        if int(run_id) == 2 and kind == "context_sentence":
            return contexts
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (15, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    raw_target = "Гало находилось на расстоянии около 22 градусов 35'."

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [first_source]
            return [[
                {"rank": 0, "text": raw_target, "score": -0.1},
                {"rank": 1, "text": "Гало было на 22 ступенях 35'.", "score": -0.2},
                {"rank": 2, "text": raw_target, "score": -0.3},
                {"rank": 3, "text": raw_target, "score": -0.4},
                {"rank": 4, "text": raw_target, "score": -0.5},
                {"rank": 5, "text": raw_target, "score": -0.6},
            ]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_angular_minute_rescue": True},
    )
    assert result["translation_run_id"] == 15
    assert result["base_translation_run_id"] == 14
    assert result["tc_big_angular_minute_rescue_attempt_count"] == 1
    assert result["tc_big_angular_minute_rescue_accepted_count"] == 1
    assert result["tc_big_angular_minute_rescue_rejected_count"] == 0
    assert result["tc_big_angular_minute_rescue_selected_ranks"] == [0]
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["target_text"] == raw_target
    rescue = items[0]["payload"]["tc_big_angular_minute_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["selection"]["semantic_angle_preserved"] is True
    assert items[0]["payload"]["hypotheses"][0]["text"] == raw_target
    assert items[1]["target_text"] == second["target_text"]
    assert items[1]["payload"]["tc_big_angular_minute_rescue"]["applied"] is False
    assert "".join(str(item["source_text"]) for item in items) == content
