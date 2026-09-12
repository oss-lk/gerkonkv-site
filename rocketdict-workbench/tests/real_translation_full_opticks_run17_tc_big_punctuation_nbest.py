from __future__ import annotations

"""Read-only TC-big n-best DOE for every persisted run-17 punctuation failure.

The experiment is intentionally broader than any Product selector and narrower than a
fallback policy: it only examines rows that already fail the maintained punctuation
hard gate in the exact persisted run-17 database. It records unmodified raw TC-big
beam hypotheses and mechanical/markup diagnostics. It never mutates the database,
rewrites source/target text, injects punctuation, or grants promotion authority.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset, tc_big_status
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run17-tc-big-punctuation-nbest/1"
RUN17_DATABASE_SHA256 = "2cbf20b39168003e494b2fb73c9b9baea427283def04a076a673e5023d7346a4"
RUN17_TRANSLATION_RUN_ID = 17
RUN17_OUTPUT_SHA256 = "f7c04209d9e8d7ffab673a2987b0024c334f24fee59736466597ea99125f7ff1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
RUN17_COUNTS = {"numeric_symbol": 20, "punctuation": 17, "length": 0, "unique": 36}
RUN17_SEGMENTS = 3343
EXPECTED_PUNCTUATION_STARTS = [
    54796, 112541, 132378, 255270, 255847, 301051, 372983, 417917, 458250,
    477054, 480217, 528789, 530302, 531604, 545451, 569170, 581821,
]
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1024


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


def _coverage(rows: list[dict[str, Any]], content: str) -> None:
    cursor = 0
    for sequence, row in enumerate(_ordered(rows)):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError("run17 sequence drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError(f"run17 source coverage drift at sequence {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError(f"run17 source coverage incomplete: {cursor} != {len(content)}")


def _hard_flags(source: str, target: str) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(source, target)
    return {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = {"numeric_symbol": [], "punctuation": [], "length": []}
    union: set[int] = set()
    for row in _ordered(rows):
        sequence = int(row["sequence_number"])
        flags = _hard_flags(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )
        for key, failed in flags.items():
            if failed:
                failures[key].append(sequence)
                union.add(sequence)
    return {
        "counts": {
            "numeric_symbol": len(failures["numeric_symbol"]),
            "punctuation": len(failures["punctuation"]),
            "length": len(failures["length"]),
            "unique": len(union),
        },
        "failures": failures,
    }


def _punctuation_counts(text: str) -> dict[str, int]:
    return {symbol: text.count(symbol) for symbol in "()[]{}?!"}


def _family(source: str, target: str) -> str:
    src = _punctuation_counts(source)
    tgt = _punctuation_counts(target)
    bracket = any(src[ch] != tgt[ch] for ch in "[]")
    paren = any(src[ch] != tgt[ch] for ch in "()")
    question = src["?"] != tgt["?"]
    exclamation = src["!"] != tgt["!"]
    curly = any(src[ch] != tgt[ch] for ch in "{}")
    active = sum((bracket, paren, question, exclamation, curly))
    if active != 1:
        return "mixed_punctuation"
    if bracket:
        if src["["] >= tgt["["] and src["]"] >= tgt["]"]:
            return "square_bracket_loss"
        return "square_bracket_addition_or_mixed"
    if paren:
        source_total = src["("] + src[")"]
        target_total = tgt["("] + tgt[")"]
        if source_total > target_total:
            return "parenthesis_loss"
        if target_total > source_total:
            return "parenthesis_addition"
        return "parenthesis_rebalance"
    if question:
        return "question_loss" if src["?"] > tgt["?"] else "question_addition"
    if exclamation:
        return "exclamation_loss" if src["!"] > tgt["!"] else "exclamation_addition"
    return "curly_brace_mismatch"


def _alpha_profile(source: str, target: str) -> dict[str, Any]:
    source_alpha = sum(ch.isalpha() for ch in source)
    target_alpha = sum(ch.isalpha() for ch in target)
    target_cyrillic = sum(
        ch.isalpha() and ("а" <= ch.casefold() <= "я" or ch.casefold() == "ё")
        for ch in target
    )
    return {
        "source_alpha": source_alpha,
        "target_alpha": target_alpha,
        "target_to_source_alpha_ratio": (target_alpha / source_alpha) if source_alpha else None,
        "target_cyrillic_alpha_ratio": (target_cyrillic / target_alpha) if target_alpha else 0.0,
    }


def _candidate(source: str, target: str, *, rank: int, score: Any) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    mechanically_admissible = (
        verdict.get("strictly_eligible") is True and emphasis.get("passed") is True
    )
    return {
        "rank": rank,
        "target_text": target,
        "score": score,
        "mechanically_admissible": mechanically_admissible,
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "strict_research_passed": verdict.get("strict_research_passed") is True,
        "punctuation_passed": verdict.get("punctuation_passed") is True,
        "numeric_symbol_passed": (verdict.get("numeric_symbol") or {}).get("passed") is True,
        "length_passed": verdict.get("length_passed") is True,
        "emphasis_markup": emphasis,
        "alpha_profile": _alpha_profile(source, target),
        "verdict": verdict,
    }


def _counterfactual(rows: list[dict[str, Any]], replacements: dict[int, str]) -> dict[str, Any]:
    changed: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        replacement = replacements.get(int(row["source_start"]))
        if replacement is not None:
            copy["target_text"] = replacement
        changed.append(copy)
    inventory = _inventory(changed)
    return {
        "replacement_count": len(replacements),
        "hard_gate_counts": inventory["counts"],
        "failure_sequences": inventory["failures"],
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN17_PUNCTUATION_DOE_ROOT",
            "work/run17-tc-big-punctuation-nbest",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != RUN17_DATABASE_SHA256:
        raise RuntimeError("DOE requires the exact persisted run17 database")

    database_sha_before = _sha(database)
    asset = load_tc_big_asset()
    runtime = tc_big_status()
    if runtime.get("available") is not True:
        raise RuntimeError(f"TC-big runtime unavailable: {runtime!r}")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, RUN17_TRANSLATION_RUN_ID)
        rows = _ordered(
            get_run_items(connection, RUN17_TRANSLATION_RUN_ID, kind="translation_segment")
        )
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))

    if (
        int(run.get("stage_number") or -1) != 12
        or str(run.get("output_sha256") or "") != RUN17_OUTPUT_SHA256
    ):
        raise RuntimeError("run17 translation identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run17 source identity drift")
    content = str(document["content_text"])
    _coverage(rows, content)
    baseline_inventory = _inventory(rows)
    if len(rows) != RUN17_SEGMENTS or baseline_inventory["counts"] != RUN17_COUNTS:
        raise RuntimeError(
            f"run17 baseline drift: rows={len(rows)}, counts={baseline_inventory['counts']!r}"
        )

    cohort = [
        row
        for row in rows
        if _hard_flags(
            str(row.get("source_text") or ""), str(row.get("target_text") or "")
        )["punctuation"]
    ]
    starts = [int(row["source_start"]) for row in cohort]
    if starts != EXPECTED_PUNCTUATION_STARTS:
        raise RuntimeError(f"run17 punctuation cohort drift: {starts!r}")

    translator = TcBigTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [str(row.get("source_text") or "") for row in cohort],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != len(cohort) or any(
        len(group) != NUM_HYPOTHESES for group in generated
    ):
        raise RuntimeError("TC-big punctuation DOE hypothesis cardinality drift")

    cases: list[dict[str, Any]] = []
    rank0_replacements: dict[int, str] = {}
    any_nbest_replacements: dict[int, str] = {}
    family_counts: Counter[str] = Counter()
    rank0_family_counts: Counter[str] = Counter()
    any_family_counts: Counter[str] = Counter()

    for row, hypotheses in zip(cohort, generated, strict=True):
        source = str(row.get("source_text") or "")
        base_target = str(row.get("target_text") or "")
        family = _family(source, base_target)
        family_counts[family] += 1
        candidates = [
            _candidate(
                source,
                str(hypothesis.get("text") or ""),
                rank=rank,
                score=hypothesis.get("score"),
            )
            for rank, hypothesis in enumerate(hypotheses)
        ]
        admissible_ranks = [
            int(candidate["rank"])
            for candidate in candidates
            if candidate["mechanically_admissible"]
        ]
        first = admissible_ranks[0] if admissible_ranks else None
        if candidates[0]["mechanically_admissible"]:
            rank0_replacements[int(row["source_start"])] = str(candidates[0]["target_text"])
            rank0_family_counts[family] += 1
        if first is not None:
            any_nbest_replacements[int(row["source_start"])] = str(
                candidates[first]["target_text"]
            )
            any_family_counts[family] += 1
        cases.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "family": family,
                "source_text": source,
                "base_target_text": base_target,
                "source_punctuation_counts": _punctuation_counts(source),
                "base_target_punctuation_counts": _punctuation_counts(base_target),
                "base_verdict": evaluate_rescue_pair(source, base_target),
                "base_emphasis_markup": compare_emphasis_markup_preservation(
                    source, base_target
                ),
                "candidates": candidates,
                "rank0_mechanically_admissible": bool(
                    candidates[0]["mechanically_admissible"]
                ),
                "admissible_ranks": admissible_ranks,
                "first_mechanically_admissible_rank": first,
                "first_mechanically_admissible_target": (
                    None if first is None else candidates[first]["target_text"]
                ),
                "semantic_review_required": bool(admissible_ranks),
            }
        )

    rank0_counterfactual = _counterfactual(rows, rank0_replacements)
    any_counterfactual = _counterfactual(rows, any_nbest_replacements)
    for label, counterfactual in (
        ("rank0", rank0_counterfactual),
        ("any_nbest", any_counterfactual),
    ):
        counts = dict(counterfactual["hard_gate_counts"])
        if any(
            int(counts[key]) > RUN17_COUNTS[key]
            for key in ("numeric_symbol", "punctuation", "length", "unique")
        ):
            raise RuntimeError(
                f"{label} TC-big counterfactual regresses hard-gate counts: {counts!r}"
            )

    if _sha(database) != database_sha_before:
        raise RuntimeError("TC-big punctuation DOE mutated run17 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only raw TC-big beam screening of every exact run17 punctuation hard failure",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": RUN17_DATABASE_SHA256,
        "base_translation_run_id": RUN17_TRANSLATION_RUN_ID,
        "base_translation_output_sha256": RUN17_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_character_count": len(content),
        "segment_count": len(rows),
        "base_hard_gate_counts": RUN17_COUNTS,
        "punctuation_failure_count": len(cohort),
        "punctuation_failure_source_starts": starts,
        "family_counts": dict(sorted(family_counts.items())),
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "max_decoding_length": MAX_DECODING_LENGTH,
        "tc_big_runtime": runtime,
        "tc_big_asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
            "repository": asset.repository,
            "revision": asset.revision,
            "model_safetensors_sha256": asset.model_safetensors_sha256,
            "license": asset.license,
        },
        "rank0_mechanically_admissible_count": len(rank0_replacements),
        "rank0_mechanically_admissible_family_counts": dict(
            sorted(rank0_family_counts.items())
        ),
        "any_nbest_mechanically_admissible_count": len(any_nbest_replacements),
        "any_nbest_mechanically_admissible_family_counts": dict(
            sorted(any_family_counts.items())
        ),
        "rank0_counterfactual": rank0_counterfactual,
        "any_nbest_counterfactual": any_counterfactual,
        "cases": cases,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_path = root / "full-opticks-run17-tc-big-punctuation-nbest.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "schema": SCHEMA,
        "base_hard_gate_counts": RUN17_COUNTS,
        "family_counts": payload["family_counts"],
        "rank0_mechanically_admissible_count": payload[
            "rank0_mechanically_admissible_count"
        ],
        "rank0_mechanically_admissible_family_counts": payload[
            "rank0_mechanically_admissible_family_counts"
        ],
        "rank0_counterfactual": rank0_counterfactual["hard_gate_counts"],
        "any_nbest_mechanically_admissible_count": payload[
            "any_nbest_mechanically_admissible_count"
        ],
        "any_nbest_mechanically_admissible_family_counts": payload[
            "any_nbest_mechanically_admissible_family_counts"
        ],
        "any_nbest_counterfactual": any_counterfactual["hard_gate_counts"],
        "evidence_sha256": payload["evidence_sha256"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
