from __future__ import annotations

"""Final unified recovery scanner with opt-in wheel zipimport runtime evidence."""

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
from .core_wheel_runtime import RUNTIME_SCHEMA, probe_wheel_runtime

SCHEMA = "rocketdict-workbench-core-recovery-scan/4"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def scan_recovery_frontier(
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
    wheel_probe_count = 0
    wheel_probe_ok_count = 0
    for row in candidates:
        if row.get("kind") != "wheel":
            continue
        if probe_wheels:
            runtime = probe_wheel_runtime(
                Path(str(row["path"])),
                python=python,
                timeout=wheel_timeout,
            )
            wheel_probe_count += 1
            if runtime.get("ok"):
                wheel_probe_ok_count += 1
            row["wheel_runtime_probe"] = runtime
            row["runtime_probe_ok"] = bool(runtime.get("ok"))
            row["runtime_proof_status"] = runtime.get("status")
            row["runtime_probe_fingerprint"] = (
                (runtime.get("identity") or {}).get("fingerprint")
            )
        else:
            row["wheel_runtime_probe"] = {
                "schema": RUNTIME_SCHEMA,
                "status": "not_requested",
                "attempted": False,
                "ok": False,
                "promotion_allowed": False,
            }
            row["runtime_probe_ok"] = False
            row["runtime_proof_status"] = "not_requested"
            row["runtime_probe_fingerprint"] = None

    # Runtime proof is useful recovery triage evidence.  Re-rank after enriching
    # wheel candidates, while retaining the exact same non-promotional priority
    # semantics used by the base scanner.
    candidates.sort(key=_priority, reverse=True)
    for rank, row in enumerate(candidates, start=1):
        row["recovery_priority_rank"] = rank

    payload = {
        "schema": SCHEMA,
        "base_scan_schema": base.get("schema"),
        "base_scan_fingerprint": ((base.get("identity") or {}).get("fingerprint")),
        "root": base.get("root"),
        "checkpoint_catalog": base.get("checkpoint_catalog"),
        "probe_directories": probe_directories,
        "probe_wheels": probe_wheels,
        "python": str(python or sys.executable),
        "wheel_timeout": wheel_timeout,
        "candidate_rows": [
            {key: value for key, value in row.items() if key != "recovery_priority_rank"}
            for row in candidates
        ],
        "errors": base.get("errors") or [],
    }
    return {
        "schema": SCHEMA,
        "status": "completed",
        "promotion_allowed": False,
        "root": base.get("root"),
        "supported_artifact_kinds": ["directory", "zip", "wheel"],
        "discovered_candidate_count": base.get("discovered_candidate_count"),
        "discovered_wheel_count": base.get("discovered_wheel_count"),
        "analyzed_candidate_count": len(candidates),
        "error_count": len(base.get("errors") or []),
        "probe_directories": probe_directories,
        "probe_wheels": probe_wheels,
        "wheel_runtime_probe_count": wheel_probe_count,
        "wheel_runtime_probe_ok_count": wheel_probe_ok_count,
        "wheel_runtime_probe_policy": (
            "opt_in_isolated_python_zipimport_no_install_no_extraction"
            if probe_wheels
            else "not_requested_structural_only"
        ),
        "checkpoint_catalog": base.get("checkpoint_catalog"),
        "ranking_semantics": (
            "Recovery triage only. Exact artifact identity and structural status remain primary. "
            "An opt-in successful wheel zipimport probe adds runtime import evidence but cannot "
            "prove exact 0.30.40 compatibility or authorize Product execution."
        ),
        "candidates": candidates,
        "errors": base.get("errors") or [],
        "identity": {"fingerprint": _canonical_sha(payload)},
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-scan",
        description=(
            "Batch screening of historical RocketDict source roots, checkpoint ZIPs and wheels "
            "with optional isolated runtime probes"
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
        report = scan_recovery_frontier(
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
