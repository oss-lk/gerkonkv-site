from __future__ import annotations

"""Fail-closed Stage12 selection for narrow source-derived resegmentation rescue.

The maintained planner remains the primary source segmentation.  This module
only defines a second real-OPUS attempt for an ordinary TXT context whose
primary output exhibits isolated numeric *omission* consistent with semantic
content loss.  It never rewrites source or target bytes, never injects missing
literals, and never applies to already-clean contexts.

Candidate source chunks may move an over-budget cut at most eight lexical tokens
backward to a semicolon outside and not immediately adjacent to a protected
source span.  The candidate context is accepted only when every raw rank-0
candidate passes all Product hard checks plus the maintained research
structural diagnostics, the numeric omission is eliminated, and aggregate
target alphabetic content does not shrink relative to the primary context.
"""

from typing import Any

from .numeric_integrity import evaluate_numeric_symbol_pair
from .research_diagnostics import (
    compare_critical_technical_tokens,
    compare_delimiter_preservation,
    compare_numeric_order,
    compare_output_artifacts,
)

RESCUE_CONTRACT = "rocketdict-stage12-selective-resegmentation-rescue/1"
SELECTOR_CONTRACT = "rocketdict-stage12-selective-resegmentation-selector/1"
BACKTRACK_TOKENS = 8
BOUNDARY_PUNCTUATION = ";"
LENGTH_MIN_RATIO = 0.15
LENGTH_MAX_RATIO = 6.0


def _cut_inside_span(cut: int, spans: list[tuple[int, int, str]]) -> bool:
    return any(int(start) < cut < int(end) for start, end, _kind in spans)


def _adjacent_to_protected_span(
    tokens: list[dict[str, Any]],
    punctuation_index: int,
    split_index: int,
    spans: list[tuple[int, int, str]],
) -> bool:
    punctuation_start = int(tokens[punctuation_index]["source_start"])
    cut = int(tokens[split_index]["source_start"])
    return any(
        int(end) == punctuation_start or int(start) == cut
        for start, end, _kind in spans
    )


def _safe_forward_split_index(
    tokens: list[dict[str, Any]],
    *,
    desired_index: int,
    spans: list[tuple[int, int, str]],
) -> int:
    if desired_index >= len(tokens):
        return len(tokens)
    for index in range(desired_index, len(tokens)):
        if not _cut_inside_span(int(tokens[index]["source_start"]), spans):
            return index
    return len(tokens)


def build_selective_resegmentation_chunks(
    content: str,
    *,
    start: int,
    end: int,
    tokens: list[dict[str, Any]],
    spans: list[tuple[int, int, str]],
    preferred_tokens: int,
) -> list[dict[str, Any]]:
    """Return byte-exact candidate chunks or the maintained split where no safe ``;`` exists."""
    if preferred_tokens < 1:
        raise ValueError("preferred_tokens must be positive")
    if start < 0 or end <= start or end > len(content):
        raise ValueError("invalid selective rescue source span")
    if not tokens:
        return [{
            "start": start,
            "end": end,
            "text": content[start:end],
            "token_count": 0,
            "split_mode": "unsplit",
            "backtrack_tokens": 0,
        }]

    chunks: list[dict[str, Any]] = []
    cursor = start
    token_index = 0
    while token_index < len(tokens):
        desired_index = min(token_index + preferred_tokens, len(tokens))
        if desired_index >= len(tokens):
            split_index = len(tokens)
            split_mode = "final"
            backtrack = 0
        else:
            maintained = _safe_forward_split_index(
                tokens, desired_index=desired_index, spans=spans
            )
            split_index = maintained
            split_mode = "maintained"
            backtrack = 0
            lower = max(token_index, desired_index - BACKTRACK_TOKENS)
            for punctuation_index in range(desired_index - 1, lower - 1, -1):
                token_text = str(
                    tokens[punctuation_index].get("source_text")
                    if tokens[punctuation_index].get("source_text") is not None
                    else tokens[punctuation_index].get("text") or ""
                )
                if token_text != BOUNDARY_PUNCTUATION:
                    continue
                candidate_index = punctuation_index + 1
                if candidate_index <= token_index or candidate_index >= len(tokens):
                    continue
                cut = int(tokens[candidate_index]["source_start"])
                if _cut_inside_span(cut, spans):
                    continue
                if _adjacent_to_protected_span(
                    tokens, punctuation_index, candidate_index, spans
                ):
                    continue
                split_index = candidate_index
                split_mode = "semicolon_backtrack"
                backtrack = desired_index - candidate_index
                break

        if split_index <= token_index:
            raise ValueError("selective rescue split failed to advance")
        if split_index >= len(tokens):
            cut = end
            split_index = len(tokens)
        else:
            cut = int(tokens[split_index]["source_start"])
        if cut <= cursor:
            raise ValueError("selective rescue produced a non-positive chunk")
        chunks.append({
            "start": cursor,
            "end": cut,
            "text": content[cursor:cut],
            "token_count": split_index - token_index,
            "split_mode": split_mode,
            "backtrack_tokens": backtrack,
        })
        cursor = cut
        token_index = split_index

    if cursor != end:
        raise ValueError("selective rescue failed complete source coverage")
    if "".join(str(row["text"]) for row in chunks) != content[start:end]:
        raise ValueError("selective rescue source coverage is not byte-exact")
    return chunks


