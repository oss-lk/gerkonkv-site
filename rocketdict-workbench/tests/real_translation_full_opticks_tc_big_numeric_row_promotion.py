from __future__ import annotations

"""Promote the proven source-defined TC-big numeric-row rescue over exact run57."""

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

SCHEMA = "rocketdict-full-opticks-tc-big-numeric-row-promotion/1"
BASE_TRANSLATION_RUN_ID = 57
BASE_DB_SHA256 = "f6eae41e02211a35f3519c8abcdeceb2699f4f0089dc2c2fa10800682fe06115"
BASE_OUTPUT_SHA256 = "c29e50beafd12f2a6670a3a34f4057beab9b23db9ab9f9a4b22850601b174195"
BASE_PARAMETERS_SHA256 = "9632693ee4f6060328feb031099efe9d4e4e3dc206245f7cec227b69bf346aa5"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 18, "punctuation": 10, "length": 0, "unique": 27}
EXPECTED_COUNTS = {"numeric_symbol": 15, "punctuation": 10, "length": 0, "unique": 24}
EXPECTED_SEGMENT_COUNT = 3335
EXPECTED_VARIANTS = {
    1577: VARIANT_PROGRESSION_DUPLICATE,
    2288: VARIANT_DENSE_FORMULA_MISSING,
    2355: VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
}
EXPECTED_SOURCE_STARTS = {1577: 268952, 2288: 401232, 2355: 414576}
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
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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
    residuals: list[dict[str, Any]] = []
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
            residuals.append(
                {
                    "sequence_number": int(row["sequence_number"]),
                    "source_start": int(row["source_start"]),
                    "hard_failure_classes": classes,
                }
            )
    return (
        {
            "numeric_symbol": int(hard["numeric_symbol"]),
            "punctuation": int(hard["punctuation"]),
            "length": int(hard["length"]),
            "unique": len(residuals),
        },
        residuals,
    )


