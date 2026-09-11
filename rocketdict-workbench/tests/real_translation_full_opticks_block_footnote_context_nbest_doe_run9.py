from __future__ import annotations

"""Research-only n-best depth DOE for exact run-9 footnote linguistic bodies.

This experiment does not select or persist any translation.  It asks a narrower
question after beam6/n6 whole-context feasibility produced zero emphasis-safe
candidates: does a deeper deterministic OPUS beam expose any raw candidate that
passes the existing strict selector and Gutenberg emphasis-preservation veto?
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-block-footnote-context-nbest-doe-run9/1"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
STARTS = [151466, 151557, 253849, 253919, 254102]
LETTERS = list("GHJKM")
PARAGRAPH_ENDS = [151557, 151652, 253919, 254026, 254202]
ROW_COVERAGE_ENDS = [151557, 151655, 253919, 254026, 254205]
CELLS = [(6, 6), (12, 12), (24, 24)]
MARKER = re.compile(r"^\[(?P<letter>[A-Z])\](?P<space>[ \t]+)")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_FOOTNOTE_CONTEXT_NBEST_DOE_ROOT",
            "work/footnote-context-nbest-doe-run9",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != DB_SHA:
        raise RuntimeError("run9 db identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN_ID)
        rows = get_run_items(connection, RUN_ID, kind="translation_segment")
        document = get_document(
            connection, int(dict(run.get("output") or {})["document_version_id"])
        )
    if str(run.get("output_sha256") or "") != OUTPUT_SHA:
        raise RuntimeError("run9 output identity drift")
    if str(document.get("text_sha256") or "") != TEXT_SHA:
        raise RuntimeError("run9 source identity drift")
    content = str(document["content_text"])
    ordered = sorted(rows, key=lambda row: int(row["sequence_number"]))
    if "".join(str(row.get("source_text") or "") for row in ordered) != content:
        raise RuntimeError("run9 source coverage drift")

    by_start = {int(row["source_start"]): row for row in ordered}
    cases: list[dict[str, Any]] = []
    for start, letter, paragraph_end, row_end in zip(
        STARTS, LETTERS, PARAGRAPH_ENDS, ROW_COVERAGE_ENDS, strict=True
    ):
        first = by_start[start]
        source = str(first.get("source_text") or "")
        match = MARKER.match(source)
        if match is None or match.group("letter") != letter:
            raise RuntimeError(f"marker cohort drift {letter}")
        if evaluate_rescue_pair(source, str(first.get("target_text") or "")).get(
            "product_hard_passed"
        ) is True:
            raise RuntimeError(f"hard-failure trigger drift {letter}")
        separator_start = content.find("\n\n", start)
        if separator_start < 0 or separator_start + 2 != paragraph_end:
            raise RuntimeError(f"semantic paragraph boundary drift {letter}")
        if paragraph_end > row_end:
            raise RuntimeError(f"paragraph exceeds row coverage {letter}")
        marker = source[: match.end()]
        marker_end = start + len(marker)
        body = content[marker_end:separator_start]
        trailing = content[paragraph_end:row_end]
        if not body.strip() or trailing.strip():
            raise RuntimeError(f"footnote body/trailing structure drift {letter}")
        cases.append(
            {
                "letter": letter,
                "source_start": start,
                "semantic_paragraph_end": paragraph_end,
                "row_coverage_end": row_end,
                "body_source": body,
                "row_trailing_whitespace_source": trailing,
                "cells": [],
            }
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    total_hypotheses = 0
    for beam_size, num_hypotheses in CELLS:
        generated = translator.translate(
            [str(case["body_source"]) for case in cases],
            beam_size=beam_size,
            num_hypotheses=num_hypotheses,
            max_decoding_length=256,
        )
        if len(generated) != len(cases):
            raise RuntimeError(f"backend cardinality drift beam={beam_size}")
        for case, hypotheses in zip(cases, generated, strict=True):
            if len(hypotheses) != num_hypotheses:
                raise RuntimeError(
                    f"n-best cardinality drift {case['letter']} beam={beam_size}: "
                    f"{len(hypotheses)}"
                )
            evaluated: list[dict[str, Any]] = []
            for rank, hypothesis in enumerate(hypotheses):
                target = str(hypothesis.get("text") or "")
                verdict = evaluate_rescue_pair(str(case["body_source"]), target)
                emphasis = compare_emphasis_markup_preservation(
                    str(case["body_source"]), target
                )
                admissible = (
                    verdict.get("strictly_eligible") is True
                    and emphasis.get("passed") is True
                )
                evaluated.append(
                    {
                        "rank": rank,
                        "target_text": target,
                        "score": hypothesis.get("score"),
                        "strictly_eligible": verdict.get("strictly_eligible") is True,
                        "product_hard_passed": verdict.get("product_hard_passed") is True,
                        "emphasis_markup": emphasis,
                        "mechanically_admissible": admissible,
                    }
                )
                total_hypotheses += 1
            case["cells"].append(
                {
                    "beam_size": beam_size,
                    "num_hypotheses": num_hypotheses,
                    "hypotheses": evaluated,
                    "admissible_ranks": [
                        item["rank"] for item in evaluated if item["mechanically_admissible"]
                    ],
                }
            )

    admissible: list[dict[str, Any]] = []
    for case in cases:
        for cell in case["cells"]:
            for hypothesis in cell["hypotheses"]:
                if hypothesis["mechanically_admissible"]:
                    admissible.append(
                        {
                            "letter": case["letter"],
                            "beam_size": cell["beam_size"],
                            "num_hypotheses": cell["num_hypotheses"],
                            "rank": hypothesis["rank"],
                            "target_text": hypothesis["target_text"],
                            "score": hypothesis["score"],
                        }
                    )

    if total_hypotheses != len(cases) * sum(cell[1] for cell in CELLS):
        raise RuntimeError("DOE hypothesis total drift")
    if _sha(database) != DB_SHA:
        raise RuntimeError("DOE mutated run9 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only deeper exact-source OPUS search for whole footnote bodies; "
            "no selection/persistence and emphasis preservation remains mandatory"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": OUTPUT_SHA,
        "attempted_source_starts": STARTS,
        "attempted_letters": LETTERS,
        "cells": [
            {"beam_size": beam, "num_hypotheses": nbest} for beam, nbest in CELLS
        ],
        "total_hypothesis_count": total_hypotheses,
        "mechanically_admissible_count": len(admissible),
        "mechanically_admissible_candidates": admissible,
        "cases": cases,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    out = root / "full-opticks-block-footnote-context-nbest-doe-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "total_hypothesis_count": total_hypotheses,
                "mechanically_admissible_count": len(admissible),
                "mechanically_admissible_candidates": admissible,
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
