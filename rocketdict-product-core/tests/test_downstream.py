from __future__ import annotations

import json
from pathlib import Path

import pytest

from rocketdict.database import (
    begin_run,
    bootstrap_database,
    finish_run,
    replace_run_items,
    transaction,
)
from rocketdict.downstream import (
    _admissible_ru_candidate,
    _probe_forms,
    assemble_card_set,
    downstream_snapshot,
    ensure_downstream_schema,
    run_stage21,
    run_stage22,
    run_stage23,
    run_stage24,
    run_stage25,
)


def _run(
    db: Path,
    *,
    stage: int,
    key: str,
    implementation: str,
    output: dict,
    items: list[dict] | None = None,
) -> int:
    with transaction(db) as connection:
        ensure_downstream_schema(connection)
        run_id, cached = begin_run(
            connection,
            stage_number=stage,
            stage_key=key,
            implementation=implementation,
            input_identity={"fixture": f"{stage}:{key}:{implementation}"},
            parameters={},
        )
        assert cached is False
        if items:
            replace_run_items(connection, run_id, items)
        finish_run(connection, run_id, output)
    return run_id


def _seed_downstream_lineage(db: Path) -> dict[str, int]:
    nlp_run = _run(
        db,
        stage=8,
        key="nlp_analysis",
        implementation="en-sm",
        output={"schema": "fixture-stage8"},
        items=[
            {
                "sequence_number": 0,
                "kind": "nlp_token",
                "source_start": 0,
                "source_end": 5,
                "source_text": "Light",
                "payload": {"lemma": "light", "pos": "NOUN", "dependency": "nsubj"},
            }
        ],
    )
    alignment_run = _run(
        db,
        stage=17,
        key="alignment",
        implementation="deterministic-structural-global",
        output={"schema": "fixture-stage17"},
        items=[
            {
                "sequence_number": 0,
                "kind": "alignment_segment",
                "source_start": 0,
                "source_end": 16,
                "source_text": "Light is bright.",
                "target_text": "Свет яркий.",
                "payload": {"confidence": 1.0},
            }
        ],
    )
    extraction_run = _run(
        db,
        stage=18,
        key="lexical_extraction",
        implementation="workbench-aligned-content-pos-v4",
        output={"schema": "fixture-stage18"},
    )
    sense_run = _run(
        db,
        stage=19,
        key="sense_induction",
        implementation="deterministic-context-target-graph",
        output={"schema": "fixture-stage19"},
    )
    stage20_run = _run(
        db,
        stage=20,
        key="sense_translation",
        implementation="contextual-lexical-opus-v3",
        output={"schema": "fixture-stage20", "real_mt": True},
    )
    stage21_run = _run(
        db,
        stage=21,
        key="cefr",
        implementation="cefrj-vocabulary-1.5",
        output={"schema": "fixture-stage21"},
    )
    stage22_run = _run(
        db,
        stage=22,
        key="pronunciation",
        implementation="cmudict-production",
        output={"schema": "fixture-stage22"},
    )

    with transaction(db) as connection:
        ensure_downstream_schema(connection)
        entry_id = int(
            connection.execute(
                """
                INSERT INTO lexical_entries(normalized_lemma,display_lemma,part_of_speech,entry_type)
                VALUES('light','Light','NOUN','word')
                """
            ).lastrowid
        )
        nlp_item_id = int(
            connection.execute(
                "SELECT id FROM run_items WHERE run_id=?", (nlp_run,)
            ).fetchone()[0]
        )
        alignment_item_id = int(
            connection.execute(
                "SELECT id FROM run_items WHERE run_id=?", (alignment_run,)
            ).fetchone()[0]
        )
        occurrence_id = int(
            connection.execute(
                """
                INSERT INTO lexical_occurrences(
                    extraction_run_id,lexical_entry_id,nlp_run_item_id,alignment_run_item_id,
                    sequence_number,source_start,source_end,surface_text,target_evidence_text,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    extraction_run,
                    entry_id,
                    nlp_item_id,
                    alignment_item_id,
                    0,
                    0,
                    5,
                    "Light",
                    "Свет яркий.",
                    json.dumps({"token": {"dependency": "nsubj"}}),
                ),
            ).lastrowid
        )
        sense_id = int(
            connection.execute(
                """
                INSERT INTO lexical_senses(
                    sense_induction_run_id,lexical_entry_id,sense_key,target_evidence_key,
                    occurrence_count,evidence_json
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    sense_run,
                    entry_id,
                    "sense-light-1",
                    "свет яркий",
                    1,
                    json.dumps(
                        {
                            "algorithm": "fixture",
                            "occurrences": [{"occurrence_id": occurrence_id}],
                        }
                    ),
                ),
            ).lastrowid
        )
        translation_content = {
            "sense_id": sense_id,
            "entry_id": entry_id,
            "lemma": "light",
            "translation": "свет",
            "provider": "contextual-lexical-opus-v3",
            "real_mt": True,
        }
        translation_id = int(
            connection.execute(
                """
                INSERT INTO sense_translation_revisions(
                    stage20_run_id,lexical_sense_id,lexical_entry_id,selected_translation,
                    selected_normalized,selected_score,candidates_json,evidence_json,approved,
                    content_sha256,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'))
                """,
                (
                    stage20_run,
                    sense_id,
                    entry_id,
                    "свет",
                    "свет",
                    0.95,
                    "[]",
                    json.dumps({"fixture": True}),
                    1,
                    __import__("hashlib").sha256(
                        json.dumps(translation_content, sort_keys=True).encode()
                    ).hexdigest(),
                ),
            ).lastrowid
        )
        cefr_id = int(
            connection.execute(
                """
                INSERT INTO cefr_assignments(
                    stage21_run_id,lexical_entry_id,level,match_kind,conflict_count,
                    source_sha256,evidence_json,created_at
                ) VALUES(?,?,?,?,?,?,?,datetime('now'))
                """,
                (stage21_run, entry_id, "A2", "fixture_exact", 0, "0" * 64, "{}"),
            ).lastrowid
        )
        pronunciation_id = int(
            connection.execute(
                """
                INSERT INTO pronunciations(
                    stage22_run_id,lexical_entry_id,form,strategy,variants_json,unknown,
                    evidence_json,created_at
                ) VALUES(?,?,?,?,?,?,?,datetime('now'))
                """,
                (
                    stage22_run,
                    entry_id,
                    "light",
                    "fixture_exact",
                    json.dumps([["L", "AY1", "T"]]),
                    0,
                    json.dumps({"generated_fallback": False}),
                ),
            ).lastrowid
        )
    return {
        "entry_id": entry_id,
        "sense_id": sense_id,
        "translation_id": translation_id,
        "cefr_id": cefr_id,
        "pronunciation_id": pronunciation_id,
    }


