from __future__ import annotations

"""Read-only recovery proof for a full historical RocketDict checkpoint ZIP.

A full checkpoint may preserve much more than the installable package: exact
source, the built RocketDict wheel, reports, manifests and continuation files.
This verifier never extracts or executes the checkpoint. It inventories the
outer ZIP, verifies historical catalog identity, reads the unique RocketDict
source package, validates any nested RocketDict wheel in memory, binds that
nested wheel to the historical catalog when an exact wheel identity exists,
compares source↔wheel package bytes, records public-API hashes, and attaches the
existing historical-base→0.30.40 compatibility plan.
"""

import argparse
from email.parser import BytesParser
from email.policy import default as email_policy
import fnmatch
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import zipfile

from .core_compatibility import RecoveryCompatibilityError, build_core_recovery_plan
from .core_recovery import (
    MAX_ARCHIVE_MEMBER_BYTES,
    MAX_ARCHIVE_PACKAGE_BYTES,
    RecoveryCandidateError,
    _canonical_sha,
    _extract_version,
    _safe_archive_name,
    _sha256_file,
)
from .core_scan import _checkpoint_matches, _load_checkpoint_catalog
from .core_wheel_integrity import (
    SCHEMA as WHEEL_INTEGRITY_SCHEMA,
    _filename_identity,
    _normalize_distribution_name,
    _parse_wheel_headers,
    _single_member,
    _verify_record,
)

SCHEMA = "rocketdict-workbench-full-checkpoint-recovery/2"
MAX_NESTED_WHEEL_BYTES = 64 * 1024 * 1024
MAX_EVIDENCE_MEMBER_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE_MEMBERS = 200

