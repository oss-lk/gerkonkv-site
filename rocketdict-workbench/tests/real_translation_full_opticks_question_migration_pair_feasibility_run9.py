from __future__ import annotations

"""Research-only pair feasibility for complementary question-mark migration.

Run-9 Stage10 context 2730 has two complementary row-local question-mark
failures: sequence 3016 adds ``?`` before the source question ends, while 3020
owns the source ``Lead?`` and drops it.  Translating the entire 339-NLP-token
context is outside the maintained 160-token whole-context cap and produced
severe model degradation.

This experiment instead tests two disjoint adjacent windows around the failing
rows.  Each window remains below the already proven 160-NLP-token cap.  No
punctuation is moved or rewritten; only exact raw OPUS n-best candidates are
considered, with the existing strict whole-context selector plus Gutenberg
emphasis preservation.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_candidate_context, evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-question-migration-pair-feasibility-run9/1"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
RUN_OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
CONTEXT_SEQUENCE = 2730
STANDARD_CAP = 160
BASE = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}
WINDOWS = [
    {
        "name": "question_opening_pair",
        "sequences": [3016, 3017],
        "source_start": 530302,
        "source_end": 530971,
        "nlp_tokens": 138,
    },
    {
        "name": "question_closing_pair",
        "sequences": [3019, 3020],
        "source_start": 531289,
        "source_end": 531872,
        "nlp_tokens": 132,
    },
]


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


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    unique: set[int] = set()
    for row in _ordered(rows):
        verdict = evaluate_rescue_pair(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
        seq = int(row["sequence_number"])
        failures = {
            "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key, failed in failures.items():
            if failed:
                counts[key] += 1
                unique.add(seq)
    return {**counts, "unique": len(unique)}


def _context_sequence(row: dict[str, Any]) -> int | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    value = planner.get("context_sentence_start")
    return None if value is None else int(value)


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_QUESTION_MIGRATION_PAIR_ROOT",
            "work/question-migration-pair-run9",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != DB_SHA:
        raise RuntimeError("run9 database identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN_ID)
        rows = get_run_items(connection, RUN_ID, kind="translation_segment")
        output = dict(run.get("output") or {})
        context_run_id = int(output["context_run_id"])
        context_run = get_run(connection, context_run_id)
        nlp_run_id = int(dict(context_run.get("output") or {})["nlp_run_id"])
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document = get_document(connection, int(output["document_version_id"]))

    if str(run.get("output_sha256") or "") != RUN_OUTPUT_SHA:
        raise RuntimeError("run9 output identity drift")
    if str(document.get("text_sha256") or "") != TEXT_SHA:
        raise RuntimeError("run9 source identity drift")
    content = str(document["content_text"])
    rows = _ordered(rows)
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run9 source coverage drift")
    if _inventory(rows) != BASE:
        raise RuntimeError(f"run9 hard-gate drift: {_inventory(rows)!r}")

    by_sequence = {int(row["sequence_number"]): row for row in rows}
    context_rows = [row for row in rows if _context_sequence(row) == CONTEXT_SEQUENCE]
    if [int(row["sequence_number"]) for row in context_rows] != [3016,3017,3018,3019,3020]:
        raise RuntimeError("context2730 row cohort drift")

    first = context_rows[0]
    last = context_rows[-1]
    first_counts = [
        str(first.get("source_text") or "").count("?"),
        str(first.get("target_text") or "").count("?"),
    ]
    last_counts = [
        str(last.get("source_text") or "").count("?"),
        str(last.get("target_text") or "").count("?"),
    ]
    if first_counts != [0,1] or last_counts != [1,0]:
        raise RuntimeError(
            f"complementary question migration trigger drift: first={first_counts}, last={last_counts}"
        )

    prepared: list[dict[str, Any]] = []
    used_sequences: set[int] = set()
    for definition in WINDOWS:
        sequences = [int(value) for value in definition["sequences"]]
        if used_sequences.intersection(sequences):
            raise RuntimeError("question migration windows overlap")
        used_sequences.update(sequences)
        primary = [by_sequence[sequence] for sequence in sequences]
        if any(_context_sequence(row) != CONTEXT_SEQUENCE for row in primary):
            raise RuntimeError(f"window crossed Stage10 context: {definition['name']}")
        start = int(definition["source_start"])
        end = int(definition["source_end"])
        source = content[start:end]
        if "".join(str(row.get("source_text") or "") for row in primary) != source:
            raise RuntimeError(f"window source coverage drift: {definition['name']}")
        token_count = sum(
            1
            for token in nlp_tokens
            if int(token["source_start"]) >= start and int(token["source_end"]) <= end
        )
        if token_count != int(definition["nlp_tokens"]):
            raise RuntimeError(
                f"window token-count drift {definition['name']}: {token_count}"
            )
        if token_count > STANDARD_CAP:
            raise RuntimeError(f"window exceeds maintained cap: {definition['name']}")
        prepared.append(
            {
                **definition,
                "primary_rows": primary,
                "source_text": source,
                "token_count": token_count,
            }
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [str(window["source_text"]) for window in prepared],
        beam_size=6,
        num_hypotheses=6,
        max_decoding_length=1024,
    )
    if len(generated) != len(prepared) or any(len(group) != 6 for group in generated):
        raise RuntimeError("question migration pair n-best cardinality drift")

    cases: list[dict[str, Any]] = []
    replacements: dict[int, dict[str, Any]] = {}
    for window, hypotheses in zip(prepared, generated, strict=True):
        candidates: list[dict[str, Any]] = []
        first_admissible: int | None = None
        for rank, hypothesis in enumerate(hypotheses):
            target = str(hypothesis.get("text") or "")
            selection = evaluate_candidate_context(
                list(window["primary_rows"]),
                [{"source_text": str(window["source_text"]), "target_text": target}],
            )
            emphasis = compare_emphasis_markup_preservation(
                str(window["source_text"]), target
            )
            admissible = (
                selection.get("accepted") is True and emphasis.get("passed") is True
            )
            candidates.append(
                {
                    "rank": rank,
                    "target_text": target,
                    "score": hypothesis.get("score"),
                    "selection": selection,
                    "emphasis_markup": emphasis,
                    "mechanically_admissible": admissible,
                }
            )
            if first_admissible is None and admissible:
                first_admissible = rank

        if first_admissible is not None:
            replacements[int(window["source_start"])] = {
                "sequences": list(window["sequences"]),
                "row": {
                    "sequence_number": 0,
                    "kind": "translation_segment",
                    "source_start": int(window["source_start"]),
                    "source_end": int(window["source_end"]),
                    "source_text": str(window["source_text"]),
                    "target_text": str(candidates[first_admissible]["target_text"]),
                    "payload": {
                        "research_complementary_question_migration_pair": True,
                        "selected_rank": first_admissible,
                        "raw_model_candidate": True,
                    },
                },
            }
        cases.append(
            {
                "name": window["name"],
                "primary_sequences": list(window["sequences"]),
                "source_start": int(window["source_start"]),
                "source_end": int(window["source_end"]),
                "nlp_token_count": int(window["token_count"]),
                "source_text": str(window["source_text"]),
                "candidates": candidates,
                "first_mechanically_admissible_rank": first_admissible,
                "first_mechanically_admissible_target": (
                    None
                    if first_admissible is None
                    else candidates[first_admissible]["target_text"]
                ),
            }
        )

    selected_sequences = {
        sequence
        for replacement in replacements.values()
        for sequence in replacement["sequences"]
    }
    candidate_rows: list[dict[str, Any]] = []
    for row in rows:
        sequence = int(row["sequence_number"])
        if sequence in selected_sequences:
            if sequence == min(
                replacements[int(row["source_start"])] ["sequences"]
            ) if int(row["source_start"]) in replacements else False:
                pass
            continue
        candidate_rows.append(dict(row))
    # Insert selected replacement rows by source span rather than relying on shifted sequence IDs.
    candidate_rows.extend(dict(value["row"]) for value in replacements.values())
    candidate_rows.sort(key=lambda row: int(row["source_start"]))
    for sequence, row in enumerate(candidate_rows):
        row["sequence_number"] = sequence
    if "".join(str(row.get("source_text") or "") for row in candidate_rows) != content:
        raise RuntimeError("question migration pair counterfactual source coverage drift")
    counterfactual = _inventory(candidate_rows)
    if any(counterfactual[key] > BASE[key] for key in BASE):
        raise RuntimeError(
            f"question migration pair counterfactual regression: {counterfactual!r}"
        )
    if _sha(database) != DB_SHA:
        raise RuntimeError("question migration pair feasibility mutated run9 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only two disjoint <=160-NLP-token raw OPUS pair windows for "
            "complementary question-mark migration; no punctuation/target rewriting"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": RUN_OUTPUT_SHA,
        "context_sequence": CONTEXT_SEQUENCE,
        "maintained_whole_context_cap": STANDARD_CAP,
        "complementary_failure_sequences": [3016,3020],
        "windows": [
            {
                "name": case["name"],
                "primary_sequences": case["primary_sequences"],
                "source_start": case["source_start"],
                "source_end": case["source_end"],
                "nlp_token_count": case["nlp_token_count"],
            }
            for case in cases
        ],
        "cases": cases,
        "selected_window_names": [
            case["name"]
            for case in cases
            if case["first_mechanically_admissible_rank"] is not None
        ],
        "base_hard_gate_counts": BASE,
        "counterfactual_hard_gate_counts": counterfactual,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    out = root / "full-opticks-question-migration-pair-feasibility-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "selected_window_names": payload["selected_window_names"],
                "selected": [
                    (case["name"], case["first_mechanically_admissible_rank"], case["first_mechanically_admissible_target"])
                    for case in cases
                ],
                "counterfactual_hard_gate_counts": counterfactual,
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
