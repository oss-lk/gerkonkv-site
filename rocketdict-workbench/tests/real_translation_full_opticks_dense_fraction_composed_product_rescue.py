from __future__ import annotations

"""Persisted full-Opticks composition of two independent default-off Stage12 rescues.

The exact run20 database is replayed with the dense figure-label OPUS rank0
wrapper first and the isolated fraction-denominator TC-big rank0 wrapper second.
The experiment proves that the two source-defined regions remain disjoint, that
each wrapper selects the exact raw rank0 candidate already accepted in its own
full-corpus replay, and that the composition removes two numeric hard failures
without changing punctuation/length hard failures or any unrelated source/target
row. This is research evidence only; lexical debt in both candidates keeps
Product-default promotion explicitly disabled.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_dense_figure_group_rescue_stage import (
    DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
    DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
    DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
    DENSE_FIGURE_GROUP_SELECTED_PHASE,
    MAX_GROUP_NLP_TOKENS,
)
from rocketdict.translation_tc_big_fraction_context_rescue_stage import (
    MAX_CONTEXT_NLP_TOKENS,
    TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_SELECTED_PHASE,
    run_stage12 as run_composed_stage12,
)

import real_translation_full_opticks_dense_figure_group_product_rescue as dense_audit
import real_translation_full_opticks_tc_big_fraction_context_product_rescue as fraction_audit

SCHEMA = "rocketdict-full-opticks-dense-fraction-composed-rescue-optin/1"
BASE_DATABASE_SHA256 = dense_audit.BASE_DATABASE_SHA256
BASE_RUN_ID = dense_audit.BASE_RUN_ID
BASE_OUTPUT_SHA256 = dense_audit.BASE_OUTPUT_SHA256
SOURCE_TEXT_SHA256 = dense_audit.SOURCE_TEXT_SHA256
BASE_COUNTS = dense_audit.BASE_COUNTS
BASE_SEGMENTS = dense_audit.BASE_SEGMENTS
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 18, "punctuation": 14, "length": 0, "unique": 31}
EXPECTED_DENSE_RUN_ID = 21
EXPECTED_FINAL_RUN_ID = 22
EXPECTED_FINAL_SEGMENTS = 3338
EXPECTED_UNTOUCHED_ROWS = 3336


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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
    return sorted(rows, key=lambda row: int(row["source_start"]))


def _outside_rescue_spans(row: dict[str, Any]) -> bool:
    start = int(row["source_start"])
    end = int(row["source_end"])
    spans = (
        (fraction_audit.EXPECTED_SOURCE_START, fraction_audit.EXPECTED_SOURCE_END),
        (dense_audit.EXPECTED_SOURCE_START, dense_audit.EXPECTED_SOURCE_END),
    )
    return not any(span_start <= start and end <= span_end for span_start, span_end in spans)


def _replacement(rows: list[dict[str, Any]], *, start: int, end: int) -> dict[str, Any]:
    matches = [
        row
        for row in rows
        if int(row["source_start"]) == start and int(row["source_end"]) == end
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one replacement for {start}:{end}, found {len(matches)}")
    return matches[0]


def _assert_safety_flags(output: dict[str, Any], *, label: str) -> None:
    for key in (
        "source_bytes_rewritten",
        "target_rewriting",
        "placeholders",
        "post_translation_literal_injection",
        "corpus_specific_target_patches",
        "evaluator_weakened",
        "n_best_cherry_picking",
    ):
        if output.get(key) is not False:
            raise RuntimeError(f"{label} unsafe flag drift: {key}={output.get(key)!r}")


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_DENSE_FRACTION_COMPOSED_PRODUCT_ROOT",
            "work/full-opticks-dense-fraction-composed-rescue",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("composed replay requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        )
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    dense_audit._coverage(base_rows, content, label="run20 base")
    base_inventory = dense_audit._inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run20 baseline drift: counts={base_inventory['counts']!r}, rows={len(base_rows)}"
        )

    fraction_span = (
        fraction_audit.EXPECTED_SOURCE_START,
        fraction_audit.EXPECTED_SOURCE_END,
    )
    dense_span = (dense_audit.EXPECTED_SOURCE_START, dense_audit.EXPECTED_SOURCE_END)
    if not (fraction_span[1] <= dense_span[0] or dense_span[1] <= fraction_span[0]):
        raise RuntimeError("fraction and dense rescue spans overlap")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_dense_figure_label_group_rescue": True,
            "dense_figure_label_group_rescue_contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
            "dense_figure_label_group_selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
            "dense_figure_label_group_trigger_contract": DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
            "dense_figure_label_group_rescue_phase": DENSE_FIGURE_GROUP_SELECTED_PHASE,
            "dense_figure_label_group_max_nlp_tokens": MAX_GROUP_NLP_TOKENS,
            "enable_tc_big_fraction_context_rescue": True,
            "tc_big_fraction_context_rescue_contract": TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
            "tc_big_fraction_context_selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
            "tc_big_fraction_context_trigger_contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
            "tc_big_fraction_context_rescue_phase": TC_BIG_FRACTION_CONTEXT_SELECTED_PHASE,
            "tc_big_fraction_context_max_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
        }
    )
    enabled = run_composed_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id != EXPECTED_FINAL_RUN_ID:
        raise RuntimeError(f"composed final run identity drift: {final_run_id}")
    if int(enabled.get("base_translation_run_id") or -1) != EXPECTED_DENSE_RUN_ID:
        raise RuntimeError("fraction layer did not compose directly over dense run21")
    if enabled.get("tc_big_fraction_context_rescue_attempt_count") != 1:
        raise RuntimeError("fraction composed attempt-count drift")
    if enabled.get("tc_big_fraction_context_rescue_accepted_count") != 1:
        raise RuntimeError("fraction composed accepted-count drift")
    if list(enabled.get("tc_big_fraction_context_rescue_accepted_context_sequences") or []) != [
        fraction_audit.EXPECTED_CONTEXT
    ]:
        raise RuntimeError("fraction composed accepted context drift")
    if list(enabled.get("tc_big_fraction_context_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("fraction composed candidate is not raw rank0")
    if list(enabled.get("tc_big_fraction_context_rescue_selected_targets") or []) != [
        fraction_audit.EXPECTED_TARGET
    ]:
        raise RuntimeError("fraction composed raw TC-big target drift")
    _assert_safety_flags(enabled, label="fraction output")

    with connect(database, readonly=True) as connection:
        dense_run = get_run(connection, EXPECTED_DENSE_RUN_ID)
        dense_rows = _ordered(
            get_run_items(connection, EXPECTED_DENSE_RUN_ID, kind="translation_segment")
        )
        dense_output = dict(dense_run.get("output") or {})
        final_run = get_run(connection, final_run_id)
        final_rows = _ordered(
            get_run_items(connection, final_run_id, kind="translation_segment")
        )
    dense_audit._coverage(dense_rows, content, label="dense intermediate")
    dense_audit._coverage(final_rows, content, label="composed final")
    if int(dense_output.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("dense layer did not compose directly over run20")
    if str(dense_output.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("dense base output SHA drift")
    if list(dense_output.get("dense_figure_label_group_rescue_accepted_groups") or []) != [
        dense_audit.EXPECTED_GROUP
    ]:
        raise RuntimeError("dense accepted group drift")
    if list(dense_output.get("dense_figure_label_group_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("dense composed candidate is not raw rank0")
    if list(dense_output.get("dense_figure_label_group_rescue_selected_targets") or []) != [
        dense_audit.EXPECTED_TARGET
    ]:
        raise RuntimeError("dense composed raw OPUS target drift")
    _assert_safety_flags(dense_output, label="dense output")

    dense_inventory = dense_audit._inventory(dense_rows)
    if dense_inventory["counts"] != dense_audit.EXPECTED_FINAL_COUNTS:
        raise RuntimeError(f"dense intermediate hard-gate drift: {dense_inventory['counts']!r}")
    final_inventory = dense_audit._inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS:
        raise RuntimeError(f"composed final hard-gate drift: {final_inventory['counts']!r}")
    if len(dense_rows) != dense_audit.EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError("dense intermediate segment-count drift")
    if len(final_rows) != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError(f"composed final segment-count drift: {len(final_rows)}")

    fraction_row = _replacement(
        final_rows,
        start=fraction_audit.EXPECTED_SOURCE_START,
        end=fraction_audit.EXPECTED_SOURCE_END,
    )
    dense_row = _replacement(
        final_rows,
        start=dense_audit.EXPECTED_SOURCE_START,
        end=dense_audit.EXPECTED_SOURCE_END,
    )
    if str(fraction_row.get("target_text") or "") != fraction_audit.EXPECTED_TARGET:
        raise RuntimeError("final fraction replacement target drift")
    if str(dense_row.get("target_text") or "") != dense_audit.EXPECTED_TARGET:
        raise RuntimeError("final dense replacement target drift")

    base_outside = {
        (int(row["source_start"]), int(row["source_end"])): dense_audit._identity(row)
        for row in base_rows
        if _outside_rescue_spans(row)
    }
    final_outside = {
        (int(row["source_start"]), int(row["source_end"])): dense_audit._identity(row)
        for row in final_rows
        if _outside_rescue_spans(row)
    }
    untouched_exact = base_outside == final_outside
    if not untouched_exact or len(base_outside) != EXPECTED_UNTOUCHED_ROWS:
        raise RuntimeError(
            f"composed unrelated-row drift: exact={untouched_exact}, count={len(base_outside)}"
        )

    fraction_base_target = "".join(
        str(row.get("target_text") or "")
        for row in base_rows
        if fraction_audit.EXPECTED_SOURCE_START <= int(row["source_start"])
        and int(row["source_end"]) <= fraction_audit.EXPECTED_SOURCE_END
    )
    fraction_source = content[
        fraction_audit.EXPECTED_SOURCE_START : fraction_audit.EXPECTED_SOURCE_END
    ]
    dense_source = content[dense_audit.EXPECTED_SOURCE_START : dense_audit.EXPECTED_SOURCE_END]
    fraction_semantic = fraction_audit._semantic_review(
        fraction_source,
        fraction_base_target,
        fraction_audit.EXPECTED_TARGET,
    )
    dense_semantic = dense_audit._semantic_review(dense_source, dense_audit.EXPECTED_TARGET)
    if fraction_semantic["all_diagnostic_anchors"] is not True:
        raise RuntimeError("fraction semantic anchor drift in composition")
    if fraction_semantic["candidate_split_join_artifact_absent"] is not True:
        raise RuntimeError("fraction split-join artifact survived composition")
    if dense_semantic["all_diagnostic_anchors"] is not True:
        raise RuntimeError("dense semantic anchor drift in composition")

    final_text = "".join(str(row.get("target_text") or "") for row in final_rows)
    output_path = root / "full-opticks-dense-fraction-composed-rescue.txt"
    output_path.write_text(final_text, encoding="utf-8")
    with sqlite3.connect(database) as raw:
        integrity = str(raw.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(raw.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError("composed replay database integrity failure")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "persisted composition of independent dense-figure OPUS rank0 and fraction-context TC-big rank0 research rescues over exact run20",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "dense_intermediate_translation_run_id": EXPECTED_DENSE_RUN_ID,
        "dense_intermediate_translation_output_sha256": str(dense_run.get("output_sha256") or ""),
        "dense_intermediate_hard_gate_counts": dense_inventory["counts"],
        "final_translation_run_id": final_run_id,
        "final_translation_output_sha256": str(final_run.get("output_sha256") or ""),
        "final_hard_gate_counts": final_inventory["counts"],
        "base_segment_count": BASE_SEGMENTS,
        "dense_intermediate_segment_count": len(dense_rows),
        "final_segment_count": len(final_rows),
        "rescues": {
            "fraction_context": {
                "context_sequence": fraction_audit.EXPECTED_CONTEXT,
                "source_span": list(fraction_span),
                "replacement_target": fraction_audit.EXPECTED_TARGET,
                "selected_rank": 0,
                "model": "TC-big",
                "semantic_review": fraction_semantic,
            },
            "dense_figure_group": {
                "context_group": dense_audit.EXPECTED_GROUP,
                "source_span": list(dense_span),
                "replacement_target": dense_audit.EXPECTED_TARGET,
                "selected_rank": 0,
                "model": "OPUS",
                "semantic_review": dense_semantic,
            },
        },
        "rescue_spans_disjoint": True,
        "untouched_row_count": len(base_outside),
        "untouched_source_target_exact": untouched_exact,
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "foreign_key_violation_count": fk_count,
        "final_database_sha256": _sha(database),
        "final_text_sha256": _sha(output_path),
        "known_lexical_debt": {
            "fraction_context": fraction_semantic["known_lexical_debt"],
            "dense_figure_group": dense_semantic["known_lexical_debt"],
        },
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
    evidence_path = root / "full-opticks-dense-fraction-composed-rescue.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "translation_run_id": final_run_id,
        "hard_gate_counts": final_inventory["counts"],
        "segment_count": len(final_rows),
        "untouched_row_count": len(base_outside),
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
