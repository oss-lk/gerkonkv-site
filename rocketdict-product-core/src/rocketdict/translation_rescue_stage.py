from __future__ import annotations

"""Public Stage12 orchestration with fail-closed selective resegmentation rescue.

The maintained ``rocketdict-stage12-protected-split/8`` run remains the primary,
immutable real-OPUS translation.  This module creates a second immutable Stage12
selection run whose input identity includes the primary run/output hash.  Clean
primary contexts are copied unchanged.  Only ordinary TXT contexts that satisfy
the narrow isolated-missing-literal trigger may receive an additional raw rank-0
OPUS attempt over source-derived semicolon resegmentation.  A candidate replaces
its primary context only when the complete candidate is strict-clean under the
versioned selector and is not more alphabetically compressed.

This is not target repair: source bytes are never rewritten, targets are raw
model output, no placeholders or literal injection exist, and a rejected rescue
leaves the original failing primary output intact for Stage15 to block.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any

from .database import (
    connect,
    get_document,
    get_run,
    get_run_items,
)
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
PRIMARY_PHASE = "selective-resegmentation-primary-v8"
DEFAULT_ENABLED = True


def _bool_parameter(value: Any, *, name: str) -> bool:
    if value is None:
        return DEFAULT_ENABLED
    if isinstance(value, bool):
        return value
    raise StageExecutionError(f"Stage12 {name} must be boolean")


def _primary_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    primary = dict(parameters)
    primary["selective_resegmentation_rescue_contract"] = RESCUE_CONTRACT
    primary["selective_resegmentation_selector_contract"] = SELECTOR_CONTRACT
    primary["selective_resegmentation_phase"] = PRIMARY_PHASE
    return primary


def _context_sequence(row: dict[str, Any]) -> int | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    start = planner.get("context_sentence_start")
    end = planner.get("context_sentence_end")
    if start is None or end is None or int(start) != int(end):
        return None
    if planner.get("source") != "nlp_sentence":
        return None
    return int(start)


def _copy_primary_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["selective_resegmentation_rescue"] = {
        "contract": RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "applied": False,
        "primary_translation_segment_id": int(row["id"]),
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
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
) -> list[dict[str, Any]]:
    primary_spans = [
        [int(row["source_start"]), int(row["source_end"])] for row in primary_rows
    ]
    candidate_spans = [[int(row["start"]), int(row["end"])] for row in chunks]
    output: list[dict[str, Any]] = []
    for index, (chunk, candidates) in enumerate(zip(chunks, hypotheses, strict=True)):
        target = str(candidates[0].get("text") or "").strip()
        payload = {
            "planner": {
                "source": "nlp_sentence",
                "context_sentence_start": context_sequence,
                "context_sentence_end": context_sequence,
                "context_sentence_count": 1,
                "planner_contract": primary_stage.PLANNER_CONTRACT,
                "split": len(chunks) > 1,
                "token_count": int(chunk["token_count"]),
                "preferred_token_budget": preferred_tokens,
                "selective_resegmentation_rescue_contract": RESCUE_CONTRACT,
                "selective_resegmentation_split_mode": str(chunk["split_mode"]),
                "selective_resegmentation_backtrack_tokens": int(chunk["backtrack_tokens"]),
            },
            "hypotheses": candidates,
            "selected_rank": 0,
            "selective_resegmentation_rescue": {
                "contract": RESCUE_CONTRACT,
                "selector_contract": SELECTOR_CONTRACT,
                "applied": True,
                "context_sequence": context_sequence,
                "trigger": "isolated_missing_numeric_literal",
                "missing_literal_count": int(trigger["missing_literal_count"]),
                "primary_source_spans": primary_spans,
                "candidate_source_spans": candidate_spans,
                "candidate_chunk_index": index,
                "boundary_punctuation": BOUNDARY_PUNCTUATION,
                "maximum_backtrack_tokens": BACKTRACK_TOKENS,
                "generation": dict(generation),
                "raw_model_rank0": True,
                "candidate_verdict": dict(selection["candidate_verdicts"][index]),
                "target_alpha_primary": int(selection["target_alpha_primary"]),
                "target_alpha_candidate": int(selection["target_alpha_candidate"]),
                "source_bytes_rewritten": False,
                "target_rewriting": False,
                "placeholders": False,
                "post_translation_literal_injection": False,
            },
        }
        output.append({
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": int(chunk["start"]),
            "source_end": int(chunk["end"]),
            "source_text": str(chunk["text"]),
            "target_text": target,
            "payload": payload,
        })
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
    enabled = _bool_parameter(
        effective.get("enable_selective_resegmentation_rescue"),
        name="enable_selective_resegmentation_rescue",
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
    effective["enable_selective_resegmentation_rescue"] = enabled
    effective["selective_resegmentation_rescue_contract"] = RESCUE_CONTRACT
    effective["selective_resegmentation_selector_contract"] = SELECTOR_CONTRACT
    effective["selective_resegmentation_phase"] = SELECTED_PHASE

    # Primary Product translation remains an immutable planner-v8 Stage12 run.
    primary_output = primary_stage.run_stage12(
        database,
        context_run_id=int(context_run_id),
        parameters=_primary_parameters({
            key: value
            for key, value in effective.items()
            if key != "selective_resegmentation_phase"
        }),
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

        attempts: dict[int, dict[str, Any]] = {}
        candidate_jobs: list[tuple[int, int, dict[str, Any]]] = []
        max_candidate_tokens = 0
        if enabled and generation_supported and selected_format == "txt":
            for sequence, rows in sorted(primary_by_context.items()):
                trigger = evaluate_primary_context_trigger(rows)
                if trigger["eligible"] is not True:
                    continue
                context = context_by_sequence.get(sequence)
                if context is None:
                    raise StageExecutionError(
                        f"selective rescue lost Stage10 context {sequence}"
                    )
                start = int(context["source_start"])
                end = int(context["source_end"])
                source = str(context["source_text"])
                if content[start:end] != source:
                    raise StageExecutionError("selective rescue context differs from immutable source")
                tokens = _source_tokens(nlp_tokens, start, end)
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
                    raise StageExecutionError(f"selective rescue planning failed: {exc}") from exc
                primary_spans = [
                    (int(row["source_start"]), int(row["source_end"])) for row in rows
                ]
                candidate_spans = [
                    (int(row["start"]), int(row["end"])) for row in chunks
                ]
                if primary_spans == candidate_spans:
                    continue
                if not any(
                    str(row["split_mode"]) == "semicolon_backtrack" for row in chunks
                ):
                    continue
                attempts[sequence] = {
                    "primary_rows": rows,
                    "trigger": trigger,
                    "chunks": chunks,
                }
                for index, chunk in enumerate(chunks):
                    candidate_jobs.append((sequence, index, chunk))
                    max_candidate_tokens = max(
                        max_candidate_tokens, int(chunk["token_count"])
                    )

        generated: list[list[dict[str, Any]]] = []
        rescue_batch_count = 0
        if candidate_jobs:
            translator = OpusTranslator(device=device, compute_type=compute_type)
            generated = primary_stage._translate_primary_request_batches(
                translator,
                [str(chunk["text"]) for _sequence, _index, chunk in candidate_jobs],
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

        hypotheses_by_context: dict[int, dict[int, list[dict[str, Any]]]] = defaultdict(dict)
        for (sequence, index, _chunk), hypotheses in zip(
            candidate_jobs, generated, strict=True
        ):
            hypotheses_by_context[sequence][index] = hypotheses

        accepted: dict[int, dict[str, Any]] = {}
        rejected: dict[int, dict[str, Any]] = {}
        generation = {"beam_size": beam_size, "num_hypotheses": num_hypotheses}
        for sequence, attempt in attempts.items():
            chunks = list(attempt["chunks"])
            raw = [hypotheses_by_context[sequence][index] for index in range(len(chunks))]
            if any(not hypotheses for hypotheses in raw):
                rejected[sequence] = {"reason": "empty_hypothesis_set"}
                continue
            targets = [str(hypotheses[0].get("text") or "").strip() for hypotheses in raw]
            if any(not target for target in targets):
                rejected[sequence] = {"reason": "empty_rank0_target"}
                continue
            candidate_eval_rows = [
                {"source_text": str(chunk["text"]), "target_text": target}
                for chunk, target in zip(chunks, targets, strict=True)
            ]
            selection = evaluate_candidate_context(
                list(attempt["primary_rows"]), candidate_eval_rows
            )
            if selection["accepted"] is not True:
                rejected[sequence] = {
                    "reason": "selector_rejected",
                    "selection": selection,
                }
                continue
            accepted[sequence] = {
                "rows": _candidate_rows(
                    context_sequence=sequence,
                    chunks=chunks,
                    hypotheses=raw,
                    primary_rows=list(attempt["primary_rows"]),
                    trigger=dict(attempt["trigger"]),
                    selection=selection,
                    preferred_tokens=preferred_tokens,
                    generation=generation,
                ),
                "selection": selection,
                "trigger": attempt["trigger"],
            }

        # Replace only complete accepted ordinary contexts. Everything else is
        # copied from the immutable primary run without target/source changes.
        final_rows: list[dict[str, Any]] = []
        emitted_rescue_contexts: set[int] = set()
        for row in sorted(primary_rows, key=lambda item: int(item["source_start"])):
            sequence = _context_sequence(row)
            if sequence in accepted:
                if sequence not in emitted_rescue_contexts:
                    final_rows.extend(accepted[sequence]["rows"])
                    emitted_rescue_contexts.add(sequence)
                continue
            final_rows.append(_copy_primary_row(row))
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        primary_source_sum = sum(len(str(row.get("source_text") or "")) for row in primary_rows)
        if source_sum != primary_source_sum:
            raise StageExecutionError("selective rescue changed total source character coverage")
        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError("selective rescue final source coverage is not byte-exact")

        output = {
            **dict(primary_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "primary_translation_run_id": primary_run_id,
            "primary_translation_output_sha256": str(primary_run.get("output_sha256") or ""),
            "primary_planner_contract": primary_stage.PLANNER_CONTRACT,
            "selective_resegmentation_rescue_contract": RESCUE_CONTRACT,
            "selective_resegmentation_selector_contract": SELECTOR_CONTRACT,
            "selective_resegmentation_enabled": enabled,
            "selective_resegmentation_generation_supported": generation_supported,
            "selective_resegmentation_trigger": "isolated_missing_numeric_literal",
            "selective_resegmentation_boundary_punctuation": BOUNDARY_PUNCTUATION,
            "selective_resegmentation_maximum_backtrack_tokens": BACKTRACK_TOKENS,
            "selective_resegmentation_attempted_context_count": len(attempts),
            "selective_resegmentation_accepted_context_count": len(accepted),
            "selective_resegmentation_rejected_context_count": len(rejected),
            "selective_resegmentation_accepted_context_sequences": sorted(accepted),
            "selective_resegmentation_rejected_context_sequences": sorted(rejected),
            "selective_resegmentation_model_request_count": len(candidate_jobs),
            "selective_resegmentation_model_batch_count": rescue_batch_count,
            "primary_segment_count": int(primary_output.get("segment_count") or len(primary_rows)),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "primary_model_request_count": int(primary_output.get("model_request_count") or 0),
            "model_request_count": int(primary_output.get("model_request_count") or 0) + len(candidate_jobs),
            "max_translation_unit_tokens": max(
                int(primary_output.get("max_translation_unit_tokens") or 0),
                max_candidate_tokens,
            ),
            "source_bytes_rewritten": False,
            "target_rewriting": False,
            "placeholders": False,
            "post_translation_literal_injection": False,
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
