from __future__ import annotations

"""Narrow post-composition audit of numeric-hard-failure whole-context candidates.

The upstream composed residual audit proves exact current-primary lineage against
an immutable canonical whole-context shadow and recomputes the existing strict
selector.  This follow-up intentionally narrows that evidence further:

* only contexts with an already-existing maintained numeric/symbol hard failure;
* only lineage-exact candidates accepted by the existing strict selector; and
* only candidates that preserve Gutenberg underscore-emphasis markup shape.

The emphasis check is a conservative veto motivated by a real semantic loss in
context 2725, where a mechanically clean whole-context candidate drops the
source phrase ``_per deliquium_``.  Passing this audit is still not semantic
proof and does not authorize Product promotion or default selection.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.emphasis_markup import (
    EMPHASIS_MARKUP_CONTRACT,
    compare_emphasis_markup_preservation,
)
from rocketdict.translation_rescue import SELECTOR_CONTRACT

SCHEMA = "rocketdict-full-opticks-numeric-whole-context-candidate-audit/1"
RESIDUAL_SCHEMA = "rocketdict-full-opticks-composed-whole-context-residual-audit/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_COMPOSED_RESIDUAL_ROOT",
            "work/composed-whole-context-residual",
        )
    ).resolve()
    residual_path = root / "full-opticks-composed-whole-context-residual-audit.json"
    if not residual_path.is_file():
        raise RuntimeError("Composed whole-context residual audit is missing")
    residual = json.loads(residual_path.read_text(encoding="utf-8"))
    if residual.get("schema") != RESIDUAL_SCHEMA:
        raise RuntimeError(f"Unexpected residual schema: {residual.get('schema')!r}")
    if residual.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")
    if residual.get("selector_contract") != SELECTOR_CONTRACT:
        raise RuntimeError("Residual selector contract drift")
    if residual.get("source_coverage_byte_exact") is not True:
        raise RuntimeError("Residual source-coverage proof is missing")
    if residual.get("database_unchanged") is not True:
        raise RuntimeError("Residual read-only database proof is missing")

    current_counts = dict(residual.get("current_hard_gate_counts") or {})
    required_count_keys = {"numeric", "punctuation", "length", "unique"}
    if set(current_counts) != required_count_keys:
        raise RuntimeError(f"Unexpected current hard-gate count keys: {sorted(current_counts)}")

    mechanical_numeric: list[int] = []
    emphasis_rejected: list[int] = []
    conservative: list[int] = []
    review: list[dict[str, Any]] = []
    eliminated_gate_events = {"numeric": 0, "punctuation": 0, "length": 0}
    eliminated_unique_sequences: set[int] = set()

    for row in list(residual.get("review_candidates") or []):
        context = int(row["context_sequence"])
        gates = {str(value) for value in row.get("hard_failure_gates") or []}
        if "numeric" not in gates:
            continue
        if row.get("status") != "lineage_exact_mechanically_accepted":
            continue

        selection = dict(row.get("recomputed_selection") or {})
        if selection.get("selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError(f"Context {context} selector contract drift")
        if selection.get("accepted") is not True:
            raise RuntimeError(
                f"Context {context} is labelled accepted but selector rejects it"
            )
        verdicts = list(selection.get("candidate_verdicts") or [])
        if len(verdicts) != 1:
            raise RuntimeError(
                f"Context {context} expected one whole-context candidate verdict"
            )
        if verdicts[0].get("product_hard_passed") is not True:
            raise RuntimeError(
                f"Context {context} mechanically accepted candidate is not Product-hard clean"
            )

        source = str(row.get("source_text") or "")
        target = str(row.get("whole_context_rank0_target") or "")
        emphasis = compare_emphasis_markup_preservation(source, target)
        mechanical_numeric.append(context)
        accepted = emphasis.get("passed") is True
        if accepted:
            conservative.append(context)
            for failure in list(row.get("hard_failures") or []):
                sequence = int(failure["segment_sequence"])
                if sequence in eliminated_unique_sequences:
                    raise RuntimeError(
                        f"Hard-failure sequence {sequence} belongs to overlapping contexts"
                    )
                eliminated_unique_sequences.add(sequence)
                for gate in set(failure.get("gates") or []):
                    if gate not in eliminated_gate_events:
                        raise RuntimeError(f"Unexpected hard-gate name {gate!r}")
                    eliminated_gate_events[gate] += 1
        else:
            emphasis_rejected.append(context)

        review.append(
            {
                "context_sequence": context,
                "hard_failure_gates": sorted(gates),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "primary_target_concatenated": str(
                    row.get("primary_target_concatenated") or ""
                ),
                "whole_context_rank0_target": target,
                "whole_context_rank0_score": row.get("whole_context_rank0_score"),
                "existing_selector_accepted": True,
                "emphasis_markup": emphasis,
                "conservative_numeric_candidate": accepted,
                "hard_failures": list(row.get("hard_failures") or []),
            }
        )

    mechanical_numeric.sort()
    emphasis_rejected.sort()
    conservative.sort()
    if not mechanical_numeric:
        raise RuntimeError("No mechanically accepted numeric residual candidates found")
    if set(emphasis_rejected) & set(conservative):
        raise RuntimeError("Candidate cannot be both accepted and emphasis-rejected")
    if sorted(emphasis_rejected + conservative) != mechanical_numeric:
        raise RuntimeError("Conservative candidate partition is incomplete")

    counterfactual_counts = {
        "numeric": int(current_counts["numeric"]) - eliminated_gate_events["numeric"],
        "punctuation": int(current_counts["punctuation"])
        - eliminated_gate_events["punctuation"],
        "length": int(current_counts["length"]) - eliminated_gate_events["length"],
        "unique": int(current_counts["unique"]) - len(eliminated_unique_sequences),
    }
    if any(value < 0 for value in counterfactual_counts.values()):
        raise RuntimeError("Conservative counterfactual produced negative hard-gate count")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only numeric-hard-failure whole-context candidate narrowing "
            "using exact composed lineage, existing strict selection, and a new "
            "conservative Gutenberg emphasis-markup veto"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(residual["source_text_sha256"]),
        "document_version_id": int(residual["document_version_id"]),
        "composed_translation_run_id": int(residual["composed_translation_run_id"]),
        "composed_translation_output_sha256": str(
            residual["composed_translation_output_sha256"]
        ),
        "residual_evidence_sha256": str(residual["evidence_sha256"]),
        "selector_contract": SELECTOR_CONTRACT,
        "emphasis_markup_contract": EMPHASIS_MARKUP_CONTRACT,
        "current_hard_gate_counts": current_counts,
        "mechanically_accepted_numeric_context_count": len(mechanical_numeric),
        "mechanically_accepted_numeric_context_sequences": mechanical_numeric,
        "emphasis_markup_rejected_context_count": len(emphasis_rejected),
        "emphasis_markup_rejected_context_sequences": emphasis_rejected,
        "conservative_numeric_candidate_context_count": len(conservative),
        "conservative_numeric_candidate_context_sequences": conservative,
        "conservative_counterfactual_eliminated_gate_events": eliminated_gate_events,
        "conservative_counterfactual_eliminated_unique_failure_count": len(
            eliminated_unique_sequences
        ),
        "conservative_counterfactual_hard_gate_counts": counterfactual_counts,
        "review_candidates": review,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)

    output = root / "full-opticks-numeric-whole-context-candidate-audit.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "mechanically_accepted_numeric_context_sequences": mechanical_numeric,
                "emphasis_markup_rejected_context_sequences": emphasis_rejected,
                "conservative_numeric_candidate_context_sequences": conservative,
                "conservative_counterfactual_hard_gate_counts": counterfactual_counts,
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
