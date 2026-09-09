from __future__ import annotations

"""Audit persisted full-Opticks Product Stage12 selective-rescue provenance.

The preceding full-corpus numeric stress owns the Product project/database. This
read-only audit proves that the public Stage12 selected run is derived from one
immutable primary planner-v8 run, that non-rescued rows are exact primary copies,
and that every rescued target is the exact raw rank-0 OPUS hypothesis recorded
in its payload. It exports complete accepted contexts for manual semantic review.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_rescue import RESCUE_CONTRACT, SELECTOR_CONTRACT
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-selective-rescue-audit/1"
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


def _json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise RuntimeError("Expected JSON object in Stage12 run metadata")
    return parsed


def _selected_stage12_run(connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT * FROM stage_runs
        WHERE stage_number=12 AND implementation='opus-en-ru-ct2' AND status='completed'
        ORDER BY id
        """
    ).fetchall()
    selected: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        output = _json(row.get("output_json"))
        if output.get("selective_resegmentation_rescue_contract") == RESCUE_CONTRACT:
            row["output"] = output
            row["input_identity"] = _json(row.get("input_identity_json"))
            row["parameters"] = _json(row.get("parameters_json"))
            selected.append(row)
    if len(selected) != 1:
        raise RuntimeError(
            f"Expected exactly one completed selected Stage12 run, observed {len(selected)}"
        )
    return selected[0]


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not database.is_file():
        raise RuntimeError(f"Full Opticks Product database is missing: {database}")

    with connect(database, readonly=True) as connection:
        selected_run = _selected_stage12_run(connection)
        selected_output = dict(selected_run["output"])
        selected_run_id = int(selected_run["id"])
        if int(selected_output.get("translation_run_id") or -1) != selected_run_id:
            raise RuntimeError("Selected Stage12 output does not identify its own immutable run")
        if selected_output.get("selective_resegmentation_selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError("Selected Stage12 selector contract drift")
        if selected_output.get("primary_planner_contract") != PLANNER_CONTRACT:
            raise RuntimeError("Selected Stage12 primary planner contract drift")

        primary_run_id = int(selected_output.get("primary_translation_run_id") or 0)
        if primary_run_id <= 0 or primary_run_id == selected_run_id:
            raise RuntimeError("Selected Stage12 has invalid primary run identity")
        primary_run = get_run(connection, primary_run_id)
        primary_output = dict(primary_run.get("output") or {})
        if primary_run.get("status") != "completed":
            raise RuntimeError("Selected Stage12 primary run is not completed")
        if str(primary_run.get("output_sha256") or "") != str(
            selected_output.get("primary_translation_output_sha256") or ""
        ):
            raise RuntimeError("Selected Stage12 primary output SHA lineage mismatch")

        input_identity = dict(selected_run["input_identity"])
        if int(input_identity.get("primary_translation_run_id") or 0) != primary_run_id:
            raise RuntimeError("Selected Stage12 cache identity omits/mismatches primary run id")
        if str(input_identity.get("primary_translation_output_sha256") or "") != str(
            primary_run.get("output_sha256") or ""
        ):
            raise RuntimeError("Selected Stage12 cache identity omits/mismatches primary output SHA")

        document_version_id = int(selected_output.get("document_version_id") or 0)
        document = get_document(connection, document_version_id)
        content = str(document["content_text"])
        selected_items = get_run_items(
            connection, selected_run_id, kind="translation_segment"
        )
        primary_items = get_run_items(
            connection, primary_run_id, kind="translation_segment"
        )

    if not selected_items or not primary_items:
        raise RuntimeError("Stage12 rescue audit observed empty persisted translation rows")
    if "".join(str(row.get("source_text") or "") for row in selected_items) != content:
        raise RuntimeError("Selected Stage12 source coverage is not byte-exact")
    if "".join(str(row.get("source_text") or "") for row in primary_items) != content:
        raise RuntimeError("Primary Stage12 source coverage is not byte-exact")
    if int(selected_output.get("source_character_sum") or -1) != len(content):
        raise RuntimeError("Selected Stage12 source character sum drift")
    if int(primary_output.get("source_character_sum") or -1) != len(content):
        raise RuntimeError("Primary Stage12 source character sum drift")

    primary_by_id = {int(row["id"]): row for row in primary_items}
    primary_by_span = {
        (int(row["source_start"]), int(row["source_end"])): row
        for row in primary_items
    }
    accepted: dict[int, list[dict[str, Any]]] = {}
    copied_count = 0
    applied_row_count = 0

    for row in selected_items:
        payload = dict(row.get("payload") or {})
        rescue = dict(payload.get("selective_resegmentation_rescue") or {})
        if rescue.get("contract") != RESCUE_CONTRACT:
            raise RuntimeError("Selected Stage12 row lacks rescue contract provenance")
        if rescue.get("selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError("Selected Stage12 row lacks selector contract provenance")
        for flag in (
            "source_bytes_rewritten",
            "target_rewriting",
            "placeholders",
            "post_translation_literal_injection",
        ):
            if rescue.get(flag) is not False:
                raise RuntimeError(f"Selected Stage12 row violates {flag}=False invariant")

        if rescue.get("applied") is True:
            applied_row_count += 1
            context_sequence = int(rescue["context_sequence"])
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
                raise RuntimeError("Applied rescue escaped the ordinary NLP-sentence scope")
            if planner.get("selective_resegmentation_rescue_contract") != RESCUE_CONTRACT:
                raise RuntimeError("Applied rescue planner provenance drift")
            accepted.setdefault(context_sequence, []).append(row)
            continue

        if rescue.get("applied") is not False:
            raise RuntimeError("Selected Stage12 row has ambiguous rescue applied state")
        primary_id = int(rescue.get("primary_translation_segment_id") or 0)
        primary = primary_by_id.get(primary_id)
        if primary is None:
            raise RuntimeError("Copied selected row references unknown primary segment")
        for field in ("source_start", "source_end", "source_text", "target_text"):
            if row.get(field) != primary.get(field):
                raise RuntimeError(f"Non-rescued selected row changed primary {field}")
        copied_count += 1

    accepted_sequences = sorted(accepted)
    published_sequences = [
        int(value)
        for value in selected_output.get(
            "selective_resegmentation_accepted_context_sequences", []
        )
    ]
    if accepted_sequences != published_sequences:
        raise RuntimeError("Persisted accepted rescue contexts disagree with Stage12 output")
    if len(accepted_sequences) != int(
        selected_output.get("selective_resegmentation_accepted_context_count") or 0
    ):
        raise RuntimeError("Persisted accepted rescue context count disagrees with Stage12 output")

    accepted_contexts: list[dict[str, Any]] = []
    for context_sequence in accepted_sequences:
        rows = sorted(accepted[context_sequence], key=lambda row: int(row["source_start"]))
        first_rescue = dict((rows[0].get("payload") or {}).get("selective_resegmentation_rescue") or {})
        primary_spans = [tuple(int(value) for value in span) for span in first_rescue.get("primary_source_spans") or []]
        primary_rows: list[dict[str, Any]] = []
        for span in primary_spans:
            primary = primary_by_span.get(span)
            if primary is None:
                raise RuntimeError("Accepted rescue references unknown primary source span")
            primary_rows.append(primary)
        source_start = int(rows[0]["source_start"])
        source_end = int(rows[-1]["source_end"])
        source_text = "".join(str(row.get("source_text") or "") for row in rows)
        if content[source_start:source_end] != source_text:
            raise RuntimeError("Accepted rescue context source is not immutable source bytes")
        accepted_contexts.append(
            {
                "context_sequence": context_sequence,
                "source_start": source_start,
                "source_end": source_end,
                "source_text": source_text,
                "trigger": first_rescue.get("trigger"),
                "missing_literal_count": int(first_rescue.get("missing_literal_count") or 0),
                "primary_rows": [
                    {
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                    }
                    for row in primary_rows
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

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only provenance and semantic-review surface for actual full-Opticks Product Stage12 selective rescue",
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "source_char_count": len(content),
        "document_version_id": document_version_id,
        "selected_translation_run_id": selected_run_id,
        "selected_output_sha256": str(selected_run.get("output_sha256") or ""),
        "primary_translation_run_id": primary_run_id,
        "primary_output_sha256": str(primary_run.get("output_sha256") or ""),
        "planner_contract": PLANNER_CONTRACT,
        "rescue_contract": RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "attempted_context_count": int(
            selected_output.get("selective_resegmentation_attempted_context_count") or 0
        ),
        "accepted_context_count": len(accepted_sequences),
        "rejected_context_count": int(
            selected_output.get("selective_resegmentation_rejected_context_count") or 0
        ),
        "accepted_context_sequences": accepted_sequences,
        "rejected_context_sequences": [
            int(value)
            for value in selected_output.get(
                "selective_resegmentation_rejected_context_sequences", []
            )
        ],
        "rescue_model_request_count": int(
            selected_output.get("selective_resegmentation_model_request_count") or 0
        ),
        "primary_segment_count": len(primary_items),
        "selected_segment_count": len(selected_items),
        "copied_primary_row_count": copied_count,
        "applied_rescue_row_count": applied_row_count,
        "source_coverage_byte_exact": True,
        "primary_lineage_sha_verified": True,
        "non_rescued_rows_primary_exact": True,
        "applied_targets_exact_raw_rank0": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "accepted_contexts": accepted_contexts,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-selective-rescue-audit.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "attempted_context_count": payload["attempted_context_count"],
                "accepted_context_count": payload["accepted_context_count"],
                "rejected_context_count": payload["rejected_context_count"],
                "accepted_context_sequences": accepted_sequences,
                "copied_primary_row_count": copied_count,
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
