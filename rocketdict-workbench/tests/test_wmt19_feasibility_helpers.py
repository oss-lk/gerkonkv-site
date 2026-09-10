from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).with_name("real_translation_full_opticks_wmt19_feasibility.py")
SPEC = importlib.util.spec_from_file_location("rocketdict_wmt19_feasibility_helpers", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load WMT19 feasibility helper")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _model(*, generation_eos=2, config_eos=2, generation_pad=1, config_pad=1):
    return SimpleNamespace(
        generation_config=SimpleNamespace(
            eos_token_id=generation_eos,
            pad_token_id=generation_pad,
        ),
        config=SimpleNamespace(
            eos_token_id=config_eos,
            pad_token_id=config_pad,
        ),
    )


def test_eos_falls_back_to_model_when_fsmt_tokenizer_does_not_publish_it() -> None:
    tokenizer = SimpleNamespace(eos_token_id=None, pad_token_id=1)
    model = _model()

    assert MODULE.resolve_special_token_id(
        "eos_token_id", tokenizer=tokenizer, model=model
    ) == 2
    assert MODULE.resolve_special_token_id(
        "pad_token_id", tokenizer=tokenizer, model=model
    ) == 1


def test_singleton_generation_token_list_is_accepted() -> None:
    tokenizer = SimpleNamespace(eos_token_id=None, pad_token_id=1)
    model = _model(generation_eos=[2])

    assert MODULE.resolve_special_token_id(
        "eos_token_id", tokenizer=tokenizer, model=model
    ) == 2


def test_conflicting_runtime_special_token_ids_fail_closed() -> None:
    tokenizer = SimpleNamespace(eos_token_id=None, pad_token_id=1)
    model = _model(generation_eos=2, config_eos=3)

    with pytest.raises(RuntimeError, match="disagreement"):
        MODULE.resolve_special_token_id(
            "eos_token_id", tokenizer=tokenizer, model=model
        )
