from __future__ import annotations

"""Read-only full-Opticks audit for Product Stage12 block section identifiers.

This audit runs only after the actual Product Stage12 full-corpus harness.  It
verifies the narrow planner-v8 contract on the immutable source and persisted
translation segments: all block-level Gutenberg license identifiers are exact
source-owned structure, receive no MT request, and survive byte-for-byte; inline
references remain ordinary prose.  Nothing is translated, rewritten or repaired
here and the Product database must remain byte-identical.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.block_section_identifiers import (
    BLOCK_SECTION_IDENTIFIER_CONTRACT,
    detect_block_section_identifiers,
)
from rocketdict.database import connect, get_document, get_run_items
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-block-section-audit/1"
BASELINE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_TOTAL_IDENTIFIERS = 26
EXPECTED_BLOCK_IDENTIFIERS = 21
EXPECTED_INLINE_IDENTIFIERS = 5


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Full Opticks Product Stage12 evidence is missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise RuntimeError(f"Unexpected full Opticks baseline schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")
    if baseline.get("actual_product_stage12_execution") is not True:
        raise RuntimeError("Block-section audit requires actual persisted Product Stage12 evidence")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Full Opticks baseline does not use the current Product planner")

    stage12 = dict(baseline.get("stage12") or {})
    if stage12.get("block_section_identifier_contract") != BLOCK_SECTION_IDENTIFIER_CONTRACT:
        raise RuntimeError("Full Opticks Stage12 block-section contract drift")
    if int(stage12.get("block_section_identifier_unit_count") or -1) != EXPECTED_BLOCK_IDENTIFIERS:
        raise RuntimeError("Pinned Opticks Stage12 must preserve exactly 21 block section identifiers")

    database_sha_before = _sha_file(database)
    document_version_id = int(baseline["document_version_id"])
    translation_run_id = int(stage12["translation_run_id"])
    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        items = get_run_items(connection, translation_run_id, kind="translation_segment")
    content = str(document["content_text"])
    if str(document.get("text_sha256") or "") != str(baseline.get("source_text_sha256") or ""):
        raise RuntimeError("Persisted document identity drift")

    all_identifiers = detect_block_section_identifiers(content)
    block_identifiers = [row for row in all_identifiers if row.block_level]
    inline_identifiers = [row for row in all_identifiers if not row.block_level]
    if len(all_identifiers) != EXPECTED_TOTAL_IDENTIFIERS:
        raise RuntimeError(
            f"Pinned Opticks identifier inventory drift: {len(all_identifiers)} != {EXPECTED_TOTAL_IDENTIFIERS}"
        )
    if len(block_identifiers) != EXPECTED_BLOCK_IDENTIFIERS:
        raise RuntimeError(
            f"Pinned Opticks block identifier inventory drift: {len(block_identifiers)} != {EXPECTED_BLOCK_IDENTIFIERS}"
        )
    if len(inline_identifiers) != EXPECTED_INLINE_IDENTIFIERS:
        raise RuntimeError(
            f"Pinned Opticks inline identifier inventory drift: {len(inline_identifiers)} != {EXPECTED_INLINE_IDENTIFIERS}"
        )

    structured_rows: list[dict[str, Any]] = []
    ordinary_rows: list[dict[str, Any]] = []
    for item in items:
        payload = dict(item.get("payload") or {})
        planner = dict(payload.get("planner") or {})
        row = {**item, "payload": payload, "planner": planner}
        if isinstance(payload.get("block_section_identifier"), dict):
            structured_rows.append(row)
        else:
            ordinary_rows.append(row)
    if len(structured_rows) != EXPECTED_BLOCK_IDENTIFIERS:
        raise RuntimeError(
            f"Persisted block section unit count drift: {len(structured_rows)} != {EXPECTED_BLOCK_IDENTIFIERS}"
        )

    preserved: list[dict[str, Any]] = []
    for identifier in block_identifiers:
        matches = [
            row
            for row in structured_rows
            if int((row["planner"] or {}).get("block_section_identifier_core_start") or -1)
            == identifier.source_start
            and int((row["planner"] or {}).get("block_section_identifier_core_end") or -1)
            == identifier.source_end
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Block identifier {identifier.identifier} at {identifier.source_start} has {len(matches)} Product units"
            )
        row = matches[0]
        payload = dict(row["payload"].get("block_section_identifier") or {})
        source_start = int(row["source_start"])
        source_end = int(row["source_end"])
        source_text = str(row.get("source_text") or "")
        target_text = str(row.get("target_text") or "")
        if source_start != identifier.source_start or source_end < identifier.source_end:
            raise RuntimeError("Block section unit source span does not own the identifier core")
        if content[source_start:source_end] != source_text:
            raise RuntimeError("Block section unit differs from immutable source bytes")
        if target_text != source_text:
            raise RuntimeError(
                f"Block section identifier was not preserved byte-exact: {source_text!r} -> {target_text!r}"
            )
        if payload.get("contract") != BLOCK_SECTION_IDENTIFIER_CONTRACT:
            raise RuntimeError("Persisted block section payload contract drift")
        if str(payload.get("identifier") or "") != identifier.identifier:
            raise RuntimeError("Persisted block section identifier value drift")
        if payload.get("source_owned_structure") is not True:
            raise RuntimeError("Block section identifier lost source-owned-structure provenance")
        if payload.get("model_request") is not False:
            raise RuntimeError("Block section identifier unexpectedly became an MT request")
        if payload.get("target_rewriting") is not False or payload.get("source_bytes_rewritten") is not False:
            raise RuntimeError("Block section identifier provenance licenses rewriting")
        if list(row["payload"].get("hypotheses") or []):
            raise RuntimeError("Block section identifier unexpectedly persisted MT hypotheses")
        if row["payload"].get("selected_rank") is not None:
            raise RuntimeError("Block section identifier unexpectedly has a model rank")
        preserved.append(
            {
                "identifier": identifier.identifier,
                "source_start": identifier.source_start,
                "source_end": identifier.source_end,
                "unit_source_start": source_start,
                "unit_source_end": source_end,
                "target_equals_source": True,
                "model_request": False,
            }
        )

    inline_rows: list[dict[str, Any]] = []
    for identifier in inline_identifiers:
        matches = [
            row
            for row in ordinary_rows
            if int(row.get("source_start") or -1) <= identifier.source_start
            and int(row.get("source_end") or -1) >= identifier.source_end
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Inline identifier {identifier.identifier} at {identifier.source_start} is not owned by one ordinary Product unit"
            )
        row = matches[0]
        if (row.get("planner") or {}).get("source") == "block_section_identifier":
            raise RuntimeError("Inline identifier was incorrectly classified as block structure")
        inline_rows.append(
            {
                "identifier": identifier.identifier,
                "source_start": identifier.source_start,
                "source_end": identifier.source_end,
                "ordinary_unit_sequence": int(row["sequence_number"]),
                "ordinary_unit_source": str((row.get("planner") or {}).get("source") or ""),
            }
        )

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Read-only block section audit mutated the Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only byte-exact audit of Product Stage12 block section identifiers",
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "block_section_identifier_contract": BLOCK_SECTION_IDENTIFIER_CONTRACT,
        "total_identifier_count": len(all_identifiers),
        "block_identifier_count": len(block_identifiers),
        "inline_identifier_count": len(inline_identifiers),
        "preserved_block_identifier_count": len(preserved),
        "block_identifier_failure_count": 0,
        "inline_identifier_ordinary_unit_count": len(inline_rows),
        "model_request_count_for_block_identifiers": 0,
        "target_rewriting": False,
        "source_bytes_rewritten": False,
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "preserved_block_identifiers": preserved,
        "inline_identifiers": inline_rows,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-block-section-audit.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "block_identifier_count": len(block_identifiers),
                "preserved_block_identifier_count": len(preserved),
                "inline_identifier_count": len(inline_identifiers),
                "block_identifier_failure_count": 0,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
