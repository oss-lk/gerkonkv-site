from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform

import stanza

ROOT = Path("rocketdict-workbench-offline-nlp")
MODEL_ROOT = ROOT / "stanza_resources"
PROCESSORS = "tokenize,pos,lemma,depparse"
VERSION = "1.14.0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    stanza.download("en", model_dir=str(MODEL_ROOT), processors=PROCESSORS, verbose=False)
    nlp = stanza.Pipeline(
        "en",
        model_dir=str(MODEL_ROOT),
        processors=PROCESSORS,
        use_gpu=False,
        download_method=None,
        verbose=False,
    )
    text = "The glass is 5/62 inch thick. The prism separates colours."
    doc = nlp(text)
    tokens = []
    for sent_index, sentence in enumerate(doc.sentences):
        for word in sentence.words:
            tokens.append({
                "sentence": sent_index,
                "text": word.text,
                "lemma": word.lemma,
                "upos": word.upos,
                "xpos": word.xpos,
                "head": word.head,
                "deprel": word.deprel,
            })
    by_surface = {row["text"].casefold(): row for row in tokens}
    assert by_surface["separates"]["lemma"].casefold() == "separate"
    assert by_surface["colours"]["lemma"].casefold() == "colour"
    assert by_surface["prism"]["upos"] in {"NOUN", "PROPN"}
    assert by_surface["thick"]["upos"] in {"ADJ", "ADV"}

    files = []
    for path in sorted(p for p in MODEL_ROOT.rglob("*") if p.is_file()):
        files.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "schema": "rocketdict-workbench-offline-nlp/1",
        "provider": "stanza-full-en",
        "stanza_version": stanza.__version__,
        "expected_stanza_version": VERSION,
        "python": platform.python_version(),
        "language": "en",
        "processors": PROCESSORS.split(","),
        "network_required_at_runtime": False,
        "pipeline_download_method": None,
        "license": "Apache-2.0",
        "model_root": "stanza_resources",
        "file_count": len(files),
        "total_bytes": sum(x["bytes"] for x in files),
        "files": files,
        "smoke": {"source": text, "tokens": tokens},
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "stanza_version": stanza.__version__,
        "processors": PROCESSORS,
        "file_count": manifest["file_count"],
        "total_bytes": manifest["total_bytes"],
        "separates": by_surface["separates"],
        "colours": by_surface["colours"],
        "prism": by_surface["prism"],
        "thick": by_surface["thick"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
