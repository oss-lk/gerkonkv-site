from __future__ import annotations

"""Unified historical-core recovery scan with fail-closed wheel proof chains."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .core_scan import (
    MAX_DEFAULT_CANDIDATES,
    MAX_DEFAULT_DEPTH,
    RecoveryScanError,
    _atomic_write,
    _priority,
)
from .core_scan_artifacts import scan_core_artifacts
from .core_wheel_pipeline import recover_wheel_candidate

SCHEMA = "rocketdict-workbench-core-recovery-scan/6"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def scan_recovery_pipeline(
    root: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
    checkpoint_catalog: Path | str | None = None,
    probe_directories: bool = False,
    probe_wheels: bool = False,
    python: str | Path | None = None,
    max_depth: int = MAX_DEFAULT_DEPTH,
    max_candidates: int = MAX_DEFAULT_CANDIDATES,
    reports_dir: Path | str | None = None,
    wheel_timeout: float = 30.0,
) -> dict[str, Any]:
    base = scan_core_artifacts(
        root,
        target_evidence_root=target_evidence_root,
        checkpoint_catalog=checkpoint_catalog,
        probe_directories=probe_directories,
        python=python,
        max_depth=max_depth,
        max_candidates=max_candidates,
        reports_dir=reports_dir,
    )
    candidates = [dict(row) for row in (base.get("candidates") or [])]
    errors = list(base.get("errors") or [])
    wheel_pipeline_count = 0
    wheel_integrity_ok_count = 0
    wheel_runtime_attempted_count = 0
    wheel_runtime_proven_count = 0
    report_root = Path(reports_dir).expanduser().resolve() if reports_dir else None

    for row in candidates:
        if row.get("kind") != "wheel":
            continue
        wheel_pipeline_count += 1
        try:
            proof = recover_wheel_candidate(
                Path(str(row["path"])),
                target_evidence_root=target_evidence_root,
                probe_runtime=probe_wheels,
                python=python,
                timeout=wheel_timeout,
            )
        except Exception as exc:  # batch boundary: preserve bad candidate evidence
            row["wheel_recovery_status"] = "error"
            row["wheel_integrity_ok"] = False
            row["runtime_probe_ok"] = False
            row["runtime_proof_status"] = "not_run_pipeline_error"
            row["wheel_recovery_fingerprint"] = None
            errors.append(
                {
                    "path": row["path"],
                    "kind": "wheel_pipeline",
                    "type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue

        integrity = proof.get("integrity") or {}
        runtime = proof.get("runtime_probe") or {}
        if integrity.get("ok"):
            wheel_integrity_ok_count += 1
        if runtime.get("attempted"):
            wheel_runtime_attempted_count += 1
        if proof.get("runtime_proven"):
            wheel_runtime_proven_count += 1

        row["wheel_recovery"] = proof
        row["wheel_recovery_status"] = proof.get("status")
        row["wheel_recovery_fingerprint"] = (
            (proof.get("identity") or {}).get("fingerprint")
        )
        row["wheel_integrity_ok"] = bool(integrity.get("ok"))
        row["wheel_integrity_status"] = integrity.get("status")
        row["wheel_integrity_fingerprint"] = (
            (integrity.get("identity") or {}).get("fingerprint")
        )
        row["runtime_probe_ok"] = bool(proof.get("runtime_proven"))
        row["runtime_proof_status"] = runtime.get("status")
        row["runtime_probe_fingerprint"] = (
            (runtime.get("identity") or {}).get("fingerprint")
        )
        row["cross_layer_artifact_identity_consistent"] = (
            (proof.get("artifact") or {}).get("artifact_identity_consistent")
        )
        row["promotion_allowed"] = False

        if report_root is not None:
            fingerprint = str(row["wheel_recovery_fingerprint"] or "unknown")
            _atomic_write(
                report_root / f"wheel-{fingerprint[:16]}.json",
                json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
            )

    candidates.sort(key=_priority, reverse=True)
    for rank, row in enumerate(candidates, start=1):
        row["recovery_priority_rank"] = rank

    fingerprint_payload = {
        "schema": SCHEMA,
        "base_scan_schema": base.get("schema"),
        "base_scan_fingerprint": ((base.get("identity") or {}).get("fingerprint")),
        "root": base.get("root"),
        "checkpoint_catalog": base.get("checkpoint_catalog"),
        "probe_directories": probe_directories,
        "probe_wheels": probe_wheels,
        "python": str(python or sys.executable),
        "wheel_timeout": wheel_timeout,
        "candidates": [
            {key: value for key, value in row.items() if key != "recovery_priority_rank"}
            for row in candidates
        ],
        "errors": errors,
    }

    return {
        "schema": SCHEMA,
        "status": "completed",
        "promotion_allowed": False,
        "product_execution_allowed": False,
        "root": base.get("root"),
        "supported_artifact_kinds": ["directory", "zip", "wheel"],
        "discovered_candidate_count": base.get("discovered_candidate_count"),
        "discovered_wheel_count": base.get("discovered_wheel_count"),
        "analyzed_candidate_count": len(candidates),
        "error_count": len(errors),
        "probe_directories": probe_directories,
        "probe_wheels": probe_wheels,
        "wheel_pipeline_count": wheel_pipeline_count,
        "wheel_integrity_ok_count": wheel_integrity_ok_count,
        "wheel_runtime_attempted_count": wheel_runtime_attempted_count,
        "wheel_runtime_proven_count": wheel_runtime_proven_count,
        "wheel_runtime_policy": (
            "runtime_allowed_only_after_integrity_structure_plan_and_cross_layer_identity"
            if probe_wheels
            else "runtime_not_requested_full_read_only_wheel_proof_still_generated"
        ),
        "checkpoint_catalog": base.get("checkpoint_catalog"),
        "ranking_semantics": (
            "Recovery triage only. Wheel runtime evidence can improve triage rank only after "
            "package integrity and exact cross-layer artifact identity pass. No rank authorizes "
            "historical bytes as exact 0.30.40 or as Product execution proof."
        ),
        "candidates": candidates,
        "errors": errors,
        "identity": {"fingerprint": _canonical_sha(fingerprint_payload)},
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-scan",
        description=(
            "Batch historical RocketDict recovery scan with integrity-gated wheel runtime proof"
        ),
    )
    p.add_argument("root", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
    p.add_argument("--checkpoint-catalog", type=Path)
    p.add_argument("--probe-directories", action="store_true")
    p.add_argument("--probe-wheels", action="store_true")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--wheel-timeout", type=float, default=30.0)
    p.add_argument("--max-depth", type=int, default=MAX_DEFAULT_DEPTH)
    p.add_argument("--max-candidates", type=int, default=MAX_DEFAULT_CANDIDATES)
    p.add_argument("--reports-dir", type=Path)
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = scan_recovery_pipeline(
            args.root,
            target_evidence_root=args.target_evidence_root,
            checkpoint_catalog=args.checkpoint_catalog,
            probe_directories=args.probe_directories,
            probe_wheels=args.probe_wheels,
            python=args.python,
            max_depth=args.max_depth,
            max_candidates=args.max_candidates,
            reports_dir=args.reports_dir,
            wheel_timeout=args.wheel_timeout,
        )
    except (OSError, RecoveryScanError) as exc:
        report = {
            "schema": SCHEMA,
            "status": "error",
            "promotion_allowed": False,
            "product_execution_allowed": False,
            "type": type(exc).__name__,
            "error": str(exc),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        _atomic_write(args.output.expanduser().resolve(), text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
