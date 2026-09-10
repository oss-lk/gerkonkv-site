from __future__ import annotations

"""Research-only staged raw n-best audit for selective Stage12 rescue chunks.

Consumes the full-Opticks fail-closed Product baseline plus the persisted opt-in
selective-rescue audit. It does not alter Product Stage12 or choose a new
translation. For every context that the current rank-0 rescue mechanically
accepts, the exact source-derived rescue chunks are regenerated with staged
raw OPUS n-best. Every hypothesis is exported with the unchanged rescue
selector verdict so semantic review can determine whether the model already
contains a genuinely acceptable alternative.

No source/target rewriting, placeholders, literal insertion, corpus-specific
target patching, or Product database writes are permitted.
"""

from itertools import product
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import (
    RESCUE_CONTRACT,
    SELECTOR_CONTRACT,
    evaluate_rescue_pair,
)
from rocketdict.translation_stage import PLANNER_CONTRACT


SCHEMA = "rocketdict-full-opticks-selective-rescue-nbest-feasibility/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTIN_SCHEMA = "rocketdict-full-opticks-selective-rescue-optin/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
GENERATION_CELLS = (
    {"beam_size": 12, "num_hypotheses": 12},
    {"beam_size": 16, "num_hypotheses": 16},
)
BATCH_SIZE = 24
MAX_REVIEW_COMBINATIONS = 128


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _alpha_count(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _translate(
    translator: OpusTranslator,
    texts: list[str],
    *,
    beam_size: int,
    num_hypotheses: int,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=max_decoding_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("selective-rescue n-best translation cardinality mismatch")
    return output


def _candidate_record(
    hypothesis: dict[str, Any],
    *,
    model_index: int,
    source: str,
) -> dict[str, Any]:
    target = str(hypothesis.get("text") or "")
    verdict = evaluate_rescue_pair(source, target)
    rank_value = hypothesis.get("rank")
    return {
        "model_index": model_index,
        "rank": int(rank_value if rank_value is not None else model_index),
        "score": hypothesis.get("score"),
        "target_text": target,
        "verdict": verdict,
    }


def _combination_score(candidates: tuple[dict[str, Any], ...]) -> float:
    total = 0.0
    for candidate in candidates:
        score = candidate.get("score")
        if isinstance(score, (int, float)) and math.isfinite(float(score)):
            total += float(score)
    return total


def _combination_record(
    candidates: tuple[dict[str, Any], ...],
    *,
    primary_alpha: int,
) -> dict[str, Any]:
    target = "".join(str(candidate["target_text"]) for candidate in candidates)
    candidate_alpha = _alpha_count(target)
    return {
        "ranks": [int(candidate["rank"]) for candidate in candidates],
        "model_indices": [int(candidate["model_index"]) for candidate in candidates],
        "score_sum": _combination_score(candidates),
        "target_alpha": candidate_alpha,
        "target_alpha_non_decreasing": candidate_alpha >= primary_alpha,
        "target_text": target,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/full-opticks-numeric-stress",
        )
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    optin_path = root / "full-opticks-selective-rescue-optin.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    for path in (baseline_path, optin_path, database):
        if not path.is_file():
            raise RuntimeError(f"required selective-rescue n-best input is missing: {path}")

    baseline_bytes = baseline_path.read_bytes()
    optin_bytes = optin_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    optin = json.loads(optin_bytes.decode("utf-8"))
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise RuntimeError("unexpected full-Opticks numeric baseline schema")
    if optin.get("schema") != OPTIN_SCHEMA:
        raise RuntimeError("unexpected selective-rescue opt-in schema")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source identity drift")
    if optin.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("selective-rescue opt-in source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("n-best audit requires maintained planner-v8 baseline")
    if optin.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("n-best audit opt-in planner contract drift")
    if optin.get("rescue_contract") != RESCUE_CONTRACT:
        raise RuntimeError("n-best audit rescue contract drift")
    if optin.get("selector_contract") != SELECTOR_CONTRACT:
        raise RuntimeError("n-best audit selector contract drift")
    if optin.get("promotion_allowed") is not False:
        raise RuntimeError("opt-in evidence unexpectedly permits Product promotion")
    if optin.get("primary_identity_reused") is not True:
        raise RuntimeError("opt-in evidence does not prove primary identity reuse")
    if int(optin.get("baseline_hard_numeric_failure_count") or -1) != int(
        baseline.get("product_numeric_failure_count") or -2
    ):
        raise RuntimeError("opt-in baseline hard-failure count drift")

    accepted_contexts = list(optin.get("accepted_contexts") or [])
    if not accepted_contexts:
        raise RuntimeError(
            "no mechanically accepted selective-rescue context exists for n-best audit"
        )
    if len(accepted_contexts) != int(optin.get("accepted_context_count") or -1):
        raise RuntimeError("selective-rescue accepted context inventory drift")

    database_sha_before = _sha(database)
    max_planned_tokens = int(baseline.get("max_planned_unit_tokens") or 64)
    max_decoding_length = max(128, max_planned_tokens * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")

    contexts: list[dict[str, Any]] = []
    total_hypotheses = 0
    total_strict_hypotheses = 0
    cells_with_mechanical_combination = 0

    for context in accepted_contexts:
        context_sequence = int(context["context_sequence"])
        source = str(context["source_text"])
        selected_rows = list(context.get("selected_rows") or [])
        primary_rows = list(context.get("primary_rows") or [])
        if not selected_rows or not primary_rows:
            raise RuntimeError(
                f"context {context_sequence} lacks persisted rescue/primary rows"
            )
        if "".join(str(row.get("source_text") or "") for row in selected_rows) != source:
            raise RuntimeError(
                f"context {context_sequence} rescue rows do not cover source exactly"
            )

        primary_target = "".join(
            str(row.get("target_text") or "") for row in primary_rows
        )
        rank0_target = "".join(
            str(row.get("target_text") or "") for row in selected_rows
        )
        primary_alpha = _alpha_count(primary_target)
        source_chunks = [str(row.get("source_text") or "") for row in selected_rows]

        cells: list[dict[str, Any]] = []
        for generation in GENERATION_CELLS:
            generated = _translate(
                translator,
                source_chunks,
                beam_size=int(generation["beam_size"]),
                num_hypotheses=int(generation["num_hypotheses"]),
                max_decoding_length=max_decoding_length,
            )
            chunk_records: list[dict[str, Any]] = []
            strict_lists: list[list[dict[str, Any]]] = []
            for chunk_index, (row, hypotheses) in enumerate(
                zip(selected_rows, generated, strict=True)
            ):
                chunk_source = str(row.get("source_text") or "")
                if not hypotheses:
                    raise RuntimeError(
                        f"context {context_sequence} chunk {chunk_index} returned no hypotheses"
                    )
                candidates = [
                    _candidate_record(
                        hypothesis,
                        model_index=model_index,
                        source=chunk_source,
                    )
                    for model_index, hypothesis in enumerate(hypotheses)
                ]
                total_hypotheses += len(candidates)
                strict = [
                    candidate
                    for candidate in candidates
                    if (candidate.get("verdict") or {}).get("strictly_eligible") is True
                ]
                total_strict_hypotheses += len(strict)
                strict_lists.append(strict)
                chunk_records.append(
                    {
                        "chunk_index": chunk_index,
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": chunk_source,
                        "rank0_product_rescue_target_text": str(
                            row.get("target_text") or ""
                        ),
                        "candidate_count": len(candidates),
                        "strict_candidate_count": len(strict),
                        "strict_candidate_ranks": [
                            int(candidate["rank"]) for candidate in strict
                        ],
                        "candidates": candidates,
                    }
                )

            raw_combination_count = (
                math.prod(len(values) for values in strict_lists)
                if strict_lists and all(strict_lists)
                else 0
            )
            mechanically_accepted: list[dict[str, Any]] = []
            mechanically_accepted_count = 0
            if raw_combination_count:
                for combo in product(*strict_lists):
                    record = _combination_record(
                        combo,
                        primary_alpha=primary_alpha,
                    )
                    if record["target_alpha_non_decreasing"] is True:
                        mechanically_accepted_count += 1
                        mechanically_accepted.append(record)
                mechanically_accepted.sort(
                    key=lambda row: (
                        -float(row["score_sum"]),
                        tuple(int(value) for value in row["ranks"]),
                    )
                )
            if mechanically_accepted_count:
                cells_with_mechanical_combination += 1

            cells.append(
                {
                    "generation": dict(generation),
                    "chunk_count": len(chunk_records),
                    "chunks": chunk_records,
                    "strict_cartesian_combination_count_before_alpha_gate": raw_combination_count,
                    "mechanically_accepted_combination_count": mechanically_accepted_count,
                    "review_combination_limit": MAX_REVIEW_COMBINATIONS,
                    "review_combinations": mechanically_accepted[
                        :MAX_REVIEW_COMBINATIONS
                    ],
                }
            )

        contexts.append(
            {
                "context_sequence": context_sequence,
                "source_start": int(context["source_start"]),
                "source_end": int(context["source_end"]),
                "source_text": source,
                "primary_target_text": primary_target,
                "rank0_product_rescue_target_text": rank0_target,
                "primary_target_alpha": primary_alpha,
                "missing_literal_count": int(
                    context.get("missing_literal_count") or 0
                ),
                "cells": cells,
            }
        )

    database_sha_after = _sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("selective-rescue n-best audit mutated Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "narrow staged raw-OPUS n-best feasibility on source-defined contexts "
            "already mechanically accepted by the research-only selective Stage12 rescue"
        ),
        "promotion_allowed": False,
        "semantic_review_required": True,
        "automatic_semantic_selector": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(baseline.get("source_text_sha256") or ""),
        "planner_contract": PLANNER_CONTRACT,
        "rescue_contract": RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "baseline_evidence_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "optin_evidence_sha256": hashlib.sha256(optin_bytes).hexdigest(),
        "primary_translation_run_id": int(optin["primary_translation_run_id"]),
        "primary_output_sha256": str(optin["primary_output_sha256"]),
        "generation_cells": [dict(cell) for cell in GENERATION_CELLS],
        "max_decoding_length": max_decoding_length,
        "accepted_context_count": len(contexts),
        "accepted_context_sequences": [
            int(context["context_sequence"]) for context in contexts
        ],
        "total_raw_hypothesis_count": total_hypotheses,
        "total_strict_hypothesis_count": total_strict_hypotheses,
        "generation_cell_context_pairs_with_mechanically_accepted_combination": (
            cells_with_mechanical_combination
        ),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
        "contexts": contexts,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-selective-rescue-nbest-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "accepted_context_count": payload["accepted_context_count"],
                "accepted_context_sequences": payload["accepted_context_sequences"],
                "total_raw_hypothesis_count": total_hypotheses,
                "total_strict_hypothesis_count": total_strict_hypotheses,
                "generation_cell_context_pairs_with_mechanically_accepted_combination": (
                    cells_with_mechanical_combination
                ),
                "database_mutated": False,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
