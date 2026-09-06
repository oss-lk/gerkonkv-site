from __future__ import annotations

from pathlib import Path

import pytest

from rocketdict.database import (
    begin_run,
    bootstrap_database,
    connect,
    finish_run,
    replace_run_items,
    transaction,
)
from rocketdict.lexical import lexical_snapshot, run_stage18, run_stage19
from rocketdict.stages import (
    StageExecutionError,
    run_length_ratio_gate,
    run_numeric_symbol_gate,
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
            input_identity={"seed_stage": stage, "seed": output.get("seed", stage)},
            parameters={},
        )
        assert cached is False
        if items is not None:
            replace_run_items(connection, run_id, items)
        output = dict(output)
        for name in {
            8: ["nlp_run_id"],
            10: ["context_run_id"],
            12: ["translation_run_id"],
        }.get(stage, []):
            output.setdefault(name, run_id)
        finish_run(connection, run_id, output)
    return run_id


def _base_lineage(db: Path) -> tuple[int, int, int]:
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
            {
                "sequence_number": 0,
                "kind": "nlp_token",
                "source_start": 0,
                "source_end": 5,
                "source_text": "Light",
                "payload": {
                    "token_index": 0,
                    "lemma": "light",
                    "pos": "NOUN",
                    "dependency": "nsubj",
                    "sentence_index": 0,
                    "flags": {"is_oov": True},
                },
            },
            {
                "sequence_number": 1,
                "kind": "nlp_token",
                "source_start": 6,
                "source_end": 8,
                "source_text": "42",
                "payload": {
                    "token_index": 1,
                    "lemma": "42",
                    "pos": "NUM",
                    "dependency": "nummod",
                    "sentence_index": 0,
                    "flags": {},
                },
            },
            {
                "sequence_number": 2,
                "kind": "nlp_token",
                "source_start": 10,
                "source_end": 16,
                "source_text": "Newton",
                "payload": {
                    "token_index": 2,
                    "lemma": "Newton",
                    "pos": "PROPN",
                    "dependency": "nsubj",
                    "sentence_index": 1,
                    "entity_type": "PERSON",
                    "flags": {},
                },
            },
            {
                "sequence_number": 3,
                "kind": "nlp_token",
                "source_start": 17,
                "source_end": 21,
                "source_text": "sees",
                "payload": {
                    "token_index": 3,
                    "lemma": "see",
                    "pos": "VERB",
                    "dependency": "ROOT",
                    "sentence_index": 1,
                    "flags": {},
                },
            },
            {
                "sequence_number": 4,
                "kind": "nlp_token",
                "source_start": 22,
                "source_end": 26,
                "source_text": "rays",
                "payload": {
                    "token_index": 4,
                    "lemma": "ray",
                    "pos": "VERB",
                    "dependency": "obj",
                    "sentence_index": 1,
                    "entity_type": "ORG",
                    "flags": {"is_oov": True},
                },
            },
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
        },
        items=[
            {
                "sequence_number": 0,
                "kind": "translation_segment",
                "source_start": 0,
                "source_end": 9,
                "source_text": "Light 42.",
                "target_text": "Свет 42.",
                "payload": {"selected_rank": 0},
            },
            {
                "sequence_number": 1,
                "kind": "translation_segment",
                "source_start": 10,
                "source_end": 27,
                "source_text": "Newton sees rays.",
                "target_text": "Ньютон видит лучи.",
                "payload": {"selected_rank": 0},
            },
        ],
    )
    return nlp, context, translation


def test_hard_gates_control_finalization_and_alignment(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    _nlp, _context, translation = _base_lineage(db)

    assembly = run_stage14(db, translation_run_id=translation)
    assert assembly["real_mt_lineage"] is True
    assembly_id = int(assembly["assembly_id"])

    with pytest.raises(StageExecutionError, match="without all hard gate PASS"):
        run_stage16(db, assembly_id=assembly_id)

    numeric = run_numeric_symbol_gate(db, assembly_id=assembly_id)
    punctuation = run_punctuation_gate(db, assembly_id=assembly_id)
    length = run_length_ratio_gate(db, assembly_id=assembly_id)
    assert numeric["passed"] is True
    assert punctuation["passed"] is True
    assert length["passed"] is True

    revision = run_stage16(db, assembly_id=assembly_id)
    assert revision["approved"] is True
    alignment = run_stage17(
        db, translation_revision_id=int(revision["translation_revision_id"])
    )
    assert alignment["coverage_complete"] is True
    assert alignment["uncovered_segment_count"] == 0


def test_numeric_gate_fails_on_missing_source_literal(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    translation = _seed_run(
        db,
        stage=12,
        key="translation_baseline",
        implementation="opus-en-ru-ct2",
        output={"schema": "rocketdict-product-stage12/1", "real_mt": True},
        items=[
            {
                "sequence_number": 0,
                "kind": "translation_segment",
                "source_start": 0,
                "source_end": 10,
                "source_text": "Value 42%.",
                "target_text": "Значение.",
                "payload": {},
            }
        ],
    )
    assembly = run_stage14(db, translation_run_id=translation)
    result = run_numeric_symbol_gate(db, assembly_id=int(assembly["assembly_id"]))
    assert result["passed"] is False
    assert result["failure_count"] == 1
    with connect(db, readonly=True) as connection:
        issue = connection.execute(
            "SELECT payload_json FROM run_items WHERE run_id=?",
            (int(result["quality_gate_run_id"]),),
        ).fetchone()
    assert issue is not None
    assert "42" in str(issue["payload_json"])


def test_native_stage18_and_19_preserve_complete_lexical_lineage(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    nlp, _context, translation = _base_lineage(db)
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
    assert extraction["nlp_run_id"] == nlp
    # NUM is intentionally outside dictionary lexical scope; four content
    # tokens remain. "rays" is narrowly repaired VERB/obj -> NOUN.
    assert extraction["eligible_token_count"] == 4
    assert extraction["occurrence_count"] == 4

    senses = run_stage19(db, extraction_run_id=int(extraction["extraction_run_id"]))
    assert senses["coverage_complete"] is True
    assert senses["occurrence_count"] == 4
    assert senses["lexical_entry_count"] == 4
    assert senses["lexical_sense_count"] == 4

    snapshot = lexical_snapshot(
        db,
        extraction_run_id=int(extraction["extraction_run_id"]),
        sense_run_id=int(senses["sense_induction_run_id"]),
    )
    assert len(snapshot["occurrences"]) == 4
    assert len(snapshot["senses"]) == 4
    rays = next(row for row in snapshot["entries"] if row["normalized_lemma"] == "ray")
    assert rays["part_of_speech"] == "NOUN"

    second_extraction = run_stage18(
        db, alignment_run_id=int(alignment["alignment_run_id"])
    )
    second_senses = run_stage19(
        db, extraction_run_id=int(extraction["extraction_run_id"])
    )
    assert second_extraction["extraction_run_id"] == extraction["extraction_run_id"]
    assert second_extraction["cache_hit"] is True
    assert second_senses["sense_induction_run_id"] == senses["sense_induction_run_id"]
    assert second_senses["cache_hit"] is True
