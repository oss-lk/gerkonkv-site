from __future__ import annotations

from rocketdict.api.registry import lab_manifest
from rocketdict.translation_rescue_stage import (
    DEFAULT_ENABLED,
    DEFAULT_WHOLE_CONTEXT_ENABLED,
    MAX_WHOLE_CONTEXT_NLP_TOKENS,
    WHOLE_CONTEXT_RESCUE_CONTRACT,
)
from rocketdict_workbench.product_policy import product_parameter_overrides
from rocketdict_workbench.product_profile import build_product_profile


def _stage12_opus(manifest: dict) -> dict:
    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)
    return next(
        row
        for row in stage12["implementations"]
        if row["implementation_key"] == "opus-en-ru-ct2"
    )


def test_semantically_unapproved_rescues_are_fail_closed_everywhere() -> None:
    manifest = lab_manifest(probe_runtime=False)
    opus = _stage12_opus(manifest)
    controls = {row["key"]: row.get("default") for row in opus["controls"]}

    assert DEFAULT_ENABLED is False
    assert controls["enable_selective_resegmentation_rescue"] is False
    assert "selective-resegmentation-rescue-research-only" in opus["tags"]

    assert DEFAULT_WHOLE_CONTEXT_ENABLED is False
    assert controls["enable_whole_context_rescue"] is False
    assert controls["whole_context_rescue_contract"] == WHOLE_CONTEXT_RESCUE_CONTRACT
    assert controls["whole_context_rescue_max_nlp_tokens"] == MAX_WHOLE_CONTEXT_NLP_TOKENS
    assert "whole-context-rescue-research-only" in opus["tags"]

    overrides = product_parameter_overrides(12, "opus-en-ru-ct2", source_kind="text")
    assert overrides["enable_selective_resegmentation_rescue"] is False
    assert overrides["enable_whole_context_rescue"] is False

    profile = build_product_profile(manifest, source_kind="text")
    params = profile["stages"]["12"]["parameters"]
    assert params["enable_selective_resegmentation_rescue"] is False
    assert params["enable_whole_context_rescue"] is False
