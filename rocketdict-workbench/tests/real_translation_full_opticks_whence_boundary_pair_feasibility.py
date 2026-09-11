from __future__ import annotations

"""Read-only feasibility for the split ``whence is it | but from ... ?`` question."""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-whence-boundary-pair-feasibility/1"
BASE_DATABASE_SHA256 = "dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304"
BASE_RUN_ID = 14
BASE_OUTPUT_SHA256 = "12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_FIRST_START = 522555
EXPECTED_SECOND_START = 522572
_FIRST_RE = re.compile(r"\bwhence\s+is\s+it\s*$", re.IGNORECASE)
_SECOND_RE = re.compile(r"^\s*but\s+from\b", re.IGNORECASE)


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


def _ratio(source: str, target: str) -> float:
    source_alpha = sum(char.isalpha() for char in source)
    target_alpha = sum(char.isalpha() for char in target)
    return target_alpha / source_alpha if source_alpha else 1.0


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_WHENCE_PAIR_ROOT", "work/whence-boundary-pair-feasibility")).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("Whence pair feasibility requires exact persisted run-14 database")
    asset = load_tc_big_asset()

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-14 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    content = str(document["content_text"])

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for first, second in zip(rows, rows[1:]):
        first_source = str(first.get("source_text") or "")
        second_source = str(second.get("source_text") or "")
        if int(first["source_end"]) != int(second["source_start"]):
            continue
        if _FIRST_RE.search(first_source) is None or _SECOND_RE.search(second_source) is None:
            continue
        if not second_source.rstrip().endswith("?"):
            continue
        pairs.append((first, second))
    if len(pairs) != 1:
        raise RuntimeError(f"whence pair cohort drift: {len(pairs)}")
    first, second = pairs[0]
    if (int(first["source_start"]), int(second["source_start"])) != (
        EXPECTED_FIRST_START,
        EXPECTED_SECOND_START,
    ):
        raise RuntimeError("whence pair identity drift")
    combined_source = str(first["source_text"]) + str(second["source_text"])
    start = int(first["source_start"])
    end = int(second["source_end"])
    if combined_source != content[start:end]:
        raise RuntimeError("whence pair source is not byte-exact")

    translator = TcBigTranslator(device="cpu", compute_type="float32")
    hypotheses = translator.translate(
        [combined_source], beam_size=6, num_hypotheses=6, max_decoding_length=512
    )[0]
    evaluated: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        target = str(hypothesis.get("text") or "")
        verdict = evaluate_rescue_pair(combined_source, target)
        emphasis = compare_emphasis_markup_preservation(combined_source, target)
        lowered = target.casefold()
        semantic_anchors = {
            "whence_relation": "откуда" in lowered or "как не" in lowered,
            "attractive_power": "притяг" in lowered,
            "water": "вод" in lowered,
            "salt": "сол" in lowered,
            "heat": "тепл" in lowered or "жар" in lowered,
        }
        evaluated.append(
            {
                "rank": int(hypothesis["rank"]),
                "score": hypothesis.get("score"),
                "target_text": target,
                "strictly_eligible": verdict.get("strictly_eligible") is True,
                "product_hard_passed": verdict.get("product_hard_passed") is True,
                "punctuation_passed": verdict.get("punctuation_passed") is True,
                "length_passed": verdict.get("length_passed") is True,
                "emphasis_passed": emphasis.get("passed") is True,
                "source_alpha_ratio": _ratio(combined_source, target),
                "semantic_anchors": semantic_anchors,
                "all_semantic_anchors": all(semantic_anchors.values()),
                "verdict": verdict,
                "emphasis_markup": emphasis,
            }
        )

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only TC-big feasibility for a falsely split interrogative boundary",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "database_mutated": False,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_run_id": BASE_RUN_ID,
        "base_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "pair_count": 1,
        "first_source_start": int(first["source_start"]),
        "second_source_start": int(second["source_start"]),
        "combined_source": combined_source,
        "base_targets": [str(first.get("target_text") or ""), str(second.get("target_text") or "")],
        "hypotheses": evaluated,
        "strict_candidate_ranks": [row["rank"] for row in evaluated if row["strictly_eligible"]],
        "semantic_anchor_candidate_ranks": [row["rank"] for row in evaluated if row["all_semantic_anchors"]],
        "strict_and_semantic_candidate_ranks": [
            row["rank"] for row in evaluated if row["strictly_eligible"] and row["all_semantic_anchors"]
        ],
        "asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
        },
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-whence-boundary-pair-feasibility.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "strict_candidate_ranks": evidence["strict_candidate_ranks"],
                "semantic_anchor_candidate_ranks": evidence["semantic_anchor_candidate_ranks"],
                "strict_and_semantic_candidate_ranks": evidence["strict_and_semantic_candidate_ranks"],
                "targets": [row["target_text"] for row in evaluated],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
