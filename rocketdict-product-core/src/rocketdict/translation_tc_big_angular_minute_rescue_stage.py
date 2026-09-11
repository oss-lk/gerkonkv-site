from __future__ import annotations

"""Opt-in Stage12 rescue for one-degree/arcminute prime mistranslation family.

The trigger is source-defined rather than corpus-position-defined.  A row must
exactly cover one Stage10 context, already fail a maintained Product hard gate,
and contain exactly one English angular expression of the form
``N Degree[s] M'`` whose numeric prime signature is not preserved by the
current target.  Only unmodified raw hypotheses from the independently pinned
TC-big runtime are eligible.

Mechanical prime preservation is necessary but not sufficient: the Russian raw
candidate must also preserve the same degree/minute values in an explicit
``N градус... M'`` angular phrase.  This semantic anchor prevents the wrapper
from reviving the unsafe generic prime fallback/decomposition family.
"""

from pathlib import Path
import re
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import evaluate_rescue_pair
from .translation_tc_big_equals_addition_rescue_stage import run_stage12 as run_base_stage12

TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT = "rocketdict-stage12-tc-big-angular-minute-prime-rescue/1"
TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT = "rocketdict-stage12-tc-big-angular-minute-prime-selector/1"
TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT = "rocketdict-stage12-tc-big-angular-minute-prime-trigger/1"
TC_BIG_ANGULAR_MINUTE_SELECTED_PHASE = "tc-big-angular-minute-prime-selected-v1"
DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 512
MIN_SOURCE_ALPHA_RATIO = 0.70
MAX_SOURCE_ALPHA_RATIO = 1.50

