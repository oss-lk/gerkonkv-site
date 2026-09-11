from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_footnote_reference_rescue_stage as stage
from rocketdict.translation_tc_big_footnote_reference_rescue_stage import (
    MAX_SOURCE_ALPHA_RATIO,
    MIN_SOURCE_ALPHA_RATIO,
    TC_BIG_FOOTNOTE_RESCUE_CONTRACT,
    TC_BIG_FOOTNOTE_SELECTED_PHASE,
    TC_BIG_FOOTNOTE_SELECTOR_CONTRACT,
    TC_BIG_FOOTNOTE_TRIGGER_CONTRACT,
    _base_parameters,
    _eligible_rows,
    evaluate_tc_big_footnote_candidate,
    evaluate_tc_big_footnote_trigger,
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


def test_base_parameters_strip_only_footnote_wrapper_controls() -> None:
    parameters = {
        "enable_tc_big_target_delimiter_rescue": True,
        "enable_tc_big_footnote_reference_rescue": True,
        "tc_big_footnote_reference_rescue_contract": TC_BIG_FOOTNOTE_RESCUE_CONTRACT,
        "tc_big_footnote_reference_selector_contract": TC_BIG_FOOTNOTE_SELECTOR_CONTRACT,
        "tc_big_footnote_reference_trigger_contract": TC_BIG_FOOTNOTE_TRIGGER_CONTRACT,
        "tc_big_footnote_reference_rescue_phase": TC_BIG_FOOTNOTE_SELECTED_PHASE,
        "beam_size": 6,
    }
    assert _base_parameters(parameters) == {
        "enable_tc_big_target_delimiter_rescue": True,
        "beam_size": 6,
    }


def test_trigger_requires_exact_context_hard_failure_shape_and_missing_ascii_marker() -> None:
    source = "[H] _How to do this, is shewn in our_ "
    failing = _row(1, source, "Как это делается?")
    trigger = evaluate_tc_big_footnote_trigger(failing, exact_stage10_context=True)
    assert trigger["eligible"] is True
    assert trigger["source_reference_lead_shape"] is True
    assert trigger["source_marker"] == "H"
    assert trigger["exact_ascii_marker_already_preserved"] is False
    assert trigger["contains_current_product_hard_failure"] is True

    assert evaluate_tc_big_footnote_trigger(failing, exact_stage10_context=False)["eligible"] is False

    preserved = _row(2, source, "[H] _Как это сделать, показано в нашем_")
    preserved_trigger = evaluate_tc_big_footnote_trigger(preserved, exact_stage10_context=True)
    assert preserved_trigger["exact_ascii_marker_already_preserved"] is True
    assert preserved_trigger["eligible"] is False

    unrelated = _row(3, "[H] ordinary note", "обычная заметка")
    assert evaluate_tc_big_footnote_trigger(unrelated, exact_stage10_context=True)["eligible"] is False


def test_hard_clean_transliterated_reference_lead_is_not_touched() -> None:
    # Run-10-like [C] row: strict footnote-marker identity may be imperfect, but
    # the maintained Product hard gates are already clean.  The second MT must
    # not broaden itself to clean output without a separately promoted policy.
    row = _row(1, "[C] _See our_ ", "[С] Посмотри на нас.")
    trigger = evaluate_tc_big_footnote_trigger(row, exact_stage10_context=True)
    assert trigger["contains_current_product_hard_failure"] is False
    assert trigger["eligible"] is False


def test_candidate_requires_exact_ascii_marker_emphasis_shape_and_source_relative_volume() -> None:
    source = "[H] _How to do this, is shewn in our_ "
    accepted = evaluate_tc_big_footnote_candidate(
        source, "[H] _Как это сделать, показано в нашем_", marker="H"
    )
    assert accepted["accepted"] is True
    assert accepted["exact_ascii_marker_preserved"] is True
    assert accepted["target_reference_lead_shape"] is True
    assert accepted["emphasis_markup"]["passed"] is True
    assert MIN_SOURCE_ALPHA_RATIO <= accepted["source_alpha_ratio"] <= MAX_SOURCE_ALPHA_RATIO

    missing = evaluate_tc_big_footnote_candidate(
        source, "_Как это сделать, показано в нашем_", marker="H"
    )
    assert missing["exact_ascii_marker_preserved"] is False
    assert missing["accepted"] is False

    cyrillic = evaluate_tc_big_footnote_candidate(
        source, "[Н] _Как это сделать, показано в нашем_", marker="H"
    )
    assert cyrillic["exact_ascii_marker_preserved"] is False
    assert cyrillic["accepted"] is False

    no_emphasis = evaluate_tc_big_footnote_candidate(
        source, "[H] Как это сделать, показано в нашем", marker="H"
    )
    assert no_emphasis["emphasis_markup"]["passed"] is False
    assert no_emphasis["accepted"] is False

    too_long = evaluate_tc_big_footnote_candidate(
        source,
        "[H] _" + "очень " * 30 + "длинный перевод_",
        marker="H",
    )
    assert too_long["source_alpha_ratio"] > MAX_SOURCE_ALPHA_RATIO
    assert too_long["accepted"] is False


def test_short_j_fragment_is_allowed_without_forcing_sentence_completion() -> None:
    source = "[J] _See our_ "
    candidate = "[J] _Смотрите наш_"
    selection = evaluate_tc_big_footnote_candidate(source, candidate, marker="J")
    assert selection["accepted"] is True
    assert not candidate.endswith(".")
    assert selection["source_alpha_ratio"] <= MAX_SOURCE_ALPHA_RATIO


def test_eligible_rows_require_exact_single_stage10_context() -> None:
    source = "[G] _This is demonstrated in our_ "
    following = "Author's Lect. Optic. "
    content = source + following
    row = _row(11, source, "Это демонстрируется в нашем...", source_start=0, context_start=0, context_end=0)
    next_row = _row(12, following, "Автор - Лект, оптика.", source_start=len(source), context_start=1, context_end=1)
    context_rows = [
        {
            "id": 101,
            "sequence_number": 0,
            "kind": "context_sentence",
            "source_start": 0,
            "source_end": len(source),
            "source_text": source,
            "target_text": "",
            "payload": {},
        },
        {
            "id": 102,
            "sequence_number": 1,
            "kind": "context_sentence",
            "source_start": len(source),
            "source_end": len(content),
            "source_text": following,
            "target_text": "",
            "payload": {},
        },
    ]
    attempts = _eligible_rows(content=content, base_rows=[row, next_row], context_rows=context_rows)
    assert len(attempts) == 1
    assert attempts[0]["row"]["id"] == 11
    assert attempts[0]["trigger"]["source_marker"] == "G"

    merged_context = [
        {
            "id": 201,
            "sequence_number": 0,
            "kind": "context_sentence",
            "source_start": 0,
            "source_end": len(content),
            "source_text": content,
            "target_text": "",
            "payload": {},
        }
    ]
    row_merged = _row(11, source, "Это демонстрируется в нашем...", source_start=0, context_start=0, context_end=0)
    assert _eligible_rows(content=content, base_rows=[row_merged, next_row], context_rows=merged_context) == []


def test_disabled_run_delegates_without_probing_tc_big(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    expected = {"translation_run_id": 10, "sentinel": "base-exact"}
    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: expected)
    monkeypatch.setattr(
        stage,
        "tc_big_status",
        lambda: (_ for _ in ()).throw(AssertionError("TC-big must not be probed when footnote rescue is disabled")),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=17,
        parameters={
            "enable_tc_big_target_delimiter_rescue": True,
            "enable_tc_big_footnote_reference_rescue": False,
        },
    )
    assert result is expected


def test_enabled_run_persists_raw_rank0_and_copies_untouched_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    source = "[G] _This is demonstrated in our_ "
    following = "Author's Lect. Optic. "
    content = source + following
    first = _row(11, source, "Это демонстрируется в нашем...", source_start=0, context_start=0, context_end=0)
    second = _row(12, following, "Автор - Лект, оптика.", source_start=len(source), context_start=1, context_end=1)
    context_rows = [
        {"id": 101, "sequence_number": 0, "kind": "context_sentence", "source_start": 0, "source_end": len(source), "source_text": source, "target_text": "", "payload": {}},
        {"id": 102, "sequence_number": 1, "kind": "context_sentence", "source_start": len(source), "source_end": len(content), "source_text": following, "target_text": "", "payload": {}},
    ]
    base_output = {"translation_run_id": 10, "document_version_id": 7, "model_request_count": 100}
    base_run = {"id": 10, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64, "selected_format": "txt"}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 10 and kind == "translation_segment":
            return [first, second]
        if int(run_id) == 17 and kind == "context_sentence":
            return context_rows
        raise AssertionError((run_id, kind))
    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (11, None))
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True, "asset_manifest_sha256": "c" * 64})
    completed: dict[str, object] = {}
    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output
    monkeypatch.setattr(stage, "_complete", fake_complete)

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"
        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [source]
            assert (beam_size, num_hypotheses, max_decoding_length) == (6, 6, 128)
            return [[
                {"rank": 0, "text": "[G] _Это продемонстрировано в нашем_", "score": -0.1},
                {"rank": 1, "text": "[G] _Это показано в нашем_", "score": -0.2},
                {"rank": 2, "text": "[Г] _Это показано в нашем_", "score": -0.3},
                {"rank": 3, "text": "Это показано в нашем", "score": -0.4},
                {"rank": 4, "text": "[G] _Это продемонстрировано в нашем_", "score": -0.5},
                {"rank": 5, "text": "[G] _Это продемонстрировано в нашем_", "score": -0.6},
            ]]
    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)

    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=17,
        parameters={"enable_tc_big_footnote_reference_rescue": True},
    )
    assert result["translation_run_id"] == 11
    assert result["base_translation_run_id"] == 10
    assert result["tc_big_footnote_reference_rescue_attempt_count"] == 1
    assert result["tc_big_footnote_reference_rescue_accepted_count"] == 1
    assert result["tc_big_footnote_reference_rescue_selected_ranks"] == [0]
    assert result["tc_big_footnote_reference_rescue_selected_targets"] == ["[G] _Это продемонстрировано в нашем_"]
    for flag in ("source_bytes_rewritten", "target_rewriting", "placeholders", "post_translation_literal_injection", "corpus_specific_target_patches"):
        assert result[flag] is False

    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert "".join(str(item["source_text"]) for item in items) == content
    rescued, untouched = items
    assert rescued["source_text"] == source
    assert rescued["target_text"] == "[G] _Это продемонстрировано в нашем_"
    rescue = rescued["payload"]["tc_big_footnote_reference_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["base_translation_segment_id"] == 11
    assert rescued["payload"]["selected_rank"] == 0
    assert rescued["payload"]["hypotheses"][0]["text"] == rescued["target_text"]
    assert untouched["source_text"] == second["source_text"]
    assert untouched["target_text"] == second["target_text"]
    assert untouched["payload"]["tc_big_footnote_reference_rescue"]["applied"] is False
