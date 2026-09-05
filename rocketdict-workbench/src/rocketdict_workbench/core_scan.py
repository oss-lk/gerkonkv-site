from __future__ import annotations

"""Batch discovery/ranking of historical RocketDict recovery candidates.

The scanner is intentionally recovery-only. It can inspect ZIPs without
extracting them and source directories without importing them by default. A
higher ranking means "inspect this recovery lead first", never "this is safe to
promote".
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
import zipfile

from .core_compatibility import build_core_recovery_plan
from .core_recovery import RecoveryCandidateError

SCHEMA = "rocketdict-workbench-core-recovery-scan/1"
MAX_DEFAULT_CANDIDATES = 500
MAX_DEFAULT_DEPTH = 8
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\D.*)?$")


class RecoveryScanError(RuntimeError):
    pass


def _version_tuple(value: Any) -> tuple[int, int, int]:
    match = _VERSION.match(str(value or ""))
    if not match:
        return (-1, -1, -1)
    return tuple(int(part) for part in match.groups())


def _depth(root: Path, path: Path) -> int:
    try:
        return len(path.relative_to(root).parts)
    except ValueError:
        return 10**9


def _candidate_root_from_package_init(init: Path) -> Path | None:
    """Map a discovered package __init__ to one supported candidate root.

    This deliberately canonicalizes `root/src/rocketdict/__init__.py` to
    `root`, rather than also reporting `root/src` as a second direct-layout
    candidate.  `root/active_source/src/rocketdict/__init__.py` similarly maps
    to `root`.
    """
    if init.name != "__init__.py" or init.parent.name != "rocketdict":
        return None
    package_parent = init.parent.parent
    if package_parent.name == "src":
        if package_parent.parent.name == "active_source":
            return package_parent.parent.parent.resolve()
        return package_parent.parent.resolve()
    return init.parent.parent.resolve()


def discover_core_candidates(
    root: Path | str,
    *,
    max_depth: int = MAX_DEFAULT_DEPTH,
    max_candidates: int = MAX_DEFAULT_CANDIDATES,
) -> list[Path]:
    root = Path(root).expanduser().resolve()
    if max_depth < 0 or max_candidates < 1:
        raise RecoveryScanError("max_depth must be >=0 and max_candidates must be >=1")
    if root.is_file():
        if root.suffix.casefold() != ".zip":
            raise RecoveryScanError("single-file scan root must be a .zip")
        return [root]
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
            if filename.casefold().endswith(".zip"):
                found.add(path.resolve())
            if filename == "__init__.py" and current_path.name == "rocketdict":
                candidate_root = _candidate_root_from_package_init(path)
                if candidate_root is not None and _depth(root, candidate_root) <= max_depth:
                    found.add(candidate_root)

        if len(found) > max_candidates:
            raise RecoveryScanError(
                f"candidate count exceeded limit {max_candidates}; narrow the scan root"
            )

    return sorted(found, key=lambda path: str(path).casefold())


def _priority(summary: dict[str, Any]) -> tuple[Any, ...]:
    status_rank = {
        "exact_version_structural_candidate": 3,
        "base_candidate_requires_compatibility_proof": 2,
        "incomplete_candidate": 1,
    }.get(str(summary.get("candidate_report_status") or ""), 0)
    version = _version_tuple(summary.get("rocketdict_version"))
    return (
        1 if summary.get("documented_archive_identity_match") else 0,
        status_rank,
        1 if summary.get("structural_complete_for_workbench_bridge") else 0,
        1 if summary.get("runtime_probe_ok") else 0,
        int(summary.get("exact_target_available_count") or 0),
        version,
        str(summary.get("path") or "").casefold(),
    )


def _summary(path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    candidate = plan.get("candidate") or {}
    target = plan.get("target") or {}
    identity = candidate.get("documented_archive_identity") or {}
    source = candidate.get("source") or {}
    return {
        "path": str(path),
        "kind": source.get("kind"),
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
        "runtime_probe_ok": bool(candidate.get("runtime_probe_ok")),
        "documented_archive_identity_match": bool(identity.get("match")),
        "documented_archive_name": identity.get("documented_archive_name"),
        "exact_target_available_count": target.get("exact_target_available_count"),
        "exact_target_missing_count": target.get("exact_target_missing_count"),
        "blockers": list(plan.get("blockers") or []),
        "promotion_allowed": False,
    }


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def scan_core_candidates(
    root: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
    probe_directories: bool = False,
    python: str | Path | None = None,
    max_depth: int = MAX_DEFAULT_DEPTH,
    max_candidates: int = MAX_DEFAULT_CANDIDATES,
    reports_dir: Path | str | None = None,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    candidates = discover_core_candidates(
        root_path, max_depth=max_depth, max_candidates=max_candidates
    )
    summaries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    report_root = Path(reports_dir).expanduser().resolve() if reports_dir else None

    for path in candidates:
        runtime = probe_directories and path.is_dir()
        try:
            plan = build_core_recovery_plan(
                path,
                target_evidence_root=target_evidence_root,
                python=python,
                probe_runtime=runtime,
            )
        except (OSError, RecoveryCandidateError, RuntimeError, zipfile.BadZipFile) as exc:
            errors.append(
                {
                    "path": str(path),
                    "type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        summary = _summary(path, plan)
        summaries.append(summary)
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
        "probe_directories": probe_directories,
        "max_depth": max_depth,
        "candidate_paths": [str(path) for path in candidates],
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
        "discovered_candidate_count": len(candidates),
        "analyzed_candidate_count": len(summaries),
        "error_count": len(errors),
        "probe_directories": probe_directories,
        "ranking_semantics": (
            "Recovery triage only: documented archive identity, exact-version structural shape, "
            "bridge completeness, optional runtime probe, exact target evidence count, then version. "
            "Ranking is not compatibility or promotion proof."
        ),
        "candidates": summaries,
        "errors": errors,
        "identity": {"fingerprint": hashlib.sha256(raw).hexdigest()},
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-scan",
        description="Batch structural screening/ranking of historical RocketDict recovery candidates",
    )
    p.add_argument("root", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
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
        report = scan_core_candidates(
            args.root,
            target_evidence_root=args.target_evidence_root,
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
