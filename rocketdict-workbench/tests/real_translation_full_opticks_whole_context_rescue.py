from __future__ import annotations

"""Full-Opticks feasibility audit for raw whole-Stage10-context Stage12 rescue.

This is deliberately research-only.  It starts from the persisted Product
Stage12 primary planner-v8 run produced by the full numeric-stress harness,
finds ordinary TXT contexts whose split primary translation has only isolated
missing-numeric-literal loss, and asks the pinned real OPUS model to translate
the *unchanged complete Stage10 sentence* once.

No source or target rewriting, placeholders, literal injection, glossary hints,
or database writes are allowed.  Mechanical selector success is evidence for
further semantic review, not permission to promote the strategy to Product
Mode.  Complete primary/candidate text is exported for that review.
"""

from collections import defaultdict
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import (
    RESCUE_CONTRACT,
    SELECTOR_CONTRACT,
    evaluate_candidate_context,
    evaluate_primary_context_trigger,
)
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-whole-context-rescue-feasibility/1"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
WHOLE_CONTEXT_CONTRACT = "rocketdict-stage12-whole-context-rescue-research/1"
MAX_WHOLE_CONTEXT_NLP_TOKENS = 160
BATCH_SIZE = 16
GENERATION = {"beam_size": 6, "num_hypotheses": 1}
KNOWN_LONG_CONTENT_LOSS_SEQUENCE = 669
KNOWN_LONG_CONTENT_LOSS_LITERALS = ("25", "30", "40")


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


def _context_sequence(row: dict[str, Any]) -> int | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    start = planner.get("context_sentence_start")
    end = planner.get("context_sentence_end")
    if start is None or end is None or int(start) != int(end):
        return None
    if planner.get("source") != "nlp_sentence":
        return None
    return int(start)


def _rows_cover_context(
    rows: list[dict[str, Any]], *, start: int, end: int, source: str
) -> bool:
    if not rows or end <= start or len(source) != end - start:
        return False
    cursor = start
    for row in sorted(rows, key=lambda item: int(item["source_start"])):
        row_start = int(row["source_start"])
        row_end = int(row["source_end"])
        if row_start != cursor or row_end <= row_start or row_end > end:
            return False
        if source[row_start - start : row_end - start] != str(row.get("source_text") or ""):
            return False
        cursor = row_end
    return cursor == end


def _normalized_similarity(left: str, right: str) -> float:
    left_norm = " ".join(left.split())
    right_norm = " ".join(right.split())
    return SequenceMatcher(a=left_norm, b=right_norm, autojunk=False).ratio()


