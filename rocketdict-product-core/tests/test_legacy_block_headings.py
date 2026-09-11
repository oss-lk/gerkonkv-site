from __future__ import annotations

from rocketdict.legacy_block_headings import (
    LEGACY_BLOCK_HEADING_CONTRACT,
    detect_legacy_block_headings,
    evaluate_legacy_block_heading_hypotheses,
    parse_legacy_block_heading_unit,
    partition_txt_base_with_legacy_block_headings,
)


def test_detection_is_block_only_and_keeps_complete_multi_part_heading() -> None:
    text = (
        "Previous prose.\n\n"
        "_PROP._ IV. PROB. I.\n\n"
        "Body references PROP. V. inline.\n\n"
        "DEFIN. II.\n\n"
        "Definition body."
    )
    all_rows = detect_legacy_block_headings(text)
    block_rows = detect_legacy_block_headings(text, block_only=True)

    assert [row.family for row in all_rows] == [
        "proposition_problem",
        "proposition",
        "definition",
    ]
    assert [row.family for row in block_rows] == [
        "proposition_problem",
        "definition",
    ]
    assert block_rows[0].roman_identifiers == ("IV", "I")
    assert block_rows[0].canonical_model_input == "Proposition IV. Problem I."
    assert block_rows[1].canonical_model_input == "Definition II."


def test_parse_keeps_source_bytes_separate_from_canonical_model_input() -> None:
    heading = parse_legacy_block_heading_unit("\n_PROP._ VII. THEOR. VI.\t")
    assert heading.source_text == "_PROP._ VII. THEOR. VI."
    assert heading.family == "proposition_theorem"
    assert heading.roman_identifiers == ("VII", "VI")
    assert heading.canonical_model_input == "Proposition VII. Theorem VI."


def test_raw_candidate_selection_requires_exact_form_and_roman_identity() -> None:
    heading = parse_legacy_block_heading_unit("_PROP._ VIII. PROB. II.")
    result = evaluate_legacy_block_heading_hypotheses(
        heading,
        [
            {"rank": 0, "text": "Предложение VIII. Задача III."},
            {"rank": 1, "text": "Предложение VIII. Теорема II."},
            {"rank": 2, "text": "Предложение VIII. Задача II."},
        ],
    )

    assert result["contract"] == LEGACY_BLOCK_HEADING_CONTRACT
    assert result["selected"] is not None
    assert result["selected"]["rank"] == 2
    assert result["selected"]["target_text"] == "Предложение VIII. Задача II."
    assert [row["acceptable"] for row in result["candidates"]] == [False, False, True]


def test_problem_and_proposition_forms_allow_only_proven_raw_targets() -> None:
    proposition = parse_legacy_block_heading_unit("PROP. IX.")
    result = evaluate_legacy_block_heading_hypotheses(
        proposition,
        [
            {"rank": 0, "text": "Пропозиция IX."},
            {"rank": 1, "text": "Предложение IX."},
        ],
    )
    assert result["selected"] is not None
    assert result["selected"]["rank"] == 1

    problem = parse_legacy_block_heading_unit("_PROP._ IV. PROB. I.")
    result = evaluate_legacy_block_heading_hypotheses(
        problem,
        [
            {"rank": 0, "text": "Предложение IV. Проблема I."},
        ],
    )
    assert result["selected"] is not None
    assert result["selected"]["rank"] == 0


def test_partition_reassembles_heading_split_across_context_rows_byte_exactly() -> None:
    content = "Intro.\n\n_PROP._ IV. PROB. I.\n\nBody text."
    h_start = content.index("_PROP._")
    h_mid_1 = content.index("IV.")
    h_mid_2 = content.index("PROB.")
    h_end = h_mid_2 + len("PROB. I.")
    base = [
        {
            "start": 0,
            "end": h_mid_1,
            "text": content[:h_mid_1],
            "metadata": {
                "source": "nlp_sentence",
                "context_sentence_start": 0,
                "context_sentence_end": 0,
            },
        },
        {
            "start": h_mid_1,
            "end": h_mid_2,
            "text": content[h_mid_1:h_mid_2],
            "metadata": {
                "source": "nlp_sentence",
                "context_sentence_start": 1,
                "context_sentence_end": 1,
            },
        },
        {
            "start": h_mid_2,
            "end": len(content),
            "text": content[h_mid_2:],
            "metadata": {
                "source": "nlp_sentence",
                "context_sentence_start": 2,
                "context_sentence_end": 2,
            },
        },
    ]

    rows = partition_txt_base_with_legacy_block_headings(content, base)
    assert "".join(row["text"] for row in rows) == content
    headings = [row for row in rows if row["metadata"]["source"] == "legacy_block_heading"]
    assert len(headings) == 1
    heading = headings[0]
    assert heading["start"] == h_start
    assert heading["end"] >= h_end
    assert heading["text"].startswith("_PROP._ IV. PROB. I.")
    assert heading["metadata"]["context_sentence_start"] == 0
    assert heading["metadata"]["context_sentence_end"] == 2
    assert heading["metadata"]["canonical_model_input"] == "Proposition IV. Problem I."
