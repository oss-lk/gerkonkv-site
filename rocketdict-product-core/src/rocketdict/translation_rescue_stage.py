from __future__ import annotations

"""Public Stage12 orchestration with fail-closed source-derived rescue strategies.

The maintained ``rocketdict-stage12-protected-split/8`` run remains the primary,
immutable real-OPUS translation.  This module creates a second immutable Stage12
selection run whose input identity includes the primary run/output hash.  Clean
primary contexts are copied unchanged.  Only ordinary TXT contexts that satisfy
the narrow isolated-missing-literal trigger may receive additional raw rank-0
OPUS attempts over source-derived alternatives.

Two research strategies are represented independently:

* selective semicolon resegmentation (legacy research path); and
* unchanged whole-Stage10-context translation for bounded long units.

A candidate replaces its primary context only when the complete candidate is
strict-clean under the versioned selector and is not more alphabetically
compressed.  Whole-context rescue is capped at 160 NLP tokens, matching the
full-Opticks feasibility experiment that recovered the known long-unit omission
without admitting the formula-heavy counterexample.

This is not target repair: source bytes are never rewritten, targets are raw
model output, no placeholders or literal injection exist, and a rejected rescue
leaves the original failing primary output intact for Stage15 to block.  Both
strategies remain research opt-in until corpus evidence and semantic review
justify Product promotion.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import (
    BACKTRACK_TOKENS,
    BOUNDARY_PUNCTUATION,
    RESCUE_CONTRACT,
    SELECTOR_CONTRACT,
    build_selective_resegmentation_chunks,
    evaluate_candidate_context,
    evaluate_primary_context_trigger,
)
from . import translation_stage as primary_stage


SELECTED_PHASE = "selective-resegmentation-selected-v1"
WHOLE_CONTEXT_SELECTED_PHASE = "whole-context-selected-v1"
WHOLE_CONTEXT_RESCUE_CONTRACT = "rocketdict-stage12-whole-context-rescue/1"
MAX_WHOLE_CONTEXT_NLP_TOKENS = 160
DEFAULT_ENABLED = False
DEFAULT_WHOLE_CONTEXT_ENABLED = False
_RESCUE_ONLY_PARAMETER_KEYS = frozenset(
    {
        "enable_selective_resegmentation_rescue",
        "selective_resegmentation_rescue_contract",
        "selective_resegmentation_selector_contract",
        "selective_resegmentation_phase",
        "enable_whole_context_rescue",
        "whole_context_rescue_contract",
        "whole_context_rescue_selector_contract",
        "whole_context_rescue_phase",
        "whole_context_rescue_max_nlp_tokens",
    }
)


def _bool_parameter(value: Any, *, name: str, default: bool = DEFAULT_ENABLED) -> bool:
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


def _primary_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Return only parameters that can affect the immutable primary Stage12 run."""
    return {
        key: value
        for key, value in parameters.items()
        if key not in _RESCUE_ONLY_PARAMETER_KEYS
    }


def _context_sequence(row: dict[str, Any]) -> int | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    start = planner.get("context_sentence_start")
    end = planner.get("context_sentence_end")
    if start is None or end is None or int(start) != int(end):
        return None
    if planner.get("source") != "nlp_sentence":
        return None
    return int(start)


def _rescue_safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }


