from __future__ import annotations

import pytest

from rocketdict.emphasis_markup import (
    EMPHASIS_MARKUP_CONTRACT,
    compare_emphasis_markup_preservation,
)


def test_translated_emphasis_payload_preserves_markup_shape() -> None:
    result = compare_emphasis_markup_preservation(
        "Salt of Tartar _per deliquium_ becomes fluid.",
        "Соль Тартара _при расплывании_ становится жидкой.",
    )
    assert result["contract"] == EMPHASIS_MARKUP_CONTRACT
    assert result["passed"] is True
    assert result["source"]["underscore_count"] == 2
    assert result["target"]["underscore_count"] == 2
    assert result["source"]["complete_span_count"] == 1
    assert result["target"]["complete_span_count"] == 1


def test_dropped_linguistic_emphasis_is_visible() -> None:
    result = compare_emphasis_markup_preservation(
        "Salt of Tartar _per deliquium_ becomes fluid.",
        "Соль Тартара становится жидкой.",
    )
    assert result["passed"] is False
    assert result["failed_checks"] == ["underscore_count", "complete_span_count"]
    assert result["source"]["spans"][0]["payload"] == "per deliquium"
    assert result["target"]["spans"] == []


def test_target_only_emphasis_is_visible() -> None:
    result = compare_emphasis_markup_preservation(
        "plain source",
        "_перевод_",
    )
    assert result["passed"] is False
    assert result["failed_checks"] == ["underscore_count", "complete_span_count"]


def test_unbalanced_source_markup_must_remain_unbalanced_shape() -> None:
    preserved = compare_emphasis_markup_preservation(
        "an unmatched _marker",
        "несогласованный _маркер",
    )
    assert preserved["passed"] is True
    assert preserved["source"]["balanced"] is False
    assert preserved["target"]["balanced"] is False

    silently_repaired = compare_emphasis_markup_preservation(
        "an unmatched _marker",
        "несогласованный _маркер_",
    )
    assert silently_repaired["passed"] is False
    assert "underscore_count" in silently_repaired["failed_checks"]
    assert "complete_span_count" in silently_repaired["failed_checks"]
    assert "balanced_state" in silently_repaired["failed_checks"]


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("_q_ and _r_", "_q_ и _r_"),
        ("no emphasis here", "здесь нет выделения"),
        ("_long ordinary phrase_", "_обычная длинная фраза_"),
    ],
)
def test_markup_shape_only_does_not_require_payload_identity(
    source: str, target: str
) -> None:
    assert compare_emphasis_markup_preservation(source, target)["passed"] is True
