from __future__ import annotations

"""Promote the proven illustration structural separator over authenticated run41.

This replay is intentionally narrow. It starts from the exact immutable run41
artifact, changes only the versioned illustration wrapper contract, then composes
the maintained outer Stage12 rescue chain. The two previously hard-failing
``[Illustration: FIG. N.]\n\n_Illustration._`` rows must become clean through
source-planned structural pieces while every unrelated run41 translation span
remains byte/target exact.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_emphasized_modifier_boundary_rescue_stage import (
    run_stage12 as run_product_stage12,
)
from rocketdict.translation_illustration_rescue_stage import (
    ILLUSTRATION_LABEL_RESCUE_CONTRACT,
    ILLUSTRATION_LABEL_SELECTED_PHASE,
    ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
    ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
    ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
    ILLUSTRATION_SOURCE_PLAN_CONTRACT,
    ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-illustration-structural-promotion/1"
BASE_TRANSLATION_RUN_ID = 41
BASE_DB_SHA256 = "e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e"
BASE_OUTPUT_SHA256 = "d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 18, "punctuation": 16, "length": 0, "unique": 33}
EXPECTED_COUNTS = {"numeric_symbol": 18, "punctuation": 14, "length": 0, "unique": 31}
EXPECTED_SOURCE_STARTS = [72401, 90105, 203786]
STRUCTURAL_SOURCE_STARTS = [72401, 90105]
ORDINARY_SOURCE_START = 203786
EXPECTED_SELECTED_RANKS = [0, 0, 0, 0, 0]
EXPECTED_FINAL_SEGMENT_COUNT = 3341
UNSAFE_FLAGS = (
    "source_bytes_rewritten",
    "model_input_source_rewritten",
    "target_rewriting",
    "placeholders",
    "post_translation_literal_injection",
    "corpus_specific_target_patches",
    "evaluator_weakened",
    "n_best_cherry_picking",
    "automatic_n_best_cherry_picking",
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
            raise RuntimeError(f"{label}: sequence drift at {sequence}")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"{label}: source coverage drift at {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label}: incomplete source coverage")


def _hard_counts(rows: list[dict[str, Any]]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    hard: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    for row in _ordered(rows):
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        classes: list[str] = []
        if dict(verdict.get("numeric_symbol") or {}).get("passed") is not True:
            hard["numeric_symbol"] += 1
            classes.append("numeric_symbol")
        if verdict.get("punctuation_passed") is not True:
            hard["punctuation"] += 1
            classes.append("punctuation")
        if verdict.get("length_passed") is not True:
            hard["length"] += 1
            classes.append("length")
        if classes:
            records.append(
                {
                    "sequence_number": int(row["sequence_number"]),
                    "source_start": int(row["source_start"]),
                    "source_end": int(row["source_end"]),
                    "source_text": source,
                    "target_text": target,
                    "hard_failure_classes": classes,
                }
            )
    counts = {
        "numeric_symbol": int(hard["numeric_symbol"]),
        "punctuation": int(hard["punctuation"]),
        "length": int(hard["length"]),
        "unique": len(records),
    }
    return counts, records


def _overlaps(start: int, end: int, intervals: list[tuple[int, int]]) -> bool:
    return any(start < right and end > left for left, right in intervals)


def _assert_unrelated_output_exact(
    base_rows: list[dict[str, Any]],
    final_rows: list[dict[str, Any]],
    intervals: list[tuple[int, int]],
) -> int:
    final_by_span = {
        (int(row["source_start"]), int(row["source_end"]), str(row.get("source_text") or "")):
        str(row.get("target_text") or "")
        for row in final_rows
    }
    checked = 0
    for base in base_rows:
        start = int(base["source_start"])
        end = int(base["source_end"])
        if _overlaps(start, end, intervals):
            continue
        key = (start, end, str(base.get("source_text") or ""))
        if key not in final_by_span:
            raise RuntimeError(f"unrelated source segmentation drift at span {start}:{end}")
        if final_by_span[key] != str(base.get("target_text") or ""):
            raise RuntimeError(f"unrelated target drift at span {start}:{end}")
        checked += 1
    return checked


def _assert_structural_provenance(
    final_rows: list[dict[str, Any]], intervals: list[tuple[int, int]]
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for left, right in intervals:
        pieces = [
            row
            for row in _ordered(final_rows)
            if int(row["source_start"]) >= left and int(row["source_end"]) <= right
        ]
        if len(pieces) != 4:
            raise RuntimeError(f"structural illustration {left}:{right} did not materialize four pieces")
        roles: list[str] = []
        piece_evidence: list[dict[str, Any]] = []
        for row in pieces:
            rescue = dict((row.get("payload") or {}).get("illustration_label_rescue") or {})
            if rescue.get("contract") != ILLUSTRATION_LABEL_RESCUE_CONTRACT:
                raise RuntimeError("illustration structural row contract drift")
            if rescue.get("selector_contract") != ILLUSTRATION_LABEL_SELECTOR_CONTRACT:
                raise RuntimeError("illustration structural row selector drift")
            if rescue.get("source_plan_contract") != ILLUSTRATION_SOURCE_PLAN_CONTRACT:
                raise RuntimeError("illustration structural row source-plan drift")
            if rescue.get("applied") is not True:
                raise RuntimeError("illustration structural row missing applied provenance")
            if rescue.get("raw_rank0_only") is not True:
                raise RuntimeError("illustration structural row lost rank0-only provenance")
            for flag in UNSAFE_FLAGS:
                if rescue.get(flag) is not False:
                    raise RuntimeError(f"illustration structural row unsafe {flag}={rescue.get(flag)!r}")
            role = str(rescue.get("role") or "")
            roles.append(role)
            source = str(row.get("source_text") or "")
            target = str(row.get("target_text") or "")
            if role in {"separator", "trailing"}:
                if rescue.get("source_owned_passthrough") is not True or target != source:
                    raise RuntimeError(f"source-owned {role} drift at {left}:{right}")
            elif role in {"label", "suffix"}:
                if rescue.get("source_owned_passthrough") is not False:
                    raise RuntimeError(f"translated {role} incorrectly marked passthrough")
                if rescue.get("model_input_source_exact") is not True:
                    raise RuntimeError(f"translated {role} lost exact source/model identity")
                if str(rescue.get("model_input") or "") != source:
                    raise RuntimeError(f"translated {role} model input differs from source span")
                if int(rescue.get("selected_rank", -1)) != 0:
                    raise RuntimeError(f"translated {role} selected non-rank0")
            else:
                raise RuntimeError(f"unexpected structural illustration role {role!r}")
            piece_evidence.append(
                {
                    "role": role,
                    "source_start": int(row["source_start"]),
                    "source_end": int(row["source_end"]),
                    "source_text": source,
                    "target_text": target,
                    "model": rescue.get("model"),
                    "model_input": rescue.get("model_input"),
                    "selected_rank": rescue.get("selected_rank"),
                    "source_owned_passthrough": rescue.get("source_owned_passthrough"),
                }
            )
        if roles != ["label", "separator", "suffix", "trailing"]:
            raise RuntimeError(f"structural illustration role order drift: {roles!r}")
        cases.append({"source_span": [left, right], "pieces": piece_evidence})
    return cases


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_ILLUSTRATION_PROMOTION_ROOT",
            "work/illustration-structural-promotion",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(
        os.environ.get("ROCKETDICT_ILLUSTRATION_PROMOTION_DB", root / "rocketdict.sqlite")
    ).resolve()
    if not database.is_file():
        raise RuntimeError(f"promotion database missing: {database}")
    if _sha(database) != BASE_DB_SHA256:
        raise RuntimeError("promotion base database identity drift")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_TRANSLATION_RUN_ID)
        base_rows = get_run_items(connection, BASE_TRANSLATION_RUN_ID, kind="translation_segment")
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run41 translation output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run41 normalized source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="run41")
    base_counts, base_failures = _hard_counts(base_rows)
    if base_counts != BASE_COUNTS:
        raise RuntimeError(f"run41 hard-gate census drift: {base_counts!r}")

    structural_intervals: list[tuple[int, int]] = []
    for start in STRUCTURAL_SOURCE_STARTS:
        candidates = [row for row in base_rows if int(row["source_start"]) == start]
        if len(candidates) != 1:
            raise RuntimeError(f"run41 structural source-start cardinality drift at {start}")
        row = candidates[0]
        structural_intervals.append((start, int(row["source_end"])))
    base_failure_starts = {int(record["source_start"]) for record in base_failures}
    if not set(STRUCTURAL_SOURCE_STARTS).issubset(base_failure_starts):
        raise RuntimeError("run41 no longer contains both structural illustration hard failures")

    parameters = dict(base_parameters)
    parameters.update(
        {
            "enable_illustration_label_rescue": True,
            "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
            "illustration_label_rescue_selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
            "illustration_label_trigger_contract": ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
            "illustration_source_plan_contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
            "illustration_word_target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
            "illustration_label_target_form_contract": ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
            "illustration_label_rescue_phase": ILLUSTRATION_LABEL_SELECTED_PHASE,
        }
    )

    promoted = run_product_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    final_run_id = int(promoted["translation_run_id"])
    if final_run_id == BASE_TRANSLATION_RUN_ID:
        raise RuntimeError("promotion unexpectedly reused run41")

    for flag in UNSAFE_FLAGS:
        if promoted.get(flag) is not False:
            raise RuntimeError(f"promotion unsafe output flag {flag}={promoted.get(flag)!r}")
    if promoted.get("illustration_label_rescue_contract") != ILLUSTRATION_LABEL_RESCUE_CONTRACT:
        raise RuntimeError("promoted illustration contract drift")
    if promoted.get("illustration_label_rescue_selector_contract") != ILLUSTRATION_LABEL_SELECTOR_CONTRACT:
        raise RuntimeError("promoted illustration selector drift")
    if promoted.get("illustration_label_trigger_contract") != ILLUSTRATION_LABEL_TRIGGER_CONTRACT:
        raise RuntimeError("promoted illustration trigger drift")
    if promoted.get("illustration_source_plan_contract") != ILLUSTRATION_SOURCE_PLAN_CONTRACT:
        raise RuntimeError("promoted illustration source-plan drift")
    if promoted.get("illustration_word_target_form_contract") != ILLUSTRATION_WORD_TARGET_FORM_CONTRACT:
        raise RuntimeError("promoted illustration word target-form drift")
    if promoted.get("illustration_label_target_form_contract") != ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT:
        raise RuntimeError("promoted illustration label target-form drift")
    if promoted.get("illustration_label_rescue_source_plan_created_before_mt") is not True:
        raise RuntimeError("promotion lost pre-MT source-plan invariant")
    if promoted.get("illustration_label_rescue_source_owned_structural_passthrough") is not True:
        raise RuntimeError("promotion lost structural passthrough invariant")
    if promoted.get("illustration_label_rescue_model_inputs_source_exact") is not True:
        raise RuntimeError("promotion lost source/model-input exactness")
    if promoted.get("illustration_label_rescue_raw_rank0_only") is not True:
        raise RuntimeError("promotion lost raw-rank0-only invariant")
    if list(promoted.get("illustration_label_rescue_attempted_source_starts") or []) != EXPECTED_SOURCE_STARTS:
        raise RuntimeError("promotion illustration attempt cohort drift")
    if list(promoted.get("illustration_label_rescue_accepted_source_starts") or []) != EXPECTED_SOURCE_STARTS:
        raise RuntimeError("promotion illustration accepted cohort drift")
    if list(promoted.get("illustration_label_rescue_rejected_source_starts") or []) != []:
        raise RuntimeError("promotion unexpectedly rejected an illustration candidate")
    if int(promoted.get("illustration_label_rescue_ordinary_accepted_count") or 0) != 1:
        raise RuntimeError("promotion ordinary illustration compatibility drift")
    if int(promoted.get("illustration_label_rescue_structural_accepted_count") or 0) != 2:
        raise RuntimeError("promotion structural illustration acceptance drift")
    if list(promoted.get("illustration_label_rescue_selected_ranks") or []) != EXPECTED_SELECTED_RANKS:
        raise RuntimeError("promotion illustration selected-rank drift")

    with connect(database, readonly=True) as connection:
        final_run = get_run(connection, final_run_id)
        final_rows = get_run_items(connection, final_run_id, kind="translation_segment")
    _coverage(final_rows, content, label="promoted")
    if len(final_rows) != EXPECTED_FINAL_SEGMENT_COUNT:
        raise RuntimeError(
            f"promoted segment-count drift: {len(final_rows)} != {EXPECTED_FINAL_SEGMENT_COUNT}"
        )
    if int(promoted.get("segment_count") or 0) != len(final_rows):
        raise RuntimeError("promoted output segment count disagrees with persisted rows")
    if int(promoted.get("source_character_sum") or 0) != len(content):
        raise RuntimeError("promoted source character sum drift")

    final_counts, final_failures = _hard_counts(final_rows)
    if final_counts != EXPECTED_COUNTS:
        raise RuntimeError(f"promoted hard-gate census drift: {final_counts!r}")
    final_failure_starts = {int(record["source_start"]) for record in final_failures}
    if set(STRUCTURAL_SOURCE_STARTS) & final_failure_starts:
        raise RuntimeError("promoted structural illustration remains in hard-failure census")

    unrelated_exact_count = _assert_unrelated_output_exact(
        base_rows, final_rows, structural_intervals
    )
    structural_cases = _assert_structural_provenance(final_rows, structural_intervals)

    ordinary_rows = [
        row for row in final_rows
        if int(row["source_start"]) == ORDINARY_SOURCE_START
    ]
    if len(ordinary_rows) != 1:
        raise RuntimeError("ordinary illustration compatibility source-start drift")
    ordinary_rescue = dict(
        (ordinary_rows[0].get("payload") or {}).get("illustration_label_rescue") or {}
    )
    if ordinary_rescue.get("candidate_kind") != "ordinary_linguistic_suffix":
        raise RuntimeError("ordinary illustration compatibility provenance drift")
    if int(ordinary_rescue.get("selected_rank", -1)) != 0:
        raise RuntimeError("ordinary illustration compatibility lost rank0")

    final_db_sha = _sha(database)
    final_text = "".join(str(row.get("target_text") or "") for row in _ordered(final_rows))
    final_text_sha = hashlib.sha256(final_text.encode("utf-8")).hexdigest()
    (root / "full-opticks-illustration-structural-promotion.txt").write_text(
        final_text, encoding="utf-8"
    )

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "promotion replay of source-planned illustration structural wrapper over authenticated full-corpus run41",
        "base_translation_run_id": BASE_TRANSLATION_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_database_sha256": BASE_DB_SHA256,
        "base_hard_gate_counts": base_counts,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_char_count": len(content),
        "promoted_translation_run_id": final_run_id,
        "promoted_translation_output_sha256": str(final_run.get("output_sha256") or ""),
        "promoted_database_sha256": final_db_sha,
        "promoted_text_sha256": final_text_sha,
        "promoted_segment_count": len(final_rows),
        "promoted_hard_gate_counts": final_counts,
        "hard_gate_delta": {
            key: final_counts[key] - base_counts[key]
            for key in ("numeric_symbol", "punctuation", "length", "unique")
        },
        "illustration_attempted_source_starts": list(promoted.get("illustration_label_rescue_attempted_source_starts") or []),
        "illustration_accepted_source_starts": list(promoted.get("illustration_label_rescue_accepted_source_starts") or []),
        "illustration_rejected_source_starts": list(promoted.get("illustration_label_rescue_rejected_source_starts") or []),
        "illustration_selected_ranks": list(promoted.get("illustration_label_rescue_selected_ranks") or []),
        "illustration_selected_targets": list(promoted.get("illustration_label_rescue_selected_targets") or []),
        "illustration_model_request_count": int(promoted.get("illustration_label_rescue_model_request_count") or 0),
        "illustration_model_batch_count": int(promoted.get("illustration_label_rescue_model_batch_count") or 0),
        "structural_cases": structural_cases,
        "ordinary_compatibility_source_start": ORDINARY_SOURCE_START,
        "unrelated_base_span_target_exact_count": unrelated_exact_count,
        "residual_source_starts": [int(record["source_start"]) for record in final_failures],
        "source_coverage_byte_exact": True,
        "unrelated_translation_spans_target_exact": True,
        "source_plan_created_before_mt": True,
        "source_owned_structural_passthrough": True,
        "model_inputs_source_exact": True,
        "raw_rank0_only": True,
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "full-opticks-illustration-structural-promotion.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "promoted_translation_run_id": final_run_id,
                "promoted_translation_output_sha256": evidence["promoted_translation_output_sha256"],
                "promoted_database_sha256": final_db_sha,
                "promoted_text_sha256": final_text_sha,
                "promoted_hard_gate_counts": final_counts,
                "hard_gate_delta": evidence["hard_gate_delta"],
                "illustration_accepted_source_starts": evidence["illustration_accepted_source_starts"],
                "illustration_selected_ranks": evidence["illustration_selected_ranks"],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
