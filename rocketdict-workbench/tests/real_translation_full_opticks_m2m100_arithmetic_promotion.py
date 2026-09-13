from __future__ import annotations

"""One-shot full-Opticks promotion harness for the source-verified M2M100 arithmetic row rescue."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.api.operations import run_stage12 as run_product_stage12
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_m2m100_arithmetic_rescue_stage import (
    M2M100_ARITHMETIC_RESCUE_CONTRACT,
)
from rocketdict.translation_m2m100_arithmetic_rules import (
    M2M100_ARITHMETIC_SELECTOR_CONTRACT,
    M2M100_ARITHMETIC_TRIGGER_CONTRACT,
)
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-m2m100-arithmetic-promotion/1"
BASE_TRANSLATION_RUN_ID = 58
BASE_DATABASE_SHA256 = "a24f35d6f8bb4747a4fc301511f383b8b866846a3c448655fce1b9359cc0ac94"
BASE_OUTPUT_SHA256 = "60349256eac118e9af7aa1366761342cd2041bb6ade4db04b45c78b46a8c6e5d"
BASE_PARAMETERS_SHA256 = "1cf60c7b582640c3923ea685ed329eb685a7b80e502e11507d99c752e6342315"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SEGMENT_COUNT = 3335
EXPECTED_BASE_COUNTS = {"numeric_symbol": 16, "punctuation": 10, "length": 0, "unique": 25}
EXPECTED_PROMOTED_COUNTS = {"numeric_symbol": 15, "punctuation": 10, "length": 0, "unique": 24}
EXPECTED_CHANGED_SEQUENCE = 2739
EXPECTED_SOURCE_START = 483234
_UNSAFE_FLAGS = (
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


def _target_sha(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        "".join(str(row.get("target_text") or "") for row in _ordered(rows)).encode("utf-8")
    ).hexdigest()


def _coverage(rows: list[dict[str, Any]], content: str, *, label: str) -> None:
    ordered = _ordered(rows)
    if len(ordered) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError(f"{label} segment-count drift: {len(ordered)}")
    cursor = 0
    pieces: list[str] = []
    for expected_sequence, row in enumerate(ordered):
        if int(row["sequence_number"]) != expected_sequence:
            raise RuntimeError(f"{label} sequence drift at {expected_sequence}")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or not (start < end <= len(content)):
            raise RuntimeError(f"{label} source span drift at {expected_sequence}: {start}:{end} cursor={cursor}")
        if content[start:end] != source:
            raise RuntimeError(f"{label} immutable source mismatch at {expected_sequence}")
        pieces.append(source)
        cursor = end
    if cursor != len(content) or "".join(pieces) != content:
        raise RuntimeError(f"{label} source coverage is not byte-exact")


def _hard_counts(rows: list[dict[str, Any]]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    numeric = 0
    punctuation = 0
    length = 0
    residuals: list[dict[str, Any]] = []
    for row in _ordered(rows):
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        numeric_failed = dict(verdict.get("numeric_symbol") or {}).get("passed") is not True
        punctuation_failed = verdict.get("punctuation_passed") is not True
        length_failed = verdict.get("length_passed") is not True
        numeric += int(numeric_failed)
        punctuation += int(punctuation_failed)
        length += int(length_failed)
        if numeric_failed or punctuation_failed or length_failed:
            residuals.append(
                {
                    "sequence_number": int(row["sequence_number"]),
                    "source_start": int(row["source_start"]),
                    "numeric_symbol_failed": numeric_failed,
                    "punctuation_failed": punctuation_failed,
                    "length_failed": length_failed,
                }
            )
    return {
        "numeric_symbol": numeric,
        "punctuation": punctuation,
        "length": length,
        "unique": len(residuals),
    }, residuals


def _assert_changed_case(
    base_row: dict[str, Any], final_row: dict[str, Any]
) -> dict[str, Any]:
    if int(base_row["sequence_number"]) != EXPECTED_CHANGED_SEQUENCE:
        raise RuntimeError("unexpected changed base sequence")
    if int(base_row["source_start"]) != EXPECTED_SOURCE_START:
        raise RuntimeError("unexpected changed source start")
    source = str(base_row.get("source_text") or "")
    if source != str(final_row.get("source_text") or ""):
        raise RuntimeError("changed row source drift")
    if str(base_row.get("target_text") or "") == str(final_row.get("target_text") or ""):
        raise RuntimeError("expected arithmetic target did not change")

    payload = dict(final_row.get("payload") or {})
    rescue = dict(payload.get("m2m100_arithmetic_rescue") or {})
    if rescue.get("contract") != M2M100_ARITHMETIC_RESCUE_CONTRACT:
        raise RuntimeError("arithmetic rescue contract drift")
    if rescue.get("trigger_contract") != M2M100_ARITHMETIC_TRIGGER_CONTRACT:
        raise RuntimeError("arithmetic trigger contract drift")
    if rescue.get("selector_contract") != M2M100_ARITHMETIC_SELECTOR_CONTRACT:
        raise RuntimeError("arithmetic selector contract drift")
    if rescue.get("applied") is not True:
        raise RuntimeError("arithmetic rescue was not marked applied")
    if rescue.get("model_input") != source or rescue.get("model_input_equals_source") is not True:
        raise RuntimeError("arithmetic model input is not exact immutable source")
    if rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
        raise RuntimeError("arithmetic persisted candidate is not unique raw rank0")
    if payload.get("selected_rank") != 0:
        raise RuntimeError("translation payload selected rank drift")
    hypotheses = list(payload.get("hypotheses") or [])
    if len(hypotheses) != 1 or int(hypotheses[0].get("rank", -1)) != 0:
        raise RuntimeError("arithmetic hypothesis cardinality/rank drift")
    if str(hypotheses[0].get("text") or "") != str(final_row.get("target_text") or ""):
        raise RuntimeError("persisted target is not the raw rank0 hypothesis")

    trigger = dict(rescue.get("trigger") or {})
    restatement = dict(trigger.get("source_restatement") or {})
    if trigger.get("eligible") is not True or restatement.get("arithmetic_verified") is not True:
        raise RuntimeError("source arithmetic trigger is not verified")
    a = int(restatement["a"])
    b = int(restatement["b"])
    c = int(restatement["c"])
    if a * b != c or int(restatement.get("product") or -1) != c:
        raise RuntimeError("source arithmetic invariant drift")

    selection = dict(rescue.get("selection") or {})
    notation = dict(selection.get("arithmetic_notation") or {})
    if selection.get("accepted") is not True:
        raise RuntimeError("arithmetic rank0 selector did not accept persisted candidate")
    if selection.get("strictly_eligible") is not True:
        raise RuntimeError("arithmetic rank0 is not strict-gate eligible")
    if dict(selection.get("emphasis_markup") or {}).get("passed") is not True:
        raise RuntimeError("arithmetic rank0 emphasis drift")
    if notation.get("numeric_sequence_exact") is not True:
        raise RuntimeError("arithmetic numeric sequence drift")
    if notation.get("multiplication_operator_preserved") is not True:
        raise RuntimeError("arithmetic multiplication notation drift")
    for flag in _UNSAFE_FLAGS:
        if rescue.get(flag) is not False:
            raise RuntimeError(f"unsafe arithmetic rescue flag drift: {flag}")

    return {
        "sequence_number": EXPECTED_CHANGED_SEQUENCE,
        "source_start": EXPECTED_SOURCE_START,
        "source_end": int(final_row["source_end"]),
        "base_target_sha256": hashlib.sha256(
            str(base_row.get("target_text") or "").encode("utf-8")
        ).hexdigest(),
        "promoted_target_sha256": hashlib.sha256(
            str(final_row.get("target_text") or "").encode("utf-8")
        ).hexdigest(),
        "source_arithmetic": {"a": a, "b": b, "c": c, "product": a * b},
        "raw_rank": 0,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_M2M100_ARITHMETIC_PROMOTION_ROOT",
            "work/full-opticks-m2m100-arithmetic-promotion",
        )
    ).resolve()
    database = Path(
        os.environ.get(
            "ROCKETDICT_M2M100_ARITHMETIC_PROMOTION_DB",
            root / "rocketdict.sqlite",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("M2M100 arithmetic promotion requires exact authenticated run58 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_TRANSLATION_RUN_ID)
        base_rows = _ordered(
            get_run_items(connection, BASE_TRANSLATION_RUN_ID, kind="translation_segment")
        )
        base_output = dict(base_run.get("output") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
    if base_run.get("status") != "completed":
        raise RuntimeError("run58 base is not completed")
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run58 output SHA drift")
    if str(base_run.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("run58 parameters SHA drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run58 source identity drift")
    content = str(document["content_text"])
    _coverage(base_rows, content, label="base")
    base_counts, _base_residuals = _hard_counts(base_rows)
    if base_counts != EXPECTED_BASE_COUNTS:
        raise RuntimeError(f"run58 hard-count drift: {base_counts}")

    parameters = dict(base_run.get("parameters") or {})
    parameters.update(
        {
            "enable_m2m100_arithmetic_rescue": True,
            "m2m100_arithmetic_rescue_contract": M2M100_ARITHMETIC_RESCUE_CONTRACT,
            "m2m100_arithmetic_selector_contract": M2M100_ARITHMETIC_SELECTOR_CONTRACT,
            "m2m100_arithmetic_trigger_contract": M2M100_ARITHMETIC_TRIGGER_CONTRACT,
        }
    )
    context_run_id = int(base_output["context_run_id"])
    promoted_output = run_product_stage12(
        database=database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    promoted_run_id = int(promoted_output["translation_run_id"])
    if promoted_run_id == BASE_TRANSLATION_RUN_ID:
        raise RuntimeError("M2M100 arithmetic wrapper did not create a promotion run")
    if int(promoted_output.get("base_translation_run_id") or 0) != BASE_TRANSLATION_RUN_ID:
        raise RuntimeError("M2M100 arithmetic wrapper did not cache-resolve exact run58")
    if str(promoted_output.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("M2M100 arithmetic base output SHA drift")
    if int(promoted_output.get("m2m100_arithmetic_rescue_attempt_count") or -1) != 1:
        raise RuntimeError("M2M100 arithmetic attempt count drift")
    if int(promoted_output.get("m2m100_arithmetic_rescue_accepted_count") or -1) != 1:
        raise RuntimeError("M2M100 arithmetic accepted count drift")
    if int(promoted_output.get("m2m100_arithmetic_rescue_rejected_count") or -1) != 0:
        raise RuntimeError("M2M100 arithmetic unexpected rejection")
    if list(promoted_output.get("m2m100_arithmetic_rescue_attempted_source_starts") or []) != [EXPECTED_SOURCE_START]:
        raise RuntimeError("M2M100 arithmetic attempted-source cohort drift")
    if list(promoted_output.get("m2m100_arithmetic_rescue_accepted_source_starts") or []) != [EXPECTED_SOURCE_START]:
        raise RuntimeError("M2M100 arithmetic accepted-source cohort drift")
    if list(promoted_output.get("m2m100_arithmetic_rescue_selected_ranks") or []) != [0]:
        raise RuntimeError("M2M100 arithmetic selected-rank drift")
    for flag in _UNSAFE_FLAGS:
        if promoted_output.get(flag) is not False:
            raise RuntimeError(f"unsafe promotion output flag drift: {flag}")

    with connect(database, readonly=True) as connection:
        promoted_run = get_run(connection, promoted_run_id)
        final_rows = _ordered(
            get_run_items(connection, promoted_run_id, kind="translation_segment")
        )
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if promoted_run.get("status") != "completed":
        raise RuntimeError("promoted arithmetic run is not completed")
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError(f"promoted SQLite integrity drift: {integrity=} {fk_count=}")
    _coverage(final_rows, content, label="promoted")

    changed: list[int] = []
    case: dict[str, Any] | None = None
    for base_row, final_row in zip(base_rows, final_rows, strict=True):
        for field in ("sequence_number", "source_start", "source_end", "source_text"):
            if base_row.get(field) != final_row.get(field):
                raise RuntimeError(f"segmentation/source drift at {base_row['sequence_number']}: {field}")
        if str(base_row.get("target_text") or "") != str(final_row.get("target_text") or ""):
            changed.append(int(base_row["sequence_number"]))
            case = _assert_changed_case(base_row, final_row)
    if changed != [EXPECTED_CHANGED_SEQUENCE] or case is None:
        raise RuntimeError(f"M2M100 arithmetic changed-target cohort drift: {changed}")
    if len(final_rows) - len(changed) != 3334:
        raise RuntimeError("M2M100 arithmetic unrelated target-count drift")

    promoted_counts, residuals = _hard_counts(final_rows)
    if promoted_counts != EXPECTED_PROMOTED_COUNTS:
        raise RuntimeError(f"M2M100 arithmetic promotion hard-count drift: {promoted_counts}")
    if any(int(row["sequence_number"]) == EXPECTED_CHANGED_SEQUENCE for row in residuals):
        raise RuntimeError("M2M100 arithmetic promoted row remains a hard residual")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-Opticks promotion of one source-verified arithmetic restatement using pinned M2M100 CTranslate2 raw rank0 over exact run58",
        "promotion_allowed": True,
        "automatic_product_default_allowed": False,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_TRANSLATION_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_parameters_sha256": BASE_PARAMETERS_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_counts": base_counts,
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": str(promoted_run.get("output_sha256") or ""),
        "promoted_database_sha256": _sha(database),
        "base_target_sha256": _target_sha(base_rows),
        "promoted_target_sha256": _target_sha(final_rows),
        "promoted_hard_counts": promoted_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed,
        "unchanged_target_count": len(final_rows) - len(changed),
        "case": case,
        "runtime_identity": promoted_output.get("m2m100_arithmetic_rescue_runtime"),
        "source_coverage_byte_exact": True,
        "database_integrity_check": integrity,
        "database_foreign_key_violation_count": fk_count,
        **{flag: False for flag in _UNSAFE_FLAGS},
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "m2m100-arithmetic-promotion-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": evidence["promoted_translation_output_sha256"],
        "promoted_database_sha256": evidence["promoted_database_sha256"],
        "promoted_target_sha256": evidence["promoted_target_sha256"],
        "promoted_hard_counts": promoted_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed,
        "accepted_source_start": EXPECTED_SOURCE_START,
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
