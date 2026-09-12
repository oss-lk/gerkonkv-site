from __future__ import annotations

"""Exact run20 read-only TC-big rank0 DOE for dense alphanumeric label series.

The source-owned selector studied here is deliberately independent of Opticks
coordinates: an ordinary Stage12 linguistic row must contain at least three
``<digits><UPPERCASE>`` labels spanning at least three distinct letter suffixes.
The DOE includes every such run20 row, including clean controls, so a candidate
cannot be justified by the single current failure alone.
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
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-alphanumeric-label-tc-big-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SEQUENCES = [1757, 1760, 1762, 1763]
EXPECTED_FAILURE_SEQUENCE = 1762
ORDINARY_SOURCES = frozenset({"nlp_sentence", "nlp_sentence_fragment", "nlp_sentence_group"})
LABEL_RE = re.compile(r"(?<![A-Za-z0-9])(?P<label>\d+(?P<letter>[A-Z]))(?![A-Za-z0-9])")
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.50
MIN_CONTROL_ALPHA_RETENTION = 0.85


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


def _labels(text: str) -> list[str]:
    return [match.group("label") for match in LABEL_RE.finditer(text)]


def _letters(text: str) -> set[str]:
    return {match.group("letter") for match in LABEL_RE.finditer(text)}


def _source_owned_selector(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    payload = dict(row.get("payload") or {})
    planner = dict(payload.get("planner") or {})
    labels = _labels(source)
    letters = _letters(source)
    ordinary = str(planner.get("source") or "") in ORDINARY_SOURCES
    eligible = ordinary and len(labels) >= 3 and len(letters) >= 3
    return {
        "eligible": eligible,
        "planner_source": str(planner.get("source") or ""),
        "labels": labels,
        "distinct_label_letters": sorted(letters),
        "label_count": len(labels),
        "distinct_label_letter_count": len(letters),
    }


def _candidate(source: str, base_target: str, target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    base_alpha = _alpha(base_target)
    source_ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    control_retention = target_alpha / base_alpha if base_alpha else (1.0 if target_alpha == 0 else float("inf"))
    source_labels = Counter(_labels(source))
    target_labels = Counter(_labels(target))
    labels_exact = source_labels == target_labels
    mechanically_admissible = bool(
        target.strip()
        and verdict.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and labels_exact
        and MIN_SOURCE_ALPHA_RATIO <= source_ratio <= MAX_SOURCE_ALPHA_RATIO
        and control_retention >= MIN_CONTROL_ALPHA_RETENTION
    )
    return {
        "mechanically_admissible": mechanically_admissible,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_labels": dict(source_labels),
        "target_labels": dict(target_labels),
        "labels_exact": labels_exact,
        "source_alpha": source_alpha,
        "base_target_alpha": base_alpha,
        "candidate_target_alpha": target_alpha,
        "source_alpha_ratio": source_ratio,
        "control_alpha_retention": control_retention,
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN20_ALPHANUM_LABEL_DOE_ROOT",
            "work/run20-alphanumeric-label-tc-big-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("alphanumeric-label DOE requires exact persisted run20 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))

    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run20 source coverage is not byte-exact")

    selected: list[dict[str, Any]] = []
    for row in rows:
        selector = _source_owned_selector(row)
        if selector["eligible"]:
            selected.append({**row, "selector": selector})
    sequences = [int(row["sequence_number"]) for row in selected]
    if sequences != EXPECTED_SEQUENCES:
        raise RuntimeError(f"alphanumeric-label census drift: {sequences!r}")

    translator = TcBigTranslator(device="cpu", compute_type="float32")
    hypotheses = translator.translate(
        [str(row.get("source_text") or "") for row in selected],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(hypotheses) != len(selected) or any(len(group) != 1 for group in hypotheses):
        raise RuntimeError("TC-big rank0 generation cardinality drift")

    records: list[dict[str, Any]] = []
    for row, group in zip(selected, hypotheses, strict=True):
        source = str(row.get("source_text") or "")
        base_target = str(row.get("target_text") or "")
        candidate_target = str(group[0].get("text") or "")
        base_verdict = evaluate_rescue_pair(source, base_target)
        evaluation = _candidate(source, base_target, candidate_target)
        records.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "base_target_text": base_target,
                "selector": dict(row["selector"]),
                "base_mechanical_verdict": base_verdict,
                "tc_big_rank0": {
                    "rank": int(group[0].get("rank") or 0),
                    "score": group[0].get("score"),
                    "target_text": candidate_target,
                    **evaluation,
                },
            }
        )

    base_failures = [
        row["sequence_number"]
        for row in records
        if row["base_mechanical_verdict"].get("strictly_eligible") is not True
    ]
    candidate_failures = [
        row["sequence_number"]
        for row in records
        if row["tc_big_rank0"].get("mechanically_admissible") is not True
    ]
    if base_failures != [EXPECTED_FAILURE_SEQUENCE]:
        raise RuntimeError(f"unexpected base control failures: {base_failures!r}")
    if candidate_failures:
        raise RuntimeError(f"TC-big rank0 is not fail-closed clean for selected class: {candidate_failures!r}")

    asset = load_tc_big_asset()
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only exact-run20 TC-big rank0 feasibility for source-defined dense alphanumeric technical-label series",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "selector": {
            "ordinary_planner_sources": sorted(ORDINARY_SOURCES),
            "minimum_label_count": 3,
            "minimum_distinct_uppercase_suffixes": 3,
            "label_pattern": LABEL_RE.pattern,
            "source_defined": True,
            "target_text_used_for_eligibility": False,
        },
        "selected_sequences": sequences,
        "selected_count": len(records),
        "base_failure_sequences": base_failures,
        "tc_big_rank0_failure_sequences": candidate_failures,
        "all_tc_big_rank0_mechanically_admissible": not candidate_failures,
        "records": records,
        "beam_size": BEAM_SIZE,
        "num_hypotheses": NUM_HYPOTHESES,
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
        raise RuntimeError("read-only alphanumeric-label DOE mutated run20 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    path = root / "full-opticks-run20-alphanumeric-label-tc-big-doe.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
