from __future__ import annotations

from collections import Counter

from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_run_state import probe_core_api_surface


def test_maintained_core_probe_has_one_canonical_mapping_per_product_operation(tmp_path) -> None:
    database = tmp_path / "rocketdict.sqlite"
    database.write_bytes(b"")

    probe = probe_core_api_surface(RocketDictCore(), database)
    operations = list(probe.get("callable_operations") or [])
    counts = Counter(str(row.get("operation") or "") for row in operations)

    product_counts = {key: value for key, value in counts.items() if key.startswith("product.")}
    assert product_counts
    assert set(product_counts.values()) == {1}

    stage8 = next(row for row in operations if row.get("operation") == "product.stage8.run")
    assert stage8["mapping_module"] == "rocketdict.api.operations"
    assert stage8["mapping_name"] == "OPERATIONS"
    assert stage8["callable_module"] == "rocketdict.api.operations"
