from __future__ import annotations

"""Default-off Stage12 rescue for Gutenberg illustration-label failures.

Two source-defined paths are supported and both are planned from immutable source
before any MT call:

* the previously accepted ordinary-suffix path keeps the exact ``[Illustration:
  ...]`` plus blank-line prefix as source-owned structure and sends only the
  exact linguistic remainder to pinned OPUS rank0; and
* the dedicated structural-word path recognizes only a complete
  ``[Illustration: FIG. N.]`` + blank-line + ``_Illustration._`` source shape,
  translates the exact label with OPUS rank0, preserves the exact source-owned
  blank-line separator, translates the exact emphasized suffix with pinned
  TC-big rank0, and preserves exact trailing source whitespace.

The structural pieces are discovered before inference.  Composition therefore
mirrors the accepted Stage12 table renderer: source-owned structural spans are
rendered from their immutable source bytes while lexical spans use unmodified raw
rank0 model output.  No source rewriting, target surgery, post-MT literal
injection, placeholders, corpus-specific target patches, evaluator weakening, or
automatic n-best selection is permitted.
"""

from pathlib import Path
import re
from typing import Any

from .alternative_mt_runtime import TcBigTranslator, tc_big_status
from .database import connect, get_document, get_run, get_run_items
from .emphasis_markup import compare_emphasis_markup_preservation
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_numeric_hard_rescue_stage import run_stage12 as run_base_stage12
from .translation_rescue import evaluate_rescue_pair
from .translation_rank0 import select_rank0_evaluation
from . import translation_stage as primary_stage

ILLUSTRATION_LABEL_RESCUE_CONTRACT = "rocketdict-stage12-illustration-label-rescue/4"
ILLUSTRATION_LABEL_SELECTOR_CONTRACT = "rocketdict-stage12-illustration-label-selector/4"
ILLUSTRATION_LABEL_TRIGGER_CONTRACT = "rocketdict-stage12-illustration-label-hard-failure-trigger/2"
ILLUSTRATION_SOURCE_PLAN_CONTRACT = "rocketdict-illustration-source-planned-structural-pieces/1"
ILLUSTRATION_WORD_TARGET_FORM_CONTRACT = "rocketdict-stage12-illustration-word-target-form/2"
ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT = "rocketdict-stage12-illustration-label-target-form/1"
ILLUSTRATION_LABEL_SELECTED_PHASE = "illustration-label-selected-v4"
DEFAULT_ENABLED = False
ILLUSTRATION_WORD_SOURCE = "_Illustration._"
ILLUSTRATION_WORD_MODEL_INPUT = ILLUSTRATION_WORD_SOURCE
ILLUSTRATION_WORD_ACCEPTED_TERMS = ("иллюстрация", "рисунок")
STRUCTURAL_WORD_BEAM_SIZE = 6
STRUCTURAL_WORD_NUM_HYPOTHESES = 1
ORDINARY_SUFFIX_BEAM_SIZE = 6
ORDINARY_SUFFIX_NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 128

_PREFIX_RE = re.compile(
    r"\A(?P<label>\[Illustration:[^\]\r\n]+\])(?P<gap>\r?\n[ \t]*\r?\n)"
)
_STRUCTURAL_LABEL_RE = re.compile(
    r"\A\[Illustration:\s*FIG\.\s*(?P<number>\d+)\.\]\Z",
    re.IGNORECASE,
)
_STRUCTURAL_WORD_RE = re.compile(
    r"\A(?P<label>\[Illustration:\s*FIG\.\s*(?P<number>\d+)\.\])"
    r"(?P<separator>\r?\n[ \t]*\r?\n)"
    r"(?P<suffix>_Illustration\._)"
    r"(?P<trailing>[ \t]*)\Z",
    re.IGNORECASE,
)
_ILLUSTRATION_ONLY_KEYS = frozenset(
    {
        "enable_illustration_label_rescue",
        "illustration_label_rescue_contract",
        "illustration_label_rescue_selector_contract",
        "illustration_label_trigger_contract",
        "illustration_source_plan_contract",
        "illustration_word_target_form_contract",
        "illustration_label_target_form_contract",
        "illustration_label_rescue_phase",
    }
)


def _bool_parameter(value: Any, *, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise StageExecutionError(f"Stage12 {name} must be boolean")


def _base_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in parameters.items()
        if key not in _ILLUSTRATION_ONLY_KEYS
    }


def _split_prefix(source: str) -> tuple[str, str] | None:
    match = _PREFIX_RE.match(source)
    if match is None:
        return None
    structural = match.group("label") + match.group("gap")
    remainder = source[match.end():]
    if not remainder.strip():
        return None
    return structural, remainder


def _structural_word_plan(source: str) -> dict[str, Any] | None:
    match = _STRUCTURAL_WORD_RE.fullmatch(source)
    if match is None:
        return None
    label = match.group("label")
    separator = match.group("separator")
    suffix = match.group("suffix")
    trailing = match.group("trailing")
    if label + separator + suffix + trailing != source:
        raise ValueError("illustration source-plan coverage drift")
    if not separator or separator.strip() or separator.count("\n") < 2:
        raise ValueError("illustration source separator is not a blank-line structural span")
    return {
        "contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
        "candidate_kind": "source_planned_structural_illustration",
        "figure_number": str(match.group("number")),
        "label_source": label,
        "separator_source": separator,
        "suffix_source": suffix,
        "trailing_source": trailing,
        "source_plan_created_before_mt": True,
        "source_owned_structural_passthrough": True,
    }


