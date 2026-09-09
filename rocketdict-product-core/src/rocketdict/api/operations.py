from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from rocketdict.api.contracts import (
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
    TRANSPORT,
)
from rocketdict.api.registry import descriptor_hash, required_inputs, stage_key
from rocketdict.downstream import (
    SET_ASSEMBLY_POLICY,
    STAGE20_POLICY,
    STAGE21_POLICY,
    STAGE22_POLICY,
    STAGE23_POLICY,
    STAGE24_POLICY,
    STAGE25_POLICY,
    assemble_card_set as _assemble_card_set,
    run_stage20 as _run_stage20,
    run_stage21 as _run_stage21,
    run_stage22 as _run_stage22,
    run_stage23 as _run_stage23,
    run_stage24 as _run_stage24,
    run_stage25 as _run_stage25,
)
from rocketdict.lexical import run_stage18 as _run_stage18, run_stage19 as _run_stage19
from rocketdict.numeric_integrity import run_numeric_symbol_gate as _run_numeric_symbol_gate
from rocketdict.stages import (
    run_length_ratio_gate as _run_length_ratio_gate,
    run_punctuation_gate as _run_punctuation_gate,
    run_stage8 as _run_stage8,
    run_stage10 as _run_stage10,
    run_stage14 as _run_stage14,
    run_stage16 as _run_stage16,
    run_stage17 as _run_stage17,
)
from rocketdict.translation_rescue_stage import run_stage12 as _run_stage12

STAGE18_IMPLEMENTATION = "workbench-aligned-content-pos-v5"
STAGE18_STAGE_KEY = "lexical_extraction"
STAGE18_REQUIRED_INPUTS = ["alignment_run_id"]


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _execution_contract(
    stage_number: int,
    inputs: list[str],
    *,
    result_schema: str,
    identity_fields: list[str],
    extra_required_fields: list[str] | None = None,
) -> dict[str, Any]:
    required = ["schema", *identity_fields, *(extra_required_fields or [])]
    required = list(dict.fromkeys(required))
    return {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": TRANSPORT,
        "replay_safe": True,
        "request": {
            "params": {
                **{name: f"input:{name}" for name in inputs},
                "parameters": "profile:parameters",
                "implementation": "binding:implementation",
            }
        },
        "result": {
            "required_fields": required,
            "identity_fields": list(identity_fields),
            "schema_field": "schema",
            "schema_values": [result_schema],
        },
    }


def _identity(stage_number: int, implementation: str) -> tuple[str, list[str], str]:
    if stage_number == 18:
        descriptor = _canonical_sha(
            {
                "stage_number": 18,
                "stage_key": STAGE18_STAGE_KEY,
                "implementation_key": STAGE18_IMPLEMENTATION,
                "required_inputs": STAGE18_REQUIRED_INPUTS,
                "policy": "aligned-content-pos-v5-table-scoped-target-evidence",
            }
        )
        return STAGE18_STAGE_KEY, list(STAGE18_REQUIRED_INPUTS), descriptor
    return (
        stage_key(stage_number),
        required_inputs(stage_number, implementation),
        descriptor_hash(stage_number, implementation),
    )


def _bind(
    fn: Callable[..., Any],
    *,
    stage_number: int,
    implementation: str,
    result_schema: str,
    identity_fields: list[str],
    extra_required_fields: list[str] | None = None,
    hard_gate: bool = False,
) -> Callable[..., Any]:
    key, inputs, descriptor = _identity(stage_number, implementation)
    fn.stage_number = int(stage_number)  # type: ignore[attr-defined]
    fn.stage_key = key  # type: ignore[attr-defined]
    fn.implementation_key = implementation  # type: ignore[attr-defined]
    fn.adapter_descriptor_hash = descriptor  # type: ignore[attr-defined]
    fn.required_inputs = list(inputs)  # type: ignore[attr-defined]
    fn.rocketdict_execution_contract = _execution_contract(  # type: ignore[attr-defined]
        stage_number,
        inputs,
        result_schema=result_schema,
        identity_fields=identity_fields,
        extra_required_fields=extra_required_fields,
    )
    if hard_gate:
        fn.rocketdict_quality_gate_semantics = {  # type: ignore[attr-defined]
            "schema": PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
            "stage_number": 15,
            "hard_gate": True,
            "failure_blocks_downstream": True,
            "pass_condition": {"field": "passed", "equals": True},
        }
    return fn


def run_stage8(
    *, database: Path | str, document_version_id: int,
    parameters: dict[str, Any] | None = None, implementation: str = "en-sm",
) -> dict[str, Any]:
    return _run_stage8(database, document_version_id=int(document_version_id), parameters=parameters, implementation=implementation)


def run_stage10(
    *, database: Path | str, nlp_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "structural-entity-term-discourse-pronoun-v1",
) -> dict[str, Any]:
    return _run_stage10(database, nlp_run_id=int(nlp_run_id), parameters=parameters, implementation=implementation)


def run_stage12(
    *, database: Path | str, context_run_id: int,
    parameters: dict[str, Any] | None = None, implementation: str = "opus-en-ru-ct2",
) -> dict[str, Any]:
    return _run_stage12(database, context_run_id=int(context_run_id), parameters=parameters, implementation=implementation)


