from __future__ import annotations

import pytest

from rocketdict.lexical_target_evidence import (
    TABLE_LEXICAL_EVIDENCE_CONTRACT,
    TargetEvidenceError,
    resolve_target_evidence,
)


def _alignment() -> dict:
    return {
        "source_start": 0,
        "source_end": 100,
        "target_text": "Вся переведённая таблица",
    }


def _table_segment() -> dict:
    return {
        "source_start": 0,
        "source_end": 100,
        "target_text": "Вся переведённая таблица",
        "payload": {
            "table": {
                "stage12_contract": "rocketdict-stage12-ascii-table-logical-rank0/1",
                "structure_contract": "rocketdict-ascii-table-cells/1",
                "logical_contract": "rocketdict-ascii-table-logical-cells/1",
                "logical_groups": [
                    {
                        "group_index": 0,
                        "source_spans": [
                            {"start": 10, "end": 20},
                            {"start": 30, "end": 40},
                        ],
                        "target_text": "Угол падения на воздух",
                        "grouping_reason": "header_vertical_lane",
                    },
                    {
                        "group_index": 1,
                        "source_spans": [{"start": 50, "end": 65}],
                        "target_text": "Диаметр кольца",
                        "grouping_reason": "indentation_record",
                    },
                ],
            }
        },
    }


def test_ordinary_segment_keeps_alignment_target() -> None:
    evidence = resolve_target_evidence(
        token_start=10,
        token_end=15,
        alignment=_alignment(),
        translation_segment={"source_start": 0, "source_end": 100, "payload": {}},
    )
    assert evidence.text == "Вся переведённая таблица"
    assert evidence.scope == "alignment_segment"
    assert evidence.metadata["contract"] == TABLE_LEXICAL_EVIDENCE_CONTRACT


def test_table_token_gets_only_matching_logical_group_target() -> None:
    evidence = resolve_target_evidence(
        token_start=32,
        token_end=36,
        alignment=_alignment(),
        translation_segment=_table_segment(),
    )
    assert evidence.text == "Угол падения на воздух"
    assert evidence.scope == "table_logical_group"
    assert evidence.metadata["group_index"] == 0
    assert evidence.metadata["source_spans"] == [
        {"start": 10, "end": 20},
        {"start": 30, "end": 40},
    ]


def test_table_token_without_group_fails_closed() -> None:
    with pytest.raises(TargetEvidenceError, match="exactly one"):
        resolve_target_evidence(
            token_start=70,
            token_end=75,
            alignment=_alignment(),
            translation_segment=_table_segment(),
        )


def test_overlapping_table_groups_fail_closed() -> None:
    segment = _table_segment()
    segment["payload"]["table"]["logical_groups"][1]["source_spans"] = [
        {"start": 15, "end": 25}
    ]
    with pytest.raises(TargetEvidenceError, match="matches=2"):
        resolve_target_evidence(
            token_start=16,
            token_end=18,
            alignment=_alignment(),
            translation_segment=segment,
        )
