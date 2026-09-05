from __future__ import annotations

"""Read-only Python wheel metadata and RECORD verification for recovery.

This module never imports, extracts or installs the candidate. It validates the
wheel container's package metadata, filename tags, ZIP CRC and the mandatory
RECORD inventory/hashes/sizes against the exact archived member bytes.
"""

import base64
import csv
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .core_recovery import RecoveryCandidateError

SCHEMA = "rocketdict-workbench-wheel-integrity/2"
_WHEEL_FILENAME = re.compile(
    r"^(?P<name>.+?)-(?P<version>[^-]+)-(?P<python>[^-]+)-(?P<abi>[^-]+)-(?P<platform>[^-]+)\.whl$",
    re.IGNORECASE,
)


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            total += len(block)
    return digest.hexdigest(), total


def _single_member(names: list[str], suffix: str) -> str | None:
    matches = [name for name in names if name.endswith(suffix)]
    if len(matches) > 1:
        raise RecoveryCandidateError(
            f"wheel contains multiple {suffix} members: {matches}"
        )
    return matches[0] if matches else None


def _parse_wheel_headers(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8")
    headers: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers.setdefault(key.strip(), []).append(value.strip())
    return {
        "wheel_version": (headers.get("Wheel-Version") or [None])[0],
        "generator": (headers.get("Generator") or [None])[0],
        "root_is_purelib": (headers.get("Root-Is-Purelib") or [None])[0],
        "tags": list(headers.get("Tag") or []),
        "build": list(headers.get("Build") or []),
    }


def _normalize_distribution_name(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[-_.]+", "-", value).casefold()


def _filename_identity(path: Path) -> dict[str, Any]:
    match = _WHEEL_FILENAME.match(path.name)
    if not match:
        return {
            "parsed": False,
            "name": None,
            "version": None,
            "python_tag": None,
            "abi_tag": None,
            "platform_tag": None,
            "tag": None,
        }
    python_tag = match.group("python")
    abi_tag = match.group("abi")
    platform_tag = match.group("platform")
    return {
        "parsed": True,
        "name": match.group("name"),
        "version": match.group("version"),
        "python_tag": python_tag,
        "abi_tag": abi_tag,
        "platform_tag": platform_tag,
        "tag": f"{python_tag}-{abi_tag}-{platform_tag}",
    }


def _verify_record(
    zf: zipfile.ZipFile,
    names: list[str],
    record_name: str | None,
) -> dict[str, Any]:
    if record_name is None:
        return {
            "available": False,
            "verified": False,
            "status": "record_missing",
            "entry_count": 0,
            "hashed_entry_count": 0,
            "unhashed_entry_count": 0,
            "unhashed_paths": [],
            "missing_members": [],
            "size_mismatches": [],
            "hash_mismatches": [],
            "unsupported_hash_algorithms": [],
            "duplicate_paths": [],
            "unrecorded_members": sorted(names),
        }

    raw = zf.read(record_name).decode("utf-8")
    rows = list(csv.reader(io.StringIO(raw)))
    seen: set[str] = set()
    duplicate_paths: list[str] = []
    missing_members: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    hash_mismatches: list[dict[str, Any]] = []
    unsupported_hash_algorithms: list[dict[str, Any]] = []
    unhashed: list[str] = []
    hashed_count = 0

    name_set = set(names)
    for row in rows:
        if len(row) != 3:
            raise RecoveryCandidateError(
                f"wheel RECORD row does not have three columns: {row!r}"
            )
        member, digest_spec, size_text = row
        if member in seen:
            duplicate_paths.append(member)
        seen.add(member)
        if member not in name_set:
            missing_members.append(member)
            continue
        info = zf.getinfo(member)
        if size_text:
            try:
                declared_size = int(size_text)
            except ValueError as exc:
                raise RecoveryCandidateError(
                    f"wheel RECORD size is not integer for {member}: {size_text!r}"
                ) from exc
            if declared_size != info.file_size:
                size_mismatches.append(
                    {
                        "path": member,
                        "declared": declared_size,
                        "observed": info.file_size,
                    }
                )
        if not digest_spec:
            unhashed.append(member)
            continue
        if "=" not in digest_spec:
            unsupported_hash_algorithms.append(
                {
                    "path": member,
                    "digest": digest_spec,
                    "reason": "missing_algorithm_separator",
                }
            )
            continue
        algorithm, expected = digest_spec.split("=", 1)
        try:
            digest = hashlib.new(algorithm)
        except ValueError:
            unsupported_hash_algorithms.append(
                {
                    "path": member,
                    "algorithm": algorithm,
                    "reason": "unsupported_algorithm",
                }
            )
            continue
        member_raw = zf.read(member)
        digest.update(member_raw)
        observed = (
            base64.urlsafe_b64encode(digest.digest()).rstrip(b"=").decode("ascii")
        )
        hashed_count += 1
        if observed != expected:
            hash_mismatches.append(
                {
                    "path": member,
                    "algorithm": algorithm,
                    "expected": expected,
                    "observed": observed,
                }
            )

    unrecorded = sorted(name_set - seen)
    verified = not (
        missing_members
        or size_mismatches
        or hash_mismatches
        or unsupported_hash_algorithms
        or duplicate_paths
        or unrecorded
    )
    return {
        "available": True,
        "verified": verified,
        "status": "record_verified" if verified else "record_verification_failed",
        "entry_count": len(rows),
        "hashed_entry_count": hashed_count,
        "unhashed_entry_count": len(unhashed),
        "unhashed_paths": sorted(unhashed),
        "missing_members": sorted(missing_members),
        "size_mismatches": size_mismatches,
        "hash_mismatches": hash_mismatches,
        "unsupported_hash_algorithms": unsupported_hash_algorithms,
        "duplicate_paths": sorted(duplicate_paths),
        "unrecorded_members": unrecorded,
    }


def inspect_wheel_integrity(candidate: Path | str) -> dict[str, Any]:
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or path.suffix.casefold() != ".whl":
        raise RecoveryCandidateError("wheel integrity candidate must be a .whl file")
    if not zipfile.is_zipfile(path):
        raise RecoveryCandidateError("wheel integrity candidate is not a valid ZIP")

    wheel_sha, wheel_bytes = _file_sha256(path)
    filename = _filename_identity(path)
    with zipfile.ZipFile(path) as zf:
        bad_crc = zf.testzip()
        names = [info.filename for info in zf.infolist() if not info.is_dir()]
        metadata_name = _single_member(names, ".dist-info/METADATA")
        wheel_name = _single_member(names, ".dist-info/WHEEL")
        record_name = _single_member(names, ".dist-info/RECORD")
        if metadata_name is None:
            raise RecoveryCandidateError("wheel contains no .dist-info/METADATA")
        if wheel_name is None:
            raise RecoveryCandidateError("wheel contains no .dist-info/WHEEL")

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

    normalized_metadata_name = _normalize_distribution_name(metadata["name"])
    normalized_filename_name = _normalize_distribution_name(filename["name"])
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
    expected_distribution = normalized_metadata_name == "rocketdict"
    filename_tag = filename.get("tag")
    wheel_tags = set(wheel_headers["tags"])
    filename_tag_consistent = bool(filename_tag and filename_tag in wheel_tags)
    py3_none_any = "py3-none-any" in wheel_tags

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

    status = "wheel_integrity_verified" if not hard_failures else "wheel_integrity_failed"
    payload = {
        "schema": SCHEMA,
        "status": status,
        "ok": not hard_failures,
        "promotion_allowed": False,
        "wheel_path": str(path),
        "wheel_sha256": wheel_sha,
        "wheel_bytes": wheel_bytes,
        "zip_crc_ok": bad_crc is None,
        "zip_crc_first_bad_member": bad_crc,
        "member_count": len(names),
        "filename": filename,
        "metadata_member": metadata_name,
        "wheel_member": wheel_name,
        "record_member": record_name,
        "metadata": metadata,
        "wheel": wheel_headers,
        "record": record,
        "distribution_is_rocketdict": expected_distribution,
        "filename_metadata_name_consistent": name_consistent,
        "filename_metadata_version_consistent": version_consistent,
        "filename_wheel_tag_consistent": filename_tag_consistent,
        "py3_none_any_tag_present": py3_none_any,
        "hard_failures": hard_failures,
        "rule": (
            "Wheel metadata/RECORD integrity proves archived package consistency only. "
            "A missing RECORD, CRC failure, package identity mismatch, filename/WHEEL tag "
            "mismatch or RECORD mismatch fails closed. This still does not prove exact "
            "0.30.40 source compatibility or runtime/Product readiness."
        ),
    }
    payload["identity"] = {
        "fingerprint": _canonical_sha(
            {key: value for key, value in payload.items() if key != "identity"}
        )
    }
    return payload
