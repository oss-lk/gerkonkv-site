from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from rocketdict import m2m100_runtime as runtime


def _write_asset(root: Path) -> Path:
    ct2 = root / "ct2"
    tokenizer = root / "tokenizer"
    ct2.mkdir(parents=True)
    tokenizer.mkdir(parents=True)
    (ct2 / "model.bin").write_bytes(b"ct2-model")
    for index, relative in enumerate(runtime.M2M100_TOKENIZER_FILES):
        (tokenizer / relative).write_bytes(f"tokenizer-{index}-{relative}".encode())
    (root / "SOURCE_PROVENANCE.json").write_text("{}\n", encoding="utf-8")
    tree = runtime._tree_identity(root)
    manifest = {
        "schema": runtime.M2M100_ASSET_SCHEMA,
        "repository": runtime.M2M100_REPOSITORY,
        "revision": runtime.M2M100_REVISION,
        "model_sha256": runtime.M2M100_MODEL_SHA256,
        "license": runtime.M2M100_LICENSE,
        "source_language": runtime.M2M100_SOURCE_LANGUAGE,
        "target_language": runtime.M2M100_TARGET_LANGUAGE,
        "ct2_model_dir": "ct2",
        "tokenizer_dir": "tokenizer",
        "compute_type": "float32",
        "payload_tree": tree,
    }
    path = root / runtime.M2M100_MANIFEST_NAME
    path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return path


def test_load_m2m100_asset_verifies_manifest_and_payload_tree(tmp_path: Path) -> None:
    manifest = _write_asset(tmp_path)
    asset = runtime.load_m2m100_asset(tmp_path)
    assert asset.repository == runtime.M2M100_REPOSITORY
    assert asset.revision == runtime.M2M100_REVISION
    assert asset.model_sha256 == runtime.M2M100_MODEL_SHA256
    assert asset.license == runtime.M2M100_LICENSE
    assert asset.source_language == "en"
    assert asset.target_language == "ru"
    assert asset.ct2_model_dir == (tmp_path / "ct2").resolve()
    assert asset.tokenizer_dir == (tmp_path / "tokenizer").resolve()
    assert asset.manifest_sha256 == runtime._file_sha256(manifest)
    assert asset.payload_tree_sha256 == runtime._tree_identity(tmp_path)["sha256"]


def test_m2m100_status_persists_exact_asset_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _write_asset(tmp_path)
    observed_tree = runtime._tree_identity(tmp_path)
    monkeypatch.setenv(runtime.M2M100_ASSET_ENV, str(tmp_path))
    status = runtime.m2m100_status()
    assert status["asset_configured"] is True
    assert status["asset_error"] is None
    assert status["asset_manifest_sha256"] == runtime._file_sha256(manifest)
    assert status["asset_payload_tree_sha256"] == observed_tree["sha256"]
    assert status["repository"] == runtime.M2M100_REPOSITORY
    assert status["revision"] == runtime.M2M100_REVISION
    assert status["model_sha256"] == runtime.M2M100_MODEL_SHA256
    assert status["source_language"] == "en"
    assert status["target_language"] == "ru"
    assert status["torch_required_for_inference"] is False


def test_load_m2m100_asset_rejects_payload_mutation(tmp_path: Path) -> None:
    _write_asset(tmp_path)
    (tmp_path / "tokenizer" / "vocab.json").write_text("mutated", encoding="utf-8")
    with pytest.raises(RuntimeError, match="payload bytes changed"):
        runtime.load_m2m100_asset(tmp_path)


