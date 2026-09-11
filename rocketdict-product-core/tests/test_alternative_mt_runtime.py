from __future__ import annotations

import json
from pathlib import Path

import pytest

from rocketdict import alternative_mt_runtime as runtime


def _write_asset(root: Path) -> Path:
    ct2 = root / "ct2"
    tokenizer = root / "tokenizer"
    ct2.mkdir(parents=True)
    tokenizer.mkdir(parents=True)
    (ct2 / "model.bin").write_bytes(b"ct2-model")
    for index, relative in enumerate(runtime.TC_BIG_TOKENIZER_FILES):
        (tokenizer / relative).write_bytes(f"tokenizer-{index}-{relative}".encode())
    (root / "SOURCE_README.md").write_text("license: cc-by-4.0\n", encoding="utf-8")
    tree = runtime._tree_identity(root)
    manifest = {
        "schema": runtime.TC_BIG_ASSET_SCHEMA,
        "repository": runtime.TC_BIG_REPOSITORY,
        "revision": runtime.TC_BIG_REVISION,
        "model_safetensors_sha256": runtime.TC_BIG_MODEL_SAFETENSORS_SHA256,
        "license": runtime.TC_BIG_LICENSE,
        "target_prefix": runtime.TC_BIG_TARGET_PREFIX,
        "ct2_model_dir": "ct2",
        "tokenizer_dir": "tokenizer",
        "compute_type": "float32",
        "payload_tree": tree,
    }
    path = root / runtime.TC_BIG_MANIFEST_NAME
    path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return path


def test_load_tc_big_asset_verifies_pinned_manifest_and_payload_tree(tmp_path: Path) -> None:
    manifest = _write_asset(tmp_path)
    asset = runtime.load_tc_big_asset(tmp_path)
    assert asset.repository == runtime.TC_BIG_REPOSITORY
    assert asset.revision == runtime.TC_BIG_REVISION
    assert asset.model_safetensors_sha256 == runtime.TC_BIG_MODEL_SAFETENSORS_SHA256
    assert asset.license == runtime.TC_BIG_LICENSE
    assert asset.ct2_model_dir == (tmp_path / "ct2").resolve()
    assert asset.tokenizer_dir == (tmp_path / "tokenizer").resolve()
    assert asset.manifest_sha256 == runtime._file_sha256(manifest)
    assert asset.payload_tree_sha256 == runtime._tree_identity(tmp_path)["sha256"]


def test_load_tc_big_asset_rejects_payload_mutation(tmp_path: Path) -> None:
    _write_asset(tmp_path)
    (tmp_path / "tokenizer" / "vocab.json").write_text("mutated", encoding="utf-8")
    with pytest.raises(RuntimeError, match="payload bytes changed"):
        runtime.load_tc_big_asset(tmp_path)


def test_load_tc_big_asset_rejects_identity_drift(tmp_path: Path) -> None:
    manifest = _write_asset(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["revision"] = "wrong"
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(RuntimeError, match="revision drift"):
        runtime.load_tc_big_asset(tmp_path)


def test_load_tc_big_asset_rejects_escaping_paths(tmp_path: Path) -> None:
    manifest = _write_asset(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["ct2_model_dir"] = "../escape"
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(RuntimeError, match="escapes asset root"):
        runtime.load_tc_big_asset(tmp_path)


def test_tc_big_status_is_fail_closed_without_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(runtime.TC_BIG_ASSET_ENV, raising=False)
    status = runtime.tc_big_status()
    assert status["available"] is False
    assert status["asset_configured"] is False
    assert status["offline"] is True
    assert status["compute_type"] == "float32"
    assert status["torch_required_for_inference"] is False


def test_translator_rejects_non_acceptance_device_and_compute() -> None:
    with pytest.raises(RuntimeError, match="requires float32"):
        runtime.TcBigTranslator(compute_type="int8")
    with pytest.raises(RuntimeError, match="pinned to CPU"):
        runtime.TcBigTranslator(device="cuda")
