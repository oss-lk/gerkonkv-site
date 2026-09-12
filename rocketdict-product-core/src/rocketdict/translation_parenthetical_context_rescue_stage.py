from __future__ import annotations

"""Default-off OPUS rescue for one bounded split-parenthetical defect class.

The current Stage12 planner remains authoritative.  This wrapper only considers
an exact Stage10 linguistic context that is split across two or more current
rows, contains exactly one balanced source ``(...)`` pair, and whose aggregate
current target has lost both round-parenthesis delimiters.  Other hard
punctuation must already match, unrelated maintained research checks must be
clean, the parenthetical payload must be short, and the context must stay inside
the proven 160-NLP-token whole-context cap.

Only the unmodified primary OPUS rank0 translation of the exact Stage10 source
is considered.  The candidate must pass every maintained hard/research check,
preserve Gutenberg emphasis, exactly preserve hard punctuation, stay inside a
source-relative alphabetic envelope, and not reduce aggregate alphabetic
content versus the current split translation.  Rejection leaves every base row
exact.  No source rewriting, target surgery, literal injection, placeholders,
n-best cherry-picking or corpus-specific whitelist is used.
"""

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import evaluate_rescue_pair
from .translation_question_context_rescue_stage import (
    MAX_CONTEXT_NLP_TOKENS,
    _alpha_count,
    _context_token_count,
    _planner_single_split_context,
    _punctuation_counts,
    _rows_cover_context,
    _safety_flags,
    _source_alpha_ratio,
    run_stage12 as run_base_stage12,
)

PARENTHETICAL_CONTEXT_RESCUE_CONTRACT = (
    "rocketdict-stage12-parenthetical-whole-context-rescue/1"
)
PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT = (
    "rocketdict-stage12-parenthetical-whole-context-selector/1"
)
PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT = (
    "rocketdict-stage12-parenthetical-whole-context-trigger/1"
)
PARENTHETICAL_CONTEXT_SELECTED_PHASE = "parenthetical-whole-context-selected-v1"
DEFAULT_ENABLED = False
MAX_CONTEXT_NLP_TOKENS = MAX_CONTEXT_NLP_TOKENS
MAX_PARENTHETICAL_ALPHA_WORDS = 8
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50
_OTHER_HARD_PUNCTUATION = "[]{}?!"
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_WRAPPER_KEYS = frozenset(
    {
        "enable_parenthetical_whole_context_rescue",
        "parenthetical_whole_context_rescue_contract",
        "parenthetical_whole_context_selector_contract",
        "parenthetical_whole_context_trigger_contract",
        "parenthetical_whole_context_rescue_phase",
        "parenthetical_whole_context_max_nlp_tokens",
        "parenthetical_whole_context_max_parenthetical_alpha_words",
    }
)


