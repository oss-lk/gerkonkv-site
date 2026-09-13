from __future__ import annotations

import rocketdict.api.operations as operations


def test_public_stage12_routes_through_default_off_arithmetic_outer_wrapper() -> None:
    assert operations._run_stage12.__module__ == (
        "rocketdict.translation_m2m100_arithmetic_rescue_stage"
    )
    assert operations.run_stage12.stage_number == 12
    assert operations.run_stage12.implementation_key == "opus-en-ru-ct2"
    assert operations.run_stage12.required_inputs == ["context_run_id"]
    contract = operations.run_stage12.rocketdict_execution_contract
    assert contract["replay_safe"] is True
    assert contract["result"]["schema_values"] == ["rocketdict-product-stage12/1"]
    assert contract["result"]["identity_fields"] == ["translation_run_id"]
