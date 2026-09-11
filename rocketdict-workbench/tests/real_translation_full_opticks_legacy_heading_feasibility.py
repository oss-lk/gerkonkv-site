from __future__ import annotations

"""Research-only raw-OPUS feasibility for legacy Opticks block headings.

Full-Opticks hard-gate inspection shows that spaCy sentence boundaries can split
Gutenberg headings such as ``DEFIN. II.``, ``AX. IV.`` and
``_PROP._ VII. THEOR. VI.`` into tiny ordinary Stage12 requests.  The baseline
model then sometimes hallucinates prose (for example explanatory-note text) or
collapses a heading/title into punctuation.

This probe does not alter Product segmentation.  It detects the complete block
heading in the immutable pinned source, creates a separate canonical *model
input* by expanding only documented English abbreviations, and asks the pinned
real OPUS model for raw n-best hypotheses.  A hypothesis is mechanically
acceptable only when it exactly matches one of the narrow expected Russian
heading forms and preserves every Roman identifier in order.  Nothing is
inserted or repaired on the target side.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.runtime import OpusTranslator

SCHEMA = "rocketdict-full-opticks-legacy-heading-feasibility/1"
CONTRACT = "rocketdict-stage12-legacy-block-heading-opus-research/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
GENERATION_CELLS = ((6, 6), (12, 12))
EXPECTED_HEADING_COUNT = 54

_ROMAN = r"[IVXLCDM]+"
_HEADING_RE = re.compile(
    rf"(?:"
    rf"(?P<definition>DEFIN\.\s+(?P<definition_id>{_ROMAN})\.)"
    rf"|(?P<axiom>AX\.\s+(?P<axiom_id>{_ROMAN})\.)"
    rf"|(?P<prop_problem>_PROP\._\s+(?P<prop_problem_id>{_ROMAN})\.\s+PROB\.\s+(?P<problem_id>{_ROMAN})\.)"
    rf"|(?P<prop_theorem>_PROP\._\s+(?P<prop_theorem_id>{_ROMAN})\.\s+THEOR\.\s+(?P<theorem_id>{_ROMAN})\.)"
    rf"|(?P<proposition>PROP\.\s+(?P<proposition_id>{_ROMAN})\.)"
    rf")",
    flags=re.IGNORECASE,
)
_ASCII_ROMAN_TOKEN = re.compile(r"(?<![A-Za-z])[IVXLCDM]+(?![A-Za-z])", re.IGNORECASE)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _is_block_start(text: str, offset: int) -> bool:
    if offset == 0:
        return True
    return bool(re.search(r"(?:\r?\n)[ \t]*(?:\r?\n)[ \t]*\Z", text[:offset]))


def _case(match: re.Match[str], *, absolute_start: int) -> dict[str, Any]:
    source = match.group(0)
    if match.group("definition") is not None:
        identifiers = [match.group("definition_id").upper()]
        canonical = f"Definition {identifiers[0]}."
        expected_patterns = [rf"Определение\s+{identifiers[0]}\."]
        family = "definition"
    elif match.group("axiom") is not None:
        identifiers = [match.group("axiom_id").upper()]
        canonical = f"Axiom {identifiers[0]}."
        expected_patterns = [rf"Аксиома\s+{identifiers[0]}\."]
        family = "axiom"
    elif match.group("prop_problem") is not None:
        identifiers = [
            match.group("prop_problem_id").upper(),
            match.group("problem_id").upper(),
        ]
        canonical = f"Proposition {identifiers[0]}. Problem {identifiers[1]}."
        expected_patterns = [
            rf"Предложение\s+{identifiers[0]}\.\s+Задача\s+{identifiers[1]}\.",
            rf"Предложение\s+{identifiers[0]}\.\s+Проблема\s+{identifiers[1]}\.",
        ]
        family = "proposition_problem"
    elif match.group("prop_theorem") is not None:
        identifiers = [
            match.group("prop_theorem_id").upper(),
            match.group("theorem_id").upper(),
        ]
        canonical = f"Proposition {identifiers[0]}. Theorem {identifiers[1]}."
        expected_patterns = [
            rf"Предложение\s+{identifiers[0]}\.\s+Теорема\s+{identifiers[1]}\."
        ]
        family = "proposition_theorem"
    elif match.group("proposition") is not None:
        identifiers = [match.group("proposition_id").upper()]
        canonical = f"Proposition {identifiers[0]}."
        expected_patterns = [rf"Предложение\s+{identifiers[0]}\."]
        family = "proposition"
    else:  # pragma: no cover - regex exhaustiveness guard
        raise RuntimeError("unrecognized legacy heading family")
    return {
        "family": family,
        "source_start": absolute_start + match.start(),
        "source_end": absolute_start + match.end(),
        "source_text": source,
        "roman_identifiers": identifiers,
        "canonical_model_input": canonical,
        "expected_target_patterns": expected_patterns,
    }


def _detect(text: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for match in _HEADING_RE.finditer(text):
        if not _is_block_start(text, match.start()):
            continue
        cases.append(_case(match, absolute_start=0))
    return cases


def _evaluate(case: dict[str, Any], target: str) -> dict[str, Any]:
    stripped = target.strip()
    identifiers = [value.upper() for value in _ASCII_ROMAN_TOKEN.findall(stripped)]
    expected_identifiers = [str(value).upper() for value in case["roman_identifiers"]]
    exact_form = any(
        re.fullmatch(pattern, stripped, flags=re.IGNORECASE) is not None
        for pattern in case["expected_target_patterns"]
    )
    return {
        "roman_identifiers_expected": expected_identifiers,
        "roman_identifiers_target": identifiers,
        "roman_identifiers_preserved": identifiers == expected_identifiers,
        "exact_expected_target_form": exact_form,
        "acceptable": exact_form and identifiers == expected_identifiers,
    }


def main() -> int:
    source_path = Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"]).resolve()
    output_dir = Path(
        os.environ.get("ROCKETDICT_HEADING_FEASIBILITY_ROOT", "work/legacy-heading-feasibility")
    ).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if _sha_file(source_path) != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source hash drift")
    content = source_path.read_text(encoding="utf-8")
    cases = _detect(content)
    if len(cases) != EXPECTED_HEADING_COUNT:
        raise RuntimeError(
            f"Legacy block-heading inventory drift: {len(cases)} != {EXPECTED_HEADING_COUNT}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    attempts: list[dict[str, Any]] = []
    accepted_case_count = 0
    for case_index, case in enumerate(cases):
        cell_records: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        for beam_size, num_hypotheses in GENERATION_CELLS:
            generated = translator.translate(
                [str(case["canonical_model_input"])],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=64,
            )
            if len(generated) != 1 or not generated[0]:
                raise RuntimeError(f"OPUS returned no heading hypotheses for case {case_index}")
            candidates: list[dict[str, Any]] = []
            for model_index, hypothesis in enumerate(generated[0]):
                target = str(hypothesis.get("text") or "")
                verdict = _evaluate(case, target)
                candidate = {
                    "model_index": model_index,
                    "rank": int(
                        hypothesis.get("rank")
                        if hypothesis.get("rank") is not None
                        else model_index
                    ),
                    "score": hypothesis.get("score"),
                    "target_text": target,
                    "verdict": verdict,
                    "raw_model_output": True,
                }
                candidates.append(candidate)
                if selected is None and verdict["acceptable"] is True:
                    selected = {
                        "beam_size": beam_size,
                        "num_hypotheses": num_hypotheses,
                        **candidate,
                    }
            cell_records.append(
                {
                    "beam_size": beam_size,
                    "num_hypotheses": num_hypotheses,
                    "candidates": candidates,
                }
            )
            if selected is not None:
                break
        if selected is not None:
            accepted_case_count += 1
        attempts.append(
            {
                "case_index": case_index,
                **case,
                "selected": selected,
                "cells": cell_records,
            }
        )

    family_counts: dict[str, int] = {}
    family_accepted_counts: dict[str, int] = {}
    for row in attempts:
        family = str(row["family"])
        family_counts[family] = family_counts.get(family, 0) + 1
        if row["selected"] is not None:
            family_accepted_counts[family] = family_accepted_counts.get(family, 0) + 1

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "purpose": "research-only raw OPUS feasibility for complete legacy Gutenberg block headings",
        "promotion_allowed": False,
        "source_sha256": OPTICKS_SHA256,
        "heading_count": len(attempts),
        "accepted_heading_count": accepted_case_count,
        "rejected_heading_count": len(attempts) - accepted_case_count,
        "family_counts": family_counts,
        "family_accepted_counts": family_accepted_counts,
        "generation_cells": [
            {"beam_size": beam_size, "num_hypotheses": num_hypotheses}
            for beam_size, num_hypotheses in GENERATION_CELLS
        ],
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "deterministic_target_translation": False,
        "post_translation_injection": False,
        "attempts": attempts,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = output_dir / "full-opticks-legacy-heading-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "heading_count": len(attempts),
                "accepted_heading_count": accepted_case_count,
                "rejected_heading_count": len(attempts) - accepted_case_count,
                "family_counts": family_counts,
                "family_accepted_counts": family_accepted_counts,
                "rejected_case_indexes": [
                    int(row["case_index"])
                    for row in attempts
                    if row["selected"] is None
                ],
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
