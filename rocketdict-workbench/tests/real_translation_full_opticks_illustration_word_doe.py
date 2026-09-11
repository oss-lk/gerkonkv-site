from __future__ import annotations

"""Research DOE for the ambiguous Gutenberg structural word ``_Illustration._``.

The direct immutable model input corrupts markup and the stripped input
``Illustration.`` is mistranslated by the pinned EN->RU OPUS model as
``Пример.``.  This experiment varies only a small, source-derived canonical
model input using the locally adjacent source concept ``FIG.``/figure.  Targets
are untouched raw OPUS hypotheses.  A candidate is interesting only when it is
hard/strict-clean against the immutable source word and is exactly the Russian
structural label ``Иллюстрация`` or ``Рисунок`` (optional terminal period), with
no markup artifacts.

This is search evidence, not Product selection or target repair.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-illustration-word-opus-doe/1"
SOURCE_TEXT = "_Illustration._ "
MODEL_INPUTS = (
    "Illustration.",
    "Illustration figure.",
    "Figure illustration.",
    "Illustration: figure.",
    "Illustration (figure).",
    "Figure.",
    "Illustration image.",
    "Image illustration.",
)
GENERATION_CELLS = ((6, 6), (12, 12))
ACCEPTED_TERMS = {"иллюстрация", "рисунок"}


def _target_shape(target: str) -> dict[str, Any]:
    stripped = target.strip()
    no_markup_artifacts = not any(char in stripped for char in "_*[]{}()")
    canonical = stripped.rstrip(".").strip().casefold()
    exact_structural_term = canonical in ACCEPTED_TERMS
    return {
        "contract": "rocketdict-illustration-word-target-form/2",
        "target_text": target,
        "canonical_target": canonical,
        "accepted_terms": sorted(ACCEPTED_TERMS),
        "no_markup_artifacts": no_markup_artifacts,
        "exact_structural_term": exact_structural_term,
        "passed": no_markup_artifacts and exact_structural_term,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_ILLUSTRATION_WORD_DOE_ROOT", "work/illustration-word-doe")
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    translator = OpusTranslator(device="cpu", compute_type="float32")

    rows: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for model_input_index, model_input in enumerate(MODEL_INPUTS):
        for beam_size, num_hypotheses in GENERATION_CELLS:
            generated = translator.translate(
                [model_input],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=64,
            )
            if len(generated) != 1 or not generated[0]:
                raise RuntimeError("illustration-word DOE backend cardinality drift")
            for rank, hypothesis in enumerate(generated[0]):
                target = str(hypothesis.get("text") or "")
                verdict = evaluate_rescue_pair(SOURCE_TEXT, target)
                shape = _target_shape(target)
                acceptable = (
                    verdict.get("strictly_eligible") is True
                    and shape.get("passed") is True
                )
                row = {
                    "model_input_index": model_input_index,
                    "model_input": model_input,
                    "source_model_input_normalized": model_input != SOURCE_TEXT.strip(),
                    "beam_size": beam_size,
                    "num_hypotheses": num_hypotheses,
                    "rank": rank,
                    "score": hypothesis.get("score"),
                    "target_text": target,
                    "target_shape": shape,
                    "verdict": verdict,
                    "acceptable": acceptable,
                    "raw_model_hypothesis": True,
                    "target_rewriting": False,
                }
                rows.append(row)
                if acceptable:
                    accepted.append(row)

    selected = None
    if accepted:
        selected = min(
            accepted,
            key=lambda row: (
                int(row["model_input_index"]),
                int(row["beam_size"]),
                int(row["rank"]),
            ),
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research canonical-model-input search for exact Gutenberg _Illustration._ structural word",
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "immutable_source_text": SOURCE_TEXT,
        "model_inputs": list(MODEL_INPUTS),
        "generation_cells": [list(cell) for cell in GENERATION_CELLS],
        "candidate_count": len(rows),
        "acceptable_candidate_count": len(accepted),
        "acceptable_candidates": [
            {
                "model_input_index": row["model_input_index"],
                "model_input": row["model_input"],
                "beam_size": row["beam_size"],
                "num_hypotheses": row["num_hypotheses"],
                "rank": row["rank"],
                "score": row["score"],
                "target_text": row["target_text"],
            }
            for row in accepted
        ],
        "selected_candidate": (
            {
                "model_input_index": selected["model_input_index"],
                "model_input": selected["model_input"],
                "beam_size": selected["beam_size"],
                "num_hypotheses": selected["num_hypotheses"],
                "rank": selected["rank"],
                "score": selected["score"],
                "target_text": selected["target_text"],
            }
            if selected is not None
            else None
        ),
        "candidates": rows,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    out = root / "full-opticks-illustration-word-opus-doe.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if selected is None:
        raise RuntimeError("illustration-word DOE found no strict semantic raw OPUS candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
