from __future__ import annotations

"""Research-only CTranslate2 parity audit for pinned TC-big over run-9 failures.

The independent model is first converted from the exact pinned Hugging Face
Marian snapshot to CTranslate2 float32. This v2 audit deliberately uses the
same Hugging Face MarianTokenizer semantics as the reference Transformers run
while keeping the actual inference runtime torch-free. This matters for
multilingual Marian models because language codes such as ``>>rus<<`` are
special vocabulary tokens and must not be passed through raw SentencePiece.

The script never selects Product output. It measures tokenizer parity, raw
hypothesis overlap, mechanical behavior, and backend/runtime feasibility only.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair


SCHEMA = "rocketdict-full-opticks-tc-big-ct2-parity-run9/2"
INPUT_SCHEMA = "rocketdict-full-opticks-alternative-mt-current-hard-failures-run9/1"
EXPECTED_INPUT_FILE_SHA256 = "5c87500453f9443f5aff42d4bfea1bc055b48fa3a2ec747e13ec99581fe16f69"
EXPECTED_INPUT_EVIDENCE_SHA256 = "1e3ce22828f72b2409e1a4093646ef0a74a4dcf9b224b3f59d286011acbebca7"
EXPECTED_DB_SHA256 = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
TARGET_PREFIX = ">>rus<< "
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 512


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _tree_identity(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
        )
    if not rows:
        raise RuntimeError("converted TC-big CTranslate2 tree is empty")
    return {
        "file_count": len(rows),
        "bytes": sum(int(row["bytes"]) for row in rows),
        "files": rows,
        "tree_sha256": _canonical_sha(rows),
    }


def _inventory(cases: list[dict[str, Any]], selected: dict[int, str]) -> dict[str, int]:
    numeric = punctuation = length = 0
    unique = 0
    for case in cases:
        sequence = int(case["baseline_planned_sequence"])
        source = str(case["source_text"])
        target = selected.get(sequence, str(case["baseline_target_text"]))
        verdict = evaluate_rescue_pair(source, target)
        failed_numeric = (verdict.get("numeric_symbol") or {}).get("passed") is not True
        failed_punctuation = verdict.get("punctuation_passed") is not True
        failed_length = verdict.get("length_passed") is not True
        numeric += int(failed_numeric)
        punctuation += int(failed_punctuation)
        length += int(failed_length)
        unique += int(failed_numeric or failed_punctuation or failed_length)
    return {"numeric_symbol": numeric, "punctuation": punctuation, "length": length, "unique": unique}


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_TC_BIG_CT2_RUN9_ROOT", "work/tc-big-ct2-run9")).resolve()
    evidence_path = root / "full-opticks-alternative-mt-current-hard-failures-run9.json"
    database = root / "rocketdict.sqlite"
    hf_model_dir = Path(os.environ["ROCKETDICT_ALT_MT_MODEL_DIR"]).resolve()
    ct2_model_dir = Path(os.environ["ROCKETDICT_ALT_MT_CT2_DIR"]).resolve()
    for path in (
        evidence_path,
        database,
        hf_model_dir / "source.spm",
        hf_model_dir / "target.spm",
        hf_model_dir / "vocab.json",
        ct2_model_dir / "model.bin",
    ):
        if not path.exists():
            raise RuntimeError(f"TC-big CTranslate2 parity input missing: {path}")

    evidence_bytes = evidence_path.read_bytes()
    if hashlib.sha256(evidence_bytes).hexdigest() != EXPECTED_INPUT_FILE_SHA256:
        raise RuntimeError("TC-big Transformers evidence file identity drift")
    evidence = json.loads(evidence_bytes.decode("utf-8"))
    if evidence.get("schema") != INPUT_SCHEMA or evidence.get("evidence_sha256") != EXPECTED_INPUT_EVIDENCE_SHA256:
        raise RuntimeError("TC-big Transformers evidence identity drift")
    if _sha(database) != EXPECTED_DB_SHA256:
        raise RuntimeError("run9 database identity drift")

    required = {row["path"]: row["sha256"] for row in evidence["model"]["required_files"]}
    for relative in ("source.spm", "target.spm", "vocab.json"):
        if _sha(hf_model_dir / relative) != required.get(relative):
            raise RuntimeError(f"pinned TC-big tokenizer identity drift: {relative}")

    if importlib.util.find_spec("torch") is not None:
        raise RuntimeError("parity inference runtime unexpectedly contains torch")

    import ctranslate2
    import transformers
    from transformers import MarianTokenizer

    tokenizer = MarianTokenizer.from_pretrained(str(hf_model_dir), local_files_only=True)
    translator = ctranslate2.Translator(str(ct2_model_dir), device="cpu", compute_type="float32")

    sources = [str(case["source_text"]) for case in evidence["cases"]]
    tokenized: list[list[str]] = []
    input_token_parity_count = 0
    input_token_rows: list[dict[str, Any]] = []
    for case, source in zip(evidence["cases"], sources, strict=True):
        input_ids = tokenizer.encode(TARGET_PREFIX + source, add_special_tokens=True)
        tokens = tokenizer.convert_ids_to_tokens(input_ids)
        expected_count = int(case.get("input_token_count") or -1)
        if len(input_ids) == expected_count:
            input_token_parity_count += 1
        input_token_rows.append(
            {
                "sequence_number": int(case["baseline_planned_sequence"]),
                "transformers_input_token_count": expected_count,
                "ct2_hf_tokenizer_input_token_count": len(input_ids),
                "count_matches": len(input_ids) == expected_count,
                "first_token": tokens[0] if tokens else None,
                "last_token": tokens[-1] if tokens else None,
            }
        )
        tokenized.append(tokens)
    if input_token_parity_count != len(sources):
        raise RuntimeError(
            f"MarianTokenizer input parity drift: {input_token_parity_count}/{len(sources)}"
        )

    translated = translator.translate_batch(
        tokenized,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        return_scores=True,
        max_decoding_length=MAX_DECODING_LENGTH,
        length_penalty=1.0,
    )
    if len(translated) != len(sources):
        raise RuntimeError("TC-big CTranslate2 result cardinality drift")

    cases_out: list[dict[str, Any]] = []
    selected: dict[int, str] = {}
    exact_rank0_matches = 0
    cases_with_any_exact_hypothesis_overlap = 0
    mechanically_admissible_cases = 0
    mechanically_admissible_hypotheses = 0

    for case, result in zip(evidence["cases"], translated, strict=True):
        if len(result.hypotheses) != NUM_HYPOTHESES:
            raise RuntimeError("TC-big CTranslate2 n-best cardinality drift")
        hf_targets = [str(row["target_text"]) for row in case["hypotheses"]]
        hypotheses: list[dict[str, Any]] = []
        first_admissible: int | None = None
        overlap = False
        for rank, tokens in enumerate(result.hypotheses):
            target_ids = tokenizer.convert_tokens_to_ids(list(tokens))
            target = tokenizer.decode(target_ids, skip_special_tokens=True).strip()
            verdict = evaluate_rescue_pair(str(case["source_text"]), target)
            emphasis = compare_emphasis_markup_preservation(str(case["source_text"]), target)
            admissible = verdict.get("strictly_eligible") is True and emphasis.get("passed") is True
            mechanically_admissible_hypotheses += int(admissible)
            if first_admissible is None and admissible:
                first_admissible = rank
            overlap = overlap or target in hf_targets
            hypotheses.append(
                {
                    "rank": rank,
                    "score": float(result.scores[rank]) if rank < len(result.scores) else None,
                    "target_text": target,
                    "mechanical_verdict": verdict,
                    "emphasis_markup": emphasis,
                    "mechanically_admissible": admissible,
                    "exact_transformers_hypothesis_match": target in hf_targets,
                    "matching_transformers_ranks": [i for i, value in enumerate(hf_targets) if value == target],
                }
            )
        if hypotheses[0]["target_text"] == hf_targets[0]:
            exact_rank0_matches += 1
        if overlap:
            cases_with_any_exact_hypothesis_overlap += 1
        sequence = int(case["baseline_planned_sequence"])
        if first_admissible is not None:
            mechanically_admissible_cases += 1
            selected[sequence] = str(hypotheses[first_admissible]["target_text"])
        cases_out.append(
            {
                "sequence_number": sequence,
                "source_start": int(case["source_start"]),
                "source_end": int(case["source_end"]),
                "source_text": str(case["source_text"]),
                "transformers_first_mechanically_admissible_rank": case.get("first_mechanically_admissible_rank"),
                "ct2_first_mechanically_admissible_rank": first_admissible,
                "hypotheses": hypotheses,
            }
        )

    upper = _inventory(list(evidence["cases"]), selected)
    tree = _tree_identity(ct2_model_dir)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only parity and torch-free-runtime feasibility for pinned TC-big converted to CTranslate2 float32 using exact MarianTokenizer semantics",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "input_evidence_file_sha256": EXPECTED_INPUT_FILE_SHA256,
        "input_evidence_sha256": EXPECTED_INPUT_EVIDENCE_SHA256,
        "run9_database_sha256": EXPECTED_DB_SHA256,
        "source_model": {
            "repository": evidence["model"]["repository"],
            "revision": evidence["model"]["requested_revision"],
            "model_safetensors_sha256": evidence["model"]["model_safetensors_sha256"],
        },
        "converted_model": {
            "compute_type": "float32",
            **tree,
        },
        "runtime": {
            "ctranslate2_version": str(ctranslate2.__version__),
            "transformers_version": str(transformers.__version__),
            "tokenizer_class": tokenizer.__class__.__name__,
            "tokenizer_semantics": "MarianTokenizer.encode+convert_ids_to_tokens / convert_tokens_to_ids+decode",
            "device": "cpu",
            "torch_available": False,
            "torch_imported_by_script": False,
        },
        "case_count": len(cases_out),
        "input_token_parity_count": input_token_parity_count,
        "input_token_parity_rows": input_token_rows,
        "exact_rank0_match_count": exact_rank0_matches,
        "case_count_with_any_exact_hypothesis_overlap": cases_with_any_exact_hypothesis_overlap,
        "mechanically_admissible_case_count": mechanically_admissible_cases,
        "mechanically_admissible_hypothesis_count": mechanically_admissible_hypotheses,
        "mechanical_upper_bound_hard_gate_counts": upper,
        "cases": cases_out,
        "database_mutated": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-tc-big-ct2-parity-run9.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "input_token_parity_count": input_token_parity_count,
                "exact_rank0_match_count": exact_rank0_matches,
                "case_count_with_any_exact_hypothesis_overlap": cases_with_any_exact_hypothesis_overlap,
                "mechanically_admissible_case_count": mechanically_admissible_cases,
                "mechanically_admissible_hypothesis_count": mechanically_admissible_hypotheses,
                "mechanical_upper_bound_hard_gate_counts": upper,
                "converted_model_tree_sha256": tree["tree_sha256"],
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
