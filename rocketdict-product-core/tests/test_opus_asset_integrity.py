from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rocketdict.runtime import (
    OPUS_ARCHIVE_SHA256,
    OPUS_ASSET_SCHEMA,
    OPUS_REVISION,
    _payload_tree_identity,
    load_opus_asset,
)


def _write_asset(root: Path) -> Path:
    (root / "ct2").mkdir(parents=True)
    (root / "ct2" / "model.bin").write_bytes(b"model-v1")
    (root / "ct2" / "config.json").write_text("{}\n", encoding="utf-8")
    (root / "source.spm").write_bytes(b"source-spm")
    (root / "target.spm").write_bytes(b"target-spm")
    tree = _payload_tree_identity(root)
    manifest = {
        "schema": OPUS_ASSET_SCHEMA,
        "revision": OPUS_REVISION,
        "source_archive_sha256": OPUS_ARCHIVE_SHA256,
        "source_archive_bytes": 123,
        "ct2_model_dir": "ct2",
        "source_sentencepiece": "source.spm",
        "target_sentencepiece": "target.spm",
        "compute_type": "float32",
        "converter": {"name": "test", "ctranslate2_version": "4.8.2"},
        "payload_tree": tree,
    }
    path = root / "rocketdict-opus-asset.json"
    path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return path


def test_load_opus_asset_verifies_complete_payload_tree(tmp_path: Path) -> None:
    manifest = _write_asset(tmp_path)
    asset = load_opus_asset(tmp_path)
    assert asset.source_archive_sha256 == OPUS_ARCHIVE_SHA256
    assert asset.payload_file_count == 4
    assert asset.payload_bytes > 0
    assert len(asset.payload_tree_sha256) == 64
    assert asset.manifest_sha256 == hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_mutated_model_bytes_are_rejected_even_with_unchanged_manifest(tmp_path: Path) -> None:
    _write_asset(tmp_path)
    (tmp_path / "ct2" / "model.bin").write_bytes(b"tampered-model")
    with pytest.raises(RuntimeError, match="payload bytes changed after provisioning"):
        load_opus_asset(tmp_path)


def test_added_untracked_payload_file_is_rejected(tmp_path: Path) -> None:
    _write_asset(tmp_path)
    (tmp_path / "ct2" / "unexpected.bin").write_bytes(b"extra")
    with pytest.raises(RuntimeError, match="payload bytes changed after provisioning"):
        load_opus_asset(tmp_path)


def test_float32_manifest_contract_is_fail_closed(tmp_path: Path) -> None:
    manifest_path = _write_asset(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["compute_type"] = "int8"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="must be float32"):
        load_opus_asset(tmp_path)
