from __future__ import annotations

"""Maintained numeric/symbol integrity semantics for Product Stage15.

This is a forward implementation of the documented Product behavior.  It does
not claim byte/source equivalence with the lost historical
``rocketdict-numeric-integrity/3.2`` implementation.  The contract name below
is therefore maintained and independently versioned.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .stages import StageExecutionError, _quality_run

CONTRACT = "rocketdict-maintained-numeric-integrity/1"

# Structured alternatives are deliberately ordered before simpler integer
# forms.  This covers the documented Newton/Stage8 semantics: mixed fractions,
# ordinary fractions, English/Russian ordinals, old ``42d`` ordinals, grouped
# thousands, decimal comma, and Newton apostrophe decimals.
_NUMERIC_RE = re.compile(
    r"(?<![\w])(?P<token>[+\-−]?\d+(?:\s*[-–]\s*|\s+)\d+\s*/\s*\d+(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))?"
    r"|[+\-−]?\d+\s*/\s*\d+(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))?"
    r"|[+\-−]?\d+['’]\d+"
    r"|[+\-−]?\d{1,3}(?:(?:[\s\u00a0\u202f]\d{3}){1,}|(?:,\d{3}){1,})"
    r"|[+\-−]?\d+[.,]\d+"
    r"|[+\-−]?\d+(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))?)(?![\w])",
    re.IGNORECASE | re.UNICODE,
)
_ORDINAL_SUFFIX_RE = re.compile(
    r"(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))$",
    re.IGNORECASE,
)
_CRITICAL_SYMBOLS = ("%", "°", "±", "=", "<", ">", "×", "÷")
_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


@dataclass(frozen=True)
class NumericLiteral:
    raw: str
    canonical: str
    start: int
    end: int


def _strip_ordinal_suffix(token: str) -> str:
    return _ORDINAL_SUFFIX_RE.sub("", token)


def normalize_numeric_literal(raw: str) -> str:
    token = raw.casefold().replace("−", "-").replace("‑", "-").replace("–", "-")
    token = re.sub(r"[\u00a0\u202f]", " ", token)
    token = _strip_ordinal_suffix(token)
    token = re.sub(r"\s*/\s*", "/", token)
    token = re.sub(r"\s*-\s*", "-", token)

    if re.fullmatch(r"[+-]?\d+['’]\d+", token):
        return token.replace("’", "'").replace("'", ".")
    if re.fullmatch(r"[+-]?\d+(?:-| )\d+/\d+", token):
        return token.replace(" ", "-")
    if re.fullmatch(r"[+-]?\d+/\d+", token):
        return token

    compact = token.replace(" ", "")
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+", compact):
        compact = compact.replace(",", "")
    elif "," in compact:
        compact = compact.replace(",", ".")

    if re.fullmatch(r"[+-]?\d+", compact):
        sign = ""
        digits = compact
        if digits[:1] in "+-":
            sign, digits = digits[0], digits[1:]
        digits = digits.lstrip("0") or "0"
        return ("-" if sign == "-" else "") + digits
    return compact


def normalize_numeric_options(raw: str) -> tuple[str, ...]:
    """Return conservative interpretations for ``1,000``-style ambiguity."""
    primary = normalize_numeric_literal(raw)
    compact = (
        raw.casefold()
        .replace("−", "-")
        .replace(" ", "")
        .replace("\u00a0", "")
        .replace("\u202f", "")
    )
    compact = _strip_ordinal_suffix(compact)
    match = re.fullmatch(r"([+-]?\d{1,3}),(\d{3})", compact)
    if not match:
        return (primary,)
    grouped = normalize_numeric_literal(match.group(1) + match.group(2))
    decimal = match.group(1) + "." + match.group(2)
    return tuple(dict.fromkeys((grouped, decimal)))


def extract_numeric_literals(text: str) -> list[NumericLiteral]:
    return [
        NumericLiteral(
            raw=match.group("token"),
            canonical=normalize_numeric_literal(match.group("token")),
            start=match.start("token"),
            end=match.end("token"),
        )
        for match in _NUMERIC_RE.finditer(text)
    ]


def contains_numeric_literal(text: str) -> bool:
    return _NUMERIC_RE.search(text) is not None


def numeric_counter(text: str) -> Counter[str]:
    return Counter(item.canonical for item in extract_numeric_literals(text))


def spelled_numeric_licenses(source: str) -> Counter[str]:
    """License only explicit basic English number words present in the source.

    A tens+unit pair (``twenty one``) licenses the composed value once instead
    of separately licensing 20 and 1.  No arbitrary prose-number inference is
    attempted.
    """
    words = re.findall(r"(?<![A-Za-z])([A-Za-z]+)(?![A-Za-z])", source.casefold())
    out: Counter[str] = Counter()
    index = 0
    while index < len(words):
        word = words[index]
        value = _NUMBER_WORDS.get(word)
        if value is None:
            index += 1
            continue
        if (
            value >= 20
            and value % 10 == 0
            and index + 1 < len(words)
            and 0 < (_NUMBER_WORDS.get(words[index + 1]) or 0) < 10
        ):
            out[str(value + _NUMBER_WORDS[words[index + 1]])] += 1
            index += 2
            continue
        out[str(value)] += 1
        index += 1
    return out


def _positive_delta(left: Counter[str], right: Counter[str]) -> dict[str, int]:
    return {key: left[key] - right[key] for key in left if left[key] > right[key]}


def compare_numeric_integrity(source: str, target: str) -> dict[str, Any]:
    required = numeric_counter(source)
    licensed = spelled_numeric_licenses(source)
    allowed = required + licensed
    observed: Counter[str] = Counter()
    for item in extract_numeric_literals(target):
        options = normalize_numeric_options(item.raw)
        chosen = next((value for value in options if observed[value] < allowed[value]), options[0])
        observed[chosen] += 1

    missing = _positive_delta(required, observed)
    excess = _positive_delta(observed, allowed)
    duplicate_required = {key: value for key, value in excess.items() if key in required}
    unlicensed_additions = {key: value for key, value in excess.items() if key not in required}
    return {
        "contract": CONTRACT,
        "required": dict(required),
        "observed": dict(observed),
        "licensed_spelled": dict(licensed),
        "missing": missing,
        "duplicate_required": duplicate_required,
        "unlicensed_additions": unlicensed_additions,
        "passed": not missing and not duplicate_required and not unlicensed_additions,
    }


def evaluate_numeric_symbol_pair(source: str, target: str) -> dict[str, Any]:
    numeric = compare_numeric_integrity(source, target)
    symbol_mismatch = {
        symbol: {"source": source.count(symbol), "target": target.count(symbol)}
        for symbol in _CRITICAL_SYMBOLS
        if source.count(symbol) != target.count(symbol)
    }
    return {
        "contract": CONTRACT,
        "numeric": numeric,
        "symbol_mismatch": symbol_mismatch,
        "passed": numeric["passed"] is True and not symbol_mismatch,
    }


def _expand_counts(values: dict[str, int]) -> list[str]:
    return [key for key in sorted(values) for _ in range(int(values[key]))]


def _numeric_issues(
    segments: list[dict[str, Any]], _parameters: dict[str, Any]
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in segments:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        result = evaluate_numeric_symbol_pair(source, target)
        if result["passed"] is True:
            continue
        numeric = dict(result["numeric"])
        issues.append(
            {
                "type": "numeric_symbol_mismatch",
                "numeric_contract": CONTRACT,
                "segment_sequence": int(row["sequence_number"]),
                "source_start": row.get("source_start"),
                "source_end": row.get("source_end"),
                "source_text": source,
                "target_text": target,
                "missing_source_literals": _expand_counts(dict(numeric["missing"])),
                "duplicate_required_literals": _expand_counts(dict(numeric["duplicate_required"])),
                "unlicensed_target_literals": _expand_counts(dict(numeric["unlicensed_additions"])),
                "symbol_mismatch": dict(result["symbol_mismatch"]),
                "numeric_detail": numeric,
            }
        )
    return issues


def run_numeric_symbol_gate(
    database: Path | str,
    *,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-numeric-symbol-preservation",
) -> dict[str, Any]:
    effective = dict(parameters or {})
    requested_contract = str(effective.get("evaluator_contract") or CONTRACT)
    if requested_contract != CONTRACT:
        raise StageExecutionError(
            f"Unsupported numeric evaluator contract {requested_contract!r}; expected {CONTRACT!r}"
        )
    # Include evaluator semantics in the immutable stage-run request identity so
    # an old cached PASS produced by the previous parser can never be reused.
    effective["evaluator_contract"] = CONTRACT
    return _quality_run(
        Path(database).expanduser().resolve(),
        implementation=implementation,
        assembly_id=int(assembly_id),
        parameters=effective,
        evaluator=_numeric_issues,
    )
