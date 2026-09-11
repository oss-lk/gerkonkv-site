from __future__ import annotations

"""Stable staged raw-OPUS n-best probe for proven citation length failures.

The upstream feasibility run contains raw CTranslate2 scores whose last floating
bits can vary between otherwise identical CPU executions.  This audit therefore
pins a score-insensitive semantic identity of that artifact, while retaining the
actual scores in emitted evidence.  No Product data or target text is rewritten.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-citation-length-nbest/2"
SOURCE_SCHEMA = "rocketdict-full-opticks-citation-length-rescue-feasibility/1"
SOURCE_STABLE_IDENTITY_SHA256 = "adfc90125fcf12f6e3fec5a593c1b3d8639dba0bf659cea2c76d3698ef372f80"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
BASELINE_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"
SELECTED_OUTPUT_SHA256 = "b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22"
PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"
STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/2"
CITATION_SPAN_CONTRACT = "rocketdict-research-abbreviated-section-citation-span/2"
TRIGGER_CONTRACT = "rocketdict-research-isolated-roman-citation-length-trigger/1"
SELECTOR_CONTRACT = "rocketdict-research-citation-length-strict-selector/1"
EXPECTED_CASE_SEQUENCES = [157, 864]
GENERATION_CELLS: tuple[tuple[int, int], ...] = ((6, 6), (12, 12), (16, 16))


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


def _stable_source(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _stable_source(item)
            for key, item in value.items()
            if key not in {"score", "evidence_sha256"}
        }
    if isinstance(value, list):
        return [_stable_source(item) for item in value]
    return value


def _candidate(
    hypothesis: dict[str, Any], *, source: str, beam_size: int, num_hypotheses: int
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


def _probe(
    translator: OpusTranslator, source: str
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    cells: list[dict[str, Any]] = []
    token_proxy = max(1, len(source.split()))
    for beam_size, num_hypotheses in GENERATION_CELLS:
        generated = translator.translate(
            [source],
            beam_size=beam_size,
            num_hypotheses=num_hypotheses,
            max_decoding_length=max(128, token_proxy * 8),
        )
        if len(generated) != 1 or not generated[0]:
            raise RuntimeError("Citation n-best OPUS returned no hypotheses")
        candidates = [
            _candidate(
                hypothesis,
                source=source,
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
            )
            for hypothesis in generated[0]
        ]
        first = next(
            (row for row in candidates if row["strictly_eligible"] is True), None
        )
        cells.append(
            {
                "beam_size": beam_size,
                "num_hypotheses": num_hypotheses,
                "strict_candidate_count": sum(
                    row["strictly_eligible"] is True for row in candidates
                ),
                "first_strict_rank": int(first["rank"]) if first else None,
                "candidates": candidates,
            }
        )
        if first is not None:
            return cells, dict(first)
    return cells, None


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_CITATION_ROOT", "work/citation-input")).resolve()
    source_path = root / "full-opticks-citation-length-rescue-feasibility.json"
    if not source_path.is_file():
        raise RuntimeError(f"Citation rank-0 feasibility artifact missing: {source_path}")

    source_bytes = source_path.read_bytes()
    artifact = json.loads(source_bytes.decode("utf-8"))
    if artifact.get("schema") != SOURCE_SCHEMA:
        raise RuntimeError("Citation n-best source schema drift")
    if _canonical_sha(_stable_source(artifact)) != SOURCE_STABLE_IDENTITY_SHA256:
        raise RuntimeError("Citation n-best score-insensitive source identity drift")
    required = {
        "source_sha256": OPTICKS_SHA256,
        "baseline_json_sha256": BASELINE_JSON_SHA256,
        "baseline_database_sha256": BASELINE_DATABASE_SHA256,
        "selected_translation_output_sha256": SELECTED_OUTPUT_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
        "citation_span_contract": CITATION_SPAN_CONTRACT,
        "trigger_contract": TRIGGER_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
    }
    for key, expected in required.items():
        if artifact.get(key) != expected:
            raise RuntimeError(f"Citation n-best source {key} drift")
    for key in (
        "promotion_allowed",
        "automatic_product_selection_allowed",
        "source_bytes_rewritten",
        "target_rewriting",
        "placeholders",
        "post_translation_literal_injection",
    ):
        if artifact.get(key) is not False:
            raise RuntimeError(f"Citation n-best unsafe upstream flag: {key}")

    cases = list(artifact.get("cases") or [])
    sequences = [int(row["failing_primary_sequence"]) for row in cases]
    if sequences != EXPECTED_CASE_SEQUENCES or int(artifact.get("trigger_count") or -1) != 2:
        raise RuntimeError("Citation n-best trigger cohort drift")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    distribution: Counter[str] = Counter()
    result_cases: list[dict[str, Any]] = []
    for case in cases:
        sequence = int(case["failing_primary_sequence"])
        chunks = list(case.get("candidate_chunks") or [])
        if not chunks or "".join(str(row["source_text"]) for row in chunks) != str(
            case["group_source_text"]
        ):
            raise RuntimeError(f"Citation n-best source coverage drift for {sequence}")

        result_chunks: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            source = str(chunk["source_text"])
            rank0_verdict = dict(chunk.get("verdict") or {})
            if rank0_verdict.get("strictly_eligible") is True:
                selected = {
                    "beam_size": 6,
                    "num_hypotheses": 1,
                    "rank": int(chunk.get("rank") or 0),
                    "score": chunk.get("score"),
                    "target_text": str(chunk["target_text"]),
                    "strictly_eligible": True,
                    "verdict": rank0_verdict,
                    "reused_rank0": True,
                }
                cells: list[dict[str, Any]] = []
                distribution["rank0_reused"] += 1
            else:
                cells, selected = _probe(translator, source)
                if selected is not None:
                    selected["reused_rank0"] = False
                    distribution[f"beam{int(selected['beam_size'])}"] += 1
            result_chunks.append(
                {
                    "chunk_index": index,
                    "source_start": int(chunk["source_start"]),
                    "source_end": int(chunk["source_end"]),
                    "source_text": source,
                    "rank0_target_text": str(chunk["target_text"]),
                    "rank0_strictly_eligible": rank0_verdict.get("strictly_eligible") is True,
                    "generation_cells_attempted": cells,
                    "first_strict_candidate": selected,
                    "mechanically_rescued": selected is not None,
                }
            )

        rescued = all(row["mechanically_rescued"] is True for row in result_chunks)
        result_cases.append(
            {
                "failing_primary_sequence": sequence,
                "citation_source_text": str(case["citation_source_text"]),
                "group_source_start": int(case["group_source_start"]),
                "group_source_end": int(case["group_source_end"]),
                "group_source_text": str(case["group_source_text"]),
                "rank0_case_strict_clean": case.get("strict_clean_candidate") is True,
                "chunks": result_chunks,
                "mechanically_rescued": rescued,
                "selected_target_concatenated": (
                    "".join(
                        str(row["first_strict_candidate"]["target_text"])
                        for row in result_chunks
                    )
                    if rescued
                    else None
                ),
                "semantic_review_required": True,
            }
        )

    rescued_sequences = [
        int(row["failing_primary_sequence"])
        for row in result_cases
        if row["mechanically_rescued"] is True
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only staged raw OPUS n-best for the exact proven citation length-failure chunks",
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "alpha_non_decreasing_required": False,
        "source_sha256": OPTICKS_SHA256,
        "source_artifact_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_stable_identity_sha256": SOURCE_STABLE_IDENTITY_SHA256,
        "source_live_evidence_sha256": artifact.get("evidence_sha256"),
        "generation_cells": [
            {"beam_size": beam, "num_hypotheses": nbest}
            for beam, nbest in GENERATION_CELLS
        ],
        "case_count": len(result_cases),
        "case_sequences": sequences,
        "mechanically_rescued_count": len(rescued_sequences),
        "mechanically_rescued_sequences": rescued_sequences,
        "selected_generation_distribution": dict(sorted(distribution.items())),
        "cases": result_cases,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-citation-length-nbest.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "case_count": len(result_cases),
                "mechanically_rescued_count": len(rescued_sequences),
                "mechanically_rescued_sequences": rescued_sequences,
                "selected_generation_distribution": payload["selected_generation_distribution"],
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
