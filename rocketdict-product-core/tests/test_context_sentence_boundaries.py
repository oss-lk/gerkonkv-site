from __future__ import annotations

from rocketdict.context_sentence_boundaries import (
    STAGE10_BOUNDARY_POLICY,
    coalesce_spacy_sentence_groups,
    evaluate_spacy_sentence_boundary,
)


def _token(content: str, text: str, start: int, *, token_index: int) -> dict:
    assert content[start : start + len(text)] == text
    return {
        "source_start": start,
        "source_end": start + len(text),
        "source_text": text,
        "payload": {"token_index": token_index},
    }


def test_lowercase_continuation_without_terminal_is_coalesced() -> None:
    content = "Nor do I see but that light returns."
    but = content.index("but")
    that = content.index("that")
    grouped = {
        0: [_token(content, "but", but, token_index=0)],
        1: [_token(content, "that", that, token_index=1)],
    }
    decision = evaluate_spacy_sentence_boundary(content, 0, grouped[0], 1, grouped[1])
    assert decision["policy"] == STAGE10_BOUNDARY_POLICY
    assert decision["merge"] is True
    assert decision["reason"] == "lowercase_continuation_without_terminal"
    assert decision["source_offset"] == that

    groups = coalesce_spacy_sentence_groups(grouped, content)
    assert len(groups) == 1
    assert groups[0]["sentence_indices"] == [0, 1]
    assert len(groups[0]["coalesced_boundaries"]) == 1


def test_terminal_punctuation_blocks_lowercase_merge_even_after_quote() -> None:
    content = 'Stop." then continue.'
    left = [_token(content, '"', content.index('"'), token_index=1)]
    # Include the terminal punctuation token so the source prefix ends in ."
    left.insert(0, _token(content, ".", content.index("."), token_index=0))
    right = [_token(content, "then", content.index("then"), token_index=2)]
    decision = evaluate_spacy_sentence_boundary(content, 0, left, 1, right)
    assert decision["merge"] is False
    assert decision["source_terminal_punctuation"] is True
    assert decision["reason"] == "source_terminal_punctuation"


def test_paragraph_break_blocks_merge_without_terminal_punctuation() -> None:
    content = "Heading\n\ncontinuation"
    left = [_token(content, "Heading", 0, token_index=0)]
    right = [_token(content, "continuation", content.index("continuation"), token_index=1)]
    decision = evaluate_spacy_sentence_boundary(content, 0, left, 1, right)
    assert decision["merge"] is False
    assert decision["paragraph_break"] is True
    assert decision["reason"] == "paragraph_break"


def test_uppercase_next_sentence_is_not_coalesced() -> None:
    content = "Heading Next"
    left = [_token(content, "Heading", 0, token_index=0)]
    right = [_token(content, "Next", content.index("Next"), token_index=1)]
    decision = evaluate_spacy_sentence_boundary(content, 0, left, 1, right)
    assert decision["merge"] is False
    assert decision["lowercase_continuation"] is False
    assert decision["reason"] == "continuation_not_lowercase"


def test_non_whitespace_gap_fails_closed() -> None:
    content = "left--right"
    left = [_token(content, "left", 0, token_index=0)]
    right = [_token(content, "right", content.index("right"), token_index=1)]
    decision = evaluate_spacy_sentence_boundary(content, 0, left, 1, right)
    assert decision["merge"] is False
    assert decision["whitespace_only_gap"] is False
    assert decision["reason"] == "non_whitespace_source_gap"


def test_gutenberg_emphasis_math_boundary_is_treated_as_source_continuation() -> None:
    content = "Line C _prt_ B any where between the Ends."
    b_start = content.index("B")
    any_start = content.index("any")
    grouped = {
        17: [_token(content, "B", b_start, token_index=7)],
        18: [_token(content, "any", any_start, token_index=8)],
    }
    groups = coalesce_spacy_sentence_groups(grouped, content)
    assert len(groups) == 1
    assert groups[0]["sentence_indices"] == [17, 18]
    assert groups[0]["coalesced_boundaries"][0]["source_offset"] == any_start


def test_nonconsecutive_parser_indices_fail_closed() -> None:
    content = "left right"
    left = [_token(content, "left", 0, token_index=0)]
    right = [_token(content, "right", content.index("right"), token_index=1)]
    decision = evaluate_spacy_sentence_boundary(content, 3, left, 5, right)
    assert decision["merge"] is False
    assert decision["reason"] == "non_consecutive_parser_indices"


def test_multiple_false_splits_can_coalesce_as_one_context_group() -> None:
    content = "alpha beta gamma. Delta."
    grouped = {
        0: [_token(content, "alpha", content.index("alpha"), token_index=0)],
        1: [_token(content, "beta", content.index("beta"), token_index=1)],
        2: [
            _token(content, "gamma", content.index("gamma"), token_index=2),
            _token(content, ".", content.index("."), token_index=3),
        ],
        3: [_token(content, "Delta", content.index("Delta"), token_index=4)],
    }
    groups = coalesce_spacy_sentence_groups(grouped, content)
    assert [group["sentence_indices"] for group in groups] == [[0, 1, 2], [3]]
    assert len(groups[0]["coalesced_boundaries"]) == 2



def test_figure_reference_lowercase_markup_continuation_is_coalesced() -> None:
    content = "Suppose that RS [in _Fig._ 1.] represents the ray."
    rs = content.index("RS")
    reference = content.index("[in")
    decision = evaluate_spacy_sentence_boundary(
        content, 0, [_token(content, "RS", rs, token_index=0)],
        1, [_token(content, "[in _Fig._ 1.]", reference, token_index=1)],
    )
    assert decision["merge"] is True
    assert decision["lowercase_continuation"] is True
    assert decision["source_offset"] == reference


def test_split_inside_gutenberg_emphasis_is_coalesced() -> None:
    content = "Variable _q_ is on the axis."
    underscore = content.index("_q_")
    q_start = underscore + 1
    decision = evaluate_spacy_sentence_boundary(
        content, 7, [_token(content, "_", underscore, token_index=7)],
        8, [_token(content, "q_", q_start, token_index=8)],
    )
    assert decision["merge"] is True
    assert decision["lowercase_continuation"] is True


def test_split_inside_gutenberg_greek_markup_is_coalesced() -> None:
    content = "Line _A[Greek:a]_ in the figure."
    left_start = content.index("[Greek:")
    right_start = content.index("a]")
    decision = evaluate_spacy_sentence_boundary(
        content, 2, [_token(content, "[Greek:", left_start, token_index=2)],
        3, [_token(content, "a]", right_start, token_index=3)],
    )
    assert decision["merge"] is True
    assert decision["source_offset"] == right_start


def test_lowercase_conjunction_continuation_is_coalesced() -> None:
    content = "The ratio is fixed; and these sines remain proportional."
    left_start = content.index("and")
    right_start = content.index("these")
    decision = evaluate_spacy_sentence_boundary(
        content, 11, [_token(content, "and", left_start, token_index=11)],
        12, [_token(content, "these", right_start, token_index=12)],
    )
    assert decision["merge"] is True


def test_markup_with_uppercase_first_lexical_character_stays_separate() -> None:
    content = "Heading [Next] section"
    right_start = content.index("[Next]")
    decision = evaluate_spacy_sentence_boundary(
        content, 0, [_token(content, "Heading", 0, token_index=0)],
        1, [_token(content, "[Next]", right_start, token_index=1)],
    )
    assert decision["merge"] is False
    assert decision["lowercase_continuation"] is False
    assert decision["reason"] == "continuation_not_lowercase"