def _translate_batches(
    translator: OpusTranslator,
    texts: list[str],
    *,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=GENERATION["beam_size"],
                num_hypotheses=GENERATION["num_hypotheses"],
                max_decoding_length=max_decoding_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("Whole-context feasibility translation cardinality mismatch")
    return output


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not database.is_file():
        raise RuntimeError(f"Full Opticks Product database is missing: {database}")

    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        completed = connection.execute(
            """
            SELECT id FROM stage_runs
            WHERE stage_number=12 AND implementation='opus-en-ru-ct2' AND status='completed'
            ORDER BY id DESC
            """
        ).fetchall()
        if not completed:
            raise RuntimeError("Whole-context feasibility found no completed Product Stage12 run")
        selected_run = get_run(connection, int(completed[0]["id"]))
        selected_output = dict(selected_run.get("output") or {})
        primary_run_id = int(selected_output.get("primary_translation_run_id") or 0)
        if primary_run_id <= 0:
            raise RuntimeError("Product Stage12 selected run does not expose immutable primary lineage")
        primary_run = get_run(connection, primary_run_id)
        primary_output = dict(primary_run.get("output") or {})
        if primary_output.get("planner_contract") != PLANNER_CONTRACT:
            raise RuntimeError("Whole-context feasibility primary planner contract drift")
        primary_rows = get_run_items(
            connection, primary_run_id, kind="translation_segment"
        )
        context_run_id = int(primary_output.get("context_run_id") or 0)
        if context_run_id <= 0:
            raise RuntimeError("Whole-context feasibility cannot recover Stage10 context run")
        context_items = get_run_items(
            connection, context_run_id, kind="context_sentence"
        )
        context_run = get_run(connection, context_run_id)
        context_output = dict(context_run.get("output") or {})
        document_version_id = int(context_output.get("document_version_id") or 0)
        document = get_document(connection, document_version_id)

    content = str(document["content_text"])
    if _sha_file(Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"])) != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source hash drift")
    if "".join(str(row.get("source_text") or "") for row in primary_rows) != content:
        raise RuntimeError("Primary Stage12 rows do not byte-exactly cover immutable Opticks")

    primary_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in primary_rows:
        sequence = _context_sequence(row)
        if sequence is not None:
            primary_by_context[sequence].append(row)
    for rows in primary_by_context.values():
        rows.sort(key=lambda row: int(row["source_start"]))
    context_by_sequence = {
        int(row["sequence_number"]): row for row in context_items
    }

    eligible: list[dict[str, Any]] = []
    skipped_over_cap: list[int] = []
    for sequence, rows in sorted(primary_by_context.items()):
        if len(rows) < 2:
            continue
        context = context_by_sequence.get(sequence)
        if context is None:
            raise RuntimeError(f"Whole-context feasibility lost Stage10 context {sequence}")
        start = int(context["source_start"])
        end = int(context["source_end"])
        source = str(context["source_text"])
        if content[start:end] != source:
            raise RuntimeError("Stage10 context differs from immutable source bytes")
        if not _rows_cover_context(rows, start=start, end=end, source=source):
            continue
        trigger = evaluate_primary_context_trigger(rows)
        if trigger.get("eligible") is not True:
            continue
        context_payload = dict(context.get("payload") or {})
        token_count = int(context_payload.get("token_count") or 0)
        if token_count <= 0:
            raise RuntimeError(f"Stage10 context {sequence} lacks NLP token count")
        if token_count > MAX_WHOLE_CONTEXT_NLP_TOKENS:
            skipped_over_cap.append(sequence)
            continue
        eligible.append(
            {
                "context_sequence": sequence,
                "source_start": start,
                "source_end": end,
                "source_text": source,
                "nlp_token_count": token_count,
                "primary_rows": rows,
                "trigger": trigger,
            }
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    max_tokens = max((int(row["nlp_token_count"]) for row in eligible), default=0)
    max_decoding_length = max(128, max_tokens * 8)
    generated = _translate_batches(
        translator,
        [str(row["source_text"]) for row in eligible],
        max_decoding_length=max_decoding_length,
    ) if eligible else []

    candidates: list[dict[str, Any]] = []
    accepted_sequences: list[int] = []
    for attempt, hypotheses in zip(eligible, generated, strict=True):
        if not hypotheses:
            raise RuntimeError(
                f"Whole-context OPUS returned no hypothesis for {attempt['context_sequence']}"
            )
        target = str(hypotheses[0].get("text") or "")
        if not target.strip():
            raise RuntimeError(
                f"Whole-context OPUS returned empty rank-0 target for {attempt['context_sequence']}"
            )
        candidate_row = {
            "source_text": str(attempt["source_text"]),
            "target_text": target,
        }
        selection = evaluate_candidate_context(
            list(attempt["primary_rows"]), [candidate_row]
        )
        primary_target = "".join(
            str(row.get("target_text") or "") for row in attempt["primary_rows"]
        )
        sequence = int(attempt["context_sequence"])
        if selection.get("accepted") is True:
            accepted_sequences.append(sequence)
        candidates.append(
            {
                "context_sequence": sequence,
                "source_start": int(attempt["source_start"]),
                "source_end": int(attempt["source_end"]),
                "nlp_token_count": int(attempt["nlp_token_count"]),
                "trigger": attempt["trigger"],
                "source_text": str(attempt["source_text"]),
                "primary_rows": [
                    {
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                    }
                    for row in attempt["primary_rows"]
                ],
                "primary_target_concatenated": primary_target,
                "whole_context_rank0_target": target,
                "whole_context_rank0_score": hypotheses[0].get("score"),
                "target_similarity_to_primary": _normalized_similarity(primary_target, target),
                "selection": selection,
                "source_bytes_rewritten": False,
                "target_rewriting": False,
                "placeholders": False,
                "post_translation_literal_injection": False,
            }
        )

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Whole-context feasibility mutated the persisted Product database")

    known = next(
        (row for row in candidates if row["context_sequence"] == KNOWN_LONG_CONTENT_LOSS_SEQUENCE),
        None,
    )
    if known is None:
        raise RuntimeError(
            "Pinned Opticks whole-context feasibility lost the known long-unit content-loss context"
        )
    if known["selection"].get("accepted") is not True:
        raise RuntimeError("Known long-unit whole-context candidate is no longer strict-clean")
    known_target = str(known["whole_context_rank0_target"])
    if any(literal not in known_target for literal in KNOWN_LONG_CONTENT_LOSS_LITERALS):
        raise RuntimeError("Known long-unit whole-context candidate lost 25/30/40")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "research-only full-corpus feasibility of translating an eligible split Stage10 sentence as one unchanged real-OPUS request",
        "promotion_allowed": False,
        "semantic_review_required_before_promotion": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "document_version_id": document_version_id,
        "selected_translation_run_id": int(selected_run["id"]),
        "selected_translation_output_sha256": str(selected_run.get("output_sha256") or ""),
        "primary_translation_run_id": primary_run_id,
        "primary_translation_output_sha256": str(primary_run.get("output_sha256") or ""),
        "primary_planner_contract": PLANNER_CONTRACT,
        "primary_rescue_contract": RESCUE_CONTRACT,
        "primary_selector_contract": SELECTOR_CONTRACT,
        "whole_context_contract": WHOLE_CONTEXT_CONTRACT,
        "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        "generation": dict(GENERATION),
        "max_decoding_length": max_decoding_length,
        "eligible_context_count": len(eligible),
        "eligible_context_sequences": [int(row["context_sequence"]) for row in eligible],
        "skipped_over_cap_context_count": len(skipped_over_cap),
        "skipped_over_cap_context_sequences": skipped_over_cap,
        "mechanically_accepted_context_count": len(accepted_sequences),
        "mechanically_accepted_context_sequences": accepted_sequences,
        "known_long_content_loss_context_sequence": KNOWN_LONG_CONTENT_LOSS_SEQUENCE,
        "known_long_content_loss_strict_clean": known["selection"].get("accepted") is True,
        "known_long_content_loss_literals_preserved": True,
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "candidates": candidates,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-whole-context-rescue-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "eligible_context_count": payload["eligible_context_count"],
                "eligible_context_sequences": payload["eligible_context_sequences"],
                "mechanically_accepted_context_count": payload["mechanically_accepted_context_count"],
                "mechanically_accepted_context_sequences": payload["mechanically_accepted_context_sequences"],
                "known_long_content_loss_strict_clean": payload["known_long_content_loss_strict_clean"],
                "database_mutated": payload["database_mutated"],
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
