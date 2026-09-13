from __future__ import annotations

"""Read-only clause-first DOE for complementary question-mark migration.

The trigger is corpus-position independent: within one planner-v8 split context,
aggregate source and target each contain one question mark, but exactly one row
adds it early and exactly one later row loses it.  The exact source question up
to its paragraph boundary is resegmented by source punctuation only: prefer the
latest semicolon in a bounded lexical window, then the latest comma, otherwise
the maintained safe forward cut.  The remainder after the question paragraph
boundary must already fit one bounded row.  Every exact source chunk is sent to
the pinned baseline OPUS once; only raw rank0 exists.  All chunk and aggregate
selectors remain strict.  The canonical database is never mutated.
"""

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_stage import _balanced_protected_spans, _cut_inside_span

import real_translation_run59_forward_paragraph_boundary_resegmentation_doe as shared

SCHEMA = "rocketdict-run59-complementary-question-clause-doe/1"
BASE_RUN_ID = 59
BASE_DATABASE_SHA256 = "41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d"
BASE_RUN_OUTPUT_SHA256 = "5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"
MIN_CHUNK_NLP_TOKENS = 24
PREFERRED_CHUNK_NLP_TOKENS = 64
MAX_SUFFIX_NLP_TOKENS = 64
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768
_PARAGRAPH_QUESTION_RE = re.compile(r"\?[ \t]*\r?\n[ \t\r]*\n")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row.get("payload") or {})


def _planner(row: dict[str, Any]) -> dict[str, Any]:
    return dict(_payload(row).get("planner") or {})


def _context_id(row: dict[str, Any]) -> int | None:
    planner = _planner(row)
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
    except (KeyError, TypeError, ValueError):
        return None
    if (
        planner.get("planner_contract") != PLANNER_CONTRACT
        or planner.get("source") != "nlp_sentence"
        or planner.get("split") is not True
        or first != last
    ):
        return None
    return first


def _non_space_tokens(tokens: list[dict[str, Any]], *, start: int, end: int) -> list[dict[str, Any]]:
    return [
        token for token in tokens
        if int(token["source_start"]) >= start
        and int(token["source_end"]) <= end
        and not bool((_payload(token).get("flags") or {}).get("is_space"))
    ]


