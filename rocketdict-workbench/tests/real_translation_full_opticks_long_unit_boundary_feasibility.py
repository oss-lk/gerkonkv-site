from __future__ import annotations

"""Research-only DOE for the planner-v8 long-unit content-loss residual.

The immutable full-Opticks artifact contains one isolated numeric-only residual
whose Stage10 parent sentence is 144 lexical tokens long. Planner v8 slices that
sentence by the soft token budget and the middle unit begins inside a logical
clause, after which rank0 OPUS drops the earlier clause containing ``25``.

This probe compares three source-derived request layouts for that exact parent:
1. persisted Product Stage12 chunks (control);
2. the complete Stage10 sentence as one real-OPUS request;
3. byte-exact semicolon clauses, preserving every source byte and delimiter.

No source words or numbers are rewritten, no target text is repaired, and only
raw OPUS hypotheses are evaluated against the unchanged maintained strict
verdict. This is feasibility evidence, not Product policy.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any

from rocketdict.runtime import OpusTranslator
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-long-unit-boundary-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
EXPECTED_PARENT_SEQUENCE = 669
EXPECTED_PARENT_START = 132834
EXPECTED_PARENT_END = 133465
EXPECTED_FAILURE_START = 133139
EXPECTED_FAILURE_END = 133431
GENERATION = {"beam_size": 6, "num_hypotheses": 6}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_row(start: int, end: int, text: str) -> dict[str, Any]:
    return {
        "sequence_number": 0,
        "source_start": start,
        "source_end": end,
        "source_text": text,
        "target_text": None,
    }


def _translate(translator: OpusTranslator, texts: list[str], max_decoding_length: int) -> list[list[dict[str, Any]]]:
    rows = translator.translate(
        texts,
        beam_size=int(GENERATION["beam_size"]),
        num_hypotheses=int(GENERATION["num_hypotheses"]),
        max_decoding_length=max_decoding_length,
    )
    if len(rows) != len(texts):
        raise RuntimeError("long-unit DOE translation cardinality mismatch")
    return rows


def _evaluate_layout(
    translator: OpusTranslator,
    chunks: list[dict[str, Any]],
    *,
    punctuation_parameters: dict[str, Any],
    length_parameters: dict[str, Any],
    max_decoding_length: int,
) -> dict[str, Any]:
    generated = _translate(translator, [str(row["text"]) for row in chunks], max_decoding_length)
    results: list[dict[str, Any]] = []
    rank0_all = True
    selectable_all = True
    selected_targets: list[str] = []
    for row, hypotheses in zip(chunks, generated, strict=True):
        source = _source_row(int(row["start"]), int(row["end"]), str(row["text"]))
        candidates: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        for index, hypothesis in enumerate(hypotheses):
            target = str(hypothesis.get("text") or "")
            verdict = _verdict(
                source,
                target,
                punctuation_parameters=punctuation_parameters,
                length_parameters=length_parameters,
            )
            candidate = {
                "model_index": index,
                "rank": int(hypothesis.get("rank") if hypothesis.get("rank") is not None else index),
                "score": hypothesis.get("score"),
                "target_text": target,
                "verdict": verdict,
            }
            candidates.append(candidate)
            if selected is None and verdict.get("strictly_eligible") is True:
                selected = candidate
        rank0_pass = bool(candidates and candidates[0]["verdict"].get("strictly_eligible") is True)
        rank0_all = rank0_all and rank0_pass
        selectable_all = selectable_all and selected is not None
        selected_targets.append("" if selected is None else str(selected["target_text"]))
        results.append(
            {
                **row,
                "rank0_strict_passed": rank0_pass,
                "selected_rank": None if selected is None else int(selected["rank"]),
                "selected_target_text": None if selected is None else str(selected["target_text"]),
                "candidates": candidates,
            }
        )
    return {
        "chunk_count": len(chunks),
        "rank0_all_strict": rank0_all,
        "nbest_all_strict": selectable_all,
        "selected_assembled_target": "".join(selected_targets) if selectable_all else None,
        "chunks": results,
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-artifact/full-opticks-numeric-stress")).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks baseline is incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA or baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("unexpected pinned full-Opticks baseline")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("long-unit baseline planner is not current")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline artifact identity drift")

    failure = next(
        (dict(row) for row in baseline.get("numeric_failures") or []
         if int(row.get("source_start") or -1) == EXPECTED_FAILURE_START
         and int(row.get("source_end") or -1) == EXPECTED_FAILURE_END),
        None,
    )
    if failure is None:
        raise RuntimeError("pinned long-unit failure span drift")
    if (failure.get("rank0_verdict") or {}).get("strictly_eligible") is True:
        raise RuntimeError("pinned long-unit failure unexpectedly passes")

    connection = sqlite3.connect(database)
    try:
        stage10_run = int(connection.execute("SELECT id FROM stage_runs WHERE stage_number=10 AND status='completed'").fetchone()[0])
        stage12_run = int(connection.execute("SELECT id FROM stage_runs WHERE stage_number=12 AND status='completed'").fetchone()[0])
        parent = connection.execute(
            "SELECT sequence_number,source_start,source_end,source_text FROM run_items WHERE run_id=? AND sequence_number=?",
            (stage10_run, EXPECTED_PARENT_SEQUENCE),
        ).fetchone()
        if parent is None:
            raise RuntimeError("pinned Stage10 parent sentence missing")
        sequence, parent_start, parent_end, parent_text = int(parent[0]), int(parent[1]), int(parent[2]), str(parent[3])
        if (sequence, parent_start, parent_end) != (EXPECTED_PARENT_SEQUENCE, EXPECTED_PARENT_START, EXPECTED_PARENT_END):
            raise RuntimeError("pinned Stage10 parent identity drift")
        current_rows = connection.execute(
            "SELECT sequence_number,source_start,source_end,source_text,target_text,payload_json FROM run_items "
            "WHERE run_id=? AND source_start>=? AND source_end<=? ORDER BY sequence_number",
            (stage12_run, parent_start, parent_end),
        ).fetchall()
    finally:
        connection.close()

    current_chunks = [
        {"start": int(row[1]), "end": int(row[2]), "text": str(row[3]), "persisted_target_text": str(row[4] or ""), "planned_sequence": int(row[0])}
        for row in current_rows
    ]
    if "".join(str(row["text"]) for row in current_chunks) != parent_text:
        raise RuntimeError("persisted Stage12 chunks do not byte-cover the parent sentence")

    semicolon_chunks: list[dict[str, Any]] = []
    cursor = 0
    for offset, char in enumerate(parent_text):
        if char != ";":
            continue
        end = offset + 1
        semicolon_chunks.append({"start": parent_start + cursor, "end": parent_start + end, "text": parent_text[cursor:end]})
        cursor = end
    if cursor < len(parent_text):
        semicolon_chunks.append({"start": parent_start + cursor, "end": parent_end, "text": parent_text[cursor:]})
    if len(semicolon_chunks) != 3 or "".join(str(row["text"]) for row in semicolon_chunks) != parent_text:
        raise RuntimeError("expected exactly three byte-exact semicolon clauses")

    whole_chunks = [{"start": parent_start, "end": parent_end, "text": parent_text}]
    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})
    max_decoding_length = max(512, int(baseline.get("max_planned_unit_tokens") or 64) * 12)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    database_sha_before = _sha(database)

    layouts = {
        "current_product_chunks_regenerated": _evaluate_layout(
            translator,
            current_chunks,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
            max_decoding_length=max_decoding_length,
        ),
        "whole_stage10_sentence": _evaluate_layout(
            translator,
            whole_chunks,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
            max_decoding_length=max_decoding_length,
        ),
        "semicolon_clauses": _evaluate_layout(
            translator,
            semicolon_chunks,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
            max_decoding_length=max_decoding_length,
        ),
    }
    database_sha_after = _sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("long-unit feasibility inference mutated retained Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "source-derived boundary feasibility for the planner-v8 long-unit numeric content-loss residual",
        "promotion_allowed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_json_sha256": _sha(baseline_path),
        "parent_sequence": sequence,
        "parent_start": parent_start,
        "parent_end": parent_end,
        "parent_text": parent_text,
        "current_failure_sequence": int(failure["planned_sequence"]),
        "current_failure_start": EXPECTED_FAILURE_START,
        "current_failure_end": EXPECTED_FAILURE_END,
        "current_failure_source_text": str(failure["source_text"]),
        "current_failure_target_text": str(failure["product_target_text"]),
        "generation": dict(GENERATION),
        "layouts": layouts,
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(os.environ.get("ROCKETDICT_LONG_UNIT_ROOT", "work/long-unit-feasibility")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-long-unit-boundary-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "current_rank0_all_strict": layouts["current_product_chunks_regenerated"]["rank0_all_strict"],
        "whole_rank0_all_strict": layouts["whole_stage10_sentence"]["rank0_all_strict"],
        "whole_nbest_all_strict": layouts["whole_stage10_sentence"]["nbest_all_strict"],
        "semicolon_rank0_all_strict": layouts["semicolon_clauses"]["rank0_all_strict"],
        "semicolon_nbest_all_strict": layouts["semicolon_clauses"]["nbest_all_strict"],
        "evidence_sha256": payload["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
