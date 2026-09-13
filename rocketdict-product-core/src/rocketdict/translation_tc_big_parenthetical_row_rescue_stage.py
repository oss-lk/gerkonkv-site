from __future__ import annotations

"""Default-off TC-big rescue for bounded row-local parenthetical loss.

This wrapper is deliberately row-local and fail-closed.  It only considers a
current Stage12 translation row whose immutable source contains one or two
balanced non-nested ``(...)`` pairs with short lexical payloads, while the
current target has lost one or more round-parenthesis delimiters without adding
new ones.  Other maintained hard punctuation and non-parenthesis research
checks must already be clean, and source complexity is conservatively bounded.

Only the unmodified pinned TC-big rank0 translation of the exact immutable row
source is considered.  Acceptance requires all maintained hard/research checks,
Gutenberg emphasis preservation, exact hard punctuation, a conservative
source-relative alphabetic range, and no reduction of alphabetic content versus
the current target.  Rejection leaves the base row exact.  No source rewriting,
target surgery, literal injection, placeholders, corpus-specific patches,
evaluator weakening, or n-best cherry-picking is used.
"""

from pathlib import Path
import re
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_illustration_rescue_stage import run_stage12 as run_base_stage12
from .translation_rescue import evaluate_rescue_pair


TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT = (
    "rocketdict-stage12-tc-big-parenthetical-row-rescue/1"
)
TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT = (
    "rocketdict-stage12-tc-big-parenthetical-row-selector/1"
)
TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT = (
    "rocketdict-stage12-tc-big-parenthetical-row-trigger/1"
)
TC_BIG_PARENTHETICAL_ROW_SELECTED_PHASE = "tc-big-parenthetical-row-selected-v1"

DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768
MIN_PARENTHESES_PAIRS = 1
MAX_PARENTHESES_PAIRS = 2
MAX_PARENTHESES_ALPHA_WORDS = 12
MAX_SOURCE_ALPHA_WORDS = 64
MAX_SOURCE_CHARS = 384
MIN_SOURCE_ALPHA_RATIO = 0.80
MAX_SOURCE_ALPHA_RATIO = 1.40

