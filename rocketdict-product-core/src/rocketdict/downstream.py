from __future__ import annotations

"""Maintained Product downstream: Stage20 sense translation through Stage25 export.

This module replaces historical ORM-bound helper execution with explicit SQLite
storage owned by the maintained Product Core.  Real OPUS remains the only MT
provider; CEFR-J and CMUdict are fail-closed external evidence sources; examples
are sense-scoped and derived from the accepted document alignment; cards/sets
are immutable content-addressed revisions.
"""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

from .database import (
    begin_run,
    canonical_json,
    canonical_sha256,
    connect,
    fail_run,
    finish_run,
    get_run,
    get_run_items,
    transaction,
    utcnow,
)
from .evidence import (
    CEFRJ_SHA256,
    cmudict_status,
    load_cefrj_rows,
    load_cmudict,
    match_cefrj_entry,
)
from .lexical import ensure_schema as ensure_lexical_schema
from .runtime import OpusTranslator, load_opus_asset

STAGE20_POLICY = "contextual-lexical-opus-v3"
STAGE21_POLICY = "cefrj-vocabulary-1.5"
STAGE22_POLICY = "cmudict-production"
STAGE23_POLICY = "examples-current"
STAGE24_POLICY = "cards-current"
STAGE25_POLICY = "export-json"
SET_ASSEMBLY_POLICY = "cards-set-assembly-v1"

VERB_ENTRY_TYPES = {"phrasal_verb", "prepositional_verb"}
OBJECT_DEPENDENCIES = {"dobj", "obj", "pobj", "nsubj", "nsubjpass"}

_DOWNSTREAM_SCHEMA = """
CREATE TABLE IF NOT EXISTS sense_translation_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage20_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_sense_id INTEGER NOT NULL REFERENCES lexical_senses(id),
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    selected_translation TEXT NOT NULL,
    selected_normalized TEXT NOT NULL,
    selected_score REAL NOT NULL,
    candidates_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    approved INTEGER NOT NULL CHECK(approved IN (0,1)),
    content_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(stage20_run_id, lexical_sense_id)
);
CREATE INDEX IF NOT EXISTS idx_sense_translation_sense
    ON sense_translation_revisions(lexical_sense_id, id);

CREATE TABLE IF NOT EXISTS cefr_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage21_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    level TEXT,
    match_kind TEXT NOT NULL,
    conflict_count INTEGER NOT NULL,
    source_sha256 TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(stage21_run_id, lexical_entry_id)
);
CREATE INDEX IF NOT EXISTS idx_cefr_entry ON cefr_assignments(lexical_entry_id,id);

CREATE TABLE IF NOT EXISTS pronunciations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage22_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    form TEXT NOT NULL,
    strategy TEXT NOT NULL,
    variants_json TEXT NOT NULL,
    unknown INTEGER NOT NULL CHECK(unknown IN (0,1)),
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(stage22_run_id, lexical_entry_id)
);
CREATE INDEX IF NOT EXISTS idx_pron_entry ON pronunciations(lexical_entry_id,id);

CREATE TABLE IF NOT EXISTS sense_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage23_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_sense_id INTEGER NOT NULL REFERENCES lexical_senses(id),
    lexical_occurrence_id INTEGER NOT NULL REFERENCES lexical_occurrences(id),
    alignment_run_item_id INTEGER NOT NULL REFERENCES run_items(id),
    role TEXT NOT NULL,
    source_text TEXT NOT NULL,
    target_text TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(stage23_run_id, lexical_sense_id, role)
);
CREATE INDEX IF NOT EXISTS idx_examples_sense ON sense_examples(lexical_sense_id,id);

CREATE TABLE IF NOT EXISTS card_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage24_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_sense_id INTEGER NOT NULL REFERENCES lexical_senses(id),
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    content_json TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(stage24_run_id, lexical_sense_id)
);
CREATE INDEX IF NOT EXISTS idx_cards_sense ON card_revisions(lexical_sense_id,id);

CREATE TABLE IF NOT EXISTS card_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assembly_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    set_name TEXT NOT NULL,
    card_count INTEGER NOT NULL,
    cards_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(assembly_run_id)
);
CREATE TABLE IF NOT EXISTS card_set_members (
    set_revision_id INTEGER NOT NULL REFERENCES card_sets(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    card_revision_id INTEGER NOT NULL REFERENCES card_revisions(id),
    PRIMARY KEY(set_revision_id, sequence_number),
    UNIQUE(set_revision_id, card_revision_id)
);
"""


def ensure_downstream_schema(connection) -> None:  # type: ignore[no-untyped-def]
    ensure_lexical_schema(connection)
    connection.executescript(_DOWNSTREAM_SCHEMA)


def ensure_downstream_database(database: Path | str) -> None:
    """Create/upgrade maintained downstream tables on a writable connection.

    Read-only evidence paths must never attempt schema DDL.  Call this before
    opening the corresponding read-only snapshot.
    """
    database = Path(database).expanduser().resolve()
    with transaction(database) as connection:
        ensure_downstream_schema(connection)


def _start(
    database: Path,
    *,
    stage_number: int,
    stage_key: str,
    implementation: str,
    input_identity: dict[str, Any],
    parameters: dict[str, Any],
) -> tuple[int, dict[str, Any] | None]:
    with transaction(database) as connection:
        ensure_downstream_schema(connection)
        run_id, cache_hit = begin_run(
            connection,
            stage_number=stage_number,
            stage_key=stage_key,
            implementation=implementation,
            input_identity=input_identity,
            parameters=parameters,
        )
    if not cache_hit:
        return run_id, None
    with connect(database, readonly=True) as connection:
        run = get_run(connection, run_id)
    output = run.get("output")
    if not isinstance(output, dict):
        raise RuntimeError(f"Completed downstream run {run_id} lacks output")
    return run_id, {**output, "cache_hit": True}


