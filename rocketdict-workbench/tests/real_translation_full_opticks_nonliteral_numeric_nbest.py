from __future__ import annotations

"""Research raw n-best for Product numeric/symbol failures outside digit-source stress.

The historical full-Opticks numeric stress only considers source rows for which
``extract_numeric_literals(source)`` is non-empty. The complete maintained
numeric/symbol gate also rejects target-added symbols/numbers in other rows.
This audit discovers those failures directly from the immutable Product output
and probes unchanged-source OPUS beam6/12/16 hypotheses.

No candidate is promoted. A mechanically strict hypothesis is only evidence that
the pinned model can express a cleaner alternative; semantic review remains
mandatory, especially for spelled-number source language.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair, extract_numeric_literals
from rocketdict.runtime import OpusTranslator
from rocketdict.structural_labels import STRUCTURAL_LABEL_CONTRACT
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-nonliteral-numeric-nbest/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
EXPECTED_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"
EXPECTED_FAILURE_COUNT = 3
GENERATION_CELLS: tuple[tuple[int, int], ...] = ((6, 6), (12, 12), (16, 16))


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


def _candidate(
    hypothesis: dict[str, Any],
    *,
    source: str,
    beam_size: int,
    num_hypotheses: int,
) -> dict[str, Any]:
    target = str(hypothesis.get("text") or "")
    verdict = evaluate_rescue_pair(source, target)
    return {
        "beam_size": beam_size,
        "num_hypotheses": num_hypotheses,
        "rank": int(hypothesis.get("rank") or 0),
        "score": hypothesis.get("score"),
        "target_text": target,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "verdict": verdict,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NONLITERAL_NUMERIC_ROOT", "work/nonliteral-numeric-input")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Nonliteral numeric n-best immutable baseline inputs are missing")
    if _sha_file(baseline_path) != EXPECTED_BASELINE_JSON_SHA256:
        raise RuntimeError("Nonliteral numeric n-best baseline JSON identity drift")
    if _sha_file(database) != EXPECTED_DATABASE_SHA256:
        raise RuntimeError("Nonliteral numeric n-best Product database identity drift")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("Nonliteral numeric n-best baseline schema drift")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Nonliteral numeric n-best pinned source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Nonliteral numeric n-best requires planner-v8 baseline")
    if baseline.get("structural_label_contract") != STRUCTURAL_LABEL_CONTRACT:
        raise RuntimeError("Nonliteral numeric n-best structural-label contract drift")

    selected_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    document_version_id = int(baseline["document_version_id"])
    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        selected_rows = sorted(
            get_run_items(connection, selected_run_id, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, document_version_id)
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in selected_rows) != content:
        raise RuntimeError("Nonliteral numeric n-best selected Stage12 source coverage drift")

    failures: list[dict[str, Any]] = []
    for row in selected_rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        if extract_numeric_literals(source):
            continue
        numeric = evaluate_numeric_symbol_pair(source, target)
        if numeric.get("passed") is True:
            continue
        failures.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "primary_target_text": target,
                "primary_numeric_symbol": numeric,
                "primary_strict_verdict": evaluate_rescue_pair(source, target),
            }
        )
    if len(failures) != EXPECTED_FAILURE_COUNT:
        raise RuntimeError(
            f"Pinned nonliteral-source numeric failure drift: {len(failures)} != {EXPECTED_FAILURE_COUNT}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    cases: list[dict[str, Any]] = []
    selected_cell_counts: Counter[str] = Counter()
    for failure in failures:
        source = str(failure["source_text"])
        token_proxy = max(1, len(source.split()))
        cells: list[dict[str, Any]] = []
        first_strict: dict[str, Any] | None = None
        for beam_size, num_hypotheses in GENERATION_CELLS:
            generated = translator.translate(
                [source],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=max(128, token_proxy * 8),
            )
            if len(generated) != 1 or not generated[0]:
                raise RuntimeError(
                    f"Nonliteral numeric n-best returned no hypotheses for {failure['sequence_number']}"
                )
            candidates = [
                _candidate(
                    hypothesis,
                    source=source,
                    beam_size=beam_size,
                    num_hypotheses=num_hypotheses,
                )
                for hypothesis in generated[0]
            ]
            cell_first = next(
                (row for row in candidates if row["strictly_eligible"] is True),
                None,
            )
            cells.append(
                {
                    "beam_size": beam_size,
                    "num_hypotheses": num_hypotheses,
                    "strict_candidate_count": sum(
                        row["strictly_eligible"] is True for row in candidates
                    ),
                    "first_strict_rank": (
                        int(cell_first["rank"]) if cell_first is not None else None
                    ),
                    "candidates": candidates,
                }
            )
            if first_strict is None and cell_first is not None:
                first_strict = dict(cell_first)
                selected_cell_counts[f"beam{beam_size}"] += 1
                # Preserve staged semantics: larger beams are unnecessary once a
                # strict candidate exists for this case.
                break
        cases.append(
            {
                **failure,
                "generation_cells_attempted": cells,
                "first_strict_candidate": first_strict,
                "mechanically_rescued": first_strict is not None,
                "semantic_review_required": True,
            }
        )

    if _sha_file(database) != database_sha_before:
        raise RuntimeError("Nonliteral numeric n-best mutated immutable Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only staged raw OPUS n-best for complete numeric/symbol failures "
            "whose immutable source has no extracted digit literal"
        ),
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "baseline_json_sha256": EXPECTED_BASELINE_JSON_SHA256,
        "baseline_database_sha256": EXPECTED_DATABASE_SHA256,
        "selected_translation_run_id": selected_run_id,
        "selected_translation_output_sha256": str(selected_run.get("output_sha256") or ""),
        "planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
        "failure_count": len(cases),
        "failure_sequences": [row["sequence_number"] for row in cases],
        "mechanically_rescued_count": sum(
            row["mechanically_rescued"] is True for row in cases
        ),
        "mechanically_rescued_sequences": [
            row["sequence_number"]
            for row in cases
            if row["mechanically_rescued"] is True
        ],
        "selected_generation_distribution": dict(sorted(selected_cell_counts.items())),
        "generation_cells": [
            {"beam_size": beam, "num_hypotheses": nbest}
            for beam, nbest in GENERATION_CELLS
        ],
        "cases": cases,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_unchanged": True,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-nonliteral-numeric-nbest.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "failure_count": len(cases),
                "failure_sequences": payload["failure_sequences"],
                "mechanically_rescued_count": payload["mechanically_rescued_count"],
                "mechanically_rescued_sequences": payload[
                    "mechanically_rescued_sequences"
                ],
                "selected_generation_distribution": payload[
                    "selected_generation_distribution"
                ],
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
