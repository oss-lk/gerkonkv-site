from __future__ import annotations

"""Native Stage20 contextual lexical translation for the maintained Product Core.

The implementation preserves the validated Workbench lexical OPUS v3 policy,
but stores evidence directly in the maintained SQLite schema.  There is no
identity/dictionary fallback: every accepted primary must come from the pinned
real OPUS runtime and every Stage19 sense must be covered before Stage20 can
complete.
"""

import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from .database import begin_run, connect, fail_run, finish_run, get_run, transaction
from .lexical import ensure_schema as ensure_lexical_schema
from .runtime import OpusTranslator, load_opus_asset

POLICY_KEY = "contextual-lexical-opus-v3"
ARBITRATION_POLICY = "lexical-primary-arbitration-v1"
PROBE_POLICY = "pos-dependency-dictionary-shape-v3"
VERB_ENTRY_TYPES = {"phrasal_verb", "prepositional_verb"}
OBJECT_DEPENDENCIES = {"dobj", "obj", "pobj", "nsubj", "nsubjpass"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sense_translation_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage20_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_sense_id INTEGER NOT NULL REFERENCES lexical_senses(id),
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    probe_index INTEGER NOT NULL,
    probe_kind TEXT NOT NULL,
    probe_text TEXT NOT NULL,
    hypothesis_rank INTEGER NOT NULL,
    raw_target_text TEXT NOT NULL,
    cleaned_target_text TEXT NOT NULL,
    normalized_target_text TEXT NOT NULL,
    accepted INTEGER NOT NULL CHECK(accepted IN (0,1)),
    rejection_reason TEXT,
    provider_confidence REAL,
    context_compatibility REAL,
    raw_score REAL,
    evidence_json TEXT NOT NULL,
    UNIQUE(stage20_run_id, lexical_sense_id, probe_index, hypothesis_rank)
);
CREATE INDEX IF NOT EXISTS idx_sense_translation_candidates_run
    ON sense_translation_candidates(stage20_run_id, lexical_sense_id, accepted);

CREATE TABLE IF NOT EXISTS sense_translation_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage20_run_id INTEGER NOT NULL REFERENCES stage_runs(id) ON DELETE CASCADE,
    lexical_sense_id INTEGER NOT NULL REFERENCES lexical_senses(id),
    lexical_entry_id INTEGER NOT NULL REFERENCES lexical_entries(id),
    selected_candidate_id INTEGER NOT NULL REFERENCES sense_translation_candidates(id),
    translation_text TEXT NOT NULL,
    normalized_translation TEXT NOT NULL,
    provider_confidence REAL NOT NULL,
    context_compatibility REAL NOT NULL,
    target_part_of_speech TEXT,
    approval_policy TEXT NOT NULL,
    approved INTEGER NOT NULL CHECK(approved IN (0,1)),
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stage20_run_id, lexical_sense_id)
);
CREATE INDEX IF NOT EXISTS idx_sense_translation_revisions_sense
    ON sense_translation_revisions(lexical_sense_id, id);
