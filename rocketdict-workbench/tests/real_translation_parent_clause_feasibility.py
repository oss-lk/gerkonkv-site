from __future__ import annotations

"""Research-only full-parent soft-clause feasibility probe for R1 residuals.

The previous punctuation-preferred 64-token boundary probe preserves parent
context but can still leave a long numeric enumeration in one MT unit.  This
probe consumes only parent contexts that that experiment failed to rescue and
replans the complete parent text at existing source comma/semicolon/colon
boundaries with a soft word budget.  No sequence id is hand-picked, no source
byte is dropped, and no target token/number is synthesized or rewritten.

This remains mechanism evidence only: even a strict mechanical pass requires
manual semantic review before any Product policy can be promoted.
"""

import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_run, get_run_items
from rocketdict.runtime import OpusTranslator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_clause_planning_feasibility import (  # noqa: E402
    EXPECTED_SELECTION_SHA256,
    _canonical_sha,
    _parameters,
    _prose_core,
    _sha_file,
    _soft_groups,
    _verdict,
)

SCHEMA = "rocketdict-maintained-r1-parent-clause-feasibility/1"
CELLS = (
    {"soft_max_words": 12, "beam_size": 6, "num_hypotheses": 1},
    {"soft_max_words": 18, "beam_size": 6, "num_hypotheses": 1},
    {"soft_max_words": 24, "beam_size": 6, "num_hypotheses": 1},
    {"soft_max_words": 12, "beam_size": 8, "num_hypotheses": 8},
    {"soft_max_words": 18, "beam_size": 8, "num_hypotheses": 8},
)


