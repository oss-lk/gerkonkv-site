from __future__ import annotations

"""Research-only WMT19 EN->RU differential on immutable Opticks failure spans.

This is an independent-model control for the focused TC-big experiment. It
reuses the exact immutable Product baseline/context inventory but uses the
Apache-2.0 ``facebook/wmt19-en-ru`` FSMT checkpoint. The model card warns that
repeated sub-phrases can lead to content truncation, so decoder non-termination
and hitting the configured generation ceiling are retained as separate
fail-closed evidence. A forced EOS at the last permitted token does not turn a
ceiling-limited generation into acceptable evidence. No result is eligible for
automatic Product promotion.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.translation_rescue import evaluate_rescue_pair


BASE_PATH = Path(__file__).with_name(
    "real_translation_full_opticks_alternative_mt_feasibility.py"
)
SPEC = importlib.util.spec_from_file_location("rocketdict_tc_big_focused", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load focused alternative-MT inventory helper")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SCHEMA = "rocketdict-full-opticks-wmt19-feasibility/4"
MODEL_REPO = "facebook/wmt19-en-ru"
MODEL_REVISION = "834cdada94e68977b9d6c1224ca43a37390936ef"
MODEL_LICENSE = "apache-2.0"
MODEL_SAFETENSORS_SHA256 = "ee0ce2988699b06bb7cd8a0152807f93638b66d653c76fb09e1f28aa4791398d"
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 512
REQUIRED_MODEL_FILES = (
    "README.md",
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "tokenizer_config.json",
    "vocab-src.json",
    "vocab-tgt.json",
)


def _model_identity(model_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for relative in REQUIRED_MODEL_FILES:
        path = model_dir / relative
        if not path.is_file():
            raise RuntimeError(f"pinned WMT19 file is missing: {relative}")
        size = path.stat().st_size
        total += size
        rows.append({"path": relative, "bytes": size, "sha256": BASE._sha(path)})
    weights_sha = next(row["sha256"] for row in rows if row["path"] == "model.safetensors")
    if weights_sha != MODEL_SAFETENSORS_SHA256:
        raise RuntimeError(f"WMT19 safetensors drift: {weights_sha!r}")
    readme = (model_dir / "README.md").read_text(encoding="utf-8")
    if re.search(r"(?im)^license:\s*apache-2\.0\s*$", readme) is None:
        raise RuntimeError("WMT19 README no longer declares Apache-2.0")
    return {
        "repository": MODEL_REPO,
        "requested_revision": MODEL_REVISION,
        "license": MODEL_LICENSE,
        "known_model_card_risk": "repeated_subphrases_can_truncate_content",
        "required_files": rows,
        "required_file_count": len(rows),
        "required_file_bytes": total,
        "required_tree_sha256": BASE._canonical_sha(rows),
        "model_safetensors_sha256": weights_sha,
    }


def _single_special_token_id(value: Any, *, name: str, source: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise RuntimeError(
                f"WMT19 {name} from {source} must be scalar/singleton, got {value!r}"
            )
        value = value[0]
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"WMT19 {name} from {source} is not an integer token id: {value!r}"
        ) from exc


def resolve_special_token_id(name: str, *, tokenizer: Any, model: Any) -> int:
    """Resolve one FSMT special token from every authoritative runtime surface."""

    sources = (
        ("tokenizer", getattr(tokenizer, name, None)),
        (
            "generation_config",
            getattr(getattr(model, "generation_config", None), name, None),
        ),
        ("model_config", getattr(getattr(model, "config", None), name, None)),
    )
    resolved: list[tuple[str, int]] = []
    for source, value in sources:
        token_id = _single_special_token_id(value, name=name, source=source)
        if token_id is not None:
            resolved.append((source, token_id))
    if not resolved:
        raise RuntimeError(f"WMT19 runtime publishes no {name}")
    distinct = {value for _source, value in resolved}
    if len(distinct) != 1:
        raise RuntimeError(
            f"WMT19 {name} disagreement across runtime surfaces: {resolved!r}"
        )
    return resolved[0][1]


def generation_ceiling_hit(token_count: int, *, max_length: int) -> bool:
    """Return whether generation consumed the complete configured token budget.

    Some generation backends force an EOS into the final allowed position.  That
    is still ceiling-limited evidence: we cannot distinguish a naturally
    completed hypothesis from output that was forced closed only because the
    budget ended.  Product-quality research therefore fails closed whenever the
    significant sequence length reaches ``max_length``.
    """

    if max_length < 1:
        raise ValueError("max_length must be positive")
    return int(token_count) >= int(max_length)


def _translate_case(
    *, case: dict[str, Any], tokenizer: Any, model: Any, torch: Any
) -> dict[str, Any]:
    source = str(case["source_text"])
    encoded = tokenizer(
        source,
        return_tensors="pt",
        add_special_tokens=True,
        truncation=False,
    )
    input_ids = encoded["input_ids"]
    input_tokens = int(input_ids.shape[-1])
    max_positions = int(
        getattr(model.config, "max_position_embeddings", 0)
        or getattr(tokenizer, "model_max_length", 0)
        or 0
    )
    if max_positions <= 0 or input_tokens > max_positions:
        raise RuntimeError(
            f"WMT19 input context invalid: {input_tokens} tokens / {max_positions} max"
        )
    unk_id = tokenizer.unk_token_id
    unk_count = int((input_ids == int(unk_id)).sum().item()) if unk_id is not None else 0
    eos_id = resolve_special_token_id("eos_token_id", tokenizer=tokenizer, model=model)
    pad_id = resolve_special_token_id("pad_token_id", tokenizer=tokenizer, model=model)

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
        raise RuntimeError("WMT19 returned unexpected hypothesis count")
    sequence_scores = getattr(generated, "sequences_scores", None)
    if sequence_scores is not None:
        sequence_scores = sequence_scores.detach().cpu().tolist()

    hypotheses: list[dict[str, Any]] = []
    for rank, tensor in enumerate(sequences):
        ids = [int(value) for value in tensor.tolist()]
        significant = [value for value in ids if value != pad_id]
        terminated = bool(significant and significant[-1] == eos_id)
        length_limit_hit = generation_ceiling_hit(
            len(significant), max_length=MAX_DECODING_LENGTH
        )
        target = tokenizer.decode(ids, skip_special_tokens=True).strip()
        verdict = evaluate_rescue_pair(source, target)
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
                "terminated_with_eos": terminated,
                "decoder_nonterminated": not terminated,
                "decoder_length_limit_hit": length_limit_hit,
                "mechanical_verdict": verdict,
                "strictly_eligible_with_decoder_termination": bool(
                    terminated
                    and not length_limit_hit
                    and verdict.get("strictly_eligible") is True
                ),
            }
        )

    strict_count = sum(
        1 for row in hypotheses if row["strictly_eligible_with_decoder_termination"] is True
    )
    nonterminated_count = sum(
        1 for row in hypotheses if row["decoder_nonterminated"] is True
    )
    length_limit_count = sum(
        1 for row in hypotheses if row["decoder_length_limit_hit"] is True
    )
    result = dict(case)
    result.update(
        {
            "input_token_count": input_tokens,
            "input_unknown_token_count": unk_count,
            "model_max_position_embeddings": max_positions,
            "input_truncated": False,
            "resolved_eos_token_id": eos_id,
            "resolved_pad_token_id": pad_id,
            "generation": {
                "beam_size": BEAM_SIZE,
                "num_hypotheses": NUM_HYPOTHESES,
                "max_decoding_length": MAX_DECODING_LENGTH,
                "do_sample": False,
            },
            "hypotheses": hypotheses,
            "strict_mechanical_hypothesis_count": strict_count,
            "decoder_nonterminated_hypothesis_count": nonterminated_count,
            "decoder_length_limit_hypothesis_count": length_limit_count,
            "all_hypotheses_decoder_terminated": nonterminated_count == 0,
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
        os.environ.get("ROCKETDICT_WMT19_MODEL_DIR", "work/wmt19-model")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    optin_path = root / "full-opticks-selective-rescue-optin.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    for path in (baseline_path, optin_path, database):
        if not path.is_file():
            raise RuntimeError(f"required WMT19 baseline input is missing: {path}")
    baseline_bytes = baseline_path.read_bytes()
    optin_bytes = optin_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    optin = json.loads(optin_bytes.decode("utf-8"))
    if baseline.get("schema") != BASE.BASELINE_SCHEMA or optin.get("schema") != BASE.OPTIN_SCHEMA:
        raise RuntimeError("WMT19 DOE baseline schema drift")
    if baseline.get("source_sha256") != BASE.OPTICKS_SHA256 or optin.get("source_sha256") != BASE.OPTICKS_SHA256:
        raise RuntimeError("WMT19 DOE pinned Opticks identity drift")
    if baseline.get("stage12_planner_contract") != BASE.PLANNER_CONTRACT:
        raise RuntimeError("WMT19 DOE requires planner-v8 baseline")
    if int(baseline.get("product_numeric_failure_count") or -1) != 27:
        raise RuntimeError("WMT19 DOE hard-failure baseline drift")
    if optin.get("promotion_allowed") is not False or optin.get("accepted_context_sequences") != [669]:
        raise RuntimeError("WMT19 DOE selective-rescue evidence drift")

    database_sha_before = BASE._sha(database)
    model_identity = _model_identity(model_dir)
    cases = BASE._load_cases(baseline, optin)
    if len(cases) != 9:
        raise RuntimeError(f"WMT19 focused inventory expected 9 cases, got {len(cases)}")

    import torch
    from transformers import FSMTForConditionalGeneration, FSMTTokenizer

    tokenizer = FSMTTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = FSMTForConditionalGeneration.from_pretrained(
        str(model_dir),
        local_files_only=True,
        use_safetensors=True,
    )
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    if str(model.config.model_type) != "fsmt":
        raise RuntimeError(f"unexpected WMT19 model type: {model.config.model_type!r}")

    eos_id = resolve_special_token_id("eos_token_id", tokenizer=tokenizer, model=model)
    pad_id = resolve_special_token_id("pad_token_id", tokenizer=tokenizer, model=model)
    results = [
        _translate_case(case=case, tokenizer=tokenizer, model=model, torch=torch)
        for case in cases
    ]
    database_sha_after = BASE._sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("WMT19 feasibility DOE mutated Product database")

    nonterminated_cases = [
        str(row["case_id"])
        for row in results
        if int(row.get("decoder_nonterminated_hypothesis_count") or 0) > 0
    ]
    length_limit_cases = [
        str(row["case_id"])
        for row in results
        if int(row.get("decoder_length_limit_hypothesis_count") or 0) > 0
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "independent Apache-2.0 EN-RU model control on immutable focused Opticks failures",
        "promotion_allowed": False,
        "semantic_review_required": True,
        "automatic_semantic_selector": False,
        "decoder_nontermination_is_fail_closed": True,
        "decoder_length_limit_is_fail_closed": True,
        "product_baseline_changed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": BASE.OPTICKS_SHA256,
        "source_text_sha256": str(baseline.get("source_text_sha256") or ""),
        "planner_contract": BASE.PLANNER_CONTRACT,
        "baseline_json_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "optin_json_sha256": hashlib.sha256(optin_bytes).hexdigest(),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
        "model": model_identity,
        "runtime": {
            "torch_version": str(torch.__version__),
            "torch_compute_dtype": "float32",
            "device": "cpu",
            "transformers_class": "FSMTForConditionalGeneration",
            "resolved_eos_token_id": eos_id,
            "resolved_pad_token_id": pad_id,
        },
        "case_count": len(results),
        "decoder_nonterminated_case_count": len(nonterminated_cases),
        "decoder_nonterminated_cases": nonterminated_cases,
        "decoder_length_limit_case_count": len(length_limit_cases),
        "decoder_length_limit_cases": length_limit_cases,
        "cases": results,
    }
    payload["evidence_sha256"] = BASE._canonical_sha(payload)
    output = root / "full-opticks-wmt19-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "case_count": len(results),
                "decoder_nonterminated_cases": nonterminated_cases,
                "decoder_length_limit_cases": length_limit_cases,
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
