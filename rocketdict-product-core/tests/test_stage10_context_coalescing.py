from __future__ import annotations

from pathlib import Path

from rocketdict.context_sentence_boundaries import (
    STAGE10_BOUNDARY_POLICY,
    STAGE10_CONTEXT_IMPLEMENTATION_V1,
    STAGE10_CONTEXT_IMPLEMENTATION_V2,
)
from rocketdict.database import (
    begin_run,
    connect,
    database_path,
    finish_run,
    replace_run_items,
    transaction,
)
from rocketdict.importing.cli import import_source
from rocketdict.interpretation.cli import interpret_source
from rocketdict.stages import run_stage10


def _seed_nlp_run(db: Path, document_version_id: int, content: str) -> int:
    words = ["Nor", "do", "I", "see", "but", "that", "light", "returns", ".", "Next", "."]
    sentence_indices = [0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2]
    cursor = 0
    items = []
    for token_index, (word, sentence_index) in enumerate(zip(words, sentence_indices, strict=True)):
        start = content.index(word, cursor)
        end = start + len(word)
        cursor = end
        items.append(
            {
                "sequence_number": token_index,
                "kind": "nlp_token",
                "source_start": start,
                "source_end": end,
                "source_text": word,
                "target_text": None,
                "payload": {
                    "token_index": token_index,
                    "lemma": word.casefold(),
                    "pos": "PRON" if word == "I" else "X",
                    "sentence_index": sentence_index,
                    "flags": {"is_space": False, "is_punct": word == "."},
                },
            }
        )
    with transaction(db) as connection:
        run_id, cached = begin_run(
            connection,
            stage_number=8,
            stage_key="nlp_analysis",
            implementation="test-spacy-boundaries",
            input_identity={"document_version_id": document_version_id, "test": "stage10-v2"},
            parameters={},
        )
        assert cached is False
        replace_run_items(connection, run_id, items)
        finish_run(
            connection,
            run_id,
            {
                "schema": "rocketdict-product-stage8/1",
                "nlp_run_id": run_id,
                "document_version_id": document_version_id,
                "token_count": len(items),
                "sentence_count": 3,
                "coverage_complete": True,
            },
        )
    return run_id


def test_stage10_v2_coalesces_false_parser_boundary_and_invalidates_v1_cache(tmp_path: Path) -> None:
    data = tmp_path / "data"
    source = tmp_path / "sample.txt"
    content = "Nor do I see but that light returns. Next."
    source.write_text(content, encoding="utf-8")
    imported = import_source(source, data_root=data)
    interpreted = interpret_source(
        int(imported["import_event_id"]), data_root=data, declared_format="txt"
    )
    db = database_path(data)
    nlp_run_id = _seed_nlp_run(db, int(interpreted["document_version_id"]), content)

    legacy = run_stage10(
        db,
        nlp_run_id=nlp_run_id,
        implementation=STAGE10_CONTEXT_IMPLEMENTATION_V1,
    )
    assert legacy["schema"] == "rocketdict-product-stage10/1"
    assert legacy["sentence_count"] == 3
    assert legacy["cache_hit"] is False

    repaired = run_stage10(db, nlp_run_id=nlp_run_id)
    assert repaired["schema"] == "rocketdict-product-stage10/2"
    assert repaired["implementation"] == STAGE10_CONTEXT_IMPLEMENTATION_V2
    assert repaired["spacy_sentence_count"] == 3
    assert repaired["sentence_count"] == 2
    assert repaired["coalesced_boundary_count"] == 1
    assert repaired["coalesced_context_count"] == 1
    assert repaired["boundary_policy"] == STAGE10_BOUNDARY_POLICY
    assert repaired["context_run_id"] != legacy["context_run_id"]
    assert repaired["cache_hit"] is False

    with connect(db, readonly=True) as connection:
        rows = connection.execute(
            "SELECT * FROM run_items WHERE run_id=? AND kind='context_sentence' ORDER BY sequence_number",
            (int(repaired["context_run_id"]),),
        ).fetchall()
    assert len(rows) == 2
    assert rows[0]["source_text"] == "Nor do I see but that light returns. "

    import json

    first_payload = json.loads(str(rows[0]["payload_json"]))
    assert first_payload["sentence_index"] == 0
    assert first_payload["spacy_sentence_indices"] == [0, 1]
    assert first_payload["spacy_sentence_count"] == 2
    assert first_payload["coalesced_boundary_count"] == 1
    assert first_payload["coalesced_boundaries"][0]["reason"] == "lowercase_continuation_without_terminal"

    cached = run_stage10(db, nlp_run_id=nlp_run_id)
    assert cached["context_run_id"] == repaired["context_run_id"]
    assert cached["cache_hit"] is True
