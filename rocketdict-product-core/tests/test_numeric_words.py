from __future__ import annotations

import pytest

from rocketdict.numeric_words import extract_russian_ordinals


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("в восемнадцатом наблюдении", ["18"]),
        ("шестого наблюдения", ["6"]),
        (
            "четвертого, четырнадцатого, шестнадцатого и восемнадцатого наблюдений",
            ["4", "14", "16", "18"],
        ),
        ("десятым и двадцать первым наблюдениями", ["10", "21"]),
        ("сто двадцать первого опыта", ["121"]),
        ("сороковой схемой", ["40"]),
        ("третьего опыта", ["3"]),
    ],
)
def test_extract_russian_ordinals(text: str, expected: list[str]) -> None:
    assert [match.canonical for match in extract_russian_ordinals(text)] == expected


def test_cardinal_words_are_not_treated_as_ordinals() -> None:
    assert extract_russian_ordinals("восемнадцать наблюдений и шесть опытов") == []


def test_unrelated_prose_is_ignored() -> None:
    assert extract_russian_ordinals("обычный русский текст без порядкового числительного") == []
