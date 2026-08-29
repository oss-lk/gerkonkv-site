import pytest

from rocketdict_workbench.product_policy import ProductPolicyError, select_product_implementation, validate_product_configuration


def _impl(key: str, *, available: bool, tags=()):
    return {
        "implementation_key": key,
        "production_eligible": True,
        "testing_only": False,
        "availability": {"available": available},
        "tags": list(tags),
        "label": key,
    }


def test_product_nlp_does_not_fall_back_to_code_only() -> None:
    stage = {
        "number": 8,
        "key": "nlp_analysis",
        "implementations": [
            _impl("nltk-treebank-punkt-en", available=True, tags=("code-only",)),
            _impl("stanza-full-en", available=False),
        ],
    }
    with pytest.raises(ProductPolicyError):
        select_product_implementation(stage, require_available=True)
    selected = select_product_implementation(stage, require_available=False)
    assert selected.implementation_key == "stanza-full-en"


def test_product_prefers_opus_translation() -> None:
    stage = {
        "number": 12,
        "key": "translation_baseline",
        "implementations": [
            _impl("m2m100-1.2b-en-ru-ct2", available=True),
            _impl("opus-en-ru-ct2", available=True),
        ],
    }
    assert select_product_implementation(stage, require_available=True).implementation_key == "opus-en-ru-ct2"


def test_validate_rejects_code_only_final_dictionary() -> None:
    manifest = {
        "stages": [
            {"number": 8, "key": "nlp_analysis", "implementations": [_impl("nltk-treebank-punkt-en", available=True, tags=("code-only",))]},
            {"number": 12, "key": "translation_baseline", "implementations": [_impl("opus-en-ru-ct2", available=True)]},
        ]
    }
    config = {
        "stages": [
            {"stage_number": 8, "enabled": True, "implementation": "nltk-treebank-punkt-en"},
            {"stage_number": 12, "enabled": True, "implementation": "opus-en-ru-ct2"},
        ]
    }
    with pytest.raises(ProductPolicyError):
        validate_product_configuration(config, manifest)