_API_LOGICAL_PATHS = (
    "src/rocketdict/api/contracts.py",
    "src/rocketdict/api/client.py",
    "src/rocketdict/api/cli.py",
)
_EVIDENCE_RE = re.compile(
    r"(?:^|/)(?:readme|continue|handoff|manifest|report|state|.*sha256.*|.*stage6y.*)(?:\.[^/]*)?$",
    re.IGNORECASE,
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_roots(names: list[str]) -> list[dict[str, str]]:
    candidates: list[tuple[str, str]] = []
    for name in names:
        parts = PurePosixPath(name).parts
        if len(parts) >= 3 and parts[-3:] == ("src", "rocketdict", "__init__.py"):
            candidates.append(("/".join(parts[:-3]), "src"))
        if len(parts) >= 2 and parts[-2:] == ("rocketdict", "__init__.py"):
            if len(parts) >= 3 and parts[-3] == "src":
                continue
            candidates.append(("/".join(parts[:-2]), "direct"))
    unique: list[tuple[str, str]] = []
    for row in candidates:
        if row not in unique:
            unique.append(row)
    return [{"prefix": prefix, "layout": layout} for prefix, layout in unique]


def _logical_source_member(name: str, root: dict[str, str]) -> str | None:
    parts = PurePosixPath(name).parts
    prefix_parts = PurePosixPath(root["prefix"]).parts if root["prefix"] else ()
    if parts[: len(prefix_parts)] != prefix_parts:
        return None
    rest = parts[len(prefix_parts) :]
    if root["layout"] == "src":
        if len(rest) < 3 or rest[:2] != ("src", "rocketdict"):
            return None
        logical = PurePosixPath(*rest).as_posix()
    else:
        if len(rest) < 2 or rest[0] != "rocketdict":
            return None
        logical = PurePosixPath("src", *rest).as_posix()
    return logical


def _read_source_package(
    zf: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    root: dict[str, str],
) -> dict[str, bytes]:
    selected: list[tuple[zipfile.ZipInfo, str]] = []
    total = 0
    for info in infos:
        logical = _logical_source_member(info.filename, root)
        if logical is None:
            continue
        if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
            raise RecoveryCandidateError(
                f"checkpoint source member exceeds recovery limit: {info.filename} ({info.file_size})"
            )
        total += int(info.file_size)
        if total > MAX_ARCHIVE_PACKAGE_BYTES:
            raise RecoveryCandidateError(
                f"checkpoint RocketDict source package exceeds recovery limit: {total}"
            )
        selected.append((info, logical))

    files: dict[str, bytes] = {}
    for info, logical in selected:
        raw = zf.read(info)
        if len(raw) != info.file_size:
            raise RecoveryCandidateError(
                f"checkpoint source member length mismatch: {info.filename}"
            )
        if logical in files:
            raise RecoveryCandidateError(
                f"checkpoint maps multiple source members to {logical}"
            )
        files[logical] = raw
    return files


def _wheel_package_files(zf: zipfile.ZipFile) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    total = 0
    for info in zf.infolist():
        if info.is_dir():
            continue
        parts = PurePosixPath(info.filename).parts
        if len(parts) < 2 or parts[0] != "rocketdict":
            continue
        if not _safe_archive_name(info.filename):
            raise RecoveryCandidateError(
                f"nested wheel contains unsafe member: {info.filename}"
            )
        if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
            raise RecoveryCandidateError(
                f"nested wheel package member exceeds recovery limit: {info.filename}"
            )
        total += int(info.file_size)
        if total > MAX_ARCHIVE_PACKAGE_BYTES:
            raise RecoveryCandidateError(
                f"nested wheel RocketDict package exceeds recovery limit: {total}"
            )
        logical = PurePosixPath("src", *parts).as_posix()
        if logical in files:
            raise RecoveryCandidateError(
                f"nested wheel maps multiple members to {logical}"
            )
        raw = zf.read(info)
        if len(raw) != info.file_size:
            raise RecoveryCandidateError(
                f"nested wheel member length mismatch: {info.filename}"
            )
        files[logical] = raw
    return files


def _wheel_catalog_matches(
    basename: str,
    wheel_sha256: str,
    wheel_bytes: int,
    catalog: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if catalog is None:
        return []
    lowered = basename.casefold()
    matches: list[dict[str, Any]] = []
    for row in catalog.get("entries") or []:
        patterns = list(row.get("wheel_name_patterns") or [])
        matched_patterns = [
            pattern
            for pattern in patterns
            if fnmatch.fnmatchcase(lowered, pattern.casefold())
        ]
        if not matched_patterns:
            continue
        expected_sha = row.get("wheel_sha256")
        expected_bytes = row.get("wheel_bytes")
        exact_identity_available = expected_sha is not None
        sha_match = bool(
            exact_identity_available
            and wheel_sha256.casefold() == str(expected_sha).casefold()
        )
        size_match = bool(expected_bytes is None or wheel_bytes == expected_bytes)
        exact_identity_match = bool(sha_match and size_match)
        matches.append(
            {
                "catalog_id": row.get("id"),
                "version": row.get("version"),
                "stage": row.get("stage"),
                "candidate_role": row.get("candidate_role"),
                "evidence_level": row.get("evidence_level"),
                "matched_patterns": matched_patterns,
                "name_match": True,
                "exact_identity_available": exact_identity_available,
                "exact_identity_match": exact_identity_match,
                "exact_identity_mismatch": bool(
                    exact_identity_available and not exact_identity_match
                ),
                "sha256_match": sha_match,
                "size_constraint_available": expected_bytes is not None,
                "size_match": size_match,
                "expected_wheel_sha256": expected_sha,
                "expected_wheel_bytes": expected_bytes,
                "observed_wheel_sha256": wheel_sha256,
                "observed_wheel_bytes": wheel_bytes,
                "promotion_allowed": False,
            }
        )
    matches.sort(
        key=lambda row: (
            1 if row["exact_identity_match"] else 0,
            str(row.get("version") or ""),
            str(row.get("catalog_id") or ""),
        ),
        reverse=True,
    )
    return matches


def _inspect_nested_wheel(raw: bytes, logical_name: str) -> dict[str, Any]:
    basename = PurePosixPath(logical_name).name
    wheel_sha = _sha256(raw)
    filename = _filename_identity(Path(basename))
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise RecoveryCandidateError(
                f"nested wheel contains duplicate member names: {logical_name}"
            )
        unsafe = [name for name in names if not _safe_archive_name(name)]
        if unsafe:
            raise RecoveryCandidateError(
                f"nested wheel contains unsafe members: {logical_name}: {unsafe[:10]}"
            )
        bad_crc = zf.testzip()
        metadata_name = _single_member(names, ".dist-info/METADATA")
        wheel_name = _single_member(names, ".dist-info/WHEEL")
        record_name = _single_member(names, ".dist-info/RECORD")
        if metadata_name is None:
            raise RecoveryCandidateError(
                f"nested wheel contains no .dist-info/METADATA: {logical_name}"
            )
        if wheel_name is None:
            raise RecoveryCandidateError(
                f"nested wheel contains no .dist-info/WHEEL: {logical_name}"
            )
        message = BytesParser(policy=email_policy).parsebytes(zf.read(metadata_name))
        metadata = {
            "metadata_version": message.get("Metadata-Version"),
            "name": message.get("Name"),
            "version": message.get("Version"),
            "requires_python": message.get("Requires-Python"),
            "requires_dist": list(message.get_all("Requires-Dist") or []),
            "provides_extra": list(message.get_all("Provides-Extra") or []),
        }
        wheel_headers = _parse_wheel_headers(zf.read(wheel_name))
        record = _verify_record(zf, names, record_name)
        package_files = _wheel_package_files(zf)

    normalized_metadata_name = _normalize_distribution_name(metadata["name"])
    normalized_filename_name = _normalize_distribution_name(filename["name"])
    expected_distribution = normalized_metadata_name == "rocketdict"
    name_consistent = bool(
        filename["parsed"]
        and normalized_metadata_name
        and normalized_metadata_name == normalized_filename_name
    )
    version_consistent = bool(
        filename["parsed"]
        and metadata["version"]
        and str(metadata["version"]) == str(filename["version"])
    )
    filename_tag = filename.get("tag")
    filename_tag_consistent = bool(
        filename_tag and filename_tag in set(wheel_headers["tags"])
    )

    hard_failures: list[str] = []
    if bad_crc is not None:
        hard_failures.append("zip_crc_failure")
    if not expected_distribution:
        hard_failures.append("metadata_distribution_is_not_rocketdict")
    if not name_consistent:
        hard_failures.append("filename_metadata_name_mismatch")
    if not version_consistent:
        hard_failures.append("filename_metadata_version_mismatch")
    if not filename_tag_consistent:
        hard_failures.append("filename_wheel_tag_mismatch")
    if not record["available"]:
        hard_failures.append("wheel_record_missing")
    elif not record["verified"]:
        hard_failures.append("wheel_record_verification_failed")

    payload = {
        "schema": WHEEL_INTEGRITY_SCHEMA,
        "logical_path": logical_name,
        "basename": basename,
        "wheel_sha256": wheel_sha,
        "wheel_bytes": len(raw),
        "member_count": len(names),
        "zip_crc_ok": bad_crc is None,
        "zip_crc_first_bad_member": bad_crc,
        "filename": filename,
        "metadata": metadata,
        "wheel": wheel_headers,
        "record": record,
        "distribution_is_rocketdict": expected_distribution,
        "filename_metadata_name_consistent": name_consistent,
        "filename_metadata_version_consistent": version_consistent,
        "filename_wheel_tag_consistent": filename_tag_consistent,
        "package_file_count": len(package_files),
        "package_bytes": sum(map(len, package_files.values())),
        "hard_failures": hard_failures,
        "ok": not hard_failures,
        "promotion_allowed": False,
    }
    payload["identity"] = {
        "fingerprint": _canonical_sha(
            {key: value for key, value in payload.items() if key != "identity"}
        )
    }
    payload["_package_files"] = package_files
    return payload


def _parity(source: dict[str, bytes], wheel: dict[str, bytes]) -> dict[str, Any]:
    source_keys = set(source)
    wheel_keys = set(wheel)
    source_only = sorted(source_keys - wheel_keys)
    wheel_only = sorted(wheel_keys - source_keys)
    mismatches: list[dict[str, Any]] = []
    for path in sorted(source_keys & wheel_keys):
        source_raw = source[path]
        wheel_raw = wheel[path]
        if source_raw != wheel_raw:
            mismatches.append(
                {
                    "path": path,
                    "source_bytes": len(source_raw),
                    "wheel_bytes": len(wheel_raw),
                    "source_sha256": _sha256(source_raw),
                    "wheel_sha256": _sha256(wheel_raw),
                }
            )
    return {
        "complete": not source_only and not wheel_only and not mismatches,
        "source_file_count": len(source),
        "wheel_file_count": len(wheel),
        "source_only_count": len(source_only),
        "wheel_only_count": len(wheel_only),
        "content_mismatch_count": len(mismatches),
        "source_only": source_only,
        "wheel_only": wheel_only,
        "content_mismatches": mismatches,
    }


def _api_inventory(files: dict[str, bytes]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path in _API_LOGICAL_PATHS:
        raw = files.get(path)
        out[path] = (
            {
                "present": True,
                "bytes": len(raw),
                "sha256": _sha256(raw),
            }
            if raw is not None
            else {"present": False}
        )
    return out


def _api_complete(inventory: dict[str, Any]) -> bool:
    return all(bool((inventory.get(path) or {}).get("present")) for path in _API_LOGICAL_PATHS)


def _evidence_inventory(
    zf: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for info in sorted(infos, key=lambda item: item.filename.casefold()):
        if len(rows) >= MAX_EVIDENCE_MEMBERS:
            break
        if not _EVIDENCE_RE.search(info.filename):
            continue
        row: dict[str, Any] = {
            "path": info.filename,
            "bytes": info.file_size,
            "compressed_bytes": info.compress_size,
        }
        if info.file_size <= MAX_EVIDENCE_MEMBER_BYTES:
            raw = zf.read(info)
            row["sha256"] = _sha256(raw)
        else:
            row["sha256"] = None
            row["hash_skipped"] = "evidence_member_over_hash_limit"
        rows.append(row)
    return rows


def inspect_full_checkpoint(
    candidate: Path | str,
    *,
    checkpoint_catalog: Path | str | None = None,
    target_evidence_root: Path | str | None = None,
) -> dict[str, Any]:
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or path.suffix.casefold() != ".zip":
        raise RecoveryCandidateError("full checkpoint candidate must be a .zip file")
    if not zipfile.is_zipfile(path):
        raise RecoveryCandidateError("full checkpoint candidate is not a valid ZIP")

    archive_sha = _sha256_file(path)
    archive_bytes = path.stat().st_size
    catalog, catalog_identity = _load_checkpoint_catalog(
        target_evidence_root=target_evidence_root,
        checkpoint_catalog=checkpoint_catalog,
    )
    catalog_matches = _checkpoint_matches(
        path,
        {
            "kind": "zip",
            "archive_sha256": archive_sha,
            "archive_bytes": archive_bytes,
        },
        catalog,
    )
    known_name = bool(catalog_matches)
    exact_catalog_match = any(row["exact_identity_match"] for row in catalog_matches)
    exact_catalog_mismatch = bool(
        known_name
        and any(row["exact_identity_available"] for row in catalog_matches)
        and not exact_catalog_match
    )

    with zipfile.ZipFile(path) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise RecoveryCandidateError("checkpoint ZIP contains duplicate member names")
        unsafe = [name for name in names if not _safe_archive_name(name)]
        if unsafe:
            raise RecoveryCandidateError(
                f"checkpoint ZIP contains unsafe member names: {unsafe[:10]}"
            )
        bad_crc = zf.testzip()
        roots = _source_roots(names)
        source_files: dict[str, bytes] = {}
        if len(roots) == 1:
            source_files = _read_source_package(zf, infos, roots[0])

        nested_infos = [
            info
            for info in infos
            if PurePosixPath(info.filename).name.casefold().startswith("rocketdict-")
            and info.filename.casefold().endswith(".whl")
        ]
        nested_wheels: list[dict[str, Any]] = []
        for info in nested_infos:
            if info.file_size > MAX_NESTED_WHEEL_BYTES:
                nested_wheels.append(
                    {
                        "logical_path": info.filename,
                        "basename": PurePosixPath(info.filename).name,
                        "wheel_bytes": info.file_size,
                        "ok": False,
                        "historical_catalog_matches": [],
                        "historical_catalog_name_match": False,
                        "historical_catalog_exact_identity_match": False,
                        "historical_catalog_exact_identity_mismatch": False,
                        "promotion_allowed": False,
                        "hard_failures": ["nested_wheel_over_recovery_size_limit"],
                    }
                )
                continue
            raw = zf.read(info)
            if len(raw) != info.file_size:
                raise RecoveryCandidateError(
                    f"nested wheel length mismatch: {info.filename}"
                )
            wheel = _inspect_nested_wheel(raw, info.filename)
            package_files = wheel.pop("_package_files")
            wheel_matches = _wheel_catalog_matches(
                wheel["basename"],
                wheel["wheel_sha256"],
                wheel["wheel_bytes"],
                catalog,
            )
            wheel["historical_catalog_matches"] = wheel_matches
            wheel["historical_catalog_name_match"] = bool(wheel_matches)
            wheel["historical_catalog_exact_identity_match"] = any(
                row["exact_identity_match"] for row in wheel_matches
            )
            wheel["historical_catalog_exact_identity_mismatch"] = bool(
                wheel_matches
                and any(row["exact_identity_available"] for row in wheel_matches)
                and not wheel["historical_catalog_exact_identity_match"]
            )
            wheel["source_parity"] = (
                _parity(source_files, package_files)
                if len(roots) == 1
                else {
                    "complete": False,
                    "status": "source_root_not_unique",
                }
            )
            wheel["api_inventory"] = _api_inventory(package_files)
            wheel["api_complete"] = _api_complete(wheel["api_inventory"])
            nested_wheels.append(wheel)

        evidence = _evidence_inventory(zf, infos)
        other_wheel_count = sum(
            1
            for info in infos
            if info.filename.casefold().endswith(".whl") and info not in nested_infos
        )

    source_version = (
        _extract_version(source_files.get("src/rocketdict/__init__.py", b""))
        if source_files
        else None
    )
    source_api = _api_inventory(source_files) if source_files else {
        api_path: {"present": False} for api_path in _API_LOGICAL_PATHS
    }
    source_api_complete = _api_complete(source_api)

    core_candidate: dict[str, Any] | None = None
    compatibility_plan: dict[str, Any] | None = None
    core_error: dict[str, str] | None = None
    if len(roots) == 1:
        try:
            compatibility_plan = build_core_recovery_plan(
                path,
                target_evidence_root=target_evidence_root,
                probe_runtime=False,
            )
            core_candidate = compatibility_plan.get("candidate")
        except (OSError, RecoveryCandidateError, RecoveryCompatibilityError, zipfile.BadZipFile) as exc:
            core_error = {"type": type(exc).__name__, "error": str(exc)}

    blockers: list[str] = []
    if bad_crc is not None:
        blockers.append("checkpoint_zip_crc_failure")
    if exact_catalog_mismatch:
        blockers.append("historical_catalog_exact_identity_mismatch")
    if len(roots) == 0:
        blockers.append("rocketdict_source_root_missing")
    elif len(roots) > 1:
        blockers.append("rocketdict_source_root_ambiguous")
    if core_error:
        blockers.append("generic_core_compatibility_plan_failed")
    if any(not bool(wheel.get("ok")) for wheel in nested_wheels):
        blockers.append("nested_rocketdict_wheel_integrity_failed")
    if any(
        bool(wheel.get("historical_catalog_exact_identity_mismatch"))
        for wheel in nested_wheels
    ):
        blockers.append("nested_rocketdict_wheel_historical_catalog_exact_identity_mismatch")
    if any(
        not bool((wheel.get("source_parity") or {}).get("complete"))
        for wheel in nested_wheels
    ):
        blockers.append("source_wheel_parity_incomplete")

    if blockers:
        status = "blocked_checkpoint_candidate"
    elif exact_catalog_match:
        status = "exact_historical_checkpoint_candidate"
    else:
        status = "unverified_historical_checkpoint_candidate"

    payload = {
        "schema": SCHEMA,
        "status": status,
        "promotion_allowed": False,
        "product_execution_allowed": False,
        "checkpoint": {
            "path": str(path),
            "basename": path.name,
            "sha256": archive_sha,
            "bytes": archive_bytes,
            "member_count": len(names),
            "zip_crc_ok": bad_crc is None,
            "zip_crc_first_bad_member": bad_crc,
        },
        "checkpoint_catalog": catalog_identity,
        "historical_checkpoint_matches": catalog_matches,
        "historical_checkpoint_name_match": known_name,
        "historical_checkpoint_exact_identity_match": exact_catalog_match,
        "source_roots": roots,
        "source_root_unique": len(roots) == 1,
        "source": {
            "version": source_version,
            "package_file_count": len(source_files),
            "package_bytes": sum(map(len, source_files.values())),
            "api_inventory": source_api,
            "api_complete": source_api_complete,
        },
        "nested_rocketdict_wheel_count": len(nested_wheels),
        "nested_rocketdict_wheel_integrity_ok_count": sum(
            1 for wheel in nested_wheels if wheel.get("ok")
        ),
        "nested_rocketdict_wheel_catalog_exact_match_count": sum(
            1
            for wheel in nested_wheels
            if wheel.get("historical_catalog_exact_identity_match")
        ),
        "nested_rocketdict_wheel_catalog_exact_mismatch_count": sum(
            1
            for wheel in nested_wheels
            if wheel.get("historical_catalog_exact_identity_mismatch")
        ),
        "source_wheel_parity_complete_count": sum(
            1
            for wheel in nested_wheels
            if (wheel.get("source_parity") or {}).get("complete")
        ),
        "other_wheel_count": other_wheel_count,
        "nested_rocketdict_wheels": nested_wheels,
        "evidence_inventory_count": len(evidence),
        "evidence_inventory": evidence,
        "core_candidate": core_candidate,
        "compatibility_plan": compatibility_plan,
        "core_plan_error": core_error,
        "blockers": blockers,
        "rule": (
            "This proof is read-only and never executes or extracts checkpoint bytes. Exact "
            "historical ZIP identity, exact nested-wheel identity, source↔wheel parity and "
            "historical API hashes still do not substitute for missing exact 0.30.40 targets "
            "or authorize Product execution."
        ),
    }
    payload["identity"] = {
        "fingerprint": _canonical_sha(
            {key: value for key, value in payload.items() if key != "identity"}
        )
    }
    return payload


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-checkpoint",
        description="Read-only full RocketDict checkpoint ZIP recovery proof",
    )
    p.add_argument("candidate", type=Path)
    p.add_argument("--checkpoint-catalog", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = inspect_full_checkpoint(
            args.candidate,
            checkpoint_catalog=args.checkpoint_catalog,
            target_evidence_root=args.target_evidence_root,
        )
    except (OSError, RecoveryCandidateError, RecoveryCompatibilityError, zipfile.BadZipFile) as exc:
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
