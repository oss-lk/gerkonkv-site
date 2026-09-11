from __future__ import annotations

"""Research-only pinned TC-big whole-Stage10-context audit for run-9 failures.

Row-level alternative MT can look mechanically clean while completing a dangling
Stage12 fragment and damaging continuity. This audit therefore reconstructs the
exact Stage10 context sentence/group for every current run-9 hard failure.

A context is eligible for a replacement counterfactual only when its immutable
Stage10 source span is exactly representable by complete current Stage12 rows.
If a Stage10 boundary cuts through a Stage12 row, the context is recorded as
``replacement_row_aligned=false`` and skipped fail-closed: the audit never slices
an existing target and never expands the source span to make replacement easier.

For row-aligned contexts, TC-big translates the complete immutable context and a
raw hypothesis can enter the mechanical upper bound only when whole-context
selection is accepted and Gutenberg emphasis is preserved. The result is
research evidence only: no Product selection, no database write, no source or
target rewriting.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_candidate_context, evaluate_rescue_pair


BASE_PATH = Path(__file__).with_name("real_translation_full_opticks_alternative_mt_feasibility.py")
SPEC = importlib.util.spec_from_file_location("rocketdict_alt_mt_context_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load pinned alternative-MT helper")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SCHEMA = "rocketdict-full-opticks-alternative-mt-hard-contexts-run9/2"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN9_OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
RUN_STAGE10 = 2
RUN_STAGE12 = 9


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    numeric = punctuation = length = 0
    unique = 0
    for row in rows:
        verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        fn = (verdict.get("numeric_symbol") or {}).get("passed") is not True
        fp = verdict.get("punctuation_passed") is not True
        fl = verdict.get("length_passed") is not True
        numeric += int(fn)
        punctuation += int(fp)
        length += int(fl)
        unique += int(fn or fp or fl)
    return {"numeric_symbol": numeric, "punctuation": punctuation, "length": length, "unique": unique}


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_ALT_MT_CONTEXT_RUN9_ROOT", "work/alt-mt-context-run9")).resolve()
    database = root / "rocketdict.sqlite"
    model_dir = Path(os.environ.get("ROCKETDICT_ALT_MT_MODEL_DIR", "work/alt-mt-model")).resolve()
    if not database.is_file() or _sha(database) != DB_SHA:
        raise RuntimeError("run9 database identity drift")

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        run9 = connection.execute("SELECT * FROM stage_runs WHERE id=?", (RUN_STAGE12,)).fetchone()
        if run9 is None or str(run9["output_sha256"] or "") != RUN9_OUTPUT_SHA:
            raise RuntimeError("run9 output identity drift")
        output = json.loads(str(run9["output_json"] or "{}"))
        document_id = int(output["document_version_id"])
        document = connection.execute("SELECT * FROM document_versions WHERE id=?", (document_id,)).fetchone()
        if document is None or str(document["text_sha256"] or "") != TEXT_SHA:
            raise RuntimeError("run9 source text identity drift")
        content = str(document["content_text"])
        stage10 = [
            _row_dict(row)
            for row in connection.execute(
                "SELECT * FROM run_items WHERE run_id=? AND kind='context_sentence' ORDER BY sequence_number",
                (RUN_STAGE10,),
            ).fetchall()
        ]
        run9_rows = [
            _row_dict(row)
            for row in connection.execute(
                "SELECT * FROM run_items WHERE run_id=? AND kind='translation_segment' ORDER BY sequence_number",
                (RUN_STAGE12,),
            ).fetchall()
        ]
    finally:
        connection.close()

    if "".join(str(row["source_text"]) for row in run9_rows) != content:
        raise RuntimeError("run9 source coverage drift")
    if _inventory(run9_rows) != BASE_COUNTS:
        raise RuntimeError(f"run9 hard-gate drift: {_inventory(run9_rows)!r}")
    stage10_by_sequence = {int(row["sequence_number"]): row for row in stage10}

    hard_rows: list[dict[str, Any]] = []
    for row in run9_rows:
        verdict = evaluate_rescue_pair(str(row["source_text"]), str(row["target_text"]))
        if verdict.get("product_hard_passed") is not True:
            hard_rows.append(row)
    if len(hard_rows) != 52:
        raise RuntimeError(f"expected 52 run9 hard rows, got {len(hard_rows)}")

    contexts: dict[tuple[int, int], dict[str, Any]] = {}
    for row in hard_rows:
        payload = json.loads(str(row["payload_json"] or "{}"))
        planner = dict(payload.get("planner") or {})
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
        key = (first, last)
        entry = contexts.setdefault(
            key,
            {
                "context_sentence_start": first,
                "context_sentence_end": last,
                "planner_sources": set(),
                "hard_sequences": [],
            },
        )
        entry["planner_sources"].add(str(planner.get("source") or ""))
        entry["hard_sequences"].append(int(row["sequence_number"]))
    if len(contexts) != 50:
        raise RuntimeError(f"expected 50 unique hard contexts, got {len(contexts)}")

    context_cases: list[dict[str, Any]] = []
    spans: list[tuple[int, int]] = []
    non_row_aligned_contexts: list[str] = []
    for (first, last), entry in sorted(contexts.items()):
        source_rows = [stage10_by_sequence[index] for index in range(first, last + 1)]
        source = "".join(str(row["source_text"]) for row in source_rows)
        start = int(source_rows[0]["source_start"])
        end = int(source_rows[-1]["source_end"])
        if source != content[start:end]:
            raise RuntimeError(f"Stage10 context source coverage drift {first}:{last}")

        overlapping = [
            row for row in run9_rows
            if int(row["source_end"]) > start and int(row["source_start"]) < end
        ]
        members = [
            row for row in run9_rows
            if start <= int(row["source_start"]) and int(row["source_end"]) <= end
        ]
        member_source = "".join(str(row["source_text"]) for row in members)
        row_aligned = bool(members) and member_source == source
        if row_aligned:
            row_aligned = (
                int(members[0]["source_start"]) == start
                and int(members[-1]["source_end"]) == end
                and len(overlapping) == len(members)
            )

        case_id = f"stage10_context_{first}_{last}"
        if not row_aligned:
            non_row_aligned_contexts.append(case_id)
        spans.append((start, end))
        context_cases.append(
            {
                "case_id": case_id,
                "family": "run9_hard_stage10_context",
                "source_start": start,
                "source_end": end,
                "source_text": source,
                "baseline_target_text": (
                    "".join(str(row["target_text"]) for row in members)
                    if row_aligned else None
                ),
                "source_origin": "run9_stage10_context",
                "context_sentence_start": first,
                "context_sentence_end": last,
                "planner_sources": sorted(entry["planner_sources"]),
                "hard_sequences": sorted(entry["hard_sequences"]),
                "replacement_row_aligned": row_aligned,
                "member_sequences": [int(row["sequence_number"]) for row in members],
                "overlapping_sequences": [int(row["sequence_number"]) for row in overlapping],
                "overlapping_spans": [
                    [int(row["source_start"]), int(row["source_end"])] for row in overlapping
                ],
                "primary_rows": members if row_aligned else [],
            }
        )
    for previous, current in zip(sorted(spans), sorted(spans)[1:]):
        if current[0] < previous[1]:
            raise RuntimeError(f"hard contexts overlap: {previous!r} vs {current!r}")

    import torch
    from transformers import MarianMTModel, MarianTokenizer

    BASE._model_identity(model_dir)
    tokenizer = MarianTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = MarianMTModel.from_pretrained(str(model_dir), local_files_only=True, use_safetensors=True)
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    max_positions = int(getattr(model.config, "max_position_embeddings", 0) or 0)
    if max_positions <= 0:
        raise RuntimeError("TC-big model context size unavailable")

    cases_out: list[dict[str, Any]] = []
    replacements: dict[int, dict[str, Any]] = {}
    over_model_context: list[str] = []
    accepted_contexts: list[str] = []

    for case in context_cases:
        out = {key: value for key, value in case.items() if key != "primary_rows"}
        if case["replacement_row_aligned"] is not True:
            out["skipped_reason"] = "stage10_span_not_exactly_representable_by_complete_run9_rows"
            out["input_token_count"] = None
            out["model_max_position_embeddings"] = max_positions
            out["over_model_context"] = False
            out["hypotheses"] = []
            out["first_mechanically_admissible_rank"] = None
            cases_out.append(out)
            continue

        model_input = BASE.TARGET_PREFIX + str(case["source_text"])
        encoded = tokenizer(model_input, return_tensors="pt", add_special_tokens=True, truncation=False)
        input_tokens = int(encoded["input_ids"].shape[-1])
        out["input_token_count"] = input_tokens
        out["model_max_position_embeddings"] = max_positions
        if input_tokens > max_positions:
            out["over_model_context"] = True
            out["hypotheses"] = []
            out["first_mechanically_admissible_rank"] = None
            over_model_context.append(str(case["case_id"]))
            cases_out.append(out)
            continue

        translated = BASE._translate_case(case=case, tokenizer=tokenizer, model=model, torch=torch)
        evaluated: list[dict[str, Any]] = []
        first_admissible: int | None = None
        for hypothesis in translated["hypotheses"]:
            target = str(hypothesis["target_text"])
            candidate_row = {
                "source_text": str(case["source_text"]),
                "target_text": target,
            }
            selection = evaluate_candidate_context(list(case["primary_rows"]), [candidate_row])
            emphasis = compare_emphasis_markup_preservation(str(case["source_text"]), target)
            admissible = selection.get("accepted") is True and emphasis.get("passed") is True
            row = dict(hypothesis)
            row["context_selection"] = selection
            row["emphasis_markup"] = emphasis
            row["mechanically_admissible"] = admissible
            evaluated.append(row)
            if first_admissible is None and admissible:
                first_admissible = int(hypothesis["rank"])
        out["over_model_context"] = False
        out["hypotheses"] = evaluated
        out["first_mechanically_admissible_rank"] = first_admissible
        if first_admissible is not None:
            accepted_contexts.append(str(case["case_id"]))
            target = str(evaluated[first_admissible]["target_text"])
            replacements[int(case["source_start"])] = {
                "start": int(case["source_start"]),
                "end": int(case["source_end"]),
                "member_sequences": list(case["member_sequences"]),
                "row": {
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": int(case["source_start"]),
                    "source_end": int(case["source_end"]),
                    "source_text": str(case["source_text"]),
                    "target_text": target,
                },
            }
        cases_out.append(out)

    replaced_sequences = {
        int(sequence)
        for replacement in replacements.values()
        for sequence in replacement["member_sequences"]
    }
    candidate_rows = [dict(row) for row in run9_rows if int(row["sequence_number"]) not in replaced_sequences]
    candidate_rows.extend(dict(replacement["row"]) for replacement in replacements.values())
    candidate_rows.sort(key=lambda row: int(row["source_start"]))
    for sequence, row in enumerate(candidate_rows):
        row["sequence_number"] = sequence
    if "".join(str(row["source_text"]) for row in candidate_rows) != content:
        raise RuntimeError("whole-context TC-big counterfactual source coverage drift")
    upper = _inventory(candidate_rows)
    if any(upper[key] > BASE_COUNTS[key] for key in BASE_COUNTS):
        raise RuntimeError(f"whole-context TC-big mechanical regression: {upper!r}")
    if _sha(database) != DB_SHA:
        raise RuntimeError("whole-context TC-big research mutated run9 database")

    row_aligned_count = sum(1 for case in context_cases if case["replacement_row_aligned"] is True)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only pinned TC-big on exact row-aligned original Stage10 context boundaries containing current run9 hard failures",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_semantic_selector": False,
        "semantic_review_required": True,
        "mechanical_upper_bound_is_not_product_selection": True,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_STAGE12,
        "base_translation_output_sha256": RUN9_OUTPUT_SHA,
        "source_text_sha256": TEXT_SHA,
        "base_hard_gate_counts": BASE_COUNTS,
        "hard_row_count": len(hard_rows),
        "unique_context_count": len(context_cases),
        "row_aligned_context_count": row_aligned_count,
        "non_row_aligned_context_count": len(non_row_aligned_contexts),
        "non_row_aligned_contexts": non_row_aligned_contexts,
        "over_model_context_count": len(over_model_context),
        "over_model_contexts": over_model_context,
        "mechanically_admissible_context_count": len(accepted_contexts),
        "mechanically_admissible_contexts": accepted_contexts,
        "mechanical_upper_bound_hard_gate_counts": upper,
        "base_segment_count": len(run9_rows),
        "counterfactual_segment_count": len(candidate_rows),
        "model": BASE._model_identity(model_dir),
        "runtime": {"torch_version": str(torch.__version__), "device": "cpu", "torch_compute_dtype": "float32"},
        "cases": cases_out,
        "database_mutated": False,
        "source_coverage_byte_exact": True,
        "non_row_aligned_contexts_skipped_fail_closed": True,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_path = root / "full-opticks-alternative-mt-hard-contexts-run9.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "hard_row_count": len(hard_rows),
        "unique_context_count": len(context_cases),
        "row_aligned_context_count": row_aligned_count,
        "non_row_aligned_context_count": len(non_row_aligned_contexts),
        "over_model_context_count": len(over_model_context),
        "mechanically_admissible_context_count": len(accepted_contexts),
        "mechanical_upper_bound_hard_gate_counts": upper,
        "evidence_sha256": payload["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
