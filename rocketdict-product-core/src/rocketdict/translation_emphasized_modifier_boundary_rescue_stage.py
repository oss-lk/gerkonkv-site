from __future__ import annotations

"""Default-off OPUS rescue for numeric loss across emphasized modifier boundaries.

Stage10 V1 intentionally remains the Product default, but full-corpus evidence
shows a narrow repeated parser-boundary family where a single-word Gutenberg
emphasis modifier is detached from the capitalized noun that follows it, for
example ``_English_ | Miles``.  This wrapper does not alter Stage10.  It scans
the immutable Stage10 context stream for that source-defined boundary shape,
coalesces consecutive matches into maximal groups, and considers only groups
whose current Stage12 output already contains exactly one numeric/symbol hard
failure and no unrelated Product hard failure.

Only unmodified pinned-OPUS rank0 output can replace such a group.  Acceptance
is fail-closed: all Product hard/research checks, Gutenberg emphasis, source-
relative output volume, base-output content retention, and terminal punctuation
must pass.  The mechanism remains disabled by default and is not public-wired.
"""

from pathlib import Path
import re
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .numeric_integrity import evaluate_numeric_symbol_pair
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import evaluate_rescue_pair
from .translation_tc_big_fraction_context_rescue_stage import run_stage12 as run_base_stage12

EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT = (
    "rocketdict-stage12-emphasized-modifier-boundary-numeric-rescue/1"
)
EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT = (
    "rocketdict-stage12-emphasized-modifier-boundary-numeric-selector/1"
)
EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT = (
    "rocketdict-stage12-emphasized-modifier-boundary-numeric-trigger/1"
)
EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT = (
    "rocketdict-stage10-emphasized-single-word-modifier-boundary-census/1"
)
EMPHASIZED_MODIFIER_BOUNDARY_SELECTED_PHASE = (
    "emphasized-modifier-boundary-numeric-selected-v1"
)

DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1536
MAX_GROUP_NLP_TOKENS = 160
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.55
MIN_BASE_ALPHA_RETENTION_RATIO = 0.95

