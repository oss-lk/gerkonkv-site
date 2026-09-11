from __future__ import annotations

"""Default-off TC-big rescue for punctuation-only false-boundary Stage12 pairs.

This wrapper does not make broad Stage10-v2 geometry a Product default. Instead
it reuses the Stage10-v2 source-only boundary predicate as evidence for one
narrow second-model attempt over two complete adjacent V1 Stage12 rows.

A pair is eligible only when its immutable source boundary is independently
proved to be a lowercase-continuation false split, both rows exactly cover two
consecutive V1 Stage10 contexts, the current pair has punctuation hard failure(s)
but no numeric/symbol or length hard failure, and the combined source remains
inside a conservative complexity envelope. TC-big rank0 is the only candidate
considered. It is selected unchanged only when all maintained hard/research
checks, Gutenberg emphasis preservation and source-relative alphabetic-volume
checks pass. Otherwise both base rows remain byte/target exact.
"""

from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .context_sentence_boundaries import (
    STAGE10_BOUNDARY_POLICY,
    STAGE10_CONTEXT_IMPLEMENTATION_V1,
    evaluate_spacy_sentence_boundary,
)
from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import evaluate_rescue_pair
from .translation_tc_big_short_angular_dms_rescue_stage import run_stage12 as run_base_stage12

TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT = (
    "rocketdict-stage12-tc-big-boundary-pair-punctuation-rescue/1"
)
TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT = (
    "rocketdict-stage12-tc-big-boundary-pair-punctuation-selector/1"
)
TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT = (
    "rocketdict-stage12-tc-big-boundary-pair-punctuation-trigger/1"
)
TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTED_PHASE = (
    "tc-big-boundary-pair-punctuation-selected-v1"
)
DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 512
MAX_SOURCE_ALPHA_WORDS = 40
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_WRAPPER_KEYS = frozenset(
    {
        "enable_tc_big_boundary_pair_punctuation_rescue",
        "tc_big_boundary_pair_punctuation_rescue_contract",
        "tc_big_boundary_pair_punctuation_selector_contract",
        "tc_big_boundary_pair_punctuation_trigger_contract",
        "tc_big_boundary_pair_punctuation_rescue_phase",
    }
)


def _bool_parameter(value: Any, *, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise StageExecutionError(f"Stage12 {name} must be boolean")


def _base_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in parameters.items() if key not in _WRAPPER_KEYS}


def _source_alpha_ratio(source: str, target: str) -> float:
    source_alpha = sum(char.isalpha() for char in source)
    target_alpha = sum(char.isalpha() for char in target)
    if source_alpha <= 0:
        return 1.0 if target_alpha == 0 else float("inf")
    return target_alpha / source_alpha


def _alpha_word_count(source: str) -> int:
    return len(_ALPHA_WORD_RE.findall(source))


def _row_int(row: dict[str, Any], key: str, default: int = -1) -> int:
    value = row.get(key)
    return default if value is None else int(value)


