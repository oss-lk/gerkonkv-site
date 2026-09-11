from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_delimiter_rescue_stage as stage
from rocketdict.translation_tc_big_delimiter_rescue_stage import (
    MAX_SOURCE_ALPHA_RATIO,
    MIN_SOURCE_ALPHA_RATIO,
    TC_BIG_DELIMITER_RESCUE_CONTRACT,
    TC_BIG_DELIMITER_SELECTED_PHASE,
    TC_BIG_DELIMITER_SELECTOR_CONTRACT,
    TC_BIG_DELIMITER_TRIGGER_CONTRACT,
    _base_parameters,
    _context_inventory,
    evaluate_tc_big_delimiter_candidate,
    evaluate_tc_big_delimiter_trigger,
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


def test_base_parameters_strip_only_tc_big_wrapper_controls() -> None:
    parameters = {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "enable_illustration_label_rescue": True,
        "enable_numeric_hard_failure_whole_context_rescue": True,
        "enable_tc_big_target_delimiter_rescue": True,
        "tc_big_target_delimiter_rescue_contract": TC_BIG_DELIMITER_RESCUE_CONTRACT,
        "tc_big_target_delimiter_selector_contract": TC_BIG_DELIMITER_SELECTOR_CONTRACT,
        "tc_big_target_delimiter_trigger_contract": TC_BIG_DELIMITER_TRIGGER_CONTRACT,
        "tc_big_target_delimiter_rescue_phase": TC_BIG_DELIMITER_SELECTED_PHASE,
    }
    assert _base_parameters(parameters) == {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "enable_illustration_label_rescue": True,
        "enable_numeric_hard_failure_whole_context_rescue": True,
    }


def test_trigger_requires_row_alignment_hard_failure_and_target_only_delimiter() -> None:
    source = "Light passes through glass."
    failing = _row(1, source, "Свет (проходит) сквозь стекло.")
    trigger = evaluate_tc_big_delimiter_trigger(
        source=source,
        aggregate_target=str(failing["target_text"]),
        primary_rows=[failing],
        row_aligned=True,
    )
    assert trigger["eligible"] is True
    assert trigger["replacement_row_aligned"] is True
    assert trigger["contains_current_product_hard_failure"] is True
    assert trigger["target_only_delimiter_additions"] == {"(": 1, ")": 1}

    assert evaluate_tc_big_delimiter_trigger(
        source=source,
        aggregate_target=str(failing["target_text"]),
        primary_rows=[failing],
        row_aligned=False,
    )["eligible"] is False

    clean = _row(2, source, "Свет проходит сквозь стекло.")
    assert evaluate_tc_big_delimiter_trigger(
        source=source,
        aggregate_target=str(clean["target_text"]),
        primary_rows=[clean],
        row_aligned=True,
    )["eligible"] is False

    numeric_failure_without_added_delimiter = _row(3, "Value 12 remains.", "Значение остается.")
    trigger = evaluate_tc_big_delimiter_trigger(
        source=str(numeric_failure_without_added_delimiter["source_text"]),
        aggregate_target=str(numeric_failure_without_added_delimiter["target_text"]),
        primary_rows=[numeric_failure_without_added_delimiter],
        row_aligned=True,
    )
    assert trigger["contains_current_product_hard_failure"] is True
    assert trigger["target_only_delimiter_additions"] == {}
    assert trigger["eligible"] is False


def test_candidate_is_source_relative_and_does_not_require_bad_baseline_alpha() -> None:
    source = "Light passes through glass."
    candidate = "Свет проходит сквозь стекло."
    selection = evaluate_tc_big_delimiter_candidate(source, candidate)
    assert selection["accepted"] is True
    assert selection["strictly_eligible"] is True
    assert selection["target_only_delimiter_additions"] == {}
    assert MIN_SOURCE_ALPHA_RATIO <= selection["source_alpha_ratio"] <= MAX_SOURCE_ALPHA_RATIO
    assert selection["baseline_target_alpha_non_decrease_required"] is False


def test_candidate_rejects_emphasis_loss_even_when_other_shape_is_clean() -> None:
    source = "_Light_ passes through glass."
    candidate = "Свет проходит сквозь стекло."
    selection = evaluate_tc_big_delimiter_candidate(source, candidate)
    assert selection["emphasis_markup"]["passed"] is False
    assert selection["accepted"] is False


def test_candidate_rejects_target_only_delimiter_and_source_relative_length_extremes() -> None:
    source = "Light passes through glass."
    added = evaluate_tc_big_delimiter_candidate(source, "Свет (проходит) сквозь стекло.")
    assert added["target_only_delimiter_additions"] == {"(": 1, ")": 1}
    assert added["accepted"] is False

    too_short = evaluate_tc_big_delimiter_candidate(source, "Свет.")
    assert too_short["source_alpha_ratio"] < MIN_SOURCE_ALPHA_RATIO
    assert too_short["source_alpha_ratio_passed"] is False
    assert too_short["accepted"] is False

    too_long = evaluate_tc_big_delimiter_candidate(
        source,
        "Свет проходит сквозь совершенно прозрачное толстое стекло без каких-либо заметных изменений.",
    )
    assert too_long["source_alpha_ratio"] > MAX_SOURCE_ALPHA_RATIO
    assert too_long["source_alpha_ratio_passed"] is False
    assert too_long["accepted"] is False


def test_context_inventory_marks_cut_through_row_non_aligned_and_never_triggers() -> None:
    # Exact Stage10 context is [0, 11) == "Alpha beta ". The second current
    # Stage12 row starts inside that context at byte 10 and extends beyond it,
    # reproducing the run-9 context-2480 geometry class without target slicing.
    content = "Alpha beta gamma."
    context_rows = [
        {
            "id": 101,
            "sequence_number": 0,
            "source_start": 0,
            "source_end": 11,
            "source_text": content[:11],
            "target_text": "",
            "payload": {},
        }
    ]
    first = _row(
        1,
        content[:10],
        "Альфа (бета)",
        source_start=0,
        context_start=0,
        context_end=0,
    )
    second = _row(
        2,
        content[10:],
        "гамма.",
        source_start=10,
        context_start=1,
        context_end=1,
    )
    cases = _context_inventory(
        content=content,
        base_rows=[first, second],
        context_rows=context_rows,
    )
    assert len(cases) == 1
    case = cases[0]
    assert case["source_text"] == content[:11]
    assert case["trigger"]["replacement_row_aligned"] is False
    assert case["trigger"]["eligible"] is False
    assert case["primary_rows"] == []
    assert [int(row["id"]) for row in case["overlapping_rows"]] == [1, 2]


def test_disabled_run_delegates_exactly_to_base_without_tc_big_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    expected = {"translation_run_id": 91, "sentinel": "base-exact"}
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
        lambda: (_ for _ in ()).throw(AssertionError("TC-big runtime must not be probed when disabled")),
    )

    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=17,
        parameters={
            "beam_size": 6,
            "enable_tc_big_target_delimiter_rescue": False,
            "tc_big_target_delimiter_rescue_contract": TC_BIG_DELIMITER_RESCUE_CONTRACT,
        },
    )
    assert result is expected
    assert observed["context_run_id"] == 17
    assert observed["implementation"] == "opus-en-ru-ct2"
    assert observed["parameters"] == {"beam_size": 6}


