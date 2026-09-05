from __future__ import annotations

"""Fail-closed base→0.30.40 recovery compatibility analysis.

This module never writes or materializes a reconstructed RocketDict core.  It
answers a narrower recovery question: given a full historical base candidate,
which target Stage8 overlay bytes are exact, which are missing, and which base
API dependencies remain unproven against the 0.30.40 Product line?
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import zipfile

from .core_recovery import (
    MAX_ARCHIVE_MEMBER_BYTES,
    RecoveryCandidateError,
    _canonical_sha,
    _read_directory,
    _read_zip,
    inspect_core_candidate,
)

SCHEMA = "rocketdict-workbench-core-recovery-plan/1"
HISTORY_SCHEMA = "rocketdict-stage8-core-recovery-history/1"
RECOVERY_SCHEMA = "rocketdict-stage8-runtime-recovery/1"
DEFAULT_TARGET_RELATIVE = Path("rocketdict/recovered/stage8-0.30.40")


class RecoveryCompatibilityError(RuntimeError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _repo_root() -> Path:
    # Source-checkout default only.  CLI callers can always provide an explicit
    # evidence root; a wheel installation is intentionally not treated as a
    # hidden source of recovery evidence.
    return Path(__file__).resolve().parents[3]


def _load_json(path: Path, *, schema: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryCompatibilityError(f"cannot load recovery JSON {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise RecoveryCompatibilityError(
            f"unexpected recovery schema in {path}: {value.get('schema') if isinstance(value, dict) else type(value).__name__}"
        )
    return value


def _exact_target_manifest(recovery: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = (((recovery.get("stage8_overlay_prefix") or {}).get("complete_members")) or [])
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RecoveryCompatibilityError("malformed complete_members recovery row")
        path = str(row.get("path") or "")
        if not path or path in out:
            raise RecoveryCompatibilityError(f"invalid/duplicate recovered target path: {path!r}")
        sha = str(row.get("sha256") or "")
        size = row.get("bytes")
        if len(sha) != 64 or not isinstance(size, int) or size < 0:
            raise RecoveryCompatibilityError(f"invalid recovered target identity for {path}")
        out[path] = {"bytes": size, "sha256": sha}
    return out


def _verify_target_bytes(
    target_root: Path,
    member: str,
    identity: dict[str, Any] | None,
) -> dict[str, Any]:
    path = target_root / PurePosixPath(member)
    if identity is None:
        return {
            "manifested_exact_target": False,
            "available": False,
            "path": str(path),
            "reason": "no_exact_recovery_manifest_identity",
        }
    if not path.is_file():
        raise RecoveryCompatibilityError(
            f"exact recovery manifest requires missing target file: {member}"
        )
    raw = path.read_bytes()
    observed = {"bytes": len(raw), "sha256": _sha256(raw)}
    if observed != identity:
        raise RecoveryCompatibilityError(
            f"exact recovered target bytes drifted for {member}: {observed} != {identity}"
        )
    return {
        "manifested_exact_target": True,
        "available": True,
        "path": str(path),
        "bytes": observed["bytes"],
        "sha256": observed["sha256"],
    }


def _zip_member_name(source: dict[str, Any], logical: str) -> str:
    prefix = str(source.get("archive_prefix") or "").strip("/")
    layout = str(source.get("source_layout") or "")
    if logical.startswith("src/rocketdict/") and layout == "direct":
        relative = logical[len("src/") :]
    else:
        relative = logical
    return f"{prefix}/{relative}" if prefix else relative


def _candidate_overlay_reader(
    candidate: Path,
) -> tuple[dict[str, bytes], dict[str, Any], Any]:
    """Return normalized package files, source metadata and logical-member reader."""
    candidate = candidate.expanduser().resolve()
    if candidate.is_dir():
        package_files, source, source_root = _read_directory(candidate)
        candidate_root = Path(source["candidate_path"])

        def read(logical: str) -> bytes | None:
            if logical.startswith("src/rocketdict/"):
                path = source_root / PurePosixPath(logical).relative_to("src")
            else:
                path = candidate_root / PurePosixPath(logical)
            if not path.is_file() or path.is_symlink():
                return None
            return path.read_bytes()

        return package_files, source, read

    if candidate.is_file() and candidate.suffix.casefold() == ".zip":
        package_files, source, _ = _read_zip(candidate)

        def read(logical: str) -> bytes | None:
            member = _zip_member_name(source, logical)
            with zipfile.ZipFile(candidate) as zf:
                try:
                    info = zf.getinfo(member)
                except KeyError:
                    return None
                if info.is_dir():
                    return None
                if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    raise RecoveryCompatibilityError(
                        f"candidate overlay member exceeds recovery limit: {member} ({info.file_size})"
                    )
                raw = zf.read(info)
                if len(raw) != info.file_size:
                    raise RecoveryCompatibilityError(
                        f"candidate overlay member length mismatch: {member}"
                    )
                return raw

        return package_files, source, read

    raise RecoveryCandidateError(
        "candidate must be a RocketDict source directory or .zip checkpoint"
    )


def _documented_archive_match(
    candidate_report: dict[str, Any], history: dict[str, Any]
) -> dict[str, Any]:
    source = candidate_report.get("candidate") or {}
    documented = history.get("documented_historical_full_checkpoint_candidate") or {}
    observed_sha = source.get("archive_sha256")
    expected_sha = documented.get("archive_sha256")
    if not observed_sha:
        return {
            "applicable": False,
            "match": False,
            "reason": "candidate_is_not_zip_archive",
            "documented_archive_name": documented.get("archive_name"),
            "documented_archive_sha256": expected_sha,
        }
    return {
        "applicable": True,
        "match": observed_sha == expected_sha,
        "observed_archive_sha256": observed_sha,
        "observed_archive_bytes": source.get("archive_bytes"),
        "documented_archive_name": documented.get("archive_name"),
        "documented_archive_sha256": expected_sha,
        "documented_archive_bytes": documented.get("archive_bytes"),
        "documented_version": documented.get("version"),
    }


def build_core_recovery_plan(
    candidate: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
    python: str | Path | None = None,
    probe_runtime: bool = True,
) -> dict[str, Any]:
    candidate_path = Path(candidate).expanduser().resolve()
    target_root = Path(target_evidence_root or (_repo_root() / DEFAULT_TARGET_RELATIVE)).expanduser().resolve()
    if not target_root.is_dir():
        raise RecoveryCompatibilityError(f"target evidence root does not exist: {target_root}")

    history = _load_json(target_root / "core-recovery-history.json", schema=HISTORY_SCHEMA)
    recovery = _load_json(target_root / "recovery.json", schema=RECOVERY_SCHEMA)
    if history.get("promotion_allowed") is not False or recovery.get("promotion_allowed") is not False:
        raise RecoveryCompatibilityError("recovery evidence unexpectedly permits promotion")

    contract = history.get("historical_materializer_contract") or {}
    members = contract.get("expected_overlay_members") or []
    if not isinstance(members, list) or len(members) != int(contract.get("expected_overlay_member_count") or -1):
        raise RecoveryCompatibilityError("historical overlay member inventory/count mismatch")
    members = [str(item) for item in members]
    if len(set(members)) != len(members):
        raise RecoveryCompatibilityError("historical overlay inventory contains duplicates")
    if bool(contract.get("contains_rocketdict_api_package")):
        raise RecoveryCompatibilityError("historical recovery contract unexpectedly claims API package in overlay")

    candidate_report = inspect_core_candidate(
        candidate_path,
        python=python,
        probe_runtime=probe_runtime,
    )
    _, source, read_candidate = _candidate_overlay_reader(candidate_path)
    exact_targets = _exact_target_manifest(recovery)

    rows: list[dict[str, Any]] = []
    for member in sorted(members):
        target = _verify_target_bytes(target_root, member, exact_targets.get(member))
        candidate_raw = read_candidate(member)
        candidate_obs = (
            {
                "present": True,
                "bytes": len(candidate_raw),
                "sha256": _sha256(candidate_raw),
            }
            if candidate_raw is not None
            else {"present": False}
        )
        if target["available"]:
            if candidate_raw is not None and candidate_obs["sha256"] == target["sha256"]:
                action = "exact_target_already_present"
            else:
                action = "exact_replacement_available"
        else:
            action = (
                "replacement_required_but_target_missing"
                if candidate_raw is not None
                else "target_missing_and_candidate_missing"
            )
        rows.append(
            {
                "path": member,
                "candidate": candidate_obs,
                "target": target,
                "action": action,
            }
        )

    exact_available = sum(1 for row in rows if row["target"]["available"])
    target_missing = len(rows) - exact_available
    replacement_available = sum(1 for row in rows if row["action"] == "exact_replacement_available")
    already_exact = sum(1 for row in rows if row["action"] == "exact_target_already_present")

    required_modules = ((candidate_report.get("observed") or {}).get("required_modules") or {})
    api_dependencies = {}
    for name in ("rocketdict.api.contracts", "rocketdict.api.client", "rocketdict.api.cli"):
        row = required_modules.get(name) or {"available": False, "matched_paths": []}
        api_dependencies[name] = {
            "candidate_available": bool(row.get("available")),
            "candidate_paths": list(row.get("matched_paths") or []),
            "target_03040_exact_bytes_recovered": False,
            "compatibility": "unproven_against_exact_0.30.40",
        }

    base_structural_complete = not ((candidate_report.get("observed") or {}).get("missing_required_modules") or [])
    runtime_ok = bool((candidate_report.get("runtime_probe") or {}).get("ok"))
    archive_identity = _documented_archive_match(candidate_report, history)

    if target_missing:
        status = "blocked_missing_exact_overlay_bytes"
    elif not base_structural_complete:
        status = "blocked_incomplete_base_core"
    elif not runtime_ok:
        status = "blocked_base_runtime_unproven"
    else:
        # Even with a full overlay, no exact 0.30.40 API bytes have been recovered.
        status = "blocked_unproven_base_api_compatibility"

    blockers = []
    if target_missing:
        blockers.append(f"missing_exact_overlay_targets:{target_missing}")
    if not base_structural_complete:
        blockers.append("base_required_workbench_modules_missing")
    if not runtime_ok:
        blockers.append("base_runtime_import_probe_not_proven")
    blockers.append("exact_0.30.40_public_api_bytes_not_recovered")
    blockers.append("live_product_verification_not_run")

    identity_payload = {
        "schema": SCHEMA,
        "candidate_fingerprint": ((candidate_report.get("identity") or {}).get("fingerprint")),
        "candidate_archive_sha256": source.get("archive_sha256"),
        "target_history_schema": history["schema"],
        "target_recovery_schema": recovery["schema"],
        "overlay_contract_sha256": contract.get("overlay_tar_gz_sha256"),
        "overlay_rows": [
            {
                "path": row["path"],
                "candidate_sha256": row["candidate"].get("sha256"),
                "target_sha256": row["target"].get("sha256"),
                "target_manifested": row["target"]["manifested_exact_target"],
                "action": row["action"],
            }
            for row in rows
        ],
        "api_dependencies": api_dependencies,
        "status": status,
    }

    return {
        "schema": SCHEMA,
        "status": status,
        "promotion_allowed": False,
        "writes_source": False,
        "candidate": {
            "report_schema": candidate_report.get("schema"),
            "report_status": candidate_report.get("status"),
            "fingerprint": ((candidate_report.get("identity") or {}).get("fingerprint")),
            "rocketdict_version": ((candidate_report.get("observed") or {}).get("rocketdict_version")),
            "source": source,
            "structural_complete_for_workbench_bridge": base_structural_complete,
            "runtime_probe_ok": runtime_ok,
            "documented_archive_identity": archive_identity,
        },
        "target": {
            "evidence_root": str(target_root),
            "history_schema": history["schema"],
            "recovery_schema": recovery["schema"],
            "overlay_tar_gz_sha256": contract.get("overlay_tar_gz_sha256"),
            "overlay_member_count": len(rows),
            "exact_target_available_count": exact_available,
            "exact_target_missing_count": target_missing,
            "exact_target_already_present_count": already_exact,
            "exact_replacement_available_count": replacement_available,
            "public_api_exact_bytes_recovered": False,
        },
        "overlay_plan": rows,
        "base_api_dependencies": api_dependencies,
        "blockers": blockers,
        "identity": {"fingerprint": _canonical_sha(identity_payload)},
        "rule": (
            "This is a read-only recovery plan, not a merger. Any historical Stage8 overlay member "
            "without manifest-backed exact target bytes remains blocked even when an older base has "
            "a file at the same path. The public API is a base-core dependency and cannot be inferred "
            "from the Stage8 overlay. Product dispatch still requires the real Workbench live verification chain."
        ),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-plan",
        description="Read-only deterministic base→0.30.40 recovery compatibility plan",
    )
    p.add_argument("candidate", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--no-runtime-probe", action="store_true")
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = build_core_recovery_plan(
            args.candidate,
            target_evidence_root=args.target_evidence_root,
            python=args.python,
            probe_runtime=not args.no_runtime_probe,
        )
    except (OSError, RecoveryCandidateError, RecoveryCompatibilityError) as exc:
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
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
