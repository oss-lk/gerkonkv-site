from __future__ import annotations

"""Read-only two-chunk DOE for the dense FIG. 6 planner group in exact run20.

The current Stage12 planner splits a source-defined 176-token figure-description
planner group into 64/64/37-token pieces.  Its middle piece loses the complete
``Reflexions ... 2K, 6N, 10Q`` clause.  Whole-group OPUS rank0 restores that
clause but produces avoidable lexical debt (notably ``рефлексионы``).

This experiment changes only source geometry: it cuts *before* the unique major
clause colon in ``and so on: But yet with this caution``.  Because Product MT
runtimes strip model outputs, keeping the colon at the start of the right source
chunk allows the two unmodified raw targets to be concatenated with no inserted
space/punctuation and therefore no target surgery.

No result is promoted automatically.  The exact run20 database is read-only,
all six OPUS and TC-big hypotheses are retained for both chunks, and rank0 is
only a semantic-review candidate.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator, load_opus_asset
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-dense-figure-clause-boundary-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 14, "length": 0, "unique": 33}
CONTEXT_SEQUENCES = [1640, 1641]
MEMBER_SEQUENCES = [1761, 1762, 1763]
SOURCE_START = 302134
SOURCE_END = 302883
EXPECTED_TOTAL_TOKENS = 176
EXPECTED_LEFT_TOKENS = 104
EXPECTED_RIGHT_TOKENS = 72
EXPECTED_CURRENT_FAILURE_SEQUENCES = [1762]
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1024
_SPLIT_RE = re.compile(r"(?=: But yet with this caution\b)")
_LABEL_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Z]{2}|(?=[A-Z0-9]{2,4}(?![A-Za-z0-9]))(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]+)(?![A-Za-z0-9])"
)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
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
    return sum(ch.isalpha() for ch in text)


def _labels(text: str) -> list[str]:
    return [match.group(0) for match in _LABEL_RE.finditer(text)]


def _candidate(source: str, target: str, *, base_target: str | None = None) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target) if base_target is not None else None
    ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    source_labels = _labels(source)
    target_labels = _labels(target)
    return {
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": ratio,
        "target_alpha_non_decreasing_vs_base": (target_alpha >= base_alpha if base_alpha is not None else None),
        "source_labels": source_labels,
        "target_labels": target_labels,
        "technical_label_sequence_exact": target_labels == source_labels,
    }


def _model_rows(
    *,
    model: str,
    hypotheses: list[dict[str, Any]],
    source: str,
    base_target: str,
) -> dict[str, Any]:
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
    return {"model": model, "candidates": rows}


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN20_DENSE_FIGURE_CLAUSE_DOE_ROOT",
            "work/run20-dense-figure-clause-boundary-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("dense-figure clause DOE requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        base_output = dict(base_run.get("output") or {})
        context_run_id = int(base_output["context_run_id"])
        contexts = {
            int(row["sequence_number"]): row
            for row in get_run_items(connection, context_run_id, kind="context_sentence")
        }
        context_run = get_run(connection, context_run_id)
        nlp_run_id = int((context_run.get("output") or {})["nlp_run_id"])
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document = get_document(connection, int(base_output["document_version_id"]))

    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("run20 source coverage drift")

    group_contexts = [contexts[index] for index in CONTEXT_SEQUENCES]
    if [int(group_contexts[0]["source_start"]), int(group_contexts[-1]["source_end"])] != [SOURCE_START, SOURCE_END]:
        raise RuntimeError("dense figure group span drift")
    source = "".join(str(row.get("source_text") or "") for row in group_contexts)
    if source != content[SOURCE_START:SOURCE_END]:
        raise RuntimeError("dense figure group immutable source mismatch")

    members = [
        row for row in base_rows
        if SOURCE_START <= int(row["source_start"]) and int(row["source_end"]) <= SOURCE_END
    ]
    if [int(row["sequence_number"]) for row in members] != MEMBER_SEQUENCES:
        raise RuntimeError("dense figure member sequence drift")
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("dense figure members do not reconstruct source")
    current_failures = [
        int(row["sequence_number"])
        for row in members
        if evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or "")).get("product_hard_passed") is not True
    ]
    if current_failures != EXPECTED_CURRENT_FAILURE_SEQUENCES:
        raise RuntimeError(f"dense figure current failure drift: {current_failures!r}")

    matches = list(_SPLIT_RE.finditer(source))
    if len(matches) != 1:
        raise RuntimeError(f"expected one source-defined clause split, got {len(matches)}")
    cut = SOURCE_START + matches[0].start()
    left_source = content[SOURCE_START:cut]
    right_source = content[cut:SOURCE_END]
    if left_source + right_source != source:
        raise RuntimeError("clause split does not preserve immutable source bytes")
    if not right_source.startswith(": But yet with this caution"):
        raise RuntimeError("source-defined right clause marker drift")

    group_tokens = [
        row for row in nlp_tokens
        if SOURCE_START <= int(row["source_start"]) and int(row["source_end"]) <= SOURCE_END
    ]
    left_tokens = [row for row in group_tokens if int(row["source_end"]) <= cut]
    right_tokens = [row for row in group_tokens if int(row["source_start"]) >= cut]
    if len(group_tokens) != EXPECTED_TOTAL_TOKENS:
        raise RuntimeError(f"group token-count drift: {len(group_tokens)}")
    if len(left_tokens) != EXPECTED_LEFT_TOKENS or len(right_tokens) != EXPECTED_RIGHT_TOKENS:
        raise RuntimeError(
            f"clause token-count drift: left={len(left_tokens)} right={len(right_tokens)}"
        )

    base_target = "".join(str(row.get("target_text") or "") for row in members)

    opus_asset = load_opus_asset()
    opus = OpusTranslator(device="cpu", compute_type="float32")
    opus_hypotheses = opus.translate(
        [left_source, right_source],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    tc_asset = load_tc_big_asset()
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    tc_hypotheses = tc_big.translate(
        [left_source, right_source],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if any(len(rows) != NUM_HYPOTHESES for rows in [*opus_hypotheses, *tc_hypotheses]):
        raise RuntimeError("clause DOE n-best cardinality drift")

    models: dict[str, Any] = {}
    for name, hypotheses in (("opus", opus_hypotheses), ("tc_big", tc_hypotheses)):
        left = _model_rows(
            model=name,
            hypotheses=hypotheses[0],
            source=left_source,
            base_target=None,
        )
        right = _model_rows(
            model=name,
            hypotheses=hypotheses[1],
            source=right_source,
            base_target=None,
        )
        rank0_target = str(left["candidates"][0]["target_text"]) + str(right["candidates"][0]["target_text"])
        rank0_eval = _candidate(source, rank0_target, base_target=base_target)
        models[name] = {
            "left": left,
            "right": right,
            "rank0_direct_concatenation_target": rank0_target,
            "rank0_direct_concatenation": rank0_eval,
            "rank0_direct_concatenation_contains_reflection_root": "отраж" in rank0_target.casefold(),
            "rank0_direct_concatenation_contains_reflexion_calque": "рефлексион" in rank0_target.casefold(),
        }

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only source-defined pre-colon two-chunk DOE for dense FIG. 6 hard omission",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "context_run_id": context_run_id,
        "context_sequences": CONTEXT_SEQUENCES,
        "member_sequences": MEMBER_SEQUENCES,
        "current_failure_sequences": current_failures,
        "source_start": SOURCE_START,
        "source_end": SOURCE_END,
        "source_text": source,
        "base_target": base_target,
        "split_contract": "source-defined-pre-major-clause-colon/1",
        "split_regex": _SPLIT_RE.pattern,
        "split_source_offset": cut,
        "left_source": left_source,
        "right_source": right_source,
        "left_nlp_token_count": len(left_tokens),
        "right_nlp_token_count": len(right_tokens),
        "total_nlp_token_count": len(group_tokens),
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "models": models,
        "opus_asset": {
            "manifest_sha256": opus_asset.manifest_sha256,
            "payload_tree_sha256": opus_asset.payload_tree_sha256,
        },
        "tc_big_asset": {
            "manifest_sha256": tc_asset.manifest_sha256,
            "payload_tree_sha256": tc_asset.payload_tree_sha256,
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
        raise RuntimeError("read-only dense figure clause DOE mutated database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "full-opticks-run20-dense-figure-clause-boundary-doe.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "split_source_offset": cut,
        "left_nlp_token_count": len(left_tokens),
        "right_nlp_token_count": len(right_tokens),
        "opus_rank0_strict": models["opus"]["rank0_direct_concatenation"]["strictly_eligible"],
        "opus_rank0_reflection_root": models["opus"]["rank0_direct_concatenation_contains_reflection_root"],
        "opus_rank0_reflexion_calque": models["opus"]["rank0_direct_concatenation_contains_reflexion_calque"],
        "tc_big_rank0_strict": models["tc_big"]["rank0_direct_concatenation"]["strictly_eligible"],
        "tc_big_rank0_reflection_root": models["tc_big"]["rank0_direct_concatenation_contains_reflection_root"],
        "tc_big_rank0_reflexion_calque": models["tc_big"]["rank0_direct_concatenation_contains_reflexion_calque"],
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
