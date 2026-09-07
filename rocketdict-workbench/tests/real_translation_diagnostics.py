from __future__ import annotations

"""Re-evaluate frozen maintained R1 output with current versioned diagnostics.

The source selector and original R1 harness are intentionally untouched.  This
companion audit reads the immutable Stage14 assembly produced by that harness
and applies dependency-free maintained research diagnostics whose semantics are
versioned independently from the frozen historical measurement surface.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_run_items
from rocketdict.research_diagnostics import (
    DELIMITER_CONTRACT,
    NUMERIC_ORDER_CONTRACT,
    compare_delimiter_preservation,
    compare_numeric_order,
)

SCHEMA = "rocketdict-maintained-r1-diagnostic-audit/1"
EXPECTED_SELECTION_SHA256 = "665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32"


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
        os.environ.get(
            "ROCKETDICT_TRANSLATION_CHALLENGE_ROOT",
            "work/translation-challenge",
        )
    ).resolve()
    baseline_path = root / "maintained-r1-baseline.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file():
        raise RuntimeError(f"R1 baseline evidence is missing: {baseline_path}")
    if not database.is_file():
        raise RuntimeError(f"R1 Product database is missing: {database}")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    selection = baseline.get("selection") or {}
    selection_sha = str(selection.get("selection_sha256") or "")
    if selection_sha != EXPECTED_SELECTION_SHA256:
        raise RuntimeError(
            f"R1 selection identity drift: {selection_sha} != {EXPECTED_SELECTION_SHA256}"
        )

    with connect(database, readonly=True) as connection:
        assembly_row = connection.execute(
            "SELECT id, output_sha256 FROM stage_runs "
            "WHERE stage_number=14 AND status='completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if assembly_row is None:
            raise RuntimeError("R1 database contains no completed Stage14 assembly")
        assembly_id = int(assembly_row["id"])
        assembly_output_sha256 = str(assembly_row["output_sha256"] or "")
        rows = get_run_items(connection, assembly_id, kind="assembly_segment")
    if not rows:
        raise RuntimeError("R1 Stage14 assembly contains no translation segments")

    numeric_order_failures: list[dict[str, Any]] = []
    delimiter_failures: list[dict[str, Any]] = []
    source_unbalanced_preserved: list[dict[str, Any]] = []
    for row in rows:
        sequence = int(row["sequence_number"])
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")

        numeric = compare_numeric_order(source, target)
        if numeric["passed"] is not True:
            numeric_order_failures.append(
                {
                    "segment_sequence": sequence,
                    "source_text": source,
                    "target_text": target,
                    "detail": numeric,
                }
            )

        delimiters = compare_delimiter_preservation(source, target)
        if delimiters["source_was_balanced"] is False and delimiters["passed"] is True:
            source_unbalanced_preserved.append(
                {
                    "segment_sequence": sequence,
                    "source_text": source,
                    "target_text": target,
                    "source_unbalanced_kinds": delimiters["source_unbalanced_kinds"],
                }
            )
        if delimiters["passed"] is not True:
            delimiter_failures.append(
                {
                    "segment_sequence": sequence,
                    "source_text": source,
                    "target_text": target,
                    "detail": delimiters,
                }
            )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "post-run evaluator audit; does not alter frozen R1 selection or Product output",
        "selection_sha256": selection_sha,
        "assembly_id": assembly_id,
        "assembly_output_sha256": assembly_output_sha256,
        "segment_count": len(rows),
        "numeric_order": {
            "contract": NUMERIC_ORDER_CONTRACT,
            "failure_count": len(numeric_order_failures),
            "failure_sequences": [
                row["segment_sequence"] for row in numeric_order_failures
            ],
            "failures": numeric_order_failures,
        },
        "delimiter_preservation": {
            "contract": DELIMITER_CONTRACT,
            "failure_count": len(delimiter_failures),
            "failure_sequences": [row["segment_sequence"] for row in delimiter_failures],
            "failures": delimiter_failures,
            "source_unbalanced_preserved_count": len(source_unbalanced_preserved),
            "source_unbalanced_preserved": source_unbalanced_preserved,
        },
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-diagnostic-audit.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
