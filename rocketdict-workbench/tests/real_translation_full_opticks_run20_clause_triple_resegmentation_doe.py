from __future__ import annotations

"""Read-only equal-rank clause-triple DOE for the run20 dense-label truncation.

The current planner split leaves a clause ending in ``and from thence to`` at
one boundary.  Earlier two-chunk colon DOE removed the numeric omission but
still produced weak terminology.  This experiment keeps the exact immutable
run20 source and tries only punctuation-owned source segmentation around the
existing colon and semicolon.  Each strategy translates three source chunks
with pinned OPUS and TC-big, then evaluates only equal-rank raw aggregates.

No target separator is injected, no source bytes are rewritten, no hypotheses
are mixed across ranks, and no result authorizes Product promotion without
manual semantic review and a later full-corpus replay.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-clause-triple-resegmentation-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SOURCE_START = 302426
EXPECTED_SOURCE_END = 302883
EXPECTED_MEMBER_SEQUENCES = [1762, 1763]
CURRENT_FAILURE_SEQUENCE = 1762
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 768
MIN_CHUNK_ALPHA_RATIO = 0.55
MAX_CHUNK_ALPHA_RATIO = 1.65
MIN_AGGREGATE_ALPHA_RATIO = 0.65
MAX_AGGREGATE_ALPHA_RATIO = 1.50
MIN_BASE_ALPHA_RETENTION = 0.98
_TECHNICAL_LABEL_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Z]{1,3}\d+|\d+[A-Z]{1,3}|[A-Z]{2,3})(?![A-Za-z0-9])"
)


def _sha(path: Path) -> str:
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


def _alpha(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _technical_labels(text: str) -> Counter[str]:
    return Counter(_TECHNICAL_LABEL_RE.findall(text))


def _chunk_eval(source: str, target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    labels_exact = _technical_labels(source) == _technical_labels(target)
    passed = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and labels_exact
        and MIN_CHUNK_ALPHA_RATIO <= ratio <= MAX_CHUNK_ALPHA_RATIO
    )
    return {
        "passed": passed,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "technical_labels_exact": labels_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_CHUNK_ALPHA_RATIO, MAX_CHUNK_ALPHA_RATIO],
    }


def _aggregate_eval(source: str, target: str, *, base_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    source_ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    base_retention = target_alpha / base_alpha if base_alpha else (1.0 if target_alpha == 0 else float("inf"))
    labels_exact = _technical_labels(source) == _technical_labels(target)
    colon_exact = source.count(":") == target.count(":")
    semicolon_exact = source.count(";") == target.count(";")
    passed = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and labels_exact
        and colon_exact
        and semicolon_exact
        and MIN_AGGREGATE_ALPHA_RATIO <= source_ratio <= MAX_AGGREGATE_ALPHA_RATIO
        and base_retention >= MIN_BASE_ALPHA_RETENTION
    )
    return {
        "passed": passed,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "technical_labels_exact": labels_exact,
        "colon_exact": colon_exact,
        "semicolon_exact": semicolon_exact,
        "source_alpha_ratio": source_ratio,
        "source_alpha_ratio_range": [MIN_AGGREGATE_ALPHA_RATIO, MAX_AGGREGATE_ALPHA_RATIO],
        "base_alpha_retention": base_retention,
        "minimum_base_alpha_retention": MIN_BASE_ALPHA_RETENTION,
    }


def _split_strategies(source: str) -> dict[str, list[str]]:
    colon = source.index(": But yet")
    semicolon = source.index("; where")
    if not (0 < colon < semicolon < len(source)):
        raise RuntimeError("clause-triple punctuation geometry drift")
    strategies = {
        "colon_right_semicolon_right": [
            source[:colon], source[colon:semicolon], source[semicolon:]
        ],
        "colon_left_semicolon_right": [
            source[: colon + 1], source[colon + 1 : semicolon], source[semicolon:]
        ],
        "colon_right_semicolon_left": [
            source[:colon], source[colon : semicolon + 1], source[semicolon + 1 :]
        ],
        "colon_left_semicolon_left": [
            source[: colon + 1], source[colon + 1 : semicolon + 1], source[semicolon + 1 :]
        ],
    }
    for name, chunks in strategies.items():
        if len(chunks) != 3 or "".join(chunks) != source or any(not chunk for chunk in chunks):
            raise RuntimeError(f"strategy {name} does not reconstruct immutable source")
    return strategies


def _translate_strategy(
    translator: Any,
    chunks: list[str],
    *,
    model_name: str,
    source: str,
    base_target: str,
) -> dict[str, Any]:
    generated = translator.translate(
        chunks,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != 3 or any(len(rows) != NUM_HYPOTHESES for rows in generated):
        raise RuntimeError(f"{model_name} clause-triple hypothesis cardinality drift")
    rank_rows: list[dict[str, Any]] = []
    for rank in range(NUM_HYPOTHESES):
        hypotheses = [rows[rank] for rows in generated]
        targets = [str(row.get("text") or "") for row in hypotheses]
        aggregate = "".join(targets)
        chunk_evaluations = [
            _chunk_eval(chunk, target) for chunk, target in zip(chunks, targets, strict=True)
        ]
        aggregate_eval = _aggregate_eval(source, aggregate, base_target=base_target)
        admissible = bool(
            aggregate_eval["passed"] is True
            and all(row["passed"] is True for row in chunk_evaluations)
        )
        rank_rows.append(
            {
                "rank": rank,
                "scores": [row.get("score") for row in hypotheses],
                "target_chunks": targets,
                "aggregate_target_text": aggregate,
                "chunk_evaluations": chunk_evaluations,
                "aggregate_evaluation": aggregate_eval,
                "mechanically_admissible": admissible,
                "target_separator_injected": False,
            }
        )
    admissible_ranks = [row["rank"] for row in rank_rows if row["mechanically_admissible"]]
    return {
        "model": model_name,
        "rank_pairs": rank_rows,
        "rank0_mechanically_admissible": bool(rank_rows and rank_rows[0]["mechanically_admissible"]),
        "mechanically_admissible_equal_rank_triples": admissible_ranks,
        "first_mechanically_admissible_rank": None if not admissible_ranks else admissible_ranks[0],
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN20_CLAUSE_TRIPLE_DOE_ROOT",
            "work/run20-clause-triple-resegmentation-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("clause-triple DOE requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        output = dict(run.get("output") or {})
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(output["document_version_id"]))

    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run20 source coverage drift")

    members = [
        row for row in rows
        if EXPECTED_SOURCE_START <= int(row["source_start"])
        and int(row["source_end"]) <= EXPECTED_SOURCE_END
    ]
    if [int(row["sequence_number"]) for row in members] != EXPECTED_MEMBER_SEQUENCES:
        raise RuntimeError("clause-triple member identity drift")
    source = "".join(str(row.get("source_text") or "") for row in members)
    if source != content[EXPECTED_SOURCE_START:EXPECTED_SOURCE_END]:
        raise RuntimeError("clause-triple immutable source mismatch")
    base_target = "".join(str(row.get("target_text") or "") for row in members)
    failing_members = [
        int(row["sequence_number"])
        for row in members
        if evaluate_rescue_pair(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        ).get("product_hard_passed") is not True
    ]
    if failing_members != [CURRENT_FAILURE_SEQUENCE]:
        raise RuntimeError(f"clause-triple current failure drift: {failing_members!r}")

    strategies = _split_strategies(source)
    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    results: dict[str, Any] = {}
    for name, chunks in strategies.items():
        results[name] = {
            "strategy": name,
            "source_chunks": chunks,
            "source_chunk_lengths": [len(chunk) for chunk in chunks],
            "source_reconstruction_exact": "".join(chunks) == source,
            "models": {
                "opus": _translate_strategy(
                    opus,
                    chunks,
                    model_name="opus-en-ru-ct2",
                    source=source,
                    base_target=base_target,
                ),
                "tc_big": _translate_strategy(
                    tc_big,
                    chunks,
                    model_name="tc-big-en-zle",
                    source=source,
                    base_target=base_target,
                ),
            },
        }

    asset = load_tc_big_asset()
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only equal-rank punctuation-owned three-clause resegmentation DOE for run20 dense-label truncation",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_start": EXPECTED_SOURCE_START,
        "source_end": EXPECTED_SOURCE_END,
        "member_sequences": EXPECTED_MEMBER_SEQUENCES,
        "current_failure_sequences": failing_members,
        "source_text": source,
        "base_target": base_target,
        "source_technical_labels": dict(_technical_labels(source)),
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "strategies": results,
        "tc_big_asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
        },
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "target_separator_injected": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
    }
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("read-only clause-triple DOE mutated run20 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "full-opticks-run20-clause-triple-resegmentation-doe.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "strategies": {
            name: {
                model: {
                    "rank0_mechanically_admissible": data["models"][model]["rank0_mechanically_admissible"],
                    "admissible_equal_rank_triples": data["models"][model]["mechanically_admissible_equal_rank_triples"],
                }
                for model in ("opus", "tc_big")
            }
            for name, data in results.items()
        },
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
