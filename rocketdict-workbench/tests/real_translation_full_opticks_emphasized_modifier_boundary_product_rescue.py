from __future__ import annotations

"""Persisted run23 replay for emphasized-modifier numeric boundary rescue.

The exact run22 database is copied byte-for-byte and the new default-off wrapper
is enabled above the already persisted dense-figure + fraction composition.  The
wrapper must discover the source-defined Gutenberg emphasis-boundary family,
attempt only current numeric-hard groups, select only raw OPUS rank0, and remain
fail-closed on the long atmospheric-density counterexample.

This script persists research evidence only.  It does not authorize Product
default promotion.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_emphasized_modifier_boundary_rescue_stage import (
    EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT,
    EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT,
    EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT,
    EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT,
    EMPHASIZED_MODIFIER_BOUNDARY_SELECTED_PHASE,
    MAX_GROUP_NLP_TOKENS,
    run_stage12 as run_emphasized_modifier_stage12,
)

import real_translation_full_opticks_dense_figure_group_product_rescue as dense_audit

SCHEMA = "rocketdict-full-opticks-emphasized-modifier-boundary-rescue-optin/1"
BASE_DATABASE_SHA256 = "5cc0bec1d8ab1c9b0eadb9441819d84676f005a5a3bbb3a068745338469b3206"
BASE_RUN_ID = 22
BASE_OUTPUT_SHA256 = "41cb94e6a2732aee597d8e630cc248487d6e0b7ce5fb9a794d01ecda7f2edb48"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 18, "punctuation": 14, "length": 0, "unique": 31}
BASE_SEGMENTS = 3338
EXPECTED_FINAL_COUNTS = {"numeric_symbol": 17, "punctuation": 14, "length": 0, "unique": 30}
EXPECTED_FINAL_RUN_ID = 23
EXPECTED_FINAL_SEGMENTS = 3337
EXPECTED_UNTOUCHED_ROWS = 3336
EXPECTED_ATTEMPTED_GROUPS = [[2496, 2497], [2633, 2634]]
EXPECTED_ACCEPTED_GROUPS = [[2496, 2497]]
EXPECTED_REJECTED_GROUPS = [[2633, 2634]]
EXPECTED_TARGET = (
    "Свет двигается от Солнца к нам примерно через семь или восемь минут "
    "времени, расстояние которого составляет около 70 000 000 _ английский_ "
    "миль, предположим, что горизонтальный Параллакс Солнца будет около 12'' ."
).replace("12'' .", "12''.")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
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


def _identity(row: dict[str, Any]) -> tuple[int, int, str, str]:
    return (
        int(row["source_start"]),
        int(row["source_end"]),
        str(row.get("source_text") or ""),
        str(row.get("target_text") or ""),
    )


def _assert_safety_flags(output: dict[str, Any]) -> None:
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
            raise RuntimeError(f"unsafe flag drift: {key}={output.get(key)!r}")


def _semantic_review(source: str, base_target: str, candidate: str) -> dict[str, Any]:
    anchors = {
        "distance_70m_present": (
            ("70,000,000" in source)
            and ("70 000 000" in candidate or "70000000" in candidate)
        ),
        "arcseconds_12_preserved": "12''" in source and "12''" in candidate,
        "english_emphasis_retained": "_English_" in source and candidate.count("_") >= 2,
        "miles_not_transliterated": "миль" in candidate.lower() and "майлз" not in candidate.lower(),
        "parallax_relation_retained": (
            "horizontal Parallax" in source
            and "горизонталь" in candidate.lower()
            and "параллакс" in candidate.lower()
        ),
        "travel_time_retained": (
            "seven or eight Minutes" in source
            and "семь или восемь минут" in candidate.lower()
        ),
        "candidate_not_shorter_than_base": (
            sum(ch.isalpha() for ch in candidate)
            >= sum(ch.isalpha() for ch in base_target)
        ),
    }
    return {
        "anchors": anchors,
        "all_diagnostic_anchors": all(anchors.values()),
        "known_lexical_debt": [
            "awkward relative-clause wording around 'which distance'",
            "historical capitalization/style remains model-owned",
        ],
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_EMPHASIZED_MODIFIER_PRODUCT_ROOT",
            "work/full-opticks-emphasized-modifier-boundary-rescue",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("run23 replay requires exact persisted run22 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        )
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        context_run_id = int(base_output["context_run_id"])
        context_rows = get_run_items(
            connection, context_run_id, kind="context_sentence"
        )
        document = get_document(
            connection, int(base_output["document_version_id"])
        )
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run22 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run22 source identity drift")
    content = str(document["content_text"])
    dense_audit._coverage(base_rows, content, label="run22 base")
    base_inventory = dense_audit._inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS or len(base_rows) != BASE_SEGMENTS:
        raise RuntimeError(
            f"run22 baseline drift: counts={base_inventory['counts']!r}, "
            f"rows={len(base_rows)}"
        )

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_emphasized_modifier_boundary_rescue": True,
            "emphasized_modifier_boundary_rescue_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT
            ),
            "emphasized_modifier_boundary_selector_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT
            ),
            "emphasized_modifier_boundary_trigger_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT
            ),
            "emphasized_modifier_boundary_source_contract": (
                EMPHASIZED_MODIFIER_BOUNDARY_SOURCE_CONTRACT
            ),
            "emphasized_modifier_boundary_rescue_phase": (
                EMPHASIZED_MODIFIER_BOUNDARY_SELECTED_PHASE
            ),
            "emphasized_modifier_boundary_max_nlp_tokens": MAX_GROUP_NLP_TOKENS,
        }
    )
    enabled = run_emphasized_modifier_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(enabled["translation_run_id"])
    if final_run_id != EXPECTED_FINAL_RUN_ID:
        raise RuntimeError(f"run23 translation run identity drift: {final_run_id}")
    if int(enabled.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("run23 did not compose directly over persisted run22")
    if list(
        enabled.get("emphasized_modifier_boundary_attempted_context_groups")
        or []
    ) != EXPECTED_ATTEMPTED_GROUPS:
        raise RuntimeError("run23 attempted-group drift")
    if list(
        enabled.get("emphasized_modifier_boundary_accepted_context_groups")
        or []
    ) != EXPECTED_ACCEPTED_GROUPS:
        raise RuntimeError("run23 accepted-group drift")
    if list(
        enabled.get("emphasized_modifier_boundary_rejected_context_groups")
        or []
    ) != EXPECTED_REJECTED_GROUPS:
        raise RuntimeError("run23 rejected-group drift")
    if list(enabled.get("emphasized_modifier_boundary_selected_ranks") or []) != [0]:
        raise RuntimeError("run23 selected candidate is not raw rank0")
    if list(
        enabled.get("emphasized_modifier_boundary_selected_targets") or []
    ) != [EXPECTED_TARGET]:
        raise RuntimeError("run23 raw OPUS target drift")
    _assert_safety_flags(enabled)

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = _ordered(
            get_run_items(
                connection, final_run_id, kind="translation_segment"
            )
        )
    dense_audit._coverage(final_rows, content, label="run23 final")
    final_inventory = dense_audit._inventory(final_rows)
    if final_inventory["counts"] != EXPECTED_FINAL_COUNTS:
        raise RuntimeError(
            f"run23 hard-gate drift: {final_inventory['counts']!r}"
        )
    if len(final_rows) != EXPECTED_FINAL_SEGMENTS:
        raise RuntimeError(
            f"run23 segment-count drift: {len(final_rows)}"
        )

    context_by_sequence = {
        int(row["sequence_number"]): row for row in context_rows
    }
    accepted_contexts = [
        context_by_sequence[sequence] for sequence in EXPECTED_ACCEPTED_GROUPS[0]
    ]
    accepted_start = int(accepted_contexts[0]["source_start"])
    accepted_end = int(accepted_contexts[-1]["source_end"])
    accepted_source = content[accepted_start:accepted_end]
    base_members = [
        row
        for row in base_rows
        if accepted_start <= int(row["source_start"])
        and int(row["source_end"]) <= accepted_end
    ]
    base_target = "".join(
        str(row.get("target_text") or "") for row in base_members
    )
    replacements = [
        row
        for row in final_rows
        if int(row["source_start"]) == accepted_start
        and int(row["source_end"]) == accepted_end
    ]
    if len(replacements) != 1:
        raise RuntimeError(
            f"run23 expected one accepted replacement, found {len(replacements)}"
        )
    replacement = replacements[0]
    if str(replacement.get("target_text") or "") != EXPECTED_TARGET:
        raise RuntimeError("run23 replacement target drift")

    base_outside = {
        (int(row["source_start"]), int(row["source_end"])): _identity(row)
        for row in base_rows
        if not (
            accepted_start <= int(row["source_start"])
            and int(row["source_end"]) <= accepted_end
        )
    }
    final_outside = {
        (int(row["source_start"]), int(row["source_end"])): _identity(row)
        for row in final_rows
        if not (
            int(row["source_start"]) == accepted_start
            and int(row["source_end"]) == accepted_end
        )
    }
    untouched_exact = base_outside == final_outside
    if not untouched_exact or len(base_outside) != EXPECTED_UNTOUCHED_ROWS:
        raise RuntimeError(
            f"run23 unrelated-row drift: exact={untouched_exact}, "
            f"count={len(base_outside)}"
        )

    semantic = _semantic_review(
        accepted_source,
        base_target,
        str(replacement.get("target_text") or ""),
    )
    if semantic["all_diagnostic_anchors"] is not True:
        raise RuntimeError("run23 semantic anchor review failed")

    rejected_contexts = [
        context_by_sequence[sequence] for sequence in EXPECTED_REJECTED_GROUPS[0]
    ]
    rejected_start = int(rejected_contexts[0]["source_start"])
    rejected_end = int(rejected_contexts[-1]["source_end"])
    rejected_base = [
        _identity(row)
        for row in base_rows
        if rejected_start <= int(row["source_start"])
        and int(row["source_end"]) <= rejected_end
    ]
    rejected_final = [
        _identity(row)
        for row in final_rows
        if rejected_start <= int(row["source_start"])
        and int(row["source_end"]) <= rejected_end
    ]
    if rejected_base != rejected_final:
        raise RuntimeError("run23 rejected long group was modified")

    final_text = "".join(
        str(row.get("target_text") or "") for row in final_rows
    )
    output_path = (
        root / "full-opticks-emphasized-modifier-boundary-rescue.txt"
    )
    output_path.write_text(final_text, encoding="utf-8")

    with sqlite3.connect(database) as raw:
        integrity = str(raw.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(raw.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError("run23 database integrity failure")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "persisted run23 default-off OPUS rank0 rescue for source-defined "
            "single-word Gutenberg emphasis modifier boundaries with an existing "
            "numeric hard failure"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "final_translation_run_id": final_run_id,
        "final_translation_output_sha256": str(
            final_run.get("output_sha256") or ""
        ),
        "final_hard_gate_counts": final_inventory["counts"],
        "base_segment_count": BASE_SEGMENTS,
        "final_segment_count": len(final_rows),
        "discovered_group_count": int(
            enabled["emphasized_modifier_boundary_discovered_group_count"]
        ),
        "attempted_context_groups": EXPECTED_ATTEMPTED_GROUPS,
        "accepted_context_groups": EXPECTED_ACCEPTED_GROUPS,
        "rejected_context_groups": EXPECTED_REJECTED_GROUPS,
        "accepted_source_span": [accepted_start, accepted_end],
        "rejected_source_span": [rejected_start, rejected_end],
        "replacement_target": EXPECTED_TARGET,
        "selected_rank": 0,
        "model": "OPUS",
        "semantic_review": semantic,
        "rejected_long_group_unchanged": True,
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
    evidence_path = (
        root / "full-opticks-emphasized-modifier-boundary-rescue.json"
    )
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "translation_run_id": final_run_id,
        "hard_gate_counts": final_inventory["counts"],
        "segment_count": len(final_rows),
        "attempted_context_groups": EXPECTED_ATTEMPTED_GROUPS,
        "accepted_context_groups": EXPECTED_ACCEPTED_GROUPS,
        "rejected_context_groups": EXPECTED_REJECTED_GROUPS,
        "database_sha256": evidence["final_database_sha256"],
        "text_sha256": evidence["final_text_sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
