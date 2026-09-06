from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

from rocketdict.database import (
    begin_run,
    bootstrap_database,
    connect,
    finish_run,
    get_run,
    get_run_items,
    replace_run_items,
    transaction,
)
from rocketdict.lexical import ensure_schema as ensure_lexical_schema
import rocketdict.sense_translation as stage20


class _FakeTranslator:
    def __init__(self, *, device: str = "cpu", compute_type: str = "float32") -> None:
        assert device == "cpu"
        assert compute_type == "float32"

    def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
        assert beam_size >= num_hypotheses > 0
        output = []
        for text in texts:
            if "Light" in text or "light" in text:
                values = ["свет", "освещение"]
            else:
                values = ["свет"]
            rows = [
                {"rank": rank, "text": value, "tokens": [value], "score": -0.1 - rank}
                for rank, value in enumerate(values[:num_hypotheses])
            ]
            output.append(rows)
        return output


class _IdentityTranslator(_FakeTranslator):
    def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
        return [
            [{"rank": 0, "text": text.casefold(), "tokens": [text], "score": -0.1}]
            for text in texts
        ]


def _asset():  # type: ignore[no-untyped-def]
    return SimpleNamespace(
        revision="opus-2020-02-11",
        source_archive_sha256="7" * 64,
        manifest_sha256="8" * 64,
        payload_tree_sha256="9" * 64,
    )