def _hard_clean_except_question(source: str, target: str) -> bool:
    verdict = evaluate_rescue_pair(source, target)
    return bool(
        (verdict.get("numeric_symbol") or {}).get("passed") is True
        and verdict.get("length_passed") is True
        and (verdict.get("numeric_order") or {}).get("passed") is True
        and (verdict.get("delimiter_preservation") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
    )


def discover_migration_groups(
    *, content: str, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        context = _context_id(row)
        if context is not None:
            grouped[context].append(row)
    output: list[dict[str, Any]] = []
    for context, members in sorted(grouped.items()):
        members = sorted(members, key=lambda row: int(row["source_start"]))
        if len(members) < 3:
            continue
        start = int(members[0]["source_start"])
        end = int(members[-1]["source_end"])
        if any(int(left["source_end"]) != int(right["source_start"]) for left, right in zip(members, members[1:])):
            continue
        source = "".join(str(row.get("source_text") or "") for row in members)
        target = "".join(str(row.get("target_text") or "") for row in members)
        if content[start:end] != source or source.count("?") != 1 or target.count("?") != 1:
            continue
        additions: list[int] = []
        losses: list[int] = []
        safe = True
        for row in members:
            row_source = str(row.get("source_text") or "")
            row_target = str(row.get("target_text") or "")
            if not _hard_clean_except_question(row_source, row_target):
                safe = False
                break
            delta = row_target.count("?") - row_source.count("?")
            if delta == 1:
                additions.append(int(row["sequence_number"]))
            elif delta == -1:
                losses.append(int(row["sequence_number"]))
            elif delta != 0:
                safe = False
                break
        if not safe or len(additions) != 1 or len(losses) != 1:
            continue
        loss_row = next(row for row in members if int(row["sequence_number"]) == losses[0])
        loss_source = str(loss_row.get("source_text") or "")
        paragraph_match = _PARAGRAPH_QUESTION_RE.search(loss_source)
        if paragraph_match is None:
            continue
        question_end = int(loss_row["source_start"]) + paragraph_match.end()
        if question_end <= start or question_end > end:
            continue
        output.append({
            "context_sequence": context,
            "members": members,
            "source_start": start,
            "source_end": end,
            "source_text": source,
            "base_target": target,
            "addition_sequence": additions[0],
            "loss_sequence": losses[0],
            "question_end": question_end,
        })
    return output


def _safe_cut_after_token(tokens: list[dict[str, Any]], token_index: int, *, end: int) -> int:
    next_index = token_index + 1
    return end if next_index >= len(tokens) else int(tokens[next_index]["source_start"])


def clause_first_chunks(
    *, content: str, nlp_tokens: list[dict[str, Any]], start: int, question_end: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tokens = _non_space_tokens(nlp_tokens, start=start, end=question_end)
    spans = _balanced_protected_spans(content[start:question_end], absolute_start=start)
    if not tokens:
        raise RuntimeError("question clause DOE has no NLP tokens")
    chunks: list[dict[str, Any]] = []
    cursor_index = 0
    cursor = start
    decisions: list[dict[str, Any]] = []
    while cursor_index < len(tokens):
        remaining = len(tokens) - cursor_index
        if remaining <= PREFERRED_CHUNK_NLP_TOKENS:
            split_index = len(tokens)
            cut = question_end
            reason = "final_question_tail"
        else:
            lower = cursor_index + MIN_CHUNK_NLP_TOKENS - 1
            upper = min(cursor_index + PREFERRED_CHUNK_NLP_TOKENS - 1, len(tokens) - 2)
            selected_token_index: int | None = None
            reason = ""
            for punctuation, label in ((";", "semicolon"), (",", "comma")):
                for index in range(upper, lower - 1, -1):
                    if str(tokens[index].get("source_text") or "") != punctuation:
                        continue
                    cut_candidate = _safe_cut_after_token(tokens, index, end=question_end)
                    if _cut_inside_span(cut_candidate, spans):
                        continue
                    selected_token_index = index
                    reason = label
                    break
                if selected_token_index is not None:
                    break
            if selected_token_index is None:
                split_index = min(cursor_index + PREFERRED_CHUNK_NLP_TOKENS, len(tokens))
                if split_index >= len(tokens):
                    cut = question_end
                    reason = "final_forward"
                else:
                    while split_index < len(tokens) and _cut_inside_span(int(tokens[split_index]["source_start"]), spans):
                        split_index += 1
                    if split_index >= len(tokens):
                        cut = question_end
                    else:
                        cut = int(tokens[split_index]["source_start"])
                    reason = "safe_forward_fallback"
            else:
                split_index = selected_token_index + 1
                cut = _safe_cut_after_token(tokens, selected_token_index, end=question_end)
        if split_index <= cursor_index or cut <= cursor:
            raise RuntimeError("question clause segmentation failed to advance")
        token_count = split_index - cursor_index
        chunks.append({"start": cursor, "end": cut, "text": content[cursor:cut], "token_count": token_count, "boundary_reason": reason})
        decisions.append({"token_count": token_count, "reason": reason, "end": cut})
        cursor_index = split_index
        cursor = cut
    if cursor != question_end or "".join(row["text"] for row in chunks) != content[start:question_end]:
        raise RuntimeError("question clause segmentation coverage drift")
    return chunks, {"decisions": decisions, "protected_span_count": len(spans)}


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN59_COMPLEMENTARY_QUESTION_DOE_ROOT", "work/run59-complementary-question-clause-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    before_sha = _sha(database)
    if before_sha != BASE_DATABASE_SHA256:
        raise RuntimeError("canonical database identity drift")
    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda row: int(row["sequence_number"]))
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
        context_run = get_run(connection, int(output["context_run_id"]))
        nlp_run_id = int(dict(context_run.get("output") or {})["nlp_run_id"])
        nlp_tokens = sorted(get_run_items(connection, nlp_run_id, kind="nlp_token"), key=lambda row: int(row["sequence_number"]))
    if str(run.get("output_sha256") or "") != BASE_RUN_OUTPUT_SHA256 or str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run/source identity drift")
    if len(rows) != 3335:
        raise RuntimeError("segment census drift")
    content = str(document["content_text"])

    groups = discover_migration_groups(content=content, rows=rows)
    if len(groups) != 1:
        raise RuntimeError(f"complementary question migration cohort drift: {len(groups)}")
    group = groups[0]
    question_chunks, segmentation = clause_first_chunks(content=content, nlp_tokens=nlp_tokens, start=int(group["source_start"]), question_end=int(group["question_end"]))
    suffix_start = int(group["question_end"])
    suffix_end = int(group["source_end"])
    suffix = content[suffix_start:suffix_end]
    suffix_tokens = _non_space_tokens(nlp_tokens, start=suffix_start, end=suffix_end)
    if not suffix.strip() or len(suffix_tokens) > MAX_SUFFIX_NLP_TOKENS:
        raise RuntimeError(f"post-question suffix outside bounded envelope: {len(suffix_tokens)}")
    chunks = question_chunks + [{"start": suffix_start, "end": suffix_end, "text": suffix, "token_count": len(suffix_tokens), "boundary_reason": "paragraph_suffix"}]
    if "".join(row["text"] for row in chunks) != str(group["source_text"]):
        raise RuntimeError("candidate chunks do not cover exact migration context")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate([row["text"] for row in chunks], beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
    if len(generated) != len(chunks) or any(len(group_) != 1 for group_ in generated):
        raise RuntimeError("OPUS clause DOE cardinality drift")
    candidates: list[dict[str, Any]] = []
    for chunk, hypotheses in zip(chunks, generated, strict=True):
        hypothesis = hypotheses[0]
        if int(hypothesis.get("rank", -1)) != 0:
            raise RuntimeError("raw rank0 only")
        target = str(hypothesis.get("text") or "")
        selection = shared.evaluate_candidate(str(chunk["text"]), target)
        candidates.append({"source_span": [int(chunk["start"]), int(chunk["end"])], "source_token_count": int(chunk["token_count"]), "boundary_reason": chunk["boundary_reason"], "model_input": chunk["text"], "hypothesis": dict(hypothesis), "raw_rank0_target": target, "selection": selection})

    aggregate_source = "".join(row["text"] for row in chunks)
    aggregate_target = "".join(row["raw_rank0_target"] for row in candidates)
    aggregate_verdict = evaluate_rescue_pair(aggregate_source, aggregate_target)
    aggregate_emphasis = compare_emphasis_markup_preservation(aggregate_source, aggregate_target)
    base_alpha = sum(ch.isalpha() for ch in str(group["base_target"]))
    candidate_alpha = sum(ch.isalpha() for ch in aggregate_target)
    accepted = bool(all(row["selection"]["accepted"] for row in candidates) and aggregate_verdict.get("strictly_eligible") is True and aggregate_emphasis.get("passed") is True and candidate_alpha >= base_alpha)
    after_sha = _sha(database)
    if after_sha != before_sha:
        raise RuntimeError("read-only DOE mutated database")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only source-punctuation clause segmentation for complementary question-mark migration",
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
        "question_end": int(group["question_end"]),
        "segmentation_contract": {"minimum_chunk_nlp_tokens": MIN_CHUNK_NLP_TOKENS, "preferred_chunk_nlp_tokens": PREFERRED_CHUNK_NLP_TOKENS, "punctuation_priority": [";", ","], "corpus_sequence_whitelist": False, "source_offset_whitelist": False, "lexical_anchor_used": False, **segmentation},
        "candidate_source_spans": [row["source_span"] for row in candidates],
        "candidate_source_token_counts": [row["source_token_count"] for row in candidates],
        "generation": {"implementation": "opus-en-ru-ct2", "beam_size": BEAM_SIZE, "num_hypotheses": NUM_HYPOTHESES, "max_decoding_length": MAX_DECODING_LENGTH, "selected_rank": 0},
        "candidate_rows": candidates,
        "aggregate_selection": {"accepted": accepted, "mechanical_verdict": aggregate_verdict, "emphasis_markup": aggregate_emphasis, "base_target_alpha_count": base_alpha, "candidate_target_alpha_count": candidate_alpha, "target_alpha_non_decreasing": candidate_alpha >= base_alpha},
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
    (root / "run59-complementary-question-clause-doe.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"schema": SCHEMA, "context_sequence": evidence["context_sequence"], "base_member_sequences": evidence["base_member_sequences"], "candidate_source_token_counts": evidence["candidate_source_token_counts"], "candidate_targets": [row["raw_rank0_target"] for row in candidates], "accepted": accepted, "evidence_sha256": evidence["evidence_sha256"]}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