def test_load_m2m100_asset_rejects_identity_and_path_drift(tmp_path: Path) -> None:
    manifest = _write_asset(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["revision"] = "wrong"
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(RuntimeError, match="revision drift"):
        runtime.load_m2m100_asset(tmp_path)

    manifest = _write_asset(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["ct2_model_dir"] = "../escape"
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(RuntimeError, match="escapes asset root"):
        runtime.load_m2m100_asset(tmp_path)


def test_m2m100_status_fails_closed_without_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(runtime.M2M100_ASSET_ENV, raising=False)
    status = runtime.m2m100_status()
    assert status["available"] is False
    assert status["asset_configured"] is False
    assert status["offline"] is True
    assert status["compute_type"] == "float32"
    assert status["torch_required_for_inference"] is False


def test_translator_rejects_non_acceptance_device_and_compute() -> None:
    with pytest.raises(RuntimeError, match="requires float32"):
        runtime.M2M100Translator(compute_type="int8")
    with pytest.raises(RuntimeError, match="pinned to CPU"):
        runtime.M2M100Translator(device="cuda")


def test_translate_forces_russian_prefix_and_strips_it_before_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_asset(tmp_path)
    monkeypatch.setenv(runtime.M2M100_ASSET_ENV, str(tmp_path))
    monkeypatch.setattr(
        runtime,
        "m2m100_status",
        lambda: {"available": True},
    )

    observed: dict[str, object] = {}

    class FakeTokenizer:
        lang_code_to_token = {"ru": "__ru__"}
        src_lang = ""

        @classmethod
        def from_pretrained(cls, path: str, *, local_files_only: bool):
            assert path == str((tmp_path / "tokenizer").resolve())
            assert local_files_only is True
            return cls()

        def encode(self, text: str, *, add_special_tokens: bool):
            assert add_special_tokens is True
            observed["source"] = text
            return [10, 11, 2]

        def convert_ids_to_tokens(self, values):
            mapping = {10: "▁Hello", 11: "!", 2: "</s>", 20: "▁Привет", 21: "!"}
            return [mapping[value] for value in values]

        def convert_tokens_to_ids(self, values):
            mapping = {"▁Привет": 20, "!": 21}
            return [mapping[value] for value in values]

        def decode(self, values, *, skip_special_tokens: bool):
            assert values == [20, 21]
            assert skip_special_tokens is True
            return "Привет!"

    class FakeBackend:
        def __init__(self, path: str, *, device: str, compute_type: str):
            assert path == str((tmp_path / "ct2").resolve())
            assert device == "cpu"
            assert compute_type == "float32"

        def translate_batch(self, source, **kwargs):
            observed["encoded"] = source
            observed["kwargs"] = kwargs
            return [SimpleNamespace(hypotheses=[["__ru__", "▁Привет", "!"]], scores=[-0.25])]

    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace(Translator=FakeBackend))
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(M2M100Tokenizer=FakeTokenizer),
    )
    translator = runtime.M2M100Translator()
    result = translator.translate(["Hello!"], beam_size=5, num_hypotheses=1)
    assert result == [[{"rank": 0, "text": "Привет!", "tokens": ["__ru__", "▁Привет", "!"], "score": -0.25}]]
    assert observed["encoded"] == [["▁Hello", "!", "</s>"]]
    kwargs = observed["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["target_prefix"] == [["__ru__"]]
    assert kwargs["beam_size"] == 5
    assert kwargs["num_hypotheses"] == 1


def test_translate_rejects_backend_without_forced_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_asset(tmp_path)
    monkeypatch.setenv(runtime.M2M100_ASSET_ENV, str(tmp_path))
    monkeypatch.setattr(runtime, "m2m100_status", lambda: {"available": True})

    class FakeTokenizer:
        lang_code_to_token = {"ru": "__ru__"}
        src_lang = ""

        @classmethod
        def from_pretrained(cls, *_args, **_kwargs):
            return cls()

        def encode(self, *_args, **_kwargs):
            return [10]

        def convert_ids_to_tokens(self, values):
            return ["▁x" for _ in values]

    class FakeBackend:
        def __init__(self, *_args, **_kwargs):
            pass

        def translate_batch(self, *_args, **_kwargs):
            return [SimpleNamespace(hypotheses=[["▁wrong"]], scores=[0.0])]

    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace(Translator=FakeBackend))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(M2M100Tokenizer=FakeTokenizer))
    translator = runtime.M2M100Translator()
    with pytest.raises(RuntimeError, match="forced target prefix"):
        translator.translate(["x"])
