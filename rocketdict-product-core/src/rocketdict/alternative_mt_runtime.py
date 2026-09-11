from __future__ import annotations

"""Pinned independent TC-big runtime for opt-in translation rescue research.

This module is intentionally separate from the accepted baseline OPUS runtime.
It loads only a previously provisioned, byte-verified CTranslate2 float32 asset
and performs no network access.  The multilingual Marian language prefix is
handled by Hugging Face ``MarianTokenizer`` semantics; PyTorch is not required
for inference.
"""

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

TC_BIG_REPOSITORY = "Helsinki-NLP/opus-mt-tc-big-en-zle"
TC_BIG_REVISION = "708be1d372fe4c358a352f404e6dc9ca0126ba48"
TC_BIG_MODEL_SAFETENSORS_SHA256 = "e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416"
TC_BIG_LICENSE = "cc-by-4.0"
TC_BIG_TARGET_PREFIX = ">>rus<<"
TC_BIG_ASSET_SCHEMA = "rocketdict-tc-big-en-ru-asset/1"
TC_BIG_ASSET_ENV = "ROCKETDICT_TC_BIG_ASSET_DIR"
TC_BIG_MANIFEST_NAME = "rocketdict-tc-big-asset.json"
TC_BIG_TOKENIZER_FILES = (
    "source.spm",
    "target.spm",
    "vocab.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
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
        if relative == TC_BIG_MANIFEST_NAME:
            continue
        size = path.stat().st_size
        total += size
        rows.append({"path": relative, "bytes": size, "sha256": _file_sha256(path)})
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"file_count": len(rows), "bytes": total, "sha256": hashlib.sha256(raw).hexdigest()}


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").casefold()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _inside(root: Path, value: str, *, label: str) -> Path:
    if not value:
        raise RuntimeError(f"TC-big asset {label} is empty")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"TC-big asset {label} escapes asset root") from exc
    return candidate


@dataclass(frozen=True)
class TcBigAsset:
    root: Path
    repository: str
    revision: str
    model_safetensors_sha256: str
    license: str
    ct2_model_dir: Path
    tokenizer_dir: Path
    manifest_sha256: str
    payload_tree_sha256: str
    payload_file_count: int
    payload_bytes: int


def load_tc_big_asset(root: Path | str | None = None) -> TcBigAsset:
    raw_root = str(root or os.environ.get(TC_BIG_ASSET_ENV) or "").strip()
    if not raw_root:
        raise RuntimeError(
            f"Pinned TC-big asset is not configured; set {TC_BIG_ASSET_ENV} to a provisioned offline asset directory"
        )
    asset_root = Path(raw_root).expanduser().resolve()
    manifest = asset_root / TC_BIG_MANIFEST_NAME
    if not manifest.is_file():
        raise RuntimeError(f"TC-big asset manifest is missing: {manifest}")
    raw = manifest.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"TC-big asset manifest is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != TC_BIG_ASSET_SCHEMA:
        raise RuntimeError("Unexpected TC-big asset manifest schema")
    if payload.get("repository") != TC_BIG_REPOSITORY:
        raise RuntimeError(f"TC-big repository drift: {payload.get('repository')!r}")
    if payload.get("revision") != TC_BIG_REVISION:
        raise RuntimeError(f"TC-big revision drift: {payload.get('revision')!r}")
    if str(payload.get("model_safetensors_sha256") or "").casefold() != TC_BIG_MODEL_SAFETENSORS_SHA256:
        raise RuntimeError("TC-big source weights identity drift")
    if str(payload.get("license") or "").casefold() != TC_BIG_LICENSE:
        raise RuntimeError("TC-big license identity drift")
    if payload.get("target_prefix") != TC_BIG_TARGET_PREFIX:
        raise RuntimeError("TC-big target language prefix drift")
    if payload.get("compute_type") != "float32":
        raise RuntimeError("TC-big Product research asset must be float32")

    expected = payload.get("payload_tree")
    if not isinstance(expected, dict):
        raise RuntimeError("TC-big asset manifest lacks payload_tree identity")
    expected_sha = str(expected.get("sha256") or "").casefold()
    expected_files = expected.get("file_count")
    expected_bytes = expected.get("bytes")
    if not _valid_sha256(expected_sha):
        raise RuntimeError("TC-big payload_tree lacks valid SHA-256")
    if isinstance(expected_files, bool) or not isinstance(expected_files, int) or expected_files <= 0:
        raise RuntimeError("TC-big payload_tree has invalid file_count")
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise RuntimeError("TC-big payload_tree has invalid byte count")
    observed = _tree_identity(asset_root)
    if observed != {"file_count": expected_files, "bytes": expected_bytes, "sha256": expected_sha}:
        raise RuntimeError(f"TC-big asset payload bytes changed after provisioning: observed={observed!r} expected={expected!r}")

    ct2_model_dir = _inside(asset_root, str(payload.get("ct2_model_dir") or ""), label="ct2_model_dir")
    tokenizer_dir = _inside(asset_root, str(payload.get("tokenizer_dir") or ""), label="tokenizer_dir")
    if not (ct2_model_dir / "model.bin").is_file():
        raise RuntimeError("TC-big CTranslate2 model.bin is missing")
    for relative in TC_BIG_TOKENIZER_FILES:
        if not (tokenizer_dir / relative).is_file():
            raise RuntimeError(f"TC-big tokenizer file is missing: {relative}")

    return TcBigAsset(
        root=asset_root,
        repository=TC_BIG_REPOSITORY,
        revision=TC_BIG_REVISION,
        model_safetensors_sha256=TC_BIG_MODEL_SAFETENSORS_SHA256,
        license=TC_BIG_LICENSE,
        ct2_model_dir=ct2_model_dir,
        tokenizer_dir=tokenizer_dir,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        payload_tree_sha256=expected_sha,
        payload_file_count=int(expected_files),
        payload_bytes=int(expected_bytes),
    )


