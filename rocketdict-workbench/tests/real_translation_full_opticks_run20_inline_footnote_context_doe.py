from __future__ import annotations

"""Read-only OPUS/TC-big n-best DOE for the bounded inline [G] context in run20."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-inline-footnote-context-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 14, "length": 0, "unique": 33}
CONTEXT_SEQUENCE = 598
EXPECTED_SOURCE_START = 112541
EXPECTED_SOURCE_END = 113069
EXPECTED_MEMBER_STARTS = [112541, 112858]
EXPECTED_TOKEN_COUNT = 115
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def _source_alpha_ratio(source: str, target: str) -> float:
    denominator = _alpha(source)
    return 1.0 if denominator == 0 and _alpha(target) == 0 else (_alpha(target) / denominator if denominator else float("inf"))


def _candidate(source: str, target: str, *, base_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _source_alpha_ratio(source, target)
    alpha_non_decreasing = _alpha(target) >= _alpha(base_target)
    marker_exact = target.count("[G]") == source.count("[G]") == 1
    admissible = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and marker_exact
        and MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
        and alpha_non_decreasing
    )
    return {
        "mechanically_admissible": admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "inline_marker_exact": marker_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_passed": MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO,
        "target_alpha_base": _alpha(base_target),
        "target_alpha_candidate": _alpha(target),
        "target_alpha_non_decreasing": alpha_non_decreasing,
    }


def _model_result(name: str, hypotheses: list[dict[str, Any]], source: str, base_target: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        target = str(hypothesis.get("text") or "")
        evaluation = _candidate(source, target, base_target=base_target)
        rows.append(
            {
                "rank": int(hypothesis.get("rank") or 0),
                "score": hypothesis.get("score"),
                "target_text": target,
                **evaluation,
            }
        )
    admissible = [row["rank"] for row in rows if row["mechanically_admissible"]]
    return {
        "model": name,
        "candidates": rows,
        "rank0_mechanically_admissible": bool(rows and rows[0]["mechanically_admissible"]),
        "mechanically_admissible_ranks": admissible,
        "first_mechanically_admissible_rank": None if not admissible else admissible[0],
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN20_INLINE_FOOTNOTE_DOE_ROOT", "work/run20-inline-footnote-context-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("inline-footnote DOE requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        base_output = dict(base_run.get("output") or {})
        context_run_id = int(base_output["context_run_id"])
        contexts = get_run_items(connection, context_run_id, kind="context_sentence")
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("run20 source coverage drift")

    context = next((row for row in contexts if int(row["sequence_number"]) == CONTEXT_SEQUENCE), None)
    if context is None:
        raise RuntimeError("inline-footnote context missing")
    if [int(context["source_start"]), int(context["source_end"])] != [EXPECTED_SOURCE_START, EXPECTED_SOURCE_END]:
        raise RuntimeError("inline-footnote source span drift")
    source = str(context.get("source_text") or "")
    if content[EXPECTED_SOURCE_START:EXPECTED_SOURCE_END] != source:
        raise RuntimeError("inline-footnote immutable source mismatch")
    token_count = int((context.get("payload") or {}).get("token_count") or 0)
    if token_count != EXPECTED_TOKEN_COUNT:
        raise RuntimeError(f"inline-footnote token-count drift: {token_count}")
    if source.count("[G]") != 1:
        raise RuntimeError("inline [G] source marker drift")

    members = [
        row for row in base_rows
        if EXPECTED_SOURCE_START <= int(row["source_start"]) and int(row["source_end"]) <= EXPECTED_SOURCE_END
    ]
    if [int(row["source_start"]) for row in members] != EXPECTED_MEMBER_STARTS:
        raise RuntimeError("inline-footnote member geometry drift")
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("inline-footnote members do not reconstruct context")
    base_target = "".join(str(row.get("target_text") or "") for row in members)
    if base_target.count("[G]") != 0:
        raise RuntimeError("run20 unexpectedly preserves [G]")

    opus = OpusTranslator(device="cpu", compute_type="float32")
    opus_hypotheses = opus.translate(
        [source], beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH
    )[0]
    tc_big_asset = load_tc_big_asset()
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    tc_big_hypotheses = tc_big.translate(
        [source], beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH
    )[0]
    if len(opus_hypotheses) != NUM_HYPOTHESES or len(tc_big_hypotheses) != NUM_HYPOTHESES:
        raise RuntimeError("inline-footnote n-best cardinality drift")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only whole-context OPUS/TC-big DOE for bounded inline [G] loss",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "context_sequence": CONTEXT_SEQUENCE,
        "source_start": EXPECTED_SOURCE_START,
        "source_end": EXPECTED_SOURCE_END,
        "nlp_token_count": token_count,
        "member_sequences": [int(row["sequence_number"]) for row in members],
        "member_source_starts": EXPECTED_MEMBER_STARTS,
        "source_text": source,
        "base_target": base_target,
        "source_inline_marker_count": source.count("[G]"),
        "base_target_inline_marker_count": base_target.count("[G]"),
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "models": {
            "opus": _model_result("opus-en-ru-ct2", opus_hypotheses, source, base_target),
            "tc_big": _model_result("tc-big-en-zle", tc_big_hypotheses, source, base_target),
        },
        "tc_big_asset": {
            "manifest_sha256": tc_big_asset.manifest_sha256,
            "payload_tree_sha256": tc_big_asset.payload_tree_sha256,
            "payload_file_count": tc_big_asset.payload_file_count,
            "payload_bytes": tc_big_asset.payload_bytes,
        },
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
    }
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("read-only inline-footnote DOE mutated database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "full-opticks-run20-inline-footnote-context-doe.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "summary.json").write_text(
        json.dumps(
            {
                "context_sequence": CONTEXT_SEQUENCE,
                "opus_rank0_admissible": evidence["models"]["opus"]["rank0_mechanically_admissible"],
                "opus_admissible_ranks": evidence["models"]["opus"]["mechanically_admissible_ranks"],
                "tc_big_rank0_admissible": evidence["models"]["tc_big"]["rank0_mechanically_admissible"],
                "tc_big_admissible_ranks": evidence["models"]["tc_big"]["mechanically_admissible_ranks"],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
