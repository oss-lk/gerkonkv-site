from __future__ import annotations

"""Unified batch recovery scan for directories, checkpoint ZIPs and wheels."""

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
import zipfile

from .core_compatibility import RecoveryCompatibilityError
from .core_recovery import RecoveryCandidateError
from .core_scan import (
    CATALOG_SCHEMA,
    MAX_DEFAULT_CANDIDATES,
    MAX_DEFAULT_DEPTH,
    RecoveryScanError,
    _atomic_write,
    _depth,
    _load_checkpoint_catalog,
    _priority,
    scan_core_candidates,
)
from .core_wheel_recovery import build_wheel_recovery_plan

SCHEMA = "rocketdict-workbench-core-recovery-scan/3"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def discover_wheel_candidates(
    root: Path | str,
    *,
    max_depth: int = MAX_DEFAULT_DEPTH,
    max_candidates: int = MAX_DEFAULT_CANDIDATES,
) -> list[Path]:
    root = Path(root).expanduser().resolve()
    if max_depth < 0 or max_candidates < 1:
        raise RecoveryScanError("max_depth must be >=0 and max_candidates must be >=1")
    if root.is_file():
        return [root] if root.suffix.casefold() == ".whl" else []
    if not root.is_dir():
        raise RecoveryScanError(f"scan root does not exist: {root}")

    found: set[Path] = set()
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        rel_depth = _depth(root, current_path)
        dirs[:] = [
            name
            for name in dirs
            if not (current_path / name).is_symlink() and rel_depth < max_depth
        ]
        for filename in files:
            path = current_path / filename
            if path.is_symlink():
                continue
            if filename.casefold().endswith(".whl"):
                found.add(path.resolve())
        if len(found) > max_candidates:
            raise RecoveryScanError(
                f"wheel candidate count exceeded limit {max_candidates}; narrow the scan root"
            )
    return sorted(found, key=lambda path: str(path).casefold())


def _validate_wheel_catalog(catalog: dict[str, Any] | None) -> None:
    if catalog is None:
        return
    if catalog.get("schema") != CATALOG_SCHEMA:
        raise RecoveryScanError("unexpected historical checkpoint catalog schema")
    for row in catalog.get("entries") or []:
        entry_id = str(row.get("id") or "")
        patterns = row.get("wheel_name_patterns", [])
        if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
            raise RecoveryScanError(f"checkpoint catalog wheel patterns invalid: {entry_id}")
        for pattern in patterns:
            if not pattern or "/" in pattern or "\\" in pattern:
                raise RecoveryScanError(
                    f"checkpoint catalog wheel pattern must be a basename glob: {entry_id}: {pattern!r}"
                )
        expected_sha = row.get("wheel_sha256")
        if expected_sha is not None and not _SHA256.fullmatch(str(expected_sha).casefold()):
            raise RecoveryScanError(f"checkpoint catalog wheel SHA-256 invalid: {entry_id}")
        expected_bytes = row.get("wheel_bytes")
        if expected_bytes is not None and (
            not isinstance(expected_bytes, int) or expected_bytes < 1
        ):
            raise RecoveryScanError(f"checkpoint catalog wheel byte size invalid: {entry_id}")
        if expected_bytes is not None and expected_sha is None:
            raise RecoveryScanError(
                f"checkpoint catalog wheel byte size lacks SHA-256: {entry_id}"
            )


