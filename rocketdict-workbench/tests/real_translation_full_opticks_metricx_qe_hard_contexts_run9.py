from __future__ import annotations

"""Research-only MetricX-24 QE audit for row-aligned TC-big Stage10 contexts.

The upstream context audit already rejects Stage10 spans that cannot replace
complete run-9 Stage12 rows and keeps only raw TC-big hypotheses passing the
mechanical whole-context selector plus Gutenberg-emphasis preservation. This
module scores the current OPUS aggregate and those admissible whole-context
candidates on the *same immutable Stage10 source unit*.

MetricX is a ranking signal only. Scores never authorize Product selection,
rewrite text, or mutate the persisted database.
"""

from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

BASE_HELPER = Path(__file__).with_name("real_translation_full_opticks_metricx_qe_audit.py")
SPEC = importlib.util.spec_from_file_location("rocketdict_metricx_context_qe_base", BASE_HELPER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load maintained MetricX QE helper")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SCHEMA = "rocketdict-full-opticks-metricx-qe-hard-contexts-run9/1"
INPUT_SCHEMA = "rocketdict-full-opticks-alternative-mt-hard-contexts-run9/2"
EXPECTED_INPUT_FILE_SHA256 = "49d679789207440d5160f044944f4261cc957070462f0cce464e047c955878d3"
EXPECTED_INPUT_EVIDENCE_SHA256 = "9309a2b0d4ed4cf84b4f2efc9a6353cc191a98b2557c26aa19fbc1489c3a0a55"
EXPECTED_RUN9_DB_SHA256 = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
EXPECTED_CONTEXT_COUNT = 50
EXPECTED_ROW_ALIGNED = 49
EXPECTED_ADMISSIBLE_CONTEXTS = 18


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_QE_CONTEXT_RUN9_ROOT", "work/qe-context-run9")).resolve()
    input_path = root / "full-opticks-alternative-mt-hard-contexts-run9.json"
    database = root / "rocketdict.sqlite"
    model_dir = Path(os.environ["ROCKETDICT_METRICX_MODEL_DIR"]).resolve()
    tokenizer_dir = Path(os.environ["ROCKETDICT_METRICX_TOKENIZER_DIR"]).resolve()
    if not input_path.is_file() or not database.is_file():
        raise RuntimeError("context MetricX input missing")

    raw = input_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_INPUT_FILE_SHA256:
        raise RuntimeError("context TC-big evidence file identity drift")
    evidence = json.loads(raw.decode("utf-8"))
    if evidence.get("schema") != INPUT_SCHEMA or evidence.get("evidence_sha256") != EXPECTED_INPUT_EVIDENCE_SHA256:
        raise RuntimeError("context TC-big evidence canonical identity drift")
    if int(evidence.get("unique_context_count") or -1) != EXPECTED_CONTEXT_COUNT:
        raise RuntimeError("context cohort drift")
    if int(evidence.get("row_aligned_context_count") or -1) != EXPECTED_ROW_ALIGNED:
        raise RuntimeError("row-aligned context cohort drift")
    if int(evidence.get("mechanically_admissible_context_count") or -1) != EXPECTED_ADMISSIBLE_CONTEXTS:
        raise RuntimeError("admissible context cohort drift")
    if BASE._sha(database) != EXPECTED_RUN9_DB_SHA256:
        raise RuntimeError("run9 database identity drift")

    metricx_identity = BASE._tree_identity(model_dir, ("README.md", "config.json", "pytorch_model.bin"))
    weights_sha = next(row["sha256"] for row in metricx_identity["required_files"] if row["path"] == "pytorch_model.bin")
    if weights_sha != BASE.METRICX_WEIGHTS_SHA256:
        raise RuntimeError("MetricX weights identity drift")
    tokenizer_identity = BASE._tree_identity(tokenizer_dir, ("config.json", "special_tokens_map.json", "spiece.model", "tokenizer_config.json"))

    import torch
    from transformers import AutoTokenizer
    from metricx24.models import MT5ForRegression

    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir), local_files_only=True)
    model = MT5ForRegression.from_pretrained(str(model_dir), local_files_only=True, torch_dtype="auto").to("cpu")
    model.eval()

    records: list[dict[str, Any]] = []
    candidate_count = 0
    considered_cases: list[dict[str, Any]] = []
    for case in evidence["cases"]:
        admissible = [h for h in case.get("hypotheses") or [] if h.get("mechanically_admissible") is True]
        if not admissible:
            continue
        if case.get("replacement_row_aligned") is not True:
            raise RuntimeError(f"non-row-aligned context unexpectedly has admissible hypotheses: {case['case_id']}")
        considered_cases.append(case)
        cid = str(case["case_id"])
        source = str(case["source_text"])
        baseline = case.get("baseline_target_text")
        if not isinstance(baseline, str) or not baseline.strip():
            raise RuntimeError(f"missing baseline target for {cid}")
        records.append({"candidate_id": f"{cid}:opus", "source_text": source, "target_text": baseline})
        for hypothesis in admissible:
            rank = int(hypothesis["rank"])
            candidate_count += 1
            records.append({"candidate_id": f"{cid}:tc:{rank}", "source_text": source, "target_text": str(hypothesis["target_text"])})

    if len(considered_cases) != EXPECTED_ADMISSIBLE_CONTEXTS:
        raise RuntimeError("MetricX considered-context count drift")
    if candidate_count <= EXPECTED_ADMISSIBLE_CONTEXTS:
        raise RuntimeError("unexpectedly shallow context n-best inventory")

    scores = BASE._score_batches(records, tokenizer=tokenizer, model=model, torch=torch)
    score_by_id = dict(zip((row["candidate_id"] for row in records), scores, strict=True))

    cases_out: list[dict[str, Any]] = []
    prefers_any = 0
    prefers_first = 0
    best_rank_counts: Counter[int] = Counter()
    deltas: list[float] = []
    first_deltas: list[float] = []
    for case in considered_cases:
        cid = str(case["case_id"])
        opus_score = float(score_by_id[f"{cid}:opus"])
        candidates: list[dict[str, Any]] = []
        for hypothesis in case["hypotheses"]:
            if hypothesis.get("mechanically_admissible") is not True:
                continue
            rank = int(hypothesis["rank"])
            score = float(score_by_id[f"{cid}:tc:{rank}"])
            candidates.append({
                "rank": rank,
                "metricx_qe_score": score,
                "delta_vs_opus": opus_score - score,
                "target_text": str(hypothesis["target_text"]),
            })
        candidates.sort(key=lambda row: (float(row["metricx_qe_score"]), int(row["rank"])))
        best = candidates[0]
        first_rank = int(case["first_mechanically_admissible_rank"])
        first = next(row for row in candidates if int(row["rank"]) == first_rank)
        best_rank_counts[int(best["rank"])] += 1
        deltas.append(float(best["delta_vs_opus"]))
        first_deltas.append(float(first["delta_vs_opus"]))
        prefers_any += int(float(best["metricx_qe_score"]) < opus_score)
        prefers_first += int(float(first["metricx_qe_score"]) < opus_score)
        cases_out.append({
            "case_id": cid,
            "hard_sequences": list(case["hard_sequences"]),
            "member_sequences": list(case["member_sequences"]),
            "source_start": int(case["source_start"]),
            "source_end": int(case["source_end"]),
            "source_text": str(case["source_text"]),
            "opus_target_text": str(case["baseline_target_text"]),
            "opus_metricx_qe_score": opus_score,
            "mechanically_admissible_candidate_count": len(candidates),
            "first_mechanically_admissible_rank": first_rank,
            "first_mechanically_admissible_metricx_qe_score": first["metricx_qe_score"],
            "first_mechanically_admissible_delta_vs_opus": first["delta_vs_opus"],
            "best_qe_admissible": best,
            "admissible_candidates_by_qe": candidates,
        })

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only reference-free QE ranking of mechanically admissible whole Stage10 TC-big contexts against the aggregate current OPUS target on the same immutable source unit",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_semantic_selector": False,
        "metricx_is_not_acceptance_threshold": True,
        "semantic_review_required": True,
        "input_evidence_file_sha256": EXPECTED_INPUT_FILE_SHA256,
        "input_evidence_sha256": EXPECTED_INPUT_EVIDENCE_SHA256,
        "run9_database_sha256": EXPECTED_RUN9_DB_SHA256,
        "model": {"repository": BASE.METRICX_REPOSITORY, "revision": BASE.METRICX_REVISION, "license": BASE.METRICX_LICENSE, **metricx_identity},
        "tokenizer": {"repository": BASE.TOKENIZER_REPOSITORY, "revision": BASE.TOKENIZER_REVISION, **tokenizer_identity},
        "runtime": {"torch_version": str(torch.__version__), "device": "cpu", "max_input_length": BASE.MAX_INPUT_LENGTH, "batch_size": BASE.BATCH_SIZE},
        "case_count": len(cases_out),
        "admissible_candidate_count": candidate_count,
        "qe_prefers_some_admissible_over_opus_count": prefers_any,
        "qe_prefers_first_admissible_over_opus_count": prefers_first,
        "best_qe_admissible_rank_counts": {str(k): int(v) for k, v in sorted(best_rank_counts.items())},
        "best_qe_delta_summary": {"minimum": min(deltas), "maximum": max(deltas), "mean": sum(deltas) / len(deltas)},
        "first_admissible_qe_delta_summary": {"minimum": min(first_deltas), "maximum": max(first_deltas), "mean": sum(first_deltas) / len(first_deltas)},
        "cases": cases_out,
        "database_mutated": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    out = root / "full-opticks-metricx-qe-hard-contexts-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "case_count": len(cases_out),
        "admissible_candidate_count": candidate_count,
        "qe_prefers_some_admissible_over_opus_count": prefers_any,
        "qe_prefers_first_admissible_over_opus_count": prefers_first,
        "best_qe_admissible_rank_counts": payload["best_qe_admissible_rank_counts"],
        "best_qe_delta_summary": payload["best_qe_delta_summary"],
        "evidence_sha256": payload["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
