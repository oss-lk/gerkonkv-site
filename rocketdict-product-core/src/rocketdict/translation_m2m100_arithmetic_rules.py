from __future__ import annotations

"""Pure trigger/selector rules for M2M100 arithmetic-restatement row rescue."""

from collections import Counter
import re
from typing import Any

from .emphasis_markup import compare_emphasis_markup_preservation
from .numeric_integrity import extract_numeric_literals
from .translation_rescue import evaluate_rescue_pair

M2M100_ARITHMETIC_TRIGGER_CONTRACT = (
    "rocketdict-stage12-m2m100-arithmetic-restatement-row-trigger/1"
)
M2M100_ARITHMETIC_SELECTOR_CONTRACT = (
    "rocketdict-stage12-m2m100-arithmetic-restatement-row-selector/1"
)
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.40
MIN_BASE_ALPHA_RETENTION_RATIO = 0.90
MAX_SOURCE_CHARS = 512
MAX_SOURCE_ALPHA_WORDS = 96
_HARD_PUNCTUATION = "()[]{}?!"
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_RESTATEMENT_RE = re.compile(
    r"\b(?P<a>\d[\d,]*)\s*[x×]\s*(?P<b>\d[\d,]*)\s*"
    r"\(\s*that\s+is\s*,\s*above\s+(?P<c>\d[\d,]*)\s*\)",
    re.IGNORECASE,
)


def _integer(raw: str) -> int:
    return int(raw.replace(",", ""))


def _alpha(text: str) -> int:
    return sum(character.isalpha() for character in text)


def _source_alpha_ratio(source: str, target: str) -> float:
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    if source_alpha <= 0:
        return 1.0 if target_alpha == 0 else float("inf")
    return target_alpha / source_alpha


def _hard_punctuation(text: str) -> dict[str, int]:
    return {symbol: text.count(symbol) for symbol in _HARD_PUNCTUATION}


def parse_source_arithmetic_restatement(source: str) -> dict[str, Any] | None:
    matches = list(_RESTATEMENT_RE.finditer(source))
    if len(matches) != 1:
        return None
    match = matches[0]
    a, b, c = (_integer(match.group(name)) for name in ("a", "b", "c"))
    expected = [str(a), str(b), str(c)]
    source_literals = [literal.canonical for literal in extract_numeric_literals(source)]
    if source_literals != expected:
        return None
    return {
        "a": a,
        "b": b,
        "c": c,
        "product": a * b,
        "arithmetic_verified": a * b == c,
        "numeric_sequence": expected,
        "source_span": [match.start(), match.end()],
        "source_fragment": match.group(0),
    }


def _target_arithmetic_notation(
    target: str, *, a: int, b: int, c: int
) -> dict[str, Any]:
    literals = extract_numeric_literals(target)
    sequence = [literal.canonical for literal in literals]
    expected = [str(a), str(b), str(c)]
    exact_sequence = sequence == expected
    multiplication_operator_preserved = False
    if exact_sequence and len(literals) == 3:
        between = target[literals[0].end : literals[1].start]
        multiplication_operator_preserved = "x" in between.casefold() or "×" in between
    return {
        "target_numeric_sequence": sequence,
        "expected_numeric_sequence": expected,
        "numeric_sequence_exact": exact_sequence,
        "multiplication_operator_preserved": multiplication_operator_preserved,
        "passed": exact_sequence and multiplication_operator_preserved,
    }


def evaluate_m2m100_arithmetic_trigger(
    row: dict[str, Any], *, source_exact: bool
) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    restatement = parse_source_arithmetic_restatement(source)
    verdict = evaluate_rescue_pair(source, target)
    numeric_symbol = dict(verdict.get("numeric_symbol") or {})
    numeric = dict(numeric_symbol.get("numeric") or {})
    source_chars = len(source)
    source_alpha_words = len(_ALPHA_WORD_RE.findall(source))
    complexity_passed = bool(
        0 < source_chars <= MAX_SOURCE_CHARS
        and 0 < source_alpha_words <= MAX_SOURCE_ALPHA_WORDS
    )
    expected_c = None if restatement is None else str(restatement["c"])
    missing = dict(numeric.get("missing") or {})
    additions = dict(numeric.get("unlicensed_additions") or {})
    corruption_shape = bool(
        expected_c is not None
        and missing == {expected_c: 1}
        and not dict(numeric.get("duplicate_required") or {})
        and len(additions) == 1
        and next(iter(additions.values()), 0) == 1
        and dict(numeric.get("prime_notation") or {}).get("passed") is True
        and not dict(numeric_symbol.get("symbol_mismatch") or {})
    )
    non_numeric_safe = bool(
        verdict.get("punctuation_passed") is True
        and verdict.get("length_passed") is True
        and dict(verdict.get("delimiter_preservation") or {}).get("passed") is True
        and dict(verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and dict(verdict.get("output_artifacts") or {}).get("passed") is True
    )
    eligible = bool(
        source_exact
        and restatement is not None
        and restatement["arithmetic_verified"] is True
        and numeric_symbol.get("passed") is not True
        and corruption_shape
        and non_numeric_safe
        and complexity_passed
    )
    return {
        "contract": M2M100_ARITHMETIC_TRIGGER_CONTRACT,
        "eligible": eligible,
        "immutable_source_exact": bool(source_exact),
        "source_restatement": restatement,
        "source_arithmetic_verified": bool(
            restatement is not None and restatement["arithmetic_verified"] is True
        ),
        "current_numeric_result_corruption_shape": corruption_shape,
        "non_numeric_hard_and_structural_checks_clean": non_numeric_safe,
        "source_char_count": source_chars,
        "source_char_cap": MAX_SOURCE_CHARS,
        "source_alpha_word_count": source_alpha_words,
        "source_alpha_word_cap": MAX_SOURCE_ALPHA_WORDS,
        "source_complexity_passed": complexity_passed,
        "current_unlicensed_additions": additions,
        "base_verdict": verdict,
    }


def evaluate_m2m100_arithmetic_candidate(
    source: str,
    target: str,
    *,
    base_target: str,
    restatement: dict[str, Any],
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _source_alpha_ratio(source, target)
    source_ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    base_alpha = _alpha(base_target)
    target_alpha = _alpha(target)
    base_retention = target_alpha / base_alpha if base_alpha else 1.0
    base_retention_passed = base_retention >= MIN_BASE_ALPHA_RETENTION_RATIO
    punctuation_exact = _hard_punctuation(source) == _hard_punctuation(target)
    arithmetic = _target_arithmetic_notation(
        target,
        a=int(restatement["a"]),
        b=int(restatement["b"]),
        c=int(restatement["c"]),
    )
    accepted = bool(
        target.strip()
        and restatement.get("arithmetic_verified") is True
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and punctuation_exact
        and source_ratio_passed
        and base_retention_passed
        and arithmetic["passed"] is True
    )
    return {
        "selector_contract": M2M100_ARITHMETIC_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "strict_research_passed": verdict.get("strict_research_passed") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "hard_punctuation_exact": punctuation_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": source_ratio_passed,
        "base_alpha_count": base_alpha,
        "candidate_alpha_count": target_alpha,
        "base_alpha_retention_ratio": base_retention,
        "base_alpha_retention_minimum": MIN_BASE_ALPHA_RETENTION_RATIO,
        "base_alpha_retention_passed": base_retention_passed,
        "arithmetic_notation": arithmetic,
        "raw_target_nonempty": bool(target.strip()),
    }
