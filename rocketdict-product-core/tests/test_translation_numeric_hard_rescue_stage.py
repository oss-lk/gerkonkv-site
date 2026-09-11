from __future__ import annotations

from rocketdict.emphasis_markup import EMPHASIS_MARKUP_CONTRACT
from rocketdict.translation_numeric_hard_rescue_stage import (
    NUMERIC_HARD_FAILURE_TRIGGER_CONTRACT,
    NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
    NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE,
    NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
    _base_parameters,
    _candidate_row,
    evaluate_numeric_hard_failure_candidate,
    evaluate_numeric_hard_failure_trigger,
)
from rocketdict.translation_rescue import SELECTOR_CONTRACT


def _primary_rows() -> list[dict[str, object]]:
    return [
        {
            "id": 20,
            "source_start": 100,
            "source_end": 121,
            "source_text": "Salt _per deliquium_ ",
            "target_text": "Соль = per deliquium_ ",
        },
        {
            "id": 21,
            "source_start": 121,
            "source_end": 132,
            "source_text": "60 Degrees.",
            "target_text": "60 градусов.",
        },
    ]


def test_base_parameters_strip_only_numeric_hard_wrapper_controls() -> None:
    parameters = {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "enable_length_failure_whole_context_rescue": True,
        "enable_citation_boundary_pair_rescue": True,
        "enable_numeric_hard_failure_whole_context_rescue": True,
        "numeric_hard_failure_whole_context_rescue_contract": (
            NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
        ),
        "numeric_hard_failure_whole_context_rescue_selector_contract": (
            NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
        ),
        "numeric_hard_failure_whole_context_rescue_phase": (
            NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE
        ),
        "numeric_hard_failure_whole_context_rescue_max_nlp_tokens": 160,
    }

    assert _base_parameters(parameters) == {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "enable_length_failure_whole_context_rescue": True,
        "enable_citation_boundary_pair_rescue": True,
    }


def test_numeric_hard_trigger_requires_existing_product_numeric_failure() -> None:
    trigger = evaluate_numeric_hard_failure_trigger(_primary_rows())

    assert trigger["contract"] == NUMERIC_HARD_FAILURE_TRIGGER_CONTRACT
    assert trigger["eligible"] is True
    assert trigger["trigger"] == "primary_numeric_symbol_hard_failure"
    assert trigger["failure_count"] == 1
    assert trigger["failures"][0]["translation_segment_id"] == 20
    assert trigger["failures"][0]["verdict"]["passed"] is False


def test_numeric_hard_trigger_stays_off_for_clean_context() -> None:
    rows = _primary_rows()
    rows[0] = {
        **rows[0],
        "target_text": "Соль _per deliquium_ ",
    }
    trigger = evaluate_numeric_hard_failure_trigger(rows)
    assert trigger["eligible"] is False
    assert trigger["failure_count"] == 0


def test_numeric_hard_selector_accepts_strict_candidate_with_preserved_emphasis() -> None:
    source = "Salt _per deliquium_ 60 Degrees."
    target = "Соль _при расплывании_ при 60 градусах."

    selection = evaluate_numeric_hard_failure_candidate(
        _primary_rows(), source=source, target=target
    )

    assert selection["selector_contract"] == (
        NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
    )
    assert selection["base_selector_contract"] == SELECTOR_CONTRACT
    assert selection["base_selection"]["accepted"] is True
    assert selection["emphasis_markup_contract"] == EMPHASIS_MARKUP_CONTRACT
    assert selection["emphasis_markup_preserved"] is True
    assert selection["accepted"] is True


def test_numeric_hard_selector_vetoes_mechanically_clean_emphasis_loss() -> None:
    source = "Salt _per deliquium_ 60 Degrees."
    target = "Соль растворилась при 60 градусах."

    selection = evaluate_numeric_hard_failure_candidate(
        _primary_rows(), source=source, target=target
    )

    assert selection["base_selection"]["accepted"] is True
    assert selection["emphasis_markup"]["passed"] is False
    assert selection["emphasis_markup"]["source"]["complete_span_count"] == 1
    assert selection["emphasis_markup"]["target"]["complete_span_count"] == 0
    assert selection["emphasis_markup_preserved"] is False
    assert selection["accepted"] is False


def test_numeric_hard_candidate_row_preserves_raw_rank0_and_provenance() -> None:
    source = "Salt _per deliquium_ 60 Degrees."
    target = "Соль _при расплывании_ при 60 градусах."
    rows = _primary_rows()
    trigger = evaluate_numeric_hard_failure_trigger(rows)
    selection = evaluate_numeric_hard_failure_candidate(
        rows, source=source, target=target
    )

    row = _candidate_row(
        context_sequence=2725,
        chunk={
            "start": 100,
            "end": 100 + len(source),
            "text": source,
            "token_count": 7,
            "split_mode": "whole_context",
            "backtrack_tokens": 0,
        },
        hypotheses=[{"text": target, "score": -1.25}],
        primary_rows=rows,
        trigger=trigger,
        selection=selection,
        preferred_tokens=64,
        max_nlp_tokens=160,
        generation={"beam_size": 6, "num_hypotheses": 1},
    )

    assert row["source_text"] == source
    assert row["target_text"] == target
    assert row["payload"]["selected_rank"] == 0
    assert row["payload"]["planner"]["rescue_strategy"] == (
        "numeric_hard_failure_whole_context"
    )
    rescue = row["payload"]["numeric_hard_failure_whole_context_rescue"]
    assert rescue["contract"] == NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
    assert rescue["selector_contract"] == (
        NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
    )
    assert rescue["base_selector_contract"] == SELECTOR_CONTRACT
    assert rescue["emphasis_markup_contract"] == EMPHASIS_MARKUP_CONTRACT
    assert rescue["trigger"] == "primary_numeric_symbol_hard_failure"
    assert rescue["raw_model_rank0"] is True
    assert rescue["emphasis_markup_preserved"] is True
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert rescue["placeholders"] is False
    assert rescue["post_translation_literal_injection"] is False
