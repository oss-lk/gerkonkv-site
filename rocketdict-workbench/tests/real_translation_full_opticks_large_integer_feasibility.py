from __future__ import annotations

"""Research-only full-Opticks DOE for large-integer preservation.

The immutable Product source and Stage12 units are unchanged. For ordinary
units containing an integer of at least seven decimal digits, the *model input
only* receives deterministic readability canonicalization:

- ungrouped/grouped decimal integers are rendered with comma thousands groups;
- ASCII ``x`` between decimal numbers is rendered as mathematical ``×``.

The full linguistic context remains in one OPUS request. Raw model hypotheses
are evaluated against the original immutable source with the unchanged strict
verdict. No placeholder, target rewriting, post-translation literal injection,
or Product-gate change is permitted. Beam 6 is tried first; beam 12/16 are
research escalation only for unresolved source-defined units.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from rocketdict.database import connect, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-large-integer-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
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
_LARGE_INTEGER_RE = re.compile(
    r"(?<![\d.,])(?P<number>(?:\d{1,3}(?:,\d{3}){2,}|\d{7,}))(?![\d.,])"
)
_NUMERIC_MULTIPLICATION_RE = re.compile(r"(?<=\d)\s+[xX]\s+(?=\d)")


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


def _canonical_integer(raw: str) -> str:
    digits = raw.replace(",", "")
    if len(digits) < 7 or not digits.isdigit():
        raise ValueError(f"not a supported large integer: {raw!r}")
    return f"{int(digits):,}"


def large_integer_model_input(text: str) -> tuple[str, list[dict[str, Any]]]:
    matches = list(_LARGE_INTEGER_RE.finditer(text))
    if not matches:
        raise ValueError("large-integer canonicalization requires a supported integer")
    output: list[str] = []
    evidence: list[dict[str, Any]] = []
    cursor = 0
    for match in matches:
        raw = match.group("number")
        canonical = _canonical_integer(raw)
        output.append(text[cursor : match.start("number")])
        output.append(canonical)
        evidence.append(
            {
                "source_text": raw,
                "canonical_model_input_text": canonical,
                "canonical_value": raw.replace(",", "").lstrip("0") or "0",
                "source_start": match.start("number"),
                "source_end": match.end("number"),
            }
        )
        cursor = match.end("number")
    output.append(text[cursor:])
    model_input = "".join(output)
    model_input = _NUMERIC_MULTIPLICATION_RE.sub(" × ", model_input)
    return model_input, evidence


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
        raise RuntimeError("large-integer translation cardinality mismatch")
    return output


def _source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence_number": int(row["sequence_number"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row["source_text"]),
        "target_text": None,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/full-opticks-artifact/full-opticks-numeric-stress",
        )
    ).resolve()
    output_root = Path(
        os.environ.get("ROCKETDICT_LARGE_INTEGER_FEASIBILITY_ROOT", "work/large-integer-feasibility")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks evidence is incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("unexpected full-Opticks baseline schema")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("large-integer baseline planner is not current")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline artifact identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_DIGEST") != EXPECTED_BASELINE_ARTIFACT_DIGEST:
        raise RuntimeError("baseline artifact digest drift")

    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    with connect(database, readonly=True) as connection:
        persisted = get_run_items(connection, translation_run_id, kind="translation_segment")
    rows: list[dict[str, Any]] = []
    for item in persisted:
        source = str(item.get("source_text") or "")
        if not _LARGE_INTEGER_RE.search(source):
            continue
        payload = dict(item.get("payload") or {})
        if isinstance(payload.get("table"), dict) or isinstance(payload.get("structural_label"), dict) or isinstance(payload.get("block_section_identifier"), dict):
            continue
        model_input, canonicalization = large_integer_model_input(source)
        rows.append(
            {
                "sequence_number": int(item["sequence_number"]),
                "source_start": int(item["source_start"]),
                "source_end": int(item["source_end"]),
                "source_text": source,
                "baseline_target_text": str(item.get("target_text") or ""),
                "model_input": model_input,
                "canonicalization": canonicalization,
            }
        )
    if not rows:
        raise RuntimeError("no ordinary large-integer units found in pinned Opticks")

    failure_sequences = {
        int(row["planned_sequence"])
        for row in list(baseline.get("numeric_failures") or [])
    }
    punctuation_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("punctuation") or {})
    length_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("length_ratio") or {})
    max_decoding_length = max(512, int(baseline.get("max_planned_unit_tokens") or 64) * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    database_sha_before = _sha_file(database)

    by_sequence = {int(row["sequence_number"]): row for row in rows}
    unresolved = sorted(by_sequence)
    selected: dict[int, dict[str, Any]] = {}
    evidence: dict[int, list[dict[str, Any]]] = {sequence: [] for sequence in unresolved}

    for cell in GENERATION_CELLS:
        if not unresolved:
            break
        generated = _translate_batches(
            translator,
            [str(by_sequence[sequence]["model_input"]) for sequence in unresolved],
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
        rescued = set(rescued_now)
        unresolved = [sequence for sequence in unresolved if sequence not in rescued]

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("large-integer research inference mutated retained Product database")

    input_failure_sequences = sorted(sequence for sequence in by_sequence if sequence in failure_sequences)
    baseline_failure_rescues = sorted(sequence for sequence in input_failure_sequences if sequence in selected)
    results = [
        {
            **row,
            "baseline_numeric_failure": int(row["sequence_number"]) in failure_sequences,
            "model_input_changed": str(row["model_input"]) != str(row["source_text"]),
            "cells": evidence[int(row["sequence_number"])],
            "selected": selected.get(int(row["sequence_number"])),
        }
        for row in rows
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-Opticks whole-unit source-side readability canonicalization for source-defined large integers",
        "promotion_allowed": False,
        "product_gate_changed": False,
        "immutable_source_changed": False,
        "model_input_numeric_formatting_only": True,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_artifact_digest": EXPECTED_BASELINE_ARTIFACT_DIGEST,
        "baseline_numeric_json_sha256": _sha_file(baseline_path),
        "generation_cells": [dict(cell) for cell in GENERATION_CELLS],
        "ordinary_large_integer_unit_count": len(rows),
        "ordinary_large_integer_sequences": sorted(by_sequence),
        "baseline_numeric_failure_count": len(input_failure_sequences),
        "baseline_numeric_failure_sequences": input_failure_sequences,
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
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-large-integer-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "schema", "ordinary_large_integer_unit_count", "baseline_numeric_failure_count",
        "strict_success_count", "baseline_failure_rescue_count", "baseline_failure_rescue_sequences",
        "residual_count", "residual_sequences", "evidence_sha256")}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
