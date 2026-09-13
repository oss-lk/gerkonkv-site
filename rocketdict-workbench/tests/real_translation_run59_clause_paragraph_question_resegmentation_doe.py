from __future__ import annotations

"""Read-only rank0 DOE for clause + paragraph resegmentation of migrated questions.

Starting from the generic forward-paragraph trigger, this experiment adds one
source-only clause boundary inside the left split row.  The boundary is the
latest comma whose trailing clause, together with the short paragraph-terminal
question tail, has a bounded lexical size.  No lexical anchor, corpus sequence
or source offset chooses the boundary.  The resulting three exact source spans
are translated independently with the pinned baseline OPUS raw rank0 and must
all pass the unchanged strict selector; aggregate source coverage, strict gates,
emphasis and alphabetic volume must also pass.  The canonical DB is read-only.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

import real_translation_run59_forward_paragraph_boundary_resegmentation_doe as base
from real_translation_run59_forward_paragraph_boundary_resegmentation_doe_v3 import (
    discover_trigger_v3,
)

SCHEMA = "rocketdict-run59-clause-paragraph-question-resegmentation-doe/1"
BASE_DATABASE_SHA256 = "41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d"
BASE_RUN_ID = 59
BASE_RUN_OUTPUT_SHA256 = "5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
LEADING_MIN_NLP_TOKENS = 24
LEADING_MAX_NLP_TOKENS = 64
TRAILING_CLAUSE_MIN_NLP_TOKENS = 16
TRAILING_CLAUSE_MAX_NLP_TOKENS = 32
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row.get("payload") or {})


def _non_space_tokens(rows: list[dict[str, Any]], *, start: int, end: int) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if int(row["source_start"]) >= start
        and int(row["source_end"]) <= end
        and not bool((_payload(row).get("flags") or {}).get("is_space"))
    ]


def _select_clause_cut(
    *,
    content: str,
    nlp_tokens: list[dict[str, Any]],
    left_start: int,
    old_boundary: int,
    paragraph_boundary: int,
) -> dict[str, Any]:
    pair_tokens = _non_space_tokens(nlp_tokens, start=left_start, end=paragraph_boundary)
    candidates: list[dict[str, Any]] = []
    for index, token in enumerate(pair_tokens):
        if str(token.get("source_text") or "") != ",":
            continue
        if int(token["source_end"]) > old_boundary:
            continue
        next_index = index + 1
        if next_index >= len(pair_tokens):
            continue
        cut = int(pair_tokens[next_index]["source_start"])
        leading_count = len(_non_space_tokens(nlp_tokens, start=left_start, end=cut))
        trailing_count = len(_non_space_tokens(nlp_tokens, start=cut, end=paragraph_boundary))
        if not (LEADING_MIN_NLP_TOKENS <= leading_count <= LEADING_MAX_NLP_TOKENS):
            continue
        if not (
            TRAILING_CLAUSE_MIN_NLP_TOKENS
            <= trailing_count
            <= TRAILING_CLAUSE_MAX_NLP_TOKENS
        ):
            continue
        candidates.append(
            {
                "cut": cut,
                "leading_nlp_token_count": leading_count,
                "trailing_clause_nlp_token_count": trailing_count,
                "comma_source_start": int(token["source_start"]),
                "comma_source_end": int(token["source_end"]),
            }
        )
    if not candidates:
        raise RuntimeError("no bounded source-only comma clause boundary")
    selected = max(candidates, key=lambda row: int(row["cut"]))
    selected["candidate_boundary_count"] = len(candidates)
    selected["selection_rule"] = "latest_bounded_comma_before_existing_split"
    selected["lexical_anchor_used"] = False
    selected["sequence_whitelist_used"] = False
    selected["source_offset_whitelist_used"] = False
    if content[int(selected["comma_source_start"]):int(selected["comma_source_end"])] != ",":
        raise RuntimeError("selected clause boundary does not reference immutable comma")
    return selected


def _candidate(source: str, hypothesis: dict[str, Any]) -> dict[str, Any]:
    if int(hypothesis.get("rank", -1)) != 0:
        raise RuntimeError("DOE permits raw rank0 only")
    target = str(hypothesis.get("text") or "")
    selection = base.evaluate_candidate(source, target)
    return {
        "model_input": source,
        "hypothesis": dict(hypothesis),
        "raw_rank0_target": target,
        "selection": selection,
    }


def main() -> int:
    root = Path(os.environ.get(
        "ROCKETDICT_RUN59_CLAUSE_PARAGRAPH_DOE_ROOT",
        "work/run59-clause-paragraph-question-resegmentation-doe",
    )).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    before_sha = _sha(database)
    if before_sha != BASE_DATABASE_SHA256:
        raise RuntimeError(f"canonical DB identity drift: {before_sha}")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda r: int(r["sequence_number"]))
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
        context_run = get_run(connection, int(output["context_run_id"]))
        nlp_run_id = int(dict(context_run.get("output") or {})["nlp_run_id"])
        nlp_tokens = sorted(get_run_items(connection, nlp_run_id, kind="nlp_token"), key=lambda r: int(r["sequence_number"]))
    if str(run.get("output_sha256") or "") != BASE_RUN_OUTPUT_SHA256:
        raise RuntimeError("run59 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    if len(rows) != 3335:
        raise RuntimeError("run59 segment census drift")
    content = str(document["content_text"])

    triggers: list[dict[str, Any]] = []
    for left, right in zip(rows, rows[1:]):
        trigger = discover_trigger_v3(content=content, left=left, right=right, nlp_tokens=nlp_tokens)
        if trigger is not None:
            triggers.append(trigger)
    if len(triggers) != 1:
        raise RuntimeError(f"forward trigger cohort drift: {len(triggers)}")
    trigger = triggers[0]

    left_start = int(trigger["old_boundary"]) - len(str(trigger["base_left_source"]))
    old_boundary = int(trigger["old_boundary"])
    paragraph_boundary = int(trigger["new_boundary"])
    right_end = old_boundary + len(str(trigger["base_right_source"]))
    clause = _select_clause_cut(
        content=content,
        nlp_tokens=nlp_tokens,
        left_start=left_start,
        old_boundary=old_boundary,
        paragraph_boundary=paragraph_boundary,
    )
    clause_cut = int(clause["cut"])
    sources = [
        content[left_start:clause_cut],
        content[clause_cut:paragraph_boundary],
        content[paragraph_boundary:right_end],
    ]
    if "".join(sources) != str(trigger["base_left_source"]) + str(trigger["base_right_source"]):
        raise RuntimeError("three-way source coverage drift")
    token_counts = [
        len(_non_space_tokens(nlp_tokens, start=start, end=end))
        for start, end in ((left_start, clause_cut), (clause_cut, paragraph_boundary), (paragraph_boundary, right_end))
    ]
    if token_counts != [int(clause["leading_nlp_token_count"]), int(clause["trailing_clause_nlp_token_count"]), int(trigger["candidate_right_nlp_token_count"])]:
        raise RuntimeError(f"three-way token accounting drift: {token_counts!r}")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(sources, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
    if len(generated) != 3 or any(len(group) != 1 for group in generated):
        raise RuntimeError("three-way OPUS cardinality drift")
    candidate_rows = [_candidate(source, group[0]) for source, group in zip(sources, generated, strict=True)]

    aggregate_source = "".join(sources)
    aggregate_target = "".join(row["raw_rank0_target"] for row in candidate_rows)
    aggregate_verdict = evaluate_rescue_pair(aggregate_source, aggregate_target)
    aggregate_emphasis = compare_emphasis_markup_preservation(aggregate_source, aggregate_target)
    base_target = str(trigger["base_left_target"]) + str(trigger["base_right_target"])
    base_alpha = sum(ch.isalpha() for ch in base_target)
    candidate_alpha = sum(ch.isalpha() for ch in aggregate_target)
    accepted = bool(
        all(row["selection"]["accepted"] for row in candidate_rows)
        and aggregate_verdict.get("strictly_eligible") is True
        and aggregate_emphasis.get("passed") is True
        and candidate_alpha >= base_alpha
    )

    after_sha = _sha(database)
    if after_sha != before_sha:
        raise RuntimeError("read-only DOE mutated canonical database")
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only generic three-way clause + paragraph resegmentation for complementary question migration",
        "base_run_id": BASE_RUN_ID,
        "base_database_sha256": before_sha,
        "base_run_output_sha256": BASE_RUN_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "segment_count": len(rows),
        "trigger_pair": [int(trigger["left_sequence"]), int(trigger["right_sequence"])],
        "forward_trigger": trigger,
        "clause_boundary": clause,
        "source_spans": [[left_start, clause_cut], [clause_cut, paragraph_boundary], [paragraph_boundary, right_end]],
        "source_token_counts": token_counts,
        "source_texts": sources,
        "generation": {
            "implementation": "opus-en-ru-ct2",
            "beam_size": BEAM_SIZE,
            "num_hypotheses": NUM_HYPOTHESES,
            "max_decoding_length": MAX_DECODING_LENGTH,
            "selected_rank": 0,
        },
        "candidate_rows": candidate_rows,
        "aggregate_selection": {
            "accepted": accepted,
            "mechanical_verdict": aggregate_verdict,
            "emphasis_markup": aggregate_emphasis,
            "base_target_alpha_count": base_alpha,
            "candidate_target_alpha_count": candidate_alpha,
            "target_alpha_non_decreasing": candidate_alpha >= base_alpha,
        },
        "database_unchanged": after_sha == before_sha,
        "database_sha256_after": after_sha,
        "source_coverage_byte_exact": "".join(sources) == aggregate_source,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "run59-clause-paragraph-question-resegmentation-doe.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "trigger_pair": evidence["trigger_pair"],
        "source_token_counts": token_counts,
        "candidate_targets": [row["raw_rank0_target"] for row in candidate_rows],
        "accepted": accepted,
        "evidence_sha256": evidence["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
