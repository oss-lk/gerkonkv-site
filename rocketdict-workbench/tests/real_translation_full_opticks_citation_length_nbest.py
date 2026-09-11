from __future__ import annotations

"""Research-only staged raw OPUS n-best for isolated citation length failures.

This follow-up consumes the immutable rank-0 citation-length feasibility artifact.
It does not broaden citation detection and it does not change Product planning.
Only the exact source-derived chunks already produced for the two proven
length-only Roman citation hallucinations are probed.

Each raw hypothesis is evaluated unchanged with the maintained rescue evaluator.
A case is mechanically rescued only when every chunk has a strict candidate.
Lower target alpha is intentionally not a rejection rule because the primary
failure is an overlong hallucination. Semantic review is still mandatory before
any Product experiment.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-citation-length-nbest/1"
SOURCE_SCHEMA = "rocketdict-full-opticks-citation-length-rescue-feasibility/1"
SOURCE_EVIDENCE_SHA256 = "82c37555d437a698554a3d17e2777e824ec94e4bf18af502377e756dee58266a"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_CASE_SEQUENCES = [157, 864]
GENERATION_CELLS: tuple[tuple[int, int], ...] = ((6, 6), (12, 12), (16, 16))


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


def _probe_chunk(
    translator: OpusTranslator,
    source: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
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
        if cell_first is not None:
            first_strict = dict(cell_first)
            break
    return cells, first_strict


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_CITATION_ROOT", "work/citation-input")
    ).resolve()
    source_path = root / "full-opticks-citation-length-rescue-feasibility.json"
    if not source_path.is_file():
        raise RuntimeError(f"Citation rank-0 feasibility artifact missing: {source_path}")

    source_bytes = source_path.read_bytes()
    source_artifact = json.loads(source_bytes.decode("utf-8"))
    if source_artifact.get("schema") != SOURCE_SCHEMA:
        raise RuntimeError("Citation n-best source schema drift")
    if source_artifact.get("evidence_sha256") != SOURCE_EVIDENCE_SHA256:
        raise RuntimeError("Citation n-best source evidence identity drift")
    if source_artifact.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Citation n-best pinned Opticks identity drift")
    if source_artifact.get("promotion_allowed") is not False:
        raise RuntimeError("Citation rank-0 evidence unexpectedly allows promotion")
    if source_artifact.get("automatic_product_selection_allowed") is not False:
        raise RuntimeError("Citation rank-0 evidence unexpectedly allows automatic selection")
    if source_artifact.get("source_bytes_rewritten") is not False:
        raise RuntimeError("Citation rank-0 evidence unexpectedly rewrites source")
    if source_artifact.get("target_rewriting") is not False:
        raise RuntimeError("Citation rank-0 evidence unexpectedly rewrites target")
    if source_artifact.get("placeholders") is not False:
        raise RuntimeError("Citation rank-0 evidence unexpectedly uses placeholders")
    if source_artifact.get("post_translation_literal_injection") is not False:
        raise RuntimeError("Citation rank-0 evidence unexpectedly injects literals")

    cases = list(source_artifact.get("cases") or [])
    case_sequences = [int(row["failing_primary_sequence"]) for row in cases]
    if case_sequences != EXPECTED_CASE_SEQUENCES:
        raise RuntimeError(
            f"Citation n-best trigger drift: {case_sequences} != {EXPECTED_CASE_SEQUENCES}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    selected_cell_counts: Counter[str] = Counter()
    output_cases: list[dict[str, Any]] = []
    for case in cases:
        sequence = int(case["failing_primary_sequence"])
        chunks = list(case.get("candidate_chunks") or [])
        if not chunks:
            raise RuntimeError(f"Citation n-best case {sequence} has no source chunks")
        if "".join(str(row["source_text"]) for row in chunks) != str(
            case["group_source_text"]
        ):
            raise RuntimeError(f"Citation n-best case {sequence} source coverage drift")

        chunk_results: list[dict[str, Any]] = []
        for chunk_index, chunk in enumerate(chunks):
            source = str(chunk["source_text"])
            rank0_target = str(chunk["target_text"])
            rank0_verdict = dict(chunk.get("verdict") or {})
            if rank0_verdict.get("strictly_eligible") is True:
                first_strict = {
                    "beam_size": 6,
                    "num_hypotheses": 1,
                    "rank": int(chunk.get("rank") or 0),
                    "score": chunk.get("score"),
                    "target_text": rank0_target,
                    "strictly_eligible": True,
                    "verdict": rank0_verdict,
                    "reused_rank0": True,
                }
                cells: list[dict[str, Any]] = []
                selected_cell_counts["rank0_reused"] += 1
            else:
                cells, first_strict = _probe_chunk(translator, source)
                if first_strict is not None:
                    selected_cell_counts[
                        f"beam{int(first_strict['beam_size'])}"
                    ] += 1
                    first_strict["reused_rank0"] = False
            chunk_results.append(
                {
                    "chunk_index": chunk_index,
                    "source_start": int(chunk["source_start"]),
                    "source_end": int(chunk["source_end"]),
                    "source_text": source,
                    "rank0_target_text": rank0_target,
                    "rank0_strictly_eligible": (
                        rank0_verdict.get("strictly_eligible") is True
                    ),
                    "generation_cells_attempted": cells,
                    "first_strict_candidate": first_strict,
                    "mechanically_rescued": first_strict is not None,
                }
            )

        mechanically_rescued = all(
            row["mechanically_rescued"] is True for row in chunk_results
        )
        selected_target = (
            "".join(
                str(row["first_strict_candidate"]["target_text"])
                for row in chunk_results
            )
            if mechanically_rescued
            else None
        )
        output_cases.append(
            {
                "failing_primary_sequence": sequence,
                "citation_source_text": str(case["citation_source_text"]),
                "group_source_start": int(case["group_source_start"]),
                "group_source_end": int(case["group_source_end"]),
                "group_source_text": str(case["group_source_text"]),
                "rank0_case_strict_clean": case.get("strict_clean_candidate") is True,
                "chunks": chunk_results,
                "mechanically_rescued": mechanically_rescued,
                "selected_target_concatenated": selected_target,
                "semantic_review_required": True,
            }
        )

    rescued_sequences = [
        int(row["failing_primary_sequence"])
        for row in output_cases
        if row["mechanically_rescued"] is True
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only staged raw OPUS n-best over the exact source-derived "
            "chunks from proven isolated Roman citation length failures"
        ),
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "alpha_non_decreasing_required": False,
        "alpha_policy_reason": (
            "trigger is a proven overlong primary hallucination; maintained hard "
            "and strict research checks govern raw candidate eligibility"
        ),
        "source_sha256": OPTICKS_SHA256,
        "source_artifact_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_evidence_sha256": SOURCE_EVIDENCE_SHA256,
        "generation_cells": [
            {"beam_size": beam, "num_hypotheses": nbest}
            for beam, nbest in GENERATION_CELLS
        ],
        "case_count": len(output_cases),
        "case_sequences": case_sequences,
        "mechanically_rescued_count": len(rescued_sequences),
        "mechanically_rescued_sequences": rescued_sequences,
        "selected_generation_distribution": dict(sorted(selected_cell_counts.items())),
        "cases": output_cases,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-citation-length-nbest.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "case_count": len(output_cases),
                "mechanically_rescued_count": len(rescued_sequences),
                "mechanically_rescued_sequences": rescued_sequences,
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
