from __future__ import annotations

"""Default-off OPUS rescue for dense technical-label figure groups.

This research wrapper handles one source-defined failure family that the ordinary
single-Stage10 whole-context rescue cannot represent: planner-v8 may coalesce a
protected figure label with following prose into one ``nlp_sentence_group`` that
spans multiple Stage10 contexts, then split that group for MT. A split member can
lose a dense graph of optical/technical labels and the prose around them.

Eligibility is deliberately fail-closed and corpus-position independent. The
complete current planner group must be byte-exact, cross at least two Stage10
contexts, carry the planner's protected-boundary provenance, contain exactly one
source Illustration marker, contain a dense technical-label graph, stay within
the proven research token cap, and contain exactly one current *missing-only*
numeric/symbol hard failure while all member non-numeric hard/structural checks
remain clean.

Only unmodified pinned OPUS rank0 for the exact planner-group source is
considered. It must pass all maintained hard/research checks, preserve Gutenberg
emphasis, preserve the complete technical-label sequence and Illustration
payload exactly, stay inside a source-relative alphabetic envelope, and not
reduce aggregate alphabetic content versus the current split translation.
Rejection leaves the base output exact. There is no source rewrite, target
repair, literal injection, placeholder use, corpus-specific target patch,
evaluator weakening, or n-best cherry-picking.
"""

from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .numeric_integrity import evaluate_numeric_symbol_pair
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_parenthetical_context_rescue_stage import run_stage12 as run_base_stage12
from .translation_rescue import evaluate_rescue_pair

DENSE_FIGURE_GROUP_RESCUE_CONTRACT = "rocketdict-stage12-dense-figure-label-group-rescue/1"
DENSE_FIGURE_GROUP_SELECTOR_CONTRACT = "rocketdict-stage12-dense-figure-label-group-selector/1"
DENSE_FIGURE_GROUP_TRIGGER_CONTRACT = "rocketdict-stage12-dense-figure-label-group-trigger/1"
DENSE_FIGURE_GROUP_SELECTED_PHASE = "dense-figure-label-group-selected-v1"
DEFAULT_ENABLED = False
MAX_GROUP_NLP_TOKENS = 192
MIN_TECHNICAL_LABEL_OCCURRENCES = 10
MIN_DISTINCT_TECHNICAL_LABELS = 8
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1536
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.50

