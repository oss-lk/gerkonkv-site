from __future__ import annotations

"""Read-only run-9 feasibility for hard-failing block-start footnote markers."""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-block-footnote-marker-feasibility-run9/1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
BASE_RUN_ID = 9
BASE_OUTPUT_SHA256 = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
BASE_COUNTS = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
EXPECTED_ALL_LETTERS = list("ABCDEFGHIJKLM")
EXPECTED_HARD_STARTS = [151466, 151557, 253849, 253919, 254102]
EXPECTED_HARD_LETTERS = list("GHJKM")
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


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _flags(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool]]:
    verdict = evaluate_rescue_pair(
        str(row.get("source_text") or ""), str(row.get("target_text") or "")
    )
    return verdict, {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    unique: set[int] = set()
    for row in _ordered(rows):
        _, flags = _flags(row)
        sequence = int(row["sequence_number"])
        for key, failed in flags.items():
            if failed:
                counts[key] += 1
                unique.add(sequence)
    return {**counts, "unique": len(unique)}


def _counterfactual(
    rows: list[dict[str, Any]], replacements: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in _ordered(rows):
        result.extend(replacements.get(int(row["source_start"]), [dict(row)]))
    result.sort(key=lambda row: int(row["source_start"]))
    for sequence, row in enumerate(result):
        row["sequence_number"] = sequence
    return result


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_FOOTNOTE_RUN9_ROOT", "work/footnote-run9")
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("run9 database identity drift")
    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        document = get_document(
            connection, int(dict(run.get("output") or {})["document_version_id"])
        )
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run9 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    content = str(document["content_text"])
    ordered = _ordered(rows)
    if "".join(str(row.get("source_text") or "") for row in ordered) != content:
        raise RuntimeError("run9 source coverage drift")
    if _inventory(rows) != BASE_COUNTS:
        raise RuntimeError(f"run9 hard gate drift: {_inventory(rows)!r}")

    all_cases: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for row in ordered:
        source = str(row.get("source_text") or "")
        match = _MARKER_RE.match(source)
        if match is None:
            continue
        marker = source[: match.end()]
        body = source[match.end() :]
        if not body.strip():
            raise RuntimeError("block footnote marker without body")
        verdict, flags = _flags(row)
        case = {
            "row": row,
            "letter": match.group("letter"),
            "marker": marker,
            "body": body,
            "base_verdict": verdict,
            "base_failures": [key for key, failed in flags.items() if failed],
        }
        all_cases.append(case)
        if verdict.get("product_hard_passed") is not True:
            attempts.append(case)
    if [case["letter"] for case in all_cases] != EXPECTED_ALL_LETTERS:
        raise RuntimeError("block footnote inventory drift")
    if [int(case["row"]["source_start"]) for case in attempts] != EXPECTED_HARD_STARTS:
        raise RuntimeError("hard-failing block footnote source cohort drift")
    if [case["letter"] for case in attempts] != EXPECTED_HARD_LETTERS:
        raise RuntimeError("hard-failing block footnote letter cohort drift")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [case["body"] for case in attempts],
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=256,
    )
    if len(generated) != len(attempts) or any(len(hypotheses) != 1 for hypotheses in generated):
        raise RuntimeError("OPUS cardinality drift")

    replacements: dict[int, list[dict[str, Any]]] = {}
    cases: list[dict[str, Any]] = []
    for attempt, hypotheses in zip(attempts, generated, strict=True):
        hypothesis = hypotheses[0]
        target = str(hypothesis.get("text") or "")
        marker_verdict = evaluate_rescue_pair(attempt["marker"], attempt["marker"])
        body_verdict = evaluate_rescue_pair(attempt["body"], target)
        accepted = (
            marker_verdict.get("strictly_eligible") is True
            and body_verdict.get("strictly_eligible") is True
        )
        row = attempt["row"]
        start = int(row["source_start"])
        boundary = start + len(attempt["marker"])
        end = int(row["source_end"])
        if accepted:
            replacements[start] = [
                {
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": start,
                    "source_end": boundary,
                    "source_text": attempt["marker"],
                    "target_text": attempt["marker"],
                    "payload": {"research_source_owned_block_footnote_marker": True},
                },
                {
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": boundary,
                    "source_end": end,
                    "source_text": attempt["body"],
                    "target_text": target,
                    "payload": {"research_raw_rank0_footnote_body": True},
                },
            ]
        cases.append(
            {
                "source_start": start,
                "source_end": end,
                "letter": attempt["letter"],
                "base_source": str(row.get("source_text") or ""),
                "base_target": str(row.get("target_text") or ""),
                "base_failures": attempt["base_failures"],
                "marker_source": attempt["marker"],
                "body_source": attempt["body"],
                "body_rank0_target": target,
                "body_rank0_score": hypothesis.get("score"),
                "marker_verdict": marker_verdict,
                "body_verdict": body_verdict,
                "accepted": accepted,
                "raw_model_rank0": True,
            }
        )

    candidate = _counterfactual(rows, replacements)
    if "".join(str(row.get("source_text") or "") for row in candidate) != content:
        raise RuntimeError("counterfactual source coverage drift")
    counts = _inventory(candidate)
    if (
        counts["numeric_symbol"] > BASE_COUNTS["numeric_symbol"]
        or counts["punctuation"] > BASE_COUNTS["punctuation"]
        or counts["length"] > BASE_COUNTS["length"]
        or counts["unique"] > BASE_COUNTS["unique"]
    ):
        raise RuntimeError(f"hard gate regression: {counts!r}")
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("read-only database mutated")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only run9 feasibility for source-owned block-start footnote markers on already-hard-failing rows only",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "all_block_marker_letters": [case["letter"] for case in all_cases],
        "attempted_source_starts": [int(case["row"]["source_start"]) for case in attempts],
        "attempted_letters": [case["letter"] for case in attempts],
        "accepted_source_starts": [case["source_start"] for case in cases if case["accepted"]],
        "accepted_letters": [case["letter"] for case in cases if case["accepted"]],
        "base_hard_gate_counts": BASE_COUNTS,
        "counterfactual_hard_gate_counts": counts,
        "base_segment_count": len(rows),
        "counterfactual_segment_count": len(candidate),
        "cases": cases,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-block-footnote-marker-feasibility-run9.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "attempted_letters",
                    "accepted_letters",
                    "accepted_source_starts",
                    "base_hard_gate_counts",
                    "counterfactual_hard_gate_counts",
                    "evidence_sha256",
                )
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
