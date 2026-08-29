from __future__ import annotations

from typing import Any

from .product_policy import ProductPolicyError, product_parameter_overrides, select_product_implementation

PROFILE_SCHEMA = "rocketdict-workbench-product-profile/4"
QUALITY_GATES = (
    "rocketdict-numeric-symbol-preservation",
    "rocketdict-punctuation-preservation",
    "rocketdict-length-ratio-proxy",
)
PREFERRED_IMPLEMENTATIONS = {
    10: "structural-entity-term-discourse-pronoun-v1",
    14: "glossary_refinement-current",
    16: "approve-if-clean-finalization",
    17: "deterministic-structural-global",
    19: "deterministic-context-target-graph",
    21: "cefr-current",
    22: "pronunciation-current",
    23: "examples-current",
    24: "cards-current",
    25: "export-json",
}


def _stage(manifest: dict[str, Any], number: int) -> dict[str, Any]:
    for row in manifest.get("stages") or []:
        if int(row.get("number") or 0) == number:
            return row
    raise ProductPolicyError(f"Lab registry has no stage {number}")


def _implementation(stage: dict[str, Any], key: str) -> dict[str, Any]:
    for row in stage.get("implementations") or []:
        if row.get("implementation_key") == key:
            return row
    raise ProductPolicyError(f"Stage {stage.get('number')} has no implementation {key!r}")


def _defaults(implementation: dict[str, Any]) -> dict[str, Any]:
    return {
        str(control["key"]): control.get("default")
        for control in implementation.get("controls") or []
        if control.get("default") is not None
    }


def _select_named_or_product(manifest: dict[str, Any], number: int, *, source_kind: str) -> dict[str, Any]:
    stage = _stage(manifest, number)
    preferred = PREFERRED_IMPLEMENTATIONS.get(number)
    if preferred:
        try:
            impl = _implementation(stage, preferred)
            if not impl.get("production_eligible") or impl.get("testing_only"):
                raise ProductPolicyError(f"Preferred implementation is not production eligible: {preferred}")
            key, reason = preferred, "workbench_product_preference"
        except ProductPolicyError:
            selected = select_product_implementation(stage, require_available=False)
            key, reason = selected.implementation_key, selected.reason
    else:
        selected = select_product_implementation(stage, require_available=False)
        key, reason = selected.implementation_key, selected.reason
    impl = _implementation(stage, key)
    params = _defaults(impl)
    params.update(product_parameter_overrides(number, key, source_kind=source_kind))
    return {
        "stage_number": number,
        "stage_key": stage.get("key"),
        "implementation": key,
        "parameters": params,
        "selection_reason": reason,
        "adapter_descriptor_hash": impl.get("descriptor_hash"),
    }


def build_product_profile(lab_manifest: dict[str, Any], *, source_kind: str = "subtitle") -> dict[str, Any]:
    if source_kind not in {"subtitle", "text"}:
        raise ValueError("source_kind must be subtitle or text")
    selected: dict[int, dict[str, Any]] = {}
    for number in (8, 10, 12, 14, 16, 17, 19, 21, 22, 23, 24, 25):
        try:
            selected[number] = _select_named_or_product(lab_manifest, number, source_kind=source_kind)
        except ProductPolicyError:
            if number <= 19:
                raise

    # The historical Stage23 default includes a smoke Tatoeba fixture. Product
    # Mode never lets that diagnostic fixture become dictionary evidence.
    if 23 in selected:
        selected[23]["parameters"]["corpus_snapshots"] = []
        selected[23]["selection_reason"] = "workbench_document_examples_only"

    stage15 = _stage(lab_manifest, 15)
    gates = []
    for key in QUALITY_GATES:
        impl = _implementation(stage15, key)
        gates.append({
            "implementation": key,
            "parameters": _defaults(impl),
            "adapter_descriptor_hash": impl.get("descriptor_hash"),
            "hard_gate": True,
            "requires_reference": False,
        })

    return {
        "schema": PROFILE_SCHEMA,
        "source_kind": source_kind,
        "registry_hash": lab_manifest.get("registry_hash"),
        "source_language": lab_manifest.get("source_language", "en"),
        "target_language": lab_manifest.get("target_language", "ru"),
        "stages": {str(k): v for k, v in sorted(selected.items())},
        "quality_gates": gates,
        "workbench_stages": {
            "18": {
                "implementation": "workbench-aligned-content-pos-v3",
                "policy": "use approved alignment plus saved full NLP; project saved NLP tokens onto structurally split alignment segments by verified document-stream offsets; lexicalize content POS and dictionary-relevant MWEs; retain rejected token coverage",
                "requires_alignment": True,
                "offset_projection_fail_closed": True,
            },
            "20_provider": {
                "implementation": "contextual-lexical-opus-v3",
                "selection": "aligned-local-consensus",
                "probe_policy": "pos-dependency-dictionary-shape-v3",
                "retain_nbest_evidence": True,
                "preserve_dictionary_form_through_stage20": True,
            },
            "23": {
                "compatibility_contract": "stage23-sense-scope-v1",
                "review_identity": "lexical_sense_scoped_settings_hash",
                "corpus_smoke_disabled": True,
                "document_alignment_evidence_required_for_primary": True,
            },
        },
        "runtime_assets": {
            "nlp": {"preferred": "en-sm", "model": "en_core_web_sm", "model_version": "3.8.0", "offline_required": True},
            "translation": {"preferred": "opus-en-ru-ct2", "compute_type": "float32", "offline_required": True},
        },
        "lifecycle": {
            "translation_revision_requires_zero_hard_quality_failures": True,
            "alignment_requires_approved_translation_revision": True,
            "sense_induction_requires_complete_lexical_coverage": True,
            "singleton_policy": "singleton-safe-v1-audited",
            "cards_require_approved_sense_translation": True,
            "examples_require_sense_scoped_review_identity": True,
            "export_requires_complete_approved_card_set": True,
        },
        "invariants": {
            "fake_or_identity_mt_allowed": False,
            "network_required_during_processing": False,
            "code_only_nlp_allowed_for_final_dictionary": False,
            "reference_dependent_quality_gate_without_reference": False,
            "silent_source_loss_allowed": False,
            "unlicensed_numeric_addition_allowed": False,
            "research_overwrites_product_output": False,
            "diagnostic_smoke_corpus_allowed_as_product_example": False,
        },
    }
