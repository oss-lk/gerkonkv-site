from __future__ import annotations

import json
from pathlib import Path

import pytest

from rocketdict.database import (
    begin_run,
    bootstrap_database,
    connect,
    finish_run,
    get_run,
    replace_run_items,
    transaction,
)
from rocketdict.numeric_integrity import (
    CONTRACT,
    compare_numeric_integrity,
    contains_numeric_literal,
    evaluate_numeric_symbol_pair,
    run_numeric_symbol_gate,
)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("22-1/2 Inches", "22 1/2 дюйма"),
        ("24th order", "24-й порядок"),
        ("1/89000th part", "1/89000-я часть"),
        ("42d observation", "42-я запись"),
        ("1,000,000 times", "1 000 000 раз"),
        ("1,000 times", "1 000 раз"),
        ("1,5 Inches", "1,5 дюйма"),
        ("1'699 and 0'000625", "1,699 и 0,000625"),
        ("four Inches and sixteen Feet", "4 дюйма и 16 футов"),
        ("twenty one divisions", "21 деление"),
    ],
)
def test_documented_numeric_equivalences_pass(source: str, target: str) -> None:
    result = compare_numeric_integrity(source, target)
    assert result["contract"] == CONTRACT
    assert result["passed"] is True


def test_documented_literals_are_detected() -> None:
    for literal in (
        "22-1/2",
        "24th",
        "1/89000th",
        "42d",
        "1 000 000",
        "1,000,000",
        "1,5",
        "1'699",
        "0'000625",
        "4'27",
    ):
        assert contains_numeric_literal(literal), literal


@pytest.mark.parametrize(
    ("source", "target", "missing", "additions"),
    [
        (
            "[in _Fig._ 2.] four Inches eight Feet three Feet",
            "[на рис.] 4 дюйма 8 футов 3 фута",
            {"2": 1},
            {},
        ),
        (
            "15 Min. that of the exterior 3 Degr.",
            "15 Мин. внешней части.",
            {"3": 1},
            {},
        ),
        (
            "1000000, 1000000000000, or 1000000000000000000 times rarer",
            "1 000 000 000 и 1 000 000 000 000 раз реже",
            {"1000000": 1, "1000000000000000000": 1},
            {"1000000000": 1},
        ),
    ],
)
def test_known_failure_classes_remain_fail_closed(
    source: str,
    target: str,
    missing: dict[str, int],
    additions: dict[str, int],
) -> None:
    result = compare_numeric_integrity(source, target)
    assert result["passed"] is False
    assert result["missing"] == missing
    assert result["unlicensed_additions"] == additions


def test_known_nbest_preserving_hypothesis_passes() -> None:
    result = compare_numeric_integrity(
        "15 Min. that of the exterior 3 Degr.",
        "15 Мин. внешней части 3 дегр.",
    )
    assert result["passed"] is True


def test_duplicates_and_unlicensed_additions_fail() -> None:
    duplicate = compare_numeric_integrity("15 Min.", "15 мин. 15")
    assert duplicate["passed"] is False
    assert duplicate["duplicate_required"] == {"15": 1}

    addition = compare_numeric_integrity("15 Min.", "15 мин. 99")
    assert addition["passed"] is False
    assert addition["unlicensed_additions"] == {"99": 1}


def test_critical_multiplication_and_division_symbols_are_preserved() -> None:
    assert evaluate_numeric_symbol_pair("4 × 2 ÷ 1", "4 × 2 ÷ 1")["passed"] is True
    result = evaluate_numeric_symbol_pair("4 × 2 ÷ 1", "4 x 2 / 1")
    assert result["passed"] is False
    assert result["symbol_mismatch"] == {
        "×": {"source": 1, "target": 0},
        "÷": {"source": 1, "target": 0},
    }


def _seed_assembly(db: Path) -> int:
    with transaction(db) as connection:
        run_id, cache_hit = begin_run(
            connection,
            stage_number=14,
            stage_key="refinement",
            implementation="glossary_refinement-current",
            input_identity={"seed": "numeric-contract"},
            parameters={},
        )
        assert cache_hit is False
        replace_run_items(
            connection,
            run_id,
            [
                {
                    "sequence_number": 0,
                    "kind": "assembly_segment",
                    "source_start": 0,
                    "source_end": 18,
                    "source_text": "Value 1,000 × 2.",
                    "target_text": "Значение 1 000 × 2.",
                    "payload": {},
                }
            ],
        )
        finish_run(
            connection,
            run_id,
            {
                "schema": "rocketdict-product-stage14/1",
                "assembly_id": run_id,
                "segment_count": 1,
                "real_mt_lineage": True,
            },
        )
    return run_id


def test_gate_contract_version_prevents_reusing_old_parameterless_pass(tmp_path: Path) -> None:
    db = tmp_path / "core.sqlite"
    bootstrap_database(db)
    assembly_id = _seed_assembly(db)
    with connect(db, readonly=True) as connection:
        assembly = get_run(connection, assembly_id)
    input_identity = {
        "assembly_id": assembly_id,
        "assembly_output_sha256": str(assembly["output_sha256"]),
    }

    # Simulate a completed cache row from the previous parser semantics.
    with transaction(db) as connection:
        old_run_id, cache_hit = begin_run(
            connection,
            stage_number=15,
            stage_key="quality",
            implementation="rocketdict-numeric-symbol-preservation",
            input_identity=input_identity,
            parameters={},
        )
        assert cache_hit is False
        finish_run(
            connection,
            old_run_id,
            {
                "schema": "rocketdict-product-stage15-quality/1",
                "quality_gate_run_id": old_run_id,
                "assembly_id": assembly_id,
                "implementation": "rocketdict-numeric-symbol-preservation",
                "passed": True,
                "failure_count": 0,
                "issues_sha256": "legacy",
            },
        )

    result = run_numeric_symbol_gate(db, assembly_id=assembly_id)
    assert result["passed"] is True
    assert result["cache_hit"] is False
    assert int(result["quality_gate_run_id"]) != old_run_id
    with connect(db, readonly=True) as connection:
        row = connection.execute(
            "SELECT parameters_json FROM stage_runs WHERE id=?",
            (int(result["quality_gate_run_id"]),),
        ).fetchone()
    assert row is not None
    assert json.loads(str(row["parameters_json"])) == {"evaluator_contract": CONTRACT}
