from __future__ import annotations

"""Research-only full-Opticks DOE for compact algebraic notation.

The immutable Product source/unit is unchanged. For ordinary Stage12 units with
compact coefficient expressions immediately followed by an uppercase variable
(``3/8A``, ``((61-1/2)/8)A``), only the *model input* receives deterministic
operator spacing such as ``3 / 8 A`` and ``((61 - 1 / 2) / 8) A``. The whole
linguistic context remains in one real-OPUS request.

Raw hypotheses are evaluated against the original source with the unchanged
strict verdict. No source storage mutation, placeholder, target rewriting,
post-translation literal injection, or Product-gate change is permitted.
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

SCHEMA = "rocketdict-full-opticks-formula-spacing-feasibility/1"
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
BATCH_SIZE = 8
# Narrow source-defined algebra token: a numeric expression containing a
# division sign, optionally parenthesized/nested, followed by one uppercase
# variable. The corpus inventory is asserted below rather than patched by span.
_ALGEBRA_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<expr>(?:\(\([0-9+\-/]+\)/[0-9]+\)|[0-9]+(?:-[0-9]+/[0-9]+)?/[0-9]+))(?P<var>[A-Z])(?![A-Za-z0-9_])"
)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def formula_spacing_model_input(text: str) -> tuple[str, list[dict[str, Any]]]:
    matches = list(_ALGEBRA_TOKEN_RE.finditer(text))
    if not matches:
        raise ValueError("formula spacing requires a compact algebra token")
    output: list[str] = []
    evidence: list[dict[str, Any]] = []
    cursor = 0
    for match in matches:
        expr = match.group("expr")
        variable = match.group("var")
        spaced = re.sub(r"\s*([+\-/])\s*", r" \1 ", expr)
        canonical = spaced + " " + variable
        output.append(text[cursor:match.start()])
        output.append(canonical)
        evidence.append(
            {
                "source_text": match.group(0),
                "canonical_model_input_text": canonical,
                "source_start": match.start(),
                "source_end": match.end(),
            }
        )
        cursor = match.end()
    output.append(text[cursor:])
    return "".join(output), evidence


def _translate_batches(translator: OpusTranslator, texts: list[str], *, beam_size: int, num_hypotheses: int, max_decoding_length: int) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(translator.translate(texts[start:start+BATCH_SIZE], beam_size=beam_size, num_hypotheses=num_hypotheses, max_decoding_length=max_decoding_length))
    if len(output) != len(texts):
        raise RuntimeError("formula-spacing translation cardinality mismatch")
    return output


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-artifact/full-opticks-numeric-stress")).resolve()
    output_root = Path(os.environ.get("ROCKETDICT_FORMULA_FEASIBILITY_ROOT", "work/formula-feasibility")).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks evidence is incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA or baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("full-Opticks baseline identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("formula-spacing baseline planner is not current")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID or os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline run/artifact identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_DIGEST") != EXPECTED_BASELINE_ARTIFACT_DIGEST:
        raise RuntimeError("baseline artifact digest drift")

    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    with connect(database, readonly=True) as connection:
        persisted = get_run_items(connection, translation_run_id, kind="translation_segment")
    rows: list[dict[str, Any]] = []
    for item in persisted:
        source = str(item.get("source_text") or "")
        if not _ALGEBRA_TOKEN_RE.search(source):
            continue
        payload = dict(item.get("payload") or {})
        if any(isinstance(payload.get(key), dict) for key in ("table", "structural_label", "block_section_identifier")):
            continue
        model_input, canonicalization = formula_spacing_model_input(source)
        rows.append({
            "sequence_number": int(item["sequence_number"]),
            "source_start": int(item["source_start"]),
            "source_end": int(item["source_end"]),
            "source_text": source,
            "baseline_target_text": str(item.get("target_text") or ""),
            "model_input": model_input,
            "canonicalization": canonicalization,
        })
    if len(rows) != 1:
        raise RuntimeError(f"pinned Opticks compact-algebra inventory drift: {len(rows)} != 1")

    failure_sequences = {int(row["planned_sequence"]) for row in list(baseline.get("numeric_failures") or [])}
    row = rows[0]
    sequence = int(row["sequence_number"])
    if sequence not in failure_sequences:
        raise RuntimeError("pinned compact-algebra unit is no longer a Product numeric failure")

    punctuation_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("punctuation") or {})
    length_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("length_ratio") or {})
    max_decoding_length = max(512, int(baseline.get("max_planned_unit_tokens") or 64) * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    database_sha_before = _sha_file(database)

    source_row = {"sequence_number": sequence, "source_start": int(row["source_start"]), "source_end": int(row["source_end"]), "source_text": str(row["source_text"]), "target_text": None}
    cells: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for cell in GENERATION_CELLS:
        generated = _translate_batches(translator, [str(row["model_input"])], beam_size=int(cell["beam_size"]), num_hypotheses=int(cell["num_hypotheses"]), max_decoding_length=max_decoding_length)[0]
        candidates: list[dict[str, Any]] = []
        chosen: dict[str, Any] | None = None
        for model_index, hypothesis in enumerate(generated):
            target = str(hypothesis.get("text") or "")
            verdict = _verdict(source_row, target, punctuation_parameters=punctuation_parameters, length_parameters=length_parameters)
            candidate = {"model_index": model_index, "rank": int(hypothesis.get("rank") if hypothesis.get("rank") is not None else model_index), "score": hypothesis.get("score"), "target_text": target, "verdict": verdict}
            candidates.append(candidate)
            if chosen is None and verdict.get("strictly_eligible") is True:
                chosen = candidate
        cells.append({"generation": dict(cell), "candidate_count": len(candidates), "strictly_eligible_count": sum(1 for candidate in candidates if candidate["verdict"].get("strictly_eligible") is True), "selected_rank": None if chosen is None else int(chosen["rank"]), "candidates": candidates})
        if chosen is not None:
            selected = {"generation": dict(cell), **chosen}
            break

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("formula-spacing research mutated retained Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "whole-unit source-side operator spacing for the complete pinned compact-algebra class",
        "promotion_allowed": False,
        "product_gate_changed": False,
        "immutable_source_changed": False,
        "model_input_spacing_only": True,
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
        "inventory_count": 1,
        "planned_sequence": sequence,
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row["source_text"]),
        "baseline_target_text": str(row["baseline_target_text"]),
        "model_input": str(row["model_input"]),
        "canonicalization": list(row["canonicalization"]),
        "cells": cells,
        "selected": selected,
        "rescued": selected is not None,
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-formula-spacing-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": SCHEMA, "planned_sequence": sequence, "rescued": selected is not None, "selected_rank": None if selected is None else selected["rank"], "selected_generation": None if selected is None else selected["generation"], "evidence_sha256": payload["evidence_sha256"]}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
