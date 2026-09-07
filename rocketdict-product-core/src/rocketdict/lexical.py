from __future__ import annotations

"""Native lexical/sense data model for the maintained Product Core."""

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .database import (
    begin_run,
    connect,
    fail_run,
    finish_run,
    get_run,
    get_run_items,
    transaction,
)
from .lexical_target_evidence import TargetEvidenceError, resolve_target_evidence

CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
OBJECT_DEPENDENCIES = {"dobj", "obj", "pobj"}
POLICY_KEY = "workbench-aligned-content-pos-v5"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lexical_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_lemma TEXT NOT NULL,
    display_lemma TEXT NOT NULL,
    part_of_speech TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(normalized_lemma, part_of_speech, entry_type)
);
CREATE TABLE IF NOT EXISTS lexical_occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    nlp_run_item_id INTEGER NOT NULL REFERENCES run_items(id),
    alignment_run_item_id INTEGER NOT NULL REFERENCES run_items(id),
    sequence_number INTEGER NOT NULL,
    source_start INTEGER NOT NULL,
    source_end INTEGER NOT NULL,
    surface_text TEXT NOT NULL,
    target_evidence_text TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(extraction_run_id, nlp_run_item_id)
);
CREATE INDEX IF NOT EXISTS idx_lexical_occurrences_run
    ON lexical_occurrences(extraction_run_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_lexical_occurrences_entry
    ON lexical_occurrences(lexical_entry_id, extraction_run_id);

CREATE TABLE IF NOT EXISTS lexical_senses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_induction_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    sense_key TEXT NOT NULL,
    target_evidence_key TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(sense_induction_run_id, lexical_entry_id, sense_key)
);
CREATE INDEX IF NOT EXISTS idx_lexical_senses_run
    ON lexical_senses(sense_induction_run_id, id);
