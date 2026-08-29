from rocketdict_workbench.product_cefr import CEFRJ_BYTES, CEFRJ_ROWS, CEFRJ_SHA256, CEFRJ_URL, POLICY_KEY


def test_cefrj_product_source_is_pinned_and_not_smoke() -> None:
    assert POLICY_KEY == "workbench-cefrj-exact-v1"
    assert CEFRJ_SHA256 == "b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498"
    assert CEFRJ_BYTES == 233214
    assert CEFRJ_ROWS == 7799
    assert CEFRJ_URL.endswith("/cefrj-vocabulary-profile-1.5.csv")
