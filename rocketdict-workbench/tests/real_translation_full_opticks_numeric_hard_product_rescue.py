from __future__ import annotations

"""Persist and audit the opt-in numeric-hard whole-context rescue on composed Opticks.

The immutable full-Opticks database after the proven opt-in length + citation
composition is reused.  The new numeric-hard wrapper must cache-hit that exact
base run, attempt only current split contexts that already fail the maintained
numeric/symbol gate, persist only raw rank-0 whole-context OPUS candidates, and
veto any mechanically clean candidate that drops Gutenberg emphasis markup.

This is research/promotion evidence only.  The new mechanism remains disabled
by default and this harness calls its stage wrapper directly until its persisted
full-corpus evidence is accepted for the public Stage12 surface.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import EMPHASIS_MARKUP_CONTRACT
from rocketdict.translation_numeric_hard_rescue_stage import (
    NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT,
    NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE,
    NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT,
    run_stage12 as run_numeric_hard_stage12,
)
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_rescue_stage import MAX_WHOLE_CONTEXT_NLP_TOKENS
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-numeric-hard-product-rescue-optin/1"
COMBINED_SCHEMA = "rocketdict-full-opticks-combined-length-citation-product-rescue-optin/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
COMBINED_JSON_SHA256 = "71aedf2f55434d770d524cff2977df80efb5cd82e66421e01b22b43ad47b34c9"
COMBINED_DATABASE_SHA256 = "afc9eba1177e1ada86ae208d3f175cc34f84cd287145b236f4dad79fd73f7f67"
EXPECTED_BASE_RUN_ID = 7
EXPECTED_ATTEMPTED_CONTEXTS = [550, 669, 1024, 1460, 2132, 2176, 2190, 2238, 2634, 2725]
EXPECTED_ACCEPTED_CONTEXTS = [550, 669, 1024, 2238]
EXPECTED_EMPHASIS_REJECTED_CONTEXTS = [2725]
EXPECTED_BASE_GATES = {"numeric_symbol": 29, "punctuation": 34, "length": 0}
EXPECTED_ENABLED_GATES = {"numeric_symbol": 25, "punctuation": 33, "length": 0}
EXPECTED_BASE_UNIQUE_FAILURES = 59
EXPECTED_ENABLED_UNIQUE_FAILURES = 55
EXPECTED_BASE_SEGMENTS = 3348
EXPECTED_ENABLED_SEGMENTS = 3343


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


def _ordered(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda row: int(row["sequence_number"]))


def _assert_source_coverage(
    items: list[dict[str, Any]], content: str, *, label: str
) -> None:
    cursor = 0
    for expected_sequence, row in enumerate(_ordered(items)):
        if int(row["sequence_number"]) != expected_sequence:
            raise RuntimeError(f"{label} sequence numbering drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"{label} source coverage is not byte-exact")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} does not cover complete immutable source")


def _hard_gate_inventory(items: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(items):
        sequence = int(row["sequence_number"])
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        if (verdict.get("numeric_symbol") or {}).get("passed") is not True:
            failures["numeric_symbol"].append(sequence)
            union.add(sequence)
        if verdict.get("punctuation_passed") is not True:
            failures["punctuation"].append(sequence)
            union.add(sequence)
        if verdict.get("length_passed") is not True:
            failures["length"].append(sequence)
            union.add(sequence)
    return {
        **failures,
        "counts": {key: len(value) for key, value in failures.items()},
        "unique_failure_count": len(union),
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_HARD_PRODUCT_ROOT",
            "work/numeric-hard-product-rescue",
        )
    ).resolve()
    combined_path = root / "full-opticks-combined-length-citation-product-rescue-optin.json"
    database = root / "rocketdict.sqlite"
    if not combined_path.is_file() or not database.is_file():
        raise RuntimeError("Numeric-hard Product rescue requires composed JSON and DB")
    if _sha(combined_path) != COMBINED_JSON_SHA256:
        raise RuntimeError("Composed rescue JSON identity drift")
    if _sha(database) != COMBINED_DATABASE_SHA256:
        raise RuntimeError("Composed rescue database identity drift before execution")

    combined = json.loads(combined_path.read_text(encoding="utf-8"))
    if combined.get("schema") != COMBINED_SCHEMA:
        raise RuntimeError("Composed rescue schema drift")
    if combined.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")
    if combined.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Numeric-hard audit requires planner-v8 composed base")
    if int(combined["enabled_translation_run_id"]) != EXPECTED_BASE_RUN_ID:
        raise RuntimeError("Unexpected composed Stage12 run identity")
    if dict(combined["enabled_hard_gate_counts"]) != EXPECTED_BASE_GATES:
        raise RuntimeError("Composed hard-gate count drift")
    if int(combined["enabled_unique_hard_failure_count"]) != EXPECTED_BASE_UNIQUE_FAILURES:
        raise RuntimeError("Composed unique hard-failure count drift")
    if int(combined["enabled_segment_count"]) != EXPECTED_BASE_SEGMENTS:
        raise RuntimeError("Composed segment count drift")

    database_sha_before = _sha(database)
    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, EXPECTED_BASE_RUN_ID)
        base_items = get_run_items(
            connection, EXPECTED_BASE_RUN_ID, kind="translation_segment"
        )
        base_output = dict(base_run.get("output") or {})
        base_parameters = dict(base_run.get("parameters") or {})
        document_version_id = int(base_output["document_version_id"])
        document = get_document(connection, document_version_id)
    content = str(document["content_text"])
    _assert_source_coverage(base_items, content, label="composed base Stage12")
    if str(base_run.get("output_sha256") or "") != str(
        combined["enabled_translation_output_sha256"]
    ):
        raise RuntimeError("Composed Stage12 output identity drift")
    base_gates = _hard_gate_inventory(base_items)
    if base_gates["counts"] != EXPECTED_BASE_GATES:
        raise RuntimeError(f"Composed base gate recomputation drift: {base_gates['counts']!r}")
    if base_gates["unique_failure_count"] != EXPECTED_BASE_UNIQUE_FAILURES:
        raise RuntimeError("Composed base unique gate recomputation drift")

    context_run_id = int(base_output["context_run_id"])
    enabled_parameters = dict(base_parameters)
    enabled_parameters.update(
        {
            "enable_numeric_hard_failure_whole_context_rescue": True,
            "numeric_hard_failure_whole_context_rescue_contract": (
                NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
            ),
            "numeric_hard_failure_whole_context_rescue_selector_contract": (
                NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
            ),
            "numeric_hard_failure_whole_context_rescue_phase": (
                NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTED_PHASE
            ),
            "numeric_hard_failure_whole_context_rescue_max_nlp_tokens": (
                MAX_WHOLE_CONTEXT_NLP_TOKENS
            ),
        }
    )
    enabled = run_numeric_hard_stage12(
        database,
        context_run_id=context_run_id,
        parameters=enabled_parameters,
        implementation="opus-en-ru-ct2",
    )
    enabled_run_id = int(enabled["translation_run_id"])
    if enabled_run_id == EXPECTED_BASE_RUN_ID:
        raise RuntimeError("Numeric-hard rescue did not create a distinct Stage12 run")
    if int(enabled.get("base_translation_run_id") or 0) != EXPECTED_BASE_RUN_ID:
        raise RuntimeError("Numeric-hard wrapper did not compose over exact run7 base")
    if str(enabled.get("base_translation_output_sha256") or "") != str(
        combined["enabled_translation_output_sha256"]
    ):
        raise RuntimeError("Numeric-hard wrapper base output SHA drift")
    if enabled.get("numeric_hard_failure_whole_context_rescue_enabled") is not True:
        raise RuntimeError("Numeric-hard rescue was not enabled")
    if enabled.get("numeric_hard_failure_whole_context_rescue_contract") != (
        NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
    ):
        raise RuntimeError("Numeric-hard rescue contract drift")
    if enabled.get("numeric_hard_failure_whole_context_rescue_selector_contract") != (
        NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
    ):
        raise RuntimeError("Numeric-hard selector contract drift")
    if enabled.get("numeric_hard_failure_whole_context_rescue_emphasis_markup_contract") != (
        EMPHASIS_MARKUP_CONTRACT
    ):
        raise RuntimeError("Numeric-hard emphasis-markup contract drift")

    attempted = [
        int(value)
        for value in enabled.get(
            "numeric_hard_failure_whole_context_rescue_attempted_context_sequences", []
        )
    ]
    accepted = [
        int(value)
        for value in enabled.get(
            "numeric_hard_failure_whole_context_rescue_accepted_context_sequences", []
        )
    ]
    rejected = [
        int(value)
        for value in enabled.get(
            "numeric_hard_failure_whole_context_rescue_rejected_context_sequences", []
        )
    ]
    emphasis_rejected = [
        int(value)
        for value in enabled.get(
            "numeric_hard_failure_whole_context_rescue_emphasis_rejected_context_sequences", []
        )
    ]
    if attempted != EXPECTED_ATTEMPTED_CONTEXTS:
        raise RuntimeError(f"Numeric-hard attempted cohort drift: {attempted!r}")
    if accepted != EXPECTED_ACCEPTED_CONTEXTS:
        raise RuntimeError(f"Numeric-hard accepted cohort drift: {accepted!r}")
    if emphasis_rejected != EXPECTED_EMPHASIS_REJECTED_CONTEXTS:
        raise RuntimeError(f"Numeric-hard emphasis-veto drift: {emphasis_rejected!r}")
    if sorted(accepted + rejected) != attempted:
        raise RuntimeError("Numeric-hard attempted cohort is not accepted/rejected partition")
    if int(enabled.get("numeric_hard_failure_whole_context_rescue_skipped_over_cap_context_count") or 0) != 0:
        raise RuntimeError("Unexpected numeric-hard residual context above token cap")

    with connect(database, readonly=True) as connection:
        persisted_run = get_run(connection, enabled_run_id)
        enabled_items = get_run_items(
            connection, enabled_run_id, kind="translation_segment"
        )
    if str(persisted_run.get("output_sha256") or "") != str(
        enabled.get("translation_output_sha256")
        or persisted_run.get("output_sha256")
        or ""
    ):
        # The public stage output schema does not require a duplicated output SHA;
        # this branch simply protects against a contradictory value if one exists.
        if enabled.get("translation_output_sha256") is not None:
            raise RuntimeError("Persisted numeric-hard output SHA contradicts return payload")

    _assert_source_coverage(enabled_items, content, label="numeric-hard Stage12")
    if len(enabled_items) != EXPECTED_ENABLED_SEGMENTS:
        raise RuntimeError(
            f"Numeric-hard segment count drift: {len(enabled_items)} != {EXPECTED_ENABLED_SEGMENTS}"
        )

    base_by_id = {int(row["id"]): row for row in base_items}
    base_by_span = {
        (int(row["source_start"]), int(row["source_end"])): row for row in base_items
    }
    copied_count = 0
    applied_rows: list[dict[str, Any]] = []
    applied_contexts: list[int] = []
    for row in enabled_items:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("numeric_hard_failure_whole_context_rescue") or {})
        if rescue.get("contract") != NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT:
            raise RuntimeError("Selected row lacks numeric-hard rescue provenance")
        if rescue.get("selector_contract") != (
            NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
        ):
            raise RuntimeError("Selected row lacks numeric-hard selector provenance")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"Numeric-hard row violates {flag}=False")

        if rescue.get("applied") is True:
            context = int(rescue["context_sequence"])
            applied_contexts.append(context)
            hypotheses = list(payload.get("hypotheses") or [])
            if not hypotheses:
                raise RuntimeError("Applied numeric-hard row lacks raw hypotheses")
            raw_rank0 = str((hypotheses[0] or {}).get("text") or "")
            if str(row.get("target_text") or "") != raw_rank0:
                raise RuntimeError("Applied numeric-hard target is not exact raw rank0")
            if rescue.get("raw_model_rank0") is not True:
                raise RuntimeError("Applied numeric-hard row lost raw-rank0 provenance")
            if rescue.get("trigger") != "primary_numeric_symbol_hard_failure":
                raise RuntimeError("Applied numeric-hard row lost hard-failure trigger")
            if rescue.get("emphasis_markup_preserved") is not True:
                raise RuntimeError("Applied numeric-hard row failed emphasis preservation")
            emphasis = dict(rescue.get("emphasis_markup") or {})
            if emphasis.get("contract") != EMPHASIS_MARKUP_CONTRACT:
                raise RuntimeError("Applied row lacks versioned emphasis evidence")
            if emphasis.get("passed") is not True:
                raise RuntimeError("Applied row persisted rejected emphasis evidence")
            candidate_verdict = dict(rescue.get("candidate_verdict") or {})
            if candidate_verdict.get("strictly_eligible") is not True:
                raise RuntimeError("Applied row is not strict-selector clean")
            spans = [tuple(int(value) for value in span) for span in rescue.get("primary_source_spans") or []]
            if len(spans) < 2:
                raise RuntimeError("Applied numeric-hard row lacks split-primary lineage")
            primary_rows = []
            for span in spans:
                base = base_by_span.get(span)
                if base is None:
                    raise RuntimeError(f"Applied row references unknown base span {span!r}")
                primary_rows.append(base)
            primary_rows.sort(key=lambda item: int(item["source_start"]))
            if "".join(str(item.get("source_text") or "") for item in primary_rows) != str(
                row.get("source_text") or ""
            ):
                raise RuntimeError("Applied row source is not exact concatenated base source")
            applied_rows.append(row)
            continue

        if rescue.get("applied") is not False:
            raise RuntimeError("Numeric-hard rescue applied state is ambiguous")
        base_id = int(rescue.get("base_translation_segment_id") or 0)
        base = base_by_id.get(base_id)
        if base is None:
            raise RuntimeError("Copied numeric-hard row references unknown base segment")
        for field in ("source_start", "source_end", "source_text", "target_text"):
            if row.get(field) != base.get(field):
                raise RuntimeError(f"Untouched numeric-hard row changed base {field}")
        copied_count += 1

    if sorted(applied_contexts) != EXPECTED_ACCEPTED_CONTEXTS:
        raise RuntimeError(f"Persisted applied context drift: {sorted(applied_contexts)!r}")

    enabled_gates = _hard_gate_inventory(enabled_items)
    if enabled_gates["counts"] != EXPECTED_ENABLED_GATES:
        raise RuntimeError(
            f"Numeric-hard enabled gate inventory drift: {enabled_gates['counts']!r}"
        )
    if enabled_gates["unique_failure_count"] != EXPECTED_ENABLED_UNIQUE_FAILURES:
        raise RuntimeError(
            "Numeric-hard enabled unique hard-failure inventory drift: "
            f"{enabled_gates['unique_failure_count']}"
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "persisted research opt-in numeric-hard split-context whole-context rescue "
            "over exact composed length+citation full-Opticks Stage12 base"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "document_version_id": document_version_id,
        "source_char_count": len(content),
        "planner_contract": PLANNER_CONTRACT,
        "base_translation_run_id": EXPECTED_BASE_RUN_ID,
        "base_translation_output_sha256": str(base_run.get("output_sha256") or ""),
        "enabled_translation_run_id": enabled_run_id,
        "enabled_translation_output_sha256": str(persisted_run.get("output_sha256") or ""),
        "numeric_hard_failure_whole_context_rescue_contract": (
            NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_RESCUE_CONTRACT
        ),
        "numeric_hard_failure_whole_context_selector_contract": (
            NUMERIC_HARD_FAILURE_WHOLE_CONTEXT_SELECTOR_CONTRACT
        ),
        "emphasis_markup_contract": EMPHASIS_MARKUP_CONTRACT,
        "attempted_context_sequences": attempted,
        "accepted_context_sequences": accepted,
        "rejected_context_sequences": rejected,
        "emphasis_rejected_context_sequences": emphasis_rejected,
        "base_hard_gate_counts": base_gates["counts"],
        "enabled_hard_gate_counts": enabled_gates["counts"],
        "base_unique_hard_failure_count": base_gates["unique_failure_count"],
        "enabled_unique_hard_failure_count": enabled_gates["unique_failure_count"],
        "base_segment_count": len(base_items),
        "enabled_segment_count": len(enabled_items),
        "copied_base_row_count": copied_count,
        "applied_context_count": len(applied_rows),
        "source_coverage_byte_exact": True,
        "untouched_rows_base_exact": True,
        "applied_targets_exact_raw_rank0": True,
        "base_stage_cache_reused": int(enabled.get("base_translation_run_id") or 0)
        == EXPECTED_BASE_RUN_ID,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_sha256_before": database_sha_before,
    }
    payload["database_sha256_after"] = _sha(database)
    payload["evidence_sha256"] = _canonical_sha(payload)

    output = root / "full-opticks-numeric-hard-product-rescue-optin.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "base_translation_run_id": EXPECTED_BASE_RUN_ID,
                "enabled_translation_run_id": enabled_run_id,
                "attempted_context_sequences": attempted,
                "accepted_context_sequences": accepted,
                "emphasis_rejected_context_sequences": emphasis_rejected,
                "base_hard_gate_counts": base_gates["counts"],
                "enabled_hard_gate_counts": enabled_gates["counts"],
                "enabled_unique_hard_failure_count": enabled_gates[
                    "unique_failure_count"
                ],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
