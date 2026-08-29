from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform

import spacy

ROOT = Path("rocketdict-workbench-offline-spacy-en")
MODEL_WHEEL = ROOT / "en_core_web_sm-3.8.0-py3-none-any.whl"
MODEL_NAME = "en_core_web_sm"
MODEL_VERSION = "3.8.0"
MODEL_RELEASE_URL = "https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0"
MODEL_WHEEL_URL = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
MODEL_SHA256 = "1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not MODEL_WHEEL.is_file():
        raise RuntimeError(f"missing model wheel: {MODEL_WHEEL}")
    actual = sha256(MODEL_WHEEL)
    if actual != MODEL_SHA256:
        raise RuntimeError(f"model SHA mismatch: {actual} != {MODEL_SHA256}")
    nlp = spacy.load(MODEL_NAME)
    text = "The glass is 5/62 inch thick. The prism separates colours."
    doc = nlp(text)
    tokens = [
        {
            "text": token.text,
            "lemma": token.lemma_,
            "pos": token.pos_,
            "tag": token.tag_,
            "dep": token.dep_,
            "head": token.head.i,
            "is_stop": bool(token.is_stop),
        }
        for token in doc
    ]
    by_surface = {row["text"].casefold(): row for row in tokens}
    assert by_surface["separates"]["lemma"].casefold() == "separate"
    assert by_surface["colours"]["lemma"].casefold() == "colour"
    assert by_surface["prism"]["pos"] in {"NOUN", "PROPN"}
    assert by_surface["thick"]["pos"] in {"ADJ", "ADV"}
    assert by_surface["the"]["pos"] == "DET"
    assert by_surface["is"]["pos"] == "AUX"
    assert by_surface["5/62"]["pos"] == "NUM"
    meta = nlp.meta
    if meta.get("license") != "MIT":
        raise RuntimeError(f"unexpected model license: {meta.get('license')!r}")
    manifest = {
        "schema": "rocketdict-workbench-offline-spacy-en/1",
        "provider": "en-sm",
        "spacy_version": spacy.__version__,
        "python": platform.python_version(),
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "model_release_url": MODEL_RELEASE_URL,
        "model_wheel_url": MODEL_WHEEL_URL,
        "model_wheel": MODEL_WHEEL.name,
        "model_wheel_bytes": MODEL_WHEEL.stat().st_size,
        "model_wheel_sha256": actual,
        "model_license": meta.get("license"),
        "model_sources": meta.get("sources"),
        "pipeline": list(nlp.pipe_names),
        "capabilities": {
            "tokenization": True,
            "sentence_boundaries": True,
            "lemma": "lemmatizer" in nlp.pipe_names,
            "pos": "tagger" in nlp.pipe_names,
            "dependency": "parser" in nlp.pipe_names,
            "ner": "ner" in nlp.pipe_names,
        },
        "network_required_at_runtime": False,
        "smoke": {"source": text, "tokens": tokens},
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "spacy_version": spacy.__version__,
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "license": meta.get("license"),
        "wheel_sha256": actual,
        "pipeline": nlp.pipe_names,
        "separates": by_surface["separates"],
        "colours": by_surface["colours"],
        "the": by_surface["the"],
        "is": by_surface["is"],
        "5/62": by_surface["5/62"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