def _copy_primary_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["selective_resegmentation_rescue"] = {
        "contract": RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "applied": False,
        "primary_translation_segment_id": int(row["id"]),
        **_rescue_safety_flags(),
    }
    payload["whole_context_rescue"] = {
        "contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "applied": False,
        "primary_translation_segment_id": int(row["id"]),
        **_rescue_safety_flags(),
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


def _source_tokens(
    nlp_tokens: list[dict[str, Any]], start: int, end: int
) -> list[dict[str, Any]]:
    return [
        token
        for token in nlp_tokens
        if int(token["source_start"]) >= start
        and int(token["source_end"]) <= end
        and not bool((token.get("payload") or {}).get("flags", {}).get("is_space"))
    ]


def _rows_cover_context(
    rows: list[dict[str, Any]], *, start: int, end: int, source: str
) -> bool:
    """Return True only when ordinary primary rows are the whole immutable context."""
    if not rows or end <= start or len(source) != end - start:
        return False
    cursor = start
    for row in sorted(rows, key=lambda item: int(item["source_start"])):
        row_start = int(row["source_start"])
        row_end = int(row["source_end"])
        row_source = str(row.get("source_text") or "")
        if row_start != cursor or row_end <= row_start or row_end > end:
            return False
        if source[row_start - start : row_end - start] != row_source:
            return False
        cursor = row_end
    return cursor == end


def _whole_context_chunk(
    *, source: str, start: int, end: int, token_count: int
) -> dict[str, Any]:
    if end <= start or len(source) != end - start:
        raise ValueError("whole-context rescue source bounds are invalid")
    if token_count <= 0:
        raise ValueError("whole-context rescue requires positive NLP token count")
    return {
        "start": start,
        "end": end,
        "text": source,
        "token_count": token_count,
        "split_mode": "whole_context",
        "backtrack_tokens": 0,
    }


def _candidate_rows(
    *,
    context_sequence: int,
    chunks: list[dict[str, Any]],
    hypotheses: list[list[dict[str, Any]]],
    primary_rows: list[dict[str, Any]],
    trigger: dict[str, Any],
    selection: dict[str, Any],
    preferred_tokens: int,
    generation: dict[str, int],
    strategy: str = "selective_resegmentation",
) -> list[dict[str, Any]]:
    if strategy not in {"selective_resegmentation", "whole_context"}:
        raise ValueError(f"unknown Stage12 rescue strategy: {strategy}")
    primary_spans = [
        [int(row["source_start"]), int(row["source_end"])] for row in primary_rows
    ]
    candidate_spans = [[int(row["start"]), int(row["end"])] for row in chunks]
    output: list[dict[str, Any]] = []
    for index, (chunk, candidates) in enumerate(zip(chunks, hypotheses, strict=True)):
        target = str(candidates[0].get("text") or "")
        planner = {
            "source": "nlp_sentence",
            "context_sentence_start": context_sequence,
            "context_sentence_end": context_sequence,
            "context_sentence_count": 1,
            "planner_contract": primary_stage.PLANNER_CONTRACT,
            "split": len(chunks) > 1,
            "token_count": int(chunk["token_count"]),
            "preferred_token_budget": preferred_tokens,
            "rescue_strategy": strategy,
        }
        common = {
            "selector_contract": SELECTOR_CONTRACT,
            "applied": True,
            "context_sequence": context_sequence,
            "trigger": "isolated_missing_numeric_literal",
            "missing_literal_count": int(trigger["missing_literal_count"]),
            "primary_source_spans": primary_spans,
            "candidate_source_spans": candidate_spans,
            "candidate_chunk_index": index,
            "generation": dict(generation),
            "raw_model_rank0": True,
            "candidate_verdict": dict(selection["candidate_verdicts"][index]),
            "target_alpha_primary": int(selection["target_alpha_primary"]),
            "target_alpha_candidate": int(selection["target_alpha_candidate"]),
            **_rescue_safety_flags(),
        }
        if strategy == "selective_resegmentation":
            planner.update(
                {
                    "selective_resegmentation_rescue_contract": RESCUE_CONTRACT,
                    "selective_resegmentation_split_mode": str(chunk["split_mode"]),
                    "selective_resegmentation_backtrack_tokens": int(chunk["backtrack_tokens"]),
                }
            )
            selective = {
                "contract": RESCUE_CONTRACT,
                "boundary_punctuation": BOUNDARY_PUNCTUATION,
                "maximum_backtrack_tokens": BACKTRACK_TOKENS,
                **common,
            }
            whole = {
                "contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
                "selector_contract": SELECTOR_CONTRACT,
                "applied": False,
                **_rescue_safety_flags(),
            }
        else:
            planner.update(
                {
                    "whole_context_rescue_contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
                    "whole_context_split_mode": "whole_context",
                }
            )
            selective = {
                "contract": RESCUE_CONTRACT,
                "selector_contract": SELECTOR_CONTRACT,
                "applied": False,
                **_rescue_safety_flags(),
            }
            whole = {
                "contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
                "maximum_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
                **common,
            }
        payload = {
            "planner": planner,
            "hypotheses": candidates,
            "selected_rank": 0,
            "selective_resegmentation_rescue": selective,
            "whole_context_rescue": whole,
        }
        output.append(
            {
                "sequence_number": 0,
                "kind": "translation_segment",
                "source_start": int(chunk["start"]),
                "source_end": int(chunk["end"]),
                "source_text": str(chunk["text"]),
                "target_text": target,
                "payload": payload,
            }
        )
    return output


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

    selective_enabled = _bool_parameter(
        effective.get("enable_selective_resegmentation_rescue"),
        name="enable_selective_resegmentation_rescue",
        default=DEFAULT_ENABLED,
    )
    requested_contract = str(
        effective.get("selective_resegmentation_rescue_contract") or RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("selective_resegmentation_selector_contract") or SELECTOR_CONTRACT
    )
    if requested_contract != RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported selective rescue contract {requested_contract!r}; expected {RESCUE_CONTRACT!r}"
        )
    if requested_selector != SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported selective rescue selector {requested_selector!r}; expected {SELECTOR_CONTRACT!r}"
        )
    if effective.get("selective_resegmentation_phase") not in {None, SELECTED_PHASE}:
        raise StageExecutionError("selective_resegmentation_phase is internal and may not be overridden")

    whole_enabled = _bool_parameter(
        effective.get("enable_whole_context_rescue"),
        name="enable_whole_context_rescue",
        default=DEFAULT_WHOLE_CONTEXT_ENABLED,
    )
    requested_whole_contract = str(
        effective.get("whole_context_rescue_contract") or WHOLE_CONTEXT_RESCUE_CONTRACT
    )
    requested_whole_selector = str(
        effective.get("whole_context_rescue_selector_contract") or SELECTOR_CONTRACT
    )
    whole_cap = _positive_int_parameter(
        effective.get("whole_context_rescue_max_nlp_tokens"),
        name="whole_context_rescue_max_nlp_tokens",
        default=MAX_WHOLE_CONTEXT_NLP_TOKENS,
    )
    if requested_whole_contract != WHOLE_CONTEXT_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported whole-context rescue contract {requested_whole_contract!r}; "
            f"expected {WHOLE_CONTEXT_RESCUE_CONTRACT!r}"
        )
    if requested_whole_selector != SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported whole-context rescue selector {requested_whole_selector!r}; "
            f"expected {SELECTOR_CONTRACT!r}"
        )
    if effective.get("whole_context_rescue_phase") not in {None, WHOLE_CONTEXT_SELECTED_PHASE}:
        raise StageExecutionError("whole_context_rescue_phase is internal and may not be overridden")
    if whole_cap > MAX_WHOLE_CONTEXT_NLP_TOKENS:
        raise StageExecutionError(
            "whole_context_rescue_max_nlp_tokens may not exceed the mechanically proven cap "
            f"{MAX_WHOLE_CONTEXT_NLP_TOKENS}"
        )

    effective["enable_selective_resegmentation_rescue"] = selective_enabled
    effective["selective_resegmentation_rescue_contract"] = RESCUE_CONTRACT
    effective["selective_resegmentation_selector_contract"] = SELECTOR_CONTRACT
    effective["selective_resegmentation_phase"] = SELECTED_PHASE
    effective["enable_whole_context_rescue"] = whole_enabled
    effective["whole_context_rescue_contract"] = WHOLE_CONTEXT_RESCUE_CONTRACT
    effective["whole_context_rescue_selector_contract"] = SELECTOR_CONTRACT
    effective["whole_context_rescue_phase"] = WHOLE_CONTEXT_SELECTED_PHASE
    effective["whole_context_rescue_max_nlp_tokens"] = whole_cap

    # Primary Product translation remains the cache-reusable immutable planner-v8
    # Stage12 run. Selection/rescue controls belong only to the wrapper run.
    primary_output = primary_stage.run_stage12(
        database,
        context_run_id=int(context_run_id),
        parameters=_primary_parameters(effective),
        implementation=implementation,
    )
    primary_run_id = int(primary_output["translation_run_id"])

    with connect(database, readonly=True) as connection:
        primary_run = get_run(connection, primary_run_id)
        primary_rows = get_run_items(connection, primary_run_id, kind="translation_segment")
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
        "primary_translation_run_id": primary_run_id,
        "primary_translation_output_sha256": str(primary_run.get("output_sha256") or ""),
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
        preferred_tokens = int(effective.get("plan_preferred_unit_tokens") or 64)
        beam_size = int(effective.get("beam_size") or 6)
        num_hypotheses = int(effective.get("num_hypotheses") or 1)
        request_batch_size = int(
            effective.get("request_batch_size", primary_stage.DEFAULT_REQUEST_BATCH_SIZE)
        )
        device = str(effective.get("device") or "cpu")
        compute_type = str(effective.get("compute_type") or "float32")
        generation_supported = beam_size == 6 and num_hypotheses == 1

        primary_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in primary_rows:
            sequence = _context_sequence(row)
            if sequence is not None:
                primary_by_context[sequence].append(row)
        for rows in primary_by_context.values():
            rows.sort(key=lambda row: int(row["source_start"]))
        context_by_sequence = {
            int(row["sequence_number"]): row for row in context_items
        }

        attempts: dict[tuple[str, int], dict[str, Any]] = {}
        candidate_jobs: list[tuple[str, int, int, dict[str, Any]]] = []
        whole_skipped_over_cap: list[int] = []
        max_candidate_tokens = 0
        if (
            (selective_enabled or whole_enabled)
            and generation_supported
            and selected_format == "txt"
        ):
            for sequence, rows in sorted(primary_by_context.items()):
                context = context_by_sequence.get(sequence)
                if context is None:
                    raise StageExecutionError(f"Stage12 rescue lost Stage10 context {sequence}")
                start = int(context["source_start"])
                end = int(context["source_end"])
                source = str(context["source_text"])
                if content[start:end] != source:
                    raise StageExecutionError("Stage12 rescue context differs from immutable source")
                if not _rows_cover_context(rows, start=start, end=end, source=source):
                    continue
                trigger = evaluate_primary_context_trigger(rows)
                if trigger["eligible"] is not True:
                    continue
                tokens = _source_tokens(nlp_tokens, start, end)
                token_count = len(tokens)
                if token_count <= 0:
                    raise StageExecutionError(
                        f"Stage12 rescue context {sequence} has no source NLP tokens"
                    )

                # Whole-context fallback is meaningful only when planner-v8 split
                # this source context.  The unchanged Stage10 source is the model
                # request; no alternate segmentation or target repair is used.
                if whole_enabled and len(rows) >= 2:
                    if token_count <= whole_cap:
                        whole_chunk = _whole_context_chunk(
                            source=source,
                            start=start,
                            end=end,
                            token_count=token_count,
                        )
                        attempts[("whole_context", sequence)] = {
                            "primary_rows": rows,
                            "trigger": trigger,
                            "chunks": [whole_chunk],
                        }
                        candidate_jobs.append(
                            ("whole_context", sequence, 0, whole_chunk)
                        )
                        max_candidate_tokens = max(max_candidate_tokens, token_count)
                    else:
                        whole_skipped_over_cap.append(sequence)

                if selective_enabled:
                    spans = primary_stage._balanced_protected_spans(
                        source, absolute_start=start
                    )
                    try:
                        chunks = build_selective_resegmentation_chunks(
                            content,
                            start=start,
                            end=end,
                            tokens=tokens,
                            spans=spans,
                            preferred_tokens=preferred_tokens,
                        )
                    except ValueError as exc:
                        raise StageExecutionError(
                            f"selective rescue planning failed: {exc}"
                        ) from exc
                    primary_spans = [
                        (int(row["source_start"]), int(row["source_end"]))
                        for row in rows
                    ]
                    candidate_spans = [
                        (int(row["start"]), int(row["end"])) for row in chunks
                    ]
                    if primary_spans == candidate_spans:
                        continue
                    if not any(
                        str(row["split_mode"]) == "semicolon_backtrack"
                        for row in chunks
                    ):
                        continue
                    attempts[("selective_resegmentation", sequence)] = {
                        "primary_rows": rows,
                        "trigger": trigger,
                        "chunks": chunks,
                    }
                    for index, chunk in enumerate(chunks):
                        candidate_jobs.append(
                            ("selective_resegmentation", sequence, index, chunk)
                        )
                        max_candidate_tokens = max(
                            max_candidate_tokens, int(chunk["token_count"])
                        )

        generated: list[list[dict[str, Any]]] = []
        rescue_batch_count = 0
        if candidate_jobs:
            translator = OpusTranslator(device=device, compute_type=compute_type)
            generated = primary_stage._translate_primary_request_batches(
                translator,
                [str(chunk["text"]) for _strategy, _sequence, _index, chunk in candidate_jobs],
                batch_size=request_batch_size,
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=max(
                    128, max(preferred_tokens, max_candidate_tokens) * 8
                ),
            )
            rescue_batch_count = (
                len(candidate_jobs) + request_batch_size - 1
            ) // request_batch_size

        hypotheses_by_attempt: dict[
            tuple[str, int], dict[int, list[dict[str, Any]]]
        ] = defaultdict(dict)
        for (strategy, sequence, index, _chunk), hypotheses in zip(
            candidate_jobs, generated, strict=True
        ):
            hypotheses_by_attempt[(strategy, sequence)][index] = hypotheses

        accepted_by_attempt: dict[tuple[str, int], dict[str, Any]] = {}
        rejected_by_attempt: dict[tuple[str, int], dict[str, Any]] = {}
        generation = {"beam_size": beam_size, "num_hypotheses": num_hypotheses}
        for key, attempt in attempts.items():
            strategy, sequence = key
            chunks = list(attempt["chunks"])
            raw = [
                hypotheses_by_attempt[key][index] for index in range(len(chunks))
            ]
            if any(not hypotheses for hypotheses in raw):
                rejected_by_attempt[key] = {"reason": "empty_hypothesis_set"}
                continue
            targets = [str(hypotheses[0].get("text") or "") for hypotheses in raw]
            if any(not target.strip() for target in targets):
                rejected_by_attempt[key] = {"reason": "empty_rank0_target"}
                continue
            candidate_eval_rows = [
                {"source_text": str(chunk["text"]), "target_text": target}
                for chunk, target in zip(chunks, targets, strict=True)
            ]
            selection = evaluate_candidate_context(
                list(attempt["primary_rows"]), candidate_eval_rows
            )
            if selection["accepted"] is not True:
                rejected_by_attempt[key] = {
                    "reason": "selector_rejected",
                    "selection": selection,
                }
                continue
            accepted_by_attempt[key] = {
                "rows": _candidate_rows(
                    context_sequence=sequence,
                    chunks=chunks,
                    hypotheses=raw,
                    primary_rows=list(attempt["primary_rows"]),
                    trigger=dict(attempt["trigger"]),
                    selection=selection,
                    preferred_tokens=preferred_tokens,
                    generation=generation,
                    strategy=strategy,
                ),
                "selection": selection,
                "trigger": attempt["trigger"],
                "strategy": strategy,
            }

        # Strategy precedence is deliberate: a strict-clean unchanged whole
        # Stage10 context is closer to the original source ownership than a new
        # segmentation.  Legacy selective resegmentation remains a fallback only
        # when explicitly enabled and whole-context did not pass.
        selected: dict[int, dict[str, Any]] = {}
        eligible_sequences = sorted(
            {sequence for _strategy, sequence in attempts}
        )
        for sequence in eligible_sequences:
            for strategy in ("whole_context", "selective_resegmentation"):
                candidate = accepted_by_attempt.get((strategy, sequence))
                if candidate is not None:
                    selected[sequence] = candidate
                    break

        # Replace only complete accepted ordinary contexts. Everything else is
        # copied from the immutable primary run without target/source changes.
        final_rows: list[dict[str, Any]] = []
        emitted_rescue_contexts: set[int] = set()
        for row in sorted(primary_rows, key=lambda item: int(item["source_start"])):
            sequence = _context_sequence(row)
            if sequence in selected:
                if sequence not in emitted_rescue_contexts:
                    final_rows.extend(selected[sequence]["rows"])
                    emitted_rescue_contexts.add(sequence)
                continue
            final_rows.append(_copy_primary_row(row))
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        primary_source_sum = sum(
            len(str(row.get("source_text") or "")) for row in primary_rows
        )
        if source_sum != primary_source_sum:
            raise StageExecutionError("Stage12 rescue changed total source character coverage")
        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError("Stage12 rescue final source coverage is not byte-exact")

        selective_attempted = sorted(
            sequence
            for strategy, sequence in attempts
            if strategy == "selective_resegmentation"
        )
        selective_accepted = sorted(
            sequence
            for (strategy, sequence) in accepted_by_attempt
            if strategy == "selective_resegmentation"
        )
        selective_rejected = sorted(
            sequence
            for (strategy, sequence) in rejected_by_attempt
            if strategy == "selective_resegmentation"
        )
        selective_requests = sum(
            1 for strategy, _sequence, _index, _chunk in candidate_jobs
            if strategy == "selective_resegmentation"
        )

        whole_attempted = sorted(
            sequence for strategy, sequence in attempts if strategy == "whole_context"
        )
        whole_accepted = sorted(
            sequence
            for (strategy, sequence) in accepted_by_attempt
            if strategy == "whole_context"
        )
        whole_rejected = sorted(
            sequence
            for (strategy, sequence) in rejected_by_attempt
            if strategy == "whole_context"
        )
        whole_requests = sum(
            1 for strategy, _sequence, _index, _chunk in candidate_jobs
            if strategy == "whole_context"
        )
        selected_strategy_by_context = {
            str(sequence): str(value["strategy"])
            for sequence, value in sorted(selected.items())
        }

        output = {
            **dict(primary_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "primary_translation_run_id": primary_run_id,
            "primary_translation_output_sha256": str(primary_run.get("output_sha256") or ""),
            "primary_planner_contract": primary_stage.PLANNER_CONTRACT,
            "selective_resegmentation_rescue_contract": RESCUE_CONTRACT,
            "selective_resegmentation_selector_contract": SELECTOR_CONTRACT,
            "selective_resegmentation_enabled": selective_enabled,
            "selective_resegmentation_generation_supported": generation_supported,
            "selective_resegmentation_trigger": "isolated_missing_numeric_literal",
            "selective_resegmentation_boundary_punctuation": BOUNDARY_PUNCTUATION,
            "selective_resegmentation_maximum_backtrack_tokens": BACKTRACK_TOKENS,
            "selective_resegmentation_attempted_context_count": len(selective_attempted),
            "selective_resegmentation_accepted_context_count": len(selective_accepted),
            "selective_resegmentation_rejected_context_count": len(selective_rejected),
            "selective_resegmentation_accepted_context_sequences": selective_accepted,
            "selective_resegmentation_rejected_context_sequences": selective_rejected,
            "selective_resegmentation_model_request_count": selective_requests,
            "selective_resegmentation_model_batch_count": (
                (selective_requests + request_batch_size - 1) // request_batch_size
                if selective_requests else 0
            ),
            "whole_context_rescue_contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
            "whole_context_rescue_selector_contract": SELECTOR_CONTRACT,
            "whole_context_rescue_enabled": whole_enabled,
            "whole_context_rescue_generation_supported": generation_supported,
            "whole_context_rescue_trigger": "isolated_missing_numeric_literal",
            "whole_context_rescue_max_nlp_tokens": whole_cap,
            "whole_context_rescue_attempted_context_count": len(whole_attempted),
            "whole_context_rescue_accepted_context_count": len(whole_accepted),
            "whole_context_rescue_rejected_context_count": len(whole_rejected),
            "whole_context_rescue_skipped_over_cap_context_count": len(whole_skipped_over_cap),
            "whole_context_rescue_attempted_context_sequences": whole_attempted,
            "whole_context_rescue_accepted_context_sequences": whole_accepted,
            "whole_context_rescue_rejected_context_sequences": whole_rejected,
            "whole_context_rescue_skipped_over_cap_context_sequences": sorted(whole_skipped_over_cap),
            "whole_context_rescue_model_request_count": whole_requests,
            "whole_context_rescue_model_batch_count": (
                (whole_requests + request_batch_size - 1) // request_batch_size
                if whole_requests else 0
            ),
            "rescue_selected_context_count": len(selected),
            "rescue_selected_strategy_by_context": selected_strategy_by_context,
            "rescue_model_request_count": len(candidate_jobs),
            "rescue_model_batch_count": rescue_batch_count,
            "primary_segment_count": int(
                primary_output.get("segment_count") or len(primary_rows)
            ),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "primary_model_request_count": int(primary_output.get("model_request_count") or 0),
            "model_request_count": int(primary_output.get("model_request_count") or 0)
            + len(candidate_jobs),
            "max_translation_unit_tokens": max(
                int(primary_output.get("max_translation_unit_tokens") or 0),
                max_candidate_tokens,
            ),
            **_rescue_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
