from __future__ import annotations

"""Persist and audit the bounded whole-context Stage12 rescue on full Opticks.

This closes the gap between the read-only whole-context feasibility experiment
and the public Product Stage12 orchestration.  Starting from the canonical
full-Opticks Product baseline, it enables only the whole-context research flag,
requires immutable primary-run reuse, audits byte-exact source ownership and raw
rank-0 provenance, and recomputes hard numeric failures from persisted selected
rows.

Promotion is deliberately not performed here.  This harness produces the
corpus-level evidence required before the registry/Product default may change.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.numeric_integrity import extract_numeric_literals
from rocketdict.translation_rescue import SELECTOR_CONTRACT
from rocketdict.translation_rescue_stage import (
    MAX_WHOLE_CONTEXT_NLP_TOKENS,
    WHOLE_CONTEXT_RESCUE_CONTRACT,
)
from rocketdict.translation_stage import PLANNER_CONTRACT
from rocketdict_workbench.core import RocketDictCore

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-whole-context-product-rescue-optin/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
KNOWN_ACCEPTED_SEQUENCE = 669
KNOWN_REJECTED_SEQUENCE = 2132
KNOWN_LITERALS = ("25", "30", "40")


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _call(core: RocketDictCore, database: Path, operation: str, **params: Any) -> dict[str, Any]:
    return dict(
        core.api(
            database,
            "call",
            operation,
            "--params",
            json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            timeout=7200,
        )
    )


def _ordered(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda row: int(row["sequence_number"]))


def _assert_source_coverage(items: list[dict[str, Any]], content: str, *, label: str) -> None:
    cursor = 0
    for expected_sequence, row in enumerate(_ordered(items)):
        sequence = int(row["sequence_number"])
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if sequence != expected_sequence:
            raise RuntimeError(f"{label} sequence numbering drift")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"{label} source coverage is not byte-exact")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"{label} does not cover the complete immutable source")


def _numeric_failures(
    items: list[dict[str, Any]],
    *,
    punctuation_parameters: dict[str, Any],
    length_parameters: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in _ordered(items):
        source = str(row.get("source_text") or "")
        if not extract_numeric_literals(source):
            continue
        target = str(row.get("target_text") or "")
        verdict = _verdict(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "target_text": None,
            },
            target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        if (verdict.get("numeric_symbol") or {}).get("passed") is False:
            failures.append(
                {
                    "sequence_number": int(row["sequence_number"]),
                    "source_start": int(row["source_start"]),
                    "source_end": int(row["source_end"]),
                    "source_text": source,
                    "target_text": target,
                    "verdict": verdict,
                }
            )
    return failures


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Full Opticks baseline Product evidence is missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise RuntimeError(f"Unexpected full Opticks baseline schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")
    if baseline.get("actual_product_stage12_execution") is not True:
        raise RuntimeError("Whole-context Product audit requires actual persisted Product Stage12")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Whole-context Product audit requires planner-v8 primary")

    params12 = dict(baseline.get("stage12_parameters") or {})
    if params12.get("enable_selective_resegmentation_rescue") is not False:
        raise RuntimeError("Canonical Product baseline must keep legacy selective rescue disabled")

    baseline_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    document_version_id = int(baseline["document_version_id"])
    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})

    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        baseline_run = get_run(connection, baseline_run_id)
        baseline_items = get_run_items(
            connection, baseline_run_id, kind="translation_segment"
        )
    content = str(document["content_text"])
    baseline_output = dict(baseline_run.get("output") or {})
    if baseline_output.get("whole_context_rescue_enabled") is not False:
        raise RuntimeError("Canonical Product baseline unexpectedly enabled whole-context rescue")
    if int(baseline_output.get("whole_context_rescue_attempted_context_count") or 0) != 0:
        raise RuntimeError("Disabled Product baseline unexpectedly attempted whole-context rescue")
    primary_run_id = int(baseline_output.get("primary_translation_run_id") or 0)
    primary_output_sha = str(baseline_output.get("primary_translation_output_sha256") or "")
    if primary_run_id <= 0 or not primary_output_sha:
        raise RuntimeError("Canonical Product baseline lacks immutable primary lineage")
    _assert_source_coverage(baseline_items, content, label="baseline selected Stage12")

    enabled_parameters = dict(params12)
    enabled_parameters.update(
        {
            "enable_whole_context_rescue": True,
            "whole_context_rescue_contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
            "whole_context_rescue_selector_contract": SELECTOR_CONTRACT,
            "whole_context_rescue_max_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        }
    )
    enabled = _call(
        RocketDictCore(),
        database,
        "product.stage12.run",
        context_run_id=context_run_id,
        parameters=enabled_parameters,
        implementation="opus-en-ru-ct2",
    )
    enabled_run_id = int(enabled["translation_run_id"])
    if enabled_run_id == baseline_run_id:
        raise RuntimeError("Whole-context opt-in incorrectly reused disabled wrapper identity")
    if enabled.get("whole_context_rescue_enabled") is not True:
        raise RuntimeError("Public Product Stage12 did not enable whole-context rescue")
    if enabled.get("selective_resegmentation_enabled") is not False:
        raise RuntimeError("Whole-context audit unexpectedly enabled legacy semicolon rescue")
    if int(enabled.get("primary_translation_run_id") or 0) != primary_run_id:
        raise RuntimeError("Whole-context opt-in changed immutable primary Stage12 identity")
    if str(enabled.get("primary_translation_output_sha256") or "") != primary_output_sha:
        raise RuntimeError("Whole-context opt-in changed immutable primary Stage12 output")
    if enabled.get("primary_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Whole-context opt-in escaped maintained planner-v8 primary")

    attempted = [int(value) for value in enabled.get("whole_context_rescue_attempted_context_sequences", [])]
    accepted = [int(value) for value in enabled.get("whole_context_rescue_accepted_context_sequences", [])]
    rejected = [int(value) for value in enabled.get("whole_context_rescue_rejected_context_sequences", [])]
    skipped = [int(value) for value in enabled.get("whole_context_rescue_skipped_over_cap_context_sequences", [])]
    if attempted != [KNOWN_ACCEPTED_SEQUENCE, KNOWN_REJECTED_SEQUENCE]:
        raise RuntimeError(f"Pinned whole-context eligibility drift: {attempted!r}")
    if accepted != [KNOWN_ACCEPTED_SEQUENCE]:
        raise RuntimeError(f"Pinned whole-context acceptance drift: {accepted!r}")
    if rejected != [KNOWN_REJECTED_SEQUENCE]:
        raise RuntimeError(f"Pinned whole-context rejection drift: {rejected!r}")
    if skipped:
        raise RuntimeError(f"Pinned eligible contexts unexpectedly exceeded cap: {skipped!r}")
    if enabled.get("rescue_selected_strategy_by_context") != {
        str(KNOWN_ACCEPTED_SEQUENCE): "whole_context"
    }:
        raise RuntimeError("Selected rescue strategy provenance drift")

    with connect(database, readonly=True) as connection:
        enabled_run = get_run(connection, enabled_run_id)
        enabled_items = get_run_items(connection, enabled_run_id, kind="translation_segment")
        primary_run = get_run(connection, primary_run_id)
        primary_items = get_run_items(connection, primary_run_id, kind="translation_segment")
    _assert_source_coverage(primary_items, content, label="immutable primary Stage12")
    _assert_source_coverage(enabled_items, content, label="whole-context selected Stage12")
    if str(primary_run.get("output_sha256") or "") != primary_output_sha:
        raise RuntimeError("Primary Stage12 output SHA changed after whole-context execution")

    primary_by_id = {int(row["id"]): row for row in primary_items}
    applied_rows: list[dict[str, Any]] = []
    copied_primary_count = 0
    for row in enabled_items:
        payload = dict(row.get("payload") or {})
        whole = dict(payload.get("whole_context_rescue") or {})
        if whole.get("contract") != WHOLE_CONTEXT_RESCUE_CONTRACT:
            raise RuntimeError("Selected row lacks whole-context contract provenance")
        if whole.get("selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError("Selected row lacks whole-context selector provenance")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
        ):
            if whole.get(flag) is not False:
                raise RuntimeError(f"Selected row violates {flag}=False invariant")

        if whole.get("applied") is True:
            applied_rows.append(row)
            if int(whole.get("context_sequence") or -1) != KNOWN_ACCEPTED_SEQUENCE:
                raise RuntimeError("Unexpected context received whole-context rescue")
            hypotheses = list(payload.get("hypotheses") or [])
            if not hypotheses:
                raise RuntimeError("Applied whole-context row lacks raw hypotheses")
            raw_rank0 = str((hypotheses[0] or {}).get("text") or "")
            if str(row.get("target_text") or "") != raw_rank0:
                raise RuntimeError("Applied whole-context target is not exact raw rank-0 OPUS")
            if whole.get("raw_model_rank0") is not True:
                raise RuntimeError("Applied whole-context row is not marked raw_model_rank0")
            if ((payload.get("planner") or {}).get("rescue_strategy")) != "whole_context":
                raise RuntimeError("Applied whole-context row lost planner strategy provenance")
            continue

        if whole.get("applied") is not False:
            raise RuntimeError("Selected row has ambiguous whole-context applied state")
        primary_id = int(whole.get("primary_translation_segment_id") or 0)
        primary = primary_by_id.get(primary_id)
        if primary is None:
            raise RuntimeError("Copied selected row references unknown primary segment")
        for field in ("source_start", "source_end", "source_text", "target_text"):
            if row.get(field) != primary.get(field):
                raise RuntimeError(f"Non-rescued selected row changed primary {field}")
        copied_primary_count += 1

    if len(applied_rows) != 1:
        raise RuntimeError(f"Expected one whole-context selected row, got {len(applied_rows)}")
    applied = applied_rows[0]
    if any(literal not in str(applied.get("target_text") or "") for literal in KNOWN_LITERALS):
        raise RuntimeError("Known long-unit whole-context Product target lost 25/30/40")

    baseline_failures = _numeric_failures(
        baseline_items,
        punctuation_parameters=punctuation_parameters,
        length_parameters=length_parameters,
    )
    enabled_failures = _numeric_failures(
        enabled_items,
        punctuation_parameters=punctuation_parameters,
        length_parameters=length_parameters,
    )
    baseline_failure_count = len(baseline_failures)
    enabled_failure_count = len(enabled_failures)
    if baseline_failure_count != int(baseline.get("product_numeric_failure_count") or -1):
        raise RuntimeError("Recomputed baseline hard numeric failure count drift")
    if enabled_failure_count != baseline_failure_count - 1:
        raise RuntimeError(
            "Bounded whole-context rescue must remove exactly the known long-unit numeric failure"
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "actual public Product Stage12 bounded whole-context rescue over canonical full Opticks",
        "promotion_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "source_char_count": len(content),
        "document_version_id": document_version_id,
        "planner_contract": PLANNER_CONTRACT,
        "whole_context_rescue_contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        "baseline_selected_translation_run_id": baseline_run_id,
        "enabled_selected_translation_run_id": enabled_run_id,
        "primary_translation_run_id": primary_run_id,
        "primary_output_sha256": primary_output_sha,
        "primary_identity_reused": True,
        "attempted_context_sequences": attempted,
        "accepted_context_sequences": accepted,
        "rejected_context_sequences": rejected,
        "skipped_over_cap_context_sequences": skipped,
        "baseline_hard_numeric_failure_count": baseline_failure_count,
        "enabled_hard_numeric_failure_count": enabled_failure_count,
        "hard_numeric_failure_delta": enabled_failure_count - baseline_failure_count,
        "primary_segment_count": len(primary_items),
        "enabled_segment_count": len(enabled_items),
        "copied_primary_row_count": copied_primary_count,
        "applied_whole_context_row_count": len(applied_rows),
        "source_coverage_byte_exact": True,
        "non_rescued_rows_primary_exact": True,
        "applied_targets_exact_raw_rank0": True,
        "known_long_content_loss_literals_preserved": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "accepted_context": {
            "context_sequence": KNOWN_ACCEPTED_SEQUENCE,
            "source_start": int(applied["source_start"]),
            "source_end": int(applied["source_end"]),
            "source_text": str(applied.get("source_text") or ""),
            "target_text": str(applied.get("target_text") or ""),
        },
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-whole-context-product-rescue-optin.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "baseline_selected_translation_run_id": baseline_run_id,
                "enabled_selected_translation_run_id": enabled_run_id,
                "primary_translation_run_id": primary_run_id,
                "baseline_hard_numeric_failure_count": baseline_failure_count,
                "enabled_hard_numeric_failure_count": enabled_failure_count,
                "attempted_context_sequences": attempted,
                "accepted_context_sequences": accepted,
                "rejected_context_sequences": rejected,
                "applied_whole_context_row_count": len(applied_rows),
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
