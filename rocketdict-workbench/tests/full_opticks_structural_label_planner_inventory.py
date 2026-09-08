from __future__ import annotations

"""Read-only full-Opticks inventory of structural labels against current Stage12 units.

The probe reconstructs the exact maintained Stage12 plan from the immutable
Stage8/10 research database retained by the full-Opticks v5 artifact.  It does
not run MT or mutate the database.  Every Exper./Obs./Qu. source event is mapped
to overlapping Stage12 units so planner-boundary damage is measured before any
Product structural-label execution policy is promoted.
"""

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_document_segments, get_run_items
from rocketdict.translation_stage import PLANNER_CONTRACT, segment_translation_units

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_full_opticks_structural_label_feasibility import (  # noqa: E402
    BASE_SCHEMA,
    OPTICKS_SHA256,
    _LABEL_RE,
    _canonical_sha,
)

SCHEMA = "rocketdict-full-opticks-structural-label-planner-inventory/1"


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _position(unit_text: str, relative_start: int, relative_end: int) -> str:
    before = unit_text[:relative_start]
    after = unit_text[relative_end:]
    has_before = bool(before.strip())
    has_after = bool(after.strip())
    if not has_before and not has_after:
        return "label_only"
    if not has_before:
        return "prefix"
    if not has_after:
        return "suffix"
    return "middle"


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress"
        )
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    sources = sorted((root / "project" / "uploads").glob("*.txt"))
    if not baseline_path.is_file() or not database.is_file() or len(sources) != 1:
        raise RuntimeError("full-Opticks planner inventory inputs are incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"unexpected baseline schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("baseline Opticks source identity drift")
    if _sha_file(sources[0]) != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source hash drift")
    source = sources[0].read_text(encoding="utf-8-sig")

    document_version_id = int(baseline["document_version_id"])
    nlp_run_id = int((baseline.get("stage8") or {})["nlp_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    preferred = int((baseline.get("stage12_parameters") or {}).get("plan_preferred_unit_tokens") or 64)
    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        document_segments = get_document_segments(connection, document_version_id)
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
    content = str(document["content_text"])
    if content != source:
        raise RuntimeError("database immutable content differs from retained source upload")
    units = segment_translation_units(
        content,
        document_segments,
        context_rows,
        nlp_tokens,
        selected_format=str(document["selected_format"]),
        preferred_tokens=preferred,
    )
    if "".join(str(row["text"]) for row in units) != content:
        raise RuntimeError("current Stage12 plan is not byte-exact")

    events: list[dict[str, Any]] = []
    overlap_count_distribution: Counter[int] = Counter()
    contained_count = 0
    crossing_count = 0
    position_counts: Counter[str] = Counter()
    labels_per_unit: defaultdict[int, list[int]] = defaultdict(list)
    for event_index, match in enumerate(_LABEL_RE.finditer(content)):
        overlaps = [
            index
            for index, unit in enumerate(units)
            if int(unit["end"]) > match.start() and int(unit["start"]) < match.end()
        ]
        overlap_count_distribution[len(overlaps)] += 1
        contained = [
            index
            for index in overlaps
            if int(units[index]["start"]) <= match.start()
            and int(units[index]["end"]) >= match.end()
        ]
        row: dict[str, Any] = {
            "event_index": event_index,
            "source_start": int(match.start()),
            "source_end": int(match.end()),
            "source_text": match.group(0),
            "kind": str(match.group("kind")).lower(),
            "number": str(match.group("number")),
            "overlapping_unit_indices": overlaps,
            "contained_unit_index": None,
            "position": "cross_unit",
            "overlap_units": [
                {
                    "unit_index": index,
                    "start": int(units[index]["start"]),
                    "end": int(units[index]["end"]),
                    "source_text": str(units[index]["text"]),
                    "planner": dict(units[index].get("metadata") or {}),
                }
                for index in overlaps
            ],
        }
        if len(contained) == 1:
            contained_count += 1
            index = contained[0]
            unit = units[index]
            relative_start = match.start() - int(unit["start"])
            relative_end = match.end() - int(unit["start"])
            position = _position(str(unit["text"]), relative_start, relative_end)
            row["contained_unit_index"] = index
            row["position"] = position
            row["relative_start"] = relative_start
            row["relative_end"] = relative_end
            position_counts[position] += 1
            labels_per_unit[index].append(event_index)
        else:
            crossing_count += 1
            position_counts["cross_unit"] += 1
        events.append(row)

    if not events:
        raise RuntimeError("no supported structural labels found")
    multi_label_units = {
        str(index): event_indices
        for index, event_indices in sorted(labels_per_unit.items())
        if len(event_indices) > 1
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "byte-exact mapping of every supported structural label to current Stage12 planner units",
        "promotion_allowed": False,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "preferred_tokens": preferred,
        "planned_unit_count": len(units),
        "event_count": len(events),
        "contained_event_count": contained_count,
        "cross_unit_event_count": crossing_count,
        "position_counts": dict(sorted(position_counts.items())),
        "overlap_count_distribution": {
            str(key): value for key, value in sorted(overlap_count_distribution.items())
        },
        "multi_label_unit_count": len(multi_label_units),
        "multi_label_units": multi_label_units,
        "database_sha256": _sha_file(database),
        "read_only": True,
        "events": events,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-structural-label-planner-inventory.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "planner_contract",
                    "planned_unit_count",
                    "event_count",
                    "contained_event_count",
                    "cross_unit_event_count",
                    "position_counts",
                    "multi_label_unit_count",
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