def _fail(database: Path, run_id: int, exc: BaseException) -> None:
    try:
        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            fail_run(
                connection,
                run_id,
                {"type": type(exc).__name__, "message": str(exc)},
            )
    except Exception:
        pass


def normalize_lexical_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").strip()
    value = re.sub(
        r"^[\s\.,;:!?…\"'«»()\[\]{}]+|[\s\.,;:!?…\"'«»()\[\]{}]+$",
        "",
        value,
    )
    return re.sub(r"\s+", " ", value).casefold().strip()


def _effective_probe_pos(pos: str | None, dependency: str | None) -> tuple[str, str]:
    normalized = str(pos or "X").upper()
    dep = str(dependency or "").casefold()
    if normalized == "VERB" and dep in OBJECT_DEPENDENCIES:
        return "NOUN", "dependency_pos_repair"
    return normalized, "declared_pos"


def _probe_forms(
    lemma: str,
    part_of_speech: str | None,
    entry_type: str | None,
    dependency: str | None,
) -> list[dict[str, Any]]:
    lemma = re.sub(r"\s+", " ", lemma.strip())
    if not lemma:
        return []
    effective_pos, pos_reason = _effective_probe_pos(part_of_speech, dependency)
    etype = str(entry_type or "").casefold()
    title = lemma[:1].upper() + lemma[1:]
    if etype in VERB_ENTRY_TYPES:
        effective_pos = "VERB"
        pos_reason = "verb_mwe_entry_type"
        values = [
            ("verb_argument", f"to {lemma} something", 0.98),
            ("verb_infinitive", f"to {lemma}", 0.84),
            ("lemma", lemma, 0.78),
            ("titlecase", title, 0.70),
        ]
    elif effective_pos == "VERB":
        values = [
            ("verb_argument", f"to {lemma} something", 0.98),
            ("verb_infinitive", f"to {lemma}", 0.84),
            ("lemma", lemma, 0.80),
            ("titlecase", title, 0.68),
        ]
    elif effective_pos == "ADJ":
        values = [
            ("adjective_copula", f"is {lemma}", 0.98),
            ("lemma", lemma, 0.90),
            ("titlecase", title, 0.72),
        ]
    elif effective_pos in {"NOUN", "PROPN"}:
        values = [("titlecase", title, 0.96), ("lemma", lemma, 0.90)]
    else:
        values = [("titlecase", title, 0.92), ("lemma", lemma, 0.88)]
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kind, text, confidence in values:
        if text in seen:
            continue
        seen.add(text)
        result.append(
            {
                "kind": kind,
                "text": text,
                "base_confidence": confidence,
                "effective_pos": effective_pos,
                "pos_reason": pos_reason,
            }
        )
    return result


