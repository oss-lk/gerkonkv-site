from __future__ import annotations

"""Read-only M2M100 DOE for source-verifiable multiplication restatements.

The source-defined predicate is arithmetic rather than corpus-position based:
``A x B (that is, above C)`` with decimal integers for which ``A * B == C``.
A row is a rescue trigger only when the current run20 target already fails the
maintained numeric/symbol Product hard gate.  The pinned M2M100 checkpoint emits
one raw beam-6 rank-0 candidate; no n-best selection or text repair is allowed.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-m2m100-product-restatement-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
MODEL_REVISION = "55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636"
MODEL_WEIGHT_SHA256 = "d907ea45e4e4b9db163382a6674f6218b3c59566fe06d77f4055c208b4e87ed1"
EXPECTED_MULTIPLICATION_ROW_COUNT = 2
EXPECTED_VERIFIED_RESTATEMENT_SEQUENCES = [2745]
EXPECTED_TRIGGER_SEQUENCES = [2745]
BEAM_SIZE = 6
MAX_NEW_TOKENS = 384
MIN_SOURCE_ALPHA_RATIO = 0.60
MAX_SOURCE_ALPHA_RATIO = 1.50
_MULTIPLICATION_RE = re.compile(r"\b\d[\d,]*\s*[x×]\s*\d[\d,]*\b", re.IGNORECASE)
_RESTATEMENT_RE = re.compile(
    r"\b(?P<a>\d[\d,]*)\s*[x×]\s*(?P<b>\d[\d,]*)\s*"
    r"\(\s*that\s+is\s*,\s*above\s+(?P<c>\d[\d,]*)\s*\)",
    re.IGNORECASE,
)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _integer(raw: str) -> int:
    return int(raw.replace(",", ""))


def _source_restatement(source: str) -> dict[str, Any] | None:
    matches = list(_RESTATEMENT_RE.finditer(source))
    if len(matches) != 1:
        return None
    match = matches[0]
    a, b, c = (_integer(match.group(name)) for name in ("a", "b", "c"))
    return {
        "a": a,
        "b": b,
        "c": c,
        "product": a * b,
        "arithmetic_verified": a * b == c,
        "source_text": match.group(0),
    }


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN20_M2M100_PRODUCT_DOE_ROOT", "work/run20-m2m100-product-restatement-doe")).resolve()
    model_dir = Path(os.environ["ROCKETDICT_M2M100_MODEL_DIR"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("M2M100 restatement DOE requires exact run20 database")
    if _sha(model_dir / "pytorch_model.bin") != MODEL_WEIGHT_SHA256:
        raise RuntimeError("M2M100 model-weight identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        output = dict(run.get("output") or {})
        rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda r: int(r["sequence_number"]))
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(r.get("source_text") or "") for r in rows) != content:
        raise RuntimeError("run20 source coverage drift")

    multiplication_rows = [r for r in rows if _MULTIPLICATION_RE.search(str(r.get("source_text") or ""))]
    if len(multiplication_rows) != EXPECTED_MULTIPLICATION_ROW_COUNT:
        raise RuntimeError(f"multiplication census drift: {len(multiplication_rows)}")
    verified: list[dict[str, Any]] = []
    for row in multiplication_rows:
        source = str(row.get("source_text") or "")
        restatement = _source_restatement(source)
        if restatement is None or restatement["arithmetic_verified"] is not True:
            continue
        current = evaluate_rescue_pair(source, str(row.get("target_text") or ""))
        verified.append({"row": row, "restatement": restatement, "current_verdict": current})
    verified_sequences = [int(item["row"]["sequence_number"]) for item in verified]
    if verified_sequences != EXPECTED_VERIFIED_RESTATEMENT_SEQUENCES:
        raise RuntimeError(f"verified restatement census drift: {verified_sequences!r}")
    triggers = [int(item["row"]["sequence_number"]) for item in verified if item["current_verdict"].get("product_hard_passed") is not True]
    if triggers != EXPECTED_TRIGGER_SEQUENCES:
        raise RuntimeError(f"restatement trigger census drift: {triggers!r}")

    import torch
    from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
    tokenizer = M2M100Tokenizer.from_pretrained(str(model_dir), local_files_only=True, src_lang="en", tgt_lang="ru")
    model = M2M100ForConditionalGeneration.from_pretrained(str(model_dir), local_files_only=True, use_safetensors=False)
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    forced_bos = int(tokenizer.get_lang_id("ru"))
    eos_id = int(tokenizer.eos_token_id)
    pad_id = int(tokenizer.pad_token_id)

    records: list[dict[str, Any]] = []
    for item in verified:
        row = item["row"]
        source = str(row.get("source_text") or "")
        encoded = tokenizer(source, return_tensors="pt", add_special_tokens=True, truncation=False)
        with torch.inference_mode():
            generated = model.generate(
                **encoded, forced_bos_token_id=forced_bos, do_sample=False,
                num_beams=BEAM_SIZE, num_return_sequences=1,
                max_new_tokens=MAX_NEW_TOKENS, return_dict_in_generate=True,
                output_scores=True, renormalize_logits=True,
            )
        ids = [int(v) for v in generated.sequences.detach().cpu()[0].tolist()]
        significant = [v for v in ids if v != pad_id]
        terminated = bool(significant and significant[-1] == eos_id)
        target = tokenizer.decode(ids, skip_special_tokens=True).strip()
        verdict = evaluate_rescue_pair(source, target)
        emphasis = compare_emphasis_markup_preservation(source, target)
        ratio = _alpha(target) / _alpha(source) if _alpha(source) else 1.0
        accepted = bool(
            terminated
            and verdict.get("strictly_eligible") is True
            and emphasis.get("passed") is True
            and MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
        )
        records.append({
            "sequence_number": int(row["sequence_number"]),
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": source,
            "current_target_text": str(row.get("target_text") or ""),
            "source_restatement": item["restatement"],
            "current_verdict": item["current_verdict"],
            "candidate_target_text": target,
            "candidate_verdict": verdict,
            "emphasis_markup": emphasis,
            "source_alpha_ratio": ratio,
            "terminated_with_eos": terminated,
            "mechanically_admissible": accepted,
        })

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only M2M100 rank0 DOE for source-verifiable integer multiplication restatements",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "multiplication_row_count": len(multiplication_rows),
        "multiplication_sequences": [int(r["sequence_number"]) for r in multiplication_rows],
        "verified_restatement_sequences": verified_sequences,
        "trigger_sequences": triggers,
        "model_revision": MODEL_REVISION,
        "model_weight_sha256": MODEL_WEIGHT_SHA256,
        "generation": {"beam_size": BEAM_SIZE, "num_return_sequences": 1, "max_new_tokens": MAX_NEW_TOKENS},
        "records": records,
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
        raise RuntimeError("M2M100 restatement DOE mutated run20 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "full-opticks-run20-m2m100-product-restatement-doe.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "multiplication_sequences": evidence["multiplication_sequences"],
        "verified_restatement_sequences": verified_sequences,
        "trigger_sequences": triggers,
        "mechanically_admissible_sequences": [r["sequence_number"] for r in records if r["mechanically_admissible"]],
        "model_weight_sha256": MODEL_WEIGHT_SHA256,
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
