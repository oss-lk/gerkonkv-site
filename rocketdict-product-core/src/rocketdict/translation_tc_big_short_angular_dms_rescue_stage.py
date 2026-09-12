from __future__ import annotations

"""Default-off TC-big rescue for short standalone DMS angle statements.

The immutable source must contain exactly one ``D deg. M'. S''`` expression,
contain the word ``Angle``, and remain a short statement (<=12 alphabetic
words).  Only the unmodified raw rank-0 TC-big hypothesis is selection-
authorized.  Higher beam hypotheses remain diagnostic evidence only and can
never alter the persisted target.
"""

from pathlib import Path
import re
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import evaluate_rescue_pair
from .translation_tc_big_angular_minute_rescue_stage import run_stage12 as run_base_stage12

TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT = "rocketdict-stage12-tc-big-short-angular-dms-rescue/2"
TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT = "rocketdict-stage12-tc-big-short-angular-dms-selector/2"
TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT = "rocketdict-stage12-tc-big-short-angular-dms-trigger/1"
TC_BIG_SHORT_ANGULAR_DMS_SELECTED_PHASE = "tc-big-short-angular-dms-selected-v2"
DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 512
MAX_SOURCE_ALPHA_WORDS = 12
MIN_SOURCE_ALPHA_RATIO = 0.70
MAX_SOURCE_ALPHA_RATIO = 1.50

