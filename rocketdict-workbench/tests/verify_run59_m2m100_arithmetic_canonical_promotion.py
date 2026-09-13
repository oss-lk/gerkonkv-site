from __future__ import annotations

"""Authenticate one persisted replay as the canonical run59 parent candidate.

This verifier performs no translation. It consumes cross-replica replay authority,
one selected persisted replay database, and an independently generated residual
census. Parent replacement is authorized only after all provenance, unchanged-row,
raw-rank0, source-coverage, SQLite, and hard-gate checks agree.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_m2m100_arithmetic_rescue_stage import (
    M2M100_ARITHMETIC_RESCUE_CONTRACT,
    M2M100_ARITHMETIC_SELECTED_PHASE,
)

SCHEMA = "rocketdict-run59-m2m100-arithmetic-canonical-promotion/1"
BASE_RUN_ID = 58
PROMOTED_RUN_ID = 59
BASE_OUTPUT_SHA256 = "60349256eac118e9af7aa1366761342cd2041bb6ade4db04b45c78b46a8c6e5d"
BASE_PARAMETERS_SHA256 = "1cf60c7b582640c3923ea685ed329eb685a7b80e502e11507d99c752e6342315"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SOURCE_START = 483234
EXPECTED_SEQUENCE_NUMBER = 2739
EXPECTED_TARGET_SHA256 = "258bc3a57d933b23317cf946af2f9e851fd266c6501a5b51813806b3294081d6"
EXPECTED_TOKENS_SHA256 = "599b77feba47448aff917fee3ea7d5e6e4a2c607378af906eaa63ca3ff37373d"
EXPECTED_CTRANSLATE2_VERSION = "4.8.2"
EXPECTED_GENERATION = {
    "beam_size": 6,
    "num_hypotheses": 1,
    "max_decoding_length": 512,
}
EXPECTED_HARD_COUNTS = {
    "numeric_symbol": 15,
    "punctuation": 10,
    "length": 0,
    "unique": 24,
}
SAFETY_FLAGS = (
    "source_bytes_rewritten",
    "model_input_source_rewritten",
    "target_rewriting",
    "placeholders",
    "post_translation_literal_injection",
    "corpus_specific_target_patches",
    "evaluator_weakened",
    "n_best_cherry_picking",
    "automatic_n_best_cherry_picking",
)


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _canonical_sha(value: Any) -> str:
    return _sha_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _load_authenticated(path: Path, schema: str) -> dict[str, Any]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("schema") != schema:
        raise RuntimeError(f"evidence schema drift for {path}: {evidence.get('schema')!r}")
    copy = dict(evidence)
    recorded = str(copy.pop("evidence_sha256", ""))
    actual = _canonical_sha(copy)
    if not recorded or recorded != actual:
        raise RuntimeError(f"evidence SHA drift for {path}")
    return evidence


def main() -> int:
    root = Path(os.environ["ROCKETDICT_RUN59_CANONICAL_ROOT"]).resolve()
    database = Path(os.environ["ROCKETDICT_RUN59_CANONICAL_DB"]).resolve()
    replica_path = Path(os.environ["ROCKETDICT_RUN59_REPLICA_EVIDENCE"]).resolve()
    aggregate_path = Path(os.environ["ROCKETDICT_RUN59_AGGREGATE_EVIDENCE"]).resolve()
    census_path = Path(os.environ["ROCKETDICT_RUN59_CENSUS_EVIDENCE"]).resolve()
    root.mkdir(parents=True, exist_ok=True)

    aggregate = _load_authenticated(
        aggregate_path,
        "rocketdict-run58-m2m100-arithmetic-public-replay-aggregate/1",
    )
    replica = _load_authenticated(
        replica_path,
        "rocketdict-run58-m2m100-arithmetic-public-replay/1",
    )
    census = _load_authenticated(census_path, "rocketdict-translation-residual-census/1")

    if aggregate.get("canonical_promotion_authorized") is not True:
        raise RuntimeError("replay aggregate did not authorize canonical promotion")
    if aggregate.get("parent_replacement_allowed") is not False:
        raise RuntimeError("replay aggregate illegally authorized parent replacement")
    if aggregate.get("rank0_target_sha256") != [EXPECTED_TARGET_SHA256]:
        raise RuntimeError("aggregate raw target identity drift")
    if aggregate.get("rank0_tokens_sha256") != [EXPECTED_TOKENS_SHA256]:
        raise RuntimeError("aggregate raw token identity drift")
    if replica.get("evidence_sha256") not in list(
        aggregate.get("replica_evidence_sha256") or []
    ):
        raise RuntimeError("selected replica is not a member of replay aggregate")
    if replica.get("replay_ready_for_aggregation") is not True:
        raise RuntimeError("selected replica was not replay-ready")
    if int(replica.get("promoted_translation_run_id") or -1) != PROMOTED_RUN_ID:
        raise RuntimeError("selected replica did not persist run59")

    db_sha = _sha_bytes(database.read_bytes())
    if db_sha != replica.get("persisted_database_sha256"):
        raise RuntimeError("selected replica database SHA drift")
    if int(census.get("translation_run_id") or -1) != PROMOTED_RUN_ID:
        raise RuntimeError("census run identity drift")
    if census.get("database_sha256") != db_sha:
        raise RuntimeError("census database identity drift")
    if census.get("hard_gate_counts") != EXPECTED_HARD_COUNTS:
        raise RuntimeError(f"run59 hard-count drift: {census.get('hard_gate_counts')}")
    if census.get("source_coverage_byte_exact") is not True:
        raise RuntimeError("census source coverage drift")
    if census.get("database_unchanged") is not True:
        raise RuntimeError("census mutated canonical database")
    if census.get("evaluator_weakened") is not False:
        raise RuntimeError("census evaluator policy drift")

    with connect(database, readonly=True) as connection:
        base = get_run(connection, BASE_RUN_ID)
        promoted = get_run(connection, PROMOTED_RUN_ID)
        base_rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        promoted_rows = sorted(
            get_run_items(connection, PROMOTED_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        promoted_output = dict(promoted.get("output") or {})
        document = get_document(connection, int(promoted_output["document_version_id"]))

    if str(base.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("canonical DB run58 output identity drift")
    if str(base.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("canonical DB run58 parameter identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("canonical DB source identity drift")
    if len(base_rows) != 3335 or len(promoted_rows) != 3335:
        raise RuntimeError("canonical translation segment cardinality drift")

    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in promoted_rows) != content:
        raise RuntimeError("canonical run59 source coverage is not byte-exact")
    changed: list[int] = []
    for base_row, promoted_row in zip(base_rows, promoted_rows, strict=True):
        if (
            int(base_row["sequence_number"]) != int(promoted_row["sequence_number"])
            or int(base_row["source_start"]) != int(promoted_row["source_start"])
            or int(base_row["source_end"]) != int(promoted_row["source_end"])
            or str(base_row.get("source_text") or "")
            != str(promoted_row.get("source_text") or "")
        ):
            raise RuntimeError("run58/run59 source-row ancestry drift")
        if str(base_row.get("target_text") or "") != str(promoted_row.get("target_text") or ""):
            changed.append(int(promoted_row["sequence_number"]))
    if changed != [EXPECTED_SEQUENCE_NUMBER]:
        raise RuntimeError(f"canonical changed-target drift: {changed}")

    selected = promoted_rows[EXPECTED_SEQUENCE_NUMBER]
    if int(selected["source_start"]) != EXPECTED_SOURCE_START:
        raise RuntimeError("canonical arithmetic source-start drift")
    payload = dict(selected.get("payload") or {})
    rescue = dict(payload.get("m2m100_arithmetic_rescue") or {})
    hypotheses = list(payload.get("hypotheses") or [])
    if rescue.get("contract") != M2M100_ARITHMETIC_RESCUE_CONTRACT:
        raise RuntimeError("canonical rescue contract drift")
    if promoted_output.get("m2m100_arithmetic_rescue_contract") != M2M100_ARITHMETIC_RESCUE_CONTRACT:
        raise RuntimeError("canonical output rescue contract drift")
    if promoted_output.get("m2m100_arithmetic_rescue_phase") not in {
        None,
        M2M100_ARITHMETIC_SELECTED_PHASE,
    }:
        raise RuntimeError("canonical rescue phase drift")
    if rescue.get("applied") is not True:
        raise RuntimeError("canonical arithmetic rescue was not applied")
    if rescue.get("model_input") != str(selected.get("source_text") or ""):
        raise RuntimeError("canonical model input differs from immutable source row")
    if rescue.get("model_input_equals_source") is not True:
        raise RuntimeError("canonical model-input provenance drift")
    if rescue.get("raw_model_selected") is not True or rescue.get("raw_model_rank") != 0:
        raise RuntimeError("canonical raw rank0 selection drift")
    if rescue.get("generation") != EXPECTED_GENERATION:
        raise RuntimeError("canonical generation contract drift")
    runtime_identity = dict(rescue.get("runtime_identity") or {})
    if runtime_identity.get("ctranslate2_version") != EXPECTED_CTRANSLATE2_VERSION:
        raise RuntimeError("canonical CT2 version drift")
    selection = dict(rescue.get("selection") or {})
    if selection.get("accepted") is not True:
        raise RuntimeError("canonical selector did not accept raw rank0")
    if len(hypotheses) != 1 or int(hypotheses[0].get("rank", -1)) != 0:
        raise RuntimeError("canonical hypothesis cardinality/rank drift")
    hypothesis = dict(hypotheses[0])
    target = str(hypothesis.get("text") or "")
    tokens = list(hypothesis.get("tokens") or [])
    if target != str(selected.get("target_text") or ""):
        raise RuntimeError("canonical persisted target differs from raw rank0")
    if _sha_text(target) != EXPECTED_TARGET_SHA256:
        raise RuntimeError("canonical raw target SHA drift")
    if _canonical_sha(tokens) != EXPECTED_TOKENS_SHA256:
        raise RuntimeError("canonical raw token SHA drift")

    if promoted_output.get("base_translation_run_id") != BASE_RUN_ID:
        raise RuntimeError("canonical base run ancestry drift")
    if promoted_output.get("base_translation_output_sha256") != BASE_OUTPUT_SHA256:
        raise RuntimeError("canonical base output ancestry drift")
    if promoted_output.get("m2m100_arithmetic_rescue_attempt_count") != 1:
        raise RuntimeError("canonical attempt count drift")
    if promoted_output.get("m2m100_arithmetic_rescue_accepted_count") != 1:
        raise RuntimeError("canonical accepted count drift")
    if promoted_output.get("m2m100_arithmetic_rescue_rejected_count") != 0:
        raise RuntimeError("canonical rejection count drift")
    for flag in SAFETY_FLAGS:
        if promoted_output.get(flag) is not False:
            raise RuntimeError(f"canonical unsafe flag {flag}")

    con = sqlite3.connect(database)
    integrity = str(con.execute("PRAGMA integrity_check").fetchone()[0])
    foreign_keys = len(con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()
    if integrity != "ok" or foreign_keys != 0:
        raise RuntimeError(
            f"canonical SQLite integrity drift: {integrity=} {foreign_keys=}"
        )

    target_text_sha = _sha_text("".join(str(row.get("target_text") or "") for row in promoted_rows))
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "parent_replacement_allowed": True,
        "canonical_translation_run_id": PROMOTED_RUN_ID,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "translation_output_sha256": str(promoted.get("output_sha256") or ""),
        "parameters_sha256": str(promoted.get("parameters_sha256") or ""),
        "database_sha256": db_sha,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "target_text_sha256": target_text_sha,
        "translation_segment_count": len(promoted_rows),
        "changed_target_sequences": changed,
        "selected_source_start": EXPECTED_SOURCE_START,
        "raw_rank0_target_sha256": EXPECTED_TARGET_SHA256,
        "raw_rank0_tokens_sha256": EXPECTED_TOKENS_SHA256,
        "rescue_contract": M2M100_ARITHMETIC_RESCUE_CONTRACT,
        "rescue_phase": M2M100_ARITHMETIC_SELECTED_PHASE,
        "runtime_identity": runtime_identity,
        "generation": EXPECTED_GENERATION,
        "hard_gate_counts": EXPECTED_HARD_COUNTS,
        "replay_aggregate_evidence_sha256": aggregate["evidence_sha256"],
        "selected_replica_evidence_sha256": replica["evidence_sha256"],
        "residual_census_evidence_sha256": census["evidence_sha256"],
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_violations": foreign_keys,
        "source_coverage_byte_exact": True,
        **{flag: False for flag in SAFETY_FLAGS},
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    out = root / "run59-m2m100-arithmetic-canonical-promotion.json"
    out.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
