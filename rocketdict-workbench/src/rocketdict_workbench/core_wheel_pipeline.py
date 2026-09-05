from __future__ import annotations

"""Fail-closed end-to-end recovery evidence for a historical RocketDict wheel.

Evidence order is strict:
1. wheel container/METADATA/WHEEL/RECORD integrity;
2. packaged RocketDict structural source inspection;
3. exact historical-base -> recovered-0.30.40 compatibility plan;
4. optional isolated/network-denied runtime import proof.

No layer authorizes Product execution.  Runtime is never attempted when wheel
integrity fails, and every layer that observes the artifact must agree on the
same SHA-256 before a runtime proof can count as valid recovery evidence.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import zipfile

from .core_compatibility import RecoveryCompatibilityError
from .core_recovery import RecoveryCandidateError
from .core_wheel_integrity import inspect_wheel_integrity
from .core_wheel_recovery import build_wheel_recovery_plan, inspect_wheel_candidate
from .core_wheel_runtime import RUNTIME_SCHEMA, probe_wheel_runtime

SCHEMA = "rocketdict-workbench-core-wheel-recovery/4"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _not_run(status: str, reason: str) -> dict[str, Any]:
    return {
        "schema": RUNTIME_SCHEMA,
        "status": status,
        "attempted": False,
        "ok": False,
        "promotion_allowed": False,
        "reason": reason,
    }


def recover_wheel_candidate(
    candidate: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
    probe_runtime: bool = False,
    python: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    path = Path(candidate).expanduser().resolve()
    integrity = inspect_wheel_integrity(path)
    structural = inspect_wheel_candidate(path)
    plan = build_wheel_recovery_plan(
        path,
        target_evidence_root=target_evidence_root,
    )

    integrity_sha = integrity.get("wheel_sha256")
    structural_sha = ((structural.get("candidate") or {}).get("archive_sha256"))
    plan_sha = (((plan.get("candidate") or {}).get("source") or {}).get("archive_sha256"))
    pre_runtime_hashes = [integrity_sha, structural_sha, plan_sha]
    pre_runtime_identity_consistent = bool(all(pre_runtime_hashes)) and len(
        set(pre_runtime_hashes)
    ) == 1

    integrity_version = ((integrity.get("metadata") or {}).get("version"))
    structural_version = ((structural.get("observed") or {}).get("rocketdict_version"))
    version_consistent = bool(
        integrity_version
        and structural_version
        and str(integrity_version) == str(structural_version)
    )

    if not integrity.get("ok"):
        runtime = _not_run(
            "blocked_by_wheel_integrity",
            "wheel integrity must pass before any historical code import is attempted",
        )
    elif not pre_runtime_identity_consistent:
        runtime = _not_run(
            "blocked_by_cross_layer_artifact_identity",
            "integrity, structural and compatibility layers did not observe one exact wheel SHA-256",
        )
    elif not version_consistent:
        runtime = _not_run(
            "blocked_by_cross_layer_version_identity",
            "wheel METADATA version and packaged rocketdict.__version__ disagree",
        )
    elif probe_runtime:
        runtime = probe_wheel_runtime(path, python=python, timeout=timeout)
    else:
        runtime = _not_run(
            "not_requested",
            "runtime probing is opt-in; wheel inspection and compatibility planning are read-only",
        )

    runtime_sha = runtime.get("wheel_sha256") if runtime.get("attempted") else None
    all_hashes = [integrity_sha, structural_sha, plan_sha]
    if runtime_sha:
        all_hashes.append(runtime_sha)
    artifact_identity_consistent = bool(all(all_hashes)) and len(set(all_hashes)) == 1

    structural_complete = not bool(
        ((structural.get("observed") or {}).get("missing_required_modules") or [])
    )
    runtime_proven = bool(
        runtime.get("attempted")
        and runtime.get("ok")
        and artifact_identity_consistent
        and integrity.get("ok")
        and version_consistent
    )

    blockers: list[str] = []
    if not integrity.get("ok"):
        blockers.extend(
            f"wheel_integrity:{item}" for item in (integrity.get("hard_failures") or [])
        )
    if not pre_runtime_identity_consistent or not artifact_identity_consistent:
        blockers.append("cross_layer_wheel_identity_mismatch")
    if not version_consistent:
        blockers.append("cross_layer_wheel_version_mismatch")
    if not structural_complete:
        blockers.append("base_required_workbench_modules_missing")
    if runtime.get("attempted") and not runtime.get("ok"):
        blockers.append(f"runtime_probe:{runtime.get('status')}")
    blockers.extend(
        [
            "missing_exact_0.30.40_overlay_and_public_api_compatibility_proof",
            "live_product_preflight_api_probe_and_execution_binding_not_run",
        ]
    )

    if not integrity.get("ok"):
        status = "blocked_wheel_integrity"
    elif not artifact_identity_consistent:
        status = "blocked_cross_layer_identity"
    elif not version_consistent:
        status = "blocked_cross_layer_version"
    elif not structural_complete:
        status = "blocked_incomplete_base_core"
    elif runtime_proven:
        status = "runtime_proven_base_candidate"
    elif runtime.get("attempted"):
        status = "blocked_runtime_import"
    else:
        status = "verified_structural_base_candidate"

    identity_payload = {
        "schema": SCHEMA,
        "artifact_sha256": integrity_sha,
        "integrity_fingerprint": ((integrity.get("identity") or {}).get("fingerprint")),
        "structural_fingerprint": ((structural.get("identity") or {}).get("fingerprint")),
        "compatibility_plan_fingerprint": ((plan.get("identity") or {}).get("fingerprint")),
        "runtime_fingerprint": ((runtime.get("identity") or {}).get("fingerprint")),
        "artifact_identity_consistent": artifact_identity_consistent,
        "version_consistent": version_consistent,
        "runtime_proven": runtime_proven,
        "status": status,
        "blockers": blockers,
    }

    return {
        "schema": SCHEMA,
        "status": status,
        "promotion_allowed": False,
        "product_execution_allowed": False,
        "artifact": {
            "path": str(path),
            "sha256": integrity_sha,
            "bytes": integrity.get("wheel_bytes"),
            "artifact_identity_consistent": artifact_identity_consistent,
            "version_consistent": version_consistent,
            "version": structural_version,
        },
        "integrity": integrity,
        "structural_candidate": structural,
        "compatibility_plan": plan,
        "runtime_probe": runtime,
        "runtime_proven": runtime_proven,
        "remaining_product_blockers": blockers,
        "identity": {"fingerprint": _canonical_sha(identity_payload)},
        "rule": (
            "Wheel runtime evidence is subordinate to exact package integrity and cross-layer "
            "artifact identity. Even a fully proven historical base runtime remains non-Product "
            "until exact 0.30.40 compatibility/API evidence and the normal immutable Product "
            "verification chain pass."
        ),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-wheel",
        description=(
            "Fail-closed RocketDict historical wheel recovery: integrity -> structure -> "
            "0.30.40 compatibility plan -> optional isolated runtime proof"
        ),
    )
    p.add_argument("candidate", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
    p.add_argument("--probe-runtime", action="store_true")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = recover_wheel_candidate(
            args.candidate,
            target_evidence_root=args.target_evidence_root,
            probe_runtime=args.probe_runtime,
            python=args.python,
            timeout=args.timeout,
        )
    except (
        OSError,
        RecoveryCandidateError,
        RecoveryCompatibilityError,
        RuntimeError,
        zipfile.BadZipFile,
    ) as exc:
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
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
