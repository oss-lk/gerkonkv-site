from __future__ import annotations

"""Default-off TC-big whole-context rescue for isolated fraction truncation.

This wrapper targets a narrow source/target-derived failure family: a Stage10
context is split into multiple current Stage12 rows, exactly one member's sole
numeric defect is ``N/D -> N/d`` with the same numerator and a denominator that
is a strict prefix of the required denominator, and every other member is
strict-clean. The immutable complete Stage10 context is translated once with
pinned TC-big rank0.

Acceptance is fail-closed. The unmodified rank0 candidate must pass all Product
hard checks and maintained research diagnostics, preserve Gutenberg emphasis,
retain the required full fraction, remove the truncated fraction, preserve
terminal sentence punctuation, retain at least 97% of the current aggregate
alphabetic content, and stay in a conservative source-relative alphabetic
range. There is no n-best selection, source rewrite, target repair, literal
injection, placeholder, corpus-specific patch, or evaluator change.
"""

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .numeric_integrity import extract_numeric_literals
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_parenthetical_context_rescue_stage import run_stage12 as run_base_stage12
from .translation_rescue import evaluate_rescue_pair

TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT = (
    "rocketdict-stage12-tc-big-fraction-denominator-whole-context-rescue/1"
)
TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT = (
    "rocketdict-stage12-tc-big-fraction-denominator-whole-context-selector/1"
)
TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT = (
    "rocketdict-stage12-tc-big-fraction-denominator-whole-context-trigger/1"
)
TC_BIG_FRACTION_CONTEXT_SELECTED_PHASE = (
    "tc-big-fraction-denominator-whole-context-selected-v1"
)
DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1024
MAX_CONTEXT_NLP_TOKENS = 160
MIN_SOURCE_ALPHA_RATIO = 0.70
MAX_SOURCE_ALPHA_RATIO = 1.50
MIN_BASE_ALPHA_RETENTION_RATIO = 0.97
MAX_MISSING_DENOMINATOR_SUFFIX_DIGITS = 2
_FRACTION_RE = re.compile(r"(?P<numerator>\d+)/(?P<denominator>\d+)\Z")
_WRAPPER_KEYS = frozenset(
    {
        "enable_tc_big_fraction_context_rescue",
        "tc_big_fraction_context_rescue_contract",
        "tc_big_fraction_context_selector_contract",
        "tc_big_fraction_context_trigger_contract",
        "tc_big_fraction_context_rescue_phase",
        "tc_big_fraction_context_max_nlp_tokens",
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


def _alpha(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _single_count(mapping: dict[str, Any]) -> str | None:
    if len(mapping) != 1:
        return None
    key, raw_count = next(iter(mapping.items()))
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return None
    return str(key) if count == 1 else None


def _fraction_parts(value: str) -> tuple[str, str] | None:
    match = _FRACTION_RE.fullmatch(value)
    if match is None:
        return None
    return match.group("numerator"), match.group("denominator")


def _fraction_truncation_pair(verdict: dict[str, Any]) -> dict[str, Any] | None:
    numeric_symbol = dict(verdict.get("numeric_symbol") or {})
    numeric = dict(numeric_symbol.get("numeric") or {})
    required = _single_count(dict(numeric.get("missing") or {}))
    observed = _single_count(dict(numeric.get("unlicensed_additions") or {}))
    if required is None or observed is None:
        return None
    required_parts = _fraction_parts(required)
    observed_parts = _fraction_parts(observed)
    if required_parts is None or observed_parts is None:
        return None
    required_num, required_den = required_parts
    observed_num, observed_den = observed_parts
    if required_num != observed_num:
        return None
    if required_den == observed_den or not required_den.startswith(observed_den):
        return None
    suffix = required_den[len(observed_den) :]
    if not (1 <= len(suffix) <= MAX_MISSING_DENOMINATOR_SUFFIX_DIGITS):
        return None
    if not suffix.isdigit():
        return None
    if dict(numeric.get("duplicate_required") or {}):
        return None
    if dict(numeric_symbol.get("symbol_mismatch") or {}):
        return None
    if dict(numeric.get("prime_notation") or {}).get("passed") is not True:
        return None
    return {
        "required": required,
        "observed": observed,
        "numerator": required_num,
        "source_denominator": required_den,
        "target_denominator": observed_den,
        "missing_denominator_suffix": suffix,
    }


def evaluate_fraction_member_trigger(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    verdict = evaluate_rescue_pair(source, target)
    pair = _fraction_truncation_pair(verdict)
    numeric_symbol = dict(verdict.get("numeric_symbol") or {})
    non_numeric_safe = bool(
        verdict.get("punctuation_passed") is True
        and verdict.get("length_passed") is True
        and dict(verdict.get("delimiter_preservation") or {}).get("passed") is True
        and dict(verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and dict(verdict.get("output_artifacts") or {}).get("passed") is True
    )
    source_required_count = 0
    if pair is not None:
        source_required_count = sum(
            1 for literal in extract_numeric_literals(source)
            if literal.canonical == pair["required"]
        )
    eligible = bool(
        pair is not None
        and numeric_symbol.get("passed") is not True
        and verdict.get("product_hard_passed") is not True
        and non_numeric_safe
        and source_required_count == 1
    )
    return {
        "contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
        "eligible": eligible,
        "truncation_pair": pair,
        "source_required_fraction_count": source_required_count,
        "non_numeric_hard_and_structural_checks_clean": non_numeric_safe,
        "base_verdict": verdict,
    }


def evaluate_fraction_context_trigger(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: int(row["source_start"]))
    member_results = [evaluate_fraction_member_trigger(row) for row in ordered]
    failing = [
        index
        for index, row in enumerate(ordered)
        if evaluate_rescue_pair(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        ).get("product_hard_passed") is not True
    ]
    triggered = [index for index, result in enumerate(member_results) if result["eligible"] is True]
    other_members_strict = True
    for index, row in enumerate(ordered):
        if index in triggered:
            continue
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
        emphasis = compare_emphasis_markup_preservation(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
        if verdict.get("strictly_eligible") is not True or emphasis.get("passed") is not True:
            other_members_strict = False
            break
    eligible = bool(
        len(ordered) >= 2
        and len(triggered) == 1
        and failing == triggered
        and other_members_strict
    )
    pair = None if len(triggered) != 1 else member_results[triggered[0]]["truncation_pair"]
    return {
        "contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
        "eligible": eligible,
        "member_count": len(ordered),
        "hard_failure_member_indices": failing,
        "fraction_trigger_member_indices": triggered,
        "other_members_strict": other_members_strict,
        "truncation_pair": pair,
        "member_results": member_results,
    }


def evaluate_tc_big_fraction_context_candidate(
    source: str,
    target: str,
    *,
    base_target: str,
    truncation_pair: dict[str, Any],
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    source_ratio = target_alpha / source_alpha if source_alpha else 1.0
    base_retention = target_alpha / base_alpha if base_alpha else 1.0
    observed_literals = [literal.canonical for literal in extract_numeric_literals(target)]
    required = str(truncation_pair["required"])
    truncated = str(truncation_pair["observed"])
    required_exact = observed_literals.count(required) == 1
    truncated_absent = truncated not in observed_literals
    source_terminal = source.rstrip()[-1:] if source.rstrip() else ""
    target_terminal = target.rstrip()[-1:] if target.rstrip() else ""
    terminal_required = source_terminal if source_terminal in ".?!" else None
    terminal_preserved = terminal_required is None or target_terminal == terminal_required
    accepted = bool(
        verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and MIN_SOURCE_ALPHA_RATIO <= source_ratio <= MAX_SOURCE_ALPHA_RATIO
        and base_retention >= MIN_BASE_ALPHA_RETENTION_RATIO
        and required_exact
        and truncated_absent
        and terminal_preserved
    )
    return {
        "selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": source_ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "base_alpha_retention_ratio": base_retention,
        "base_alpha_retention_minimum": MIN_BASE_ALPHA_RETENTION_RATIO,
        "required_fraction": required,
        "required_fraction_exactly_once": required_exact,
        "truncated_fraction": truncated,
        "truncated_fraction_absent": truncated_absent,
        "source_terminal_punctuation": terminal_required,
        "target_terminal_punctuation": target_terminal,
        "terminal_punctuation_preserved": terminal_preserved,
    }


def _planner_context_sequence(row: dict[str, Any]) -> int | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
    except (KeyError, TypeError, ValueError):
        return None
    return first if first >= 0 and first == last else None


def _rows_cover_context(
    rows: list[dict[str, Any]], *, start: int, end: int, source: str
) -> bool:
    ordered = sorted(rows, key=lambda row: int(row["source_start"]))
    if not ordered:
        return False
    return bool(
        int(ordered[0]["source_start"]) == start
        and int(ordered[-1]["source_end"]) == end
        and "".join(str(row.get("source_text") or "") for row in ordered) == source
    )


def _safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["tc_big_fraction_context_rescue"] = {
        "contract": TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
        "selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
        "trigger_contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
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
        effective.get("enable_tc_big_fraction_context_rescue"),
        name="enable_tc_big_fraction_context_rescue",
        default=DEFAULT_ENABLED,
    )
    if not enabled:
        return run_base_stage12(
            database,
            context_run_id=int(context_run_id),
            parameters=_base_parameters(effective),
            implementation=implementation,
        )

    requested_contract = str(effective.get("tc_big_fraction_context_rescue_contract") or TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT)
    requested_selector = str(effective.get("tc_big_fraction_context_selector_contract") or TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT)
    requested_trigger = str(effective.get("tc_big_fraction_context_trigger_contract") or TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT)
    max_tokens = _positive_int_parameter(
        effective.get("tc_big_fraction_context_max_nlp_tokens"),
        name="tc_big_fraction_context_max_nlp_tokens",
        default=MAX_CONTEXT_NLP_TOKENS,
    )
    if max_tokens > MAX_CONTEXT_NLP_TOKENS:
        raise StageExecutionError(f"tc_big_fraction_context_max_nlp_tokens may not exceed {MAX_CONTEXT_NLP_TOKENS}")
    if requested_contract != TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT:
        raise StageExecutionError(f"Unsupported TC-big fraction-context rescue contract {requested_contract!r}")
    if requested_selector != TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT:
        raise StageExecutionError(f"Unsupported TC-big fraction-context selector {requested_selector!r}")
    if requested_trigger != TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT:
        raise StageExecutionError(f"Unsupported TC-big fraction-context trigger {requested_trigger!r}")
    if effective.get("tc_big_fraction_context_rescue_phase") not in {None, TC_BIG_FRACTION_CONTEXT_SELECTED_PHASE}:
        raise StageExecutionError("tc_big_fraction_context_rescue_phase is internal and may not be overridden")

    effective.update({
        "enable_tc_big_fraction_context_rescue": True,
        "tc_big_fraction_context_rescue_contract": TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
        "tc_big_fraction_context_selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
        "tc_big_fraction_context_trigger_contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
        "tc_big_fraction_context_rescue_phase": TC_BIG_FRACTION_CONTEXT_SELECTED_PHASE,
        "tc_big_fraction_context_max_nlp_tokens": max_tokens,
    })

    base_output = run_base_stage12(database, context_run_id=int(context_run_id), parameters=_base_parameters(effective), implementation=implementation)
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
    run_id, cached = _start(database, stage_number=12, implementation=implementation, input_identity=input_identity, parameters=effective)
    if cached is not None:
        return cached

    try:
        content = str(document["content_text"])
        contexts = {int(row["sequence_number"]): row for row in context_rows}
        rows_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in base_rows:
            sequence = _planner_context_sequence(row)
            if sequence is not None:
                rows_by_context[sequence].append(row)
        for rows in rows_by_context.values():
            rows.sort(key=lambda row: int(row["source_start"]))

        attempts: dict[int, dict[str, Any]] = {}
        skipped_over_cap: list[int] = []
        for sequence, rows in sorted(rows_by_context.items()):
            if len(rows) < 2:
                continue
            context = contexts.get(sequence)
            if context is None:
                raise StageExecutionError(f"TC-big fraction-context lost Stage10 context {sequence}")
            start = int(context["source_start"])
            end = int(context["source_end"])
            source = str(context.get("source_text") or "")
            if content[start:end] != source:
                raise StageExecutionError(f"TC-big fraction-context source drift for {sequence}")
            if not _rows_cover_context(rows, start=start, end=end, source=source):
                continue
            trigger = evaluate_fraction_context_trigger(rows)
            if trigger["eligible"] is not True:
                continue
            token_count = int((context.get("payload") or {}).get("token_count") or 0)
            if token_count <= 0:
                raise StageExecutionError(f"TC-big fraction-context {sequence} has no token count")
            if token_count > max_tokens:
                skipped_over_cap.append(sequence)
                continue
            attempts[sequence] = {
                "rows": rows,
                "trigger": trigger,
                "source": source,
                "start": start,
                "end": end,
                "token_count": token_count,
                "base_target": "".join(str(row.get("target_text") or "") for row in rows),
            }

        generated: list[list[dict[str, Any]]] = []
        runtime_status: dict[str, Any] | None = None
        if attempts:
            runtime_status = tc_big_status()
            if runtime_status.get("available") is not True:
                raise StageExecutionError(f"TC-big fraction-context runtime unavailable: {runtime_status}")
            translator = TcBigTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(
                [str(attempts[sequence]["source"]) for sequence in sorted(attempts)],
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(len(rows) != NUM_HYPOTHESES for rows in generated):
                raise StageExecutionError("TC-big fraction-context rank0 cardinality drift")

        accepted: dict[int, dict[str, Any]] = {}
        rejected: dict[int, dict[str, Any]] = {}
        for sequence, hypotheses in zip(sorted(attempts), generated, strict=True):
            attempt = attempts[sequence]
            hypothesis = hypotheses[0]
            if int(hypothesis.get("rank") or 0) != 0:
                raise StageExecutionError("TC-big fraction-context candidate is not rank0")
            target = str(hypothesis.get("text") or "")
            pair = dict(attempt["trigger"]["truncation_pair"])
            selection = evaluate_tc_big_fraction_context_candidate(
                str(attempt["source"]), target, base_target=str(attempt["base_target"]), truncation_pair=pair
            )
            if selection["accepted"] is not True:
                rejected[sequence] = {"reason": "rank0_selector_rejected", "selection": selection, "target_text": target}
                continue
            payload = {
                "planner": {
                    "source": "nlp_sentence",
                    "context_sentence_start": sequence,
                    "context_sentence_end": sequence,
                    "context_sentence_count": 1,
                    "split": False,
                    "token_count": int(attempt["token_count"]),
                    "rescue_strategy": "tc_big_fraction_denominator_whole_context",
                },
                "hypotheses": hypotheses,
                "selected_rank": 0,
                "tc_big_fraction_context_rescue": {
                    "contract": TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
                    "selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
                    "trigger_contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
                    "applied": True,
                    "context_sequence": sequence,
                    "trigger": dict(attempt["trigger"]),
                    "selection": selection,
                    "base_translation_run_id": base_run_id,
                    "base_translation_segment_ids": [int(row["id"]) for row in attempt["rows"]],
                    "raw_model_selected": True,
                    "raw_model_rank": 0,
                    "generation": {"beam_size": BEAM_SIZE, "num_hypotheses": NUM_HYPOTHESES, "max_decoding_length": MAX_DECODING_LENGTH},
                    **_safety_flags(),
                },
            }
            accepted[sequence] = {
                "row": {
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": int(attempt["start"]),
                    "source_end": int(attempt["end"]),
                    "source_text": str(attempt["source"]),
                    "target_text": target,
                    "payload": payload,
                },
                "target_text": target,
            }

        final_rows: list[dict[str, Any]] = []
        emitted: set[int] = set()
        for row in sorted(base_rows, key=lambda row: int(row["source_start"])):
            sequence = _planner_context_sequence(row)
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
            raise StageExecutionError("TC-big fraction-context final source coverage is not byte-exact")

        accepted_sequences = sorted(accepted)
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "tc_big_fraction_context_rescue_contract": TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
            "tc_big_fraction_context_selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
            "tc_big_fraction_context_trigger_contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
            "tc_big_fraction_context_rescue_enabled": True,
            "tc_big_fraction_context_rescue_attempt_count": len(attempts),
            "tc_big_fraction_context_rescue_accepted_count": len(accepted_sequences),
            "tc_big_fraction_context_rescue_rejected_count": len(rejected),
            "tc_big_fraction_context_rescue_skipped_over_cap_count": len(skipped_over_cap),
            "tc_big_fraction_context_rescue_attempted_context_sequences": sorted(attempts),
            "tc_big_fraction_context_rescue_accepted_context_sequences": accepted_sequences,
            "tc_big_fraction_context_rescue_rejected_context_sequences": sorted(rejected),
            "tc_big_fraction_context_rescue_skipped_over_cap_context_sequences": sorted(skipped_over_cap),
            "tc_big_fraction_context_rescue_selected_ranks": [0 for _ in accepted_sequences],
            "tc_big_fraction_context_rescue_selected_targets": [accepted[seq]["target_text"] for seq in accepted_sequences],
            "tc_big_fraction_context_rescue_runtime": runtime_status,
            "base_segment_count": len(base_rows),
            "segment_count": len(final_rows),
            "source_character_sum": sum(len(str(row["source_text"])) for row in final_rows),
            "model_request_count": int(base_output.get("model_request_count") or 0) + len(attempts),
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
