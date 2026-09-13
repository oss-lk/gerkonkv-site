from __future__ import annotations

"""Promote only TC-big numeric-row variants reproduced by current CT2 rank0."""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_tc_big_numeric_row_rescue_stage import (
    TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT,
    run_stage12 as run_product_stage12,
)
from rocketdict.translation_tc_big_numeric_row_rules import (
    SELECTOR_CONTRACT,
    TRIGGER_CONTRACT,
    VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
    VARIANT_DENSE_FORMULA_MISSING,
    VARIANT_PROGRESSION_DUPLICATE,
)

SCHEMA = "rocketdict-full-opticks-tc-big-numeric-row-promotion/2"
BASE_RUN_ID = 57
BASE_DB_SHA256 = "f6eae41e02211a35f3519c8abcdeceb2699f4f0089dc2c2fa10800682fe06115"
BASE_OUTPUT_SHA256 = "c29e50beafd12f2a6670a3a34f4057beab9b23db9ab9f9a4b22850601b174195"
BASE_PARAMETERS_SHA256 = "9632693ee4f6060328feb031099efe9d4e4e3dc206245f7cec227b69bf346aa5"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 18, "punctuation": 10, "length": 0, "unique": 27}
EXPECTED_COUNTS = {"numeric_symbol": 16, "punctuation": 10, "length": 0, "unique": 25}
SEGMENT_COUNT = 3335
EXPECTED_ACCEPTED = {
    2288: (401232, VARIANT_DENSE_FORMULA_MISSING),
    2355: (414576, VARIANT_APOSTROPHE_DECIMAL_TRUNCATION),
}
EXPECTED_REJECTED_SOURCE_START = 268952
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
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _hard_counts(rows: list[dict[str, Any]]) -> tuple[dict[str, int], list[int]]:
    counts: Counter[str] = Counter()
    residuals: list[int] = []
    for row in _ordered(rows):
        verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        failed = False
        if dict(verdict.get("numeric_symbol") or {}).get("passed") is not True:
            counts["numeric_symbol"] += 1
            failed = True
        if verdict.get("punctuation_passed") is not True:
            counts["punctuation"] += 1
            failed = True
        if verdict.get("length_passed") is not True:
            counts["length"] += 1
            failed = True
        if failed:
            residuals.append(int(row["sequence_number"]))
    return {
        "numeric_symbol": int(counts["numeric_symbol"]),
        "punctuation": int(counts["punctuation"]),
        "length": int(counts["length"]),
        "unique": len(residuals),
    }, residuals


def _coverage(rows: list[dict[str, Any]], content: str) -> None:
    cursor = 0
    for sequence, row in enumerate(_ordered(rows)):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError(f"sequence drift at {sequence}")
        start, end = int(row["source_start"]), int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"source coverage drift at {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError("incomplete source coverage")


def _target_sha(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        "".join(str(row.get("target_text") or "") for row in _ordered(rows)).encode("utf-8")
    ).hexdigest()


