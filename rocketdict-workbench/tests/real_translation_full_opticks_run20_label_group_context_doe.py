from __future__ import annotations

"""Read-only whole-group OPUS/TC-big DOE for run20 technical-label content loss.

The immutable source geometry is the planner-created group spanning Stage10
contexts 1640+1641.  It contains the complete ``[Illustration: FIG. 6.]``
marker and the dense optical construction labels around the current numeric
failure.  The experiment translates the complete source group without target
repair and records six raw hypotheses per model.  It never authorizes automatic
n-best selection or Product-default promotion.
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

SCHEMA = "rocketdict-full-opticks-run20-label-group-context-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
CONTEXT_SEQUENCES = [1640, 1641]
EXPECTED_SOURCE_START = 302134
EXPECTED_SOURCE_END = 302883
EXPECTED_CONTEXT_TOKEN_COUNTS = [5, 171]
EXPECTED_TOTAL_TOKEN_COUNT = 176
EXPECTED_MEMBER_SEQUENCES = [1761, 1762, 1763]
EXPECTED_MEMBER_STARTS = [302134, 302426, 302721]
CURRENT_FAILURE_SEQUENCE = 1762
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.50
MIN_BASE_ALPHA_RETENTION = 0.95

# Source-owned optical/figure labels.  This deliberately covers both A1/1I
# orientations and short all-uppercase labels such as HI/HL/FIG.  It does not
# infer translations or inspect target text for DOE eligibility.
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
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _alpha(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _technical_labels(text: str) -> Counter[str]:
    return Counter(_TECHNICAL_LABEL_RE.findall(text))


def _candidate(source: str, target: str, *, base_target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    source_ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    base_retention = target_alpha / base_alpha if base_alpha else (1.0 if target_alpha == 0 else float("inf"))
    source_labels = _technical_labels(source)
    target_labels = _technical_labels(target)
    labels_exact = source_labels == target_labels
    illustration_exact = bool(
        "[Illustration: FIG. 6.]" in source
        and (
            "[Illustration: FIG. 6.]" in target
            or "[Иллюстрация: FIG. 6.]" in target
        )
    )
    admissible = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and labels_exact
        and illustration_exact
        and MIN_SOURCE_ALPHA_RATIO <= source_ratio <= MAX_SOURCE_ALPHA_RATIO
        and base_retention >= MIN_BASE_ALPHA_RETENTION
    )
    return {
        "mechanically_admissible": admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_technical_labels": dict(source_labels),
        "target_technical_labels": dict(target_labels),
        "technical_labels_exact": labels_exact,
        "illustration_marker_exact": illustration_exact,
        "source_alpha": source_alpha,
        "base_target_alpha": base_alpha,
        "candidate_target_alpha": target_alpha,
        "source_alpha_ratio": source_ratio,
        "base_alpha_retention": base_retention,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "minimum_base_alpha_retention": MIN_BASE_ALPHA_RETENTION,
    }


def _model_result(
    name: str,
    hypotheses: list[dict[str, Any]],
    source: str,
    base_target: str,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        target = str(hypothesis.get("text") or "")
        candidates.append(
            {
                "rank": int(hypothesis.get("rank") or 0),
                "score": hypothesis.get("score"),
                "target_text": target,
                **_candidate(source, target, base_target=base_target),
            }
        )
    admissible = [
        int(row["rank"])
        for row in candidates
        if row["mechanically_admissible"] is True
    ]
    return {
        "model": name,
        "candidates": candidates,
        "rank0_mechanically_admissible": bool(
            candidates and candidates[0]["mechanically_admissible"] is True
        ),
        "mechanically_admissible_ranks": admissible,
        "first_mechanically_admissible_rank": None if not admissible else admissible[0],
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN20_LABEL_GROUP_DOE_ROOT",
            "work/run20-label-group-context-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("label-group DOE requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        output = dict(run.get("output") or {})
        context_run_id = int(output["context_run_id"])
        context_rows = sorted(
            get_run_items(connection, context_run_id, kind="context_sentence"),
            key=lambda row: int(row["sequence_number"]),
        )
        base_rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(output["document_version_id"]))

    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in base_rows) != content:
        raise RuntimeError("run20 source coverage is not byte-exact")

    contexts_by_sequence = {int(row["sequence_number"]): row for row in context_rows}
    contexts = [contexts_by_sequence[sequence] for sequence in CONTEXT_SEQUENCES]
    if [int(row["source_start"]) for row in contexts] != [302134, 302154]:
        raise RuntimeError("label-group Stage10 start geometry drift")
    if int(contexts[0]["source_start"]) != EXPECTED_SOURCE_START or int(contexts[-1]["source_end"]) != EXPECTED_SOURCE_END:
        raise RuntimeError("label-group Stage10 span drift")
    token_counts = [int((row.get("payload") or {}).get("token_count") or 0) for row in contexts]
    if token_counts != EXPECTED_CONTEXT_TOKEN_COUNTS or sum(token_counts) != EXPECTED_TOTAL_TOKEN_COUNT:
        raise RuntimeError(f"label-group Stage10 token-count drift: {token_counts!r}")
    source = "".join(str(row.get("source_text") or "") for row in contexts)
    if source != content[EXPECTED_SOURCE_START:EXPECTED_SOURCE_END]:
        raise RuntimeError("label-group immutable source mismatch")
    if "[Illustration: FIG. 6.]" not in source:
        raise RuntimeError("label-group illustration identity drift")

    members = [
        row
        for row in base_rows
        if EXPECTED_SOURCE_START <= int(row["source_start"])
        and int(row["source_end"]) <= EXPECTED_SOURCE_END
    ]
    if [int(row["sequence_number"]) for row in members] != EXPECTED_MEMBER_SEQUENCES:
        raise RuntimeError("label-group run20 member sequence drift")
    if [int(row["source_start"]) for row in members] != EXPECTED_MEMBER_STARTS:
        raise RuntimeError("label-group run20 member start drift")
    if "".join(str(row.get("source_text") or "") for row in members) != source:
        raise RuntimeError("label-group run20 members do not reconstruct source")
    base_target = "".join(str(row.get("target_text") or "") for row in members)
    base_member_verdicts = {
        int(row["sequence_number"]): evaluate_rescue_pair(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        for row in members
    }
    failing_members = [
        sequence
        for sequence, verdict in base_member_verdicts.items()
        if verdict.get("product_hard_passed") is not True
    ]
    if failing_members != [CURRENT_FAILURE_SEQUENCE]:
        raise RuntimeError(f"label-group current hard-failure identity drift: {failing_members!r}")

    opus = OpusTranslator(device="cpu", compute_type="float32")
    opus_hypotheses = opus.translate(
        [source],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )[0]
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    tc_big_hypotheses = tc_big.translate(
        [source],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )[0]
    if len(opus_hypotheses) != NUM_HYPOTHESES or len(tc_big_hypotheses) != NUM_HYPOTHESES:
        raise RuntimeError("label-group n-best cardinality drift")

    asset = load_tc_big_asset()
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only whole Stage10-group OPUS/TC-big DOE for dense technical-label content loss",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "context_run_id": context_run_id,
        "context_sequences": CONTEXT_SEQUENCES,
        "context_token_counts": token_counts,
        "total_nlp_token_count": sum(token_counts),
        "source_start": EXPECTED_SOURCE_START,
        "source_end": EXPECTED_SOURCE_END,
        "member_sequences": EXPECTED_MEMBER_SEQUENCES,
        "member_source_starts": EXPECTED_MEMBER_STARTS,
        "current_failure_sequences": failing_members,
        "source_text": source,
        "base_target": base_target,
        "source_technical_labels": dict(_technical_labels(source)),
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
        "models": {
            "opus": _model_result("opus-en-ru-ct2", opus_hypotheses, source, base_target),
            "tc_big": _model_result("tc-big-en-zle", tc_big_hypotheses, source, base_target),
        },
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
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
    }
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("read-only label-group DOE mutated run20 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "full-opticks-run20-label-group-context-doe.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "context_sequences": CONTEXT_SEQUENCES,
        "total_nlp_token_count": EXPECTED_TOTAL_TOKEN_COUNT,
        "opus_rank0_admissible": evidence["models"]["opus"]["rank0_mechanically_admissible"],
        "opus_admissible_ranks": evidence["models"]["opus"]["mechanically_admissible_ranks"],
        "tc_big_rank0_admissible": evidence["models"]["tc_big"]["rank0_mechanically_admissible"],
        "tc_big_admissible_ranks": evidence["models"]["tc_big"]["mechanically_admissible_ranks"],
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