def test_enabled_run_persists_only_raw_selected_context_and_copies_untouched_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    content = "Light passes through glass. Clean row."
    first_source = "Light passes through glass. "
    second_source = "Clean row."
    first = _row(
        11,
        first_source,
        "Свет (проходит) сквозь стекло. ",
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
        "translation_run_id": 90,
        "document_version_id": 7,
        "model_request_count": 100,
        "sentinel": "base-output",
    }
    base_run = {"id": 90, "output": base_output, "output_sha256": "a" * 64}
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
        if int(run_id) == 90 and kind == "translation_segment":
            return [first, second]
        if int(run_id) == 17 and kind == "context_sentence":
            return context_rows
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_get_run_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (91, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["run_id"] = run_id
        completed["output"] = output
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True, "revision": "pinned"})

    raw_target = "Свет проходит сквозь стекло."

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu"
            assert compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [first_source]
            assert (beam_size, num_hypotheses, max_decoding_length) == (6, 6, 512)
            return [[
                {"rank": 0, "text": raw_target, "score": -0.1},
                {"rank": 1, "text": "Свет проходит через стекло.", "score": -0.2},
                {"rank": 2, "text": raw_target, "score": -0.3},
                {"rank": 3, "text": raw_target, "score": -0.4},
                {"rank": 4, "text": raw_target, "score": -0.5},
                {"rank": 5, "text": raw_target, "score": -0.6},
            ]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)

    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=17,
        parameters={"enable_tc_big_target_delimiter_rescue": True},
    )
    assert result["translation_run_id"] == 91
    assert result["tc_big_target_delimiter_rescue_attempt_count"] == 1
    assert result["tc_big_target_delimiter_rescue_accepted_count"] == 1
    assert result["tc_big_target_delimiter_rescue_rejected_count"] == 0
    assert result["tc_big_target_delimiter_rescue_selected_ranks"] == [0]
    assert result["tc_big_target_delimiter_rescue_selected_targets"] == [raw_target]
    assert result["source_bytes_rewritten"] is False
    assert result["target_rewriting"] is False
    assert result["placeholders"] is False
    assert result["post_translation_literal_injection"] is False
    assert result["corpus_specific_target_patches"] is False

    items = completed["items"]
    assert isinstance(items, list)
    assert len(items) == 2
    assert "".join(str(item["source_text"]) for item in items) == content
    rescued = items[0]
    untouched = items[1]
    assert rescued["source_text"] == first_source
    assert rescued["target_text"] == raw_target
    rescue = rescued["payload"]["tc_big_target_delimiter_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["base_translation_segment_ids"] == [11]
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert rescue["placeholders"] is False
    assert rescue["post_translation_literal_injection"] is False
    assert rescue["corpus_specific_target_patches"] is False
    assert rescued["payload"]["hypotheses"][0]["text"] == rescued["target_text"]

    assert untouched["source_text"] == second["source_text"]
    assert untouched["target_text"] == second["target_text"]
    untouched_rescue = untouched["payload"]["tc_big_target_delimiter_rescue"]
    assert untouched_rescue["applied"] is False
    assert untouched_rescue["base_translation_segment_id"] == 12