def run_stage14(
    *, database: Path | str, translation_run_id: int,
    parameters: dict[str, Any] | None = None, implementation: str = "glossary_refinement-current",
) -> dict[str, Any]:
    return _run_stage14(database, translation_run_id=int(translation_run_id), parameters=parameters, implementation=implementation)


def run_numeric_symbol_gate(
    *, database: Path | str, assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-numeric-symbol-preservation",
) -> dict[str, Any]:
    return _run_numeric_symbol_gate(database, assembly_id=int(assembly_id), parameters=parameters, implementation=implementation)


def run_punctuation_gate(
    *, database: Path | str, assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-punctuation-preservation",
) -> dict[str, Any]:
    return _run_punctuation_gate(database, assembly_id=int(assembly_id), parameters=parameters, implementation=implementation)


def run_length_ratio_gate(
    *, database: Path | str, assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-length-ratio-proxy",
) -> dict[str, Any]:
    return _run_length_ratio_gate(database, assembly_id=int(assembly_id), parameters=parameters, implementation=implementation)


def run_stage16(
    *, database: Path | str, assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "approve-if-clean-finalization",
) -> dict[str, Any]:
    return _run_stage16(database, assembly_id=int(assembly_id), parameters=parameters, implementation=implementation)


def run_stage17(
    *, database: Path | str, translation_revision_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "deterministic-structural-global",
) -> dict[str, Any]:
    return _run_stage17(database, translation_revision_id=int(translation_revision_id), parameters=parameters, implementation=implementation)


def run_stage18(
    *, database: Path | str, alignment_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE18_IMPLEMENTATION,
) -> dict[str, Any]:
    return _run_stage18(database, alignment_run_id=int(alignment_run_id), parameters=parameters, implementation=implementation)


def run_stage19(
    *, database: Path | str, extraction_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "deterministic-context-target-graph",
) -> dict[str, Any]:
    return _run_stage19(database, extraction_run_id=int(extraction_run_id), parameters=parameters, implementation=implementation)


def run_stage20(
    *, database: Path | str, sense_induction_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE20_POLICY,
) -> dict[str, Any]:
    return _run_stage20(database, sense_induction_run_id=int(sense_induction_run_id), parameters=parameters, implementation=implementation)


def run_stage21(
    *, database: Path | str, lexical_entry_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE21_POLICY,
) -> dict[str, Any]:
    return _run_stage21(database, lexical_entry_id=int(lexical_entry_id), parameters=parameters, implementation=implementation)


def run_stage22(
    *, database: Path | str, lexical_entry_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE22_POLICY,
) -> dict[str, Any]:
    return _run_stage22(database, lexical_entry_id=int(lexical_entry_id), parameters=parameters, implementation=implementation)


def run_stage23(
    *, database: Path | str, lexical_sense_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE23_POLICY,
) -> dict[str, Any]:
    return _run_stage23(database, lexical_sense_id=int(lexical_sense_id), parameters=parameters, implementation=implementation)


def run_stage24(
    *, database: Path | str, lexical_sense_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE24_POLICY,
) -> dict[str, Any]:
    return _run_stage24(database, lexical_sense_id=int(lexical_sense_id), parameters=parameters, implementation=implementation)


def run_stage25(
    *, database: Path | str, set_revision_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = STAGE25_POLICY,
) -> dict[str, Any]:
    return _run_stage25(database, set_revision_id=int(set_revision_id), parameters=parameters, implementation=implementation)


def assemble_card_set(
    *, database: Path | str, card_revision_ids: list[int],
    set_name: str = "RocketDict Product output",
) -> dict[str, Any]:
    return _assemble_card_set(database, card_revision_ids=card_revision_ids, set_name=set_name)


