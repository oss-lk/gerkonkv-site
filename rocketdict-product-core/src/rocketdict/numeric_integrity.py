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

from .numeric_words import extract_russian_ordinals
from .prime_notation import compare_numeric_prime_notation
from .stages import StageExecutionError, _quality_run

CONTRACT = "rocketdict-maintained-numeric-integrity/5"

_ORDINAL_SUFFIX = r"(?:st|nd|rd|th|d|[-‑–]?(?:й|я|е|го|му|ым|ом|ой|ую|ых))"
_ENG_DIGIT_ORDINAL_RE = re.compile(r"^\s*\d+(?:st|nd|rd|th)\s*$", re.IGNORECASE)
# Space-grouping is deliberately allowed after an arbitrary-length leading
# digit group. Real R1 evidence contains model output such as ``11/178 000``
# and ``961/72000 000``; these are formatting variants of the exact source
# values, not newly invented numbers.
_GROUPED_INT = r"(?:\d{1,3}(?:,\d{3})+|\d+(?:[\s\u00a0\u202f]\d{3})*)"
_SIGN = r"[+\-−]?\s*"

# Numeric boundaries are digit-based rather than Python-word-based. This is
# necessary for Gutenberg/source markup such as ``_Obs._16`` and technical
# payloads where a digit may touch an underscore or letter. Structural-token
# identity remains a separate hard diagnostic; counting its digits here adds a
# second fail-closed signal rather than licensing changes.
_NUMERIC_RE = re.compile(
    rf"(?<!\d)(?P<token>"
    rf"{_SIGN}{_GROUPED_INT}(?:\s*[-–]\s*|\s+){_GROUPED_INT}\s*/\s*{_GROUPED_INT}{_ORDINAL_SUFFIX}?"
    rf"|{_SIGN}{_GROUPED_INT}\s*/\s*{_GROUPED_INT}{_ORDINAL_SUFFIX}?"
    rf"|{_SIGN}\d+['’]\d+"
    rf"|{_SIGN}\d{{1,3}}(?:,\d{{3}})+"
    rf"|{_SIGN}\d+(?:[\s\u00a0\u202f]\d{{3}})+"
    rf"|{_SIGN}\d+[.,]\d+"
    rf"|{_SIGN}\d+{_ORDINAL_SUFFIX}?"
    rf")(?!\d)",
    re.IGNORECASE | re.UNICODE,
)
_ORDINAL_SUFFIX_RE = re.compile(rf"{_ORDINAL_SUFFIX}$", re.IGNORECASE)
_SPACED_MINUS_RE = re.compile(r"^[-−]\s+\d")
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
    # Exact source word -> target digit licences. This does not parse arbitrary
    # prose quantities; it only permits a model to render the explicit word as
    # the corresponding literal. ``an hundred`` is present in frozen R1.
    "hundred": 100,
}
_ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
    "thirtieth": 30,
    "fortieth": 40,
    "fiftieth": 50,
    "sixtieth": 60,
    "seventieth": 70,
    "eightieth": 80,
    "ninetieth": 90,
}


@dataclass(frozen=True)
class NumericLiteral:
    raw: str
    canonical: str
    start: int
    end: int


def _strip_ordinal_suffix(token: str) -> str:
    return _ORDINAL_SUFFIX_RE.sub("", token)


def _normalize_integer(raw: str) -> str:
    compact = re.sub(r"[\s\u00a0\u202f]", "", raw)
    # At integer-only positions commas are grouping punctuation. Decimal-comma
    # ambiguity is handled separately by ``normalize_numeric_options``.
    compact = compact.replace(",", "")
    sign = ""
    if compact[:1] in {"+", "-", "−"}:
        sign, compact = compact[0], compact[1:]
    digits = compact.lstrip("0") or "0"
    return ("-" if sign in {"-", "−"} else "") + digits


