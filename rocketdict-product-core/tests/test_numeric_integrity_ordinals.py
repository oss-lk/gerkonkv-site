from __future__ import annotations

import pytest

from rocketdict.numeric_integrity import CONTRACT, compare_numeric_integrity


@pytest.mark.parametrize(
    ("source", "target", "credit"),
    [
        ("18th Observation", "в восемнадцатом наблюдении", {"18": 1}),
        ("6th Observation", "шестого наблюдения", {"6": 1}),
        (
            "4th, 14th, 16th and 18th Observations",
            "четвертого, четырнадцатого, шестнадцатого и восемнадцатого наблюдений",
            {"4": 1, "14": 1, "16": 1, "18": 1},
        ),
        ("10th and 21st Observations", "десятым и 21-м наблюдениями", {"10": 1}),
        ("121st experiment", "сто двадцать первого опыта", {"121": 1}),
    ],
)
def test_digit_ordinals_accept_matching_russian_ordinal_words(
    source: str, target: str, credit: dict[str, int]
) -> None:
    result = compare_numeric_integrity(source, target)
    assert result["contract"] == CONTRACT
    assert result["passed"] is True
    assert result["missing"] == {}
    assert result["target_russian_ordinal_credit"] == credit


def test_cardinal_source_is_not_licensed_by_russian_ordinal_word() -> None:
    result = compare_numeric_integrity("18 observations", "в восемнадцатом наблюдении")
    assert result["passed"] is False
    assert result["missing"] == {"18": 1}
    assert result["target_russian_ordinal_credit"] == {}


def test_old_d_ordinal_not_licensed_by_russian_word_equivalence() -> None:
    result = compare_numeric_integrity("42d observation", "сорок втором наблюдении")
    assert result["passed"] is False
    assert result["missing"] == {"42": 1}
    assert result["source_digit_ordinals"] == {}


def test_technical_identifier_digits_are_not_licensed_by_russian_ordinals() -> None:
    result = compare_numeric_integrity("Points 2D and 2E remain", "точки второй и второй остаются")
    assert result["passed"] is False
    assert result["missing"] == {"2": 2}
    assert result["target_russian_ordinal_credit"] == {}


def test_unrelated_target_ordinal_words_do_not_become_numeric_additions() -> None:
    result = compare_numeric_integrity("plain observation", "в шестом наблюдении")
    assert result["passed"] is True
    assert result["required"] == {}
    assert result["unlicensed_additions"] == {}
    assert result["target_russian_ordinal_candidates"] == {"6": 1}
    assert result["target_russian_ordinal_credit"] == {}


def test_explicit_target_literal_still_wins_without_double_credit() -> None:
    result = compare_numeric_integrity("18th Observation", "18-е, восемнадцатое наблюдение")
    assert result["passed"] is True
    assert result["explicit_observed"] == {"18": 1}
    assert result["target_russian_ordinal_credit"] == {}
