from __future__ import annotations

"""Research-only pinned TC-big differential for run-9 delimiter-addition failures."""

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation

BASE_PATH = Path(__file__).with_name(
    "real_translation_full_opticks_alternative_mt_feasibility.py"
)
SPEC = importlib.util.spec_from_file_location("rocketdict_alt_mt_base_run9", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load pinned alternative-MT helper")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SCHEMA = "rocketdict-full-opticks-target-delimiter-alternative-mt-run9/1"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
RUN_OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
SEQUENCES = [3, 1864, 1878, 2219, 2382, 2862, 3220]
STARTS = [488, 326217, 329423, 388656, 417917, 501398, 569170]


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_TARGET_DELIMITER_ALT_ROOT",
            "work/target-delimiter-alternative-mt-run9",
        )
    ).resolve()
    model_dir = Path(os.environ["ROCKETDICT_ALT_MT_MODEL_DIR"]).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or BASE._sha(database) != DB_SHA:
        raise RuntimeError("run9 database identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN_ID)
        rows = get_run_items(connection, RUN_ID, kind="translation_segment")
        document = get_document(
            connection, int(dict(run.get("output") or {})["document_version_id"])
        )
    if str(run.get("output_sha256") or "") != RUN_OUTPUT_SHA:
        raise RuntimeError("run9 output identity drift")
    if str(document.get("text_sha256") or "") != TEXT_SHA:
        raise RuntimeError("run9 source identity drift")
    content = str(document["content_text"])
    rows = sorted(rows, key=lambda row: int(row["sequence_number"]))
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run9 source coverage drift")

    by_sequence = {int(row["sequence_number"]): row for row in rows}
    cases: list[dict[str, Any]] = []
    for sequence, expected_start in zip(SEQUENCES, STARTS, strict=True):
        row = by_sequence[sequence]
        if int(row["source_start"]) != expected_start:
            raise RuntimeError(f"delimiter alt-MT span drift seq {sequence}")
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = BASE.evaluate_rescue_pair(source, target)
        if verdict.get("punctuation_passed") is True:
            raise RuntimeError(f"delimiter alt-MT trigger unexpectedly clean seq {sequence}")
        cases.append(
            {
                "case_id": f"run9_target_delimiter_{sequence}",
                "family": "run9_target_only_delimiter_addition",
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "baseline_target_text": target,
                "baseline_planned_sequence": sequence,
                "source_origin": "run9_target_delimiter_hard_failure",
            }
        )

    database_sha_before = BASE._sha(database)
    model_identity = BASE._model_identity(model_dir)

    import torch
    from transformers import MarianMTModel, MarianTokenizer

    tokenizer = MarianTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = MarianMTModel.from_pretrained(
        str(model_dir), local_files_only=True, use_safetensors=True
    )
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    if str(model.config.model_type) != "marian":
        raise RuntimeError(f"unexpected alternative model type: {model.config.model_type!r}")

    results: list[dict[str, Any]] = []
    for case in cases:
        translated = BASE._translate_case(
            case=case, tokenizer=tokenizer, model=model, torch=torch
        )
        for hypothesis in translated["hypotheses"]:
            target = str(hypothesis.get("target_text") or "")
            emphasis = compare_emphasis_markup_preservation(
                str(case["source_text"]), target
            )
            hypothesis["emphasis_markup"] = emphasis
            hypothesis["mechanically_admissible"] = (
                (hypothesis.get("mechanical_verdict") or {}).get("strictly_eligible")
                is True
                and emphasis.get("passed") is True
            )
        translated["mechanically_admissible_ranks"] = [
            int(hypothesis["rank"])
            for hypothesis in translated["hypotheses"]
            if hypothesis["mechanically_admissible"]
        ]
        results.append(translated)

    database_sha_after = BASE._sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("alternative MT screening mutated run9 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only pinned independent real-MT differential on exact run-9 "
            "target-only delimiter hard-failure spans after pinned OPUS n-best remained trapped"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_semantic_selector": False,
        "semantic_review_required": True,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": RUN_OUTPUT_SHA,
        "source_text_sha256": TEXT_SHA,
        "model": model_identity,
        "runtime": {
            "torch_version": str(torch.__version__),
            "torch_compute_dtype": "float32",
            "device": "cpu",
            "transformers_class": "MarianMTModel",
        },
        "attempted_sequences": SEQUENCES,
        "attempted_source_starts": STARTS,
        "case_count": len(results),
        "cases": results,
        "cases_with_any_mechanically_admissible_alternative": [
            int(case["baseline_planned_sequence"])
            for case in results
            if case["mechanically_admissible_ranks"]
        ],
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
    }
    payload["evidence_sha256"] = BASE._canonical_sha(payload)
    out = root / "full-opticks-target-delimiter-alternative-mt-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "model_repository": BASE.MODEL_REPO,
                "model_revision": BASE.MODEL_REVISION,
                "cases_with_any_mechanically_admissible_alternative": payload[
                    "cases_with_any_mechanically_admissible_alternative"
                ],
                "admissible_ranks": {
                    str(case["baseline_planned_sequence"]): case[
                        "mechanically_admissible_ranks"
                    ]
                    for case in results
                },
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
