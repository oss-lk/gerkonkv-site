from rocketdict_workbench.product_pronunciation import POLICY_KEY, product_pronunciation_settings


def test_product_pronunciation_is_exact_only() -> None:
    settings = product_pronunciation_settings()
    assert POLICY_KEY == "workbench-cmudict-exact-v1"
    assert settings["requested_dialects"] == ["en-US"]
    assert settings["enable_generated_fallback"] is False
    assert settings["enable_mwe_composition"] is True
    assert settings["include_russian_hint"] is False
