from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_figure_reference_rescue_stage as stage
from rocketdict.translation_tc_big_figure_reference_rescue_stage import (
    TC_BIG_FIGURE_RESCUE_CONTRACT,
    TC_BIG_FIGURE_SELECTED_PHASE,
    TC_BIG_FIGURE_SELECTOR_CONTRACT,
    TC_BIG_FIGURE_TRIGGER_CONTRACT,
    _base_parameters,
    _eligible_rows,
    evaluate_tc_big_figure_candidate,
    evaluate_tc_big_figure_trigger,
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


def test_base_parameters_strip_only_figure_wrapper_controls() -> None:
    parameters = {
        "beam_size": 6,
        "enable_tc_big_target_delimiter_rescue": True,
        "enable_tc_big_footnote_reference_rescue": True,
        "enable_tc_big_figure_reference_rescue": True,
        "tc_big_figure_reference_rescue_contract": TC_BIG_FIGURE_RESCUE_CONTRACT,
        "tc_big_figure_reference_selector_contract": TC_BIG_FIGURE_SELECTOR_CONTRACT,
        "tc_big_figure_reference_trigger_contract": TC_BIG_FIGURE_TRIGGER_CONTRACT,
        "tc_big_figure_reference_rescue_phase": TC_BIG_FIGURE_SELECTED_PHASE,
    }
    assert _base_parameters(parameters) == {
        "beam_size": 6,
        "enable_tc_big_target_delimiter_rescue": True,
        "enable_tc_big_footnote_reference_rescue": True,
    }


def test_trigger_requires_exact_context_hard_failure_and_lost_leading_reference() -> None:
    source = "[in _Fig._ 15.] is the Spectator's Eye, and OP a Line."
    broken = _row(1, source, "=== Fig._15. === Глаз зрителя и OP — линия.")
    trigger = evaluate_tc_big_figure_trigger(broken, exact_stage10_context=True)
    assert trigger["eligible"] is True
    assert trigger["source_figure_number"] == "15"
    assert trigger["contains_current_product_hard_failure"] is True
    assert trigger["target_reference_already_preserved"]["passed"] is False

    assert evaluate_tc_big_figure_trigger(
        broken, exact_stage10_context=False
    )["eligible"] is False

    preserved = _row(
        2,
        source,
        "[В _рис._ 15.] Глаз зрителя, и OP — линия.",
    )
    assert evaluate_tc_big_figure_trigger(
        preserved, exact_stage10_context=True
    )["eligible"] is False

    non_figure = _row(3, "[G] _See our_ ", "Смотрите наш")
    assert evaluate_tc_big_figure_trigger(
        non_figure, exact_stage10_context=True
    )["eligible"] is False


def test_candidate_accepts_translated_leading_label_with_same_number() -> None:
    source = (
        "[in _Fig._ 15.] is the Spectator's Eye, and OP a Line drawn parallel "
        "to the Sun's Rays and let POE be an Angle of 40 Degr."
    )
    target = (
        "[В _рис._ 15.] это Глаз Зрителя, и OP линия, проведенная параллельно "
        "солнечным лучам, и пусть POE будет углом 40 Degr."
    )
    selection = evaluate_tc_big_figure_candidate(
        source, target, figure_number="15"
    )
    assert selection["accepted"] is True
    assert selection["strictly_eligible"] is True
    assert selection["target_reference_lead"]["passed"] is True
    assert selection["target_reference_lead"]["figure_number_preserved_in_lead"] is True
    assert selection["target_reference_lead"]["emphasis_inside_lead"] is True
    assert selection["emphasis_markup"]["passed"] is True


def test_candidate_rejects_wrong_number_missing_emphasis_or_nonleading_reference() -> None:
    source = "[in _Fig._ 15.] is the Spectator's Eye."
    wrong_number = evaluate_tc_big_figure_candidate(
        source,
        "[В _рис._ 16.] это Глаз Зрителя.",
        figure_number="15",
    )
    assert wrong_number["accepted"] is False

    missing_emphasis = evaluate_tc_big_figure_candidate(
        source,
        "[В рис. 15.] это Глаз Зрителя.",
        figure_number="15",
    )
    assert missing_emphasis["target_reference_lead"]["emphasis_inside_lead"] is False
    assert missing_emphasis["accepted"] is False

    nonleading = evaluate_tc_big_figure_candidate(
        source,
        "Это Глаз Зрителя [в _рис._ 15.].",
        figure_number="15",
    )
    assert nonleading["target_reference_lead"]["leading_square_reference"] is False
    assert nonleading["accepted"] is False


def test_eligible_rows_require_exact_stage10_geometry() -> None:
    content = "[in _Fig._ 15.] Alpha beta. Tail."
    first_source = "[in _Fig._ 15.] Alpha beta. "
    row = _row(
        1,
        first_source,
        "Альфа-бета.",
        source_start=0,
        context_start=0,
        context_end=0,
    )
    exact_context = [
        {
            "id": 100,
            "sequence_number": 0,
            "kind": "context_sentence",
            "source_start": 0,
            "source_end": len(first_source),
            "source_text": first_source,
            "target_text": "",
            "payload": {},
        }
    ]
    attempts = _eligible_rows(
        content=content,
        base_rows=[row],
        context_rows=exact_context,
    )
    assert len(attempts) == 1

    cut_context = [
        {
            **exact_context[0],
            "source_end": len(first_source) - 1,
            "source_text": first_source[:-1],
        }
    ]
    assert _eligible_rows(
        content=content,
        base_rows=[row],
        context_rows=cut_context,
    ) == []


def test_disabled_run_delegates_without_probing_tc_big(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 11, "sentinel": "base-exact"}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed.update(
            database=database,
            context_run_id=context_run_id,
            parameters=parameters,
            implementation=implementation,
        )
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "tc_big_status",
        lambda: (_ for _ in ()).throw(
            AssertionError("TC-big runtime must not be probed while figure rescue is disabled")
        ),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_footnote_reference_rescue": True,
            "enable_tc_big_figure_reference_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_tc_big_footnote_reference_rescue": True}


