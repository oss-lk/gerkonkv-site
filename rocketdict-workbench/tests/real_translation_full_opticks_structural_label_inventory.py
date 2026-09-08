from __future__ import annotations

"""Research-only full-Opticks structural-label candidate inventory.

Every numbered Exper./Obs./Qu. occurrence in the immutable source is expanded
only on the source side (Experiment/Observation/Query) and translated with the
same pinned real OPUS model. The probe asks whether raw beam-6 n-best contains
at least one candidate that preserves the source number and expresses the
expected Russian structural-label meaning. No target rewriting is performed.
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
    EXACT,
    EXPECTED_RU,
    _semantic_ok,
)
from real_translation_full_opticks_structural_label_feasibility import (  # noqa: E402
    OPTICKS_SHA256,
    _LABEL_RE,
    _canonical_sha,
    _translate_batches,
)

SCHEMA = "rocketdict-full-opticks-structural-label-inventory/1"
GENERATION = {"beam_size": 6, "num_hypotheses": 6}


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
    sources = sorted((root / "project" / "uploads").glob("*.txt"))
    if len(sources) != 1:
        raise RuntimeError(
            f"expected one immutable Opticks TXT source, found {len(sources)}"
        )
    source_path = sources[0]
    if _sha_file(source_path) != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source hash drift")
    text = source_path.read_text(encoding="utf-8-sig")

    events: list[dict[str, Any]] = []
    requests: list[str] = []
    for index, match in enumerate(_LABEL_RE.finditer(text)):
        kind = str(match.group("kind")).lower()
        number = str(match.group("number"))
        canonical = f"{EXACT[kind]} {number}."
        events.append(
            {
                "event_index": index,
                "source_start": int(match.start()),
                "source_end": int(match.end()),
                "source_text": match.group(0),
                "kind": kind,
                "number": number,
                "canonical_source_text": canonical,
            }
        )
        requests.append(canonical)
    if not events:
        raise RuntimeError("Opticks source produced no supported structural labels")

    unique_requests = list(dict.fromkeys(requests))
    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = _translate_batches(
        translator,
        unique_requests,
        beam_size=GENERATION["beam_size"],
        num_hypotheses=GENERATION["num_hypotheses"],
        max_decoding_length=128,
    )
    by_request = {
        request: hypotheses
        for request, hypotheses in zip(unique_requests, generated, strict=True)
    }

    success_events: list[int] = []
    failure_events: list[int] = []
    kind_counts: Counter[str] = Counter()
    kind_successes: Counter[str] = Counter()
    rank_distribution: Counter[int] = Counter()
    results = []
    for event in events:
        kind = str(event["kind"])
        kind_counts[kind] += 1
        candidates = []
        selected = None
        for model_index, hypothesis in enumerate(
            by_request[str(event["canonical_source_text"])]
        ):
            target = str(hypothesis.get("text") or "").strip()
            numeric = compare_numeric_integrity(str(event["source_text"]), target)
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
            if selected is None and candidate["acceptable"]:
                selected = candidate
        event_index = int(event["event_index"])
        if selected is None:
            failure_events.append(event_index)
        else:
            success_events.append(event_index)
            kind_successes[kind] += 1
            rank_distribution[int(selected["rank"])] += 1
        results.append({**event, "selected": selected, "candidates": candidates})

    asset = translator.asset
    payload = {
        "schema": SCHEMA,
        "purpose": "full-corpus availability check for source-canonicalized raw OPUS structural-label candidates",
        "promotion_allowed": False,
        "source_sha256": OPTICKS_SHA256,
        "source_character_count": len(text),
        "supported_kinds": sorted(EXACT),
        "exact_expansions": EXACT,
        "expected_russian_terms": EXPECTED_RU,
        "generation": GENERATION,
        "event_count": len(events),
        "unique_request_count": len(unique_requests),
        "kind_counts": dict(sorted(kind_counts.items())),
        "acceptable_event_count": len(success_events),
        "acceptable_event_indices": success_events,
        "unresolved_event_count": len(failure_events),
        "unresolved_event_indices": failure_events,
        "kind_acceptable_counts": dict(sorted(kind_successes.items())),
        "selected_rank_distribution": {
            str(key): value for key, value in sorted(rank_distribution.items())
        },
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
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-structural-label-inventory.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "event_count",
                    "kind_counts",
                    "acceptable_event_count",
                    "unresolved_event_count",
                    "unresolved_event_indices",
                    "kind_acceptable_counts",
                    "selected_rank_distribution",
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
