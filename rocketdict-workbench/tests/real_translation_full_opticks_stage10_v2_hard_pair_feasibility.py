from __future__ import annotations

"""Read-only real-MT feasibility for Stage10-v2 false-boundary hard-failing pairs.

The cohort is not corpus-phrase-selected: a boundary must be independently proven
by the maintained Stage10-v2 source predicate, be exactly representable between
two complete adjacent run-16 Stage12 rows, and at least one of those primary rows
must already fail a maintained Product hard gate. Both pinned real MT backends
then see the exact byte-concatenated pair source. Raw n-best hypotheses are only
audited here; this experiment never mutates the database or promotes a candidate.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.context_sentence_boundaries import (
    STAGE10_BOUNDARY_POLICY,
    evaluate_spacy_sentence_boundary,
)
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator, load_opus_asset
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-stage10-v2-hard-pair-feasibility/1"
BASE_DATABASE_SHA256 = "573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11"
BASE_RUN_ID = 16
BASE_OUTPUT_SHA256 = "767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 18, "length": 0, "unique": 37}
EXPECTED_BOUNDARY_OFFSETS = (54796, 112001, 522572)
EXPECTED_LEFT_STARTS = {54796: 54772, 112001: 111869, 522572: 522555}
N_BEST = 8


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


def _alpha_ratio(source: str, target: str) -> float:
    source_alpha = sum(char.isalpha() for char in source)
    target_alpha = sum(char.isalpha() for char in target)
    return target_alpha / source_alpha if source_alpha else 1.0


def _hard_flags(source: str, target: str) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(source, target)
    return {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures: dict[str, list[int]] = {
        "numeric_symbol": [],
        "punctuation": [],
        "length": [],
    }
    unique: set[int] = set()
    for row in _ordered(rows):
        sequence = int(row["sequence_number"])
        flags = _hard_flags(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        for key, failed in flags.items():
            if failed:
                failures[key].append(sequence)
                unique.add(sequence)
    return {
        "counts": {
            "numeric_symbol": len(failures["numeric_symbol"]),
            "punctuation": len(failures["punctuation"]),
            "length": len(failures["length"]),
            "unique": len(unique),
        },
        "failures": failures,
    }


def _semantic_diagnostics(offset: int, target: str) -> dict[str, bool]:
    """Diagnostic-only anchors. They never authorize selection."""
    lowered = target.casefold()
    if offset == 54796:
        return {
            "figure_16": "16" in target and ("рис" in lowered or "фиг" in lowered),
            "prism": "призм" in lowered,
            "distance": "рассто" in lowered,
            "wall": "стен" in lowered,
            "spectrum": "спектр" in lowered,
        }
    if offset == 112001:
        return {
            "sines": "синус" in lowered,
            "proportion": "пропорц" in lowered,
            "least": "наимень" in lowered or "мал" in lowered,
        }
    if offset == 522572:
        return {
            "whence_relation": "откуда" in lowered or "как не" in lowered,
            "attractive_power": "притяг" in lowered or "привлек" in lowered,
            "water": "вод" in lowered,
            "salt": "сол" in lowered,
            "heat": "тепл" in lowered or "жар" in lowered,
        }
    raise AssertionError(offset)


def _candidate_evidence(
    *,
    offset: int,
    source: str,
    model: str,
    hypothesis: dict[str, Any],
    base_pair_failure_counts: dict[str, int],
    base_pair_unique_failures: int,
) -> dict[str, Any]:
    target = str(hypothesis.get("text") or "")
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    flags = _hard_flags(source, target)
    candidate_unique = 1 if any(flags.values()) else 0
    projected = {
        "numeric_symbol": BASE_COUNTS["numeric_symbol"]
        - base_pair_failure_counts["numeric_symbol"]
        + int(flags["numeric_symbol"]),
        "punctuation": BASE_COUNTS["punctuation"]
        - base_pair_failure_counts["punctuation"]
        + int(flags["punctuation"]),
        "length": BASE_COUNTS["length"]
        - base_pair_failure_counts["length"]
        + int(flags["length"]),
        "unique": BASE_COUNTS["unique"] - base_pair_unique_failures + candidate_unique,
    }
    semantics = _semantic_diagnostics(offset, target)
    return {
        "model": model,
        "rank": int(hypothesis["rank"]),
        "score": hypothesis.get("score"),
        "target_text": target,
        "source_alpha_ratio": _alpha_ratio(source, target),
        "product_hard_passed": verdict.get("product_hard_passed") is True,
        "strict_research_passed": verdict.get("strict_research_passed") is True,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "emphasis_passed": emphasis.get("passed") is True,
        "mechanically_admissible": (
            verdict.get("strictly_eligible") is True and emphasis.get("passed") is True
        ),
        "semantic_diagnostics": semantics,
        "all_semantic_diagnostics": all(semantics.values()),
        "semantic_diagnostics_are_non_authoritative": True,
        "hard_failures": flags,
        "projected_full_corpus_counts_if_pair_alone_replaced": projected,
        "verdict": verdict,
        "emphasis_markup": emphasis,
    }


def _stage10_decision_for_offset(
    content: str,
    grouped: dict[int, list[dict[str, Any]]],
    offset: int,
) -> dict[str, Any]:
    indices = sorted(grouped)
    matches: list[dict[str, Any]] = []
    for left_index, right_index in zip(indices, indices[1:]):
        right_rows = grouped[right_index]
        if not right_rows or int(right_rows[0]["source_start"]) != offset:
            continue
        decision = evaluate_spacy_sentence_boundary(
            content,
            left_index,
            grouped[left_index],
            right_index,
            right_rows,
        )
        matches.append(decision)
    if len(matches) != 1:
        raise RuntimeError(f"Stage10 predicate identity drift at {offset}: {len(matches)} matches")
    decision = matches[0]
    if (
        decision.get("policy") != STAGE10_BOUNDARY_POLICY
        or decision.get("merge") is not True
        or int(decision.get("source_offset") or -1) != offset
        or decision.get("reason") != "lowercase_continuation_without_terminal"
    ):
        raise RuntimeError(f"Stage10-v2 no longer proves boundary {offset}: {decision!r}")
    return decision


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_STAGE10_HARD_PAIR_ROOT",
            "work/full-opticks-stage10-v2-hard-pair-feasibility",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("Stage10 hard-pair feasibility requires exact persisted run-16 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        run_output = dict(run.get("output") or {})
        context_run_id = int(run_output["context_run_id"])
        context_run = get_run(connection, context_run_id)
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        nlp_rows = _ordered(get_run_items(connection, nlp_run_id, kind="nlp_token"))
        document = get_document(connection, int(run_output["document_version_id"]))

    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-16 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    content = str(document["content_text"])
    base_inventory = _inventory(base_rows)
    if base_inventory["counts"] != BASE_COUNTS:
        raise RuntimeError(f"run-16 hard-gate drift: {base_inventory['counts']!r}")

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in nlp_rows:
        payload = dict(row.get("payload") or {})
        grouped[int(payload["sentence_index"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row["sequence_number"]))

    by_end: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_start: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in base_rows:
        by_end[int(row["source_end"])].append(row)
        by_start[int(row["source_start"])].append(row)

    cohort: list[dict[str, Any]] = []
    for offset in EXPECTED_BOUNDARY_OFFSETS:
        decision = _stage10_decision_for_offset(content, grouped, offset)
        lefts = by_end[offset]
        rights = by_start[offset]
        if len(lefts) != 1 or len(rights) != 1:
            raise RuntimeError(
                f"run-16 exact pair geometry drift at {offset}: left={len(lefts)} right={len(rights)}"
            )
        left, right = lefts[0], rights[0]
        if int(left["source_start"]) != EXPECTED_LEFT_STARTS[offset]:
            raise RuntimeError(f"run-16 pair left identity drift at {offset}")
        if int(left["sequence_number"]) + 1 != int(right["sequence_number"]):
            raise RuntimeError(f"run-16 pair is not adjacent at {offset}")
        combined_source = str(left.get("source_text") or "") + str(right.get("source_text") or "")
        start = int(left["source_start"])
        end = int(right["source_end"])
        if combined_source != content[start:end]:
            raise RuntimeError(f"pair source is not byte-exact at {offset}")
        left_flags = _hard_flags(str(left["source_text"]), str(left.get("target_text") or ""))
        right_flags = _hard_flags(str(right["source_text"]), str(right.get("target_text") or ""))
        if not (any(left_flags.values()) or any(right_flags.values())):
            raise RuntimeError(f"Stage10-v2 boundary {offset} is not a run-16 hard-failing pair")
        pair_failure_counts = {
            key: int(left_flags[key]) + int(right_flags[key])
            for key in ("numeric_symbol", "punctuation", "length")
        }
        pair_unique = int(any(left_flags.values())) + int(any(right_flags.values()))
        cohort.append(
            {
                "boundary_offset": offset,
                "source_start": start,
                "source_end": end,
                "combined_source": combined_source,
                "left": {
                    "sequence_number": int(left["sequence_number"]),
                    "source_start": int(left["source_start"]),
                    "source_end": int(left["source_end"]),
                    "source_text": str(left["source_text"]),
                    "target_text": str(left.get("target_text") or ""),
                    "hard_failures": left_flags,
                },
                "right": {
                    "sequence_number": int(right["sequence_number"]),
                    "source_start": int(right["source_start"]),
                    "source_end": int(right["source_end"]),
                    "source_text": str(right["source_text"]),
                    "target_text": str(right.get("target_text") or ""),
                    "hard_failures": right_flags,
                },
                "base_pair_failure_counts": pair_failure_counts,
                "base_pair_unique_failure_count": pair_unique,
                "stage10_v2_decision": decision,
            }
        )

    opus_asset = load_opus_asset()
    tc_big_asset = load_tc_big_asset()
    sources = [row["combined_source"] for row in cohort]
    opus_hypotheses = OpusTranslator(device="cpu", compute_type="float32").translate(
        sources,
        beam_size=N_BEST,
        num_hypotheses=N_BEST,
        max_decoding_length=512,
    )
    tc_big_hypotheses = TcBigTranslator(device="cpu", compute_type="float32").translate(
        sources,
        beam_size=N_BEST,
        num_hypotheses=N_BEST,
        max_decoding_length=512,
    )

    if len(opus_hypotheses) != len(cohort) or len(tc_big_hypotheses) != len(cohort):
        raise RuntimeError("real-MT batch cardinality drift")

    for index, row in enumerate(cohort):
        evaluated: list[dict[str, Any]] = []
        for model, hypotheses in (
            ("opus-en-ru-ct2", opus_hypotheses[index]),
            ("tc-big-en-zle-ct2", tc_big_hypotheses[index]),
        ):
            if len(hypotheses) != N_BEST:
                raise RuntimeError(
                    f"{model} hypothesis-count drift at {row['boundary_offset']}: {len(hypotheses)}"
                )
            for hypothesis in hypotheses:
                evaluated.append(
                    _candidate_evidence(
                        offset=int(row["boundary_offset"]),
                        source=str(row["combined_source"]),
                        model=model,
                        hypothesis=hypothesis,
                        base_pair_failure_counts=dict(row["base_pair_failure_counts"]),
                        base_pair_unique_failures=int(row["base_pair_unique_failure_count"]),
                    )
                )
        row["candidates"] = evaluated
        row["mechanically_admissible_candidates"] = [
            {"model": candidate["model"], "rank": candidate["rank"]}
            for candidate in evaluated
            if candidate["mechanically_admissible"]
        ]
        row["mechanically_and_diagnostic_candidates"] = [
            {"model": candidate["model"], "rank": candidate["rank"]}
            for candidate in evaluated
            if candidate["mechanically_admissible"] and candidate["all_semantic_diagnostics"]
        ]

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "read-only OPUS+TC-big n-best feasibility for run-16 hard-failing adjacent rows "
            "whose boundary is independently proven false by Stage10-v2 source geometry"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_candidate_selection_allowed": False,
        "semantic_review_required": True,
        "database_mutated": False,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_run_id": BASE_RUN_ID,
        "base_output_sha256": BASE_OUTPUT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "context_run_id": context_run_id,
        "nlp_run_id": nlp_run_id,
        "stage10_boundary_policy": STAGE10_BOUNDARY_POLICY,
        "expected_boundary_offsets": list(EXPECTED_BOUNDARY_OFFSETS),
        "cohort_count": len(cohort),
        "n_best_per_model": N_BEST,
        "cohort": cohort,
        "opus_asset": {
            "revision": opus_asset.revision,
            "source_archive_sha256": opus_asset.source_archive_sha256,
            "manifest_sha256": opus_asset.manifest_sha256,
            "payload_tree_sha256": opus_asset.payload_tree_sha256,
            "payload_file_count": opus_asset.payload_file_count,
            "payload_bytes": opus_asset.payload_bytes,
        },
        "tc_big_asset": {
            "repository": tc_big_asset.repository,
            "revision": tc_big_asset.revision,
            "license": tc_big_asset.license,
            "manifest_sha256": tc_big_asset.manifest_sha256,
            "payload_tree_sha256": tc_big_asset.payload_tree_sha256,
            "payload_file_count": tc_big_asset.payload_file_count,
            "payload_bytes": tc_big_asset.payload_bytes,
        },
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-stage10-v2-hard-pair-feasibility.json"
    destination.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "cohort": [
                    {
                        "boundary_offset": row["boundary_offset"],
                        "base_pair_failure_counts": row["base_pair_failure_counts"],
                        "mechanically_admissible_candidates": row["mechanically_admissible_candidates"],
                        "mechanically_and_diagnostic_candidates": row["mechanically_and_diagnostic_candidates"],
                    }
                    for row in cohort
                ],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