_SOURCE_DMS_RE = re.compile(
    r"\b(?P<degrees>\d+)\s+deg\.\s+(?P<minutes>\d+)'\.\s+(?P<seconds>\d+)''",
    re.IGNORECASE,
)
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_WRAPPER_KEYS = frozenset(
    {
        "enable_tc_big_short_angular_dms_rescue",
        "tc_big_short_angular_dms_rescue_contract",
        "tc_big_short_angular_dms_selector_contract",
        "tc_big_short_angular_dms_trigger_contract",
        "tc_big_short_angular_dms_rescue_phase",
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


def _planner_context_key(row: dict[str, Any]) -> tuple[int, int] | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
    except (KeyError, TypeError, ValueError):
        return None
    if first < 0 or last < first:
        return None
    return first, last


def _source_dms(source: str) -> dict[str, str] | None:
    matches = list(_SOURCE_DMS_RE.finditer(source))
    if len(matches) != 1:
        return None
    match = matches[0]
    return {
        "degrees": match.group("degrees"),
        "minutes": match.group("minutes"),
        "seconds": match.group("seconds"),
    }


def _alpha_word_count(source: str) -> int:
    return len(_ALPHA_WORD_RE.findall(source))


def _target_dms_anchor(target: str, dms: dict[str, str]) -> bool:
    if "угол" not in target.casefold():
        return False
    pattern = re.compile(
        rf"(?<!\d){re.escape(dms['degrees'])}\s+град[^0-9]{{0,8}}"
        rf"{re.escape(dms['minutes'])}'[^0-9]{{0,8}}{re.escape(dms['seconds'])}''",
        re.IGNORECASE,
    )
    return pattern.search(target) is not None


def _prime_verdict(verdict: dict[str, Any]) -> dict[str, Any]:
    return dict(
        ((verdict.get("numeric_symbol") or {}).get("numeric") or {}).get(
            "prime_notation"
        )
        or {}
    )


def evaluate_tc_big_short_angular_dms_trigger(
    row: dict[str, Any], *, exact_stage10_context: bool
) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    dms = _source_dms(source)
    alpha_words = _alpha_word_count(source)
    contains_angle_word = re.search(r"\bAngle\b", source, re.IGNORECASE) is not None
    verdict = evaluate_rescue_pair(source, target)
    prime = _prime_verdict(verdict)
    source_signature = list(prime.get("source_signature") or [])
    expected_signature = (
        []
        if dms is None
        else [
            {"value": dms["minutes"], "prime_count": 1},
            {"value": dms["seconds"], "prime_count": 2},
        ]
    )
    exact_prime_shape = source_signature == expected_signature
    eligible = bool(
        exact_stage10_context
        and dms is not None
        and contains_angle_word
        and alpha_words <= MAX_SOURCE_ALPHA_WORDS
        and exact_prime_shape
        and verdict.get("product_hard_passed") is not True
        and prime.get("passed") is not True
    )
    return {
        "contract": TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
        "eligible": eligible,
        "exact_stage10_single_row_context": bool(exact_stage10_context),
        "contains_current_product_hard_failure": verdict.get("product_hard_passed")
        is not True,
        "source_dms": dms,
        "source_alpha_word_count": alpha_words,
        "source_alpha_word_cap": MAX_SOURCE_ALPHA_WORDS,
        "source_contains_angle_word": contains_angle_word,
        "source_exact_dms_prime_shape": exact_prime_shape,
        "current_prime_notation_passed": prime.get("passed") is True,
        "base_verdict": verdict,
    }


def evaluate_tc_big_short_angular_dms_candidate(
    source: str, target: str
) -> dict[str, Any]:
    dms = _source_dms(source)
    verdict = evaluate_rescue_pair(source, target)
    prime = _prime_verdict(verdict)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _source_alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    semantic_dms_preserved = bool(dms is not None and _target_dms_anchor(target, dms))
    accepted = bool(
        dms is not None
        and verdict.get("strictly_eligible") is True
        and prime.get("passed") is True
        and emphasis.get("passed") is True
        and ratio_passed
        and semantic_dms_preserved
    )
    return {
        "selector_contract": TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "mechanical_verdict": verdict,
        "prime_notation": prime,
        "emphasis_markup": emphasis,
        "source_dms": dms,
        "semantic_dms_preserved": semantic_dms_preserved,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
    }


def _evaluate_rank0_hypotheses(
    source: str, hypotheses: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str | None, dict[str, Any] | None]:
    """Retain all raw beams as evidence while authorizing rank0 only."""
    evaluated: list[dict[str, Any]] = []
    rank0_target: str | None = None
    rank0_selection: dict[str, Any] | None = None
    rank0_count = 0
    for hypothesis in hypotheses:
        rank = int(hypothesis["rank"])
        target = str(hypothesis.get("text") or "")
        selection = evaluate_tc_big_short_angular_dms_candidate(source, target)
        evaluated.append(
            {
                "rank": rank,
                "target_text": target,
                "score": hypothesis.get("score"),
                "accepted": selection["accepted"],
                "selection": selection,
                "selection_authorized": rank == 0,
            }
        )
        if rank == 0:
            rank0_count += 1
            rank0_target = target
            rank0_selection = selection
    if rank0_count != 1 or rank0_target is None or rank0_selection is None:
        raise StageExecutionError(
            f"TC-big short-angular-DMS rank-0 cardinality drift: {rank0_count}"
        )
    if rank0_selection["accepted"] is not True:
        return evaluated, None, None
    return evaluated, rank0_target, rank0_selection


def _safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "automatic_n_best_cherry_picking": False,
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["tc_big_short_angular_dms_rescue"] = {
        "contract": TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
        "selector_contract": TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
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


def _eligible_rows(
    *,
    content: str,
    base_rows: list[dict[str, Any]],
    context_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_sequence = {int(row["sequence_number"]): row for row in context_rows}
    attempts: list[dict[str, Any]] = []
    for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
        source = str(row.get("source_text") or "")
        if _source_dms(source) is None or _alpha_word_count(source) > MAX_SOURCE_ALPHA_WORDS:
            continue
        key = _planner_context_key(row)
        exact_context = False
        if key is not None:
            first, last = key
            try:
                source_rows = [by_sequence[index] for index in range(first, last + 1)]
            except KeyError:
                source_rows = []
            if source_rows:
                context_source = "".join(
                    str(item.get("source_text") or "") for item in source_rows
                )
                start = int(source_rows[0]["source_start"])
                end = int(source_rows[-1]["source_end"])
                if context_source != content[start:end]:
                    raise StageExecutionError(
                        f"TC-big short-angular-DMS Stage10 source coverage drift for {first}:{last}"
                    )
                exact_context = bool(
                    start == int(row["source_start"])
                    and end == int(row["source_end"])
                    and context_source == source
                )
        trigger = evaluate_tc_big_short_angular_dms_trigger(
            row, exact_stage10_context=exact_context
        )
        if trigger["eligible"] is True:
            attempts.append({"row": row, "trigger": trigger, "context_key": key})
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
        effective.get("enable_tc_big_short_angular_dms_rescue"),
        name="enable_tc_big_short_angular_dms_rescue",
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
        effective.get("tc_big_short_angular_dms_rescue_contract")
        or TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("tc_big_short_angular_dms_selector_contract")
        or TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT
    )
    requested_trigger = str(
        effective.get("tc_big_short_angular_dms_trigger_contract")
        or TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT
    )
    if requested_contract != TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT:
        raise StageExecutionError("Unsupported TC-big short-angular-DMS rescue contract")
    if requested_selector != TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT:
        raise StageExecutionError("Unsupported TC-big short-angular-DMS selector")
    if requested_trigger != TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT:
        raise StageExecutionError("Unsupported TC-big short-angular-DMS trigger")
    if effective.get("tc_big_short_angular_dms_rescue_phase") not in {
        None,
        TC_BIG_SHORT_ANGULAR_DMS_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "tc_big_short_angular_dms_rescue_phase is internal and may not be overridden"
        )

    effective.update(
        {
            "enable_tc_big_short_angular_dms_rescue": True,
            "tc_big_short_angular_dms_rescue_contract": TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
            "tc_big_short_angular_dms_selector_contract": TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
            "tc_big_short_angular_dms_trigger_contract": TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
            "tc_big_short_angular_dms_rescue_phase": TC_BIG_SHORT_ANGULAR_DMS_SELECTED_PHASE,
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
        base_rows = get_run_items(
            connection, base_run_id, kind="translation_segment"
        )
        context_rows = get_run_items(
            connection, int(context_run_id), kind="context_sentence"
        )
        stored_output = dict(base_run.get("output") or {})
        document = get_document(connection, int(stored_output["document_version_id"]))

    input_identity = {
        "context_run_id": int(context_run_id),
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
        attempts = _eligible_rows(
            content=content, base_rows=base_rows, context_rows=context_rows
        )
        generated: list[list[dict[str, Any]]] = []
        runtime_status: dict[str, Any] | None = None
        if attempts:
            runtime_status = tc_big_status()
            if runtime_status.get("available") is not True:
                raise StageExecutionError(
                    f"TC-big short-angular-DMS runtime unavailable: {runtime_status}"
                )
            translator = TcBigTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(
                [str(attempt["row"]["source_text"]) for attempt in attempts],
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(
                len(hypotheses) != NUM_HYPOTHESES for hypotheses in generated
            ):
                raise StageExecutionError(
                    "TC-big short-angular-DMS n-best cardinality drift"
                )

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            row = attempt["row"]
            evaluated, selected_target, selected_selection = _evaluate_rank0_hypotheses(
                str(row["source_text"]), hypotheses
            )
            if selected_target is None or selected_selection is None:
                rejected.append(
                    {
                        "source_start": int(row["source_start"]),
                        "reason": "rank0_selector_rejected",
                        "evaluated_hypotheses": evaluated,
                    }
                )
                continue

            payload = dict(row.get("payload") or {})
            payload["hypotheses"] = hypotheses
            payload["selected_rank"] = 0
            payload["tc_big_short_angular_dms_rescue"] = {
                "contract": TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
                "selector_contract": TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
                "trigger_contract": TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
                "applied": True,
                "trigger": dict(attempt["trigger"]),
                "selection": selected_selection,
                "base_translation_run_id": base_run_id,
                "base_translation_segment_id": int(row["id"]),
                "raw_model_selected": True,
                "raw_model_selected_rank": 0,
                "generation": {
                    "beam_size": BEAM_SIZE,
                    "num_hypotheses": NUM_HYPOTHESES,
                    "max_decoding_length": MAX_DECODING_LENGTH,
                    "selection_authorized_ranks": [0],
                },
                **_safety_flags(),
            }
            accepted[int(row["id"])] = {
                "source_start": int(row["source_start"]),
                "target_text": selected_target,
                "selected_rank": 0,
                "payload": payload,
            }

        final_rows: list[dict[str, Any]] = []
        for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
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
                "TC-big short-angular-DMS final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        if source_sum != sum(
            len(str(row.get("source_text") or "")) for row in base_rows
        ):
            raise StageExecutionError(
                "TC-big short-angular-DMS changed total source coverage"
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
            "tc_big_short_angular_dms_rescue_contract": TC_BIG_SHORT_ANGULAR_DMS_RESCUE_CONTRACT,
            "tc_big_short_angular_dms_selector_contract": TC_BIG_SHORT_ANGULAR_DMS_SELECTOR_CONTRACT,
            "tc_big_short_angular_dms_trigger_contract": TC_BIG_SHORT_ANGULAR_DMS_TRIGGER_CONTRACT,
            "tc_big_short_angular_dms_rescue_enabled": True,
            "tc_big_short_angular_dms_rescue_attempt_count": len(attempts),
            "tc_big_short_angular_dms_rescue_accepted_count": len(accepted_values),
            "tc_big_short_angular_dms_rescue_rejected_count": len(rejected),
            "tc_big_short_angular_dms_rescue_attempted_source_starts": [
                int(attempt["row"]["source_start"]) for attempt in attempts
            ],
            "tc_big_short_angular_dms_rescue_accepted_source_starts": [
                int(value["source_start"]) for value in accepted_values
            ],
            "tc_big_short_angular_dms_rescue_selected_ranks": [
                int(value["selected_rank"]) for value in accepted_values
            ],
            "tc_big_short_angular_dms_rescue_selected_targets": [
                str(value["target_text"]) for value in accepted_values
            ],
            "tc_big_short_angular_dms_rescue_model_request_count": len(attempts),
            "tc_big_short_angular_dms_rescue_model_batch_count": 1 if attempts else 0,
            "tc_big_short_angular_dms_rescue_runtime": runtime_status,
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
