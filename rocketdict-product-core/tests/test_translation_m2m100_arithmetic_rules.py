from __future__ import annotations

from rocketdict.translation_m2m100_arithmetic_rules import (
    M2M100_ARITHMETIC_SELECTOR_CONTRACT,
    M2M100_ARITHMETIC_TRIGGER_CONTRACT,
    evaluate_m2m100_arithmetic_candidate,
    evaluate_m2m100_arithmetic_trigger,
    parse_source_arithmetic_restatement,
)


def _row(source: str, target: str) -> dict[str, object]:
    return {
        "id": 1,
        "sequence_number": 0,
        "source_start": 0,
        "source_end": len(source),
        "source_text": source,
        "target_text": target,
        "payload": {},
    }


def test_parser_requires_one_exact_verified_arithmetic_restatement_and_only_its_literals() -> None:
    source = "The ratio is above 12 x 12 (that is, above 144) times the base."
    parsed = parse_source_arithmetic_restatement(source)
    assert parsed is not None
    assert parsed["a"] == 12
    assert parsed["b"] == 12
    assert parsed["c"] == 144
    assert parsed["product"] == 144
    assert parsed["arithmetic_verified"] is True
    assert parsed["numeric_sequence"] == ["12", "12", "144"]

    wrong = "The ratio is above 12 x 12 (that is, above 145) times the base."
    parsed_wrong = parse_source_arithmetic_restatement(wrong)
    assert parsed_wrong is not None
    assert parsed_wrong["arithmetic_verified"] is False

    extra = "At 2 trials, the ratio is above 12 x 12 (that is, above 144) times the base."
    assert parse_source_arithmetic_restatement(extra) is None

    doubled = source + " Again 3 x 3 (that is, above 9)."
    assert parse_source_arithmetic_restatement(doubled) is None


def test_trigger_accepts_only_exact_source_verified_result_corruption() -> None:
    source = "The force is above 700000 x 700000 (that is, above 490,000,000,000) times greater."
    broken = "Сила выше 700000 x 700 000 (то есть выше 490 000 000 000 000) раз больше."
    trigger = evaluate_m2m100_arithmetic_trigger(_row(source, broken), source_exact=True)
    assert trigger["contract"] == M2M100_ARITHMETIC_TRIGGER_CONTRACT
    assert trigger["eligible"] is True
    assert trigger["source_arithmetic_verified"] is True
    assert trigger["current_numeric_result_corruption_shape"] is True
    assert trigger["non_numeric_hard_and_structural_checks_clean"] is True

    assert evaluate_m2m100_arithmetic_trigger(
        _row(source, broken), source_exact=False
    )["eligible"] is False

    clean = "Сила выше 700000 x 700 000 (то есть выше 490 000 000 000) раз больше."
    assert evaluate_m2m100_arithmetic_trigger(
        _row(source, clean), source_exact=True
    )["eligible"] is False

    wrong_source = "The force is above 700000 x 700000 (that is, above 491,000,000,000) times greater."
    wrong_target = "Сила выше 700000 x 700000 (то есть выше 491 000 000 000 000) раз больше."
    assert evaluate_m2m100_arithmetic_trigger(
        _row(wrong_source, wrong_target), source_exact=True
    )["eligible"] is False


def test_trigger_rejects_other_hard_debt_and_wrong_corruption_shape() -> None:
    source = "The force is above 12 x 12 (that is, above 144) times greater?"
    missing_question = "Сила выше 12 x 12 (то есть выше 145) раз больше."
    trigger = evaluate_m2m100_arithmetic_trigger(
        _row(source, missing_question), source_exact=True
    )
    assert trigger["non_numeric_hard_and_structural_checks_clean"] is False
    assert trigger["eligible"] is False

    ordinary_source = "The force is above 12 x 12 (that is, above 144) times greater."
    duplicate = "Сила выше 12 x 12 (то есть выше 144 и 144) раз больше."
    trigger = evaluate_m2m100_arithmetic_trigger(
        _row(ordinary_source, duplicate), source_exact=True
    )
    assert trigger["current_numeric_result_corruption_shape"] is False
    assert trigger["eligible"] is False


def test_candidate_requires_current_strict_gates_emphasis_volume_and_arithmetic_notation() -> None:
    source = "The _force_ is above 12 x 12 (that is, above 144) times greater."
    base = "_Сила_ выше 12 x 12 (то есть выше 145) раз больше."
    restatement = parse_source_arithmetic_restatement(source)
    assert restatement is not None
    clean = "_Сила_ выше 12 x 12 (то есть выше 144) раз больше."
    selection = evaluate_m2m100_arithmetic_candidate(
        source, clean, base_target=base, restatement=restatement
    )
    assert selection["selector_contract"] == M2M100_ARITHMETIC_SELECTOR_CONTRACT
    assert selection["accepted"] is True
    assert selection["arithmetic_notation"]["numeric_sequence_exact"] is True
    assert selection["arithmetic_notation"]["multiplication_operator_preserved"] is True
    assert selection["emphasis_markup"]["passed"] is True
    assert selection["hard_punctuation_exact"] is True

    no_operator = "_Сила_ выше 12 на 12 (то есть выше 144) раз больше."
    selection = evaluate_m2m100_arithmetic_candidate(
        source, no_operator, base_target=base, restatement=restatement
    )
    assert selection["arithmetic_notation"]["multiplication_operator_preserved"] is False
    assert selection["accepted"] is False

    no_emphasis = "Сила выше 12 x 12 (то есть выше 144) раз больше."
    selection = evaluate_m2m100_arithmetic_candidate(
        source, no_emphasis, base_target=base, restatement=restatement
    )
    assert selection["emphasis_markup"]["passed"] is False
    assert selection["accepted"] is False

    compressed = "_Сила_ 12 x 12 (144)."
    selection = evaluate_m2m100_arithmetic_candidate(
        source, compressed, base_target=base, restatement=restatement
    )
    assert (
        selection["source_alpha_ratio_passed"] is False
        or selection["base_alpha_retention_passed"] is False
        or selection["strictly_eligible"] is False
    )
    assert selection["accepted"] is False


def test_real_proven_geometry_is_source_defined_and_candidate_clean() -> None:
    source = (
        "And therefore the elastick force of this\n"
        "Medium, in proportion to its density, must be above 700000 x 700000\n"
        "(that is, above 490,000,000,000) times greater than the elastick force\n"
        "of the Air is in proportion to its density. "
    )
    base = (
        "Таким образом, эластичная сила этого Среднего, пропорциональная его плотности, "
        "должна быть более 700000 х 700 000 (т.е. более 490 000 000 000 000) в раз больше, "
        "чем эластичная сила воздуха пропорционально его плотности."
    )
    candidate = (
        "И поэтому эластичная сила этого Среднего, в пропорции к его плотности, должна быть "
        "выше 700 000 x 700 000 (то есть выше 490 000 000 000) раз больше, чем эластичная "
        "сила воздуха в пропорции к его плотности."
    )
    trigger = evaluate_m2m100_arithmetic_trigger(_row(source, base), source_exact=True)
    assert trigger["eligible"] is True
    restatement = trigger["source_restatement"]
    assert isinstance(restatement, dict)
    selection = evaluate_m2m100_arithmetic_candidate(
        source, candidate, base_target=base, restatement=restatement
    )
    assert selection["accepted"] is True
    assert selection["mechanical_verdict"]["strictly_eligible"] is True
