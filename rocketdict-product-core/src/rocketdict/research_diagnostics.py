from __future__ import annotations

"""Dependency-free research diagnostics aligned with maintained Product semantics.

These checks are measurement surfaces, not additional Product hard gates.  They
must therefore avoid contradicting the maintained hard-gate parser while still
remaining independently versioned and auditable.
"""

from collections import Counter
import re
from typing import Any

from .numeric_integrity import _target_numeric_options, extract_numeric_literals

NUMERIC_ORDER_CONTRACT = "rocketdict-maintained-numeric-order/1"
DELIMITER_CONTRACT = "rocketdict-maintained-delimiter-preservation/1"
CRITICAL_TOKEN_CONTRACT = "rocketdict-maintained-critical-technical-token/2"
OUTPUT_ARTIFACT_CONTRACT = "rocketdict-maintained-output-artifact/2"

_GREEK_SOURCE_RE = re.compile(r"\[Greek:\s*([^\]]*)\]", flags=re.IGNORECASE)
_GREEK_TARGET_RE = re.compile(
    r"\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]*)\]",
    flags=re.IGNORECASE,
)
_ILLUSTRATION_SOURCE_RE = re.compile(r"\[Illustration:\s*([^\]]*)\]", flags=re.IGNORECASE)
_ILLUSTRATION_TARGET_RE = re.compile(
    r"\[(?:Illustration|Иллюстрация)\s*:\s*([^\]]*)\]", flags=re.IGNORECASE
)
_FOOTNOTE_RE = re.compile(r"\[([A-Z])\]")
_EMPH_RE = re.compile(r"_([^_\n]{1,80})_")
_COMBINED_GREEK_SOURCE_RE = re.compile(
    r"_([A-Za-z]{1,3})\[Greek:\s*([^\]]+)\]_", flags=re.IGNORECASE
)
_COMBINED_GREEK_TARGET_RE = re.compile(
    r"_([A-Za-z]{1,3})\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]+)\]_",
    flags=re.IGNORECASE,
)
_STRUCTURAL_ID_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.[A-Za-z]+)+\.\d+\.)(?![A-Za-z0-9])"
)
_HTML_ENTITY_RE = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|#\d+|#x[0-9A-Fa-f]+);")
_QUOTE_DELIMITERS = '"“”«»„‟‹›'


def compare_numeric_order(source: str, target: str) -> dict[str, Any]:
    """Check that explicit source numeric values survive in source order.

    Exact counts/additions are intentionally left to the Product numeric hard
    gate.  This diagnostic asks only whether the canonical required sequence is
    a subsequence of target numeric tokens, while reusing the same target-token
    ambiguity semantics as the hard gate (grouped thousands, apostrophe
    decimals, spaced dash separators, etc.).
    """
    required = [item.canonical for item in extract_numeric_literals(source)]
    target_literals = extract_numeric_literals(target)
    observed_primary = [item.canonical for item in target_literals]
    observed_options: list[list[str]] = []
    matched_target_indices: list[int] = []
    cursor = 0
    for index, item in enumerate(target_literals):
        options = list(_target_numeric_options(target, item))
        observed_options.append(options)
        if cursor < len(required) and required[cursor] in options:
            matched_target_indices.append(index)
            cursor += 1
    return {
        "contract": NUMERIC_ORDER_CONTRACT,
        "required_sequence": required,
        "observed_primary_sequence": observed_primary,
        "observed_options": observed_options,
        "matched_target_indices": matched_target_indices,
        "matched_required_count": cursor,
        "required_count": len(required),
        "passed": cursor == len(required),
    }


def compare_delimiter_preservation(source: str, target: str) -> dict[str, Any]:
    """Measure exact preservation of source paired-delimiter counts.

    A malformed/unbalanced immutable source is *not* a licence to fabricate a
    closing delimiter.  If the model preserves the same unmatched count, this
    diagnostic passes and records ``source_balanced=False`` for research.  A
    balanced source still requires exact left/right counts in the target.
    """
    rows: dict[str, Any] = {}
    passed = True
    unbalanced_source_kinds: list[str] = []
    for name, left, right in (
        ("square", "[", "]"),
        ("round", "(", ")"),
        ("curly", "{", "}"),
    ):
        source_counts = (source.count(left), source.count(right))
        target_counts = (target.count(left), target.count(right))
        source_balanced = source_counts[0] == source_counts[1]
        exact = target_counts == source_counts
        if not source_balanced:
            unbalanced_source_kinds.append(name)
        rows[name] = {
            "source": list(source_counts),
            "target": list(target_counts),
            "source_balanced": source_balanced,
            "exactly_preserved": exact,
            "passed": exact,
        }
        passed = passed and exact
    return {
        "contract": DELIMITER_CONTRACT,
        "delimiters": rows,
        "source_unbalanced_kinds": unbalanced_source_kinds,
        "source_was_balanced": not unbalanced_source_kinds,
        "passed": passed,
    }