def _parameters(run: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(run.get("parameters") or {})
    if not parameters and isinstance(run.get("parameters_json"), str):
        parameters = json.loads(str(run["parameters_json"]))
    if not parameters:
        raise RuntimeError("run57 parameters unavailable")
    parameters.update(
        {
            "enable_tc_big_numeric_row_rescue": True,
            "tc_big_numeric_row_rescue_contract": TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT,
            "tc_big_numeric_row_selector_contract": SELECTOR_CONTRACT,
            "tc_big_numeric_row_trigger_contract": TRIGGER_CONTRACT,
        }
    )
    return parameters


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_NUMERIC_ROW_PROMOTION_ROOT", "work/full-opticks-tc-big-numeric-row-promotion")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(os.environ.get("ROCKETDICT_NUMERIC_ROW_PROMOTION_DB", root / "rocketdict.sqlite")).resolve()
    if not database.is_file() or _sha(database) != BASE_DB_SHA256:
        raise RuntimeError("exact run57 SQLite required")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        base_output = dict(base_run.get("output") or {})
        document = get_document(connection, int(base_output["document_version_id"]))
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if base_run.get("status") != "completed" or integrity != "ok" or fk != 0:
        raise RuntimeError("run57 persistence identity/integrity drift")
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run57 output SHA drift")
    if str(base_run.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("run57 parameters SHA drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    if len(base_rows) != SEGMENT_COUNT:
        raise RuntimeError("run57 segment count drift")
    content = str(document["content_text"])
    _coverage(base_rows, content)
    base_counts, _ = _hard_counts(base_rows)
    if base_counts != BASE_COUNTS:
        raise RuntimeError(f"run57 hard-count drift: {base_counts}")

    promoted = run_product_stage12(
        database,
        context_run_id=int(base_output["context_run_id"]),
        parameters=_parameters(base_run),
        implementation="opus-en-ru-ct2",
    )
    promoted_run_id = int(promoted["translation_run_id"])
    diagnostic = {
        "base_translation_run_id": promoted.get("base_translation_run_id"),
        "attempt_count": promoted.get("tc_big_numeric_row_rescue_attempt_count"),
        "accepted_count": promoted.get("tc_big_numeric_row_rescue_accepted_count"),
        "rejected_count": promoted.get("tc_big_numeric_row_rescue_rejected_count"),
        "variant_attempt_counts": promoted.get("tc_big_numeric_row_rescue_variant_attempt_counts"),
        "variant_accept_counts": promoted.get("tc_big_numeric_row_rescue_variant_accept_counts"),
        "accepted_source_starts": promoted.get("tc_big_numeric_row_rescue_accepted_source_starts"),
        "selected_variants": promoted.get("tc_big_numeric_row_rescue_selected_variants"),
        "rejected": promoted.get("tc_big_numeric_row_rescue_rejected"),
    }
    print(json.dumps({"numeric_row_diagnostic": diagnostic}, ensure_ascii=False, sort_keys=True))
    if int(promoted.get("base_translation_run_id") or 0) != BASE_RUN_ID:
        raise RuntimeError("wrapper did not cache-resolve exact run57")
    if str(promoted.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("base output SHA drift")
    if int(promoted.get("tc_big_numeric_row_rescue_attempt_count") or -1) != 3:
        raise RuntimeError("attempt count drift")
    if int(promoted.get("tc_big_numeric_row_rescue_accepted_count") or -1) != 2:
        raise RuntimeError("accepted count drift")
    if int(promoted.get("tc_big_numeric_row_rescue_rejected_count") or -1) != 1:
        raise RuntimeError("rejected count drift")

    rejected = list(promoted.get("tc_big_numeric_row_rescue_rejected") or [])
    if len(rejected) != 1 or int(rejected[0].get("source_start", -1)) != EXPECTED_REJECTED_SOURCE_START:
        raise RuntimeError(f"progression negative-control cohort drift: {rejected}")
    if str(rejected[0].get("variant") or "") != VARIANT_PROGRESSION_DUPLICATE:
        raise RuntimeError("progression negative-control variant drift")
    rejected_selection = dict(rejected[0].get("selection") or {})
    if rejected_selection.get("accepted") is not False:
        raise RuntimeError("progression negative control unexpectedly accepted")
    if not (
        rejected_selection.get("variant_notation_preserved") is False
        or dict(rejected_selection.get("emphasis_markup") or {}).get("passed") is False
    ):
        raise RuntimeError("progression rejection lost its safety reason")

    with connect(database, readonly=True) as connection:
        promoted_run = get_run(connection, promoted_run_id)
        final_rows = _ordered(get_run_items(connection, promoted_run_id, kind="translation_segment"))
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if promoted_run.get("status") != "completed" or integrity != "ok" or fk != 0:
        raise RuntimeError("promoted persistence/integrity drift")
    if len(final_rows) != SEGMENT_COUNT:
        raise RuntimeError("promoted segment count drift")
    _coverage(final_rows, content)

    changed: list[int] = []
    cases: list[dict[str, Any]] = []
    for base, final in zip(base_rows, final_rows, strict=True):
        sequence = int(base["sequence_number"])
        for key in ("source_start", "source_end", "source_text"):
            if final.get(key) != base.get(key):
                raise RuntimeError(f"source identity drift at {sequence}:{key}")
        if str(final.get("target_text") or "") == str(base.get("target_text") or ""):
            continue
        changed.append(sequence)
        if sequence not in EXPECTED_ACCEPTED:
            raise RuntimeError(f"unexpected target change at {sequence}")
        expected_start, expected_variant = EXPECTED_ACCEPTED[sequence]
        if int(final["source_start"]) != expected_start:
            raise RuntimeError(f"source-start drift at {sequence}")
        rescue = dict((final.get("payload") or {}).get("tc_big_numeric_row_rescue") or {})
        if rescue.get("applied") is not True or rescue.get("variant") != expected_variant:
            raise RuntimeError(f"rescue provenance drift at {sequence}")
        source = str(final.get("source_text") or "")
        target = str(final.get("target_text") or "")
        if rescue.get("model_input") != source or rescue.get("model_input_equals_source") is not True:
            raise RuntimeError(f"model-input drift at {sequence}")
        if rescue.get("raw_model_selected") is not True or int(rescue.get("raw_model_rank", -1)) != 0:
            raise RuntimeError(f"rank0 drift at {sequence}")
        hypotheses = list((final.get("payload") or {}).get("hypotheses") or [])
        if len(hypotheses) != 1 or int(hypotheses[0].get("rank", -1)) != 0 or str(hypotheses[0].get("text") or "") != target:
            raise RuntimeError(f"persisted hypothesis drift at {sequence}")
        trigger = dict(rescue.get("trigger") or {})
        selection = dict(rescue.get("selection") or {})
        if trigger.get("eligible") is not True or selection.get("accepted") is not True or selection.get("variant_notation_preserved") is not True:
            raise RuntimeError(f"trigger/selector drift at {sequence}")
        runtime = dict(rescue.get("runtime_identity") or {})
        if runtime.get("revision") != "708be1d372fe4c358a352f404e6dc9ca0126ba48":
            raise RuntimeError(f"TC-big revision drift at {sequence}")
        if runtime.get("model_safetensors_sha256") != "e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416":
            raise RuntimeError(f"TC-big weights drift at {sequence}")
        for flag in UNSAFE_FLAGS:
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe flag {flag} at {sequence}")
        cases.append({
            "sequence_number": sequence,
            "source_start": int(final["source_start"]),
            "source_end": int(final["source_end"]),
            "variant": expected_variant,
            "base_target": str(base.get("target_text") or ""),
            "promoted_target": target,
            "runtime_identity": runtime,
            "trigger": trigger,
            "selection": selection,
        })
    if changed != sorted(EXPECTED_ACCEPTED):
        raise RuntimeError(f"target-change cohort drift: {changed}")

    final_counts, residuals = _hard_counts(final_rows)
    if final_counts != EXPECTED_COUNTS:
        raise RuntimeError(f"hard-count drift: {final_counts}")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_translation_parameters_sha256": BASE_PARAMETERS_SHA256,
        "base_database_sha256": BASE_DB_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_counts": BASE_COUNTS,
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": str(promoted_run.get("output_sha256") or ""),
        "promoted_database_sha256": _sha(database),
        "promoted_target_sha256": _target_sha(final_rows),
        "promoted_hard_counts": final_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed,
        "unchanged_target_count": SEGMENT_COUNT - len(changed),
        "promotion_cases": cases,
        "rejected_progression_negative_control": rejected[0],
        "residual_sequences": residuals,
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violation_count": fk,
        "base_cache_identity_exact": True,
        "source_coverage_byte_exact": True,
        "unrelated_targets_byte_exact": True,
        "model_input_equals_immutable_source": True,
        "raw_rank0_only": True,
        "ct2_parity_workflow_run_id": 34626241784,
        "ct2_parity_artifact_id": 10274549063,
        "ct2_parity_evidence_sha256": "360c5f9b537ef46b2a178d3f3062c1633f5e54a126c59aa51be27ff0eb5f48d8",
        **{flag: False for flag in UNSAFE_FLAGS},
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "numeric-row-promotion-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": evidence["promoted_translation_output_sha256"],
        "promoted_database_sha256": evidence["promoted_database_sha256"],
        "promoted_target_sha256": evidence["promoted_target_sha256"],
        "promoted_hard_counts": final_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed,
        "rejected_progression_source_start": EXPECTED_REJECTED_SOURCE_START,
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
