from __future__ import annotations

"""Persist and audit the default-off bounded question-context OPUS rescue over run18."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_question_context_rescue_stage import (
    MAX_CONTEXT_NLP_TOKENS,
    QUESTION_CONTEXT_RESCUE_CONTRACT,
    QUESTION_CONTEXT_SELECTED_PHASE,
    QUESTION_CONTEXT_SELECTOR_CONTRACT,
    QUESTION_CONTEXT_TRIGGER_CONTRACT,
    run_stage12 as run_question_context_stage12,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-question-mark-whole-context-rescue-optin/1"
BASE_DATABASE_SHA256 = "803a2cbccb287ad0fadf4b14d932e1e33ebafef2ec5406619b0caf0898525143"
BASE_RUN_ID = 18
BASE_OUTPUT_SHA256 = "666e8a2cae0bb6ff6f25b95475c2335ee5e3c98f7f2d6ab7deb9be92295be290"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 16, "length": 0, "unique": 35}
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 20, "punctuation": 15, "length": 0, "unique": 34}
BASE_SEGMENTS = 3343
EXPECTED_FINAL_SEGMENTS = 3342
EXPECTED_ATTEMPT_CONTEXTS = [2462, 2726]
EXPECTED_ACCEPTED_CONTEXTS = [2462]
EXPECTED_REJECTED_CONTEXTS = [2726]
EXPECTED_SOURCE_START = 477054
EXPECTED_SOURCE_END = 477373
EXPECTED_MEMBER_STARTS = [477054, 477366]
EXPECTED_TARGET = (
    "Когда Уголь Огня двигается по окружности Круга, то вся окружность становится "
    "как круг Огня. Разве не потому, что движения, взволнованные на дне Глаза "
    "лучами света, имеют длительный характер и продолжаются до тех пор, пока "
    "Уголь Огня не вернется в свое прежнее место?"
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _coverage(rows: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for sequence, row in enumerate(_ordered(rows)):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError(f"{label} sequence drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"{label} source coverage drift at sequence {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage: {cursor} != {len(content)}")


def _hard_flags(source: str, target: str) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(source, target)
    return {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
        sequence = int(row["sequence_number"])
        flags = _hard_flags(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
        for key, failed in flags.items():
            if failed:
                failures[key].append(sequence)
                union.add(sequence)
    return {
        "counts": {
            "numeric_symbol": len(failures["numeric_symbol"]),
            "punctuation": len(failures["punctuation"]),
            "length": len(failures["length"]),
            "unique": len(union),
        },
        "failures": failures,
    }


def _semantic_review(source: str, target: str) -> dict[str, Any]:
    lowered = target.casefold()
    anchors = {
        "coal_of_fire": "уголь" in lowered and "огн" in lowered,
        "circle": "круг" in lowered,
        "eye": "глаз" in lowered,
        "rays_of_light": "луч" in lowered and "свет" in lowered,
        "lasting_nature": "длитель" in lowered,
        "returns": "верн" in lowered,
        "former_place": "прежн" in lowered and "мест" in lowered,
        "single_question": target.count("?") == source.count("?") == 1,
    }
    verdict = evaluate_rescue_pair(source, target)
    return {
        "source": source,
        "target": target,
        "diagnostic_anchors": anchors,
        "all_diagnostic_anchors": all(anchors.values()),
        "numeric_symbol_clean": (verdict.get("numeric_symbol") or {}).get("passed") is True,
        "punctuation_clean": verdict.get("punctuation_passed") is True,
        "length_clean": verdict.get("length_passed") is True,
        "strict_research_clean": verdict.get("strict_research_passed") is True,
        "diagnostics_are_non_authoritative": True,
        "manual_semantic_review_still_required_for_product_promotion": True,
    }


def _identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
        str(row.get("target_text") or ""),
    )


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_QUESTION_CONTEXT_PRODUCT_ROOT",
            "work/full-opticks-question-mark-whole-context-rescue",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("question-context replay requires exact persisted run18 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        document = get_document(connection, int(base_output["document_version_id"]))

    if int(base_run.get("stage_number") or -1) != 12:
        raise RuntimeError("run18 is not a Stage12 run")
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run18 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run18 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run18 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run18 baseline drift: counts={base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    context_by_sequence = {int(row["sequence_number"]): row for row in context_rows}
    accepted_context = context_by_sequence.get(EXPECTED_ACCEPTED_CONTEXTS[0])
    rejected_context = context_by_sequence.get(EXPECTED_REJECTED_CONTEXTS[0])
    if accepted_context is None or rejected_context is None:
        raise RuntimeError("expected question contexts are missing from run18 Stage10")
    if [int(accepted_context["source_start"]), int(accepted_context["source_end"])] != [
        EXPECTED_SOURCE_START,
        EXPECTED_SOURCE_END,
    ]:
        raise RuntimeError("accepted question context source span drift")
    accepted_source = str(accepted_context.get("source_text") or "")
    if content[EXPECTED_SOURCE_START:EXPECTED_SOURCE_END] != accepted_source:
        raise RuntimeError("accepted question context differs from immutable source")

    accepted_base_rows = [
        row
        for row in base_rows
        if EXPECTED_SOURCE_START <= int(row["source_start"])
        and int(row["source_end"]) <= EXPECTED_SOURCE_END
    ]
    if [int(row["source_start"]) for row in accepted_base_rows] != EXPECTED_MEMBER_STARTS:
        raise RuntimeError("accepted question-context base-row geometry drift")
    if "".join(str(row.get("source_text") or "") for row in accepted_base_rows) != accepted_source:
        raise RuntimeError("accepted question-context base rows do not cover immutable source")
    accepted_base_target = "".join(str(row.get("target_text") or "") for row in accepted_base_rows)
    if accepted_source.count("?") != 1 or accepted_base_target.count("?") != 2:
        raise RuntimeError("accepted question-context base question shape drift")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_question_mark_whole_context_rescue": True,
            "question_mark_whole_context_rescue_contract": QUESTION_CONTEXT_RESCUE_CONTRACT,
            "question_mark_whole_context_selector_contract": QUESTION_CONTEXT_SELECTOR_CONTRACT,
            "question_mark_whole_context_trigger_contract": QUESTION_CONTEXT_TRIGGER_CONTRACT,
            "question_mark_whole_context_rescue_phase": QUESTION_CONTEXT_SELECTED_PHASE,
            "question_mark_whole_context_max_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
        }
    )
    enabled = run_question_context_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id != BASE_RUN_ID + 1:
        raise RuntimeError(f"question-context final run identity drift: {final_run_id}")
    if int(enabled.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("question-context wrapper did not compose directly over exact run18")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("question-context base output SHA drift")
    if enabled.get("question_mark_whole_context_rescue_attempt_count") != 2:
        raise RuntimeError("question-context attempt-count drift")
    if enabled.get("question_mark_whole_context_rescue_accepted_count") != 1:
        raise RuntimeError("question-context accepted-count drift")
    if enabled.get("question_mark_whole_context_rescue_rejected_count") != 1:
        raise RuntimeError("question-context rejected-count drift")
    if list(enabled.get("question_mark_whole_context_rescue_attempted_context_sequences") or []) != EXPECTED_ATTEMPT_CONTEXTS:
        raise RuntimeError("question-context attempt cohort drift")
    if list(enabled.get("question_mark_whole_context_rescue_accepted_context_sequences") or []) != EXPECTED_ACCEPTED_CONTEXTS:
        raise RuntimeError("question-context accepted cohort drift")
    if list(enabled.get("question_mark_whole_context_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("question-context selector did not use raw OPUS rank0")
    if list(enabled.get("question_mark_whole_context_rescue_selected_targets") or []) != [EXPECTED_TARGET]:
        raise RuntimeError("question-context raw OPUS rank0 drift from read-only DOE")
    rejections = list(enabled.get("question_mark_whole_context_rescue_rejections") or [])
    if [int(row.get("context_sequence") or -1) for row in rejections] != EXPECTED_REJECTED_CONTEXTS:
        raise RuntimeError("question-context rejected cohort drift")
    rejection_selection = dict(rejections[0].get("selection") or {})
    if rejection_selection.get("accepted") is not False:
        raise RuntimeError("rejected question context unexpectedly selector-clean")
    if (rejection_selection.get("emphasis_markup") or {}).get("passed") is not False:
        raise RuntimeError("expected emphasis veto disappeared from rejected question context")
    if enabled.get("base_segment_count") != BASE_SEGMENTS or enabled.get("segment_count") != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("question-context segment-count drift")
    if enabled.get("question_mark_whole_context_rescue_model") != "opus-en-ru-ct2":
        raise RuntimeError("question-context rescue model drift")

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = _ordered(get_run_items(connection, final_run_id, kind="translation_segment"))
    _coverage(final_rows, content, label="question-context final")
    final_inventory = _inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS or len(final_rows) != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError(
            f"question-context final hard-gate drift: {final_inventory['counts']!r}, rows={len(final_rows)}"
        )

    accepted_final = next(
        (row for row in final_rows if int(row["source_start"]) == EXPECTED_SOURCE_START),
        None,
    )
    if accepted_final is None:
        raise RuntimeError("accepted question-context final row missing")
    if int(accepted_final["source_end"]) != EXPECTED_SOURCE_END:
        raise RuntimeError("accepted question-context final source span drift")
    if str(accepted_final.get("source_text") or "") != accepted_source:
        raise RuntimeError("accepted question-context final source bytes drift")
    if str(accepted_final.get("target_text") or "") != EXPECTED_TARGET:
        raise RuntimeError("accepted question-context final target drift")
    rescue = dict((accepted_final.get("payload") or {}).get("question_mark_whole_context_rescue") or {})
    if rescue.get("contract") != QUESTION_CONTEXT_RESCUE_CONTRACT:
        raise RuntimeError("accepted question-context rescue contract drift")
    if rescue.get("selector_contract") != QUESTION_CONTEXT_SELECTOR_CONTRACT:
        raise RuntimeError("accepted question-context selector contract drift")
    if rescue.get("trigger_contract") != QUESTION_CONTEXT_TRIGGER_CONTRACT:
        raise RuntimeError("accepted question-context trigger contract drift")
    if rescue.get("applied") is not True or rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
        raise RuntimeError("accepted question-context row is not exact raw OPUS rank0")
    trigger = dict(rescue.get("trigger") or {})
    selection = dict(rescue.get("selection") or {})
    if trigger.get("eligible") is not True or trigger.get("context_nlp_token_count") != 71:
        raise RuntimeError("accepted question-context source trigger drift")
    if trigger.get("premature_target_question_sequences") != [2705]:
        raise RuntimeError("accepted question-context premature-question identity drift")
    if selection.get("accepted") is not True or selection.get("strictly_eligible") is not True:
        raise RuntimeError("accepted question-context selector evidence drift")
    if selection.get("emphasis_markup", {}).get("passed") is not True:
        raise RuntimeError("accepted question-context emphasis evidence drift")
    if selection.get("target_alpha_non_decreasing") is not True:
        raise RuntimeError("accepted question-context completeness evidence drift")
    for flag in (
        "source_bytes_rewritten",
        "target_rewriting",
        "placeholders",
        "post_translation_literal_injection",
        "corpus_specific_target_patches",
        "evaluator_weakened",
    ):
        if rescue.get(flag) is not False:
            raise RuntimeError(f"unsafe question-context row flag: {flag}")

    base_by_geometry = {
        (int(row["source_start"]), int(row["source_end"])): row
        for row in base_rows
        if not (
            EXPECTED_SOURCE_START <= int(row["source_start"])
            and int(row["source_end"]) <= EXPECTED_SOURCE_END
        )
    }
    untouched = 0
    untouched_target_drift = 0
    for row in final_rows:
        if int(row["source_start"]) == EXPECTED_SOURCE_START:
            continue
        key = (int(row["source_start"]), int(row["source_end"]))
        base = base_by_geometry.get(key)
        if base is None:
            raise RuntimeError(f"unexpected non-rescue source geometry: {key!r}")
        untouched += 1
        if _identity(row) != _identity(base):
            untouched_target_drift += 1
        row_rescue = dict((row.get("payload") or {}).get("question_mark_whole_context_rescue") or {})
        if row_rescue.get("contract") != QUESTION_CONTEXT_RESCUE_CONTRACT or row_rescue.get("applied") is not False:
            raise RuntimeError("untouched question-context row metadata drift")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
            "corpus_specific_target_patches",
            "evaluator_weakened",
        ):
            if row_rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe untouched question-context row flag: {flag}")
    if untouched != BASE_SEGMENTS - len(accepted_base_rows) or untouched_target_drift != 0:
        raise RuntimeError(
            f"question-context untouched-row drift: untouched={untouched}, target_drift={untouched_target_drift}"
        )

    rejected_start = int(rejected_context["source_start"])
    rejected_end = int(rejected_context["source_end"])
    rejected_base = [
        row
        for row in base_rows
        if rejected_start <= int(row["source_start"]) and int(row["source_end"]) <= rejected_end
    ]
    rejected_final = [
        row
        for row in final_rows
        if rejected_start <= int(row["source_start"]) and int(row["source_end"]) <= rejected_end
    ]
    if [_identity(row) for row in rejected_final] != [_identity(row) for row in rejected_base]:
        raise RuntimeError("selector rejection did not preserve the long question context exactly")

    semantic = _semantic_review(accepted_source, EXPECTED_TARGET)
    if semantic["all_diagnostic_anchors"] is not True:
        raise RuntimeError("accepted question-context candidate failed semantic diagnostics")

    with sqlite3.connect(database) as raw:
        integrity = str(raw.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_key_violations = list(raw.execute("PRAGMA foreign_key_check"))
    if integrity != "ok" or foreign_key_violations:
        raise RuntimeError(
            f"question-context database integrity failed: integrity={integrity!r}, fk={foreign_key_violations!r}"
        )

    database_sha = _sha(database)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off raw OPUS rank0 whole-context rescue for bounded split questions with premature target question marks",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "final_translation_run_id": final_run_id,
        "final_output_sha256": str(final_run.get("output_sha256") or ""),
        "final_database_sha256": database_sha,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "final_hard_gate_counts": final_inventory["counts"],
        "base_segment_count": BASE_SEGMENTS,
        "final_segment_count": len(final_rows),
        "attempted_context_sequences": EXPECTED_ATTEMPT_CONTEXTS,
        "accepted_context_sequences": EXPECTED_ACCEPTED_CONTEXTS,
        "rejected_context_sequences": EXPECTED_REJECTED_CONTEXTS,
        "accepted_source_start": EXPECTED_SOURCE_START,
        "accepted_source_end": EXPECTED_SOURCE_END,
        "accepted_base_member_starts": EXPECTED_MEMBER_STARTS,
        "selected_rank": 0,
        "selected_target": EXPECTED_TARGET,
        "accepted_trigger": trigger,
        "accepted_selection": selection,
        "rejection_evidence": rejections,
        "semantic_review": semantic,
        "untouched_base_row_count": untouched,
        "untouched_target_drift_count": untouched_target_drift,
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "foreign_key_violation_count": len(foreign_key_violations),
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-question-mark-whole-context-rescue.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "base": BASE_COUNTS,
                "final": final_inventory["counts"],
                "attempted_contexts": EXPECTED_ATTEMPT_CONTEXTS,
                "accepted_contexts": EXPECTED_ACCEPTED_CONTEXTS,
                "rejected_contexts": EXPECTED_REJECTED_CONTEXTS,
                "final_run_id": final_run_id,
                "final_output_sha256": payload["final_output_sha256"],
                "final_database_sha256": database_sha,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
