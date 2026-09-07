from __future__ import annotations

import pytest

from rocketdict.research_diagnostics import (
    CRITICAL_TOKEN_CONTRACT,
    DELIMITER_CONTRACT,
    NUMERIC_ORDER_CONTRACT,
    OUTPUT_ARTIFACT_CONTRACT,
    compare_critical_technical_tokens,
    compare_delimiter_preservation,
    compare_numeric_order,
    compare_output_artifacts,
)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (
            "100 Foot, 4 Inches, 961/72000000 parts",
            "100 футов, 4 дюйма, 961/72000 000 частей",
        ),
        (
            "1/178000, 3/178000, 11/178000",
            "1/178000, 3/178000, 11/178 000",
        ),
        (
            "1'688, 2'389, 2'925",
            "1'688, 2'389, 2'925",
        ),
        (
            "42 then 50",
            "POF - 42, затем POG - 50",
        ),
    ],
)
def test_numeric_order_uses_maintained_numeric_equivalences(source: str, target: str) -> None:
    result = compare_numeric_order(source, target)
    assert result["contract"] == NUMERIC_ORDER_CONTRACT
    assert result["passed"] is True
    assert result["matched_required_count"] == result["required_count"]


def test_numeric_order_keeps_real_loss_visible() -> None:
    result = compare_numeric_order(
        "1'688, 2'389, 2'925",
        "1'688, 2'38, 2'925",
    )
    assert result["passed"] is False
    assert result["required_sequence"] == ["1.688", "2.389", "2.925"]
    assert result["observed_primary_sequence"] == ["1.688", "2.38", "2.925"]
    assert result["matched_required_count"] == 1


def test_numeric_order_is_order_sensitive_even_when_values_exist() -> None:
    result = compare_numeric_order("1 2 3", "1 3 2")
    assert result["passed"] is False
    assert result["required_sequence"] == ["1", "2", "3"]


def test_balanced_delimiters_require_exact_counts() -> None:
    assert compare_delimiter_preservation("[Greek: x] (note)", "[Greek: x] (прим.)")["passed"] is True
    result = compare_delimiter_preservation("[Greek: x]", "Greek: x")
    assert result["passed"] is False
    assert result["delimiters"]["square"]["exactly_preserved"] is False


def test_unbalanced_source_is_preserved_not_synthetically_repaired() -> None:
    preserved = compare_delimiter_preservation("_Boyle_) as when", "_Boyle_) как когда")
    assert preserved["contract"] == DELIMITER_CONTRACT
    assert preserved["passed"] is True
    assert preserved["source_was_balanced"] is False
    assert preserved["source_unbalanced_kinds"] == ["round"]

    fabricated = compare_delimiter_preservation("_Boyle_) as when", "(_Boyle_) как когда")
    assert fabricated["passed"] is False
    assert fabricated["delimiters"]["round"]["source"] == [0, 1]
    assert fabricated["delimiters"]["round"]["target"] == [1, 1]


def test_target_added_balanced_pair_still_fails() -> None:
    result = compare_delimiter_preservation("Lectiones Opticae", "(Lectiones Opticae)")
    assert result["passed"] is False
    assert result["source_was_balanced"] is True


def test_critical_technical_tokens_accept_preserved_payloads_and_localized_labels() -> None:
    source = "[Illustration: FIG. 1.] [Greek: ab] _q_ [C] 1.F.4."
    target = "[Иллюстрация: FIG. 1.] [греческом: ab] _q_ [C] 1.F.4."
    result = compare_critical_technical_tokens(source, target)
    assert result["contract"] == CRITICAL_TOKEN_CONTRACT
    assert result["passed"] is True
    assert result["failed_checks"] == []


@pytest.mark.parametrize(
    ("source", "target", "failed"),
    [
        ("They are [Greek: letter].", "Они обозначены буквой.", "greek_payloads"),
        ("Point _q_ remains.", "Точка q_ остаётся.", "symbolic_emphasis"),
        ("See note [C].", "См. примечание [С].", "footnote_markers"),
        ("[Illustration: FIG. 2.]", "[Иллюстрация: FIG.]", "illustration_payloads"),
        ("Section 1.F.4.", "Раздел 1.F.4", "structural_identifiers"),
    ],
)
def test_critical_technical_tokens_keep_real_corruption_visible(
    source: str, target: str, failed: str
) -> None:
    result = compare_critical_technical_tokens(source, target)
    assert result["passed"] is False
    assert failed in result["failed_checks"]


def test_output_artifact_diagnostic_rejects_target_only_html_entities() -> None:
    result = compare_output_artifacts("green-making", "&quot; зелёный &quot;")
    assert result["contract"] == OUTPUT_ARTIFACT_CONTRACT
    assert result["passed"] is False
    assert result["introduced_entities"] == {"&quot;": 2}


def test_output_artifact_diagnostic_licenses_entities_already_present_in_source() -> None:
    result = compare_output_artifacts("literal &quot; token", "буквальный &quot; token")
    assert result["passed"] is True
    assert result["introduced_entities"] == {}


def test_output_artifact_diagnostic_rejects_new_replacement_character() -> None:
    result = compare_output_artifacts("plain source", "испорчено �")
    assert result["passed"] is False
    assert result["introduced_replacement_character_count"] == 1


def test_output_artifact_diagnostic_rejects_target_only_quote_delimiters() -> None:
    result = compare_output_artifacts(
        "the Sines of the red-making Rays",
        '"Синусы красного производства"',
    )
    assert result["contract"] == OUTPUT_ARTIFACT_CONTRACT
    assert result["passed"] is False
    assert result["source_quote_delimiter_count"] == 0
    assert result["target_quote_delimiter_count"] == 2
    assert result["introduced_quote_delimiter_count"] == 2


def test_output_artifact_diagnostic_allows_quote_style_substitution() -> None:
    result = compare_output_artifacts('"quoted title"', "«переведённое название»")
    assert result["passed"] is True
    assert result["source_quote_delimiter_count"] == 2
    assert result["target_quote_delimiter_count"] == 2
    assert result["introduced_quote_delimiter_count"] == 0