def _punctuation_passed(source: str, target: str) -> bool:
    for left, right in (("(", ")"), ("[", "]"), ("{", "}")):
        if source.count(left) != target.count(left):
            return False
        if source.count(right) != target.count(right):
            return False
    return all(source.count(mark) == target.count(mark) for mark in ("?", "!"))


def _length_passed(source: str, target: str) -> tuple[bool, float | str]:
    source_alpha = sum(char.isalpha() for char in source)
    target_alpha = sum(char.isalpha() for char in target)
    if source_alpha:
        ratio = target_alpha / source_alpha
        passed = bool(target.strip()) and LENGTH_MIN_RATIO <= ratio <= LENGTH_MAX_RATIO
        return passed, ratio
    passed = bool(target.strip()) and target_alpha == 0
    return passed, 1.0 if passed else "infinite"


def evaluate_rescue_pair(source: str, target: str) -> dict[str, Any]:
    numeric = evaluate_numeric_symbol_pair(source, target)
    punctuation_passed = _punctuation_passed(source, target)
    length_passed, length_ratio = _length_passed(source, target)
    numeric_order = compare_numeric_order(source, target)
    delimiters = compare_delimiter_preservation(source, target)
    critical = compare_critical_technical_tokens(source, target)
    output_artifacts = compare_output_artifacts(source, target)
    product_hard_passed = (
        numeric["passed"] is True
        and punctuation_passed
        and length_passed
        and bool(target.strip())
    )
    research_passed = (
        numeric_order["passed"] is True
        and delimiters["passed"] is True
        and critical["passed"] is True
        and output_artifacts["passed"] is True
    )
    return {
        "selector_contract": SELECTOR_CONTRACT,
        "product_hard_passed": product_hard_passed,
        "strict_research_passed": research_passed,
        "strictly_eligible": product_hard_passed and research_passed,
        "numeric_symbol": numeric,
        "punctuation_passed": punctuation_passed,
        "length_passed": length_passed,
        "length_ratio": length_ratio,
        "numeric_order": numeric_order,
        "delimiter_preservation": delimiters,
        "critical_technical_tokens": critical,
        "output_artifacts": output_artifacts,
    }


def evaluate_primary_context_trigger(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Require isolated missing-literal numeric loss and no unrelated hard/structural defect."""
    verdicts: list[dict[str, Any]] = []
    omission_count = 0
    eligible = bool(rows)
    for row in rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        verdicts.append(verdict)
        numeric = dict(verdict["numeric_symbol"])
        detail = dict(numeric["numeric"])
        if numeric["passed"] is True:
            # Clean primary chunks must still be structurally safe. Numeric order
            # is meaningful here and therefore part of the non-trigger checks.
            if (
                verdict["punctuation_passed"] is not True
                or verdict["length_passed"] is not True
                or verdict["delimiter_preservation"]["passed"] is not True
                or verdict["critical_technical_tokens"]["passed"] is not True
                or verdict["output_artifacts"]["passed"] is not True
                or verdict["numeric_order"]["passed"] is not True
            ):
                eligible = False
            continue

        missing_only = (
            bool(detail.get("missing"))
            and not detail.get("duplicate_required")
            and not detail.get("unlicensed_additions")
            and not numeric.get("symbol_mismatch")
            and dict(detail.get("prime_notation") or {}).get("passed") is True
        )
        non_numeric_safe = (
            verdict["punctuation_passed"] is True
            and verdict["length_passed"] is True
            and verdict["delimiter_preservation"]["passed"] is True
            and verdict["critical_technical_tokens"]["passed"] is True
            and verdict["output_artifacts"]["passed"] is True
        )
        if missing_only and non_numeric_safe:
            omission_count += sum(int(value) for value in dict(detail["missing"]).values())
        else:
            eligible = False

    eligible = eligible and omission_count > 0
    return {
        "contract": RESCUE_CONTRACT,
        "eligible": eligible,
        "trigger": "isolated_missing_numeric_literal" if eligible else None,
        "missing_literal_count": omission_count,
        "primary_verdicts": verdicts,
    }


def evaluate_candidate_context(
    primary_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    verdicts = [
        evaluate_rescue_pair(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        for row in candidate_rows
    ]
    primary_alpha = sum(
        sum(char.isalpha() for char in str(row.get("target_text") or ""))
        for row in primary_rows
    )
    candidate_alpha = sum(
        sum(char.isalpha() for char in str(row.get("target_text") or ""))
        for row in candidate_rows
    )
    strict_clean = bool(verdicts) and all(
        verdict["strictly_eligible"] is True for verdict in verdicts
    )
    numeric_clean = bool(verdicts) and all(
        verdict["numeric_symbol"]["passed"] is True for verdict in verdicts
    )
    alpha_non_decreasing = candidate_alpha >= primary_alpha
    accepted = strict_clean and numeric_clean and alpha_non_decreasing
    return {
        "contract": RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "accepted": accepted,
        "strict_clean": strict_clean,
        "numeric_clean": numeric_clean,
        "target_alpha_primary": primary_alpha,
        "target_alpha_candidate": candidate_alpha,
        "target_alpha_non_decreasing": alpha_non_decreasing,
        "candidate_verdicts": verdicts,
    }
