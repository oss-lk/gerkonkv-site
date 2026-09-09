from __future__ import annotations

import re

from rocketdict.translation_rescue import (
    RESCUE_CONTRACT,
    build_selective_resegmentation_chunks,
    evaluate_candidate_context,
    evaluate_primary_context_trigger,
)


def _tokens(content: str) -> list[dict]:
    rows: list[dict] = []
    for index, match in enumerate(re.finditer(r"[A-Za-z_]+|\d+|[;:]", content)):
        rows.append({
            "sequence_number": index,
            "source_start": match.start(),
            "source_end": match.end(),
            "source_text": match.group(0),
            "payload": {"flags": {"is_space": False}},
        })
    return rows


def test_semicolon_candidate_moves_only_the_over_budget_cut_backward() -> None:
    content = "alpha beta gamma 25; delta epsilon zeta eta 30 theta"
    chunks = build_selective_resegmentation_chunks(
        content,
        start=0,
        end=len(content),
        tokens=_tokens(content),
        spans=[],
        preferred_tokens=6,
    )

    assert "".join(row["text"] for row in chunks) == content
    assert chunks[0]["text"] == "alpha beta gamma 25; "
    assert chunks[0]["split_mode"] == "semicolon_backtrack"
    assert chunks[0]["backtrack_tokens"] == 1
    assert chunks[-1]["end"] == len(content)


def test_semicolon_adjacent_to_protected_emphasis_is_not_a_candidate() -> None:
    content = "_r_; _s_ alpha beta gamma delta"
    tokens = _tokens(content)
    # Gutenberg emphasis spans end/start immediately around the semicolon cut.
    spans = [(0, 3, "emphasis"), (5, 8, "emphasis")]
    chunks = build_selective_resegmentation_chunks(
        content,
        start=0,
        end=len(content),
        tokens=tokens,
        spans=spans,
        preferred_tokens=3,
    )

    assert chunks[0]["split_mode"] == "maintained"
    assert chunks[0]["text"] != "_r_; "
    assert "".join(row["text"] for row in chunks) == content


def test_primary_trigger_accepts_only_isolated_missing_numeric_content() -> None:
    trigger = evaluate_primary_context_trigger([
        {
            "source_text": "the value was 25 and later 30",
            "target_text": "значение позже было 30",
        }
    ])
    assert trigger["contract"] == RESCUE_CONTRACT
    assert trigger["eligible"] is True
    assert trigger["missing_literal_count"] == 1

    prime_corruption = evaluate_primary_context_trigger([
        {"source_text": "the angle is 5''", "target_text": "угол равен 5 футов"}
    ])
    assert prime_corruption["eligible"] is False

    duplicate = evaluate_primary_context_trigger([
        {"source_text": "the value is 25", "target_text": "значение 25 и 25"}
    ])
    assert duplicate["eligible"] is False


def test_candidate_requires_full_strict_cleanliness_and_non_decreasing_alpha() -> None:
    primary = [
        {
            "source_text": "the value was 25 and later 30",
            "target_text": "значение позже было 30",
        }
    ]
    candidate = [
        {"source_text": "the value was 25;", "target_text": "значение было 25;"},
        {"source_text": "and later 30", "target_text": "а позднее стало 30"},
    ]
    selection = evaluate_candidate_context(primary, candidate)
    assert selection["strict_clean"] is True
    assert selection["numeric_clean"] is True
    assert selection["target_alpha_non_decreasing"] is True
    assert selection["accepted"] is True

    compressed = evaluate_candidate_context(
        primary,
        [{"source_text": "the value was 25 and later 30", "target_text": "это 25 30"}],
    )
    assert compressed["strict_clean"] is True
    assert compressed["target_alpha_non_decreasing"] is False
    assert compressed["accepted"] is False