def tc_big_status() -> dict[str, Any]:
    ctranslate2_available = importlib.util.find_spec("ctranslate2") is not None
    transformers_available = importlib.util.find_spec("transformers") is not None
    sentencepiece_available = importlib.util.find_spec("sentencepiece") is not None
    sacremoses_available = importlib.util.find_spec("sacremoses") is not None
    try:
        asset = load_tc_big_asset()
        asset_error = None
    except Exception as exc:
        asset = None
        asset_error = str(exc)
    available = bool(
        ctranslate2_available
        and transformers_available
        and sentencepiece_available
        and sacremoses_available
        and asset is not None
    )
    return {
        "available": available,
        "reason": "ready" if available else "missing_runtime_or_verified_asset",
        "ctranslate2_importable": ctranslate2_available,
        "transformers_importable": transformers_available,
        "sentencepiece_importable": sentencepiece_available,
        "sacremoses_importable": sacremoses_available,
        "asset_configured": asset is not None,
        "asset_error": asset_error,
        "asset_manifest_sha256": None if asset is None else asset.manifest_sha256,
        "asset_payload_tree_sha256": None if asset is None else asset.payload_tree_sha256,
        "asset_payload_file_count": None if asset is None else asset.payload_file_count,
        "asset_payload_bytes": None if asset is None else asset.payload_bytes,
        "repository": TC_BIG_REPOSITORY,
        "revision": TC_BIG_REVISION,
        "model_safetensors_sha256": TC_BIG_MODEL_SAFETENSORS_SHA256,
        "license": TC_BIG_LICENSE,
        "offline": True,
        "compute_type": "float32",
        "torch_required_for_inference": False,
    }


class TcBigTranslator:
    def __init__(self, *, device: str = "cpu", compute_type: str = "float32") -> None:
        if compute_type != "float32":
            raise RuntimeError(f"TC-big acceptance research requires float32; got {compute_type!r}")
        if device != "cpu":
            raise RuntimeError(f"Current TC-big acceptance research is pinned to CPU; got {device!r}")
        status = tc_big_status()
        if not status["available"]:
            raise RuntimeError(f"Pinned TC-big runtime is unavailable: {status}")
        asset = load_tc_big_asset()
        import ctranslate2
        from transformers import MarianTokenizer

        self.asset = asset
        self._tokenizer = MarianTokenizer.from_pretrained(str(asset.tokenizer_dir), local_files_only=True)
        self._translator = ctranslate2.Translator(str(asset.ct2_model_dir), device=device, compute_type=compute_type)

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
        encoded: list[list[str]] = []
        for text in texts:
            ids = self._tokenizer.encode(f"{TC_BIG_TARGET_PREFIX} {text}", add_special_tokens=True)
            tokens = list(self._tokenizer.convert_ids_to_tokens(ids))
            if not tokens:
                raise RuntimeError("TC-big MarianTokenizer produced an empty source token sequence")
            encoded.append(tokens)
        results = self._translator.translate_batch(
            encoded,
            beam_size=int(beam_size),
            num_hypotheses=int(num_hypotheses),
            max_decoding_length=int(max_decoding_length),
            length_penalty=1.0,
            return_scores=True,
        )
        if len(results) != len(texts):
            raise RuntimeError("TC-big backend returned a different batch cardinality")
        output: list[list[dict[str, Any]]] = []
        for result in results:
            hypotheses = list(result.hypotheses)
            scores = list(getattr(result, "scores", []) or [])
            rows: list[dict[str, Any]] = []
            for rank, tokens in enumerate(hypotheses):
                token_ids = self._tokenizer.convert_tokens_to_ids(list(tokens))
                text = self._tokenizer.decode(token_ids, skip_special_tokens=True).strip()
                rows.append({
                    "rank": rank,
                    "text": text,
                    "tokens": list(tokens),
                    "score": float(scores[rank]) if rank < len(scores) else None,
                })
            output.append(rows)
        return output
