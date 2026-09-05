from __future__ import annotations

"""Read-only recovery analysis for historical RocketDict Python wheels.

A wheel is a useful recovery source because it can preserve the complete
installed Python package even when the large handoff/checkpoint ZIP is gone.
This module deliberately does *not* install or execute a wheel.  It reuses the
same structural and exact-byte rules as the ZIP/directory recovery path and
produces the same compatibility-plan shape, with runtime proof left blocked
until the wheel is installed in an isolated environment by a later explicit
step.
"""

import argparse
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import zipfile

from .core_compatibility import (
    DEFAULT_TARGET_RELATIVE,
    HISTORY_SCHEMA,
    RECOVERY_SCHEMA,
    SCHEMA as PLAN_SCHEMA,
    RecoveryCompatibilityError,
    _exact_target_manifest,
    _load_json,
    _repo_root,
    _sha256,
    _verify_target_bytes,
    _zip_member_name,
)
from .core_recovery import (
    EXACT_PRODUCT_VERSION,
    MAX_ARCHIVE_MEMBER_BYTES,
    SCHEMA as CANDIDATE_SCHEMA,
    RecoveryCandidateError,
    _canonical_sha,
    _exact_evidence,
    _extract_version,
    _module_presence,
    _read_zip,
    _tree_sha,
)

WHEEL_SCHEMA = "rocketdict-workbench-core-wheel-recovery/1"


def _wheel_path(candidate: Path | str) -> Path:
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or path.suffix.casefold() != ".whl":
        raise RecoveryCandidateError("candidate must be a .whl RocketDict wheel")
    return path


def inspect_wheel_candidate(candidate: Path | str) -> dict[str, Any]:
    """Inspect a wheel without extraction, installation or execution."""
    path = _wheel_path(candidate)
    files, source, _ = _read_zip(path)
    source = dict(source)
    source["kind"] = "wheel"
    source["artifact_format"] = "python-wheel"

    if "src/rocketdict/__init__.py" not in files:
        raise RecoveryCandidateError(
            "wheel package root was detected but RocketDict __init__.py was not read"
        )

    version = _extract_version(files["src/rocketdict/__init__.py"])
    modules = _module_presence(files)
    exact = _exact_evidence(files)
    missing_modules = [name for name, row in modules.items() if not row["available"]]
    exact_matches = [member for member, row in exact.items() if row["match"]]
    exact_mismatches = [member for member, row in exact.items() if not row["match"]]
    package_tree = {
        "python_file_count": len(files),
        "python_bytes": sum(map(len, files.values())),
        "sha256": _tree_sha(files),
    }

    structural_complete = not missing_modules
    exact_version = version == EXACT_PRODUCT_VERSION
    exact_recovered_files_match = not exact_mismatches
    if structural_complete and exact_version and exact_recovered_files_match:
        status = "exact_version_structural_candidate"
    elif structural_complete:
        status = "base_candidate_requires_compatibility_proof"
    else:
        status = "incomplete_candidate"

    promotion_blockers: list[str] = []
    if not structural_complete:
        promotion_blockers.append("required_workbench_bridge_modules_missing")
    if not exact_version:
        promotion_blockers.append("candidate_is_not_exact_0.30.40")
    if not exact_recovered_files_match:
        promotion_blockers.append(
            "candidate_disagrees_with_exact_recovered_0.30.40_bytes"
        )
    promotion_blockers.extend(
        [
            "runtime_import_probe_not_proven",
            "wheel_not_installed_or_executed_by_recovery_verifier",
            "live_product_preflight_api_probe_and_execution_binding_not_run",
        ]
    )

    runtime = {
        "attempted": False,
        "ok": False,
        "reason": (
            "wheel_is_structural_evidence_only_install_into_isolated_environment_"
            "before_runtime_probe"
        ),
    }
    evidence: dict[str, Any] = {
        "schema": CANDIDATE_SCHEMA,
        "status": status,
        "promotion_allowed": False,
        "candidate": source,
        "observed": {
            "rocketdict_version": version,
            "package_tree": package_tree,
            "required_modules": modules,
            "missing_required_modules": missing_modules,
            "exact_recovered_03040_files": exact,
            "exact_recovered_match_paths": exact_matches,
            "exact_recovered_mismatch_paths": exact_mismatches,
        },
        "runtime_probe": runtime,
        "promotion_blockers": promotion_blockers,
        "promotion_rule": (
            "A wheel can prove packaged source structure and hashes, not runtime compatibility. "
            "Promotion still requires an isolated installation followed by Workbench doctor, "
            "immutable Product preflight, live registry/API probe, exact callable binding and "
            "execution-contract verification."
        ),
    }
    evidence["identity"] = {
        "fingerprint": _canonical_sha(
            {
                "schema": CANDIDATE_SCHEMA,
                "candidate_kind": "wheel",
                "candidate_archive_sha256": source.get("archive_sha256"),
                "rocketdict_version": version,
                "package_tree_sha256": package_tree["sha256"],
                "required_modules": {
                    key: row["matched_paths"] for key, row in modules.items()
                },
                "exact_recovered_03040_files": {
                    key: {
                        "present": row["present"],
                        "observed_sha256": row.get("observed_sha256"),
                        "match": row["match"],
                    }
                    for key, row in exact.items()
                },
                "runtime": {"attempted": False, "ok": False},
            }
        )
    }
    return evidence


