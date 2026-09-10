from __future__ import annotations

"""Research-only MetricX-24 QE audit for TC-big failure-triggered candidates.

The maintained OPUS Product baseline has 27 hard numeric failures. Pinned TC-big
beam-6 contains mechanically strict raw candidates for a subset, but manual
review proves that mechanical integrity cannot distinguish terminology and
semantic errors. This audit scores the immutable OPUS target and every raw
TC-big hypothesis with a pinned reference-free MetricX-24 model (source + MT,
no reference) to test whether learned QE is useful as a *research ranking
surface*.

MetricX never authorizes Product promotion here. Inputs are immutable artifact
text, the Product database is not opened or mutated, no target is rewritten,
and no score threshold is treated as an acceptance rule.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCHEMA = "rocketdict-full-opticks-metricx-qe-audit/1"
NBEST_SCHEMA = "rocketdict-full-opticks-tc-big-failure-nbest/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"
EXPECTED_BASELINE_JSON_SHA256 = "3d899605172decdadbab55eedf9fb161c5dd599a921679bea47fd98adbf2efb4"
EXPECTED_DATABASE_SHA256 = "eff56dab177baa161b6e8126a9ff75ecdc341c19deff5866fec201c6bf232687"
EXPECTED_NBEST_EVIDENCE_SHA256 = "77a10398319094cdbc09ba1096dd236bac64970c06baac539283b983f240bfb8"
METRICX_REPOSITORY = "google/metricx-24-hybrid-large-v2p6-bfloat16"
METRICX_REVISION = "febb720e29a059df2e8af3ffd71dcdc9e0a24910"
METRICX_LICENSE = "apache-2.0"
METRICX_WEIGHTS_SHA256 = "b1f2c03ab5ec5318a55b90b42eefa22431daa7b1a8e28a97a6aef23d18a24278"
METRICX_CODE_REPOSITORY = "google-research/metricx"
METRICX_CODE_REVISION = "fc4978eb064670f7cc33e93ea4f52d38396b8ae6"
TOKENIZER_REPOSITORY = "google/mt5-large"
TOKENIZER_REVISION = "50b7223e98fcd124b0cabb1ec81bc6324c7df107"
MAX_INPUT_LENGTH = 1536
BATCH_SIZE = 4


def _sha(path: Path) -> str:
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


def _tree_identity(root: Path, required: tuple[str, ...]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for relative in required:
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"required pinned MetricX/QE file missing: {root}/{relative}")
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
        )
    return {
        "required_file_count": len(rows),
        "required_file_bytes": sum(int(row["bytes"]) for row in rows),
        "required_files": rows,
        "required_tree_sha256": _canonical_sha(rows),
    }


def _score_batches(
    records: list[dict[str, Any]],
    *,
    tokenizer: Any,
    model: Any,
    torch: Any,
) -> list[float]:
    prepared: list[dict[str, Any]] = []
    for record in records:
        model_input = "source: " + str(record["source_text"]) + " candidate: " + str(record["target_text"])
        tokenized = tokenizer(
            model_input,
            add_special_tokens=True,
            truncation=False,
            padding=False,
        )
        ids = list(tokenized["input_ids"])
        mask = list(tokenized["attention_mask"])
        if ids and ids[-1] == tokenizer.eos_token_id:
            ids = ids[:-1]
            mask = mask[:-1]
        if len(ids) > MAX_INPUT_LENGTH:
            raise RuntimeError(
                f"MetricX QE input would truncate for {record['candidate_id']}: "
                f"{len(ids)} > {MAX_INPUT_LENGTH}"
            )
        prepared.append({"input_ids": ids, "attention_mask": mask})

    scores: list[float] = []
    for start in range(0, len(prepared), BATCH_SIZE):
        batch = prepared[start : start + BATCH_SIZE]
        max_len = max(len(row["input_ids"]) for row in batch)
        pad_id = int(tokenizer.pad_token_id)
        ids = [
            row["input_ids"] + [pad_id] * (max_len - len(row["input_ids"]))
            for row in batch
        ]
        masks = [
            row["attention_mask"] + [0] * (max_len - len(row["attention_mask"]))
            for row in batch
        ]
        with torch.inference_mode():
            result = model(
                input_ids=torch.tensor(ids, dtype=torch.long),
                attention_mask=torch.tensor(masks, dtype=torch.long),
            )
        predictions = result.predictions.detach().cpu().to(torch.float32).tolist()
        scores.extend(float(value) for value in predictions)
    if len(scores) != len(records):
        raise RuntimeError("MetricX QE score cardinality drift")
    return scores


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_QE_ROOT", "work/qe-input")).resolve()
    model_dir = Path(os.environ.get("ROCKETDICT_METRICX_MODEL_DIR", "work/metricx-model")).resolve()
    tokenizer_dir = Path(os.environ.get("ROCKETDICT_METRICX_TOKENIZER_DIR", "work/metricx-tokenizer")).resolve()
    nbest_path = root / "full-opticks-tc-big-failure-nbest.json"
    baseline_path = root / "full-opticks-numeric-stress.json"
    database_path = root / "rocketdict.sqlite"
    for path in (nbest_path, baseline_path, database_path):
        if not path.is_file():
            raise RuntimeError(f"MetricX QE input missing: {path}")

    nbest_bytes = nbest_path.read_bytes()
    nbest = json.loads(nbest_bytes.decode("utf-8"))
    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    if nbest.get("schema") != NBEST_SCHEMA:
        raise RuntimeError("MetricX QE n-best schema drift")
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise RuntimeError("MetricX QE baseline schema drift")
    if nbest.get("source_sha256") != OPTICKS_SHA256 or baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("MetricX QE Opticks source identity drift")
    if nbest.get("planner_contract") != PLANNER_CONTRACT or baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("MetricX QE planner contract drift")
    if hashlib.sha256(baseline_bytes).hexdigest() != EXPECTED_BASELINE_JSON_SHA256:
        raise RuntimeError("MetricX QE immutable baseline JSON SHA drift")
    if _sha(database_path) != EXPECTED_DATABASE_SHA256:
        raise RuntimeError("MetricX QE immutable Product database SHA drift")
    if str(nbest.get("evidence_sha256") or "") != EXPECTED_NBEST_EVIDENCE_SHA256:
        raise RuntimeError("MetricX QE TC-big n-best evidence identity drift")
    if int(nbest.get("baseline_failure_count") or -1) != 27:
        raise RuntimeError("MetricX QE expected exactly 27 OPUS hard failures")

    metricx_identity = _tree_identity(
        model_dir,
        ("README.md", "config.json", "pytorch_model.bin"),
    )
    weights_sha = next(
        row["sha256"] for row in metricx_identity["required_files"] if row["path"] == "pytorch_model.bin"
    )
    if weights_sha != METRICX_WEIGHTS_SHA256:
        raise RuntimeError(f"MetricX weights drift: {weights_sha} != {METRICX_WEIGHTS_SHA256}")
    tokenizer_identity = _tree_identity(
        tokenizer_dir,
        ("config.json", "special_tokens_map.json", "spiece.model", "tokenizer_config.json"),
    )

    import torch
    from transformers import AutoTokenizer
    from metricx24.models import MT5ForRegression

    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir), local_files_only=True)
    model = MT5ForRegression.from_pretrained(
        str(model_dir),
        local_files_only=True,
        torch_dtype="auto",
    )
    model = model.to("cpu")
    model.eval()

    flat: list[dict[str, Any]] = []
    for case in nbest.get("cases") or []:
        sequence = int(case["sequence_number"])
        source = str(case["source_text"])
        flat.append(
            {
                "candidate_id": f"{sequence}:opus",
                "sequence_number": sequence,
                "kind": "opus_baseline",
                "rank": None,
                "source_text": source,
                "target_text": str(case["baseline_target_text"]),
                "mechanically_strict": False,
            }
        )
        for hyp in case.get("hypotheses") or []:
            flat.append(
                {
                    "candidate_id": f"{sequence}:tc:{int(hyp['rank'])}",
                    "sequence_number": sequence,
                    "kind": "tc_big",
                    "rank": int(hyp["rank"]),
                    "source_text": source,
                    "target_text": str(hyp["target_text"]),
                    "mechanically_strict": bool(hyp.get("strict_pass_fail_closed")),
                }
            )
    expected = 27 * 7
    if len(flat) != expected:
        raise RuntimeError(f"MetricX QE candidate inventory drift: {len(flat)} != {expected}")

    scores = _score_batches(flat, tokenizer=tokenizer, model=model, torch=torch)
    score_by_id = dict(zip((row["candidate_id"] for row in flat), scores, strict=True))

    cases_out: list[dict[str, Any]] = []
    qe_prefers_strict_tc_count = 0
    strict_candidate_case_count = 0
    best_strict_rank_counts: Counter[int] = Counter()
    for case in nbest["cases"]:
        sequence = int(case["sequence_number"])
        opus_id = f"{sequence}:opus"
        opus_score = float(score_by_id[opus_id])
        hypotheses: list[dict[str, Any]] = []
        strict_rows: list[dict[str, Any]] = []
        for hyp in case["hypotheses"]:
            rank = int(hyp["rank"])
            row = {
                "rank": rank,
                "metricx_qe_score": float(score_by_id[f"{sequence}:tc:{rank}"]),
                "strict_pass_fail_closed": bool(hyp.get("strict_pass_fail_closed")),
                "numeric_pass_fail_closed": bool(hyp.get("numeric_pass_fail_closed")),
                "target_text": str(hyp["target_text"]),
            }
            hypotheses.append(row)
            if row["strict_pass_fail_closed"]:
                strict_rows.append(row)
        strict_rows.sort(key=lambda row: (row["metricx_qe_score"], row["rank"]))
        best_strict = strict_rows[0] if strict_rows else None
        if best_strict is not None:
            strict_candidate_case_count += 1
            best_strict_rank_counts[int(best_strict["rank"])] += 1
            if float(best_strict["metricx_qe_score"]) < opus_score:
                qe_prefers_strict_tc_count += 1
        cases_out.append(
            {
                "sequence_number": sequence,
                "source_start": int(case["source_start"]),
                "source_end": int(case["source_end"]),
                "source_text": str(case["source_text"]),
                "opus_baseline_target_text": str(case["baseline_target_text"]),
                "opus_baseline_metricx_qe_score": opus_score,
                "tc_big_hypotheses": hypotheses,
                "strict_candidate_count": len(strict_rows),
                "metricx_best_strict_tc_big_rank": (
                    int(best_strict["rank"]) if best_strict is not None else None
                ),
                "metricx_best_strict_tc_big_score": (
                    float(best_strict["metricx_qe_score"]) if best_strict is not None else None
                ),
                "metricx_prefers_best_strict_tc_over_failing_opus": bool(
                    best_strict is not None
                    and float(best_strict["metricx_qe_score"]) < opus_score
                ),
            }
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only reference-free MetricX-24 ranking audit over immutable OPUS failures "
            "and raw TC-big beam-6 hypotheses; no score is a Product acceptance rule"
        ),
        "promotion_allowed": False,
        "automatic_selector_allowed": False,
        "semantic_review_required": True,
        "product_baseline_changed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "baseline_json_sha256": EXPECTED_BASELINE_JSON_SHA256,
        "baseline_database_sha256": EXPECTED_DATABASE_SHA256,
        "tc_big_nbest_json_sha256": hashlib.sha256(nbest_bytes).hexdigest(),
        "tc_big_nbest_evidence_sha256": EXPECTED_NBEST_EVIDENCE_SHA256,
        "metricx": {
            "repository": METRICX_REPOSITORY,
            "requested_revision": METRICX_REVISION,
            "license": METRICX_LICENSE,
            "weights_sha256": METRICX_WEIGHTS_SHA256,
            "identity": metricx_identity,
            "code_repository": METRICX_CODE_REPOSITORY,
            "code_revision": METRICX_CODE_REVISION,
            "mode": "reference-free-qe",
            "score_semantics": "lower_is_better_predicted_error_0_to_25",
            "max_input_length": MAX_INPUT_LENGTH,
            "input_truncation_allowed": False,
            "batch_size": BATCH_SIZE,
        },
        "tokenizer": {
            "repository": TOKENIZER_REPOSITORY,
            "requested_revision": TOKENIZER_REVISION,
            "identity": tokenizer_identity,
        },
        "runtime": {
            "torch_version": str(torch.__version__),
            "model_dtype": str(next(model.parameters()).dtype),
            "device": "cpu",
        },
        "case_count": len(cases_out),
        "candidate_score_count": len(flat),
        "strict_candidate_case_count": strict_candidate_case_count,
        "metricx_prefers_strict_tc_over_failing_opus_count": qe_prefers_strict_tc_count,
        "metricx_best_strict_rank_counts": {
            str(rank): count for rank, count in sorted(best_strict_rank_counts.items())
        },
        "cases": cases_out,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-metricx-qe-audit.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "case_count": len(cases_out),
                "candidate_score_count": len(flat),
                "strict_candidate_case_count": strict_candidate_case_count,
                "metricx_prefers_strict_tc_over_failing_opus_count": qe_prefers_strict_tc_count,
                "metricx_best_strict_rank_counts": payload["metricx_best_strict_rank_counts"],
                "model_dtype": payload["runtime"]["model_dtype"],
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
