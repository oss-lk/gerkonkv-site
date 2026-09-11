from __future__ import annotations

"""Provision the pinned TC-big snapshot into an offline CTranslate2 asset.

The builder is an explicit provisioning-time operation. It accepts a previously
downloaded Hugging Face snapshot, verifies every file used by the accepted
research identity, converts the pinned Marian weights to CTranslate2 float32,
and writes the manifest consumed by :mod:`rocketdict.alternative_mt_runtime`.
No network access occurs here.
"""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .alternative_mt_runtime import (
    TC_BIG_ASSET_SCHEMA,
    TC_BIG_LICENSE,
    TC_BIG_MANIFEST_NAME,
    TC_BIG_MODEL_SAFETENSORS_SHA256,
    TC_BIG_REPOSITORY,
    TC_BIG_REVISION,
    TC_BIG_TARGET_PREFIX,
    TC_BIG_TOKENIZER_FILES,
)

PINNED_SOURCE_FILES: dict[str, str] = {
    "README.md": "20a1bf8e91021f5aae1b271c633fbb70319acce47206292f0063f39db1cb67f9",
    "config.json": "962d235879c9def4cfdf140be81436d4fb9da25271dd69079df2c90b459f1332",
    "generation_config.json": "d851d84c804c745d92dae5659bd2d8e8b976b664dd0fbc39b82ee88340147802",
    "model.safetensors": TC_BIG_MODEL_SAFETENSORS_SHA256,
    "source.spm": "3612abfe04bf08344ba91115f0e15e228a7a15a621ea856bfd548097dbaeb43c",
    "special_tokens_map.json": "09059cedc26bc46bc09a52f05b92d4922e11917e87f3b92059bb1a63a59ab2c4",
    "target.spm": "22940e744b3a9fd166a04880938fb61f7dfa8ba4b5d2d3f6371a6c4ba8f3b019",
    "tokenizer_config.json": "41deeedfc0e3ce366d6bde180dee025a8ca1bcd62b1451889301e8ea4bcbb609",
    "vocab.json": "41dbdff4a0b5a6ab125715c3342c5ce6516e93ffd49608813240403f036c5efb",
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _tree_identity(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.relative_to(root).as_posix() == TC_BIG_MANIFEST_NAME:
            continue
        size = path.stat().st_size
        total += size
        rows.append({"path": path.relative_to(root).as_posix(), "bytes": size, "sha256": _sha(path)})
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"file_count": len(rows), "bytes": total, "sha256": hashlib.sha256(raw).hexdigest(), "files": rows}


def _verify_snapshot(source: Path) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    for relative, expected_sha in PINNED_SOURCE_FILES.items():
        path = source / relative
        if not path.is_file():
            raise RuntimeError(f"Pinned TC-big source file is missing: {relative}")
        actual = _sha(path)
        if actual != expected_sha:
            raise RuntimeError(f"Pinned TC-big source file identity drift for {relative}: {actual} != {expected_sha}")
        observed.append({"path": relative, "bytes": path.stat().st_size, "sha256": actual})
    readme = (source / "README.md").read_text(encoding="utf-8")
    if "license: cc-by-4.0" not in readme.casefold():
        raise RuntimeError("Pinned TC-big README no longer declares CC-BY-4.0")
    return observed


def build_tc_big_asset(source_snapshot: Path | str, destination: Path | str, *, force: bool = False) -> dict[str, Any]:
    source = Path(source_snapshot).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    source_files = _verify_snapshot(source)
    if destination.exists() and any(destination.iterdir()) and not force:
        raise RuntimeError(f"Destination is not empty: {destination}; pass --force for an explicit rebuild")
    destination.mkdir(parents=True, exist_ok=True)

    try:
        import ctranslate2
    except Exception as exc:
        raise RuntimeError("TC-big provisioning requires CTranslate2") from exc
    try:
        import transformers  # noqa: F401
    except Exception as exc:
        raise RuntimeError("TC-big provisioning requires Transformers and its model-loading dependencies") from exc

    with tempfile.TemporaryDirectory(prefix="rocketdict-tc-big-") as temp_name:
        build_root = Path(temp_name) / "asset"
        ct2_root = build_root / "ct2"
        tokenizer_root = build_root / "tokenizer"
        ct2_root.mkdir(parents=True)
        tokenizer_root.mkdir(parents=True)

        ctranslate2.converters.TransformersConverter(str(source)).convert(
            str(ct2_root), quantization="float32", force=True
        )
        if not (ct2_root / "model.bin").is_file():
            raise RuntimeError("TC-big CTranslate2 conversion did not create model.bin")

        for relative in TC_BIG_TOKENIZER_FILES:
            shutil.copy2(source / relative, tokenizer_root / relative)
        # Keep immutable attribution/provenance text beside the runnable payload.
        shutil.copy2(source / "README.md", build_root / "SOURCE_README.md")
        if (source / "generation_config.json").is_file():
            shutil.copy2(source / "generation_config.json", tokenizer_root / "generation_config.json")

        tree = _tree_identity(build_root)
        manifest = {
            "schema": TC_BIG_ASSET_SCHEMA,
            "repository": TC_BIG_REPOSITORY,
            "revision": TC_BIG_REVISION,
            "model_safetensors_sha256": TC_BIG_MODEL_SAFETENSORS_SHA256,
            "license": TC_BIG_LICENSE,
            "target_prefix": TC_BIG_TARGET_PREFIX,
            "source_snapshot_files": source_files,
            "ct2_model_dir": "ct2",
            "tokenizer_dir": "tokenizer",
            "compute_type": "float32",
            "converter": {
                "name": "ctranslate2.converters.TransformersConverter",
                "ctranslate2_version": str(ctranslate2.__version__),
            },
            "payload_tree": {"file_count": tree["file_count"], "bytes": tree["bytes"], "sha256": tree["sha256"]},
        }
        (build_root / TC_BIG_MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        "schema": "rocketdict-tc-big-en-ru-asset-build/1",
        "status": "completed",
        "destination": str(destination),
        "repository": TC_BIG_REPOSITORY,
        "revision": TC_BIG_REVISION,
        "model_safetensors_sha256": TC_BIG_MODEL_SAFETENSORS_SHA256,
        "license": TC_BIG_LICENSE,
        "manifest_sha256": _sha(destination / TC_BIG_MANIFEST_NAME),
        "payload_tree_sha256": manifest["payload_tree"]["sha256"],
        "payload_file_count": manifest["payload_tree"]["file_count"],
        "payload_bytes": manifest["payload_tree"]["bytes"],
        "network_used_by_builder": False,
    }
