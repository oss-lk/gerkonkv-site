from __future__ import annotations

"""RocketDict Stage 8 / O-v1: paired semantic-regression proxy.

This is deliberately NOT a semantic-quality oracle and NOT a promotion gate.
It exists because v8 can satisfy every objective structural/numeric/language
residue contract while still producing suspicious terminology (for example a
bad rendering of "Refraction").

Method
------
1. Reproduce the exact frozen v8 5044-word reconstruction in-process.
2. Select only units where v8 changed baseline output.
3. Download the official OPUS RU->EN model from the matching 2020-02-11 line,
   convert it to CTranslate2 float32, and back-translate baseline and candidate.
4. Compare each back-translation to the original English source using paired:
   - chrF++ (SacreBLEU sentence chrF, word_order=2),
   - token multiset F1,
   - character trigram Dice.
5. Persist deltas and ranked suspicious units for manual review.

The first run is diagnostic: no semantic threshold is allowed to fail the job.
After observing the paired distribution, any future threshold must be frozen in
a new contract/version and tested without changing the 5044-word selection.
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
import sacrebleu
import sentencepiece as spm

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
from real_opus_gate import (  # noqa: E402
    download,
    locate_model,
    locate_sentencepiece,
    validate_zip_members,
)

ROOT = Path("work-stage8-semantic-proxy")
REVERSE_SRC = ROOT / "ru-en-src"
REVERSE_CT2 = ROOT / "ru-en-ct2"
EVIDENCE = ROOT / "evidence"
RU_EN_URL = "https://object.pouta.csc.fi/OPUS-MT-models/ru-en/opus-2020-02-11.zip"
# First O-v1 run records the observed official artifact hash. O-v2 must pin it.
EXPECTED_RU_EN_SHA256: str | None = None

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", flags=re.UNICODE)
SPACE_RE = re.compile(r"\s+")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_for_similarity(text: str) -> str:
    # Keep lexical content and numbers; normalize Gutenberg markup and spacing.
    text = text.replace("_", " ")
    text = re.sub(r"\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]*)\]", r" \1 ", text, flags=re.I)
    text = re.sub(r"\[(?:Illustration|Иллюстрация)\s*:\s*([^\]]*)\]", r" \1 ", text, flags=re.I)
    text = re.sub(r"[\[\](){}]", " ", text)
    return SPACE_RE.sub(" ", text).strip()


def token_counter(text: str) -> Counter[str]:
    return Counter(t.casefold() for t in TOKEN_RE.findall(normalize_for_similarity(text)))


def multiset_f1(reference: str, hypothesis: str) -> float:
    r = token_counter(reference)
    h = token_counter(hypothesis)
    if not r and not h:
        return 1.0
    overlap = sum((r & h).values())
    precision = overlap / sum(h.values()) if h else 0.0
    recall = overlap / sum(r.values()) if r else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def char_ngrams(text: str, n: int = 3) -> Counter[str]:
    s = normalize_for_similarity(text).casefold()
    s = re.sub(r"\s+", " ", s)
    if len(s) < n:
        return Counter([s]) if s else Counter()
    return Counter(s[i:i+n] for i in range(len(s) - n + 1))


def multiset_dice(a: Counter[str], b: Counter[str]) -> float:
    if not a and not b:
        return 1.0
    overlap = sum((a & b).values())
    denom = sum(a.values()) + sum(b.values())
    return (2 * overlap / denom) if denom else 0.0


def trigram_dice(reference: str, hypothesis: str) -> float:
    return multiset_dice(char_ngrams(reference, 3), char_ngrams(hypothesis, 3))


def chrfpp(reference: str, hypothesis: str) -> float:
    return float(
        sacrebleu.sentence_chrf(
            normalize_for_similarity(hypothesis),
            [normalize_for_similarity(reference)],
            word_order=2,
        ).score
    )


def prepare_reverse_model():
    ROOT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "opus-ru-en-2020-02-11.zip"
    download(RU_EN_URL, archive)
    observed = sha256(archive)
    if EXPECTED_RU_EN_SHA256 is not None and observed != EXPECTED_RU_EN_SHA256:
        raise RuntimeError(
            f"RU-EN official artifact hash mismatch: {observed} != {EXPECTED_RU_EN_SHA256}"
        )

    if REVERSE_SRC.exists():
        shutil.rmtree(REVERSE_SRC)
    REVERSE_SRC.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"RU-EN zip CRC failure: {bad}")
        validate_zip_members(zf)
        zf.extractall(REVERSE_SRC)

    model_dir, decoder_config, model_files, vocab_files = locate_model(REVERSE_SRC)
    source_spm, target_spm = locate_sentencepiece(model_dir)

    if REVERSE_CT2.exists():
        shutil.rmtree(REVERSE_CT2)
    REVERSE_CT2.mkdir(parents=True)
    t0 = time.time()
    ctranslate2.converters.OpusMTConverter(str(model_dir)).convert(
        str(REVERSE_CT2), quantization="float32", force=True
    )
    conversion_seconds = time.time() - t0

    translator = ctranslate2.Translator(str(REVERSE_CT2), device="cpu", compute_type="float32")
    source_tok = spm.SentencePieceProcessor(model_file=str(source_spm))
    target_tok = spm.SentencePieceProcessor(model_file=str(target_spm))
    identity = {
        "official_opus_url": RU_EN_URL,
        "opus_zip_sha256": observed,
        "hash_pinned_in_this_run": EXPECTED_RU_EN_SHA256 is not None,
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
        "sacrebleu_version": sacrebleu.__version__,
        "conversion_seconds": conversion_seconds,
    }
    return translator, source_tok, target_tok, identity


def reverse_batch(translator, source_tok, target_tok, texts: list[str]) -> list[str]:
    tokenized = [source_tok.encode(t, out_type=str) for t in texts]
    results = translator.translate_batch(tokenized, beam_size=4, max_batch_size=8)
    return [target_tok.decode(x.hypotheses[0]).strip() for x in results]


def score_pair(source: str, baseline_back: str, candidate_back: str) -> dict:
    b = {
        "chrfpp": chrfpp(source, baseline_back),
        "token_f1": multiset_f1(source, baseline_back),
        "char3_dice": trigram_dice(source, baseline_back),
    }
    c = {
        "chrfpp": chrfpp(source, candidate_back),
        "token_f1": multiset_f1(source, candidate_back),
        "char3_dice": trigram_dice(source, candidate_back),
    }
    # Composite is descriptive only. Components are normalized to 0..1.
    b_comp = 0.50 * (b["chrfpp"] / 100.0) + 0.25 * b["token_f1"] + 0.25 * b["char3_dice"]
    c_comp = 0.50 * (c["chrfpp"] / 100.0) + 0.25 * c["token_f1"] + 0.25 * c["char3_dice"]
    return {
        "baseline": {**b, "composite": b_comp},
        "candidate": {**c, "composite": c_comp},
        "delta_candidate_minus_baseline": {
            "chrfpp": c["chrfpp"] - b["chrfpp"],
            "token_f1": c["token_f1"] - b["token_f1"],
            "char3_dice": c["char3_dice"] - b["char3_dice"],
            "composite": c_comp - b_comp,
        },
    }


def main() -> None:
    # Reproduce the clean v8 output in this independent workflow process.
    v8.main()
    units_path = v5.EVIDENCE / "units.jsonl"
    rows = [
        json.loads(line)
        for line in units_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    changed = [r for r in rows if r["baseline"] != r["candidate"]]
    if len(changed) != 10:
        raise RuntimeError(f"expected 10 clean-v8 changed units, got {len(changed)}")

    translator, source_tok, target_tok, reverse_identity = prepare_reverse_model()
    baseline_back = reverse_batch(translator, source_tok, target_tok, [r["baseline"] for r in changed])
    candidate_back = reverse_batch(translator, source_tok, target_tok, [r["candidate"] for r in changed])

    evidence_rows = []
    for r, bb, cb in zip(changed, baseline_back, candidate_back):
        scores = score_pair(r["source"], bb, cb)
        evidence_rows.append({
            "occurrence": r["occurrence"],
            "category": r["category"],
            "mechanism": r["mechanism"],
            "source": r["source"],
            "baseline_ru": r["baseline"],
            "candidate_ru": r["candidate"],
            "baseline_back_en": bb,
            "candidate_back_en": cb,
            "scores": scores,
        })

    ranked = sorted(
        evidence_rows,
        key=lambda x: x["scores"]["delta_candidate_minus_baseline"]["composite"],
    )
    deltas = [x["scores"]["delta_candidate_minus_baseline"]["composite"] for x in evidence_rows]
    chrf_deltas = [x["scores"]["delta_candidate_minus_baseline"]["chrfpp"] for x in evidence_rows]
    payload = {
        "schema": "rocketdict-stage8-semantic-regression-proxy/1",
        "status": "DIAGNOSTIC_ONLY_NO_THRESHOLD",
        "parent_candidate": "clean v8 / run 33088908923",
        "selection_sha256": "ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe",
        "changed_units": len(evidence_rows),
        "reverse_model": reverse_identity,
        "method": {
            "back_translation": "official OPUS RU->EN 2020-02-11, CTranslate2 float32, beam4 top1",
            "metrics": ["sentence chrF++", "casefold token multiset F1", "character trigram multiset Dice"],
            "composite": "0.50*chrF++ + 0.25*token_F1 + 0.25*char3_Dice after 0..1 normalization",
            "purpose": "paired regression proxy only",
            "semantic_correctness_claimed": False,
            "threshold_frozen": False,
        },
        "aggregate": {
            "mean_composite_delta": sum(deltas) / len(deltas),
            "min_composite_delta": min(deltas),
            "max_composite_delta": max(deltas),
            "mean_chrfpp_delta": sum(chrf_deltas) / len(chrf_deltas),
            "candidate_better_composite_units": sum(d > 0 for d in deltas),
            "candidate_worse_composite_units": sum(d < 0 for d in deltas),
            "ties": sum(d == 0 for d in deltas),
        },
        "ranked_worst_first": [
            {
                "occurrence": x["occurrence"],
                "mechanism": x["mechanism"],
                "delta": x["scores"]["delta_candidate_minus_baseline"],
            }
            for x in ranked
        ],
        "units": evidence_rows,
        "promotion_allowed": False,
        "next_action": "Inspect the paired distribution and worst units manually. Freeze any regression threshold only in a new proxy version; do not tune O-v1 after seeing its results.",
    }

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "stage8-semantic-regression-proxy.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