def _model_input_for_remainder(remainder: str) -> tuple[str, bool, str]:
    candidate_kind = (
        "standalone_illustration_word"
        if remainder.strip() == ILLUSTRATION_WORD_SOURCE
        else "ordinary_linguistic_suffix"
    )
    return remainder, False, candidate_kind


def evaluate_illustration_word_target_shape(
    target: str, *, require_emphasis: bool = False
) -> dict[str, Any]:
    stripped = target.strip()
    emphasis_wrapped = bool(
        len(stripped) >= 2
        and stripped.startswith("_")
        and stripped.endswith("_")
        and stripped.count("_") == 2
    )
    semantic_text = stripped[1:-1] if emphasis_wrapped else stripped
    canonical = semantic_text.rstrip(".").strip().casefold()
    exact_structural_term = canonical in ILLUSTRATION_WORD_ACCEPTED_TERMS
    period_preserved = semantic_text.rstrip().endswith(".")
    no_bracket_artifacts = not any(char in stripped for char in "[]{}")
    emphasis_requirement_passed = emphasis_wrapped if require_emphasis else not emphasis_wrapped
    passed = bool(
        exact_structural_term
        and period_preserved
        and no_bracket_artifacts
        and emphasis_requirement_passed
    )
    return {
        "contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "target_text": target,
        "canonical_target": canonical,
        "accepted_terms": list(ILLUSTRATION_WORD_ACCEPTED_TERMS),
        "require_emphasis": require_emphasis,
        "emphasis_wrapped": emphasis_wrapped,
        "period_preserved": period_preserved,
        "no_bracket_artifacts": no_bracket_artifacts,
        "exact_structural_term": exact_structural_term,
        "passed": passed,
    }


def evaluate_illustration_label_target_shape(
    source: str, target: str
) -> dict[str, Any]:
    source_match = _STRUCTURAL_LABEL_RE.fullmatch(source)
    figure_number = (
        None if source_match is None else str(source_match.group("number"))
    )
    stripped = target.strip()
    square_wrapped = stripped.startswith("[") and stripped.endswith("]")
    same_figure_number = False
    if figure_number is not None:
        same_figure_number = (
            re.search(rf"(?<!\d){re.escape(figure_number)}(?!\d)", stripped)
            is not None
        )
    semantic_term = next(
        (term for term in ILLUSTRATION_WORD_ACCEPTED_TERMS if term in stripped.casefold()),
        None,
    )
    period_before_close = stripped.endswith(".]")
    no_emphasis_artifacts = "_" not in stripped
    passed = bool(
        figure_number is not None
        and square_wrapped
        and same_figure_number
        and semantic_term is not None
        and period_before_close
        and no_emphasis_artifacts
    )
    return {
        "contract": ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
        "source_text": source,
        "target_text": target,
        "source_figure_number": figure_number,
        "square_wrapped": square_wrapped,
        "same_figure_number": same_figure_number,
        "semantic_term": semantic_term,
        "period_before_close": period_before_close,
        "no_emphasis_artifacts": no_emphasis_artifacts,
        "passed": passed,
    }


