from __future__ import annotations

"""Research-only clause/list-aware planning probe for strict R1 residuals.

The probe consumes the no-structural-island residuals instead of naming hand
picked sequences.  It preserves every source byte in a deterministic planning
map, chooses cuts only after source comma/semicolon/colon boundaries, and lets a
soft source-word budget decide which adjacent clauses are translated together.
No number, punctuation, target token or source-owned structure is synthesized.
The frozen Product database is read-only throughout.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_run, get_run_items
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair
from rocketdict.research_diagnostics import (
    compare_critical_technical_tokens,
    compare_delimiter_preservation,
    compare_numeric_order,
    compare_output_artifacts,
)
from rocketdict.runtime import OpusTranslator
from rocketdict.stages import _length_issues, _punctuation_issues

SCHEMA = "rocketdict-maintained-r1-clause-planning-feasibility/1"
EXPECTED_SELECTION_SHA256 = "665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32"
CELLS = (
    {"soft_max_words": 18, "beam_size": 6},
    {"soft_max_words": 28, "beam_size": 6},
    {"soft_max_words": 40, "beam_size": 6},
)
_WORD_RE = re.compile(r"\b[\w’'-]+\b", flags=re.UNICODE)
_CLAUSE_BOUNDARY_RE = re.compile(r"[,;:](?=\s|$)")


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


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _primitive_clauses(source: str) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    cursor = 0
    for match in _CLAUSE_BOUNDARY_RE.finditer(source):
        end = match.end()
        if end > cursor:
            parts.append(
                {
                    "start": cursor,
                    "end": end,
                    "text": source[cursor:end],
                    "word_count": _word_count(source[cursor:end]),
                }
            )
        cursor = end
    if cursor < len(source):
        parts.append(
            {
                "start": cursor,
                "end": len(source),
                "text": source[cursor:],
                "word_count": _word_count(source[cursor:]),
            }
        )
    if not parts:
        parts = [{"start": 0, "end": len(source), "text": source, "word_count": _word_count(source)}]
    if "".join(str(part["text"]) for part in parts) != source:
        raise RuntimeError("Primitive clause plan is not byte-exact")
    return parts


def _soft_groups(source: str, *, max_words: int) -> list[dict[str, Any]]:
    if max_words < 1:
        raise RuntimeError("soft_max_words must be positive")
    primitive = _primitive_clauses(source)
    groups: list[dict[str, Any]] = []
    start_index = 0
    current_words = 0
    for index, part in enumerate(primitive):
        words = int(part["word_count"])
        if index > start_index and current_words > 0 and current_words + words > max_words:
            start = int(primitive[start_index]["start"])
            end = int(primitive[index - 1]["end"])
            groups.append(
                {
                    "start": start,
                    "end": end,
                    "text": source[start:end],
                    "word_count": _word_count(source[start:end]),
                    "primitive_count": index - start_index,
                }
            )
            start_index = index
            current_words = 0
        current_words += words
    start = int(primitive[start_index]["start"])
    end = int(primitive[-1]["end"])
    groups.append(
        {
            "start": start,
            "end": end,
            "text": source[start:end],
            "word_count": _word_count(source[start:end]),
            "primitive_count": len(primitive) - start_index,
        }
    )
    if "".join(str(group["text"]) for group in groups) != source:
        raise RuntimeError("Clause soft-group plan is not byte-exact")
    return groups


def _prose_core(fragment: str) -> tuple[str, str, str]:
    if not fragment.strip():
        return fragment, "", ""
    left = len(fragment) - len(fragment.lstrip())
    right = len(fragment) - len(fragment.rstrip())
    leading = fragment[:left]
    trailing = fragment[len(fragment) - right :] if right else ""
    core_end = len(fragment) - right if right else len(fragment)
    return leading, fragment[left:core_end], trailing


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
    punctuation = _punctuation_issues([probe], punctuation_parameters)
    length = _length_issues([probe], length_parameters)
    numeric_order = compare_numeric_order(source, target)
    delimiters = compare_delimiter_preservation(source, target)
    critical = compare_critical_technical_tokens(source, target)
    artifacts = compare_output_artifacts(source, target)
    product_hard = numeric["passed"] is True and not punctuation and not length and bool(target.strip())
    research = (
        numeric_order["passed"] is True
        and delimiters["passed"] is True
        and critical["passed"] is True
        and artifacts["passed"] is True
    )
    return {
        "product_hard_passed": product_hard,
        "strict_research_passed": research,
        "strictly_eligible": product_hard and research,
        "numeric_symbol": numeric,
        "punctuation_issues": punctuation,
        "length_issues": length,
        "numeric_order": numeric_order,
        "delimiter_preservation": delimiters,
        "critical_technical_tokens": critical,
        "output_artifacts": artifacts,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_TRANSLATION_CHALLENGE_ROOT", "work/translation-challenge")
    ).resolve()
    baseline_path = root / "maintained-r1-baseline.json"
    nbest_path = root / "maintained-r1-nbest-feasibility.json"
    structural_path = root / "maintained-r1-structural-island-feasibility.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not all(path.is_file() for path in (baseline_path, nbest_path, structural_path, database)):
        raise RuntimeError("Clause-planning probe prerequisites are missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    nbest = json.loads(nbest_path.read_text(encoding="utf-8"))
    structural = json.loads(structural_path.read_text(encoding="utf-8"))
    selection_sha = str((baseline.get("selection") or {}).get("selection_sha256") or "")
    if selection_sha != EXPECTED_SELECTION_SHA256:
        raise RuntimeError("Frozen R1 selection identity drift")
    if nbest.get("selection_sha256") != selection_sha or structural.get("selection_sha256") != selection_sha:
        raise RuntimeError("R1 probe evidence is not bound to the same frozen selection")

    scoped_sequences = [int(value) for value in structural.get("no_recognized_island_sequences") or []]
    if not scoped_sequences:
        raise RuntimeError("No non-structural strict residuals remain for clause planning")

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
        raise RuntimeError("Clause-planning scope references a missing R1 assembly segment")
    gate_parameters = {
        str(row["implementation"]): _parameters(row["parameters_json"])
        for row in gate_rows
    }
    punctuation_parameters = dict(gate_parameters.get("rocketdict-punctuation-preservation") or {})
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
            jobs: list[str] = []
            plan: list[dict[str, Any]] = []
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
                num_hypotheses=1,
                max_decoding_length=max_decoding_length,
            ) if jobs else []
            if len(generated) != sum(1 for group in plan if group["core"]):
                raise RuntimeError("Clause-planning translation cardinality mismatch")
            generated_iter = iter(generated)
            target_parts: list[str] = []
            public_plan: list[dict[str, Any]] = []
            for group in plan:
                if group["core"]:
                    hypotheses = next(generated_iter)
                    if not hypotheses:
                        raise RuntimeError(f"OPUS returned no clause hypothesis for sequence {sequence}")
                    translated = str(hypotheses[0].get("text") or "")
                    rank = int(hypotheses[0].get("rank") or 0)
                    score = hypotheses[0].get("score")
                else:
                    translated, rank, score = "", None, None
                target_parts.append(
                    str(group["leading_whitespace"]) + translated + str(group["trailing_whitespace"])
                    if group["core"]
                    else str(group["text"])
                )
                public_plan.append(
                    {
                        "source_text": group["text"],
                        "word_count": group["word_count"],
                        "primitive_count": group["primitive_count"],
                        "translated_core": translated,
                        "model_rank": rank,
                        "model_score": score,
                    }
                )
            candidate = "".join(target_parts)
            verdict = _verdict(
                row,
                candidate,
                punctuation_parameters=punctuation_parameters,
                length_parameters=length_parameters,
            )
            cell_results.append(
                {
                    "config": dict(cell),
                    "group_count": len(groups),
                    "plan": public_plan,
                    "candidate_target_text": candidate,
                    "verdict": verdict,
                    "rescued": verdict["strictly_eligible"] is True,
                }
            )
        successful = [cell for cell in cell_results if cell["rescued"] is True]
        results.append(
            {
                "segment_sequence": sequence,
                "source_text": source,
                "baseline_target_text": str(row.get("target_text") or ""),
                "primitive_clause_count": len(_primitive_clauses(source)),
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

    rescued = [int(row["segment_sequence"]) for row in results if row["rescued_any_cell"] is True]
    failed = [int(row["segment_sequence"]) for row in results if row["rescued_any_cell"] is not True]
    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Clause-planning feasibility probe mutated frozen R1 database")
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "mechanism feasibility only; deterministic source-punctuation clause planning",
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "selection_sha256": selection_sha,
        "nbest_evidence_sha256": str(nbest.get("evidence_sha256") or ""),
        "structural_island_evidence_sha256": str(structural.get("evidence_sha256") or ""),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "cells": [dict(cell) for cell in CELLS],
        "cut_policy": "only after source comma/semicolon/colon; soft source-word budget; no hard fallback cut",
        "scoped_sequences": scoped_sequences,
        "rescued_count": len(rescued),
        "rescued_sequences": rescued,
        "failed_count": len(failed),
        "failed_sequences": failed,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-clause-planning-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "scoped_sequences": scoped_sequences,
                "rescued_sequences": rescued,
                "failed_sequences": failed,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
