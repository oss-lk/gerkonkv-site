from __future__ import annotations

"""Re-score stored full-Opticks raw n-best selections for numeric prime notation.

This is a read-only research audit. It does not re-run OPUS, change Product
hard gates, rewrite target text, or mutate any database. It adds one
conservative diagnostic for numeric prime marks (minutes/seconds/thirds style)
that current numeric-v4 does not model separately from apostrophe decimals.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from rocketdict.prime_notation import CONTRACT, compare_numeric_prime_notation

SCHEMA = "rocketdict-full-opticks-prime-notation-rescore/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/2"
ESCALATION_SCHEMA = "rocketdict-full-opticks-nbest-escalation/1"
SOURCE_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _audit_selected(
    rows: list[dict[str, Any]],
    *,
    selected_key: str,
    target_key: str,
) -> tuple[list[int], list[int], list[dict[str, Any]]]:
    prior: list[int] = []
    safe: list[int] = []
    invalidated: list[dict[str, Any]] = []
    for row in rows:
        selected = row.get(selected_key)
        if not isinstance(selected, dict):
            continue
        sequence = int(row["planned_sequence"])
        target = str(selected.get(target_key) or "")
        prior.append(sequence)
        prime = compare_numeric_prime_notation(str(row.get("source_text") or ""), target)
        if prime["passed"] is True:
            safe.append(sequence)
        else:
            invalidated.append(
                {
                    "planned_sequence": sequence,
                    "source_text": str(row.get("source_text") or ""),
                    "selected_target_text": target,
                    "selected_rank": int(selected.get("rank") or 0),
                    "prime_notation": prime,
                }
            )
    return prior, safe, invalidated


def _summary_text(
    *,
    beam6_prior: list[int],
    beam6_invalidated: list[dict[str, Any]],
    staged_prior: list[int],
    staged_invalidated: list[dict[str, Any]],
    residual_prime_rows: list[dict[str, Any]],
) -> str:
    return (
        "prime-notation rescore audited "
        f"{len(beam6_prior)} beam6 and {len(staged_prior)} staged selected rescues; "
        f"invalidated {len(beam6_invalidated)} beam6 and {len(staged_invalidated)} staged rescues; "
        f"{len(residual_prime_rows)} unresolved staged residuals contain numeric prime notation"
    )


def rescore(baseline_path: Path, escalation_path: Path) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    escalation = json.loads(escalation_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"Unexpected baseline schema: {baseline.get('schema')!r}")
    if escalation.get("schema") != ESCALATION_SCHEMA:
        raise RuntimeError(f"Unexpected escalation schema: {escalation.get('schema')!r}")
    if baseline.get("source_sha256") != SOURCE_SHA256 or escalation.get("source_sha256") != SOURCE_SHA256:
        raise RuntimeError("Pinned Opticks identity drift")
    if baseline.get("no_synthetic_target_repair") is not True:
        raise RuntimeError("Baseline no-repair invariant missing")
    if escalation.get("no_post_translation_literal_injection") is not True:
        raise RuntimeError("Escalation no-literal-injection invariant missing")

    beam6_prior, beam6_safe, beam6_invalidated = _audit_selected(
        list(baseline.get("numeric_failures") or []),
        selected_key="selected_strict_candidate",
        target_key="target_text",
    )
    staged_prior, staged_safe, staged_invalidated = _audit_selected(
        list(escalation.get("results") or []),
        selected_key="selected",
        target_key="target_text",
    )

    residual_prime_rows: list[dict[str, Any]] = []
    baseline_failures = {
        int(row["planned_sequence"]): row
        for row in list(baseline.get("numeric_failures") or [])
    }
    for sequence in escalation.get("residual_sequences") or []:
        row = baseline_failures[int(sequence)]
        prime = compare_numeric_prime_notation(
            str(row.get("source_text") or ""),
            str(row.get("rank0_target_text") or ""),
        )
        if prime["source_signature"] or prime["target_signature"]:
            residual_prime_rows.append(
                {
                    "planned_sequence": int(sequence),
                    "source_text": str(row.get("source_text") or ""),
                    "rank0_target_text": str(row.get("rank0_target_text") or ""),
                    "prime_notation": prime,
                }
            )

    beam6_invalidated_sequences = [
        int(row["planned_sequence"]) for row in beam6_invalidated
    ]
    staged_invalidated_sequences = [
        int(row["planned_sequence"]) for row in staged_invalidated
    ]
    residual_prime_sequences = [
        int(row["planned_sequence"]) for row in residual_prime_rows
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only conservative prime-notation audit of already generated full-Opticks n-best selections",
        "promotion_allowed": False,
        "mt_rerun": False,
        "product_gate_changed": False,
        "target_rewriting": False,
        "source_sha256": SOURCE_SHA256,
        "baseline_json_sha256": _sha(baseline_path),
        "escalation_json_sha256": _sha(escalation_path),
        "prime_notation_contract": CONTRACT,
        "beam6_prior_strict_rescue_count": len(beam6_prior),
        "beam6_prior_strict_rescue_sequences": beam6_prior,
        "beam6_prime_safe_rescue_count": len(beam6_safe),
        "beam6_prime_safe_rescue_sequences": beam6_safe,
        "beam6_invalidated_count": len(beam6_invalidated),
        "beam6_invalidated_sequences": beam6_invalidated_sequences,
        "beam6_invalidated": beam6_invalidated,
        "staged_prior_strict_rescue_count": len(staged_prior),
        "staged_prior_strict_rescue_sequences": staged_prior,
        "staged_prime_safe_rescue_count": len(staged_safe),
        "staged_prime_safe_rescue_sequences": staged_safe,
        "staged_invalidated_count": len(staged_invalidated),
        "staged_invalidated_sequences": staged_invalidated_sequences,
        "staged_invalidated": staged_invalidated,
        "residual_prime_notation_count": len(residual_prime_rows),
        "residual_prime_notation_sequences": residual_prime_sequences,
        "residual_prime_notation": residual_prime_rows,
        "conclusion": _summary_text(
            beam6_prior=beam6_prior,
            beam6_invalidated=beam6_invalidated,
            staged_prior=staged_prior,
            staged_invalidated=staged_invalidated,
            residual_prime_rows=residual_prime_rows,
        ),
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("escalation", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = rescore(
        args.baseline.expanduser().resolve(),
        args.escalation.expanduser().resolve(),
    )
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "beam6_prior_strict_rescue_count": payload["beam6_prior_strict_rescue_count"],
                "beam6_prime_safe_rescue_count": payload["beam6_prime_safe_rescue_count"],
                "beam6_invalidated_sequences": payload["beam6_invalidated_sequences"],
                "staged_prior_strict_rescue_count": payload["staged_prior_strict_rescue_count"],
                "staged_prime_safe_rescue_count": payload["staged_prime_safe_rescue_count"],
                "staged_invalidated_sequences": payload["staged_invalidated_sequences"],
                "residual_prime_notation_sequences": payload["residual_prime_notation_sequences"],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
