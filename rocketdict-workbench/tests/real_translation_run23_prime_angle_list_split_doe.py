from __future__ import annotations

"""Read-only rank0 DOE for the residual four-pair angular prime list family.

The family predicate is source-defined: one Stage12 row contains exactly four
``N' M''`` pairs and lexical angular/secant anchors.  The experiment compares
whole-row rank0 with three immutable source partitions around the complete
angular clause.  Every persisted candidate is a concatenation of unmodified
raw rank0 model outputs; no target symbol injection, placeholders, target
repair, or n-best selection is allowed.
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
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run23-prime-angle-list-split-doe/1"
BASE_DATABASE_SHA256 = "75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8"
BASE_RUN_ID = 23
BASE_OUTPUT_SHA256 = "976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_FAMILY_COUNT = 1
EXPECTED_FAMILY_SEQUENCE = 2346
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768
MIN_SOURCE_ALPHA_RATIO = 0.60
MAX_SOURCE_ALPHA_RATIO = 1.60
_PAIR_RE = re.compile(r"(?<!\d)(?P<minute>\d+)'\s+(?P<second>\d+)''(?!')")
_ANGLES_RE = re.compile(r"\bthe\s+Angles\b", re.IGNORECASE)
_SECANTS_RE = re.compile(r"\bSecants\b", re.IGNORECASE)


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
    return sum(ch.isalpha() for ch in text)


def _family_partition(source: str) -> dict[str, Any] | None:
    pairs = list(_PAIR_RE.finditer(source))
    if len(pairs) != 4 or _SECANTS_RE.search(source) is None:
        return None
    angles = list(_ANGLES_RE.finditer(source, 0, pairs[0].start()))
    if not angles:
        return None
    clause_start = angles[-1].start()
    clause_end = pairs[-1].end()
    prefix = source[:clause_start]
    clause = source[clause_start:clause_end]
    suffix = source[clause_end:]
    if prefix + clause + suffix != source:
        raise RuntimeError("angle-list source partition drift")
    return {
        "prefix": prefix,
        "clause": clause,
        "suffix": suffix,
        "pairs": [
            {"minutes": m.group("minute"), "seconds": m.group("second")}
            for m in pairs
        ],
    }


def _translate_rank0(translator: Any, parts: list[str]) -> tuple[list[str], list[Any]]:
    generated = translator.translate(
        parts,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != len(parts) or any(len(rows) != 1 for rows in generated):
        raise RuntimeError("prime angle-list rank0 cardinality drift")
    ranks = [int(rows[0]["rank"]) for rows in generated]
    if any(rank != 0 for rank in ranks):
        raise RuntimeError(f"prime angle-list non-rank0 hypothesis: {ranks!r}")
    return (
        [str(rows[0].get("text") or "") for rows in generated],
        [rows[0].get("score") for rows in generated],
    )


def _evaluate(source: str, target: str, *, parts: list[str], targets: list[str]) -> dict[str, Any]:
    aggregate = evaluate_rescue_pair(source, target)
    part_evaluations = [
        evaluate_rescue_pair(part, candidate)
        for part, candidate in zip(parts, targets, strict=True)
    ]
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    mechanically_admissible = bool(
        aggregate.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    )
    return {
        "candidate_target_text": target,
        "aggregate_evaluation": aggregate,
        "part_evaluations": part_evaluations,
        "emphasis_markup": emphasis,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "mechanically_admissible": mechanically_admissible,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN23_PRIME_ANGLE_LIST_SPLIT_DOE_ROOT",
            "work/run23-prime-angle-list-split-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("prime angle-list DOE requires exact run23 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        output = dict(run.get("output") or {})
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run23 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run23 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run23 source coverage drift")

    family: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source_text") or "")
        partition = _family_partition(source)
        if partition is not None:
            family.append({"row": row, "source": source, "partition": partition})
    if len(family) != EXPECTED_FAMILY_COUNT:
        raise RuntimeError(f"prime angle-list family census drift: {len(family)}")
    item = family[0]
    sequence = int(item["row"]["sequence_number"])
    if sequence != EXPECTED_FAMILY_SEQUENCE:
        raise RuntimeError(f"prime angle-list family sequence drift: {sequence}")

    source = item["source"]
    p = item["partition"]
    geometries = {
        "whole_row": [source],
        "three_way": [p["prefix"], p["clause"], p["suffix"]],
        "lead_clause_then_suffix": [p["prefix"] + p["clause"], p["suffix"]],
        "prefix_then_clause_suffix": [p["prefix"], p["clause"] + p["suffix"]],
    }
    for name, parts in geometries.items():
        if "".join(parts) != source:
            raise RuntimeError(f"geometry {name} source coverage drift")

    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    models: dict[str, Any] = {}
    for model_name, translator in (("opus", opus), ("tc_big", tc_big)):
        model_geometries: dict[str, Any] = {}
        for geometry_name, parts in geometries.items():
            targets, scores = _translate_rank0(translator, parts)
            candidate = "".join(targets)
            model_geometries[geometry_name] = {
                "source_parts": parts,
                "raw_rank0_targets": targets,
                "rank0_scores": scores,
                "target_separator_injected": False,
                **_evaluate(source, candidate, parts=parts, targets=targets),
            }
        models[model_name] = model_geometries

    asset = load_tc_big_asset()
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only rank0 source-partition DOE for four-pair angular prime list residual",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "family_count": len(family),
        "family_sequence": sequence,
        "source_start": int(item["row"]["source_start"]),
        "source_end": int(item["row"]["source_end"]),
        "source_text": source,
        "current_target_text": str(item["row"].get("target_text") or ""),
        "partition": p,
        "models": models,
        "mechanical_admissibility": {
            model: {
                geometry: bool(record["mechanically_admissible"])
                for geometry, record in rows_by_geometry.items()
            }
            for model, rows_by_geometry in models.items()
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
        "target_separator_injected": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "automatic_n_best_cherry_picking": False,
        "selected_hypothesis_ranks": [0],
    }
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("prime angle-list DOE mutated run23 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "run23-prime-angle-list-split-doe.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "family_count": len(family),
        "family_sequence": sequence,
        "mechanical_admissibility": evidence["mechanical_admissibility"],
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
