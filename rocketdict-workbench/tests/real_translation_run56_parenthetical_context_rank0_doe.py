from __future__ import annotations

"""Read-only whole-context DOE for bounded run56 parenthetical mismatches.

The maintained parenthetical rescue intentionally covers one lost short pair.
Run56 exposes a different source-defined family: a complete Stage10 context is
split into multiple current Stage12 rows, has one to three balanced short
parenthetical payloads, stays within the proven 160-token research cap, and the
aggregate current target has a round-parenthesis count mismatch while unrelated
hard checks remain clean.

This experiment retranslates only the exact immutable complete context with raw
rank0 from pinned OPUS and pinned TC-big.  It is discovery evidence only: no
candidate is persisted and no automatic Product promotion is authorized.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run56-bounded-parenthetical-context-rank0-doe/1"
BASE_DATABASE_SHA256 = "cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56"
BASE_RUN_ID = 56
BASE_OUTPUT_SHA256 = "2971fb099674aa81c14e0b75590c5fbcb943d1ea3477efb0ceedbd81bd69fbc5"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
MAX_CONTEXT_NLP_TOKENS = 160
MAX_PARENTHESES_PAIRS = 3
MAX_PARENTHESES_ALPHA_WORDS = 8
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1536
HARD_PUNCTUATION = "()[]{}?!"
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_PARENTHETICAL_RE = re.compile(r"\(([^()]*)\)")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row.get("payload") or {})


def _planner(row: dict[str, Any]) -> dict[str, Any]:
    return dict(_payload(row).get("planner") or {})


def _context_token_count(context: dict[str, Any]) -> int:
    payload = _payload(context)
    try:
        value = int(payload.get("token_count") or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _alpha(text: str) -> int:
    return sum(character.isalpha() for character in text)


def _punctuation_counts(text: str) -> dict[str, int]:
    return {symbol: text.count(symbol) for symbol in HARD_PUNCTUATION}


def _parenthetical_payloads(source: str) -> list[str] | None:
    if source.count("(") != source.count(")"):
        return None
    pair_count = source.count("(")
    if not (1 <= pair_count <= MAX_PARENTHESES_PAIRS):
        return None
    payloads = _PARENTHETICAL_RE.findall(source)
    if len(payloads) != pair_count:
        return None
    if any(not (1 <= len(_ALPHA_WORD_RE.findall(payload)) <= MAX_PARENTHESES_ALPHA_WORDS) for payload in payloads):
        return None
    return payloads


def _aggregate_research_clean_except_round(source: str, target: str) -> tuple[bool, dict[str, Any]]:
    verdict = evaluate_rescue_pair(source, target)
    other_exact = all(source.count(symbol) == target.count(symbol) for symbol in "[]{}?!")
    clean = bool(
        (verdict.get("numeric_symbol") or {}).get("passed") is True
        and verdict.get("length_passed") is True
        and (verdict.get("numeric_order") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and (verdict.get("output_artifacts") or {}).get("passed") is True
        and other_exact
    )
    return clean, verdict


def _rank0_batch(translator: Any, sources: list[str]) -> list[dict[str, Any]]:
    generated = translator.translate(
        sources,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != len(sources):
        raise RuntimeError("parenthetical DOE model batch cardinality drift")
    output: list[dict[str, Any]] = []
    for source, hypotheses in zip(sources, generated, strict=True):
        if len(hypotheses) != 1 or int(hypotheses[0].get("rank", -1)) != 0:
            raise RuntimeError(f"parenthetical DOE rank0 cardinality drift for {source[:80]!r}")
        target = str(hypotheses[0].get("text") or "")
        if not target.strip():
            raise RuntimeError("parenthetical DOE empty rank0 target")
        output.append({"rank": 0, "text": target, "score": hypotheses[0].get("score")})
    return output


def _candidate(source: str, target: str, *, primary_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_counts = _punctuation_counts(source)
    target_counts = _punctuation_counts(target)
    hard_punctuation_exact = source_counts == target_counts
    ratio = _alpha(target) / _alpha(source) if _alpha(source) else 1.0
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    alpha_retained = _alpha(target) >= _alpha(primary_target)
    accepted = bool(
        verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and hard_punctuation_exact
        and ratio_passed
        and alpha_retained
    )
    return {
        "screening_passed": accepted,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_hard_punctuation": source_counts,
        "target_hard_punctuation": target_counts,
        "hard_punctuation_exact": hard_punctuation_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "primary_alpha_count": _alpha(primary_target),
        "candidate_alpha_count": _alpha(target),
        "primary_alpha_retained": alpha_retained,
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN56_PARENTHETICAL_DOE_ROOT", "work/run56-parenthetical-context-rank0-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(os.environ.get("ROCKETDICT_RUN56_PARENTHETICAL_DOE_DB", root / "rocketdict.sqlite")).resolve()
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("parenthetical DOE requires exact run56 database")
    database_sha_before = _sha(database)

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        base_rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda row: int(row["source_start"]))
        run_output = dict(run.get("output") or {})
        contexts = sorted(get_run_items(connection, int(run_output["context_run_id"]), kind="context_sentence"), key=lambda row: int(row["sequence_number"]))
        document = get_document(connection, int(run_output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("parenthetical DOE run56 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("parenthetical DOE source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("parenthetical DOE run56 source coverage drift")

    by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in base_rows:
        planner = _planner(row)
        try:
            first = int(planner["context_sentence_start"])
            last = int(planner["context_sentence_end"])
        except (KeyError, TypeError, ValueError):
            continue
        if first == last and bool(planner.get("split")):
            by_context[first].append(row)

    attempts: list[dict[str, Any]] = []
    for context in contexts:
        sequence = int(context["sequence_number"])
        members = sorted(by_context.get(sequence, []), key=lambda row: int(row["source_start"]))
        if len(members) < 2:
            continue
        source = str(context.get("source_text") or "")
        start = int(context["source_start"])
        end = int(context["source_end"])
        if content[start:end] != source:
            raise RuntimeError(f"parenthetical DOE context source drift at {sequence}")
        if "".join(str(row.get("source_text") or "") for row in members) != source:
            raise RuntimeError(f"parenthetical DOE member coverage drift at {sequence}")
        token_count = _context_token_count(context)
        if not (0 < token_count <= MAX_CONTEXT_NLP_TOKENS):
            continue
        payloads = _parenthetical_payloads(source)
        if payloads is None:
            continue
        primary_target = "".join(str(row.get("target_text") or "") for row in members)
        source_round = [source.count("("), source.count(")")]
        target_round = [primary_target.count("("), primary_target.count(")")]
        if source_round == target_round:
            continue
        aggregate_clean, base_verdict = _aggregate_research_clean_except_round(source, primary_target)
        if not aggregate_clean:
            continue
        member_punctuation_failures = []
        for row in members:
            verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
            if verdict.get("punctuation_passed") is not True:
                member_punctuation_failures.append(int(row["sequence_number"]))
        if not member_punctuation_failures:
            continue
        attempts.append(
            {
                "context": context,
                "members": members,
                "source_text": source,
                "primary_target": primary_target,
                "source_round_parentheses": source_round,
                "target_round_parentheses": target_round,
                "parenthetical_payloads": payloads,
                "parenthetical_alpha_word_counts": [len(_ALPHA_WORD_RE.findall(payload)) for payload in payloads],
                "token_count": token_count,
                "member_punctuation_failures": member_punctuation_failures,
                "base_aggregate_verdict": base_verdict,
            }
        )

    sources = [str(attempt["source_text"]) for attempt in attempts]
    opus_rank0 = _rank0_batch(OpusTranslator(device="cpu", compute_type="float32"), sources)
    tc_rank0 = _rank0_batch(TcBigTranslator(device="cpu", compute_type="float32"), sources)
    cases: list[dict[str, Any]] = []
    for attempt, opus_raw, tc_raw in zip(attempts, opus_rank0, tc_rank0, strict=True):
        source = str(attempt["source_text"])
        primary_target = str(attempt["primary_target"])
        model_results: dict[str, Any] = {}
        for model, raw in (("opus", opus_raw), ("tc_big", tc_raw)):
            target = str(raw["text"])
            model_results[model] = {
                "model": model,
                "raw_rank": 0,
                "raw_score": raw.get("score"),
                "raw_target": target,
                **_candidate(source, target, primary_target=primary_target),
            }
        context = attempt["context"]
        cases.append(
            {
                "context_sequence": int(context["sequence_number"]),
                "source_start": int(context["source_start"]),
                "source_end": int(context["source_end"]),
                "source_text": source,
                "primary_target": primary_target,
                "source_round_parentheses": attempt["source_round_parentheses"],
                "target_round_parentheses": attempt["target_round_parentheses"],
                "parenthetical_payloads": attempt["parenthetical_payloads"],
                "parenthetical_alpha_word_counts": attempt["parenthetical_alpha_word_counts"],
                "context_nlp_token_count": attempt["token_count"],
                "member_sequences": [int(row["sequence_number"]) for row in attempt["members"]],
                "member_punctuation_failure_sequences": attempt["member_punctuation_failures"],
                "base_aggregate_verdict": attempt["base_aggregate_verdict"],
                "opus": model_results["opus"],
                "tc_big": model_results["tc_big"],
                "screening_passing_models": [
                    model for model in ("opus", "tc_big") if model_results[model]["screening_passed"] is True
                ],
            }
        )

    if _sha(database) != database_sha_before:
        raise RuntimeError("read-only parenthetical DOE mutated run56 database")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only whole-context rank0 DOE for bounded split parenthetical mismatch geometries not covered by the maintained single-pair trigger",
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "max_context_nlp_tokens": MAX_CONTEXT_NLP_TOKENS,
        "max_parentheses_pairs": MAX_PARENTHESES_PAIRS,
        "max_parentheses_alpha_words": MAX_PARENTHESES_ALPHA_WORDS,
        "case_count": len(cases),
        "cases": cases,
        "passing_contexts": {
            model: [case["context_sequence"] for case in cases if case[model]["screening_passed"] is True]
            for model in ("opus", "tc_big")
        },
        "database_unchanged": True,
        "source_coverage_byte_exact": True,
        "raw_rank0_only": True,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "run56-bounded-parenthetical-context-rank0-doe.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "case_count": len(cases),
        "case_context_sequences": [case["context_sequence"] for case in cases],
        "passing_contexts": evidence["passing_contexts"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
