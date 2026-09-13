from __future__ import annotations

"""Read-only TC-big rank0 DOE for a bounded row-local parenthetical class.

The trigger is corpus-independent and source/geometry-defined.  It considers
only current translation rows that already fail punctuation, contain one or two
balanced non-nested source parenthetical pairs with short payloads, have only a
loss/imbalance of round parentheses in the current target, and are otherwise
clean under the maintained research checks.  Source size is conservatively
bounded.

The exact immutable row source is passed unchanged to pinned TC-big and only its
unique raw rank0 output is evaluated.  No candidate is persisted and no Product
promotion is authorized by this script.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run56-tc-big-parenthetical-row-doe/1"
BASE_DATABASE_SHA256 = "cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56"
BASE_RUN_ID = 56
BASE_OUTPUT_SHA256 = "2971fb099674aa81c14e0b75590c5fbcb943d1ea3477efb0ceedbd81bd69fbc5"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SEGMENT_COUNT = 3335
EXPECTED_PUNCTUATION_FAILURE_COUNT = 14
MIN_PARENTHESES_PAIRS = 1
MAX_PARENTHESES_PAIRS = 2
MAX_PARENTHESES_ALPHA_WORDS = 12
MAX_SOURCE_ALPHA_WORDS = 64
MAX_SOURCE_CHARS = 384
MIN_SOURCE_ALPHA_RATIO = 0.80
MAX_SOURCE_ALPHA_RATIO = 1.40
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768
HARD_PUNCTUATION = "()[]{}?!"
OTHER_HARD_PUNCTUATION = "[]{}?!"
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
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _alpha_count(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _alpha_word_count(text: str) -> int:
    return len(_ALPHA_WORD_RE.findall(text))


def _punctuation_counts(text: str) -> dict[str, int]:
    return {symbol: text.count(symbol) for symbol in HARD_PUNCTUATION}


def _parenthetical_payloads(source: str) -> list[str] | None:
    if source.count("(") != source.count(")"):
        return None
    pair_count = source.count("(")
    if not (MIN_PARENTHESES_PAIRS <= pair_count <= MAX_PARENTHESES_PAIRS):
        return None
    payloads = _PARENTHETICAL_RE.findall(source)
    if len(payloads) != pair_count:
        return None
    counts = [_alpha_word_count(payload) for payload in payloads]
    if any(not (1 <= count <= MAX_PARENTHESES_ALPHA_WORDS) for count in counts):
        return None
    return payloads


def _base_clean_except_round(source: str, target: str) -> tuple[bool, dict[str, Any]]:
    verdict = evaluate_rescue_pair(source, target)
    other_punctuation_exact = all(
        source.count(symbol) == target.count(symbol)
        for symbol in OTHER_HARD_PUNCTUATION
    )
    clean = bool(
        (verdict.get("numeric_symbol") or {}).get("passed") is True
        and verdict.get("length_passed") is True
        and (verdict.get("numeric_order") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and (verdict.get("output_artifacts") or {}).get("passed") is True
        and other_punctuation_exact
    )
    return clean, verdict


def _trigger(source: str, target: str) -> dict[str, Any]:
    payloads = _parenthetical_payloads(source)
    source_open = source.count("(")
    source_close = source.count(")")
    target_open = target.count("(")
    target_close = target.count(")")
    round_mismatch = (source_open, source_close) != (target_open, target_close)
    round_loss_only = bool(
        target_open <= source_open
        and target_close <= source_close
        and round_mismatch
    )
    source_words = _alpha_word_count(source)
    source_chars = len(source)
    base_clean, base_verdict = _base_clean_except_round(source, target)
    eligible = bool(
        payloads is not None
        and 0 < source_words <= MAX_SOURCE_ALPHA_WORDS
        and 0 < source_chars <= MAX_SOURCE_CHARS
        and round_loss_only
        and base_clean
        and base_verdict.get("punctuation_passed") is not True
    )
    return {
        "eligible": eligible,
        "source_parenthetical_payloads": payloads,
        "source_parenthetical_pair_count": None if payloads is None else len(payloads),
        "source_parenthetical_alpha_word_counts": [] if payloads is None else [_alpha_word_count(value) for value in payloads],
        "source_round_parentheses": [source_open, source_close],
        "target_round_parentheses": [target_open, target_close],
        "round_parenthesis_loss_only": round_loss_only,
        "source_alpha_word_count": source_words,
        "source_alpha_word_cap": MAX_SOURCE_ALPHA_WORDS,
        "source_char_count": source_chars,
        "source_char_cap": MAX_SOURCE_CHARS,
        "base_clean_except_round_parentheses": base_clean,
        "base_verdict": base_verdict,
    }


def _candidate(source: str, target: str, *, base_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_punctuation = _punctuation_counts(source)
    target_punctuation = _punctuation_counts(target)
    punctuation_exact = source_punctuation == target_punctuation
    source_alpha = _alpha_count(source)
    target_alpha = _alpha_count(target)
    base_alpha = _alpha_count(base_target)
    ratio = target_alpha / source_alpha if source_alpha else 1.0
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    base_alpha_retained = target_alpha >= base_alpha
    accepted = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and punctuation_exact
        and ratio_passed
        and base_alpha_retained
    )
    return {
        "accepted": accepted,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_hard_punctuation": source_punctuation,
        "target_hard_punctuation": target_punctuation,
        "hard_punctuation_exact": punctuation_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "base_alpha_count": base_alpha,
        "candidate_alpha_count": target_alpha,
        "base_alpha_retained": base_alpha_retained,
    }


def _rank0_batch(translator: TcBigTranslator, sources: list[str]) -> list[dict[str, Any]]:
    generated = translator.translate(
        sources,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != len(sources):
        raise RuntimeError("parenthetical row DOE model batch cardinality drift")
    result: list[dict[str, Any]] = []
    for source, hypotheses in zip(sources, generated, strict=True):
        if len(hypotheses) != 1:
            raise RuntimeError(f"parenthetical row DOE hypothesis cardinality drift for {source[:80]!r}")
        hypothesis = dict(hypotheses[0])
        if int(hypothesis.get("rank", -1)) != 0:
            raise RuntimeError("parenthetical row DOE received non-rank0 hypothesis")
        target = str(hypothesis.get("text") or "")
        if not target.strip():
            raise RuntimeError("parenthetical row DOE received empty rank0 target")
        result.append({"rank": 0, "text": target, "score": hypothesis.get("score")})
    return result


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN56_PARENTHESES_ROW_DOE_ROOT",
            "work/run56-tc-big-parenthetical-row-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(
        os.environ.get(
            "ROCKETDICT_RUN56_PARENTHESES_ROW_DOE_DB",
            root / "rocketdict.sqlite",
        )
    ).resolve()
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("parenthetical row DOE requires exact run56 database")
    database_sha_before = _sha(database)

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        run_output = dict(run.get("output") or {})
        document = get_document(connection, int(run_output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("parenthetical row DOE run56 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("parenthetical row DOE source identity drift")
    if len(rows) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError("parenthetical row DOE segment-count drift")

    content = str(document["content_text"])
    cursor = 0
    punctuation_failures: list[int] = []
    attempts: list[dict[str, Any]] = []
    for expected_sequence, row in enumerate(rows):
        sequence = int(row["sequence_number"])
        if sequence != expected_sequence:
            raise RuntimeError("parenthetical row DOE translation sequence drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"parenthetical row DOE source coverage drift at {sequence}")
        cursor = end
        verdict = evaluate_rescue_pair(source, target)
        if verdict.get("punctuation_passed") is not True:
            punctuation_failures.append(sequence)
            trigger = _trigger(source, target)
            if trigger["eligible"] is True:
                attempts.append(
                    {
                        "row": row,
                        "source_text": source,
                        "base_target": target,
                        "trigger": trigger,
                    }
                )
    if cursor != len(content):
        raise RuntimeError("parenthetical row DOE incomplete source coverage")
    if len(punctuation_failures) != EXPECTED_PUNCTUATION_FAILURE_COUNT:
        raise RuntimeError("parenthetical row DOE punctuation cohort drift")

    sources = [str(attempt["source_text"]) for attempt in attempts]
    raw_rank0 = _rank0_batch(
        TcBigTranslator(device="cpu", compute_type="float32"), sources
    )
    cases: list[dict[str, Any]] = []
    for attempt, raw in zip(attempts, raw_rank0, strict=True):
        row = attempt["row"]
        source = str(attempt["source_text"])
        target = str(raw["text"])
        cases.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "base_target": str(attempt["base_target"]),
                "trigger": attempt["trigger"],
                "model": "tc_big",
                "model_input": source,
                "model_input_equals_source": True,
                "raw_rank": 0,
                "raw_score": raw.get("score"),
                "raw_target": target,
                "selection": _candidate(
                    source,
                    target,
                    base_target=str(attempt["base_target"]),
                ),
            }
        )

    if _sha(database) != database_sha_before:
        raise RuntimeError("read-only parenthetical row DOE mutated run56 database")

    accepted = [
        case["sequence_number"]
        for case in cases
        if case["selection"]["accepted"] is True
    ]
    rejected = [
        case["sequence_number"]
        for case in cases
        if case["selection"]["accepted"] is not True
    ]
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only source-defined TC-big raw-rank0 DOE for bounded row-local parenthetical punctuation loss",
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "translation_segment_count": len(rows),
        "punctuation_failure_count": len(punctuation_failures),
        "punctuation_failure_sequences": punctuation_failures,
        "trigger_attempt_count": len(cases),
        "trigger_attempt_sequences": [case["sequence_number"] for case in cases],
        "accepted_count": len(accepted),
        "accepted_sequences": accepted,
        "rejected_sequences": rejected,
        "trigger_contract": {
            "parentheses_pair_range": [MIN_PARENTHESES_PAIRS, MAX_PARENTHESES_PAIRS],
            "max_parenthetical_alpha_words": MAX_PARENTHESES_ALPHA_WORDS,
            "max_source_alpha_words": MAX_SOURCE_ALPHA_WORDS,
            "max_source_chars": MAX_SOURCE_CHARS,
            "round_parenthesis_loss_only": True,
            "other_hard_punctuation_exact": True,
            "base_research_clean_except_round_parentheses": True,
        },
        "selector_contract": {
            "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
            "strictly_eligible": True,
            "emphasis_markup_preserved": True,
            "hard_punctuation_exact": True,
            "base_alpha_retained": True,
        },
        "cases": cases,
        "database_unchanged": True,
        "source_coverage_byte_exact": True,
        "model_input_equals_immutable_source": True,
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
    path = root / "run56-tc-big-parenthetical-row-doe.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "trigger_attempt_sequences": evidence["trigger_attempt_sequences"],
        "accepted_sequences": accepted,
        "rejected_sequences": rejected,
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
