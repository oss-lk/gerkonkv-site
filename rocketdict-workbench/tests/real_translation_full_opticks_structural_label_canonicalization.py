from __future__ import annotations

"""Research-only source-canonicalized structural-label feasibility on full Opticks.

Consumes immutable full-corpus numeric/n-best evidence. Only residual units
with Gutenberg Exper./Obs./Qu. labels are scoped. Surrounding prose goes to
real OPUS unchanged; label abbreviations are expanded on the source side before
real OPUS. No target-side insertion, placeholders, source alphabetic passthrough
or post-MT rewrite is allowed. ``Question`` is measured only as an explicit
research synonym for historical ``Query`` and is never silently promoted.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from rocketdict.runtime import OpusTranslator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_full_opticks_structural_label_feasibility import (  # noqa: E402
    BASE_SCHEMA,
    ESCALATION_SCHEMA,
    OPTICKS_SHA256,
    _LABEL_RE,
    _canonical_sha,
    _compose,
    _core,
    _source_row,
    _split_parts,
    _translate_batches,
)
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-structural-label-canonicalization/1"
GENERATION = {"beam_size": 6, "num_hypotheses": 6}
PROSE_GENERATION = {"beam_size": 6, "num_hypotheses": 1}
EXACT = {"exper": "Experiment", "obs": "Observation", "qu": "Query"}
EXPECTED_RU = {"exper": "эксперимент", "obs": "наблюдение", "qu": "вопрос"}


def _variants(kind: str, number: str) -> list[dict[str, str]]:
    rows = [
        {
            "variant": "exact_abbreviation_expansion",
            "semantic_distance": "abbreviation_expansion_only",
            "source_text": f"{EXACT[kind]} {number}.",
        }
    ]
    if kind == "qu":
        rows.append(
            {
                "variant": "semantic_question",
                "semantic_distance": "research_only_synonym_normalization",
                "source_text": f"Question {number}.",
            }
        )
    return rows


def _semantic_ok(kind: str, target: str) -> bool:
    return bool(re.search(rf"(?<![а-яё]){EXPECTED_RU[kind]}", target.lower()))


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
    if not length:
        raise RuntimeError("baseline lacks length-ratio parameters")

    failures = {
        int(row["planned_sequence"]): row
        for row in baseline.get("numeric_failures") or []
    }
    residuals = [int(value) for value in escalation.get("residual_sequences") or []]
    scoped = []
    for sequence in residuals:
        row = failures[sequence]
        matches = list(_LABEL_RE.finditer(str(row["source_text"])))
        if matches:
            if len(matches) != 1:
                raise RuntimeError(
                    f"residual {sequence} has multiple structural labels"
                )
            scoped.append(row)
    if not scoped:
        raise RuntimeError("no structural-label residuals found")

    plans: dict[int, list[dict[str, Any]]] = {}
    prose_jobs: list[str] = []
    prose_refs: list[tuple[int, int]] = []
    label_jobs: list[str] = []
    label_refs: list[tuple[int, str, str, str]] = []
    for row in scoped:
        sequence = int(row["planned_sequence"])
        parts = _split_parts(str(row["source_text"]))
        plans[sequence] = parts
        for index, part in enumerate(parts):
            leading, core, trailing = _core(str(part["text"]))
            part.update(
                source_core=core,
                leading_whitespace=leading,
                trailing_whitespace=trailing,
            )
            if not core:
                continue
            if part["kind"] == "label":
                kind = str(part["label_kind"]).lower()
                number = str(part["label_number"])
                for row_variant in _variants(kind, number):
                    label_jobs.append(row_variant["source_text"])
                    label_refs.append(
                        (
                            sequence,
                            row_variant["variant"],
                            row_variant["semantic_distance"],
                            row_variant["source_text"],
                        )
                    )
            else:
                prose_jobs.append(core)
                prose_refs.append((sequence, index))

    max_tokens = int(baseline.get("max_planned_unit_tokens") or 64)
    max_decode = max(128, max_tokens * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    prose_out = (
        _translate_batches(
            translator,
            prose_jobs,
            beam_size=PROSE_GENERATION["beam_size"],
            num_hypotheses=1,
            max_decoding_length=max_decode,
        )
        if prose_jobs
        else []
    )
    prose_targets = {int(row["planned_sequence"]): {} for row in scoped}
    for (sequence, index), hypotheses in zip(prose_refs, prose_out, strict=True):
        if not hypotheses:
            raise RuntimeError(f"no prose hypothesis for {sequence}")
        prose_targets[sequence][index] = dict(hypotheses[0])

    label_out = _translate_batches(
        translator,
        label_jobs,
        beam_size=GENERATION["beam_size"],
        num_hypotheses=GENERATION["num_hypotheses"],
        max_decoding_length=max_decode,
    )
    label_map = {
        (sequence, variant): {
            "semantic_distance": distance,
            "canonical_source_text": source,
            "hypotheses": hypotheses,
        }
        for (sequence, variant, distance, source), hypotheses in zip(
            label_refs, label_out, strict=True
        )
    }

    results = []
    exact_success: list[int] = []
    any_success: list[int] = []
    variant_dist: Counter[str] = Counter()
    rank_dist: Counter[int] = Counter()
    for row in scoped:
        sequence = int(row["planned_sequence"])
        parts = plans[sequence]
        label = next(part for part in parts if part["kind"] == "label")
        kind = str(label["label_kind"]).lower()
        number = str(label["label_number"])
        source_row = _source_row(row)
        variant_rows = []
        selected = None
        exact_selected = None
        for variant in _variants(kind, number):
            meta = label_map[(sequence, variant["variant"])]
            candidates = []
            variant_selected = None
            for model_index, hypothesis in enumerate(meta["hypotheses"]):
                target, part_evidence = _compose(
                    parts,
                    prose_targets=prose_targets[sequence],
                    label_target=hypothesis,
                )
                verdict = _verdict(
                    source_row,
                    target,
                    punctuation_parameters=punct,
                    length_parameters=length,
                )
                label_target = str(hypothesis.get("text") or "")
                semantic_ok = _semantic_ok(kind, label_target)
                candidate = {
                    "model_index": model_index,
                    "rank": int(
                        hypothesis.get("rank")
                        if hypothesis.get("rank") is not None
                        else model_index
                    ),
                    "score": hypothesis.get("score"),
                    "label_target_text": label_target,
                    "composite_target_text": target,
                    "parts": part_evidence,
                    "verdict": verdict,
                    "semantic_target_check": {
                        "expected_russian_term": EXPECTED_RU[kind],
                        "passed": semantic_ok,
                    },
                    "strict_and_semantic": bool(
                        verdict.get("strictly_eligible") is True and semantic_ok
                    ),
                }
                candidates.append(candidate)
                if variant_selected is None and candidate["strict_and_semantic"]:
                    variant_selected = candidate
            variant_row = {
                **variant,
                "original_label_source_text": str(label["text"]),
                "original_label_source_core": str(label.get("source_core") or ""),
                "strict_and_semantic_count": sum(
                    1 for candidate in candidates if candidate["strict_and_semantic"]
                ),
                "selected": variant_selected,
                "candidates": candidates,
            }
            variant_rows.append(variant_row)
            if (
                variant_selected is not None
                and variant["variant"] == "exact_abbreviation_expansion"
            ):
                exact_selected = {
                    "variant": variant["variant"],
                    **variant_selected,
                }
            if selected is None and variant_selected is not None:
                selected = {"variant": variant["variant"], **variant_selected}
        if exact_selected is not None:
            exact_success.append(sequence)
        if selected is not None:
            any_success.append(sequence)
            variant_dist[selected["variant"]] += 1
            rank_dist[int(selected["rank"])] += 1
        results.append(
            {
                "planned_sequence": sequence,
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "rank0_target_text": str(row["rank0_target_text"]),
                "label_kind": kind,
                "label_number": number,
                "variants": variant_rows,
                "exact_expansion_selected": exact_selected,
                "selected": selected,
            }
        )

    asset = translator.asset
    payload = {
        "schema": SCHEMA,
        "purpose": "source-side structural-label canonicalization with real OPUS and unchanged strict verdict",
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
        "exact_expansion_strict_semantic_success_count": len(exact_success),
        "exact_expansion_strict_semantic_success_sequences": exact_success,
        "any_variant_strict_semantic_success_count": len(any_success),
        "any_variant_strict_semantic_success_sequences": any_success,
        "selected_variant_distribution": dict(sorted(variant_dist.items())),
        "selected_rank_distribution": {
            str(key): value for key, value in sorted(rank_dist.items())
        },
        "generation": GENERATION,
        "prose_generation": PROSE_GENERATION,
        "exact_expansions": EXACT,
        "semantic_query_variant": "Question",
        "expected_russian_terms": EXPECTED_RU,
        "source_canonicalization_recorded": True,
        "no_post_translation_literal_injection": True,
        "no_placeholder_roundtrip": True,
        "no_source_alphabetic_passthrough": True,
        "all_non_whitespace_target_from_real_mt": True,
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
    output = root / "full-opticks-structural-label-canonicalization.json"
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
                    "input_residual_count",
                    "scoped_count",
                    "exact_expansion_strict_semantic_success_count",
                    "exact_expansion_strict_semantic_success_sequences",
                    "any_variant_strict_semantic_success_count",
                    "selected_variant_distribution",
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
