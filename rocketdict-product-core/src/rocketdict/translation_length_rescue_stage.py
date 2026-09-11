from __future__ import annotations

"""Opt-in Stage12 whole-context rescue for proven primary length failures.

This module is deliberately separate from the existing numeric-triggered
whole-context rescue contract.  It reuses the current public Stage12 output as
an immutable base, then considers only ordinary TXT Stage10 contexts that the
maintained planner split into multiple rows and where at least one base row
already fails the maintained length-ratio gate.

The candidate request is the unchanged whole Stage10 source context, bounded to
160 non-space NLP tokens, translated once with the pinned real OPUS backend at
beam=6/rank0.  A candidate may replace the complete split context only when the
existing strict rescue evaluator passes.  Alphabetic non-decrease is recorded
but is intentionally not an acceptance rule for this contract because the
primary row is independently proven malformed by the maintained length gate.

This remains research opt-in.  No source rewriting, placeholders, target repair
or post-translation literal insertion is performed.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import evaluate_rescue_pair
from .translation_rescue_stage import (
    MAX_WHOLE_CONTEXT_NLP_TOKENS,
    _context_sequence,
    _rows_cover_context,
    _source_tokens,
    _whole_context_chunk,
    run_stage12 as run_base_stage12,
)
from . import translation_stage as primary_stage


LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT = (
    "rocketdict-stage12-length-failure-whole-context-rescue/1"
)
LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT = (
    "rocketdict-stage12-length-failure-whole-context-selector/1"
)
LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE = (
    "length-failure-whole-context-selected-v1"
)
DEFAULT_ENABLED = False
_LENGTH_ONLY_KEYS = frozenset(
    {
        "enable_length_failure_whole_context_rescue",
        "length_failure_whole_context_rescue_contract",
        "length_failure_whole_context_rescue_selector_contract",
        "length_failure_whole_context_rescue_phase",
        "length_failure_whole_context_rescue_max_nlp_tokens",
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
    """Strip only this wrapper's controls from the current public Stage12 identity."""
    return {key: value for key, value in parameters.items() if key not in _LENGTH_ONLY_KEYS}


def _alpha_count(text: str) -> int:
    return sum(character.isalpha() for character in text)


