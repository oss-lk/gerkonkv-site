from __future__ import annotations

"""Research-only Stage12 context-boundary feasibility probe.

The probe starts from residual segments that broad clause planning could not
rescue, then reconstructs each segment's complete Stage10 parent context.  It
models one narrow planner change: before a preferred-token hard cut, prefer the
nearest preceding source comma/semicolon/colon boundary within a controlled
fraction of the token budget.  Every source byte remains in exactly one group.
Raw OPUS hypotheses are selected only when they pass the maintained strict local
integrity/structure verdict; the recomposed complete parent context must pass as
well.  No target rewriting, placeholder repair, literal injection or Product DB
mutation is allowed.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_stage import _balanced_protected_spans, _cut_inside_span

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_clause_planning_feasibility import (  # noqa: E402
    EXPECTED_SELECTION_SHA256,
    _canonical_sha,
    _parameters,
    _prose_core,
    _sha_file,
    _verdict,
)

SCHEMA = "rocketdict-maintained-r1-context-boundary-feasibility/1"
CELLS = (
    {"preferred_tokens": 64, "minimum_fraction": 0.50, "beam_size": 6, "num_hypotheses": 1},
    {"preferred_tokens": 64, "minimum_fraction": 0.65, "beam_size": 6, "num_hypotheses": 1},
    {"preferred_tokens": 64, "minimum_fraction": 0.80, "beam_size": 6, "num_hypotheses": 1},
    {"preferred_tokens": 64, "minimum_fraction": 0.65, "beam_size": 8, "num_hypotheses": 8},
)
_BOUNDARY_PUNCTUATION = (",", ";", ":")


def _candidate_row(source_text: str, sequence: int) -> dict[str, Any]:
    return {
        "sequence_number": sequence,
        "source_start": None,
        "source_end": None,
        "source_text": source_text,
        "target_text": None,
    }


def _preferred_groups(
    content: str,
    tokens: list[dict[str, Any]],
    *,
    absolute_start: int,
    preferred_tokens: int,
    minimum_fraction: float,
) -> list[dict[str, Any]]:
    if not 0 < minimum_fraction <= 1:
        raise RuntimeError("minimum_fraction must be in (0, 1]")
    if preferred_tokens < 2:
        raise RuntimeError("preferred_tokens must be at least 2")
    absolute_end = absolute_start + len(content)
    spans = _balanced_protected_spans(content, absolute_start=absolute_start)
    groups: list[dict[str, Any]] = []
    token_index = 0
    cursor = absolute_start
    while token_index < len(tokens):
        desired = min(token_index + preferred_tokens, len(tokens))
        split_index = desired
        boundary_preferred = False
        if desired < len(tokens):
            minimum_advance = max(1, int(preferred_tokens * minimum_fraction))
            minimum_index = min(desired, token_index + minimum_advance)
            for index in range(desired, minimum_index - 1, -1):
                cut = int(tokens[index]["source_start"])
                if _cut_inside_span(cut, spans):
                    continue
                prefix = content[cursor - absolute_start : cut - absolute_start]
                if prefix.rstrip().endswith(_BOUNDARY_PUNCTUATION):
                    split_index = index
                    boundary_preferred = True
                    break
            if not boundary_preferred:
                for index in range(desired, len(tokens)):
                    cut = int(tokens[index]["source_start"])
                    if not _cut_inside_span(cut, spans):
                        split_index = index
                        break
                else:
                    split_index = len(tokens)
        if split_index <= token_index:
            raise RuntimeError("Context-boundary planner failed to advance")
        cut = absolute_end if split_index >= len(tokens) else int(tokens[split_index]["source_start"])
        if cut <= cursor:
            raise RuntimeError("Context-boundary planner produced a non-positive group")
        text = content[cursor - absolute_start : cut - absolute_start]
        groups.append(
            {
                "source_start": cursor,
                "source_end": cut,
                "source_text": text,
                "token_start": token_index,
                "token_end": split_index,
                "token_count": split_index - token_index,
                "boundary_preferred": boundary_preferred,
            }
        )
        cursor = cut
        token_index = split_index
    if cursor != absolute_end:
        raise RuntimeError("Context-boundary planner did not cover parent context")
    if "".join(group["source_text"] for group in groups) != content:
        raise RuntimeError("Context-boundary planner source coverage is not byte-exact")
    return groups


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_TRANSLATION_CHALLENGE_ROOT", "work/translation-challenge")
    ).resolve()
    baseline_path = root / "maintained-r1-baseline.json"
    clause_path = root / "maintained-r1-clause-planning-feasibility.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not clause_path.is_file() or not database.is_file():
        raise RuntimeError("Context-boundary probe prerequisites are missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    clause = json.loads(clause_path.read_text(encoding="utf-8"))
    selection_sha = str((baseline.get("selection") or {}).get("selection_sha256") or "")
    if selection_sha != EXPECTED_SELECTION_SHA256:
        raise RuntimeError("Frozen R1 selection identity drift")
    if clause.get("selection_sha256") != selection_sha:
        raise RuntimeError("Clause evidence is not bound to the frozen R1 selection")
    scoped_sequences = [int(value) for value in clause.get("failed_sequences") or []]
    if not scoped_sequences:
        payload = {
            "schema": SCHEMA,
            "purpose": "no-op: broad clause planning left no residual parent contexts",
            "promotion_allowed": False,
            "selection_sha256": selection_sha,
            "scoped_sequences": [],
            "parent_contexts": [],
        }
        payload["evidence_sha256"] = _canonical_sha(payload)
        (root / "maintained-r1-context-boundary-feasibility.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    assembly_id = int((baseline.get("stage14") or {})["assembly_id"])
    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        assembly_rows = get_run_items(connection, assembly_id, kind="assembly_segment")
        translation_rows = get_run_items(connection, translation_run_id, kind="translation_segment")
        translation_run = get_run(connection, translation_run_id)
        translation_output = dict(translation_run.get("output") or {})
        context_run_id = int(translation_output["context_run_id"])
        context_run = get_run(connection, context_run_id)
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        gate_rows = connection.execute(
            "SELECT implementation, parameters_json FROM stage_runs "
            "WHERE stage_number=15 AND status='completed' ORDER BY id"
        ).fetchall()

    assembly_by_sequence = {int(row["sequence_number"]): row for row in assembly_rows}
    translation_by_sequence = {int(row["sequence_number"]): row for row in translation_rows}
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

    parent_keys: dict[tuple[int, int], list[int]] = {}
    for sequence in scoped_sequences:
        translation = translation_by_sequence.get(sequence)
        if translation is None or sequence not in assembly_by_sequence:
            raise RuntimeError("Context-boundary scope references a missing translation segment")
        planner = dict((translation.get("payload") or {}).get("planner") or {})
        first = int(planner.get("context_sentence_start", -1))
        last = int(planner.get("context_sentence_end", -1))
        if first < 0 or last < first:
            raise RuntimeError("Residual translation segment lacks parent context identity")
        parent_keys.setdefault((first, last), []).append(sequence)

    translator = OpusTranslator(device="cpu", compute_type="float32")
    results: list[dict[str, Any]] = []
    for parent_index, ((first, last), child_sequences) in enumerate(sorted(parent_keys.items())):
        context_parts = [context_by_sequence[index] for index in range(first, last + 1)]
        absolute_start = int(context_parts[0]["source_start"])
        absolute_end = int(context_parts[-1]["source_end"])
        for left, right in zip(context_parts, context_parts[1:]):
            if int(left["source_end"]) != int(right["source_start"]):
                raise RuntimeError("Parent context rows are not contiguous")
        source = "".join(str(row.get("source_text") or "") for row in context_parts)
        if len(source) != absolute_end - absolute_start:
            raise RuntimeError("Parent context source span length mismatch")
        parent_tokens = [
            token
            for token in nlp_tokens
            if int(token["source_start"]) >= absolute_start
            and int(token["source_end"]) <= absolute_end
            and not bool((token.get("payload") or {}).get("flags", {}).get("is_space"))
        ]
        if not parent_tokens:
            raise RuntimeError("Parent context contains no NLP tokens")

        cell_results: list[dict[str, Any]] = []
        for cell in CELLS:
            groups = _preferred_groups(
                source,
                parent_tokens,
                absolute_start=absolute_start,
                preferred_tokens=int(cell["preferred_tokens"]),
                minimum_fraction=float(cell["minimum_fraction"]),
            )
            jobs: list[str] = []
            plan: list[dict[str, Any]] = []
            for group in groups:
                leading, core, trailing = _prose_core(str(group["source_text"]))
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
                max_decoding_length=max(128, int(cell["preferred_tokens"]) * 8),
            )
            if len(generated) != sum(1 for group in plan if group["core"]):
                raise RuntimeError("Context-boundary translation cardinality mismatch")

            generated_iter = iter(generated)
            target_parts: list[str] = []
            public_plan: list[dict[str, Any]] = []
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
                    target_parts.append(str(group["source_text"]))
                public_plan.append(
                    {
                        "source_text": group["source_text"],
                        "token_count": group["token_count"],
                        "boundary_preferred": group["boundary_preferred"],
                        "selected_rank": selected["rank"] if selected is not None else None,
                        "selected_target_text": selected["target_text"] if selected is not None else None,
                        "candidates": candidates,
                    }
                )

            target = "".join(target_parts) if all_groups_selected else None
            global_verdict = (
                _verdict(
                    _candidate_row(source, parent_index),
                    target,
                    punctuation_parameters=punctuation_parameters,
                    length_parameters=length_parameters,
                )
                if target is not None
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
                    "candidate_target_text": target,
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
                "child_failure_sequences": sorted(child_sequences),
                "source_text": source,
                "token_count": len(parent_tokens),
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
        raise RuntimeError("Context-boundary probe mutated frozen R1 database")
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "feasibility of punctuation-preferred token-budget boundaries on complete parent contexts",
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "selection_sha256": selection_sha,
        "parent_clause_evidence_sha256": str(clause.get("evidence_sha256") or ""),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "cells": [dict(cell) for cell in CELLS],
        "boundary_policy": (
            "before a preferred-token cut, choose the nearest preceding source comma/semicolon/colon "
            "outside protected spans and not earlier than the configured minimum fraction; otherwise "
            "retain the current protected-span-safe forward cut"
        ),
        "scoped_sequences": scoped_sequences,
        "parent_context_count": len(results),
        "rescued_parent_contexts": rescued_contexts,
        "parent_contexts": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-context-boundary-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "scoped_sequences": scoped_sequences,
                "parent_context_count": len(results),
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
