from __future__ import annotations

"""Read-only feasibility audit for a narrow TC-big delimiter-hallucination rescue.

Trigger: an exact, row-aligned source-defined Stage10 context whose *current*
run-9 aggregate target adds one or more (), [], or {} delimiter characters not
present in the immutable source. Candidate: an unmodified raw TC-big hypothesis
already persisted by the whole-context audit. It must be strict-clean,
numeric-clean, Gutenberg-emphasis-safe, remove the target-only delimiter debt,
and retain a conservative source-relative alphabetic coverage ratio.

This intentionally does not use the old ``candidate alpha >= baseline alpha``
rule: hallucinated baseline text can be longer precisely because it contains
invented material. The replacement remains research-only until a persisted
Product implementation proves the same contract.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-tc-big-target-delimiter-context-rescue-feasibility/1"
INPUT_SCHEMA = "rocketdict-full-opticks-alternative-mt-hard-contexts-run9/2"
INPUT_FILE_SHA256 = "49d679789207440d5160f044944f4261cc957070462f0cce464e047c955878d3"
INPUT_EVIDENCE_SHA256 = "9309a2b0d4ed4cf84b4f2efc9a6353cc191a98b2557c26aa19fbc1489c3a0a55"
DB_SHA256 = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN9_ID = 9
BASE_COUNTS = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
DELIMITERS = "()[]{}"
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _added_delimiters(source: str, target: str) -> dict[str, int]:
    return {char: target.count(char) - source.count(char) for char in DELIMITERS if target.count(char) > source.count(char)}


def _alpha_ratio(source: str, target: str) -> float:
    source_alpha = sum(ch.isalpha() for ch in source)
    target_alpha = sum(ch.isalpha() for ch in target)
    if source_alpha <= 0:
        return 1.0 if target_alpha == 0 else float("inf")
    return target_alpha / source_alpha


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"numeric_symbol": 0, "punctuation": 0, "length": 0, "unique": 0}
    for row in rows:
        verdict = evaluate_rescue_pair(str(row["source_text"]), str(row["target_text"]))
        flags = {
            "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key in ("numeric_symbol", "punctuation", "length"):
            out[key] += int(flags[key])
        out["unique"] += int(any(flags.values()))
    return out


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_TC_BIG_DELIMITER_CONTEXT_ROOT", "work/tc-big-delimiter-context")).resolve()
    evidence_path = root / "full-opticks-alternative-mt-hard-contexts-run9.json"
    database = root / "rocketdict.sqlite"
    if _sha(evidence_path) != INPUT_FILE_SHA256 or _sha(database) != DB_SHA256:
        raise RuntimeError("immutable input identity drift")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("schema") != INPUT_SCHEMA or evidence.get("evidence_sha256") != INPUT_EVIDENCE_SHA256:
        raise RuntimeError("context evidence identity drift")

    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in con.execute("SELECT * FROM run_items WHERE run_id=? AND kind='translation_segment' ORDER BY sequence_number", (RUN9_ID,))]
    finally:
        con.close()
    if _inventory(rows) != BASE_COUNTS:
        raise RuntimeError(f"run9 inventory drift: {_inventory(rows)!r}")

    replacements: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for case in evidence["cases"]:
        source = str(case["source_text"])
        baseline = case.get("baseline_target_text")
        additions = _added_delimiters(source, str(baseline or "")) if isinstance(baseline, str) else {}
        triggered = case.get("replacement_row_aligned") is True and bool(additions)
        attempt = {
            "case_id": str(case["case_id"]),
            "source_start": int(case["source_start"]),
            "source_end": int(case["source_end"]),
            "hard_sequences": list(case.get("hard_sequences") or []),
            "member_sequences": list(case.get("member_sequences") or []),
            "replacement_row_aligned": case.get("replacement_row_aligned") is True,
            "baseline_target_only_delimiter_additions": additions,
            "triggered": triggered,
            "selected_rank": None,
            "selected_target": None,
            "selected_source_alpha_ratio": None,
            "candidate_diagnostics": [],
        }
        if triggered:
            for hypothesis in case.get("hypotheses") or []:
                selection = dict(hypothesis.get("context_selection") or {})
                emphasis = dict(hypothesis.get("emphasis_markup") or {})
                target = str(hypothesis.get("target_text") or "")
                ratio = _alpha_ratio(source, target)
                candidate_additions = _added_delimiters(source, target)
                eligible = (
                    selection.get("strict_clean") is True
                    and selection.get("numeric_clean") is True
                    and emphasis.get("passed") is True
                    and not candidate_additions
                    and MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
                )
                diag = {
                    "rank": int(hypothesis["rank"]),
                    "strict_clean": selection.get("strict_clean") is True,
                    "numeric_clean": selection.get("numeric_clean") is True,
                    "emphasis_passed": emphasis.get("passed") is True,
                    "target_only_delimiter_additions": candidate_additions,
                    "source_alpha_ratio": ratio,
                    "source_alpha_ratio_in_range": MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO,
                    "eligible": eligible,
                    "target_text": target,
                }
                attempt["candidate_diagnostics"].append(diag)
                if attempt["selected_rank"] is None and eligible:
                    attempt["selected_rank"] = int(hypothesis["rank"])
                    attempt["selected_target"] = target
                    attempt["selected_source_alpha_ratio"] = ratio
            if attempt["selected_rank"] is not None:
                replacements.append(attempt)
        attempts.append(attempt)

    replaced_sequences = {int(seq) for rep in replacements for seq in rep["member_sequences"]}
    candidate_rows = [dict(row) for row in rows if int(row["sequence_number"]) not in replaced_sequences]
    for rep in replacements:
        source = next(str(case["source_text"]) for case in evidence["cases"] if case["case_id"] == rep["case_id"])
        candidate_rows.append({
            "sequence_number": -1,
            "source_start": int(rep["source_start"]),
            "source_end": int(rep["source_end"]),
            "source_text": source,
            "target_text": str(rep["selected_target"]),
        })
    candidate_rows.sort(key=lambda row: int(row["source_start"]))
    content = "".join(str(row["source_text"]) for row in rows)
    if "".join(str(row["source_text"]) for row in candidate_rows) != content:
        raise RuntimeError("delimiter-context counterfactual source coverage drift")
    upper = _inventory(candidate_rows)
    if any(upper[key] > BASE_COUNTS[key] for key in BASE_COUNTS):
        raise RuntimeError(f"delimiter-context mechanical regression: {upper!r}")
    if _sha(database) != DB_SHA256:
        raise RuntimeError("read-only feasibility mutated database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only feasibility for source-defined whole-context TC-big rescue of current target-only delimiter additions",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "input_evidence_file_sha256": INPUT_FILE_SHA256,
        "input_evidence_sha256": INPUT_EVIDENCE_SHA256,
        "run9_database_sha256": DB_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "selector": {
            "trigger": "row_aligned_context_with_current_target_only_()[]{}_delimiter_addition",
            "candidate_requires_strict_clean": True,
            "candidate_requires_numeric_clean": True,
            "candidate_requires_emphasis_preservation": True,
            "candidate_requires_no_target_only_delimiter_additions": True,
            "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
            "baseline_target_alpha_non_decrease_required": False,
        },
        "triggered_context_count": sum(int(a["triggered"]) for a in attempts),
        "accepted_context_count": len(replacements),
        "accepted_contexts": [rep["case_id"] for rep in replacements],
        "attempts": attempts,
        "mechanical_upper_bound_hard_gate_counts": upper,
        "database_mutated": False,
        "source_coverage_byte_exact": True,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    out = root / "full-opticks-tc-big-target-delimiter-context-rescue-feasibility.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "triggered_context_count": payload["triggered_context_count"],
        "accepted_context_count": payload["accepted_context_count"],
        "accepted_contexts": payload["accepted_contexts"],
        "mechanical_upper_bound_hard_gate_counts": upper,
        "evidence_sha256": payload["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
