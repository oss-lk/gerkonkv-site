from __future__ import annotations

"""Research-only staged n-best escalation for unresolved structural-label inventory.

Consumes the immutable beam-6 full-Opticks structural-label inventory and asks
whether any still-unresolved *canonical source request* has a semantically and
numerically acceptable raw OPUS hypothesis at beam12/16.  The probe never
rewrites target text, never injects a source number after MT, and deduplicates
identical unresolved canonical requests before generation.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.numeric_integrity import compare_numeric_integrity
from rocketdict.runtime import OpusTranslator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_full_opticks_structural_label_canonicalization import (  # noqa: E402
    EXPECTED_RU,
    _semantic_ok,
)
from real_translation_full_opticks_structural_label_feasibility import (  # noqa: E402
    OPTICKS_SHA256,
    _canonical_sha,
    _translate_batches,
)
from real_translation_full_opticks_structural_label_inventory import (  # noqa: E402
    SCHEMA as INVENTORY_SCHEMA,
)

SCHEMA = "rocketdict-full-opticks-structural-label-inventory-escalation/1"
GENERATION_CELLS = (
    {"beam_size": 12, "num_hypotheses": 12},
    {"beam_size": 16, "num_hypotheses": 16},
)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress"
        )
    ).resolve()
    inventory_path = root / "full-opticks-structural-label-inventory.json"
    if not inventory_path.is_file():
        raise RuntimeError("structural-label inventory evidence is missing")
    inventory_bytes = inventory_path.read_bytes()
    inventory = json.loads(inventory_bytes.decode("utf-8"))
    if inventory.get("schema") != INVENTORY_SCHEMA:
        raise RuntimeError(f"unexpected inventory schema: {inventory.get('schema')!r}")
    if inventory.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("inventory Opticks source identity drift")
    if inventory.get("no_post_translation_literal_injection") is not True:
        raise RuntimeError("inventory does not prove no target literal injection")
    if inventory.get("all_target_candidates_from_real_mt") is not True:
        raise RuntimeError("inventory does not prove real-MT candidate lineage")

    source_candidates = sorted((root / "project" / "uploads").glob("*.txt"))
    if len(source_candidates) != 1:
        raise RuntimeError("expected one immutable Opticks source upload")
    if _sha_file(source_candidates[0]) != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source hash drift")

    unresolved_indices = [int(v) for v in inventory.get("unresolved_event_indices") or []]
    by_index = {
        int(row["event_index"]): dict(row)
        for row in list(inventory.get("results") or [])
    }
    unresolved = [by_index[index] for index in unresolved_indices]
    if len(unresolved) != len(unresolved_indices):
        raise RuntimeError("inventory unresolved-event lookup mismatch")

    unique_requests = list(
        dict.fromkeys(str(row["canonical_source_text"]) for row in unresolved)
    )
    translator = OpusTranslator(device="cpu", compute_type="float32")
    request_results: dict[str, dict[str, Any]] = {
        request: {"request": request, "cells": [], "selected": None}
        for request in unique_requests
    }
    still_unresolved = list(unique_requests)

    for cell in GENERATION_CELLS:
        if not still_unresolved:
            break
        generated = _translate_batches(
            translator,
            still_unresolved,
            beam_size=int(cell["beam_size"]),
            num_hypotheses=int(cell["num_hypotheses"]),
            max_decoding_length=128,
        )
        rescued: list[str] = []
        for request, hypotheses in zip(still_unresolved, generated, strict=True):
            rows = [row for row in unresolved if str(row["canonical_source_text"]) == request]
            if not rows:
                raise RuntimeError("unresolved request lost its source events")
            kinds = {str(row["kind"]) for row in rows}
            source_labels = {str(row["source_text"]) for row in rows}
            if len(kinds) != 1 or len(source_labels) != 1:
                raise RuntimeError("deduplicated structural-label request has incompatible events")
            kind = next(iter(kinds))
            source_label = next(iter(source_labels))
            candidates: list[dict[str, Any]] = []
            chosen: dict[str, Any] | None = None
            for model_index, hypothesis in enumerate(hypotheses):
                target = str(hypothesis.get("text") or "").strip()
                numeric = compare_numeric_integrity(source_label, target)
                semantic_ok = _semantic_ok(kind, target)
                candidate = {
                    "model_index": model_index,
                    "rank": int(
                        hypothesis.get("rank")
                        if hypothesis.get("rank") is not None
                        else model_index
                    ),
                    "score": hypothesis.get("score"),
                    "target_text": target,
                    "numeric_integrity": numeric,
                    "semantic_target_check": {
                        "expected_russian_term": EXPECTED_RU[kind],
                        "passed": semantic_ok,
                    },
                    "acceptable": bool(numeric["passed"] is True and semantic_ok),
                }
                candidates.append(candidate)
                if chosen is None and candidate["acceptable"]:
                    chosen = candidate
            request_results[request]["cells"].append(
                {
                    "generation": dict(cell),
                    "candidate_count": len(candidates),
                    "acceptable_count": sum(1 for row in candidates if row["acceptable"]),
                    "candidates": candidates,
                }
            )
            if chosen is not None:
                request_results[request]["selected"] = {
                    "generation": dict(cell),
                    **chosen,
                }
                rescued.append(request)
        rescued_set = set(rescued)
        still_unresolved = [r for r in still_unresolved if r not in rescued_set]

    event_results: list[dict[str, Any]] = []
    rescued_events: list[int] = []
    residual_events: list[int] = []
    selected_rank_distribution: Counter[int] = Counter()
    selected_generation_distribution: Counter[str] = Counter()
    for row in unresolved:
        request = str(row["canonical_source_text"])
        selected = request_results[request]["selected"]
        event_index = int(row["event_index"])
        if selected is None:
            residual_events.append(event_index)
        else:
            rescued_events.append(event_index)
            selected_rank_distribution[int(selected["rank"])] += 1
            selected_generation_distribution[
                f"beam-{int(selected['generation']['beam_size'])}"
            ] += 1
        event_results.append(
            {
                "event_index": event_index,
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "kind": str(row["kind"]),
                "number": str(row["number"]),
                "canonical_source_text": request,
                "selected": selected,
            }
        )

    asset = translator.asset
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "staged raw-OPUS search for semantic+numeric candidates missing from beam6 structural-label inventory",
        "promotion_allowed": False,
        "source_sha256": OPTICKS_SHA256,
        "inventory_json_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "inventory_internal_evidence_sha256": str(inventory.get("evidence_sha256") or ""),
        "input_unresolved_event_count": len(unresolved),
        "input_unresolved_event_indices": unresolved_indices,
        "unique_unresolved_request_count": len(unique_requests),
        "unique_unresolved_requests": unique_requests,
        "generation_cells": [dict(cell) for cell in GENERATION_CELLS],
        "rescued_event_count": len(rescued_events),
        "rescued_event_indices": rescued_events,
        "residual_event_count": len(residual_events),
        "residual_event_indices": residual_events,
        "residual_unique_requests": still_unresolved,
        "selected_rank_distribution": {
            str(k): v for k, v in sorted(selected_rank_distribution.items())
        },
        "selected_generation_distribution": dict(
            sorted(selected_generation_distribution.items())
        ),
        "no_post_translation_literal_injection": True,
        "no_placeholder_roundtrip": True,
        "no_source_passthrough": True,
        "all_target_candidates_from_real_mt": True,
        "model": {
            "revision": asset.revision,
            "source_archive_sha256": asset.source_archive_sha256,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "compute_type": "float32",
            "device": "cpu",
        },
        "request_results": [request_results[r] for r in unique_requests],
        "event_results": event_results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-structural-label-inventory-escalation.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "input_unresolved_event_count",
                    "unique_unresolved_request_count",
                    "rescued_event_count",
                    "residual_event_count",
                    "residual_event_indices",
                    "residual_unique_requests",
                    "selected_rank_distribution",
                    "selected_generation_distribution",
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