def test_lexical_probe_policy_rejects_non_real_candidate_shapes() -> None:
    probes = _probe_forms("run", "VERB", "word", "ROOT")
    assert probes[0]["kind"] == "verb_argument"
    assert probes[0]["text"] == "to run something"
    assert probes[0]["effective_pos"] == "VERB"
    assert _admissible_ru_candidate("light", "свет", entry_type="word") == (True, None)
    assert _admissible_ru_candidate("light", "light", entry_type="word") == (False, "identity")
    assert _admissible_ru_candidate("light", "123", entry_type="word") == (False, "no_cyrillic")
    assert _admissible_ru_candidate("light", "свет light", entry_type="word") == (False, "latin_leakage")


def test_stage21_and_22_refuse_degraded_evidence_before_execution(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    ids = _seed_downstream_lineage(db)

    monkeypatch.delenv("ROCKETDICT_CEFRJ_ASSET", raising=False)
    with pytest.raises(RuntimeError, match="CEFR-J asset is not configured"):
        run_stage21(db, lexical_entry_id=ids["entry_id"])

    with pytest.raises(RuntimeError, match="forbids generated pronunciation fallback"):
        run_stage22(
            db,
            lexical_entry_id=ids["entry_id"],
            parameters={"enable_generated_fallback": True},
        )


def test_stage23_to_stage25_produce_durable_card_set_and_export(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    ids = _seed_downstream_lineage(db)

    examples = run_stage23(db, lexical_sense_id=ids["sense_id"])
    assert examples["scope_contract"] == "stage23-sense-scope-v2"
    assert examples["approved_sense_translation_revision_id"] == ids["translation_id"]
    assert examples["primary_missing"] is False
    assert examples["example_ids"]

    card = run_stage24(db, lexical_sense_id=ids["sense_id"])
    assert card["complete"] is True
    assert int(card["card_revision_id"]) > 0
    assert len(card["content_sha256"]) == 64

    card_set = assemble_card_set(
        db,
        card_revision_ids=[int(card["card_revision_id"])],
        set_name="fixture product set",
    )
    assert card_set["complete"] is True
    assert card_set["card_count"] == 1
    assert int(card_set["set_revision_id"]) > 0

    export_path = tmp_path / "out" / "dictionary.json"
    exported = run_stage25(
        db,
        set_revision_id=int(card_set["set_revision_id"]),
        parameters={"output_path": str(export_path)},
    )
    assert exported["complete"] is True
    assert exported["card_count"] == 1
    assert export_path.is_file()
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "rocketdict-product-export/1"
    assert payload["card_count"] == 1
    assert len(payload["cards"]) == 1
    assert payload["cards"][0]["translation"] == "свет"
    assert payload["cards"][0]["pronunciation"]["generated_fallback"] is False

    snapshot = downstream_snapshot(db)
    assert snapshot["counts"]["sense_examples"] >= 1
    assert snapshot["counts"]["card_revisions"] == 1
    assert snapshot["counts"]["card_sets"] == 1


def test_card_set_rejects_duplicate_and_missing_revisions(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    with pytest.raises(RuntimeError, match="non-empty unique positive"):
        assemble_card_set(db, card_revision_ids=[])
    with pytest.raises(RuntimeError, match="non-empty unique positive"):
        assemble_card_set(db, card_revision_ids=[1, 1])
    with pytest.raises(RuntimeError, match="missing card revisions"):
        assemble_card_set(db, card_revision_ids=[999])