def evaluate_illustration_label_trigger(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    structural_plan = _structural_word_plan(source)
    split = _split_prefix(source)
    ordinary_split = None
    if structural_plan is None and split is not None:
        structural, remainder = split
        # Exact standalone _Illustration._ is authorized only by the complete
        # structural-word plan above.  A broader prefix must fail closed.
        if remainder.strip() != ILLUSTRATION_WORD_SOURCE:
            ordinary_split = (structural, remainder)
    base_verdict = evaluate_rescue_pair(source, target)
    hard_failure = base_verdict.get("product_hard_passed") is not True
    candidate_kind = None
    if structural_plan is not None:
        candidate_kind = "source_planned_structural_illustration"
    elif ordinary_split is not None:
        candidate_kind = "ordinary_linguistic_suffix"
    eligible = bool(hard_failure and candidate_kind is not None)
    return {
        "contract": ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
        "eligible": eligible,
        "candidate_kind": candidate_kind,
        "standalone_illustration_prefix": split is not None,
        "source_planned_structural_illustration": structural_plan is not None,
        "ordinary_linguistic_suffix": ordinary_split is not None,
        "already_product_hard_failing": hard_failure,
        "structural_source": None if ordinary_split is None else ordinary_split[0],
        "remainder_source": None if ordinary_split is None else ordinary_split[1],
        "source_plan": structural_plan,
        "base_verdict": base_verdict,
    }


def evaluate_illustration_label_candidate(
    row: dict[str, Any], *, structural_source: str, remainder_source: str,
    target: str, normalized_model_input: bool,
) -> dict[str, Any]:
    """Evaluate the retained ordinary-suffix OPUS path."""
    base_verdict = evaluate_rescue_pair(
        str(row.get("source_text") or ""), str(row.get("target_text") or "")
    )
    structural_verdict = evaluate_rescue_pair(structural_source, structural_source)
    remainder_verdict = evaluate_rescue_pair(remainder_source, target)
    if normalized_model_input:
        raise ValueError("illustration-label rescue forbids normalized model input")
    if remainder_source.strip() == ILLUSTRATION_WORD_SOURCE:
        target_shape = evaluate_illustration_word_target_shape(target)
    else:
        target_shape = {
            "contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
            "applicable": False,
            "passed": True,
        }
    accepted = bool(
        base_verdict.get("product_hard_passed") is not True
        and structural_verdict.get("strictly_eligible") is True
        and remainder_verdict.get("strictly_eligible") is True
        and target_shape.get("passed") is True
    )
    return {
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "accepted": accepted,
        "candidate_kind": "ordinary_linguistic_suffix",
        "base_product_hard_failure": base_verdict.get("product_hard_passed") is not True,
        "base_verdict": base_verdict,
        "structural_verdict": structural_verdict,
        "remainder_verdict": remainder_verdict,
        "illustration_word_target_shape": target_shape,
    }


def evaluate_structural_separator_candidate(
    row: dict[str, Any], *, label_source: str, separator_source: str,
    suffix_source: str, trailing_source: str, label_target: str,
    suffix_target: str,
) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    base_target = str(row.get("target_text") or "")
    if label_source + separator_source + suffix_source + trailing_source != source:
        raise ValueError("illustration structural candidate source plan does not cover source exactly")
    if not separator_source or separator_source.strip() or separator_source.count("\n") < 2:
        raise ValueError("illustration structural candidate separator is not source-owned blank-line structure")
    if suffix_source != ILLUSTRATION_WORD_SOURCE:
        raise ValueError("illustration structural candidate suffix source drift")

    label_verdict = evaluate_rescue_pair(label_source, label_target)
    suffix_verdict = evaluate_rescue_pair(suffix_source, suffix_target)
    aggregate_target = label_target + separator_source + suffix_target + trailing_source
    aggregate_verdict = evaluate_rescue_pair(source, aggregate_target)
    emphasis = compare_emphasis_markup_preservation(source, aggregate_target)
    label_shape = evaluate_illustration_label_target_shape(label_source, label_target)
    suffix_shape = evaluate_illustration_word_target_shape(
        suffix_target, require_emphasis=True
    )
    base_verdict = evaluate_rescue_pair(source, base_target)
    accepted = bool(
        base_verdict.get("product_hard_passed") is not True
        and label_verdict.get("strictly_eligible") is True
        and suffix_verdict.get("strictly_eligible") is True
        and aggregate_verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and label_shape.get("passed") is True
        and suffix_shape.get("passed") is True
    )
    return {
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "source_plan_contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
        "candidate_kind": "source_planned_structural_illustration",
        "accepted": accepted,
        "base_product_hard_failure": base_verdict.get("product_hard_passed") is not True,
        "base_verdict": base_verdict,
        "label_verdict": label_verdict,
        "suffix_verdict": suffix_verdict,
        "aggregate_target": aggregate_target,
        "aggregate_verdict": aggregate_verdict,
        "aggregate_emphasis_markup": emphasis,
        "label_target_shape": label_shape,
        "illustration_word_target_shape": suffix_shape,
        "source_plan_created_before_mt": True,
        "source_owned_structural_passthrough": True,
        "exact_source_separator_preserved": True,
        "exact_trailing_source_preserved": True,
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
    payload["illustration_label_rescue"] = {
        "contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "source_plan_contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
        "target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "label_target_form_contract": ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
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
    """Build retained ordinary-suffix replacement rows."""
    if selected_rank != 0:
        raise ValueError("illustration-label rescue is rank0-only")
    if normalized_model_input:
        raise ValueError("illustration-label rescue forbids normalized model input")
    if model_input != remainder_source:
        raise ValueError("illustration-label rescue model input must equal source remainder")
    if candidate_kind != "ordinary_linguistic_suffix":
        raise ValueError("ordinary illustration candidate kind drift")
    rank0 = _unique_rank0(hypotheses, label="illustration ordinary suffix")
    target = str(rank0.get("text") or "")
    if selection.get("accepted") is not True:
        raise ValueError("illustration-label ordinary suffix selection is not accepted")
    start = int(base["source_start"])
    boundary = start + len(structural_source)
    end = int(base["source_end"])
    if boundary >= end or boundary + len(remainder_source) != end:
        raise ValueError("illustration-label rescue source bounds drift")
    base_planner = dict((base.get("payload") or {}).get("planner") or {})
    common = {
        "contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "source_plan_contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
        "target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "label_target_form_contract": ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
        "applied": True,
        "trigger": "standalone_illustration_label_existing_hard_failure",
        "base_translation_segment_id": int(base["id"]),
        "base_source_span": [start, end],
        "split_source_boundary": boundary,
        "candidate_kind": candidate_kind,
        "model_input": model_input,
        "model_input_source_span": [boundary, end],
        "source_model_input_normalized": False,
        "model_input_source_exact": True,
        "generation": dict(generation),
        "selected_rank": 0,
        "selected_target": target,
        "trigger_evidence": trigger,
        "selection": selection,
        "raw_model_selected": True,
        "raw_rank0_only": True,
        "source_plan_created_before_mt": True,
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
        "selected_rank": 0,
        "illustration_label_rescue": {
            **common,
            "role": "linguistic_remainder",
            "model": "opus",
            "source_owned_passthrough": False,
        },
    }
    return [
        {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": start,
            "source_end": boundary,
            "source_text": structural_source,
            "target_text": structural_source,
            "payload": structural_payload,
        },
        {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": boundary,
            "source_end": end,
            "source_text": remainder_source,
            "target_text": target,
            "payload": remainder_payload,
        },
    ]


def _structural_candidate_rows(
    *, base: dict[str, Any], plan: dict[str, Any],
    label_model_input: str, suffix_model_input: str,
    label_hypotheses: list[dict[str, Any]], suffix_hypotheses: list[dict[str, Any]],
    label_selected_rank: int, suffix_selected_rank: int,
    trigger: dict[str, Any], selection: dict[str, Any],
) -> list[dict[str, Any]]:
    if label_selected_rank != 0 or suffix_selected_rank != 0:
        raise ValueError("illustration structural rescue is rank0-only")
    label = str(plan["label_source"])
    separator = str(plan["separator_source"])
    suffix = str(plan["suffix_source"])
    trailing = str(plan["trailing_source"])
    if label_model_input != label or suffix_model_input != suffix:
        raise ValueError("illustration structural model input must equal exact source piece")
    label_rank0 = _unique_rank0(
        label_hypotheses, label="illustration structural label"
    )
    suffix_rank0 = _unique_rank0(
        suffix_hypotheses, label="illustration structural suffix"
    )
    label_target = str(label_rank0.get("text") or "")
    suffix_target = str(suffix_rank0.get("text") or "")
    expected_aggregate = label_target + separator + suffix_target + trailing
    if selection.get("accepted") is not True:
        raise ValueError("illustration structural selection is not accepted")
    if str(selection.get("aggregate_target") or "") != expected_aggregate:
        raise ValueError("illustration structural selection target drift")

    start = int(base["source_start"])
    label_end = start + len(label)
    separator_end = label_end + len(separator)
    suffix_end = separator_end + len(suffix)
    end = int(base["source_end"])
    if suffix_end + len(trailing) != end:
        raise ValueError("illustration structural source bounds drift")
    if label + separator + suffix + trailing != str(base.get("source_text") or ""):
        raise ValueError("illustration structural source plan no longer matches base source")

    base_planner = dict((base.get("payload") or {}).get("planner") or {})
    source_plan = {
        "contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
        "created_before_mt": True,
        "pieces": [
            {"role": "label", "source_span": [start, label_end], "kind": "translate", "model": "opus"},
            {"role": "separator", "source_span": [label_end, separator_end], "kind": "preserve_source_structure"},
            {"role": "suffix", "source_span": [separator_end, suffix_end], "kind": "translate", "model": "tc_big"},
            {"role": "trailing", "source_span": [suffix_end, end], "kind": "preserve_source_structure"},
        ],
    }
    common = {
        "contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        "selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "trigger_contract": ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
        "source_plan_contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
        "target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "label_target_form_contract": ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
        "applied": True,
        "candidate_kind": "source_planned_structural_illustration",
        "base_translation_segment_id": int(base["id"]),
        "base_source_span": [start, end],
        "figure_number": str(plan["figure_number"]),
        "source_plan": source_plan,
        "source_plan_created_before_mt": True,
        "source_owned_structural_passthrough": True,
        "trigger_evidence": trigger,
        "selection": selection,
        "raw_rank0_only": True,
        **_safety_flags(),
    }

    def translated_payload(
        *, role: str, model: str, model_input: str,
        source_span: list[int], target: str, hypotheses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "planner": {
                **base_planner,
                "source": f"illustration_source_planned_{role}",
                "planner_contract": primary_stage.PLANNER_CONTRACT,
                "split": True,
                "rescue_strategy": "illustration_source_planned_structural_separator",
                "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
            },
            "hypotheses": hypotheses,
            "selected_rank": 0,
            "illustration_label_rescue": {
                **common,
                "role": role,
                "model": model,
                "model_input": model_input,
                "model_input_source_span": source_span,
                "model_input_source_exact": True,
                "source_model_input_normalized": False,
                "selected_rank": 0,
                "selected_target": target,
                "raw_model_selected": True,
                "source_owned_passthrough": False,
                "generation": {
                    "beam_size": STRUCTURAL_WORD_BEAM_SIZE,
                    "num_hypotheses": STRUCTURAL_WORD_NUM_HYPOTHESES,
                    "max_decoding_length": MAX_DECODING_LENGTH,
                    "selection_authorized_ranks": [0],
                },
            },
        }

    def passthrough_payload(*, role: str, source_span: list[int]) -> dict[str, Any]:
        return {
            "planner": {
                **base_planner,
                "source": f"illustration_source_owned_{role}",
                "planner_contract": primary_stage.PLANNER_CONTRACT,
                "split": True,
                "rescue_strategy": "illustration_source_planned_structural_separator",
                "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
            },
            "illustration_label_rescue": {
                **common,
                "role": role,
                "source_span": source_span,
                "source_owned_passthrough": True,
                "raw_model_selected": False,
            },
        }

    rows = [
        {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": start,
            "source_end": label_end,
            "source_text": label,
            "target_text": label_target,
            "payload": translated_payload(
                role="label",
                model="opus",
                model_input=label_model_input,
                source_span=[start, label_end],
                target=label_target,
                hypotheses=label_hypotheses,
            ),
        },
        {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": label_end,
            "source_end": separator_end,
            "source_text": separator,
            "target_text": separator,
            "payload": passthrough_payload(
                role="separator", source_span=[label_end, separator_end]
            ),
        },
        {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": separator_end,
            "source_end": suffix_end,
            "source_text": suffix,
            "target_text": suffix_target,
            "payload": translated_payload(
                role="suffix",
                model="tc_big",
                model_input=suffix_model_input,
                source_span=[separator_end, suffix_end],
                target=suffix_target,
                hypotheses=suffix_hypotheses,
            ),
        },
    ]
    if trailing:
        rows.append(
            {
                "sequence_number": 0,
                "kind": "translation_segment",
                "source_start": suffix_end,
                "source_end": end,
                "source_text": trailing,
                "target_text": trailing,
                "payload": passthrough_payload(
                    role="trailing", source_span=[suffix_end, end]
                ),
            }
        )
    return rows


def _unique_rank0(
    hypotheses: list[dict[str, Any]], *, label: str
) -> dict[str, Any]:
    rank0: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        try:
            rank = int(hypothesis["rank"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StageExecutionError(f"{label} malformed rank evidence") from exc
        if rank == 0:
            rank0.append(hypothesis)
    if len(rank0) != 1:
        raise StageExecutionError(f"{label} rank0 cardinality drift: {len(rank0)}")
    target = str(rank0[0].get("text") or "")
    if not target.strip():
        raise StageExecutionError(f"{label} rank0 target is empty")
    return rank0[0]


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
        name="enable_illustration_label_rescue",
        default=DEFAULT_ENABLED,
    )
    if not enabled:
        return run_base_stage12(
            database,
            context_run_id=int(context_run_id),
            parameters=_base_parameters(effective),
            implementation=implementation,
        )
    if _bool_parameter(
        effective.get("enable_selective_resegmentation_rescue"),
        name="enable_selective_resegmentation_rescue",
        default=False,
    ) or _bool_parameter(
        effective.get("enable_whole_context_rescue"),
        name="enable_whole_context_rescue",
        default=False,
    ):
        raise StageExecutionError(
            "illustration-label rescue may not be combined with legacy Stage12 selective/whole-context research rescues"
        )

    requested_contract = str(
        effective.get("illustration_label_rescue_contract")
        or ILLUSTRATION_LABEL_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("illustration_label_rescue_selector_contract")
        or ILLUSTRATION_LABEL_SELECTOR_CONTRACT
    )
    requested_trigger = str(
        effective.get("illustration_label_trigger_contract")
        or ILLUSTRATION_LABEL_TRIGGER_CONTRACT
    )
    requested_source_plan = str(
        effective.get("illustration_source_plan_contract")
        or ILLUSTRATION_SOURCE_PLAN_CONTRACT
    )
    requested_target_form = str(
        effective.get("illustration_word_target_form_contract")
        or ILLUSTRATION_WORD_TARGET_FORM_CONTRACT
    )
    requested_label_form = str(
        effective.get("illustration_label_target_form_contract")
        or ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT
    )
    if requested_contract != ILLUSTRATION_LABEL_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported illustration-label rescue contract {requested_contract!r}"
        )
    if requested_selector != ILLUSTRATION_LABEL_SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported illustration-label selector {requested_selector!r}"
        )
    if requested_trigger != ILLUSTRATION_LABEL_TRIGGER_CONTRACT:
        raise StageExecutionError(
            f"Unsupported illustration-label trigger {requested_trigger!r}"
        )
    if requested_source_plan != ILLUSTRATION_SOURCE_PLAN_CONTRACT:
        raise StageExecutionError(
            f"Unsupported illustration source-plan contract {requested_source_plan!r}"
        )
    if requested_target_form != ILLUSTRATION_WORD_TARGET_FORM_CONTRACT:
        raise StageExecutionError(
            f"Unsupported illustration-word target form {requested_target_form!r}"
        )
    if requested_label_form != ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT:
        raise StageExecutionError(
            f"Unsupported illustration-label target form {requested_label_form!r}"
        )
    if effective.get("illustration_label_rescue_phase") not in {
        None,
        ILLUSTRATION_LABEL_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "illustration_label_rescue_phase is internal and may not be overridden"
        )

    effective["enable_illustration_label_rescue"] = True
    effective["illustration_label_rescue_contract"] = ILLUSTRATION_LABEL_RESCUE_CONTRACT
    effective["illustration_label_rescue_selector_contract"] = ILLUSTRATION_LABEL_SELECTOR_CONTRACT
    effective["illustration_label_trigger_contract"] = ILLUSTRATION_LABEL_TRIGGER_CONTRACT
    effective["illustration_source_plan_contract"] = ILLUSTRATION_SOURCE_PLAN_CONTRACT
    effective["illustration_word_target_form_contract"] = ILLUSTRATION_WORD_TARGET_FORM_CONTRACT
    effective["illustration_label_target_form_contract"] = ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT
    effective["illustration_label_rescue_phase"] = ILLUSTRATION_LABEL_SELECTED_PHASE

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
        selected_format = str(document["selected_format"])
        beam_size = int(effective.get("beam_size") or 6)
        num_hypotheses = int(effective.get("num_hypotheses") or 1)
        request_batch_size = int(
            effective.get("request_batch_size", primary_stage.DEFAULT_REQUEST_BATCH_SIZE)
        )
        device = str(effective.get("device") or "cpu")
        compute_type = str(effective.get("compute_type") or "float32")
        generation_supported = beam_size == 6 and num_hypotheses == 1
        if selected_format == "txt" and not generation_supported:
            raise StageExecutionError(
                "Stage12 illustration-label rescue requires beam_size=6 and num_hypotheses=1"
            )

        attempts: list[dict[str, Any]] = []
        if generation_supported and selected_format == "txt":
            for row in sorted(base_rows, key=lambda item: int(item["source_start"])):
                trigger = evaluate_illustration_label_trigger(row)
                if trigger["eligible"] is not True:
                    continue
                if trigger["candidate_kind"] == "ordinary_linguistic_suffix":
                    remainder = str(trigger["remainder_source"])
                    model_input, normalized, candidate_kind = _model_input_for_remainder(
                        remainder
                    )
                    attempts.append(
                        {
                            "row": row,
                            "trigger": trigger,
                            "candidate_kind": candidate_kind,
                            "structural": str(trigger["structural_source"]),
                            "remainder": remainder,
                            "model_input": model_input,
                            "normalized_model_input": normalized,
                        }
                    )
                elif trigger["candidate_kind"] == "source_planned_structural_illustration":
                    plan = dict(trigger["source_plan"] or {})
                    attempts.append(
                        {
                            "row": row,
                            "trigger": trigger,
                            "candidate_kind": "source_planned_structural_illustration",
                            "plan": plan,
                            "label_model_input": str(plan["label_source"]),
                            "suffix_model_input": str(plan["suffix_source"]),
                        }
                    )
                else:
                    raise StageExecutionError(
                        f"Stage12 illustration-label unknown candidate kind: {trigger['candidate_kind']!r}"
                    )

        normalized_attempts = [
            attempt
            for attempt in attempts
            if bool(attempt.get("normalized_model_input", False))
        ]
        if normalized_attempts:
            raise StageExecutionError(
                "Stage12 illustration-label exact-source contract forbids normalized model input"
            )

        ordinary_attempts = [
            attempt
            for attempt in attempts
            if attempt["candidate_kind"] == "ordinary_linguistic_suffix"
        ]
        structural_attempts = [
            attempt
            for attempt in attempts
            if attempt["candidate_kind"] == "source_planned_structural_illustration"
        ]

        ordinary_generated: dict[int, list[dict[str, Any]]] = {}
        label_generated: dict[int, list[dict[str, Any]]] = {}
        suffix_generated: dict[int, list[dict[str, Any]]] = {}
        opus_batch_count = 0
        tc_big_batch_count = 0
        tc_big_runtime: dict[str, Any] | None = None

        if ordinary_attempts or structural_attempts:
            opus = OpusTranslator(device=device, compute_type=compute_type)
            if ordinary_attempts:
                generated = primary_stage._translate_primary_request_batches(
                    opus,
                    [str(attempt["model_input"]) for attempt in ordinary_attempts],
                    batch_size=request_batch_size,
                    beam_size=ORDINARY_SUFFIX_BEAM_SIZE,
                    num_hypotheses=ORDINARY_SUFFIX_NUM_HYPOTHESES,
                    max_decoding_length=MAX_DECODING_LENGTH,
                )
                if len(generated) != len(ordinary_attempts) or any(
                    len(hypotheses) != ORDINARY_SUFFIX_NUM_HYPOTHESES
                    for hypotheses in generated
                ):
                    raise StageExecutionError(
                        "Stage12 illustration-label ordinary-suffix hypothesis cardinality drift"
                    )
                for attempt, hypotheses in zip(
                    ordinary_attempts, generated, strict=True
                ):
                    ordinary_generated[int(attempt["row"]["id"])] = hypotheses
                opus_batch_count += (
                    len(ordinary_attempts) + request_batch_size - 1
                ) // request_batch_size

            if structural_attempts:
                if device != "cpu" or compute_type != "float32":
                    raise StageExecutionError(
                        "Stage12 illustration structural rescue is pinned to CPU float32"
                    )
                generated = primary_stage._translate_primary_request_batches(
                    opus,
                    [str(attempt["label_model_input"]) for attempt in structural_attempts],
                    batch_size=request_batch_size,
                    beam_size=STRUCTURAL_WORD_BEAM_SIZE,
                    num_hypotheses=STRUCTURAL_WORD_NUM_HYPOTHESES,
                    max_decoding_length=MAX_DECODING_LENGTH,
                )
                if len(generated) != len(structural_attempts) or any(
                    len(hypotheses) != STRUCTURAL_WORD_NUM_HYPOTHESES
                    for hypotheses in generated
                ):
                    raise StageExecutionError(
                        "Stage12 illustration-label structural label hypothesis cardinality drift"
                    )
                for attempt, hypotheses in zip(
                    structural_attempts, generated, strict=True
                ):
                    label_generated[int(attempt["row"]["id"])] = hypotheses
                opus_batch_count += (
                    len(structural_attempts) + request_batch_size - 1
                ) // request_batch_size

                tc_big_runtime = tc_big_status()
                if tc_big_runtime.get("available") is not True:
                    raise StageExecutionError(
                        f"Stage12 illustration structural TC-big runtime unavailable: {tc_big_runtime}"
                    )
                tc_big = TcBigTranslator(device="cpu", compute_type="float32")
                generated = tc_big.translate(
                    [str(attempt["suffix_model_input"]) for attempt in structural_attempts],
                    beam_size=STRUCTURAL_WORD_BEAM_SIZE,
                    num_hypotheses=STRUCTURAL_WORD_NUM_HYPOTHESES,
                    max_decoding_length=MAX_DECODING_LENGTH,
                )
                if len(generated) != len(structural_attempts) or any(
                    len(hypotheses) != STRUCTURAL_WORD_NUM_HYPOTHESES
                    for hypotheses in generated
                ):
                    raise StageExecutionError(
                        "Stage12 illustration-label structural suffix hypothesis cardinality drift"
                    )
                for attempt, hypotheses in zip(
                    structural_attempts, generated, strict=True
                ):
                    suffix_generated[int(attempt["row"]["id"])] = hypotheses
                tc_big_batch_count = 1

        accepted: dict[int, dict[str, Any]] = {}
        rejected: dict[int, dict[str, Any]] = {}
        for attempt in attempts:
            row = attempt["row"]
            row_id = int(row["id"])
            if attempt["candidate_kind"] == "ordinary_linguistic_suffix":
                hypotheses = ordinary_generated.get(row_id) or []
                if not hypotheses:
                    rejected[row_id] = {"reason": "empty_hypothesis_set"}
                    continue
                evaluated: list[dict[str, Any]] = []
                for index, hypothesis in enumerate(hypotheses):
                    rank = int(hypothesis.get("rank", index))
                    target = str(hypothesis.get("text") or "")
                    if not target.strip():
                        evaluated.append(
                            {
                                "rank": rank,
                                "target_text": target,
                                "score": hypothesis.get("score"),
                                "accepted": False,
                                "reason": "empty_target",
                            }
                        )
                        continue
                    selection = evaluate_illustration_label_candidate(
                        row,
                        structural_source=str(attempt["structural"]),
                        remainder_source=str(attempt["remainder"]),
                        target=target,
                        normalized_model_input=False,
                    )
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
                rank0_choice = select_rank0_evaluation(evaluated)
                if rank0_choice is None:
                    rejected[row_id] = {
                        "reason": "rank0_selector_rejected",
                        "evaluated_hypotheses": evaluated,
                    }
                    continue
                selected_selection = dict(rank0_choice["selection"])
                rows = _candidate_rows(
                    base=row,
                    structural_source=str(attempt["structural"]),
                    remainder_source=str(attempt["remainder"]),
                    model_input=str(attempt["model_input"]),
                    normalized_model_input=False,
                    candidate_kind="ordinary_linguistic_suffix",
                    hypotheses=hypotheses,
                    selected_rank=0,
                    trigger=dict(attempt["trigger"]),
                    selection=selected_selection,
                    generation={
                        "beam_size": ORDINARY_SUFFIX_BEAM_SIZE,
                        "num_hypotheses": ORDINARY_SUFFIX_NUM_HYPOTHESES,
                        "max_decoding_length": MAX_DECODING_LENGTH,
                    },
                )
                accepted[row_id] = {
                    "rows": rows,
                    "selected_ranks": [0],
                    "selected_targets": [str(rank0_choice["target_text"])],
                    "source_start": int(row["source_start"]),
                    "candidate_kind": "ordinary_linguistic_suffix",
                    "evaluated_hypotheses": evaluated,
                }
                continue

            label_hypotheses = label_generated.get(row_id) or []
            suffix_hypotheses = suffix_generated.get(row_id) or []
            if not label_hypotheses or not suffix_hypotheses:
                rejected[row_id] = {"reason": "empty_structural_piece_hypothesis_set"}
                continue
            label_rank0 = _unique_rank0(
                label_hypotheses, label="illustration structural label"
            )
            suffix_rank0 = _unique_rank0(
                suffix_hypotheses, label="illustration structural suffix"
            )
            plan = dict(attempt["plan"])
            selection = evaluate_structural_separator_candidate(
                row,
                label_source=str(plan["label_source"]),
                separator_source=str(plan["separator_source"]),
                suffix_source=str(plan["suffix_source"]),
                trailing_source=str(plan["trailing_source"]),
                label_target=str(label_rank0["text"]),
                suffix_target=str(suffix_rank0["text"]),
            )
            if selection["accepted"] is not True:
                rejected[row_id] = {
                    "reason": "structural_rank0_selector_rejected",
                    "label_rank0": label_rank0,
                    "suffix_rank0": suffix_rank0,
                    "selection": selection,
                }
                continue
            rows = _structural_candidate_rows(
                base=row,
                plan=plan,
                label_model_input=str(attempt["label_model_input"]),
                suffix_model_input=str(attempt["suffix_model_input"]),
                label_hypotheses=label_hypotheses,
                suffix_hypotheses=suffix_hypotheses,
                label_selected_rank=0,
                suffix_selected_rank=0,
                trigger=dict(attempt["trigger"]),
                selection=selection,
            )
            accepted[row_id] = {
                "rows": rows,
                "selected_ranks": [0, 0],
                "selected_targets": [
                    str(label_rank0["text"]),
                    str(suffix_rank0["text"]),
                ],
                "source_start": int(row["source_start"]),
                "candidate_kind": "source_planned_structural_illustration",
                "aggregate_target": str(selection["aggregate_target"]),
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
            raise StageExecutionError(
                "Stage12 illustration-label rescue final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(
            len(str(row.get("source_text") or "")) for row in base_rows
        )
        if source_sum != base_source_sum:
            raise StageExecutionError(
                "Stage12 illustration-label rescue changed total source character coverage"
            )

        accepted_values = sorted(
            accepted.values(), key=lambda value: int(value["source_start"])
        )
        attempted_starts = sorted(
            int(attempt["row"]["source_start"]) for attempt in attempts
        )
        accepted_starts = [
            int(value["source_start"]) for value in accepted_values
        ]
        rejected_starts = sorted(
            int(attempt["row"]["source_start"])
            for attempt in attempts
            if int(attempt["row"]["id"]) in rejected
        )
        ordinary_count = sum(
            1
            for value in accepted_values
            if value["candidate_kind"] == "ordinary_linguistic_suffix"
        )
        structural_count = sum(
            1
            for value in accepted_values
            if value["candidate_kind"] == "source_planned_structural_illustration"
        )
        logical_model_requests = len(ordinary_attempts) + (2 * len(structural_attempts))
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
            "illustration_label_rescue_selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
            "illustration_label_trigger_contract": ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
            "illustration_source_plan_contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
            "illustration_word_target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
            "illustration_label_target_form_contract": ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
            "illustration_label_rescue_enabled": True,
            "illustration_label_rescue_generation_supported": generation_supported,
            "illustration_label_rescue_trigger": "standalone_illustration_label_existing_hard_failure",
            "illustration_label_rescue_attempt_count": len(attempts),
            "illustration_label_rescue_accepted_count": len(accepted),
            "illustration_label_rescue_rejected_count": len(rejected),
            "illustration_label_rescue_ordinary_accepted_count": ordinary_count,
            "illustration_label_rescue_structural_accepted_count": structural_count,
            "illustration_label_rescue_attempted_source_starts": attempted_starts,
            "illustration_label_rescue_accepted_source_starts": accepted_starts,
            "illustration_label_rescue_rejected_source_starts": rejected_starts,
            "illustration_label_rescue_selected_ranks": [
                rank
                for value in accepted_values
                for rank in value["selected_ranks"]
            ],
            "illustration_label_rescue_selected_targets": [
                target
                for value in accepted_values
                for target in value["selected_targets"]
            ],
            "illustration_label_rescue_normalized_model_input_source_starts": [],
            "illustration_label_rescue_model_inputs_source_exact": True,
            "illustration_label_rescue_source_plan_created_before_mt": True,
            "illustration_label_rescue_source_owned_structural_passthrough": bool(structural_attempts),
            "illustration_label_rescue_raw_rank0_only": True,
            "illustration_label_rescue_structural_word_beam_size": STRUCTURAL_WORD_BEAM_SIZE,
            "illustration_label_rescue_structural_word_num_hypotheses": STRUCTURAL_WORD_NUM_HYPOTHESES,
            "illustration_label_rescue_ordinary_suffix_beam_size": ORDINARY_SUFFIX_BEAM_SIZE,
            "illustration_label_rescue_ordinary_suffix_num_hypotheses": ORDINARY_SUFFIX_NUM_HYPOTHESES,
            "illustration_label_rescue_model_request_count": logical_model_requests,
            "illustration_label_rescue_model_batch_count": opus_batch_count + tc_big_batch_count,
            "illustration_label_rescue_tc_big_runtime": tc_big_runtime,
            "base_segment_count": len(base_rows),
            "segment_count": len(final_rows),
            "source_character_sum": source_sum,
            "model_request_count": int(base_output.get("model_request_count") or 0)
            + logical_model_requests,
            "source_owned_structural_passthrough": bool(structural_attempts),
            "source_plan_created_before_mt": True,
            "raw_rank0_only": True,
            **_safety_flags(),
        }
        return _complete(database, run_id, output, items=final_rows)
    except Exception as exc:
        _fail(database, run_id, exc)
        raise