_TECHNICAL_LABEL_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Z]{1,3}\d+|\d+[A-Z]{1,3}|[A-Z]{2,3})(?![A-Za-z0-9])"
)
_SOURCE_ILLUSTRATION_RE = re.compile(r"\[Illustration:\s*([^\]]+)\]", flags=re.IGNORECASE)
_TARGET_ILLUSTRATION_RE = re.compile(
    r"\[(?:Illustration|Иллюстрация)\s*:\s*([^\]]+)\]", flags=re.IGNORECASE
)
_WRAPPER_KEYS = frozenset(
    {
        "enable_dense_figure_label_group_rescue",
        "dense_figure_label_group_rescue_contract",
        "dense_figure_label_group_selector_contract",
        "dense_figure_label_group_trigger_contract",
        "dense_figure_label_group_rescue_phase",
        "dense_figure_label_group_max_nlp_tokens",
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


def _alpha_count(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _source_alpha_ratio(source: str, target: str) -> float:
    source_alpha = _alpha_count(source)
    target_alpha = _alpha_count(target)
    if source_alpha <= 0:
        return 1.0 if target_alpha == 0 else float("inf")
    return target_alpha / source_alpha


def _technical_label_sequence(text: str) -> list[str]:
    return _TECHNICAL_LABEL_RE.findall(text)


def _technical_label_counter(text: str) -> Counter[str]:
    return Counter(_technical_label_sequence(text))


def _illustration_payloads(regex: re.Pattern[str], text: str) -> list[str]:
    return [match.group(1).strip() for match in regex.finditer(text)]


def _planner_group_key(row: dict[str, Any]) -> tuple[int, int] | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    if str(planner.get("source") or "") != "nlp_sentence_group":
        return None
    if planner.get("protected_sentence_boundary_coalesced") is not True:
        return None
    if planner.get("split") is not True:
        return None
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
        count = int(planner["context_sentence_count"])
    except (KeyError, TypeError, ValueError):
        return None
    if first < 0 or last <= first or count != last - first + 1:
        return None
    return first, last


def _rows_cover_span(
    rows: list[dict[str, Any]], *, start: int, end: int, source: str
) -> bool:
    ordered = sorted(rows, key=lambda row: int(row["source_start"]))
    cursor = start
    pieces: list[str] = []
    for row in ordered:
        row_start = int(row["source_start"])
        row_end = int(row["source_end"])
        row_source = str(row.get("source_text") or "")
        if row_start != cursor or row_end <= row_start:
            return False
        pieces.append(row_source)
        cursor = row_end
    return bool(ordered and cursor == end and "".join(pieces) == source)


def _context_group_source(
    *,
    content: str,
    context_by_sequence: dict[int, dict[str, Any]],
    first: int,
    last: int,
) -> dict[str, Any] | None:
    try:
        contexts = [context_by_sequence[index] for index in range(first, last + 1)]
    except KeyError:
        return None
    start = int(contexts[0]["source_start"])
    end = int(contexts[-1]["source_end"])
    cursor = start
    pieces: list[str] = []
    token_count = 0
    for expected_sequence, context in zip(range(first, last + 1), contexts, strict=True):
        if int(context["sequence_number"]) != expected_sequence:
            return None
        context_start = int(context["source_start"])
        context_end = int(context["source_end"])
        context_source = str(context.get("source_text") or "")
        if context_start != cursor or context_end <= context_start:
            return None
        if content[context_start:context_end] != context_source:
            return None
        pieces.append(context_source)
        cursor = context_end
        try:
            tokens = int((context.get("payload") or {}).get("token_count") or 0)
        except (TypeError, ValueError):
            return None
        if tokens <= 0:
            return None
        token_count += tokens
    source = "".join(pieces)
    if cursor != end or content[start:end] != source:
        return None
    return {
        "contexts": contexts,
        "start": start,
        "end": end,
        "source": source,
        "token_count": token_count,
    }


def _member_numeric_omission_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    non_numeric_safe = True
    for row in sorted(rows, key=lambda item: int(item["source_start"])):
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        numeric_symbol = evaluate_numeric_symbol_pair(source, target)
        rescue = evaluate_rescue_pair(source, target)
        emphasis = compare_emphasis_markup_preservation(source, target)
        if (
            rescue.get("punctuation_passed") is not True
            or rescue.get("length_passed") is not True
            or (rescue.get("delimiter_preservation") or {}).get("passed") is not True
            or (rescue.get("output_artifacts") or {}).get("passed") is not True
            or emphasis.get("passed") is not True
        ):
            non_numeric_safe = False
        if numeric_symbol.get("passed") is True:
            continue
        numeric = dict(numeric_symbol.get("numeric") or {})
        prime = dict(numeric.get("prime_notation") or {})
        missing_only = bool(
            numeric.get("missing")
            and not numeric.get("duplicate_required")
            and not numeric.get("unlicensed_additions")
            and not numeric_symbol.get("symbol_mismatch")
            and prime.get("passed") is True
        )
        failures.append(
            {
                "translation_segment_id": int(row.get("id") or 0),
                "sequence_number": int(row.get("sequence_number") or 0),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "missing_only": missing_only,
                "numeric_symbol": numeric_symbol,
            }
        )
    return {
        "failure_count": len(failures),
        "all_failures_missing_only": bool(failures) and all(
            failure["missing_only"] is True for failure in failures
        ),
        "member_non_numeric_checks_safe": non_numeric_safe,
        "failures": failures,
    }


def evaluate_dense_figure_group_trigger(
    *,
    content: str,
    context_by_sequence: dict[int, dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    max_nlp_tokens: int = MAX_GROUP_NLP_TOKENS,
) -> dict[str, Any]:
    ordered = sorted(primary_rows, key=lambda row: int(row["source_start"]))
    key = _planner_group_key(ordered[0]) if ordered else None
    planner_exact = bool(
        key is not None and all(_planner_group_key(row) == key for row in ordered)
    )
    group = (
        _context_group_source(
            content=content,
            context_by_sequence=context_by_sequence,
            first=key[0],
            last=key[1],
        )
        if planner_exact and key is not None
        else None
    )
    if group is None:
        source = ""
        start = 0
        end = 0
        token_count = 0
        contexts_exact = False
    else:
        source = str(group["source"])
        start = int(group["start"])
        end = int(group["end"])
        token_count = int(group["token_count"])
        contexts_exact = True
    rows_exact = bool(
        group is not None
        and _rows_cover_span(ordered, start=start, end=end, source=source)
    )
    within_cap = bool(0 < token_count <= int(max_nlp_tokens))
    labels = _technical_label_sequence(source)
    distinct_labels = sorted(set(labels))
    dense_labels = bool(
        len(labels) >= MIN_TECHNICAL_LABEL_OCCURRENCES
        and len(distinct_labels) >= MIN_DISTINCT_TECHNICAL_LABELS
    )
    illustration_payloads = _illustration_payloads(_SOURCE_ILLUSTRATION_RE, source)
    single_illustration = len(illustration_payloads) == 1
    omission = _member_numeric_omission_profile(ordered)
    exactly_one_missing_only_failure = bool(
        omission["failure_count"] == 1
        and omission["all_failures_missing_only"] is True
    )
    eligible = bool(
        planner_exact
        and contexts_exact
        and rows_exact
        and len(ordered) >= 2
        and within_cap
        and dense_labels
        and single_illustration
        and exactly_one_missing_only_failure
        and omission["member_non_numeric_checks_safe"] is True
    )
    return {
        "contract": DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
        "eligible": eligible,
        "planner_group": None if key is None else [key[0], key[1]],
        "planner_group_exact": planner_exact,
        "immutable_context_group_exact": contexts_exact,
        "complete_current_rows": rows_exact,
        "member_count": len(ordered),
        "member_sequences": [int(row["sequence_number"]) for row in ordered],
        "source_start": start,
        "source_end": end,
        "group_nlp_token_count": token_count,
        "group_nlp_token_cap": int(max_nlp_tokens),
        "within_group_nlp_token_cap": within_cap,
        "technical_label_occurrences": len(labels),
        "technical_label_distinct_count": len(distinct_labels),
        "technical_label_occurrence_minimum": MIN_TECHNICAL_LABEL_OCCURRENCES,
        "technical_label_distinct_minimum": MIN_DISTINCT_TECHNICAL_LABELS,
        "technical_label_sequence": labels,
        "dense_technical_label_graph": dense_labels,
        "source_illustration_payloads": illustration_payloads,
        "single_source_illustration_marker": single_illustration,
        "numeric_omission_profile": omission,
        "exactly_one_missing_only_numeric_failure": exactly_one_missing_only_failure,
    }


def evaluate_dense_figure_group_candidate(
    source: str,
    target: str,
    *,
    primary_target: str,
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_labels = _technical_label_sequence(source)
    target_labels = _technical_label_sequence(target)
    label_sequence_exact = source_labels == target_labels
    source_illustrations = _illustration_payloads(_SOURCE_ILLUSTRATION_RE, source)
    target_illustrations = _illustration_payloads(_TARGET_ILLUSTRATION_RE, target)
    illustration_exact = bool(
        len(source_illustrations) == 1 and target_illustrations == source_illustrations
    )
    ratio = _source_alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    primary_alpha = _alpha_count(primary_target)
    candidate_alpha = _alpha_count(target)
    alpha_non_decreasing = candidate_alpha >= primary_alpha
    accepted = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and label_sequence_exact
        and illustration_exact
        and ratio_passed
        and alpha_non_decreasing
    )
    return {
        "selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "strict_research_passed": verdict.get("strict_research_passed") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_technical_labels": source_labels,
        "target_technical_labels": target_labels,
        "technical_label_sequence_exact": label_sequence_exact,
        "source_technical_label_counter": dict(_technical_label_counter(source)),
        "target_technical_label_counter": dict(_technical_label_counter(target)),
        "source_illustration_payloads": source_illustrations,
        "target_illustration_payloads": target_illustrations,
        "illustration_payload_exact": illustration_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "target_alpha_primary": primary_alpha,
        "target_alpha_candidate": candidate_alpha,
        "target_alpha_non_decreasing": alpha_non_decreasing,
        "raw_target_nonempty": bool(target.strip()),
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["dense_figure_label_group_rescue"] = {
        "contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
        "selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
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


def _eligible_groups(
    *,
    content: str,
    base_rows: list[dict[str, Any]],
    context_rows: list[dict[str, Any]],
    max_nlp_tokens: int,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in base_rows:
        key = _planner_group_key(row)
        if key is not None:
            grouped[key].append(row)
    context_by_sequence = {
        int(row["sequence_number"]): row for row in context_rows
    }
    attempts: list[dict[str, Any]] = []
    for key, members in sorted(grouped.items()):
        ordered = sorted(members, key=lambda row: int(row["source_start"]))
        if len(ordered) < 2:
            continue
        trigger = evaluate_dense_figure_group_trigger(
            content=content,
            context_by_sequence=context_by_sequence,
            primary_rows=ordered,
            max_nlp_tokens=max_nlp_tokens,
        )
        if trigger["eligible"] is not True:
            continue
        group = _context_group_source(
            content=content,
            context_by_sequence=context_by_sequence,
            first=key[0],
            last=key[1],
        )
        if group is None:
            raise StageExecutionError("dense figure group vanished after trigger acceptance")
        attempts.append(
            {
                "planner_group": key,
                "primary_rows": ordered,
                "trigger": trigger,
                "group": group,
            }
        )
    return attempts


def _replacement_row(
    *,
    attempt: dict[str, Any],
    target: str,
    hypothesis: dict[str, Any],
    selection: dict[str, Any],
    base_run_id: int,
) -> dict[str, Any]:
    group = dict(attempt["group"])
    first, last = attempt["planner_group"]
    primary_rows = list(attempt["primary_rows"])
    first_planner = dict((primary_rows[0].get("payload") or {}).get("planner") or {})
    payload = {
        "planner": {
            **first_planner,
            "source": "nlp_sentence_group",
            "context_sentence_start": int(first),
            "context_sentence_end": int(last),
            "context_sentence_count": int(last) - int(first) + 1,
            "protected_sentence_boundary_coalesced": True,
            "split": False,
            "token_count": int(group["token_count"]),
            "rescue_strategy": "dense_figure_label_group",
            "dense_figure_label_group_rescue_contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
        },
        "hypotheses": [hypothesis],
        "selected_rank": 0,
        "dense_figure_label_group_rescue": {
            "contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
            "selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
            "trigger_contract": DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
            "applied": True,
            "trigger": dict(attempt["trigger"]),
            "selection": selection,
            "base_translation_run_id": int(base_run_id),
            "base_translation_segment_ids": [int(row["id"]) for row in primary_rows],
            "base_source_spans": [
                [int(row["source_start"]), int(row["source_end"])] for row in primary_rows
            ],
            "base_targets": [str(row.get("target_text") or "") for row in primary_rows],
            "raw_model_selected": True,
            "raw_model_rank": 0,
            "model": "opus-en-ru-ct2",
            "generation": {
                "beam_size": BEAM_SIZE,
                "num_hypotheses": NUM_HYPOTHESES,
                "max_decoding_length": MAX_DECODING_LENGTH,
            },
            **_safety_flags(),
        },
    }
    return {
        "sequence_number": 0,
        "kind": "translation_segment",
        "source_start": int(group["start"]),
        "source_end": int(group["end"]),
        "source_text": str(group["source"]),
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
        effective.get("enable_dense_figure_label_group_rescue"),
        name="enable_dense_figure_label_group_rescue",
        default=DEFAULT_ENABLED,
    )
    cap = _positive_int_parameter(
        effective.get("dense_figure_label_group_max_nlp_tokens"),
        name="dense_figure_label_group_max_nlp_tokens",
        default=MAX_GROUP_NLP_TOKENS,
    )
    if cap > MAX_GROUP_NLP_TOKENS:
        raise StageExecutionError(
            "dense_figure_label_group_max_nlp_tokens may not exceed the proven cap "
            f"{MAX_GROUP_NLP_TOKENS}"
        )
    if not enabled:
        return run_base_stage12(
            database,
            context_run_id=int(context_run_id),
            parameters=_base_parameters(effective),
            implementation=implementation,
        )

    if str(effective.get("dense_figure_label_group_rescue_contract") or DENSE_FIGURE_GROUP_RESCUE_CONTRACT) != DENSE_FIGURE_GROUP_RESCUE_CONTRACT:
        raise StageExecutionError("Unsupported dense figure group rescue contract")
    if str(effective.get("dense_figure_label_group_selector_contract") or DENSE_FIGURE_GROUP_SELECTOR_CONTRACT) != DENSE_FIGURE_GROUP_SELECTOR_CONTRACT:
        raise StageExecutionError("Unsupported dense figure group selector contract")
    if str(effective.get("dense_figure_label_group_trigger_contract") or DENSE_FIGURE_GROUP_TRIGGER_CONTRACT) != DENSE_FIGURE_GROUP_TRIGGER_CONTRACT:
        raise StageExecutionError("Unsupported dense figure group trigger contract")
    if effective.get("dense_figure_label_group_rescue_phase") not in {
        None,
        DENSE_FIGURE_GROUP_SELECTED_PHASE,
    }:
        raise StageExecutionError("dense_figure_label_group_rescue_phase is internal")

    effective.update(
        {
            "enable_dense_figure_label_group_rescue": True,
            "dense_figure_label_group_rescue_contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
            "dense_figure_label_group_selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
            "dense_figure_label_group_trigger_contract": DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
            "dense_figure_label_group_rescue_phase": DENSE_FIGURE_GROUP_SELECTED_PHASE,
            "dense_figure_label_group_max_nlp_tokens": cap,
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
        base_rows = get_run_items(connection, base_run_id, kind="translation_segment")
        context_rows = get_run_items(connection, int(context_run_id), kind="context_sentence")
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
        attempts = _eligible_groups(
            content=content,
            base_rows=base_rows,
            context_rows=context_rows,
            max_nlp_tokens=cap,
        )
        generated: list[list[dict[str, Any]]] = []
        if attempts:
            translator = OpusTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(
                [str(attempt["group"]["source"]) for attempt in attempts],
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(len(h) != 1 for h in generated):
                raise StageExecutionError("dense figure group OPUS rank0 cardinality drift")

        accepted: dict[tuple[int, int], dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            hypothesis = hypotheses[0]
            if int(hypothesis.get("rank") or 0) != 0:
                raise StageExecutionError("dense figure group OPUS result is not rank0")
            source = str(attempt["group"]["source"])
            primary_target = "".join(
                str(row.get("target_text") or "") for row in attempt["primary_rows"]
            )
            target = str(hypothesis.get("text") or "")
            selection = evaluate_dense_figure_group_candidate(
                source,
                target,
                primary_target=primary_target,
            )
            key = tuple(attempt["planner_group"])
            if selection["accepted"] is not True:
                rejected.append(
                    {
                        "planner_group": [int(key[0]), int(key[1])],
                        "source_start": int(attempt["group"]["start"]),
                        "reason": "rank0_selector_rejected",
                        "rank0_target": target,
                        "rank0_score": hypothesis.get("score"),
                        "selection": selection,
                    }
                )
                continue
            accepted[key] = {
                "planner_group": key,
                "row": _replacement_row(
                    attempt=attempt,
                    target=target,
                    hypothesis=hypothesis,
                    selection=selection,
                    base_run_id=base_run_id,
                ),
                "selected_rank": 0,
                "target_text": target,
                "member_ids": {int(row["id"]) for row in attempt["primary_rows"]},
            }

        removed_ids = {
            row_id for value in accepted.values() for row_id in value["member_ids"]
        }
        final_rows = [
            _copy_base_row(row)
            for row in sorted(base_rows, key=lambda value: int(value["source_start"]))
            if int(row["id"]) not in removed_ids
        ]
        final_rows.extend(dict(value["row"]) for value in accepted.values())
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError("dense figure group rescue source coverage is not byte-exact")
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(len(str(row.get("source_text") or "")) for row in base_rows)
        if source_sum != base_source_sum:
            raise StageExecutionError("dense figure group rescue changed source coverage")

        accepted_values = sorted(
            accepted.values(), key=lambda value: int(value["row"]["source_start"])
        )
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "dense_figure_label_group_rescue_contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
            "dense_figure_label_group_selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
            "dense_figure_label_group_trigger_contract": DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
            "dense_figure_label_group_rescue_enabled": True,
            "dense_figure_label_group_max_nlp_tokens": cap,
            "dense_figure_label_group_min_technical_label_occurrences": MIN_TECHNICAL_LABEL_OCCURRENCES,
            "dense_figure_label_group_min_distinct_technical_labels": MIN_DISTINCT_TECHNICAL_LABELS,
            "dense_figure_label_group_rescue_attempt_count": len(attempts),
            "dense_figure_label_group_rescue_accepted_count": len(accepted_values),
            "dense_figure_label_group_rescue_rejected_count": len(rejected),
            "dense_figure_label_group_rescue_attempted_groups": [
                [int(attempt["planner_group"][0]), int(attempt["planner_group"][1])]
                for attempt in attempts
            ],
            "dense_figure_label_group_rescue_accepted_groups": [
                [int(value["planner_group"][0]), int(value["planner_group"][1])]
                for value in accepted_values
            ],
            "dense_figure_label_group_rescue_selected_ranks": [0 for _ in accepted_values],
            "dense_figure_label_group_rescue_selected_targets": [
                str(value["target_text"]) for value in accepted_values
            ],
            "dense_figure_label_group_rescue_rejections": rejected,
            "dense_figure_label_group_rescue_model": "opus-en-ru-ct2",
            "dense_figure_label_group_rescue_model_request_count": len(attempts),
            "dense_figure_label_group_rescue_model_batch_count": 1 if attempts else 0,
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
