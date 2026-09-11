from __future__ import annotations

"""Research-only feasibility for narrow abbreviated citation boundary protection.

The current planner already coalesces spaCy sentence boundaries that fall inside
balanced ``[]``, ``()``, ``{}`` or Gutenberg emphasis spans. Full-Opticks
residual review found two tiny ``IV.``/``II.`` length failures created when spaCy
split *inside* ordinary bibliographic references such as ``Sect. IV. Prop 29``
and ``Sect. II. Sec. 29``.

This experiment does not change Product planning. It detects a narrow,
source-derived citation span, adds those spans to the existing protected-boundary
set, then applies the same planner-v8 token-budget split to only the affected
context groups and sends the resulting unchanged source chunks to real pinned
OPUS. Raw rank-0 output is compared with the immutable Product rows using the
existing strict rescue evaluator.

No source/target rewriting, placeholders, literal injection, database writes or
Product promotion are allowed.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.structural_labels import STRUCTURAL_LABEL_CONTRACT
from rocketdict.translation_rescue import evaluate_candidate_context, evaluate_rescue_pair
from rocketdict.translation_stage import (
    PLANNER_CONTRACT,
    _balanced_protected_spans,
    _safe_forward_split_index,
)

SCHEMA = "rocketdict-full-opticks-citation-boundary-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
EXPECTED_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"
EXPECTED_CITATION_COUNT = 4
PREFERRED_TOKENS = 64
CITATION_SPAN_CONTRACT = "rocketdict-research-abbreviated-section-citation-span/1"

_CITATION_RE = re.compile(
    r"\bSect\.\s+(?:[IVXLCDM]+|\d+)\."
    r"(?:\s+(?:Prop|Sec)\.?\s+\d+(?:\s*,\s*\d+)*\.?)?",
    flags=re.IGNORECASE,
)


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


def _citation_spans(text: str) -> list[tuple[int, int, str]]:
    return [
        (match.start(), match.end(), "abbreviated_section_citation")
        for match in _CITATION_RE.finditer(text)
    ]


def _inside(boundary: int, spans: list[tuple[int, int, str]]) -> bool:
    return any(start < boundary < end for start, end, _kind in spans)


def _non_space_tokens(
    tokens: list[dict[str, Any]], start: int, end: int
) -> list[dict[str, Any]]:
    return [
        row
        for row in tokens
        if int(row["source_start"]) >= start
        and int(row["source_end"]) <= end
        and not bool((row.get("payload") or {}).get("flags", {}).get("is_space"))
    ]


def _coalesced_groups(
    content: str,
    contexts: list[dict[str, Any]],
    *,
    balanced: list[tuple[int, int, str]],
    citations: list[tuple[int, int, str]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for row in contexts:
        sequence = int(row["sequence_number"])
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if content[start:end] != source:
            raise RuntimeError("Stage10 context differs from immutable source")
        if current is None:
            current = {
                "start": start,
                "end": end,
                "context_sequences": [sequence],
                "citation_boundary_count": 0,
                "balanced_boundary_count": 0,
            }
            continue
        if start != int(current["end"]):
            raise RuntimeError("Stage10 contexts are not contiguous")
        citation_boundary = _inside(start, citations)
        balanced_boundary = _inside(start, balanced)
        if citation_boundary or balanced_boundary:
            current["end"] = end
            current["context_sequences"].append(sequence)
            current["citation_boundary_count"] += int(citation_boundary)
            current["balanced_boundary_count"] += int(balanced_boundary)
            continue
        current["source_text"] = content[int(current["start"]):int(current["end"])]
        groups.append(current)
        current = {
            "start": start,
            "end": end,
            "context_sequences": [sequence],
            "citation_boundary_count": 0,
            "balanced_boundary_count": 0,
        }
    if current is not None:
        current["source_text"] = content[int(current["start"]):int(current["end"])]
        groups.append(current)
    return groups


def _split_group(
    content: str,
    group: dict[str, Any],
    tokens: list[dict[str, Any]],
    spans: list[tuple[int, int, str]],
) -> list[dict[str, Any]]:
    start = int(group["start"])
    end = int(group["end"])
    contained = _non_space_tokens(tokens, start, end)
    if not contained:
        raise RuntimeError("Citation feasibility group contains no lexical tokens")
    if len(contained) <= PREFERRED_TOKENS:
        return [
            {
                "source_start": start,
                "source_end": end,
                "source_text": content[start:end],
                "token_count": len(contained),
                "split": False,
            }
        ]

    output: list[dict[str, Any]] = []
    cursor = start
    token_index = 0
    while token_index < len(contained):
        desired = min(token_index + PREFERRED_TOKENS, len(contained))
        split_index = _safe_forward_split_index(
            contained,
            desired_index=desired,
            spans=spans,
        )
        if split_index <= token_index:
            raise RuntimeError("Citation feasibility token split failed to advance")
        if split_index >= len(contained):
            cut = end
            split_index = len(contained)
        else:
            cut = int(contained[split_index]["source_start"])
        if cut <= cursor:
            raise RuntimeError("Citation feasibility produced a non-positive source chunk")
        output.append(
            {
                "source_start": cursor,
                "source_end": cut,
                "source_text": content[cursor:cut],
                "token_count": split_index - token_index,
                "split": True,
            }
        )
        cursor = cut
        token_index = split_index
    if cursor != end:
        raise RuntimeError("Citation feasibility failed exact source coverage")
    if "".join(row["source_text"] for row in output) != content[start:end]:
        raise RuntimeError("Citation feasibility split is not byte-exact")
    return output


def _translate(
    translator: OpusTranslator, chunks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    max_tokens = max(int(row["token_count"]) for row in chunks)
    generated = translator.translate(
        [str(row["source_text"]) for row in chunks],
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=max(128, max_tokens * 8),
    )
    if len(generated) != len(chunks):
        raise RuntimeError("Citation feasibility OPUS cardinality drift")
    output: list[dict[str, Any]] = []
    for chunk, hypotheses in zip(chunks, generated, strict=True):
        if not hypotheses:
            raise RuntimeError("Citation feasibility OPUS returned no rank-0 hypothesis")
        target = str(hypotheses[0].get("text") or "")
        if not target.strip():
            raise RuntimeError("Citation feasibility OPUS returned an empty rank-0 target")
        output.append(
            {
                **chunk,
                "target_text": target,
                "rank": int(hypotheses[0].get("rank") or 0),
                "score": hypotheses[0].get("score"),
                "verdict": evaluate_rescue_pair(str(chunk["source_text"]), target),
            }
        )
    return output


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_CITATION_ROOT", "work/citation-input")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Citation feasibility immutable baseline inputs are missing")
    if _sha_file(baseline_path) != EXPECTED_BASELINE_JSON_SHA256:
        raise RuntimeError("Citation feasibility baseline JSON identity drift")
    if _sha_file(database) != EXPECTED_DATABASE_SHA256:
        raise RuntimeError("Citation feasibility Product database identity drift")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("Citation feasibility baseline schema drift")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Citation feasibility pinned source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Citation feasibility requires planner-v8 baseline")
    if baseline.get("structural_label_contract") != STRUCTURAL_LABEL_CONTRACT:
        raise RuntimeError("Citation feasibility structural-label contract drift")

    selected_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    nlp_run_id = int((baseline.get("stage8") or {})["nlp_run_id"])
    document_version_id = int(baseline["document_version_id"])

    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        selected_rows = get_run_items(
            connection, selected_run_id, kind="translation_segment"
        )
        contexts = get_run_items(connection, context_run_id, kind="context_sentence")
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document = get_document(connection, document_version_id)
    content = str(document["content_text"])
    if str(document["text_sha256"]) != str(baseline["source_text_sha256"]):
        raise RuntimeError("Citation feasibility persisted source text identity drift")
    if "".join(str(row.get("source_text") or "") for row in selected_rows) != content:
        raise RuntimeError("Citation feasibility selected Stage12 coverage drift")

    citations = _citation_spans(content)
    if len(citations) != EXPECTED_CITATION_COUNT:
        raise RuntimeError(
            f"Pinned Opticks citation inventory drift: {len(citations)} != {EXPECTED_CITATION_COUNT}"
        )
    balanced = _balanced_protected_spans(content, absolute_start=0)
    context_boundaries = {int(row["source_start"]) for row in contexts[1:]}
    citation_boundary_positions = sorted(
        boundary
        for boundary in context_boundaries
        if _inside(boundary, citations)
    )
    if len(citation_boundary_positions) < EXPECTED_CITATION_COUNT:
        raise RuntimeError("Not every pinned citation crosses a Stage10 sentence boundary")

    groups = _coalesced_groups(
        content,
        contexts,
        balanced=balanced,
        citations=citations,
    )
    affected = [row for row in groups if int(row["citation_boundary_count"]) > 0]
    if not affected:
        raise RuntimeError("Citation feasibility produced no affected context groups")

    selected_ordered = sorted(selected_rows, key=lambda row: int(row["source_start"]))
    translator = OpusTranslator(device="cpu", compute_type="float32")
    evidence: list[dict[str, Any]] = []
    for group in affected:
        start = int(group["start"])
        end = int(group["end"])
        primary = [
            row
            for row in selected_ordered
            if int(row["source_start"]) >= start and int(row["source_end"]) <= end
        ]
        if not primary:
            raise RuntimeError("Affected citation group has no Product Stage12 rows")
        if int(primary[0]["source_start"]) != start or int(primary[-1]["source_end"]) != end:
            raise RuntimeError("Citation group does not align to current Product row coverage")
        if "".join(str(row.get("source_text") or "") for row in primary) != content[start:end]:
            raise RuntimeError("Citation group Product rows are not byte-exact")
        for row in primary:
            planner = dict((row.get("payload") or {}).get("planner") or {})
            if planner.get("source") in {
                "ascii_table",
                "structural_label",
                "block_section_identifier",
            }:
                raise RuntimeError("Citation feasibility overlaps source-owned Product structure")

        group_spans = [
            span
            for span in balanced + citations
            if span[0] < end and span[1] > start
        ]
        chunks = _split_group(content, group, nlp_tokens, group_spans)
        candidate = _translate(translator, chunks)
        primary_for_selector = [
            {
                "source_text": str(row.get("source_text") or ""),
                "target_text": str(row.get("target_text") or ""),
            }
            for row in primary
        ]
        candidate_for_selector = [
            {
                "source_text": str(row["source_text"]),
                "target_text": str(row["target_text"]),
            }
            for row in candidate
        ]
        selection = evaluate_candidate_context(
            primary_for_selector,
            candidate_for_selector,
        )
        primary_verdicts = [
            evaluate_rescue_pair(
                str(row.get("source_text") or ""),
                str(row.get("target_text") or ""),
            )
            for row in primary
        ]
        evidence.append(
            {
                "source_start": start,
                "source_end": end,
                "source_text": content[start:end],
                "context_sequences": list(group["context_sequences"]),
                "citation_boundary_count": int(group["citation_boundary_count"]),
                "balanced_boundary_count": int(group["balanced_boundary_count"]),
                "primary_rows": [
                    {
                        "sequence_number": int(row["sequence_number"]),
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                        "verdict": verdict,
                    }
                    for row, verdict in zip(primary, primary_verdicts, strict=True)
                ],
                "candidate_chunks": candidate,
                "primary_hard_failure_count": sum(
                    verdict["product_hard_passed"] is not True
                    for verdict in primary_verdicts
                ),
                "candidate_hard_failure_count": sum(
                    (row["verdict"] or {}).get("product_hard_passed") is not True
                    for row in candidate
                ),
                "selection": selection,
                "source_bytes_rewritten": False,
                "target_rewriting": False,
                "placeholders": False,
                "post_translation_literal_injection": False,
            }
        )

    if _sha_file(database) != database_sha_before:
        raise RuntimeError("Citation feasibility mutated the immutable Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only exact planner-v8 citation-boundary coalescing feasibility; "
            "no Product planning change"
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
        "citation_span_contract": CITATION_SPAN_CONTRACT,
        "citation_regex": _CITATION_RE.pattern,
        "preferred_token_budget": PREFERRED_TOKENS,
        "citation_count": len(citations),
        "citation_spans": [
            {
                "source_start": start,
                "source_end": end,
                "source_text": content[start:end],
            }
            for start, end, _kind in citations
        ],
        "citation_crossing_context_boundary_count": len(citation_boundary_positions),
        "affected_context_group_count": len(affected),
        "affected_context_groups": evidence,
        "mechanically_accepted_group_count": sum(
            (row["selection"] or {}).get("accepted") is True for row in evidence
        ),
        "primary_hard_failure_count": sum(
            int(row["primary_hard_failure_count"]) for row in evidence
        ),
        "candidate_hard_failure_count": sum(
            int(row["candidate_hard_failure_count"]) for row in evidence
        ),
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_unchanged": True,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-citation-boundary-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "citation_count": len(citations),
                "citation_crossing_context_boundary_count": len(citation_boundary_positions),
                "affected_context_group_count": len(affected),
                "mechanically_accepted_group_count": payload[
                    "mechanically_accepted_group_count"
                ],
                "primary_hard_failure_count": payload["primary_hard_failure_count"],
                "candidate_hard_failure_count": payload["candidate_hard_failure_count"],
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