def _wheel_overlay_reader(
    candidate: Path,
    source: dict[str, Any],
):
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
                    f"wheel member exceeds recovery limit: {member} ({info.file_size})"
                )
            raw = zf.read(info)
            if len(raw) != info.file_size:
                raise RecoveryCompatibilityError(
                    f"wheel member length mismatch: {member}"
                )
            return raw

    return read


def build_wheel_recovery_plan(
    candidate: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
) -> dict[str, Any]:
    """Build the normal base→0.30.40 plan from packaged wheel source bytes."""
    candidate_path = _wheel_path(candidate)
    target_root = Path(
        target_evidence_root or (_repo_root() / DEFAULT_TARGET_RELATIVE)
    ).expanduser().resolve()
    if not target_root.is_dir():
        raise RecoveryCompatibilityError(
            f"target evidence root does not exist: {target_root}"
        )

    history = _load_json(target_root / "core-recovery-history.json", schema=HISTORY_SCHEMA)
    recovery = _load_json(target_root / "recovery.json", schema=RECOVERY_SCHEMA)
    if history.get("promotion_allowed") is not False or recovery.get("promotion_allowed") is not False:
        raise RecoveryCompatibilityError("recovery evidence unexpectedly permits promotion")

    contract = history.get("historical_materializer_contract") or {}
    members = contract.get("expected_overlay_members") or []
    if not isinstance(members, list) or len(members) != int(
        contract.get("expected_overlay_member_count") or -1
    ):
        raise RecoveryCompatibilityError(
            "historical overlay member inventory/count mismatch"
        )
    members = [str(item) for item in members]
    if len(set(members)) != len(members):
        raise RecoveryCompatibilityError(
            "historical overlay inventory contains duplicates"
        )
    if bool(contract.get("contains_rocketdict_api_package")):
        raise RecoveryCompatibilityError(
            "historical recovery contract unexpectedly claims API package in overlay"
        )

    candidate_report = inspect_wheel_candidate(candidate_path)
    source = dict(candidate_report["candidate"])
    read_candidate = _wheel_overlay_reader(candidate_path, source)
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
    replacement_available = sum(
        1 for row in rows if row["action"] == "exact_replacement_available"
    )
    already_exact = sum(
        1 for row in rows if row["action"] == "exact_target_already_present"
    )

    required_modules = (
        (candidate_report.get("observed") or {}).get("required_modules") or {}
    )
    api_dependencies: dict[str, Any] = {}
    for name in (
        "rocketdict.api.contracts",
        "rocketdict.api.client",
        "rocketdict.api.cli",
    ):
        row = required_modules.get(name) or {"available": False, "matched_paths": []}
        api_dependencies[name] = {
            "candidate_available": bool(row.get("available")),
            "candidate_paths": list(row.get("matched_paths") or []),
            "target_03040_exact_bytes_recovered": False,
            "compatibility": "unproven_against_exact_0.30.40",
        }

    base_structural_complete = not (
        (candidate_report.get("observed") or {}).get("missing_required_modules") or []
    )
    runtime_ok = False
    if target_missing:
        status = "blocked_missing_exact_overlay_bytes"
    elif not base_structural_complete:
        status = "blocked_incomplete_base_core"
    else:
        status = "blocked_base_runtime_unproven"

    blockers: list[str] = []
    if target_missing:
        blockers.append(f"missing_exact_overlay_targets:{target_missing}")
    if not base_structural_complete:
        blockers.append("base_required_workbench_modules_missing")
    blockers.extend(
        [
            "base_runtime_import_probe_not_proven",
            "wheel_requires_isolated_installation_before_runtime_probe",
            "exact_0.30.40_public_api_bytes_not_recovered",
            "live_product_verification_not_run",
        ]
    )

    identity_payload = {
        "schema": PLAN_SCHEMA,
        "candidate_fingerprint": (
            (candidate_report.get("identity") or {}).get("fingerprint")
        ),
        "candidate_archive_sha256": source.get("archive_sha256"),
        "candidate_kind": "wheel",
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
        "schema": PLAN_SCHEMA,
        "status": status,
        "promotion_allowed": False,
        "writes_source": False,
        "candidate": {
            "report_schema": candidate_report.get("schema"),
            "report_status": candidate_report.get("status"),
            "fingerprint": (
                (candidate_report.get("identity") or {}).get("fingerprint")
            ),
            "rocketdict_version": (
                (candidate_report.get("observed") or {}).get("rocketdict_version")
            ),
            "source": source,
            "structural_complete_for_workbench_bridge": base_structural_complete,
            "runtime_probe_ok": runtime_ok,
            "documented_archive_identity": {
                "applicable": False,
                "match": False,
                "reason": "candidate_is_wheel_artifact",
            },
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
            "This is read-only wheel recovery evidence. Packaged historical source can "
            "establish base structure and hashes, but cannot substitute for missing exact "
            "0.30.40 overlay/API bytes or for a real isolated runtime verification chain."
        ),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-wheel",
        description="Read-only RocketDict wheel structural and 0.30.40 recovery analysis",
    )
    p.add_argument("candidate", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        plan = build_wheel_recovery_plan(
            args.candidate,
            target_evidence_root=args.target_evidence_root,
        )
        report = {
            "schema": WHEEL_SCHEMA,
            "status": "completed",
            "promotion_allowed": False,
            "candidate": inspect_wheel_candidate(args.candidate),
            "compatibility_plan": plan,
        }
    except (
        OSError,
        RecoveryCandidateError,
        RecoveryCompatibilityError,
        zipfile.BadZipFile,
    ) as exc:
        report = {
            "schema": WHEEL_SCHEMA,
            "status": "error",
            "promotion_allowed": False,
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