"""


def ensure_schema(connection) -> None:  # type: ignore[no-untyped-def]
    ensure_lexical_schema(connection)
    connection.executescript(_SCHEMA)


def normalize_lexical_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").strip()
    value = re.sub(r"^[\s\.,;:!?…\"'«»()\[\]{}]+|[\s\.,;:!?…\"'«»()\[\]{}]+$", "", value)
    return re.sub(r"\s+", " ", value).casefold().strip()


def effective_probe_pos(part_of_speech: str | None, dependency: str | None) -> tuple[str, str]:
    pos = str(part_of_speech or "X").upper()
    dep = str(dependency or "").casefold()
    if pos == "VERB" and dep in OBJECT_DEPENDENCIES:
        return "NOUN", "dependency_pos_repair"
    return pos, "declared_pos"


def probe_forms(
    lemma: str,
    part_of_speech: str | None = None,
    entry_type: str | None = None,
    dependency: str | None = None,
) -> list[dict[str, Any]]:
    lemma = re.sub(r"\s+", " ", lemma.strip())
    if not lemma:
        return []
    effective_pos, pos_reason = effective_probe_pos(part_of_speech, dependency)
    entry_type = str(entry_type or "").casefold()
    title = lemma[:1].upper() + lemma[1:]
    if entry_type in VERB_ENTRY_TYPES:
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
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kind, text, base_confidence in values:
        if text in seen:
            continue
        seen.add(text)
        output.append(
            {
                "kind": kind,
                "text": text,
                "base_confidence": base_confidence,
                "effective_pos": effective_pos,
                "pos_reason": pos_reason,
            }
        )
    return output


def clean_probe_target(target: str, probe_kind: str) -> tuple[str, str | None]:
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


def admissible_ru_candidate(
    source_lemma: str,
    target: str,
    *,
    entry_type: str | None = None,
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


def provider_confidence(
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


def _context_compatibility(candidate: str, target_evidence: str, base: float) -> tuple[float, str]:
    candidate_norm = normalize_lexical_text(candidate)
    evidence_norm = normalize_lexical_text(target_evidence)
    if not candidate_norm or not evidence_norm:
        return round(base, 4), "no_aligned_target_evidence"
    if candidate_norm in evidence_norm:
        return round(min(0.99, base + 0.06), 4), "exact_phrase_in_aligned_target"
    candidate_words = set(re.findall(r"[А-Яа-яЁё]+", candidate_norm))
    evidence_words = set(re.findall(r"[А-Яа-яЁё]+", evidence_norm))
    overlap = len(candidate_words & evidence_words)
    if overlap:
        return round(min(0.99, base + min(0.04, 0.02 * overlap)), 4), "token_overlap_with_aligned_target"
    return round(base, 4), "no_surface_overlap"


def _sense_rows(database: Path, sense_induction_run_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with connect(database, readonly=True) as connection:
        ensure_schema(connection)
        stage19 = get_run(connection, int(sense_induction_run_id))
        if int(stage19["stage_number"]) != 19 or stage19["status"] != "completed":
            raise RuntimeError("Stage20 requires a completed Stage19 sense-induction run")
        rows = connection.execute(
            """
            SELECT s.*, e.normalized_lemma, e.display_lemma, e.part_of_speech, e.entry_type
            FROM lexical_senses s
            JOIN lexical_entries e ON e.id=s.lexical_entry_id
            WHERE s.sense_induction_run_id=?
            ORDER BY s.id
            """,
            (int(sense_induction_run_id),),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for raw in rows:
            row = dict(raw)
            row["evidence"] = json.loads(row.pop("evidence_json"))
            occurrences = connection.execute(
                """
                SELECT * FROM lexical_occurrences
                WHERE extraction_run_id=? AND lexical_entry_id=?
                ORDER BY sequence_number,id
                """,
                (
                    int((stage19.get("output") or {})["extraction_run_id"]),
                    int(row["lexical_entry_id"]),
                ),
            ).fetchall()
            occurrence_rows = []
            for occurrence in occurrences:
                value = dict(occurrence)
                value["evidence"] = json.loads(value.pop("evidence_json"))
                if normalize_lexical_text(str(value.get("target_evidence_text") or "")) == str(row["target_evidence_key"]):
                    occurrence_rows.append(value)
            row["occurrences"] = occurrence_rows
            result.append(row)
    if not result:
        raise RuntimeError("Stage20 cannot run on an empty Stage19 sense set")
    return stage19, result


def _dependency_for_sense(sense: dict[str, Any]) -> str | None:
    dependencies: list[str] = []
    for occurrence in sense.get("occurrences") or []:
        token = (occurrence.get("evidence") or {}).get("token") or {}
        value = str(token.get("dependency") or "").casefold()
        if value:
            dependencies.append(value)
    return dependencies[0] if dependencies and len(set(dependencies)) == 1 else None


def _target_evidence_for_sense(sense: dict[str, Any]) -> str:
    values = [
        str(row.get("target_evidence_text") or "").strip()
        for row in sense.get("occurrences") or []
        if str(row.get("target_evidence_text") or "").strip()
    ]
    if not values:
        return ""
    # Stage19 groups by normalized target evidence; all rows should represent the
    # same local context. Keep the first exact persisted surface form.
    return values[0]


def _validated_parameters(parameters: dict[str, Any] | None) -> dict[str, Any]:
    supplied = dict(parameters or {})
    allowed = {"beam_size", "num_hypotheses", "maximum_candidates_per_sense", "source_policy"}
    unknown = sorted(set(supplied) - allowed)
    if unknown:
        raise RuntimeError(f"Stage20 received unsupported parameters: {unknown}")
    values = {
        "beam_size": int(supplied.get("beam_size", 12)),
        "num_hypotheses": int(supplied.get("num_hypotheses", 12)),
        "maximum_candidates_per_sense": int(supplied.get("maximum_candidates_per_sense", 8)),
        "source_policy": str(supplied.get("source_policy", "aligned-local-consensus")),
    }
    if min(values["beam_size"], values["num_hypotheses"], values["maximum_candidates_per_sense"]) <= 0:
        raise ValueError("Stage20 generation settings must be positive")
    if values["num_hypotheses"] > values["beam_size"]:
        raise ValueError("Stage20 num_hypotheses must not exceed beam_size")
    if values["source_policy"] != "aligned-local-consensus":
        raise RuntimeError("Product Stage20 is pinned to aligned-local-consensus")
    return values


def run_stage20(
    database: Path | str,
    *,
    sense_induction_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = POLICY_KEY,
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    if implementation != POLICY_KEY:
        raise RuntimeError(f"Unsupported Stage20 implementation {implementation!r}")
    settings = _validated_parameters(parameters)
    stage19, senses = _sense_rows(database, int(sense_induction_run_id))
    asset = load_opus_asset()
    input_identity = {
        "sense_induction_run_id": int(sense_induction_run_id),
        "stage19_output_sha256": str(stage19.get("output_sha256") or ""),
        "sense_ids_sha256": str((stage19.get("output") or {}).get("sense_ids_sha256") or ""),
        "provider": POLICY_KEY,
        "probe_policy": PROBE_POLICY,
        "arbitration_policy": ARBITRATION_POLICY,
        "opus_revision": asset.revision,
        "opus_archive_sha256": asset.source_archive_sha256,
        "opus_manifest_sha256": asset.manifest_sha256,
        "opus_payload_tree_sha256": asset.payload_tree_sha256,
        "network_access": False,
    }
    with transaction(database) as connection:
        ensure_schema(connection)
        run_id, cache_hit = begin_run(
            connection,
            stage_number=20,
            stage_key="sense_translation",
            implementation=implementation,
            input_identity=input_identity,
            parameters=settings,
        )
    if cache_hit:
        with connect(database, readonly=True) as connection:
            cached = get_run(connection, run_id)
        return {**dict(cached.get("output") or {}), "cache_hit": True}

    try:
        translator = OpusTranslator(device="cpu", compute_type="float32")
        generated: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for sense in senses:
            lemma = str(sense.get("normalized_lemma") or sense.get("display_lemma") or "").strip()
            pos = str(sense.get("part_of_speech") or "X").upper()
            entry_type = str(sense.get("entry_type") or "word")
            dependency = _dependency_for_sense(sense)
            target_evidence = _target_evidence_for_sense(sense)
            probes = probe_forms(lemma, pos, entry_type, dependency)
            if not probes:
                unresolved.append({"sense_id": int(sense["id"]), "reason": "no_probe_forms"})
                continue
            translations = translator.translate(
                [str(probe["text"]) for probe in probes],
                beam_size=settings["beam_size"],
                num_hypotheses=settings["num_hypotheses"],
                max_decoding_length=64,
            )
            evidence_rows: list[dict[str, Any]] = []
            best_by_target: dict[str, dict[str, Any]] = {}
            for probe_index, (probe, outputs) in enumerate(zip(probes, translations)):
                for hypothesis in outputs:
                    rank = int(hypothesis.get("rank") or 0)
                    raw_target = str(hypothesis.get("text") or "")
                    cleaned, transform = clean_probe_target(raw_target, str(probe["kind"]))
                    accepted, rejection = admissible_ru_candidate(lemma, cleaned, entry_type=entry_type)
                    normalized = normalize_lexical_text(cleaned)
                    confidence = None
                    compatibility = None
                    compatibility_reason = None
                    target_pos = None
                    if accepted:
                        confidence = provider_confidence(
                            rank,
                            str(probe["kind"]),
                            base_confidence=float(probe["base_confidence"]),
                            effective_pos=str(probe["effective_pos"]),
                            target=cleaned,
                            entry_type=entry_type,
                        )
                        compatibility, compatibility_reason = _context_compatibility(
                            cleaned, target_evidence, confidence
                        )
                        if pos == "VERB" and _looks_like_russian_infinitive(cleaned):
                            target_pos = "VERB"
                        elif pos == "ADJ" and str(probe["kind"]) == "adjective_copula":
                            target_pos = "ADJ"
                    row = {
                        "sense_id": int(sense["id"]),
                        "entry_id": int(sense["lexical_entry_id"]),
                        "lemma": lemma,
                        "declared_pos": pos,
                        "entry_type": entry_type,
                        "dependency": dependency,
                        "target_evidence": target_evidence,
                        "probe_index": probe_index,
                        "probe_kind": str(probe["kind"]),
                        "probe_text": str(probe["text"]),
                        "effective_pos": str(probe["effective_pos"]),
                        "pos_reason": str(probe["pos_reason"]),
                        "rank": rank,
                        "raw_target": raw_target,
                        "cleaned_target": cleaned,
                        "normalized_target": normalized,
                        "target_transform": transform,
                        "raw_score": hypothesis.get("score"),
                        "accepted": bool(accepted),
                        "rejection_reason": rejection,
                        "provider_confidence": confidence,
                        "context_compatibility": compatibility,
                        "context_compatibility_reason": compatibility_reason,
                        "target_pos": target_pos,
                    }
                    evidence_rows.append(row)
                    if not accepted or not normalized:
                        continue
                    candidate = {
                        "translation": cleaned,
                        "normalized_translation": normalized,
                        "provider_confidence": float(confidence),
                        "context_compatibility": float(compatibility),
                        "target_pos": target_pos,
                        "probe_index": probe_index,
                        "hypothesis_rank": rank,
                    }
                    prior = best_by_target.get(normalized)
                    score = (candidate["context_compatibility"], candidate["provider_confidence"], -rank)
                    prior_score = (
                        (prior["context_compatibility"], prior["provider_confidence"], -prior["hypothesis_rank"])
                        if prior is not None
                        else None
                    )
                    if prior is None or score > prior_score:
                        best_by_target[normalized] = candidate
            accepted_candidates = sorted(
                best_by_target.values(),
                key=lambda row: (
                    -float(row["context_compatibility"]),
                    -float(row["provider_confidence"]),
                    str(row["normalized_translation"]),
                ),
            )[: settings["maximum_candidates_per_sense"]]
            if not accepted_candidates:
                unresolved.append(
                    {
                        "sense_id": int(sense["id"]),
                        "entry_id": int(sense["lexical_entry_id"]),
                        "lemma": lemma,
                        "reason": "no_admissible_real_opus_candidate",
                        "rejections": sorted(
                            {str(row["rejection_reason"]) for row in evidence_rows if row["rejection_reason"]}
                        ),
                    }
                )
                generated.append({"sense": sense, "evidence": evidence_rows, "candidates": []})
                continue
            generated.append(
                {
                    "sense": sense,
                    "evidence": evidence_rows,
                    "candidates": accepted_candidates,
                    "selected": accepted_candidates[0],
                }
            )

        if unresolved:
            raise RuntimeError(
                "Stage20 full-sense real OPUS coverage failed: "
                + json.dumps(unresolved[:50], ensure_ascii=False, sort_keys=True)
            )

        with transaction(database) as connection:
            ensure_schema(connection)
            connection.execute("DELETE FROM sense_translation_candidates WHERE stage20_run_id=?", (run_id,))
            connection.execute("DELETE FROM sense_translation_revisions WHERE stage20_run_id=?", (run_id,))
            revision_rows: list[dict[str, Any]] = []
            candidate_count = 0
            rejected_count = 0
            for item in generated:
                sense = item["sense"]
                candidate_ids: dict[tuple[int, int], int] = {}
                for row in item["evidence"]:
                    evidence = {
                        key: value
                        for key, value in row.items()
                        if key
                        not in {
                            "probe_index",
                            "probe_kind",
                            "probe_text",
                            "rank",
                            "raw_target",
                            "cleaned_target",
                            "normalized_target",
                            "accepted",
                            "rejection_reason",
                            "provider_confidence",
                            "context_compatibility",
                            "raw_score",
                        }
                    }
                    cursor = connection.execute(
                        """
                        INSERT INTO sense_translation_candidates(
                            stage20_run_id,lexical_sense_id,lexical_entry_id,probe_index,probe_kind,
                            probe_text,hypothesis_rank,raw_target_text,cleaned_target_text,
                            normalized_target_text,accepted,rejection_reason,provider_confidence,
                            context_compatibility,raw_score,evidence_json
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            run_id,
                            int(sense["id"]),
                            int(sense["lexical_entry_id"]),
                            int(row["probe_index"]),
                            str(row["probe_kind"]),
                            str(row["probe_text"]),
                            int(row["rank"]),
                            str(row["raw_target"]),
                            str(row["cleaned_target"]),
                            str(row["normalized_target"]),
                            1 if row["accepted"] else 0,
                            row["rejection_reason"],
                            row["provider_confidence"],
                            row["context_compatibility"],
                            row["raw_score"],
                            json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                        ),
                    )
                    candidate_ids[(int(row["probe_index"]), int(row["rank"]))] = int(cursor.lastrowid)
                    candidate_count += 1
                    rejected_count += 0 if row["accepted"] else 1
                selected = item["selected"]
                selected_candidate_id = candidate_ids[
                    (int(selected["probe_index"]), int(selected["hypothesis_rank"]))
                ]
                revision_evidence = {
                    "provider": POLICY_KEY,
                    "probe_policy": PROBE_POLICY,
                    "arbitration_policy": ARBITRATION_POLICY,
                    "source_policy": settings["source_policy"],
                    "target_evidence_key": str(sense.get("target_evidence_key") or ""),
                    "opus_revision": asset.revision,
                    "opus_archive_sha256": asset.source_archive_sha256,
                    "opus_manifest_sha256": asset.manifest_sha256,
                    "opus_payload_tree_sha256": asset.payload_tree_sha256,
                    "network_access": False,
                }
                cursor = connection.execute(
                    """
                    INSERT INTO sense_translation_revisions(
                        stage20_run_id,lexical_sense_id,lexical_entry_id,selected_candidate_id,
                        translation_text,normalized_translation,provider_confidence,
                        context_compatibility,target_part_of_speech,approval_policy,approved,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        int(sense["id"]),
                        int(sense["lexical_entry_id"]),
                        selected_candidate_id,
                        str(selected["translation"]),
                        str(selected["normalized_translation"]),
                        float(selected["provider_confidence"]),
                        float(selected["context_compatibility"]),
                        selected.get("target_pos"),
                        ARBITRATION_POLICY,
                        1,
                        json.dumps(revision_evidence, ensure_ascii=False, sort_keys=True),
                    ),
                )
                revision_rows.append(
                    {
                        "sense_id": int(sense["id"]),
                        "entry_id": int(sense["lexical_entry_id"]),
                        "lemma": str(sense["normalized_lemma"]),
                        "selection_revision_id": int(cursor.lastrowid),
                        "generation_run_id": run_id,
                        "translation": str(selected["translation"]),
                        "confidence": float(selected["provider_confidence"]),
                        "context_compatibility": float(selected["context_compatibility"]),
                        "target_pos": selected.get("target_pos"),
                        "approved": True,
                        "approval_policy": ARBITRATION_POLICY,
                    }
                )
            sense_ids = [int(row["sense_id"]) for row in revision_rows]
            revisions_sha = hashlib.sha256(
                json.dumps(revision_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            output = {
                "schema": "rocketdict-product-stage20/1",
                "provider": POLICY_KEY,
                "probe_policy": PROBE_POLICY,
                "arbitration_policy": ARBITRATION_POLICY,
                "sense_translation_run_id": run_id,
                "stage_result_id": run_id,
                "sense_induction_run_id": int(sense_induction_run_id),
                "sense_count": len(senses),
                "selection_revision_count": len(revision_rows),
                "candidate_evidence_count": candidate_count,
                "rejected_candidate_count": rejected_count,
                "coverage_complete": len(revision_rows) == len(senses),
                "unresolved_sense_count": 0,
                "all_selected_approved": True,
                "revision_rows_sha256": revisions_sha,
                "sense_ids_sha256": hashlib.sha256(
                    json.dumps(sense_ids, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "model_revision": asset.revision,
                "model_archive_sha256": asset.source_archive_sha256,
                "model_manifest_sha256": asset.manifest_sha256,
                "model_payload_tree_sha256": asset.payload_tree_sha256,
                "compute_type": "float32",
                "network_used": False,
                "results": revision_rows,
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


def get_stage20_revisions(database: Path | str, sense_translation_run_id: int) -> list[dict[str, Any]]:
    database = Path(database).expanduser().resolve()
    with connect(database, readonly=True) as connection:
        ensure_schema(connection)
        run = get_run(connection, int(sense_translation_run_id))
        if int(run["stage_number"]) != 20 or run["status"] != "completed":
            raise RuntimeError("Requested run is not a completed Stage20 translation run")
        rows = connection.execute(
            """
            SELECT r.*, e.normalized_lemma, e.display_lemma, e.part_of_speech, e.entry_type
            FROM sense_translation_revisions r
            JOIN lexical_entries e ON e.id=r.lexical_entry_id
            WHERE r.stage20_run_id=?
            ORDER BY r.lexical_sense_id,r.id
            """,
            (int(sense_translation_run_id),),
        ).fetchall()
    output: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        row["evidence"] = json.loads(row.pop("evidence_json"))
        row["approved"] = bool(row["approved"])
        output.append(row)
    return output