def _clean_probe_target(target: str, probe_kind: str) -> tuple[str, str | None]:
    cleaned = target.strip().strip(" .,!;:…")
    transform = None
    if probe_kind == "verb_argument":
        stripped = re.sub(
            r"\s+(?:что(?:-|\s)?то|что(?:-|\s)?нибудь|это)\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if stripped != cleaned:
            cleaned = stripped
            transform = "strip_generic_argument"
    return cleaned, transform


def _looks_like_russian_infinitive(value: str) -> bool:
    first = normalize_lexical_text(value).split(" ", 1)[0]
    return bool(re.search(r"(?:ть|ться|ти|тись|чь|чься)$", first))


def _admissible_ru_candidate(
    source_lemma: str,
    target: str,
    *,
    entry_type: str | None,
) -> tuple[bool, str | None]:
    cleaned = target.strip()
    normalized = normalize_lexical_text(cleaned)
    if not normalized:
        return False, "empty"
    if normalized == normalize_lexical_text(source_lemma):
        return False, "identity"
    cyr = len(re.findall(r"[А-Яа-яЁё]", cleaned))
    latin = len(re.findall(r"[A-Za-z]", cleaned))
    if cyr == 0:
        return False, "no_cyrillic"
    if latin:
        return False, "latin_leakage"
    if re.fullmatch(r"[\W\d_]+", cleaned, re.UNICODE):
        return False, "numeric_or_punctuation_only"
    if any(ch.isdigit() for ch in cleaned) and not any(ch.isdigit() for ch in source_lemma):
        return False, "unlicensed_numeric_addition"
    if cleaned and not (cleaned[0].isalnum() or cleaned[0] in {'«', '"'}):
        return False, "leading_symbol_noise"
    if normalized.startswith(("чтобы ", "для того чтобы ")):
        return False, "synthetic_probe_wrapper"
    if str(entry_type or "").casefold() in VERB_ENTRY_TYPES:
        if len(re.findall(r"[А-Яа-яЁё]+", cleaned)) < 2:
            return False, "incomplete_multiword_translation"
    return True, None


def _provider_confidence(
    rank: int,
    probe_kind: str,
    *,
    base_confidence: float,
    effective_pos: str,
    target: str,
    entry_type: str,
) -> float:
    score = float(base_confidence) - 0.045 * int(rank)
    is_infinitive = effective_pos == "VERB" and _looks_like_russian_infinitive(target)
    if effective_pos == "VERB":
        if is_infinitive:
            score = max(score, 0.84) + 0.08
        else:
            score -= 0.20
    if entry_type.casefold() in VERB_ENTRY_TYPES and is_infinitive:
        score += 0.05
    return round(min(0.99, max(0.52, score)), 4)


def _context_overlap(candidate: str, aligned_target: str) -> float:
    candidate_norm = normalize_lexical_text(candidate)
    target_norm = normalize_lexical_text(aligned_target)
    if not candidate_norm or not target_norm:
        return 0.0
    if candidate_norm in target_norm:
        return 1.0
    candidate_words = set(re.findall(r"[а-яё]+", candidate_norm, flags=re.IGNORECASE))
    target_words = set(re.findall(r"[а-яё]+", target_norm, flags=re.IGNORECASE))
    if not candidate_words:
        return 0.0
    return len(candidate_words & target_words) / len(candidate_words)


def _stage19_rows(database: Path, sense_induction_run_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ensure_downstream_database(database)
    with connect(database, readonly=True) as connection:
        run = get_run(connection, int(sense_induction_run_id))
        if int(run["stage_number"]) != 19 or run["status"] != "completed":
            raise RuntimeError("Stage20 requires a completed maintained Stage19 run")
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT s.*,e.normalized_lemma,e.display_lemma,e.part_of_speech,e.entry_type
                FROM lexical_senses s
                JOIN lexical_entries e ON e.id=s.lexical_entry_id
                WHERE s.sense_induction_run_id=?
                ORDER BY s.id
                """,
                (int(sense_induction_run_id),),
            ).fetchall()
        ]
        extraction_run_id = int((run.get("input_identity") or {}).get("extraction_run_id") or 0)
        occurrence_rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM lexical_occurrences WHERE extraction_run_id=? ORDER BY id",
                (extraction_run_id,),
            ).fetchall()
        ]
    occurrences = {int(row["id"]): row for row in occurrence_rows}
    for row in rows:
        evidence = json.loads(str(row.pop("evidence_json")))
        row["sense_evidence"] = evidence
        occurrence_ids = [
            int(item.get("occurrence_id") or 0)
            for item in list(evidence.get("occurrences") or [])
            if int(item.get("occurrence_id") or 0) > 0
        ]
        first = occurrences.get(occurrence_ids[0]) if occurrence_ids else None
        lexical_evidence = json.loads(str(first["evidence_json"])) if first else {}
        token = dict(lexical_evidence.get("token") or {})
        row["dependency"] = token.get("dependency")
    return run, rows


def run_stage20(
    database: Path | str,
    *,
    sense_induction_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE20_POLICY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != STAGE20_POLICY:
        raise RuntimeError(f"Unsupported Stage20 Product policy {implementation!r}")
    parameters = dict(parameters or {})
    beam_size = int(parameters.get("beam_size") or 12)
    num_hypotheses = int(parameters.get("num_hypotheses") or 12)
    maximum_candidates = int(parameters.get("maximum_candidates_per_lemma") or 8)
    batch_size = int(parameters.get("probe_batch_size") or 64)
    if min(beam_size, num_hypotheses, maximum_candidates, batch_size) <= 0:
        raise RuntimeError("Stage20 generation settings must be positive")
    stage19, senses = _stage19_rows(database, int(sense_induction_run_id))
    if not senses:
        raise RuntimeError("Stage20 received no lexical senses")
    asset = load_opus_asset()
    input_identity = {
        "sense_induction_run_id": int(sense_induction_run_id),
        "stage19_output_sha256": str(stage19.get("output_sha256") or ""),
        "opus_revision": asset.revision,
        "opus_archive_sha256": asset.source_archive_sha256,
        "opus_manifest_sha256": asset.manifest_sha256,
        "opus_payload_tree_sha256": asset.payload_tree_sha256,
    }
    run_id, cached = _start(
        database,
        stage_number=20,
        stage_key="sense_translation",
        implementation=implementation,
        input_identity=input_identity,
        parameters={
            **parameters,
            "beam_size": beam_size,
            "num_hypotheses": num_hypotheses,
            "maximum_candidates_per_lemma": maximum_candidates,
            "probe_batch_size": batch_size,
            "device": "cpu",
            "compute_type": "float32",
            "network_access": False,
        },
    )
    if cached is not None:
        return cached
    try:
        probe_rows: list[dict[str, Any]] = []
        for sense in senses:
            probes = _probe_forms(
                str(sense["normalized_lemma"]),
                str(sense["part_of_speech"]),
                str(sense["entry_type"]),
                sense.get("dependency"),
            )
            if not probes:
                raise RuntimeError(f"Stage20 produced no lexical probes for sense {sense['id']}")
            for probe in probes:
                probe_rows.append(
                    {
                        "sense": sense,
                        "probe": probe,
                    }
                )
        translator = OpusTranslator(device="cpu", compute_type="float32")
        translated: list[list[dict[str, Any]]] = []
        for offset in range(0, len(probe_rows), batch_size):
            batch = probe_rows[offset : offset + batch_size]
            outputs = translator.translate(
                [str(row["probe"]["text"]) for row in batch],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=64,
            )
            if len(outputs) != len(batch):
                raise RuntimeError("Stage20 OPUS probe batch cardinality mismatch")
            translated.extend(outputs)
        if len(translated) != len(probe_rows):
            raise RuntimeError("Stage20 OPUS probe coverage mismatch")

        by_sense: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row, outputs in zip(probe_rows, translated, strict=True):
            sense = row["sense"]
            probe = row["probe"]
            lemma = str(sense["normalized_lemma"])
            entry_type = str(sense["entry_type"])
            aligned_target = str(sense.get("target_evidence_key") or "")
            for rank, output in enumerate(outputs):
                raw_target = str(output.get("text") or "")
                cleaned, transform = _clean_probe_target(raw_target, str(probe["kind"]))
                accepted, rejection_reason = _admissible_ru_candidate(
                    lemma, cleaned, entry_type=entry_type
                )
                provider = (
                    _provider_confidence(
                        rank,
                        str(probe["kind"]),
                        base_confidence=float(probe["base_confidence"]),
                        effective_pos=str(probe["effective_pos"]),
                        target=cleaned,
                        entry_type=entry_type,
                    )
                    if accepted
                    else None
                )
                overlap = _context_overlap(cleaned, aligned_target) if accepted else 0.0
                selection_score = (
                    round(min(1.0, float(provider) + 0.08 * overlap), 4)
                    if provider is not None
                    else None
                )
                by_sense[int(sense["id"])].append(
                    {
                        "probe_kind": probe["kind"],
                        "probe_text": probe["text"],
                        "effective_pos": probe["effective_pos"],
                        "pos_reason": probe["pos_reason"],
                        "rank": rank,
                        "raw_target": raw_target,
                        "cleaned_target": cleaned,
                        "target_transform": transform,
                        "raw_score": output.get("score"),
                        "accepted": accepted,
                        "rejection_reason": rejection_reason,
                        "provider_confidence": provider,
                        "aligned_context_overlap": round(overlap, 4),
                        "selection_score": selection_score,
                    }
                )

        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            connection.execute(
                "DELETE FROM sense_translation_revisions WHERE stage20_run_id=?",
                (run_id,),
            )
            revision_ids: list[int] = []
            result_rows: list[dict[str, Any]] = []
            for sense in senses:
                candidates = by_sense.get(int(sense["id"]), [])
                accepted_map: dict[str, dict[str, Any]] = {}
                for candidate in candidates:
                    if candidate.get("accepted") is not True:
                        continue
                    key = normalize_lexical_text(str(candidate.get("cleaned_target") or ""))
                    if not key:
                        continue
                    prior = accepted_map.get(key)
                    rank_key = (
                        float(candidate.get("selection_score") or 0.0),
                        float(candidate.get("provider_confidence") or 0.0),
                        -int(candidate.get("rank") or 0),
                    )
                    prior_key = (
                        float(prior.get("selection_score") or 0.0),
                        float(prior.get("provider_confidence") or 0.0),
                        -int(prior.get("rank") or 0),
                    ) if prior else None
                    if prior is None or rank_key > prior_key:
                        accepted_map[key] = candidate
                accepted = sorted(
                    accepted_map.values(),
                    key=lambda item: (
                        -float(item.get("selection_score") or 0.0),
                        -float(item.get("provider_confidence") or 0.0),
                        normalize_lexical_text(str(item.get("cleaned_target") or "")),
                    ),
                )[:maximum_candidates]
                if not accepted:
                    raise RuntimeError(
                        f"Stage20 has no admissible real-MT translation for sense {sense['id']} "
                        f"({sense['normalized_lemma']!r})"
                    )
                selected = accepted[0]
                translation = str(selected["cleaned_target"]).strip()
                content = {
                    "sense_id": int(sense["id"]),
                    "entry_id": int(sense["lexical_entry_id"]),
                    "lemma": str(sense["normalized_lemma"]),
                    "translation": translation,
                    "selected_score": float(selected["selection_score"]),
                    "provider": STAGE20_POLICY,
                    "real_mt": True,
                }
                content_sha = canonical_sha256(content)
                evidence = {
                    "aligned_target_evidence": str(sense.get("target_evidence_key") or ""),
                    "dependency": sense.get("dependency"),
                    "candidate_count": len(candidates),
                    "accepted_candidate_count": len(accepted),
                    "opus_revision": asset.revision,
                    "opus_archive_sha256": asset.source_archive_sha256,
                    "opus_manifest_sha256": asset.manifest_sha256,
                    "opus_payload_tree_sha256": asset.payload_tree_sha256,
                    "network_used": False,
                    "compute_type": "float32",
                }
                cursor = connection.execute(
                    """
                    INSERT INTO sense_translation_revisions(
                        stage20_run_id,lexical_sense_id,lexical_entry_id,selected_translation,
                        selected_normalized,selected_score,candidates_json,evidence_json,approved,
                        content_sha256,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        int(sense["id"]),
                        int(sense["lexical_entry_id"]),
                        translation,
                        normalize_lexical_text(translation),
                        float(selected["selection_score"]),
                        canonical_json(candidates),
                        canonical_json(evidence),
                        1,
                        content_sha,
                        utcnow(),
                    ),
                )
                revision_id = int(cursor.lastrowid)
                revision_ids.append(revision_id)
                result_rows.append(
                    {
                        "sense_id": int(sense["id"]),
                        "entry_id": int(sense["lexical_entry_id"]),
                        "selection_revision_id": revision_id,
                        "generation_run_id": run_id,
                        "translation": translation,
                        "selection_score": float(selected["selection_score"]),
                        "coverage_complete": True,
                    }
                )
            output = {
                "schema": "rocketdict-product-stage20/1",
                "sense_translation_run_id": run_id,
                "stage_result_id": run_id,
                "sense_induction_run_id": int(sense_induction_run_id),
                "sense_count": len(senses),
                "revision_count": len(revision_ids),
                "coverage_complete": len(revision_ids) == len(senses),
                "real_mt": True,
                "network_used": False,
                "provider": STAGE20_POLICY,
                "compute_type": "float32",
                "opus_archive_sha256": asset.source_archive_sha256,
                "revision_ids_sha256": canonical_sha256(revision_ids),
                "results": result_rows,
            }
            if output["coverage_complete"] is not True:
                raise RuntimeError("Stage20 sense translation coverage is incomplete")
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def _entry(database: Path, lexical_entry_id: int) -> dict[str, Any]:
    ensure_downstream_database(database)
    with connect(database, readonly=True) as connection:
        row = connection.execute(
            "SELECT * FROM lexical_entries WHERE id=?", (int(lexical_entry_id),)
        ).fetchone()
    if row is None:
        raise RuntimeError(f"Lexical entry does not exist: {lexical_entry_id}")
    return dict(row)


def run_stage21(
    database: Path | str,
    *,
    lexical_entry_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE21_POLICY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != STAGE21_POLICY:
        raise RuntimeError(f"Unsupported Stage21 Product policy {implementation!r}")
    parameters = dict(parameters or {})
    if parameters.get("use_builtin_smoke_sources") not in {None, False}:
        raise RuntimeError("Product Stage21 forbids builtin smoke CEFR sources")
    entry = _entry(database, int(lexical_entry_id))
    asset, rows = load_cefrj_rows()
    lemma = str(entry["normalized_lemma"]).casefold()
    matched = match_cefrj_entry(
        rows,
        lemma=lemma,
        part_of_speech=str(entry.get("part_of_speech") or ""),
    )
    level = matched["level"]
    match_kind = str(matched["match_kind"])
    conflicts = int(matched["conflict_count"])
    input_identity = {
        "lexical_entry_id": int(lexical_entry_id),
        "entry_identity": canonical_sha256(
            {
                "normalized_lemma": entry["normalized_lemma"],
                "part_of_speech": entry["part_of_speech"],
                "entry_type": entry["entry_type"],
            }
        ),
        "cefrj_sha256": asset["sha256"],
    }
    run_id, cached = _start(
        database,
        stage_number=21,
        stage_key="cefr",
        implementation=implementation,
        input_identity=input_identity,
        parameters={**parameters, "use_builtin_smoke_sources": False, "frequency_inference": False},
    )
    if cached is not None:
        return cached
    try:
        evidence = {
            "dataset": asset["dataset"],
            "source_sha256": asset["sha256"],
            "entry_part_of_speech": str(entry.get("part_of_speech") or ""),
            "expected_cefrj_pos": matched["expected_cefrj_pos"],
            "headword_match_count": matched["headword_match_count"],
            "pos_match_count": matched["pos_match_count"],
            "source_rows": matched["matched_rows"],
            "headword_rows": matched["headword_rows"],
            "builtin_smoke_used": False,
            "frequency_inference_used": False,
            "network_used": False,
        }
        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            connection.execute("DELETE FROM cefr_assignments WHERE stage21_run_id=?", (run_id,))
            cursor = connection.execute(
                """
                INSERT INTO cefr_assignments(
                    stage21_run_id,lexical_entry_id,level,match_kind,conflict_count,
                    source_sha256,evidence_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    int(lexical_entry_id),
                    level,
                    match_kind,
                    conflicts,
                    asset["sha256"],
                    canonical_json(evidence),
                    utcnow(),
                ),
            )
            assignment_id = int(cursor.lastrowid)
            output = {
                "schema": "rocketdict-product-stage21/1",
                "cefr_run_id": run_id,
                "stage_result_id": run_id,
                "cefr_assignment_id": assignment_id,
                "lexical_entry_id": int(lexical_entry_id),
                "level": level,
                "match_kind": match_kind,
                "conflict_count": conflicts,
                "expected_cefrj_pos": matched["expected_cefrj_pos"],
                "headword_match_count": matched["headword_match_count"],
                "pos_match_count": matched["pos_match_count"],
                "source_sha256": asset["sha256"],
                "builtin_smoke_used": False,
                "frequency_inference_used": False,
            }
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def _cmudict_variants(
    form: str,
    dictionary: dict[str, list[list[str]]],
) -> tuple[str, list[list[str]], list[str]]:
    normalized = form.strip().casefold()
    direct = dictionary.get(normalized) or []
    if direct:
        return "exact_form", direct, []
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", form)
    if len(words) <= 1:
        return "unknown_exact_form", [], [form]
    components: list[list[list[str]]] = []
    missing: list[str] = []
    for word in words:
        variants = dictionary.get(word.casefold()) or []
        if variants:
            components.append(variants)
        else:
            missing.append(word)
    if missing:
        return "unknown_mwe_component", [], missing
    # Exact component evidence, deterministic first-variant composition.  All
    # component variants remain in evidence; no phoneme generation is used.
    composed = [[phoneme for variants in components for phoneme in variants[0]]]
    return "exact_word_composition", composed, []


def run_stage22(
    database: Path | str,
    *,
    lexical_entry_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE22_POLICY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != STAGE22_POLICY:
        raise RuntimeError(f"Unsupported Stage22 Product policy {implementation!r}")
    parameters = dict(parameters or {})
    if parameters.get("enable_generated_fallback") not in {None, False}:
        raise RuntimeError("Product Stage22 forbids generated pronunciation fallback")
    entry = _entry(database, int(lexical_entry_id))
    status, dictionary = load_cmudict()
    form = str(entry["normalized_lemma"] or entry["display_lemma"]).strip()
    strategy, variants, missing = _cmudict_variants(form, dictionary)
    unknown = not bool(variants)
    input_identity = {
        "lexical_entry_id": int(lexical_entry_id),
        "entry_identity": canonical_sha256(
            {
                "normalized_lemma": entry["normalized_lemma"],
                "part_of_speech": entry["part_of_speech"],
                "entry_type": entry["entry_type"],
            }
        ),
        "cmudict_package_version": status.get("package_version"),
    }
    run_id, cached = _start(
        database,
        stage_number=22,
        stage_key="pronunciation",
        implementation=implementation,
        input_identity=input_identity,
        parameters={**parameters, "enable_generated_fallback": False},
    )
    if cached is not None:
        return cached
    try:
        evidence = {
            "package": "cmudict",
            "package_version": status.get("package_version"),
            "strategy": strategy,
            "missing_components": missing,
            "generated_fallback": False,
            "network_used": False,
        }
        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            connection.execute("DELETE FROM pronunciations WHERE stage22_run_id=?", (run_id,))
            cursor = connection.execute(
                """
                INSERT INTO pronunciations(
                    stage22_run_id,lexical_entry_id,form,strategy,variants_json,unknown,
                    evidence_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    int(lexical_entry_id),
                    form,
                    strategy,
                    canonical_json(variants),
                    1 if unknown else 0,
                    canonical_json(evidence),
                    utcnow(),
                ),
            )
            pronunciation_id = int(cursor.lastrowid)
            output = {
                "schema": "rocketdict-product-stage22/1",
                "pronunciation_run_id": run_id,
                "stage_result_id": run_id,
                "pronunciation_id": pronunciation_id,
                "lexical_entry_id": int(lexical_entry_id),
                "form": form,
                "strategy": strategy,
                "variants": variants,
                "unknown": unknown,
                "missing_components": missing,
                "generated_fallback": False,
            }
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def _approved_translation(connection, lexical_sense_id: int) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    row = connection.execute(
        """
        SELECT * FROM sense_translation_revisions
        WHERE lexical_sense_id=? AND approved=1
        ORDER BY id DESC LIMIT 1
        """,
        (int(lexical_sense_id),),
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"Sense {lexical_sense_id} has no approved maintained Stage20 translation revision"
        )
    return dict(row)


def run_stage23(
    database: Path | str,
    *,
    lexical_sense_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE23_POLICY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != STAGE23_POLICY:
        raise RuntimeError(f"Unsupported Stage23 Product policy {implementation!r}")
    parameters = dict(parameters or {})
    if parameters.get("corpus_snapshots") not in (None, []):
        raise RuntimeError("Maintained Stage23 currently accepts document-aligned examples only")
    ensure_downstream_database(database)
    with connect(database, readonly=True) as connection:
        sense = connection.execute(
            "SELECT * FROM lexical_senses WHERE id=?", (int(lexical_sense_id),)
        ).fetchone()
        if sense is None:
            raise RuntimeError(f"Lexical sense does not exist: {lexical_sense_id}")
        translation = _approved_translation(connection, int(lexical_sense_id))
        sense_evidence = json.loads(str(sense["evidence_json"]))
        occurrence_ids = [
            int(item.get("occurrence_id") or 0)
            for item in list(sense_evidence.get("occurrences") or [])
            if int(item.get("occurrence_id") or 0) > 0
        ]
        occurrences = []
        for occurrence_id in occurrence_ids:
            row = connection.execute(
                "SELECT * FROM lexical_occurrences WHERE id=?", (occurrence_id,)
            ).fetchone()
            if row is not None:
                occurrences.append(dict(row))
        alignment_ids = [int(row["alignment_run_item_id"]) for row in occurrences]
        alignments = {}
        for alignment_id in alignment_ids:
            row = connection.execute("SELECT * FROM run_items WHERE id=?", (alignment_id,)).fetchone()
            if row is not None:
                alignments[alignment_id] = dict(row)
    input_identity = {
        "lexical_sense_id": int(lexical_sense_id),
        "sense_key": str(sense["sense_key"]),
        "approved_sense_translation_revision_id": int(translation["id"]),
        "approved_sense_translation_content_sha256": str(translation["content_sha256"]),
        "occurrence_ids_sha256": canonical_sha256(occurrence_ids),
    }
    run_id, cached = _start(
        database,
        stage_number=23,
        stage_key="examples",
        implementation=implementation,
        input_identity=input_identity,
        parameters={**parameters, "corpus_snapshots": []},
    )
    if cached is not None:
        return cached
    try:
        selected: list[dict[str, Any]] = []
        seen_alignment: set[int] = set()
        occurrence_by_alignment = {
            int(row["alignment_run_item_id"]): row for row in occurrences
        }
        for alignment_id in alignment_ids:
            if alignment_id in seen_alignment:
                continue
            alignment = alignments.get(alignment_id)
            occurrence = occurrence_by_alignment.get(alignment_id)
            if alignment is None or occurrence is None:
                continue
            seen_alignment.add(alignment_id)
            selected.append(
                {
                    "occurrence": occurrence,
                    "alignment": alignment,
                }
            )
            if len(selected) >= 2:
                break
        if not selected:
            raise RuntimeError(
                f"Stage23 found no provenance-complete aligned example for sense {lexical_sense_id}"
            )
        example_ids: list[int] = []
        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            connection.execute("DELETE FROM sense_examples WHERE stage23_run_id=?", (run_id,))
            for index, item in enumerate(selected):
                occurrence = item["occurrence"]
                alignment = item["alignment"]
                role = "primary" if index == 0 else "secondary"
                evidence = {
                    "scope_contract": "stage23-sense-scope-v2",
                    "approved_sense_translation_revision_id": int(translation["id"]),
                    "approved_sense_translation_content_sha256": str(translation["content_sha256"]),
                    "alignment_run_item_id": int(alignment["id"]),
                    "lexical_occurrence_id": int(occurrence["id"]),
                }
                cursor = connection.execute(
                    """
                    INSERT INTO sense_examples(
                        stage23_run_id,lexical_sense_id,lexical_occurrence_id,alignment_run_item_id,
                        role,source_text,target_text,evidence_json,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        int(lexical_sense_id),
                        int(occurrence["id"]),
                        int(alignment["id"]),
                        role,
                        str(alignment["source_text"] or ""),
                        str(alignment["target_text"] or ""),
                        canonical_json(evidence),
                        utcnow(),
                    ),
                )
                example_ids.append(int(cursor.lastrowid))
            output = {
                "schema": "rocketdict-product-stage23/1",
                "example_run_id": run_id,
                "stage_result_id": run_id,
                "lexical_sense_id": int(lexical_sense_id),
                "approved_sense_translation_revision_id": int(translation["id"]),
                "scope_contract": "stage23-sense-scope-v2",
                "example_ids": example_ids,
                "candidate_count": len(selected),
                "primary_missing": False,
                "secondary_missing": len(selected) < 2,
                "corpus_smoke_disabled": True,
            }
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def _latest_entry_evidence(connection, table: str, entry_id: int) -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
    if table not in {"cefr_assignments", "pronunciations"}:
        raise ValueError(table)
    row = connection.execute(
        f"SELECT * FROM {table} WHERE lexical_entry_id=? ORDER BY id DESC LIMIT 1",
        (int(entry_id),),
    ).fetchone()
    return dict(row) if row is not None else None


def run_stage24(
    database: Path | str,
    *,
    lexical_sense_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE24_POLICY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != STAGE24_POLICY:
        raise RuntimeError(f"Unsupported Stage24 Product policy {implementation!r}")
    parameters = dict(parameters or {})
    ensure_downstream_database(database)
    with connect(database, readonly=True) as connection:
        sense = connection.execute(
            """
            SELECT s.*,e.normalized_lemma,e.display_lemma,e.part_of_speech,e.entry_type
            FROM lexical_senses s JOIN lexical_entries e ON e.id=s.lexical_entry_id
            WHERE s.id=?
            """,
            (int(lexical_sense_id),),
        ).fetchone()
        if sense is None:
            raise RuntimeError(f"Lexical sense does not exist: {lexical_sense_id}")
        sense = dict(sense)
        translation = _approved_translation(connection, int(lexical_sense_id))
        cefr = _latest_entry_evidence(connection, "cefr_assignments", int(sense["lexical_entry_id"]))
        pronunciation = _latest_entry_evidence(connection, "pronunciations", int(sense["lexical_entry_id"]))
        examples = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM sense_examples WHERE lexical_sense_id=? ORDER BY id",
                (int(lexical_sense_id),),
            ).fetchall()
        ]
    if cefr is None:
        raise RuntimeError(f"Stage24 requires Stage21 CEFR evidence for entry {sense['lexical_entry_id']}")
    if pronunciation is None:
        raise RuntimeError(
            f"Stage24 requires Stage22 pronunciation evidence for entry {sense['lexical_entry_id']}"
        )
    if not examples:
        raise RuntimeError(f"Stage24 requires Stage23 examples for sense {lexical_sense_id}")
    input_identity = {
        "lexical_sense_id": int(lexical_sense_id),
        "sense_key": str(sense["sense_key"]),
        "translation_revision_id": int(translation["id"]),
        "translation_content_sha256": str(translation["content_sha256"]),
        "cefr_assignment_id": int(cefr["id"]),
        "pronunciation_id": int(pronunciation["id"]),
        "example_ids": [int(row["id"]) for row in examples],
    }
    run_id, cached = _start(
        database,
        stage_number=24,
        stage_key="cards",
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        card = {
            "lexical_sense_id": int(lexical_sense_id),
            "lexical_entry_id": int(sense["lexical_entry_id"]),
            "lemma": str(sense["display_lemma"] or sense["normalized_lemma"]),
            "normalized_lemma": str(sense["normalized_lemma"]),
            "part_of_speech": str(sense["part_of_speech"]),
            "entry_type": str(sense["entry_type"]),
            "translation": str(translation["selected_translation"]),
            "translation_revision_id": int(translation["id"]),
            "cefr": {
                "level": cefr.get("level"),
                "match_kind": str(cefr["match_kind"]),
                "assignment_id": int(cefr["id"]),
                "source_sha256": str(cefr["source_sha256"]),
            },
            "pronunciation": {
                "strategy": str(pronunciation["strategy"]),
                "unknown": bool(pronunciation["unknown"]),
                "variants": json.loads(str(pronunciation["variants_json"])),
                "pronunciation_id": int(pronunciation["id"]),
                "generated_fallback": False,
            },
            "examples": [
                {
                    "role": str(row["role"]),
                    "source": str(row["source_text"]),
                    "target": str(row["target_text"]),
                    "example_id": int(row["id"]),
                }
                for row in examples
            ],
        }
        content_sha = canonical_sha256(card)
        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            connection.execute("DELETE FROM card_revisions WHERE stage24_run_id=?", (run_id,))
            cursor = connection.execute(
                """
                INSERT INTO card_revisions(
                    stage24_run_id,lexical_sense_id,lexical_entry_id,content_json,content_sha256,created_at
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    run_id,
                    int(lexical_sense_id),
                    int(sense["lexical_entry_id"]),
                    canonical_json(card),
                    content_sha,
                    utcnow(),
                ),
            )
            card_revision_id = int(cursor.lastrowid)
            output = {
                "schema": "rocketdict-product-stage24/1",
                "card_run_id": run_id,
                "stage_result_id": run_id,
                "lexical_sense_id": int(lexical_sense_id),
                "card_revision_id": card_revision_id,
                "content_sha256": content_sha,
                "complete": True,
            }
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def assemble_card_set(
    database: Path | str,
    *,
    card_revision_ids: Iterable[int],
    set_name: str = "RocketDict Product output",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    ids = [int(value) for value in card_revision_ids]
    if not ids or any(value <= 0 for value in ids) or len(ids) != len(set(ids)):
        raise RuntimeError("Card-set assembly requires a non-empty unique positive card_revision_ids list")
    ensure_downstream_database(database)
    with connect(database, readonly=True) as connection:
        rows = [
            connection.execute("SELECT * FROM card_revisions WHERE id=?", (value,)).fetchone()
            for value in ids
        ]
    if any(row is None for row in rows):
        missing = [value for value, row in zip(ids, rows, strict=True) if row is None]
        raise RuntimeError(f"Card-set assembly references missing card revisions: {missing}")
    card_hashes = [str(row["content_sha256"]) for row in rows if row is not None]
    input_identity = {
        "card_revision_ids": ids,
        "card_content_sha256": card_hashes,
        "set_name": str(set_name),
    }
    run_id, cached = _start(
        database,
        stage_number=24,
        stage_key="card_set_assembly",
        implementation=SET_ASSEMBLY_POLICY,
        input_identity=input_identity,
        parameters={},
    )
    if cached is not None:
        return cached
    try:
        cards_sha = canonical_sha256(
            [{"id": card_id, "sha256": sha} for card_id, sha in zip(ids, card_hashes, strict=True)]
        )
        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            connection.execute("DELETE FROM card_sets WHERE assembly_run_id=?", (run_id,))
            cursor = connection.execute(
                """
                INSERT INTO card_sets(assembly_run_id,set_name,card_count,cards_sha256,created_at)
                VALUES(?,?,?,?,?)
                """,
                (run_id, str(set_name), len(ids), cards_sha, utcnow()),
            )
            set_revision_id = int(cursor.lastrowid)
            for sequence, card_id in enumerate(ids):
                connection.execute(
                    "INSERT INTO card_set_members(set_revision_id,sequence_number,card_revision_id) VALUES(?,?,?)",
                    (set_revision_id, sequence, card_id),
                )
            output = {
                "schema": "rocketdict-product-card-set/1",
                "set_assembly_run_id": run_id,
                "set_revision_id": set_revision_id,
                "set_name": str(set_name),
                "card_count": len(ids),
                "cards_sha256": cards_sha,
                "complete": True,
            }
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def _export_payload(database: Path, set_revision_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ensure_downstream_database(database)
    with connect(database, readonly=True) as connection:
        set_row = connection.execute("SELECT * FROM card_sets WHERE id=?", (int(set_revision_id),)).fetchone()
        if set_row is None:
            raise RuntimeError(f"Card set does not exist: {set_revision_id}")
        rows = connection.execute(
            """
            SELECT m.sequence_number,c.*
            FROM card_set_members m JOIN card_revisions c ON c.id=m.card_revision_id
            WHERE m.set_revision_id=? ORDER BY m.sequence_number
            """,
            (int(set_revision_id),),
        ).fetchall()
    cards = [json.loads(str(row["content_json"])) for row in rows]
    metadata = {
        "set_revision_id": int(set_revision_id),
        "set_name": str(set_row["set_name"]),
        "card_count": int(set_row["card_count"]),
        "cards_sha256": str(set_row["cards_sha256"]),
    }
    if len(cards) != metadata["card_count"]:
        raise RuntimeError("Stage25 card-set membership coverage changed")
    return metadata, cards


def run_stage25(
    database: Path | str,
    *,
    set_revision_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE25_POLICY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != STAGE25_POLICY:
        raise RuntimeError(f"Unsupported Stage25 Product policy {implementation!r}")
    parameters = dict(parameters or {})
    metadata, cards = _export_payload(database, int(set_revision_id))
    input_identity = {
        "set_revision_id": int(set_revision_id),
        "set_name": metadata["set_name"],
        "card_count": metadata["card_count"],
        "cards_sha256": metadata["cards_sha256"],
    }
    run_id, cached = _start(
        database,
        stage_number=25,
        stage_key="export",
        implementation=implementation,
        input_identity=input_identity,
        parameters=parameters,
    )
    if cached is not None:
        return cached
    try:
        raw_output = str(parameters.get("output_path") or "").strip()
        output_path = (
            Path(raw_output).expanduser().resolve()
            if raw_output
            else database.parent / "exports" / f"rocketdict-set-{int(set_revision_id)}.json"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        export = {
            "schema": "rocketdict-product-export/1",
            **metadata,
            "cards": cards,
        }
        serialized = json.dumps(
            export,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        temp = output_path.with_suffix(output_path.suffix + ".tmp")
        temp.write_text(serialized, encoding="utf-8")
        temp.replace(output_path)
        export_sha = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        output = {
            "schema": "rocketdict-product-stage25/1",
            "export_run_id": run_id,
            "stage_result_id": run_id,
            "set_revision_id": int(set_revision_id),
            "export_path": str(output_path),
            "export_sha256": export_sha,
            "export_bytes": output_path.stat().st_size,
            "card_count": len(cards),
            "format": "json",
            "complete": True,
        }
        with transaction(database) as connection:
            ensure_downstream_schema(connection)
            finish_run(connection, run_id, output)
        return {**output, "cache_hit": False}
    except Exception as exc:
        _fail(database, run_id, exc)
        raise


def downstream_snapshot(database: Path | str, *, sense_translation_run_id: int | None = None) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    ensure_downstream_database(database)
    with connect(database, readonly=True) as connection:
        translations = []
        if sense_translation_run_id is not None:
            translations = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM sense_translation_revisions WHERE stage20_run_id=? ORDER BY lexical_sense_id",
                    (int(sense_translation_run_id),),
                ).fetchall()
            ]
            for row in translations:
                row["candidates"] = json.loads(row.pop("candidates_json"))
                row["evidence"] = json.loads(row.pop("evidence_json"))
        counts = {}
        for table in (
            "sense_translation_revisions",
            "cefr_assignments",
            "pronunciations",
            "sense_examples",
            "card_revisions",
            "card_sets",
        ):
            counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    return {
        "schema": "rocketdict-product-core-downstream-snapshot/1",
        "counts": counts,
        "translations": translations,
    }
