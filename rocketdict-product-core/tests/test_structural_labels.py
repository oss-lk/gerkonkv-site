from __future__ import annotations

from rocketdict.structural_labels import (
    SOURCE_EXPANSIONS,
    STRUCTURAL_LABEL_CONTRACT,
    TARGET_TERMS,
    detect_structural_labels,
    evaluate_structural_label_hypotheses,
    parse_structural_label_unit,
)


def test_block_detection_excludes_inline_parenthetical_label() -> None:
    text = (
        "Previous paragraph.\n\n"
        "_Exper._ 11. Following text.\n"
        "Inline (_Exper._ 10. _Part_ 2.) remains prose.\n\n"
        "_Qu._ 3. Question text."
    )
    all_labels = detect_structural_labels(text)
    block_labels = detect_structural_labels(text, block_only=True)

    assert [(row.kind, row.number) for row in all_labels] == [
        ("exper", "11"),
        ("exper", "10"),
        ("qu", "3"),
    ]
    assert [(row.kind, row.number) for row in block_labels] == [
        ("exper", "11"),
        ("qu", "3"),
    ]
    assert block_labels[0].canonical_model_input == "Experiment 11."
    assert block_labels[1].canonical_model_input == "Query 3."


def test_parse_isolated_label_keeps_source_semantics_separate_from_model_input() -> None:
    label = parse_structural_label_unit("\n_Obs._ 6. \t")
    assert label.source_text == "_Obs._ 6."
    assert label.kind == "obs"
    assert label.number == "6"
    assert label.canonical_model_input == "Observation 6."
    assert SOURCE_EXPANSIONS[label.kind] == "Observation"
    assert TARGET_TERMS[label.kind] == "Наблюдение"


def test_candidate_selection_requires_exact_russian_heading_number_and_period() -> None:
    label = parse_structural_label_unit("_Exper._ 5.")
    result = evaluate_structural_label_hypotheses(
        label,
        [
            {"rank": 0, "score": -0.1, "text": "Эксперимент 5:"},
            {"rank": 1, "score": -0.2, "text": "Эксперимент 6."},
            {"rank": 2, "score": -0.3, "text": "Экспериментальный 5."},
            {"rank": 3, "score": -0.4, "text": "Эксперимент 5."},
        ],
    )
    assert result["contract"] == STRUCTURAL_LABEL_CONTRACT
    assert result["selected"] is not None
    assert result["selected"]["rank"] == 3
    assert result["selected"]["target_text"] == "Эксперимент 5."
    assert [row["acceptable"] for row in result["candidates"]] == [
        False,
        False,
        False,
        True,
    ]


def test_observation_one_can_be_selected_from_later_raw_rank() -> None:
    label = parse_structural_label_unit("_Obs._ 1.")
    result = evaluate_structural_label_hypotheses(
        label,
        [
            {"rank": 0, "text": "Замечание 1."},
            {"rank": 1, "text": "Примечание 1."},
            {"rank": 5, "text": "Наблюдение 1."},
        ],
    )
    assert result["selected"] is not None
    assert result["selected"]["rank"] == 5
    assert result["selected"]["numeric_integrity"]["passed"] is True


def test_wrong_or_missing_numeric_identity_is_never_accepted() -> None:
    label = parse_structural_label_unit("_Qu._ 10.")
    result = evaluate_structural_label_hypotheses(
        label,
        [
            {"rank": 0, "text": "Вопрос."},
            {"rank": 1, "text": "Вопрос 11."},
            {"rank": 2, "text": "Вопрос 10."},
        ],
    )
    assert result["selected"] is not None
    assert result["selected"]["rank"] == 2
    assert result["candidates"][0]["numeric_integrity"]["passed"] is False
    assert result["candidates"][1]["numeric_integrity"]["passed"] is False
