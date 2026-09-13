from __future__ import annotations

"""Default-off exact-row TC-big rescue for three proven numeric source shapes."""

from collections import Counter
from pathlib import Path
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .database import connect, get_document, get_run, get_run_items
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_tc_big_parenthetical_row_rescue_stage import run_stage12 as run_base_stage12
from .translation_tc_big_numeric_row_rules import (
    SELECTOR_CONTRACT,
    TRIGGER_CONTRACT,
    evaluate_tc_big_numeric_row_candidate,
    evaluate_tc_big_numeric_row_trigger,
)

TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT = "rocketdict-stage12-tc-big-numeric-row-rescue/1"
TC_BIG_NUMERIC_ROW_SELECTED_PHASE = "tc-big-numeric-row-selected-v1"
DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1024
_WRAPPER_KEYS = frozenset(
    {
        "enable_tc_big_numeric_row_rescue",
        "tc_big_numeric_row_rescue_contract",
        "tc_big_numeric_row_selector_contract",
        "tc_big_numeric_row_trigger_contract",
        "tc_big_numeric_row_rescue_phase",
    }
)
_RUNTIME_IDENTITY_KEYS = (
    "asset_manifest_sha256",
    "asset_payload_tree_sha256",
    "repository",
    "revision",
    "model_safetensors_sha256",
    "compute_type",
)


def _bool_parameter(value: Any, *, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise StageExecutionError(f"Stage12 {name} must be boolean")


def _base_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in parameters.items() if key not in _WRAPPER_KEYS}


