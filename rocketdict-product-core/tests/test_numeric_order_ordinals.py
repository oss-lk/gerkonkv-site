from __future__ import annotations

from rocketdict.research_diagnostics import NUMERIC_ORDER_CONTRACT, compare_numeric_order


def test_numeric_order_accepts_russian_ordinal_word_equivalence_in_order() -> None:
    result = compare_numeric_order(
        "4th, 14th, 16th and 18th Observations",
        "четвертого, четырнадцатого, шестнадцатого и восемнадцатого наблюдений",
    )
    assert result["contract"] == NUMERIC_ORDER_CONTRACT
    assert result["passed"] is True
    assert result["required_sequence"] == ["4", "14", "16", "18"]
    assert result["required_is_english_digit_ordinal"] == [True, True, True, True]
    assert [row["kind"] for row in result["observed_events"]] == [
        "russian_ordinal_word",
        "russian_ordinal_word",
        "russian_ordinal_word",
        "russian_ordinal_word",
    ]


def test_numeric_order_accepts_mixed_russian_word_and_explicit_literal() -> None:
    result = compare_numeric_order(
        "10th and 21st Observations",
        "десятым и 21-м наблюдениями",
    )
    assert result["passed"] is True
    assert result["matched_required_count"] == 2


def test_numeric_order_does_not_use_russian_ordinal_for_cardinal_source() -> None:
    result = compare_numeric_order("18 observations", "в восемнадцатом наблюдении")
    assert result["passed"] is False
    assert result["matched_required_count"] == 0


def test_numeric_order_does_not_use_russian_ordinal_for_old_d_notation() -> None:
    result = compare_numeric_order("42d observation", "в сорок втором наблюдении")
    assert result["passed"] is False
    assert result["required_is_english_digit_ordinal"] == [False]


def test_numeric_order_rejects_wrong_or_reordered_ordinal_values() -> None:
    wrong = compare_numeric_order("6th then 18th", "седьмого, затем восемнадцатого")
    assert wrong["passed"] is False
    assert wrong["matched_required_count"] == 0

    reordered = compare_numeric_order("6th then 18th", "восемнадцатого, затем шестого")
    assert reordered["passed"] is False
    assert reordered["matched_required_count"] < 2
