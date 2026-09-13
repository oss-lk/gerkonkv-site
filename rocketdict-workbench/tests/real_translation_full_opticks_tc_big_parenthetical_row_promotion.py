from __future__ import annotations

"""Promote the proven bounded TC-big parenthetical row rescue over run56.

This replay starts from the exact authenticated run56 SQLite artifact.  The
existing outer Stage12 chain must resolve by cache to run56; only the new
row-local wrapper is allowed to create a new translation run.  The source and
segmentation remain byte-identical.  Exactly four previously proven residual
rows may change target text, while every unrelated run56 target stays exact.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_parenthetical_row_rescue_stage import (
    TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT,
    TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT,
    TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT,
    run_stage12 as run_product_stage12,
)

SCHEMA = "rocketdict-full-opticks-tc-big-parenthetical-row-promotion/1"
BASE_TRANSLATION_RUN_ID = 56
BASE_DB_SHA256 = "cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56"
BASE_OUTPUT_SHA256 = "2971fb099674aa81c14e0b75590c5fbcb943d1ea3477efb0ceedbd81bd69fbc5"
BASE_PARAMETERS_SHA256 = "7e0ff2456509d2ffd6a8ed89c68e54a73ea51af45a5308e35f2a3bba5d4044b1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 18, "punctuation": 14, "length": 0, "unique": 31}
EXPECTED_COUNTS = {"numeric_symbol": 18, "punctuation": 10, "length": 0, "unique": 27}
EXPECTED_BASE_SEGMENT_COUNT = 3335
EXPECTED_FINAL_SEGMENT_COUNT = 3335
EXPECTED_ATTEMPTED_SEQUENCES = [741, 1497, 2108, 2589, 2719, 3081]
EXPECTED_ACCEPTED_SEQUENCES = [741, 1497, 2108, 2589]
EXPECTED_REJECTED_SEQUENCES = [2719, 3081]
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


def _target_sha(rows: list[dict[str, Any]]) -> str:
    raw = "".join(str(row.get("target_text") or "") for row in _ordered(rows))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_exact_base(database: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], str]:
    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_TRANSLATION_RUN_ID)
        rows = _ordered(
            get_run_items(
                connection,
                BASE_TRANSLATION_RUN_ID,
                kind="translation_segment",
            )
        )
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if run.get("status") != "completed":
        raise RuntimeError("run56 is not completed")
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run56 output identity drift")
    if str(run.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("run56 parameter identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run56 source identity drift")
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError(f"run56 SQLite integrity drift: {integrity=} {fk_count=}")
    if len(rows) != EXPECTED_BASE_SEGMENT_COUNT:
        raise RuntimeError(f"run56 segment count drift: {len(rows)}")
    content = str(document["content_text"])
    _coverage(rows, content, label="run56")
    counts, _ = _hard_counts(rows)
    if counts != BASE_COUNTS:
        raise RuntimeError(f"run56 hard-count drift: {counts}")
    return run, rows, document, content


def _parameters(run: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(run.get("parameters") or {})
    if not parameters:
        raw = run.get("parameters_json")
        if isinstance(raw, str) and raw:
            parameters = json.loads(raw)
    if not parameters:
        raise RuntimeError("run56 stored parameters unavailable")
    parameters["enable_tc_big_parenthetical_row_rescue"] = True
    parameters["tc_big_parenthetical_row_rescue_contract"] = (
        TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT
    )
    parameters["tc_big_parenthetical_row_selector_contract"] = (
        TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT
    )
    parameters["tc_big_parenthetical_row_trigger_contract"] = (
        TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT
    )
    return parameters


def _by_sequence(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row["sequence_number"]): row for row in rows}


def _assert_row_identity_and_diff(
    base_rows: list[dict[str, Any]], final_rows: list[dict[str, Any]]
) -> tuple[list[int], int]:
    if len(base_rows) != len(final_rows):
        raise RuntimeError("promotion changed translation segment cardinality")
    changed: list[int] = []
    unchanged = 0
    for base, final in zip(_ordered(base_rows), _ordered(final_rows), strict=True):
        sequence = int(base["sequence_number"])
        if int(final["sequence_number"]) != sequence:
            raise RuntimeError(f"promotion sequence drift at {sequence}")
        for key in ("source_start", "source_end", "source_text"):
            if final.get(key) != base.get(key):
                raise RuntimeError(f"promotion source identity drift at {sequence} {key}")
        if str(final.get("target_text") or "") != str(base.get("target_text") or ""):
            changed.append(sequence)
        else:
            unchanged += 1
    if changed != EXPECTED_ACCEPTED_SEQUENCES:
        raise RuntimeError(f"promotion target-change cohort drift: {changed}")
    if unchanged != EXPECTED_FINAL_SEGMENT_COUNT - len(EXPECTED_ACCEPTED_SEQUENCES):
        raise RuntimeError(f"promotion unchanged target count drift: {unchanged}")
    return changed, unchanged


def _assert_provenance(
    base_rows: list[dict[str, Any]], final_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    base_by_sequence = _by_sequence(base_rows)
    final_by_sequence = _by_sequence(final_rows)
    cases: list[dict[str, Any]] = []
    for sequence in EXPECTED_ACCEPTED_SEQUENCES:
        base = base_by_sequence[sequence]
        final = final_by_sequence[sequence]
        payload = dict(final.get("payload") or {})
        rescue = dict(payload.get("tc_big_parenthetical_row_rescue") or {})
        if rescue.get("applied") is not True:
            raise RuntimeError(f"promotion missing rescue provenance at {sequence}")
        if rescue.get("contract") != TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT:
            raise RuntimeError(f"promotion contract drift at {sequence}")
        if rescue.get("selector_contract") != TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT:
            raise RuntimeError(f"promotion selector drift at {sequence}")
        if rescue.get("trigger_contract") != TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT:
            raise RuntimeError(f"promotion trigger drift at {sequence}")
        source = str(final.get("source_text") or "")
        target = str(final.get("target_text") or "")
        if rescue.get("model_input") != source or rescue.get("model_input_equals_source") is not True:
            raise RuntimeError(f"promotion model-input drift at {sequence}")
        if rescue.get("raw_model_selected") is not True or int(rescue.get("raw_model_rank", -1)) != 0:
            raise RuntimeError(f"promotion rank0 provenance drift at {sequence}")
        hypotheses = list(payload.get("hypotheses") or [])
        if len(hypotheses) != 1:
            raise RuntimeError(f"promotion hypothesis cardinality drift at {sequence}")
        hypothesis = dict(hypotheses[0])
        if int(hypothesis.get("rank", -1)) != 0 or str(hypothesis.get("text") or "") != target:
            raise RuntimeError(f"promotion persisted hypothesis drift at {sequence}")
        if dict(rescue.get("selection") or {}).get("accepted") is not True:
            raise RuntimeError(f"promotion selector was not accepted at {sequence}")
        if dict(rescue.get("trigger") or {}).get("eligible") is not True:
            raise RuntimeError(f"promotion trigger was not eligible at {sequence}")
        if str(rescue.get("base_target") or "") != str(base.get("target_text") or ""):
            raise RuntimeError(f"promotion base target provenance drift at {sequence}")
        for flag in UNSAFE_FLAGS:
            if rescue.get(flag) is not False:
                raise RuntimeError(f"promotion unsafe flag {flag} at {sequence}")
        cases.append(
            {
                "sequence_number": sequence,
                "source_start": int(final["source_start"]),
                "source_end": int(final["source_end"]),
                "source_text": source,
                "base_target": str(base.get("target_text") or ""),
                "promoted_target": target,
                "raw_rank": 0,
                "model_input_equals_source": True,
                "trigger": rescue["trigger"],
                "selection": rescue["selection"],
            }
        )
    for sequence in EXPECTED_REJECTED_SEQUENCES:
        base = base_by_sequence[sequence]
        final = final_by_sequence[sequence]
        if str(final.get("target_text") or "") != str(base.get("target_text") or ""):
            raise RuntimeError(f"promotion rejected row target drift at {sequence}")
        rescue = dict((final.get("payload") or {}).get("tc_big_parenthetical_row_rescue") or {})
        if rescue.get("applied") is not False:
            raise RuntimeError(f"promotion rejected row marked applied at {sequence}")
    return cases


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_PARENTHESES_ROW_PROMOTION_ROOT",
            "work/full-opticks-tc-big-parenthetical-row-promotion",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(
        os.environ.get(
            "ROCKETDICT_PARENTHESES_ROW_PROMOTION_DB",
            root / "rocketdict.sqlite",
        )
    ).resolve()
    if not database.is_file():
        raise RuntimeError(f"promotion database missing: {database}")
    if _sha(database) != BASE_DB_SHA256:
        raise RuntimeError("promotion requires exact authenticated run56 SQLite")

    base_run, base_rows, document, content = _load_exact_base(database)
    base_target_sha = _target_sha(base_rows)
    parameters = _parameters(base_run)
    context_run_id = int(dict(base_run.get("output") or {})["context_run_id"])

    promoted_output = run_product_stage12(
        database,
        context_run_id=context_run_id,
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    promoted_run_id = int(promoted_output["translation_run_id"])
    if promoted_run_id == BASE_TRANSLATION_RUN_ID:
        raise RuntimeError("parenthetical row wrapper did not create a promotion run")
    if int(promoted_output.get("base_translation_run_id") or 0) != BASE_TRANSLATION_RUN_ID:
        raise RuntimeError(
            "parenthetical row wrapper did not cache-resolve exact run56 as its base"
        )
    if str(promoted_output.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("parenthetical row promotion base output SHA drift")
    if int(promoted_output.get("tc_big_parenthetical_row_rescue_attempt_count") or -1) != len(EXPECTED_ATTEMPTED_SEQUENCES):
        raise RuntimeError("parenthetical row promotion attempt count drift")
    if int(promoted_output.get("tc_big_parenthetical_row_rescue_accepted_count") or -1) != len(EXPECTED_ACCEPTED_SEQUENCES):
        raise RuntimeError("parenthetical row promotion accepted count drift")
    if int(promoted_output.get("tc_big_parenthetical_row_rescue_rejected_count") or -1) != len(EXPECTED_REJECTED_SEQUENCES):
        raise RuntimeError("parenthetical row promotion rejected count drift")
    if list(promoted_output.get("tc_big_parenthetical_row_rescue_selected_ranks") or []) != [0] * len(EXPECTED_ACCEPTED_SEQUENCES):
        raise RuntimeError("parenthetical row promotion selected-rank drift")

    with connect(database, readonly=True) as connection:
        promoted_run = get_run(connection, promoted_run_id)
        final_rows = _ordered(
            get_run_items(connection, promoted_run_id, kind="translation_segment")
        )
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if promoted_run.get("status") != "completed":
        raise RuntimeError("promoted run is not completed")
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError(f"promoted SQLite integrity drift: {integrity=} {fk_count=}")
    if len(final_rows) != EXPECTED_FINAL_SEGMENT_COUNT:
        raise RuntimeError(f"promoted segment count drift: {len(final_rows)}")
    _coverage(final_rows, content, label="promoted")
    changed_sequences, unchanged_target_count = _assert_row_identity_and_diff(
        base_rows, final_rows
    )
    cases = _assert_provenance(base_rows, final_rows)
    final_counts, residuals = _hard_counts(final_rows)
    if final_counts != EXPECTED_COUNTS:
        raise RuntimeError(f"parenthetical row promotion hard-count drift: {final_counts}")

    database_sha = _sha(database)
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-Opticks promotion of source-defined default-off TC-big row-local parenthetical rescue from exact run56",
        "base_translation_run_id": BASE_TRANSLATION_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_translation_parameters_sha256": BASE_PARAMETERS_SHA256,
        "base_database_sha256": BASE_DB_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "base_hard_counts": BASE_COUNTS,
        "base_segment_count": len(base_rows),
        "base_target_sha256": base_target_sha,
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": str(promoted_run.get("output_sha256") or ""),
        "promoted_database_sha256": database_sha,
        "promoted_target_sha256": _target_sha(final_rows),
        "promoted_hard_counts": final_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed_sequences,
        "unchanged_target_count": unchanged_target_count,
        "expected_attempted_sequences": EXPECTED_ATTEMPTED_SEQUENCES,
        "expected_accepted_sequences": EXPECTED_ACCEPTED_SEQUENCES,
        "expected_rejected_sequences": EXPECTED_REJECTED_SEQUENCES,
        "promotion_cases": cases,
        "residual_sequences": [int(item["sequence_number"]) for item in residuals],
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violation_count": fk_count,
        "base_cache_identity_exact": True,
        "source_coverage_byte_exact": True,
        "unrelated_targets_byte_exact": True,
        "model_input_equals_immutable_source": True,
        "raw_rank0_only": True,
        "semantic_review_basis": "focused run56 row DOE c82ce59e48eb380a4cf23b41e69574271cf8480659f0815617732fd4cc56ce5e",
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
    evidence_path = root / "parenthetical-row-promotion-evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "base_translation_run_id": BASE_TRANSLATION_RUN_ID,
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": evidence[
            "promoted_translation_output_sha256"
        ],
        "promoted_database_sha256": database_sha,
        "promoted_target_sha256": evidence["promoted_target_sha256"],
        "promoted_hard_counts": final_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed_sequences,
        "unchanged_target_count": unchanged_target_count,
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
