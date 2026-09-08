from __future__ import annotations

"""Research-only full-Opticks source-side semantic-hint DOE for prime notation.

The immutable Product source/unit is never changed.  Only the real-OPUS model
input receives a deterministic semantic expansion immediately after each
already-recognized numeric prime event:

- one prime  -> ``arcminute(s)``;
- two primes -> ``arcsecond(s)``;
- three primes -> historical ``third(s) of arc``.

The original prime bytes and all original linguistic context remain in the
model input.  The generated target is raw OPUS output and is evaluated against
the original source with the unchanged Product/research strict verdict.  No
placeholder, target rewriting, post-translation literal injection, or Product
gate change is permitted.  Beam 6 is tried first; beam 12 and 16 are research
escalations only for unresolved units.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.prime_notation import (
    CONTRACT as PRIME_CONTRACT,
    compare_numeric_prime_notation,
    extract_numeric_prime_events,
)
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-prime-semantic-hint-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
PRIME_SCHEMA = "rocketdict-full-opticks-prime-stress/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
EXPECTED_BASELINE_ARTIFACT_DIGEST = (
    "sha256:7c77092dc86516983a7917931e9b000e6c2774595562e8854623a9faff4979b4"
)
GENERATION_CELLS = (
    {"beam_size": 6, "num_hypotheses": 6},
    {"beam_size": 12, "num_hypotheses": 12},
    {"beam_size": 16, "num_hypotheses": 16},
)
BATCH_SIZE = 16


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence_number": int(row["planned_sequence"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row["source_text"]),
        "target_text": None,
    }


def _unit_hint(event_value: str, prime_count: int) -> str:
    singular = event_value == "1"
    if prime_count == 1:
        return " arcminute" if singular else " arcminutes"
    if prime_count == 2:
        return " arcsecond" if singular else " arcseconds"
    if prime_count == 3:
        return " third of arc" if singular else " thirds of arc"
    raise ValueError(f"unsupported prime count for semantic hint: {prime_count}")


def semantic_hint_model_input(text: str) -> str:
    events = extract_numeric_prime_events(text)
    if not events:
        raise ValueError("prime semantic hinting requires numeric prime events")
    output = text
    for event in reversed(events):
        hint = _unit_hint(event.value, event.prime_count)
        output = output[: event.end] + hint + output[event.end :]
    # Hints are alphabetic additions to model input only.  They may not alter
    # the original numeric/prime signature or duplicate any numeric literal.
    if compare_numeric_prime_notation(text, output)["passed"] is not True:
        raise RuntimeError("prime semantic hinting changed the prime signature")
    return output


def _translate_batches(
    translator: OpusTranslator,
    texts: list[str],
    *,
    beam_size: int,
    num_hypotheses: int,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=max_decoding_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("prime semantic-hint translation cardinality mismatch")
    return output


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/full-opticks-artifact/full-opticks-numeric-stress",
        )
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    prime_path = root / "full-opticks-prime-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not prime_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks evidence is incomplete")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    prime = json.loads(prime_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA or prime.get("schema") != PRIME_SCHEMA:
        raise RuntimeError("unexpected full-Opticks evidence schema")
    if baseline.get("source_sha256") != OPTICKS_SHA256 or prime.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT or prime.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("prime semantic-hint baseline planner is not current")
    if prime.get("prime_notation_contract") != PRIME_CONTRACT:
        raise RuntimeError("prime notation contract drift")
    if prime.get("baseline_json_sha256") != _sha_file(baseline_path):
        raise RuntimeError("prime stress does not bind to supplied baseline")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline artifact identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_DIGEST") != EXPECTED_BASELINE_ARTIFACT_DIGEST:
        raise RuntimeError("baseline artifact digest drift")

    ordinary_rows = [
        dict(row)
        for row in list(prime.get("prime_units") or [])
        if not bool(row.get("production_table_composite"))
    ]
    if len(ordinary_rows) != 16:
        raise RuntimeError(f"pinned Opticks ordinary prime-unit inventory drift: {len(ordinary_rows)} != 16")

    by_sequence = {int(row["planned_sequence"]): row for row in ordinary_rows}
    model_inputs = {
        sequence: semantic_hint_model_input(str(row["source_text"]))
        for sequence, row in by_sequence.items()
    }
    if any(model_inputs[sequence] == str(by_sequence[sequence]["source_text"]) for sequence in model_inputs):
        raise RuntimeError("prime semantic hinting did not change a model input")

    punctuation_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("punctuation") or {})
    length_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("length_ratio") or {})
    max_decoding_length = int(prime.get("max_decoding_length") or 512)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    database_sha_before = _sha_file(database)

    unresolved = sorted(by_sequence)
    selected: dict[int, dict[str, Any]] = {}
    evidence: dict[int, list[dict[str, Any]]] = {sequence: [] for sequence in unresolved}

    for cell in GENERATION_CELLS:
        if not unresolved:
            break
        generated = _translate_batches(
            translator,
            [model_inputs[sequence] for sequence in unresolved],
            beam_size=int(cell["beam_size"]),
            num_hypotheses=int(cell["num_hypotheses"]),
            max_decoding_length=max_decoding_length,
        )
        rescued_now: list[int] = []
        for sequence, hypotheses in zip(unresolved, generated, strict=True):
            row = by_sequence[sequence]
            source_row = _source_row(row)
            candidates: list[dict[str, Any]] = []
            chosen: dict[str, Any] | None = None
            for model_index, hypothesis in enumerate(hypotheses):
                target = str(hypothesis.get("text") or "")
                verdict = _verdict(
                    source_row,
                    target,
                    punctuation_parameters=punctuation_parameters,
                    length_parameters=length_parameters,
                )
                candidate = {
                    "model_index": model_index,
                    "rank": int(hypothesis.get("rank") if hypothesis.get("rank") is not None else model_index),
                    "score": hypothesis.get("score"),
                    "target_text": target,
                    "prime_notation": compare_numeric_prime_notation(str(row["source_text"]), target),
                    "verdict": verdict,
                }
                candidates.append(candidate)
                if chosen is None and verdict.get("strictly_eligible") is True:
                    chosen = candidate
            evidence[sequence].append(
                {
                    "generation": dict(cell),
                    "candidate_count": len(candidates),
                    "strictly_eligible_count": sum(
                        1 for candidate in candidates if candidate["verdict"].get("strictly_eligible") is True
                    ),
                    "selected_rank": None if chosen is None else int(chosen["rank"]),
                    "candidates": candidates,
                }
            )
            if chosen is not None:
                selected[sequence] = {"generation": dict(cell), **chosen}
                rescued_now.append(sequence)
        rescued_set = set(rescued_now)
        unresolved = [sequence for sequence in unresolved if sequence not in rescued_set]

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("prime semantic-hint inference mutated retained Product database")

    baseline_failures = [
        int(row["planned_sequence"])
        for row in ordinary_rows
        if (row.get("strict_verdict") or {}).get("strictly_eligible") is not True
    ]
    results = []
    for row in ordinary_rows:
        sequence = int(row["planned_sequence"])
        results.append(
            {
                "planned_sequence": sequence,
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "baseline_target_text": str(row["rank0_target_text"]),
                "baseline_strictly_eligible": (row.get("strict_verdict") or {}).get("strictly_eligible") is True,
                "semantic_hint_model_input": model_inputs[sequence],
                "semantic_hint_model_input_changed": True,
                "cells": evidence[sequence],
                "selected": selected.get(sequence),
            }
        )

    baseline_failure_rescues = sorted(sequence for sequence in baseline_failures if sequence in selected)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-Opticks whole-unit source-side semantic disambiguation of numeric prime marks with raw OPUS selection",
        "promotion_allowed": False,
        "product_gate_changed": False,
        "immutable_source_changed": False,
        "model_input_semantic_expansion": True,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "prime_notation_contract": PRIME_CONTRACT,
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_artifact_digest": EXPECTED_BASELINE_ARTIFACT_DIGEST,
        "baseline_numeric_json_sha256": _sha_file(baseline_path),
        "baseline_prime_json_sha256": _sha_file(prime_path),
        "generation_cells": [dict(cell) for cell in GENERATION_CELLS],
        "ordinary_prime_unit_count": len(ordinary_rows),
        "baseline_strict_failure_count": len(baseline_failures),
        "baseline_strict_failure_sequences": baseline_failures,
        "strict_success_count": len(selected),
        "strict_success_sequences": sorted(selected),
        "baseline_failure_rescue_count": len(baseline_failure_rescues),
        "baseline_failure_rescue_sequences": baseline_failure_rescues,
        "residual_count": len(unresolved),
        "residual_sequences": sorted(unresolved),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(os.environ.get("ROCKETDICT_PRIME_FEASIBILITY_ROOT", "work/prime-feasibility")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-prime-semantic-hint-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "ordinary_prime_unit_count",
                    "baseline_strict_failure_count",
                    "strict_success_count",
                    "baseline_failure_rescue_count",
                    "baseline_failure_rescue_sequences",
                    "residual_count",
                    "residual_sequences",
                    "evidence_sha256",
                )
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
