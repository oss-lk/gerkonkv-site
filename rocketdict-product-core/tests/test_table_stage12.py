from __future__ import annotations

import pytest

from rocketdict.table_stage12 import (
    TABLE_STAGE12_CONTRACT,
    build_stage12_table_plan,
    partition_txt_base_with_ascii_tables,
    render_stage12_table_rank0,
    table_plan_metrics,
)


def _base(start: int, end: int, content: str, sequence: int = 0) -> dict:
    return {
        "start": start,
        "end": end,
        "text": content[start:end],
        "metadata": {
            "source": "nlp_sentence",
            "context_sentence_start": sequence,
            "context_sentence_end": sequence,
            "context_sentence_count": 1,
        },
    }


def test_table_stage12_contract_is_explicit() -> None:
    assert TABLE_STAGE12_CONTRACT == "rocketdict-stage12-ascii-table-logical-rank0/1"


def test_partition_replaces_table_inside_one_nlp_sentence_byte_exactly() -> None:
    table = (
        "------+------\n"
        "Head  | Other\n"
        "More  |  42  \n"
        "Tail  |  43  \n"
        "------+------\n"
    )
    content = "Before.\n" + table + "After."
    rows = partition_txt_base_with_ascii_tables(
        content,
        [_base(0, len(content), content)],
    )

    assert [row["metadata"]["source"] for row in rows] == [
        "nlp_sentence_fragment",
        "ascii_table",
        "nlp_sentence_fragment",
    ]
    assert rows[1]["text"] == table
    assert rows[1]["metadata"]["table_stage12_contract"] == TABLE_STAGE12_CONTRACT
    assert "".join(row["text"] for row in rows) == content
    assert rows[0]["end"] == rows[1]["start"]
    assert rows[1]["end"] == rows[2]["start"]


def test_partition_coalesces_split_newline_after_table_into_following_prose() -> None:
    table = (
        "------+------\n"
        "Head  | Other\n"
        "More  | Text \n"
        "Tail  | Text \n"
        "------+------\n"
    )
    content = table + "\nFollowing prose."
    table_end = len(table)
    # Match the full-Opticks shape: one Stage10 sentence ends one byte after
    # the detected table, leaving a split-created newline outside the table.
    base = [
        _base(0, table_end + 1, content, sequence=0),
        _base(table_end + 1, len(content), content, sequence=1),
    ]
    rows = partition_txt_base_with_ascii_tables(content, base)

    assert rows[0]["metadata"]["source"] == "ascii_table"
    assert rows[0]["text"] == table
    assert not [row for row in rows if not str(row["text"]).strip()]
    assert rows[1]["start"] == table_end
    assert rows[1]["text"] == "\nFollowing prose."
    assert rows[1]["metadata"]["ascii_table_boundary_whitespace_coalesced"] is True
    assert "".join(str(row["text"]) for row in rows) == content


def test_single_pipe_prose_is_not_promoted_to_table() -> None:
    content = "A | B is a one-off notation, not an ASCII table."
    base = [_base(0, len(content), content)]
    rows = partition_txt_base_with_ascii_tables(content, base)
    assert rows == base


def test_rank0_render_preserves_numeric_cells_and_emits_group_source_spans() -> None:
    table = (
        "-------------------+----------\n"
        "Angle of Incidence | Diameter \n"
        "      on Air.      | of Ring. \n"
        "-------------------+----------\n"
        "       23          |  4'27    \n"
        "-------------------+----------\n"
    )
    plan = build_stage12_table_plan(table, absolute_start=100)
    assert len(plan.groups) == 2
    hypotheses = {
        plan.groups[0].index: [
            {"rank": 0, "text": "Угол падения на воздух", "tokens": [], "score": -1.0}
        ],
        plan.groups[1].index: [
            {"rank": 0, "text": "Диаметр кольца", "tokens": [], "score": -1.0}
        ],
    }

    target, evidence = render_stage12_table_rank0(plan, hypotheses)
    assert "Угол падения на воздух" in target
    assert "Диаметр кольца" in target
    assert "23" in target
    assert "4'27" in target
    assert target.count("|") == table.count("|")
    assert target.count("\n") == table.count("\n")
    assert len(evidence[0]["source_spans"]) == 2
    assert all(span["start"] >= 100 for row in evidence for span in row["source_spans"])
    metrics = table_plan_metrics(plan)
    assert metrics["logical_group_count"] == 2
    assert metrics["multi_piece_group_count"] == 2
    assert metrics["preserved_source_character_count"] > 0


def test_rank0_render_rejects_missing_group_hypothesis() -> None:
    table = (
        "------+------\n"
        "Head  | Other\n"
        "More  | Text \n"
        "------+------\n"
    )
    plan = build_stage12_table_plan(table, absolute_start=0)
    assert len(plan.groups) == 2
    with pytest.raises(ValueError, match="hypothesis mapping mismatch"):
        render_stage12_table_rank0(plan, {plan.groups[0].index: [{"rank": 0, "text": "X"}]})
