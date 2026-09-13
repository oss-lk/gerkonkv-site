from __future__ import annotations

"""Pinned offline M2M100 EN→RU CTranslate2 runtime for opt-in research rescues.

The runtime loads only a previously provisioned, byte-verified float32 asset.
PyTorch is required to provision/convert the Hugging Face checkpoint but is not
required for inference.  The source and target languages are pinned to English
and Russian and the M2M100 target-language prefix is supplied explicitly.
"""

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

M2M100_REPOSITORY = "facebook/m2m100_418M"
M2M100_REVISION = "55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636"
M2M100_MODEL_SHA256 = "d907ea45e4e4b9db163382a6674f6218b3c59566fe06d77f4055c208b4e87ed1"
M2M100_LICENSE = "MIT"
M2M100_SOURCE_LANGUAGE = "en"
M2M100_TARGET_LANGUAGE = "ru"
M2M100_ASSET_SCHEMA = "rocketdict-m2m100-en-ru-asset/1"
M2M100_ASSET_ENV = "ROCKETDICT_M2M100_ASSET_DIR"
M2M100_MANIFEST_NAME = "rocketdict-m2m100-asset.json"
M2M100_TOKENIZER_FILES = (
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "vocab.json",
    "config.json",
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_identity(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == M2M100_MANIFEST_NAME:
            continue
        size = path.stat().st_size
        total += size
        rows.append({"path": relative, "bytes": size, "sha256": _file_sha256(path)})
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(rows),
        "bytes": total,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").casefold()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _inside(root: Path, value: str, *, label: str) -> Path:
    if not value:
        raise RuntimeError(f"M2M100 asset {label} is empty")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"M2M100 asset {label} escapes asset root") from exc
    return candidate


@dataclass(frozen=True)
class M2M100Asset:
    root: Path
    repository: str
    revision: str
    model_sha256: str
    license: str
    source_language: str
    target_language: str
    ct2_model_dir: Path
    tokenizer_dir: Path
    manifest_sha256: str
    payload_tree_sha256: str
    payload_file_count: int
    payload_bytes: int


def load_m2m100_asset(root: Path | str | None = None) -> M2M100Asset:
    raw_root = str(root or os.environ.get(M2M100_ASSET_ENV) or "").strip()
    if not raw_root:
        raise RuntimeError(
            f"Pinned M2M100 asset is not configured; set {M2M100_ASSET_ENV} to a provisioned offline asset directory"
        )
    asset_root = Path(raw_root).expanduser().resolve()
    manifest = asset_root / M2M100_MANIFEST_NAME
    if not manifest.is_file():
        raise RuntimeError(f"M2M100 asset manifest is missing: {manifest}")
    raw = manifest.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"M2M100 asset manifest is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != M2M100_ASSET_SCHEMA:
        raise RuntimeError("Unexpected M2M100 asset manifest schema")
    if payload.get("repository") != M2M100_REPOSITORY:
        raise RuntimeError(f"M2M100 repository drift: {payload.get('repository')!r}")
    if payload.get("revision") != M2M100_REVISION:
        raise RuntimeError(f"M2M100 revision drift: {payload.get('revision')!r}")
    if str(payload.get("model_sha256") or "").casefold() != M2M100_MODEL_SHA256:
        raise RuntimeError("M2M100 source weights identity drift")
    if str(payload.get("license") or "").casefold() != M2M100_LICENSE.casefold():
        raise RuntimeError("M2M100 license identity drift")
    if payload.get("source_language") != M2M100_SOURCE_LANGUAGE:
        raise RuntimeError("M2M100 source language drift")
    if payload.get("target_language") != M2M100_TARGET_LANGUAGE:
        raise RuntimeError("M2M100 target language drift")
    if payload.get("compute_type") != "float32":
        raise RuntimeError("M2M100 Product research asset must be float32")

    expected = payload.get("payload_tree")
    if not isinstance(expected, dict):
        raise RuntimeError("M2M100 asset manifest lacks payload_tree identity")
    expected_sha = str(expected.get("sha256") or "").casefold()
    expected_files = expected.get("file_count")
    expected_bytes = expected.get("bytes")
    if not _valid_sha256(expected_sha):
        raise RuntimeError("M2M100 payload_tree lacks valid SHA-256")
    if isinstance(expected_files, bool) or not isinstance(expected_files, int) or expected_files <= 0:
        raise RuntimeError("M2M100 payload_tree has invalid file_count")
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise RuntimeError("M2M100 payload_tree has invalid byte count")
    observed = _tree_identity(asset_root)
    expected_identity = {
        "file_count": expected_files,
        "bytes": expected_bytes,
        "sha256": expected_sha,
    }
    if observed != expected_identity:
        raise RuntimeError(
            f"M2M100 asset payload bytes changed after provisioning: observed={observed!r} expected={expected_identity!r}"
        )

    ct2_model_dir = _inside(
        asset_root, str(payload.get("ct2_model_dir") or ""), label="ct2_model_dir"
    )
    tokenizer_dir = _inside(
        asset_root, str(payload.get("tokenizer_dir") or ""), label="tokenizer_dir"
    )
    if not (ct2_model_dir / "model.bin").is_file():
        raise RuntimeError("M2M100 CTranslate2 model.bin is missing")
    for relative in M2M100_TOKENIZER_FILES:
        if not (tokenizer_dir / relative).is_file():
            raise RuntimeError(f"M2M100 tokenizer file is missing: {relative}")

    return M2M100Asset(
        root=asset_root,
        repository=M2M100_REPOSITORY,
        revision=M2M100_REVISION,
        model_sha256=M2M100_MODEL_SHA256,
        license=M2M100_LICENSE,
        source_language=M2M100_SOURCE_LANGUAGE,
        target_language=M2M100_TARGET_LANGUAGE,
        ct2_model_dir=ct2_model_dir,
        tokenizer_dir=tokenizer_dir,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        payload_tree_sha256=expected_sha,
        payload_file_count=int(expected_files),
        payload_bytes=int(expected_bytes),
    )


def m2m100_status() -> dict[str, Any]:
    ctranslate2_available = importlib.util.find_spec("ctranslate2") is not None
    transformers_available = importlib.util.find_spec("transformers") is not None
    sentencepiece_available = importlib.util.find_spec("sentencepiece") is not None
    try:
        asset = load_m2m100_asset()
        asset_error = None
    except Exception as exc:
        asset = None
        asset_error = str(exc)
    available = bool(
        ctranslate2_available
        and transformers_available
        and sentencepiece_available
        and asset is not None
    )
    return {
        "available": available,
        "reason": "ready" if available else "missing_runtime_or_verified_asset",
        "ctranslate2_importable": ctranslate2_available,
        "transformers_importable": transformers_available,
        "sentencepiece_importable": sentencepiece_available,
        "asset_configured": asset is not None,
        "asset_error": asset_error,
        "asset_manifest_sha256": None if asset is None else asset.manifest_sha256,
        "asset_payload_tree_sha256": None if asset is None else asset.payload_tree_sha256,
        "asset_payload_file_count": None if asset is None else asset.payload_file_count,
        "asset_payload_bytes": None if asset is None else asset.payload_bytes,
        "repository": M2M100_REPOSITORY,
        "revision": M2M100_REVISION,
        "model_sha256": M2M100_MODEL_SHA256,
        "license": M2M100_LICENSE,
        "source_language": M2M100_SOURCE_LANGUAGE,
        "target_language": M2M100_TARGET_LANGUAGE,
        "offline": True,
        "compute_type": "float32",
        "torch_required_for_inference": False,
    }


class M2M100Translator:
    def __init__(self, *, device: str = "cpu", compute_type: str = "float32") -> None:
        if compute_type != "float32":
            raise RuntimeError(
                f"M2M100 acceptance research requires float32; got {compute_type!r}"
            )
        if device != "cpu":
            raise RuntimeError(
                f"Current M2M100 acceptance research is pinned to CPU; got {device!r}"
            )
        status = m2m100_status()
        if not status["available"]:
            raise RuntimeError(f"Pinned M2M100 runtime is unavailable: {status}")
        asset = load_m2m100_asset()
        import ctranslate2
        from transformers import M2M100Tokenizer

        self.asset = asset
        self._tokenizer = M2M100Tokenizer.from_pretrained(
            str(asset.tokenizer_dir), local_files_only=True
        )
        self._tokenizer.src_lang = M2M100_SOURCE_LANGUAGE
        try:
            self._target_prefix_token = self._tokenizer.lang_code_to_token[
                M2M100_TARGET_LANGUAGE
            ]
        except KeyError as exc:
            raise RuntimeError("Pinned M2M100 tokenizer lacks Russian target token") from exc
        self._translator = ctranslate2.Translator(
            str(asset.ct2_model_dir), device=device, compute_type=compute_type
        )

    def translate(
        self,
        texts: list[str],
        *,
        beam_size: int = 5,
        num_hypotheses: int = 1,
        max_decoding_length: int = 512,
    ) -> list[list[dict[str, Any]]]:
        if not texts:
            return []
        encoded: list[list[str]] = []
        for text in texts:
            ids = self._tokenizer.encode(text, add_special_tokens=True)
            tokens = list(self._tokenizer.convert_ids_to_tokens(ids))
            if not tokens:
                raise RuntimeError("M2M100 tokenizer produced an empty source token sequence")
            encoded.append(tokens)
        target_prefix = [[self._target_prefix_token] for _ in encoded]
        results = self._translator.translate_batch(
            encoded,
            target_prefix=target_prefix,
            beam_size=int(beam_size),
            num_hypotheses=int(num_hypotheses),
            max_decoding_length=int(max_decoding_length),
            length_penalty=1.0,
            return_scores=True,
        )
        if len(results) != len(texts):
            raise RuntimeError("M2M100 backend returned a different batch cardinality")
        output: list[list[dict[str, Any]]] = []
        for result in results:
            hypotheses = list(result.hypotheses)
            scores = list(getattr(result, "scores", []) or [])
            rows: list[dict[str, Any]] = []
            for rank, raw_tokens in enumerate(hypotheses):
                tokens = list(raw_tokens)
                if not tokens or tokens[0] != self._target_prefix_token:
                    raise RuntimeError("M2M100 backend did not preserve the forced target prefix")
                tokens = tokens[1:]
                token_ids = self._tokenizer.convert_tokens_to_ids(tokens)
                text = self._tokenizer.decode(
                    token_ids, skip_special_tokens=True
                ).strip()
                if not text:
                    raise RuntimeError("M2M100 backend produced an empty decoded target")
                rows.append(
                    {
                        "rank": rank,
                        "text": text,
                        "tokens": list(raw_tokens),
                        "score": float(scores[rank]) if rank < len(scores) else None,
                    }
                )
            output.append(rows)
        return output
