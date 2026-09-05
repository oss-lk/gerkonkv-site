from __future__ import annotations

"""Batch discovery/ranking of historical RocketDict recovery candidates.

The scanner is recovery-only. It can inspect ZIPs without extracting them and
source directories without importing them by default. A higher ranking means
"inspect this recovery lead first", never "this is safe to promote".

Historical artifact identity is SHA-first. A known SHA-256 is sufficient to
identify an archive when its old byte-size record was lost; if an expected size
is also known, the observed size must match as an additional guard.
"""

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

from .core_compatibility import build_core_recovery_plan
from .core_recovery import RecoveryCandidateError

SCHEMA = "rocketdict-workbench-core-recovery-scan/3"
CATALOG_SCHEMA = "rocketdict-historical-checkpoint-catalog/1"
MAX_DEFAULT_CANDIDATES = 500
MAX_DEFAULT_DEPTH = 8
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\D.*)?$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _default_catalog_path(target_evidence_root: Path | str | None) -> Path:
    if target_evidence_root is not None:
        return Path(target_evidence_root).expanduser().resolve().parent / "checkpoint-catalog.json"
    return Path(__file__).resolve().parents[3] / "rocketdict" / "recovered" / "checkpoint-catalog.json"


def _load_checkpoint_catalog(
    *,
    target_evidence_root: Path | str | None,
    checkpoint_catalog: Path | str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    explicit = checkpoint_catalog is not None
    path = (
        Path(checkpoint_catalog).expanduser().resolve()
        if checkpoint_catalog is not None
        else _default_catalog_path(target_evidence_root)
    )
    if not path.is_file():
        if explicit:
            raise RecoveryScanError(f"checkpoint catalog does not exist: {path}")
        return None, {
            "available": False,
            "path": str(path),
            "schema": None,
            "sha256": None,
            "entry_count": 0,
        }

    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryScanError(f"cannot load checkpoint catalog {path}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("schema") != CATALOG_SCHEMA:
        observed = payload.get("schema") if isinstance(payload, dict) else type(payload).__name__
        raise RecoveryScanError(f"unexpected checkpoint catalog schema: {observed}")
    if payload.get("promotion_allowed") is not False:
        raise RecoveryScanError("checkpoint catalog unexpectedly permits promotion")

    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise RecoveryScanError("checkpoint catalog entries must be a list")

    seen_ids: set[str] = set()
    for row in entries:
        if not isinstance(row, dict):
            raise RecoveryScanError("checkpoint catalog contains non-object entry")
        entry_id = str(row.get("id") or "")
        if not entry_id or entry_id in seen_ids:
            raise RecoveryScanError(f"checkpoint catalog has invalid/duplicate id: {entry_id!r}")
        seen_ids.add(entry_id)
        if row.get("promotion_allowed") is not False:
            raise RecoveryScanError(f"checkpoint catalog entry permits promotion: {entry_id}")

        patterns = row.get("archive_name_patterns")
        if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
            raise RecoveryScanError(f"checkpoint catalog patterns invalid: {entry_id}")
        for pattern in patterns:
            if not pattern or "/" in pattern or "\\" in pattern:
                raise RecoveryScanError(
                    f"checkpoint catalog pattern must be a basename glob: {entry_id}: {pattern!r}"
                )

        expected_sha = row.get("archive_sha256")
        if expected_sha is not None and not _SHA256.fullmatch(str(expected_sha).casefold()):
            raise RecoveryScanError(f"checkpoint catalog SHA-256 invalid: {entry_id}")
        expected_bytes = row.get("archive_bytes")
        if expected_bytes is not None and (
            not isinstance(expected_bytes, int) or expected_bytes < 1
        ):
            raise RecoveryScanError(f"checkpoint catalog byte size invalid: {entry_id}")
        if expected_bytes is not None and expected_sha is None:
            raise RecoveryScanError(
                f"checkpoint catalog archive byte size lacks SHA-256: {entry_id}"
            )

    return payload, {
        "available": True,
        "path": str(path),
        "schema": CATALOG_SCHEMA,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "entry_count": len(entries),
    }


def _checkpoint_matches(
    path: Path,
    source: dict[str, Any],
    catalog: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if catalog is None or source.get("kind") != "zip":
        return []

    basename = path.name.casefold()
    observed_sha = str(source.get("archive_sha256") or "").casefold() or None
    observed_bytes = source.get("archive_bytes")
    matches: list[dict[str, Any]] = []

    for row in catalog["entries"]:
        patterns = list(row.get("archive_name_patterns") or [])
        matched_patterns = [
            pattern
            for pattern in patterns
            if fnmatch.fnmatchcase(basename, pattern.casefold())
        ]
        if not matched_patterns:
            continue

        expected_sha = row.get("archive_sha256")
        expected_bytes = row.get("archive_bytes")
        exact_identity_available = expected_sha is not None
        sha_match = bool(
            exact_identity_available
            and observed_sha == str(expected_sha).casefold()
        )
        size_match = bool(expected_bytes is None or observed_bytes == expected_bytes)
        exact_identity_match = bool(sha_match and size_match)

        matches.append(
            {
                "catalog_id": row["id"],
                "version": row.get("version"),
                "stage": row.get("stage"),
                "candidate_role": row.get("candidate_role"),
                "evidence_level": row.get("evidence_level"),
                "name_match": True,
                "matched_patterns": matched_patterns,
                "exact_identity_available": exact_identity_available,
                "exact_identity_match": exact_identity_match,
                "exact_identity_mismatch": bool(
                    exact_identity_available and not exact_identity_match
                ),
                "sha256_match": sha_match,
                "size_constraint_available": expected_bytes is not None,
                "size_match": size_match,
                "expected_archive_sha256": expected_sha,
                "expected_archive_bytes": expected_bytes,
                "observed_archive_sha256": observed_sha,
                "observed_archive_bytes": observed_bytes,
                "promotion_allowed": False,
            }
        )

    matches.sort(
        key=lambda item: (
            1 if item["exact_identity_match"] else 0,
            _version_tuple(item.get("version")),
            str(item["catalog_id"]),
        ),
        reverse=True,
    )
    return matches


def _priority(summary: dict[str, Any]) -> tuple[Any, ...]:
    status_rank = {
        "exact_version_structural_candidate": 3,
        "base_candidate_requires_compatibility_proof": 2,
        "incomplete_candidate": 1,
    }.get(str(summary.get("candidate_report_status") or ""), 0)
    catalog_matches = list(summary.get("historical_checkpoint_matches") or [])
    catalog_exact = any(row.get("exact_identity_match") for row in catalog_matches)
    catalog_name = bool(catalog_matches)
    version = _version_tuple(summary.get("rocketdict_version"))
    return (
        1 if summary.get("documented_archive_identity_match") or catalog_exact else 0,
        status_rank,
        1 if catalog_name else 0,
        1 if summary.get("structural_complete_for_workbench_bridge") else 0,
        1 if summary.get("runtime_probe_ok") else 0,
        int(summary.get("exact_target_available_count") or 0),
        version,
        str(summary.get("path") or "").casefold(),
    )


def _summary(
    path: Path,
    plan: dict[str, Any],
    *,
    catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate = plan.get("candidate") or {}
    target = plan.get("target") or {}
    identity = candidate.get("documented_archive_identity") or {}
    source = candidate.get("source") or {}
    matches = _checkpoint_matches(path, source, catalog)
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


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def scan_core_candidates(
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
    catalog, catalog_identity = _load_checkpoint_catalog(
        target_evidence_root=target_evidence_root,
        checkpoint_catalog=checkpoint_catalog,
    )
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
        summary = _summary(path, plan, catalog=catalog)
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
        "checkpoint_catalog": catalog_identity,
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
        "checkpoint_catalog": catalog_identity,
        "ranking_semantics": (
            "Recovery triage only: exact documented archive identity, candidate structural status, "
            "historical catalog name match, bridge completeness, optional runtime probe, exact target "
            "evidence count, then version. Name-only matching never becomes byte identity. A known "
            "SHA-256 is sufficient exact ZIP identity; a known historical byte size is an additional "
            "mandatory match."
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
        report = scan_core_candidates(
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