def _database(tmp_path: Path) -> tuple[Path, int]:
    database = tmp_path / "rocketdict.sqlite"
    bootstrap_database(database)
    with transaction(database) as connection:
        ensure_lexical_schema(connection)
        extraction_run_id, _ = begin_run(
            connection,
            stage_number=18,
            stage_key="lexical_extraction",
            implementation="workbench-aligned-content-pos-v4",
            input_identity={"alignment_run_id": 1},
            parameters={},
        )
        replace_run_items(
            connection,
            extraction_run_id,
            [
                {"kind": "nlp_token", "source_start": 0, "source_end": 5, "source_text": "Light", "payload": {"pos": "NOUN", "lemma": "light", "dependency": "nsubj"}},
                {"kind": "alignment_segment", "source_start": 0, "source_end": 5, "source_text": "Light", "target_text": "Свет проходит через призму", "payload": {"confidence": 1.0}},
            ],
        )
        items = get_run_items(connection, extraction_run_id)
        token_item = next(row for row in items if row["kind"] == "nlp_token")
        alignment_item = next(row for row in items if row["kind"] == "alignment_segment")
        cursor = connection.execute(
            "INSERT INTO lexical_entries(normalized_lemma,display_lemma,part_of_speech,entry_type) VALUES(?,?,?,?)",
            ("light", "Light", "NOUN", "word"),
        )
        entry_id = int(cursor.lastrowid)
        evidence = '{"token":{"dependency":"nsubj","pos":"NOUN"}}'
        cursor = connection.execute(
            """
            INSERT INTO lexical_occurrences(
                extraction_run_id,lexical_entry_id,nlp_run_item_id,alignment_run_item_id,
                sequence_number,source_start,source_end,surface_text,target_evidence_text,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                extraction_run_id,
                entry_id,
                int(token_item["id"]),
                int(alignment_item["id"]),
                0,
                0,
                5,
                "Light",
                "Свет проходит через призму",
                evidence,
            ),
        )
        occurrence_id = int(cursor.lastrowid)
        finish_run(
            connection,
            extraction_run_id,
            {"schema": "rocketdict-product-stage18/1", "extraction_run_id": extraction_run_id, "coverage_complete": True},
        )

        sense_run_id, _ = begin_run(
            connection,
            stage_number=19,
            stage_key="sense_induction",
            implementation="deterministic-context-target-graph",
            input_identity={"extraction_run_id": extraction_run_id},
            parameters={},
        )
        cursor = connection.execute(
            """
            INSERT INTO lexical_senses(
                sense_induction_run_id,lexical_entry_id,sense_key,target_evidence_key,
                occurrence_count,evidence_json
            ) VALUES(?,?,?,?,?,?)
            """,
            (
                sense_run_id,
                entry_id,
                "a" * 64,
                "свет проходит через призму",
                1,
                '{"algorithm":"test","occurrence_ids":[%d]}' % occurrence_id,
            ),
        )
        sense_id = int(cursor.lastrowid)
        finish_run(
            connection,
            sense_run_id,
            {
                "schema": "rocketdict-product-stage19/1",
                "sense_induction_run_id": sense_run_id,
                "stage_result_id": sense_run_id,
                "extraction_run_id": extraction_run_id,
                "lexical_sense_count": 1,
                "coverage_complete": True,
                "sense_ids_sha256": "b" * 64,
            },
        )
    assert sense_id > 0
    return database, sense_run_id


def test_stage20_persists_real_provider_evidence_and_approved_revision(tmp_path: Path, monkeypatch) -> None:
    database, sense_run_id = _database(tmp_path)
    monkeypatch.setattr(stage20, "load_opus_asset", lambda: _asset())
    monkeypatch.setattr(stage20, "OpusTranslator", _FakeTranslator)

    result = stage20.run_stage20(
        database,
        sense_induction_run_id=sense_run_id,
        parameters={"beam_size": 2, "num_hypotheses": 2, "maximum_candidates_per_sense": 2},
    )
    assert result["schema"] == "rocketdict-product-stage20/1"
    assert result["coverage_complete"] is True
    assert result["sense_count"] == result["selection_revision_count"] == 1
    assert result["all_selected_approved"] is True
    assert result["results"][0]["translation"] == "свет"
    assert result["results"][0]["approval_policy"] == "lexical-primary-arbitration-v1"
    assert result["results"][0]["selection_revision_id"] > 0

    revisions = stage20.get_stage20_revisions(database, result["sense_translation_run_id"])
    assert len(revisions) == 1
    assert revisions[0]["translation_text"] == "свет"
    assert revisions[0]["approved"] is True
    with connect(database, readonly=True) as connection:
        candidate_count = connection.execute(
            "SELECT COUNT(*) FROM sense_translation_candidates WHERE stage20_run_id=?",
            (result["sense_translation_run_id"],),
        ).fetchone()[0]
    assert candidate_count >= 2

    cached = stage20.run_stage20(
        database,
        sense_induction_run_id=sense_run_id,
        parameters={"beam_size": 2, "num_hypotheses": 2, "maximum_candidates_per_sense": 2},
    )
    assert cached["cache_hit"] is True
    assert cached["sense_translation_run_id"] == result["sense_translation_run_id"]


def test_stage20_fails_closed_when_real_provider_has_no_admissible_ru_candidate(tmp_path: Path, monkeypatch) -> None:
    database, sense_run_id = _database(tmp_path)
    monkeypatch.setattr(stage20, "load_opus_asset", lambda: _asset())
    monkeypatch.setattr(stage20, "OpusTranslator", _IdentityTranslator)
    with pytest.raises(RuntimeError, match="full-sense real OPUS coverage failed"):
        stage20.run_stage20(
            database,
            sense_induction_run_id=sense_run_id,
            parameters={"beam_size": 1, "num_hypotheses": 1},
        )
    with connect(database, readonly=True) as connection:
        run = connection.execute("SELECT id,status FROM stage_runs WHERE stage_number=20").fetchone()
        assert run is not None
        assert run["status"] == "failed"
        assert connection.execute("SELECT COUNT(*) FROM sense_translation_revisions").fetchone()[0] == 0


def test_stage20_probe_policy_rejects_non_russian_and_prefers_infinitive_for_verbs() -> None:
    assert stage20.admissible_ru_candidate("light", "light") == (False, "identity")
    assert stage20.admissible_ru_candidate("light", "illumination") == (False, "no_cyrillic")
    assert stage20.admissible_ru_candidate("light", "свет")[0] is True
    probes = stage20.probe_forms("form", "VERB", "word", "ROOT")
    assert probes[0]["kind"] == "verb_argument"
    infinitive = stage20.provider_confidence(
        0,
        "verb_infinitive",
        base_confidence=0.84,
        effective_pos="VERB",
        target="формировать",
        entry_type="word",
    )
    finite = stage20.provider_confidence(
        0,
        "verb_infinitive",
        base_confidence=0.84,
        effective_pos="VERB",
        target="формирует",
        entry_type="word",
    )
    assert infinitive > finite
