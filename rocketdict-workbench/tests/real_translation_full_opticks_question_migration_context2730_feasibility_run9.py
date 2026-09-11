from __future__ import annotations

"""Research-only exact whole-context feasibility for run-9 question-mark migration.

Stage10 context 2730 is split into five Stage12 rows.  Exactly two rows fail the
maintained question-mark count in complementary directions: the first raw MT
fragment adds ``?`` while the last fragment, which owns the source ``Lead?``,
drops it.  Aggregate source/target question-mark cardinality is nevertheless
1/1.  We do not weaken the row hard gate or move punctuation post-hoc.

Instead this experiment sends the exact unchanged Stage10 source context to the
pinned OPUS model as one research request.  The context is deliberately above
the existing proven 160-NLP-token whole-context rescue cap, so success here may
only establish feasibility for a separately bounded source-defined mechanism;
it cannot silently widen the maintained rescue contract.
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

SCHEMA = "rocketdict-full-opticks-question-migration-context2730-feasibility-run9/1"
DB_SHA = "9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad"
RUN_ID = 9
RUN_OUTPUT_SHA = "c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be"
TEXT_SHA = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
CONTEXT_SEQUENCE = 2730
CONTEXT_START = 530302
CONTEXT_END = 531872
EXPECTED_NLP_TOKENS = 339
STANDARD_WHOLE_CONTEXT_CAP = 160
EXPECTED_ROW_SEQUENCES = [3016, 3017, 3018, 3019, 3020]
EXPECTED_ROW_SPANS = [
    [530302, 530626],
    [530626, 530971],
    [530971, 531289],
    [531289, 531604],
    [531604, 531872],
]
BASE = {"numeric_symbol": 24, "punctuation": 30, "length": 0, "unique": 52}


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
    if value is None:
        return None
    return int(value)


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_QUESTION_MIGRATION_2730_ROOT",
            "work/question-migration-context2730-run9",
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
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
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

    context = next(
        (row for row in context_rows if int(row["sequence_number"]) == CONTEXT_SEQUENCE),
        None,
    )
    if context is None:
        raise RuntimeError("Stage10 context2730 missing")
    source = str(context.get("source_text") or "")
    if [int(context["source_start"]), int(context["source_end"])] != [
        CONTEXT_START,
        CONTEXT_END,
    ]:
        raise RuntimeError("context2730 span drift")
    if content[CONTEXT_START:CONTEXT_END] != source:
        raise RuntimeError("context2730 differs from immutable source")

    primary = [row for row in rows if _context_sequence(row) == CONTEXT_SEQUENCE]
    if [int(row["sequence_number"]) for row in primary] != EXPECTED_ROW_SEQUENCES:
        raise RuntimeError("context2730 selected-row sequence drift")
    if [
        [int(row["source_start"]), int(row["source_end"])] for row in primary
    ] != EXPECTED_ROW_SPANS:
        raise RuntimeError("context2730 selected-row span drift")
    if "".join(str(row.get("source_text") or "") for row in primary) != source:
        raise RuntimeError("context2730 primary rows do not cover exact source")

    token_count = sum(
        1
        for token in nlp_tokens
        if int(token["source_start"]) >= CONTEXT_START
        and int(token["source_end"]) <= CONTEXT_END
    )
    if token_count != EXPECTED_NLP_TOKENS:
        raise RuntimeError(f"context2730 NLP token count drift: {token_count}")
    if token_count <= STANDARD_WHOLE_CONTEXT_CAP:
        raise RuntimeError("context2730 unexpectedly fits maintained 160-token cap")

    row_question_counts: list[dict[str, Any]] = []
    punctuation_failure_sequences: list[int] = []
    for row in primary:
        row_source = str(row.get("source_text") or "")
        row_target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(row_source, row_target)
        if verdict.get("punctuation_passed") is not True:
            punctuation_failure_sequences.append(int(row["sequence_number"]))
        row_question_counts.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_question_marks": row_source.count("?"),
                "target_question_marks": row_target.count("?"),
                "punctuation_passed": verdict.get("punctuation_passed") is True,
            }
        )
    if punctuation_failure_sequences != [3016, 3020]:
        raise RuntimeError(
            f"context2730 complementary punctuation cohort drift: {punctuation_failure_sequences!r}"
        )
    primary_target = "".join(str(row.get("target_text") or "") for row in primary)
    if source.count("?") != 1 or primary_target.count("?") != 1:
        raise RuntimeError("context2730 aggregate question-mark cardinality drift")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [source],
        beam_size=6,
        num_hypotheses=6,
        max_decoding_length=2048,
    )
    if len(generated) != 1 or len(generated[0]) != 6:
        raise RuntimeError("context2730 n-best cardinality drift")

    candidates: list[dict[str, Any]] = []
    first_admissible: int | None = None
    for rank, hypothesis in enumerate(generated[0]):
        target = str(hypothesis.get("text") or "")
        selection = evaluate_candidate_context(
            primary,
            [{"source_text": source, "target_text": target}],
        )
        emphasis = compare_emphasis_markup_preservation(source, target)
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

    counterfactual = BASE
    if first_admissible is not None:
        replacement = {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": CONTEXT_START,
            "source_end": CONTEXT_END,
            "source_text": source,
            "target_text": candidates[first_admissible]["target_text"],
            "payload": {
                "research_question_migration_whole_context": True,
                "selected_rank": first_admissible,
                "raw_model_candidate": True,
            },
        }
        primary_ids = {int(row["id"]) for row in primary}
        candidate_rows = [dict(row) for row in rows if int(row["id"]) not in primary_ids]
        candidate_rows.append(replacement)
        candidate_rows.sort(key=lambda row: int(row["source_start"]))
        for sequence, row in enumerate(candidate_rows):
            row["sequence_number"] = sequence
        if "".join(str(row.get("source_text") or "") for row in candidate_rows) != content:
            raise RuntimeError("context2730 counterfactual source coverage drift")
        counterfactual = _inventory(candidate_rows)
        if any(counterfactual[key] > BASE[key] for key in BASE):
            raise RuntimeError(
                f"context2730 whole-context counterfactual regression: {counterfactual!r}"
            )

    if _sha(database) != DB_SHA:
        raise RuntimeError("context2730 feasibility mutated run9 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only exact Stage10 context raw OPUS feasibility for complementary "
            "question-mark migration; maintained 160-token rescue cap is not changed"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": DB_SHA,
        "base_translation_run_id": RUN_ID,
        "base_translation_output_sha256": RUN_OUTPUT_SHA,
        "context_run_id": context_run_id,
        "context_sequence": CONTEXT_SEQUENCE,
        "context_source_start": CONTEXT_START,
        "context_source_end": CONTEXT_END,
        "context_nlp_token_count": token_count,
        "maintained_whole_context_cap": STANDARD_WHOLE_CONTEXT_CAP,
        "exceeds_maintained_whole_context_cap": True,
        "primary_row_sequences": EXPECTED_ROW_SEQUENCES,
        "primary_row_spans": EXPECTED_ROW_SPANS,
        "primary_row_question_mark_counts": row_question_counts,
        "primary_punctuation_failure_sequences": punctuation_failure_sequences,
        "aggregate_source_question_marks": source.count("?"),
        "aggregate_primary_target_question_marks": primary_target.count("?"),
        "base_hard_gate_counts": BASE,
        "counterfactual_hard_gate_counts": counterfactual,
        "candidates": candidates,
        "first_mechanically_admissible_rank": first_admissible,
        "first_mechanically_admissible_target": (
            None if first_admissible is None else candidates[first_admissible]["target_text"]
        ),
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    out = root / "full-opticks-question-migration-context2730-feasibility-run9.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "context_nlp_token_count": token_count,
                "first_mechanically_admissible_rank": first_admissible,
                "first_mechanically_admissible_target": payload[
                    "first_mechanically_admissible_target"
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
