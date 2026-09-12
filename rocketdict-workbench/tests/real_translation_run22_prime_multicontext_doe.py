from __future__ import annotations

"""Read-only OPUS/TC-big DOE for run22 prime-notation multi-context groups.

Historical prime experiments translated individual Stage12/Stage10 units. This
experiment changes source geometry materially: it translates four coherent
multi-context source groups from the exact persisted run22 database, including a
suspected false boundary at ``_English_ | Miles``. Six raw hypotheses are
recorded from each pinned model, but no non-rank0 candidate is authorized for
automatic Product selection and the database remains immutable.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run22-prime-multicontext-doe/1"
BASE_DATABASE_SHA256 = "5cc0bec1d8ab1c9b0eadb9441819d84676f005a5a3bbb3a068745338469b3206"
BASE_RUN_ID = 22
BASE_OUTPUT_SHA256 = "41cb94e6a2732aee597d8e630cc248487d6e0b7ce5fb9a794d01ecda7f2edb48"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
GROUPS = {
    "angle_derivation_a": [590, 591],
    "angle_derivation_b": [593, 594, 595],
    "telescope_arcseconds": [674, 675, 676],
    "english_miles_boundary": [2496, 2497],
}
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.55


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


def _candidate(source: str, target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    ratio = _alpha(target) / _alpha(source) if _alpha(source) else 1.0
    ratio_passed = MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    admissible = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and ratio_passed
    )
    return {
        "mechanically_admissible": admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_passed": ratio_passed,
    }


def _model_result(source: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for h in hypotheses:
        target = str(h.get("text") or "")
        rows.append(
            {
                "rank": int(h.get("rank") or 0),
                "score": h.get("score"),
                "target_text": target,
                **_candidate(source, target),
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
    root = Path(os.environ.get("ROCKETDICT_RUN22_PRIME_MULTICONTEXT_ROOT", "work/run22-prime-multicontext-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("prime multi-context DOE requires exact persisted run22 database")
    database_sha_before = _sha(database)

    with connect(database, readonly=True) as connection:
        base_run = get_run(connection, BASE_RUN_ID)
        base_rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda row: int(row["source_start"]))
        base_output = dict(base_run.get("output") or {})
        context_run_id = int(base_output["context_run_id"])
        contexts = get_run_items(connection, context_run_id, kind="context_sentence")
        document = get_document(connection, int(base_output["document_version_id"]))
    if str(base_run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run22 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run22 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("run22 source coverage drift")
    by_context = {int(row["sequence_number"]): row for row in contexts}

    group_inputs: list[dict[str, Any]] = []
    for name, sequences in GROUPS.items():
        context_rows = [by_context[seq] for seq in sequences]
        if [int(row["sequence_number"]) for row in context_rows] != sequences:
            raise RuntimeError(f"{name} context sequence drift")
        start = int(context_rows[0]["source_start"])
        end = int(context_rows[-1]["source_end"])
        source = "".join(str(row.get("source_text") or "") for row in context_rows)
        if source != content[start:end]:
            raise RuntimeError(f"{name} source is not byte-exact")
        members = [
            row for row in base_rows
            if start <= int(row["source_start"]) and int(row["source_end"]) <= end
        ]
        if "".join(str(row.get("source_text") or "") for row in members) != source:
            raise RuntimeError(f"{name} Stage12 members do not reconstruct group")
        base_target = "".join(str(row.get("target_text") or "") for row in members)
        base_verdict = evaluate_rescue_pair(source, base_target)
        member_failures = []
        for row in members:
            verdict = evaluate_rescue_pair(str(row.get("source_text") or ""), str(row.get("target_text") or ""))
            if verdict.get("product_hard_passed") is not True:
                member_failures.append(
                    {
                        "sequence_number": int(row["sequence_number"]),
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "verdict": verdict,
                    }
                )
        group_inputs.append(
            {
                "name": name,
                "context_sequences": sequences,
                "source_start": start,
                "source_end": end,
                "context_token_count": sum(int((row.get("payload") or {}).get("token_count") or 0) for row in context_rows),
                "source_text": source,
                "base_target": base_target,
                "base_aggregate_verdict": base_verdict,
                "base_member_hard_failures": member_failures,
                "member_stage12_sequences": [int(row["sequence_number"]) for row in members],
            }
        )

    sources = [row["source_text"] for row in group_inputs]
    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    opus_hypotheses = opus.translate(sources, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
    tc_hypotheses = tc_big.translate(sources, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
    if len(opus_hypotheses) != len(group_inputs) or len(tc_hypotheses) != len(group_inputs):
        raise RuntimeError("prime multi-context model cardinality drift")

    cases: list[dict[str, Any]] = []
    for group, oh, th in zip(group_inputs, opus_hypotheses, tc_hypotheses, strict=True):
        if len(oh) != NUM_HYPOTHESES or len(th) != NUM_HYPOTHESES:
            raise RuntimeError("prime multi-context n-best cardinality drift")
        cases.append(
            {
                **group,
                "opus": _model_result(str(group["source_text"]), oh),
                "tc_big": _model_result(str(group["source_text"]), th),
            }
        )

    if _sha(database) != database_sha_before:
        raise RuntimeError("read-only prime multi-context DOE mutated database")
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only multi-context source-geometry DOE for persisted run22 prime-notation residual families",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "n_best_cherry_picking": False,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "groups": GROUPS,
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "cases": cases,
        "rank0_mechanically_admissible": {
            "opus": [case["name"] for case in cases if case["opus"]["rank0_mechanically_admissible"]],
            "tc_big": [case["name"] for case in cases if case["tc_big"]["rank0_mechanically_admissible"]],
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
    (root / "run22-prime-multicontext-doe.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "rank0_mechanically_admissible": evidence["rank0_mechanically_admissible"],
        "case_count": len(cases),
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
