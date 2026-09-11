from __future__ import annotations

from rocketdict.translation_rescue import RESCUE_CONTRACT, SELECTOR_CONTRACT
from rocketdict.translation_rescue_stage import (
    MAX_WHOLE_CONTEXT_NLP_TOKENS,
    SELECTED_PHASE,
    WHOLE_CONTEXT_RESCUE_CONTRACT,
    WHOLE_CONTEXT_SELECTED_PHASE,
    _candidate_rows,
    _primary_parameters,
    _rows_cover_context,
    _whole_context_chunk,
)


def test_primary_parameters_strip_rescue_selection_from_primary_identity() -> None:
    primary = {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "num_hypotheses": 1,
        "request_batch_size": 48,
    }
    enabled = {
        **primary,
        "enable_selective_resegmentation_rescue": True,
        "selective_resegmentation_rescue_contract": RESCUE_CONTRACT,
        "selective_resegmentation_selector_contract": SELECTOR_CONTRACT,
        "selective_resegmentation_phase": SELECTED_PHASE,
        "enable_whole_context_rescue": True,
        "whole_context_rescue_contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
        "whole_context_rescue_selector_contract": SELECTOR_CONTRACT,
        "whole_context_rescue_phase": WHOLE_CONTEXT_SELECTED_PHASE,
        "whole_context_rescue_max_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
    }
    disabled = {
        **enabled,
        "enable_selective_resegmentation_rescue": False,
        "enable_whole_context_rescue": False,
    }

    assert _primary_parameters(enabled) == primary
    assert _primary_parameters(disabled) == primary
    assert enabled["enable_selective_resegmentation_rescue"] is True
    assert enabled["selective_resegmentation_phase"] == SELECTED_PHASE
    assert enabled["enable_whole_context_rescue"] is True
    assert enabled["whole_context_rescue_phase"] == WHOLE_CONTEXT_SELECTED_PHASE


def test_rows_cover_context_requires_exact_contiguous_whole_context() -> None:
    source = "alpha 25; beta 30"
    exact = [
        {
            "source_start": 0,
            "source_end": 10,
            "source_text": "alpha 25; ",
        },
        {
            "source_start": 10,
            "source_end": len(source),
            "source_text": "beta 30",
        },
    ]
    assert _rows_cover_context(exact, start=0, end=len(source), source=source) is True

    gap = [
        exact[0],
        {
            "source_start": 11,
            "source_end": len(source),
            "source_text": "eta 30",
        },
    ]
    assert _rows_cover_context(gap, start=0, end=len(source), source=source) is False

    partial = [exact[0]]
    assert _rows_cover_context(partial, start=0, end=len(source), source=source) is False

    wrong_source = [dict(exact[0]), dict(exact[1])]
    wrong_source[1]["source_text"] = "BETA 30"
    assert _rows_cover_context(
        wrong_source, start=0, end=len(source), source=source
    ) is False


def test_whole_context_chunk_is_exact_unsplit_source() -> None:
    source = "alpha 25; beta 30; gamma 40"
    chunk = _whole_context_chunk(
        source=source,
        start=100,
        end=100 + len(source),
        token_count=9,
    )

    assert chunk == {
        "start": 100,
        "end": 100 + len(source),
        "text": source,
        "token_count": 9,
        "split_mode": "whole_context",
        "backtrack_tokens": 0,
    }


def test_candidate_rows_preserve_raw_rank0_target_exactly() -> None:
    raw_target = "  значение 25  "
    rows = _candidate_rows(
        context_sequence=7,
        chunks=[
            {
                "start": 0,
                "end": 9,
                "text": "value 25;",
                "token_count": 3,
                "split_mode": "semicolon_backtrack",
                "backtrack_tokens": 1,
            }
        ],
        hypotheses=[[{"text": raw_target, "score": -1.0}]],
        primary_rows=[
            {
                "id": 11,
                "source_start": 0,
                "source_end": 9,
                "source_text": "value 25;",
                "target_text": "значение",
            }
        ],
        trigger={"missing_literal_count": 1},
        selection={
            "candidate_verdicts": [{"strictly_eligible": True}],
            "target_alpha_primary": 8,
            "target_alpha_candidate": 8,
        },
        preferred_tokens=64,
        generation={"beam_size": 6, "num_hypotheses": 1},
    )

    assert rows[0]["target_text"] == raw_target
    rescue = rows[0]["payload"]["selective_resegmentation_rescue"]
    assert rescue["raw_model_rank0"] is True
    assert rescue["target_rewriting"] is False
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["placeholders"] is False
    assert rescue["post_translation_literal_injection"] is False
    assert rows[0]["payload"]["whole_context_rescue"]["applied"] is False


def test_whole_context_candidate_has_distinct_raw_model_provenance() -> None:
    source = "the value was 25 and later 30 and finally 40"
    raw_target = "значение было 25, позже 30 и наконец 40"
    rows = _candidate_rows(
        context_sequence=9,
        chunks=[
            _whole_context_chunk(
                source=source,
                start=50,
                end=50 + len(source),
                token_count=11,
            )
        ],
        hypotheses=[[{"text": raw_target, "score": -2.0}]],
        primary_rows=[
            {
                "id": 21,
                "source_start": 50,
                "source_end": 70,
                "source_text": "the value was 25 and ",
                "target_text": "значение было",
            },
            {
                "id": 22,
                "source_start": 70,
                "source_end": 50 + len(source),
                "source_text": source[20:],
                "target_text": "позже 30 и наконец 40",
            },
        ],
        trigger={"missing_literal_count": 1},
        selection={
            "candidate_verdicts": [{"strictly_eligible": True}],
            "target_alpha_primary": 20,
            "target_alpha_candidate": 30,
        },
        preferred_tokens=64,
        generation={"beam_size": 6, "num_hypotheses": 1},
        strategy="whole_context",
    )

    assert len(rows) == 1
    assert rows[0]["source_text"] == source
    assert rows[0]["target_text"] == raw_target
    assert rows[0]["payload"]["planner"]["rescue_strategy"] == "whole_context"
    whole = rows[0]["payload"]["whole_context_rescue"]
    assert whole["contract"] == WHOLE_CONTEXT_RESCUE_CONTRACT
    assert whole["raw_model_rank0"] is True
    assert whole["target_rewriting"] is False
    assert whole["source_bytes_rewritten"] is False
    assert whole["placeholders"] is False
    assert whole["post_translation_literal_injection"] is False
    assert rows[0]["payload"]["selective_resegmentation_rescue"]["applied"] is False
