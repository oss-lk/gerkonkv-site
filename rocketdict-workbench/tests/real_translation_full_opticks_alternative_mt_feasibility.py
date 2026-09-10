from __future__ import annotations

"""Research-only alternative-MT probe over immutable full-Opticks failure spans.

This experiment answers one narrow question: after the maintained OPUS baseline,
source-derived resegmentation, whole-context rescue, and raw OPUS n-best all fail
semantic review, does an independently trained real EN->RU model already contain
better raw hypotheses for the same immutable source bytes?

It never changes Product policy, never rewrites source/target text, never injects
literals/placeholders, and never writes to the Product database. Mechanical
checks are exported only as diagnostics; promotion always requires separate
semantic review and a complete Product/full-corpus regression.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.translation_rescue import evaluate_rescue_pair


SCHEMA = "rocketdict-full-opticks-alternative-mt-feasibility/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTIN_SCHEMA = "rocketdict-full-opticks-selective-rescue-optin/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"
MODEL_REPO = "Helsinki-NLP/opus-mt-tc-big-en-zle"
MODEL_REVISION = "708be1d372fe4c358a352f404e6dc9ca0126ba48"
MODEL_LICENSE = "cc-by-4.0"
MODEL_SAFETENSORS_SHA256 = "e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416"
TARGET_PREFIX = ">>rus<< "
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 512
EXPECTED_RESIDUALS = {
    744: (133139, 133431, "long_content_omission"),
    2296: (401232, 401532, "compact_formula"),
    2381: (417625, 417917, "large_integer_ratio"),
    2750: (483234, 483458, "large_integer_product"),
    2898: (507544, 507698, "extreme_integer_scale"),
}
REQUIRED_MODEL_FILES = (
    "README.md",
    "config.json",
    "generation_config.json",
    "model.safetensors",
    "source.spm",
    "special_tokens_map.json",
    "target.spm",
    "tokenizer_config.json",
    "vocab.json",
)


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


def _model_identity(model_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for relative in REQUIRED_MODEL_FILES:
        path = model_dir / relative
        if not path.is_file():
            raise RuntimeError(f"pinned alternative MT file is missing: {relative}")
        size = path.stat().st_size
        total += size
        rows.append({"path": relative, "bytes": size, "sha256": _sha(path)})
    weights_sha = next(row["sha256"] for row in rows if row["path"] == "model.safetensors")
    if weights_sha != MODEL_SAFETENSORS_SHA256:
        raise RuntimeError(
            "alternative MT weights drift: "
            f"{weights_sha!r} != {MODEL_SAFETENSORS_SHA256!r}"
        )
    readme = (model_dir / "README.md").read_text(encoding="utf-8")
    if re.search(r"(?im)^license:\s*cc-by-4\.0\s*$", readme) is None:
        raise RuntimeError("alternative MT README no longer declares CC-BY-4.0")
    tree_sha = _canonical_sha(rows)
    return {
        "repository": MODEL_REPO,
        "requested_revision": MODEL_REVISION,
        "license": MODEL_LICENSE,
        "target_prefix": TARGET_PREFIX.strip(),
        "required_files": rows,
        "required_file_count": len(rows),
        "required_file_bytes": total,
        "required_tree_sha256": tree_sha,
        "model_safetensors_sha256": weights_sha,
    }


def _load_cases(baseline: dict[str, Any], optin: dict[str, Any]) -> list[dict[str, Any]]:
    failures = {
        int(row["planned_sequence"]): row
        for row in baseline.get("numeric_failures") or []
    }
    cases: list[dict[str, Any]] = []
    for sequence, (expected_start, expected_end, family) in EXPECTED_RESIDUALS.items():
        row = failures.get(sequence)
        if row is None:
            raise RuntimeError(f"expected residual sequence {sequence} is absent")
        start = int(row["source_start"])
        end = int(row["source_end"])
        if (start, end) != (expected_start, expected_end):
            raise RuntimeError(
                f"residual sequence {sequence} span drift: {(start, end)!r}"
            )
        cases.append(
            {
                "case_id": f"planner_residual_{sequence}",
                "family": family,
                "source_start": start,
                "source_end": end,
                "source_text": str(row["source_text"]),
                "baseline_target_text": str(row["product_target_text"]),
                "baseline_planned_sequence": sequence,
                "source_origin": "planner_v8_numeric_failure",
            }
        )

    accepted = list(optin.get("accepted_contexts") or [])
    if len(accepted) != 1 or int(accepted[0].get("context_sequence") or -1) != 669:
        raise RuntimeError("expected exactly selective-rescue context 669")
    context = accepted[0]
    source_text = str(context["source_text"])
    if (int(context["source_start"]), int(context["source_end"])) != (132834, 133465):
        raise RuntimeError("selective-rescue context 669 immutable span drift")
    primary_target = "".join(
        str(row.get("target_text") or "") for row in context.get("primary_rows") or []
    )
    rank0_rescue_target = "".join(
        str(row.get("target_text") or "") for row in context.get("selected_rows") or []
    )
    cases.insert(
        0,
        {
            "case_id": "selective_context_669_whole",
            "family": "long_content_omission_parent_context",
            "source_start": int(context["source_start"]),
            "source_end": int(context["source_end"]),
            "source_text": source_text,
            "baseline_target_text": primary_target,
            "rank0_selective_rescue_target_text": rank0_rescue_target,
            "source_origin": "selective_rescue_parent_context",
        },
    )
    chunks = list(context.get("selected_rows") or [])
    if len(chunks) != 3:
        raise RuntimeError("context 669 no longer has the expected three rescue chunks")
    for index, row in enumerate(chunks):
        cases.append(
            {
                "case_id": f"selective_context_669_chunk_{index}",
                "family": "long_content_omission_semicolon_chunk",
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "baseline_target_text": str(row.get("target_text") or ""),
                "split_mode": str(row.get("split_mode") or ""),
                "source_origin": "selective_rescue_chunk",
            }
        )
    return cases


def _translate_case(
    *,
    case: dict[str, Any],
    tokenizer: Any,
    model: Any,
    torch: Any,
) -> dict[str, Any]:
    source = str(case["source_text"])
    model_input = TARGET_PREFIX + source
    encoded = tokenizer(
        model_input,
        return_tensors="pt",
        add_special_tokens=True,
        truncation=False,
    )
    input_ids = encoded["input_ids"]
    input_tokens = int(input_ids.shape[-1])
    max_positions = int(getattr(model.config, "max_position_embeddings", 0) or 0)
    if max_positions <= 0:
        raise RuntimeError("alternative model does not publish max_position_embeddings")
    if input_tokens > max_positions:
        raise RuntimeError(
            f"alternative MT input would exceed model context: {input_tokens} > {max_positions}"
        )
    unk_id = tokenizer.unk_token_id
    unk_count = int((input_ids == int(unk_id)).sum().item()) if unk_id is not None else 0

    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            do_sample=False,
            num_beams=BEAM_SIZE,
            num_return_sequences=NUM_HYPOTHESES,
            max_length=MAX_DECODING_LENGTH,
            return_dict_in_generate=True,
            output_scores=True,
            renormalize_logits=True,
        )
    sequences = generated.sequences.detach().cpu()
    if int(sequences.shape[0]) != NUM_HYPOTHESES:
        raise RuntimeError("alternative MT returned unexpected hypothesis count")
    sequence_scores = getattr(generated, "sequences_scores", None)
    if sequence_scores is not None:
        sequence_scores = sequence_scores.detach().cpu().tolist()
    eos_id = tokenizer.eos_token_id
    pad_id = tokenizer.pad_token_id
    hypotheses: list[dict[str, Any]] = []
    for rank, token_tensor in enumerate(sequences):
        token_ids = [int(value) for value in token_tensor.tolist()]
        significant = [value for value in token_ids if pad_id is None or value != int(pad_id)]
        terminated = bool(eos_id is not None and significant and significant[-1] == int(eos_id))
        if not terminated:
            raise RuntimeError(
                f"alternative MT hypothesis {case['case_id']} rank {rank} lacks EOS; "
                "possible decoding truncation"
            )
        target = tokenizer.decode(token_ids, skip_special_tokens=True).strip()
        hypotheses.append(
            {
                "rank": rank,
                "score": (
                    float(sequence_scores[rank])
                    if sequence_scores is not None and rank < len(sequence_scores)
                    else None
                ),
                "target_text": target,
                "output_token_count": len(significant),
                "terminated_with_eos": True,
                "mechanical_verdict": evaluate_rescue_pair(source, target),
            }
        )
    result = dict(case)
    result.update(
        {
            "model_input_prefix": TARGET_PREFIX.strip(),
            "input_token_count": input_tokens,
            "input_unknown_token_count": unk_count,
            "model_max_position_embeddings": max_positions,
            "input_truncated": False,
            "generation": {
                "beam_size": BEAM_SIZE,
                "num_hypotheses": NUM_HYPOTHESES,
                "max_decoding_length": MAX_DECODING_LENGTH,
                "do_sample": False,
            },
            "hypotheses": hypotheses,
            "strict_mechanical_hypothesis_count": sum(
                1
                for row in hypotheses
                if (row.get("mechanical_verdict") or {}).get("strictly_eligible") is True
            ),
        }
    )
    return result


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/baseline/full-opticks-numeric-stress",
        )
    ).resolve()
    model_dir = Path(
        os.environ.get("ROCKETDICT_ALT_MT_MODEL_DIR", "work/alt-mt-model")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    optin_path = root / "full-opticks-selective-rescue-optin.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    for path in (baseline_path, optin_path, database):
        if not path.is_file():
            raise RuntimeError(f"required immutable baseline input is missing: {path}")

    baseline_bytes = baseline_path.read_bytes()
    optin_bytes = optin_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    optin = json.loads(optin_bytes.decode("utf-8"))
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise RuntimeError("unexpected full-Opticks baseline schema")
    if optin.get("schema") != OPTIN_SCHEMA:
        raise RuntimeError("unexpected selective-rescue evidence schema")
    if baseline.get("source_sha256") != OPTICKS_SHA256 or optin.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT or optin.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("alternative MT DOE requires planner-v8 evidence")
    if int(baseline.get("product_numeric_failure_count") or -1) != 27:
        raise RuntimeError("baseline hard numeric failure count drift")
    if optin.get("promotion_allowed") is not False:
        raise RuntimeError("selective-rescue evidence unexpectedly permits promotion")
    if int(optin.get("enabled_hard_numeric_failure_count") or -1) != 26:
        raise RuntimeError("selective-rescue mechanical comparison drift")

    database_sha_before = _sha(database)
    model_identity = _model_identity(model_dir)
    cases = _load_cases(baseline, optin)

    import torch
    from transformers import MarianMTModel, MarianTokenizer

    tokenizer = MarianTokenizer.from_pretrained(
        str(model_dir),
        local_files_only=True,
    )
    model = MarianMTModel.from_pretrained(
        str(model_dir),
        local_files_only=True,
        use_safetensors=True,
    )
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    if str(model.config.model_type) != "marian":
        raise RuntimeError(f"unexpected alternative model type: {model.config.model_type!r}")

    results = [
        _translate_case(case=case, tokenizer=tokenizer, model=model, torch=torch)
        for case in cases
    ]
    database_sha_after = _sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("alternative MT feasibility DOE mutated Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only independent real-MT differential on immutable full-Opticks "
            "failure spans after the maintained OPUS baseline exhausted planner/n-best alternatives"
        ),
        "promotion_allowed": False,
        "semantic_review_required": True,
        "automatic_semantic_selector": False,
        "product_baseline_changed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(baseline.get("source_text_sha256") or ""),
        "planner_contract": PLANNER_CONTRACT,
        "baseline_json_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "optin_json_sha256": hashlib.sha256(optin_bytes).hexdigest(),
        "baseline_evidence_sha256": str(baseline.get("evidence_sha256") or ""),
        "optin_evidence_sha256": str(optin.get("evidence_sha256") or ""),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
        "model": model_identity,
        "runtime": {
            "torch_version": str(torch.__version__),
            "torch_compute_dtype": "float32",
            "device": "cpu",
            "transformers_class": "MarianMTModel",
        },
        "case_count": len(results),
        "cases": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-alternative-mt-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "model_repository": MODEL_REPO,
                "model_revision": MODEL_REVISION,
                "case_count": len(results),
                "strict_mechanical_counts": {
                    row["case_id"]: row["strict_mechanical_hypothesis_count"]
                    for row in results
                },
                "database_mutated": False,
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