def _hard_flags(source: str, target: str) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(source, target)
    return {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _planner_single_context(row: dict[str, Any]) -> int | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    if planner.get("source") != "nlp_sentence" or bool(planner.get("split")):
        return None
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
        count = int(planner.get("context_sentence_count", 1))
    except (KeyError, TypeError, ValueError):
        return None
    if first < 0 or first != last or count != 1:
        return None
    return first


def _context_spacy_sentence_index(row: dict[str, Any]) -> int | None:
    payload = dict(row.get("payload") or {})
    try:
        return int(payload["sentence_index"])
    except (KeyError, TypeError, ValueError):
        return None


def evaluate_tc_big_boundary_pair_punctuation_trigger(
    *,
    content: str,
    left: dict[str, Any],
    right: dict[str, Any],
    left_context: dict[str, Any],
    right_context: dict[str, Any],
    stage8_grouped: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Return generic source-owned eligibility for one adjacent pair."""
    left_source = str(left.get("source_text") or "")
    right_source = str(right.get("source_text") or "")
    left_target = str(left.get("target_text") or "")
    right_target = str(right.get("target_text") or "")
    start = _row_int(left, "source_start", 0)
    boundary = _row_int(right, "source_start", 0)
    end = _row_int(right, "source_end", 0)

    adjacent_source_geometry = _row_int(left, "source_end") == boundary
    pair_source = left_source + right_source
    immutable_source_exact = bool(
        adjacent_source_geometry
        and 0 <= start < boundary < end <= len(content)
        and content[start:end] == pair_source
    )

    left_context_sequence = _planner_single_context(left)
    right_context_sequence = _planner_single_context(right)
    consecutive_contexts = bool(
        left_context_sequence is not None
        and right_context_sequence is not None
        and right_context_sequence == left_context_sequence + 1
    )
    left_context_exact = bool(
        left_context_sequence is not None
        and _row_int(left_context, "sequence_number") == left_context_sequence
        and _row_int(left_context, "source_start") == _row_int(left, "source_start", -2)
        and _row_int(left_context, "source_end") == _row_int(left, "source_end", -2)
        and str(left_context.get("source_text") or "") == left_source
    )
    right_context_exact = bool(
        right_context_sequence is not None
        and _row_int(right_context, "sequence_number") == right_context_sequence
        and _row_int(right_context, "source_start") == _row_int(right, "source_start", -2)
        and _row_int(right_context, "source_end") == _row_int(right, "source_end", -2)
        and str(right_context.get("source_text") or "") == right_source
    )

    left_spacy = _context_spacy_sentence_index(left_context)
    right_spacy = _context_spacy_sentence_index(right_context)
    boundary_decision: dict[str, Any] | None = None
    if left_spacy is not None and right_spacy is not None:
        left_tokens = stage8_grouped.get(left_spacy) or []
        right_tokens = stage8_grouped.get(right_spacy) or []
        if left_tokens and right_tokens:
            boundary_decision = evaluate_spacy_sentence_boundary(
                content, left_spacy, left_tokens, right_spacy, right_tokens
            )
    source_boundary_proven = bool(
        boundary_decision
        and boundary_decision.get("policy") == STAGE10_BOUNDARY_POLICY
        and boundary_decision.get("merge") is True
        and boundary_decision.get("reason") == "lowercase_continuation_without_terminal"
        and int(boundary_decision.get("source_offset") or -1) == boundary
    )

    left_flags = _hard_flags(left_source, left_target)
    right_flags = _hard_flags(right_source, right_target)
    punctuation_failures = int(left_flags["punctuation"]) + int(right_flags["punctuation"])
    numeric_failures = int(left_flags["numeric_symbol"]) + int(right_flags["numeric_symbol"])
    length_failures = int(left_flags["length"]) + int(right_flags["length"])
    punctuation_only_hard_family = bool(
        punctuation_failures > 0 and numeric_failures == 0 and length_failures == 0
    )
    source_alpha_words = _alpha_word_count(pair_source)
    within_source_complexity = source_alpha_words <= MAX_SOURCE_ALPHA_WORDS
    eligible = bool(
        immutable_source_exact
        and consecutive_contexts
        and left_context_exact
        and right_context_exact
        and source_boundary_proven
        and punctuation_only_hard_family
        and within_source_complexity
    )
    return {
        "contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT,
        "eligible": eligible,
        "source_start": start,
        "boundary_offset": boundary,
        "source_end": end,
        "adjacent_source_geometry": adjacent_source_geometry,
        "immutable_source_exact": immutable_source_exact,
        "left_context_sequence": left_context_sequence,
        "right_context_sequence": right_context_sequence,
        "consecutive_v1_contexts": consecutive_contexts,
        "left_context_exact": left_context_exact,
        "right_context_exact": right_context_exact,
        "stage10_v2_boundary_proven": source_boundary_proven,
        "boundary_decision": boundary_decision,
        "base_left_hard_failures": left_flags,
        "base_right_hard_failures": right_flags,
        "base_pair_failure_counts": {
            "numeric_symbol": numeric_failures,
            "punctuation": punctuation_failures,
            "length": length_failures,
        },
        "punctuation_only_hard_family": punctuation_only_hard_family,
        "source_alpha_word_count": source_alpha_words,
        "source_alpha_word_cap": MAX_SOURCE_ALPHA_WORDS,
        "source_complexity_passed": within_source_complexity,
    }


def evaluate_tc_big_boundary_pair_punctuation_candidate(
    source: str, target: str
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _source_alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    accepted = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and ratio_passed
    )
    return {
        "selector_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "strict_research_passed": verdict.get("strict_research_passed") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "raw_target_nonempty": bool(target.strip()),
    }


def _safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["tc_big_boundary_pair_punctuation_rescue"] = {
        "contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT,
        "selector_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT,
        "applied": False,
        "base_translation_segment_id": int(row["id"]),
        **_safety_flags(),
    }
    return {
        "sequence_number": 0,
        "kind": "translation_segment",
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row.get("source_text") or ""),
        "target_text": str(row.get("target_text") or ""),
        "payload": payload,
    }


def _eligible_pairs(
    *,
    content: str,
    base_rows: list[dict[str, Any]],
    context_rows: list[dict[str, Any]],
    nlp_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(base_rows, key=lambda row: int(row["source_start"]))
    contexts = {int(row["sequence_number"]): row for row in context_rows}
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in nlp_rows:
        payload = dict(row.get("payload") or {})
        try:
            sentence_index = int(payload["sentence_index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StageExecutionError(
                "Boundary-pair rescue Stage8 token lacks sentence_index"
            ) from exc
        grouped[sentence_index].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: (int(row["source_start"]), int(row["sequence_number"])))

    attempts: list[dict[str, Any]] = []
    for left, right in zip(ordered, ordered[1:]):
        left_sequence = _planner_single_context(left)
        right_sequence = _planner_single_context(right)
        if left_sequence is None or right_sequence is None:
            continue
        left_context = contexts.get(left_sequence)
        right_context = contexts.get(right_sequence)
        if left_context is None or right_context is None:
            continue
        trigger = evaluate_tc_big_boundary_pair_punctuation_trigger(
            content=content,
            left=left,
            right=right,
            left_context=left_context,
            right_context=right_context,
            stage8_grouped=grouped,
        )
        if trigger["eligible"] is True:
            attempts.append(
                {
                    "left": left,
                    "right": right,
                    "left_context": left_context,
                    "right_context": right_context,
                    "trigger": trigger,
                }
            )

    counts = Counter()
    for attempt in attempts:
        counts[int(attempt["left"]["id"])] += 1
        counts[int(attempt["right"]["id"])] += 1
    overlapping = {row_id for row_id, count in counts.items() if count > 1}
    if overlapping:
        attempts = [
            attempt
            for attempt in attempts
            if int(attempt["left"]["id"]) not in overlapping
            and int(attempt["right"]["id"]) not in overlapping
        ]
    return attempts


def _merged_planner(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_planner = dict((left.get("payload") or {}).get("planner") or {})
    right_planner = dict((right.get("payload") or {}).get("planner") or {})
    first = int(left_planner["context_sentence_start"])
    last = int(right_planner["context_sentence_end"])
    return {
        **left_planner,
        "source": "nlp_sentence_group",
        "context_sentence_start": first,
        "context_sentence_end": last,
        "context_sentence_count": last - first + 1,
        "split": False,
        "boundary_pair_punctuation_rescue": True,
    }


def run_stage12(
    database: Path | str,
    *,
    context_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "opus-en-ru-ct2",
) -> dict[str, Any]:
    if implementation != "opus-en-ru-ct2":
        raise StageExecutionError(f"Unsupported real MT implementation: {implementation}")
    database = Path(database).expanduser().resolve()
    effective = dict(parameters or {})
    enabled = _bool_parameter(
        effective.get("enable_tc_big_boundary_pair_punctuation_rescue"),
        name="enable_tc_big_boundary_pair_punctuation_rescue",
        default=DEFAULT_ENABLED,
    )
    if not enabled:
        return run_base_stage12(
            database,
            context_run_id=int(context_run_id),
            parameters=_base_parameters(effective),
            implementation=implementation,
        )

    requested_contract = str(
        effective.get("tc_big_boundary_pair_punctuation_rescue_contract")
        or TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("tc_big_boundary_pair_punctuation_selector_contract")
        or TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT
    )
    requested_trigger = str(
        effective.get("tc_big_boundary_pair_punctuation_trigger_contract")
        or TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT
    )
    if requested_contract != TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT:
        raise StageExecutionError("Unsupported TC-big boundary-pair punctuation rescue contract")
    if requested_selector != TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT:
        raise StageExecutionError("Unsupported TC-big boundary-pair punctuation selector")
    if requested_trigger != TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT:
        raise StageExecutionError("Unsupported TC-big boundary-pair punctuation trigger")
    if effective.get("tc_big_boundary_pair_punctuation_rescue_phase") not in {
        None,
        TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "tc_big_boundary_pair_punctuation_rescue_phase is internal and may not be overridden"
        )

    effective["enable_tc_big_boundary_pair_punctuation_rescue"] = True
    effective["tc_big_boundary_pair_punctuation_rescue_contract"] = (
        TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT
    )
    effective["tc_big_boundary_pair_punctuation_selector_contract"] = (
        TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT
    )
    effective["tc_big_boundary_pair_punctuation_trigger_contract"] = (
        TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT
    )
    effective["tc_big_boundary_pair_punctuation_rescue_phase"] = (
        TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTED_PHASE
    )

    base_output = run_base_stage12(
        database,
        context_run_id=int(context_run_id),
        parameters=_base_parameters(effective),
        implementation=implementation,
    )
    base_run_id = int(base_output["translation_run_id"])
    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, base_run_id)
        base_rows = get_run_items(connection, base_run_id, kind="translation_segment")
        context_run = get_run(connection, int(context_run_id))
        if (
            int(context_run["stage_number"]) != 10
            or context_run["status"] != "completed"
            or str(context_run.get("implementation") or "") != STAGE10_CONTEXT_IMPLEMENTATION_V1
        ):
            raise StageExecutionError(
                "TC-big boundary-pair punctuation rescue requires completed Stage10 V1 context evidence"
            )
        context_rows = get_run_items(connection, int(context_run_id), kind="context_sentence")
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        nlp_rows = get_run_items(connection, nlp_run_id, kind="nlp_token")
        stored_output = dict(base_run.get("output") or {})
        document = get_document(connection, int(stored_output["document_version_id"]))

    input_identity = {
        "context_run_id": int(context_run_id),
        "context_output_sha256": str(context_run.get("output_sha256") or ""),
        "nlp_run_id": nlp_run_id,
        "document_version_id": int(stored_output["document_version_id"]),
        "source_text_sha256": str(document["text_sha256"]),
        "base_translation_run_id": base_run_id,
        "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
    }
    run_id, cached = _start(
        database,
        stage_number=12,
        implementation=implementation,
        input_identity=input_identity,
        parameters=effective,
    )
    if cached is not None:
        return cached

    try:
        content = str(document["content_text"])
        ordered_base = sorted(base_rows, key=lambda row: int(row["source_start"]))
        attempts = _eligible_pairs(
            content=content,
            base_rows=ordered_base,
            context_rows=context_rows,
            nlp_rows=nlp_rows,
        )
        generated: list[list[dict[str, Any]]] = []
        runtime_status: dict[str, Any] | None = None
        if attempts:
            runtime_status = tc_big_status()
            if runtime_status.get("available") is not True:
                raise StageExecutionError(
                    f"TC-big boundary-pair punctuation runtime unavailable: {runtime_status}"
                )
            translator = TcBigTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(
                [
                    str(attempt["left"]["source_text"])
                    + str(attempt["right"]["source_text"])
                    for attempt in attempts
                ],
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(
                len(hypotheses) != NUM_HYPOTHESES for hypotheses in generated
            ):
                raise StageExecutionError(
                    "TC-big boundary-pair punctuation rank0 cardinality drift"
                )

        accepted_by_left_id: dict[int, dict[str, Any]] = {}
        consumed_right_ids: set[int] = set()
        rejected: list[dict[str, Any]] = []
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            left = attempt["left"]
            right = attempt["right"]
            hypothesis = dict(hypotheses[0])
            if int(hypothesis.get("rank") or 0) != 0:
                raise StageExecutionError(
                    "TC-big boundary-pair punctuation expected rank0-only generation"
                )
            combined_source = str(left["source_text"]) + str(right["source_text"])
            target = str(hypothesis.get("text") or "")
            selection = evaluate_tc_big_boundary_pair_punctuation_candidate(
                combined_source, target
            )
            if selection["accepted"] is not True:
                rejected.append(
                    {
                        "source_start": int(left["source_start"]),
                        "boundary_offset": int(right["source_start"]),
                        "reason": "rank0_selector_rejected",
                        "rank0_target": target,
                        "selection": selection,
                    }
                )
                continue

            payload = dict(left.get("payload") or {})
            payload["planner"] = _merged_planner(left, right)
            payload["hypotheses"] = [hypothesis]
            payload["selected_rank"] = 0
            payload["tc_big_boundary_pair_punctuation_rescue"] = {
                "contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT,
                "selector_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT,
                "trigger_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT,
                "applied": True,
                "trigger": dict(attempt["trigger"]),
                "selection": selection,
                "base_translation_run_id": base_run_id,
                "base_translation_segment_ids": [int(left["id"]), int(right["id"])],
                "base_targets": [
                    str(left.get("target_text") or ""),
                    str(right.get("target_text") or ""),
                ],
                "raw_model_selected": True,
                "raw_model_rank": 0,
                "generation": {
                    "beam_size": BEAM_SIZE,
                    "num_hypotheses": NUM_HYPOTHESES,
                    "max_decoding_length": MAX_DECODING_LENGTH,
                },
                **_safety_flags(),
            }
            accepted_by_left_id[int(left["id"])] = {
                "right_id": int(right["id"]),
                "source_start": int(left["source_start"]),
                "boundary_offset": int(right["source_start"]),
                "source_end": int(right["source_end"]),
                "source_text": combined_source,
                "target_text": target,
                "payload": payload,
            }
            consumed_right_ids.add(int(right["id"]))

        final_rows: list[dict[str, Any]] = []
        for row in ordered_base:
            row_id = int(row["id"])
            if row_id in consumed_right_ids:
                continue
            replacement = accepted_by_left_id.get(row_id)
            if replacement is None:
                final_rows.append(_copy_base_row(row))
            else:
                final_rows.append(
                    {
                        "sequence_number": 0,
                        "kind": "translation_segment",
                        "source_start": int(replacement["source_start"]),
                        "source_end": int(replacement["source_end"]),
                        "source_text": str(replacement["source_text"]),
                        "target_text": str(replacement["target_text"]),
                        "payload": replacement["payload"],
                    }
                )

        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number
        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError(
                "TC-big boundary-pair punctuation final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(len(str(row.get("source_text") or "")) for row in ordered_base)
        if source_sum != base_source_sum or source_sum != len(content):
            raise StageExecutionError(
                "TC-big boundary-pair punctuation changed total source coverage"
            )
        if len(final_rows) != len(ordered_base) - len(accepted_by_left_id):
            raise StageExecutionError(
                "TC-big boundary-pair punctuation segment cardinality invariant failed"
            )

        accepted_values = sorted(
            accepted_by_left_id.values(), key=lambda value: int(value["source_start"])
        )
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "tc_big_boundary_pair_punctuation_rescue_contract": (
                TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT
            ),
            "tc_big_boundary_pair_punctuation_selector_contract": (
                TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT
            ),
            "tc_big_boundary_pair_punctuation_trigger_contract": (
                TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT
            ),
            "tc_big_boundary_pair_punctuation_rescue_enabled": True,
            "tc_big_boundary_pair_punctuation_rescue_attempt_count": len(attempts),
            "tc_big_boundary_pair_punctuation_rescue_accepted_count": len(accepted_values),
            "tc_big_boundary_pair_punctuation_rescue_rejected_count": len(rejected),
            "tc_big_boundary_pair_punctuation_rescue_attempted_boundaries": [
                int(attempt["right"]["source_start"]) for attempt in attempts
            ],
            "tc_big_boundary_pair_punctuation_rescue_accepted_boundaries": [
                int(value["boundary_offset"]) for value in accepted_values
            ],
            "tc_big_boundary_pair_punctuation_rescue_accepted_source_starts": [
                int(value["source_start"]) for value in accepted_values
            ],
            "tc_big_boundary_pair_punctuation_rescue_selected_ranks": [
                0 for _value in accepted_values
            ],
            "tc_big_boundary_pair_punctuation_rescue_selected_targets": [
                str(value["target_text"]) for value in accepted_values
            ],
            "tc_big_boundary_pair_punctuation_rescue_model_request_count": len(attempts),
            "tc_big_boundary_pair_punctuation_rescue_model_batch_count": 1 if attempts else 0,
            "tc_big_boundary_pair_punctuation_rescue_runtime": runtime_status,
            "base_segment_count": len(ordered_base),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "model_request_count": int(base_output.get("model_request_count") or 0) + len(attempts),
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
