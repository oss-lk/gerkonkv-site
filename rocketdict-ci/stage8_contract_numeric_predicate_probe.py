from __future__ import annotations

"""NON-PROMOTIONAL Stage 8 numeric-eligibility diagnostic.

This does not recreate rocketdict-numeric-integrity/3.2. It preserves the
source-proven 0.30.40 coverage-stratified-v1 defaults and changes only the
numeric-eligibility predicate, using features already recorded for the lost
3.2 evaluator. The input must be the canonical heavy SQLite.
"""

from collections import deque
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3

CANONICAL_SQLITE_SHA256 = "3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274"
EXPECTED_STREAM_SHA256 = "7a981e80c9630320d8a81aa1ae2aac3b1b6da2ae48a982c3200052aa568684c6"
WORD_RE = re.compile(r"(?u)\b\w+\b")
OLD_RE = re.compile(r"(?<![\w])(?:[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?)(?![\w])")
CONTRACT_DERIVED_RE = re.compile(
    r"(?<!\d)(?:"
    r"\d+\s*-\s*\d+\s*/\s*\d+(?:st|nd|rd|th|d)?"
    r"|\d+\s*/\s*\d+(?:st|nd|rd|th|d)?"
    r"|\d{1,3}(?:(?:,\d{3})|(?:[\s\u00a0\u202f]\d{3}))+(?:st|nd|rd|th|d)?"
    r"|\d+['’]\d+(?:st|nd|rd|th|d)?"
    r"|\d+(?:[.,]\d+)?(?:st|nd|rd|th|d)?"
    r")",
    re.IGNORECASE | re.UNICODE,
)
CRITICAL_SYMBOLS = ("=", "%", "°", "±", "×", "÷")
FAILURE_IDS = (15697, 16200, 17795)


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_json(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def words(text: str) -> int:
    return len(WORD_RE.findall(text))


def spread_pick(items: list[dict], count: int) -> list[dict]:
    if count <= 0 or not items:
        return []
    if count >= len(items):
        return list(items)
    out, seen = [], set()
    for index in range(count):
        pos = min(len(items) - 1, int(((index + 0.5) * len(items)) / count))
        item = items[pos]
        if item["id"] not in seen:
            out.append(item); seen.add(item["id"])
    if len(out) < count:
        for item in items:
            if item["id"] not in seen:
                out.append(item); seen.add(item["id"])
                if len(out) >= count:
                    break
    return out


def spread_order(items: list[dict]) -> list[dict]:
    q = deque([(0, len(items))]); out = []
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


def select(items: list[dict], numeric_re: re.Pattern[str], target_words: int = 5000) -> dict:
    selected: dict[int, dict] = {}
    def add(item: dict) -> None:
        selected[item["id"]] = item

    n = len(items)
    for bucket in range(min(8, n)):
        start = bucket * n // min(8, n)
        end = (bucket + 1) * n // min(8, n)
        if end > start:
            add(items[start + (end - start - 1) // 2])

    numeric = [x for x in items if numeric_re.search(x["text"])]
    critical = [x for x in items if any(s in x["text"] for s in CRITICAL_SYMBOLS)]
    long_units = [x for x in items if words(x["text"]) >= 24]
    numeric_seed = spread_pick(numeric, min(8, len(numeric)))
    for x in numeric_seed:
        add(x)
    for x in spread_pick(critical, min(8, len(critical))):
        add(x)
    for x in sorted(long_units, key=lambda v: (-words(v["text"]), v["sequence_number"], v["id"]))[:8]:
        add(x)

    total = sum(words(x["text"]) for x in selected.values())
    if total < target_words:
        for x in spread_order(items):
            if x["id"] in selected:
                continue
            add(x); total += words(x["text"])
            if total >= target_words:
                break
    ordered = sorted(selected.values(), key=lambda x: (x["sequence_number"], x["id"]))
    return {
        "numeric_available": len(numeric),
        "selected_occurrences": len(ordered),
        "selected_words": sum(words(x["text"]) for x in ordered),
        "numeric_seed_ids": [x["id"] for x in numeric_seed],
        "selected_ids": [x["id"] for x in ordered],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sqlite", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if sha_file(args.sqlite) != CANONICAL_SQLITE_SHA256:
        raise SystemExit("canonical SQLite SHA mismatch")

    con = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    stage = con.execute(
        "SELECT id FROM stage_results WHERE stage_name='punctuation_and_segmentation' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    rows = con.execute(
        """SELECT fo.id, fo.sequence_number, fo.canonical_fragment_id,
                  fo.structural_node_id, cf.normalized_sha256, cf.normalized_text
             FROM fragment_occurrences fo
             JOIN canonical_fragments cf ON cf.id=fo.canonical_fragment_id
            WHERE fo.stage_result_id=? AND cf.fragment_type='sentence'
            ORDER BY fo.sequence_number, fo.id""",
        (stage["id"],),
    ).fetchall()
    items = [{"id": int(r["id"]), "sequence_number": int(r["sequence_number"]), "text": r["normalized_text"]} for r in rows]
    manifest = [{k: r[k] for k in ("id", "sequence_number", "canonical_fragment_id", "structural_node_id", "normalized_sha256")} for r in rows]
    if sha_json(manifest) != EXPECTED_STREAM_SHA256:
        raise SystemExit("canonical occurrence stream SHA mismatch")

    old = select(items, OLD_RE)
    new = select(items, CONTRACT_DERIVED_RE)
    old_numeric = {x["id"] for x in items if OLD_RE.search(x["text"])}
    new_numeric = {x["id"] for x in items if CONTRACT_DERIVED_RE.search(x["text"])}
    added = sorted(new_numeric - old_numeric)
    by_id = {x["id"]: x for x in items}
    classes = {"ordinal_suffix_or_old_d": 0, "digit_letter_or_variable": 0, "other_structural": 0}
    for oid in added:
        text = by_id[oid]["text"]
        if re.search(r"\d+(?:st|nd|rd|th|d)\b", text, re.I):
            classes["ordinal_suffix_or_old_d"] += 1
        elif re.search(r"\d+[A-Za-z]|[A-Za-z]\d+", text):
            classes["digit_letter_or_variable"] += 1
        else:
            classes["other_structural"] += 1

    report = {
        "schema": "rocketdict-stage8-contract-derived-numeric-predicate-diagnostic/1",
        "promotion_allowed": False,
        "exact_numeric_integrity_3_2_claimed": False,
        "old": {k: old[k] for k in ("numeric_available", "selected_occurrences", "selected_words", "numeric_seed_ids")},
        "diagnostic": {k: new[k] for k in ("numeric_available", "selected_occurrences", "selected_words", "numeric_seed_ids")},
        "numeric_eligibility_added_count": len(added),
        "numeric_eligibility_added_id_manifest_sha256": sha_json(added),
        "numeric_eligibility_classes": classes,
        "selected_id_symmetric_difference": sorted(set(old["selected_ids"]) ^ set(new["selected_ids"])),
        "historical_failure_presence": {str(fid): {"old": fid in old["selected_ids"], "diagnostic": fid in new["selected_ids"]} for fid in FAILURE_IDS},
    }
    raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")

if __name__ == "__main__":
    main()
