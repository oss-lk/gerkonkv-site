from __future__ import annotations

"""Read-only OPUS/TC-big DOE for Gutenberg emphasis-modifier false boundaries.

The exact persisted run22 Stage10 V1 context stream is scanned without corpus
position or literal-word whitelists. A candidate boundary is source-defined:
the left context ends in one balanced single-word Gutenberg emphasis span,
followed only by non-paragraph whitespace, while the next contiguous context
starts with a capitalized lexical word. Consecutive matching boundaries are
coalesced into maximal source groups before inference.

This experiment is deliberately non-promoting. It records all matching groups,
their current Stage12 hard-failure state, and six unmodified raw hypotheses from
each pinned model. Mechanical admissibility is necessary but never sufficient;
semantic review remains mandatory and only rank0 could later be considered by a
separate fail-closed research wrapper.
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
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run22-emphasized-modifier-boundary-doe/1"
BOUNDARY_CONTRACT = "rocketdict-stage10-emphasized-single-word-modifier-boundary-census/1"
BASE_DATABASE_SHA256 = "5cc0bec1d8ab1c9b0eadb9441819d84676f005a5a3bbb3a068745338469b3206"
BASE_RUN_ID = 22
BASE_OUTPUT_SHA256 = "41cb94e6a2732aee597d8e630cc248487d6e0b7ce5fb9a794d01ecda7f2edb48"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1536
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.55
MIN_BASE_ALPHA_RETENTION_RATIO = 0.95
_EMPHASIZED_SINGLE_WORD_RE = re.compile(r"_([A-Za-z][A-Za-z-]{0,30})_([ \t\r\n]*)\Z")
_CAPITALIZED_LEXICAL_RE = re.compile(r"\s*([A-Z][A-Za-z-]*)")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def _alpha(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _boundary(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any] | None:
    if int(left["source_end"]) != int(right["source_start"]):
        return None
    left_source = str(left.get("source_text") or "")
    right_source = str(right.get("source_text") or "")
    emphasized = _EMPHASIZED_SINGLE_WORD_RE.search(left_source)
    if emphasized is None:
        return None
    trailing = emphasized.group(2).replace("\r", "")
    if "\n\n" in trailing:
        return None
    right_match = _CAPITALIZED_LEXICAL_RE.match(right_source)
    if right_match is None:
        return None
    return {
        "contract": BOUNDARY_CONTRACT,
        "left_context_sequence": int(left["sequence_number"]),
        "right_context_sequence": int(right["sequence_number"]),
        "boundary_offset": int(left["source_end"]),
        "emphasized_modifier": emphasized.group(1),
        "right_lexical_start": right_match.group(1),
        "trailing_whitespace": trailing,
        "paragraph_break": False,
    }


def _discover_groups(contexts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[list[int]]]:
    ordered = sorted(contexts, key=lambda row: int(row["sequence_number"]))
    boundaries: list[dict[str, Any]] = []
    for left, right in zip(ordered, ordered[1:], strict=False):
        row = _boundary(left, right)
        if row is not None:
            boundaries.append(row)

    edges = {
        (int(row["left_context_sequence"]), int(row["right_context_sequence"]))
        for row in boundaries
    }
    groups: list[list[int]] = []
    consumed: set[tuple[int, int]] = set()
    for left, right in sorted(edges):
        if (left, right) in consumed:
            continue
        sequence = [left, right]
        consumed.add((left, right))
        cursor = right
        while (cursor, cursor + 1) in edges:
            sequence.append(cursor + 1)
            consumed.add((cursor, cursor + 1))
            cursor += 1
        groups.append(sequence)
    return boundaries, groups


def _candidate(source: str, target: str, *, base_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    source_ratio = target_alpha / source_alpha if source_alpha else 1.0
    base_retention = target_alpha / base_alpha if base_alpha else 1.0
    source_terminal = source.rstrip()[-1:] if source.rstrip() else ""
    target_terminal = target.rstrip()[-1:] if target.rstrip() else ""
    terminal_required = source_terminal if source_terminal in ".?!" else None
    terminal_preserved = terminal_required is None or target_terminal == terminal_required
    admissible = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and MIN_SOURCE_ALPHA_RATIO <= source_ratio <= MAX_SOURCE_ALPHA_RATIO
        and base_retention >= MIN_BASE_ALPHA_RETENTION_RATIO
        and terminal_preserved
    )
    return {
        "mechanically_admissible": admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": source_ratio,
        "source_alpha_ratio_passed": MIN_SOURCE_ALPHA_RATIO <= source_ratio <= MAX_SOURCE_ALPHA_RATIO,
        "base_alpha_retention_ratio": base_retention,
        "base_alpha_retention_passed": base_retention >= MIN_BASE_ALPHA_RETENTION_RATIO,
        "terminal_punctuation_required": terminal_required,
        "terminal_punctuation_preserved": terminal_preserved,
    }


def _model_result(source: str, base_target: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        target = str(hypothesis.get("text") or "")
        rows.append(
            {
                "rank": int(hypothesis.get("rank") or 0),
                "score": hypothesis.get("score"),
                "target_text": target,
                **_candidate(source, target, base_target=base_target),
            }
        )
    admissible = [row["rank"] for row in rows if row["mechanically_admissible"]]
    return {
        "hypotheses": rows,
        "rank0_mechanically_admissible": bool(rows and rows[0]["mechanically_admissible"]),
        "mechanically_admissible_ranks": admissible,
        "first_mechanically_admissible_rank": None if not admissible else admissible[0],
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN22_EMPHASIZED_MODIFIER_ROOT",
            "work/run22-emphasized-modifier-boundary-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("emphasized-modifier DOE requires exact persisted run22 database")
    database_sha_before = _sha(database)

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["source_start"]),
        )
        base_output = dict(base_run.get("output") or {})
        context_run_id = int(base_output["context_run_id"])
        contexts = sorted(
            get_run_items(connection, context_run_id, kind="context_sentence"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run22 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run22 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("run22 source coverage drift")

    boundaries, groups = _discover_groups(contexts)
    by_context = {int(row["sequence_number"]): row for row in contexts}
    boundary_by_edge = {
        (int(row["left_context_sequence"]), int(row["right_context_sequence"])): row
        for row in boundaries
    }

    group_inputs: list[dict[str, Any]] = []
    for sequences in groups:
        context_rows = [by_context[sequence] for sequence in sequences]
        start = int(context_rows[0]["source_start"])
        end = int(context_rows[-1]["source_end"])
        source = "".join(str(row.get("source_text") or "") for row in context_rows)
        if source != content[start:end]:
            raise RuntimeError(f"context group {sequences!r} is not byte-exact")
        members = [
            row
            for row in base_rows
            if start <= int(row["source_start"]) and int(row["source_end"]) <= end
        ]
        if not members or "".join(str(row.get("source_text") or "") for row in members) != source:
            raise RuntimeError(f"Stage12 members do not reconstruct context group {sequences!r}")
        base_target = "".join(str(row.get("target_text") or "") for row in members)
        member_failures: list[dict[str, Any]] = []
        numeric_failure_count = 0
        for row in members:
            row_source = str(row.get("source_text") or "")
            row_target = str(row.get("target_text") or "")
            verdict = evaluate_rescue_pair(row_source, row_target)
            numeric = evaluate_numeric_symbol_pair(row_source, row_target)
            if numeric.get("passed") is not True:
                numeric_failure_count += 1
            if verdict.get("product_hard_passed") is not True:
                member_failures.append(
                    {
                        "sequence_number": int(row["sequence_number"]),
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "numeric_symbol_failed": numeric.get("passed") is not True,
                        "verdict": verdict,
                    }
                )
        group_boundaries = [
            boundary_by_edge[(left, right)]
            for left, right in zip(sequences, sequences[1:], strict=False)
        ]
        group_inputs.append(
            {
                "name": f"contexts_{sequences[0]}_{sequences[-1]}",
                "context_sequences": sequences,
                "source_start": start,
                "source_end": end,
                "context_token_count": sum(
                    int((row.get("payload") or {}).get("token_count") or 0)
                    for row in context_rows
                ),
                "boundaries": group_boundaries,
                "source_text": source,
                "base_target": base_target,
                "base_aggregate_verdict": evaluate_rescue_pair(source, base_target),
                "base_member_hard_failures": member_failures,
                "base_numeric_failure_member_count": numeric_failure_count,
                "member_stage12_sequences": [int(row["sequence_number"]) for row in members],
            }
        )

    sources = [str(row["source_text"]) for row in group_inputs]
    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    opus_hypotheses = opus.translate(
        sources,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    tc_hypotheses = tc_big.translate(
        sources,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(opus_hypotheses) != len(group_inputs) or len(tc_hypotheses) != len(group_inputs):
        raise RuntimeError("emphasized-modifier model cardinality drift")

    cases: list[dict[str, Any]] = []
    for group, opus_rows, tc_rows in zip(
        group_inputs, opus_hypotheses, tc_hypotheses, strict=True
    ):
        if len(opus_rows) != NUM_HYPOTHESES or len(tc_rows) != NUM_HYPOTHESES:
            raise RuntimeError("emphasized-modifier n-best cardinality drift")
        cases.append(
            {
                **group,
                "opus": _model_result(
                    str(group["source_text"]), str(group["base_target"]), opus_rows
                ),
                "tc_big": _model_result(
                    str(group["source_text"]), str(group["base_target"]), tc_rows
                ),
            }
        )

    if _sha(database) != database_sha_before:
        raise RuntimeError("read-only emphasized-modifier DOE mutated database")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "boundary_contract": BOUNDARY_CONTRACT,
        "purpose": "read-only source-derived Gutenberg emphasized-modifier false-boundary DOE over exact persisted run22",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "n_best_cherry_picking": False,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "boundary_count": len(boundaries),
        "group_count": len(groups),
        "boundaries": boundaries,
        "groups": groups,
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "cases": cases,
        "hard_failure_groups": [
            case["name"] for case in cases if case["base_member_hard_failures"]
        ],
        "numeric_failure_groups": [
            case["name"]
            for case in cases
            if int(case["base_numeric_failure_member_count"]) > 0
        ],
        "rank0_mechanically_admissible": {
            "opus": [
                case["name"]
                for case in cases
                if case["opus"]["rank0_mechanically_admissible"]
            ],
            "tc_big": [
                case["name"]
                for case in cases
                if case["tc_big"]["rank0_mechanically_admissible"]
            ],
        },
        "database_unchanged": True,
        "source_coverage_byte_exact": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "run22-emphasized-modifier-boundary-doe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "boundary_count": evidence["boundary_count"],
        "group_count": evidence["group_count"],
        "hard_failure_groups": evidence["hard_failure_groups"],
        "numeric_failure_groups": evidence["numeric_failure_groups"],
        "rank0_mechanically_admissible": evidence["rank0_mechanically_admissible"],
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
