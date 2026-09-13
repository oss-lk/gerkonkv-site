from __future__ import annotations

"""Source-defined rules for conservative TC-big row-local numeric rescue."""

from collections import Counter
import re
from typing import Any

from .emphasis_markup import compare_emphasis_markup_preservation
from .numeric_integrity import extract_numeric_literals
from .translation_rescue import evaluate_rescue_pair

TRIGGER_CONTRACT = "rocketdict-stage12-tc-big-numeric-row-trigger/1"
SELECTOR_CONTRACT = "rocketdict-stage12-tc-big-numeric-row-selector/1"
VARIANT_PROGRESSION_DUPLICATE = "progression_duplicate"
VARIANT_DENSE_FORMULA_MISSING = "dense_formula_missing"
VARIANT_APOSTROPHE_DECIMAL_TRUNCATION = "apostrophe_decimal_truncation"
VARIANTS = (
    VARIANT_PROGRESSION_DUPLICATE,
    VARIANT_DENSE_FORMULA_MISSING,
    VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
)
MAX_SOURCE_CHARS = 384
MAX_SOURCE_ALPHA_WORDS = 80
MIN_SOURCE_ALPHA_RATIO = 0.80
MAX_SOURCE_ALPHA_RATIO = 1.40
MIN_BASE_ALPHA_RETENTION_RATIO = 0.95
HARD_PUNCTUATION = "()[]{}?!"

_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_APOSTROPHE_DECIMAL_RE = re.compile(r"(?<!\d)\d+['’]\d+(?!\d)")
_FORMULA_A_RE = re.compile(r"(?<![A-Za-z0-9])([0-9(][0-9()/\-]*A)(?![A-Za-z])")
_DECIMAL_RE = re.compile(r"(?P<whole>\d+)\.(?P<fraction>\d+)\Z")


def _alpha_count(text: str) -> int:
    return sum(character.isalpha() for character in text)


def _alpha_word_count(text: str) -> int:
    return len(_ALPHA_WORD_RE.findall(text))


def _single_count(values: dict[str, Any]) -> str | None:
    if len(values) != 1:
        return None
    value, raw_count = next(iter(values.items()))
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return None
    return str(value) if count == 1 else None


def _formula_a_tokens(text: str) -> list[str]:
    return _FORMULA_A_RE.findall(text)


def _apostrophe_decimal_tokens(text: str) -> list[str]:
    return _APOSTROPHE_DECIMAL_RE.findall(text)


def _decimal_prefix_truncation(
    missing: dict[str, Any], additions: dict[str, Any]
) -> dict[str, str] | None:
    required = _single_count(missing)
    observed = _single_count(additions)
    if required is None or observed is None:
        return None
    required_match = _DECIMAL_RE.fullmatch(required)
    observed_match = _DECIMAL_RE.fullmatch(observed)
    if required_match is None or observed_match is None:
        return None
    if required_match.group("whole") != observed_match.group("whole"):
        return None
    required_fraction = required_match.group("fraction")
    observed_fraction = observed_match.group("fraction")
    if (
        required_fraction == observed_fraction
        or not required_fraction.startswith(observed_fraction)
        or len(required_fraction) - len(observed_fraction) > 2
    ):
        return None
    return {"required": required, "observed": observed}


def _base_unique_rank0(row: dict[str, Any]) -> bool:
    payload = dict(row.get("payload") or {})
    hypotheses = list(payload.get("hypotheses") or [])
    if len(hypotheses) != 1:
        return False
    hypothesis = dict(hypotheses[0])
    try:
        selected_rank = int(payload.get("selected_rank", -1))
        rank = int(hypothesis.get("rank", -1))
    except (TypeError, ValueError):
        return False
    return bool(
        selected_rank == 0
        and rank == 0
        and str(hypothesis.get("text") or "") == str(row.get("target_text") or "")
    )


