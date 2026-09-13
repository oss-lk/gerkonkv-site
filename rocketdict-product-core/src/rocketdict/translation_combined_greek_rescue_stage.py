from __future__ import annotations

"""Default-off source-planned rescue for lost combined Gutenberg Greek atoms.

A combined technical atom such as ``_A[Greek: a]_`` is classified from exact
immutable source before inference.  Its surrounding lexical spans are translated
with unmodified OPUS rank0; source-owned separators and the technical atom are
rendered from source bytes into one semantic carrier.  This follows the accepted
illustration/table structural-rendering precedent and never performs post-MT
literal injection or target repair.
"""

from pathlib import Path
import re
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .research_diagnostics import compare_critical_technical_tokens
from .runtime import OpusTranslator, opus_status
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_m2m100_arithmetic_rescue_stage import run_stage12 as run_base_stage12
from .translation_rescue import evaluate_rescue_pair

COMBINED_GREEK_RESCUE_CONTRACT = "rocketdict-stage12-combined-greek-source-plan-rescue/1"
COMBINED_GREEK_SELECTOR_CONTRACT = "rocketdict-stage12-combined-greek-source-plan-selector/1"
COMBINED_GREEK_TRIGGER_CONTRACT = "rocketdict-stage12-combined-greek-source-plan-trigger/1"
COMBINED_GREEK_SOURCE_PLAN_CONTRACT = "rocketdict-combined-greek-source-planned-technical-atom/1"
COMBINED_GREEK_SELECTED_PHASE = "combined-greek-source-plan-selected-v1"
DEFAULT_ENABLED = False
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 512
_COMBINED_SOURCE_RE = re.compile(r"_([A-Za-z]{1,3})\[Greek:\s*([^\]]+)\]_", re.IGNORECASE)
_COMBINED_TARGET_RE = re.compile(
    r"_([A-Za-z]{1,3})\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]+)\]_",
    re.IGNORECASE,
)
_WRAPPER_KEYS = frozenset(
    {
        "enable_combined_greek_source_plan_rescue",
        "combined_greek_source_plan_rescue_contract",
        "combined_greek_source_plan_selector_contract",
        "combined_greek_source_plan_trigger_contract",
        "combined_greek_source_plan_contract",
        "combined_greek_source_plan_rescue_phase",
    }
)
_RUNTIME_IDENTITY_KEYS = (
    "revision",
    "source_archive_sha256",
    "manifest_sha256",
    "payload_tree_sha256",
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


def _combined(regex: re.Pattern[str], text: str) -> list[list[str]]:
    return [[m.group(1), m.group(2).strip()] for m in regex.finditer(text)]


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def build_combined_greek_source_plan(source: str) -> dict[str, Any] | None:
    matches = list(_COMBINED_SOURCE_RE.finditer(source))
    if len(matches) != 1:
        return None
    match = matches[0]
    atom_start, atom_end = match.span()
    left = atom_start
    while left > 0 and source[left - 1] in " \t":
        left -= 1
    right = atom_end
    while right < len(source) and source[right] in " \t":
        right += 1
    prefix = source[:left]
    left_gap = source[left:atom_start]
    atom = source[atom_start:atom_end]
    right_gap = source[atom_end:right]
    suffix = source[right:]
    if not prefix.strip() or not suffix.strip() or not left_gap or not right_gap:
        return None
    if prefix + left_gap + atom + right_gap + suffix != source:
        raise ValueError("combined Greek source plan coverage drift")
    return {
        "contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
        "created_before_mt": True,
        "prefix_source": prefix,
        "left_separator_source": left_gap,
        "technical_atom_source": atom,
        "right_separator_source": right_gap,
        "suffix_source": suffix,
        "technical_symbol": match.group(1),
        "greek_payload": match.group(2).strip(),
        "source_owned_technical_passthrough": True,
    }


def evaluate_combined_greek_trigger(row: dict[str, Any], *, source_exact: bool) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    plan = build_combined_greek_source_plan(source)
    source_combined = _combined(_COMBINED_SOURCE_RE, source)
    target_combined = _combined(_COMBINED_TARGET_RE, target)
    base_verdict = evaluate_rescue_pair(source, target)
    base_critical = compare_critical_technical_tokens(source, target)
    combined_lost = bool(source_combined and source_combined != target_combined)
    eligible = bool(
        source_exact
        and plan is not None
        and combined_lost
        and base_verdict.get("product_hard_passed") is not True
        and base_critical.get("passed") is not True
    )
    return {
        "contract": COMBINED_GREEK_TRIGGER_CONTRACT,
        "eligible": eligible,
        "immutable_source_exact": source_exact,
        "source_combined": source_combined,
        "target_combined": target_combined,
        "combined_technical_atom_lost": combined_lost,
        "source_plan": plan,
        "base_verdict": base_verdict,
        "base_critical_technical_tokens": base_critical,
        "corpus_sequence_whitelist": False,
        "source_start_whitelist": False,
    }


def evaluate_combined_greek_candidate(
    source: str,
    *,
    base_target: str,
    plan: dict[str, Any],
    prefix_target: str,
    suffix_target: str,
) -> dict[str, Any]:
    if (
        str(plan.get("prefix_source") or "")
        + str(plan.get("left_separator_source") or "")
        + str(plan.get("technical_atom_source") or "")
        + str(plan.get("right_separator_source") or "")
        + str(plan.get("suffix_source") or "")
        != source
    ):
        raise ValueError("combined Greek candidate plan no longer covers source")
    prefix_source = str(plan["prefix_source"])
    suffix_source = str(plan["suffix_source"])
    prefix_verdict = evaluate_rescue_pair(prefix_source, prefix_target)
    suffix_verdict = evaluate_rescue_pair(suffix_source, suffix_target)
    prefix_emphasis = compare_emphasis_markup_preservation(prefix_source, prefix_target)
    suffix_emphasis = compare_emphasis_markup_preservation(suffix_source, suffix_target)
    candidate_target = (
        prefix_target
        + str(plan["left_separator_source"])
        + str(plan["technical_atom_source"])
        + str(plan["right_separator_source"])
        + suffix_target
    )
    aggregate = evaluate_rescue_pair(source, candidate_target)
    aggregate_emphasis = compare_emphasis_markup_preservation(source, candidate_target)
    aggregate_critical = compare_critical_technical_tokens(source, candidate_target)
    alpha_non_decreasing = _alpha(candidate_target) >= _alpha(base_target)
    accepted = bool(
        prefix_target.strip()
        and suffix_target.strip()
        and prefix_verdict.get("strictly_eligible") is True
        and suffix_verdict.get("strictly_eligible") is True
        and prefix_emphasis.get("passed") is True
        and suffix_emphasis.get("passed") is True
        and aggregate.get("strictly_eligible") is True
        and aggregate_emphasis.get("passed") is True
        and aggregate_critical.get("passed") is True
        and alpha_non_decreasing
    )
    return {
        "selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
        "accepted": accepted,
        "candidate_target": candidate_target,
        "prefix_verdict": prefix_verdict,
        "suffix_verdict": suffix_verdict,
        "prefix_emphasis": prefix_emphasis,
        "suffix_emphasis": suffix_emphasis,
        "aggregate_verdict": aggregate,
        "aggregate_emphasis_markup": aggregate_emphasis,
        "aggregate_critical_technical_tokens": aggregate_critical,
        "base_target_alpha_count": _alpha(base_target),
        "candidate_target_alpha_count": _alpha(candidate_target),
        "target_alpha_non_decreasing": alpha_non_decreasing,
        "source_plan_created_before_mt": True,
        "source_owned_technical_passthrough": True,
    }


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
    payload["combined_greek_source_plan_rescue"] = {
        "contract": COMBINED_GREEK_RESCUE_CONTRACT,
        "selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
        "trigger_contract": COMBINED_GREEK_TRIGGER_CONTRACT,
        "source_plan_contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
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
    output: list[dict[str, Any]] = []
    for row in sorted(base_rows, key=lambda value: int(value["source_start"])):
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        source_exact = bool(0 <= start < end <= len(content) and content[start:end] == source)
        trigger = evaluate_combined_greek_trigger(row, source_exact=source_exact)
        if trigger["eligible"] is True:
            output.append({"row": row, "trigger": trigger})
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
    enabled = _bool_parameter(effective.get("enable_combined_greek_source_plan_rescue"), name="enable_combined_greek_source_plan_rescue", default=DEFAULT_ENABLED)
    if not enabled:
        return run_base_stage12(database, context_run_id=int(context_run_id), parameters=_base_parameters(effective), implementation=implementation)

    requested_contract = str(effective.get("combined_greek_source_plan_rescue_contract") or COMBINED_GREEK_RESCUE_CONTRACT)
    requested_selector = str(effective.get("combined_greek_source_plan_selector_contract") or COMBINED_GREEK_SELECTOR_CONTRACT)
    requested_trigger = str(effective.get("combined_greek_source_plan_trigger_contract") or COMBINED_GREEK_TRIGGER_CONTRACT)
    requested_plan = str(effective.get("combined_greek_source_plan_contract") or COMBINED_GREEK_SOURCE_PLAN_CONTRACT)
    if requested_contract != COMBINED_GREEK_RESCUE_CONTRACT:
        raise StageExecutionError(f"Unsupported combined Greek rescue contract {requested_contract!r}")
    if requested_selector != COMBINED_GREEK_SELECTOR_CONTRACT:
        raise StageExecutionError(f"Unsupported combined Greek selector {requested_selector!r}")
    if requested_trigger != COMBINED_GREEK_TRIGGER_CONTRACT:
        raise StageExecutionError(f"Unsupported combined Greek trigger {requested_trigger!r}")
    if requested_plan != COMBINED_GREEK_SOURCE_PLAN_CONTRACT:
        raise StageExecutionError(f"Unsupported combined Greek source plan {requested_plan!r}")
    if effective.get("combined_greek_source_plan_rescue_phase") not in {None, COMBINED_GREEK_SELECTED_PHASE}:
        raise StageExecutionError("combined_greek_source_plan_rescue_phase is internal and may not be overridden")

    effective.update({
        "enable_combined_greek_source_plan_rescue": True,
        "combined_greek_source_plan_rescue_contract": COMBINED_GREEK_RESCUE_CONTRACT,
        "combined_greek_source_plan_selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
        "combined_greek_source_plan_trigger_contract": COMBINED_GREEK_TRIGGER_CONTRACT,
        "combined_greek_source_plan_contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
        "combined_greek_source_plan_rescue_phase": COMBINED_GREEK_SELECTED_PHASE,
    })

    base_output = run_base_stage12(database, context_run_id=int(context_run_id), parameters=_base_parameters(effective), implementation=implementation)
    base_run_id = int(base_output["translation_run_id"])
    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, base_run_id)
        base_rows = get_run_items(connection, base_run_id, kind="translation_segment")
        stored_output = dict(base_run.get("output") or {})
        document = get_document(connection, int(stored_output["document_version_id"]))
    content = str(document["content_text"])
    attempts = _eligible_rows(content=content, base_rows=base_rows)
    status: dict[str, Any] | None = None
    if attempts:
        status = opus_status()
        if status.get("available") is not True:
            raise StageExecutionError(f"combined Greek rescue OPUS runtime unavailable: {status}")

    identity = {
        "context_run_id": int(context_run_id),
        "document_version_id": int(stored_output["document_version_id"]),
        "source_text_sha256": str(document["text_sha256"]),
        "base_translation_run_id": base_run_id,
        "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
        "combined_greek_opus_runtime_identity": _runtime_identity(status),
    }
    run_id, cached = _start(database, stage_number=12, implementation=implementation, input_identity=identity, parameters=effective)
    if cached is not None:
        return cached

    try:
        generated: list[list[dict[str, Any]]] = []
        if attempts:
            model_inputs: list[str] = []
            for attempt in attempts:
                plan = dict(attempt["trigger"]["source_plan"])
                model_inputs.extend([str(plan["prefix_source"]), str(plan["suffix_source"])])
            translator = OpusTranslator(device="cpu", compute_type="float32")
            generated = translator.translate(model_inputs, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
            if len(generated) != len(model_inputs) or any(len(group) != 1 for group in generated):
                raise StageExecutionError("combined Greek raw rank0 cardinality drift")

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        cursor = 0
        for attempt in attempts:
            row = attempt["row"]
            trigger = dict(attempt["trigger"])
            plan = dict(trigger["source_plan"])
            prefix_h = dict(generated[cursor][0]); suffix_h = dict(generated[cursor + 1][0]); cursor += 2
            if int(prefix_h.get("rank", -1)) != 0 or int(suffix_h.get("rank", -1)) != 0:
                raise StageExecutionError("combined Greek rescue permits raw rank0 only")
            prefix_target = str(prefix_h.get("text") or "")
            suffix_target = str(suffix_h.get("text") or "")
            selection = evaluate_combined_greek_candidate(
                str(row.get("source_text") or ""),
                base_target=str(row.get("target_text") or ""),
                plan=plan,
                prefix_target=prefix_target,
                suffix_target=suffix_target,
            )
            if selection["accepted"] is not True:
                rejected.append({
                    "source_start": int(row["source_start"]),
                    "reason": "rank0_selector_rejected",
                    "prefix_rank0": prefix_h,
                    "suffix_rank0": suffix_h,
                    "trigger": trigger,
                    "selection": selection,
                    "runtime_identity": _runtime_identity(status),
                })
                continue

            payload = dict(row.get("payload") or {})
            pieces = [
                {"role": "prefix", "kind": "translate", "source_text": plan["prefix_source"], "model_input": plan["prefix_source"], "selected_rank": 0, "selected_target": prefix_target, "hypothesis": prefix_h},
                {"role": "left_separator", "kind": "preserve_source_structure", "source_text": plan["left_separator_source"], "rendered_text": plan["left_separator_source"], "source_owned": True},
                {"role": "technical_atom", "kind": "preserve_source_structure", "source_text": plan["technical_atom_source"], "rendered_text": plan["technical_atom_source"], "source_owned": True},
                {"role": "right_separator", "kind": "preserve_source_structure", "source_text": plan["right_separator_source"], "rendered_text": plan["right_separator_source"], "source_owned": True},
                {"role": "suffix", "kind": "translate", "source_text": plan["suffix_source"], "model_input": plan["suffix_source"], "selected_rank": 0, "selected_target": suffix_target, "hypothesis": suffix_h},
            ]
            payload["combined_greek_source_plan_rescue"] = {
                "contract": COMBINED_GREEK_RESCUE_CONTRACT,
                "selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
                "trigger_contract": COMBINED_GREEK_TRIGGER_CONTRACT,
                "source_plan_contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
                "applied": True,
                "rendering": "source_planned_semantic_carrier",
                "base_translation_run_id": base_run_id,
                "base_translation_segment_id": int(row["id"]),
                "base_target": str(row.get("target_text") or ""),
                "trigger": trigger,
                "selection": selection,
                "source_plan": {"contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT, "created_before_mt": True, "pieces": pieces},
                "generation": {"beam_size": BEAM_SIZE, "num_hypotheses": NUM_HYPOTHESES, "max_decoding_length": MAX_DECODING_LENGTH, "selected_rank": 0},
                "runtime_identity": _runtime_identity(status),
                **_safety_flags(),
            }
            payload["selected_rank"] = 0
            accepted[int(row["id"])] = {
                "source_start": int(row["source_start"]),
                "target_text": str(selection["candidate_target"]),
                "payload": payload,
            }

        final_rows: list[dict[str, Any]] = []
        for row in sorted(base_rows, key=lambda value: int(value["source_start"])):
            replacement = accepted.get(int(row["id"]))
            if replacement is None:
                final_rows.append(_copy_base_row(row))
            else:
                final_rows.append({
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": int(row["source_start"]),
                    "source_end": int(row["source_end"]),
                    "source_text": str(row.get("source_text") or ""),
                    "target_text": str(replacement["target_text"]),
                    "payload": replacement["payload"],
                })
        final_rows.sort(key=lambda value: int(value["source_start"]))
        for sequence, row in enumerate(final_rows):
            row["sequence_number"] = sequence
        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError("combined Greek final source coverage is not byte-exact")

        accepted_values = sorted(accepted.values(), key=lambda value: int(value["source_start"]))
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "combined_greek_source_plan_rescue_contract": COMBINED_GREEK_RESCUE_CONTRACT,
            "combined_greek_source_plan_selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
            "combined_greek_source_plan_trigger_contract": COMBINED_GREEK_TRIGGER_CONTRACT,
            "combined_greek_source_plan_contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
            "combined_greek_source_plan_rescue_enabled": True,
            "combined_greek_source_plan_rescue_attempt_count": len(attempts),
            "combined_greek_source_plan_rescue_accepted_count": len(accepted_values),
            "combined_greek_source_plan_rescue_rejected_count": len(rejected),
            "combined_greek_source_plan_rescue_attempted_source_starts": [int(a["row"]["source_start"]) for a in attempts],
            "combined_greek_source_plan_rescue_accepted_source_starts": [int(v["source_start"]) for v in accepted_values],
            "combined_greek_source_plan_rescue_rejected": rejected,
            "combined_greek_source_plan_rescue_model_request_count": len(attempts) * 2,
            "combined_greek_source_plan_rescue_runtime": status,
            "base_segment_count": len(base_rows),
            "segment_count": len(final_rows),
            "source_character_sum": sum(len(str(row["source_text"])) for row in final_rows),
            "model_request_count": int(base_output.get("model_request_count") or 0) + len(attempts) * 2,
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