def _candidate_row(source_text: str, sequence: int) -> dict[str, Any]:
    return {
        "sequence_number": sequence,
        "source_start": None,
        "source_end": None,
        "source_text": source_text,
        "target_text": None,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_TRANSLATION_CHALLENGE_ROOT", "work/translation-challenge")
    ).resolve()
    baseline_path = root / "maintained-r1-baseline.json"
    boundary_path = root / "maintained-r1-context-boundary-feasibility.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not boundary_path.is_file() or not database.is_file():
        raise RuntimeError("Parent-clause probe prerequisites are missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    selection_sha = str((baseline.get("selection") or {}).get("selection_sha256") or "")
    if selection_sha != EXPECTED_SELECTION_SHA256:
        raise RuntimeError("Frozen R1 selection identity drift")
    if boundary.get("selection_sha256") != selection_sha:
        raise RuntimeError("Context-boundary evidence is not bound to the frozen R1 selection")

    failed_parents = [
        row
        for row in list(boundary.get("parent_contexts") or [])
        if row.get("rescued_any_cell") is not True
    ]
    if not failed_parents:
        payload: dict[str, Any] = {
            "schema": SCHEMA,
            "purpose": "no-op: context-boundary probe left no failed parent contexts",
            "promotion_allowed": False,
            "no_synthetic_target_repair": True,
            "selection_sha256": selection_sha,
            "parent_boundary_evidence_sha256": str(boundary.get("evidence_sha256") or ""),
            "failed_parent_contexts": [],
            "parent_contexts": [],
        }
        payload["evidence_sha256"] = _canonical_sha(payload)
        output = root / "maintained-r1-parent-clause-feasibility.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        translation_run = get_run(connection, translation_run_id)
        translation_output = dict(translation_run.get("output") or {})
        context_run_id = int(translation_output["context_run_id"])
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        gate_rows = connection.execute(
            "SELECT implementation, parameters_json FROM stage_runs "
            "WHERE stage_number=15 AND status='completed' ORDER BY id"
        ).fetchall()

    context_by_sequence = {int(row["sequence_number"]): row for row in context_rows}
    gate_parameters = {
        str(row["implementation"]): _parameters(row["parameters_json"])
        for row in gate_rows
    }
    punctuation_parameters = dict(
        gate_parameters.get("rocketdict-punctuation-preservation") or {}
    )
    length_parameters = dict(gate_parameters.get("rocketdict-length-ratio-proxy") or {})
    if not length_parameters:
        raise RuntimeError("R1 database lacks recorded length-ratio parameters")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    results: list[dict[str, Any]] = []

    for parent_index, parent in enumerate(failed_parents):
        first = int(parent["context_sentence_start"])
        last = int(parent["context_sentence_end"])
        parts = [context_by_sequence[index] for index in range(first, last + 1)]
        for left, right in zip(parts, parts[1:]):
            if int(left["source_end"]) != int(right["source_start"]):
                raise RuntimeError("Parent context rows are not contiguous")
        source = "".join(str(row.get("source_text") or "") for row in parts)
        recorded_source = str(parent.get("source_text") or "")
        if recorded_source and source != recorded_source:
            raise RuntimeError("Parent context source differs from bound context-boundary evidence")

        cell_results: list[dict[str, Any]] = []
        for cell in CELLS:
            groups = _soft_groups(source, max_words=int(cell["soft_max_words"]))
            plan: list[dict[str, Any]] = []
            jobs: list[str] = []
            for group in groups:
                leading, core, trailing = _prose_core(str(group["text"]))
                plan.append(
                    {
                        **group,
                        "leading_whitespace": leading,
                        "core": core,
                        "trailing_whitespace": trailing,
                    }
                )
                if core:
                    jobs.append(core)

            generated = translator.translate(
                jobs,
                beam_size=int(cell["beam_size"]),
                num_hypotheses=int(cell["num_hypotheses"]),
                max_decoding_length=512,
            ) if jobs else []
            if len(generated) != sum(1 for group in plan if group["core"]):
                raise RuntimeError("Parent-clause translation cardinality mismatch")

            generated_iter = iter(generated)
            public_plan: list[dict[str, Any]] = []
            target_parts: list[str] = []
            all_groups_selected = True
            for group_index, group in enumerate(plan):
                core = str(group["core"])
                candidates: list[dict[str, Any]] = []
                selected: dict[str, Any] | None = None
                if core:
                    hypotheses = next(generated_iter)
                    local_row = _candidate_row(core, parent_index * 1000 + group_index)
                    for hypothesis in hypotheses:
                        target = str(hypothesis.get("text") or "")
                        verdict = _verdict(
                            local_row,
                            target,
                            punctuation_parameters=punctuation_parameters,
                            length_parameters=length_parameters,
                        )
                        candidate = {
                            "rank": int(hypothesis.get("rank") or 0),
                            "score": hypothesis.get("score"),
                            "target_text": target,
                            "verdict": verdict,
                        }
                        candidates.append(candidate)
                        if selected is None and verdict["strictly_eligible"] is True:
                            selected = candidate
                    if selected is None:
                        all_groups_selected = False
                        selected_text = ""
                    else:
                        selected_text = str(selected["target_text"])
                    target_parts.append(
                        str(group["leading_whitespace"])
                        + selected_text
                        + str(group["trailing_whitespace"])
                    )
                else:
                    target_parts.append(str(group["text"]))

                public_plan.append(
                    {
                        "source_text": group["text"],
                        "word_count": group["word_count"],
                        "primitive_count": group["primitive_count"],
                        "selected_rank": selected["rank"] if selected is not None else None,
                        "selected_target_text": selected["target_text"] if selected is not None else None,
                        "candidates": candidates,
                    }
                )

            candidate_target = "".join(target_parts) if all_groups_selected else None
            global_verdict = (
                _verdict(
                    _candidate_row(source, parent_index),
                    candidate_target,
                    punctuation_parameters=punctuation_parameters,
                    length_parameters=length_parameters,
                )
                if candidate_target is not None
                else None
            )
            rescued = bool(
                all_groups_selected
                and global_verdict is not None
                and global_verdict["strictly_eligible"] is True
            )
            cell_results.append(
                {
                    "config": dict(cell),
                    "group_count": len(groups),
                    "all_groups_selected": all_groups_selected,
                    "candidate_target_text": candidate_target,
                    "global_verdict": global_verdict,
                    "rescued": rescued,
                    "plan": public_plan,
                }
            )

        successful = [cell for cell in cell_results if cell["rescued"] is True]
        results.append(
            {
                "context_sentence_start": first,
                "context_sentence_end": last,
                "child_failure_sequences": list(parent.get("child_failure_sequences") or []),
                "source_text": source,
                "cells": cell_results,
                "rescued_any_cell": bool(successful),
                "successful_cells": [
                    {
                        "config": cell["config"],
                        "group_count": cell["group_count"],
                        "candidate_target_text": cell["candidate_target_text"],
                    }
                    for cell in successful
                ],
            }
        )

    rescued_contexts = [
        [int(row["context_sentence_start"]), int(row["context_sentence_end"])]
        for row in results
        if row["rescued_any_cell"] is True
    ]
    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Parent-clause feasibility probe mutated frozen R1 database")

    payload = {
        "schema": SCHEMA,
        "purpose": "full-parent soft clause planning after boundary-only residuals",
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "selection_sha256": selection_sha,
        "parent_boundary_evidence_sha256": str(boundary.get("evidence_sha256") or ""),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "cells": [dict(cell) for cell in CELLS],
        "cut_policy": (
            "complete parent context; comma/semicolon/colon primitive clauses; soft source-word "
            "budget; no hard fallback cut; adjacent clauses stay grouped while within budget"
        ),
        "failed_parent_context_count": len(failed_parents),
        "rescued_parent_contexts": rescued_contexts,
        "parent_contexts": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-parent-clause-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "failed_parent_context_count": len(failed_parents),
                "rescued_parent_contexts": rescued_contexts,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
