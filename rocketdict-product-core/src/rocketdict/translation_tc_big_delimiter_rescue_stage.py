from __future__ import annotations

"""Opt-in Stage12 rescue for baseline target-only delimiter hallucinations.

This wrapper is deliberately narrow and disabled by default. It runs only after
the existing illustration/numeric/length/citation composition and only examines
source-defined Stage10 contexts that:

* contain at least one current Product-hard-failing Stage12 row;
* are exactly replaceable by complete current Stage12 rows; and
* have an aggregate current target that adds (), [], or {} delimiter characters
  not present in the immutable source context.

The candidate is an unmodified raw hypothesis from the independently pinned
TC-big EN->RU Marian model. It is accepted only when all maintained strict
mechanical checks pass, Gutenberg emphasis is preserved, the target-only
delimiter debt disappears, and target alphabetic volume remains within a
conservative source-relative range. No target repair, literal injection,
placeholder insertion, or corpus-specific whitelist is used.
"""

from pathlib import Path
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_illustration_rescue_stage import run_stage12 as run_base_stage12
from .translation_rescue import evaluate_rescue_pair

TC_BIG_DELIMITER_RESCUE_CONTRACT = "rocketdict-stage12-tc-big-target-delimiter-context-rescue/1"
TC_BIG_DELIMITER_SELECTOR_CONTRACT = "rocketdict-stage12-tc-big-target-delimiter-context-selector/1"
TC_BIG_DELIMITER_TRIGGER_CONTRACT = "rocketdict-stage12-tc-big-target-delimiter-context-trigger/1"
TC_BIG_DELIMITER_SELECTED_PHASE = "tc-big-target-delimiter-context-selected-v1"
DEFAULT_ENABLED = False
DELIMITERS = "()[]{}"
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 512
_TC_BIG_ONLY_KEYS = frozenset({
    "enable_tc_big_target_delimiter_rescue",
    "tc_big_target_delimiter_rescue_contract",
    "tc_big_target_delimiter_selector_contract",
    "tc_big_target_delimiter_trigger_contract",
    "tc_big_target_delimiter_rescue_phase",
})


def _bool_parameter(value: Any, *, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise StageExecutionError(f"Stage12 {name} must be boolean")


def _base_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in parameters.items() if key not in _TC_BIG_ONLY_KEYS}


def _added_delimiters(source: str, target: str) -> dict[str, int]:
    return {
        char: target.count(char) - source.count(char)
        for char in DELIMITERS
        if target.count(char) > source.count(char)
    }


def _source_alpha_ratio(source: str, target: str) -> float:
    source_alpha = sum(char.isalpha() for char in source)
    target_alpha = sum(char.isalpha() for char in target)
    if source_alpha <= 0:
        return 1.0 if target_alpha == 0 else float("inf")
    return target_alpha / source_alpha


def evaluate_tc_big_delimiter_trigger(
    *,
    source: str,
    aggregate_target: str,
    primary_rows: list[dict[str, Any]],
    row_aligned: bool,
) -> dict[str, Any]:
    verdicts = [
        evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        for row in primary_rows
    ]
    has_hard_failure = any(verdict.get("product_hard_passed") is not True for verdict in verdicts)
    additions = _added_delimiters(source, aggregate_target)
    return {
        "contract": TC_BIG_DELIMITER_TRIGGER_CONTRACT,
        "eligible": bool(row_aligned and primary_rows and has_hard_failure and additions),
        "replacement_row_aligned": bool(row_aligned),
        "contains_current_product_hard_failure": has_hard_failure,
        "target_only_delimiter_additions": additions,
        "member_verdicts": verdicts,
    }


