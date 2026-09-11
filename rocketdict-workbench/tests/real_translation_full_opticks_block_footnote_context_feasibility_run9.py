from __future__ import annotations

"""Research-only n-best full-footnote-context feasibility over persisted run 9.

The current Stage12 rows do not always end exactly at the semantic footnote
paragraph boundary: H and M own three additional newline bytes in their final
row.  This harness therefore separates source-defined marker/body/paragraph
separator bytes from the enclosing run-9 row-coverage envelope.  Only the
linguistic body is sent to OPUS; marker, paragraph separator, and any additional
trailing blank-line bytes are preserved byte-exactly as source-owned structure.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-block-footnote-context-feasibility-run9/2"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
STARTS = [151466, 151557, 253849, 253919, 254102]
LETTERS = list("GHJKM")
PARAGRAPH_ENDS = [151557, 151652, 253919, 254026, 254202]
ROW_COVERAGE_ENDS = [151557, 151655, 253919, 254026, 254205]
MARKER = re.compile(r"^\[(?P<letter>[A-Z])\](?P<space>[ \t]+)")


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


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _verdict(source: str, target: str) -> dict[str, Any]:
    return evaluate_rescue_pair(str(source or ""), str(target or ""))


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    unique: set[int] = set()
    for row in _ordered(rows):
        verdict = _verdict(row.get("source_text"), row.get("target_text"))
        sequence = int(row["sequence_number"])
        tests = {
            "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key, failed in tests.items():
            if failed:
                counts[key] += 1
                unique.add(sequence)
    return {**counts, "unique": len(unique)}


def _counterfactual(
    rows: list[dict[str, Any]], replacements: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    skipped: set[int] = set()
    for row in _ordered(rows):
        start = int(row["source_start"])
        if start in skipped:
            continue
        replacement = replacements.get(start)
        if replacement is None:
            result.append(dict(row))
            continue
        result.extend(replacement["rows"])
        coverage_end = int(replacement["row_coverage_end"])
        skipped.update(
            int(candidate["source_start"])
            for candidate in rows
            if start < int(candidate["source_start"]) < coverage_end
        )
    result.sort(key=lambda row: int(row["source_start"]))
    for sequence, row in enumerate(result):
        row["sequence_number"] = sequence
    return result


def _source_owned_row(
    *, start: int, end: int, source: str, role: str
) -> dict[str, Any]:
    return {
        "sequence_number": 0,
        "kind": "translation_segment",
        "source_start": start,
        "source_end": end,
        "source_text": source,
        "target_text": source,
        "payload": {
            "research_source_owned_block_footnote_structure": True,
            "source_owned_role": role,
        },
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_FOOTNOTE_CONTEXT_RUN9_ROOT",
            "work/footnote-context-run9",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != DB_SHA:
        raise RuntimeError("run9 db identity drift")
    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN_ID)
        rows = get_run_items(connection, RUN_ID, kind="translation_segment")
        document = get_document(
            connection, int(dict(run.get("output") or {})["document_version_id"])
        )
    if str(run.get("output_sha256") or "") != OUTPUT_SHA:
        raise RuntimeError("run9 output identity drift")
    if str(document.get("text_sha256") or "") != TEXT_SHA:
        raise RuntimeError("run9 source identity drift")
    content = str(document["content_text"])
    rows = _ordered(rows)
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run9 source coverage drift")
    if _inventory(rows) != BASE:
        raise RuntimeError(f"run9 hard-gate drift: {_inventory(rows)!r}")

    by_start = {int(row["source_start"]): row for row in rows}
    groups: list[dict[str, Any]] = []
    for start, letter, expected_paragraph_end, expected_coverage_end in zip(
        STARTS, LETTERS, PARAGRAPH_ENDS, ROW_COVERAGE_ENDS, strict=True
    ):
        first = by_start[start]
        first_source = str(first.get("source_text") or "")
        match = MARKER.match(first_source)
        if match is None or match.group("letter") != letter:
            raise RuntimeError(f"footnote marker trigger drift {letter}")
        if _verdict(first_source, first.get("target_text")).get("product_hard_passed") is True:
            raise RuntimeError(f"footnote hard-failure trigger drift {letter}")

        marker = first_source[: match.end()]
        marker_end = start + len(marker)
        separator_start = content.find("\n\n", start)
        if separator_start < 0:
            raise RuntimeError(f"footnote paragraph separator missing {letter}")
        paragraph_end = separator_start + 2
        if paragraph_end != expected_paragraph_end:
            raise RuntimeError(
                f"footnote semantic paragraph end drift {letter}: {paragraph_end}"
            )

        members: list[dict[str, Any]] = []
        cursor = start
        for row in rows:
            row_start = int(row["source_start"])
            row_end = int(row["source_end"])
            if row_end <= start:
                continue
            if row_start >= expected_coverage_end:
                break
            if row_start != cursor:
                raise RuntimeError(f"footnote row coverage gap {letter} at {cursor}")
            members.append(row)
            cursor = row_end
            if cursor >= expected_coverage_end:
                break
        if cursor != expected_coverage_end:
            raise RuntimeError(
                f"footnote row coverage end drift {letter}: {cursor}"
            )
        envelope_source = content[start:expected_coverage_end]
        if "".join(str(row.get("source_text") or "") for row in members) != envelope_source:
            raise RuntimeError(f"footnote row coverage bytes drift {letter}")
        if paragraph_end > expected_coverage_end:
            raise RuntimeError(f"footnote semantic boundary exceeds row coverage {letter}")

        body = content[marker_end:separator_start]
        paragraph_separator = content[separator_start:paragraph_end]
        trailing = content[paragraph_end:expected_coverage_end]
        if not body.strip():
            raise RuntimeError(f"footnote linguistic body unexpectedly empty {letter}")
        if paragraph_separator != "\n\n":
            raise RuntimeError(f"footnote paragraph separator drift {letter}")
        if trailing.strip():
            raise RuntimeError(f"footnote trailing row bytes are not whitespace {letter}")

        groups.append(
            {
                "letter": letter,
                "start": start,
                "marker_end": marker_end,
                "body_end": separator_start,
                "paragraph_end": paragraph_end,
                "row_coverage_end": expected_coverage_end,
                "marker": marker,
                "body": body,
                "paragraph_separator": paragraph_separator,
                "trailing": trailing,
                "members": members,
                "semantic_source": content[start:paragraph_end],
                "envelope_source": envelope_source,
            }
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [group["body"] for group in groups],
        beam_size=6,
        num_hypotheses=6,
        max_decoding_length=256,
    )
    if len(generated) != len(groups) or any(len(hypotheses) != 6 for hypotheses in generated):
        raise RuntimeError("footnote-context n-best cardinality drift")

    replacements: dict[int, dict[str, Any]] = {}
    cases: list[dict[str, Any]] = []
    for group, hypotheses in zip(groups, generated, strict=True):
        evaluated: list[dict[str, Any]] = []
        first_admissible: int | None = None
        marker_verdict = _verdict(group["marker"], group["marker"])
        for rank, hypothesis in enumerate(hypotheses):
            target = str(hypothesis.get("text") or "")
            body_verdict = _verdict(group["body"], target)
            emphasis = compare_emphasis_markup_preservation(group["body"], target)
            admissible = (
                marker_verdict.get("strictly_eligible") is True
                and body_verdict.get("strictly_eligible") is True
                and emphasis.get("passed") is True
            )
            evaluated.append(
                {
                    "rank": rank,
                    "target_text": target,
                    "score": hypothesis.get("score"),
                    "body_verdict": body_verdict,
                    "emphasis_markup": emphasis,
                    "mechanically_admissible": admissible,
                }
            )
            if first_admissible is None and admissible:
                first_admissible = rank

        if first_admissible is not None:
            target = str(evaluated[first_admissible]["target_text"])
            replacement_rows = [
                _source_owned_row(
                    start=int(group["start"]),
                    end=int(group["marker_end"]),
                    source=str(group["marker"]),
                    role="marker",
                ),
                {
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": int(group["marker_end"]),
                    "source_end": int(group["body_end"]),
                    "source_text": str(group["body"]),
                    "target_text": target,
                    "payload": {
                        "research_raw_nbest_whole_footnote_body": True,
                        "selected_rank": first_admissible,
                    },
                },
                _source_owned_row(
                    start=int(group["body_end"]),
                    end=int(group["paragraph_end"]),
                    source=str(group["paragraph_separator"]),
                    role="paragraph_separator",
                ),
            ]
            if group["trailing"]:
                replacement_rows.append(
                    _source_owned_row(
                        start=int(group["paragraph_end"]),
                        end=int(group["row_coverage_end"]),
                        source=str(group["trailing"]),
                        role="row_trailing_whitespace",
                    )
                )
            if "".join(str(row["source_text"]) for row in replacement_rows) != str(
                group["envelope_source"]
            ):
                raise RuntimeError(
                    f"footnote replacement source envelope drift {group['letter']}"
                )
            replacements[int(group["start"])] = {
                "row_coverage_end": int(group["row_coverage_end"]),
                "rows": replacement_rows,
            }

        cases.append(
            {
                "letter": group["letter"],
                "source_start": group["start"],
                "semantic_paragraph_end": group["paragraph_end"],
                "row_coverage_end": group["row_coverage_end"],
                "semantic_source": group["semantic_source"],
                "envelope_source": group["envelope_source"],
                "marker_source": group["marker"],
                "body_source": group["body"],
                "paragraph_separator_source": group["paragraph_separator"],
                "row_trailing_whitespace_source": group["trailing"],
                "primary_member_spans": [
                    [int(row["source_start"]), int(row["source_end"])]
                    for row in group["members"]
                ],
                "hypotheses": evaluated,
                "first_mechanically_admissible_rank": first_admissible,
                "first_mechanically_admissible_target": (
                    None
                    if first_admissible is None
                    else evaluated[first_admissible]["target_text"]
                ),
            }
        )

    candidate = _counterfactual(rows, replacements)
    if "".join(str(row.get("source_text") or "") for row in candidate) != content:
        raise RuntimeError("footnote-context counterfactual source coverage drift")
    counts = _inventory(candidate)
    if any(counts[key] > BASE[key] for key in BASE):
        raise RuntimeError(f"footnote-context counterfactual regression: {counts!r}")
    if _sha(database) != DB_SHA:
        raise RuntimeError("footnote-context research mutated database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only source-owned marker/separators plus complete linguistic "
            "footnote body n-best; emphasis preservation is mandatory mechanical veto"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": OUTPUT_SHA,
        "attempted_source_starts": STARTS,
        "attempted_letters": LETTERS,
        "semantic_paragraph_ends": PARAGRAPH_ENDS,
        "row_coverage_ends": ROW_COVERAGE_ENDS,
        "base_hard_gate_counts": BASE,
        "counterfactual_hard_gate_counts": counts,
        "base_segment_count": len(rows),
        "counterfactual_segment_count": len(candidate),
        "mechanically_admissible_letters": [
            case["letter"]
            for case in cases
            if case["first_mechanically_admissible_rank"] is not None
        ],
        "cases": cases,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-block-footnote-context-feasibility-run9.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "mechanically_admissible_letters": payload[
                    "mechanically_admissible_letters"
                ],
                "selected": [
                    (
                        case["letter"],
                        case["first_mechanically_admissible_rank"],
                        case["first_mechanically_admissible_target"],
                    )
                    for case in cases
                ],
                "counterfactual_hard_gate_counts": counts,
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
