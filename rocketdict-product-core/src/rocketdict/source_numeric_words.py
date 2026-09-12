from __future__ import annotations

"""Conservative source-side English number-word licences.

The numeric hard gate primarily compares explicit digit literals.  This helper
allows an explicit English number word to license an equivalent target digit,
without requiring a translation to render prose numbers as digits.

Compound scale handling is intentionally narrow.  Only uninterrupted
``<cardinal> hundred thousand[ thousand ...]`` chains (and final
``thousandth``) are composed.  Coordinators such as ``and``/``or`` terminate a
chain, so elliptical expressions like ``two and three hundred`` are not
silently collapsed into a single value.
"""

from collections import Counter
import re
from typing import Mapping

_WORD_RE = re.compile(r"(?<![A-Za-z])([A-Za-z]+)(?![A-Za-z])")
_DETERMINERS = {"a", "an"}
_THOUSAND_SCALES = {"thousand", "thousandth"}


def _compound_hundred_thousand(
    words: list[str],
    index: int,
    cardinal_words: Mapping[str, int],
) -> tuple[int, int] | None:
    """Return ``(value, next_index)`` for one unambiguous scale chain.

    The accepted grammar deliberately requires an explicit head, ``hundred``,
    and at least one adjacent thousand scale.  It therefore covers historical
    forms such as ``ten hundred thousand`` and ``an hundred thousand thousand``
    while refusing to bridge conjunctions/disjunctions.
    """

    cursor = index
    word = words[cursor]
    if word in _DETERMINERS:
        head = 1
        cursor += 1
    else:
        head_value = cardinal_words.get(word)
        if head_value is None or word == "hundred":
            return None
        head = int(head_value)
        cursor += 1
        # Preserve the existing tens+units equivalence inside the explicit
        # scale head, e.g. ``twenty one hundred thousand``.
        if (
            20 <= head < 100
            and head % 10 == 0
            and cursor < len(words)
            and 0 < int(cardinal_words.get(words[cursor], 0) or 0) < 10
        ):
            head += int(cardinal_words[words[cursor]])
            cursor += 1

    if cursor >= len(words) or words[cursor] != "hundred":
        return None
    cursor += 1
    if cursor >= len(words) or words[cursor] not in _THOUSAND_SCALES:
        return None

    value = head * 100
    while cursor < len(words) and words[cursor] in _THOUSAND_SCALES:
        scale_word = words[cursor]
        value *= 1000
        cursor += 1
        if scale_word == "thousandth":
            break
    return value, cursor


def extract_spelled_numeric_licenses(
    source: str,
    *,
    cardinal_words: Mapping[str, int],
    ordinal_words: Mapping[str, int],
) -> Counter[str]:
    """Return conservative digit licences for explicit English number words."""

    words = _WORD_RE.findall(source.casefold())
    out: Counter[str] = Counter()
    index = 0
    while index < len(words):
        compound = _compound_hundred_thousand(words, index, cardinal_words)
        if compound is not None:
            value, index = compound
            out[str(value)] += 1
            continue

        word = words[index]
        ordinal = ordinal_words.get(word)
        if ordinal is not None:
            out[str(int(ordinal))] += 1
            index += 1
            continue

        value = cardinal_words.get(word)
        if value is None:
            index += 1
            continue
        value = int(value)
        if (
            20 <= value < 100
            and value % 10 == 0
            and index + 1 < len(words)
            and 0 < int(cardinal_words.get(words[index + 1], 0) or 0) < 10
        ):
            out[str(value + int(cardinal_words[words[index + 1]]))] += 1
            index += 2
            continue
        out[str(value)] += 1
        index += 1
    return out
