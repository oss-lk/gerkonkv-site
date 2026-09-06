from __future__ import annotations

"""Fail-closed discovery and matching of Product downstream evidence sources.

CEFR-J is an explicit pinned external asset. It is never downloaded during
processing. CMUdict is supplied by the installed ``cmudict`` Python package.
Both sources may be cached process-locally only after their exact evidence
identity has been verified. Generated pronunciation fallback is never enabled.
"""

import csv
from functools import lru_cache
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

# Deliberately conservative mapping from Universal/spaCy POS to the labels
# actually used by CEFR-J. Unknown categories do not receive a guessed match.
CEFRJ_POS_BY_UPOS = {
    "ADJ": "adjective",
    "ADV": "adverb",
    "ADP": "preposition",
    "AUX": "be-verb",
    "CCONJ": "conjunction",
    "DET": "determiner",
    "NOUN": "noun",
    "NUM": "number",
    "PRON": "pronoun",
    "SCONJ": "conjunction",
    "VERB": "verb",
}


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


@lru_cache(maxsize=4)
def _load_cefrj_cached(path_text: str, sha256: str) -> tuple[tuple[tuple[str, str], ...], ...]:
    # ``sha256`` is part of the cache key even though the accepted Product asset
    # is currently single-pinned. This prevents stale rows if the path is reused
    # for different bytes in a future explicit asset revision.
    if sha256 != CEFRJ_SHA256:
        raise RuntimeError("Attempted to cache unaccepted CEFR-J identity")
    asset = Path(path_text)
    with asset.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if len(rows) != CEFRJ_ROWS:
        raise RuntimeError("CEFR-J rows changed after verification")
    return tuple(tuple(sorted(row.items())) for row in rows)


def load_cefrj_rows(path: Path | str | None = None) -> tuple[dict[str, Any], list[dict[str, str]]]:
    verified = verify_cefrj_asset(path)
    packed = _load_cefrj_cached(str(verified["path"]), str(verified["sha256"]))
    rows = [dict(items) for items in packed]
    return verified, rows


def cefrj_pos_label(part_of_speech: str | None) -> str | None:
    normalized = str(part_of_speech or "").strip().upper()
    return CEFRJ_POS_BY_UPOS.get(normalized)


def match_cefrj_entry(
    rows: list[dict[str, str]],
    *,
    lemma: str,
    part_of_speech: str | None,
) -> dict[str, Any]:
    normalized_lemma = str(lemma or "").strip().casefold()
    headword_rows = [
        row
        for row in rows
        if str(row.get("headword") or "").strip().casefold() == normalized_lemma
    ]
    expected_pos = cefrj_pos_label(part_of_speech)
    if not headword_rows:
        matched: list[dict[str, str]] = []
        match_kind = "unknown_exact_headword"
    elif expected_pos is None:
        # Do not invent a mapping for unsupported POS. The headword evidence is
        # retained for audit but no CEFR level is selected from it.
        matched = []
        match_kind = "headword_found_pos_mapping_unavailable"
    else:
        matched = [
            row
            for row in headword_rows
            if str(row.get("pos") or "").strip().casefold() == expected_pos.casefold()
        ]
        match_kind = "exact_headword_pos" if matched else "headword_found_pos_mismatch"

    levels = sorted(
        {
            str(row.get("CEFR") or "").strip()
            for row in matched
            if str(row.get("CEFR") or "").strip()
        }
    )
    if len(levels) == 1:
        level = levels[0]
        conflicts = 0
    elif len(levels) > 1:
        level = None
        conflicts = len(levels)
        match_kind = "conflicting_exact_headword_pos_levels"
    else:
        level = None
        conflicts = 0
    return {
        "level": level,
        "match_kind": match_kind,
        "conflict_count": conflicts,
        "expected_cefrj_pos": expected_pos,
        "headword_match_count": len(headword_rows),
        "pos_match_count": len(matched),
        "headword_rows": headword_rows,
        "matched_rows": matched,
    }


@lru_cache(maxsize=4)
def _load_cmudict_cached(package_version: str) -> tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]:
    import cmudict

    data = cmudict.dict()
    if not isinstance(data, dict) or not data:
        raise RuntimeError("CMUdict package returned an empty/non-dictionary resource")
    packed = []
    for key, variants in data.items():
        packed.append(
            (
                str(key).casefold(),
                tuple(tuple(map(str, variant)) for variant in variants),
            )
        )
    packed.sort(key=lambda item: item[0])
    return tuple(packed)


def load_cmudict() -> tuple[dict[str, Any], dict[str, list[list[str]]]]:
    status = cmudict_status()
    if not status["available"]:
        raise RuntimeError(f"Exact CMUdict evidence is unavailable: {status}")
    version = str(status.get("package_version") or "unknown")
    packed = _load_cmudict_cached(version)
    normalized = {
        key: [list(variant) for variant in variants]
        for key, variants in packed
    }
    return status, normalized
