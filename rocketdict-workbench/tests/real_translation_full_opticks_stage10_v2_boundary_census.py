from __future__ import annotations

"""Read-only census of every full-Opticks Stage8 boundary merged by Stage10 v2."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.context_sentence_boundaries import (
    STAGE10_BOUNDARY_POLICY,
    STAGE10_CONTEXT_IMPLEMENTATION_V1,
    coalesce_spacy_sentence_groups,
)
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_stage import _balanced_protected_spans

SCHEMA = "rocketdict-full-opticks-stage10-v2-boundary-census/1"
BASE_DATABASE_SHA256 = "573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11"
BASE_RUN_ID = 16
BASE_OUTPUT_SHA256 = "767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
WHENCE_BOUNDARY_OFFSET = 522572


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _token_view(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    return {
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "text": str(row.get("source_text") or ""),
        "token_index": payload.get("token_index"),
        "lemma": payload.get("lemma"),
        "pos": payload.get("pos"),
        "tag": payload.get("tag"),
        "dependency": payload.get("dependency"),
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_STAGE10_V2_CENSUS_ROOT", "work/full-opticks-stage10-v2-boundary-census")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("Stage10 boundary census requires exact persisted run-16 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_output = dict(base_run.get("output") or {})
        context_run_id = int(base_output["context_run_id"])
        context_run = get_run(connection, context_run_id)
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-16 output identity drift")
    if str(context_run.get("implementation") or "") != STAGE10_CONTEXT_IMPLEMENTATION_V1:
        raise RuntimeError("run-16 context implementation is not Stage10 v1")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run-16 source identity drift")
    content = str(document["content_text"])

    grouped: dict[int, list[dict[str, Any]]] = {}
    for token in tokens:
        sentence = int((token.get("payload") or {}).get("sentence_index") or 0)
        grouped.setdefault(sentence, []).append(token)
    groups = coalesce_spacy_sentence_groups(grouped, content)
    protected = _balanced_protected_spans(content, absolute_start=0)

    decisions: list[dict[str, Any]] = []
    for group in groups:
        for raw_decision in list(group["coalesced_boundaries"]):
            decision = dict(raw_decision)
            offset = int(decision["source_offset"])
            left_index = int(decision["left_sentence_index"])
            right_index = int(decision["right_sentence_index"])
            left = sorted(grouped[left_index], key=lambda row: int(row["source_start"]))
            right = sorted(grouped[right_index], key=lambda row: int(row["source_start"]))
            containing = [
                {"start": start, "end": end, "kind": kind}
                for start, end, kind in protected
                if start < offset < end
            ]
            left_start = int(left[0]["source_start"])
            left_end = int(left[-1]["source_end"])
            right_start = int(right[0]["source_start"])
            right_end = int(right[-1]["source_end"])
            decision.update(
                {
                    "inside_stage12_protected_span": bool(containing),
                    "containing_stage12_protected_spans": containing,
                    "left_source_start": left_start,
                    "left_source_end": left_end,
                    "right_source_start": right_start,
                    "right_source_end": right_end,
                    "left_tail": content[max(left_start, offset - 240):offset],
                    "right_head": content[offset:min(right_end, offset + 240)],
                    "source_excerpt": content[max(0, offset - 180):min(len(content), offset + 260)],
                    "left_last_tokens": [_token_view(row) for row in left[-6:]],
                    "right_first_tokens": [_token_view(row) for row in right[:6]],
                }
            )
            decisions.append(decision)
    decisions.sort(key=lambda row: int(row["source_offset"]))

    inside = [row for row in decisions if row["inside_stage12_protected_span"]]
    outside = [row for row in decisions if not row["inside_stage12_protected_span"]]
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only raw Stage8 census for Stage10-v2 lowercase-continuation coalescing",
        "database_mutated": False,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "boundary_policy": STAGE10_BOUNDARY_POLICY,
        "raw_spacy_sentence_count": len(grouped),
        "stage10_v2_context_group_count": len(groups),
        "merged_boundary_count": len(decisions),
        "inside_stage12_protected_span_count": len(inside),
        "outside_stage12_protected_span_count": len(outside),
        "all_boundary_offsets": [int(row["source_offset"]) for row in decisions],
        "inside_stage12_protected_span_offsets": [int(row["source_offset"]) for row in inside],
        "outside_stage12_protected_span_offsets": [int(row["source_offset"]) for row in outside],
        "known_whence_boundary_present": WHENCE_BOUNDARY_OFFSET in {int(row["source_offset"]) for row in decisions},
        "decisions": decisions,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-stage10-v2-boundary-census.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if not evidence["known_whence_boundary_present"]:
        raise RuntimeError("known whence boundary missing from Stage10-v2 census")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