def _base_non_numeric_clean(source: str, target: str, verdict: dict[str, Any]) -> bool:
    emphasis = compare_emphasis_markup_preservation(source, target)
    return bool(
        verdict.get("punctuation_passed") is True
        and verdict.get("length_passed") is True
        and dict(verdict.get("delimiter_preservation") or {}).get("passed") is True
        and dict(verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and dict(verdict.get("output_artifacts") or {}).get("passed") is True
        and emphasis.get("passed") is True
    )


def evaluate_tc_big_numeric_row_trigger(
    row: dict[str, Any], *, source_exact: bool
) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    verdict = evaluate_rescue_pair(source, target)
    numeric_symbol = dict(verdict.get("numeric_symbol") or {})
    numeric = dict(numeric_symbol.get("numeric") or {})
    missing = dict(numeric.get("missing") or {})
    duplicate = dict(numeric.get("duplicate_required") or {})
    additions = dict(numeric.get("unlicensed_additions") or {})
    prime_clean = dict(numeric.get("prime_notation") or {}).get("passed") is True
    symbols_clean = not dict(numeric_symbol.get("symbol_mismatch") or {})
    complexity_passed = bool(
        0 < len(source) <= MAX_SOURCE_CHARS
        and 0 < _alpha_word_count(source) <= MAX_SOURCE_ALPHA_WORDS
    )
    common = bool(
        source_exact
        and _base_unique_rank0(row)
        and numeric_symbol.get("passed") is not True
        and prime_clean
        and symbols_clean
        and complexity_passed
        and _base_non_numeric_clean(source, target, verdict)
    )

    source_literals = extract_numeric_literals(source)
    progression = bool(
        common
        and "&c." in source
        and len(source_literals) >= 6
        and not missing
        and not additions
        and _single_count(duplicate) is not None
    )

    formula_tokens = _formula_a_tokens(source)
    dense_formula = bool(
        common
        and len(formula_tokens) >= 2
        and _single_count(missing) is not None
        and not duplicate
        and not additions
    )

    apostrophe_tokens = _apostrophe_decimal_tokens(source)
    truncation = _decimal_prefix_truncation(missing, additions)
    apostrophe_decimal = bool(
        common
        and len(apostrophe_tokens) >= 3
        and truncation is not None
        and not duplicate
    )

    matched = [
        name
        for name, passed in (
            (VARIANT_PROGRESSION_DUPLICATE, progression),
            (VARIANT_DENSE_FORMULA_MISSING, dense_formula),
            (VARIANT_APOSTROPHE_DECIMAL_TRUNCATION, apostrophe_decimal),
        )
        if passed
    ]
    variant = matched[0] if len(matched) == 1 else None
    return {
        "contract": TRIGGER_CONTRACT,
        "eligible": variant is not None,
        "variant": variant,
        "matched_variants": matched,
        "immutable_source_exact": bool(source_exact),
        "base_unique_rank0": _base_unique_rank0(row),
        "base_non_numeric_checks_clean": _base_non_numeric_clean(source, target, verdict),
        "source_char_count": len(source),
        "source_alpha_word_count": _alpha_word_count(source),
        "source_numeric_literal_count": len(source_literals),
        "source_formula_a_tokens": formula_tokens,
        "source_apostrophe_decimal_tokens": apostrophe_tokens,
        "decimal_prefix_truncation": truncation,
        "numeric_missing": missing,
        "numeric_duplicate_required": duplicate,
        "numeric_unlicensed_additions": additions,
        "prime_notation_clean": prime_clean,
        "critical_symbols_clean": symbols_clean,
        "base_verdict": verdict,
    }


def _variant_notation_preserved(variant: str, source: str, target: str) -> bool:
    if variant == VARIANT_PROGRESSION_DUPLICATE:
        return "&c." in target
    if variant == VARIANT_DENSE_FORMULA_MISSING:
        return Counter(_formula_a_tokens(source)) == Counter(_formula_a_tokens(target))
    if variant == VARIANT_APOSTROPHE_DECIMAL_TRUNCATION:
        return _apostrophe_decimal_tokens(source) == _apostrophe_decimal_tokens(target)
    return False


def evaluate_tc_big_numeric_row_candidate(
    source: str,
    target: str,
    *,
    base_target: str,
    variant: str,
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_punctuation = {symbol: source.count(symbol) for symbol in HARD_PUNCTUATION}
    target_punctuation = {symbol: target.count(symbol) for symbol in HARD_PUNCTUATION}
    punctuation_exact = source_punctuation == target_punctuation
    source_alpha = _alpha_count(source)
    target_alpha = _alpha_count(target)
    base_alpha = _alpha_count(base_target)
    source_ratio = target_alpha / source_alpha if source_alpha else 1.0
    base_retention = target_alpha / base_alpha if base_alpha else 1.0
    notation_preserved = _variant_notation_preserved(variant, source, target)
    accepted = bool(
        target.strip()
        and variant in VARIANTS
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and punctuation_exact
        and MIN_SOURCE_ALPHA_RATIO <= source_ratio <= MAX_SOURCE_ALPHA_RATIO
        and base_retention >= MIN_BASE_ALPHA_RETENTION_RATIO
        and notation_preserved
    )
    return {
        "selector_contract": SELECTOR_CONTRACT,
        "accepted": accepted,
        "variant": variant,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "hard_punctuation_exact": punctuation_exact,
        "source_alpha_ratio": source_ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "base_alpha_retention_ratio": base_retention,
        "base_alpha_retention_minimum": MIN_BASE_ALPHA_RETENTION_RATIO,
        "variant_notation_preserved": notation_preserved,
        "raw_target_nonempty": bool(target.strip()),
    }
