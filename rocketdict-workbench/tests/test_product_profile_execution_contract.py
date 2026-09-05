from __future__ import annotations

import pytest

from rocketdict_workbench.product_policy import ProductPolicyError
from rocketdict_workbench.product_profile import _select_named_or_product


def _manifest(*, stage_inputs=..., implementation_inputs=...) -> dict:  # type: ignore[no-untyped-def]
    stage = {
        "number": 8,
        "key": "nlp_analysis",
        "implementations": [
            {
                "implementation_key": "en-sm",
                "production_eligible": True,
                "testing_only": False,
                "availability": {"available": True},
                "descriptor_hash": "d" * 64,
                "controls": [],
                "tags": [],
            }
        ],
    }
    if stage_inputs is not ...:
        stage["required_inputs"] = stage_inputs
    if implementation_inputs is not ...:
        stage["implementations"][0]["required_inputs"] = implementation_inputs
    return {"stages": [stage]}


def test_product_profile_prefers_implementation_execution_contract() -> None:
    row = _select_named_or_product(
        _manifest(stage_inputs=["historical_stage_input"], implementation_inputs=["document_version_id"]),
        8,
        source_kind="text",
    )
    assert row["required_inputs"] == ["document_version_id"]


def test_product_profile_accepts_explicit_stage_execution_contract() -> None:
    row = _select_named_or_product(
        _manifest(stage_inputs=["document_version_id"]),
        8,
        source_kind="text",
    )
    assert row["required_inputs"] == ["document_version_id"]


def test_product_profile_preserves_missing_execution_contract_as_unknown() -> None:
    row = _select_named_or_product(_manifest(), 8, source_kind="text")
    assert row["required_inputs"] is None


def test_product_profile_rejects_invalid_execution_contract() -> None:
    with pytest.raises(ProductPolicyError, match="invalid required_inputs"):
        _select_named_or_product(
            _manifest(implementation_inputs="document_version_id"),
            8,
            source_kind="text",
        )
