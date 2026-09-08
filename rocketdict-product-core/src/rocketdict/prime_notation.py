from __future__ import annotations

"""Conservative research diagnostic for numeric prime-mark notation.

This is intentionally *not* a Product hard gate. It distinguishes old
apostrophe-decimal forms such as ``1'699`` from numeric unit/angle notation
such as ``5' 2''`` or compact ``5'2''``. The diagnostic compares the ordered
(value, prime-count) events only; it never rewrites source or target text.

ASCII/curly apostrophes and Unicode prime glyphs are normalized to prime counts:
one-prime (', ’, ′), double-prime (″), and triple-prime (‴).
"""

from dataclasses import dataclass
import re
from typing import Any

CONTRACT = "rocketdict-maintained-numeric-prime-notation/1"

_MARK_ATOM = r"(?:['’′]|″|‴)"
_COMPACT_PAIR_RE = re.compile(
    rf"(?<!\d)(?P<left>\d+)(?P<separator>['’′])"
    rf"(?P<right>\d+)(?P<right_marks>{_MARK_ATOM}+)(?!\d)"
)
_TRAILING_RE = re.compile(
    rf"(?<!\d)(?P<number>\d+)\s*(?P<marks>{_MARK_ATOM}+)(?!\d)"
)


@dataclass(frozen=True)
class PrimeEvent:
    value: str
    prime_count: int
    start: int
    end: int
    raw: str


def _normalize_integer(raw: str) -> str:
    return raw.lstrip("0") or "0"


def _prime_count(raw: str) -> int:
    total = 0
    for char in raw:
        if char in {"'", "’", "′"}:
            total += 1
        elif char == "″":
            total += 2
        elif char == "‴":
            total += 3
        elif char.isspace():
            continue
        else:
            raise ValueError(f"Unsupported prime mark {char!r}")
    return total


def extract_numeric_prime_events(text: str) -> list[PrimeEvent]:
    """Extract ordered numeric prime-mark events without treating decimals as primes."""
    events: list[PrimeEvent] = []
    occupied: list[tuple[int, int]] = []

    # In ``4'58''`` the separator after 4 is a prime mark because the
    # right-hand number itself carries a terminal prime run. In ``1'699`` there
    # is no terminal prime run, so the apostrophe remains decimal notation.
    for match in _COMPACT_PAIR_RE.finditer(text):
        left_raw = match.group("left")
        separator = match.group("separator")
        right_raw = match.group("right")
        right_marks = match.group("right_marks")
        events.append(
            PrimeEvent(
                value=_normalize_integer(left_raw),
                prime_count=_prime_count(separator),
                start=match.start("left"),
                end=match.end("separator"),
                raw=text[match.start("left") : match.end("separator")],
            )
        )
        events.append(
            PrimeEvent(
                value=_normalize_integer(right_raw),
                prime_count=_prime_count(right_marks),
                start=match.start("right"),
                end=match.end("right_marks"),
                raw=text[match.start("right") : match.end("right_marks")],
            )
        )
        occupied.append((match.start(), match.end()))

    for match in _TRAILING_RE.finditer(text):
        if any(match.start() < end and match.end() > start for start, end in occupied):
            continue
        marks = match.group("marks")
        events.append(
            PrimeEvent(
                value=_normalize_integer(match.group("number")),
                prime_count=_prime_count(marks),
                start=match.start("number"),
                end=match.end("marks"),
                raw=text[match.start("number") : match.end("marks")],
            )
        )

    events.sort(key=lambda event: (event.start, event.end))
    return events


def compare_numeric_prime_notation(source: str, target: str) -> dict[str, Any]:
    source_events = extract_numeric_prime_events(source)
    target_events = extract_numeric_prime_events(target)
    source_signature = [
        {"value": event.value, "prime_count": event.prime_count}
        for event in source_events
    ]
    target_signature = [
        {"value": event.value, "prime_count": event.prime_count}
        for event in target_events
    ]
    return {
        "contract": CONTRACT,
        "source_events": [
            {
                "value": event.value,
                "prime_count": event.prime_count,
                "start": event.start,
                "end": event.end,
                "raw": event.raw,
            }
            for event in source_events
        ],
        "target_events": [
            {
                "value": event.value,
                "prime_count": event.prime_count,
                "start": event.start,
                "end": event.end,
                "raw": event.raw,
            }
            for event in target_events
        ],
        "source_signature": source_signature,
        "target_signature": target_signature,
        "passed": source_signature == target_signature,
    }
