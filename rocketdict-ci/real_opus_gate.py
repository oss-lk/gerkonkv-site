from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
import urllib.request
import zipfile

import ctranslate2
import sentencepiece as spm

OPUS_URL = "https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip"
OPTICKS_URL = "https://www.gutenberg.org/cache/epub/33504/pg33504.txt"
ROOT = Path("work")
SRC = ROOT / "model-src"
CT2 = ROOT / "model-ct2"
CORPUS = ROOT / "corpus" / "opticks.txt"
EVIDENCE = ROOT / "evidence"
OUTPUT = ROOT / "output"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, attempts: int = 5) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RocketDict-GitHub-Gate/1"})
            with urllib.request.urlopen(req, timeout=60) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
            if dest.stat().st_size == 0:
                raise RuntimeError("downloaded file is empty")
            return
        except Exception as exc:
            last = exc
            if dest.exists():
                dest.unlink()
            print(f"download attempt {attempt}/{attempts} failed for {url}: {exc}", flush=True)
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"download failed after {attempts} attempts: {url}: {last}")


def locate_model(root: Path) -> Path:
    candidates = [root] + [p for p in root.rglob("*") if p.is_dir()]
    for p in candidates:
        if (p / "model.npz").is_file() and (p / "decoder.yml").is_file():
            return p
    raise RuntimeError("original OPUS Marian model.npz/decoder.yml not found")


def locate_sentencepiece(root: Path) -> tuple[Path, Path]:
    files = sorted(root.rglob("*.spm"))
    if len(files) < 2:
        raise RuntimeError(f"expected >=2 SentencePiece model files, found {files}")
    source = next((p for p in files if "source" in p.name.lower()), files[0])
    target = next((p for p in files if "target" in p.name.lower() and p != source), None)
    if target is None:
        target = next(p for p in files if p != source)
    return source, target


def main() -> None:
    for d in (SRC, CT2, CORPUS.parent, EVIDENCE, OUTPUT):
        d.mkdir(parents=True, exist_ok=True)

    opus_zip = ROOT / "opus-2020-02-11.zip"
    print("Downloading official OPUS EN->RU artifact...", flush=True)
    download(OPUS_URL, opus_zip)
    print("Downloading Project Gutenberg Opticks...", flush=True)
    download(OPTICKS_URL, CORPUS)

    opus_sha = sha256(opus_zip)
    opticks_sha = sha256(CORPUS)
    (EVIDENCE / "opus.sha256").write_text(f"{opus_sha}  {opus_zip.name}\n", encoding="utf-8")
    (EVIDENCE / "opticks.sha256").write_text(f"{opticks_sha}  {CORPUS.name}\n", encoding="utf-8")

    with zipfile.ZipFile(opus_zip) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"OPUS zip CRC failure: {bad}")
        zf.extractall(SRC)
        inventory = [{"name": i.filename, "size": i.file_size, "crc": i.CRC} for i in zf.infolist() if not i.is_dir()]
    (EVIDENCE / "opus-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")

    model_dir = locate_model(SRC)
    source_spm, target_spm = locate_sentencepiece(model_dir)

    print(f"Converting {model_dir} to CTranslate2 float32...", flush=True)
    t0 = time.time()
    ctranslate2.converters.OpusMTConverter(str(model_dir)).convert(
        str(CT2), quantization="float32", force=True
    )
    conversion_seconds = time.time() - t0

    source_tok = spm.SentencePieceProcessor(model_file=str(source_spm))
    target_tok = spm.SentencePieceProcessor(model_file=str(target_spm))
    translator = ctranslate2.Translator(str(CT2), device="cpu", compute_type="float32")

    def translate(texts: list[str]) -> list[str]:
        tokenized = [source_tok.encode(t, out_type=str) for t in texts]
        result = translator.translate_batch(tokenized, beam_size=4, max_batch_size=32)
        return [target_tok.decode(x.hypotheses[0]) for x in result]

    smoke_source = [
        "Light is composed of rays differently refrangible.",
        "The same plane was used in the experiment.",
        "The distance was 15 inches and not 50 inches.",
    ]
    smoke_translation = translate(smoke_source)
    if len(smoke_translation) != len(smoke_source) or any(not x.strip() for x in smoke_translation):
        raise RuntimeError("real OPUS smoke translation is incomplete")

    text = CORPUS.read_text(encoding="utf-8-sig", errors="replace")
    word_count = len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))
    if word_count < 90_000:
        raise RuntimeError(f"Opticks corpus below acceptance threshold: {word_count}")

    sentences = [
        x.strip()
        for x in re.split(r"(?<=[.!?])\s+", text)
        if 4 <= len(x.split()) <= 80
    ]
    if len(sentences) < 120:
        raise RuntimeError(f"not enough bounded sentences: {len(sentences)}")

    picks: list[str] = []
    for frac in (0.05, 0.25, 0.50, 0.75, 0.95):
        center = min(len(sentences) - 1, int(len(sentences) * frac))
        picks.extend(sentences[max(0, center - 12): min(len(sentences), center + 12)])
    picks = picks[:120]

    translated: list[str] = []
    t1 = time.time()
    for i in range(0, len(picks), 16):
        translated.extend(translate(picks[i:i + 16]))
    pilot_seconds = time.time() - t1
    if len(translated) != len(picks) or any(not x.strip() for x in translated):
        raise RuntimeError("representative real-model pilot incomplete")

    payload = {
        "schema": "rocketdict-github-real-opus-gate/2",
        "real_model": True,
        "fake_or_identity_translation": False,
        "official_opus_url": OPUS_URL,
        "opus_zip_sha256": opus_sha,
        "opticks_url": OPTICKS_URL,
        "opticks_sha256": opticks_sha,
        "ctranslate2_version": ctranslate2.__version__,
        "sentencepiece_version": getattr(spm, "__version__", None),
        "compute_type": "float32",
        "conversion_seconds": conversion_seconds,
        "opticks_words_regex": word_count,
        "meets_90000_word_requirement": word_count >= 90_000,
        "representative_sentences": len(picks),
        "representative_words": sum(len(x.split()) for x in picks),
        "pilot_seconds": pilot_seconds,
        "smoke": [
            {"source": s, "translation": t}
            for s, t in zip(smoke_source, smoke_translation)
        ],
        "representative_sample": [
            {"source": s, "translation": t}
            for s, t in list(zip(picks, translated))[:20]
        ],
    }
    (EVIDENCE / "real-opus-gate.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT / "representative.tsv").write_text(
        "".join(f"{s}\t{t}\n" for s, t in zip(picks, translated)), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
