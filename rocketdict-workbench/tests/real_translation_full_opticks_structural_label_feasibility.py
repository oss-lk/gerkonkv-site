from __future__ import annotations

"""Research-only full-Opticks explicit structural-label MT feasibility.

This probe consumes the immutable full-corpus numeric-stress + staged-n-best
artifacts and investigates only remaining isolated numeric failures containing
explicit Gutenberg experiment/observation/question labels.  It does not pass
alphabetic source structure through to the target and it never inserts missing
numbers after translation.  Instead, the label and surrounding prose are sent
to the same real OPUS model as separate source-derived requests and then
reassembled in source order with source-owned whitespace only.

The result is mechanism evidence, not Product policy.  Mechanical strict-gate
success remains insufficient for promotion without target-language review and
planner regression evidence.
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
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-structural-label-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/2"
ESCALATION_SCHEMA = "rocketdict-full-opticks-nbest-escalation/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
LABEL_GENERATION_CELLS = (
    {"beam_size": 6, "num_hypotheses": 6},
    {"beam_size": 12, "num_hypotheses": 12},
)
PROSE_GENERATION = {"beam_size": 6, "num_hypotheses": 1}
BATCH_SIZE = 32

# Accept the canonical Gutenberg form (``_Exper._ 11.``) and the boundary-
# damaged form (``Qu._ 3.``) observed when Stage10 owns the leading underscore
# in the previous context sentence.  The optional leading underscore is an
# input-classification concession only; no missing byte is fabricated later.
_LABEL_RE = re.compile(
    r"(?<![A-Za-z0-9])_?(?P<kind>Exper|Obs|Qu)\._?\s+(?P<number>\d+)\.",
    flags=re.IGNORECASE,
)


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _translate_batches(
    translator: OpusTranslator,
    texts: list[str],
    *,
    beam_size: int,
    num_hypotheses: int,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=max_decoding_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("Structural-label translation batch cardinality mismatch")
    return output


def _source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence_number": int(row["planned_sequence"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row["source_text"]),
        "target_text": None,
    }


def _split_parts(text: str) -> list[dict[str, Any]]:
    matches = list(_LABEL_RE.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"Structural-label probe requires exactly one explicit label per scoped unit, got {len(matches)}"
        )
    match = matches[0]
    parts: list[dict[str, Any]] = []
    if match.start() > 0:
        parts.append(
            {
                "kind": "prose",
                "start": 0,
                "end": match.start(),
                "text": text[: match.start()],
            }
        )
    parts.append(
        {
            "kind": "label",
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0),
            "label_kind": str(match.group("kind")).lower(),
            "label_number": str(match.group("number")),
            "canonical_leading_underscore": match.group(0).startswith("_"),
        }
    )
    if match.end() < len(text):
        parts.append(
            {
                "kind": "prose",
                "start": match.end(),
                "end": len(text),
                "text": text[match.end() :],
            }
        )
    if "".join(str(part["text"]) for part in parts) != text:
        raise RuntimeError("Structural-label split is not byte-exact over source")
    return parts


def _core(fragment: str) -> tuple[str, str, str]:
    if not fragment.strip():
        return fragment, "", ""
    left = len(fragment) - len(fragment.lstrip())
    right = len(fragment) - len(fragment.rstrip())
    leading = fragment[:left]
    trailing = fragment[len(fragment) - right :] if right else ""
    end = len(fragment) - right if right else len(fragment)
    return leading, fragment[left:end], trailing


def _compose(
    parts: list[dict[str, Any]],
    *,
    prose_targets: dict[int, dict[str, Any]],
    label_target: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    output: list[str] = []
    evidence: list[dict[str, Any]] = []
    label_used = False
    for index, part in enumerate(parts):
        leading, core, trailing = _core(str(part["text"]))
        if not core:
            output.append(str(part["text"]))
            evidence.append(
                {
                    "kind": str(part["kind"]),
                    "source_text": str(part["text"]),
                    "target_text": str(part["text"]),
                    "whitespace_only": True,
                }
            )
            continue
        if part["kind"] == "label":
            if label_used:
                raise RuntimeError("Structural-label probe unexpectedly encountered multiple label cores")
            hypothesis = label_target
            label_used = True
        else:
            hypothesis = prose_targets[index]
        translated = str(hypothesis.get("text") or "").strip()
        if not translated:
            raise RuntimeError("OPUS returned an empty structural-label component")
        output.append(leading + translated + trailing)
        evidence.append(
            {
                "kind": str(part["kind"]),
                "source_text": str(part["text"]),
                "source_core": core,
                "target_core": translated,
                "model_rank": int(hypothesis.get("rank") or 0),
                "model_score": hypothesis.get("score"),
                "source_owned_whitespace": True,
                "non_whitespace_target_from_real_mt": True,
            }
        )
    if not label_used:
        raise RuntimeError("Structural-label composition did not consume a label hypothesis")
    return "".join(output), evidence


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    escalation_path = root / "full-opticks-nbest-escalation.json"
    if not baseline_path.is_file() or not escalation_path.is_file():
        raise RuntimeError("Full Opticks numeric-stress or n-best escalation evidence is missing")

    baseline_bytes = baseline_path.read_bytes()
    escalation_bytes = escalation_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    escalation = json.loads(escalation_bytes.decode("utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"Unexpected numeric-stress schema: {baseline.get('schema')!r}")
    if escalation.get("schema") != ESCALATION_SCHEMA:
        raise RuntimeError(f"Unexpected n-best escalation schema: {escalation.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256 or escalation.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks identity drift across structural-label inputs")
    if baseline.get("no_synthetic_target_repair") is not True:
        raise RuntimeError("Baseline does not prove no-synthetic-target-repair semantics")
    if escalation.get("no_post_translation_literal_injection") is not True:
        raise RuntimeError("Escalation evidence does not prove no-literal-injection semantics")

    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})
    if not length_parameters:
        raise RuntimeError("Full Opticks evidence lacks length-ratio gate parameters")

    failures = {
        int(row["planned_sequence"]): row
        for row in list(baseline.get("numeric_failures") or [])
    }
    residual_sequences = {int(value) for value in escalation.get("residual_sequences") or []}
    scoped: list[dict[str, Any]] = []
    for sequence in sorted(residual_sequences):
        row = failures.get(sequence)
        if row is None:
            raise RuntimeError(f"Escalation residual {sequence} is absent from numeric-stress failures")
        source = str(row["source_text"])
        matches = list(_LABEL_RE.finditer(source))
        if matches:
            if len(matches) != 1:
                raise RuntimeError(f"Residual {sequence} contains multiple explicit structural labels")
            scoped.append(row)
    if not scoped:
        raise RuntimeError("No full-Opticks staged-n-best residual contains an explicit structural label")

    plans: dict[int, list[dict[str, Any]]] = {}
    prose_jobs: list[str] = []
    prose_refs: list[tuple[int, int]] = []
    label_jobs: list[str] = []
    sequences: list[int] = []
    for row in scoped:
        sequence = int(row["planned_sequence"])
        sequences.append(sequence)
        parts = _split_parts(str(row["source_text"]))
        plans[sequence] = parts
        for index, part in enumerate(parts):
            leading, core, trailing = _core(str(part["text"]))
            part["leading_whitespace"] = leading
            part["source_core"] = core
            part["trailing_whitespace"] = trailing
            if not core:
                continue
            if part["kind"] == "label":
                label_jobs.append(core)
            else:
                prose_refs.append((sequence, index))
                prose_jobs.append(core)

    if len(label_jobs) != len(scoped):
        raise RuntimeError("Structural-label plan did not produce exactly one label request per scoped unit")

    max_planned_tokens = int(baseline.get("max_planned_unit_tokens") or 64)
    max_decoding_length = max(128, max_planned_tokens * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")

    prose_generated = _translate_batches(
        translator,
        prose_jobs,
        beam_size=int(PROSE_GENERATION["beam_size"]),
        num_hypotheses=int(PROSE_GENERATION["num_hypotheses"]),
        max_decoding_length=max_decoding_length,
    ) if prose_jobs else []
    prose_targets: dict[int, dict[int, dict[str, Any]]] = {sequence: {} for sequence in sequences}
    for (sequence, part_index), hypotheses in zip(prose_refs, prose_generated, strict=True):
        if not hypotheses:
            raise RuntimeError(f"OPUS returned no prose hypothesis for residual {sequence}")
        prose_targets[sequence][part_index] = dict(hypotheses[0])

    label_results: dict[int, list[dict[str, Any]]] = {sequence: [] for sequence in sequences}
    unresolved = list(sequences)
    selected: dict[int, dict[str, Any]] = {}
    label_source_by_sequence = {
        sequence: next(
            str(part.get("source_core") or "")
            for part in plans[sequence]
            if part["kind"] == "label"
        )
        for sequence in sequences
    }

    for cell in LABEL_GENERATION_CELLS:
        if not unresolved:
            break
        jobs = [label_source_by_sequence[sequence] for sequence in unresolved]
        generated = _translate_batches(
            translator,
            jobs,
            beam_size=int(cell["beam_size"]),
            num_hypotheses=int(cell["num_hypotheses"]),
            max_decoding_length=max_decoding_length,
        )
        rescued_now: list[int] = []
        for sequence, hypotheses in zip(unresolved, generated, strict=True):
            row = failures[sequence]
            source_row = _source_row(row)
            cell_candidates: list[dict[str, Any]] = []
            chosen: dict[str, Any] | None = None
            for model_index, hypothesis in enumerate(hypotheses):
                target, part_evidence = _compose(
                    plans[sequence],
                    prose_targets=prose_targets[sequence],
                    label_target=hypothesis,
                )
                verdict = _verdict(
                    source_row,
                    target,
                    punctuation_parameters=punctuation_parameters,
                    length_parameters=length_parameters,
                )
                candidate = {
                    "model_index": model_index,
                    "rank": int(hypothesis.get("rank") if hypothesis.get("rank") is not None else model_index),
                    "score": hypothesis.get("score"),
                    "label_target_text": str(hypothesis.get("text") or ""),
                    "composite_target_text": target,
                    "parts": part_evidence,
                    "verdict": verdict,
                }
                cell_candidates.append(candidate)
                if chosen is None and verdict.get("strictly_eligible") is True:
                    chosen = candidate
            label_results[sequence].append(
                {
                    "generation": dict(cell),
                    "candidate_count": len(cell_candidates),
                    "strictly_eligible_count": sum(
                        1 for candidate in cell_candidates if candidate["verdict"].get("strictly_eligible") is True
                    ),
                    "selected_rank": None if chosen is None else int(chosen["rank"]),
                    "candidates": cell_candidates,
                }
            )
            if chosen is not None:
                selected[sequence] = {"generation": dict(cell), **chosen}
                rescued_now.append(sequence)
        rescued_set = set(rescued_now)
        unresolved = [sequence for sequence in unresolved if sequence not in rescued_set]

    results: list[dict[str, Any]] = []
    for row in scoped:
        sequence = int(row["planned_sequence"])
        label = next(part for part in plans[sequence] if part["kind"] == "label")
        results.append(
            {
                "planned_sequence": sequence,
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "rank0_target_text": str(row["rank0_target_text"]),
                "label": {
                    "source_text": str(label["text"]),
                    "source_core": str(label.get("source_core") or ""),
                    "kind": str(label["label_kind"]),
                    "number": str(label["label_number"]),
                    "canonical_leading_underscore": bool(label["canonical_leading_underscore"]),
                },
                "cells": label_results[sequence],
                "selected": selected.get(sequence),
            }
        )

    selected_rank_distribution = Counter(
        int(value["rank"]) for value in selected.values()
    )
    selected_generation_distribution = Counter(
        f"beam-{value['generation']['beam_size']}" for value in selected.values()
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-corpus feasibility of source-side explicit structural-label separation with all non-whitespace target content produced by real OPUS",
        "promotion_allowed": False,
        "no_placeholder_roundtrip": True,
        "no_source_alphabetic_passthrough": True,
        "no_post_translation_literal_injection": True,
        "source_owned_whitespace_only": True,
        "all_non_whitespace_target_from_real_mt": True,
        "source_sha256": OPTICKS_SHA256,
        "baseline_evidence_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "escalation_evidence_sha256": hashlib.sha256(escalation_bytes).hexdigest(),
        "baseline_internal_evidence_sha256": str(baseline.get("evidence_sha256") or ""),
        "escalation_internal_evidence_sha256": str(escalation.get("evidence_sha256") or ""),
        "model": dict(baseline.get("model") or {}),
        "recognized_label_kinds": ["exper", "obs", "qu"],
        "prose_generation": dict(PROSE_GENERATION),
        "label_generation_cells": [dict(cell) for cell in LABEL_GENERATION_CELLS],
        "max_decoding_length": max_decoding_length,
        "input_residual_count": len(residual_sequences),
        "scoped_count": len(scoped),
        "scoped_sequences": sequences,
        "rescued_count": len(selected),
        "rescued_sequences": sorted(selected),
        "residual_after_label_split_count": len(unresolved),
        "residual_after_label_split_sequences": sorted(unresolved),
        "selected_rank_distribution": {
            str(key): value for key, value in sorted(selected_rank_distribution.items())
        },
        "selected_generation_distribution": dict(sorted(selected_generation_distribution.items())),
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-structural-label-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "scoped_count": len(scoped),
                "scoped_sequences": sequences,
                "rescued_count": len(selected),
                "rescued_sequences": sorted(selected),
                "residual_after_label_split_count": len(unresolved),
                "residual_after_label_split_sequences": sorted(unresolved),
                "selected_rank_distribution": payload["selected_rank_distribution"],
                "selected_generation_distribution": payload["selected_generation_distribution"],
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