def _runtime_identity(status: dict[str, Any] | None) -> dict[str, Any] | None:
    if status is None:
        return None
    return {key: status.get(key) for key in _RUNTIME_IDENTITY_KEYS}


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
    payload["tc_big_numeric_row_rescue"] = {
        "contract": TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "trigger_contract": TRIGGER_CONTRACT,
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
        source_exact = bool(0 <= start < end <= len(content) and content[start:end] == source)
        trigger = evaluate_tc_big_numeric_row_trigger(row, source_exact=source_exact)
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
        effective.get("enable_tc_big_numeric_row_rescue"),
        name="enable_tc_big_numeric_row_rescue",
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
        effective.get("tc_big_numeric_row_rescue_contract")
        or TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("tc_big_numeric_row_selector_contract") or SELECTOR_CONTRACT
    )
    requested_trigger = str(
        effective.get("tc_big_numeric_row_trigger_contract") or TRIGGER_CONTRACT
    )
    if requested_contract != TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big numeric-row rescue contract {requested_contract!r}"
        )
    if requested_selector != SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big numeric-row selector {requested_selector!r}"
        )
    if requested_trigger != TRIGGER_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big numeric-row trigger {requested_trigger!r}"
        )
    if effective.get("tc_big_numeric_row_rescue_phase") not in {
        None,
        TC_BIG_NUMERIC_ROW_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "tc_big_numeric_row_rescue_phase is internal and may not be overridden"
        )

    effective["enable_tc_big_numeric_row_rescue"] = True
    effective["tc_big_numeric_row_rescue_contract"] = TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT
    effective["tc_big_numeric_row_selector_contract"] = SELECTOR_CONTRACT
    effective["tc_big_numeric_row_trigger_contract"] = TRIGGER_CONTRACT
    effective["tc_big_numeric_row_rescue_phase"] = TC_BIG_NUMERIC_ROW_SELECTED_PHASE

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

    content = str(document["content_text"])
    attempts = _eligible_rows(content=content, base_rows=base_rows)
    runtime_status: dict[str, Any] | None = None
    if attempts:
        runtime_status = tc_big_status()
        if runtime_status.get("available") is not True:
            raise StageExecutionError(
                f"TC-big numeric-row rescue runtime unavailable: {runtime_status}"
            )

    input_identity = {
        "context_run_id": int(context_run_id),
        "document_version_id": document_version_id,
        "source_text_sha256": str(document["text_sha256"]),
        "base_translation_run_id": base_run_id,
        "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
        "tc_big_runtime_identity": _runtime_identity(runtime_status),
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
        generated: list[list[dict[str, Any]]] = []
        if attempts:
            translator = TcBigTranslator(device="cpu", compute_type="float32")
            model_inputs = [str(attempt["row"].get("source_text") or "") for attempt in attempts]
            generated = translator.translate(
                model_inputs,
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(
                len(hypotheses) != NUM_HYPOTHESES for hypotheses in generated
            ):
                raise StageExecutionError("TC-big numeric-row rank0 cardinality drift")

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        variant_attempts: Counter[str] = Counter()
        variant_accepts: Counter[str] = Counter()
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            row = attempt["row"]
            trigger = dict(attempt["trigger"])
            variant = str(trigger.get("variant") or "")
            variant_attempts[variant] += 1
            source = str(row.get("source_text") or "")
            hypothesis = dict(hypotheses[0])
            if int(hypothesis.get("rank", -1)) != 0:
                raise StageExecutionError("TC-big numeric-row result is not rank0")
            target = str(hypothesis.get("text") or "")
            if not target.strip():
                raise StageExecutionError("TC-big numeric-row received empty rank0 target")
            selection = evaluate_tc_big_numeric_row_candidate(
                source,
                target,
                base_target=str(row.get("target_text") or ""),
                variant=variant,
            )
            if selection["accepted"] is not True:
                rejected.append(
                    {
                        "source_start": int(row["source_start"]),
                        "variant": variant,
                        "reason": "rank0_selector_rejected",
                        "rank0_target": target,
                        "rank0_score": hypothesis.get("score"),
                        "selection": selection,
                    }
                )
                continue

            variant_accepts[variant] += 1
            payload = dict(row.get("payload") or {})
            payload["hypotheses"] = [hypothesis]
            payload["selected_rank"] = 0
            payload["tc_big_numeric_row_rescue"] = {
                "contract": TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT,
                "selector_contract": SELECTOR_CONTRACT,
                "trigger_contract": TRIGGER_CONTRACT,
                "applied": True,
                "variant": variant,
                "trigger": trigger,
                "selection": selection,
                "base_translation_run_id": base_run_id,
                "base_translation_segment_id": int(row["id"]),
                "base_target": str(row.get("target_text") or ""),
                "model": "tc-big-en-zle-ct2",
                "model_input": source,
                "model_input_equals_source": True,
                "raw_model_selected": True,
                "raw_model_rank": 0,
                "runtime_identity": _runtime_identity(runtime_status),
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
                "variant": variant,
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
            raise StageExecutionError("TC-big numeric-row final source coverage is not byte-exact")
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(len(str(row.get("source_text") or "")) for row in base_rows)
        if source_sum != base_source_sum:
            raise StageExecutionError("TC-big numeric-row changed total source coverage")

        accepted_values = sorted(accepted.values(), key=lambda value: int(value["source_start"]))
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "tc_big_numeric_row_rescue_contract": TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT,
            "tc_big_numeric_row_selector_contract": SELECTOR_CONTRACT,
            "tc_big_numeric_row_trigger_contract": TRIGGER_CONTRACT,
            "tc_big_numeric_row_rescue_enabled": True,
            "tc_big_numeric_row_rescue_attempt_count": len(attempts),
            "tc_big_numeric_row_rescue_accepted_count": len(accepted_values),
            "tc_big_numeric_row_rescue_rejected_count": len(rejected),
            "tc_big_numeric_row_rescue_variant_attempt_counts": dict(sorted(variant_attempts.items())),
            "tc_big_numeric_row_rescue_variant_accept_counts": dict(sorted(variant_accepts.items())),
            "tc_big_numeric_row_rescue_attempted_source_starts": [
                int(attempt["row"]["source_start"]) for attempt in attempts
            ],
            "tc_big_numeric_row_rescue_accepted_source_starts": [
                int(value["source_start"]) for value in accepted_values
            ],
            "tc_big_numeric_row_rescue_selected_ranks": [
                int(value["selected_rank"]) for value in accepted_values
            ],
            "tc_big_numeric_row_rescue_selected_variants": [
                str(value["variant"]) for value in accepted_values
            ],
            "tc_big_numeric_row_rescue_selected_targets": [
                str(value["target_text"]) for value in accepted_values
            ],
            "tc_big_numeric_row_rescue_rejected": rejected,
            "tc_big_numeric_row_rescue_model_request_count": len(attempts),
            "tc_big_numeric_row_rescue_model_batch_count": 1 if attempts else 0,
            "tc_big_numeric_row_rescue_runtime": runtime_status,
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
