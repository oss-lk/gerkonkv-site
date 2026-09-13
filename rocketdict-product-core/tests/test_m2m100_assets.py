from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from rocketdict import m2m100_assets as assets
from rocketdict import m2m100_runtime as runtime


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(root: Path) -> dict[str, str]:
    root.mkdir(parents=True)
    payloads = {
        "config.json": json.dumps(
            {"model_type": "m2m_100", "max_position_embeddings": 1024},
            sort_keys=True,
        ).encode(),
        "pytorch_model.bin": b"fake-m2m100-weights",
        "sentencepiece.bpe.model": b"fake-spm",
        "special_tokens_map.json": b"{}",
        "tokenizer_config.json": b"{}",
        "vocab.json": b"{}",
    }
    for relative, payload in payloads.items():
        (root / relative).write_bytes(payload)
    return {relative: _sha(root / relative) for relative in payloads}


def test_verify_snapshot_requires_pinned_bytes_and_model_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    expected = _snapshot(source)
    monkeypatch.setattr(assets, "PINNED_SOURCE_FILES", expected)
    rows = assets._verify_snapshot(source)
    assert {row["path"] for row in rows} == set(expected)

    (source / "vocab.json").write_text("mutated", encoding="utf-8")
    with pytest.raises(RuntimeError, match="identity drift"):
        assets._verify_snapshot(source)


def test_verify_snapshot_rejects_wrong_model_type_and_context_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    expected = _snapshot(source)
    config_path = source / "config.json"
    config = json.loads(config_path.read_text())
    config["model_type"] = "wrong"
    config_path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
    expected["config.json"] = _sha(config_path)
    monkeypatch.setattr(assets, "PINNED_SOURCE_FILES", expected)
    with pytest.raises(RuntimeError, match="model_type drift"):
        assets._verify_snapshot(source)

    config["model_type"] = "m2m_100"
    config["max_position_embeddings"] = 512
    config_path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
    expected["config.json"] = _sha(config_path)
    with pytest.raises(RuntimeError, match="max_position_embeddings drift"):
        assets._verify_snapshot(source)


def test_build_m2m100_asset_is_offline_float32_and_manifested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    expected = _snapshot(source)
    monkeypatch.setattr(assets, "PINNED_SOURCE_FILES", expected)
    destination = tmp_path / "asset"

    observed: dict[str, object] = {}

    class FakeConverter:
        def __init__(self, model: str) -> None:
            observed["model"] = model

        def convert(self, destination_path: str, *, quantization: str, force: bool) -> None:
            observed["quantization"] = quantization
            observed["force"] = force
            root = Path(destination_path)
            root.mkdir(parents=True, exist_ok=True)
            (root / "model.bin").write_bytes(b"converted")
            (root / "config.json").write_text("{}", encoding="utf-8")

    fake_ct2 = SimpleNamespace(
        __version__="4.8.2",
        converters=SimpleNamespace(TransformersConverter=FakeConverter),
    )
    monkeypatch.setitem(sys.modules, "ctranslate2", fake_ct2)
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace())

    result = assets.build_m2m100_asset(source, destination)
    assert result["status"] == "completed"
    assert result["network_used_by_builder"] is False
    assert result["repository"] == runtime.M2M100_REPOSITORY
    assert result["revision"] == runtime.M2M100_REVISION
    assert observed == {
        "model": str(source.resolve()),
        "quantization": "float32",
        "force": True,
    }
    manifest = json.loads(
        (destination / runtime.M2M100_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["schema"] == runtime.M2M100_ASSET_SCHEMA
    assert manifest["compute_type"] == "float32"
    assert manifest["source_language"] == "en"
    assert manifest["target_language"] == "ru"
    assert manifest["converter"]["ctranslate2_version"] == "4.8.2"
    assert manifest["payload_tree"]["sha256"] == runtime._tree_identity(destination)["sha256"]
    assert (destination / "ct2" / "model.bin").is_file()
    for relative in runtime.M2M100_TOKENIZER_FILES:
        assert (destination / "tokenizer" / relative).is_file()


def test_build_refuses_nonempty_destination_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    expected = _snapshot(source)
    monkeypatch.setattr(assets, "PINNED_SOURCE_FILES", expected)
    destination = tmp_path / "asset"
    destination.mkdir()
    (destination / "existing").write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Destination is not empty"):
        assets.build_m2m100_asset(source, destination)
