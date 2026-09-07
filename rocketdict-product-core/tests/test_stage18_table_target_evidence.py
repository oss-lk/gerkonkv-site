from __future__ import annotations

from pathlib import Path

from rocketdict.database import (
    begin_run,
    bootstrap_database,
    finish_run,
    replace_run_items,
    transaction,
)
from rocketdict.lexical import lexical_snapshot, run_stage18
from rocketdict.numeric_integrity import run_numeric_symbol_gate
from rocketdict.stages import (
    run_length_ratio_gate,
    run_punctuation_gate,
    run_stage14,
    run_stage16,
    run_stage17,
)


def _seed_run(
    db: Path,
    *,
    stage: int,
    key: str,
    implementation: str,
    output: dict,
    items: list[dict] | None = None,
) -> int:
    with transaction(db) as connection:
        run_id, cached = begin_run(
            connection,
            stage_number=stage,
            stage_key=key,
            implementation=implementation,
            input_identity={"table_target_seed": stage},
            parameters={},
        )
        assert cached is False
        if items is not None:
            replace_run_items(connection, run_id, items)
        result = dict(output)
        for name in {
            8: ["nlp_run_id"],
            10: ["context_run_id"],
            12: ["translation_run_id"],
        }.get(stage, []):
            result.setdefault(name, run_id)
        finish_run(connection, run_id, result)
    return run_id


def _token(index: int, text: str, source: str) -> dict:
    start = source.index(text)
    return {
        "sequence_number": index,
        "kind": "nlp_token",
        "source_start": start,
        "source_end": start + len(text),
        "source_text": text,
        "payload": {
            "token_index": index,
            "lemma": text.casefold(),
            "pos": "NOUN",
            "dependency": "ROOT",
            "sentence_index": 0,
            "flags": {"is_oov": False},
        },
    }


def test_stage18_uses_logical_table_group_target_not_whole_table(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    source = "Head   | Other\nMore   | Text \n"
    head_start = source.index("Head")
    other_start = source.index("Other")
    more_start = source.index("More")
    text_start = source.index("Text")

    nlp = _seed_run(
        db,
        stage=8,
        key="nlp_analysis",
        implementation="en-sm",
        output={
            "schema": "rocketdict-product-stage8/1",
            "document_version_id": 1,
            "coverage_complete": True,
        },
        items=[
            _token(0, "Head", source),
            _token(1, "Other", source),
            _token(2, "More", source),
            _token(3, "Text", source),
        ],
    )
    context = _seed_run(
        db,
        stage=10,
        key="context_enrichment",
        implementation="structural-entity-term-discourse-pronoun-v1",
        output={
            "schema": "rocketdict-product-stage10/1",
            "nlp_run_id": nlp,
            "document_version_id": 1,
            "coverage_complete": True,
        },
    )
    rendered_target = "Заголовок | Другое\n          | Текст \n"
    translation = _seed_run(
        db,
        stage=12,
        key="translation_baseline",
        implementation="opus-en-ru-ct2",
        output={
            "schema": "rocketdict-product-stage12/1",
            "context_run_id": context,
            "document_version_id": 1,
            "real_mt": True,
            "network_used": False,
            "planner_contract": "rocketdict-stage12-protected-split/4",
        },
        items=[
            {
                "sequence_number": 0,
                "kind": "translation_segment",
                "source_start": 0,
                "source_end": len(source),
                "source_text": source,
                "target_text": rendered_target,
                "payload": {
                    "selected_rank": 0,
                    "composite_real_mt": True,
                    "table": {
                        "stage12_contract": "rocketdict-stage12-ascii-table-logical-rank0/1",
                        "structure_contract": "rocketdict-ascii-table-cells/1",
                        "logical_contract": "rocketdict-ascii-table-logical-cells/1",
                        "logical_groups": [
                            {
                                "group_index": 0,
                                "source_spans": [
                                    {"start": head_start, "end": head_start + 4},
                                    {"start": more_start, "end": more_start + 4},
                                ],
                                "source_text": "Head More",
                                "target_text": "Заголовок больше",
                                "grouping_reason": "header_vertical_lane",
                            },
                            {
                                "group_index": 1,
                                "source_spans": [
                                    {"start": other_start, "end": other_start + 5},
                                    {"start": text_start, "end": text_start + 4},
                                ],
                                "source_text": "Other Text",
                                "target_text": "Другой текст",
                                "grouping_reason": "header_vertical_lane",
                            },
                        ],
                    },
                },
            }
        ],
    )

    assembly = run_stage14(db, translation_run_id=translation)
    assembly_id = int(assembly["assembly_id"])
    assert run_numeric_symbol_gate(db, assembly_id=assembly_id)["passed"] is True
    assert run_punctuation_gate(db, assembly_id=assembly_id)["passed"] is True
    assert run_length_ratio_gate(db, assembly_id=assembly_id)["passed"] is True
    revision = run_stage16(db, assembly_id=assembly_id)
    alignment = run_stage17(
        db, translation_revision_id=int(revision["translation_revision_id"])
    )
    extraction = run_stage18(db, alignment_run_id=int(alignment["alignment_run_id"]))

    assert extraction["coverage_complete"] is True
    assert extraction["uncovered_token_count"] == 0
    assert extraction["table_scoped_target_evidence_count"] == 4
    assert extraction["target_evidence_policy"] == "narrowest-stage12-structural-scope-v1"

    snapshot = lexical_snapshot(db, extraction_run_id=int(extraction["extraction_run_id"]))
    by_surface = {row["surface_text"]: row for row in snapshot["occurrences"]}
    assert by_surface["Head"]["target_evidence_text"] == "Заголовок больше"
    assert by_surface["More"]["target_evidence_text"] == "Заголовок больше"
    assert by_surface["Other"]["target_evidence_text"] == "Другой текст"
    assert by_surface["Text"]["target_evidence_text"] == "Другой текст"
    assert all(
        row["target_evidence_text"] != rendered_target
        for row in snapshot["occurrences"]
    )
    assert all(
        row["evidence"]["target_evidence_scope"] == "table_logical_group"
        for row in snapshot["occurrences"]
    )
