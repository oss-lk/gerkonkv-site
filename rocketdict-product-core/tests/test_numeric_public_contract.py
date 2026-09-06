from __future__ import annotations

from pathlib import Path

import rocketdict.api.operations as product_operations
from rocketdict.api.registry import NUMERIC_INTEGRITY_CONTRACT, lab_manifest
from rocketdict.numeric_integrity import CONTRACT


def test_registry_binds_maintained_numeric_contract_into_descriptor_identity() -> None:
    assert NUMERIC_INTEGRITY_CONTRACT == CONTRACT
    manifest = lab_manifest(probe_runtime=False)
    stage15 = next(row for row in manifest["stages"] if int(row["number"]) == 15)
    numeric = next(
        row
        for row in stage15["implementations"]
        if row["implementation_key"] == "rocketdict-numeric-symbol-preservation"
    )
    controls = {row["key"]: row.get("default") for row in numeric["controls"]}
    assert controls == {"evaluator_contract": CONTRACT}
    assert "versioned-evaluator" in numeric["tags"]
    assert len(numeric["descriptor_hash"]) == 64


def test_public_numeric_operation_routes_to_maintained_evaluator(monkeypatch, tmp_path: Path) -> None:
    observed = {}

    def fake_gate(database, *, assembly_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed.update(
            {
                "database": Path(database),
                "assembly_id": assembly_id,
                "parameters": parameters,
                "implementation": implementation,
            }
        )
        return {"passed": True, "quality_gate_run_id": 17}

    monkeypatch.setattr(product_operations, "_run_numeric_symbol_gate", fake_gate)
    result = product_operations.OPERATIONS["product.stage15.numeric-symbol"](
        database=tmp_path / "core.sqlite",
        assembly_id=9,
        parameters={"evaluator_contract": CONTRACT},
        implementation="rocketdict-numeric-symbol-preservation",
    )
    assert result == {"passed": True, "quality_gate_run_id": 17}
    assert observed == {
        "database": tmp_path / "core.sqlite",
        "assembly_id": 9,
        "parameters": {"evaluator_contract": CONTRACT},
        "implementation": "rocketdict-numeric-symbol-preservation",
    }
