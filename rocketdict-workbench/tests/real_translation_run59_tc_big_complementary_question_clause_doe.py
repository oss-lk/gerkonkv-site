from __future__ import annotations

"""Read-only TC-big rank0 DOE for complementary question migration.

This reuses the exact source-defined migration trigger and punctuation-first
chunk geometry proven by the baseline-OPUS DOE.  It changes only the MT backend:
the pinned TC-big runtime receives each immutable source chunk once and only raw
rank0 is evaluated.  Candidate and aggregate selectors are unchanged and strict.
The canonical run59 database remains read-only.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

import real_translation_run59_complementary_question_clause_doe as source_doe
import real_translation_run59_forward_paragraph_boundary_resegmentation_doe as shared

SCHEMA = "rocketdict-run59-tc-big-complementary-question-clause-doe/1"
BASE_DATABASE_SHA256 = source_doe.BASE_DATABASE_SHA256
BASE_RUN_ID = source_doe.BASE_RUN_ID
BASE_RUN_OUTPUT_SHA256 = source_doe.BASE_RUN_OUTPUT_SHA256
SOURCE_TEXT_SHA256 = source_doe.SOURCE_TEXT_SHA256
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 512


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


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN59_TC_BIG_COMPLEMENTARY_QUESTION_DOE_ROOT",
            "work/run59-tc-big-complementary-question-clause-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    before_sha = _sha(database)
    if before_sha != BASE_DATABASE_SHA256:
        raise RuntimeError(f"canonical database identity drift: {before_sha}")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
        context_run = get_run(connection, int(output["context_run_id"]))
        nlp_run_id = int(dict(context_run.get("output") or {})["nlp_run_id"])
        nlp_tokens = sorted(
            get_run_items(connection, nlp_run_id, kind="nlp_token"),
            key=lambda row: int(row["sequence_number"]),
        )
    if str(run.get("output_sha256") or "") != BASE_RUN_OUTPUT_SHA256:
        raise RuntimeError("run59 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    if len(rows) != 3335:
        raise RuntimeError("run59 segment census drift")
    content = str(document["content_text"])

    groups = source_doe.discover_migration_groups(content=content, rows=rows)
    if len(groups) != 1:
        raise RuntimeError(f"complementary question migration cohort drift: {len(groups)}")
    group = groups[0]
    question_chunks, segmentation = source_doe.clause_first_chunks(
        content=content,
        nlp_tokens=nlp_tokens,
        start=int(group["source_start"]),
        question_end=int(group["question_end"]),
    )
    suffix_start = int(group["question_end"])
    suffix_end = int(group["source_end"])
    suffix_tokens = source_doe._non_space_tokens(nlp_tokens, start=suffix_start, end=suffix_end)
    if not content[suffix_start:suffix_end].strip() or len(suffix_tokens) > source_doe.MAX_SUFFIX_NLP_TOKENS:
        raise RuntimeError(f"post-question suffix outside bounded envelope: {len(suffix_tokens)}")
    chunks = question_chunks + [{
        "start": suffix_start,
        "end": suffix_end,
        "text": content[suffix_start:suffix_end],
        "token_count": len(suffix_tokens),
        "boundary_reason": "paragraph_suffix",
    }]
    if "".join(str(row["text"]) for row in chunks) != str(group["source_text"]):
        raise RuntimeError("candidate source coverage drift")

    asset = load_tc_big_asset()
    translator = TcBigTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [str(row["text"]) for row in chunks],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != len(chunks) or any(len(group_) != 1 for group_ in generated):
        raise RuntimeError("TC-big clause DOE cardinality drift")

    candidates: list[dict[str, Any]] = []
    for chunk, hypotheses in zip(chunks, generated, strict=True):
        hypothesis = hypotheses[0]
        if int(hypothesis.get("rank", -1)) != 0:
            raise RuntimeError("DOE permits raw rank0 only")
        source = str(chunk["text"])
        target = str(hypothesis.get("text") or "")
        selection = shared.evaluate_candidate(source, target)
        candidates.append({
            "source_span": [int(chunk["start"]), int(chunk["end"])],
            "source_token_count": int(chunk["token_count"]),
            "boundary_reason": str(chunk["boundary_reason"]),
            "model_input": source,
            "hypothesis": dict(hypothesis),
            "raw_rank0_target": target,
            "selection": selection,
        })

    aggregate_source = "".join(str(row["text"]) for row in chunks)
    aggregate_target = "".join(str(row["raw_rank0_target"]) for row in candidates)
    aggregate_verdict = evaluate_rescue_pair(aggregate_source, aggregate_target)
    aggregate_emphasis = compare_emphasis_markup_preservation(aggregate_source, aggregate_target)
    base_alpha = sum(char.isalpha() for char in str(group["base_target"]))
    candidate_alpha = sum(char.isalpha() for char in aggregate_target)
    accepted = bool(
        all(row["selection"]["accepted"] for row in candidates)
        and aggregate_verdict.get("strictly_eligible") is True
        and aggregate_emphasis.get("passed") is True
        and candidate_alpha >= base_alpha
    )

    after_sha = _sha(database)
    if after_sha != before_sha:
        raise RuntimeError("read-only TC-big DOE mutated database")
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only pinned TC-big raw-rank0 replay of source-defined complementary-question clause geometry",
        "base_run_id": BASE_RUN_ID,
        "base_database_sha256": before_sha,
        "base_run_output_sha256": BASE_RUN_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "segment_count": len(rows),
        "discovered_context_count": len(groups),
        "context_sequence": int(group["context_sequence"]),
        "base_member_sequences": [int(row["sequence_number"]) for row in group["members"]],
        "addition_sequence": int(group["addition_sequence"]),
        "loss_sequence": int(group["loss_sequence"]),
        "segmentation_contract": {
            "minimum_chunk_nlp_tokens": source_doe.MIN_CHUNK_NLP_TOKENS,
            "preferred_chunk_nlp_tokens": source_doe.PREFERRED_CHUNK_NLP_TOKENS,
            "punctuation_priority": [";", ","],
            "corpus_sequence_whitelist": False,
            "source_offset_whitelist": False,
            "lexical_anchor_used": False,
            **segmentation,
        },
        "candidate_source_spans": [row["source_span"] for row in candidates],
        "candidate_source_token_counts": [row["source_token_count"] for row in candidates],
        "generation": {
            "implementation": "tc-big-en-ru-ct2",
            "beam_size": BEAM_SIZE,
            "num_hypotheses": NUM_HYPOTHESES,
            "max_decoding_length": MAX_DECODING_LENGTH,
            "selected_rank": 0,
        },
        "tc_big_asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
        },
        "candidate_rows": candidates,
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
        "source_coverage_byte_exact": aggregate_source == str(group["source_text"]),
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
    destination = root / "run59-tc-big-complementary-question-clause-doe.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "context_sequence": evidence["context_sequence"],
        "candidate_source_token_counts": evidence["candidate_source_token_counts"],
        "candidate_targets": [row["raw_rank0_target"] for row in candidates],
        "accepted": accepted,
        "evidence_sha256": evidence["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
