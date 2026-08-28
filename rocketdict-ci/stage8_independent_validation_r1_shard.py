from __future__ import annotations

"""Parallel forward shard for Stage 8 independent validation R1.

This file changes execution topology only.  The frozen R1 selection is first
reproduced in full and hard-pinned, then partitioned by stable position modulo
SHARD_COUNT.  Every selected unit is processed by the exact existing v8 code.
No threshold, decoder setting, source transform, gate, or rescue mechanism is
changed here.  Global aggregate acceptance and O-v2/Q-v1 are evaluated only
after all shards are recombined.
"""

from collections import Counter
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_gate as base  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
import stage8_independent_validation_r1 as r1  # noqa: E402
import stage8_validation_selection_r1 as sel  # noqa: E402

SHARD_INDEX = int(os.environ.get("R1_SHARD_INDEX", "0"))
SHARD_COUNT = int(os.environ.get("R1_SHARD_COUNT", "8"))
if SHARD_COUNT < 1 or not (0 <= SHARD_INDEX < SHARD_COUNT):
    raise RuntimeError(f"invalid shard coordinates {SHARD_INDEX}/{SHARD_COUNT}")

ROOT = Path("work-stage8-independent-validation-r1-shards") / f"shard-{SHARD_INDEX}"
EVIDENCE = ROOT / "v8-evidence"
OUTPUT = ROOT / "v8-output"
CORPUS = ROOT / "corpus" / "opticks.txt"
WRAPPER = ROOT / "forward-shard.json"
UNITS_COPY = ROOT / "units-shard.jsonl"

FULL_META: dict | None = None
FULL_OCCURRENCES: list[int] | None = None
SHARD_META: dict | None = None


def shard_selector(units: list[dict]) -> tuple[list[dict], dict]:
    global FULL_META, FULL_OCCURRENCES, SHARD_META
    full, full_meta = r1.select_validation(units)
    if full_meta["selection_sha256"] != r1.EXPECTED_VALIDATION_SHA:
        raise RuntimeError("full R1 selection drift before sharding")

    shard = [u for pos, u in enumerate(full) if pos % SHARD_COUNT == SHARD_INDEX]
    if not shard:
        raise RuntimeError(f"empty R1 shard {SHARD_INDEX}/{SHARD_COUNT}")

    FULL_META = full_meta
    FULL_OCCURRENCES = [u["occurrence"] for u in full]
    serialized = sel.serialize(shard)
    SHARD_META = {
        "selector": "rocketdict-stage8-independent-validation-r1-forward-shard/1",
        "shard_index": SHARD_INDEX,
        "shard_count": SHARD_COUNT,
        "selection_sha256": base.text_sha256(serialized),
        "full_selection_sha256": r1.EXPECTED_VALIDATION_SHA,
        "full_units": len(full),
        "actual_words": sum(u["words"] for u in shard),
        "units": len(shard),
        "category_unit_counts": dict(Counter(u["category"] for u in shard)),
        "category_word_counts": {
            name: sum(u["words"] for u in shard if u["category"] == name)
            for name in sel.QUOTAS
        },
        "partition_rule": "stable full-selection position modulo shard_count",
    }
    return shard, SHARD_META


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CORPUS.parent.mkdir(parents=True, exist_ok=True)

    # Redirect only filesystem roots and selector.  Per-unit v8 code is reused.
    v5.CORPUS = CORPUS
    v5.EVIDENCE = EVIDENCE
    v5.OUTPUT = OUTPUT
    v5.TARGET_WORDS = 0  # shard size guard is replaced by full-selection hard pin above
    v5.select_challenge = shard_selector

    parent_error: str | None = None
    try:
        v8.main()
    except SystemExit as exc:
        # A shard-level aggregate may fail even though the recombined global
        # aggregate passes.  Preserve completed per-unit evidence either way.
        parent_error = str(exc)

    summary_path = EVIDENCE / "stage8-ghi-reconstruction.json"
    units_path = EVIDENCE / "units.jsonl"
    if not summary_path.exists() or not units_path.exists():
        raise RuntimeError("v8 shard did not complete enough to persist evidence")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in units_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if FULL_META is None or FULL_OCCURRENCES is None or SHARD_META is None:
        raise RuntimeError("shard selector metadata was not initialized")

    expected = [
        occ for pos, occ in enumerate(FULL_OCCURRENCES)
        if pos % SHARD_COUNT == SHARD_INDEX
    ]
    observed = [r["occurrence"] for r in rows]
    if observed != expected:
        raise RuntimeError(f"shard occurrence mismatch: {observed} != {expected}")

    full_occ_hash = base.text_sha256(",".join(map(str, FULL_OCCURRENCES)))
    payload = {
        "schema": "rocketdict-stage8-independent-validation-r1-forward-shard/1",
        "status": "FORWARD_COMPLETE",
        "execution_only_change": True,
        "mechanism_stack_changed_from_v9": False,
        "full_selection": FULL_META,
        "full_occurrences_sha256": full_occ_hash,
        "shard": SHARD_META,
        "v8_parent_error": parent_error,
        "v8_summary": summary,
        "row_count": len(rows),
        "row_occurrences": observed,
        "promotion_allowed": False,
    }
    WRAPPER.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with UNITS_COPY.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({
        "status": payload["status"],
        "shard": f"{SHARD_INDEX}/{SHARD_COUNT}",
        "units": len(rows),
        "words": SHARD_META["actual_words"],
        "full_selection_sha256": FULL_META["selection_sha256"],
        "v8_parent_error": parent_error,
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
