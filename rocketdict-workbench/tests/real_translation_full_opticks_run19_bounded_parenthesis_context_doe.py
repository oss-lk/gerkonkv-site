from __future__ import annotations

"""Read-only run19 DOE for bounded split Stage10 contexts with round-parenthesis debt."""

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

SCHEMA = "rocketdict-full-opticks-run19-bounded-parenthesis-context-doe/1"
BASE_DATABASE_SHA256 = "8519ea592b0bd948b68980ed19b710f05f20f9e0a60f0cb6c3e1a7763d5a8f76"
BASE_RUN_ID = 19
BASE_OUTPUT_SHA256 = "48096e0c1085c0598bc8abf212a2b2ba9a1109bb232fa2487c0472f35c06a1d9"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_COUNTS = {"numeric_symbol": 20, "punctuation": 15, "length": 0, "unique": 34}
BASE_SEGMENTS = 3342
TOKEN_CAP = 160
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.75
MAX_SOURCE_ALPHA_RATIO = 1.50
EXPECTED_CONTEXTS = {
    668: {"source_start": 132378, "source_end": 132834, "tokens": 104, "members": 2},
    1393: {"source_start": 255534, "source_end": 256014, "tokens": 108, "members": 2},
    1977: {"source_start": 372983, "source_end": 373528, "tokens": 109, "members": 2},
    2969: {"source_start": 581436, "source_end": 582111, "tokens": 136, "members": 2},
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["source_start"]))


def _inventory(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"numeric_symbol": 0, "punctuation": 0, "length": 0}
    union: set[int] = set()
    for row in _ordered(rows):
        verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
        sequence = int(row["sequence_number"])
        failures = {
            "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
            "punctuation": verdict.get("punctuation_passed") is not True,
            "length": verdict.get("length_passed") is not True,
        }
        for key, failed in failures.items():
            if failed:
                counts[key] += 1
                union.add(sequence)
    return {**counts, "unique": len(union)}


def _planner_context(row: dict[str, Any]) -> tuple[int, int] | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    try:
        return int(planner["context_sentence_start"]), int(planner["context_sentence_end"])
    except (KeyError, TypeError, ValueError):
        return None


def _alpha_count(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def _alpha_ratio(source: str, target: str) -> float:
    source_alpha = _alpha_count(source)
    target_alpha = _alpha_count(target)
    return target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))


def _candidate(source: str, target: str, *, base_target: str, rank: int, score: Any) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _alpha_ratio(source, target)
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    alpha_non_decreasing = _alpha_count(target) >= _alpha_count(base_target)
    round_exact = source.count("(") == target.count("(") and source.count(")") == target.count(")")
    admissible = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and round_exact
        and ratio_passed
        and alpha_non_decreasing
    )
    return {
        "rank": rank,
        "score": score,
        "target_text": target,
        "mechanically_admissible": admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_round_parentheses": [source.count("("), source.count(")")],
        "target_round_parentheses": [target.count("("), target.count(")")],
        "round_parentheses_exact": round_exact,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "source_alpha_ratio_passed": ratio_passed,
        "target_alpha_base": _alpha_count(base_target),
        "target_alpha_candidate": _alpha_count(target),
        "target_alpha_non_decreasing": alpha_non_decreasing,
    }


