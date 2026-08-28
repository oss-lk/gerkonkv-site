from __future__ import annotations

"""Verify the recovered canonical RocketDict heavy SQLite and emit Stage-8 recovery evidence.

This tool does NOT reconstruct or promote F96. It verifies the immutable heavy
SQLite identity, freezes the final Stage-7 sentence-occurrence stream, proves the
three historical F96 failure IDs are members of that stream, and runs the older
coverage-stratified-v1 policy directly on those occurrences as a diagnostic.
"""

from collections import deque
from dataclasses import dataclass
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3

CANONICAL_SQLITE_SHA256 = "3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274"
EXPECTED_STAGE_NAME = "punctuation_and_segmentation"
EXPECTED_STAGE_VERSION = "1.4"
EXPECTED_STAGE_OUTPUT_SHA256 = "81aee8f4762745856251d619a6cfc90935d5437816562023a80651797f24b851"
EXPECTED_SENTENCE_COUNT = 2914
EXPECTED_STREAM_MANIFEST_SHA256 = "4cc87876a99f84419fc2598a895469eb1e5e4d8c5a7136659c6536b9db30e063"
FAILURE_IDS = (15697, 16200, 17795)
WORD_RE = re.compile(r"(?u)\b\w+\b")
NUMBER_RE = re.compile(r"(?<![\w])(?:[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?)(?![\w])")
CRITICAL_SYMBOLS = ("=", "%", "°", "±", "×", "÷")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_json(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def words(text: str) -> int:
    return len(WORD_RE.findall(text))


@dataclass(frozen=True)
class Occurrence:
    id: int
    sequence_number: int
    canonical_fragment_id: int
    structural_node_id: int | None
    text: str
    normalized_sha256: str
    source_start_line: int | None
    source_end_line: int | None


def spread_pick(items: list[Occurrence], count: int) -> list[Occurrence]:
    if count <= 0 or not items:
        return []
    if count >= len(items):
        return list(items)
    result: list[Occurrence] = []
    seen: set[int] = set()
    for index in range(count):
        position = min(len(items) - 1, int(((index + 0.5) * len(items)) / count))
        item = items[position]
        if item.id not in seen:
            result.append(item)
            seen.add(item.id)
    if len(result) < count:
        for item in items:
            if item.id not in seen:
                result.append(item)
                seen.add(item.id)
                if len(result) >= count:
                    break
    return result


def spread_order(items: list[Occurrence]) -> list[Occurrence]:
    q: deque[tuple[int, int]] = deque([(0, len(items))])
    out: list[Occurrence] = []
    while q:
        start, end = q.popleft()
        if end <= start:
            continue
        middle = start + (end - start - 1) // 2
        out.append(items[middle])
        if start < middle:
            q.append((start, middle))
        if middle + 1 < end:
            q.append((middle + 1, end))
    return out


def coverage_stratified_v1_occurrence_diagnostic(items: list[Occurrence], target_words: int = 5000) -> dict:
    selected: dict[int, Occurrence] = {}
    reasons: dict[int, set[str]] = {}

    def add(item: Occurrence, reason: str) -> None:
        selected[item.id] = item
        reasons.setdefault(item.id, set()).add(reason)

    n = len(items)
    for bucket in range(min(8, n)):
        start = bucket * n // min(8, n)
        end = (bucket + 1) * n // min(8, n)
        if end > start:
            add(items[start + (end - start - 1) // 2], f"position_bucket:{bucket}")

    numeric = [x for x in items if NUMBER_RE.search(x.text)]
    critical = [x for x in items if any(s in x.text for s in CRITICAL_SYMBOLS)]
    long_items = [x for x in items if words(x.text) >= 24]
    for x in spread_pick(numeric, min(8, len(numeric))):
        add(x, "numeric")
    for x in spread_pick(critical, min(8, len(critical))):
        add(x, "critical_symbol")
    for x in sorted(long_items, key=lambda v: (-words(v.text), v.sequence_number, v.id))[:8]:
        add(x, "long_unit")

    total = sum(words(x.text) for x in selected.values())
    if total < target_words:
        for x in spread_order(items):
            if x.id in selected:
                continue
            add(x, "budget_fill")
            total += words(x.text)
            if total >= target_words:
                break

    ordered = sorted(selected.values(), key=lambda x: (x.sequence_number, x.id))
    return {
        "contract": "coverage-stratified-v1 applied directly to sentence occurrences (diagnostic only)",
        "target_words": target_words,
        "selected_occurrences": len(ordered),
        "selected_words": sum(words(x.text) for x in ordered),
        "contains_historical_f96_failure_ids": {str(fid): fid in selected for fid in FAILURE_IDS},
        "all_historical_failure_ids_present": all(fid in selected for fid in FAILURE_IDS),
        "selected_occurrence_ids_sha256": sha_json([x.id for x in ordered]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sqlite", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    db_sha = sha_file(args.sqlite)
    if db_sha != CANONICAL_SQLITE_SHA256:
        raise SystemExit(f"canonical SQLite SHA mismatch: {db_sha}")

    con = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    quick = con.execute("PRAGMA quick_check").fetchone()[0]
    if quick != "ok":
        raise SystemExit(f"SQLite quick_check failed: {quick}")

    stage = con.execute(
        "SELECT * FROM stage_results WHERE stage_name=? ORDER BY id DESC LIMIT 1",
        (EXPECTED_STAGE_NAME,),
    ).fetchone()
    if not stage:
        raise SystemExit("final punctuation_and_segmentation stage missing")
    if stage["stage_version"] != EXPECTED_STAGE_VERSION or stage["output_hash"] != EXPECTED_STAGE_OUTPUT_SHA256:
        raise SystemExit("final segmentation stage identity mismatch")

    rows = con.execute(
        """
        SELECT fo.id, fo.sequence_number, fo.canonical_fragment_id, fo.structural_node_id,
               cf.normalized_text, cf.normalized_sha256,
               fo.source_start_line, fo.source_end_line
          FROM fragment_occurrences fo
          JOIN canonical_fragments cf ON cf.id = fo.canonical_fragment_id
         WHERE fo.stage_result_id = ? AND cf.fragment_type = 'sentence'
         ORDER BY fo.sequence_number, fo.id
        """,
        (stage["id"],),
    ).fetchall()
    items = [
        Occurrence(
            id=int(r["id"]),
            sequence_number=int(r["sequence_number"]),
            canonical_fragment_id=int(r["canonical_fragment_id"]),
            structural_node_id=None if r["structural_node_id"] is None else int(r["structural_node_id"]),
            text=str(r["normalized_text"]),
            normalized_sha256=str(r["normalized_sha256"]),
            source_start_line=r["source_start_line"],
            source_end_line=r["source_end_line"],
        )
        for r in rows
    ]
    if len(items) != EXPECTED_SENTENCE_COUNT:
        raise SystemExit(f"sentence occurrence count mismatch: {len(items)}")

    manifest = [
        {
            "id": x.id,
            "sequence_number": x.sequence_number,
            "canonical_fragment_id": x.canonical_fragment_id,
            "structural_node_id": x.structural_node_id,
            "normalized_sha256": x.normalized_sha256,
            "source_start_line": x.source_start_line,
            "source_end_line": x.source_end_line,
        }
        for x in items
    ]
    manifest_sha = sha_json(manifest)
    if manifest_sha != EXPECTED_STREAM_MANIFEST_SHA256:
        raise SystemExit(f"sentence stream manifest SHA mismatch: {manifest_sha}")

    by_id = {x.id: x for x in items}
    failures = {}
    for fid in FAILURE_IDS:
        x = by_id.get(fid)
        if x is None:
            raise SystemExit(f"historical F96 occurrence {fid} missing from final sentence stream")
        failures[str(fid)] = {
            "sequence_number": x.sequence_number,
            "canonical_fragment_id": x.canonical_fragment_id,
            "structural_node_id": x.structural_node_id,
            "normalized_sha256": x.normalized_sha256,
            "source_start_line": x.source_start_line,
            "source_end_line": x.source_end_line,
            "characters": len(x.text),
            "regex_words": words(x.text),
        }

    summary = json.loads(stage["result_summary_json"])
    report = {
        "schema": "rocketdict-stage8-canonical-heavy-recovery/1",
        "promotion_allowed": False,
        "claim": "exact canonical pre-Stage8 heavy/source-stream recovery; Stage8 F96 selector/evaluator identity still missing",
        "sqlite": {"sha256": db_sha, "quick_check": quick},
        "final_segmentation_stage": {
            "id": int(stage["id"]),
            "stage_name": stage["stage_name"],
            "stage_version": stage["stage_version"],
            "input_hash": stage["input_hash"],
            "settings_hash": stage["settings_hash"],
            "output_hash": stage["output_hash"],
            "paragraph_count": summary.get("paragraph_count"),
            "sentence_count": summary.get("sentence_count"),
            "heading_count": summary.get("heading_count"),
            "section_count": summary.get("section_count"),
            "versions": summary.get("versions"),
        },
        "sentence_occurrence_stream": {
            "count": len(items),
            "manifest_sha256": manifest_sha,
            "ordering": ["fragment_occurrences.sequence_number", "fragment_occurrences.id"],
            "fragment_type": "sentence",
        },
        "historical_f96_failures": failures,
        "older_selector_diagnostic": coverage_stratified_v1_occurrence_diagnostic(items),
        "interpretation": [
            "The canonical Stage7/final segmentation input stream no longer needs reconstruction from the public Gutenberg text.",
            "The earlier spaCy-based Stage7 recovery DOE is superseded for F96 source-stream recovery.",
            "The older coverage-stratified-v1 policy is related evidence only: on exact occurrences it selects all three historical failure IDs but yields 100 occurrences / 5025 words, not historical F96 109 / 5000.",
            "Remaining exact-handoff blockers are the late Stage8 challenge selector, numeric-integrity/3.2 evaluator, and missing 0.30.40 overlay/Research Vault bytes.",
        ],
    }
    raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")


if __name__ == "__main__":
    main()