"""


def ensure_schema(connection) -> None:  # type: ignore[no-untyped-def]
    connection.executescript(_SCHEMA)


def _normalize_lemma(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip()).casefold()
    return value


def _normalize_target(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _token_normalized(row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    payload = dict(row.get("payload") or {})
    flags = dict(payload.get("flags") or {})
    payload["flags"] = flags
    repairs: list[str] = []
    pos = str(payload.get("pos") or "X").upper()
    dep = str(payload.get("dependency") or "").casefold()
    text = str(row.get("source_text") or "")
    if pos == "VERB" and dep in OBJECT_DEPENDENCIES:
        payload["pos"] = "NOUN"
        pos = "NOUN"
        repairs.append("verb_object_to_noun")
    if pos in CONTENT_POS and text.isalpha() and bool(flags.get("is_oov")):
        flags["is_oov"] = False
        repairs.append("spacy_is_oov_not_unknown_token")
    if payload.get("entity_type") and pos != "PROPN":
        flags["original_entity_type"] = payload.get("entity_type")
        payload["entity_type"] = None
        payload["entity_iob"] = None
        repairs.append("non_propn_ner_not_entry_type")
    return payload, repairs


def _lineage(database: Path, alignment_run_id: int) -> dict[str, Any]:
    with connect(database, readonly=True) as connection:
        alignment = get_run(connection, alignment_run_id)
        if int(alignment["stage_number"]) != 17 or alignment["status"] != "completed":
            raise RuntimeError("Stage18 requires completed Stage17 alignment")
        alignment_output = dict(alignment.get("output") or {})
        revision = get_run(connection, int(alignment_output["translation_revision_id"]))
        assembly = get_run(connection, int((revision.get("output") or {})["assembly_id"]))
        translation = get_run(connection, int((assembly.get("output") or {})["translation_run_id"]))
        context = get_run(connection, int((translation.get("output") or {})["context_run_id"]))
        nlp = get_run(connection, int((context.get("output") or {})["nlp_run_id"]))
    return {
        "alignment": alignment,
        "revision": revision,
        "assembly": assembly,
        "translation": translation,
        "context": context,
        "nlp": nlp,
    }


def run_stage18(
    database: Path | str,
    *,
    alignment_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = POLICY_KEY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != POLICY_KEY:
        raise RuntimeError(f"Unsupported Stage18 Product policy {implementation!r}")
    parameters = dict(parameters or {})
    lineage = _lineage(database, int(alignment_run_id))
    nlp_run_id = int(lineage["nlp"]["id"])
    translation_run_id = int(lineage["translation"]["id"])
    input_identity = {
        "alignment_run_id": int(alignment_run_id),
        "alignment_output_sha256": str(lineage["alignment"].get("output_sha256") or ""),
        "nlp_run_id": nlp_run_id,
        "nlp_output_sha256": str(lineage["nlp"].get("output_sha256") or ""),
        "translation_run_id": translation_run_id,
        "translation_output_sha256": str(lineage["translation"].get("output_sha256") or ""),
    }
    with transaction(database) as connection:
        ensure_schema(connection)
        run_id, cache_hit = begin_run(
            connection,
            stage_number=18,
            stage_key="lexical_extraction",
            implementation=implementation,
            input_identity=input_identity,
            parameters=parameters,
        )
    if cache_hit:
        with connect(database, readonly=True) as connection:
            cached = get_run(connection, run_id)
        return {**dict(cached.get("output") or {}), "cache_hit": True}
    try:
        with connect(database, readonly=True) as connection:
            nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
            alignments = get_run_items(
                connection, int(alignment_run_id), kind="alignment_segment"
            )
            translation_segments = get_run_items(
                connection, translation_run_id, kind="translation_segment"
            )
        translation_by_span: dict[tuple[int, int], dict[str, Any]] = {}
        for segment in translation_segments:
            key = (int(segment["source_start"]), int(segment["source_end"]))
            if key in translation_by_span:
                raise RuntimeError(
                    f"Stage18 translation lineage has duplicate source span {key}"
                )
            translation_by_span[key] = segment

        eligible: list[tuple[dict[str, Any], dict[str, Any], list[str]]] = []
        for token in nlp_tokens:
            payload, repairs = _token_normalized(token)
            pos = str(payload.get("pos") or "X").upper()
            text = str(token.get("source_text") or "")
            if pos not in CONTENT_POS or not text.strip() or not any(ch.isalpha() for ch in text):
                continue
            eligible.append((token, payload, repairs))
        occurrences: list[dict[str, Any]] = []
        uncovered: list[dict[str, Any]] = []
        table_scoped_count = 0
        for token, payload, repairs in eligible:
            start = int(token["source_start"])
            end = int(token["source_end"])
            matches = [
                row
                for row in alignments
                if int(row["source_start"]) <= start and int(row["source_end"]) >= end
            ]
            if len(matches) != 1:
                uncovered.append(
                    {
                        "nlp_run_item_id": int(token["id"]),
                        "source_start": start,
                        "source_end": end,
                        "surface": token.get("source_text"),
                        "alignment_match_count": len(matches),
                    }
                )
                continue
            alignment = matches[0]
            alignment_span = (
                int(alignment["source_start"]),
                int(alignment["source_end"]),
            )
            translation_segment = translation_by_span.get(alignment_span)
            if translation_segment is None:
                uncovered.append(
                    {
                        "nlp_run_item_id": int(token["id"]),
                        "source_start": start,
                        "source_end": end,
                        "surface": token.get("source_text"),
                        "reason": "alignment_has_no_exact_stage12_translation_segment",
                        "alignment_span": list(alignment_span),
                    }
                )
                continue
            try:
                target_evidence = resolve_target_evidence(
                    token_start=start,
                    token_end=end,
                    alignment=alignment,
                    translation_segment=translation_segment,
                )
            except TargetEvidenceError as exc:
                uncovered.append(
                    {
                        "nlp_run_item_id": int(token["id"]),
                        "source_start": start,
                        "source_end": end,
                        "surface": token.get("source_text"),
                        "reason": "target_evidence_resolution_failed",
                        "detail": str(exc),
                    }
                )
                continue
            table_scoped_count += int(target_evidence.scope == "table_logical_group")

            lemma = _normalize_lemma(str(payload.get("lemma") or token.get("source_text") or ""))
            if not lemma:
                uncovered.append(
                    {
                        "nlp_run_item_id": int(token["id"]),
                        "source_start": start,
                        "source_end": end,
                        "surface": token.get("source_text"),
                        "reason": "empty_normalized_lemma",
                    }
                )
                continue
            pos = str(payload.get("pos") or "X").upper()
            entry_type = "proper_noun" if pos == "PROPN" else "word"
            occurrences.append(
                {
                    "token": token,
                    "payload": payload,
                    "repairs": repairs,
                    "alignment": alignment,
                    "translation_segment": translation_segment,
                    "target_evidence": target_evidence,
                    "lemma": lemma,
                    "pos": pos,
                    "entry_type": entry_type,
                }
            )
        if uncovered:
            raise RuntimeError(
                "Stage18 lexical coverage is incomplete for Product content-token scope: "
                + json.dumps(uncovered[:20], ensure_ascii=False)
            )
        with transaction(database) as connection:
            ensure_schema(connection)
            connection.execute(
                "DELETE FROM lexical_occurrences WHERE extraction_run_id=?", (run_id,)
            )
            entry_ids: set[int] = set()
            for sequence, row in enumerate(occurrences):
                existing = connection.execute(
                    """
                    SELECT id FROM lexical_entries
                    WHERE normalized_lemma=? AND part_of_speech=? AND entry_type=?
                    """,
                    (row["lemma"], row["pos"], row["entry_type"]),
                ).fetchone()
                if existing is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO lexical_entries(
                            normalized_lemma,display_lemma,part_of_speech,entry_type
                        ) VALUES(?,?,?,?)
                        """,
                        (
                            row["lemma"],
                            str(row["token"].get("source_text") or row["lemma"]),
                            row["pos"],
                            row["entry_type"],
                        ),
                    )
                    entry_id = int(cursor.lastrowid)
                else:
                    entry_id = int(existing["id"])
                entry_ids.add(entry_id)
                target_evidence = row["target_evidence"]
                evidence = {
                    "policy": POLICY_KEY,
                    "repairs": list(row["repairs"]),
                    "token": row["payload"],
                    "alignment_confidence": (row["alignment"].get("payload") or {}).get(
                        "confidence"
                    ),
                    "target_evidence_scope": target_evidence.scope,
                    "target_evidence": target_evidence.metadata,
                    "translation_segment_id": int(row["translation_segment"]["id"]),
                }
                connection.execute(
                    """
                    INSERT INTO lexical_occurrences(
                        extraction_run_id,lexical_entry_id,nlp_run_item_id,alignment_run_item_id,
                        sequence_number,source_start,source_end,surface_text,target_evidence_text,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        entry_id,
                        int(row["token"]["id"]),
                        int(row["alignment"]["id"]),
                        sequence,
                        int(row["token"]["source_start"]),
                        int(row["token"]["source_end"]),
                        str(row["token"].get("source_text") or ""),
                        target_evidence.text,
                        json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                    ),
                )
            output = {
                "schema": "rocketdict-product-stage18/1",
                "policy": POLICY_KEY,
                "extraction_run_id": run_id,
                "stage_result_id": run_id,
                "alignment_run_id": int(alignment_run_id),
                "nlp_run_id": nlp_run_id,
                "translation_run_id": translation_run_id,
                "source_mode": "aligned",
                "target_evidence_policy": "narrowest-stage12-structural-scope-v1",
                "eligible_token_count": len(eligible),
                "occurrence_count": len(occurrences),
                "lexical_entry_count": len(entry_ids),
                "table_scoped_target_evidence_count": table_scoped_count,
                "coverage_complete": True,
                "uncovered_token_count": 0,
            }
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        try:
            with transaction(database) as connection:
                fail_run(connection, run_id, {"type": type(exc).__name__, "message": str(exc)})
        except Exception:
            pass
        raise


def run_stage19(
    database: Path | str,
    *,
    extraction_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "deterministic-context-target-graph",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    parameters = dict(parameters or {})
    with connect(database, readonly=True) as connection:
        ensure_schema(connection)
        extraction = get_run(connection, int(extraction_run_id))
        if int(extraction["stage_number"]) != 18 or extraction["status"] != "completed":
            raise RuntimeError("Stage19 requires a completed Stage18 extraction")
        rows = connection.execute(
            """
            SELECT o.*, e.normalized_lemma, e.part_of_speech, e.entry_type
            FROM lexical_occurrences o
            JOIN lexical_entries e ON e.id=o.lexical_entry_id
            WHERE o.extraction_run_id=?
            ORDER BY o.lexical_entry_id,o.sequence_number,o.id
            """,
            (int(extraction_run_id),),
        ).fetchall()
    input_identity = {
        "extraction_run_id": int(extraction_run_id),
        "extraction_output_sha256": str(extraction.get("output_sha256") or ""),
    }
    with transaction(database) as connection:
        ensure_schema(connection)
        run_id, cache_hit = begin_run(
            connection,
            stage_number=19,
            stage_key="sense_induction",
            implementation=implementation,
            input_identity=input_identity,
            parameters=parameters,
        )
    if cache_hit:
        with connect(database, readonly=True) as connection:
            cached = get_run(connection, run_id)
        return {**dict(cached.get("output") or {}), "cache_hit": True}
    try:
        grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for raw in rows:
            row = dict(raw)
            target_key = _normalize_target(str(row.get("target_evidence_text") or ""))
            # Empty target evidence is a distinct auditable singleton class, not
            # silently dropped. Stage20 may later refuse/resolve it.
            grouped.setdefault((int(row["lexical_entry_id"]), target_key), []).append(row)
        with transaction(database) as connection:
            ensure_schema(connection)
            connection.execute(
                "DELETE FROM lexical_senses WHERE sense_induction_run_id=?", (run_id,)
            )
            sense_ids: list[int] = []
            by_entry: dict[int, int] = {}
            for entry_id, target_key in sorted(grouped, key=lambda key: (key[0], key[1])):
                occurrence_rows = grouped[(entry_id, target_key)]
                sense_identity = {
                    "entry_id": entry_id,
                    "target_evidence_key": target_key,
                    "occurrence_ids": [int(row["id"]) for row in occurrence_rows],
                }
                sense_key = hashlib.sha256(
                    json.dumps(
                        sense_identity,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                evidence = {
                    "algorithm": "deterministic-context-target-graph-v1",
                    "target_evidence_key": target_key,
                    "occurrences": [
                        {
                            "occurrence_id": int(row["id"]),
                            "source_start": int(row["source_start"]),
                            "source_end": int(row["source_end"]),
                            "surface_text": str(row["surface_text"]),
                            "target_evidence_text": str(row["target_evidence_text"]),
                        }
                        for row in occurrence_rows
                    ],
                }
                cursor = connection.execute(
                    """
                    INSERT INTO lexical_senses(
                        sense_induction_run_id,lexical_entry_id,sense_key,target_evidence_key,
                        occurrence_count,evidence_json
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        entry_id,
                        sense_key,
                        target_key,
                        len(occurrence_rows),
                        json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                    ),
                )
                sense_ids.append(int(cursor.lastrowid))
                by_entry[entry_id] = by_entry.get(entry_id, 0) + 1
            output = {
                "schema": "rocketdict-product-stage19/1",
                "sense_induction_run_id": run_id,
                "stage_result_id": run_id,
                "extraction_run_id": int(extraction_run_id),
                "lexical_entry_count": len(by_entry),
                "lexical_sense_count": len(sense_ids),
                "occurrence_count": len(rows),
                "coverage_complete": sum(
                    len(group) for group in grouped.values()
                ) == len(rows),
                "singleton_policy": "singleton-safe-v1-audited",
                "sense_ids_sha256": hashlib.sha256(
                    json.dumps(sense_ids, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
            }
            if not output["coverage_complete"]:
                raise RuntimeError("Stage19 sense occurrence coverage is incomplete")
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        try:
            with transaction(database) as connection:
                fail_run(connection, run_id, {"type": type(exc).__name__, "message": str(exc)})
        except Exception:
            pass
        raise


def lexical_snapshot(database: Path | str, *, extraction_run_id: int | None = None, sense_run_id: int | None = None) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    with connect(database, readonly=True) as connection:
        ensure_schema(connection)
        entries = [dict(row) for row in connection.execute(
            "SELECT * FROM lexical_entries ORDER BY id"
        ).fetchall()]
        occurrences = []
        if extraction_run_id is not None:
            occurrences = [dict(row) for row in connection.execute(
                "SELECT * FROM lexical_occurrences WHERE extraction_run_id=? ORDER BY sequence_number,id",
                (int(extraction_run_id),),
            ).fetchall()]
            for row in occurrences:
                row["evidence"] = json.loads(row.pop("evidence_json"))
        senses = []
        if sense_run_id is not None:
            senses = [dict(row) for row in connection.execute(
                "SELECT * FROM lexical_senses WHERE sense_induction_run_id=? ORDER BY id",
                (int(sense_run_id),),
            ).fetchall()]
            for row in senses:
                row["evidence"] = json.loads(row.pop("evidence_json"))
    return {
        "schema": "rocketdict-product-core-lexical-snapshot/1",
        "entries": entries,
        "occurrences": occurrences,
        "senses": senses,
    }
