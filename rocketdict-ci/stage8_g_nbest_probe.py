from __future__ import annotations

"""RocketDict Stage 8 / DOE G: integrity-aware n-best selection probe.

This is deliberately a narrow, reproducible probe for the F96 occurrence 16200
failure class.  It does not claim to replace the full 5k Stage 8 challenge gate.
It proves (or falsifies) one mechanism before that mechanism is integrated into
RocketDict proper:

* ask the same real OPUS model for multiple hypotheses;
* never rewrite/synthesize a hypothesis;
* select the highest-ranked model hypothesis whose numeric literal multiset is
  exactly compatible with the source for this ordinary-number case;
* retain every candidate and verdict as evidence.

The full promotion rule remains the one in rocketdict/RESEARCH_STATUS.md.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time
import zipfile

import ctranslate2
import sentencepiece as spm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_opus_gate import (  # noqa: E402
    OPUS_URL,
    download,
    locate_model,
    locate_sentencepiece,
    validate_zip_members,
)

ROOT = Path("work-stage8-g")
SRC = ROOT / "model-src"
CT2 = ROOT / "model-ct2"
EVIDENCE = ROOT / "evidence"
EXPECTED_OPUS_SHA256 = "798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677"

# Exact short F96 failure recorded in rocketdict/RESEARCH_STATUS.md.
TARGET_CASE = {
    "id": "f96-occurrence-16200",
    "source": "15 Min. that of the exterior 3 Degr.",
    "classification": "ordinary/structural numeric loss",
    "required_source_literals": ["15", "3"],
}

# These are diagnostics only.  They are fragments of the other two F96 failure
# descriptions, not substitutes for the exact original units; their result is
# therefore never used to promote G.
DIAGNOSTIC_CASES = [
    {
        "id": "diagnostic-extreme-literal-fragment",
        "source": "1000000, 1000000000000, or 1000000000000000000 times rarer.",
        "classification": "extreme literal sequence fragment; non-promotional",
    },
]

CONFIG_CELLS = [
    {"beam_size": 4, "num_hypotheses": 4},
    {"beam_size": 8, "num_hypotheses": 8},
    {"beam_size": 16, "num_hypotheses": 8},
    {"beam_size": 16, "num_hypotheses": 16},
]

# Stage 8 numeric-integrity/3.2 is richer than this extractor.  This probe uses
# only an exact integer-multiset contract because the target failure contains
# exactly the ordinary literals 15 and 3.  The distinction is recorded in the
# evidence and the full 3.2 gate remains mandatory before promotion.
_INTEGER_RE = re.compile(r"(?<![\w])\d+(?![\w])", flags=re.UNICODE)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def literal_multiset(text: str) -> Counter[str]:
    return Counter(_INTEGER_RE.findall(text))


def prepare_model() -> tuple[ctranslate2.Translator, spm.SentencePieceProcessor, spm.SentencePieceProcessor, dict]:
    for d in (SRC, CT2, EVIDENCE):
        d.mkdir(parents=True, exist_ok=True)

    opus_zip = ROOT / "opus-2020-02-11.zip"
    download(OPUS_URL, opus_zip)
    observed_sha = sha256(opus_zip)
    if observed_sha != EXPECTED_OPUS_SHA256:
        raise RuntimeError(
            f"official OPUS artifact hash mismatch: {observed_sha} != {EXPECTED_OPUS_SHA256}"
        )

    if SRC.exists():
        shutil.rmtree(SRC)
    SRC.mkdir(parents=True)
    with zipfile.ZipFile(opus_zip) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"OPUS zip CRC failure: {bad}")
        validate_zip_members(zf)
        zf.extractall(SRC)

    model_dir, decoder_config, model_files, vocab_files = locate_model(SRC)
    source_spm, target_spm = locate_sentencepiece(model_dir)

    if CT2.exists():
        shutil.rmtree(CT2)
    CT2.mkdir(parents=True)
    t0 = time.time()
    ctranslate2.converters.OpusMTConverter(str(model_dir)).convert(
        str(CT2), quantization="float32", force=True
    )
    conversion_seconds = time.time() - t0

    translator = ctranslate2.Translator(str(CT2), device="cpu", compute_type="float32")
    source_tok = spm.SentencePieceProcessor(model_file=str(source_spm))
    target_tok = spm.SentencePieceProcessor(model_file=str(target_spm))
    model_identity = {
        "official_opus_url": OPUS_URL,
        "opus_zip_sha256": observed_sha,
        "model_files": [
            {"path": str(p.relative_to(model_dir)), "sha256": sha256(p)} for p in model_files
        ],
        "vocab_files": [
            {"path": str(p.relative_to(model_dir)), "sha256": sha256(p)} for p in vocab_files
        ],
        "decoder": decoder_config,
        "compute_type": "float32",
        "ctranslate2_version": ctranslate2.__version__,
        "sentencepiece_version": getattr(spm, "__version__", None),
        "conversion_seconds": conversion_seconds,
    }
    return translator, source_tok, target_tok, model_identity


def run_cell(
    translator: ctranslate2.Translator,
    source_tok: spm.SentencePieceProcessor,
    target_tok: spm.SentencePieceProcessor,
    case: dict,
    cell: dict,
) -> dict:
    source = case["source"]
    source_tokens = source_tok.encode(source, out_type=str)
    started = time.time()
    result = translator.translate_batch(
        [source_tokens],
        beam_size=cell["beam_size"],
        num_hypotheses=cell["num_hypotheses"],
        return_scores=True,
        max_batch_size=1,
    )[0]
    elapsed = time.time() - started

    source_literals = literal_multiset(source)
    hypotheses = []
    selected_rank = None
    for rank, tokens in enumerate(result.hypotheses):
        text = target_tok.decode(tokens)
        target_literals = literal_multiset(text)
        exact_literal_multiset = target_literals == source_literals
        score = result.scores[rank] if rank < len(result.scores) else None
        candidate = {
            "rank": rank,
            "score": score,
            "text": text,
            "numeric_literals": dict(target_literals),
            "integrity_exact_integer_multiset": exact_literal_multiset,
        }
        hypotheses.append(candidate)
        if selected_rank is None and exact_literal_multiset:
            selected_rank = rank

    selected = hypotheses[selected_rank] if selected_rank is not None else None
    return {
        "case_id": case["id"],
        "source": source,
        "source_numeric_literals": dict(source_literals),
        "classification": case["classification"],
        "config": dict(cell),
        "duration_seconds": elapsed,
        "candidate_count": len(hypotheses),
        "hypotheses": hypotheses,
        "selected_rank": selected_rank,
        "selected_text": selected["text"] if selected else None,
        "selector_passed": selected is not None,
        "selection_policy": "first/highest-model-rank hypothesis with exact integer literal multiset; no target rewriting",
    }


def main() -> None:
    translator, source_tok, target_tok, model_identity = prepare_model()

    all_cases = [TARGET_CASE, *DIAGNOSTIC_CASES]
    results = []
    for case in all_cases:
        for cell in CONFIG_CELLS:
            row = run_cell(translator, source_tok, target_tok, case, cell)
            results.append(row)
            print(
                f"{row['case_id']} beam={cell['beam_size']} n={cell['num_hypotheses']} "
                f"pass={row['selector_passed']} rank={row['selected_rank']} "
                f"selected={row['selected_text']!r}",
                flush=True,
            )

    target_rows = [r for r in results if r["case_id"] == TARGET_CASE["id"]]
    successful_cells = [r for r in target_rows if r["selector_passed"]]
    probe_passed = bool(successful_cells)

    payload = {
        "schema": "rocketdict-stage8-g-nbest-probe/1",
        "scope": "mechanism probe for exact F96 occurrence 16200; not the full 5k promotion gate",
        "stage8_parent": "F96",
        "research_branch": "G-integrity-aware-nbest-selector",
        "full_numeric_contract_required_for_promotion": "rocketdict-numeric-integrity/3.2",
        "probe_numeric_contract": "exact integer literal multiset for ordinary-number target case only",
        "no_synthetic_target_repair": True,
        "target_case": TARGET_CASE,
        "diagnostic_cases": DIAGNOSTIC_CASES,
        "config_cells": CONFIG_CELLS,
        "model_identity": model_identity,
        "results": results,
        "target_successful_cells": [
            {
                "config": r["config"],
                "selected_rank": r["selected_rank"],
                "selected_text": r["selected_text"],
            }
            for r in successful_cells
        ],
        "probe_passed": probe_passed,
        "promotion_allowed": False,
        "promotion_blocker": "must integrate G into the exact F96 pipeline and rerun identical ~5k challenge under numeric-integrity/3.2",
    }

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / "stage8-g-nbest-probe.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)

    if not probe_passed:
        raise SystemExit("Stage 8 G mechanism probe failed: no integrity-valid n-best hypothesis for F96 occurrence 16200")


if __name__ == "__main__":
    main()
