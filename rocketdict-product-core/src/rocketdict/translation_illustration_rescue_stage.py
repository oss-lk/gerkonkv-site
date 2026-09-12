from __future__ import annotations

"""Opt-in Stage12 rescue for standalone Gutenberg illustration labels.

Only already-hard-failing rows beginning an exact standalone ``[Illustration:
...]`` line plus blank separator are considered. The prefix remains byte-exact
source-owned structure. The linguistic remainder still uses pinned real OPUS.
Every linguistic remainder is sent to MT exactly as it appears in the immutable
source. Exact ``_Illustration._`` remains a semantically constrained source class,
but it receives no canonicalization and only its unique raw rank0 may be persisted.
Disabled by default; no source/model-input or target rewriting, placeholders, or
post-translation literal injection.
"""

from pathlib import Path
import re
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_numeric_hard_rescue_stage import run_stage12 as run_base_stage12
from .translation_rescue import evaluate_rescue_pair
from .translation_rank0 import select_rank0_evaluation
from . import translation_stage as primary_stage

ILLUSTRATION_LABEL_RESCUE_CONTRACT = "rocketdict-stage12-illustration-label-rescue/3"
ILLUSTRATION_LABEL_SELECTOR_CONTRACT = "rocketdict-stage12-illustration-label-selector/3"
ILLUSTRATION_WORD_TARGET_FORM_CONTRACT = "rocketdict-stage12-illustration-word-target-form/1"
ILLUSTRATION_LABEL_SELECTED_PHASE = "illustration-label-selected-v3"
ILLUSTRATION_LABEL_TRIGGER_CONTRACT = "rocketdict-stage12-illustration-label-hard-failure-trigger/1"
DEFAULT_ENABLED = False
ILLUSTRATION_WORD_SOURCE = "_Illustration._"
ILLUSTRATION_WORD_MODEL_INPUT = ILLUSTRATION_WORD_SOURCE
ILLUSTRATION_WORD_ACCEPTED_TERMS = ("иллюстрация", "рисунок")
STRUCTURAL_WORD_BEAM_SIZE = 6
STRUCTURAL_WORD_NUM_HYPOTHESES = 6
ORDINARY_SUFFIX_BEAM_SIZE = 6
ORDINARY_SUFFIX_NUM_HYPOTHESES = 1
_PREFIX_RE = re.compile(r"\A(?P<label>\[Illustration:[^\]\r\n]+\])(?P<gap>\r?\n[ \t]*\r?\n)")
_ILLUSTRATION_ONLY_KEYS = frozenset({
    "enable_illustration_label_rescue",
    "illustration_label_rescue_contract",
    "illustration_label_rescue_selector_contract",
    "illustration_word_target_form_contract",
    "illustration_label_rescue_phase",
})


def _bool_parameter(value: Any, *, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise StageExecutionError(f"Stage12 {name} must be boolean")


def _base_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in parameters.items() if key not in _ILLUSTRATION_ONLY_KEYS}


def _split_prefix(source: str) -> tuple[str, str] | None:
    match = _PREFIX_RE.match(source)
    if match is None:
        return None
    structural = match.group("label") + match.group("gap")
    remainder = source[match.end():]
    if not remainder.strip():
        return None
    return structural, remainder


def _model_input_for_remainder(remainder: str) -> tuple[str, bool, str]:
    candidate_kind = (
        "standalone_illustration_word"
        if remainder.strip() == ILLUSTRATION_WORD_SOURCE
        else "ordinary_linguistic_suffix"
    )
    return remainder, False, candidate_kind


def evaluate_illustration_word_target_shape(target: str) -> dict[str, Any]:
    stripped = target.strip()
    canonical = stripped.rstrip(".").strip().casefold()
    no_markup_artifacts = not any(char in stripped for char in "_*[]{}")
    exact_structural_term = canonical in ILLUSTRATION_WORD_ACCEPTED_TERMS
    return {
        "contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "target_text": target,
        "canonical_target": canonical,
        "accepted_terms": list(ILLUSTRATION_WORD_ACCEPTED_TERMS),
        "no_markup_artifacts": no_markup_artifacts,
        "exact_structural_term": exact_structural_term,
        "passed": no_markup_artifacts and exact_structural_term,
    }


