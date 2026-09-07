from __future__ import annotations

"""Research-only n-best feasibility audit for the frozen maintained R1 run.

This script never mutates Product output or the R1 database.  It asks the exact
pinned OPUS model for additional *raw model hypotheses* only on units whose
current rank-0 target fails a Product hard gate or a maintained structural
research diagnostic.  A candidate is considered strictly eligible only when it
passes all current Product hard gates plus numeric-order, delimiter and critical
technical-token preservation.  No target rewriting, placeholder repair or
literal injection is allowed.
"""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_run, get_run_items
from rocketdict.numeric_integrity import CONTRACT as NUMERIC_CONTRACT
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair
from rocketdict.research_diagnostics import (
    CRITICAL_TOKEN_CONTRACT,
    DELIMITER_CONTRACT,
    NUMERIC_ORDER_CONTRACT,
    compare_critical_technical_tokens,
    compare_delimiter_preservation,
    compare_numeric_order,
)
from rocketdict.runtime import OpusTranslator
from rocketdict.stages import _length_issues, _punctuation_issues

SCHEMA = "rocketdict-maintained-r1-nbest-feasibility/1"
EXPECTED_SELECTION_SHA256 = "665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32"
GENERATION_CELLS = (
    {"beam_size": 6, "num_hypotheses": 6},
    {"beam_size": 12, "num_hypotheses": 12},
    {"beam_size": 16, "num_hypotheses": 16},
)


def _sha_file(path: Path) -> str:
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


def _parameters(raw: str | None) -> dict[str, Any]:
    value = json.loads(str(raw or "{}"))
    if not isinstance(value, dict):
        raise RuntimeError("Stage15 parameters_json is not an object")
    return value


def _candidate_row(source_row: dict[str, Any], target: str) -> dict[str, Any]:
    return {
        "sequence_number": int(source_row["sequence_number"]),
        "source_start": source_row.get("source_start"),
        "source_end": source_row.get("source_end"),
        "source_text": str(source_row.get("source_text") or ""),
        "target_text": target,
    }


def _verdict(
    source_row: dict[str, Any],
    target: str,
    *,
    punctuation_parameters: dict[str, Any],
    length_parameters: dict[str, Any],
) -> dict[str, Any]:
    source = str(source_row.get("source_text") or "")
    probe = _candidate_row(source_row, target)
    numeric = evaluate_numeric_symbol_pair(source, target)
    punctuation_issues = _punctuation_issues([probe], punctuation_parameters)
    length_issues = _length_issues([probe], length_parameters)
    numeric_order = compare_numeric_order(source, target)
    delimiters = compare_delimiter_preservation(source, target)
    critical = compare_critical_technical_tokens(source, target)
    product_hard_passed = (
        numeric["passed"] is True
        and not punctuation_issues
        and not length_issues
        and bool(target.strip())
    )
    strict_research_passed = (
        numeric_order["passed"] is True
        and delimiters["passed"] is True
        and critical["passed"] is True
    )
    return {
        "product_hard_passed": product_hard_passed,
        "strict_research_passed": strict_research_passed,
        "strictly_eligible": product_hard_passed and strict_research_passed,
        "numeric_symbol": numeric,
        "punctuation_issues": punctuation_issues,
        "length_issues": length_issues,
        "numeric_order": numeric_order,
        "delimiter_preservation": delimiters,
        "critical_technical_tokens": critical,
    }


