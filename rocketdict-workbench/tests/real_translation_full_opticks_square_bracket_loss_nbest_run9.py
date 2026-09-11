from __future__ import annotations

"""Research-only raw OPUS n-best screening for non-block square-bracket losses."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-square-bracket-loss-nbest-run9/1"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
RUN_OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
SEQUENCES = [325, 650, 1321, 1757]
STARTS = [54796, 112541, 228046, 301051]


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    unique: set[int] = set()
    for row in sorted(rows, key=lambda value: int(value["sequence_number"])):
        verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        sequence = int(row["sequence_number"])
        failures = {
            "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key, failed in failures.items():
            if failed:
                counts[key] += 1
                unique.add(sequence)
    return {**counts, "unique": len(unique)}


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_SQUARE_BRACKET_NBEST_ROOT", "work/square-bracket-loss-nbest-run9")).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != DB_SHA:
        raise RuntimeError("run9 database identity drift")
    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN_ID)
        rows = get_run_items(connection, RUN_ID, kind="translation_segment")
        document = get_document(connection, int(dict(run.get("output") or {})["document_version_id"]))
    if str(run.get("output_sha256") or "") != RUN_OUTPUT_SHA or str(document.get("text_sha256") or "") != TEXT_SHA:
        raise RuntimeError("run9 identity drift")
    content = str(document["content_text"])
    rows = sorted(rows, key=lambda value: int(value["sequence_number"]))
    if "".join(str(row.get("source_text") or "") for row in rows) != content or _inventory(rows) != BASE:
        raise RuntimeError("run9 coverage/gate drift")
    by_sequence = {int(row["sequence_number"]): row for row in rows}
    cohort = [by_sequence[sequence] for sequence in SEQUENCES]
    if [int(row["source_start"]) for row in cohort] != STARTS:
        raise RuntimeError("square-bracket cohort span drift")
    for row in cohort:
        source, target = str(row.get("source_text") or ""), str(row.get("target_text") or "")
        if source.count("[") == target.count("[") and source.count("]") == target.count("]"):
            raise RuntimeError(f"square-bracket trigger unexpectedly clean seq {row['sequence_number']}")
        if source.count("[") == 0 or source.count("]") == 0:
            raise RuntimeError(f"square-bracket source payload missing seq {row['sequence_number']}")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate([str(row.get("source_text") or "") for row in cohort], beam_size=6, num_hypotheses=6, max_decoding_length=768)
    if len(generated) != len(cohort) or any(len(group) != 6 for group in generated):
        raise RuntimeError("square-bracket n-best cardinality drift")

    replacements: dict[int, dict[str, Any]] = {}
    cases: list[dict[str, Any]] = []
    for row, hypotheses in zip(cohort, generated, strict=True):
        source = str(row.get("source_text") or "")
        candidates: list[dict[str, Any]] = []
        first: int | None = None
        for rank, hypothesis in enumerate(hypotheses):
            target = str(hypothesis.get("text") or "")
            verdict = evaluate_rescue_pair(source, target)
            emphasis = compare_emphasis_markup_preservation(source, target)
            admissible = verdict.get("strictly_eligible") is True and emphasis.get("passed") is True
            candidates.append({"rank": rank, "target_text": target, "score": hypothesis.get("score"), "verdict": verdict, "emphasis_markup": emphasis, "mechanically_admissible": admissible})
            if first is None and admissible:
                first = rank
        if first is not None:
            replacements[int(row["id"])] = {**dict(row), "target_text": candidates[first]["target_text"]}
        cases.append({
            "sequence_number": int(row["sequence_number"]),
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": source,
            "base_target_text": str(row.get("target_text") or ""),
            "candidates": candidates,
            "first_mechanically_admissible_rank": first,
            "first_mechanically_admissible_target": None if first is None else candidates[first]["target_text"],
        })

    candidate_rows = [dict(replacements.get(int(row["id"]), row)) for row in rows]
    for sequence, row in enumerate(candidate_rows):
        row["sequence_number"] = sequence
    if "".join(str(row.get("source_text") or "") for row in candidate_rows) != content:
        raise RuntimeError("square-bracket counterfactual source coverage drift")
    counterfactual = _inventory(candidate_rows)
    if any(counterfactual[key] > BASE[key] for key in BASE):
        raise RuntimeError(f"square-bracket counterfactual regression: {counterfactual!r}")
    if _sha(database) != DB_SHA:
        raise RuntimeError("square-bracket research mutated run9 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only exact-source raw OPUS n-best screening for current non-block square-bracket losses",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": RUN_OUTPUT_SHA,
        "attempted_sequences": SEQUENCES,
        "attempted_source_starts": STARTS,
        "selected_sequences": [case["sequence_number"] for case in cases if case["first_mechanically_admissible_rank"] is not None],
        "base_hard_gate_counts": BASE,
        "counterfactual_hard_gate_counts": counterfactual,
        "cases": cases,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    out = root / "full-opticks-square-bracket-loss-nbest-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": SCHEMA, "selected_sequences": payload["selected_sequences"], "counterfactual_hard_gate_counts": counterfactual, "evidence_sha256": payload["evidence_sha256"]}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