_SOURCE_ANGLE_RE = re.compile(
    r"\b(?P<degrees>\d+)\s+Degrees?\s+(?P<minutes>\d+)'",
    re.IGNORECASE,
)
_WRAPPER_KEYS = frozenset(
    {
        "enable_tc_big_angular_minute_rescue",
        "tc_big_angular_minute_rescue_contract",
        "tc_big_angular_minute_selector_contract",
        "tc_big_angular_minute_trigger_contract",
        "tc_big_angular_minute_rescue_phase",
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


def _source_angle(source: str) -> dict[str, str] | None:
    matches = list(_SOURCE_ANGLE_RE.finditer(source))
    if len(matches) != 1:
        return None
    match = matches[0]
    return {"degrees": match.group("degrees"), "minutes": match.group("minutes")}


def _target_angle_preserved(target: str, *, degrees: str, minutes: str) -> bool:
    pattern = re.compile(
        rf"(?<!\d){re.escape(degrees)}\s+градус(?:а|ов)?\s+{re.escape(minutes)}'(?!')",
        re.IGNORECASE,
    )
    return pattern.search(target) is not None


def _prime_verdict(verdict: dict[str, Any]) -> dict[str, Any]:
    numeric_symbol = dict(verdict.get("numeric_symbol") or {})
    numeric = dict(numeric_symbol.get("numeric") or {})
    return dict(numeric.get("prime_notation") or {})


def evaluate_tc_big_angular_minute_trigger(
    row: dict[str, Any], *, exact_stage10_context: bool
) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    angle = _source_angle(source)
    verdict = evaluate_rescue_pair(source, target)
    prime = _prime_verdict(verdict)
    source_events = list(prime.get("source_events") or [])
    exact_prime_shape = bool(
        angle is not None
        and len(source_events) == 1
        and str(source_events[0].get("value") or "") == angle["minutes"]
        and int(source_events[0].get("prime_count") or 0) == 1
    )
    eligible = bool(
        exact_stage10_context
        and angle is not None
        and exact_prime_shape
        and verdict.get("product_hard_passed") is not True
        and prime.get("passed") is not True
    )
    return {
        "contract": TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT,
        "eligible": eligible,
        "exact_stage10_single_row_context": bool(exact_stage10_context),
        "contains_current_product_hard_failure": verdict.get("product_hard_passed") is not True,
        "source_angle": angle,
        "source_single_minute_prime_shape": exact_prime_shape,
        "current_prime_notation_passed": prime.get("passed") is True,
        "base_verdict": verdict,
    }


def evaluate_tc_big_angular_minute_candidate(source: str, target: str) -> dict[str, Any]:
    angle = _source_angle(source)
    verdict = evaluate_rescue_pair(source, target)
    prime = _prime_verdict(verdict)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _source_alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    semantic_angle_preserved = bool(
        angle is not None
        and _target_angle_preserved(
            target,
            degrees=angle["degrees"],
            minutes=angle["minutes"],
        )
    )
    accepted = bool(
        angle is not None
        and verdict.get("strictly_eligible") is True
        and prime.get("passed") is True
        and emphasis.get("passed") is True
        and ratio_passed
        and semantic_angle_preserved
    )
    return {
        "selector_contract": TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "mechanical_verdict": verdict,
        "prime_notation": prime,
        "emphasis_markup": emphasis,
        "source_angle": angle,
        "semantic_angle_preserved": semantic_angle_preserved,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
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
    payload["tc_big_angular_minute_rescue"] = {
        "contract": TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT,
        "selector_contract": TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
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
    *, content: str, base_rows: list[dict[str, Any]], context_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_sequence = {int(row["sequence_number"]): row for row in context_rows}
    attempts: list[dict[str, Any]] = []
    for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
        source = str(row.get("source_text") or "")
        if _source_angle(source) is None:
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
                context_source = "".join(str(item.get("source_text") or "") for item in source_rows)
                start = int(source_rows[0]["source_start"])
                end = int(source_rows[-1]["source_end"])
                if context_source != content[start:end]:
                    raise StageExecutionError(
                        f"TC-big angular-minute Stage10 source coverage drift for {first}:{last}"
                    )
                exact_context = bool(
                    start == int(row["source_start"])
                    and end == int(row["source_end"])
                    and context_source == source
                )
        trigger = evaluate_tc_big_angular_minute_trigger(
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
        effective.get("enable_tc_big_angular_minute_rescue"),
        name="enable_tc_big_angular_minute_rescue",
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
        effective.get("tc_big_angular_minute_rescue_contract")
        or TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("tc_big_angular_minute_selector_contract")
        or TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT
    )
    requested_trigger = str(
        effective.get("tc_big_angular_minute_trigger_contract")
        or TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT
    )
    if requested_contract != TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big angular-minute rescue contract {requested_contract!r}"
        )
    if requested_selector != TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big angular-minute selector {requested_selector!r}"
        )
    if requested_trigger != TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT:
        raise StageExecutionError(
            f"Unsupported TC-big angular-minute trigger {requested_trigger!r}"
        )
    if effective.get("tc_big_angular_minute_rescue_phase") not in {
        None,
        TC_BIG_ANGULAR_MINUTE_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "tc_big_angular_minute_rescue_phase is internal and may not be overridden"
        )

    effective["enable_tc_big_angular_minute_rescue"] = True
    effective["tc_big_angular_minute_rescue_contract"] = TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT
    effective["tc_big_angular_minute_selector_contract"] = TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT
    effective["tc_big_angular_minute_trigger_contract"] = TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT
    effective["tc_big_angular_minute_rescue_phase"] = TC_BIG_ANGULAR_MINUTE_SELECTED_PHASE

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
                    f"TC-big angular-minute runtime unavailable: {runtime_status}"
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
                raise StageExecutionError("TC-big angular-minute n-best cardinality drift")

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            row = attempt["row"]
            evaluated: list[dict[str, Any]] = []
            selected_rank: int | None = None
            selected_target: str | None = None
            selected_selection: dict[str, Any] | None = None
            for hypothesis in hypotheses:
                rank = int(hypothesis["rank"])
                target = str(hypothesis.get("text") or "")
                selection = evaluate_tc_big_angular_minute_candidate(
                    str(row["source_text"]), target
                )
                evaluated.append(
                    {
                        "rank": rank,
                        "target_text": target,
                        "score": hypothesis.get("score"),
                        "accepted": selection["accepted"],
                        "selection": selection,
                    }
                )
                if selected_rank is None and selection["accepted"] is True:
                    selected_rank = rank
                    selected_target = target
                    selected_selection = selection
            if selected_rank is None or selected_target is None or selected_selection is None:
                rejected.append(
                    {
                        "source_start": int(row["source_start"]),
                        "reason": "selector_rejected",
                        "evaluated_hypotheses": evaluated,
                    }
                )
                continue

            payload = dict(row.get("payload") or {})
            payload["hypotheses"] = hypotheses
            payload["selected_rank"] = selected_rank
            payload["tc_big_angular_minute_rescue"] = {
                "contract": TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT,
                "selector_contract": TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
                "trigger_contract": TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT,
                "applied": True,
                "trigger": dict(attempt["trigger"]),
                "selection": selected_selection,
                "base_translation_run_id": base_run_id,
                "base_translation_segment_id": int(row["id"]),
                "raw_model_selected": True,
                "generation": {
                    "beam_size": BEAM_SIZE,
                    "num_hypotheses": NUM_HYPOTHESES,
                    "max_decoding_length": MAX_DECODING_LENGTH,
                },
                **_safety_flags(),
            }
            accepted[int(row["id"])] = {
                "source_start": int(row["source_start"]),
                "target_text": selected_target,
                "selected_rank": selected_rank,
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
                "TC-big angular-minute final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        if source_sum != sum(
            len(str(row.get("source_text") or "")) for row in base_rows
        ):
            raise StageExecutionError("TC-big angular-minute changed total source coverage")

        accepted_values = sorted(
            accepted.values(), key=lambda value: int(value["source_start"])
        )
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "tc_big_angular_minute_rescue_contract": TC_BIG_ANGULAR_MINUTE_RESCUE_CONTRACT,
            "tc_big_angular_minute_selector_contract": TC_BIG_ANGULAR_MINUTE_SELECTOR_CONTRACT,
            "tc_big_angular_minute_trigger_contract": TC_BIG_ANGULAR_MINUTE_TRIGGER_CONTRACT,
            "tc_big_angular_minute_rescue_enabled": True,
            "tc_big_angular_minute_rescue_attempt_count": len(attempts),
            "tc_big_angular_minute_rescue_accepted_count": len(accepted_values),
            "tc_big_angular_minute_rescue_rejected_count": len(rejected),
            "tc_big_angular_minute_rescue_attempted_source_starts": [
                int(attempt["row"]["source_start"]) for attempt in attempts
            ],
            "tc_big_angular_minute_rescue_accepted_source_starts": [
                int(value["source_start"]) for value in accepted_values
            ],
            "tc_big_angular_minute_rescue_selected_ranks": [
                int(value["selected_rank"]) for value in accepted_values
            ],
            "tc_big_angular_minute_rescue_selected_targets": [
                str(value["target_text"]) for value in accepted_values
            ],
            "tc_big_angular_minute_rescue_model_request_count": len(attempts),
            "tc_big_angular_minute_rescue_model_batch_count": 1 if attempts else 0,
            "tc_big_angular_minute_rescue_runtime": runtime_status,
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
