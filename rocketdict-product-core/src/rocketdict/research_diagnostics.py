from __future__ import annotations

"""Dependency-free research diagnostics aligned with maintained Product semantics.

These checks are measurement surfaces, not additional Product hard gates.  They
must therefore avoid contradicting the maintained hard-gate parser while still
remaining independently versioned and auditable.
"""

from typing import Any

from .numeric_integrity import _target_numeric_options, extract_numeric_literals

NUMERIC_ORDER_CONTRACT = "rocketdict-maintained-numeric-order/1"
DELIMITER_CONTRACT = "rocketdict-maintained-delimiter-preservation/1"


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