def evaluate_tc_big_delimiter_candidate(source: str, target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    additions = _added_delimiters(source, target)
    ratio = _source_alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    accepted = (
        verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and not additions
        and ratio_passed
    )
    return {
        "selector_contract": TC_BIG_DELIMITER_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "target_only_delimiter_additions": additions,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "baseline_target_alpha_non_decrease_required": False,
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
    payload["tc_big_target_delimiter_rescue"] = {
        "contract": TC_BIG_DELIMITER_RESCUE_CONTRACT,
        "selector_contract": TC_BIG_DELIMITER_SELECTOR_CONTRACT,
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


def _context_inventory(
    *,
    content: str,
    base_rows: list[dict[str, Any]],
    context_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hard_keys: set[tuple[int, int]] = set()
    for row in base_rows:
        if evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or "")).get("product_hard_passed") is True:
            continue
        key = _planner_context_key(row)
        if key is not None:
            hard_keys.add(key)

    by_sequence = {int(row["sequence_number"]): row for row in context_rows}
    cases: list[dict[str, Any]] = []
    for first, last in sorted(hard_keys):
        try:
            sources = [by_sequence[index] for index in range(first, last + 1)]
        except KeyError:
            continue
        source = "".join(str(row.get("source_text") or "") for row in sources)
        start = int(sources[0]["source_start"])
        end = int(sources[-1]["source_end"])
        if source != content[start:end]:
            raise StageExecutionError(f"TC-big delimiter rescue Stage10 source coverage drift for {first}:{last}")
        overlapping = [
            row for row in base_rows
            if int(row["source_end"]) > start and int(row["source_start"]) < end
        ]
        members = [
            row for row in base_rows
            if start <= int(row["source_start"]) and int(row["source_end"]) <= end
        ]
        member_source = "".join(str(row.get("source_text") or "") for row in members)
        row_aligned = bool(members) and member_source == source
        if row_aligned:
            row_aligned = (
                int(members[0]["source_start"]) == start
                and int(members[-1]["source_end"]) == end
                and len(overlapping) == len(members)
            )
        aggregate_target = (
            "".join(str(row.get("target_text") or "") for row in members)
            if row_aligned else ""
        )
        trigger = evaluate_tc_big_delimiter_trigger(
            source=source,
            aggregate_target=aggregate_target,
            primary_rows=members if row_aligned else [],
            row_aligned=row_aligned,
        )
        cases.append({
            "context_sentence_start": first,
            "context_sentence_end": last,
            "source_start": start,
            "source_end": end,
            "source_text": source,
            "primary_rows": members if row_aligned else [],
            "overlapping_rows": overlapping,
            "aggregate_target": aggregate_target,
            "trigger": trigger,
        })
    return cases


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
        effective.get("enable_tc_big_target_delimiter_rescue"),
        name="enable_tc_big_target_delimiter_rescue",
        default=DEFAULT_ENABLED,
    )
    if not enabled:
        return run_base_stage12(
            database,
            context_run_id=int(context_run_id),
            parameters=_base_parameters(effective),
            implementation=implementation,
        )

    requested_contract = str(effective.get("tc_big_target_delimiter_rescue_contract") or TC_BIG_DELIMITER_RESCUE_CONTRACT)
    requested_selector = str(effective.get("tc_big_target_delimiter_selector_contract") or TC_BIG_DELIMITER_SELECTOR_CONTRACT)
    requested_trigger = str(effective.get("tc_big_target_delimiter_trigger_contract") or TC_BIG_DELIMITER_TRIGGER_CONTRACT)
    if requested_contract != TC_BIG_DELIMITER_RESCUE_CONTRACT:
        raise StageExecutionError(f"Unsupported TC-big delimiter rescue contract {requested_contract!r}")
    if requested_selector != TC_BIG_DELIMITER_SELECTOR_CONTRACT:
        raise StageExecutionError(f"Unsupported TC-big delimiter selector {requested_selector!r}")
    if requested_trigger != TC_BIG_DELIMITER_TRIGGER_CONTRACT:
        raise StageExecutionError(f"Unsupported TC-big delimiter trigger {requested_trigger!r}")
    if effective.get("tc_big_target_delimiter_rescue_phase") not in {None, TC_BIG_DELIMITER_SELECTED_PHASE}:
        raise StageExecutionError("tc_big_target_delimiter_rescue_phase is internal and may not be overridden")

    effective["enable_tc_big_target_delimiter_rescue"] = True
    effective["tc_big_target_delimiter_rescue_contract"] = TC_BIG_DELIMITER_RESCUE_CONTRACT
    effective["tc_big_target_delimiter_selector_contract"] = TC_BIG_DELIMITER_SELECTOR_CONTRACT
    effective["tc_big_target_delimiter_trigger_contract"] = TC_BIG_DELIMITER_TRIGGER_CONTRACT
    effective["tc_big_target_delimiter_rescue_phase"] = TC_BIG_DELIMITER_SELECTED_PHASE

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
        cases = _context_inventory(content=content, base_rows=base_rows, context_rows=context_rows)
        attempts = [case for case in cases if case["trigger"]["eligible"] is True]

        generated: list[list[dict[str, Any]]] = []
        runtime_status: dict[str, Any] | None = None
        if attempts:
            runtime_status = tc_big_status()
            if runtime_status.get("available") is not True:
                raise StageExecutionError(f"TC-big target-delimiter rescue runtime unavailable: {runtime_status}")
            translator = TcBigTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(
                [str(case["source_text"]) for case in attempts],
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(len(row) != NUM_HYPOTHESES for row in generated):
                raise StageExecutionError("TC-big target-delimiter rescue n-best cardinality drift")

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        for case, hypotheses in zip(attempts, generated, strict=True):
            evaluated: list[dict[str, Any]] = []
            selected_rank: int | None = None
            selected_target: str | None = None
            selected_selection: dict[str, Any] | None = None
            for hypothesis in hypotheses:
                rank = int(hypothesis["rank"])
                target = str(hypothesis.get("text") or "")
                selection = evaluate_tc_big_delimiter_candidate(str(case["source_text"]), target)
                evaluated.append({
                    "rank": rank,
                    "target_text": target,
                    "score": hypothesis.get("score"),
                    "accepted": selection["accepted"],
                    "selection": selection,
                })
                if selected_rank is None and selection["accepted"] is True:
                    selected_rank = rank
                    selected_target = target
                    selected_selection = selection
            if selected_rank is None or selected_target is None or selected_selection is None:
                rejected.append({
                    "source_start": int(case["source_start"]),
                    "context_sentence_start": int(case["context_sentence_start"]),
                    "context_sentence_end": int(case["context_sentence_end"]),
                    "reason": "selector_rejected",
                    "evaluated_hypotheses": evaluated,
                })
                continue
            member_ids = [int(row["id"]) for row in case["primary_rows"]]
            payload = {
                "planner": {
                    "source": "tc_big_target_delimiter_context_rescue",
                    "context_sentence_start": int(case["context_sentence_start"]),
                    "context_sentence_end": int(case["context_sentence_end"]),
                    "split": False,
                    "rescue_strategy": "tc_big_target_delimiter_context",
                    "tc_big_target_delimiter_rescue_contract": TC_BIG_DELIMITER_RESCUE_CONTRACT,
                },
                "hypotheses": hypotheses,
                "selected_rank": selected_rank,
                "tc_big_target_delimiter_rescue": {
                    "contract": TC_BIG_DELIMITER_RESCUE_CONTRACT,
                    "selector_contract": TC_BIG_DELIMITER_SELECTOR_CONTRACT,
                    "trigger_contract": TC_BIG_DELIMITER_TRIGGER_CONTRACT,
                    "applied": True,
                    "trigger": dict(case["trigger"]),
                    "selection": selected_selection,
                    "base_translation_run_id": base_run_id,
                    "base_translation_segment_ids": member_ids,
                    "base_source_span": [int(case["source_start"]), int(case["source_end"])],
                    "raw_model_selected": True,
                    "generation": {
                        "beam_size": BEAM_SIZE,
                        "num_hypotheses": NUM_HYPOTHESES,
                        "max_decoding_length": MAX_DECODING_LENGTH,
                    },
                    **_safety_flags(),
                },
            }
            accepted[int(case["source_start"])] = {
                "member_ids": set(member_ids),
                "source_start": int(case["source_start"]),
                "source_end": int(case["source_end"]),
                "source_text": str(case["source_text"]),
                "target_text": selected_target,
                "selected_rank": selected_rank,
                "payload": payload,
                "evaluated_hypotheses": evaluated,
            }

        replaced_ids = {
            member_id
            for replacement in accepted.values()
            for member_id in replacement["member_ids"]
        }
        final_rows = [
            _copy_base_row(row)
            for row in sorted(base_rows, key=lambda item: int(item["source_start"]))
            if int(row["id"]) not in replaced_ids
        ]
        for replacement in accepted.values():
            final_rows.append({
                "sequence_number": 0,
                "kind": "translation_segment",
                "source_start": replacement["source_start"],
                "source_end": replacement["source_end"],
                "source_text": replacement["source_text"],
                "target_text": replacement["target_text"],
                "payload": replacement["payload"],
            })
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError("TC-big target-delimiter rescue final source coverage is not byte-exact")
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        if source_sum != sum(len(str(row.get("source_text") or "")) for row in base_rows):
            raise StageExecutionError("TC-big target-delimiter rescue changed total source character coverage")

        accepted_values = sorted(accepted.values(), key=lambda value: int(value["source_start"]))
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "tc_big_target_delimiter_rescue_contract": TC_BIG_DELIMITER_RESCUE_CONTRACT,
            "tc_big_target_delimiter_selector_contract": TC_BIG_DELIMITER_SELECTOR_CONTRACT,
            "tc_big_target_delimiter_trigger_contract": TC_BIG_DELIMITER_TRIGGER_CONTRACT,
            "tc_big_target_delimiter_rescue_enabled": True,
            "tc_big_target_delimiter_rescue_attempt_count": len(attempts),
            "tc_big_target_delimiter_rescue_accepted_count": len(accepted_values),
            "tc_big_target_delimiter_rescue_rejected_count": len(rejected),
            "tc_big_target_delimiter_rescue_attempted_source_starts": [int(case["source_start"]) for case in attempts],
            "tc_big_target_delimiter_rescue_accepted_source_starts": [int(value["source_start"]) for value in accepted_values],
            "tc_big_target_delimiter_rescue_selected_ranks": [int(value["selected_rank"]) for value in accepted_values],
            "tc_big_target_delimiter_rescue_selected_targets": [str(value["target_text"]) for value in accepted_values],
            "tc_big_target_delimiter_rescue_model_request_count": len(attempts),
            "tc_big_target_delimiter_rescue_model_batch_count": 1 if attempts else 0,
            "tc_big_target_delimiter_rescue_runtime": runtime_status,
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
