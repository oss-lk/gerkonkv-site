from __future__ import annotations

"""Runtime discovery/loading for production NLP and real OPUS MT.

No downloader lives here.  Product processing is offline: assets must already
be provisioned and their identities must be explicit.  Missing assets produce
``available=false`` or a hard exception, never a degraded fake implementation.
"""

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

OPUS_REVISION = "opus-2020-02-11"
OPUS_ARCHIVE_SHA256 = "798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677"
OPUS_ASSET_SCHEMA = "rocketdict-opus-asset/1"
OPUS_ASSET_ENV = "ROCKETDICT_OPUS_ASSET_DIR"

NLP_MODELS = {
    "en-sm": "en_core_web_sm",
    "en-md": "en_core_web_md",
    "en-lg": "en_core_web_lg",
    "en-trf": "en_core_web_trf",
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nlp_status(implementation: str) -> dict[str, Any]:
    model = NLP_MODELS.get(implementation)
    if model is None:
        return {
            "available": False,
            "reason": "unsupported_product_nlp_implementation",
            "implementation": implementation,
        }
    spacy_available = importlib.util.find_spec("spacy") is not None
    model_available = importlib.util.find_spec(model) is not None
    available = bool(spacy_available and model_available)
    return {
        "available": available,
        "reason": "ready" if available else "missing_spacy_or_model",
        "implementation": implementation,
        "spacy_importable": spacy_available,
        "model": model,
        "model_importable": model_available,
        "offline": True,
    }


def load_nlp(implementation: str):  # type: ignore[no-untyped-def]
    status = nlp_status(implementation)
    if not status["available"]:
        raise RuntimeError(f"Production NLP runtime is unavailable: {status}")
    import spacy

    model = str(status["model"])
    nlp = spacy.load(model)
    pipe_names = set(nlp.pipe_names)
    if "parser" not in pipe_names:
        raise RuntimeError(f"spaCy model {model!r} lacks dependency parser")
    if not ({"tagger", "morphologizer"} & pipe_names):
        raise RuntimeError(f"spaCy model {model!r} lacks POS-capable pipeline")
    if not ("lemmatizer" in pipe_names or hasattr(nlp.vocab, "morphology")):
        raise RuntimeError(f"spaCy model {model!r} lacks lemma capability")
    return nlp


@dataclass(frozen=True)
class OpusAsset:
    root: Path
    revision: str
    source_archive_sha256: str
    ct2_model_dir: Path
    source_sentencepiece: Path
    target_sentencepiece: Path
    manifest_sha256: str


def _inside(root: Path, value: str, *, label: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"OPUS asset {label} escapes asset root") from exc
    return candidate


def load_opus_asset(root: Path | str | None = None) -> OpusAsset:
    raw_root = str(root or os.environ.get(OPUS_ASSET_ENV) or "").strip()
    if not raw_root:
        raise RuntimeError(
            f"Real OPUS asset is not configured; set {OPUS_ASSET_ENV} to a provisioned offline asset directory"
        )
    asset_root = Path(raw_root).expanduser().resolve()
    manifest = asset_root / "rocketdict-opus-asset.json"
    if not manifest.is_file():
        raise RuntimeError(f"OPUS asset manifest is missing: {manifest}")
    raw = manifest.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"OPUS asset manifest is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != OPUS_ASSET_SCHEMA:
        raise RuntimeError(f"Unexpected OPUS asset manifest schema: {payload.get('schema') if isinstance(payload, dict) else type(payload).__name__}")
    if payload.get("revision") != OPUS_REVISION:
        raise RuntimeError(
            f"OPUS asset revision drift: {payload.get('revision')!r} != {OPUS_REVISION!r}"
        )
    archive_sha = str(payload.get("source_archive_sha256") or "").casefold()
    if archive_sha != OPUS_ARCHIVE_SHA256:
        raise RuntimeError(
            "OPUS asset does not bind the accepted official archive SHA-256: "
            f"{archive_sha!r} != {OPUS_ARCHIVE_SHA256!r}"
        )
    model_dir = _inside(asset_root, str(payload.get("ct2_model_dir") or ""), label="ct2_model_dir")
    source_spm = _inside(asset_root, str(payload.get("source_sentencepiece") or ""), label="source_sentencepiece")
    target_spm = _inside(asset_root, str(payload.get("target_sentencepiece") or ""), label="target_sentencepiece")
    if not model_dir.is_dir():
        raise RuntimeError(f"CTranslate2 model directory is missing: {model_dir}")
    if not source_spm.is_file() or not target_spm.is_file():
        raise RuntimeError("SentencePiece model files declared by OPUS manifest are missing")
    if not (model_dir / "model.bin").is_file():
        raise RuntimeError(f"CTranslate2 model.bin is missing: {model_dir / 'model.bin'}")
    return OpusAsset(
        root=asset_root,
        revision=OPUS_REVISION,
        source_archive_sha256=archive_sha,
        ct2_model_dir=model_dir,
        source_sentencepiece=source_spm,
        target_sentencepiece=target_spm,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )


def opus_status() -> dict[str, Any]:
    ctranslate2_available = importlib.util.find_spec("ctranslate2") is not None
    sentencepiece_available = importlib.util.find_spec("sentencepiece") is not None
    try:
        asset = load_opus_asset()
        asset_error = None
    except Exception as exc:
        asset = None
        asset_error = str(exc)
    available = bool(ctranslate2_available and sentencepiece_available and asset is not None)
    return {
        "available": available,
        "reason": "ready" if available else "missing_runtime_or_verified_asset",
        "ctranslate2_importable": ctranslate2_available,
        "sentencepiece_importable": sentencepiece_available,
        "asset_configured": asset is not None,
        "asset_error": asset_error,
        "revision": asset.revision if asset else OPUS_REVISION,
        "source_archive_sha256": asset.source_archive_sha256 if asset else OPUS_ARCHIVE_SHA256,
        "manifest_sha256": asset.manifest_sha256 if asset else None,
        "offline": True,
        "compute_type": "float32",
    }


class OpusTranslator:
    def __init__(self, *, device: str = "cpu", compute_type: str = "float32") -> None:
        if compute_type != "float32":
            raise RuntimeError(
                f"Product OPUS acceptance requires float32; got {compute_type!r}"
            )
        if device != "cpu":
            raise RuntimeError(
                f"Current Product OPUS profile is pinned to CPU for reproducible acceptance; got {device!r}"
            )
        status = opus_status()
        if not status["available"]:
            raise RuntimeError(f"Real OPUS runtime is unavailable: {status}")
        asset = load_opus_asset()
        import ctranslate2
        import sentencepiece as spm

        self.asset = asset
        self._source = spm.SentencePieceProcessor(model_file=str(asset.source_sentencepiece))
        self._target = spm.SentencePieceProcessor(model_file=str(asset.target_sentencepiece))
        self._translator = ctranslate2.Translator(
            str(asset.ct2_model_dir), device=device, compute_type=compute_type
        )

    def translate(
        self,
        texts: list[str],
        *,
        beam_size: int = 6,
        num_hypotheses: int = 1,
        max_decoding_length: int = 512,
    ) -> list[list[dict[str, Any]]]:
        if not texts:
            return []
        encoded = [self._source.encode(text, out_type=str) for text in texts]
        if any(not row for row in encoded):
            raise RuntimeError("OPUS tokenizer produced an empty source token sequence")
        results = self._translator.translate_batch(
            encoded,
            beam_size=int(beam_size),
            num_hypotheses=int(num_hypotheses),
            max_decoding_length=int(max_decoding_length),
            return_scores=True,
        )
        output: list[list[dict[str, Any]]] = []
        for result in results:
            rows: list[dict[str, Any]] = []
            hypotheses = list(result.hypotheses)
            scores = list(getattr(result, "scores", []) or [])
            for rank, tokens in enumerate(hypotheses):
                text = self._target.decode(tokens).strip()
                rows.append(
                    {
                        "rank": rank,
                        "text": text,
                        "tokens": list(tokens),
                        "score": float(scores[rank]) if rank < len(scores) else None,
                    }
                )
            output.append(rows)
        if len(output) != len(texts):
            raise RuntimeError("OPUS backend returned a different batch cardinality")
        return output
