from __future__ import annotations

"""No-inference verifier for canonical promotion of combined-Greek run60.

The verifier consumes a cross-replica replay authority, one persisted replay
SQLite, and an independently generated residual census. It never invokes MT.
Parent replacement is authorized only when provenance, byte-exact ancestry,
raw-rank0 source-plan evidence, unchanged-row preservation, SQLite integrity,
and the maintained hard-gate census all agree.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_combined_greek_rescue_stage import (
    COMBINED_GREEK_RESCUE_CONTRACT,
    COMBINED_GREEK_SELECTED_PHASE,
    COMBINED_GREEK_SELECTOR_CONTRACT,
    COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
    COMBINED_GREEK_TRIGGER_CONTRACT,
)

SCHEMA = "rocketdict-run60-combined-greek-canonical-promotion/1"
REPLAY_SCHEMA = "rocketdict-run59-combined-greek-public-replay/1"
AGGREGATE_SCHEMA = "rocketdict-run59-combined-greek-public-replay-aggregate/1"
CENSUS_SCHEMA = "rocketdict-translation-residual-census/1"
BASE_RUN_ID = 59
PROMOTED_RUN_ID = 60
BASE_OUTPUT_SHA256 = "5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1"
BASE_PARAMETERS_SHA256 = "5b1ea478963221869b64ebca2c9a60f8e9838c41e4616b9b737aa648436b4878"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_CONTEXT_RUN_ID = 2
EXPECTED_SOURCE_START = 301051
EXPECTED_SEQUENCE_NUMBER = 1753
EXPECTED_SEGMENT_COUNT = 3335
EXPECTED_TARGET_SHA256 = "c53660ded405267f6346d0611fa41edf4bfde8fb86155ca40289669c6c2a6f51"
EXPECTED_PREFIX_TARGET_SHA256 = "e8d5b27cd3ce22898f5d443aca5b578af85b5a67885e944607e9f10527c8bf7e"
EXPECTED_PREFIX_TOKENS_SHA256 = "bf1994714366cb1b57949a493932d4d1432c78dc089bcc7db2180189ea3fec7e"
EXPECTED_SUFFIX_TARGET_SHA256 = "603757cfe250ed5f95f8bec0f1c9649599a008e2cf8e7eb37853358b438d3086"
EXPECTED_SUFFIX_TOKENS_SHA256 = "1f95a6c89f8aa6a99d408d90862079f57cf4ddb4b71a0faeee1d2ea679805ae5"
EXPECTED_OPUS_RUNTIME_IDENTITY = {
    "revision": "opus-2020-02-11",
    "source_archive_sha256": "798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677",
    "manifest_sha256": "0c1720b41db19d262899133e400a94e2657b806affc1126cf8da8ca00569a001",
    "payload_tree_sha256": "35c5982497fadf88d1748a67f969d4fd8d3ed8babc3c9bc1141223dbfaf0f3ce",
    "compute_type": "float32",
}
EXPECTED_GENERATION = {
    "beam_size": 6,
    "num_hypotheses": 1,
    "max_decoding_length": 512,
    "selected_rank": 0,
}
EXPECTED_HARD_COUNTS = {
    "numeric_symbol": 15,
    "punctuation": 9,
    "length": 0,
    "unique": 23,
}
COMBINED_KEYS = {
    "enable_combined_greek_source_plan_rescue",
    "combined_greek_source_plan_rescue_contract",
    "combined_greek_source_plan_selector_contract",
    "combined_greek_source_plan_trigger_contract",
    "combined_greek_source_plan_contract",
    "combined_greek_source_plan_rescue_phase",
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
    canonical = dict(evidence)
    recorded = str(canonical.pop("evidence_sha256", ""))
    actual = _canonical_sha(canonical)
    if not recorded or actual != recorded:
        raise RuntimeError(f"evidence SHA drift for {path}")
    return evidence


def _translated_piece(piece: dict[str, Any], role: str) -> dict[str, Any]:
    if piece.get("role") != role or piece.get("kind") != "translate":
        raise RuntimeError(f"{role} source-plan piece drift")
    hypothesis = dict(piece.get("hypothesis") or {})
    if int(piece.get("selected_rank", -1)) != 0 or int(hypothesis.get("rank", -1)) != 0:
        raise RuntimeError(f"{role} is not raw rank0")
    if piece.get("model_input") != piece.get("source_text"):
        raise RuntimeError(f"{role} model input differs from immutable planned source")
    if piece.get("selected_target") != hypothesis.get("text"):
        raise RuntimeError(f"{role} selected target differs from raw rank0")
    return hypothesis


def _verify_selected_row(row: dict[str, Any]) -> dict[str, Any]:
    if int(row["sequence_number"]) != EXPECTED_SEQUENCE_NUMBER:
        raise RuntimeError("canonical combined-Greek sequence drift")
    if int(row["source_start"]) != EXPECTED_SOURCE_START:
        raise RuntimeError("canonical combined-Greek source-start drift")
    target = str(row.get("target_text") or "")
    if _sha_text(target) != EXPECTED_TARGET_SHA256:
        raise RuntimeError("canonical combined-Greek target SHA drift")
    payload = dict(row.get("payload") or {})
    rescue = dict(payload.get("combined_greek_source_plan_rescue") or {})
    if rescue.get("applied") is not True:
        raise RuntimeError("canonical combined-Greek rescue is not applied")
    if rescue.get("contract") != COMBINED_GREEK_RESCUE_CONTRACT:
        raise RuntimeError("canonical rescue contract drift")
    if rescue.get("selector_contract") != COMBINED_GREEK_SELECTOR_CONTRACT:
        raise RuntimeError("canonical selector contract drift")
    if rescue.get("trigger_contract") != COMBINED_GREEK_TRIGGER_CONTRACT:
        raise RuntimeError("canonical trigger contract drift")
    if rescue.get("source_plan_contract") != COMBINED_GREEK_SOURCE_PLAN_CONTRACT:
        raise RuntimeError("canonical source-plan contract drift")
    if int(rescue.get("base_translation_run_id") or -1) != BASE_RUN_ID:
        raise RuntimeError("canonical selected-row ancestry drift")
    trigger = dict(rescue.get("trigger") or {})
    if trigger.get("corpus_sequence_whitelist") is not False or trigger.get("source_start_whitelist") is not False:
        raise RuntimeError("canonical trigger became corpus-position specific")
    selection = dict(rescue.get("selection") or {})
    if selection.get("accepted") is not True:
        raise RuntimeError("canonical combined-Greek selector did not accept candidate")
    plan = dict(rescue.get("source_plan") or {})
    if plan.get("contract") != COMBINED_GREEK_SOURCE_PLAN_CONTRACT or plan.get("created_before_mt") is not True:
        raise RuntimeError("canonical source-plan provenance drift")
    pieces = list(plan.get("pieces") or [])
    if len(pieces) != 5 or [p.get("role") for p in pieces] != [
        "prefix", "left_separator", "technical_atom", "right_separator", "suffix"
    ]:
        raise RuntimeError("canonical source-plan piece order drift")
    if "".join(str(p.get("source_text") or "") for p in pieces) != str(row.get("source_text") or ""):
        raise RuntimeError("canonical source-plan byte coverage drift")
    for piece in pieces[1:4]:
        if (
            piece.get("kind") != "preserve_source_structure"
            or piece.get("source_owned") is not True
            or piece.get("rendered_text") != piece.get("source_text")
        ):
            raise RuntimeError(f"canonical source-owned structural piece drift: {piece!r}")
    if str(pieces[2].get("source_text") or "") != "_A[Greek: a]_":
        raise RuntimeError("canonical technical atom identity drift")
    prefix_h = _translated_piece(dict(pieces[0]), "prefix")
    suffix_h = _translated_piece(dict(pieces[4]), "suffix")
    if _sha_text(str(prefix_h.get("text") or "")) != EXPECTED_PREFIX_TARGET_SHA256:
        raise RuntimeError("canonical prefix rank0 target SHA drift")
    if _canonical_sha(list(prefix_h.get("tokens") or [])) != EXPECTED_PREFIX_TOKENS_SHA256:
        raise RuntimeError("canonical prefix rank0 tokens SHA drift")
    if _sha_text(str(suffix_h.get("text") or "")) != EXPECTED_SUFFIX_TARGET_SHA256:
        raise RuntimeError("canonical suffix rank0 target SHA drift")
    if _canonical_sha(list(suffix_h.get("tokens") or [])) != EXPECTED_SUFFIX_TOKENS_SHA256:
        raise RuntimeError("canonical suffix rank0 tokens SHA drift")
    if dict(rescue.get("runtime_identity") or {}) != EXPECTED_OPUS_RUNTIME_IDENTITY:
        raise RuntimeError("canonical OPUS runtime identity drift")
    if dict(rescue.get("generation") or {}) != EXPECTED_GENERATION:
        raise RuntimeError("canonical generation contract drift")
    for flag in SAFETY_FLAGS:
        if rescue.get(flag) is not False:
            raise RuntimeError(f"canonical selected-row unsafe flag {flag}")
    return rescue


def main() -> int:
    root = Path(os.environ["ROCKETDICT_RUN60_CANONICAL_ROOT"]).resolve()
    database = Path(os.environ["ROCKETDICT_RUN60_CANONICAL_DB"]).resolve()
    replica_path = Path(os.environ["ROCKETDICT_RUN60_REPLICA_EVIDENCE"]).resolve()
    aggregate_path = Path(os.environ["ROCKETDICT_RUN60_AGGREGATE_EVIDENCE"]).resolve()
    census_path = Path(os.environ["ROCKETDICT_RUN60_CENSUS_EVIDENCE"]).resolve()
    root.mkdir(parents=True, exist_ok=True)

    aggregate = _load_authenticated(aggregate_path, AGGREGATE_SCHEMA)
    replica = _load_authenticated(replica_path, REPLAY_SCHEMA)
    census = _load_authenticated(census_path, CENSUS_SCHEMA)

    if aggregate.get("canonical_promotion_authorized") is not True:
        raise RuntimeError("replay aggregate did not authorize canonical promotion")
    if aggregate.get("parent_replacement_allowed") is not False:
        raise RuntimeError("replay aggregate illegally authorized parent replacement")
    if aggregate.get("candidate_target_sha256") != [EXPECTED_TARGET_SHA256]:
        raise RuntimeError("aggregate candidate target identity drift")
    if aggregate.get("prefix_rank0_target_sha256") != [EXPECTED_PREFIX_TARGET_SHA256]:
        raise RuntimeError("aggregate prefix rank0 target identity drift")
    if aggregate.get("prefix_rank0_tokens_sha256") != [EXPECTED_PREFIX_TOKENS_SHA256]:
        raise RuntimeError("aggregate prefix rank0 tokens identity drift")
    if aggregate.get("suffix_rank0_target_sha256") != [EXPECTED_SUFFIX_TARGET_SHA256]:
        raise RuntimeError("aggregate suffix rank0 target identity drift")
    if aggregate.get("suffix_rank0_tokens_sha256") != [EXPECTED_SUFFIX_TOKENS_SHA256]:
        raise RuntimeError("aggregate suffix rank0 tokens identity drift")
    if replica.get("evidence_sha256") not in list(aggregate.get("replica_evidence_sha256") or []):
        raise RuntimeError("selected replay replica is not authenticated by aggregate")
    if replica.get("replay_ready_for_aggregation") is not True:
        raise RuntimeError("selected replay replica was not aggregation-ready")
    if replica.get("parent_replacement_allowed") is not False:
        raise RuntimeError("single replay illegally authorized parent replacement")
    if int(replica.get("promoted_translation_run_id") or -1) != PROMOTED_RUN_ID:
        raise RuntimeError("selected replay did not persist run60")

    db_sha = _sha_bytes(database.read_bytes())
    if db_sha != replica.get("persisted_database_sha256"):
        raise RuntimeError("selected replay database SHA drift")
    if int(census.get("translation_run_id") or -1) != PROMOTED_RUN_ID:
        raise RuntimeError("residual census run identity drift")
    if census.get("database_sha256") != db_sha:
        raise RuntimeError("residual census database identity drift")
    if census.get("hard_gate_counts") != EXPECTED_HARD_COUNTS:
        raise RuntimeError(f"run60 hard-count drift: {census.get('hard_gate_counts')!r}")
    if census.get("source_coverage_byte_exact") is not True or census.get("database_unchanged") is not True:
        raise RuntimeError("residual census source/read-only contract drift")
    if census.get("evaluator_weakened") is not False:
        raise RuntimeError("residual census evaluator policy drift")

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
        raise RuntimeError("canonical DB run59 output identity drift")
    if str(base.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("canonical DB run59 parameter identity drift")
    base_identity = dict(base.get("input_identity") or {})
    if int(base_identity.get("context_run_id") or -1) != EXPECTED_CONTEXT_RUN_ID:
        raise RuntimeError("canonical DB run59 context ancestry drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("canonical DB immutable source identity drift")
    if len(base_rows) != EXPECTED_SEGMENT_COUNT or len(promoted_rows) != EXPECTED_SEGMENT_COUNT:
        raise RuntimeError("canonical translation segment cardinality drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in promoted_rows) != content:
        raise RuntimeError("canonical run60 source coverage is not byte-exact")

    changed: list[int] = []
    unchanged_target_rows = 0
    for base_row, promoted_row in zip(base_rows, promoted_rows, strict=True):
        if (
            int(base_row["sequence_number"]) != int(promoted_row["sequence_number"])
            or int(base_row["source_start"]) != int(promoted_row["source_start"])
            or int(base_row["source_end"]) != int(promoted_row["source_end"])
            or str(base_row.get("source_text") or "") != str(promoted_row.get("source_text") or "")
        ):
            raise RuntimeError("run59/run60 immutable source-row ancestry drift")
        if str(base_row.get("target_text") or "") != str(promoted_row.get("target_text") or ""):
            changed.append(int(promoted_row["sequence_number"]))
        else:
            unchanged_target_rows += 1
    if changed != [EXPECTED_SEQUENCE_NUMBER] or unchanged_target_rows != EXPECTED_SEGMENT_COUNT - 1:
        raise RuntimeError(f"canonical target-delta drift: {changed=} {unchanged_target_rows=}")

    base_parameters = dict(base.get("parameters") or {})
    promoted_parameters = dict(promoted.get("parameters") or {})
    stripped = {k: v for k, v in promoted_parameters.items() if k not in COMBINED_KEYS}
    if stripped != base_parameters:
        raise RuntimeError("canonical run60 changed lower Stage12 parameters")
    if promoted_parameters.get("enable_combined_greek_source_plan_rescue") is not True:
        raise RuntimeError("canonical run60 combined-Greek wrapper is not explicitly enabled")

    rescue = _verify_selected_row(promoted_rows[EXPECTED_SEQUENCE_NUMBER])
    if promoted_output.get("base_translation_run_id") != BASE_RUN_ID:
        raise RuntimeError("canonical run60 base-run ancestry drift")
    if promoted_output.get("base_translation_output_sha256") != BASE_OUTPUT_SHA256:
        raise RuntimeError("canonical run60 base-output ancestry drift")
    if promoted_output.get("combined_greek_source_plan_rescue_contract") != COMBINED_GREEK_RESCUE_CONTRACT:
        raise RuntimeError("canonical output rescue contract drift")
    if promoted_output.get("combined_greek_source_plan_rescue_phase") not in {
        None, COMBINED_GREEK_SELECTED_PHASE
    }:
        raise RuntimeError("canonical output rescue phase drift")
    if promoted_output.get("combined_greek_source_plan_rescue_attempt_count") != 1:
        raise RuntimeError("canonical combined-Greek attempt count drift")
    if promoted_output.get("combined_greek_source_plan_rescue_accepted_count") != 1:
        raise RuntimeError("canonical combined-Greek accepted count drift")
    if promoted_output.get("combined_greek_source_plan_rescue_rejected_count") != 0:
        raise RuntimeError("canonical combined-Greek rejection count drift")
    if promoted_output.get("combined_greek_source_plan_rescue_attempted_source_starts") != [EXPECTED_SOURCE_START]:
        raise RuntimeError("canonical attempted-source cohort drift")
    if promoted_output.get("combined_greek_source_plan_rescue_accepted_source_starts") != [EXPECTED_SOURCE_START]:
        raise RuntimeError("canonical accepted-source cohort drift")
    for flag in SAFETY_FLAGS:
        if promoted_output.get(flag) is not False:
            raise RuntimeError(f"canonical run60 unsafe flag {flag}")

    con = sqlite3.connect(database)
    integrity = str(con.execute("PRAGMA integrity_check").fetchone()[0])
    foreign_keys = len(con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()
    if integrity != "ok" or foreign_keys != 0:
        raise RuntimeError(f"canonical SQLite integrity drift: {integrity=} {foreign_keys=}")

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
        "unchanged_target_row_count": unchanged_target_rows,
        "selected_source_start": EXPECTED_SOURCE_START,
        "candidate_target_sha256": EXPECTED_TARGET_SHA256,
        "prefix_rank0_target_sha256": EXPECTED_PREFIX_TARGET_SHA256,
        "prefix_rank0_tokens_sha256": EXPECTED_PREFIX_TOKENS_SHA256,
        "suffix_rank0_target_sha256": EXPECTED_SUFFIX_TARGET_SHA256,
        "suffix_rank0_tokens_sha256": EXPECTED_SUFFIX_TOKENS_SHA256,
        "rescue_contract": COMBINED_GREEK_RESCUE_CONTRACT,
        "rescue_phase": COMBINED_GREEK_SELECTED_PHASE,
        "selector_contract": COMBINED_GREEK_SELECTOR_CONTRACT,
        "trigger_contract": COMBINED_GREEK_TRIGGER_CONTRACT,
        "source_plan_contract": COMBINED_GREEK_SOURCE_PLAN_CONTRACT,
        "runtime_identity": dict(rescue.get("runtime_identity") or {}),
        "generation": dict(rescue.get("generation") or {}),
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
    out = root / "run60-combined-greek-canonical-promotion.json"
    out.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
