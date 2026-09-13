from __future__ import annotations

"""Corrected run59 forward-boundary DOE with a narrow attempt-gate repair.

V1 accidentally required the *base* left row to pass every research diagnostic,
which suppressed the intended source/planner geometry because the existing OPUS
target introduced a pair of quote delimiters.  Candidate selection was already
strict and remains unchanged.  This launcher only broadens *attempt eligibility*
for a Product-hard-clean left row whose sole tolerated research artifact is
introduced quote delimiters; entities/replacement characters remain forbidden.
The candidate rows and aggregate must still pass the original strict selector.
"""

from typing import Any

import real_translation_run59_forward_paragraph_boundary_resegmentation_doe as doe


doe.BASE_DATABASE_SHA256 = "41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d"
doe.SCHEMA = "rocketdict-run59-forward-paragraph-boundary-resegmentation-doe/2"


def _left_attempt_safe(verdict: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    artifacts = dict(verdict.get("output_artifacts") or {})
    quote_only_artifact = bool(
        artifacts.get("passed") is not True
        and not dict(artifacts.get("introduced_entities") or {})
        and int(artifacts.get("introduced_replacement_character_count") or 0) == 0
        and int(artifacts.get("introduced_quote_delimiter_count") or 0) > 0
    )
    artifacts_allowed = bool(artifacts.get("passed") is True or quote_only_artifact)
    safe = bool(
        verdict.get("product_hard_passed") is True
        and (verdict.get("numeric_order") or {}).get("passed") is True
        and (verdict.get("delimiter_preservation") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and artifacts_allowed
    )
    return safe, {
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "numeric_order_passed": (verdict.get("numeric_order") or {}).get("passed") is True,
        "delimiter_preservation_passed": (verdict.get("delimiter_preservation") or {}).get("passed") is True,
        "critical_technical_tokens_passed": (verdict.get("critical_technical_tokens") or {}).get("passed") is True,
        "output_artifacts_passed": artifacts.get("passed") is True,
        "quote_only_output_artifact_tolerated_for_attempt": quote_only_artifact,
        "candidate_selector_weakened": False,
        "accepted": safe,
    }


def discover_trigger_v3(
    *,
    content: str,
    left: dict[str, Any],
    right: dict[str, Any],
    nlp_tokens: list[dict[str, Any]],
) -> dict[str, Any] | None:
    left_geometry = doe._single_split_context(left)
    right_geometry = doe._single_split_context(right)
    if left_geometry is None or right_geometry is None:
        return None
    left_context, left_token_count, preferred = left_geometry
    right_context, right_token_count, right_preferred = right_geometry
    if left_context != right_context or preferred != right_preferred:
        return None

    left_start = int(left["source_start"])
    left_end = int(left["source_end"])
    right_start = int(right["source_start"])
    right_end = int(right["source_end"])
    left_source = str(left.get("source_text") or "")
    right_source = str(right.get("source_text") or "")
    left_target = str(left.get("target_text") or "")
    right_target = str(right.get("target_text") or "")

    if left_end != right_start:
        return None
    if not (
        0 <= left_start < left_end < right_end <= len(content)
        and content[left_start:left_end] == left_source
        and content[right_start:right_end] == right_source
    ):
        return None

    match = doe._PREFIX_RE.match(right_source)
    if match is None:
        return None
    prefix = match.group(1)
    suffix = right_source[len(prefix) :]
    if not suffix.strip() or doe._alpha_word_count(suffix) < doe.MIN_SUFFIX_ALPHA_WORDS:
        return None
    if prefix.count("?") != 1 or suffix.count("?") != 0:
        return None

    new_boundary = right_start + len(prefix)
    prefix_tokens = doe._non_space_nlp_tokens(
        nlp_tokens, start=right_start, end=new_boundary
    )
    if not (1 <= len(prefix_tokens) <= doe.MAX_FORWARD_NLP_TOKENS):
        return None
    if left_token_count < preferred:
        return None
    if left_token_count + len(prefix_tokens) > preferred + doe.MAX_FORWARD_NLP_TOKENS:
        return None

    left_verdict = doe.evaluate_rescue_pair(left_source, left_target)
    right_verdict = doe.evaluate_rescue_pair(right_source, right_target)
    left_safe, left_gate = _left_attempt_safe(left_verdict)
    if not left_safe:
        return None
    if right_verdict.get("punctuation_passed") is True:
        return None
    if not doe._strict_non_punctuation_clean(right_verdict):
        return None
    if right_source.count("?") <= right_target.count("?"):
        return None

    candidate_left = content[left_start:new_boundary]
    candidate_right = content[new_boundary:right_end]
    if candidate_left != left_source + prefix or candidate_right != suffix:
        raise RuntimeError("forward paragraph resegmentation source coverage drift")
    return {
        "eligible": True,
        "context_sequence": left_context,
        "left_sequence": int(left["sequence_number"]),
        "right_sequence": int(right["sequence_number"]),
        "old_boundary": right_start,
        "new_boundary": new_boundary,
        "forward_char_count": len(prefix),
        "forward_nlp_token_count": len(prefix_tokens),
        "preferred_token_budget": preferred,
        "base_left_nlp_token_count": left_token_count,
        "base_right_nlp_token_count": right_token_count,
        "candidate_left_nlp_token_count": left_token_count + len(prefix_tokens),
        "candidate_right_nlp_token_count": right_token_count - len(prefix_tokens),
        "prefix": prefix,
        "suffix_alpha_word_count": doe._alpha_word_count(suffix),
        "base_left_source": left_source,
        "base_right_source": right_source,
        "base_left_target": left_target,
        "base_right_target": right_target,
        "candidate_left_source": candidate_left,
        "candidate_right_source": candidate_right,
        "base_left_attempt_gate": left_gate,
        "base_left_verdict": left_verdict,
        "base_right_verdict": right_verdict,
    }


doe.discover_trigger = discover_trigger_v3


if __name__ == "__main__":
    raise SystemExit(doe.main())