def _safe_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TRANSLATION_CHALLENGE_ROOT",
            "work/translation-challenge",
        )
    ).resolve()
    baseline_path = root / "maintained-r1-baseline.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Frozen maintained R1 baseline/database is missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    selection_sha = str((baseline.get("selection") or {}).get("selection_sha256") or "")
    if selection_sha != EXPECTED_SELECTION_SHA256:
        raise RuntimeError(
            f"Frozen R1 selection drift: {selection_sha} != {EXPECTED_SELECTION_SHA256}"
        )
    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    assembly_id = int((baseline.get("stage14") or {})["assembly_id"])
    database_sha_before = _sha_file(database)

    with connect(database, readonly=True) as connection:
        translation_run = get_run(connection, translation_run_id)
        assembly_run = get_run(connection, assembly_id)
        rows = get_run_items(connection, assembly_id, kind="assembly_segment")
        gate_rows = connection.execute(
            "SELECT implementation, parameters_json FROM stage_runs "
            "WHERE stage_number=15 AND status='completed' AND assembly_id IS NULL "
            "ORDER BY id"
        ).fetchall() if False else connection.execute(
            "SELECT implementation, parameters_json FROM stage_runs "
            "WHERE stage_number=15 AND status='completed' ORDER BY id"
        ).fetchall()

    if not rows:
        raise RuntimeError("Frozen R1 Stage14 assembly contains no segments")
    gate_parameters = {
        str(row["implementation"]): _parameters(row["parameters_json"])
        for row in gate_rows
    }
    punctuation_parameters = dict(
        gate_parameters.get("rocketdict-punctuation-preservation") or {}
    )
    length_parameters = dict(
        gate_parameters.get("rocketdict-length-ratio-proxy") or {}
    )
    if not length_parameters:
        raise RuntimeError("Frozen R1 database lacks recorded length-ratio gate parameters")

    baseline_rows: list[dict[str, Any]] = []
    problem_rows: list[dict[str, Any]] = []
    hard_problem_sequences: list[int] = []
    research_only_problem_sequences: list[int] = []
    for row in rows:
        target = str(row.get("target_text") or "")
        verdict = _verdict(
            row,
            target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        record = {
            "segment_sequence": int(row["sequence_number"]),
            "source_start": row.get("source_start"),
            "source_end": row.get("source_end"),
            "source_text": str(row.get("source_text") or ""),
            "target_text": target,
            "verdict": verdict,
        }
        baseline_rows.append(record)
        if verdict["strictly_eligible"] is not True:
            problem_rows.append(row)
            if verdict["product_hard_passed"] is not True:
                hard_problem_sequences.append(int(row["sequence_number"]))
            else:
                research_only_problem_sequences.append(int(row["sequence_number"]))

    translation_output = dict(translation_run.get("output") or {})
    max_unit_tokens = int(translation_output.get("max_translation_unit_tokens") or 64)
    max_decoding_length = max(128, max_unit_tokens * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    texts = [str(row.get("source_text") or "") for row in problem_rows]

    results_by_sequence: dict[int, dict[str, Any]] = {
        int(row["sequence_number"]): {
            "segment_sequence": int(row["sequence_number"]),
            "source_start": row.get("source_start"),
            "source_end": row.get("source_end"),
            "source_text": str(row.get("source_text") or ""),
            "baseline": next(
                item
                for item in baseline_rows
                if item["segment_sequence"] == int(row["sequence_number"])
            ),
            "cells": [],
        }
        for row in problem_rows
    }

    for cell in GENERATION_CELLS:
        generated = translator.translate(
            texts,
            beam_size=int(cell["beam_size"]),
            num_hypotheses=int(cell["num_hypotheses"]),
            max_decoding_length=max_decoding_length,
        )
        if len(generated) != len(problem_rows):
            raise RuntimeError("n-best probe output cardinality differs from problem-unit count")
        for row, hypotheses in zip(problem_rows, generated, strict=True):
            candidates: list[dict[str, Any]] = []
            selected_rank: int | None = None
            for hypothesis in hypotheses:
                target = str(hypothesis.get("text") or "")
                verdict = _verdict(
                    row,
                    target,
                    punctuation_parameters=punctuation_parameters,
                    length_parameters=length_parameters,
                )
                candidate = {
                    "rank": int(hypothesis["rank"]),
                    "score": hypothesis.get("score"),
                    "target_text": target,
                    "verdict": verdict,
                }
                candidates.append(candidate)
                if selected_rank is None and verdict["strictly_eligible"] is True:
                    selected_rank = int(hypothesis["rank"])
            results_by_sequence[int(row["sequence_number"])]["cells"].append(
                {
                    "config": dict(cell),
                    "candidate_count": len(candidates),
                    "strictly_eligible_count": sum(
                        1 for candidate in candidates if candidate["verdict"]["strictly_eligible"] is True
                    ),
                    "selected_rank": selected_rank,
                    "selected_target_text": (
                        next(
                            candidate["target_text"]
                            for candidate in candidates
                            if candidate["rank"] == selected_rank
                        )
                        if selected_rank is not None
                        else None
                    ),
                    "candidates": candidates,
                }
            )

    problem_results = [results_by_sequence[key] for key in sorted(results_by_sequence)]
    for row in problem_results:
        successful_cells = [cell for cell in row["cells"] if cell["selected_rank"] is not None]
        row["rescuable_any_cell"] = bool(successful_cells)
        row["successful_cells"] = [
            {
                "config": cell["config"],
                "selected_rank": cell["selected_rank"],
                "selected_target_text": cell["selected_target_text"],
            }
            for cell in successful_cells
        ]

    rescuable_sequences = [
        int(row["segment_sequence"])
        for row in problem_results
        if row["rescuable_any_cell"] is True
    ]
    unrescued_sequences = [
        int(row["segment_sequence"])
        for row in problem_results
        if row["rescuable_any_cell"] is not True
    ]
    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Research-only n-best probe mutated the frozen R1 Product database")

    asset = translator.asset
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "feasibility only; no Product target rewriting and no Product default mutation",
        "promotion_allowed": False,
        "selection_policy": (
            "within each explicit generation cell, first/highest model-rank raw OPUS hypothesis "
            "passing all current Product hard gates plus maintained numeric-order, delimiter and "
            "critical technical-token diagnostics"
        ),
        "no_synthetic_target_repair": True,
        "selection_sha256": selection_sha,
        "baseline_evidence_sha256": _sha_file(baseline_path),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "assembly_id": assembly_id,
        "assembly_output_sha256": str(assembly_run.get("output_sha256") or ""),
        "translation_run_id": translation_run_id,
        "translation_output_sha256": str(translation_run.get("output_sha256") or ""),
        "stage12_planner_contract": translation_output.get("planner_contract"),
        "baseline_stage12_segment_count": int(translation_output.get("segment_count") or len(rows)),
        "generation_cells": [dict(cell) for cell in GENERATION_CELLS],
        "max_decoding_length": max_decoding_length,
        "gate_parameters": {
            "punctuation": punctuation_parameters,
            "length_ratio": length_parameters,
        },
        "contracts": {
            "numeric_symbol": NUMERIC_CONTRACT,
            "numeric_order": NUMERIC_ORDER_CONTRACT,
            "delimiter": DELIMITER_CONTRACT,
            "critical_technical_token": CRITICAL_TOKEN_CONTRACT,
            "punctuation": "current rocketdict.stages._punctuation_issues runtime semantics",
            "length_ratio": "current rocketdict.stages._length_issues runtime semantics",
        },
        "model": {
            "revision": asset.revision,
            "source_archive_sha256": asset.source_archive_sha256,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "compute_type": "float32",
            "device": "cpu",
            "ctranslate2_version": _safe_version("ctranslate2"),
            "sentencepiece_version": _safe_version("sentencepiece"),
        },
        "baseline_segment_count": len(rows),
        "problem_unit_count": len(problem_rows),
        "hard_problem_sequences": sorted(hard_problem_sequences),
        "research_only_problem_sequences": sorted(research_only_problem_sequences),
        "rescuable_any_cell_count": len(rescuable_sequences),
        "rescuable_any_cell_sequences": rescuable_sequences,
        "unrescued_count": len(unrescued_sequences),
        "unrescued_sequences": unrescued_sequences,
        "problem_units": problem_results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-nbest-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "problem_unit_count": len(problem_rows),
                "hard_problem_sequences": sorted(hard_problem_sequences),
                "research_only_problem_sequences": sorted(research_only_problem_sequences),
                "rescuable_any_cell_sequences": rescuable_sequences,
                "unrescued_sequences": unrescued_sequences,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
