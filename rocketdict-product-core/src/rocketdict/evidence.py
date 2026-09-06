from __future__ import annotations

"""Fail-closed discovery of Product downstream evidence sources.

CEFR-J is an explicit pinned external asset.  It is never downloaded during
processing.  CMUdict is supplied by the installed ``cmudict`` Python package;
its package version and resource identity are exposed for audit and generated
pronunciation fallback is never enabled by this module.
"""

import csv
import hashlib
import importlib.metadata
import importlib.util
import os
from pathlib import Path
from typing import Any

CEFRJ_URL = (
    "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/"
    "master/cefrj-vocabulary-profile-1.5.csv"
)
CEFRJ_SHA256 = "b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498"
CEFRJ_BYTES = 233214
CEFRJ_ROWS = 7799
CEFRJ_HEADER = [
    "headword",
    "pos",
    "CEFR",
    "CoreInventory 1",
    "CoreInventory 2",
    "Threshold",
]
CEFRJ_ASSET_ENV = "ROCKETDICT_CEFRJ_ASSET"


def file_sha256(path: Path | str) -> str:
    path = Path(path).expanduser().resolve()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_cefrj_asset(path: Path | str | None = None) -> dict[str, Any]:
    raw_path = str(path or os.environ.get(CEFRJ_ASSET_ENV) or "").strip()
    if not raw_path:
        raise RuntimeError(
            f"Pinned CEFR-J asset is not configured; set {CEFRJ_ASSET_ENV} to "
            "cefrj-vocabulary-profile-1.5.csv"
        )
    asset = Path(raw_path).expanduser().resolve()
    if not asset.is_file():
        raise RuntimeError(f"CEFR-J asset is missing: {asset}")
    actual_sha = file_sha256(asset)
    if actual_sha != CEFRJ_SHA256:
        raise RuntimeError(
            f"CEFR-J asset SHA-256 mismatch: {actual_sha} != {CEFRJ_SHA256}"
        )
    actual_bytes = asset.stat().st_size
    if actual_bytes != CEFRJ_BYTES:
        raise RuntimeError(
            f"CEFR-J asset byte size mismatch: {actual_bytes} != {CEFRJ_BYTES}"
        )
    with asset.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CEFRJ_HEADER:
            raise RuntimeError(
                f"CEFR-J asset columns changed: {reader.fieldnames!r} != {CEFRJ_HEADER!r}"
            )
        rows = sum(1 for _ in reader)
    if rows != CEFRJ_ROWS:
        raise RuntimeError(f"CEFR-J row count mismatch: {rows} != {CEFRJ_ROWS}")
    return {
        "available": True,
        "dataset": "CEFR-J Vocabulary Profile 1.5",
        "path": str(asset),
        "sha256": actual_sha,
        "bytes": actual_bytes,
        "rows": rows,
        "source_url": CEFRJ_URL,
        "network_used": False,
        "builtin_smoke_used": False,
        "frequency_inference_used": False,
    }


def cefrj_status() -> dict[str, Any]:
    try:
        verified = verify_cefrj_asset()
    except Exception as exc:
        return {
            "available": False,
            "reason": "missing_or_invalid_pinned_cefrj_asset",
            "asset_error": str(exc),
            "sha256": CEFRJ_SHA256,
            "rows": CEFRJ_ROWS,
            "bytes": CEFRJ_BYTES,
            "offline": True,
        }
    return {
        **verified,
        "reason": "ready",
        "offline": True,
    }


def cmudict_status() -> dict[str, Any]:
    available = importlib.util.find_spec("cmudict") is not None
    version = None
    if available:
        try:
            version = importlib.metadata.version("cmudict")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
    return {
        "available": available,
        "reason": "ready" if available else "cmudict_package_not_installed",
        "package": "cmudict",
        "package_version": version,
        "generated_fallback_allowed": False,
        "offline": True,
    }


def load_cefrj_rows(path: Path | str | None = None) -> tuple[dict[str, Any], list[dict[str, str]]]:
    verified = verify_cefrj_asset(path)
    asset = Path(str(verified["path"]))
    with asset.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if len(rows) != CEFRJ_ROWS:
        raise RuntimeError("CEFR-J rows changed after verification")
    return verified, rows


def load_cmudict() -> tuple[dict[str, Any], dict[str, list[list[str]]]]:
    status = cmudict_status()
    if not status["available"]:
        raise RuntimeError(f"Exact CMUdict evidence is unavailable: {status}")
    import cmudict

    data = cmudict.dict()
    if not isinstance(data, dict) or not data:
        raise RuntimeError("CMUdict package returned an empty/non-dictionary resource")
    normalized: dict[str, list[list[str]]] = {}
    for key, variants in data.items():
        normalized[str(key).casefold()] = [list(map(str, variant)) for variant in variants]
    return status, normalized
