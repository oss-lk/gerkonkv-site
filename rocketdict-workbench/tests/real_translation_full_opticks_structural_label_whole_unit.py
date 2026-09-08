from __future__ import annotations

"""Research-only whole-unit source canonicalization for Opticks labels.

The immutable source span remains the evaluation source. Only the request sent
to real OPUS expands Exper./Obs./Qu. to Experiment/Observation/Query. No target
rewrite, placeholder, source passthrough, or n-best selection is used: this
probe asks whether source-side abbreviation expansion alone makes Product
rank-0 semantics sufficient.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.runtime import OpusTranslator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_full_opticks_structural_label_canonicalization import (  # noqa: E402
    EXACT,
    EXPECTED_RU,
    _semantic_ok,
)
from real_translation_full_opticks_structural_label_feasibility import (  # noqa: E402
    BASE_SCHEMA,
    ESCALATION_SCHEMA,
    OPTICKS_SHA256,
    _LABEL_RE,
    _canonical_sha,
    _source_row,
    _translate_batches,
)
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-structural-label-whole-unit/1"
GENERATION = {"beam_size": 6, "num_hypotheses": 1}


def _canonical_request(source: str, match: Any) -> tuple[str, dict[str, Any]]:
    kind = str(match.group("kind")).lower()
    number = str(match.group("number"))
    canonical = f"{EXACT[kind]} {number}."
    request = source[: match.start()] + canonical + source[match.end() :]
    return request, {
        "kind": kind,
        "number": number,
        "original_label_text": match.group(0),
        "canonical_label_text": canonical,
        "source_start": int(match.start()),
        "source_end": int(match.end()),
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress"
        )
    ).resolve()
    bp = root / "full-opticks-numeric-stress.json"
    ep = root / "full-opticks-nbest-escalation.json"
    if not bp.is_file() or not ep.is_file():
        raise RuntimeError("full-Opticks baseline/escalation evidence is missing")
    bbytes, ebytes = bp.read_bytes(), ep.read_bytes()
    baseline = json.loads(bbytes.decode("utf-8"))
    escalation = json.loads(ebytes.decode("utf-8"))
    if (
        baseline.get("schema") != BASE_SCHEMA
        or escalation.get("schema") != ESCALATION_SCHEMA
    ):
        raise RuntimeError("unexpected full-Opticks input schema")
    if (
        baseline.get("source_sha256") != OPTICKS_SHA256
        or escalation.get("source_sha256") != OPTICKS_SHA256
    ):
        raise RuntimeError("pinned Opticks identity drift")
    if (
        baseline.get("no_synthetic_target_repair") is not True
        or escalation.get("no_post_translation_literal_injection") is not True
    ):
        raise RuntimeError("input evidence does not prove no-repair semantics")

    quality = dict(baseline.get("quality_gate_parameters") or {})
    punct = dict(quality.get("punctuation") or {})
    length = dict(quality.get("length_ratio") or {})
    failures = {
        int(row["planned_sequence"]): row
        for row in baseline.get("numeric_failures") or []
    }
    residuals = [int(value) for value in escalation.get("residual_sequences") or []]

    scoped: list[dict[str, Any]] = []
    requests: list[str] = []
    canonicalization: list[dict[str, Any]] = []
    for sequence in residuals:
        row = failures[sequence]
        matches = list(_LABEL_RE.finditer(str(row["source_text"])))
        if not matches:
            continue
        if len(matches) != 1:
            raise RuntimeError(
                f"residual {sequence} has multiple structural labels"
            )
        request, evidence = _canonical_request(str(row["source_text"]), matches[0])
        scoped.append(row)
        requests.append(request)
        canonicalization.append(evidence)
    if not scoped:
        raise RuntimeError("no structural-label residuals found")

    max_tokens = int(baseline.get("max_planned_unit_tokens") or 64)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = _translate_batches(
        translator,
        requests,
        beam_size=GENERATION["beam_size"],
        num_hypotheses=GENERATION["num_hypotheses"],
        max_decoding_length=max(128, max_tokens * 8),
    )

    results = []
    successes: list[int] = []
    for row, request, canon, hypotheses in zip(
        scoped, requests, canonicalization, generated, strict=True
    ):
        if not hypotheses:
            raise RuntimeError(
                f"OPUS returned no whole-unit hypothesis for {row['planned_sequence']}"
            )
        hypothesis = hypotheses[0]
        target = str(hypothesis.get("text") or "").strip()
        if not target:
            raise RuntimeError(
                f"OPUS returned empty whole-unit target for {row['planned_sequence']}"
            )
        verdict = _verdict(
            _source_row(row),
            target,
            punctuation_parameters=punct,
            length_parameters=length,
        )
        semantic_ok = _semantic_ok(str(canon["kind"]), target)
        passed = bool(verdict.get("strictly_eligible") is True and semantic_ok)
        if passed:
            successes.append(int(row["planned_sequence"]))
        results.append(
            {
                "planned_sequence": int(row["planned_sequence"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "canonical_request_text": request,
                "canonicalization": canon,
                "rank0_target_text": target,
                "rank0_score": hypothesis.get("score"),
                "semantic_target_check": {
                    "expected_russian_term": EXPECTED_RU[str(canon["kind"])],
                    "passed": semantic_ok,
                },
                "verdict": verdict,
                "strict_and_semantic": passed,
            }
        )

    asset = translator.asset
    payload = {
        "schema": SCHEMA,
        "purpose": "test exact source-side abbreviation expansion with whole-unit Product rank0 real OPUS",
        "promotion_allowed": False,
        "source_sha256": OPTICKS_SHA256,
        "baseline_json_sha256": hashlib.sha256(bbytes).hexdigest(),
        "baseline_internal_evidence_sha256": str(
            baseline.get("evidence_sha256") or ""
        ),
        "escalation_json_sha256": hashlib.sha256(ebytes).hexdigest(),
        "escalation_internal_evidence_sha256": str(
            escalation.get("evidence_sha256") or ""
        ),
        "input_residual_count": len(residuals),
        "scoped_count": len(scoped),
        "scoped_sequences": [int(row["planned_sequence"]) for row in scoped],
        "strict_semantic_success_count": len(successes),
        "strict_semantic_success_sequences": successes,
        "generation": GENERATION,
        "exact_expansions": EXACT,
        "expected_russian_terms": EXPECTED_RU,
        "source_canonicalization_recorded": True,
        "no_nbest_selection": True,
        "no_post_translation_literal_injection": True,
        "no_placeholder_roundtrip": True,
        "no_source_passthrough": True,
        "all_target_from_real_mt": True,
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
    output = root / "full-opticks-structural-label-whole-unit.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "scoped_count": len(scoped),
                "strict_semantic_success_count": len(successes),
                "strict_semantic_success_sequences": successes,
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
