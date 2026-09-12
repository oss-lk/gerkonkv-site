from __future__ import annotations

"""Read-only M2M100 rank-0 shadow over the exact 20 run20 numeric residuals.

This is a third-model feasibility probe, not Product policy.  It keeps the
persisted run20 SQLite read-only, translates exactly the rows that still fail
the maintained numeric/symbol hard gate, and records one deterministic raw
beam candidate per source row from the pinned M2M100 418M checkpoint.

No source/target rewriting, placeholders, literal injection, n-best selection,
or evaluator weakening is permitted.  Mechanical pass is only an upper bound;
manual semantic review is mandatory before any narrower wrapper is considered.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-m2m100-numeric-shadow/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_FAILURE_SEQUENCES = [
    325, 641, 642, 644, 646, 750, 751, 752, 1570, 1580,
    1762, 1791, 2293, 2349, 2360, 2378, 2743, 2745, 2893, 3001,
]
MODEL_REPO = "facebook/m2m100_418M"
MODEL_REVISION = "55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636"
MODEL_LICENSE = "MIT"
BEAM_SIZE = 6
NUM_RETURN_SEQUENCES = 1
MAX_NEW_TOKENS = 384
MIN_SOURCE_ALPHA_RATIO = 0.55
MAX_SOURCE_ALPHA_RATIO = 1.75


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


def _alpha(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _candidate(source: str, target: str, *, terminated: bool, ceiling_hit: bool) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    admissible = bool(
        target.strip()
        and terminated
        and not ceiling_hit
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    )
    return {
        "mechanically_admissible": admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN20_M2M100_NUMERIC_SHADOW_ROOT",
            "work/run20-m2m100-numeric-shadow",
        )
    ).resolve()
    model_dir = Path(os.environ["ROCKETDICT_M2M100_MODEL_DIR"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("M2M100 shadow requires exact persisted run20 database")

    required_model_files = [
        "config.json",
        "pytorch_model.bin",
        "sentencepiece.bpe.model",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "vocab.json",
    ]
    missing = [name for name in required_model_files if not (model_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"M2M100 snapshot is incomplete: {missing!r}")
    model_files = {
        name: {
            "sha256": _sha(model_dir / name),
            "bytes": (model_dir / name).stat().st_size,
        }
        for name in required_model_files
    }

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        output = dict(run.get("output") or {})
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(output["document_version_id"]))

    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run20 source coverage is not byte-exact")

    failures: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        numeric = dict(verdict.get("numeric_symbol") or {})
        if numeric.get("passed") is True:
            continue
        failures.append(row)
    failure_sequences = [int(row["sequence_number"]) for row in failures]
    if failure_sequences != EXPECTED_FAILURE_SEQUENCES:
        raise RuntimeError(f"run20 numeric residual identity drift: {failure_sequences!r}")

    import torch
    from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

    tokenizer = M2M100Tokenizer.from_pretrained(
        str(model_dir),
        local_files_only=True,
        src_lang="en",
        tgt_lang="ru",
    )
    model = M2M100ForConditionalGeneration.from_pretrained(
        str(model_dir),
        local_files_only=True,
        use_safetensors=False,
    )
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    if str(model.config.model_type) != "m2m_100":
        raise RuntimeError(f"unexpected M2M100 model type: {model.config.model_type!r}")
    max_positions = int(getattr(model.config, "max_position_embeddings", 0) or 0)
    if max_positions <= 0:
        raise RuntimeError("M2M100 does not publish max_position_embeddings")
    forced_bos = int(tokenizer.get_lang_id("ru"))
    eos_id = int(tokenizer.eos_token_id)
    pad_id = int(tokenizer.pad_token_id)
    unk_id = tokenizer.unk_token_id

    records: list[dict[str, Any]] = []
    for row in failures:
        source = str(row.get("source_text") or "")
        base_target = str(row.get("target_text") or "")
        encoded = tokenizer(source, return_tensors="pt", add_special_tokens=True, truncation=False)
        input_ids = encoded["input_ids"]
        input_count = int(input_ids.shape[1])
        if input_count > max_positions:
            raise RuntimeError(
                f"M2M100 input exceeds context at sequence {row['sequence_number']}: "
                f"{input_count} > {max_positions}"
            )
        unknown_count = int((input_ids == int(unk_id)).sum().item()) if unk_id is not None else 0
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                forced_bos_token_id=forced_bos,
                do_sample=False,
                num_beams=BEAM_SIZE,
                num_return_sequences=NUM_RETURN_SEQUENCES,
                max_new_tokens=MAX_NEW_TOKENS,
                return_dict_in_generate=True,
                output_scores=True,
                renormalize_logits=True,
            )
        sequence = generated.sequences.detach().cpu()[0]
        ids = [int(value) for value in sequence.tolist()]
        significant = [value for value in ids if value != pad_id]
        terminated = bool(significant and significant[-1] == eos_id)
        ceiling_hit = len(significant) >= MAX_NEW_TOKENS
        target = tokenizer.decode(ids, skip_special_tokens=True).strip()
        scores = getattr(generated, "sequences_scores", None)
        score = float(scores.detach().cpu()[0].item()) if scores is not None else None
        candidate = _candidate(source, target, terminated=terminated, ceiling_hit=ceiling_hit)
        base_verdict = evaluate_rescue_pair(source, base_target)
        records.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "base_target_text": base_target,
                "base_verdict": base_verdict,
                "candidate_target_text": target,
                "candidate_score": score,
                "input_token_count": input_count,
                "input_unknown_token_count": unknown_count,
                "output_token_count": len(significant),
                "terminated_with_eos": terminated,
                "generation_ceiling_hit": ceiling_hit,
                **candidate,
            }
        )

    mechanically_admissible = [
        int(row["sequence_number"])
        for row in records
        if row["mechanically_admissible"] is True
    ]
    numeric_pass = [
        int(row["sequence_number"])
        for row in records
        if ((row["mechanical_verdict"].get("numeric_symbol") or {}).get("passed") is True)
    ]
    hard_pass = [
        int(row["sequence_number"])
        for row in records
        if row["mechanical_verdict"].get("product_hard_passed") is True
    ]

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only M2M100 rank0 shadow over exact run20 numeric residuals",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "failure_sequences": failure_sequences,
        "failure_count": len(failure_sequences),
        "model": {
            "repository": MODEL_REPO,
            "revision": MODEL_REVISION,
            "license": MODEL_LICENSE,
            "model_type": str(model.config.model_type),
            "max_position_embeddings": max_positions,
            "forced_target_language": "ru",
            "forced_bos_token_id": forced_bos,
            "files": model_files,
        },
        "generation": {
            "beam_size": BEAM_SIZE,
            "num_return_sequences": NUM_RETURN_SEQUENCES,
            "max_new_tokens": MAX_NEW_TOKENS,
            "do_sample": False,
        },
        "records": records,
        "numeric_pass_sequences": numeric_pass,
        "product_hard_pass_sequences": hard_pass,
        "mechanically_admissible_sequences": mechanically_admissible,
        "numeric_pass_count": len(numeric_pass),
        "product_hard_pass_count": len(hard_pass),
        "mechanically_admissible_count": len(mechanically_admissible),
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
    }
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("read-only M2M100 shadow mutated run20 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "full-opticks-run20-m2m100-numeric-shadow.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "failure_count": len(failure_sequences),
        "numeric_pass_count": len(numeric_pass),
        "product_hard_pass_count": len(hard_pass),
        "mechanically_admissible_count": len(mechanically_admissible),
        "numeric_pass_sequences": numeric_pass,
        "product_hard_pass_sequences": hard_pass,
        "mechanically_admissible_sequences": mechanically_admissible,
        "model_revision": MODEL_REVISION,
        "model_weight_sha256": model_files["pytorch_model.bin"]["sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