_bind(run_stage8, stage_number=8, implementation="en-sm", result_schema="rocketdict-product-stage8/1", identity_fields=["nlp_run_id"])
_bind(run_stage10, stage_number=10, implementation="structural-entity-term-discourse-pronoun-v1", result_schema="rocketdict-product-stage10/1", identity_fields=["context_run_id"])
_bind(run_stage12, stage_number=12, implementation="opus-en-ru-ct2", result_schema="rocketdict-product-stage12/1", identity_fields=["translation_run_id"], extra_required_fields=["real_mt"])
_bind(run_stage14, stage_number=14, implementation="glossary_refinement-current", result_schema="rocketdict-product-stage14/1", identity_fields=["assembly_id"], extra_required_fields=["real_mt_lineage"])
_bind(run_numeric_symbol_gate, stage_number=15, implementation="rocketdict-numeric-symbol-preservation", result_schema="rocketdict-product-stage15-quality/1", identity_fields=["quality_gate_run_id"], extra_required_fields=["passed"], hard_gate=True)
_bind(run_punctuation_gate, stage_number=15, implementation="rocketdict-punctuation-preservation", result_schema="rocketdict-product-stage15-quality/1", identity_fields=["quality_gate_run_id"], extra_required_fields=["passed"], hard_gate=True)
_bind(run_length_ratio_gate, stage_number=15, implementation="rocketdict-length-ratio-proxy", result_schema="rocketdict-product-stage15-quality/1", identity_fields=["quality_gate_run_id"], extra_required_fields=["passed"], hard_gate=True)
_bind(run_stage16, stage_number=16, implementation="approve-if-clean-finalization", result_schema="rocketdict-product-stage16/1", identity_fields=["translation_revision_id", "stage_result_id"], extra_required_fields=["approved"])
_bind(run_stage17, stage_number=17, implementation="deterministic-structural-global", result_schema="rocketdict-product-stage17/1", identity_fields=["alignment_run_id", "stage_result_id"], extra_required_fields=["coverage_complete"])
_bind(run_stage18, stage_number=18, implementation=STAGE18_IMPLEMENTATION, result_schema="rocketdict-product-stage18/1", identity_fields=["extraction_run_id", "stage_result_id", "alignment_run_id", "nlp_run_id"], extra_required_fields=["coverage_complete", "uncovered_token_count"])
_bind(run_stage19, stage_number=19, implementation="deterministic-context-target-graph", result_schema="rocketdict-product-stage19/1", identity_fields=["sense_induction_run_id", "stage_result_id"], extra_required_fields=["coverage_complete"])
_bind(run_stage20, stage_number=20, implementation=STAGE20_POLICY, result_schema="rocketdict-product-stage20/1", identity_fields=["sense_translation_run_id", "stage_result_id"], extra_required_fields=["coverage_complete", "real_mt"])
_bind(run_stage21, stage_number=21, implementation=STAGE21_POLICY, result_schema="rocketdict-product-stage21/1", identity_fields=["cefr_run_id", "stage_result_id", "cefr_assignment_id", "lexical_entry_id"])
_bind(run_stage22, stage_number=22, implementation=STAGE22_POLICY, result_schema="rocketdict-product-stage22/1", identity_fields=["pronunciation_run_id", "stage_result_id", "pronunciation_id", "lexical_entry_id"], extra_required_fields=["generated_fallback"])
_bind(run_stage23, stage_number=23, implementation=STAGE23_POLICY, result_schema="rocketdict-product-stage23/1", identity_fields=["example_run_id", "stage_result_id", "lexical_sense_id"], extra_required_fields=["scope_contract"])
_bind(run_stage24, stage_number=24, implementation=STAGE24_POLICY, result_schema="rocketdict-product-stage24/1", identity_fields=["card_run_id", "stage_result_id", "lexical_sense_id", "card_revision_id"], extra_required_fields=["complete"])
_bind(run_stage25, stage_number=25, implementation=STAGE25_POLICY, result_schema="rocketdict-product-stage25/1", identity_fields=["export_run_id", "stage_result_id", "set_revision_id"], extra_required_fields=["complete", "export_sha256"])

# Set assembly is deliberately a distinct callable rather than pretending to be
# the Stage24 per-sense card implementation.  Workbench discovery can identify
# it from the exact input/result contract without aliasing it to cards-current.
assemble_card_set.stage_number = 24  # type: ignore[attr-defined]
assemble_card_set.stage_key = "card_set_assembly"  # type: ignore[attr-defined]
assemble_card_set.implementation_key = SET_ASSEMBLY_POLICY  # type: ignore[attr-defined]
assemble_card_set.required_inputs = ["card_revision_ids", "set_name"]  # type: ignore[attr-defined]
assemble_card_set.adapter_descriptor_hash = _canonical_sha(  # type: ignore[attr-defined]
    {
        "stage_number": 24,
        "stage_key": "card_set_assembly",
        "implementation_key": SET_ASSEMBLY_POLICY,
        "required_inputs": ["card_revision_ids", "set_name"],
        "immutable": True,
    }
)
assemble_card_set.rocketdict_execution_contract = {  # type: ignore[attr-defined]
    "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    "transport": TRANSPORT,
    "replay_safe": True,
    "request": {
        "params": {
            "card_revision_ids": "input:card_revision_ids",
            "set_name": "input:set_name",
        }
    },
    "result": {
        "required_fields": ["schema", "set_revision_id", "card_count", "complete"],
        "identity_fields": ["set_revision_id"],
        "schema_field": "schema",
        "schema_values": ["rocketdict-product-card-set/1"],
    },
}

OPERATIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "product.stage8.run": run_stage8,
    "product.stage10.run": run_stage10,
    "product.stage12.run": run_stage12,
    "product.stage14.run": run_stage14,
    "product.stage15.numeric-symbol": run_numeric_symbol_gate,
    "product.stage15.punctuation": run_punctuation_gate,
    "product.stage15.length-ratio": run_length_ratio_gate,
    "product.stage16.run": run_stage16,
    "product.stage17.run": run_stage17,
    "product.stage18.run": run_stage18,
    "product.stage19.run": run_stage19,
    "product.stage20.run": run_stage20,
    "product.stage21.run": run_stage21,
    "product.stage22.run": run_stage22,
    "product.stage23.run": run_stage23,
    "product.stage24.run": run_stage24,
    "product.card-set.assemble": assemble_card_set,
    "product.stage25.run": run_stage25,
}
