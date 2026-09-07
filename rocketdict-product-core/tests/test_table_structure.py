from __future__ import annotations

import pytest

from rocketdict.table_structure import (
    TABLE_STRUCTURE_CONTRACT,
    detect_ascii_table_blocks,
    plan_ascii_table_pieces,
    render_ascii_table,
)


def test_contract_is_versioned() -> None:
    assert TABLE_STRUCTURE_CONTRACT == "rocketdict-ascii-table-cells/1"


def test_detector_ignores_incidental_single_pipe_prose() -> None:
    source = "Use A | B as notation.\nNext ordinary sentence.\n"
    assert detect_ascii_table_blocks(source) == []


def test_detector_finds_contiguous_multiline_ascii_table_exactly() -> None:
    prefix = "Before.\n\n"
    table = (
        "------+-------\n"
        "Name  | Value\n"
        "------+-------\n"
        "Red   | 10-1/3\n"
        "Blue  | 11-1/2\n"
        "------+-------\n"
    )
    suffix = "\nAfter.\n"
    source = prefix + table + suffix

    blocks = detect_ascii_table_blocks(source)
    assert len(blocks) == 1
    block = blocks[0]
    assert source[block.start : block.end] == table
    assert block.pipe_line_count == 3
    assert block.separator_line_count == 3


def test_piece_plan_is_byte_exact_and_keeps_numeric_cells_outside_mt() -> None:
    table = (
        "----------------+----------+\n"
        "{Very black     |  1/2     |\n"
        "Of second order {Yellow   | 16-2/7   |\n"
        "----------------+----------+\n"
    )
    absolute_start = 123
    pieces = plan_ascii_table_pieces(table, absolute_start=absolute_start)

    assert "".join(piece.text for piece in pieces) == table
    assert pieces[0].start == absolute_start
    assert pieces[-1].end == absolute_start + len(table)
    assert all(left.end == right.start for left, right in zip(pieces, pieces[1:]))

    translated = [piece.text for piece in pieces if piece.kind == "translate"]
    passthrough = [piece.text for piece in pieces if piece.kind == "passthrough"]
    structure = [piece.text for piece in pieces if piece.kind == "structure"]

    assert "Very black" in translated
    assert "Of second order" in translated
    assert "Yellow" in translated
    assert "1/2" in passthrough
    assert "16-2/7" in passthrough
    assert "{" in structure
    assert "|" in structure

    # Every alphabetic source payload inside the table is assigned to real MT;
    # passthrough is restricted to alpha-free source content.
    assert all(not any(char.isalpha() for char in piece.text) for piece in pieces if piece.kind != "translate")


def test_mixed_numeric_text_cell_is_translated_as_raw_model_input() -> None:
    table = "Body | 23 to 14 | 1'699 |\nBody2 | 100 to 73 | 0'8765 |\nBody3 | 3 to 2 | 1'25 |\n"
    pieces = plan_ascii_table_pieces(table)
    translated = [piece.text for piece in pieces if piece.kind == "translate"]
    passthrough = [piece.text for piece in pieces if piece.kind == "passthrough"]

    assert "23 to 14" in translated
    assert "100 to 73" in translated
    assert "3 to 2" in translated
    assert "1'699" in passthrough
    assert "0'8765" in passthrough
    assert "1'25" in passthrough


def test_render_uses_only_raw_model_slots_and_preserves_structure() -> None:
    table = "Red   |  9      |  6-3/4\nBlue  | 14      | 10-1/2\nGreen | 15-1/8  | 11-2/3\n"
    pieces = plan_ascii_table_pieces(table)
    translations = {
        piece.index: {
            "Red": "Красный",
            "Blue": "Синий",
            "Green": "Зелёный",
        }[piece.text]
        for piece in pieces
        if piece.kind == "translate"
    }

    rendered = render_ascii_table(table, pieces, translations)
    assert rendered == (
        "Красный   |  9      |  6-3/4\n"
        "Синий  | 14      | 10-1/2\n"
        "Зелёный | 15-1/8  | 11-2/3\n"
    )
    for literal in ("9", "6-3/4", "14", "10-1/2", "15-1/8", "11-2/3"):
        assert literal in rendered
    assert rendered.count("|") == table.count("|")
    assert rendered.count("\n") == table.count("\n")


def test_render_rejects_missing_or_extra_translation_slots() -> None:
    table = "Name | 10\nName | 11\nName | 12\n"
    pieces = plan_ascii_table_pieces(table)
    indices = [piece.index for piece in pieces if piece.kind == "translate"]
    assert len(indices) == 3

    with pytest.raises(ValueError, match="mapping mismatch"):
        render_ascii_table(table, pieces, {indices[0]: "Имя"})
    with pytest.raises(ValueError, match="mapping mismatch"):
        render_ascii_table(
            table,
            pieces,
            {**{index: "Имя" for index in indices}, 999: "лишнее"},
        )