def _wheel_matches(
    path: Path,
    source: dict[str, Any],
    catalog: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if catalog is None:
        return []
    basename = path.name.casefold()
    observed_sha = str(source.get("archive_sha256") or "").casefold() or None
    observed_bytes = source.get("archive_bytes")
    matches: list[dict[str, Any]] = []
    for row in catalog["entries"]:
        patterns = list(row.get("wheel_name_patterns") or [])
        matched_patterns = [
            pattern
            for pattern in patterns
            if fnmatch.fnmatchcase(basename, pattern.casefold())
        ]
        if not matched_patterns:
            continue
        expected_sha = row.get("wheel_sha256")
        expected_bytes = row.get("wheel_bytes")
        exact_identity_available = expected_sha is not None
        exact_identity_match = bool(
            exact_identity_available
            and observed_sha == str(expected_sha).casefold()
            and (expected_bytes is None or observed_bytes == expected_bytes)
        )
        matches.append(
            {
                "catalog_id": row["id"],
                "version": row.get("version"),
                "stage": row.get("stage"),
                "candidate_role": row.get("candidate_role"),
                "evidence_level": row.get("evidence_level"),
                "artifact_kind": "wheel",
                "name_match": True,
                "matched_patterns": matched_patterns,
                "exact_identity_available": exact_identity_available,
                "exact_identity_match": exact_identity_match,
                "exact_identity_mismatch": bool(
                    exact_identity_available and not exact_identity_match
                ),
                "expected_wheel_sha256": expected_sha,
                "expected_wheel_bytes": expected_bytes,
                "observed_wheel_sha256": observed_sha,
                "observed_wheel_bytes": observed_bytes,
                "promotion_allowed": False,
            }
        )
    matches.sort(
        key=lambda item: (
            1 if item["exact_identity_match"] else 0,
            str(item.get("version") or ""),
            str(item["catalog_id"]),
        ),
        reverse=True,
    )
    return matches


def _wheel_summary(
    path: Path,
    plan: dict[str, Any],
    *,
    catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate = plan.get("candidate") or {}
    target = plan.get("target") or {}
    source = candidate.get("source") or {}
    matches = _wheel_matches(path, source, catalog)
    return {
        "path": str(path),
        "kind": "wheel",
        "archive_sha256": source.get("archive_sha256"),
        "archive_bytes": source.get("archive_bytes"),
        "rocketdict_version": candidate.get("rocketdict_version"),
        "candidate_report_status": candidate.get("report_status"),
        "candidate_fingerprint": candidate.get("fingerprint"),
        "compatibility_plan_status": plan.get("status"),
        "compatibility_plan_fingerprint": ((plan.get("identity") or {}).get("fingerprint")),
        "structural_complete_for_workbench_bridge": bool(
            candidate.get("structural_complete_for_workbench_bridge")
        ),
        "runtime_probe_ok": False,
        "documented_archive_identity_match": False,
        "documented_archive_name": None,
        "historical_checkpoint_matches": matches,
        "historical_checkpoint_name_match": bool(matches),
        "historical_checkpoint_exact_identity_match": any(
            row["exact_identity_match"] for row in matches
        ),
        "exact_target_available_count": target.get("exact_target_available_count"),
        "exact_target_missing_count": target.get("exact_target_missing_count"),
        "blockers": list(plan.get("blockers") or []),
        "promotion_allowed": False,
    }


def scan_core_artifacts(
    root: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
    checkpoint_catalog: Path | str | None = None,
    probe_directories: bool = False,
    python: str | Path | None = None,
    max_depth: int = MAX_DEFAULT_DEPTH,
    max_candidates: int = MAX_DEFAULT_CANDIDATES,
    reports_dir: Path | str | None = None,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise RecoveryScanError(f"scan root does not exist: {root_path}")
    if root_path.is_file() and root_path.suffix.casefold() not in {".zip", ".whl"}:
        raise RecoveryScanError("single-file scan root must be a .zip or .whl")

    catalog, catalog_identity = _load_checkpoint_catalog(
        target_evidence_root=target_evidence_root,
        checkpoint_catalog=checkpoint_catalog,
    )
    _validate_wheel_catalog(catalog)

    base_report: dict[str, Any] | None = None
    if root_path.is_dir() or root_path.suffix.casefold() == ".zip":
        base_report = scan_core_candidates(
            root_path,
            target_evidence_root=target_evidence_root,
            checkpoint_catalog=checkpoint_catalog,
            probe_directories=probe_directories,
            python=python,
            max_depth=max_depth,
            max_candidates=max_candidates,
            reports_dir=reports_dir,
        )

    wheels = discover_wheel_candidates(
        root_path,
        max_depth=max_depth,
        max_candidates=max_candidates,
    )
    base_discovered = int((base_report or {}).get("discovered_candidate_count") or 0)
    if base_discovered + len(wheels) > max_candidates:
        raise RecoveryScanError(
            f"combined candidate count exceeded limit {max_candidates}; narrow the scan root"
        )

    summaries = list((base_report or {}).get("candidates") or [])
    errors = list((base_report or {}).get("errors") or [])
    report_root = Path(reports_dir).expanduser().resolve() if reports_dir else None

    for wheel in wheels:
        try:
            plan = build_wheel_recovery_plan(
                wheel,
                target_evidence_root=target_evidence_root,
            )
        except (
            OSError,
            RecoveryCandidateError,
            RecoveryCompatibilityError,
            RuntimeError,
            zipfile.BadZipFile,
        ) as exc:
            errors.append(
                {
                    "path": str(wheel),
                    "kind": "wheel",
                    "type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        summaries.append(_wheel_summary(wheel, plan, catalog=catalog))
        if report_root is not None:
            fingerprint = str((plan.get("identity") or {}).get("fingerprint") or "unknown")
            _atomic_write(
                report_root / f"{fingerprint[:16]}.json",
                json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            )

    summaries.sort(key=_priority, reverse=True)
    for index, row in enumerate(summaries, start=1):
        row["recovery_priority_rank"] = index

    fingerprint_payload = {
        "schema": SCHEMA,
        "root": str(root_path),
        "target_evidence_root": str(Path(target_evidence_root).resolve())
        if target_evidence_root
        else None,
        "checkpoint_catalog": catalog_identity,
        "probe_directories": probe_directories,
        "max_depth": max_depth,
        "base_scan_fingerprint": ((base_report or {}).get("identity") or {}).get(
            "fingerprint"
        ),
        "wheel_paths": [str(path) for path in wheels],
        "summaries": [
            {key: value for key, value in row.items() if key != "recovery_priority_rank"}
            for row in summaries
        ],
        "errors": errors,
    }
    raw = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return {
        "schema": SCHEMA,
        "status": "completed",
        "promotion_allowed": False,
        "root": str(root_path),
        "supported_artifact_kinds": ["directory", "zip", "wheel"],
        "discovered_candidate_count": base_discovered + len(wheels),
        "discovered_wheel_count": len(wheels),
        "analyzed_candidate_count": len(summaries),
        "error_count": len(errors),
        "probe_directories": probe_directories,
        "wheel_runtime_probe_policy": "structural_only_until_explicit_isolated_installation",
        "checkpoint_catalog": catalog_identity,
        "ranking_semantics": (
            "Recovery triage only. Exact catalog SHA identities outrank name-only matches; "
            "structural/runtime evidence follows. Wheel structure is read directly from the "
            "wheel but is not executed. No ranking value is Product promotion proof."
        ),
        "candidates": summaries,
        "errors": errors,
        "identity": {"fingerprint": hashlib.sha256(raw).hexdigest()},
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-scan",
        description=(
            "Batch structural screening/ranking of historical RocketDict source roots, "
            "checkpoint ZIPs and Python wheels"
        ),
    )
    p.add_argument("root", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
    p.add_argument("--checkpoint-catalog", type=Path)
    p.add_argument("--probe-directories", action="store_true")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--max-depth", type=int, default=MAX_DEFAULT_DEPTH)
    p.add_argument("--max-candidates", type=int, default=MAX_DEFAULT_CANDIDATES)
    p.add_argument("--reports-dir", type=Path)
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = scan_core_artifacts(
            args.root,
            target_evidence_root=args.target_evidence_root,
            checkpoint_catalog=args.checkpoint_catalog,
            probe_directories=args.probe_directories,
            python=args.python,
            max_depth=args.max_depth,
            max_candidates=args.max_candidates,
            reports_dir=args.reports_dir,
        )
    except (OSError, RecoveryScanError) as exc:
        payload = {
            "schema": SCHEMA,
            "status": "error",
            "promotion_allowed": False,
            "type": type(exc).__name__,
            "error": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        _atomic_write(args.output.expanduser().resolve(), text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
