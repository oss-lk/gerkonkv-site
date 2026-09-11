from __future__ import annotations

"""Research-only full-Opticks feasibility for source-owned block footnote markers.

The pinned Gutenberg source contains a closed class of footnote-definition
markers at block/line start: ``[A] `` ... ``[M] ``.  They are document
structure, not translatable prose.  This experiment keeps the exact marker plus
its following horizontal whitespace byte-for-byte and sends only the remaining
body of the already-selected primary Stage12 row to the pinned real OPUS model.

Inline references such as ``understand,[G] that`` and linguistic bracketed
annotations such as ``[Illustration: ...]`` are deliberately out of scope.
Nothing is written back to the Product database and no target repair, placeholder
or post-translation literal insertion is used.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_stage import PLANNER_CONTRACT, STRUCTURAL_LABEL_CONTRACT

SCHEMA = "rocketdict-full-opticks-block-footnote-marker-feasibility/1"
CONTRACT = "rocketdict-research-block-footnote-marker/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
BASELINE_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"
SELECTED_OUTPUT_SHA256 = "b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22"
EXPECTED_SEQUENCES = [156, 159, 852, 855, 858, 861, 866, 870, 1478, 1479, 1484, 1490, 1494]
_MARKER_RE = re.compile(r"^\[(?P<letter>[A-Z])\](?P<space>[ \t]+)")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_CITATION_ROOT", "work/citation-input")).resolve()
    database = root / "rocketdict.sqlite"
    baseline_path = root / "full-opticks-numeric-stress.json"
    if not database.is_file() or not baseline_path.is_file():
        raise RuntimeError("Block-footnote feasibility requires pinned baseline DB and JSON")
    if _sha(database) != BASELINE_DATABASE_SHA256:
        raise RuntimeError("Block-footnote baseline database identity drift")
    if _sha(baseline_path) != BASELINE_JSON_SHA256:
        raise RuntimeError("Block-footnote baseline JSON identity drift")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Block-footnote pinned Opticks source identity drift")
    selected_run_id = int(baseline["stage12"]["translation_run_id"])

    with connect(database, readonly=True) as connection:
        run = get_run(connection, selected_run_id)
        rows = get_run_items(connection, selected_run_id, kind="translation_segment")
    if str(run.get("output_sha256") or "") != SELECTED_OUTPUT_SHA256:
        raise RuntimeError("Block-footnote selected Stage12 output identity drift")

    ordered = sorted(rows, key=lambda row: int(row["sequence_number"]))
    cases: list[dict[str, Any]] = []
    for row in ordered:
        source = str(row.get("source_text") or "")
        match = _MARKER_RE.match(source)
        if match is None:
            continue
        sequence = int(row["sequence_number"])
        marker_end = int(match.end())
        marker_source = source[:marker_end]
        body_source = source[marker_end:]
        if not body_source.strip():
            raise RuntimeError(f"Block-footnote row {sequence} has no linguistic body")
        payload = dict(row.get("payload") or {})
        planner = dict(payload.get("planner") or {})
        if planner.get("planner_contract") != PLANNER_CONTRACT:
            raise RuntimeError(f"Block-footnote row {sequence} planner contract drift")
        cases.append(
            {
                "sequence": sequence,
                "row_id": int(row["id"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "baseline_target": str(row.get("target_text") or ""),
                "marker_source": marker_source,
                "marker_letter": match.group("letter"),
                "marker_start": int(row["source_start"]),
                "marker_end": int(row["source_start"]) + marker_end,
                "body_source": body_source,
                "body_start": int(row["source_start"]) + marker_end,
                "body_end": int(row["source_end"]),
                "planner": planner,
            }
        )

    sequences = [row["sequence"] for row in cases]
    if sequences != EXPECTED_SEQUENCES:
        raise RuntimeError(f"Block-footnote marker cohort drift: {sequences}")
    letters = [row["marker_letter"] for row in cases]
    if letters != list("ABCDEFGH") + list("IJKLM"):
        raise RuntimeError(f"Block-footnote marker letter order drift: {letters}")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    hypotheses = translator.translate(
        [row["body_source"] for row in cases],
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=512,
    )
    if len(hypotheses) != len(cases) or any(len(row) != 1 for row in hypotheses):
        raise RuntimeError("Block-footnote OPUS response cardinality drift")

    hard_rescued: list[int] = []
    hard_regressed: list[int] = []
    strict_rescued: list[int] = []
    strict_regressed: list[int] = []
    output_cases: list[dict[str, Any]] = []
    marker_target_exact_count = 0
    candidate_hard_failures = 0
    baseline_hard_failures = 0
    for case, generated in zip(cases, hypotheses, strict=True):
        body_target = str(generated[0].get("text") or "")
        marker_target = str(case["marker_source"])
        baseline_verdict = evaluate_rescue_pair(case["source_text"], case["baseline_target"])
        marker_verdict = evaluate_rescue_pair(case["marker_source"], marker_target)
        body_verdict = evaluate_rescue_pair(case["body_source"], body_target)
        candidate_hard = (
            marker_verdict["product_hard_passed"] is True
            and body_verdict["product_hard_passed"] is True
        )
        candidate_strict = (
            marker_verdict["strictly_eligible"] is True
            and body_verdict["strictly_eligible"] is True
        )
        baseline_hard = baseline_verdict["product_hard_passed"] is True
        baseline_strict = baseline_verdict["strictly_eligible"] is True
        if not baseline_hard:
            baseline_hard_failures += 1
        if not candidate_hard:
            candidate_hard_failures += 1
        if not baseline_hard and candidate_hard:
            hard_rescued.append(case["sequence"])
        if baseline_hard and not candidate_hard:
            hard_regressed.append(case["sequence"])
        if not baseline_strict and candidate_strict:
            strict_rescued.append(case["sequence"])
        if baseline_strict and not candidate_strict:
            strict_regressed.append(case["sequence"])
        if marker_target == case["marker_source"]:
            marker_target_exact_count += 1

        if case["marker_source"] + case["body_source"] != case["source_text"]:
            raise RuntimeError(f"Block-footnote source coverage drift for {case['sequence']}")
        output_cases.append(
            {
                **case,
                "baseline_verdict": baseline_verdict,
                "marker_target": marker_target,
                "marker_verdict": marker_verdict,
                "body_target": body_target,
                "body_rank0_score": generated[0].get("score"),
                "body_verdict": body_verdict,
                "candidate_target_concatenated": marker_target + body_target,
                "candidate_product_hard_passed": candidate_hard,
                "candidate_strictly_eligible": candidate_strict,
            }
        )

    if hard_regressed:
        raise RuntimeError(f"Block-footnote marker candidate regressed hard gates: {hard_regressed}")
    if marker_target_exact_count != len(cases):
        raise RuntimeError("Block-footnote marker target exactness drift")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "purpose": (
            "research-only source-owned block-start footnote marker partition; "
            "marker bytes remain exact and only linguistic bodies use real OPUS"
        ),
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "baseline_json_sha256": BASELINE_JSON_SHA256,
        "baseline_database_sha256": BASELINE_DATABASE_SHA256,
        "selected_translation_run_id": selected_run_id,
        "selected_translation_output_sha256": SELECTED_OUTPUT_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
        "detection_rule": "line/stage-row start ^\\[[A-Z]\\][ \\t]+ only",
        "inline_markers_in_scope": False,
        "linguistic_bracket_annotations_in_scope": False,
        "case_count": len(output_cases),
        "case_sequences": sequences,
        "marker_letters": letters,
        "marker_target_exact_count": marker_target_exact_count,
        "baseline_hard_failure_count": baseline_hard_failures,
        "candidate_hard_failure_count": candidate_hard_failures,
        "hard_rescued_sequences": hard_rescued,
        "hard_regressed_sequences": hard_regressed,
        "strict_rescued_sequences": strict_rescued,
        "strict_regressed_sequences": strict_regressed,
        "cases": output_cases,
        "source_bytes_rewritten": False,
        "marker_source_owned_passthrough": True,
        "linguistic_body_real_opus": True,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_written": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-block-footnote-marker-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "case_count": len(output_cases),
                "baseline_hard_failure_count": baseline_hard_failures,
                "candidate_hard_failure_count": candidate_hard_failures,
                "hard_rescued_sequences": hard_rescued,
                "hard_regressed_sequences": hard_regressed,
                "strict_rescued_sequences": strict_rescued,
                "strict_regressed_sequences": strict_regressed,
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
