from __future__ import annotations

"""Opt-in Stage12 rescue for bare Roman fragments split from inline ``Sect.`` citations.

The maintained planner intentionally does not classify bare ``IV.``/``II.`` rows
as structural headings.  Full-Opticks evidence shows two residual length failures
where sentence segmentation split an ordinary inline citation immediately after
``Sect. ``.  This wrapper preserves the planner and immutable source bytes, then
retranslates only the exact contiguous pair ``<row ending Sect. ><bare Roman row>``
with raw rank-0 pinned OPUS.

A candidate pair is accepted only when the bare-Roman primary row already fails
the maintained length check, the merged raw candidate passes every Product hard
check, and it introduces no new strict research-debt category relative to the two
primary rows.  Existing strict debt may be carried forward but never increased.
No source/target rewriting, placeholders or post-translation literal insertion is
performed.  The mechanism remains disabled by default.
"""

from pathlib import Path
import re
from typing import Any

from .database import connect, get_document, get_run, get_run_items
from .runtime import OpusTranslator
from .stages import StageExecutionError, _complete, _fail, _start
from .translation_rescue import evaluate_rescue_pair
from .translation_length_rescue_stage import run_stage12 as run_base_stage12
from . import translation_stage as primary_stage

CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT = (
    "rocketdict-stage12-citation-boundary-pair-rescue/1"
)
CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT = (
    "rocketdict-stage12-citation-boundary-pair-selector/1"
)
CITATION_BOUNDARY_PAIR_SELECTED_PHASE = "citation-boundary-pair-selected-v1"
DEFAULT_ENABLED = False
DEFAULT_MAX_SOURCE_CHARS = 256
MAX_SOURCE_CHARS = 512
_ROMAN_FRAGMENT_RE = re.compile(r"[IVXLCDM]+\.\s*\Z")
_SECT_SUFFIX_RE = re.compile(r"\bSect\.\s*\Z", flags=re.IGNORECASE)
_CITATION_ONLY_KEYS = frozenset(
    {
        "enable_citation_boundary_pair_rescue",
        "citation_boundary_pair_rescue_contract",
        "citation_boundary_pair_rescue_selector_contract",
        "citation_boundary_pair_rescue_phase",
        "citation_boundary_pair_rescue_max_source_chars",
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
    """Strip only citation-wrapper controls from the underlying Stage12 identity."""
    return {key: value for key, value in parameters.items() if key not in _CITATION_ONLY_KEYS}


def _strict_debt(verdict: dict[str, Any]) -> set[str]:
    debt: set[str] = set()
    if verdict.get("numeric_symbol", {}).get("passed") is not True:
        debt.add("numeric_symbol")
    if verdict.get("punctuation_passed") is not True:
        debt.add("punctuation")
    if verdict.get("length_passed") is not True:
        debt.add("length")
    if verdict.get("numeric_order", {}).get("passed") is not True:
        debt.add("numeric_order")
    if verdict.get("delimiter_preservation", {}).get("passed") is not True:
        debt.add("delimiter_preservation")
    for name in verdict.get("critical_technical_tokens", {}).get("failed_checks") or []:
        debt.add(f"critical:{name}")
    if verdict.get("output_artifacts", {}).get("passed") is not True:
        debt.add("output_artifacts")
    return debt


def _planner_source(row: dict[str, Any]) -> str:
    return str(((row.get("payload") or {}).get("planner") or {}).get("source") or "")


def evaluate_citation_pair_trigger(
    previous: dict[str, Any], current: dict[str, Any], *, max_source_chars: int
) -> dict[str, Any]:
    previous_source = str(previous.get("source_text") or "")
    current_source = str(current.get("source_text") or "")
    contiguous = int(previous["source_end"]) == int(current["source_start"])
    ordinary = _planner_source(previous) not in {
        "ascii_table",
        "structural_label",
        "block_section_identifier",
    } and _planner_source(current) not in {
        "ascii_table",
        "structural_label",
        "block_section_identifier",
    }
    roman_fragment = _ROMAN_FRAGMENT_RE.fullmatch(current_source) is not None
    citation_prefix = _SECT_SUFFIX_RE.search(previous_source) is not None
    pair_source = previous_source + current_source
    current_verdict = evaluate_rescue_pair(
        current_source, str(current.get("target_text") or "")
    )
    eligible = (
        contiguous
        and ordinary
        and roman_fragment
        and citation_prefix
        and current_verdict.get("length_passed") is not True
        and len(pair_source) <= max_source_chars
    )
    return {
        "contract": "rocketdict-stage12-citation-boundary-pair-trigger/1",
        "eligible": eligible,
        "contiguous": contiguous,
        "ordinary": ordinary,
        "roman_fragment": roman_fragment,
        "citation_prefix": citation_prefix,
        "pair_source_chars": len(pair_source),
        "max_source_chars": max_source_chars,
        "current_length_failure": current_verdict.get("length_passed") is not True,
        "current_verdict": current_verdict,
    }


def evaluate_citation_pair_candidate(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    source: str,
    target: str,
) -> dict[str, Any]:
    previous_verdict = evaluate_rescue_pair(
        str(previous.get("source_text") or ""), str(previous.get("target_text") or "")
    )
    current_verdict = evaluate_rescue_pair(
        str(current.get("source_text") or ""), str(current.get("target_text") or "")
    )
    candidate_verdict = evaluate_rescue_pair(source, target)
    primary_debt = _strict_debt(previous_verdict) | _strict_debt(current_verdict)
    candidate_debt = _strict_debt(candidate_verdict)
    new_debt = candidate_debt - primary_debt
    accepted = (
        current_verdict.get("length_passed") is not True
        and candidate_verdict.get("product_hard_passed") is True
        and candidate_verdict.get("length_passed") is True
        and not new_debt
    )
    return {
        "selector_contract": CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
        "accepted": accepted,
        "candidate_verdict": candidate_verdict,
        "previous_verdict": previous_verdict,
        "current_verdict": current_verdict,
        "primary_strict_debt": sorted(primary_debt),
        "candidate_strict_debt": sorted(candidate_debt),
        "new_strict_debt": sorted(new_debt),
        "strict_debt_non_worsening": not new_debt,
    }


def _safety_flags() -> dict[str, bool]:
    return {
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }


def _copy_base_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["citation_boundary_pair_rescue"] = {
        "contract": CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
        "selector_contract": CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
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


def _candidate_row(
    *,
    previous: dict[str, Any],
    current: dict[str, Any],
    source: str,
    hypotheses: list[dict[str, Any]],
    trigger: dict[str, Any],
    selection: dict[str, Any],
    generation: dict[str, int],
    max_source_chars: int,
) -> dict[str, Any]:
    if not hypotheses:
        raise ValueError("citation-boundary pair rescue requires a hypothesis")
    target = str(hypotheses[0].get("text") or "")
    previous_planner = dict((previous.get("payload") or {}).get("planner") or {})
    payload = {
        "planner": {
            **previous_planner,
            "source": "nlp_sentence_pair",
            "planner_contract": primary_stage.PLANNER_CONTRACT,
            "split": False,
            "rescue_strategy": "citation_boundary_pair",
            "citation_boundary_pair_rescue_contract": (
                CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT
            ),
        },
        "hypotheses": hypotheses,
        "selected_rank": 0,
        "citation_boundary_pair_rescue": {
            "contract": CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
            "selector_contract": CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
            "applied": True,
            "trigger": "bare_roman_after_sect_length_failure",
            "base_translation_segment_ids": [int(previous["id"]), int(current["id"])],
            "primary_source_spans": [
                [int(previous["source_start"]), int(previous["source_end"])],
                [int(current["source_start"]), int(current["source_end"])],
            ],
            "roman_fragment": str(current.get("source_text") or ""),
            "maximum_source_chars": max_source_chars,
            "generation": dict(generation),
            "raw_model_rank0": True,
            "trigger_evidence": trigger,
            "candidate_verdict": dict(selection["candidate_verdict"]),
            "primary_strict_debt": list(selection["primary_strict_debt"]),
            "candidate_strict_debt": list(selection["candidate_strict_debt"]),
            "new_strict_debt": list(selection["new_strict_debt"]),
            "strict_debt_non_worsening": bool(selection["strict_debt_non_worsening"]),
            **_safety_flags(),
        },
    }
    return {
        "sequence_number": 0,
        "kind": "translation_segment",
        "source_start": int(previous["source_start"]),
        "source_end": int(current["source_end"]),
        "source_text": source,
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
        effective.get("enable_citation_boundary_pair_rescue"),
        name="enable_citation_boundary_pair_rescue",
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
            "citation-boundary pair rescue may not be combined with legacy Stage12 "
            "research rescue strategies; length-failure whole-context rescue is allowed"
        )

    requested_contract = str(
        effective.get("citation_boundary_pair_rescue_contract")
        or CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT
    )
    requested_selector = str(
        effective.get("citation_boundary_pair_rescue_selector_contract")
        or CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT
    )
    max_source_chars = _positive_int_parameter(
        effective.get("citation_boundary_pair_rescue_max_source_chars"),
        name="citation_boundary_pair_rescue_max_source_chars",
        default=DEFAULT_MAX_SOURCE_CHARS,
    )
    if requested_contract != CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT:
        raise StageExecutionError(
            f"Unsupported citation-boundary pair rescue contract {requested_contract!r}"
        )
    if requested_selector != CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT:
        raise StageExecutionError(
            f"Unsupported citation-boundary pair selector {requested_selector!r}"
        )
    if effective.get("citation_boundary_pair_rescue_phase") not in {
        None,
        CITATION_BOUNDARY_PAIR_SELECTED_PHASE,
    }:
        raise StageExecutionError(
            "citation_boundary_pair_rescue_phase is internal and may not be overridden"
        )
    if max_source_chars > MAX_SOURCE_CHARS:
        raise StageExecutionError(
            "citation_boundary_pair_rescue_max_source_chars may not exceed "
            f"the conservative cap {MAX_SOURCE_CHARS}"
        )

    effective["enable_citation_boundary_pair_rescue"] = True
    effective["citation_boundary_pair_rescue_contract"] = (
        CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT
    )
    effective["citation_boundary_pair_rescue_selector_contract"] = (
        CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT
    )
    effective["citation_boundary_pair_rescue_phase"] = (
        CITATION_BOUNDARY_PAIR_SELECTED_PHASE
    )
    effective["citation_boundary_pair_rescue_max_source_chars"] = max_source_chars

    base_parameters = _base_parameters(effective)
    base_output = run_base_stage12(
        database,
        context_run_id=int(context_run_id),
        parameters=base_parameters,
        implementation=implementation,
    )
    base_run_id = int(base_output["translation_run_id"])

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, base_run_id)
        base_rows = get_run_items(connection, base_run_id, kind="translation_segment")
        context_run = get_run(connection, int(context_run_id))
        context_output = dict(context_run.get("output") or {})
        document_version_id = int(context_output["document_version_id"])
        document = get_document(connection, document_version_id)

    input_identity = {
        "context_run_id": int(context_run_id),
        "context_output_sha256": str(context_run.get("output_sha256") or ""),
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

        ordered = sorted(base_rows, key=lambda row: int(row["source_start"]))
        attempts: list[dict[str, Any]] = []
        if selected_format == "txt" and generation_supported:
            for index in range(1, len(ordered)):
                previous = ordered[index - 1]
                current = ordered[index]
                trigger = evaluate_citation_pair_trigger(
                    previous, current, max_source_chars=max_source_chars
                )
                if trigger["eligible"] is not True:
                    continue
                source = content[int(previous["source_start"]):int(current["source_end"])]
                if source != str(previous.get("source_text") or "") + str(
                    current.get("source_text") or ""
                ):
                    raise StageExecutionError(
                        "Stage12 citation-boundary pair differs from immutable source"
                    )
                attempts.append(
                    {
                        "previous": previous,
                        "current": current,
                        "trigger": trigger,
                        "source": source,
                    }
                )

        generated: list[list[dict[str, Any]]] = []
        if attempts:
            translator = OpusTranslator(device=device, compute_type=compute_type)
            generated = primary_stage._translate_primary_request_batches(
                translator,
                [str(attempt["source"]) for attempt in attempts],
                batch_size=request_batch_size,
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=256,
            )

        accepted: dict[int, dict[str, Any]] = {}
        rejected: list[dict[str, Any]] = []
        generation = {"beam_size": beam_size, "num_hypotheses": num_hypotheses}
        for attempt, hypotheses in zip(attempts, generated, strict=True):
            previous = attempt["previous"]
            current = attempt["current"]
            if not hypotheses:
                rejected.append({"source_start": int(previous["source_start"]), "reason": "empty_hypothesis_set"})
                continue
            target = str(hypotheses[0].get("text") or "")
            if not target.strip():
                rejected.append({"source_start": int(previous["source_start"]), "reason": "empty_rank0_target"})
                continue
            selection = evaluate_citation_pair_candidate(
                previous,
                current,
                source=str(attempt["source"]),
                target=target,
            )
            if selection["accepted"] is not True:
                rejected.append(
                    {
                        "source_start": int(previous["source_start"]),
                        "reason": "selector_rejected",
                        "selection": selection,
                    }
                )
                continue
            accepted[int(previous["id"])] = {
                "current_id": int(current["id"]),
                "row": _candidate_row(
                    previous=previous,
                    current=current,
                    source=str(attempt["source"]),
                    hypotheses=hypotheses,
                    trigger=dict(attempt["trigger"]),
                    selection=selection,
                    generation=generation,
                    max_source_chars=max_source_chars,
                ),
                "selection": selection,
            }

        final_rows: list[dict[str, Any]] = []
        skip_ids: set[int] = set()
        for row in ordered:
            row_id = int(row["id"])
            if row_id in skip_ids:
                continue
            if row_id in accepted:
                final_rows.append(accepted[row_id]["row"])
                skip_ids.add(int(accepted[row_id]["current_id"]))
                continue
            final_rows.append(_copy_base_row(row))
        final_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence_number, row in enumerate(final_rows):
            row["sequence_number"] = sequence_number

        if "".join(str(row["source_text"]) for row in final_rows) != content:
            raise StageExecutionError(
                "Stage12 citation-boundary pair rescue final source coverage is not byte-exact"
            )
        source_sum = sum(len(str(row["source_text"])) for row in final_rows)
        base_source_sum = sum(len(str(row.get("source_text") or "")) for row in base_rows)
        if source_sum != base_source_sum:
            raise StageExecutionError(
                "Stage12 citation-boundary pair rescue changed total source character coverage"
            )

        accepted_starts = sorted(int(value["row"]["source_start"]) for value in accepted.values())
        output = {
            **dict(base_output),
            "translation_run_id": run_id,
            "cache_hit": False,
            "base_translation_run_id": base_run_id,
            "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
            "citation_boundary_pair_rescue_contract": CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
            "citation_boundary_pair_rescue_selector_contract": CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
            "citation_boundary_pair_rescue_enabled": True,
            "citation_boundary_pair_rescue_generation_supported": generation_supported,
            "citation_boundary_pair_rescue_trigger": "bare_roman_after_sect_length_failure",
            "citation_boundary_pair_rescue_max_source_chars": max_source_chars,
            "citation_boundary_pair_rescue_attempted_pair_count": len(attempts),
            "citation_boundary_pair_rescue_accepted_pair_count": len(accepted),
            "citation_boundary_pair_rescue_rejected_pair_count": len(rejected),
            "citation_boundary_pair_rescue_accepted_source_starts": accepted_starts,
            "citation_boundary_pair_rescue_rejected_pairs": rejected,
            "citation_boundary_pair_rescue_model_request_count": len(attempts),
            "citation_boundary_pair_rescue_model_batch_count": (
                (len(attempts) + request_batch_size - 1) // request_batch_size
                if attempts
                else 0
            ),
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