_EMPHASIZED_SINGLE_WORD_RE = re.compile(
    r"_([A-Za-z][A-Za-z-]{0,30})_([ \t\r\n]*)\Z"
)
_CAPITALIZED_LEXICAL_RE = re.compile(r"\s*([A-Z][A-Za-z-]*)")
_WRAPPER_KEYS = frozenset(
    {
        "enable_emphasized_modifier_boundary_rescue",
        "emphasized_modifier_boundary_rescue_contract",
        "emphasized_modifier_boundary_selector_contract",
        "emphasized_modifier_boundary_trigger_contract",
        "emphasized_modifier_boundary_source_contract",
        "emphasized_modifier_boundary_rescue_phase",
        "emphasized_modifier_boundary_max_nlp_tokens",
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


def evaluate_emphasized_modifier_boundary(
    left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    """Classify one immutable Stage10 boundary without corpus-specific text."""

    contiguous = int(left["source_end"]) == int(right["source_start"])
    left_source = str(left.get("source_text") or "")
    right_source = str(right.get("source_text") or "")
    emphasized = _EMPHASIZED_SINGLE_WORD_RE.search(left_source)
    trailing = "" if emphasized is None else emphasized.group(2).replace("\r", "")
    right_match = _CAPITALIZED_LEXICAL_RE.match(right_source)
    no_paragraph_break = "\n\n" not in trailing
    eligible = bool(
        contiguous
        and emphasized is not None
        and no_paragraph_break
        and right_match is not None
    )
    return {
        "contract": EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT,
        "eligible": eligible,
        "contiguous": contiguous,
        "emphasized_single_word": (
            emphasized.group(1) if emphasized is not None else None
        ),
        "trailing_whitespace": trailing,
        "no_paragraph_break": no_paragraph_break,
        "right_lexical_start": (
            right_match.group(1) if right_match is not None else None
        ),
        "left_context_sequence": int(left["sequence_number"]),
        "right_context_sequence": int(right["sequence_number"]),
        "boundary_offset": int(left["source_end"]),
    }


def discover_emphasized_modifier_groups(
    context_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return maximal connected Stage10 groups for the source boundary family."""

    ordered = sorted(context_rows, key=lambda row: int(row["sequence_number"]))
    boundaries: list[dict[str, Any]] = []
    for left, right in zip(ordered, ordered[1:], strict=False):
        verdict = evaluate_emphasized_modifier_boundary(left, right)
        if verdict["eligible"] is True:
            boundaries.append(verdict)

    boundary_by_left = {
        int(row["left_context_sequence"]): row for row in boundaries
    }
    predecessor = {
        int(row["right_context_sequence"]) for row in boundaries
    }
    groups: list[dict[str, Any]] = []
    for boundary in boundaries:
        first = int(boundary["left_context_sequence"])
        if first in predecessor:
            continue
        sequences = [first]
        group_boundaries: list[dict[str, Any]] = []
        cursor = first
        while cursor in boundary_by_left:
            edge = boundary_by_left[cursor]
            right = int(edge["right_context_sequence"])
            sequences.append(right)
            group_boundaries.append(edge)
            cursor = right
        groups.append(
            {
                "context_sequences": sequences,
                "boundaries": group_boundaries,
            }
        )
    return groups


def evaluate_emphasized_modifier_group_trigger(
    rows: list[dict[str, Any]],
    *,
    boundaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Require exactly one numeric hard-failure member and clean siblings."""

    ordered = sorted(rows, key=lambda row: int(row["source_start"]))
    hard_failures: list[int] = []
    numeric_failures: list[int] = []
    sibling_strict = True
    member_evidence: list[dict[str, Any]] = []

    for index, row in enumerate(ordered):
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        numeric = evaluate_numeric_symbol_pair(source, target)
        emphasis = compare_emphasis_markup_preservation(source, target)
        hard_failed = verdict.get("product_hard_passed") is not True
        numeric_failed = numeric.get("passed") is not True
        if hard_failed:
            hard_failures.append(index)
        if numeric_failed:
            numeric_failures.append(index)
        member_evidence.append(
            {
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "product_hard_failed": hard_failed,
                "numeric_symbol_failed": numeric_failed,
                "strictly_eligible": verdict.get("strictly_eligible") is True,
                "emphasis_preserved": emphasis.get("passed") is True,
            }
        )

    numeric_failure_set = set(numeric_failures)
    for index, evidence in enumerate(member_evidence):
        if index in numeric_failure_set:
            continue
        if (
            evidence["strictly_eligible"] is not True
            or evidence["emphasis_preserved"] is not True
        ):
            sibling_strict = False
            break

    eligible = bool(
        boundaries
        and len(ordered) >= 2
        and len(numeric_failures) == 1
        and hard_failures == numeric_failures
        and sibling_strict
    )
    return {
        "contract": EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT,
        "eligible": eligible,
        "member_count": len(ordered),
        "boundary_count": len(boundaries),
        "hard_failure_member_indices": hard_failures,
        "numeric_failure_member_indices": numeric_failures,
        "other_members_strict": sibling_strict,
        "member_evidence": member_evidence,
    }


def evaluate_emphasized_modifier_candidate(
    source: str,
    target: str,
    *,
    base_target: str,
) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    source_ratio = target_alpha / source_alpha if source_alpha else 1.0
    base_retention = target_alpha / base_alpha if base_alpha else 1.0
    source_terminal = source.rstrip()[-1:] if source.rstrip() else ""
    target_terminal = target.rstrip()[-1:] if target.rstrip() else ""
    terminal_required = source_terminal if source_terminal in ".?!" else None
    terminal_preserved = (
        terminal_required is None or target_terminal == terminal_required
    )
    accepted = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and MIN_SOURCE_ALPHA_RATIO <= source_ratio <= MAX_SOURCE_ALPHA_RATIO
        and base_retention >= MIN_BASE_ALPHA_RETENTION_RATIO
        and terminal_preserved
    )
    return {
        "selector_contract": EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT,
        "accepted": accepted,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": source_ratio,
        "source_alpha_ratio_range": [
            MIN_SOURCE_ALPHA_RATIO,
            MAX_SOURCE_ALPHA_RATIO,
        ],
        "base_alpha_retention_ratio": base_retention,
        "base_alpha_retention_minimum": MIN_BASE_ALPHA_RETENTION_RATIO,
        "terminal_punctuation_required": terminal_required,
        "target_terminal_punctuation": target_terminal,
        "terminal_punctuation_preserved": terminal_preserved,
    }


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
    payload["emphasized_modifier_boundary_rescue"] = {
        "contract": EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT,
        "selector_contract": EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT,
        "trigger_contract": EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT,
        "source_contract": EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT,
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
        raise StageExecutionError(
            f"Unsupported real MT implementation: {implementation}"
        )
    database = Path(database).expanduser().resolve()
    effective = dict(parameters or {})
    enabled = _bool_parameter(
        effective.get("enable_emphasized_modifier_boundary_rescue"),
        name="enable_emphasized_modifier_boundary_rescue",
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
        effective.get("emphasized_modifier_boundary_rescue_contract")
        or EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("emphasized_modifier_boundary_selector_contract")
        or EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT
    )
    requested_trigger = str(
        effective.get("emphasized_modifier_boundary_trigger_contract")
        or EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT
    )
    requested_source = str(
        effective.get("emphasized_modifier_boundary_source_contract")
        or EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT
    )
    max_tokens = _positive_int_parameter(
        effective.get("emphasized_modifier_boundary_max_nlp_tokens"),
        name="emphasized_modifier_boundary_max_nlp_tokens",
        default=MAX_GROUP_NLP_TOKENS,
    )
    if max_tokens > MAX_GROUP_NLP_TOKENS:
        raise StageExecutionError(
            "emphasized_modifier_boundary_max_nlp_tokens may not exceed "
            f"{MAX_GROUP_NLP_TOKENS}"
        )
    if requested_contract != EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported emphasized-modifier rescue contract {requested_contract!r}"
        )
    if requested_selector != EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported emphasized-modifier selector {requested_selector!r}"
        )
    if requested_trigger != EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT:
        raise StageExecutionError(
            f"Unsupported emphasized-modifier trigger {requested_trigger!r}"
        )
    if requested_source != EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported emphasized-modifier source contract {requested_source!r}"
        )
    if effective.get("emphasized_modifier_boundary_rescue_phase") not in {
        None,
        EMPHASIZED_MODIFIER_BOUNDARY_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "emphasized_modifier_boundary_rescue_phase is internal and may not be overridden"
        )

    effective.update(
        {
            "enable_emphasized_modifier_boundary_rescue": True,
            "emphasized_modifier_boundary_rescue_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT
            ),
            "emphasized_modifier_boundary_selector_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT
            ),
            "emphasized_modifier_boundary_trigger_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT
            ),
            "emphasized_modifier_boundary_source_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT
            ),
            "emphasized_modifier_boundary_rescue_phase": (
                EMPHASIZED_MODIFIER_BOUNDARY_SELECTED_PHASE
            ),
            "emphasized_modifier_boundary_max_nlp_tokens": max_tokens,
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
        context_run = get_run(connection, int(context_run_id))
        context_rows = get_run_items(
            connection, int(context_run_id), kind="context_sentence"
        )
        stored_output = dict(base_run.get("output") or {})
        document = get_document(
            connection, int(stored_output["document_version_id"])
        )

    input_identity = {
        "context_run_id": int(context_run_id),
        "context_output_sha256": str(context_run.get("output_sha256") or ""),
        "document_version_id": int(stored_output["document_version_id"]),
        "source_text_sha256": str(document["text_sha256"]),
        "base_translation_run_id": base_run_id,
        "base_translation_output_sha256": str(
            base_run.get("output_sha256") or ""
        ),
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
        contexts = {
            int(row["sequence_number"]): row for row in context_rows
        }
        groups = discover_emphasized_modifier_groups(context_rows)

        attempts: list[dict[str, Any]] = []
        skipped_over_cap: list[list[int]] = []
        for group in groups:
            sequences = list(group["context_sequences"])
            selected_contexts = [contexts[sequence] for sequence in sequences]
            start = int(selected_contexts[0]["source_start"])
            end = int(selected_contexts[-1]["source_end"])
            source = "".join(
                str(row.get("source_text") or "") for row in selected_contexts
            )
            if source != content[start:end]:
                raise StageExecutionError(
                    f"emphasized-modifier group source drift for {sequences!r}"
                )
            members = sorted(
                [
                    row
                    for row in base_rows
                    if start <= int(row["source_start"])
                    and int(row["source_end"]) <= end
                ],
                key=lambda row: int(row["source_start"]),
            )
            if (
                not members
                or int(members[0]["source_start"]) != start
                or int(members[-1]["source_end"]) != end
                or "".join(
                    str(row.get("source_text") or "") for row in members
                )
                != source
            ):
                continue

            trigger = evaluate_emphasized_modifier_group_trigger(
                members,
                boundaries=list(group["boundaries"]),
            )
            if trigger["eligible"] is not True:
                continue
            token_count = sum(
                int((row.get("payload") or {}).get("token_count") or 0)
                for row in selected_contexts
            )
            if token_count <= 0:
                raise StageExecutionError(
                    f"emphasized-modifier group {sequences!r} has no token count"
                )
            if token_count > max_tokens:
                skipped_over_cap.append(sequences)
                continue
            attempts.append(
                {
                    "context_sequences": sequences,
                    "boundaries": list(group["boundaries"]),
                    "rows": members,
                    "trigger": trigger,
                    "source": source,
                    "start": start,
                    "end": end,
                    "token_count": token_count,
                    "base_target": "".join(
                        str(row.get("target_text") or "") for row in members
                    ),
                }
            )

        generated: list[list[dict[str, Any]]] = []
        if attempts:
            translator = OpusTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(
                [str(attempt["source"]) for attempt in attempts],
                beam_size=BEAM_SIZE,
                num_hypotheses=NUM_HYPOTHESES,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            if len(generated) != len(attempts) or any(
                len(rows) != NUM_HYPOTHESES for rows in generated
            ):
                raise StageExecutionError(
                    "emphasized-modifier OPUS rank0 cardinality drift"
                )

        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            hypothesis = hypotheses[0]
            if int(hypothesis.get("rank") or 0) != 0:
                raise StageExecutionError(
                    "emphasized-modifier candidate is not rank0"
                )
            target = str(hypothesis.get("text") or "")
            selection = evaluate_emphasized_modifier_candidate(
                str(attempt["source"]),
                target,
                base_target=str(attempt["base_target"]),
            )
            evidence = {
                **attempt,
                "target_text": target,
                "hypotheses": hypotheses,
                "selection": selection,
            }
            if selection["accepted"] is True:
                accepted.append(evidence)
            else:
                rejected.append(
                    {
                        "context_sequences": list(
                            attempt["context_sequences"]
                        ),
                        "reason": "rank0_selector_rejected",
                        "selection": selection,
                        "target_text": target,
                    }
                )

        accepted_member_ids: dict[int, dict[str, Any]] = {}
        for attempt in accepted:
            for row in attempt["rows"]:
                accepted_member_ids[int(row["id"])] = attempt

        final_rows: list[dict[str, Any]] = []
        emitted_group_starts: set[int] = set()
        for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
            accepted_attempt = accepted_member_ids.get(int(row["id"]))
            if accepted_attempt is None:
                final_rows.append(_copy_base_row(row))
                continue
            group_start = int(accepted_attempt["start"])
            if group_start in emitted_group_starts:
                continue
            emitted_group_starts.add(group_start)
            sequences = list(accepted_attempt["context_sequences"])
            payload = {
                "planner": {
                    "source": "nlp_sentence_group",
                    "context_sentence_start": sequences[0],
                    "context_sentence_end": sequences[-1],
                    "context_sentence_count": len(sequences),
                    "split": False,
                    "token_count": int(accepted_attempt["token_count"]),
                    "rescue_strategy": "emphasized_modifier_boundary_numeric",
                },
                "hypotheses": list(accepted_attempt["hypotheses"]),
                "selected_rank": 0,
                "emphasized_modifier_boundary_rescue": {
                    "contract": EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT,
                    "selector_contract": (
                        EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT
                    ),
                    "trigger_contract": (
                        EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT
                    ),
                    "source_contract": (
                        EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT
                    ),
                    "applied": True,
                    "context_sequences": sequences,
                    "boundaries": list(accepted_attempt["boundaries"]),
                    "trigger": dict(accepted_attempt["trigger"]),
                    "selection": dict(accepted_attempt["selection"]),
                    "base_translation_run_id": base_run_id,
                    "base_translation_segment_ids": [
                        int(item["id"]) for item in accepted_attempt["rows"]
                    ],
                    "raw_model_selected": True,
                    "raw_model_rank": 0,
                    "generation": {
                        "beam_size": BEAM_SIZE,
                        "num_hypotheses": NUM_HYPOTHESES,
                        "max_decoding_length": MAX_DECODING_LENGTH,
                    },
                    **_safety_flags(),
                },
            }
            final_rows.append(
                {
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": int(accepted_attempt["start"]),
                    "source_end": int(accepted_attempt["end"]),
                    "source_text": str(accepted_attempt["source"]),
                    "target_text": str(accepted_attempt["target_text"]),
                    "payload": payload,
                }
            )

        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError(
                "emphasized-modifier rescue final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(
            len(str(row.get("source_text") or "")) for row in base_rows
        )
        if source_sum != base_source_sum:
            raise StageExecutionError(
                "emphasized-modifier rescue changed source character coverage"
            )

        accepted_groups = [
            list(row["context_sequences"]) for row in accepted
        ]
        rejected_groups = [
            list(row["context_sequences"]) for row in rejected
        ]
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(
                base_run.get("output_sha256") or ""
            ),
            "emphasized_modifier_boundary_rescue_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT
            ),
            "emphasized_modifier_boundary_selector_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT
            ),
            "emphasized_modifier_boundary_trigger_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT
            ),
            "emphasized_modifier_boundary_source_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT
            ),
            "emphasized_modifier_boundary_rescue_enabled": True,
            "emphasized_modifier_boundary_discovered_group_count": len(groups),
            "emphasized_modifier_boundary_attempt_count": len(attempts),
            "emphasized_modifier_boundary_accepted_count": len(accepted),
            "emphasized_modifier_boundary_rejected_count": len(rejected),
            "emphasized_modifier_boundary_skipped_over_cap_count": len(
                skipped_over_cap
            ),
            "emphasized_modifier_boundary_attempted_context_groups": [
                list(row["context_sequences"]) for row in attempts
            ],
            "emphasized_modifier_boundary_accepted_context_groups": (
                accepted_groups
            ),
            "emphasized_modifier_boundary_rejected_context_groups": (
                rejected_groups
            ),
            "emphasized_modifier_boundary_skipped_over_cap_context_groups": (
                skipped_over_cap
            ),
            "emphasized_modifier_boundary_selected_ranks": [
                0 for _ in accepted
            ],
            "emphasized_modifier_boundary_selected_targets": [
                str(row["target_text"]) for row in accepted
            ],
            "base_segment_count": len(base_rows),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "model_request_count": int(
                base_output.get("model_request_count") or 0
            )
            + len(attempts),
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
