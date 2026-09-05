from __future__ import annotations

"""Unified historical-core recovery scan with fail-closed ZIP/wheel proof chains."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .core_checkpoint_recovery import inspect_full_checkpoint
from .core_scan import (
    MAX_DEFAULT_CANDIDATES,
    MAX_DEFAULT_DEPTH,
    RecoveryScanError,
    _atomic_write,
    _priority,
)
from .core_scan_artifacts import scan_core_artifacts
from .core_wheel_pipeline import recover_wheel_candidate

SCHEMA = "rocketdict-workbench-core-recovery-scan/8"


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
    report_root = Path(reports_dir).expanduser().resolve() if reports_dir else None

    checkpoint_pipeline_count = 0
    checkpoint_exact_identity_match_count = 0
    checkpoint_blocked_count = 0
    checkpoint_source_api_complete_count = 0
    checkpoint_nested_wheel_count = 0
    checkpoint_nested_wheel_integrity_ok_count = 0
    checkpoint_nested_wheel_catalog_exact_match_count = 0
    checkpoint_nested_wheel_catalog_exact_mismatch_count = 0
    checkpoint_source_wheel_parity_complete_count = 0

    wheel_pipeline_count = 0
    wheel_integrity_ok_count = 0
    wheel_catalog_exact_match_count = 0
    wheel_catalog_exact_mismatch_count = 0
    wheel_runtime_attempted_count = 0
    wheel_runtime_proven_count = 0

    for row in candidates:
        if row.get("kind") == "zip":
            checkpoint_pipeline_count += 1
            try:
                proof = inspect_full_checkpoint(
                    Path(str(row["path"])),
                    target_evidence_root=target_evidence_root,
                    checkpoint_catalog=checkpoint_catalog,
                )
            except Exception as exc:  # batch boundary: preserve generic ZIP evidence
                row["checkpoint_recovery_status"] = "error"
                row["checkpoint_recovery_fingerprint"] = None
                row["checkpoint_exact_identity_match"] = False
                row["checkpoint_source_api_complete"] = False
                errors.append(
                    {
                        "path": row["path"],
                        "kind": "checkpoint_pipeline",
                        "type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
            else:
                source = proof.get("source") or {}
                if proof.get("historical_checkpoint_exact_identity_match"):
                    checkpoint_exact_identity_match_count += 1
                if proof.get("status") == "blocked_checkpoint_candidate":
                    checkpoint_blocked_count += 1
                if source.get("api_complete"):
                    checkpoint_source_api_complete_count += 1
                checkpoint_nested_wheel_count += int(
                    proof.get("nested_rocketdict_wheel_count") or 0
                )
                checkpoint_nested_wheel_integrity_ok_count += int(
                    proof.get("nested_rocketdict_wheel_integrity_ok_count") or 0
                )
                checkpoint_nested_wheel_catalog_exact_match_count += int(
                    proof.get("nested_rocketdict_wheel_catalog_exact_match_count") or 0
                )
                checkpoint_nested_wheel_catalog_exact_mismatch_count += int(
                    proof.get("nested_rocketdict_wheel_catalog_exact_mismatch_count") or 0
                )
                checkpoint_source_wheel_parity_complete_count += int(
                    proof.get("source_wheel_parity_complete_count") or 0
                )

                row["checkpoint_recovery"] = proof
                row["checkpoint_recovery_status"] = proof.get("status")
                row["checkpoint_recovery_fingerprint"] = (
                    (proof.get("identity") or {}).get("fingerprint")
                )
                row["checkpoint_exact_identity_match"] = bool(
                    proof.get("historical_checkpoint_exact_identity_match")
                )
                row["checkpoint_source_api_complete"] = bool(source.get("api_complete"))
                row["checkpoint_nested_rocketdict_wheel_count"] = int(
                    proof.get("nested_rocketdict_wheel_count") or 0
                )
                row["checkpoint_source_wheel_parity_complete_count"] = int(
                    proof.get("source_wheel_parity_complete_count") or 0
                )
                row["promotion_allowed"] = False

                if report_root is not None:
                    fingerprint = str(row["checkpoint_recovery_fingerprint"] or "unknown")
                    _atomic_write(
                        report_root / f"checkpoint-{fingerprint[:16]}.json",
                        json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
                    )

        if row.get("kind") != "wheel":
            continue
        wheel_pipeline_count += 1
        try:
            proof = recover_wheel_candidate(
                Path(str(row["path"])),
                target_evidence_root=target_evidence_root,
                checkpoint_catalog=checkpoint_catalog,
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
        catalog = proof.get("historical_catalog") or {}
        runtime = proof.get("runtime_probe") or {}
        if integrity.get("ok"):
            wheel_integrity_ok_count += 1
        if catalog.get("exact_identity_match"):
            wheel_catalog_exact_match_count += 1
        if catalog.get("exact_identity_mismatch"):
            wheel_catalog_exact_mismatch_count += 1
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
        row["historical_catalog_name_match"] = bool(catalog.get("name_match"))
        row["historical_catalog_exact_identity_match"] = bool(
            catalog.get("exact_identity_match")
        )
        row["historical_catalog_exact_identity_mismatch"] = bool(
            catalog.get("exact_identity_mismatch")
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
        "checkpoint_pipeline_count": checkpoint_pipeline_count,
        "checkpoint_exact_identity_match_count": checkpoint_exact_identity_match_count,
        "checkpoint_blocked_count": checkpoint_blocked_count,
        "checkpoint_source_api_complete_count": checkpoint_source_api_complete_count,
        "checkpoint_nested_wheel_count": checkpoint_nested_wheel_count,
        "checkpoint_nested_wheel_integrity_ok_count": checkpoint_nested_wheel_integrity_ok_count,
        "checkpoint_nested_wheel_catalog_exact_match_count": checkpoint_nested_wheel_catalog_exact_match_count,
        "checkpoint_nested_wheel_catalog_exact_mismatch_count": checkpoint_nested_wheel_catalog_exact_mismatch_count,
        "checkpoint_source_wheel_parity_complete_count": checkpoint_source_wheel_parity_complete_count,
        "checkpoint_policy": (
            "all_discovered_checkpoint_ZIPs_receive_read_only_outer_identity_source_nested_wheel_"
            "catalog_parity_api_evidence_and_base_to_03040_proof"
        ),
        "wheel_pipeline_count": wheel_pipeline_count,
        "wheel_integrity_ok_count": wheel_integrity_ok_count,
        "wheel_catalog_exact_match_count": wheel_catalog_exact_match_count,
        "wheel_catalog_exact_mismatch_count": wheel_catalog_exact_mismatch_count,
        "wheel_runtime_attempted_count": wheel_runtime_attempted_count,
        "wheel_runtime_proven_count": wheel_runtime_proven_count,
        "wheel_runtime_policy": (
            "runtime_allowed_only_after_integrity_known_catalog_identity_structure_plan_and_cross_layer_identity"
            if probe_wheels
            else "runtime_not_requested_full_read_only_wheel_proof_still_generated"
        ),
        "checkpoint_catalog": base.get("checkpoint_catalog"),
        "ranking_semantics": (
            "Recovery triage only. Checkpoint ZIPs receive an additional read-only proof of outer "
            "catalog identity, source API inventory, nested RocketDict wheel integrity/catalog "
            "identity and source↔wheel parity. Known wheel basenames still require exact catalog "
            "identity before runtime probing. No ZIP/wheel proof or rank authorizes historical "
            "bytes as exact 0.30.40 or Product execution proof."
        ),
        "candidates": candidates,
        "errors": errors,
        "identity": {"fingerprint": _canonical_sha(fingerprint_payload)},
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-scan",
        description=(
            "Batch historical RocketDict recovery scan with read-only full-checkpoint proof "
            "and integrity/catalog-gated wheel runtime proof"
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