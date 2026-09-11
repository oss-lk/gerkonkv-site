from __future__ import annotations

"""Research-only pinned TC-big screen over every unique run-9 hard-failing row.

This widens the already-pinned independent Marian model to the exact current
Stage12 run-9 residual set.  It is an evidence inventory, not an automatic
fallback: all raw hypotheses, mechanical diagnostics, and a mechanical upper
bound are persisted while promotion/automatic semantic selection remain false.
"""

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

BASE_PATH = Path(__file__).with_name("real_translation_full_opticks_alternative_mt_feasibility.py")
SPEC = importlib.util.spec_from_file_location("rocketdict_alt_mt_all_run9", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load pinned alternative-MT helper")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SCHEMA = "rocketdict-full-opticks-alternative-mt-current-hard-failures-run9/1"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
RUN_OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_BASE = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}


def _flags(source: str, target: str) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(source, target)
    return {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in sorted(rows, key=lambda value: int(value["sequence_number"])):
        sequence = int(row["sequence_number"])
        flags = _flags(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        for key, failed in flags.items():
            if failed:
                failures[key].append(sequence)
                union.add(sequence)
    return {
        **failures,
        "counts": {key: len(value) for key, value in failures.items()},
        "unique_failure_count": len(union),
        "unique_failure_sequences": sorted(union),
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_ALT_MT_RUN9_ROOT", "work/alternative-mt-current-hard-failures-run9")).resolve()
    model_dir = Path(os.environ["ROCKETDICT_ALT_MT_MODEL_DIR"]).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or BASE._sha(database) != DB_SHA:
        raise RuntimeError("run9 database identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN_ID)
        rows = get_run_items(connection, RUN_ID, kind="translation_segment")
        document = get_document(connection, int(dict(run.get("output") or {})["document_version_id"]))
    if str(run.get("output_sha256") or "") != RUN_OUTPUT_SHA or str(document.get("text_sha256") or "") != TEXT_SHA:
        raise RuntimeError("run9 identity drift")
    content = str(document["content_text"])
    rows = sorted(rows, key=lambda value: int(value["sequence_number"]))
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run9 source coverage drift")
    base_inventory = _inventory(rows)
    base_counts = {**base_inventory["counts"], "unique": base_inventory["unique_failure_count"]}
    if base_counts != EXPECTED_BASE:
        raise RuntimeError(f"run9 hard-gate drift: {base_counts!r}")

    hard_rows = [
        row
        for row in rows
        if any(_flags(str(row.get("source_text") or ""), str(row.get("target_text") or "")).values())
    ]
    if len(hard_rows) != EXPECTED_BASE["unique"]:
        raise RuntimeError("run9 unique hard-failure cohort cardinality drift")

    cases: list[dict[str, Any]] = []
    for row in hard_rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        cases.append({
            "case_id": f"run9_hard_failure_{int(row['sequence_number'])}",
            "family": "run9_current_hard_failure",
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": source,
            "baseline_target_text": target,
            "baseline_planned_sequence": int(row["sequence_number"]),
            "source_origin": "run9_current_hard_failure",
            "baseline_failure_flags": _flags(source, target),
        })

    database_sha_before = BASE._sha(database)
    model_identity = BASE._model_identity(model_dir)
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    tokenizer = MarianTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = MarianMTModel.from_pretrained(str(model_dir), local_files_only=True, use_safetensors=True)
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    if str(model.config.model_type) != "marian":
        raise RuntimeError(f"unexpected alternative model type: {model.config.model_type!r}")

    results: list[dict[str, Any]] = []
    replacement_targets: dict[int, str] = {}
    for case in cases:
        translated = BASE._translate_case(case=case, tokenizer=tokenizer, model=model, torch=torch)
        first_admissible: int | None = None
        for hypothesis in translated["hypotheses"]:
            target = str(hypothesis.get("target_text") or "")
            emphasis = compare_emphasis_markup_preservation(str(case["source_text"]), target)
            hypothesis["emphasis_markup"] = emphasis
            hypothesis["mechanically_admissible"] = (
                (hypothesis.get("mechanical_verdict") or {}).get("strictly_eligible") is True
                and emphasis.get("passed") is True
            )
            if first_admissible is None and hypothesis["mechanically_admissible"]:
                first_admissible = int(hypothesis["rank"])
        translated["mechanically_admissible_ranks"] = [
            int(hypothesis["rank"])
            for hypothesis in translated["hypotheses"]
            if hypothesis["mechanically_admissible"]
        ]
        translated["first_mechanically_admissible_rank"] = first_admissible
        if first_admissible is not None:
            replacement_targets[int(case["baseline_planned_sequence"])] = str(
                translated["hypotheses"][first_admissible]["target_text"]
            )
        results.append(translated)

    upper_rows: list[dict[str, Any]] = []
    for row in rows:
        candidate = dict(row)
        replacement = replacement_targets.get(int(row["sequence_number"]))
        if replacement is not None:
            candidate["target_text"] = replacement
        upper_rows.append(candidate)
    upper_inventory = _inventory(upper_rows)
    upper_counts = {**upper_inventory["counts"], "unique": upper_inventory["unique_failure_count"]}
    if any(upper_counts[key] > EXPECTED_BASE[key] for key in EXPECTED_BASE):
        raise RuntimeError(f"alternative-MT mechanical upper-bound regression: {upper_counts!r}")
    if "".join(str(row.get("source_text") or "") for row in upper_rows) != content:
        raise RuntimeError("alternative-MT upper-bound source coverage drift")

    database_sha_after = BASE._sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("alternative MT run9 screen mutated database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only pinned independent real-MT screen across every current run-9 hard-failing translation row",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_semantic_selector": False,
        "semantic_review_required": True,
        "mechanical_upper_bound_is_not_product_selection": True,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": RUN_OUTPUT_SHA,
        "source_text_sha256": TEXT_SHA,
        "base_hard_gate_inventory": base_inventory,
        "base_hard_gate_counts": EXPECTED_BASE,
        "model": model_identity,
        "runtime": {"torch_version": str(torch.__version__), "torch_compute_dtype": "float32", "device": "cpu", "transformers_class": "MarianMTModel"},
        "case_count": len(results),
        "cases": results,
        "cases_with_any_mechanically_admissible_alternative": [
            int(case["baseline_planned_sequence"])
            for case in results
            if case["mechanically_admissible_ranks"]
        ],
        "case_count_with_any_mechanically_admissible_alternative": sum(1 for case in results if case["mechanically_admissible_ranks"]),
        "mechanical_upper_bound_hard_gate_inventory": upper_inventory,
        "mechanical_upper_bound_hard_gate_counts": upper_counts,
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
        "source_coverage_byte_exact": True,
    }
    payload["evidence_sha256"] = BASE._canonical_sha(payload)
    out = root / "full-opticks-alternative-mt-current-hard-failures-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "case_count": len(results),
        "case_count_with_any_mechanically_admissible_alternative": payload["case_count_with_any_mechanically_admissible_alternative"],
        "mechanical_upper_bound_hard_gate_counts": upper_counts,
        "evidence_sha256": payload["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
