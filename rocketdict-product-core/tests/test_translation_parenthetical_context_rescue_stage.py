from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_parenthetical_context_rescue_stage as stage
from rocketdict.translation_parenthetical_context_rescue_stage import (
    MAX_CONTEXT_NLP_TOKENS,
    MAX_PARENTHETICAL_ALPHA_WORDS,
    PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
    PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
    PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
    _base_parameters,
    evaluate_parenthetical_context_candidate,
    evaluate_parenthetical_context_trigger,
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


def _context(source: str, *, sequence: int = 0, token_count: int = 30) -> dict[str, object]:
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
    first_source = "The light was transmitted, and when viewed through it "
    second_source = "seemed (as it were) a hole in the air. "
    source = first_source + second_source
    rows = [
        _row(
            1,
            first_source,
            "Свет передавался, и при взгляде сквозь него ",
            source_start=0,
        ),
        _row(
            2,
            second_source,
            "казался как будто отверстием в воздухе. ",
            source_start=len(first_source),
        ),
    ]
    return source, _context(source), rows


def test_base_parameters_strip_only_parenthetical_controls() -> None:
    parameters = {
        "enable_question_mark_whole_context_rescue": True,
        "enable_parenthetical_whole_context_rescue": True,
        "parenthetical_whole_context_rescue_contract": PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
        "parenthetical_whole_context_selector_contract": PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
        "parenthetical_whole_context_trigger_contract": PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
        "parenthetical_whole_context_max_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
        "parenthetical_whole_context_max_parenthetical_alpha_words": MAX_PARENTHETICAL_ALPHA_WORDS,
    }
    assert _base_parameters(parameters) == {
        "enable_question_mark_whole_context_rescue": True
    }


def test_trigger_accepts_single_lost_bounded_parenthetical_pair() -> None:
    source, context, rows = _good_fixture()
    trigger = evaluate_parenthetical_context_trigger(
        content=source,
        context=context,
        primary_rows=rows,
    )
    assert trigger["eligible"] is True
    assert trigger["source_round_parentheses"] == [1, 1]
    assert trigger["aggregate_target_round_parentheses"] == [0, 0]
    assert trigger["parenthetical_alpha_word_count"] == 3
    assert trigger["within_context_nlp_token_cap"] is True

    over_cap = {**context, "payload": {"sentence_index": 0, "token_count": 161}}
    assert evaluate_parenthetical_context_trigger(
        content=source,
        context=over_cap,
        primary_rows=rows,
    )["eligible"] is False


def test_trigger_rejects_multiple_partial_or_large_parenthetical_shapes() -> None:
    source, context, rows = _good_fixture()
    multiple_source = source.replace(
        "a hole in the air", "a hole (or opening) in the air"
    )
    multiple_context = _context(multiple_source)
    multiple_rows = [
        _row(1, multiple_source[: len(rows[0]["source_text"])], str(rows[0]["target_text"]), source_start=0),
        _row(
            2,
            multiple_source[len(rows[0]["source_text"]) :],
            str(rows[1]["target_text"]),
            source_start=len(rows[0]["source_text"]),
        ),
    ]
    assert evaluate_parenthetical_context_trigger(
        content=multiple_source,
        context=multiple_context,
        primary_rows=multiple_rows,
    )["eligible"] is False

    partial = [rows[0], {**rows[1], "target_text": "казался (как будто отверстием в воздухе. "}]
    assert evaluate_parenthetical_context_trigger(
        content=source,
        context=context,
        primary_rows=partial,
    )["eligible"] is False

    long_source = source.replace("as it were", "as one might perhaps describe it in ordinary speech")
    long_context = _context(long_source)
    long_rows = [
        _row(1, long_source[: len(rows[0]["source_text"])], str(rows[0]["target_text"]), source_start=0),
        _row(
            2,
            long_source[len(rows[0]["source_text"]) :],
            str(rows[1]["target_text"]),
            source_start=len(rows[0]["source_text"]),
        ),
    ]
    assert evaluate_parenthetical_context_trigger(
        content=long_source,
        context=long_context,
        primary_rows=long_rows,
    )["eligible"] is False


def test_candidate_requires_exact_parentheses_and_no_content_loss() -> None:
    source = "The light seemed (as it were) a hole in the air."
    primary = "Свет казался как будто отверстием в воздухе."
    target = "Свет казался (как будто) отверстием в воздухе."
    selection = evaluate_parenthetical_context_candidate(
        source,
        target,
        primary_target=primary,
    )
    assert selection["accepted"] is True
    assert selection["hard_punctuation_exact"] is True
    assert selection["target_alpha_non_decreasing"] is True

    missing = evaluate_parenthetical_context_candidate(
        source,
        primary,
        primary_target=primary,
    )
    assert missing["hard_punctuation_exact"] is False
    assert missing["accepted"] is False

    short = evaluate_parenthetical_context_candidate(
        source,
        "Свет (как будто) отверстие.",
        primary_target=primary,
    )
    assert short["target_alpha_non_decreasing"] is False
    assert short["accepted"] is False


def test_disabled_run_delegates_without_opus_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 19}
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
            "enable_question_mark_whole_context_rescue": True,
            "enable_parenthetical_whole_context_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_question_mark_whole_context_rescue": True}


def test_enabled_run_persists_rank0_and_merges_only_eligible_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    source, context, rows = _good_fixture()
    base_output = {
        "translation_run_id": 19,
        "document_version_id": 7,
        "model_request_count": 501,
    }
    base_run = {"id": 19, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": source, "text_sha256": "b" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)

    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 19 and kind == "translation_segment":
            return rows
        if int(run_id) == 2 and kind == "context_sentence":
            return [context]
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (20, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    raw_target = "Свет передавался, и при взгляде сквозь него казался (как будто) отверстием в воздухе. "

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
        parameters={"enable_parenthetical_whole_context_rescue": True},
    )
    assert result["translation_run_id"] == 20
    assert result["base_translation_run_id"] == 19
    assert result["parenthetical_whole_context_rescue_attempt_count"] == 1
    assert result["parenthetical_whole_context_rescue_accepted_count"] == 1
    assert result["parenthetical_whole_context_rescue_accepted_context_sequences"] == [0]
    assert result["parenthetical_whole_context_rescue_selected_ranks"] == [0]
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 1
    rescue = items[0]["payload"]["parenthetical_whole_context_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["raw_model_rank"] == 0
    assert rescue["base_translation_segment_ids"] == [1, 2]
    assert items[0]["source_text"] == source
    assert items[0]["target_text"] == raw_target
