from __future__ import annotations

from rocketdict.numeric_integrity import (
    CONTRACT,
    compare_numeric_integrity,
    spelled_numeric_licenses,
)


def test_compound_hundred_thousand_licenses_exact_multiplicative_value() -> None:
    source = "divided into ten hundred thousand equal parts"
    assert CONTRACT == "rocketdict-maintained-numeric-integrity/6"
    assert spelled_numeric_licenses(source) == {"1000000": 1}
    assert compare_numeric_integrity(source, "разделено на 1,000,000 равных частей")["passed"] is True


def test_compound_hundred_thousand_rejects_component_and_truncated_values() -> None:
    source = "divided into ten hundred thousand equal parts"
    for target in (
        "разделено на 10 равных частей",
        "разделено на 100 равных частей",
        "разделено на 100,000 равных частей",
    ):
        result = compare_numeric_integrity(source, target)
        assert result["passed"] is False
        assert result["unlicensed_additions"]


def test_repeated_and_ordinal_thousand_scales_are_composed() -> None:
    assert spelled_numeric_licenses("above an hundred thousand thousand times") == {
        "100000000": 1
    }
    assert spelled_numeric_licenses("the ten hundred thousandth Part") == {"1000000": 1}
    assert compare_numeric_integrity(
        "the ten hundred thousandth Part",
        "1,000,000-я часть",
    )["passed"] is True


def test_compound_scale_parser_does_not_cross_coordinators() -> None:
    # These historical/range-like constructions are deliberately left to the
    # former fail-closed per-word semantics rather than collapsed greedily.
    assert spelled_numeric_licenses("between two and three hundred times") == {
        "2": 1,
        "3": 1,
        "100": 1,
    }
    assert spelled_numeric_licenses("three or four thousand times") == {
        "3": 1,
        "4": 1,
    }
