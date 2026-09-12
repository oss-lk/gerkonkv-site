from __future__ import annotations

"""Persist and audit the default-off dense figure-label OPUS rescue over run20."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_dense_figure_group_rescue_stage import (
    DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
    DENSE_FIGURE_GROUP_SELECTED_PHASE,
    DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
    DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
    MAX_GROUP_NLP_TOKENS,
    MIN_DISTINCT_TECHNICAL_LABELS,
    MIN_TECHNICAL_LABEL_OCCURRENCES,
    run_stage12 as run_dense_figure_stage12,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-dense-figure-label-group-rescue-optin/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 14, "length": 0, "unique": 33}
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 19, "punctuation": 14, "length": 0, "unique": 32}
BASE_SEGMENTS = 3341
EXPECTED_FINAL_SEGMENTS = 3339
EXPECTED_GROUP = [1640, 1641]
EXPECTED_SOURCE_START = 302134
EXPECTED_SOURCE_END = 302883
EXPECTED_MEMBER_SEQUENCES = [1761, 1762, 1763]
EXPECTED_MEMBER_STARTS = [302134, 302426, 302721]
EXPECTED_GROUP_NLP_TOKENS = 176
EXPECTED_LABEL_OCCURRENCES = 14
EXPECTED_DISTINCT_LABELS = 12
EXPECTED_TARGET = (
    "[Иллюстрация: FIG. 6.] Но дальше, чтобы определить широту этих цветов в каждом "
    "кольце или серии, пусть A1 конструирует наименьшую толщину и A3 наибольшую "
    "толщину, при которой отражается экстремальная фиолетовая в первой серии, и "
    "пусть HI и HL проектируют аналогичные пределы для крайне красного, и пусть "
    "промежуточные цвета ограничиваются промежуточными частями линий 1I и 3L, на "
    "которых написаны названия этих цветов, и так далее: но с этой осторожностью, "
    "что рефлексионы считаются самыми сильными в промежуточных пространствах, 2K, "
    "6N, 10Q, &c. и с этого момента постепенно уменьшаются к этим пределам, 1I, "
    "3L, 5M, 7O, &c. с любой стороны; где вы не должны считать их точно "
    "ограниченными, а должны бесконечно разлагаться."
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
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
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
        "illustration_payload": "[иллюстрация: fig. 6.]" in lowered,
        "first_series": "первой серии" in lowered,
        "violet": "фиолет" in lowered,
        "red": "красн" in lowered,
        "intermediate_colours": "промежуточн" in lowered and "цвет" in lowered,
        "strongest_clause": "самыми сильными" in lowered,
        "decrease_clause": "уменьша" in lowered,
        "limits_clause": "предел" in lowered,
        "dense_labels": all(label in target for label in ("A1", "A3", "HI", "HL", "1I", "3L", "2K", "6N", "10Q", "5M", "7O")),
    }
    verdict = evaluate_rescue_pair(source, target)
    return {
        "diagnostic_anchors": anchors,
        "all_diagnostic_anchors": all(anchors.values()),
        "numeric_symbol_clean": (verdict.get("numeric_symbol") or {}).get("passed") is True,
        "punctuation_clean": verdict.get("punctuation_passed") is True,
        "length_clean": verdict.get("length_passed") is True,
        "strict_research_clean": verdict.get("strict_research_passed") is True,
        "research_acceptance": "accepted_for_default_off_full_corpus_replay",
        "product_default_promotion_allowed": False,
        "manual_semantic_review_still_required_for_product_promotion": True,
        "known_lexical_debt": [
            "Reflexions is rendered as the calque 'рефлексионы'",
            "decay indefinitely is rendered as 'бесконечно разлагаться'",
        ],
        "quality_rationale": (
            "The raw whole-group candidate restores the complete omitted clause and all "
            "technical labels while retaining some lexical/style debt; this is sufficient "
            "for research replay, not Product-default promotion."
        ),
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_DENSE_FIGURE_GROUP_PRODUCT_ROOT",
            "work/full-opticks-dense-figure-label-group-rescue",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("dense figure replay requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        )
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        document = get_document(connection, int(base_output["document_version_id"]))

    if int(base_run.get("stage_number") or -1) != 12:
        raise RuntimeError("run20 is not Stage12")
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run20 base")
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run20 baseline drift: counts={base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    context_by_sequence = {
        int(row["sequence_number"]): row for row in context_rows
    }
    contexts = [context_by_sequence[index] for index in EXPECTED_GROUP]
    source = "".join(str(row.get("source_text") or "") for row in contexts)
    if [int(contexts[0]["source_start"]), int(contexts[-1]["source_end"])] != [
        EXPECTED_SOURCE_START,
        EXPECTED_SOURCE_END,
    ]:
        raise RuntimeError("dense figure context span drift")
    if source != content[EXPECTED_SOURCE_START:EXPECTED_SOURCE_END]:
        raise RuntimeError("dense figure context source drift")
    members = [
        row
        for row in base_rows
        if EXPECTED_SOURCE_START <= int(row["source_start"])
        and int(row["source_end"]) <= EXPECTED_SOURCE_END
    ]
    if [int(row["sequence_number"]) for row in members] != EXPECTED_MEMBER_SEQUENCES:
        raise RuntimeError("dense figure member sequence drift")
    if [int(row["source_start"]) for row in members] != EXPECTED_MEMBER_STARTS:
        raise RuntimeError("dense figure member start drift")
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("dense figure base members do not reconstruct source")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_dense_figure_label_group_rescue": True,
            "dense_figure_label_group_rescue_contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
            "dense_figure_label_group_selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
            "dense_figure_label_group_trigger_contract": DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
            "dense_figure_label_group_rescue_phase": DENSE_FIGURE_GROUP_SELECTED_PHASE,
            "dense_figure_label_group_max_nlp_tokens": MAX_GROUP_NLP_TOKENS,
        }
    )
    enabled = run_dense_figure_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id != BASE_RUN_ID + 1:
        raise RuntimeError(f"dense figure final run identity drift: {final_run_id}")
    if int(enabled.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("dense figure wrapper did not compose directly over run20")
    if str(enabled.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("dense figure base output SHA drift")
    if enabled.get("dense_figure_label_group_rescue_attempt_count") != 1:
        raise RuntimeError("dense figure attempt-count drift")
    if enabled.get("dense_figure_label_group_rescue_accepted_count") != 1:
        raise RuntimeError("dense figure accepted-count drift")
    if enabled.get("dense_figure_label_group_rescue_rejected_count") != 0:
        raise RuntimeError("dense figure rejected-count drift")
    if list(enabled.get("dense_figure_label_group_rescue_attempted_groups") or []) != [EXPECTED_GROUP]:
        raise RuntimeError("dense figure attempt cohort drift")
    if list(enabled.get("dense_figure_label_group_rescue_accepted_groups") or []) != [EXPECTED_GROUP]:
        raise RuntimeError("dense figure accepted cohort drift")
    if list(enabled.get("dense_figure_label_group_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("dense figure rescue did not use raw rank0")
    if list(enabled.get("dense_figure_label_group_rescue_selected_targets") or []) != [EXPECTED_TARGET]:
        raise RuntimeError("dense figure raw OPUS rank0 drift from DOE")
    if enabled.get("base_segment_count") != BASE_SEGMENTS:
        raise RuntimeError("dense figure base segment-count drift")
    if enabled.get("segment_count") != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("dense figure final segment-count drift")

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = _ordered(
            get_run_items(connection, final_run_id, kind="translation_segment")
        )
    _coverage(final_rows, content, label="dense figure final")
    final_inventory = _inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS:
        raise RuntimeError(
            f"dense figure final hard-gate drift: {final_inventory['counts']!r}"
        )
    if len(final_rows) != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("dense figure final row cardinality drift")

    replacement = next(
        (row for row in final_rows if int(row["source_start"]) == EXPECTED_SOURCE_START),
        None,
    )
    if replacement is None or int(replacement["source_end"]) != EXPECTED_SOURCE_END:
        raise RuntimeError("dense figure replacement row missing")
    if str(replacement.get("source_text") or "") != source:
        raise RuntimeError("dense figure replacement source drift")
    if str(replacement.get("target_text") or "") != EXPECTED_TARGET:
        raise RuntimeError("dense figure replacement target drift")
    rescue = dict(
        (replacement.get("payload") or {}).get("dense_figure_label_group_rescue") or {}
    )
    trigger = dict(rescue.get("trigger") or {})
    selection = dict(rescue.get("selection") or {})
    if rescue.get("contract") != DENSE_FIGURE_GROUP_RESCUE_CONTRACT:
        raise RuntimeError("dense figure rescue contract drift")
    if rescue.get("selector_contract") != DENSE_FIGURE_GROUP_SELECTOR_CONTRACT:
        raise RuntimeError("dense figure selector contract drift")
    if rescue.get("trigger_contract") != DENSE_FIGURE_GROUP_TRIGGER_CONTRACT:
        raise RuntimeError("dense figure trigger contract drift")
    if rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
        raise RuntimeError("dense figure replacement is not raw OPUS rank0")
    if trigger.get("eligible") is not True:
        raise RuntimeError("dense figure source trigger no longer eligible")
    if trigger.get("group_nlp_token_count") != EXPECTED_GROUP_NLP_TOKENS:
        raise RuntimeError("dense figure group token-count drift")
    if trigger.get("technical_label_occurrences") != EXPECTED_LABEL_OCCURRENCES:
        raise RuntimeError("dense figure technical-label occurrence drift")
    if trigger.get("technical_label_distinct_count") != EXPECTED_DISTINCT_LABELS:
        raise RuntimeError("dense figure distinct-label drift")
    if trigger.get("technical_label_occurrence_minimum") != MIN_TECHNICAL_LABEL_OCCURRENCES:
        raise RuntimeError("dense figure occurrence threshold drift")
    if trigger.get("technical_label_distinct_minimum") != MIN_DISTINCT_TECHNICAL_LABELS:
        raise RuntimeError("dense figure distinct threshold drift")
    if selection.get("accepted") is not True:
        raise RuntimeError("dense figure persisted selection is not accepted")
    if selection.get("technical_label_sequence_exact") is not True:
        raise RuntimeError("dense figure label sequence not exact")
    if selection.get("illustration_payload_exact") is not True:
        raise RuntimeError("dense figure illustration payload not exact")
    if selection.get("target_alpha_non_decreasing") is not True:
        raise RuntimeError("dense figure candidate loses aggregate alphabetic content")

    base_outside = {
        (int(row["source_start"]), int(row["source_end"])): _identity(row)
        for row in base_rows
        if not (
            EXPECTED_SOURCE_START <= int(row["source_start"])
            and int(row["source_end"]) <= EXPECTED_SOURCE_END
        )
    }
    final_outside = {
        (int(row["source_start"]), int(row["source_end"])): _identity(row)
        for row in final_rows
        if not (
            int(row["source_start"]) == EXPECTED_SOURCE_START
            and int(row["source_end"]) == EXPECTED_SOURCE_END
        )
    }
    untouched_exact = base_outside == final_outside
    if not untouched_exact or len(base_outside) != BASE_SEGMENTS - len(members):
        raise RuntimeError("dense figure rescue changed unrelated source/target rows")

    semantic = _semantic_review(source, EXPECTED_TARGET)
    if semantic["all_diagnostic_anchors"] is not True:
        raise RuntimeError("dense figure semantic diagnostic anchor drift")

    final_text = "".join(str(row.get("target_text") or "") for row in final_rows)
    output_path = root / "full-opticks-dense-figure-label-group-rescue.txt"
    output_path.write_text(final_text, encoding="utf-8")

    with sqlite3.connect(database) as raw:
        integrity = str(raw.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(raw.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError("dense figure replay database integrity failure")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted default-off dense figure-label planner-group OPUS rank0 rescue over exact run20",
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
        "attempted_groups": enabled["dense_figure_label_group_rescue_attempted_groups"],
        "accepted_groups": enabled["dense_figure_label_group_rescue_accepted_groups"],
        "selected_ranks": enabled["dense_figure_label_group_rescue_selected_ranks"],
        "source_start": EXPECTED_SOURCE_START,
        "source_end": EXPECTED_SOURCE_END,
        "member_sequences": EXPECTED_MEMBER_SEQUENCES,
        "member_source_starts": EXPECTED_MEMBER_STARTS,
        "replacement_source": source,
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
        **{
            key: False
            for key in (
                "source_bytes_rewritten",
                "target_rewriting",
                "placeholders",
                "post_translation_literal_injection",
                "corpus_specific_target_patches",
                "evaluator_weakened",
                "n_best_cherry_picking",
            )
        },
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "full-opticks-dense-figure-label-group-rescue.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "translation_run_id": final_run_id,
        "hard_gate_counts": final_inventory["counts"],
        "segment_count": len(final_rows),
        "attempted_groups": evidence["attempted_groups"],
        "accepted_groups": evidence["accepted_groups"],
        "untouched_row_count": evidence["untouched_row_count"],
        "database_sha256": evidence["final_database_sha256"],
        "text_sha256": evidence["final_text_sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
