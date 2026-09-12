from __future__ import annotations

"""Persist/audit default-off TC-big whole-context fraction rescue over exact run20."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_fraction_context_rescue_stage import (
    TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_SELECTED_PHASE,
    MAX_CONTEXT_NLP_TOKENS,
    run_stage12 as run_fraction_context_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-fraction-context-rescue-optin/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 14, "length": 0, "unique": 33}
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 19, "punctuation": 14, "length": 0, "unique": 32}
BASE_SEGMENTS = 3341
EXPECTED_FINAL_SEGMENTS = 3340
EXPECTED_CONTEXT = 1460
EXPECTED_SOURCE_START = 267212
EXPECTED_SOURCE_END = 267616
EXPECTED_MEMBER_SEQUENCES = [1570, 1571]
EXPECTED_MEMBER_STARTS = [267212, 267543]
EXPECTED_TOKEN_COUNT = 87
EXPECTED_TARGET = (
    "Это стекло, положенное на то же самое простое стекло, диаметр пятого из темных "
    "колец, когда черное пятно в их центре появляется явно, не нажимая на очки, было "
    "по мерке компасов на верхних частях стекла 121/600 дюйма, и, следовательно, "
    "между стеклами было 1222/6000: ибо верхнее стекло было толщиной 1/8 дюйма, и "
    "мой глаз был удален от него на 8 дюймов."
)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _coverage(rows: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for sequence, row in enumerate(_ordered(rows)):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError(f"{label} sequence drift")
        start, end = int(row["source_start"]), int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"{label} source coverage drift at {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} incomplete source coverage")


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
        seq = int(row["sequence_number"])
        verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        flags = {
            "numeric_symbol": dict(verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key, failed in flags.items():
            if failed:
                failures[key].append(seq)
                union.add(seq)
    return {"counts": {"numeric_symbol": len(failures["numeric_symbol"]), "punctuation": len(failures["punctuation"]), "length": len(failures["length"]), "unique": len(union)}, "failures": failures}


def _identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (int(row["source_start"]), int(row["source_end"]), str(row.get("source_text") or ""), str(row.get("target_text") or ""))


def _semantic_review(source: str, base_target: str, target: str) -> dict[str, Any]:
    lowered = target.casefold()
    anchors = {
        "black_spot": "черное пятно" in lowered or "чёрное пятно" in lowered,
        "diameter": "диаметр" in lowered,
        "compasses": "компас" in lowered,
        "causal_consequence": "следовательно" in lowered,
        "upper_glass": "верхн" in lowered and "стекл" in lowered,
        "eye": "глаз" in lowered,
        "inch": "дюйм" in lowered,
        "all_numeric_values": all(value in target for value in ("121/600", "1222/6000", "1/8", "8")),
        "terminal_sentence_complete": target.rstrip().endswith("."),
    }
    verdict = evaluate_rescue_pair(source, target)
    return {
        "diagnostic_anchors": anchors,
        "all_diagnostic_anchors": all(anchors.values()),
        "numeric_symbol_clean": dict(verdict.get("numeric_symbol") or {}).get("passed") is True,
        "punctuation_clean": verdict.get("punctuation_passed") is True,
        "length_clean": verdict.get("length_passed") is True,
        "strict_research_clean": verdict.get("strict_research_passed") is True,
        "base_split_join_artifact_present": "слоевСтекло" in base_target,
        "candidate_split_join_artifact_absent": "слоевСтекло" not in target,
        "research_acceptance": "accepted_as_default_off_full_corpus_research_basis",
        "product_default_promotion_allowed": False,
        "manual_semantic_review_still_required_for_product_promotion": True,
        "known_lexical_debt": [
            "source plural 'Glasses' in 'without pressing the Glasses' is still rendered as 'очки'; this ambiguity already exists in the base target"
        ],
        "quality_rationale": (
            "The raw TC-big whole-context rank0 removes the denominator truncation and the split-row join artifact, preserves the complete measurement sentence and all numeric values, and improves 'black Spot' to 'черное пятно'. Remaining Glasses/очки lexical debt is inherited rather than newly introduced."
        ),
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_TC_BIG_FRACTION_CONTEXT_PRODUCT_ROOT", "work/full-opticks-tc-big-fraction-context-rescue")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("fraction-context replay requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run20 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(f"run20 baseline drift: {base_inventory['counts']!r}, {len(base_rows)}")

    context = next(row for row in context_rows if int(row["sequence_number"]) == EXPECTED_CONTEXT)
    source = str(context.get("source_text") or "")
    if [int(context["source_start"]), int(context["source_end"])] != [EXPECTED_SOURCE_START, EXPECTED_SOURCE_END]:
        raise RuntimeError("fraction context span drift")
    if source != content[EXPECTED_SOURCE_START:EXPECTED_SOURCE_END]:
        raise RuntimeError("fraction context source drift")
    if int((context.get("payload") or {}).get("token_count") or 0) != EXPECTED_TOKEN_COUNT:
        raise RuntimeError("fraction context token-count drift")
    members = [row for row in base_rows if EXPECTED_SOURCE_START <= int(row["source_start"]) and int(row["source_end"]) <= EXPECTED_SOURCE_END]
    if [int(row["sequence_number"]) for row in members] != EXPECTED_MEMBER_SEQUENCES:
        raise RuntimeError("fraction member sequence drift")
    if [int(row["source_start"]) for row in members] != EXPECTED_MEMBER_STARTS:
        raise RuntimeError("fraction member source-start drift")
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("fraction base members do not reconstruct context")
    base_target = "".join(str(row.get("target_text") or "") for row in members)
    if "слоевСтекло" not in base_target:
        raise RuntimeError("expected run20 split-join artifact drift")

    parameters = dict(base_parameters)
    parameters.update({
        "enable_tc_big_fraction_context_rescue": True,
        "tc_big_fraction_context_rescue_contract": TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
        "tc_big_fraction_context_selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
        "tc_big_fraction_context_trigger_contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
        "tc_big_fraction_context_rescue_phase": TC_BIG_FRACTION_CONTEXT_SELECTED_PHASE,
        "tc_big_fraction_context_max_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
    })
    enabled = run_fraction_context_stage12(database, context_run_id=context_run_id, parameters=parameters, implementation="opus-en-ru-ct2")
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id != BASE_RUN_ID + 1:
        raise RuntimeError(f"fraction-context final run identity drift: {final_run_id}")
    if int(enabled.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("fraction-context did not compose directly over run20")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("fraction-context base output SHA drift")
    if enabled.get("tc_big_fraction_context_rescue_attempt_count") != 1 or enabled.get("tc_big_fraction_context_rescue_accepted_count") != 1 or enabled.get("tc_big_fraction_context_rescue_rejected_count") != 0:
        raise RuntimeError("fraction-context attempt/acceptance cohort drift")
    if list(enabled.get("tc_big_fraction_context_rescue_attempted_context_sequences") or []) != [EXPECTED_CONTEXT]:
        raise RuntimeError("fraction-context attempted cohort drift")
    if list(enabled.get("tc_big_fraction_context_rescue_accepted_context_sequences") or []) != [EXPECTED_CONTEXT]:
        raise RuntimeError("fraction-context accepted cohort drift")
    if list(enabled.get("tc_big_fraction_context_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("fraction-context did not select rank0")
    if list(enabled.get("tc_big_fraction_context_rescue_selected_targets") or []) != [EXPECTED_TARGET]:
        raise RuntimeError("fraction-context raw TC-big rank0 drift from exact DOE")
    if enabled.get("base_segment_count") != BASE_SEGMENTS or enabled.get("segment_count") != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("fraction-context segment-count drift")

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = _ordered(get_run_items(connection, final_run_id, kind="translation_segment"))
    _coverage(final_rows, content, label="fraction-context final")
    final_inventory = _inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS:
        raise RuntimeError(f"fraction-context final hard-gate drift: {final_inventory['counts']!r}")
    if len(final_rows) != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("fraction-context final row cardinality drift")

    replacement = next((row for row in final_rows if int(row["source_start"]) == EXPECTED_SOURCE_START), None)
    if replacement is None or int(replacement["source_end"]) != EXPECTED_SOURCE_END:
        raise RuntimeError("fraction-context replacement missing")
    if str(replacement.get("source_text") or "") != source or str(replacement.get("target_text") or "") != EXPECTED_TARGET:
        raise RuntimeError("fraction-context replacement source/target drift")
    rescue = dict((replacement.get("payload") or {}).get("tc_big_fraction_context_rescue") or {})
    trigger = dict(rescue.get("trigger") or {})
    selection = dict(rescue.get("selection") or {})
    if rescue.get("contract") != TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT or rescue.get("selector_contract") != TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT or rescue.get("trigger_contract") != TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT:
        raise RuntimeError("fraction-context contract drift")
    if rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
        raise RuntimeError("fraction-context replacement is not raw TC-big rank0")
    if trigger.get("eligible") is not True or dict(trigger.get("truncation_pair") or {}).get("required") != "1222/6000":
        raise RuntimeError("fraction-context trigger drift")
    if selection.get("accepted") is not True or selection.get("required_fraction_exactly_once") is not True or selection.get("truncated_fraction_absent") is not True:
        raise RuntimeError("fraction-context selection drift")

    base_outside = {(int(row["source_start"]), int(row["source_end"])): _identity(row) for row in base_rows if not (EXPECTED_SOURCE_START <= int(row["source_start"]) and int(row["source_end"]) <= EXPECTED_SOURCE_END)}
    final_outside = {(int(row["source_start"]), int(row["source_end"])): _identity(row) for row in final_rows if not (int(row["source_start"]) == EXPECTED_SOURCE_START and int(row["source_end"]) == EXPECTED_SOURCE_END)}
    untouched_exact = base_outside == final_outside
    if not untouched_exact or len(base_outside) != BASE_SEGMENTS - len(members):
        raise RuntimeError("fraction-context changed unrelated source/target rows")

    semantic = _semantic_review(source, base_target, EXPECTED_TARGET)
    if semantic["all_diagnostic_anchors"] is not True or semantic["candidate_split_join_artifact_absent"] is not True:
        raise RuntimeError("fraction-context semantic diagnostics drift")

    final_text = "".join(str(row.get("target_text") or "") for row in final_rows)
    output_path = root / "full-opticks-tc-big-fraction-context-rescue.txt"
    output_path.write_text(final_text, encoding="utf-8")
    with sqlite3.connect(database) as raw:
        integrity = str(raw.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(raw.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError("fraction-context database integrity failure")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off TC-big rank0 whole-context rescue for isolated fraction-denominator truncation over exact run20",
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
        "final_hard_gate_counts": final_inventory["counts"],
        "base_segment_count": BASE_SEGMENTS,
        "final_segment_count": len(final_rows),
        "context_sequence": EXPECTED_CONTEXT,
        "source_start": EXPECTED_SOURCE_START,
        "source_end": EXPECTED_SOURCE_END,
        "member_sequences": EXPECTED_MEMBER_SEQUENCES,
        "replacement_source": source,
        "base_aggregate_target": base_target,
        "replacement_target": EXPECTED_TARGET,
        "trigger": trigger,
        "selection": selection,
        "semantic_review": semantic,
        "untouched_row_count": len(base_outside),
        "untouched_source_target_exact": untouched_exact,
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "foreign_key_violation_count": fk_count,
        "final_database_sha256": _sha(database),
        "final_text_sha256": _sha(output_path),
        **{key: False for key in ("source_bytes_rewritten", "target_rewriting", "placeholders", "post_translation_literal_injection", "corpus_specific_target_patches", "evaluator_weakened", "n_best_cherry_picking")},
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "full-opticks-tc-big-fraction-context-rescue.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "translation_run_id": final_run_id,
        "hard_gate_counts": final_inventory["counts"],
        "segment_count": len(final_rows),
        "accepted_contexts": enabled["tc_big_fraction_context_rescue_accepted_context_sequences"],
        "untouched_row_count": len(base_outside),
        "database_sha256": evidence["final_database_sha256"],
        "text_sha256": evidence["final_text_sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