def test_enabled_run_persists_raw_candidate_and_exact_untouched_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    first_source = "[in _Fig._ 15.] Eye and OP are shown. "
    second_source = "Clean row."
    content = first_source + second_source
    first = _row(
        11,
        first_source,
        "=== Fig._15. === Глаз и OP показаны. ",
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
    base_output = {
        "translation_run_id": 11,
        "document_version_id": 7,
        "model_request_count": 200,
    }
    base_run = {"id": 11, "output": base_output, "output_sha256": "a" * 64}
    document = {
        "id": 7,
        "content_text": content,
        "text_sha256": "b" * 64,
        "selected_format": "txt",
    }

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)

    def fake_get_run_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 11 and kind == "translation_segment":
            return [first, second]
        if int(run_id) == 2 and kind == "context_sentence":
            return context_rows
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_get_run_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (12, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["run_id"] = run_id
        completed["output"] = output
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})

    raw_target = "[В _рис._ 15.] Глаз и OP показаны."

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu"
            assert compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [first_source]
            assert (beam_size, num_hypotheses, max_decoding_length) == (6, 6, 512)
            return [[
                {"rank": 0, "text": raw_target, "score": -0.1},
                {"rank": 1, "text": "Без ссылки.", "score": -0.2},
                {"rank": 2, "text": raw_target, "score": -0.3},
                {"rank": 3, "text": raw_target, "score": -0.4},
                {"rank": 4, "text": raw_target, "score": -0.5},
                {"rank": 5, "text": raw_target, "score": -0.6},
            ]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)

    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_figure_reference_rescue": True},
    )
    assert result["translation_run_id"] == 12
    assert result["base_translation_run_id"] == 11
    assert result["tc_big_figure_reference_rescue_attempt_count"] == 1
    assert result["tc_big_figure_reference_rescue_accepted_count"] == 1
    assert result["tc_big_figure_reference_rescue_rejected_count"] == 0
    assert result["tc_big_figure_reference_rescue_selected_ranks"] == [0]
    assert result["tc_big_figure_reference_rescue_selected_targets"] == [raw_target]

    items = completed["items"]
    assert isinstance(items, list)
    assert len(items) == 2
    assert "".join(str(item["source_text"]) for item in items) == content
    rescued, untouched = items
    assert rescued["target_text"] == raw_target
    rescue = rescued["payload"]["tc_big_figure_reference_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["source_figure_number"] == "15"
    assert rescue["base_translation_segment_id"] == 11
    assert rescued["payload"]["hypotheses"][0]["text"] == raw_target
    for flag in (
        "source_bytes_rewritten",
        "target_rewriting",
        "placeholders",
        "post_translation_literal_injection",
        "corpus_specific_target_patches",
    ):
        assert rescue[flag] is False
        assert result[flag] is False

    assert untouched["source_text"] == second["source_text"]
    assert untouched["target_text"] == second["target_text"]
    untouched_rescue = untouched["payload"]["tc_big_figure_reference_rescue"]
    assert untouched_rescue["applied"] is False
    assert untouched_rescue["base_translation_segment_id"] == 12
