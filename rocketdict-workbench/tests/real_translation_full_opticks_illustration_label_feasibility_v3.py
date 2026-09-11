from __future__ import annotations

"""Read-only full-Opticks illustration-label feasibility v3.

V3 keeps v2's byte-exact source-owned ``[Illustration: ...]`` split.  N-best is
used only for the exact immutable suffix ``_Illustration._`` because v1/v2
proved a source-defined sense/markup ambiguity.  Ordinary suffixes remain exact
source input + raw rank0.  No Product code/default or persisted DB is changed.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import real_translation_full_opticks_illustration_label_feasibility as v2
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-illustration-label-feasibility/3"
TARGET_SHAPE_CONTRACT = "rocketdict-illustration-word-target-form/2"
ACCEPTED_TERMS = ("иллюстрация", "рисунок")
STRUCTURAL_BEAM = 6
STRUCTURAL_NBEST = 6
ORDINARY_BEAM = 6
ORDINARY_NBEST = 1
DOE = {
    "workflow_run_id": 34603700499,
    "artifact_id": 10265013225,
    "artifact_digest_sha256": "3e92ac761908175f25d0a66c0942e1772809f402fedb9c637c2f8ad8f1bf50c0",
    "evidence_file_sha256": "54e23fd53c2a4015e030aee5699aa92bb6c051471ae6b4f367cc16957f683025",
    "evidence_sha256": "3c7d3a6e651a33654783cff551d477fdd0973fc75a1a63048c0e0afc44414e08",
    "selected_model_input": v2.ILLUSTRATION_WORD_MODEL_INPUT,
    "selected_beam_size": STRUCTURAL_BEAM,
    "selected_num_hypotheses": STRUCTURAL_NBEST,
    "selected_rank": 3,
    "selected_target": "Иллюстрация.",
}


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _target_shape(target: str) -> dict[str, Any]:
    stripped = target.strip()
    canonical = stripped.rstrip(".").strip().casefold()
    no_markup_artifacts = not any(char in stripped for char in "_*[]{}")
    exact_structural_term = canonical in ACCEPTED_TERMS
    return {
        "contract": TARGET_SHAPE_CONTRACT,
        "target_text": target,
        "canonical_target": canonical,
        "accepted_terms": list(ACCEPTED_TERMS),
        "no_markup_artifacts": no_markup_artifacts,
        "exact_structural_term": exact_structural_term,
        "passed": no_markup_artifacts and exact_structural_term,
    }


def _evaluate(
    attempt: dict[str, Any], hypothesis: dict[str, Any], rank: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    target = str(hypothesis.get("text") or "")
    if not target.strip():
        return {
            "rank": rank,
            "score": hypothesis.get("score"),
            "target_text": target,
            "accepted": False,
            "rejection": "empty_target",
            "raw_model_hypothesis": True,
        }, []
    rows = v2._candidate_rows(
        attempt["row"],
        structural=str(attempt["structural"]),
        remainder=str(attempt["remainder"]),
        target=target,
    )
    structural_verdict = evaluate_rescue_pair(rows[0]["source_text"], rows[0]["target_text"])
    remainder_verdict = evaluate_rescue_pair(rows[1]["source_text"], rows[1]["target_text"])
    shape = (
        _target_shape(target)
        if bool(attempt["source_model_input_normalized"])
        else {"contract": TARGET_SHAPE_CONTRACT, "applicable": False, "passed": True}
    )
    accepted = (
        structural_verdict.get("strictly_eligible") is True
        and remainder_verdict.get("strictly_eligible") is True
        and shape.get("passed") is True
    )
    return {
        "rank": rank,
        "score": hypothesis.get("score"),
        "target_text": target,
        "structural_verdict": structural_verdict,
        "remainder_verdict": remainder_verdict,
        "illustration_word_target_shape": shape,
        "accepted": accepted,
        "raw_model_hypothesis": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
    }, rows


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_ILLUSTRATION_FEASIBILITY_ROOT", "work/illustration-feasibility")
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file():
        raise RuntimeError("illustration v3 requires persisted run-8 database")
    if v2._sha_file(database) != v2.BASE_DATABASE_SHA256:
        raise RuntimeError("illustration v3 database identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, v2.BASE_RUN_ID)
        rows = get_run_items(connection, v2.BASE_RUN_ID, kind="translation_segment")
        document = get_document(connection, int(dict(run.get("output") or {})["document_version_id"]))
    if str(run.get("output_sha256") or "") != v2.BASE_OUTPUT_SHA256:
        raise RuntimeError("illustration v3 Stage12 output identity drift")
    if str(document.get("text_sha256") or "") != v2.SOURCE_TEXT_SHA256:
        raise RuntimeError("illustration v3 source identity drift")
    content = str(document["content_text"])
    ordered = v2._ordered(rows)
    if "".join(str(row.get("source_text") or "") for row in ordered) != content:
        raise RuntimeError("run-8 source coverage is not byte-exact")
    labels = [m.group(0) for m in v2._LABEL_LINE_RE.finditer(content)]
    if len(labels) != v2.EXPECTED_CORPUS_LABEL_COUNT:
        raise RuntimeError(f"illustration label corpus count drift: {len(labels)}")
    base_inventory = v2._inventory(rows)
    if base_inventory["counts"] != {"numeric_symbol": 25, "punctuation": 33, "length": 0, "unique": 55}:
        raise RuntimeError(f"run-8 hard-gate inventory drift: {base_inventory['counts']}")

    attempts: list[dict[str, Any]] = []
    for row in ordered:
        split = v2._split_prefix(str(row.get("source_text") or ""))
        if split is None:
            continue
        flags = v2._gate_flags(row)
        if not any(flags.values()):
            continue
        structural, remainder = split
        model_input, normalized, candidate_kind = v2._model_input_for_remainder(remainder)
        attempts.append({
            "row": row,
            "structural": structural,
            "remainder": remainder,
            "model_input": model_input,
            "source_model_input_normalized": normalized,
            "candidate_kind": candidate_kind,
            "base_gate_failures": [name for name, failed in flags.items() if failed],
        })
    starts = [int(item["row"]["source_start"]) for item in attempts]
    if starts != v2.EXPECTED_SOURCE_STARTS:
        raise RuntimeError(f"illustration hard-failure cohort drift: {starts}")
    normalized_starts = [
        int(item["row"]["source_start"])
        for item in attempts
        if bool(item["source_model_input_normalized"])
    ]
    if normalized_starts != v2.EXPECTED_NORMALIZED_SOURCE_STARTS:
        raise RuntimeError(f"illustration normalized-input cohort drift: {normalized_starts}")

    normalized_attempts = [x for x in attempts if bool(x["source_model_input_normalized"])]
    ordinary_attempts = [x for x in attempts if not bool(x["source_model_input_normalized"])]
    translator = OpusTranslator(device="cpu", compute_type="float32")
    structural_generated = translator.translate(
        [str(x["model_input"]) for x in normalized_attempts],
        beam_size=STRUCTURAL_BEAM,
        num_hypotheses=STRUCTURAL_NBEST,
        max_decoding_length=128,
    )
    ordinary_generated = translator.translate(
        [str(x["model_input"]) for x in ordinary_attempts],
        beam_size=ORDINARY_BEAM,
        num_hypotheses=ORDINARY_NBEST,
        max_decoding_length=128,
    )
    if len(structural_generated) != len(normalized_attempts) or any(len(x) != STRUCTURAL_NBEST for x in structural_generated):
        raise RuntimeError("illustration structural-word n-best cardinality drift")
    if len(ordinary_generated) != len(ordinary_attempts) or any(len(x) != ORDINARY_NBEST for x in ordinary_generated):
        raise RuntimeError("illustration ordinary-suffix hypothesis cardinality drift")

    generated_by_start: dict[int, list[dict[str, Any]]] = {}
    for attempt, hypotheses in zip(normalized_attempts, structural_generated, strict=True):
        generated_by_start[int(attempt["row"]["source_start"])] = hypotheses
    for attempt, hypotheses in zip(ordinary_attempts, ordinary_generated, strict=True):
        generated_by_start[int(attempt["row"]["source_start"])] = hypotheses

    replacements: dict[int, list[dict[str, Any]]] = {}
    cases: list[dict[str, Any]] = []
    accepted_starts: list[int] = []
    for attempt in attempts:
        base = attempt["row"]
        start = int(base["source_start"])
        evaluated: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        selected_rows: list[dict[str, Any]] | None = None
        for rank, hypothesis in enumerate(generated_by_start[start]):
            evidence, candidate_rows = _evaluate(attempt, hypothesis, rank)
            evaluated.append(evidence)
            if selected is None and evidence.get("accepted") is True:
                selected = evidence
                selected_rows = candidate_rows
        if selected is not None and selected_rows is not None:
            replacements[start] = selected_rows
            accepted_starts.append(start)
        cases.append({
            "source_start": start,
            "source_end": int(base["source_end"]),
            "base_source": str(base.get("source_text") or ""),
            "base_target": str(base.get("target_text") or ""),
            "base_gate_failures": list(attempt["base_gate_failures"]),
            "structural_source": str(attempt["structural"]),
            "remainder_source": str(attempt["remainder"]),
            "model_input": str(attempt["model_input"]),
            "source_model_input_normalized": bool(attempt["source_model_input_normalized"]),
            "candidate_kind": str(attempt["candidate_kind"]),
            "beam_size": STRUCTURAL_BEAM if bool(attempt["source_model_input_normalized"]) else ORDINARY_BEAM,
            "num_hypotheses": len(generated_by_start[start]),
            "hypotheses": evaluated,
            "selected_rank": None if selected is None else int(selected["rank"]),
            "selected_target": None if selected is None else str(selected["target_text"]),
            "accepted": selected is not None,
            "raw_model_selected": selected is not None,
        })

    candidate_rows = v2._counterfactual(rows, replacements)
    if "".join(str(row.get("source_text") or "") for row in candidate_rows) != content:
        raise RuntimeError("illustration v3 counterfactual source coverage drift")
    counterfactual = v2._inventory(candidate_rows)
    if v2._sha_file(database) != v2.BASE_DATABASE_SHA256:
        raise RuntimeError("illustration v3 mutated read-only database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only source-owned illustration-label split with narrow raw n-best semantic selection for exact _Illustration._",
        "v1_negative_evidence": {
            "observed_raw_rank0_target": "*Иллюстрация._",
            "mechanical_hard_gates_missed_markup_corruption": True,
            "promotion_rejected": True,
        },
        "v2_negative_evidence": {
            "canonical_model_input": v2.ILLUSTRATION_WORD_MODEL_INPUT,
            "observed_raw_rank0_target": "Пример.",
            "wrong_structural_sense_rejected": True,
            "promotion_rejected": True,
        },
        "illustration_word_doe": DOE,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": v2.SOURCE_SHA256,
        "source_text_sha256": v2.SOURCE_TEXT_SHA256,
        "base_database_sha256": v2.BASE_DATABASE_SHA256,
        "base_translation_run_id": v2.BASE_RUN_ID,
        "base_translation_output_sha256": v2.BASE_OUTPUT_SHA256,
        "standalone_illustration_label_count": len(labels),
        "attempted_source_starts": starts,
        "normalized_model_input_source_starts": normalized_starts,
        "accepted_source_starts": accepted_starts,
        "attempt_count": len(attempts),
        "accepted_count": len(accepted_starts),
        "base_hard_gate_counts": base_inventory["counts"],
        "counterfactual_hard_gate_counts": counterfactual["counts"],
        "base_segment_count": len(rows),
        "counterfactual_segment_count": len(candidate_rows),
        "cases": cases,
        "nbest_scope": "exact _Illustration._ suffix only",
        "ordinary_suffix_policy": "exact source model input + raw rank0 only",
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-illustration-label-feasibility-v3.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "accepted_source_starts": accepted_starts,
        "selected": [
            {"source_start": x["source_start"], "rank": x["selected_rank"], "target": x["selected_target"]}
            for x in cases
        ],
        "base_hard_gate_counts": base_inventory["counts"],
        "counterfactual_hard_gate_counts": counterfactual["counts"],
        "evidence_sha256": payload["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