def _payloads(regex: re.Pattern[str], text: str) -> list[str]:
    return [match.group(1).strip() for match in regex.finditer(text)]


def _combined(regex: re.Pattern[str], text: str) -> list[list[str]]:
    return [[match.group(1), match.group(2).strip()] for match in regex.finditer(text)]


def _is_symbolic_emphasis(inner: str) -> bool:
    value = inner.strip()
    if re.fullmatch(r"[A-Za-z]{1,3}", value):
        return True
    atom = r"(?:\d+[A-Za-z]|[A-Za-z]\d+)"
    return bool(re.fullmatch(rf"{atom}(?:\s+{atom})*", value))


def _symbolic_emphasis_sequence(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in _EMPH_RE.finditer(text)
        if _is_symbolic_emphasis(match.group(1))
    ]


def compare_critical_technical_tokens(source: str, target: str) -> dict[str, Any]:
    """Measure preservation of source-owned technical payloads and identifiers.

    This retains the useful frozen-R1 critical-token surface while moving it to
    a maintained, dependency-free and independently versioned diagnostic.  It
    never repairs or injects a token: source and target sequences are compared
    exactly for Greek/illustration payloads, symbolic Gutenberg emphasis, ASCII
    footnote markers and immutable Gutenberg section identifiers such as
    ``1.F.4.``.
    """
    checks: dict[str, dict[str, Any]] = {
        "greek_payloads": {
            "source": _payloads(_GREEK_SOURCE_RE, source),
            "target": _payloads(_GREEK_TARGET_RE, target),
        },
        "combined_greek_variables": {
            "source": _combined(_COMBINED_GREEK_SOURCE_RE, source),
            "target": _combined(_COMBINED_GREEK_TARGET_RE, target),
        },
        "symbolic_emphasis": {
            "source": _symbolic_emphasis_sequence(source),
            "target": _symbolic_emphasis_sequence(target),
        },
        "footnote_markers": {
            "source": _payloads(_FOOTNOTE_RE, source),
            "target": _payloads(_FOOTNOTE_RE, target),
        },
        "illustration_payloads": {
            "source": _payloads(_ILLUSTRATION_SOURCE_RE, source),
            "target": _payloads(_ILLUSTRATION_TARGET_RE, target),
        },
        "structural_identifiers": {
            "source": _payloads(_STRUCTURAL_ID_RE, source),
            "target": _payloads(_STRUCTURAL_ID_RE, target),
        },
    }
    failed = [name for name, row in checks.items() if row["source"] != row["target"]]
    return {
        "contract": CRITICAL_TOKEN_CONTRACT,
        "checks": checks,
        "failed_checks": failed,
        "passed": not failed,
    }


def _quote_delimiter_counts(text: str) -> dict[str, int]:
    return {char: text.count(char) for char in _QUOTE_DELIMITERS if char in text}


def compare_output_artifacts(source: str, target: str) -> dict[str, Any]:
    """Reject obvious target-only serialization/punctuation artifacts.

    Literal HTML/XML entities and the Unicode replacement character are visible
    corruption in plain-text Product output when the immutable source did not
    contain them.  Research evidence also records quote delimiters across common
    English/Russian styles.  Style substitution is allowed when the total quote
    delimiter cardinality is unchanged; only *introduced* quote delimiters are
    rejected here.  Apostrophes are intentionally excluded because they carry
    lexical and historical numeric meaning in the corpus.

    This remains a measurement surface: it does not decode, strip, normalize or
    rewrite either source or target.
    """
    source_entities = Counter(_HTML_ENTITY_RE.findall(source))
    target_entities = Counter(_HTML_ENTITY_RE.findall(target))
    introduced_entities = target_entities - source_entities
    source_replacement = source.count("�")
    target_replacement = target.count("�")
    introduced_replacement = max(0, target_replacement - source_replacement)
    source_quotes = _quote_delimiter_counts(source)
    target_quotes = _quote_delimiter_counts(target)
    source_quote_count = sum(source_quotes.values())
    target_quote_count = sum(target_quotes.values())
    introduced_quote_count = max(0, target_quote_count - source_quote_count)
    return {
        "contract": OUTPUT_ARTIFACT_CONTRACT,
        "source_entities": dict(source_entities),
        "target_entities": dict(target_entities),
        "introduced_entities": dict(introduced_entities),
        "source_replacement_character_count": source_replacement,
        "target_replacement_character_count": target_replacement,
        "introduced_replacement_character_count": introduced_replacement,
        "source_quote_delimiters": source_quotes,
        "target_quote_delimiters": target_quotes,
        "source_quote_delimiter_count": source_quote_count,
        "target_quote_delimiter_count": target_quote_count,
        "introduced_quote_delimiter_count": introduced_quote_count,
        "passed": (
            not introduced_entities
            and introduced_replacement == 0
            and introduced_quote_count == 0
        ),
    }
