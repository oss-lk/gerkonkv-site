from __future__ import annotations

"""Read-only TC-big feasibility for the short standalone DMS angle failure."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_tc_big_short_angular_dms_rescue_stage import (
    evaluate_tc_big_short_angular_dms_candidate,
)

SCHEMA = "rocketdict-full-opticks-short-angular-dms-feasibility/1"
BASE_DATABASE_SHA256 = "dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304"
BASE_RUN_ID = 14
BASE_OUTPUT_SHA256 = "12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_START = 110881
EXPECTED_SOURCE = "Whence this Angle is 2 deg. 0'. 7''. "
EXPECTED_BASE_TARGET = "Откуда угол 2 градуса. 0 футов 7 футов."


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


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_SHORT_DMS_FEASIBILITY_ROOT", "work/short-angular-dms-feasibility")).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("short-DMS feasibility requires exact persisted run-14 database")
    asset = load_tc_big_asset()

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run-14 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    content = str(document["content_text"])

    matches = [row for row in rows if int(row["source_start"]) == EXPECTED_START]
    if len(matches) != 1:
        raise RuntimeError(f"short-DMS cohort drift: {len(matches)}")
    row = matches[0]
    source = str(row.get("source_text") or "")
    base_target = str(row.get("target_text") or "")
    if source != EXPECTED_SOURCE or base_target != EXPECTED_BASE_TARGET:
        raise RuntimeError("short-DMS persisted source/target identity drift")
    start = int(row["source_start"])
    end = int(row["source_end"])
    if content[start:end] != source:
        raise RuntimeError("short-DMS source is not byte-exact")

    translator = TcBigTranslator(device="cpu", compute_type="float32")
    hypotheses = translator.translate([source], beam_size=6, num_hypotheses=6, max_decoding_length=512)[0]
    evaluated: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        target = str(hypothesis.get("text") or "")
        selection = evaluate_tc_big_short_angular_dms_candidate(source, target)
        evaluated.append(
            {
                "rank": int(hypothesis["rank"]),
                "score": hypothesis.get("score"),
                "target_text": target,
                "accepted": selection.get("accepted") is True,
                "strictly_eligible": selection.get("strictly_eligible") is True,
                "product_hard_passed": selection.get("product_hard_passed") is True,
                "semantic_dms_preserved": selection.get("semantic_dms_preserved") is True,
                "prime_notation_passed": (selection.get("prime_notation") or {}).get("passed") is True,
                "source_alpha_ratio": selection.get("source_alpha_ratio"),
                "selection": selection,
            }
        )

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only TC-big feasibility for the short standalone DMS angle failure",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "database_mutated": False,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_run_id": BASE_RUN_ID,
        "base_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "source_start": start,
        "source_text": source,
        "base_target": base_target,
        "hypotheses": evaluated,
        "accepted_candidate_ranks": [row["rank"] for row in evaluated if row["accepted"]],
        "strict_candidate_ranks": [row["rank"] for row in evaluated if row["strictly_eligible"]],
        "semantic_dms_candidate_ranks": [row["rank"] for row in evaluated if row["semantic_dms_preserved"]],
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
    destination = root / "full-opticks-short-angular-dms-feasibility.json"
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "accepted_candidate_ranks": evidence["accepted_candidate_ranks"],
        "strict_candidate_ranks": evidence["strict_candidate_ranks"],
        "semantic_dms_candidate_ranks": evidence["semantic_dms_candidate_ranks"],
        "targets": [row["target_text"] for row in evaluated],
        "evidence_sha256": evidence["evidence_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
