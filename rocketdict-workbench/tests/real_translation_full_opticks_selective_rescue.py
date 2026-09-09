from __future__ import annotations

"""Execute and audit the opt-in Product Stage12 selective rescue on full Opticks.

The canonical full-Opticks numeric stress first materializes the default,
fail-closed Product Stage12 selection run and its immutable planner-v8 primary
run.  This script then calls the *public* Product Stage12 API a second time with
only the research rescue switch enabled.  The wrapper must reuse exactly the
same primary run/output identity, may replace only complete mechanically
accepted ordinary TXT contexts, and must persist exact raw rank-0 OPUS targets.

This is research evidence, not promotion: mechanical hard-gate improvement is
reported together with complete accepted contexts for semantic review while the
registry default remains disabled.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.numeric_integrity import extract_numeric_literals
from rocketdict.translation_rescue import RESCUE_CONTRACT, SELECTOR_CONTRACT
from rocketdict.translation_stage import PLANNER_CONTRACT
from rocketdict_workbench.core import RocketDictCore

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-selective-rescue-optin/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"


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
        raise RuntimeError("Selective rescue audit requires actual persisted Product Stage12")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Selective rescue audit requires the maintained planner-v8 primary")

    params12 = dict(baseline.get("stage12_parameters") or {})
    if params12.get("enable_selective_resegmentation_rescue") is not False:
        raise RuntimeError("Canonical Product baseline must keep selective rescue disabled")
    if params12.get("selective_resegmentation_rescue_contract") != RESCUE_CONTRACT:
        raise RuntimeError("Product baseline rescue contract drift")
    if params12.get("selective_resegmentation_selector_contract") != SELECTOR_CONTRACT:
        raise RuntimeError("Product baseline selector contract drift")

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
    if baseline_output.get("selective_resegmentation_enabled") is not False:
        raise RuntimeError("Persisted canonical Product Stage12 baseline is not fail-closed")
    if int(baseline_output.get("selective_resegmentation_attempted_context_count") or 0) != 0:
        raise RuntimeError("Disabled canonical Product baseline unexpectedly attempted rescue")
    primary_run_id = int(baseline_output.get("primary_translation_run_id") or 0)
    primary_output_sha = str(baseline_output.get("primary_translation_output_sha256") or "")
    if primary_run_id <= 0 or not primary_output_sha:
        raise RuntimeError("Canonical Product baseline lacks immutable primary lineage")
    _assert_source_coverage(baseline_items, content, label="baseline selected Stage12")

    enabled_parameters = dict(params12)
    enabled_parameters["enable_selective_resegmentation_rescue"] = True
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
        raise RuntimeError("Opt-in selective rescue incorrectly reused disabled wrapper identity")
    if enabled.get("selective_resegmentation_enabled") is not True:
        raise RuntimeError("Opt-in Product Stage12 did not enable selective rescue")
    if int(enabled.get("primary_translation_run_id") or 0) != primary_run_id:
        raise RuntimeError("Rescue opt-in changed the immutable primary Stage12 run identity")
    if str(enabled.get("primary_translation_output_sha256") or "") != primary_output_sha:
        raise RuntimeError("Rescue opt-in changed the immutable primary Stage12 output identity")
    if enabled.get("primary_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Rescue opt-in escaped the maintained planner-v8 primary")

    with connect(database, readonly=True) as connection:
        enabled_run = get_run(connection, enabled_run_id)
        enabled_items = get_run_items(
            connection, enabled_run_id, kind="translation_segment"
        )
        primary_run = get_run(connection, primary_run_id)
        primary_items = get_run_items(
            connection, primary_run_id, kind="translation_segment"
        )
    _assert_source_coverage(primary_items, content, label="immutable primary Stage12")
    _assert_source_coverage(enabled_items, content, label="enabled selected Stage12")
    if str(primary_run.get("output_sha256") or "") != primary_output_sha:
        raise RuntimeError("Primary Stage12 output SHA changed after opt-in execution")

    primary_by_id = {int(row["id"]): row for row in primary_items}
    primary_by_span = {
        (int(row["source_start"]), int(row["source_end"])): row
        for row in primary_items
    }
    accepted: dict[int, list[dict[str, Any]]] = {}
    copied_primary_count = 0
    applied_row_count = 0
    for row in enabled_items:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("selective_resegmentation_rescue") or {})
        if rescue.get("contract") != RESCUE_CONTRACT:
            raise RuntimeError("Enabled selected row lacks rescue contract provenance")
        if rescue.get("selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError("Enabled selected row lacks selector contract provenance")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"Enabled selected row violates {flag}=False invariant")

        if rescue.get("applied") is True:
            applied_row_count += 1
            sequence = int(rescue["context_sequence"])
            hypotheses = list(payload.get("hypotheses") or [])
            if not hypotheses:
                raise RuntimeError("Applied rescue row lacks raw OPUS hypotheses")
            raw_rank0 = str((hypotheses[0] or {}).get("text") or "")
            if str(row.get("target_text") or "") != raw_rank0:
                raise RuntimeError("Applied rescue target is not exact raw rank-0 OPUS output")
            if rescue.get("raw_model_rank0") is not True:
                raise RuntimeError("Applied rescue row is not marked raw_model_rank0")
            planner = dict(payload.get("planner") or {})
            if planner.get("source") != "nlp_sentence":
                raise RuntimeError("Applied rescue escaped ordinary NLP-sentence scope")
            accepted.setdefault(sequence, []).append(row)
            continue

        if rescue.get("applied") is not False:
            raise RuntimeError("Enabled selected row has ambiguous rescue applied state")
        primary_id = int(rescue.get("primary_translation_segment_id") or 0)
        primary = primary_by_id.get(primary_id)
        if primary is None:
            raise RuntimeError("Copied enabled row references unknown primary segment")
        for field in ("source_start", "source_end", "source_text", "target_text"):
            if row.get(field) != primary.get(field):
                raise RuntimeError(f"Non-rescued enabled row changed primary {field}")
        copied_primary_count += 1

    accepted_sequences = sorted(accepted)
    published_accepted = [
        int(value)
        for value in enabled.get(
            "selective_resegmentation_accepted_context_sequences", []
        )
    ]
    if accepted_sequences != published_accepted:
        raise RuntimeError("Persisted accepted rescue contexts disagree with Stage12 output")
    if len(accepted_sequences) != int(
        enabled.get("selective_resegmentation_accepted_context_count") or 0
    ):
        raise RuntimeError("Persisted accepted rescue context count disagrees with Stage12 output")

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
    if accepted_sequences and enabled_failure_count >= baseline_failure_count:
        raise RuntimeError("Mechanically accepted rescue did not reduce hard numeric failures")
    if not accepted_sequences and enabled_failure_count != baseline_failure_count:
        raise RuntimeError("No accepted rescue exists but hard numeric failure count changed")

    accepted_contexts: list[dict[str, Any]] = []
    for context_sequence in accepted_sequences:
        rows = sorted(accepted[context_sequence], key=lambda row: int(row["source_start"]))
        first_rescue = dict(
            (rows[0].get("payload") or {}).get("selective_resegmentation_rescue") or {}
        )
        primary_spans = [
            tuple(int(value) for value in span)
            for span in first_rescue.get("primary_source_spans") or []
        ]
        context_primary: list[dict[str, Any]] = []
        for span in primary_spans:
            primary = primary_by_span.get(span)
            if primary is None:
                raise RuntimeError("Accepted rescue references unknown primary source span")
            context_primary.append(primary)
        start = int(rows[0]["source_start"])
        end = int(rows[-1]["source_end"])
        if content[start:end] != "".join(str(row.get("source_text") or "") for row in rows):
            raise RuntimeError("Accepted rescue context differs from immutable source bytes")
        accepted_contexts.append(
            {
                "context_sequence": context_sequence,
                "source_start": start,
                "source_end": end,
                "source_text": content[start:end],
                "trigger": first_rescue.get("trigger"),
                "missing_literal_count": int(first_rescue.get("missing_literal_count") or 0),
                "primary_rows": [
                    {
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                    }
                    for row in context_primary
                ],
                "selected_rows": [
                    {
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                        "split_mode": str(
                            ((row.get("payload") or {}).get("planner") or {}).get(
                                "selective_resegmentation_split_mode"
                            )
                            or ""
                        ),
                        "candidate_verdict": dict(
                            ((row.get("payload") or {}).get("selective_resegmentation_rescue") or {}).get(
                                "candidate_verdict"
                            )
                            or {}
                        ),
                    }
                    for row in rows
                ],
            }
        )

    baseline_failure_spans = [
        [int(row["source_start"]), int(row["source_end"])] for row in baseline_failures
    ]
    enabled_failure_spans = [
        [int(row["source_start"]), int(row["source_end"])] for row in enabled_failures
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "actual public Product Stage12 opt-in selective rescue over the canonical full Opticks baseline",
        "promotion_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "source_char_count": len(content),
        "document_version_id": document_version_id,
        "planner_contract": PLANNER_CONTRACT,
        "rescue_contract": RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "registry_default_enabled": False,
        "baseline_selected_translation_run_id": baseline_run_id,
        "enabled_selected_translation_run_id": enabled_run_id,
        "primary_translation_run_id": primary_run_id,
        "primary_output_sha256": primary_output_sha,
        "primary_identity_reused": True,
        "baseline_hard_numeric_failure_count": baseline_failure_count,
        "enabled_hard_numeric_failure_count": enabled_failure_count,
        "hard_numeric_failure_delta": enabled_failure_count - baseline_failure_count,
        "baseline_hard_numeric_failure_spans": baseline_failure_spans,
        "enabled_hard_numeric_failure_spans": enabled_failure_spans,
        "attempted_context_count": int(
            enabled.get("selective_resegmentation_attempted_context_count") or 0
        ),
        "accepted_context_count": len(accepted_sequences),
        "rejected_context_count": int(
            enabled.get("selective_resegmentation_rejected_context_count") or 0
        ),
        "accepted_context_sequences": accepted_sequences,
        "rejected_context_sequences": [
            int(value)
            for value in enabled.get(
                "selective_resegmentation_rejected_context_sequences", []
            )
        ],
        "rescue_model_request_count": int(
            enabled.get("selective_resegmentation_model_request_count") or 0
        ),
        "rescue_model_batch_count": int(
            enabled.get("selective_resegmentation_model_batch_count") or 0
        ),
        "primary_segment_count": len(primary_items),
        "enabled_segment_count": len(enabled_items),
        "copied_primary_row_count": copied_primary_count,
        "applied_rescue_row_count": applied_row_count,
        "source_coverage_byte_exact": True,
        "non_rescued_rows_primary_exact": True,
        "applied_targets_exact_raw_rank0": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "accepted_contexts": accepted_contexts,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-selective-rescue-optin.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "primary_translation_run_id": primary_run_id,
                "baseline_selected_translation_run_id": baseline_run_id,
                "enabled_selected_translation_run_id": enabled_run_id,
                "baseline_hard_numeric_failure_count": baseline_failure_count,
                "enabled_hard_numeric_failure_count": enabled_failure_count,
                "attempted_context_count": payload["attempted_context_count"],
                "accepted_context_count": payload["accepted_context_count"],
                "rejected_context_count": payload["rejected_context_count"],
                "accepted_context_sequences": accepted_sequences,
                "rejected_context_sequences": payload["rejected_context_sequences"],
                "copied_primary_row_count": copied_primary_count,
                "applied_rescue_row_count": applied_row_count,
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