def _bool_parameter(value: Any, *, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise StageExecutionError(f"Stage12 {name} must be boolean")


def _positive_int_parameter(value: Any, *, name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise StageExecutionError(f"Stage12 {name} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise StageExecutionError(f"Stage12 {name} must be a positive integer") from exc
    if parsed <= 0:
        raise StageExecutionError(f"Stage12 {name} must be a positive integer")
    return parsed


def _base_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in parameters.items() if key not in _WRAPPER_KEYS}


def _single_parenthetical_payload(source: str) -> str | None:
    if source.count("(") != 1 or source.count(")") != 1:
        return None
    opening = source.find("(")
    closing = source.find(")", opening + 1)
    if opening < 0 or closing <= opening:
        return None
    if source.find(")", closing + 1) >= 0:
        return None
    return source[opening + 1 : closing]


def _parenthetical_alpha_words(source: str) -> int | None:
    payload = _single_parenthetical_payload(source)
    if payload is None:
        return None
    return len(_ALPHA_WORD_RE.findall(payload))


def _research_clean_except_round_parentheses(source: str, target: str) -> tuple[bool, dict[str, Any]]:
    verdict = evaluate_rescue_pair(source, target)
    other_punctuation_exact = all(
        source.count(symbol) == target.count(symbol)
        for symbol in _OTHER_HARD_PUNCTUATION
    )
    clean = bool(
        (verdict.get("numeric_symbol") or {}).get("passed") is True
        and verdict.get("length_passed") is True
        and (verdict.get("numeric_order") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and (verdict.get("output_artifacts") or {}).get("passed") is True
        and other_punctuation_exact
    )
    return clean, verdict


def evaluate_parenthetical_context_trigger(
    *,
    content: str,
    context: dict[str, Any],
    primary_rows: list[dict[str, Any]],
    max_nlp_tokens: int = MAX_CONTEXT_NLP_TOKENS,
    max_parenthetical_alpha_words: int = MAX_PARENTHETICAL_ALPHA_WORDS,
) -> dict[str, Any]:
    start = int(context.get("source_start") or 0)
    end = int(context.get("source_end") or 0)
    source = str(context.get("source_text") or "")
    sequence = int(context.get("sequence_number") or 0)
    ordered = sorted(primary_rows, key=lambda row: int(row["source_start"]))
    source_exact = bool(0 <= start < end <= len(content) and content[start:end] == source)
    rows_exact = _rows_cover_context(ordered, start=start, end=end, source=source)
    planner_exact = bool(
        ordered and all(_planner_single_split_context(row) == sequence for row in ordered)
    )
    token_count = _context_token_count(context)
    within_token_cap = bool(0 < token_count <= int(max_nlp_tokens))
    parenthetical_words = _parenthetical_alpha_words(source)
    source_shape = parenthetical_words is not None
    payload_bounded = bool(
        parenthetical_words is not None
        and 0 < parenthetical_words <= int(max_parenthetical_alpha_words)
    )
    aggregate_target = "".join(str(row.get("target_text") or "") for row in ordered)
    target_lost_pair = aggregate_target.count("(") == 0 and aggregate_target.count(")") == 0
    aggregate_other_punctuation_exact = all(
        source.count(symbol) == aggregate_target.count(symbol)
        for symbol in _OTHER_HARD_PUNCTUATION
    )

    member_verdicts: list[dict[str, Any]] = []
    member_research_clean = True
    punctuation_failure_count = 0
    for row in ordered:
        clean, verdict = _research_clean_except_round_parentheses(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        member_verdicts.append(verdict)
        if not clean:
            member_research_clean = False
        if verdict.get("punctuation_passed") is not True:
            punctuation_failure_count += 1

    eligible = bool(
        source_exact
        and rows_exact
        and planner_exact
        and within_token_cap
        and source_shape
        and payload_bounded
        and target_lost_pair
        and aggregate_other_punctuation_exact
        and member_research_clean
        and punctuation_failure_count >= 1
    )
    return {
        "contract": PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
        "eligible": eligible,
        "context_sequence": sequence,
        "source_start": start,
        "source_end": end,
        "immutable_source_exact": source_exact,
        "complete_current_rows": rows_exact,
        "split_planner_geometry_exact": planner_exact,
        "member_count": len(ordered),
        "member_sequences": [int(row["sequence_number"]) for row in ordered],
        "context_nlp_token_count": token_count,
        "context_nlp_token_cap": int(max_nlp_tokens),
        "within_context_nlp_token_cap": within_token_cap,
        "source_single_balanced_parenthetical": source_shape,
        "source_round_parentheses": [source.count("("), source.count(")")],
        "aggregate_target_round_parentheses": [
            aggregate_target.count("("), aggregate_target.count(")")
        ],
        "target_lost_complete_parenthesis_pair": target_lost_pair,
        "parenthetical_alpha_word_count": parenthetical_words,
        "parenthetical_alpha_word_cap": int(max_parenthetical_alpha_words),
        "parenthetical_payload_bounded": payload_bounded,
        "aggregate_other_hard_punctuation_exact": aggregate_other_punctuation_exact,
        "member_research_clean_except_round_parentheses": member_research_clean,
        "punctuation_failure_count": punctuation_failure_count,
        "aggregate_current_target": aggregate_target,
        "member_verdicts": member_verdicts,
    }


def evaluate_parenthetical_context_candidate(
    source: str,
    target: str,
    *,
    primary_target: str,
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_counts = _punctuation_counts(source)
    target_counts = _punctuation_counts(target)
    punctuation_exact = source_counts == target_counts
    ratio = _source_alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    primary_alpha = _alpha_count(primary_target)
    candidate_alpha = _alpha_count(target)
    alpha_non_decreasing = candidate_alpha >= primary_alpha
    accepted = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and punctuation_exact
        and ratio_passed
        and alpha_non_decreasing
    )
    return {
        "selector_contract": PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "strict_research_passed": verdict.get("strict_research_passed") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_punctuation_counts": source_counts,
        "target_punctuation_counts": target_counts,
        "hard_punctuation_exact": punctuation_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "target_alpha_primary": primary_alpha,
        "target_alpha_candidate": candidate_alpha,
        "target_alpha_non_decreasing": alpha_non_decreasing,
        "raw_target_nonempty": bool(target.strip()),
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["parenthetical_whole_context_rescue"] = {
        "contract": PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
        "selector_contract": PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
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


def _eligible_contexts(
    *,
    content: str,
    base_rows: list[dict[str, Any]],
    context_rows: list[dict[str, Any]],
    max_nlp_tokens: int,
    max_parenthetical_alpha_words: int,
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in base_rows:
        sequence = _planner_single_split_context(row)
        if sequence is not None:
            grouped[sequence].append(row)
    attempts: list[dict[str, Any]] = []
    for context in sorted(context_rows, key=lambda row: int(row["sequence_number"])):
        sequence = int(context["sequence_number"])
        members = sorted(grouped.get(sequence, []), key=lambda row: int(row["source_start"]))
        if len(members) < 2:
            continue
        trigger = evaluate_parenthetical_context_trigger(
            content=content,
            context=context,
            primary_rows=members,
            max_nlp_tokens=max_nlp_tokens,
            max_parenthetical_alpha_words=max_parenthetical_alpha_words,
        )
        if trigger["eligible"] is True:
            attempts.append({"context": context, "primary_rows": members, "trigger": trigger})
    return attempts


def _replacement_row(
    *,
    attempt: dict[str, Any],
    target: str,
    hypothesis: dict[str, Any],
    selection: dict[str, Any],
    base_run_id: int,
) -> dict[str, Any]:
    context = attempt["context"]
    primary_rows = list(attempt["primary_rows"])
    first_planner = dict((primary_rows[0].get("payload") or {}).get("planner") or {})
    sequence = int(context["sequence_number"])
    payload = {
        "planner": {
            **first_planner,
            "source": "nlp_sentence",
            "context_sentence_start": sequence,
            "context_sentence_end": sequence,
            "context_sentence_count": 1,
            "split": False,
            "token_count": _context_token_count(context),
            "rescue_strategy": "parenthetical_whole_context",
            "parenthetical_whole_context_rescue_contract": PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
        },
        "hypotheses": [hypothesis],
        "selected_rank": 0,
        "parenthetical_whole_context_rescue": {
            "contract": PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
            "selector_contract": PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
            "trigger_contract": PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
            "applied": True,
            "trigger": dict(attempt["trigger"]),
            "selection": selection,
            "base_translation_run_id": int(base_run_id),
            "base_translation_segment_ids": [int(row["id"]) for row in primary_rows],
            "base_source_spans": [
                [int(row["source_start"]), int(row["source_end"])] for row in primary_rows
            ],
            "base_targets": [str(row.get("target_text") or "") for row in primary_rows],
            "raw_model_selected": True,
            "raw_model_rank": 0,
            "model": "opus-en-ru-ct2",
            "generation": {
                "beam_size": BEAM_SIZE,
                "num_hypotheses": NUM_HYPOTHESES,
                "max_decoding_length": MAX_DECODING_LENGTH,
            },
            **_safety_flags(),
        },
    }
    return {
        "sequence_number": 0,
        "kind": "translation_segment",
        "source_start": int(context["source_start"]),
        "source_end": int(context["source_end"]),
        "source_text": str(context.get("source_text") or ""),
        "target_text": target,
        "payload": payload,
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
        effective.get("enable_parenthetical_whole_context_rescue"),
        name="enable_parenthetical_whole_context_rescue",
        default=DEFAULT_ENABLED,
    )
    cap = _positive_int_parameter(
        effective.get("parenthetical_whole_context_max_nlp_tokens"),
        name="parenthetical_whole_context_max_nlp_tokens",
        default=MAX_CONTEXT_NLP_TOKENS,
    )
    payload_cap = _positive_int_parameter(
        effective.get("parenthetical_whole_context_max_parenthetical_alpha_words"),
        name="parenthetical_whole_context_max_parenthetical_alpha_words",
        default=MAX_PARENTHETICAL_ALPHA_WORDS,
    )
    if cap > MAX_CONTEXT_NLP_TOKENS:
        raise StageExecutionError(
            "parenthetical_whole_context_max_nlp_tokens may not exceed the proven cap "
            f"{MAX_CONTEXT_NLP_TOKENS}"
        )
    if payload_cap > MAX_PARENTHETICAL_ALPHA_WORDS:
        raise StageExecutionError(
            "parenthetical_whole_context_max_parenthetical_alpha_words may not exceed the proven cap "
            f"{MAX_PARENTHETICAL_ALPHA_WORDS}"
        )
    if not enabled:
        return run_base_stage12(
            database,
            context_run_id=int(context_run_id),
            parameters=_base_parameters(effective),
            implementation=implementation,
        )

    if str(effective.get("parenthetical_whole_context_rescue_contract") or PARENTHETICAL_CONTEXT_RESCUE_CONTRACT) != PARENTHETICAL_CONTEXT_RESCUE_CONTRACT:
        raise StageExecutionError("Unsupported parenthetical whole-context rescue contract")
    if str(effective.get("parenthetical_whole_context_selector_contract") or PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT) != PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT:
        raise StageExecutionError("Unsupported parenthetical whole-context selector contract")
    if str(effective.get("parenthetical_whole_context_trigger_contract") or PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT) != PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT:
        raise StageExecutionError("Unsupported parenthetical whole-context trigger contract")
    if effective.get("parenthetical_whole_context_rescue_phase") not in {None, PARENTHETICAL_CONTEXT_SELECTED_PHASE}:
        raise StageExecutionError("parenthetical_whole_context_rescue_phase is internal")

    effective.update(
        {
            "enable_parenthetical_whole_context_rescue": True,
            "parenthetical_whole_context_rescue_contract": PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
            "parenthetical_whole_context_selector_contract": PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
            "parenthetical_whole_context_trigger_contract": PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
            "parenthetical_whole_context_rescue_phase": PARENTHETICAL_CONTEXT_SELECTED_PHASE,
            "parenthetical_whole_context_max_nlp_tokens": cap,
            "parenthetical_whole_context_max_parenthetical_alpha_words": payload_cap,
        }
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
        context_rows = get_run_items(connection, int(context_run_id), kind="context_sentence")
        stored_output = dict(base_run.get("output") or {})
        document_version_id = int(stored_output["document_version_id"])
        document = get_document(connection, document_version_id)

    input_identity = {
        "context_run_id": int(context_run_id),
        "document_version_id": document_version_id,
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
        attempts = _eligible_contexts(
            content=content,
            base_rows=base_rows,
            context_rows=context_rows,
            max_nlp_tokens=cap,
            max_parenthetical_alpha_words=payload_cap,
        )
        generated: list[list[dict[str, Any]]] = []
        if attempts:
            translator = OpusTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(
                [str(attempt["context"].get("source_text") or "") for attempt in attempts],
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(len(h) != 1 for h in generated):
                raise StageExecutionError("parenthetical OPUS rank0 cardinality drift")

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            hypothesis = hypotheses[0]
            if int(hypothesis.get("rank") or 0) != 0:
                raise StageExecutionError("parenthetical OPUS result is not rank0")
            context = attempt["context"]
            source = str(context.get("source_text") or "")
            primary_target = "".join(
                str(row.get("target_text") or "") for row in attempt["primary_rows"]
            )
            target = str(hypothesis.get("text") or "")
            selection = evaluate_parenthetical_context_candidate(
                source, target, primary_target=primary_target
            )
            sequence = int(context["sequence_number"])
            if selection["accepted"] is not True:
                rejected.append(
                    {
                        "context_sequence": sequence,
                        "source_start": int(context["source_start"]),
                        "reason": "rank0_selector_rejected",
                        "rank0_target": target,
                        "rank0_score": hypothesis.get("score"),
                        "selection": selection,
                    }
                )
                continue
            accepted[sequence] = {
                "context_sequence": sequence,
                "row": _replacement_row(
                    attempt=attempt,
                    target=target,
                    hypothesis=hypothesis,
                    selection=selection,
                    base_run_id=base_run_id,
                ),
                "selected_rank": 0,
                "target_text": target,
                "member_ids": {int(row["id"]) for row in attempt["primary_rows"]},
            }

        removed_ids = {
            row_id for value in accepted.values() for row_id in value["member_ids"]
        }
        final_rows = [
            _copy_base_row(row)
            for row in sorted(base_rows, key=lambda value: int(value["source_start"]))
            if int(row["id"]) not in removed_ids
        ]
        final_rows.extend(dict(value["row"]) for value in accepted.values())
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError("parenthetical rescue source coverage is not byte-exact")
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        if source_sum != sum(len(str(row.get("source_text") or "")) for row in base_rows):
            raise StageExecutionError("parenthetical rescue changed source coverage")

        accepted_values = sorted(
            accepted.values(), key=lambda value: int(value["row"]["source_start"])
        )
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "parenthetical_whole_context_rescue_contract": PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
            "parenthetical_whole_context_selector_contract": PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
            "parenthetical_whole_context_trigger_contract": PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
            "parenthetical_whole_context_rescue_enabled": True,
            "parenthetical_whole_context_max_nlp_tokens": cap,
            "parenthetical_whole_context_max_parenthetical_alpha_words": payload_cap,
            "parenthetical_whole_context_rescue_attempt_count": len(attempts),
            "parenthetical_whole_context_rescue_accepted_count": len(accepted_values),
            "parenthetical_whole_context_rescue_rejected_count": len(rejected),
            "parenthetical_whole_context_rescue_attempted_context_sequences": [
                int(attempt["context"]["sequence_number"]) for attempt in attempts
            ],
            "parenthetical_whole_context_rescue_accepted_context_sequences": [
                int(value["context_sequence"]) for value in accepted_values
            ],
            "parenthetical_whole_context_rescue_selected_ranks": [0 for _ in accepted_values],
            "parenthetical_whole_context_rescue_selected_targets": [
                str(value["target_text"]) for value in accepted_values
            ],
            "parenthetical_whole_context_rescue_rejections": rejected,
            "parenthetical_whole_context_rescue_model": "opus-en-ru-ct2",
            "parenthetical_whole_context_rescue_model_request_count": len(attempts),
            "parenthetical_whole_context_rescue_model_batch_count": 1 if attempts else 0,
            "base_segment_count": len(base_rows),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "model_request_count": int(base_output.get("model_request_count") or 0) + len(attempts),
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
