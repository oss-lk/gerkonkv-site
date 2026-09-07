from __future__ import annotations

"""Research-only fine-grained clause + raw n-best feasibility probe.

This probe consumes only failures left by the broader clause-planning probe.
It never names a challenge sequence directly.  Source punctuation determines
all clause boundaries, every source byte remains represented in the plan, and
selection is restricted to raw OPUS hypotheses.  No placeholder round-trip,
post-translation literal injection, target rewriting, or Product-default change
is allowed by this experiment.
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

SCHEMA = "rocketdict-maintained-r1-clause-nbest-feasibility/1"
CELLS = (
    {"soft_max_words": 8, "beam_size": 6, "num_hypotheses": 1},
    {"soft_max_words": 10, "beam_size": 6, "num_hypotheses": 1},
    {"soft_max_words": 12, "beam_size": 6, "num_hypotheses": 1},
    {"soft_max_words": 8, "beam_size": 8, "num_hypotheses": 8},
    {"soft_max_words": 10, "beam_size": 8, "num_hypotheses": 8},
    {"soft_max_words": 12, "beam_size": 8, "num_hypotheses": 8},
)


def _local_row(parent: dict[str, Any], source_text: str) -> dict[str, Any]:
    return {
        "sequence_number": int(parent["sequence_number"]),
        "source_start": parent.get("source_start"),
        "source_end": parent.get("source_end"),
        "source_text": source_text,
        "target_text": None,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_TRANSLATION_CHALLENGE_ROOT", "work/translation-challenge")
    ).resolve()
    baseline_path = root / "maintained-r1-baseline.json"
    clause_path = root / "maintained-r1-clause-planning-feasibility.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not clause_path.is_file() or not database.is_file():
        raise RuntimeError("Fine-grained clause n-best prerequisites are missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    clause = json.loads(clause_path.read_text(encoding="utf-8"))
    selection_sha = str((baseline.get("selection") or {}).get("selection_sha256") or "")
    if selection_sha != EXPECTED_SELECTION_SHA256:
        raise RuntimeError("Frozen R1 selection identity drift")
    if clause.get("selection_sha256") != selection_sha:
        raise RuntimeError("Clause evidence is not bound to the frozen R1 selection")

    scoped_sequences = [int(value) for value in clause.get("failed_sequences") or []]
    if not scoped_sequences:
        raise RuntimeError("No broad-clause residuals remain for fine-grained n-best")

    assembly_id = int((baseline.get("stage14") or {})["assembly_id"])
    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        rows = get_run_items(connection, assembly_id, kind="assembly_segment")
        translation_run = get_run(connection, translation_run_id)
        gate_rows = connection.execute(
            "SELECT implementation, parameters_json FROM stage_runs "
            "WHERE stage_number=15 AND status='completed' ORDER BY id"
        ).fetchall()

    by_sequence = {int(row["sequence_number"]): row for row in rows}
    if any(sequence not in by_sequence for sequence in scoped_sequences):
        raise RuntimeError("Fine-grained clause scope references a missing assembly segment")
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

    translation_output = dict(translation_run.get("output") or {})
    max_unit_tokens = int(translation_output.get("max_translation_unit_tokens") or 64)
    max_decoding_length = max(128, max_unit_tokens * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    results: list[dict[str, Any]] = []

    for sequence in scoped_sequences:
        row = by_sequence[sequence]
        source = str(row.get("source_text") or "")
        cell_results: list[dict[str, Any]] = []
        for cell in CELLS:
            groups = _soft_groups(source, max_words=int(cell["soft_max_words"]))
            plan: list[dict[str, Any]] = []
            jobs: list[str] = []
            for group in groups:
                leading, core, trailing = _prose_core(str(group["text"]))
                planned = {
                    **group,
                    "leading_whitespace": leading,
                    "core": core,
                    "trailing_whitespace": trailing,
                }
                plan.append(planned)
                if core:
                    jobs.append(core)

            generated = (
                translator.translate(
                    jobs,
                    beam_size=int(cell["beam_size"]),
                    num_hypotheses=int(cell["num_hypotheses"]),
                    max_decoding_length=max_decoding_length,
                )
                if jobs
                else []
            )
            if len(generated) != sum(1 for group in plan if group["core"]):
                raise RuntimeError("Fine-grained clause translation cardinality mismatch")

            generated_iter = iter(generated)
            target_parts: list[str] = []
            public_plan: list[dict[str, Any]] = []
            all_groups_selected = True
            for group in plan:
                core = str(group["core"])
                selected: dict[str, Any] | None = None
                candidates: list[dict[str, Any]] = []
                if core:
                    hypotheses = next(generated_iter)
                    if not hypotheses:
                        raise RuntimeError(
                            f"OPUS returned no fine-grained hypothesis for sequence {sequence}"
                        )
                    local_row = _local_row(row, core)
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
                        "core": core,
                        "word_count": group["word_count"],
                        "primitive_count": group["primitive_count"],
                        "selected_rank": selected["rank"] if selected is not None else None,
                        "selected_target_text": (
                            selected["target_text"] if selected is not None else None
                        ),
                        "candidates": candidates,
                    }
                )

            candidate_target = "".join(target_parts) if all_groups_selected else None
            global_verdict = (
                _verdict(
                    row,
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
                "segment_sequence": sequence,
                "source_text": source,
                "baseline_target_text": str(row.get("target_text") or ""),
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

    rescued_sequences = [
        int(row["segment_sequence"]) for row in results if row["rescued_any_cell"] is True
    ]
    failed_sequences = [
        int(row["segment_sequence"]) for row in results if row["rescued_any_cell"] is not True
    ]
    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Fine-grained clause n-best mutated the frozen R1 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "fine-grained source-clause planning plus strict raw-model n-best selection",
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "selection_sha256": selection_sha,
        "parent_clause_evidence_sha256": str(clause.get("evidence_sha256") or ""),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "cells": [dict(cell) for cell in CELLS],
        "selection_policy": (
            "within each source-punctuation clause group, select the first/highest raw OPUS "
            "hypothesis passing the same strict local Product/research verdict; require every "
            "group and the recomposed segment to pass; never rewrite a hypothesis"
        ),
        "scoped_sequences": scoped_sequences,
        "rescued_count": len(rescued_sequences),
        "rescued_sequences": rescued_sequences,
        "failed_count": len(failed_sequences),
        "failed_sequences": failed_sequences,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-clause-nbest-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "scoped_sequences": scoped_sequences,
                "rescued_sequences": rescued_sequences,
                "failed_sequences": failed_sequences,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
