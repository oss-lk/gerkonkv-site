from __future__ import annotations

"""Persist and audit the default-off bounded parenthetical OPUS rescue over run19."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_parenthetical_context_rescue_stage import (
    MAX_CONTEXT_NLP_TOKENS,
    MAX_PARENTHETICAL_ALPHA_WORDS,
    PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
    PARENTHETICAL_CONTEXT_SELECTED_PHASE,
    PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
    PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
    run_stage12 as run_parenthetical_stage12,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-parenthetical-whole-context-rescue-optin/1"
BASE_DATABASE_SHA256 = "8519ea592b0bd948b68980ed19b710f05f20f9e0a60f0cb6c3e1a7763d5a8f76"
BASE_RUN_ID = 19
BASE_OUTPUT_SHA256 = "48096e0c1085c0598bc8abf212a2b2ba9a1109bb232fa2487c0472f35c06a1d9"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 15, "length": 0, "unique": 34}
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 20, "punctuation": 14, "length": 0, "unique": 33}
BASE_SEGMENTS = 3342
EXPECTED_FINAL_SEGMENTS = 3341
EXPECTED_CONTEXT = 1393
EXPECTED_SOURCE_START = 255534
EXPECTED_SOURCE_END = 256014
EXPECTED_MEMBER_STARTS = [255534, 255847]
EXPECTED_TARGET = (
    "Ибо, когда свет падает на воздух, который в других местах был между ними, "
    "что все должно было отражаться; казалось, что в этом месте контакта полностью "
    "передается, так же, что при взгляде на него он представлялся как чёрное или "
    "темное пятно, по причине того, что маленький или неразумный Свет был отражен "
    "оттуда, как и в других местах; и когда он смотрел через него, казалось "
    "(как это было) отверстие в воздухе, которое образовывалось в тонкий платок, "
    "сжимаясь между очками."
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


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


def _identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
        str(row.get("target_text") or ""),
    )


def _semantic_review(source: str, target: str) -> dict[str, Any]:
    lowered = target.casefold()
    anchors = {
        "light": "свет" in lowered,
        "air": "воздух" in lowered,
        "reflection": "отраж" in lowered,
        "transmission": "переда" in lowered,
        "black_or_dark_spot": "чёрн" in lowered and "темн" in lowered and "пятн" in lowered,
        "little_or_no_sensible_light": "маленьк" in lowered and "неразумн" in lowered,
        "parenthetical_hole": "(" in target and ")" in target and "отверст" in lowered,
        "thin_plate": "тонк" in lowered and "плат" in lowered,
        "compressed_between_glasses": "сжима" in lowered and "очк" in lowered,
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


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_PARENTHETICAL_CONTEXT_PRODUCT_ROOT",
            "work/full-opticks-parenthetical-whole-context-rescue",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("parenthetical replay requires exact persisted run19 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        document = get_document(connection, int(base_output["document_version_id"]))

    if int(base_run.get("stage_number") or -1) != 12:
        raise RuntimeError("run19 is not Stage12")
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run19 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run19 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run19 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run19 baseline drift: counts={base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    context = next(
        (row for row in context_rows if int(row["sequence_number"]) == EXPECTED_CONTEXT),
        None,
    )
    if context is None:
        raise RuntimeError("expected parenthetical context missing")
    if [int(context["source_start"]), int(context["source_end"])] != [
        EXPECTED_SOURCE_START,
        EXPECTED_SOURCE_END,
    ]:
        raise RuntimeError("parenthetical context source-span drift")
    source = str(context.get("source_text") or "")
    if content[EXPECTED_SOURCE_START:EXPECTED_SOURCE_END] != source:
        raise RuntimeError("parenthetical context source bytes drift")
    members = [
        row
        for row in base_rows
        if EXPECTED_SOURCE_START <= int(row["source_start"])
        and int(row["source_end"]) <= EXPECTED_SOURCE_END
    ]
    if [int(row["source_start"]) for row in members] != EXPECTED_MEMBER_STARTS:
        raise RuntimeError("parenthetical member geometry drift")
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("parenthetical members do not reconstruct context")
    base_target = "".join(str(row.get("target_text") or "") for row in members)
    if [source.count("("), source.count(")")] != [1, 1]:
        raise RuntimeError("parenthetical source-shape drift")
    if [base_target.count("("), base_target.count(")")] != [0, 0]:
        raise RuntimeError("parenthetical base-target shape drift")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_parenthetical_whole_context_rescue": True,
            "parenthetical_whole_context_rescue_contract": PARENTHETICAL_CONTEXT_RESCUE_CONTRACT,
            "parenthetical_whole_context_selector_contract": PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT,
            "parenthetical_whole_context_trigger_contract": PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT,
            "parenthetical_whole_context_rescue_phase": PARENTHETICAL_CONTEXT_SELECTED_PHASE,
            "parenthetical_whole_context_max_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
            "parenthetical_whole_context_max_parenthetical_alpha_words": MAX_PARENTHETICAL_ALPHA_WORDS,
        }
    )
    enabled = run_parenthetical_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id != BASE_RUN_ID + 1:
        raise RuntimeError(f"parenthetical final run identity drift: {final_run_id}")
    if int(enabled.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("parenthetical wrapper did not compose directly over run19")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("parenthetical base output SHA drift")
    if enabled.get("parenthetical_whole_context_rescue_attempt_count") != 1:
        raise RuntimeError("parenthetical attempt-count drift")
    if enabled.get("parenthetical_whole_context_rescue_accepted_count") != 1:
        raise RuntimeError("parenthetical accepted-count drift")
    if enabled.get("parenthetical_whole_context_rescue_rejected_count") != 0:
        raise RuntimeError("parenthetical rejected-count drift")
    if list(enabled.get("parenthetical_whole_context_rescue_attempted_context_sequences") or []) != [EXPECTED_CONTEXT]:
        raise RuntimeError("parenthetical attempt cohort drift")
    if list(enabled.get("parenthetical_whole_context_rescue_accepted_context_sequences") or []) != [EXPECTED_CONTEXT]:
        raise RuntimeError("parenthetical accepted cohort drift")
    if list(enabled.get("parenthetical_whole_context_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("parenthetical rescue did not use raw rank0")
    if list(enabled.get("parenthetical_whole_context_rescue_selected_targets") or []) != [EXPECTED_TARGET]:
        raise RuntimeError("parenthetical raw OPUS rank0 drift from DOE")
    if enabled.get("base_segment_count") != BASE_SEGMENTS:
        raise RuntimeError("parenthetical base segment count drift")
    if enabled.get("segment_count") != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("parenthetical final segment count drift")

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = _ordered(get_run_items(connection, final_run_id, kind="translation_segment"))
    _coverage(final_rows, content, label="parenthetical final")
    final_inventory = _inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS or len(final_rows) != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError(
            f"parenthetical final hard-gate drift: {final_inventory['counts']!r}, rows={len(final_rows)}"
        )

    replacement = next(
        (row for row in final_rows if int(row["source_start"]) == EXPECTED_SOURCE_START),
        None,
    )
    if replacement is None or int(replacement["source_end"]) != EXPECTED_SOURCE_END:
        raise RuntimeError("parenthetical replacement row missing")
    if str(replacement.get("source_text") or "") != source:
        raise RuntimeError("parenthetical replacement source drift")
    if str(replacement.get("target_text") or "") != EXPECTED_TARGET:
        raise RuntimeError("parenthetical replacement target drift")
    rescue = dict(
        (replacement.get("payload") or {}).get("parenthetical_whole_context_rescue") or {}
    )
    trigger = dict(rescue.get("trigger") or {})
    selection = dict(rescue.get("selection") or {})
    if rescue.get("contract") != PARENTHETICAL_CONTEXT_RESCUE_CONTRACT:
        raise RuntimeError("parenthetical rescue contract drift")
    if rescue.get("selector_contract") != PARENTHETICAL_CONTEXT_SELECTOR_CONTRACT:
        raise RuntimeError("parenthetical selector contract drift")
    if rescue.get("trigger_contract") != PARENTHETICAL_CONTEXT_TRIGGER_CONTRACT:
        raise RuntimeError("parenthetical trigger contract drift")
    if rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
        raise RuntimeError("parenthetical replacement is not raw OPUS rank0")
    if trigger.get("eligible") is not True:
        raise RuntimeError("parenthetical source trigger no longer eligible")
    if trigger.get("context_nlp_token_count") != 108:
        raise RuntimeError("parenthetical context token-count drift")
    if trigger.get("source_round_parentheses") != [1, 1]:
        raise RuntimeError("parenthetical source pair drift")
    if trigger.get("aggregate_target_round_parentheses") != [0, 0]:
        raise RuntimeError("parenthetical base target pair drift")
    if trigger.get("parenthetical_alpha_word_count") != 3:
        raise RuntimeError("parenthetical payload complexity drift")
    if selection.get("accepted") is not True or selection.get("strictly_eligible") is not True:
        raise RuntimeError("parenthetical selector evidence drift")
    if (selection.get("emphasis_markup") or {}).get("passed") is not True:
        raise RuntimeError("parenthetical emphasis evidence drift")

    member_ids = {int(row["id"]) for row in members}
    base_untouched = sorted(
        (_identity(row) for row in base_rows if int(row["id"]) not in member_ids),
        key=lambda value: value[0],
    )
    final_untouched = sorted(
        (_identity(row) for row in final_rows if int(row["source_start"]) != EXPECTED_SOURCE_START),
        key=lambda value: value[0],
    )
    if base_untouched != final_untouched:
        raise RuntimeError("parenthetical rescue caused unrelated source/target drift")
    if len(base_untouched) != 3340:
        raise RuntimeError(f"parenthetical untouched-row cardinality drift: {len(base_untouched)}")

    semantic = _semantic_review(source, EXPECTED_TARGET)
    if semantic["all_diagnostic_anchors"] is not True:
        raise RuntimeError(f"parenthetical semantic anchor drift: {semantic!r}")

    with sqlite3.connect(database) as raw:
        integrity = raw.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = raw.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise RuntimeError(
            f"parenthetical database integrity failure: integrity={integrity!r}, fk={foreign_keys!r}"
        )

    output_path = root / "full-opticks-parenthetical-whole-context-rescue.txt"
    output_path.write_text("\n".join(str(row.get("target_text") or "") for row in final_rows), encoding="utf-8")
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persist exact run19 plus bounded source-defined parenthetical OPUS-rank0 rescue",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "final_translation_run_id": final_run_id,
        "final_translation_output_sha256": str(final_run.get("output_sha256") or ""),
        "final_database_sha256": _sha(database),
        "final_text_sha256": _sha(output_path),
        "final_hard_gate_counts": final_inventory["counts"],
        "base_segment_count": BASE_SEGMENTS,
        "final_segment_count": len(final_rows),
        "attempted_context_sequences": [EXPECTED_CONTEXT],
        "accepted_context_sequences": [EXPECTED_CONTEXT],
        "selected_ranks": [0],
        "accepted_source_span": [EXPECTED_SOURCE_START, EXPECTED_SOURCE_END],
        "base_member_source_starts": EXPECTED_MEMBER_STARTS,
        "untouched_row_count": len(base_untouched),
        "untouched_source_target_exact": True,
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "foreign_key_violation_count": len(foreign_keys),
        "trigger": trigger,
        "selection": selection,
        "semantic_review": semantic,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "full-opticks-parenthetical-whole-context-rescue.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary_path = root / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "final_hard_gate_counts": final_inventory["counts"],
                "final_translation_run_id": final_run_id,
                "accepted_context_sequences": [EXPECTED_CONTEXT],
                "evidence_sha256": evidence["evidence_sha256"],
                "database_sha256": evidence["final_database_sha256"],
                "output_sha256": evidence["final_text_sha256"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
