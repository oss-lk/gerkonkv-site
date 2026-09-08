from __future__ import annotations

"""Full contiguous Opticks rank-0 stress for numeric prime-mark notation.

This research-only harness reuses the immutable Stage8/10 database produced by
``real_translation_full_opticks_numeric_stress`` and reconstructs the exact
current Stage12 plan over the complete pinned source. Every planned unit whose
source contains conservative numeric prime notation is translated with the same
rank-0 OPUS semantics as Product Stage12, including the maintained composite
ASCII-table path.

The goal is to measure a known selector blind spot without changing Product
hard gates: historical apostrophe decimals remain numeric-v4 territory, while
minute/second/third-style prime marks receive an independent research verdict.
No target rewriting, placeholder repair, literal injection, or database mutation
is allowed.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import (
    connect,
    get_document,
    get_document_segments,
    get_run_items,
)
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair
from rocketdict.prime_notation import CONTRACT as PRIME_CONTRACT
from rocketdict.prime_notation import compare_numeric_prime_notation, extract_numeric_prime_events
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_stage import PLANNER_CONTRACT, segment_translation_units

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_full_opticks_numeric_stress import (  # noqa: E402
    OPTICKS_SHA256,
    _production_rank0_targets,
    _sha_file,
)
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-prime-stress/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/2"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _row(unit: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {
        "sequence_number": sequence,
        "source_start": int(unit["start"]),
        "source_end": int(unit["end"]),
        "source_text": str(unit["text"]),
        "target_text": None,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    source_path = Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"]).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Full Opticks prime stress prerequisites are missing")
    if _sha_file(source_path) != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source hash drift")

    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"Unexpected numeric-stress schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks identity drift in numeric-stress evidence")
    if baseline.get("no_synthetic_target_repair") is not True:
        raise RuntimeError("Numeric-stress evidence lacks no-repair invariant")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Prime stress baseline does not use the current Stage12 planner")

    document_version_id = int(baseline["document_version_id"])
    nlp_run_id = int((baseline.get("stage8") or {})["nlp_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    stage12_parameters = dict(baseline.get("stage12_parameters") or {})
    preferred_tokens = int(stage12_parameters.get("plan_preferred_unit_tokens") or 64)
    punctuation_parameters = dict(
        ((baseline.get("quality_gate_parameters") or {}).get("punctuation") or {})
    )
    length_parameters = dict(
        ((baseline.get("quality_gate_parameters") or {}).get("length_ratio") or {})
    )
    if not length_parameters:
        raise RuntimeError("Prime stress baseline lacks length-ratio gate parameters")

    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        document_segments = get_document_segments(connection, document_version_id)
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
    content = str(document["content_text"])
    if content != source_path.read_text(encoding="utf-8"):
        raise RuntimeError("Prime stress database source differs from pinned immutable Opticks bytes")

    units = segment_translation_units(
        content,
        document_segments,
        context_rows,
        nlp_tokens,
        selected_format=str(document["selected_format"]),
        preferred_tokens=preferred_tokens,
    )
    if "".join(str(unit["text"]) for unit in units) != content:
        raise RuntimeError("Prime stress Stage12 plan does not cover full Opticks byte-exactly")
    if len(units) != int(baseline.get("planned_unit_count") or -1):
        raise RuntimeError("Prime stress Stage12 planned-unit cardinality drift")

    prime_units = [
        (sequence, unit)
        for sequence, unit in enumerate(units)
        if extract_numeric_prime_events(str(unit["text"]))
    ]
    if not prime_units:
        raise RuntimeError("Full Opticks plan contains no numeric prime-bearing units")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    targets, max_decoding_length, table_request_count = _production_rank0_targets(
        translator,
        prime_units,
        beam_size=int(stage12_parameters.get("beam_size") or 6),
        preferred_tokens=preferred_tokens,
    )

    records: list[dict[str, Any]] = []
    prime_failures: list[dict[str, Any]] = []
    prime_only_failures: list[dict[str, Any]] = []
    numeric_only_failures: list[dict[str, Any]] = []
    strict_failures: list[dict[str, Any]] = []
    for sequence, unit in prime_units:
        source = str(unit["text"])
        target_row = targets[sequence]
        target = str(target_row["target_text"])
        source_row = _row(unit, sequence)
        numeric = evaluate_numeric_symbol_pair(source, target)
        prime = compare_numeric_prime_notation(source, target)
        strict = _verdict(
            source_row,
            target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        record = {
            "planned_sequence": sequence,
            "source_start": int(unit["start"]),
            "source_end": int(unit["end"]),
            "source_text": source,
            "planner": dict(unit.get("metadata") or {}),
            "rank0_target_text": target,
            "rank0_score": target_row.get("rank0_score"),
            "production_table_composite": bool(target_row["production_table_composite"]),
            "source_prime_events": [
                {
                    "value": event.value,
                    "prime_count": event.prime_count,
                    "raw": event.raw,
                    "start": event.start,
                    "end": event.end,
                }
                for event in extract_numeric_prime_events(source)
            ],
            "product_numeric_symbol": numeric,
            "prime_notation": prime,
            "strict_verdict": strict,
        }
        records.append(record)
        if prime["passed"] is not True:
            prime_failures.append(record)
            if numeric["passed"] is True:
                prime_only_failures.append(record)
        if numeric["passed"] is not True and prime["passed"] is True:
            numeric_only_failures.append(record)
        if strict["strictly_eligible"] is not True:
            strict_failures.append(record)

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Prime stress mutated the Stage8/10 research database")

    table_units = [row for row in records if row["production_table_composite"]]
    prime_count_distribution = Counter(
        event["prime_count"]
        for row in records
        for event in row["source_prime_events"]
    )
    asset = translator.asset
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full contiguous Opticks prevalence and rank0 integrity audit for numeric prime-mark notation",
        "promotion_allowed": False,
        "product_gate_changed": False,
        "research_diagnostic_only": True,
        "no_synthetic_target_repair": True,
        "no_post_translation_literal_injection": True,
        "source_sha256": OPTICKS_SHA256,
        "source_char_count": len(content),
        "source_text_sha256": str(document["text_sha256"]),
        "baseline_json_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "baseline_internal_evidence_sha256": str(baseline.get("evidence_sha256") or ""),
        "document_version_id": document_version_id,
        "stage12_planner_contract": PLANNER_CONTRACT,
        "stage12_parameters": stage12_parameters,
        "prime_notation_contract": PRIME_CONTRACT,
        "planned_unit_count": len(units),
        "prime_bearing_unit_count": len(records),
        "prime_bearing_sequences": [int(row["planned_sequence"]) for row in records],
        "source_prime_event_count": sum(len(row["source_prime_events"]) for row in records),
        "source_prime_count_distribution": {
            str(key): value for key, value in sorted(prime_count_distribution.items())
        },
        "table_prime_bearing_unit_count": len(table_units),
        "table_prime_model_request_count": table_request_count,
        "prime_rank0_failure_count": len(prime_failures),
        "prime_rank0_failure_sequences": [
            int(row["planned_sequence"]) for row in prime_failures
        ],
        "prime_only_failure_count": len(prime_only_failures),
        "prime_only_failure_sequences": [
            int(row["planned_sequence"]) for row in prime_only_failures
        ],
        "product_numeric_failure_prime_pass_count": len(numeric_only_failures),
        "product_numeric_failure_prime_pass_sequences": [
            int(row["planned_sequence"]) for row in numeric_only_failures
        ],
        "strict_failure_count": len(strict_failures),
        "strict_failure_sequences": [
            int(row["planned_sequence"]) for row in strict_failures
        ],
        "max_decoding_length": max_decoding_length,
        "model": {
            "revision": asset.revision,
            "source_archive_sha256": asset.source_archive_sha256,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "compute_type": "float32",
            "device": "cpu",
        },
        "database_sha256_before_inference": database_sha_before,
        "database_sha256_after_inference": database_sha_after,
        "quality_gate_parameters": {
            "punctuation": punctuation_parameters,
            "length_ratio": length_parameters,
        },
        "prime_units": records,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-prime-stress.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "prime_bearing_unit_count": len(records),
                "source_prime_event_count": payload["source_prime_event_count"],
                "prime_rank0_failure_count": len(prime_failures),
                "prime_only_failure_count": len(prime_only_failures),
                "product_numeric_failure_prime_pass_count": len(numeric_only_failures),
                "strict_failure_count": len(strict_failures),
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