def evaluate_illustration_label_trigger(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    split = _split_prefix(source)
    base_verdict = evaluate_rescue_pair(source, target)
    hard_failure = base_verdict.get("product_hard_passed") is not True
    return {
        "contract": ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
        "eligible": split is not None and hard_failure,
        "standalone_illustration_prefix": split is not None,
        "already_product_hard_failing": hard_failure,
        "structural_source": None if split is None else split[0],
        "remainder_source": None if split is None else split[1],
        "base_verdict": base_verdict,
    }


def evaluate_illustration_label_candidate(
    row: dict[str, Any], *, structural_source: str, remainder_source: str,
    target: str, normalized_model_input: bool,
) -> dict[str, Any]:
    base_verdict = evaluate_rescue_pair(
        str(row.get("source_text") or ""), str(row.get("target_text") or "")
    )
    structural_verdict = evaluate_rescue_pair(structural_source, structural_source)
    remainder_verdict = evaluate_rescue_pair(remainder_source, target)
    if normalized_model_input:
        raise ValueError("illustration-label rescue forbids normalized model input")
    standalone_word = remainder_source.strip() == ILLUSTRATION_WORD_SOURCE
    target_shape = (
        evaluate_illustration_word_target_shape(target)
        if standalone_word
        else {"contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT, "applicable": False, "passed": True}
    )
    accepted = (
        base_verdict.get("product_hard_passed") is not True
        and structural_verdict.get("strictly_eligible") is True
        and remainder_verdict.get("strictly_eligible") is True
        and target_shape.get("passed") is True
    )
    return {
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "accepted": accepted,
        "base_product_hard_failure": base_verdict.get("product_hard_passed") is not True,
        "base_verdict": base_verdict,
        "structural_verdict": structural_verdict,
        "remainder_verdict": remainder_verdict,
        "illustration_word_target_shape": target_shape,
    }


def _safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "automatic_n_best_cherry_picking": False,
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["illustration_label_rescue"] = {
        "contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
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


def _candidate_rows(
    *, base: dict[str, Any], structural_source: str, remainder_source: str,
    model_input: str, normalized_model_input: bool, candidate_kind: str,
    hypotheses: list[dict[str, Any]], selected_rank: int,
    trigger: dict[str, Any], selection: dict[str, Any], generation: dict[str, int],
) -> list[dict[str, Any]]:
    if selected_rank != 0:
        raise ValueError("illustration-label rescue is rank0-only")
    if normalized_model_input:
        raise ValueError("illustration-label rescue forbids normalized model input")
    if model_input != remainder_source:
        raise ValueError("illustration-label rescue model input must equal source remainder")
    if selected_rank < 0 or selected_rank >= len(hypotheses):
        raise ValueError("illustration-label rescue selected rank is outside hypotheses")
    target = str(hypotheses[selected_rank].get("text") or "")
    start = int(base["source_start"])
    boundary = start + len(structural_source)
    end = int(base["source_end"])
    if boundary >= end or boundary + len(remainder_source) != end:
        raise ValueError("illustration-label rescue source bounds drift")
    base_planner = dict((base.get("payload") or {}).get("planner") or {})
    common = {
        "contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "applied": True,
        "trigger": "standalone_illustration_label_existing_hard_failure",
        "base_translation_segment_id": int(base["id"]),
        "base_source_span": [start, end],
        "split_source_boundary": boundary,
        "candidate_kind": candidate_kind,
        "model_input": model_input,
        "source_model_input_normalized": False,
        "model_input_source_exact": True,
        "generation": dict(generation),
        "selected_rank": selected_rank,
        "selected_target": target,
        "trigger_evidence": trigger,
        "selection": selection,
        "raw_model_selected": True,
        **_safety_flags(),
    }
    structural_payload = {
        "planner": {
            **base_planner,
            "source": "source_owned_illustration_label",
            "planner_contract": primary_stage.PLANNER_CONTRACT,
            "split": True,
            "rescue_strategy": "illustration_label_source_owned_prefix",
            "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        },
        "illustration_label_rescue": {
            **common,
            "role": "source_owned_prefix",
            "source_owned_passthrough": True,
            "raw_model_selected": False,
        },
    }
    remainder_payload = {
        "planner": {
            **base_planner,
            "source": "illustration_label_linguistic_remainder",
            "planner_contract": primary_stage.PLANNER_CONTRACT,
            "split": True,
            "rescue_strategy": "illustration_label_linguistic_remainder",
            "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        },
        "hypotheses": hypotheses,
        "selected_rank": selected_rank,
        "illustration_label_rescue": {
            **common,
            "role": "linguistic_remainder",
            "source_owned_passthrough": False,
        },
    }
    return [
        {
            "sequence_number": 0, "kind": "translation_segment",
            "source_start": start, "source_end": boundary,
            "source_text": structural_source, "target_text": structural_source,
            "payload": structural_payload,
        },
        {
            "sequence_number": 0, "kind": "translation_segment",
            "source_start": boundary, "source_end": end,
            "source_text": remainder_source, "target_text": target,
            "payload": remainder_payload,
        },
    ]


def run_stage12(
    database: Path | str, *, context_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "opus-en-ru-ct2",
) -> dict[str, Any]:
    if implementation != "opus-en-ru-ct2":
        raise StageExecutionError(f"Unsupported real MT implementation: {implementation}")
    database = Path(database).expanduser().resolve()
    effective = dict(parameters or {})
    enabled = _bool_parameter(
        effective.get("enable_illustration_label_rescue"),
        name="enable_illustration_label_rescue", default=DEFAULT_ENABLED,
    )
    if not enabled:
        return run_base_stage12(
            database, context_run_id=int(context_run_id),
            parameters=_base_parameters(effective), implementation=implementation,
        )
    if _bool_parameter(
        effective.get("enable_selective_resegmentation_rescue"),
        name="enable_selective_resegmentation_rescue", default=False,
    ) or _bool_parameter(
        effective.get("enable_whole_context_rescue"),
        name="enable_whole_context_rescue", default=False,
    ):
        raise StageExecutionError(
            "illustration-label rescue may not be combined with legacy Stage12 selective/whole-context research rescues"
        )

    requested_contract = str(effective.get("illustration_label_rescue_contract") or ILLUSTRATION_LABEL_RESCUE_CONTRACT)
    requested_selector = str(effective.get("illustration_label_rescue_selector_contract") or ILLUSTRATION_LABEL_SELECTOR_CONTRACT)
    requested_target_form = str(effective.get("illustration_word_target_form_contract") or ILLUSTRATION_WORD_TARGET_FORM_CONTRACT)
    if requested_contract != ILLUSTRATION_LABEL_RESCUE_CONTRACT:
        raise StageExecutionError(f"Unsupported illustration-label rescue contract {requested_contract!r}")
    if requested_selector != ILLUSTRATION_LABEL_SELECTOR_CONTRACT:
        raise StageExecutionError(f"Unsupported illustration-label selector {requested_selector!r}")
    if requested_target_form != ILLUSTRATION_WORD_TARGET_FORM_CONTRACT:
        raise StageExecutionError(f"Unsupported illustration-word target form {requested_target_form!r}")
    if effective.get("illustration_label_rescue_phase") not in {None, ILLUSTRATION_LABEL_SELECTED_PHASE}:
        raise StageExecutionError("illustration_label_rescue_phase is internal and may not be overridden")

    effective["enable_illustration_label_rescue"] = True
    effective["illustration_label_rescue_contract"] = ILLUSTRATION_LABEL_RESCUE_CONTRACT
    effective["illustration_label_rescue_selector_contract"] = ILLUSTRATION_LABEL_SELECTOR_CONTRACT
    effective["illustration_word_target_form_contract"] = ILLUSTRATION_WORD_TARGET_FORM_CONTRACT
    effective["illustration_label_rescue_phase"] = ILLUSTRATION_LABEL_SELECTED_PHASE

    base_output = run_base_stage12(
        database, context_run_id=int(context_run_id),
        parameters=_base_parameters(effective), implementation=implementation,
    )
    base_run_id = int(base_output["translation_run_id"])
    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, base_run_id)
        base_rows = get_run_items(connection, base_run_id, kind="translation_segment")
        base_run_output = dict(base_run.get("output") or {})
        document_version_id = int(base_run_output["document_version_id"])
        document = get_document(connection, document_version_id)

    input_identity = {
        "context_run_id": int(context_run_id),
        "document_version_id": document_version_id,
        "source_text_sha256": str(document["text_sha256"]),
        "base_translation_run_id": base_run_id,
        "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
    }
    run_id, cached = _start(
        database, stage_number=12, implementation=implementation,
        input_identity=input_identity, parameters=effective,
    )
    if cached is not None:
        return cached

    try:
        content = str(document["content_text"])
        selected_format = str(document["selected_format"])
        beam_size = int(effective.get("beam_size") or 6)
        num_hypotheses = int(effective.get("num_hypotheses") or 1)
        request_batch_size = int(effective.get("request_batch_size", primary_stage.DEFAULT_REQUEST_BATCH_SIZE))
        device = str(effective.get("device") or "cpu")
        compute_type = str(effective.get("compute_type") or "float32")
        generation_supported = beam_size == 6 and num_hypotheses == 1

        attempts: list[dict[str, Any]] = []
        if generation_supported and selected_format == "txt":
            for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
                trigger = evaluate_illustration_label_trigger(row)
                if trigger["eligible"] is not True:
                    continue
                structural = str(trigger["structural_source"])
                remainder = str(trigger["remainder_source"])
                model_input, normalized, candidate_kind = _model_input_for_remainder(remainder)
                attempts.append({
                    "row": row, "trigger": trigger, "structural": structural,
                    "remainder": remainder, "model_input": model_input,
                    "normalized_model_input": normalized, "candidate_kind": candidate_kind,
                })

        normalized_attempts = [x for x in attempts if bool(x["normalized_model_input"])]
        if normalized_attempts:
            raise StageExecutionError("Stage12 illustration-label exact-source contract forbids normalized model input")
        ordinary_attempts = list(attempts)
        generated_by_id: dict[int, list[dict[str, Any]]] = {}
        structural_batch_count = 0
        ordinary_batch_count = 0
        if attempts:
            translator = OpusTranslator(device=device, compute_type=compute_type)
            if ordinary_attempts:
                generated = primary_stage._translate_primary_request_batches(
                    translator, [str(x["model_input"]) for x in ordinary_attempts],
                    batch_size=request_batch_size, beam_size=ORDINARY_SUFFIX_BEAM_SIZE,
                    num_hypotheses=ORDINARY_SUFFIX_NUM_HYPOTHESES, max_decoding_length=128,
                )
                if len(generated) != len(ordinary_attempts) or any(len(h) != ORDINARY_SUFFIX_NUM_HYPOTHESES for h in generated):
                    raise StageExecutionError("Stage12 illustration-label ordinary-suffix hypothesis cardinality drift")
                for attempt, hypotheses in zip(ordinary_attempts, generated, strict=True):
                    generated_by_id[int(attempt["row"]["id"])] = hypotheses
                ordinary_batch_count = (len(ordinary_attempts) + request_batch_size - 1) // request_batch_size

        accepted: dict[int, dict[str, Any]] = {}
        rejected: dict[int, dict[str, Any]] = {}
        for attempt in attempts:
            row = attempt["row"]
            row_id = int(row["id"])
            hypotheses = generated_by_id.get(row_id) or []
            if not hypotheses:
                rejected[row_id] = {"reason": "empty_hypothesis_set"}
                continue
            selected_rank: int | None = None
            selected_selection: dict[str, Any] | None = None
            evaluated: list[dict[str, Any]] = []
            for index, hypothesis in enumerate(hypotheses):
                rank = int(hypothesis.get("rank", index))
                target = str(hypothesis.get("text") or "")
                if not target.strip():
                    evaluated.append({"rank": rank, "target_text": target, "score": hypothesis.get("score"), "accepted": False, "reason": "empty_target"})
                    continue
                selection = evaluate_illustration_label_candidate(
                    row, structural_source=str(attempt["structural"]),
                    remainder_source=str(attempt["remainder"]), target=target,
                    normalized_model_input=bool(attempt["normalized_model_input"]),
                )
                evaluated.append({"rank": rank, "target_text": target, "score": hypothesis.get("score"), "accepted": selection["accepted"], "selection": selection})
                if selected_rank is None and selection["accepted"] is True:
                    selected_rank = rank
                    selected_selection = selection
            rank0_choice = select_rank0_evaluation(evaluated)
            if rank0_choice is None:
                selected_rank = None
                selected_selection = None
            else:
                selected_rank = 0
                selected_selection = dict(rank0_choice["selection"])
            if selected_rank is None or selected_selection is None:
                rejected[row_id] = {"reason": "selector_rejected", "evaluated_hypotheses": evaluated}
                continue
            generation = {
                "beam_size": STRUCTURAL_WORD_BEAM_SIZE if bool(attempt["normalized_model_input"]) else ORDINARY_SUFFIX_BEAM_SIZE,
                "num_hypotheses": len(hypotheses),
            }
            accepted[row_id] = {
                "rows": _candidate_rows(
                    base=row, structural_source=str(attempt["structural"]),
                    remainder_source=str(attempt["remainder"]), model_input=str(attempt["model_input"]),
                    normalized_model_input=bool(attempt["normalized_model_input"]),
                    candidate_kind=str(attempt["candidate_kind"]), hypotheses=hypotheses,
                    selected_rank=selected_rank, trigger=dict(attempt["trigger"]),
                    selection=selected_selection, generation=generation,
                ),
                "selected_rank": selected_rank,
                "selected_target": str(hypotheses[selected_rank].get("text") or ""),
                "source_start": int(row["source_start"]),
                "normalized_model_input": bool(attempt["normalized_model_input"]),
                "evaluated_hypotheses": evaluated,
            }

        final_rows: list[dict[str, Any]] = []
        for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
            replacement = accepted.get(int(row["id"]))
            if replacement is None:
                final_rows.append(_copy_base_row(row))
            else:
                final_rows.extend(replacement["rows"])
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError("Stage12 illustration-label rescue final source coverage is not byte-exact")
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(len(str(row.get("source_text") or "")) for row in base_rows)
        if source_sum != base_source_sum:
            raise StageExecutionError("Stage12 illustration-label rescue changed total source character coverage")

        accepted_values = sorted(accepted.values(), key=lambda value: int(value["source_start"]))
        attempted_starts = sorted(int(x["row"]["source_start"]) for x in attempts)
        accepted_starts = [int(value["source_start"]) for value in accepted_values]
        rejected_starts = sorted(int(x["row"]["source_start"]) for x in attempts if int(x["row"]["id"]) in rejected)
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
            "illustration_label_rescue_selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
            "illustration_word_target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
            "illustration_label_rescue_enabled": True,
            "illustration_label_rescue_generation_supported": generation_supported,
            "illustration_label_rescue_trigger": "standalone_illustration_label_existing_hard_failure",
            "illustration_label_rescue_attempt_count": len(attempts),
            "illustration_label_rescue_accepted_count": len(accepted),
            "illustration_label_rescue_rejected_count": len(rejected),
            "illustration_label_rescue_attempted_source_starts": attempted_starts,
            "illustration_label_rescue_accepted_source_starts": accepted_starts,
            "illustration_label_rescue_rejected_source_starts": rejected_starts,
            "illustration_label_rescue_selected_ranks": [int(value["selected_rank"]) for value in accepted_values],
            "illustration_label_rescue_selected_targets": [str(value["selected_target"]) for value in accepted_values],
            "illustration_label_rescue_normalized_model_input_source_starts": [],
            "illustration_label_rescue_model_inputs_source_exact": True,
            "illustration_label_rescue_structural_word_beam_size": STRUCTURAL_WORD_BEAM_SIZE,
            "illustration_label_rescue_structural_word_num_hypotheses": STRUCTURAL_WORD_NUM_HYPOTHESES,
            "illustration_label_rescue_ordinary_suffix_beam_size": ORDINARY_SUFFIX_BEAM_SIZE,
            "illustration_label_rescue_ordinary_suffix_num_hypotheses": ORDINARY_SUFFIX_NUM_HYPOTHESES,
            "illustration_label_rescue_model_request_count": len(attempts),
            "illustration_label_rescue_model_batch_count": structural_batch_count + ordinary_batch_count,
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
