from __future__ import annotations

"""Research-only full-Opticks DOE for prime/unit-notation preservation.

The probe consumes the immutable successful planner-v8 full-Opticks artifact and
compares two source-side mechanisms on every ordinary Stage12 unit containing
numeric prime notation:

1. whole-unit model-input canonicalization from ASCII/curly prime runs to the
   corresponding Unicode prime glyphs, preserving the complete linguistic
   context and selecting only raw OPUS hypotheses;
2. structural decomposition where numeric prime-expression spans are preserved
   byte-exact as non-linguistic technical notation and every alphabetic source
   fragment is translated by the same real OPUS model before ordered assembly.

Neither branch rewrites an OPUS target, inserts a missing literal after MT, uses
placeholders, or changes the Product hard gate. This is feasibility evidence,
not Product policy.
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

SCHEMA = "rocketdict-full-opticks-prime-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
PRIME_SCHEMA = "rocketdict-full-opticks-prime-stress/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
EXPECTED_BASELINE_ARTIFACT_DIGEST = (
    "sha256:7c77092dc86516983a7917931e9b000e6c2774595562e8854623a9faff4979b4"
)
CANONICAL_GENERATION = {"beam_size": 6, "num_hypotheses": 6}
STRUCTURAL_GENERATION = {"beam_size": 6, "num_hypotheses": 1}
BATCH_SIZE = 32


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
        raise RuntimeError("prime feasibility translation cardinality mismatch")
    return output


def _prime_glyph(count: int) -> str:
    if count == 1:
        return "′"
    if count == 2:
        return "″"
    if count == 3:
        return "‴"
    return "′" * count


def _unicode_prime_model_input(text: str) -> str:
    events = extract_numeric_prime_events(text)
    if not events:
        raise ValueError("prime canonicalization requires at least one numeric prime event")
    output = text
    for event in reversed(events):
        raw = output[event.start : event.end]
        digits = "".join(char for char in raw if char.isdigit())
        if not digits:
            raise RuntimeError("numeric prime event lost its numeric value")
        replacement = digits + _prime_glyph(event.prime_count)
        output = output[: event.start] + replacement + output[event.end :]
    if not extract_numeric_prime_events(output):
        raise RuntimeError("Unicode prime canonicalization destroyed prime events")
    return output


def _technical_spans(text: str) -> list[tuple[int, int]]:
    events = extract_numeric_prime_events(text)
    if not events:
        return []
    spans: list[tuple[int, int]] = []
    start = int(events[0].start)
    end = int(events[0].end)
    for event in events[1:]:
        gap = text[end : int(event.start)]
        # Join adjacent prime values only across punctuation/whitespace. Any
        # alphabetic or numeric content remains linguistic model input.
        if not any(char.isalnum() or char == "_" for char in gap):
            end = int(event.end)
            continue
        spans.append((start, end))
        start = int(event.start)
        end = int(event.end)
    spans.append((start, end))
    return spans


def _parts(text: str) -> list[dict[str, Any]]:
    spans = _technical_spans(text)
    if not spans:
        raise ValueError("prime structural split requires at least one technical span")
    output: list[dict[str, Any]] = []
    cursor = 0
    for start, end in spans:
        if start > cursor:
            output.append({"kind": "prose", "start": cursor, "end": start, "text": text[cursor:start]})
        output.append({"kind": "prime", "start": start, "end": end, "text": text[start:end]})
        cursor = end
    if cursor < len(text):
        output.append({"kind": "prose", "start": cursor, "end": len(text), "text": text[cursor:]})
    if "".join(str(part["text"]) for part in output) != text:
        raise RuntimeError("prime structural split is not byte-exact")
    return output


def _core(fragment: str) -> tuple[str, str, str]:
    if not fragment.strip():
        return fragment, "", ""
    left = len(fragment) - len(fragment.lstrip())
    right = len(fragment) - len(fragment.rstrip())
    leading = fragment[:left]
    trailing = fragment[len(fragment) - right :] if right else ""
    end = len(fragment) - right if right else len(fragment)
    return leading, fragment[left:end], trailing


def _structural_jobs(rows: list[dict[str, Any]]) -> tuple[list[str], list[tuple[int, int]], dict[int, list[dict[str, Any]]]]:
    jobs: list[str] = []
    refs: list[tuple[int, int]] = []
    plans: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        sequence = int(row["planned_sequence"])
        parts = _parts(str(row["source_text"]))
        plans[sequence] = parts
        for part_index, part in enumerate(parts):
            if part["kind"] != "prose":
                continue
            _, core, _ = _core(str(part["text"]))
            if not core:
                continue
            # Punctuation-only fragments are source-owned layout; all source
            # alphabetic content and numeric prose context must go through MT.
            if not any(char.isalnum() for char in core):
                continue
            jobs.append(core)
            refs.append((sequence, part_index))
    return jobs, refs, plans


def _compose_structural(
    parts: list[dict[str, Any]],
    translated: dict[int, dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    output: list[str] = []
    evidence: list[dict[str, Any]] = []
    for part_index, part in enumerate(parts):
        text = str(part["text"])
        if part["kind"] == "prime":
            if any(char.isalpha() for char in text):
                raise RuntimeError("prime technical span unexpectedly contains alphabetic source content")
            output.append(text)
            evidence.append(
                {
                    "kind": "prime",
                    "source_text": text,
                    "target_text": text,
                    "source_owned_technical_notation": True,
                    "model_request": False,
                }
            )
            continue
        leading, core, trailing = _core(text)
        if not core or not any(char.isalnum() for char in core):
            output.append(text)
            evidence.append(
                {
                    "kind": "layout",
                    "source_text": text,
                    "target_text": text,
                    "source_owned_layout_only": True,
                    "model_request": False,
                }
            )
            continue
        hypothesis = translated.get(part_index)
        if hypothesis is None:
            raise RuntimeError("missing translated prime-feasibility prose fragment")
        target_core = str(hypothesis.get("text") or "").strip()
        if not target_core:
            raise RuntimeError("OPUS returned an empty prime-feasibility prose fragment")
        output.append(leading + target_core + trailing)
        evidence.append(
            {
                "kind": "prose",
                "source_text": text,
                "source_core": core,
                "target_core": target_core,
                "model_request": True,
                "model_rank": int(hypothesis.get("rank") or 0),
                "model_score": hypothesis.get("score"),
            }
        )
    return "".join(output), evidence


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-artifact/full-opticks-numeric-stress")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    prime_path = root / "full-opticks-prime-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not prime_path.is_file() or not database.is_file():
        raise RuntimeError("successful planner-v8 full-Opticks artifact is incomplete")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    prime = json.loads(prime_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA or prime.get("schema") != PRIME_SCHEMA:
        raise RuntimeError("unexpected full-Opticks evidence schema")
    if baseline.get("source_sha256") != OPTICKS_SHA256 or prime.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT or prime.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("prime feasibility baseline planner is not current")
    if prime.get("prime_notation_contract") != PRIME_CONTRACT:
        raise RuntimeError("prime diagnostic contract drift")
    if prime.get("baseline_json_sha256") != _sha_file(baseline_path):
        raise RuntimeError("prime stress does not bind to the supplied numeric baseline")
    if int(prime.get("prime_bearing_unit_count") or -1) != 17:
        raise RuntimeError("pinned Opticks prime inventory drift")

    run_id = os.environ.get("ROCKETDICT_BASELINE_RUN_ID", "")
    artifact_id = os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID", "")
    artifact_digest = os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_DIGEST", "")
    if run_id != EXPECTED_BASELINE_RUN_ID or artifact_id != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("prime feasibility workflow baseline run/artifact identity drift")
    if artifact_digest != EXPECTED_BASELINE_ARTIFACT_DIGEST:
        raise RuntimeError("prime feasibility workflow baseline artifact digest drift")

    ordinary_rows = [
        dict(row)
        for row in list(prime.get("prime_units") or [])
        if not bool(row.get("production_table_composite"))
    ]
    if len(ordinary_rows) != 16:
        raise RuntimeError(f"pinned Opticks ordinary prime-unit inventory drift: {len(ordinary_rows)} != 16")

    punctuation_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("punctuation") or {})
    length_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("length_ratio") or {})
    max_decoding_length = int(prime.get("max_decoding_length") or 512)
    translator = OpusTranslator(device="cpu", compute_type="float32")

    canonical_inputs = [_unicode_prime_model_input(str(row["source_text"])) for row in ordinary_rows]
    canonical_generated = _translate_batches(
        translator,
        canonical_inputs,
        beam_size=int(CANONICAL_GENERATION["beam_size"]),
        num_hypotheses=int(CANONICAL_GENERATION["num_hypotheses"]),
        max_decoding_length=max_decoding_length,
    )

    structural_jobs, structural_refs, structural_plans = _structural_jobs(ordinary_rows)
    structural_generated = _translate_batches(
        translator,
        structural_jobs,
        beam_size=int(STRUCTURAL_GENERATION["beam_size"]),
        num_hypotheses=int(STRUCTURAL_GENERATION["num_hypotheses"]),
        max_decoding_length=max_decoding_length,
    ) if structural_jobs else []
    structural_by_sequence: dict[int, dict[int, dict[str, Any]]] = {
        int(row["planned_sequence"]): {} for row in ordinary_rows
    }
    for (sequence, part_index), hypotheses in zip(structural_refs, structural_generated, strict=True):
        if not hypotheses:
            raise RuntimeError(f"OPUS returned no structural prose hypothesis for {sequence}:{part_index}")
        structural_by_sequence[sequence][part_index] = dict(hypotheses[0])

    database_sha_before = _sha_file(database)
    results: list[dict[str, Any]] = []
    canonical_rank0_success = 0
    canonical_nbest_success = 0
    structural_success = 0
    baseline_success = 0
    baseline_failure_rescued_canonical: list[int] = []
    baseline_failure_rescued_structural: list[int] = []

    for row, model_input, hypotheses in zip(ordinary_rows, canonical_inputs, canonical_generated, strict=True):
        source_row = _source_row(row)
        sequence = int(row["planned_sequence"])
        baseline_target = str(row["rank0_target_text"])
        baseline_verdict = dict(row.get("strict_verdict") or {})
        if baseline_verdict.get("strictly_eligible") is True:
            baseline_success += 1

        canonical_candidates: list[dict[str, Any]] = []
        canonical_selected: dict[str, Any] | None = None
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
            canonical_candidates.append(candidate)
            if canonical_selected is None and verdict.get("strictly_eligible") is True:
                canonical_selected = candidate
        if canonical_candidates and canonical_candidates[0]["verdict"].get("strictly_eligible") is True:
            canonical_rank0_success += 1
        if canonical_selected is not None:
            canonical_nbest_success += 1
            if baseline_verdict.get("strictly_eligible") is not True:
                baseline_failure_rescued_canonical.append(sequence)

        structural_target, structural_parts = _compose_structural(
            structural_plans[sequence], structural_by_sequence[sequence]
        )
        structural_verdict = _verdict(
            source_row,
            structural_target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        if structural_verdict.get("strictly_eligible") is True:
            structural_success += 1
            if baseline_verdict.get("strictly_eligible") is not True:
                baseline_failure_rescued_structural.append(sequence)

        results.append(
            {
                "planned_sequence": sequence,
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "baseline_target_text": baseline_target,
                "baseline_strictly_eligible": baseline_verdict.get("strictly_eligible") is True,
                "unicode_prime_model_input": model_input,
                "unicode_prime_model_input_changed": model_input != str(row["source_text"]),
                "canonical_candidates": canonical_candidates,
                "canonical_selected": canonical_selected,
                "structural_target_text": structural_target,
                "structural_parts": structural_parts,
                "structural_prime_notation": compare_numeric_prime_notation(
                    str(row["source_text"]), structural_target
                ),
                "structural_verdict": structural_verdict,
            }
        )

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("prime feasibility inference mutated the retained Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-Opticks source-side prime-notation mechanism comparison over immutable planner-v8 evidence",
        "promotion_allowed": False,
        "product_gate_changed": False,
        "no_placeholders": True,
        "no_target_rewriting": True,
        "no_post_translation_literal_injection": True,
        "all_source_alphabetic_content_through_real_mt": True,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "prime_notation_contract": PRIME_CONTRACT,
        "baseline_run_id": run_id,
        "baseline_artifact_id": artifact_id,
        "baseline_artifact_digest": artifact_digest,
        "baseline_numeric_json_sha256": _sha_file(baseline_path),
        "baseline_prime_json_sha256": _sha_file(prime_path),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "ordinary_prime_unit_count": len(ordinary_rows),
        "baseline_strict_success_count": baseline_success,
        "baseline_strict_failure_count": len(ordinary_rows) - baseline_success,
        "canonical_generation": dict(CANONICAL_GENERATION),
        "canonical_rank0_strict_success_count": canonical_rank0_success,
        "canonical_nbest_strict_success_count": canonical_nbest_success,
        "canonical_nbest_strict_failure_count": len(ordinary_rows) - canonical_nbest_success,
        "baseline_failure_rescued_canonical_sequences": baseline_failure_rescued_canonical,
        "structural_generation": dict(STRUCTURAL_GENERATION),
        "structural_strict_success_count": structural_success,
        "structural_strict_failure_count": len(ordinary_rows) - structural_success,
        "baseline_failure_rescued_structural_sequences": baseline_failure_rescued_structural,
        "max_decoding_length": max_decoding_length,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)

    output_root = Path(
        os.environ.get("ROCKETDICT_PRIME_FEASIBILITY_ROOT", "work/prime-feasibility")
    ).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-prime-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "ordinary_prime_unit_count",
                    "baseline_strict_success_count",
                    "canonical_rank0_strict_success_count",
                    "canonical_nbest_strict_success_count",
                    "structural_strict_success_count",
                    "baseline_failure_rescued_canonical_sequences",
                    "baseline_failure_rescued_structural_sequences",
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