_ALL_HARD_PUNCTUATION = "()[]{}?!"
_OTHER_HARD_PUNCTUATION = "[]{}?!"
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_PARENTHETICAL_RE = re.compile(r"\(([^()]*)\)")
_WRAPPER_KEYS = frozenset(
    {
        "enable_tc_big_parenthetical_row_rescue",
        "tc_big_parenthetical_row_rescue_contract",
        "tc_big_parenthetical_row_selector_contract",
        "tc_big_parenthetical_row_trigger_contract",
        "tc_big_parenthetical_row_rescue_phase",
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


def _alpha_count(text: str) -> int:
    return sum(character.isalpha() for character in text)


def _alpha_word_count(text: str) -> int:
    return len(_ALPHA_WORD_RE.findall(text))


def _source_alpha_ratio(source: str, target: str) -> float:
    source_alpha = _alpha_count(source)
    target_alpha = _alpha_count(target)
    if source_alpha <= 0:
        return 1.0 if target_alpha == 0 else float("inf")
    return target_alpha / source_alpha


def _punctuation_counts(text: str) -> dict[str, int]:
    return {symbol: text.count(symbol) for symbol in _ALL_HARD_PUNCTUATION}


def _parenthetical_payloads(source: str) -> list[str] | None:
    if source.count("(") != source.count(")"):
        return None
    pair_count = source.count("(")
    if not (MIN_PARENTHESES_PAIRS <= pair_count <= MAX_PARENTHESES_PAIRS):
        return None
    payloads = _PARENTHETICAL_RE.findall(source)
    if len(payloads) != pair_count:
        return None
    alpha_counts = [_alpha_word_count(payload) for payload in payloads]
    if any(not (1 <= count <= MAX_PARENTHESES_ALPHA_WORDS) for count in alpha_counts):
        return None
    return payloads


def _base_clean_except_round_parentheses(
    source: str, target: str
) -> tuple[bool, dict[str, Any]]:
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


def evaluate_tc_big_parenthetical_row_trigger(
    row: dict[str, Any], *, source_exact: bool
) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    payloads = _parenthetical_payloads(source)
    source_counts = _punctuation_counts(source)
    target_counts = _punctuation_counts(target)
    round_mismatch = (
        source_counts["("] != target_counts["("]
        or source_counts[")"] != target_counts[")"]
    )
    round_loss_only = bool(
        target_counts["("] <= source_counts["("]
        and target_counts[")"] <= source_counts[")"]
        and round_mismatch
    )
    source_alpha_words = _alpha_word_count(source)
    source_chars = len(source)
    complexity_passed = bool(
        0 < source_alpha_words <= MAX_SOURCE_ALPHA_WORDS
        and 0 < source_chars <= MAX_SOURCE_CHARS
    )
    clean_except_round, verdict = _base_clean_except_round_parentheses(source, target)
    punctuation_failed = verdict.get("punctuation_passed") is not True
    eligible = bool(
        source_exact
        and payloads is not None
        and round_loss_only
        and clean_except_round
        and punctuation_failed
        and complexity_passed
    )
    return {
        "contract": TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT,
        "eligible": eligible,
        "immutable_source_exact": bool(source_exact),
        "source_parenthetical_payloads": payloads,
        "source_parenthetical_pair_count": None if payloads is None else len(payloads),
        "source_parenthetical_alpha_word_counts": (
            [] if payloads is None else [_alpha_word_count(value) for value in payloads]
        ),
        "source_punctuation_counts": source_counts,
        "target_punctuation_counts": target_counts,
        "round_parenthesis_loss_only": round_loss_only,
        "other_hard_punctuation_exact": all(
            source_counts[symbol] == target_counts[symbol]
            for symbol in _OTHER_HARD_PUNCTUATION
        ),
        "base_clean_except_round_parentheses": clean_except_round,
        "contains_current_punctuation_hard_failure": punctuation_failed,
        "source_alpha_word_count": source_alpha_words,
        "source_alpha_word_cap": MAX_SOURCE_ALPHA_WORDS,
        "source_char_count": source_chars,
        "source_char_cap": MAX_SOURCE_CHARS,
        "source_complexity_passed": complexity_passed,
        "base_verdict": verdict,
    }


def evaluate_tc_big_parenthetical_row_candidate(
    source: str, target: str, *, base_target: str
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_counts = _punctuation_counts(source)
    target_counts = _punctuation_counts(target)
    punctuation_exact = source_counts == target_counts
    ratio = _source_alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    base_alpha = _alpha_count(base_target)
    candidate_alpha = _alpha_count(target)
    base_alpha_retained = candidate_alpha >= base_alpha
    accepted = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and punctuation_exact
        and ratio_passed
        and base_alpha_retained
    )
    return {
        "selector_contract": TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT,
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
        "base_alpha_count": base_alpha,
        "candidate_alpha_count": candidate_alpha,
        "base_alpha_retained": base_alpha_retained,
        "raw_target_nonempty": bool(target.strip()),
    }


def _safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["tc_big_parenthetical_row_rescue"] = {
        "contract": TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT,
        "selector_contract": TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT,
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


def _eligible_rows(*, content: str, base_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for row in sorted(base_rows, key=lambda value: int(value["source_start"])):
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        source_exact = bool(
            0 <= start < end <= len(content) and content[start:end] == source
        )
        trigger = evaluate_tc_big_parenthetical_row_trigger(
            row, source_exact=source_exact
        )
        if trigger["eligible"] is True:
            attempts.append({"row": row, "trigger": trigger})
    return attempts


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
        effective.get("enable_tc_big_parenthetical_row_rescue"),
        name="enable_tc_big_parenthetical_row_rescue",
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
        effective.get("tc_big_parenthetical_row_rescue_contract")
        or TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("tc_big_parenthetical_row_selector_contract")
        or TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT
    )
    requested_trigger = str(
        effective.get("tc_big_parenthetical_row_trigger_contract")
        or TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT
    )
    if requested_contract != TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big parenthetical-row rescue contract {requested_contract!r}"
        )
    if requested_selector != TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big parenthetical-row selector {requested_selector!r}"
        )
    if requested_trigger != TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big parenthetical-row trigger {requested_trigger!r}"
        )
    if effective.get("tc_big_parenthetical_row_rescue_phase") not in {
        None,
        TC_BIG_PARENTHETICAL_ROW_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "tc_big_parenthetical_row_rescue_phase is internal and may not be overridden"
        )

    effective["enable_tc_big_parenthetical_row_rescue"] = True
    effective["tc_big_parenthetical_row_rescue_contract"] = (
        TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT
    )
    effective["tc_big_parenthetical_row_selector_contract"] = (
        TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT
    )
    effective["tc_big_parenthetical_row_trigger_contract"] = (
        TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT
    )
    effective["tc_big_parenthetical_row_rescue_phase"] = (
        TC_BIG_PARENTHETICAL_ROW_SELECTED_PHASE
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
        attempts = _eligible_rows(content=content, base_rows=base_rows)
        generated: list[list[dict[str, Any]]] = []
        runtime_status: dict[str, Any] | None = None
        if attempts:
            runtime_status = tc_big_status()
            if runtime_status.get("available") is not True:
                raise StageExecutionError(
                    f"TC-big parenthetical-row rescue runtime unavailable: {runtime_status}"
                )
            translator = TcBigTranslator(device="cpu", compute_type="float32")
            model_inputs = [
                str(attempt["row"].get("source_text") or "") for attempt in attempts
            ]
            generated = translator.translate(
                model_inputs,
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(
                len(hypotheses) != NUM_HYPOTHESES for hypotheses in generated
            ):
                raise StageExecutionError(
                    "TC-big parenthetical-row rescue rank0 cardinality drift"
                )

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            row = attempt["row"]
            source = str(row.get("source_text") or "")
            hypothesis = dict(hypotheses[0])
            if int(hypothesis.get("rank", -1)) != 0:
                raise StageExecutionError(
                    "TC-big parenthetical-row rescue result is not rank0"
                )
            target = str(hypothesis.get("text") or "")
            if not target.strip():
                raise StageExecutionError(
                    "TC-big parenthetical-row rescue received empty rank0 target"
                )
            selection = evaluate_tc_big_parenthetical_row_candidate(
                source,
                target,
                base_target=str(row.get("target_text") or ""),
            )
            if selection["accepted"] is not True:
                rejected.append(
                    {
                        "source_start": int(row["source_start"]),
                        "reason": "rank0_selector_rejected",
                        "rank0_target": target,
                        "rank0_score": hypothesis.get("score"),
                        "selection": selection,
                    }
                )
                continue

            payload = dict(row.get("payload") or {})
            payload["hypotheses"] = [hypothesis]
            payload["selected_rank"] = 0
            payload["tc_big_parenthetical_row_rescue"] = {
                "contract": TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT,
                "selector_contract": TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT,
                "trigger_contract": TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT,
                "applied": True,
                "trigger": dict(attempt["trigger"]),
                "selection": selection,
                "base_translation_run_id": base_run_id,
                "base_translation_segment_id": int(row["id"]),
                "base_target": str(row.get("target_text") or ""),
                "model": "tc-big-en-zle-ct2",
                "model_input": source,
                "model_input_equals_source": True,
                "raw_model_selected": True,
                "raw_model_rank": 0,
                "generation": {
                    "beam_size": BEAM_SIZE,
                    "num_hypotheses": NUM_HYPOTHESES,
                    "max_decoding_length": MAX_DECODING_LENGTH,
                },
                **_safety_flags(),
            }
            accepted[int(row["id"])] = {
                "source_start": int(row["source_start"]),
                "target_text": target,
                "selected_rank": 0,
                "payload": payload,
            }

        final_rows: list[dict[str, Any]] = []
        for row in sorted(base_rows, key=lambda value: int(value["source_start"])):
            replacement = accepted.get(int(row["id"]))
            if replacement is None:
                final_rows.append(_copy_base_row(row))
            else:
                final_rows.append(
                    {
                        "sequence_number": 0,
                        "kind": "translation_segment",
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(replacement["target_text"]),
                        "payload": replacement["payload"],
                    }
                )
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError(
                "TC-big parenthetical-row final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(len(str(row.get("source_text") or "")) for row in base_rows)
        if source_sum != base_source_sum:
            raise StageExecutionError(
                "TC-big parenthetical-row rescue changed total source coverage"
            )

        accepted_values = sorted(
            accepted.values(), key=lambda value: int(value["source_start"])
        )
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "tc_big_parenthetical_row_rescue_contract": (
                TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT
            ),
            "tc_big_parenthetical_row_selector_contract": (
                TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT
            ),
            "tc_big_parenthetical_row_trigger_contract": (
                TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT
            ),
            "tc_big_parenthetical_row_rescue_enabled": True,
            "tc_big_parenthetical_row_rescue_attempt_count": len(attempts),
            "tc_big_parenthetical_row_rescue_accepted_count": len(accepted_values),
            "tc_big_parenthetical_row_rescue_rejected_count": len(rejected),
            "tc_big_parenthetical_row_rescue_attempted_source_starts": [
                int(attempt["row"]["source_start"]) for attempt in attempts
            ],
            "tc_big_parenthetical_row_rescue_accepted_source_starts": [
                int(value["source_start"]) for value in accepted_values
            ],
            "tc_big_parenthetical_row_rescue_selected_ranks": [
                int(value["selected_rank"]) for value in accepted_values
            ],
            "tc_big_parenthetical_row_rescue_selected_targets": [
                str(value["target_text"]) for value in accepted_values
            ],
            "tc_big_parenthetical_row_rescue_model_request_count": len(attempts),
            "tc_big_parenthetical_row_rescue_model_batch_count": 1 if attempts else 0,
            "tc_big_parenthetical_row_rescue_runtime": runtime_status,
            "base_segment_count": len(base_rows),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "model_request_count": int(base_output.get("model_request_count") or 0)
            + len(attempts),
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
