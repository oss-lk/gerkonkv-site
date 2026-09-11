from __future__ import annotations

from rocketdict.translation_length_rescue_stage import (
    LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
    LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
    LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE,
    _base_parameters,
    _candidate_row,
    evaluate_length_failure_candidate,
    evaluate_length_failure_trigger,
)


def test_base_parameters_strip_only_length_rescue_identity_controls() -> None:
    parameters = {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "num_hypotheses": 1,
        "enable_whole_context_rescue": False,
        "enable_length_failure_whole_context_rescue": True,
        "length_failure_whole_context_rescue_contract": (
            LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
        ),
        "length_failure_whole_context_rescue_selector_contract": (
            LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
        ),
        "length_failure_whole_context_rescue_phase": (
            LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE
        ),
        "length_failure_whole_context_rescue_max_nlp_tokens": 160,
    }

    assert _base_parameters(parameters) == {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "num_hypotheses": 1,
        "enable_whole_context_rescue": False,
    }


def test_length_failure_trigger_requires_existing_maintained_length_failure() -> None:
    rows = [
        {
            "id": 10,
            "source_start": 0,
            "source_end": 13,
            "source_text": "being\n10000. ",
            "target_text": "10000.",
        },
        {
            "id": 11,
            "source_start": 13,
            "source_end": 26,
            "source_text": "Radius stays. ",
            "target_text": "Радиус остаётся. ",
        },
    ]

    trigger = evaluate_length_failure_trigger(rows)

    assert trigger["eligible"] is True
    assert trigger["failure_count"] == 1
    assert trigger["failures"][0]["translation_segment_id"] == 10
    assert trigger["failures"][0]["source_start"] == 0
    assert trigger["failures"][0]["source_end"] == 13


def test_length_failure_selector_can_accept_strict_candidate_with_lower_alpha() -> None:
    source = "Radius being 10000."
    target = "Радиус 10000."
    primary_rows = [
        {
            "target_text": "Радиус был чрезвычайно протяжённый 10000.",
        }
    ]

    selection = evaluate_length_failure_candidate(
        primary_rows,
        source=source,
        target=target,
    )

    assert selection["candidate_verdict"]["strictly_eligible"] is True
    assert selection["accepted"] is True
    assert selection["target_alpha_non_decreasing"] is False
    assert selection["target_alpha_non_decreasing_required"] is False
    assert selection["target_alpha_delta"] < 0


def test_length_failure_candidate_row_preserves_raw_rank0_and_provenance() -> None:
    source = "Radius being 10000."
    target = "Радиус 10000."
    primary_rows = [
        {
            "id": 20,
            "source_start": 100,
            "source_end": 110,
            "source_text": "Radius bei",
            "target_text": "Радиус был длинный ",
        },
        {
            "id": 21,
            "source_start": 110,
            "source_end": 119,
            "source_text": "ng 10000.",
            "target_text": "10000.",
        },
    ]
    trigger = {
        "failure_count": 1,
        "failures": [
            {
                "translation_segment_id": 21,
                "source_start": 110,
                "source_end": 119,
                "length_ratio": 0.0,
                "verdict": {"length_passed": False},
            }
        ],
    }
    selection = evaluate_length_failure_candidate(
        primary_rows,
        source=source,
        target=target,
    )
    row = _candidate_row(
        context_sequence=7,
        chunk={
            "start": 100,
            "end": 100 + len(source),
            "text": source,
            "token_count": 4,
            "split_mode": "whole_context",
            "backtrack_tokens": 0,
        },
        hypotheses=[[{"text": target, "score": -1.0}][0]],
        primary_rows=primary_rows,
        trigger=trigger,
        selection=selection,
        preferred_tokens=64,
        max_nlp_tokens=160,
        generation={"beam_size": 6, "num_hypotheses": 1},
    )

    assert row["source_text"] == source
    assert row["target_text"] == target
    assert row["payload"]["selected_rank"] == 0
    assert row["payload"]["planner"]["rescue_strategy"] == "length_failure_whole_context"
    rescue = row["payload"]["length_failure_whole_context_rescue"]
    assert rescue["contract"] == LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
    assert rescue["selector_contract"] == LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
    assert rescue["trigger"] == "primary_length_ratio_failure"
    assert rescue["raw_model_rank0"] is True
    assert rescue["target_alpha_non_decreasing_required"] is False
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert rescue["placeholders"] is False
    assert rescue["post_translation_literal_injection"] is False