def normalize_numeric_literal(raw: str) -> str:
    token = raw.casefold().replace("−", "-").replace("‑", "-").replace("–", "-")
    token = re.sub(r"[\u00a0\u202f]", " ", token).strip()
    token = _strip_ordinal_suffix(token).strip()
    token = re.sub(r"^([+-])\s+", r"\1", token)

    # Mixed/simple fractions, including grouped denominators emitted by MT.
    mixed = re.fullmatch(
        rf"(?P<sign>[+-]?)\s*(?P<whole>{_GROUPED_INT})(?:\s*-\s*|\s+)(?P<num>{_GROUPED_INT})\s*/\s*(?P<den>{_GROUPED_INT})",
        token,
        flags=re.IGNORECASE,
    )
    if mixed:
        sign = "-" if mixed.group("sign") == "-" else ""
        return (
            sign
            + _normalize_integer(mixed.group("whole"))
            + "-"
            + _normalize_integer(mixed.group("num"))
            + "/"
            + _normalize_integer(mixed.group("den"))
        )
    fraction = re.fullmatch(
        rf"(?P<sign>[+-]?)\s*(?P<num>{_GROUPED_INT})\s*/\s*(?P<den>{_GROUPED_INT})",
        token,
        flags=re.IGNORECASE,
    )
    if fraction:
        sign = "-" if fraction.group("sign") == "-" else ""
        return (
            sign
            + _normalize_integer(fraction.group("num"))
            + "/"
            + _normalize_integer(fraction.group("den"))
        )

    if re.fullmatch(r"[+-]?\d+['’]\d+", token):
        return token.replace("’", "'").replace("'", ".")

    compact = token.replace(" ", "")
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+", compact):
        return _normalize_integer(compact)
    if "," in compact:
        compact = compact.replace(",", ".")

    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", compact):
        sign = ""
        value = compact
        if value[:1] in "+-":
            sign, value = value[0], value[1:]
        if "." in value:
            integer, fraction_part = value.split(".", 1)
            integer = integer.lstrip("0") or "0"
            fraction_part = fraction_part.rstrip("0")
            normalized = integer + ("." + fraction_part if fraction_part else "")
        else:
            normalized = value.lstrip("0") or "0"
        return ("-" if sign == "-" else "") + normalized
    return compact


def normalize_numeric_options(raw: str) -> tuple[str, ...]:
    """Return conservative intrinsic interpretations of one numeric token."""
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
    grouped = _normalize_integer(match.group(1) + match.group(2))
    decimal = normalize_numeric_literal(match.group(1) + "." + match.group(2))
    return tuple(dict.fromkeys((grouped, decimal)))


def _spaced_dash_can_be_separator(text: str, literal: NumericLiteral) -> bool:
    """Return whether a spaced leading ``-`` is syntactically separator-like.

    R1 exposed model output such as ``POF - 42`` and
    ``77-1/3 - 77-1/2``. Treating every ``- 42`` as unary minus creates false
    numeric corruption. We license an unsigned interpretation only when the
    spaced dash follows completed alphanumeric/closing-delimiter content. A
    token at the beginning of the segment, or after an opening/math operator,
    remains strictly signed. This preserves ``- 6/106`` as a real negative and
    does not make direct ``-42`` ambiguous.
    """
    if not _SPACED_MINUS_RE.match(literal.raw):
        return False
    prefix = text[: literal.start].rstrip()
    if not prefix:
        return False
    return prefix[-1].isalnum() or prefix[-1] in ")] }_".replace(" ", "")


def _target_numeric_options(text: str, literal: NumericLiteral) -> tuple[str, ...]:
    options = list(normalize_numeric_options(literal.raw))
    if _spaced_dash_can_be_separator(text, literal):
        unsigned_raw = re.sub(r"^[-−]\s+", "", literal.raw, count=1)
        options.extend(normalize_numeric_options(unsigned_raw))
    return tuple(dict.fromkeys(options))


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


def is_english_digit_ordinal(literal: NumericLiteral) -> bool:
    """Whether a source literal is an ordinary ``1st``/``2nd``/``18th`` ordinal.

    Old notation such as ``42d`` and identifiers like ``2D`` are deliberately
    excluded.  Fractions/decimals/grouped values are also excluded because the
    Russian word-equivalence evidence applies only to ordinary integer ordinals.
    """
    return _ENG_DIGIT_ORDINAL_RE.fullmatch(literal.raw) is not None


