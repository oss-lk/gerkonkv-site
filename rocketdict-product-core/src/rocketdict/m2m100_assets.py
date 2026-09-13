from __future__ import annotations

"""Provision the pinned facebook/m2m100_418M checkpoint as an offline CT2 asset."""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .m2m100_runtime import (
    M2M100_ASSET_SCHEMA,
    M2M100_LICENSE,
    M2M100_MANIFEST_NAME,
    M2M100_MODEL_SHA256,
    M2M100_REPOSITORY,
    M2M100_REVISION,
    M2M100_SOURCE_LANGUAGE,
    M2M100_TARGET_LANGUAGE,
    M2M100_TOKENIZER_FILES,
)

PINNED_SOURCE_FILES: dict[str, str] = {
    "config.json": "df0ae43e4e4b0d7e3c97b7f447857a70ef6b6a2aa1f145cedbcc730d95f67134",
    "pytorch_model.bin": M2M100_MODEL_SHA256,
    "sentencepiece.bpe.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
    "special_tokens_map.json": "c1a4f86c3874d279ae1b2a05162858db5dd6c61665d84223ed886cbcff08fda6",
    "tokenizer_config.json": "a53e6aa83da0b82565ed90c3849056307a9453843322ac5b8439ec4b9497fe48",
    "vocab.json": "b6e77e474aeea8f441363aca7614317c06381f3eacfe10fb9856d5081d1074cc",
}


def _sha(path: Path) -> str:
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
        rows.append({"path": relative, "bytes": size, "sha256": _sha(path)})
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(rows),
        "bytes": total,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "files": rows,
    }


def _verify_snapshot(source: Path) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    for relative, expected_sha in PINNED_SOURCE_FILES.items():
        path = source / relative
        if not path.is_file():
            raise RuntimeError(f"Pinned M2M100 source file is missing: {relative}")
        actual = _sha(path)
        if actual != expected_sha:
            raise RuntimeError(
                f"Pinned M2M100 source file identity drift for {relative}: {actual} != {expected_sha}"
            )
        observed.append(
            {"path": relative, "bytes": path.stat().st_size, "sha256": actual}
        )
    config = json.loads((source / "config.json").read_text(encoding="utf-8"))
    if config.get("model_type") != "m2m_100":
        raise RuntimeError(f"Pinned M2M100 model_type drift: {config.get('model_type')!r}")
    if int(config.get("max_position_embeddings") or 0) != 1024:
        raise RuntimeError("Pinned M2M100 max_position_embeddings drift")
    return observed


def build_m2m100_asset(
    source_snapshot: Path | str,
    destination: Path | str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    source = Path(source_snapshot).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    source_files = _verify_snapshot(source)
    if destination.exists() and any(destination.iterdir()) and not force:
        raise RuntimeError(
            f"Destination is not empty: {destination}; pass --force for an explicit rebuild"
        )
    destination.mkdir(parents=True, exist_ok=True)

    try:
        import ctranslate2
    except Exception as exc:
        raise RuntimeError("M2M100 provisioning requires CTranslate2") from exc
    try:
        import transformers  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "M2M100 provisioning requires Transformers and its model-loading dependencies"
        ) from exc

    with tempfile.TemporaryDirectory(prefix="rocketdict-m2m100-") as temp_name:
        build_root = Path(temp_name) / "asset"
        ct2_root = build_root / "ct2"
        tokenizer_root = build_root / "tokenizer"
        ct2_root.mkdir(parents=True)
        tokenizer_root.mkdir(parents=True)

        ctranslate2.converters.TransformersConverter(str(source)).convert(
            str(ct2_root), quantization="float32", force=True
        )
        if not (ct2_root / "model.bin").is_file():
            raise RuntimeError("M2M100 CTranslate2 conversion did not create model.bin")

        for relative in M2M100_TOKENIZER_FILES:
            shutil.copy2(source / relative, tokenizer_root / relative)
        provenance = {
            "repository": M2M100_REPOSITORY,
            "revision": M2M100_REVISION,
            "license": M2M100_LICENSE,
            "model_sha256": M2M100_MODEL_SHA256,
            "source_language": M2M100_SOURCE_LANGUAGE,
            "target_language": M2M100_TARGET_LANGUAGE,
        }
        (build_root / "SOURCE_PROVENANCE.json").write_text(
            json.dumps(provenance, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

        tree = _tree_identity(build_root)
        manifest = {
            "schema": M2M100_ASSET_SCHEMA,
            "repository": M2M100_REPOSITORY,
            "revision": M2M100_REVISION,
            "model_sha256": M2M100_MODEL_SHA256,
            "license": M2M100_LICENSE,
            "source_language": M2M100_SOURCE_LANGUAGE,
            "target_language": M2M100_TARGET_LANGUAGE,
            "source_snapshot_files": source_files,
            "ct2_model_dir": "ct2",
            "tokenizer_dir": "tokenizer",
            "compute_type": "float32",
            "converter": {
                "name": "ctranslate2.converters.TransformersConverter",
                "ctranslate2_version": str(ctranslate2.__version__),
            },
            "payload_tree": {
                "file_count": tree["file_count"],
                "bytes": tree["bytes"],
                "sha256": tree["sha256"],
            },
        }
        (build_root / M2M100_MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if destination.exists() and force:
            for child in list(destination.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        for child in build_root.iterdir():
            target = destination / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)

    return {
        "schema": "rocketdict-m2m100-en-ru-asset-build/1",
        "status": "completed",
        "destination": str(destination),
        "repository": M2M100_REPOSITORY,
        "revision": M2M100_REVISION,
        "model_sha256": M2M100_MODEL_SHA256,
        "license": M2M100_LICENSE,
        "source_language": M2M100_SOURCE_LANGUAGE,
        "target_language": M2M100_TARGET_LANGUAGE,
        "manifest_sha256": _sha(destination / M2M100_MANIFEST_NAME),
        "payload_tree_sha256": manifest["payload_tree"]["sha256"],
        "payload_file_count": manifest["payload_tree"]["file_count"],
        "payload_bytes": manifest["payload_tree"]["bytes"],
        "network_used_by_builder": False,
    }
