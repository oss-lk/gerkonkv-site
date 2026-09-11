from __future__ import annotations

"""Source-defined repair for false spaCy sentence boundaries used by Stage10.

Stage8 deliberately preserves the raw sentence assignment produced by spaCy.  This
module operates one layer later: it may coalesce two adjacent parser sentences
only when the immutable source itself gives strong evidence that the second is a
lower-case continuation rather than a new sentence.
"""

import re
from typing import Any

STAGE10_CONTEXT_IMPLEMENTATION_V1 = "structural-entity-term-discourse-pronoun-v1"
STAGE10_CONTEXT_IMPLEMENTATION_V2 = "structural-entity-term-discourse-pronoun-v2"
STAGE10_BOUNDARY_POLICY = "rocketdict-stage10-lowercase-continuation-coalescer/1"

_TERMINAL_PUNCTUATION = frozenset(".?!")
_TRAILING_CLOSERS = frozenset("\"'”’)]}_*")
_PARAGRAPH_BREAK = re.compile(r"(?:\r?\n)[ \t]*(?:\r?\n)")


def _ordered_tokens(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            int(row["source_start"]),
            int((row.get("payload") or {}).get("token_index") or 0),
        ),
    )


def _first_lexical_char(rows: list[dict[str, Any]]) -> str | None:
    for row in _ordered_tokens(rows):
        text = str(row.get("source_text") or "")
        for char in text:
            if char.isalpha():
                return char
    return None


def _has_terminal_sentence_punctuation(fragment: str) -> bool:
    text = fragment.rstrip()
    while text and text[-1] in _TRAILING_CLOSERS:
        text = text[:-1].rstrip()
    return bool(text) and text[-1] in _TERMINAL_PUNCTUATION


def evaluate_spacy_sentence_boundary(
    content: str,
    left_sentence_index: int,
    left_rows: list[dict[str, Any]],
    right_sentence_index: int,
    right_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a deterministic, source-only decision for one parser boundary."""

    left = _ordered_tokens(left_rows)
    right = _ordered_tokens(right_rows)
    if not left or not right:
        return {
            "policy": STAGE10_BOUNDARY_POLICY,
            "merge": False,
            "reason": "empty_parser_sentence",
            "left_sentence_index": int(left_sentence_index),
            "right_sentence_index": int(right_sentence_index),
        }

    left_start = int(left[0]["source_start"])
    left_token_end = int(left[-1]["source_end"])
    right_start = int(right[0]["source_start"])
    if not (0 <= left_start <= left_token_end <= right_start <= len(content)):
        return {
            "policy": STAGE10_BOUNDARY_POLICY,
            "merge": False,
            "reason": "non_contiguous_source_geometry",
            "left_sentence_index": int(left_sentence_index),
            "right_sentence_index": int(right_sentence_index),
        }

    gap = content[left_token_end:right_start]
    boundary_prefix = content[left_start:right_start]
    first_lexical = _first_lexical_char(right)
    terminal = _has_terminal_sentence_punctuation(boundary_prefix)
    paragraph_break = bool(_PARAGRAPH_BREAK.search(gap))
    whitespace_only_gap = not gap or gap.isspace()
    lowercase_continuation = bool(first_lexical and first_lexical.islower())
    consecutive_parser_indices = int(right_sentence_index) == int(left_sentence_index) + 1

    merge = bool(
        consecutive_parser_indices
        and whitespace_only_gap
        and not paragraph_break
        and not terminal
        and lowercase_continuation
    )
    if not consecutive_parser_indices:
        reason = "non_consecutive_parser_indices"
    elif not whitespace_only_gap:
        reason = "non_whitespace_source_gap"
    elif paragraph_break:
        reason = "paragraph_break"
    elif terminal:
        reason = "source_terminal_punctuation"
    elif not lowercase_continuation:
        reason = "continuation_not_lowercase"
    else:
        reason = "lowercase_continuation_without_terminal"

    return {
        "policy": STAGE10_BOUNDARY_POLICY,
        "merge": merge,
        "reason": reason,
        "left_sentence_index": int(left_sentence_index),
        "right_sentence_index": int(right_sentence_index),
        "source_offset": right_start,
        "gap": gap,
        "first_right_lexical_char": first_lexical,
        "source_terminal_punctuation": terminal,
        "paragraph_break": paragraph_break,
        "whitespace_only_gap": whitespace_only_gap,
        "lowercase_continuation": lowercase_continuation,
        "consecutive_parser_indices": consecutive_parser_indices,
    }


def parser_sentence_groups(
    grouped: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Represent raw Stage8 sentence groups without changing their geometry."""

    result: list[dict[str, Any]] = []
    for sentence_index in sorted(grouped):
        rows = _ordered_tokens(grouped[sentence_index])
        if not rows:
            continue
        result.append(
            {
                "sentence_indices": [int(sentence_index)],
                "tokens": rows,
                "coalesced_boundaries": [],
            }
        )
    return result


def coalesce_spacy_sentence_groups(
    grouped: dict[int, list[dict[str, Any]]],
    content: str,
) -> list[dict[str, Any]]:
    """Coalesce only source-proven lower-case continuation false splits.

    Raw Stage8 rows are never modified.  Returned groups contain the original
    rows plus explicit provenance describing each parser boundary that was
    removed by Stage10.
    """

    raw = parser_sentence_groups(grouped)
    if not raw:
        return []

    result: list[dict[str, Any]] = []
    current = {
        "sentence_indices": list(raw[0]["sentence_indices"]),
        "tokens": list(raw[0]["tokens"]),
        "coalesced_boundaries": [],
    }
    for next_group in raw[1:]:
        left_index = int(current["sentence_indices"][-1])
        right_index = int(next_group["sentence_indices"][0])
        # Evaluate the actual last raw parser sentence against the next one.
        left_rows = grouped[left_index]
        right_rows = grouped[right_index]
        decision = evaluate_spacy_sentence_boundary(
            content,
            left_index,
            left_rows,
            right_index,
            right_rows,
        )
        if decision["merge"] is True:
            current["sentence_indices"].append(right_index)
            current["tokens"].extend(next_group["tokens"])
            current["tokens"] = _ordered_tokens(current["tokens"])
            current["coalesced_boundaries"].append(decision)
            continue
        result.append(current)
        current = {
            "sentence_indices": list(next_group["sentence_indices"]),
            "tokens": list(next_group["tokens"]),
            "coalesced_boundaries": [],
        }
    result.append(current)
    return result
