from __future__ import annotations

"""Exact-run20 read-only OPUS/TC-big DOE for denominator-truncation context 1460.

The current Stage12 split cuts one Stage10 sentence after ``For the upper ``.
The first split row corrupts ``1222/6000`` to ``1222/600`` and the aggregate
split target also contains an awkward lexical boundary. This DOE retranslates
the immutable 87-token Stage10 context as a whole with both pinned models.

All six hypotheses are retained as evidence, but only rank0 is a possible future
research candidate. The database is read-only and no target/source repair,
literal injection, placeholder, n-best selection, or evaluator change occurs.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator, load_opus_asset
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-fraction-context-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 14, "length": 0, "unique": 33}
CONTEXT_SEQUENCE = 1460
MEMBER_SEQUENCES = [1570, 1571]
SOURCE_START = 267212
SOURCE_END = 267616
EXPECTED_TOKEN_COUNT = 87
EXPECTED_FAILURE_SEQUENCES = [1570]
REQUIRED_FRACTIONS = ["121/600", "1222/6000", "1/8"]
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
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def _candidate(source: str, target: str, *, base_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    lowered = target.casefold()
    semantic_anchors = {
        "glass": "стекл" in lowered,
        "diameter": "диаметр" in lowered,
        "inch": "дюйм" in lowered,
        "eye": "глаз" in lowered,
        "required_fractions": all(value in target for value in REQUIRED_FRACTIONS),
        "distance_8_inches": "8" in target and "дюйм" in lowered,
    }
    return {
        "mechanical_verdict": verdict,
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": target_alpha / source_alpha if source_alpha else 1.0,
        "base_alpha_count": base_alpha,
        "target_alpha_count": target_alpha,
        "base_alpha_retention_ratio": target_alpha / base_alpha if base_alpha else 1.0,
        "semantic_anchors": semantic_anchors,
        "semantic_anchors_all_present": all(semantic_anchors.values()),
    }


def _model_result(name: str, hypotheses: list[dict[str, Any]], source: str, base_target: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        target = str(hypothesis.get("text") or "")
        rows.append({"rank": int(hypothesis.get("rank") or 0), "score": hypothesis.get("score"), "target_text": target, **_candidate(source, target, base_target=base_target)})
    return {"model": name, "candidates": rows, "rank0_strictly_eligible": rows[0]["strictly_eligible"], "rank0_semantic_anchors_all_present": rows[0]["semantic_anchors_all_present"]}


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN20_FRACTION_CONTEXT_DOE_ROOT", "work/run20-fraction-context-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("fraction-context DOE requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda row: int(row["sequence_number"]))
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
        raise RuntimeError("fraction context missing")
    if [int(context["source_start"]), int(context["source_end"])] != [SOURCE_START, SOURCE_END]:
        raise RuntimeError("fraction context span drift")
    source = str(context.get("source_text") or "")
    if source != content[SOURCE_START:SOURCE_END]:
        raise RuntimeError("fraction immutable source mismatch")
    token_count = int((context.get("payload") or {}).get("token_count") or 0)
    if token_count != EXPECTED_TOKEN_COUNT:
        raise RuntimeError(f"fraction context token-count drift: {token_count}")

    members = [row for row in base_rows if SOURCE_START <= int(row["source_start"]) and int(row["source_end"]) <= SOURCE_END]
    if [int(row["sequence_number"]) for row in members] != MEMBER_SEQUENCES:
        raise RuntimeError("fraction member sequence drift")
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("fraction members do not reconstruct context")
    failures = [int(row["sequence_number"]) for row in members if evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or "")).get("product_hard_passed") is not True]
    if failures != EXPECTED_FAILURE_SEQUENCES:
        raise RuntimeError(f"fraction member hard-failure drift: {failures}")
    base_target = "".join(str(row.get("target_text") or "") for row in members)

    opus_asset = load_opus_asset()
    opus = OpusTranslator(device="cpu", compute_type="float32")
    opus_hypotheses = opus.translate([source], beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)[0]
    tc_asset = load_tc_big_asset()
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    tc_hypotheses = tc_big.translate([source], beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)[0]
    if len(opus_hypotheses) != NUM_HYPOTHESES or len(tc_hypotheses) != NUM_HYPOTHESES:
        raise RuntimeError("fraction context n-best cardinality drift")

    models = {"opus": _model_result("opus-en-ru-ct2", opus_hypotheses, source, base_target), "tc_big": _model_result("tc-big-en-zle", tc_hypotheses, source, base_target)}
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "exact-run20 whole-Stage10-context OPUS/TC-big DOE for isolated denominator truncation",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "context_run_id": context_run_id,
        "context_sequence": CONTEXT_SEQUENCE,
        "member_sequences": MEMBER_SEQUENCES,
        "member_failure_sequences": failures,
        "source_start": SOURCE_START,
        "source_end": SOURCE_END,
        "nlp_token_count": token_count,
        "source_text": source,
        "base_target": base_target,
        "base_target_contains_split_join_artifact": "слоевСтекло" in base_target,
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "models": models,
        "opus_asset": {"manifest_sha256": opus_asset.manifest_sha256, "payload_tree_sha256": opus_asset.payload_tree_sha256},
        "tc_big_asset": {"manifest_sha256": tc_asset.manifest_sha256, "payload_tree_sha256": tc_asset.payload_tree_sha256},
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
        raise RuntimeError("read-only fraction-context DOE mutated database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "full-opticks-run20-fraction-context-doe.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "context_sequence": CONTEXT_SEQUENCE,
        "base_target_contains_split_join_artifact": evidence["base_target_contains_split_join_artifact"],
        "opus_rank0_strict": models["opus"]["rank0_strictly_eligible"],
        "opus_rank0_semantic_anchors": models["opus"]["rank0_semantic_anchors_all_present"],
        "tc_big_rank0_strict": models["tc_big"]["rank0_strictly_eligible"],
        "tc_big_rank0_semantic_anchors": models["tc_big"]["rank0_semantic_anchors_all_present"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
