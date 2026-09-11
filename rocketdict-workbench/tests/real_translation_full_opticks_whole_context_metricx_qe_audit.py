from __future__ import annotations

"""Reference-free MetricX audit for strict whole-context hard-failure candidates.

The input cohort is produced only from split Product contexts that already fail
at least one maintained hard gate. MetricX scores the unchanged concatenated
primary target and the unchanged raw rank-0 whole-context target. Scores are a
research ranking surface only: no threshold or preference authorizes Product
selection.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

SCHEMA = "rocketdict-full-opticks-whole-context-metricx-qe/1"
COHORT_SCHEMA = "rocketdict-full-opticks-whole-context-hard-failure-cohort/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"
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
        model_input = (
            "source: "
            + str(record["source_text"])
            + " candidate: "
            + str(record["target_text"])
        )
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
    model_dir = Path(
        os.environ.get("ROCKETDICT_METRICX_MODEL_DIR", "work/metricx-model")
    ).resolve()
    tokenizer_dir = Path(
        os.environ.get("ROCKETDICT_METRICX_TOKENIZER_DIR", "work/metricx-tokenizer")
    ).resolve()
    cohort_path = root / "full-opticks-whole-context-hard-failure-cohort.json"
    if not cohort_path.is_file():
        raise RuntimeError(f"whole-context MetricX cohort input missing: {cohort_path}")

    cohort_bytes = cohort_path.read_bytes()
    cohort = json.loads(cohort_bytes.decode("utf-8"))
    if cohort.get("schema") != COHORT_SCHEMA:
        raise RuntimeError("whole-context MetricX cohort schema drift")
    if cohort.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("whole-context MetricX Opticks source identity drift")
    if cohort.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("whole-context MetricX planner contract drift")
    if cohort.get("promotion_allowed") is not False:
        raise RuntimeError("whole-context cohort unexpectedly allows Product promotion")
    if cohort.get("automatic_product_selection_allowed") is not False:
        raise RuntimeError("whole-context cohort unexpectedly allows automatic selection")

    accepted = [
        dict(row)
        for row in list(cohort.get("review_candidates") or [])
        if row.get("status") == "mechanically_accepted"
    ]
    expected_sequences = [
        int(value) for value in cohort.get("accepted_context_sequences", [])
    ]
    if [int(row["context_sequence"]) for row in accepted] != expected_sequences:
        raise RuntimeError("whole-context accepted cohort sequence drift")
    if len(accepted) != int(
        cohort.get("mechanically_accepted_hard_failure_context_count") or -1
    ):
        raise RuntimeError("whole-context accepted cohort cardinality drift")
    if not accepted:
        raise RuntimeError("whole-context MetricX cohort has no mechanically accepted cases")

    metricx_identity = _tree_identity(
        model_dir,
        ("README.md", "config.json", "pytorch_model.bin"),
    )
    weights_sha = next(
        row["sha256"]
        for row in metricx_identity["required_files"]
        if row["path"] == "pytorch_model.bin"
    )
    if weights_sha != METRICX_WEIGHTS_SHA256:
        raise RuntimeError(
            f"MetricX weights drift: {weights_sha} != {METRICX_WEIGHTS_SHA256}"
        )
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
    for case in accepted:
        sequence = int(case["context_sequence"])
        source = str(case["source_text"])
        flat.extend(
            [
                {
                    "candidate_id": f"{sequence}:primary",
                    "context_sequence": sequence,
                    "kind": "primary_split_concatenated",
                    "source_text": source,
                    "target_text": str(case["primary_target_concatenated"]),
                },
                {
                    "candidate_id": f"{sequence}:whole",
                    "context_sequence": sequence,
                    "kind": "whole_context_rank0",
                    "source_text": source,
                    "target_text": str(case["whole_context_rank0_target"]),
                },
            ]
        )
    scores = _score_batches(flat, tokenizer=tokenizer, model=model, torch=torch)
    score_by_id = dict(zip((row["candidate_id"] for row in flat), scores, strict=True))

    cases_out: list[dict[str, Any]] = []
    preference_counts: Counter[str] = Counter()
    for case in accepted:
        sequence = int(case["context_sequence"])
        primary_score = float(score_by_id[f"{sequence}:primary"])
        whole_score = float(score_by_id[f"{sequence}:whole"])
        if whole_score < primary_score:
            preference = "whole_context"
        elif primary_score < whole_score:
            preference = "primary_split"
        else:
            preference = "tie"
        preference_counts[preference] += 1
        cases_out.append(
            {
                "context_sequence": sequence,
                "hard_failure_segment_sequences": list(
                    case["hard_failure_segment_sequences"]
                ),
                "hard_failure_gates": list(case["hard_failure_gates"]),
                "source_start": int(case["source_start"]),
                "source_end": int(case["source_end"]),
                "nlp_token_count": int(case["nlp_token_count"]),
                "source_text": str(case["source_text"]),
                "primary_target_concatenated": str(
                    case["primary_target_concatenated"]
                ),
                "whole_context_rank0_target": str(
                    case["whole_context_rank0_target"]
                ),
                "primary_metricx_qe_score": primary_score,
                "whole_context_metricx_qe_score": whole_score,
                "whole_minus_primary_metricx_qe": whole_score - primary_score,
                "metricx_preference": preference,
            }
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only reference-free MetricX-24 comparison of unchanged "
            "primary split targets versus strict raw whole-context candidates"
        ),
        "promotion_allowed": False,
        "automatic_selector_allowed": False,
        "score_threshold_is_acceptance_rule": False,
        "semantic_review_required": True,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": cohort.get("source_text_sha256"),
        "planner_contract": PLANNER_CONTRACT,
        "cohort_json_sha256": hashlib.sha256(cohort_bytes).hexdigest(),
        "cohort_evidence_sha256": cohort.get("evidence_sha256"),
        "source_workflow_run_id": os.environ.get("ROCKETDICT_SOURCE_RUN_ID"),
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
        "metricx_preference_counts": dict(sorted(preference_counts.items())),
        "cases": cases_out,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-whole-context-metricx-qe.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "case_count": len(cases_out),
                "candidate_score_count": len(flat),
                "metricx_preference_counts": dict(sorted(preference_counts.items())),
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
