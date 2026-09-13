from __future__ import annotations

from rocketdict.translation_tc_big_numeric_row_rules import (
    VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
    VARIANT_DENSE_FORMULA_MISSING,
    VARIANT_PROGRESSION_DUPLICATE,
    evaluate_tc_big_numeric_row_candidate,
    evaluate_tc_big_numeric_row_trigger,
)


def _row(source: str, target: str) -> dict[str, object]:
    return {
        "id": 1,
        "sequence_number": 0,
        "source_start": 0,
        "source_end": len(source),
        "source_text": source,
        "target_text": target,
        "payload": {
            "selected_rank": 0,
            "hypotheses": [{"rank": 0, "text": target, "score": -0.4}],
        },
    }


def _progression() -> tuple[str, str, str]:
    source = "The progression is 1, 3, 5, 7, 9, 11, &c. in the table."
    base = "Прогрессия равна 1, 3, 5, 7, 9, 11, 11, &c. в таблице."
    clean = "Прогрессия равна 1, 3, 5, 7, 9, 11, &c. в таблице."
    return source, base, clean


def _formula() -> tuple[str, str, str]:
    source = "The formula values 3/8A, 5/16A, 9A and 8A remain fixed in the table."
    base = "Значения формулы 3/8A, 5/16A и 9A остаются фиксированными в таблице."
    clean = "Значения формулы 3/8A, 5/16A, 9A и 8A остаются фиксированными в таблице."
    return source, base, clean


def _apostrophe_decimal() -> tuple[str, str, str]:
    source = "The measured values are 1'688, 2'389, 2'925, 3'375 inches in order."
    base = "Измеренные значения равны 1'688, 2'38, 2'925, 3'375 дюйма по порядку."
    clean = "Измеренные значения равны 1'688, 2'389, 2'925, 3'375 дюйма по порядку."
    return source, base, clean


def test_trigger_recognizes_three_neutral_source_defined_variants() -> None:
    expected = [
        (_progression(), VARIANT_PROGRESSION_DUPLICATE),
        (_formula(), VARIANT_DENSE_FORMULA_MISSING),
        (_apostrophe_decimal(), VARIANT_APOSTROPHE_DECIMAL_TRUNCATION),
    ]
    for (source, base, _clean), variant in expected:
        trigger = evaluate_tc_big_numeric_row_trigger(
            _row(source, base), source_exact=True
        )
        assert trigger["eligible"] is True, trigger
        assert trigger["variant"] == variant
        assert trigger["matched_variants"] == [variant]
        assert trigger["base_unique_rank0"] is True
        assert trigger["base_non_numeric_checks_clean"] is True
        assert trigger["prime_notation_clean"] is True
        assert trigger["critical_symbols_clean"] is True


def test_trigger_fails_closed_on_non_exact_non_rank0_and_near_miss_shapes() -> None:
    source, base, _ = _progression()
    assert evaluate_tc_big_numeric_row_trigger(
        _row(source, base), source_exact=False
    )["eligible"] is False

    non_rank0 = _row(source, base)
    non_rank0["payload"] = {
        "selected_rank": 1,
        "hypotheses": [{"rank": 1, "text": base}],
    }
    assert evaluate_tc_big_numeric_row_trigger(
        non_rank0, source_exact=True
    )["eligible"] is False

    short_source = "The progression is 1, 3, 5, &c. in the table."
    short_base = "Прогрессия равна 1, 3, 5, 5, &c. в таблице."
    short = evaluate_tc_big_numeric_row_trigger(
        _row(short_source, short_base), source_exact=True
    )
    assert short["eligible"] is False

    one_formula = "The formula 3/8A remains fixed and value 9 is shown."
    one_formula_base = "Формула 3/8A остается фиксированной, а значение не показано."
    assert evaluate_tc_big_numeric_row_trigger(
        _row(one_formula, one_formula_base), source_exact=True
    )["eligible"] is False

    two_decimals = "The values are 1'688 and 2'389 inches in order."
    two_decimals_base = "Значения равны 1'688 и 2'38 дюйма по порядку."
    assert evaluate_tc_big_numeric_row_trigger(
        _row(two_decimals, two_decimals_base), source_exact=True
    )["eligible"] is False


def test_candidate_accepts_clean_rank0_for_each_variant() -> None:
    cases = [
        (_progression(), VARIANT_PROGRESSION_DUPLICATE),
        (_formula(), VARIANT_DENSE_FORMULA_MISSING),
        (_apostrophe_decimal(), VARIANT_APOSTROPHE_DECIMAL_TRUNCATION),
    ]
    for (source, base, clean), variant in cases:
        result = evaluate_tc_big_numeric_row_candidate(
            source,
            clean,
            base_target=base,
            variant=variant,
        )
        assert result["accepted"] is True, result
        assert result["strictly_eligible"] is True
        assert result["emphasis_markup"]["passed"] is True
        assert result["hard_punctuation_exact"] is True
        assert result["variant_notation_preserved"] is True
        assert result["base_alpha_retention_ratio"] >= 0.95


def test_candidate_rejects_notation_loss_even_when_numeric_value_can_be_equivalent() -> None:
    source, base, _clean = _progression()
    no_etc = "Прогрессия равна 1, 3, 5, 7, 9, 11 в таблице."
    result = evaluate_tc_big_numeric_row_candidate(
        source,
        no_etc,
        base_target=base,
        variant=VARIANT_PROGRESSION_DUPLICATE,
    )
    assert result["variant_notation_preserved"] is False
    assert result["accepted"] is False

    source, base, _clean = _apostrophe_decimal()
    reformatted = "Измеренные значения равны 1.688, 2.389, 2.925, 3.375 дюйма по порядку."
    result = evaluate_tc_big_numeric_row_candidate(
        source,
        reformatted,
        base_target=base,
        variant=VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
    )
    assert result["variant_notation_preserved"] is False
    assert result["accepted"] is False


def test_candidate_rejects_formula_token_loss_and_emphasis_loss() -> None:
    source, base, clean = _formula()
    changed_formula = clean.replace("8A", "8")
    result = evaluate_tc_big_numeric_row_candidate(
        source,
        changed_formula,
        base_target=base,
        variant=VARIANT_DENSE_FORMULA_MISSING,
    )
    assert result["variant_notation_preserved"] is False
    assert result["accepted"] is False

    emphasized_source = "The _measured_ values are 1'688, 2'389, 2'925, 3'375 inches."
    emphasized_base = "Измеренные значения равны 1'688, 2'38, 2'925, 3'375 дюйма."
    missing_emphasis = "Измеренные значения равны 1'688, 2'389, 2'925, 3'375 дюйма."
    result = evaluate_tc_big_numeric_row_candidate(
        emphasized_source,
        missing_emphasis,
        base_target=emphasized_base,
        variant=VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
    )
    assert result["emphasis_markup"]["passed"] is False
    assert result["accepted"] is False