def _target_sha(rows: list[dict[str, Any]]) -> str:
    text = "".join(str(row.get("target_text") or "") for row in _ordered(rows))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_base(database: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], str]:
    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_TRANSLATION_RUN_ID)
        rows = _ordered(get_run_items(connection, BASE_TRANSLATION_RUN_ID, kind="translation_segment"))
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if run.get("status") != "completed":
        raise RuntimeError("run57 is not completed")
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run57 output identity drift")
    if str(run.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("run57 parameter identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run57 source identity drift")
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError(f"run57 SQLite integrity drift: {integrity=} {fk_count=}")
    if len(rows) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError(f"run57 segment count drift: {len(rows)}")
    content = str(document["content_text"])
    _coverage(rows, content, label="run57")
    counts, _ = _hard_counts(rows)
    if counts != BASE_COUNTS:
        raise RuntimeError(f"run57 hard-count drift: {counts}")
    return run, rows, document, content


def _parameters(run: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(run.get("parameters") or {})
    if not parameters:
        raw = run.get("parameters_json")
        if isinstance(raw, str) and raw:
            parameters = json.loads(raw)
    if not parameters:
        raise RuntimeError("run57 stored parameters unavailable")
    parameters["enable_tc_big_numeric_row_rescue"] = True
    parameters["tc_big_numeric_row_rescue_contract"] = TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT
    parameters["tc_big_numeric_row_selector_contract"] = SELECTOR_CONTRACT
    parameters["tc_big_numeric_row_trigger_contract"] = TRIGGER_CONTRACT
    return parameters


def _assert_diff_and_provenance(
    base_rows: list[dict[str, Any]], final_rows: list[dict[str, Any]]
) -> tuple[list[int], list[dict[str, Any]]]:
    if len(base_rows) != len(final_rows):
        raise RuntimeError("numeric-row promotion changed segment cardinality")
    changed: list[int] = []
    cases: list[dict[str, Any]] = []
    for base, final in zip(_ordered(base_rows), _ordered(final_rows), strict=True):
        sequence = int(base["sequence_number"])
        if int(final["sequence_number"]) != sequence:
            raise RuntimeError(f"sequence drift at {sequence}")
        for key in ("source_start", "source_end", "source_text"):
            if final.get(key) != base.get(key):
                raise RuntimeError(f"source identity drift at {sequence} {key}")
        base_target = str(base.get("target_text") or "")
        target = str(final.get("target_text") or "")
        if target == base_target:
            continue
        changed.append(sequence)
        if sequence not in EXPECTED_VARIANTS:
            raise RuntimeError(f"unexpected target change at {sequence}")
        if int(final["source_start"]) != EXPECTED_SOURCE_STARTS[sequence]:
            raise RuntimeError(f"source-start drift at {sequence}")
        payload = dict(final.get("payload") or {})
        rescue = dict(payload.get("tc_big_numeric_row_rescue") or {})
        if rescue.get("applied") is not True:
            raise RuntimeError(f"missing numeric-row rescue provenance at {sequence}")
        if rescue.get("contract") != TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT:
            raise RuntimeError(f"rescue contract drift at {sequence}")
        if rescue.get("selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError(f"selector contract drift at {sequence}")
        if rescue.get("trigger_contract") != TRIGGER_CONTRACT:
            raise RuntimeError(f"trigger contract drift at {sequence}")
        if rescue.get("variant") != EXPECTED_VARIANTS[sequence]:
            raise RuntimeError(f"variant drift at {sequence}: {rescue.get('variant')!r}")
        source = str(final.get("source_text") or "")
        if rescue.get("model_input") != source or rescue.get("model_input_equals_source") is not True:
            raise RuntimeError(f"model-input identity drift at {sequence}")
        if rescue.get("raw_model_selected") is not True or int(rescue.get("raw_model_rank", -1)) != 0:
            raise RuntimeError(f"rank0 provenance drift at {sequence}")
        hypotheses = list(payload.get("hypotheses") or [])
        if len(hypotheses) != 1:
            raise RuntimeError(f"hypothesis cardinality drift at {sequence}")
        hypothesis = dict(hypotheses[0])
        if int(hypothesis.get("rank", -1)) != 0 or str(hypothesis.get("text") or "") != target:
            raise RuntimeError(f"persisted hypothesis drift at {sequence}")
        trigger = dict(rescue.get("trigger") or {})
        selection = dict(rescue.get("selection") or {})
        if trigger.get("eligible") is not True or selection.get("accepted") is not True:
            raise RuntimeError(f"trigger/selector acceptance drift at {sequence}")
        if selection.get("variant_notation_preserved") is not True:
            raise RuntimeError(f"variant notation was not preserved at {sequence}")
        if str(rescue.get("base_target") or "") != base_target:
            raise RuntimeError(f"base-target provenance drift at {sequence}")
        runtime_identity = dict(rescue.get("runtime_identity") or {})
        if runtime_identity.get("revision") != "708be1d372fe4c358a352f404e6dc9ca0126ba48":
            raise RuntimeError(f"TC-big revision drift at {sequence}")
        if runtime_identity.get("model_safetensors_sha256") != "e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416":
            raise RuntimeError(f"TC-big weights drift at {sequence}")
        for flag in UNSAFE_FLAGS:
            if rescue.get(flag) is not False:
                raise RuntimeError(f"unsafe flag {flag} at {sequence}")
        cases.append(
            {
                "sequence_number": sequence,
                "source_start": int(final["source_start"]),
                "source_end": int(final["source_end"]),
                "variant": rescue["variant"],
                "base_target": base_target,
                "promoted_target": target,
                "raw_rank": 0,
                "model_input_equals_source": True,
                "runtime_identity": runtime_identity,
                "trigger": trigger,
                "selection": selection,
            }
        )
    expected = sorted(EXPECTED_VARIANTS)
    if changed != expected:
        raise RuntimeError(f"target-change cohort drift: {changed} != {expected}")
    return changed, cases


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_ROW_PROMOTION_ROOT",
            "work/full-opticks-tc-big-numeric-row-promotion",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(
        os.environ.get("ROCKETDICT_NUMERIC_ROW_PROMOTION_DB", root / "rocketdict.sqlite")
    ).resolve()
    if not database.is_file() or _sha(database) != BASE_DB_SHA256:
        raise RuntimeError("promotion requires exact authenticated run57 SQLite")

    base_run, base_rows, document, content = _load_base(database)
    context_run_id = int(dict(base_run.get("output") or {})["context_run_id"])
    base_target_sha = _target_sha(base_rows)
    promoted_output = run_product_stage12(
        database,
        context_run_id=context_run_id,
        parameters=_parameters(base_run),
        implementation="opus-en-ru-ct2",
    )
    promoted_run_id = int(promoted_output["translation_run_id"])
    if promoted_run_id == BASE_TRANSLATION_RUN_ID:
        raise RuntimeError("numeric-row wrapper did not create a promotion run")
    if int(promoted_output.get("base_translation_run_id") or 0) != BASE_TRANSLATION_RUN_ID:
        raise RuntimeError("numeric-row wrapper did not cache-resolve exact run57")
    if str(promoted_output.get("base_translation_output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("numeric-row base output SHA drift")
    if int(promoted_output.get("tc_big_numeric_row_rescue_attempt_count") or -1) != 3:
        raise RuntimeError("numeric-row attempt count drift")
    if int(promoted_output.get("tc_big_numeric_row_rescue_accepted_count") or -1) != 3:
        raise RuntimeError("numeric-row accepted count drift")
    if int(promoted_output.get("tc_big_numeric_row_rescue_rejected_count") or -1) != 0:
        raise RuntimeError("numeric-row unexpected rejection")
    if list(promoted_output.get("tc_big_numeric_row_rescue_selected_ranks") or []) != [0, 0, 0]:
        raise RuntimeError("numeric-row selected-rank drift")

    with connect(database, readonly=True) as connection:
        promoted_run = get_run(connection, promoted_run_id)
        final_rows = _ordered(get_run_items(connection, promoted_run_id, kind="translation_segment"))
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    if promoted_run.get("status") != "completed":
        raise RuntimeError("promoted run is not completed")
    if integrity != "ok" or fk_count != 0:
        raise RuntimeError(f"promoted SQLite integrity drift: {integrity=} {fk_count=}")
    if len(final_rows) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError(f"promoted segment-count drift: {len(final_rows)}")
    _coverage(final_rows, content, label="promoted")
    changed, cases = _assert_diff_and_provenance(base_rows, final_rows)
    final_counts, residuals = _hard_counts(final_rows)
    if final_counts != EXPECTED_COUNTS:
        raise RuntimeError(f"numeric-row promotion hard-count drift: {final_counts}")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-Opticks promotion of three source-defined exact-row TC-big rank0 numeric rescue variants over exact run57",
        "base_translation_run_id": BASE_TRANSLATION_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_translation_parameters_sha256": BASE_PARAMETERS_SHA256,
        "base_database_sha256": BASE_DB_SHA256,
        "base_target_sha256": base_target_sha,
        "base_hard_counts": BASE_COUNTS,
        "source_text_sha256": str(document["text_sha256"]),
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": str(promoted_run.get("output_sha256") or ""),
        "promoted_database_sha256": _sha(database),
        "promoted_target_sha256": _target_sha(final_rows),
        "promoted_hard_counts": final_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed,
        "unchanged_target_count": EXPECTED_SEGMENT_COUNT - len(changed),
        "promotion_cases": cases,
        "residual_sequences": [int(item["sequence_number"]) for item in residuals],
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violation_count": fk_count,
        "base_cache_identity_exact": True,
        "source_coverage_byte_exact": True,
        "unrelated_targets_byte_exact": True,
        "model_input_equals_immutable_source": True,
        "raw_rank0_only": True,
        "historical_shadow_workflow_run_id": 34451550027,
        "historical_shadow_artifact_id": 10142342824,
        "historical_shadow_evidence_sha256": "2cbd880285fe4675708781d045a6d3323d5a7666e6682897be1d75635e4d0487",
        **{flag: False for flag in UNSAFE_FLAGS},
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "numeric-row-promotion-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "promoted_translation_run_id": promoted_run_id,
        "promoted_translation_output_sha256": evidence["promoted_translation_output_sha256"],
        "promoted_database_sha256": evidence["promoted_database_sha256"],
        "promoted_target_sha256": evidence["promoted_target_sha256"],
        "promoted_hard_counts": final_counts,
        "promoted_segment_count": len(final_rows),
        "changed_target_sequences": changed,
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
