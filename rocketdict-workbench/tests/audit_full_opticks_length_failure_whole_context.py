from __future__ import annotations

"""Research-only audit of whole-context rank0 for proven split length failures.

This audit consumes the immutable corpus-wide whole-context shadow.  The trigger
is not alpha gain and not a corpus-specific sequence list: at least one primary
split row must already fail the maintained length-ratio gate.  For that narrow
cohort the raw whole-context rank0 target is accepted mechanically when the
existing strict rescue evaluator passes.  Alpha non-decrease is intentionally
reported but is not an acceptance rule because the primary translation is
already proven malformed by the length gate.

No Product data or policy is changed here.  Semantic review remains mandatory.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_rescue_stage import MAX_WHOLE_CONTEXT_NLP_TOKENS
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-length-failure-whole-context/1"
TRIGGER_CONTRACT = "rocketdict-research-split-length-failure-whole-context-trigger/1"
SELECTOR_CONTRACT = "rocketdict-research-length-failure-whole-context-selector/1"
SHADOW_SCHEMA = "rocketdict-full-opticks-whole-context-shadow/2"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
SHADOW_JSON_SHA256 = "48e3966ce961b48dc931e26a12c2eaa6d97476dc94a929d246e74b67d40eb509"
SHADOW_EVIDENCE_SHA256 = "3495bdfdbab5acd8f99702a2e8912f634c7310fe7fcf027a9899ef14059c1f38"
EXPECTED_CONTEXTS = [577, 629, 919]


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_LENGTH_WHOLE_ROOT", "work/whole-context-input")
    ).resolve()
    shadow_path = root / "full-opticks-whole-context-shadow.json"
    if not shadow_path.is_file():
        raise RuntimeError(f"Whole-context shadow artifact missing: {shadow_path}")
    raw = shadow_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHADOW_JSON_SHA256:
        raise RuntimeError("Whole-context shadow JSON identity drift")
    shadow = json.loads(raw.decode("utf-8"))
    if shadow.get("schema") != SHADOW_SCHEMA:
        raise RuntimeError("Whole-context shadow schema drift")
    if shadow.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")
    if shadow.get("evidence_sha256") != SHADOW_EVIDENCE_SHA256:
        raise RuntimeError("Whole-context shadow evidence identity drift")
    if shadow.get("primary_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Whole-context planner contract drift")
    if int(shadow.get("maximum_whole_context_nlp_tokens") or 0) != MAX_WHOLE_CONTEXT_NLP_TOKENS:
        raise RuntimeError("Whole-context token cap drift")

    candidates: list[dict[str, Any]] = []
    for row in list(shadow.get("all_candidates") or []):
        primary_rows = list(row.get("primary_rows") or [])
        failing_rows: list[dict[str, Any]] = []
        for primary in primary_rows:
            verdict = evaluate_rescue_pair(
                str(primary.get("source_text") or ""),
                str(primary.get("target_text") or ""),
            )
            if verdict.get("length_passed") is not True:
                failing_rows.append(
                    {
                        "source_start": int(primary["source_start"]),
                        "source_end": int(primary["source_end"]),
                        "source_text": str(primary["source_text"]),
                        "target_text": str(primary["target_text"]),
                        "verdict": verdict,
                    }
                )
        if not failing_rows:
            continue

        source = str(row["source_text"])
        target = str(row["whole_context_rank0_target"])
        candidate_verdict = evaluate_rescue_pair(source, target)
        alpha_primary = int(row["target_alpha_primary"])
        alpha_candidate = int(row["target_alpha_candidate"])
        accepted = candidate_verdict.get("strictly_eligible") is True
        candidates.append(
            {
                "context_sequence": int(row["context_sequence"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "nlp_token_count": int(row["nlp_token_count"]),
                "source_text": source,
                "primary_rows": primary_rows,
                "primary_length_failure_rows": failing_rows,
                "primary_target_concatenated": str(row["primary_target_concatenated"]),
                "whole_context_rank0_target": target,
                "whole_context_rank0_score": row.get("whole_context_rank0_score"),
                "candidate_verdict": candidate_verdict,
                "target_alpha_primary": alpha_primary,
                "target_alpha_candidate": alpha_candidate,
                "target_alpha_delta": alpha_candidate - alpha_primary,
                "target_alpha_non_decreasing": alpha_candidate >= alpha_primary,
                "mechanically_accepted": accepted,
                "semantic_review_required": True,
            }
        )

    sequences = [row["context_sequence"] for row in candidates]
    if sequences != EXPECTED_CONTEXTS:
        raise RuntimeError(f"Length-failure whole-context cohort drift: {sequences}")
    if any(row["nlp_token_count"] > MAX_WHOLE_CONTEXT_NLP_TOKENS for row in candidates):
        raise RuntimeError("Length-failure whole-context candidate exceeds token cap")
    rejected = [row["context_sequence"] for row in candidates if not row["mechanically_accepted"]]
    if rejected:
        raise RuntimeError(f"Length-failure whole-context strict candidate regression: {rejected}")

    alpha_relaxed = [
        row["context_sequence"]
        for row in candidates
        if row["target_alpha_non_decreasing"] is False
    ]
    if alpha_relaxed != [577, 629]:
        raise RuntimeError(f"Length-trigger alpha-relaxation cohort drift: {alpha_relaxed}")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "trigger_contract": TRIGGER_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "purpose": (
            "research-only whole-context rank0 selection for split contexts whose "
            "primary translation already fails the maintained length-ratio gate"
        ),
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "shadow_json_sha256": SHADOW_JSON_SHA256,
        "shadow_evidence_sha256": SHADOW_EVIDENCE_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        "trigger_requires_primary_length_failure": True,
        "candidate_requires_existing_strict_evaluator_pass": True,
        "alpha_non_decreasing_required": False,
        "alpha_policy_reason": (
            "alpha non-decrease is not meaningful as a universal guard when the "
            "primary row is already independently proven malformed by the length gate"
        ),
        "context_count": len(candidates),
        "context_sequences": sequences,
        "mechanically_accepted_count": len(candidates),
        "alpha_relaxed_context_sequences": alpha_relaxed,
        "cases": candidates,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_written": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-length-failure-whole-context.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "context_count": len(candidates),
                "context_sequences": sequences,
                "mechanically_accepted_count": len(candidates),
                "alpha_relaxed_context_sequences": alpha_relaxed,
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