def _counterfactual(
    base_rows: list[dict[str, Any]],
    selected: dict[int, str],
    prepared: dict[int, dict[str, Any]],
    content: str,
) -> dict[str, Any]:
    removed = {
        int(row["id"])
        for context_sequence in selected
        for row in prepared[context_sequence]["member_rows"]
    }
    rows = [dict(row) for row in base_rows if int(row["id"]) not in removed]
    for context_sequence, target in selected.items():
        case = prepared[context_sequence]
        rows.append({
            "id": -context_sequence,
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": case["source_start"],
            "source_end": case["source_end"],
            "source_text": case["source_text"],
            "target_text": target,
            "payload": {"research_bounded_parenthesis_context": True},
        })
    rows.sort(key=lambda row: int(row["source_start"]))
    for sequence, row in enumerate(rows):
        row["sequence_number"] = sequence
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("parenthesis DOE counterfactual source coverage drift")
    counts = _inventory(rows)
    if any(counts[key] > BASE_COUNTS[key] for key in BASE_COUNTS):
        raise RuntimeError(f"parenthesis DOE counterfactual regression: {counts!r}")
    return {"selected_context_sequences": sorted(selected), "selected_context_count": len(selected), "hard_gate_counts": counts, "segment_count": len(rows)}


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN19_PAREN_CONTEXT_ROOT", "work/full-opticks-run19-bounded-parenthesis-context-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("parenthesis DOE requires exact persisted run19 database")
    db_sha_before = _sha(database)

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = _ordered(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"))
        base_output = dict(base_run.get("output") or {})
        context_run_id = int(base_output["context_run_id"])
        context_rows = get_run_items(connection, context_run_id, kind="context_sentence")
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run19 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run19 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("run19 source coverage drift")
    if len(base_rows) != BASE_SEGMENTS or _inventory(base_rows) != BASE_COUNTS:
        raise RuntimeError("run19 baseline count/segment drift")

    contexts = {int(row["sequence_number"]): row for row in context_rows}
    prepared: dict[int, dict[str, Any]] = {}
    for sequence, expected in EXPECTED_CONTEXTS.items():
        context = contexts.get(sequence)
        if context is None:
            raise RuntimeError(f"missing Stage10 context {sequence}")
        start, end = int(context["source_start"]), int(context["source_end"])
        source = str(context.get("source_text") or "")
        token_count = int((context.get("payload") or {}).get("token_count") or 0)
        if [start, end, token_count] != [expected["source_start"], expected["source_end"], expected["tokens"]]:
            raise RuntimeError(f"context identity drift: {sequence}")
        if token_count > TOKEN_CAP or content[start:end] != source:
            raise RuntimeError(f"context cap/source drift: {sequence}")
        members = [row for row in base_rows if _planner_context(row) == (sequence, sequence)]
        members = _ordered(members)
        if len(members) != expected["members"] or "".join(str(row.get("source_text") or "") for row in members) != source:
            raise RuntimeError(f"context member geometry drift: {sequence}")
        base_target = "".join(str(row.get("target_text") or "") for row in members)
        source_round = [source.count("("), source.count(")")]
        target_round = [base_target.count("("), base_target.count(")")]
        if source_round == target_round or source_round == [0, 0]:
            raise RuntimeError(f"context is no longer a round-parenthesis residual: {sequence}")
        for row in members:
            verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
            if (verdict.get("numeric_symbol") or {}).get("passed") is not True or verdict.get("length_passed") is not True:
                raise RuntimeError(f"context has non-punctuation hard debt: {sequence}")
        prepared[sequence] = {
            "context_sequence": sequence,
            "source_start": start,
            "source_end": end,
            "source_text": source,
            "nlp_token_count": token_count,
            "member_rows": members,
            "member_sequences": [int(row["sequence_number"]) for row in members],
            "base_target": base_target,
            "source_round_parentheses": source_round,
            "base_target_round_parentheses": target_round,
        }

    ordered_cases = [prepared[key] for key in sorted(prepared)]
    texts = [str(case["source_text"]) for case in ordered_cases]
    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_asset = load_tc_big_asset()
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    opus_groups = opus.translate(texts, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
    tc_groups = tc_big.translate(texts, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
    if any(len(group) != NUM_HYPOTHESES for group in opus_groups + tc_groups):
        raise RuntimeError("parenthesis DOE n-best cardinality drift")

    strategies = {"opus_rank0": {}, "tc_big_rank0": {}, "opus_first_admissible": {}, "tc_big_first_admissible": {}}
    cases: list[dict[str, Any]] = []
    for case, opus_hypotheses, tc_hypotheses in zip(ordered_cases, opus_groups, tc_groups, strict=True):
        models: dict[str, Any] = {}
        for name, hypotheses in (("opus", opus_hypotheses), ("tc_big", tc_hypotheses)):
            evaluated = [
                _candidate(str(case["source_text"]), str(hypothesis.get("text") or ""), base_target=str(case["base_target"]), rank=rank, score=hypothesis.get("score"))
                for rank, hypothesis in enumerate(hypotheses)
            ]
            admissible = [row for row in evaluated if row["mechanically_admissible"]]
            first = None if not admissible else int(admissible[0]["rank"])
            if evaluated[0]["mechanically_admissible"]:
                strategies[f"{name}_rank0"][int(case["context_sequence"])] = str(evaluated[0]["target_text"])
            if first is not None:
                strategies[f"{name}_first_admissible"][int(case["context_sequence"])] = str(evaluated[first]["target_text"])
            models[name] = {
                "candidates": evaluated,
                "rank0_mechanically_admissible": bool(evaluated[0]["mechanically_admissible"]),
                "first_mechanically_admissible_rank": first,
                "mechanically_admissible_ranks": [int(row["rank"]) for row in admissible],
            }
        cases.append({**{key: value for key, value in case.items() if key != "member_rows"}, "models": models})

    counterfactuals = {name: _counterfactual(base_rows, selected, prepared, content) for name, selected in strategies.items()}
    if _sha(database) != db_sha_before:
        raise RuntimeError("parenthesis DOE mutated run19 database")
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only exact-run19 OPUS/TC-big n-best DOE for <=160-token split Stage10 contexts with round-parenthesis debt",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": BASE_COUNTS,
        "base_segment_count": BASE_SEGMENTS,
        "token_cap": TOKEN_CAP,
        "context_sequences": sorted(prepared),
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "cases": cases,
        "counterfactuals": counterfactuals,
        "tc_big_asset": {
            "repository": tc_asset.repository,
            "revision": tc_asset.revision,
            "model_safetensors_sha256": tc_asset.model_safetensors_sha256,
            "license": tc_asset.license,
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
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    (root / "full-opticks-run19-bounded-parenthesis-context-doe.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": SCHEMA, "contexts": sorted(prepared), "counterfactuals": counterfactuals, "evidence_sha256": payload["evidence_sha256"]}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
