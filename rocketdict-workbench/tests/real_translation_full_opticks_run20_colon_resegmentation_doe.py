from __future__ import annotations

"""Read-only run20 colon-boundary resegmentation DOE for the dense-label failure.

The current 64-token planner cut leaves the optical clause beginning ``But yet``
inside a truncated row.  The immutable source contains one natural colon at
``and so on: But yet``.  This experiment tests two byte-exact ownerships of that
same colon, using unmodified raw OPUS and TC-big hypotheses.  No whitespace,
literal, source or target repair is injected between chunks.
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

SCHEMA = "rocketdict-full-opticks-run20-colon-resegmentation-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
SOURCE_START = 302426
SOURCE_END = 302883
COLON_OFFSET = 302586
LEFT_COLON_CUT = COLON_OFFSET + 1
RIGHT_COLON_CUT = COLON_OFFSET
EXPECTED_MEMBER_SEQUENCES = [1762, 1763]
EXPECTED_PHRASE = "and so on: But yet with this caution"
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 768
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.50
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
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _alpha(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _labels(text: str) -> Counter[str]:
    return Counter(_TECHNICAL_LABEL_RE.findall(text))


def _pair_evaluation(source_chunks: list[str], target_chunks: list[str]) -> dict[str, Any]:
    if len(source_chunks) != 2 or len(target_chunks) != 2:
        raise ValueError("colon DOE requires exactly two chunks")
    per_chunk = [
        {
            "source_text": source,
            "target_text": target,
            "verdict": evaluate_rescue_pair(source, target),
            "emphasis_markup": compare_emphasis_markup_preservation(source, target),
            "source_alpha_ratio": (_alpha(target) / _alpha(source)) if _alpha(source) else 1.0,
            "technical_labels_exact": _labels(source) == _labels(target),
            "source_technical_labels": dict(_labels(source)),
            "target_technical_labels": dict(_labels(target)),
        }
        for source, target in zip(source_chunks, target_chunks, strict=True)
    ]
    source = "".join(source_chunks)
    target = "".join(target_chunks)
    aggregate = evaluate_rescue_pair(source, target)
    aggregate_emphasis = compare_emphasis_markup_preservation(source, target)
    labels_exact = _labels(source) == _labels(target)
    ratios_pass = all(
        MIN_SOURCE_ALPHA_RATIO <= float(row["source_alpha_ratio"]) <= MAX_SOURCE_ALPHA_RATIO
        for row in per_chunk
    )
    chunk_strict = all(
        row["verdict"].get("strictly_eligible") is True
        and row["emphasis_markup"].get("passed") is True
        and row["technical_labels_exact"] is True
        for row in per_chunk
    )
    # No target separator is inserted.  Record whether raw boundary bytes are
    # readable by themselves.  The right-owned form is expected to be safest:
    # first target ends prose, second raw target starts with ': '.
    left_target, right_target = target_chunks
    raw_boundary = left_target[-24:] + "|" + right_target[:40]
    readable_boundary = bool(
        (left_target.endswith(":") and right_target[:1].isspace())
        or right_target.startswith(": ")
        or left_target.endswith((".", "!", "?", ";"))
    )
    mechanically_admissible = bool(
        chunk_strict
        and aggregate.get("strictly_eligible") is True
        and aggregate_emphasis.get("passed") is True
        and labels_exact
        and ratios_pass
        and readable_boundary
    )
    return {
        "mechanically_admissible": mechanically_admissible,
        "chunk_strict": chunk_strict,
        "per_chunk": per_chunk,
        "aggregate_verdict": aggregate,
        "aggregate_emphasis_markup": aggregate_emphasis,
        "aggregate_technical_labels_exact": labels_exact,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "chunk_source_alpha_ratios_passed": ratios_pass,
        "raw_target_boundary": raw_boundary,
        "raw_target_boundary_readable_without_injection": readable_boundary,
        "target_separator_injected": False,
        "aggregate_target_text": target,
    }


def _strategy_result(
    *,
    name: str,
    source_chunks: list[str],
    opus_groups: list[list[dict[str, Any]]],
    tc_groups: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    if len(opus_groups) != 2 or len(tc_groups) != 2:
        raise RuntimeError("colon DOE model batch cardinality drift")
    for groups in (opus_groups, tc_groups):
        if any(len(group) != NUM_HYPOTHESES for group in groups):
            raise RuntimeError("colon DOE n-best cardinality drift")

    def model(name_: str, groups: list[list[dict[str, Any]]]) -> dict[str, Any]:
        rank_pairs: list[dict[str, Any]] = []
        for rank in range(NUM_HYPOTHESES):
            hypotheses = [groups[0][rank], groups[1][rank]]
            targets = [str(row.get("text") or "") for row in hypotheses]
            rank_pairs.append(
                {
                    "rank": rank,
                    "scores": [row.get("score") for row in hypotheses],
                    "target_chunks": targets,
                    **_pair_evaluation(source_chunks, targets),
                }
            )
        admissible = [row["rank"] for row in rank_pairs if row["mechanically_admissible"] is True]
        return {
            "model": name_,
            "rank_pairs": rank_pairs,
            "rank0_mechanically_admissible": bool(rank_pairs[0]["mechanically_admissible"]),
            "mechanically_admissible_equal_rank_pairs": admissible,
        }

    return {
        "strategy": name,
        "source_chunks": source_chunks,
        "source_chunk_lengths": [len(value) for value in source_chunks],
        "source_reconstruction_exact": "".join(source_chunks),
        "models": {
            "opus": model("opus-en-ru-ct2", opus_groups),
            "tc_big": model("tc-big-en-zle", tc_groups),
        },
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN20_COLON_DOE_ROOT", "work/run20-colon-resegmentation-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("colon DOE requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
        base_rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda row: int(row["sequence_number"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    members = [row for row in base_rows if int(row["sequence_number"]) in EXPECTED_MEMBER_SEQUENCES]
    if [int(row["sequence_number"]) for row in members] != EXPECTED_MEMBER_SEQUENCES:
        raise RuntimeError("colon DOE member identity drift")
    if int(members[0]["source_start"]) != SOURCE_START or int(members[-1]["source_end"]) != SOURCE_END:
        raise RuntimeError("colon DOE source span drift")
    source = content[SOURCE_START:SOURCE_END]
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("colon DOE members do not reconstruct immutable source")
    if EXPECTED_PHRASE not in source:
        raise RuntimeError("colon DOE source phrase/boundary drift")
    if content[COLON_OFFSET] != ":":
        raise RuntimeError("colon DOE punctuation offset drift")

    strategies = {
        "colon_owned_left": [content[SOURCE_START:LEFT_COLON_CUT], content[LEFT_COLON_CUT:SOURCE_END]],
        "colon_owned_right": [content[SOURCE_START:RIGHT_COLON_CUT], content[RIGHT_COLON_CUT:SOURCE_END]],
    }
    if any("".join(chunks) != source for chunks in strategies.values()):
        raise RuntimeError("colon DOE source reconstruction drift")

    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    results: dict[str, Any] = {}
    for name, chunks in strategies.items():
        opus_groups = opus.translate(chunks, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
        tc_groups = tc_big.translate(chunks, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
        results[name] = _strategy_result(
            name=name,
            source_chunks=chunks,
            opus_groups=opus_groups,
            tc_groups=tc_groups,
        )
        if results[name]["source_reconstruction_exact"] != source:
            raise RuntimeError("colon DOE result source reconstruction drift")

    asset = load_tc_big_asset()
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only source-punctuation resegmentation DOE for run20 dense-label numeric/content loss",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_start": SOURCE_START,
        "source_end": SOURCE_END,
        "colon_offset": COLON_OFFSET,
        "member_sequences": EXPECTED_MEMBER_SEQUENCES,
        "source_text": source,
        "source_technical_labels": dict(_labels(source)),
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
        raise RuntimeError("read-only colon DOE mutated run20 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "full-opticks-run20-colon-resegmentation-doe.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "evidence_sha256": evidence["evidence_sha256"],
        "strategies": {
            name: {
                model: {
                    "rank0_mechanically_admissible": result["models"][model]["rank0_mechanically_admissible"],
                    "admissible_equal_rank_pairs": result["models"][model]["mechanically_admissible_equal_rank_pairs"],
                }
                for model in ("opus", "tc_big")
            }
            for name, result in results.items()
        },
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
