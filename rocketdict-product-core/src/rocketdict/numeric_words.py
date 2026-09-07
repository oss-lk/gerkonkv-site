from __future__ import annotations

"""Dependency-free target-language numeric-word equivalences.

The maintained numeric hard gate normally reasons about explicit numeric
literals.  Real contiguous-Opticks evidence showed a narrower legitimate
translation equivalence: an English digit ordinal such as ``18th`` can be
rendered as the inflected Russian ordinal word ``восемнадцатом``.  This module
extracts Russian *ordinal* words conservatively so the numeric evaluator can
credit only a matching source ordinal requirement.

It intentionally does not treat arbitrary Russian cardinal words as target
numeric literals and it does not make unmatched target words into unlicensed
numeric additions.  That keeps idiomatic target wording outside the scope of a
literal-preservation gate while fixing the demonstrated ordinal false positive.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RussianOrdinalMatch:
    raw: str
    canonical: str
    start: int
    end: int


_RU_WORD_RE = re.compile(r"[А-Яа-яЁё]+", re.UNICODE)
_ORDINAL_SUFFIX = (
    r"(?:ый|ий|ой|ая|яя|ое|ее|ые|ие|ого|его|ой|ому|ему|ым|им|"
    r"ую|юю|ом|ем|ых|их|ыми|ими)"
)
_SIMPLE_STEMS: dict[int, str] = {
    1: r"перв",
    2: r"втор",
    4: r"четв[её]рт",
    5: r"пят",
    6: r"шест",
    7: r"седьм",
    8: r"восьм",
    9: r"девят",
    10: r"десят",
    11: r"одиннадцат",
    12: r"двенадцат",
    13: r"тринадцат",
    14: r"четырнадцат",
    15: r"пятнадцат",
    16: r"шестнадцат",
    17: r"семнадцат",
    18: r"восемнадцат",
    19: r"девятнадцат",
    20: r"двадцат",
    30: r"тридцат",
    40: r"сороков",
    50: r"пятидесят",
    60: r"шестидесят",
    70: r"семидесят",
    80: r"восьмидесят",
    90: r"девяност",
}
_SIMPLE_PATTERNS: tuple[tuple[int, re.Pattern[str]], ...] = tuple(
    (value, re.compile(rf"(?:{stem}){_ORDINAL_SUFFIX}", re.IGNORECASE))
    for value, stem in _SIMPLE_STEMS.items()
) + (
    (
        3,
        re.compile(
            r"(?:третий|третья|третье|третьи|третьего|третьей|третьему|"
            r"третьим|третьем|третью|третьих|третьими)",
            re.IGNORECASE,
        ),
    ),
)

# In compound Russian ordinals only the final ordinal component is inflected;
# preceding tens/hundreds remain cardinal lexical prefixes.  Supporting these
# exact prefixes prevents ``двадцать первого`` from being misread as bare 1.
_COMPOUND_PREFIXES: dict[str, int] = {
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
    "сто": 100,
    "двести": 200,
    "триста": 300,
    "четыреста": 400,
    "пятьсот": 500,
    "шестьсот": 600,
    "семьсот": 700,
    "восемьсот": 800,
    "девятьсот": 900,
}


def _simple_ordinal_value(word: str) -> int | None:
    for value, pattern in _SIMPLE_PATTERNS:
        if pattern.fullmatch(word):
            return value
    return None


def extract_russian_ordinals(text: str) -> list[RussianOrdinalMatch]:
    """Extract conservative Russian ordinal-word values with source spans.

    Simple ordinals from 1..20 and the round tens are recognized across common
    case/gender/number inflections.  Compound forms such as ``двадцать первого``
    and ``сто двадцать первого`` are combined when their lexical prefixes are
    exact.  The function does not parse general Russian number prose.
    """
    words = [
        (match.group(0).casefold(), match.start(), match.end())
        for match in _RU_WORD_RE.finditer(text)
    ]
    out: list[RussianOrdinalMatch] = []
    for index, (word, start, end) in enumerate(words):
        value = _simple_ordinal_value(word)
        if value is None:
            continue
        total = value
        span_start = start
        previous = index - 1
        if (
            value < 10
            and previous >= 0
            and words[previous][0] in _COMPOUND_PREFIXES
            and _COMPOUND_PREFIXES[words[previous][0]] < 100
        ):
            total += _COMPOUND_PREFIXES[words[previous][0]]
            span_start = words[previous][1]
            previous -= 1
        if (
            total < 100
            and previous >= 0
            and words[previous][0] in _COMPOUND_PREFIXES
            and _COMPOUND_PREFIXES[words[previous][0]] >= 100
        ):
            total += _COMPOUND_PREFIXES[words[previous][0]]
            span_start = words[previous][1]
        out.append(
            RussianOrdinalMatch(
                raw=text[span_start:end],
                canonical=str(total),
                start=span_start,
                end=end,
            )
        )
    return out