def evaluate_length_failure_trigger(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        if verdict.get("length_passed") is not True:
            failures.append(
                {
                    "translation_segment_id": int(row.get("id") or 0),
                    "source_start": int(row["source_start"]),
                    "source_end": int(row["source_end"]),
                    "length_ratio": verdict.get("length_ratio"),
                    "verdict": verdict,
                }
            )
    return {
        "contract": "rocketdict-stage12-primary-length-failure-trigger/1",
        "eligible": bool(failures),
        "failure_count": len(failures),
        "failures": failures,
    }


def evaluate_length_failure_candidate(
    primary_rows: list[dict[str, Any]], *, source: str, target: str
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    primary_target = "".join(str(row.get("target_text") or "") for row in primary_rows)
    alpha_primary = _alpha_count(primary_target)
    alpha_candidate = _alpha_count(target)
    return {
        "selector_contract": LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
        "accepted": verdict.get("strictly_eligible") is True,
        "strict_clean": verdict.get("strictly_eligible") is True,
        "candidate_verdict": verdict,
        "target_alpha_primary": alpha_primary,
        "target_alpha_candidate": alpha_candidate,
        "target_alpha_delta": alpha_candidate - alpha_primary,
        "target_alpha_non_decreasing": alpha_candidate >= alpha_primary,
        "target_alpha_non_decreasing_required": False,
    }


def _safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["length_failure_whole_context_rescue"] = {
        "contract": LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
        "selector_contract": LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
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


def _candidate_row(
    *,
    context_sequence: int,
    chunk: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    trigger: dict[str, Any],
    selection: dict[str, Any],
    preferred_tokens: int,
    max_nlp_tokens: int,
    generation: dict[str, int],
) -> dict[str, Any]:
    if not hypotheses:
        raise ValueError("length-failure whole-context rescue requires a hypothesis")
    target = str(hypotheses[0].get("text") or "")
    primary_spans = [
        [int(row["source_start"]), int(row["source_end"])] for row in primary_rows
    ]
    payload = {
        "planner": {
            "source": "nlp_sentence",
            "context_sentence_start": context_sequence,
            "context_sentence_end": context_sequence,
            "context_sentence_count": 1,
            "planner_contract": primary_stage.PLANNER_CONTRACT,
            "split": False,
            "token_count": int(chunk["token_count"]),
            "preferred_token_budget": preferred_tokens,
            "rescue_strategy": "length_failure_whole_context",
            "length_failure_whole_context_rescue_contract": (
                LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
            ),
            "length_failure_whole_context_split_mode": "whole_context",
        },
        "hypotheses": hypotheses,
        "selected_rank": 0,
        "length_failure_whole_context_rescue": {
            "contract": LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
            "selector_contract": LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
            "applied": True,
            "context_sequence": context_sequence,
            "trigger": "primary_length_ratio_failure",
            "primary_length_failure_count": int(trigger["failure_count"]),
            "primary_length_failures": list(trigger["failures"]),
            "primary_source_spans": primary_spans,
            "candidate_source_span": [int(chunk["start"]), int(chunk["end"])],
            "maximum_nlp_tokens": max_nlp_tokens,
            "generation": dict(generation),
            "raw_model_rank0": True,
            "candidate_verdict": dict(selection["candidate_verdict"]),
            "target_alpha_primary": int(selection["target_alpha_primary"]),
            "target_alpha_candidate": int(selection["target_alpha_candidate"]),
            "target_alpha_delta": int(selection["target_alpha_delta"]),
            "target_alpha_non_decreasing": bool(
                selection["target_alpha_non_decreasing"]
            ),
            "target_alpha_non_decreasing_required": False,
            **_safety_flags(),
        },
    }
    return {
        "sequence_number": 0,
        "kind": "translation_segment",
        "source_start": int(chunk["start"]),
        "source_end": int(chunk["end"]),
        "source_text": str(chunk["text"]),
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
        effective.get("enable_length_failure_whole_context_rescue"),
        name="enable_length_failure_whole_context_rescue",
        default=DEFAULT_ENABLED,
    )
    if not enabled:
        return run_base_stage12(
            database,
            context_run_id=int(context_run_id),
            parameters=_base_parameters(effective),
            implementation=implementation,
        )

    if _bool_parameter(
        effective.get("enable_selective_resegmentation_rescue"),
        name="enable_selective_resegmentation_rescue",
        default=False,
    ) or _bool_parameter(
        effective.get("enable_whole_context_rescue"),
        name="enable_whole_context_rescue",
        default=False,
    ):
        raise StageExecutionError(
            "length-failure whole-context rescue may not be combined with other "
            "Stage12 research rescue strategies in the same run"
        )

    requested_contract = str(
        effective.get("length_failure_whole_context_rescue_contract")
        or LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("length_failure_whole_context_rescue_selector_contract")
        or LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
    )
    max_nlp_tokens = _positive_int_parameter(
        effective.get("length_failure_whole_context_rescue_max_nlp_tokens"),
        name="length_failure_whole_context_rescue_max_nlp_tokens",
        default=MAX_WHOLE_CONTEXT_NLP_TOKENS,
    )
    if requested_contract != LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported length-failure whole-context rescue contract {requested_contract!r}"
        )
    if requested_selector != LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported length-failure whole-context selector {requested_selector!r}"
        )
    if effective.get("length_failure_whole_context_rescue_phase") not in {
        None,
        LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "length_failure_whole_context_rescue_phase is internal and may not be overridden"
        )
    if max_nlp_tokens > MAX_WHOLE_CONTEXT_NLP_TOKENS:
        raise StageExecutionError(
            "length_failure_whole_context_rescue_max_nlp_tokens may not exceed "
            f"the mechanically proven cap {MAX_WHOLE_CONTEXT_NLP_TOKENS}"
        )

    effective["enable_length_failure_whole_context_rescue"] = True
    effective["length_failure_whole_context_rescue_contract"] = (
        LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
    )
    effective["length_failure_whole_context_rescue_selector_contract"] = (
        LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
    )
    effective["length_failure_whole_context_rescue_phase"] = (
        LENGTH_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE
    )
    effective["length_failure_whole_context_rescue_max_nlp_tokens"] = max_nlp_tokens

    base_parameters = _base_parameters(effective)
    base_output = run_base_stage12(
        database,
        context_run_id=int(context_run_id),
        parameters=base_parameters,
        implementation=implementation,
    )
    base_run_id = int(base_output["translation_run_id"])

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, base_run_id)
        base_rows = get_run_items(connection, base_run_id, kind="translation_segment")
        context_run = get_run(connection, int(context_run_id))
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        context_items = get_run_items(connection, int(context_run_id), kind="context_sentence")
        document_version_id = int(context_output["document_version_id"])
        document = get_document(connection, document_version_id)

    input_identity = {
        "context_run_id": int(context_run_id),
        "context_output_sha256": str(context_run.get("output_sha256") or ""),
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
        selected_format = str(document["selected_format"])
        beam_size = int(effective.get("beam_size") or 6)
        num_hypotheses = int(effective.get("num_hypotheses") or 1)
        preferred_tokens = int(effective.get("plan_preferred_unit_tokens") or 64)
        request_batch_size = int(
            effective.get("request_batch_size", primary_stage.DEFAULT_REQUEST_BATCH_SIZE)
        )
        device = str(effective.get("device") or "cpu")
        compute_type = str(effective.get("compute_type") or "float32")
        generation_supported = beam_size == 6 and num_hypotheses == 1

        rows_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in base_rows:
            sequence = _context_sequence(row)
            if sequence is not None:
                rows_by_context[sequence].append(row)
        for rows in rows_by_context.values():
            rows.sort(key=lambda item: int(item["source_start"]))
        context_by_sequence = {
            int(row["sequence_number"]): row for row in context_items
        }

        attempts: dict[int, dict[str, Any]] = {}
        skipped_over_cap: list[int] = []
        maximum_candidate_tokens = 0
        if enabled and generation_supported and selected_format == "txt":
            for sequence, rows in sorted(rows_by_context.items()):
                if len(rows) < 2:
                    continue
                context = context_by_sequence.get(sequence)
                if context is None:
                    raise StageExecutionError(
                        f"Stage12 length-failure rescue lost Stage10 context {sequence}"
                    )
                start = int(context["source_start"])
                end = int(context["source_end"])
                source = str(context["source_text"])
                if content[start:end] != source:
                    raise StageExecutionError(
                        "Stage12 length-failure rescue context differs from immutable source"
                    )
                if not _rows_cover_context(rows, start=start, end=end, source=source):
                    continue
                trigger = evaluate_length_failure_trigger(rows)
                if trigger["eligible"] is not True:
                    continue
                token_count = len(_source_tokens(nlp_tokens, start, end))
                if token_count <= 0:
                    raise StageExecutionError(
                        f"Stage12 length-failure rescue context {sequence} has no NLP tokens"
                    )
                if token_count > max_nlp_tokens:
                    skipped_over_cap.append(sequence)
                    continue
                chunk = _whole_context_chunk(
                    source=source,
                    start=start,
                    end=end,
                    token_count=token_count,
                )
                attempts[sequence] = {
                    "rows": rows,
                    "trigger": trigger,
                    "chunk": chunk,
                }
                maximum_candidate_tokens = max(maximum_candidate_tokens, token_count)

        generated: list[list[dict[str, Any]]] = []
        if attempts:
            translator = OpusTranslator(device=device, compute_type=compute_type)
            generated = primary_stage._translate_primary_request_batches(
                translator,
                [str(attempts[sequence]["chunk"]["text"]) for sequence in sorted(attempts)],
                batch_size=request_batch_size,
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=max(
                    128, max(preferred_tokens, maximum_candidate_tokens) * 8
                ),
            )

        accepted: dict[int, dict[str, Any]] = {}
        rejected: dict[int, dict[str, Any]] = {}
        generation = {"beam_size": beam_size, "num_hypotheses": num_hypotheses}
        for sequence, hypotheses in zip(sorted(attempts), generated, strict=True):
            attempt = attempts[sequence]
            if not hypotheses:
                rejected[sequence] = {"reason": "empty_hypothesis_set"}
                continue
            target = str(hypotheses[0].get("text") or "")
            if not target.strip():
                rejected[sequence] = {"reason": "empty_rank0_target"}
                continue
            selection = evaluate_length_failure_candidate(
                list(attempt["rows"]),
                source=str(attempt["chunk"]["text"]),
                target=target,
            )
            if selection["accepted"] is not True:
                rejected[sequence] = {
                    "reason": "selector_rejected",
                    "selection": selection,
                }
                continue
            accepted[sequence] = {
                "row": _candidate_row(
                    context_sequence=sequence,
                    chunk=dict(attempt["chunk"]),
                    hypotheses=hypotheses,
                    primary_rows=list(attempt["rows"]),
                    trigger=dict(attempt["trigger"]),
                    selection=selection,
                    preferred_tokens=preferred_tokens,
                    max_nlp_tokens=max_nlp_tokens,
                    generation=generation,
                ),
                "selection": selection,
            }

        final_rows: list[dict[str, Any]] = []
        emitted: set[int] = set()
        for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
            sequence = _context_sequence(row)
            if sequence in accepted:
                if sequence not in emitted:
                    final_rows.append(accepted[sequence]["row"])
                    emitted.add(sequence)
                continue
            final_rows.append(_copy_base_row(row))
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError(
                "Stage12 length-failure rescue final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(len(str(row.get("source_text") or "")) for row in base_rows)
        if source_sum != base_source_sum:
            raise StageExecutionError(
                "Stage12 length-failure rescue changed total source character coverage"
            )

        attempted_sequences = sorted(attempts)
        accepted_sequences = sorted(accepted)
        rejected_sequences = sorted(rejected)
        alpha_relaxed_sequences = sorted(
            sequence
            for sequence, value in accepted.items()
            if value["selection"]["target_alpha_non_decreasing"] is False
        )
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "length_failure_whole_context_rescue_contract": (
                LENGTH_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
            ),
            "length_failure_whole_context_rescue_selector_contract": (
                LENGTH_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
            ),
            "length_failure_whole_context_rescue_enabled": True,
            "length_failure_whole_context_rescue_generation_supported": generation_supported,
            "length_failure_whole_context_rescue_trigger": "primary_length_ratio_failure",
            "length_failure_whole_context_rescue_max_nlp_tokens": max_nlp_tokens,
            "length_failure_whole_context_rescue_attempted_context_count": len(
                attempted_sequences
            ),
            "length_failure_whole_context_rescue_accepted_context_count": len(
                accepted_sequences
            ),
            "length_failure_whole_context_rescue_rejected_context_count": len(
                rejected_sequences
            ),
            "length_failure_whole_context_rescue_skipped_over_cap_context_count": len(
                skipped_over_cap
            ),
            "length_failure_whole_context_rescue_attempted_context_sequences": attempted_sequences,
            "length_failure_whole_context_rescue_accepted_context_sequences": accepted_sequences,
            "length_failure_whole_context_rescue_rejected_context_sequences": rejected_sequences,
            "length_failure_whole_context_rescue_skipped_over_cap_context_sequences": sorted(
                skipped_over_cap
            ),
            "length_failure_whole_context_rescue_alpha_relaxed_context_sequences": alpha_relaxed_sequences,
            "length_failure_whole_context_rescue_model_request_count": len(attempted_sequences),
            "length_failure_whole_context_rescue_model_batch_count": (
                (len(attempted_sequences) + request_batch_size - 1) // request_batch_size
                if attempted_sequences
                else 0
            ),
            "base_segment_count": len(base_rows),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "model_request_count": int(base_output.get("model_request_count") or 0)
            + len(attempted_sequences),
            "max_translation_unit_tokens": max(
                int(base_output.get("max_translation_unit_tokens") or 0),
                maximum_candidate_tokens,
            ),
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
