from __future__ import annotations

import rocketdict.api.operations as operations
import rocketdict.translation_combined_greek_rescue_stage as combined_greek


def test_public_stage12_uses_combined_greek_outer_wrapper() -> None:
    assert operations._run_stage12 is combined_greek.run_stage12


def test_public_stage12_descriptor_identity_remains_product_stage12() -> None:
    assert operations.run_stage12.stage_number == 12
    assert operations.run_stage12.stage_key == "translation_baseline"
    assert operations.run_stage12.implementation_key == "opus-en-ru-ct2"
    assert operations.run_stage12.required_inputs == ["context_run_id"]
