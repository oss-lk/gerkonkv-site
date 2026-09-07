from __future__ import annotations

"""Research-only policy audit for a narrowly scoped Stage12 numeric retry.

This probe does not call MT again and does not mutate Product output.  It consumes
the frozen R1 raw n-best evidence and asks a much narrower question than the
broad feasibility probe: when rank-0 fails *only* numeric/symbol integrity while
punctuation and length gates already pass, can the fixed beam-6 raw hypotheses
repair that loss without introducing any other maintained strict failure?

Edit similarity to rank-0 is reported over several thresholds as locality
evidence, not as a semantic-quality guarantee or a Product acceptance gate.
"""

from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.research_diagnostics import OUTPUT_ARTIFACT_CONTRACT

SCHEMA = "rocketdict-maintained-r1-numeric-nbest-policy-feasibility/1"
EXPECTED_SELECTION_SHA256 = "665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32"
EXPECTED_GENERATION = {"beam_size": 6, "num_hypotheses": 6}
SIMILARITY_THRESHOLDS = (0.70, 0.80, 0.90, 0.98)


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(a=left, b=right, autojunk=False).ratio()


def _numeric_only_baseline(verdict: dict[str, Any]) -> bool:
    return bool(
        (verdict.get("numeric_symbol") or {}).get("passed") is False
        and not list(verdict.get("punctuation_issues") or [])
        and not list(verdict.get("length_issues") or [])
        and (verdict.get("delimiter_preservation") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and (verdict.get("output_artifacts") or {}).get("passed") is True
    )


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_TRANSLATION_CHALLENGE_ROOT", "work/translation-challenge")
    ).resolve()
    nbest_path = root / "maintained-r1-nbest-feasibility.json"
    if not nbest_path.is_file():
        raise RuntimeError("Numeric n-best policy probe requires R1 n-best evidence")
    nbest = json.loads(nbest_path.read_text(encoding="utf-8"))
    if nbest.get("selection_sha256") != EXPECTED_SELECTION_SHA256:
        raise RuntimeError("Frozen R1 selection identity drift")
    if ((nbest.get("contracts") or {}).get("output_artifact")) != OUTPUT_ARTIFACT_CONTRACT:
        raise RuntimeError(
            "Numeric n-best policy evidence is stale relative to maintained output-artifact semantics"
        )

    scoped: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in list(nbest.get("problem_units") or []):
        baseline = dict(row.get("baseline") or {})
        verdict = dict(baseline.get("verdict") or {})
        if _numeric_only_baseline(verdict):
            scoped.append(row)
        elif (verdict.get("numeric_symbol") or {}).get("passed") is False:
            excluded.append(
                {
                    "segment_sequence": int(row["segment_sequence"]),
                    "reason": "numeric failure is not isolated from other hard/strict concerns",
                    "punctuation_issue_count": len(list(verdict.get("punctuation_issues") or [])),
                    "length_issue_count": len(list(verdict.get("length_issues") or [])),
                    "delimiter_passed": (verdict.get("delimiter_preservation") or {}).get("passed"),
                    "critical_token_passed": (verdict.get("critical_technical_tokens") or {}).get("passed"),
                    "output_artifact_passed": (verdict.get("output_artifacts") or {}).get("passed"),
                }
            )

    results: list[dict[str, Any]] = []
    for row in scoped:
        baseline = dict(row.get("baseline") or {})
        baseline_target = str(baseline.get("target_text") or "")
        cell = next(
            (
                candidate_cell
                for candidate_cell in list(row.get("cells") or [])
                if dict(candidate_cell.get("config") or {}) == EXPECTED_GENERATION
            ),
            None,
        )
        if cell is None:
            raise RuntimeError("R1 n-best evidence lacks the fixed beam-6 generation cell")

        eligible: list[dict[str, Any]] = []
        for candidate in list(cell.get("candidates") or []):
            verdict = dict(candidate.get("verdict") or {})
            if verdict.get("strictly_eligible") is not True:
                continue
            target = str(candidate.get("target_text") or "")
            eligible.append(
                {
                    "rank": int(candidate.get("rank") or 0),
                    "score": candidate.get("score"),
                    "target_text": target,
                    "similarity_to_rank0": _similarity(baseline_target, target),
                    "verdict": verdict,
                }
            )
        eligible.sort(key=lambda candidate: int(candidate["rank"]))
        selected = eligible[0] if eligible else None
        threshold_pass = {
            f"{threshold:.2f}": bool(
                selected is not None
                and float(selected["similarity_to_rank0"]) >= threshold
            )
            for threshold in SIMILARITY_THRESHOLDS
        }
        results.append(
            {
                "segment_sequence": int(row["segment_sequence"]),
                "source_text": str(row.get("source_text") or ""),
                "rank0_target_text": baseline_target,
                "generation": dict(EXPECTED_GENERATION),
                "strictly_eligible_candidate_count": len(eligible),
                "selected": selected,
                "similarity_threshold_pass": threshold_pass,
            }
        )

    selected_sequences = [
        int(row["segment_sequence"])
        for row in results
        if row["selected"] is not None
    ]
    threshold_sequences = {
        f"{threshold:.2f}": [
            int(row["segment_sequence"])
            for row in results
            if row["similarity_threshold_pass"][f"{threshold:.2f}"] is True
        ]
        for threshold in SIMILARITY_THRESHOLDS
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "policy feasibility only; isolated numeric hard-failure raw n-best retry",
        "promotion_allowed": False,
        "no_new_mt_call": True,
        "no_synthetic_target_repair": True,
        "selection_sha256": EXPECTED_SELECTION_SHA256,
        "nbest_evidence_sha256": str(nbest.get("evidence_sha256") or ""),
        "output_artifact_contract": OUTPUT_ARTIFACT_CONTRACT,
        "generation": dict(EXPECTED_GENERATION),
        "selection_rule": (
            "scope only rank-0 numeric/symbol failures whose punctuation, length, delimiter, "
            "critical-token and output-artifact checks otherwise pass; choose the highest-ranked "
            "raw beam-6 hypothesis passing the complete strict maintained verdict"
        ),
        "similarity_is_measurement_only": True,
        "similarity_thresholds": list(SIMILARITY_THRESHOLDS),
        "numeric_only_scope_count": len(results),
        "numeric_only_scope_sequences": [int(row["segment_sequence"]) for row in results],
        "excluded_numeric_failures": excluded,
        "strictly_rescuable_sequences": selected_sequences,
        "similarity_threshold_sequences": threshold_sequences,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-numeric-nbest-policy-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "numeric_only_scope_sequences": payload["numeric_only_scope_sequences"],
                "strictly_rescuable_sequences": selected_sequences,
                "similarity_threshold_sequences": threshold_sequences,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
