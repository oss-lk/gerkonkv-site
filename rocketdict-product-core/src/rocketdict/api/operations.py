from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from rocketdict.api.contracts import (
    PUBLIC_EXECUTION_CONTRACT_SCHEMA,
    PUBLIC_QUALITY_GATE_SEMANTICS_SCHEMA,
    TRANSPORT,
)
from rocketdict.api.registry import descriptor_hash, required_inputs, stage_key
from rocketdict.lexical import run_stage18 as _run_stage18, run_stage19 as _run_stage19
from rocketdict.stages import (
    run_length_ratio_gate as _run_length_ratio_gate,
    run_numeric_symbol_gate as _run_numeric_symbol_gate,
    run_punctuation_gate as _run_punctuation_gate,
    run_stage8 as _run_stage8,
    run_stage10 as _run_stage10,
    run_stage12 as _run_stage12,
    run_stage14 as _run_stage14,
    run_stage16 as _run_stage16,
    run_stage17 as _run_stage17,
)


def _execution_contract(
    stage_number: int,
    inputs: list[str],
    *,
    result_schema: str,
    identity_fields: list[str],
    extra_required_fields: list[str] | None = None,
) -> dict[str, Any]:
    required = ["schema", *identity_fields, *(extra_required_fields or [])]
    # Keep order stable while refusing accidental duplicate result fields.
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
    inputs = required_inputs(stage_number, implementation)
    fn.stage_number = int(stage_number)  # type: ignore[attr-defined]
    fn.stage_key = stage_key(stage_number)  # type: ignore[attr-defined]
    fn.implementation_key = implementation  # type: ignore[attr-defined]
    fn.adapter_descriptor_hash = descriptor_hash(stage_number, implementation)  # type: ignore[attr-defined]
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
    *,
    database: Path | str,
    document_version_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "en-sm",
) -> dict[str, Any]:
    return _run_stage8(
        database,
        document_version_id=int(document_version_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_stage10(
    *,
    database: Path | str,
    nlp_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "structural-entity-term-discourse-pronoun-v1",
) -> dict[str, Any]:
    return _run_stage10(
        database,
        nlp_run_id=int(nlp_run_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_stage12(
    *,
    database: Path | str,
    context_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "opus-en-ru-ct2",
) -> dict[str, Any]:
    return _run_stage12(
        database,
        context_run_id=int(context_run_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_stage14(
    *,
    database: Path | str,
    translation_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "glossary_refinement-current",
) -> dict[str, Any]:
    return _run_stage14(
        database,
        translation_run_id=int(translation_run_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_numeric_symbol_gate(
    *,
    database: Path | str,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-numeric-symbol-preservation",
) -> dict[str, Any]:
    return _run_numeric_symbol_gate(
        database,
        assembly_id=int(assembly_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_punctuation_gate(
    *,
    database: Path | str,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-punctuation-preservation",
) -> dict[str, Any]:
    return _run_punctuation_gate(
        database,
        assembly_id=int(assembly_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_length_ratio_gate(
    *,
    database: Path | str,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "rocketdict-length-ratio-proxy",
) -> dict[str, Any]:
    return _run_length_ratio_gate(
        database,
        assembly_id=int(assembly_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_stage16(
    *,
    database: Path | str,
    assembly_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "approve-if-clean-finalization",
) -> dict[str, Any]:
    return _run_stage16(
        database,
        assembly_id=int(assembly_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_stage17(
    *,
    database: Path | str,
    translation_revision_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "deterministic-structural-global",
) -> dict[str, Any]:
    return _run_stage17(
        database,
        translation_revision_id=int(translation_revision_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_stage18(
    *,
    database: Path | str,
    alignment_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "workbench-aligned-content-pos-v4",
) -> dict[str, Any]:
    return _run_stage18(
        database,
        alignment_run_id=int(alignment_run_id),
        parameters=parameters,
        implementation=implementation,
    )


def run_stage19(
    *,
    database: Path | str,
    extraction_run_id: int,
    parameters: dict[str, Any] | None = None,
    implementation: str = "deterministic-context-target-graph",
) -> dict[str, Any]:
    return _run_stage19(
        database,
        extraction_run_id=int(extraction_run_id),
        parameters=parameters,
        implementation=implementation,
    )


_bind(
    run_stage8,
    stage_number=8,
    implementation="en-sm",
    result_schema="rocketdict-product-stage8/1",
    identity_fields=["nlp_run_id"],
)
_bind(
    run_stage10,
    stage_number=10,
    implementation="structural-entity-term-discourse-pronoun-v1",
    result_schema="rocketdict-product-stage10/1",
    identity_fields=["context_run_id"],
)
_bind(
    run_stage12,
    stage_number=12,
    implementation="opus-en-ru-ct2",
    result_schema="rocketdict-product-stage12/1",
    identity_fields=["translation_run_id"],
    extra_required_fields=["real_mt"],
)
_bind(
    run_stage14,
    stage_number=14,
    implementation="glossary_refinement-current",
    result_schema="rocketdict-product-stage14/1",
    identity_fields=["assembly_id"],
    extra_required_fields=["real_mt_lineage"],
)
_bind(
    run_numeric_symbol_gate,
    stage_number=15,
    implementation="rocketdict-numeric-symbol-preservation",
    result_schema="rocketdict-product-stage15-quality/1",
    identity_fields=["quality_gate_run_id"],
    extra_required_fields=["passed"],
    hard_gate=True,
)
_bind(
    run_punctuation_gate,
    stage_number=15,
    implementation="rocketdict-punctuation-preservation",
    result_schema="rocketdict-product-stage15-quality/1",
    identity_fields=["quality_gate_run_id"],
    extra_required_fields=["passed"],
    hard_gate=True,
)
_bind(
    run_length_ratio_gate,
    stage_number=15,
    implementation="rocketdict-length-ratio-proxy",
    result_schema="rocketdict-product-stage15-quality/1",
    identity_fields=["quality_gate_run_id"],
    extra_required_fields=["passed"],
    hard_gate=True,
)
_bind(
    run_stage16,
    stage_number=16,
    implementation="approve-if-clean-finalization",
    result_schema="rocketdict-product-stage16/1",
    identity_fields=["translation_revision_id", "stage_result_id"],
    extra_required_fields=["approved"],
)
_bind(
    run_stage17,
    stage_number=17,
    implementation="deterministic-structural-global",
    result_schema="rocketdict-product-stage17/1",
    identity_fields=["alignment_run_id", "stage_result_id"],
    extra_required_fields=["coverage_complete"],
)
# Stage18 is a maintained-core operation even though current Workbench Product
# profile still treats it as an internal bridge. Its public contract enables the
# next migration step away from historical ORM helpers.
_bind(
    run_stage18,
    stage_number=18,
    implementation="workbench-aligned-content-pos-v4",
    result_schema="rocketdict-product-stage18/1",
    identity_fields=["extraction_run_id", "stage_result_id", "alignment_run_id", "nlp_run_id"],
    extra_required_fields=["coverage_complete", "uncovered_token_count"],
)
_bind(
    run_stage19,
    stage_number=19,
    implementation="deterministic-context-target-graph",
    result_schema="rocketdict-product-stage19/1",
    identity_fields=["sense_induction_run_id", "stage_result_id"],
    extra_required_fields=["coverage_complete"],
)

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
}
