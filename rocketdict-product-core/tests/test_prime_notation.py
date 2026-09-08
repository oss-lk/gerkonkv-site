from __future__ import annotations

import pytest

from rocketdict.prime_notation import (
    CONTRACT,
    compare_numeric_prime_notation,
    extract_numeric_prime_events,
)


def test_spaced_and_compact_prime_notation_are_equivalent() -> None:
    source = "5' 2'', and 53 deg. 4' 58''"
    target = "5'2'', и 53 градуса 4'58''"
    result = compare_numeric_prime_notation(source, target)
    assert result["contract"] == CONTRACT
    assert result["passed"] is True
    assert result["source_signature"] == [
        {"value": "5", "prime_count": 1},
        {"value": "2", "prime_count": 2},
        {"value": "4", "prime_count": 1},
        {"value": "58", "prime_count": 2},
    ]


def test_lost_prime_mark_is_detected_even_when_digits_survive() -> None:
    result = compare_numeric_prime_notation(
        "5' 2'', and 53 deg. 4' 58''",
        "5'2', и 53 градуса 4'58''",
    )
    assert result["passed"] is False
    assert result["target_signature"][1] == {"value": "2", "prime_count": 1}


def test_feet_mistranslation_does_not_masquerade_as_prime_preservation() -> None:
    result = compare_numeric_prime_notation(
        "it exceeds not 2'' 45''' or 3''.",
        "она не превышает 2 футов 45' или 3''.",
    )
    assert result["passed"] is False
    assert result["source_signature"] == [
        {"value": "2", "prime_count": 2},
        {"value": "45", "prime_count": 3},
        {"value": "3", "prime_count": 2},
    ]
    assert result["target_signature"] == [
        {"value": "45", "prime_count": 1},
        {"value": "3", "prime_count": 2},
    ]


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("diameter 1'699 Inches", "диаметр 1,699 дюйма"),
        ("values 0'000625 and 4'27", "значения 0,000625 и 4,27"),
    ],
)
def test_historical_apostrophe_decimals_are_not_prime_events(
    source: str, target: str
) -> None:
    assert extract_numeric_prime_events(source) == []
    assert compare_numeric_prime_notation(source, target)["passed"] is True


def test_unicode_prime_glyphs_are_equivalent_to_ascii_runs() -> None:
    result = compare_numeric_prime_notation(
        "26' 13'', 37' 5'', 45' 6'''",
        "26′13″, 37′5″, 45′6‴",
    )
    assert result["passed"] is True
