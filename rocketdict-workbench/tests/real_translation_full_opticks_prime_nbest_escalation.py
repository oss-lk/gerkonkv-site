from __future__ import annotations

"""Research-only staged raw-OPUS n-best escalation for prime-bearing failures.

Unlike the generic n-best experiment, this scope is source-defined by numeric
prime notation. The complete original Stage12 unit is translated unchanged so
linguistic context is preserved. Beam 6, 12, then 16 are attempted only for
units whose persisted Product rank0 target fails the unchanged strict verdict.
Only raw OPUS hypotheses may be selected; there is no source rewrite, target
rewrite, placeholder, or literal injection.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.prime_notation import CONTRACT as PRIME_CONTRACT
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-prime-nbest-escalation/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
PRIME_SCHEMA = "rocketdict-full-opticks-prime-stress/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
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
        raise RuntimeError("prime n-best translation cardinality mismatch")
    return output


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-artifact/full-opticks-numeric-stress")
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
        raise RuntimeError("prime n-best baseline planner is not current")
    if prime.get("prime_notation_contract") != PRIME_CONTRACT:
        raise RuntimeError("prime notation contract drift")
    if prime.get("baseline_json_sha256") != _sha_file(baseline_path):
        raise RuntimeError("prime stress does not bind to supplied baseline")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline artifact identity drift")

    failed_rows = [
        dict(row)
        for row in list(prime.get("prime_units") or [])
        if not bool(row.get("production_table_composite"))
        and (row.get("strict_verdict") or {}).get("strictly_eligible") is not True
    ]
    if len(failed_rows) != 11:
        raise RuntimeError(f"pinned Opticks prime failure inventory drift: {len(failed_rows)} != 11")

    punctuation_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("punctuation") or {})
    length_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("length_ratio") or {})
    max_decoding_length = int(prime.get("max_decoding_length") or 512)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    database_sha_before = _sha_file(database)

    unresolved = [int(row["planned_sequence"]) for row in failed_rows]
    by_sequence = {int(row["planned_sequence"]): row for row in failed_rows}
    selected: dict[int, dict[str, Any]] = {}
    evidence: dict[int, list[dict[str, Any]]] = {sequence: [] for sequence in unresolved}

    for cell in GENERATION_CELLS:
        if not unresolved:
            break
        generated = _translate_batches(
            translator,
            [str(by_sequence[sequence]["source_text"]) for sequence in unresolved],
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
        raise RuntimeError("prime n-best inference mutated retained Product database")

    results = [
        {
            "planned_sequence": int(row["planned_sequence"]),
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": str(row["source_text"]),
            "baseline_target_text": str(row["rank0_target_text"]),
            "cells": evidence[int(row["planned_sequence"])],
            "selected": selected.get(int(row["planned_sequence"])),
        }
        for row in failed_rows
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "staged raw whole-unit OPUS n-best for source-defined prime-notation Product failures",
        "promotion_allowed": False,
        "source_text_changed": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "prime_notation_contract": PRIME_CONTRACT,
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_numeric_json_sha256": _sha_file(baseline_path),
        "baseline_prime_json_sha256": _sha_file(prime_path),
        "generation_cells": [dict(cell) for cell in GENERATION_CELLS],
        "input_failure_count": len(failed_rows),
        "input_failure_sequences": [int(row["planned_sequence"]) for row in failed_rows],
        "rescue_count": len(selected),
        "rescued_sequences": sorted(selected),
        "residual_count": len(unresolved),
        "residual_sequences": sorted(unresolved),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(os.environ.get("ROCKETDICT_PRIME_FEASIBILITY_ROOT", "work/prime-feasibility")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-prime-nbest-escalation.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "input_failure_count",
                    "rescue_count",
                    "rescued_sequences",
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
