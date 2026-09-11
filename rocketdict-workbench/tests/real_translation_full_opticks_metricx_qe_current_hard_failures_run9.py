from __future__ import annotations

"""Research-only MetricX-24 QE audit for current run-9 TC-big survivors.

The upstream TC-big differential is already fail-closed mechanically and keeps
only raw hypotheses.  This audit adds an independent learned QE ranking signal
for semantic review.  It does not choose Product translations, define a score
threshold, rewrite text, or mutate the persisted Product database.
"""

from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any


BASE_HELPER = Path(__file__).with_name("real_translation_full_opticks_metricx_qe_audit.py")
SPEC = importlib.util.spec_from_file_location("rocketdict_metricx_qe_base", BASE_HELPER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load maintained MetricX QE helper")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SCHEMA = "rocketdict-full-opticks-metricx-qe-current-hard-failures-run9/1"
INPUT_SCHEMA = "rocketdict-full-opticks-alternative-mt-current-hard-failures-run9/1"
EXPECTED_INPUT_FILE_SHA256 = "5c87500453f9443f5aff42d4bfea1bc055b48fa3a2ec747e13ec99581fe16f69"
EXPECTED_INPUT_EVIDENCE_SHA256 = "1e3ce22828f72b2409e1a4093646ef0a74a4dcf9b224b3f59d286011acbebca7"
EXPECTED_RUN9_DB_SHA256 = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
EXPECTED_CASE_COUNT = 52
EXPECTED_BASE_COUNTS = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
EXPECTED_MECHANICAL_UPPER = {"numeric_symbol": 13, "punctuation": 8, "length": 0, "unique": 20}


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_QE_RUN9_ROOT", "work/qe-run9")).resolve()
    input_path = root / "full-opticks-alternative-mt-current-hard-failures-run9.json"
    database = root / "rocketdict.sqlite"
    model_dir = Path(os.environ.get("ROCKETDICT_METRICX_MODEL_DIR", "work/metricx-model")).resolve()
    tokenizer_dir = Path(os.environ.get("ROCKETDICT_METRICX_TOKENIZER_DIR", "work/metricx-tokenizer")).resolve()
    for path in (input_path, database):
        if not path.is_file():
            raise RuntimeError(f"run9 MetricX input missing: {path}")

    input_bytes = input_path.read_bytes()
    if hashlib.sha256(input_bytes).hexdigest() != EXPECTED_INPUT_FILE_SHA256:
        raise RuntimeError("run9 TC-big all-failure evidence file identity drift")
    evidence = json.loads(input_bytes.decode("utf-8"))
    if evidence.get("schema") != INPUT_SCHEMA:
        raise RuntimeError("run9 TC-big evidence schema drift")
    if evidence.get("evidence_sha256") != EXPECTED_INPUT_EVIDENCE_SHA256:
        raise RuntimeError("run9 TC-big evidence canonical identity drift")
    if int(evidence.get("case_count") or -1) != EXPECTED_CASE_COUNT:
        raise RuntimeError("run9 TC-big case count drift")
    if dict(evidence.get("base_hard_gate_counts") or {}) != EXPECTED_BASE_COUNTS:
        raise RuntimeError("run9 base hard-gate inventory drift")
    if dict(evidence.get("mechanical_upper_bound_hard_gate_counts") or {}) != EXPECTED_MECHANICAL_UPPER:
        raise RuntimeError("run9 TC-big mechanical upper bound drift")
    if BASE._sha(database) != EXPECTED_RUN9_DB_SHA256:
        raise RuntimeError("run9 persisted database identity drift")

    metricx_identity = BASE._tree_identity(
        model_dir,
        ("README.md", "config.json", "pytorch_model.bin"),
    )
    weights_sha = next(
        row["sha256"]
        for row in metricx_identity["required_files"]
        if row["path"] == "pytorch_model.bin"
    )
    if weights_sha != BASE.METRICX_WEIGHTS_SHA256:
        raise RuntimeError("MetricX weights identity drift")
    tokenizer_identity = BASE._tree_identity(
        tokenizer_dir,
        ("config.json", "special_tokens_map.json", "spiece.model", "tokenizer_config.json"),
    )

    import torch
    from transformers import AutoTokenizer
    from metricx24.models import MT5ForRegression

    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir), local_files_only=True)
    model = MT5ForRegression.from_pretrained(
        str(model_dir), local_files_only=True, torch_dtype="auto"
    ).to("cpu")
    model.eval()

    records: list[dict[str, Any]] = []
    admissible_candidate_count = 0
    for case in evidence["cases"]:
        sequence = int(case["baseline_planned_sequence"])
        source = str(case["source_text"])
        records.append(
            {
                "candidate_id": f"{sequence}:opus",
                "sequence_number": sequence,
                "kind": "opus_baseline",
                "rank": None,
                "source_text": source,
                "target_text": str(case["baseline_target_text"]),
            }
        )
        for hypothesis in case["hypotheses"]:
            if hypothesis.get("mechanically_admissible") is not True:
                continue
            rank = int(hypothesis["rank"])
            admissible_candidate_count += 1
            records.append(
                {
                    "candidate_id": f"{sequence}:tc:{rank}",
                    "sequence_number": sequence,
                    "kind": "tc_big_mechanically_admissible",
                    "rank": rank,
                    "source_text": source,
                    "target_text": str(hypothesis["target_text"]),
                }
            )
    if len(records) != EXPECTED_CASE_COUNT + admissible_candidate_count:
        raise RuntimeError("run9 MetricX flattened inventory drift")
    if admissible_candidate_count != 172:
        raise RuntimeError(f"run9 admissible TC-big hypothesis count drift: {admissible_candidate_count}")

    scores = BASE._score_batches(records, tokenizer=tokenizer, model=model, torch=torch)
    score_by_id = dict(zip((row["candidate_id"] for row in records), scores, strict=True))

    cases_out: list[dict[str, Any]] = []
    cases_with_admissible = 0
    qe_prefers_any_admissible = 0
    qe_prefers_first_admissible = 0
    best_rank_counts: Counter[int] = Counter()
    deltas: list[float] = []

    for case in evidence["cases"]:
        sequence = int(case["baseline_planned_sequence"])
        opus_score = float(score_by_id[f"{sequence}:opus"])
        candidates: list[dict[str, Any]] = []
        for hypothesis in case["hypotheses"]:
            if hypothesis.get("mechanically_admissible") is not True:
                continue
            rank = int(hypothesis["rank"])
            score = float(score_by_id[f"{sequence}:tc:{rank}"])
            candidates.append(
                {
                    "rank": rank,
                    "metricx_qe_score": score,
                    "delta_vs_opus": opus_score - score,
                    "target_text": str(hypothesis["target_text"]),
                }
            )
        candidates.sort(key=lambda row: (float(row["metricx_qe_score"]), int(row["rank"])))
        best = candidates[0] if candidates else None
        first_rank = case.get("first_mechanically_admissible_rank")
        first = next(
            (row for row in candidates if int(row["rank"]) == int(first_rank)),
            None,
        ) if first_rank is not None else None
        if candidates:
            cases_with_admissible += 1
            assert best is not None
            best_rank_counts[int(best["rank"])] += 1
            deltas.append(float(best["delta_vs_opus"]))
            if float(best["metricx_qe_score"]) < opus_score:
                qe_prefers_any_admissible += 1
            if first is not None and float(first["metricx_qe_score"]) < opus_score:
                qe_prefers_first_admissible += 1
        cases_out.append(
            {
                "sequence_number": sequence,
                "family": str(case.get("family") or ""),
                "baseline_failure_flags": dict(case.get("baseline_failure_flags") or {}),
                "source_start": int(case["source_start"]),
                "source_end": int(case["source_end"]),
                "source_text": str(case["source_text"]),
                "opus_target_text": str(case["baseline_target_text"]),
                "opus_metricx_qe_score": opus_score,
                "mechanically_admissible_candidate_count": len(candidates),
                "first_mechanically_admissible_rank": first_rank,
                "first_mechanically_admissible_metricx_qe_score": (
                    None if first is None else first["metricx_qe_score"]
                ),
                "best_qe_admissible": best,
                "admissible_candidates_by_qe": candidates,
            }
        )

    if cases_with_admissible != 32:
        raise RuntimeError(f"run9 admissible-case count drift: {cases_with_admissible}")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only reference-free QE ranking of mechanically admissible raw TC-big alternatives for current run9 hard failures",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_semantic_selector": False,
        "metricx_is_not_acceptance_threshold": True,
        "semantic_review_required": True,
        "input_evidence_file_sha256": EXPECTED_INPUT_FILE_SHA256,
        "input_evidence_sha256": EXPECTED_INPUT_EVIDENCE_SHA256,
        "run9_database_sha256": EXPECTED_RUN9_DB_SHA256,
        "model": {
            "repository": BASE.METRICX_REPOSITORY,
            "revision": BASE.METRICX_REVISION,
            "license": BASE.METRICX_LICENSE,
            **metricx_identity,
        },
        "tokenizer": {
            "repository": BASE.TOKENIZER_REPOSITORY,
            "revision": BASE.TOKENIZER_REVISION,
            **tokenizer_identity,
        },
        "runtime": {
            "torch_version": str(torch.__version__),
            "device": "cpu",
            "max_input_length": BASE.MAX_INPUT_LENGTH,
            "batch_size": BASE.BATCH_SIZE,
        },
        "case_count": EXPECTED_CASE_COUNT,
        "admissible_candidate_count": admissible_candidate_count,
        "case_count_with_admissible_alternative": cases_with_admissible,
        "qe_prefers_some_admissible_over_opus_count": qe_prefers_any_admissible,
        "qe_prefers_first_admissible_over_opus_count": qe_prefers_first_admissible,
        "best_qe_admissible_rank_counts": {str(k): int(v) for k, v in sorted(best_rank_counts.items())},
        "best_qe_delta_summary": {
            "minimum": min(deltas) if deltas else None,
            "maximum": max(deltas) if deltas else None,
            "mean": (sum(deltas) / len(deltas)) if deltas else None,
        },
        "cases": cases_out,
        "database_mutated": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-metricx-qe-current-hard-failures-run9.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "admissible_candidate_count": admissible_candidate_count,
                "case_count_with_admissible_alternative": cases_with_admissible,
                "qe_prefers_some_admissible_over_opus_count": qe_prefers_any_admissible,
                "qe_prefers_first_admissible_over_opus_count": qe_prefers_first_admissible,
                "best_qe_admissible_rank_counts": payload["best_qe_admissible_rank_counts"],
                "best_qe_delta_summary": payload["best_qe_delta_summary"],
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