def source_digit_ordinal_counter(source: str) -> Counter[str]:
    return Counter(
        literal.canonical
        for literal in extract_numeric_literals(source)
        if is_english_digit_ordinal(literal)
    )


def spelled_numeric_licenses(source: str) -> Counter[str]:
    """License only explicit English cardinal/ordinal number words in source."""
    words = re.findall(r"(?<![A-Za-z])([A-Za-z]+)(?![A-Za-z])", source.casefold())
    out: Counter[str] = Counter()
    index = 0
    while index < len(words):
        word = words[index]
        ordinal = _ORDINAL_WORDS.get(word)
        if ordinal is not None:
            out[str(ordinal)] += 1
            index += 1
            continue
        value = _NUMBER_WORDS.get(word)
        if value is None:
            index += 1
            continue
        if (
            value >= 20
            and value < 100
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


def _russian_ordinal_credit(
    source: str,
    target: str,
    *,
    required: Counter[str],
    explicit_observed: Counter[str],
) -> tuple[Counter[str], Counter[str]]:
    """Credit matching Russian ordinal words only for residual source ordinals.

    Target ordinal prose is not itself treated as a numeric addition.  It can
    only satisfy an otherwise-missing source literal that was explicitly an
    English digit ordinal (``st/nd/rd/th``).  This prevents a cardinal source
    ``18`` from being silently licensed by target ``восемнадцатый`` and keeps
    unrelated Russian ordinal prose outside the literal-addition semantics.
    """
    source_ordinals = source_digit_ordinal_counter(source)
    candidates = Counter(match.canonical for match in extract_russian_ordinals(target))
    residual = required - explicit_observed
    credit: Counter[str] = Counter()
    for value in source_ordinals:
        amount = min(source_ordinals[value], candidates[value], residual[value])
        if amount > 0:
            credit[value] = amount
    return credit, candidates


def compare_numeric_integrity(source: str, target: str) -> dict[str, Any]:
    required = numeric_counter(source)
    licensed = spelled_numeric_licenses(source)
    allowed = required + licensed
    explicit_observed: Counter[str] = Counter()
    for item in extract_numeric_literals(target):
        options = _target_numeric_options(target, item)
        chosen = next(
            (value for value in options if explicit_observed[value] < allowed[value]),
            options[0],
        )
        explicit_observed[chosen] += 1

    ordinal_credit, ordinal_candidates = _russian_ordinal_credit(
        source,
        target,
        required=required,
        explicit_observed=explicit_observed,
    )
    effective_observed = explicit_observed + ordinal_credit
    missing = _positive_delta(required, effective_observed)

    # Duplicates/additions remain an explicit-literal concern.  Russian ordinal
    # words only satisfy a demonstrated residual source ordinal requirement and
    # never create target numeric additions by themselves.
    excess = _positive_delta(explicit_observed, allowed)
    duplicate_required = {key: value for key, value in excess.items() if key in required}
    unlicensed_additions = {key: value for key, value in excess.items() if key not in required}
    prime_notation = compare_numeric_prime_notation(source, target)
    return {
        "contract": CONTRACT,
        "required": dict(required),
        "observed": dict(effective_observed),
        "explicit_observed": dict(explicit_observed),
        "licensed_spelled": dict(licensed),
        "source_digit_ordinals": dict(source_digit_ordinal_counter(source)),
        "target_russian_ordinal_candidates": dict(ordinal_candidates),
        "target_russian_ordinal_credit": dict(ordinal_credit),
        "missing": missing,
        "duplicate_required": duplicate_required,
        "unlicensed_additions": unlicensed_additions,
        "prime_notation": prime_notation,
        "passed": (
            not missing
            and not duplicate_required
            and not unlicensed_additions
            and prime_notation["passed"] is True
        ),
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
                "prime_notation_mismatch": (
                    None
                    if numeric["prime_notation"]["passed"] is True
                    else dict(numeric["prime_notation"])
                ),
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
    # an old cached PASS produced by a previous parser can never be reused.
    effective["evaluator_contract"] = CONTRACT
    return _quality_run(
        Path(database).expanduser().resolve(),
        implementation=implementation,
        assembly_id=int(assembly_id),
        parameters=effective,
        evaluator=_numeric_issues,
    )
