from __future__ import annotations

"""Research-only staged n-best escalation on full Opticks numeric residuals.

Consumes the immutable evidence emitted by ``real_translation_full_opticks_numeric_stress``
and retries only ordinary numeric failures that were already proven isolated from
punctuation, length, delimiter, critical-token, and output-artifact concerns but
were not rescued by the beam-6 Product-shaped research retry.  Beam 12 then 16
are tried in order.  Only raw OPUS hypotheses that pass the exact same strict
verdict are eligible; nothing is inserted, rewritten, or repaired after MT.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.runtime import OpusTranslator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-nbest-escalation/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
GENERATION_CELLS = (
    {"beam_size": 12, "num_hypotheses": 12},
    {"beam_size": 16, "num_hypotheses": 16},
)
BATCH_SIZE = 24


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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
        raise RuntimeError("Full Opticks n-best escalation batch cardinality mismatch")
    return output


def _source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence_number": int(row["planned_sequence"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row["source_text"]),
        "target_text": None,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    if not baseline_path.is_file():
        raise RuntimeError("Full Opticks numeric stress evidence is missing")
    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"Unexpected full Opticks numeric stress schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks identity drift in numeric stress evidence")
    if baseline.get("no_synthetic_target_repair") is not True:
        raise RuntimeError("Numeric stress evidence does not prove no-synthetic-repair semantics")

    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})
    if not length_parameters:
        raise RuntimeError("Full Opticks evidence lacks length-ratio gate parameters")

    numeric_failures = list(baseline.get("numeric_failures") or [])
    initial = [
        row
        for row in numeric_failures
        if row.get("production_table_composite") is not True
        and row.get("production_structural_label") is not True
        and row.get("numeric_failure_is_isolated") is True
        and not isinstance(row.get("selected_strict_candidate"), dict)
    ]
    if not initial:
        raise RuntimeError("No isolated beam-6 residuals remain for staged n-best escalation")

    unresolved = {int(row["planned_sequence"]): row for row in initial}
    results: dict[int, dict[str, Any]] = {
        sequence: {
            "planned_sequence": sequence,
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": str(row["source_text"]),
            "product_baseline_target_text": str(row["product_target_text"]),
            "beam6_candidate_count": len(row.get("candidates") or []),
            "cells": [],
            "selected": None,
        }
        for sequence, row in unresolved.items()
    }

    translator = OpusTranslator(device="cpu", compute_type="float32")
    max_planned_tokens = int(baseline.get("max_planned_unit_tokens") or 64)
    max_decoding_length = max(128, max_planned_tokens * 8)

    for cell in GENERATION_CELLS:
        if not unresolved:
            break
        sequences = sorted(unresolved)
        generated = _translate_batches(
            translator,
            [str(unresolved[sequence]["source_text"]) for sequence in sequences],
            beam_size=int(cell["beam_size"]),
            num_hypotheses=int(cell["num_hypotheses"]),
            max_decoding_length=max_decoding_length,
        )
        rescued_now: list[int] = []
        for sequence, hypotheses in zip(sequences, generated, strict=True):
            row = unresolved[sequence]
            source_row = _source_row(row)
            candidates: list[dict[str, Any]] = []
            selected: dict[str, Any] | None = None
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
                if selected is None and verdict.get("strictly_eligible") is True:
                    selected = candidate
            results[sequence]["cells"].append(
                {
                    "generation": dict(cell),
                    "candidate_count": len(candidates),
                    "strictly_eligible_count": sum(
                        1 for candidate in candidates if candidate["verdict"].get("strictly_eligible") is True
                    ),
                    "selected_rank": None if selected is None else int(selected["rank"]),
                    "selected_target_text": None if selected is None else str(selected["target_text"]),
                    "candidates": candidates,
                }
            )
            if selected is not None:
                results[sequence]["selected"] = {
                    "generation": dict(cell),
                    **selected,
                }
                rescued_now.append(sequence)
        for sequence in rescued_now:
            unresolved.pop(sequence, None)

    selected = [row for row in results.values() if isinstance(row.get("selected"), dict)]
    residual_sequences = sorted(unresolved)
    rank_distribution = Counter(int(row["selected"]["rank"]) for row in selected)
    generation_distribution = Counter(
        f"beam-{row['selected']['generation']['beam_size']}"
        for row in selected
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-corpus generalization test for staged raw-model n-best escalation after beam-6 isolated numeric residuals",
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "no_post_translation_literal_injection": True,
        "source_sha256": OPTICKS_SHA256,
        "baseline_evidence_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "baseline_internal_evidence_sha256": str(baseline.get("evidence_sha256") or ""),
        "model": dict(baseline.get("model") or {}),
        "generation_cells": [dict(cell) for cell in GENERATION_CELLS],
        "selection_rule": "after beam-6 failed on an ordinary isolated numeric hard failure, escalate beam 12 then 16 and select the first/highest raw OPUS hypothesis passing the unchanged complete strict verdict; never rewrite a hypothesis",
        "max_decoding_length": max_decoding_length,
        "initial_beam6_isolated_residual_count": len(initial),
        "initial_beam6_isolated_residual_sequences": sorted(results),
        "escalation_rescue_count": len(selected),
        "escalation_rescue_sequences": sorted(int(row["planned_sequence"]) for row in selected),
        "residual_count": len(residual_sequences),
        "residual_sequences": residual_sequences,
        "selected_rank_distribution": {str(k): v for k, v in sorted(rank_distribution.items())},
        "selected_generation_distribution": dict(sorted(generation_distribution.items())),
        "results": [results[sequence] for sequence in sorted(results)],
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-nbest-escalation.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
