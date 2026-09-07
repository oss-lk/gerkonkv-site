from __future__ import annotations

import pytest

from rocketdict.table_logical_structure import (
    LOGICAL_TABLE_CONTRACT,
    plan_logical_table_text_groups,
    render_logical_ascii_table,
)
from rocketdict.table_structure import plan_ascii_table_pieces


def _group_sources(table: str) -> list[str]:
    pieces = plan_ascii_table_pieces(table)
    return [
        group.source_text
        for group in plan_logical_table_text_groups(table, pieces)
    ]


def test_contract_is_independently_versioned() -> None:
    assert LOGICAL_TABLE_CONTRACT == "rocketdict-ascii-table-logical-cells/1"


def test_multiline_headers_are_joined_by_visual_lane() -> None:
    table = (
        "-------------------+--------------------+----------+----------\n"
        "Angle of Incidence |Angle of Refraction |Diameter  |Thickness\n"
        "        on         |         into       |  of the  |   of the\n"
        "      the Air.     |       the Air.     |   Ring.  |    Air.\n"
        "-------------------+--------------------+----------+----------\n"
        "    00      00     |     00      00     |  10      |  10\n"
        "-------------------+--------------------+----------+----------\n"
    )
    assert _group_sources(table) == [
        "Angle of Incidence on the Air.",
        "Angle of Refraction into the Air.",
        "Diameter of the Ring.",
        "Thickness of the Air.",
    ]


def test_indented_multiline_record_is_joined_but_numeric_relations_stay_singletons() -> None:
    table = (
        "---------------------+----------------+----------\n"
        "A Pseudo-Topazius,   |                |          \n"
        "  being a natural,   |                |          \n"
        "  pellucid, brittle, |   23 to   14   |  4'27   \n"
        "  hairy Stone, of a  |                |          \n"
        "  yellow Colour.     |                |          \n"
        "Air.                 | 3201 to 3200   |  0'0012 \n"
        "Spirit of Wine well  |                |          \n"
        "  rectified.         |  100 to   73   |  0'866  \n"
        "---------------------+----------------+----------\n"
    )
    groups = _group_sources(table)
    assert "A Pseudo-Topazius, being a natural, pellucid, brittle, hairy Stone, of a yellow Colour." in groups
    assert "Spirit of Wine well rectified." in groups
    assert "23 to   14" in groups
    assert "3201 to 3200" in groups
    assert "100 to   73" in groups
    assert "Air." in groups


def test_repeated_brace_lane_joins_sparse_order_label_not_colour_rows() -> None:
    table = (
        "                                        |---------+----------+\n"
        "                       {Blue            |  2-2/5  |  1-4/5   |\n"
        "Their Colours of the   {White           |  5-1/4  |  3-7/8   |\n"
        "first Order,           {Yellow          |  7-1/9  |  5-1/3   |\n"
        "                       {Orange          |  8      |  6       |\n"
        "                                        |---------+----------|\n"
    )
    groups = _group_sources(table)
    assert "Their Colours of the first Order," in groups
    for colour in ("Blue", "White", "Yellow", "Orange"):
        assert colour in groups
    assert "Blue White" not in groups
    assert "Yellow Orange" not in groups


def test_horizontal_separators_prevent_cross_record_grouping() -> None:
    table = (
        "-------------------------------------------+-----------+--------\n"
        "The breadth between the Middles of the     |   1/38    |\n"
        "  brightest Light of the innermost Fringes |    or     |\n"
        "  on either side the Shadow                |   1/39    |  7/50\n"
        "-------------------------------------------+-----------+--------\n"
        "The distance between the Middles of the    |           |\n"
        "  brightest Light of the first and second  |           |\n"
        "  Fringes                                  |  1/120    |  1/21\n"
        "-------------------------------------------+-----------+--------\n"
    )
    groups = _group_sources(table)
    assert "The breadth between the Middles of the brightest Light of the innermost Fringes on either side the Shadow" in groups
    assert "The distance between the Middles of the brightest Light of the first and second Fringes" in groups
    assert not any("Shadow The distance" in source for source in groups)


def test_logical_render_uses_one_translation_then_blanks_continuation_slots() -> None:
    table = (
        "-----------------+------------------\n"
        "  Incidence on   | Refraction into  \n"
        "   the Water.    |    the Water.    \n"
        "-----------------+------------------\n"
    )
    pieces = plan_ascii_table_pieces(table)
    groups = plan_logical_table_text_groups(table, pieces)
    assert [group.source_text for group in groups] == [
        "Incidence on the Water.",
        "Refraction into the Water.",
    ]
    rendered = render_logical_ascii_table(
        table,
        pieces,
        groups,
        {groups[0].index: "Угол падения на воду", groups[1].index: "Преломление в воду"},
    )
    assert "Угол падения на воду" in rendered
    assert "Преломление в воду" in rendered
    assert "the Water" not in rendered
    assert rendered.count("|") == table.count("|")
    assert rendered.count("\n") == table.count("\n")


def test_logical_render_rejects_incomplete_mapping() -> None:
    # The repeated pipe column is intentional: lane inference is conservative
    # and does not create a visual boundary from a one-off ``A | B`` line.
    table = (
        "------+------\n"
        "Head  | Other\n"
        "more  | field\n"
        "------+------\n"
    )
    pieces = plan_ascii_table_pieces(table)
    groups = plan_logical_table_text_groups(table, pieces)
    assert len(groups) == 2
    with pytest.raises(ValueError, match="mapping mismatch"):
        render_logical_ascii_table(table, pieces, groups, {groups[0].index: "Заголовок"})
