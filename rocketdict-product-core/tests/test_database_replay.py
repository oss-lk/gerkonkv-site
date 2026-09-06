from __future__ import annotations

from pathlib import Path

from rocketdict.database import (
    begin_run,
    bootstrap_database,
    fail_run,
    finish_run,
    get_run,
    transaction,
)


def _begin(db: Path) -> tuple[int, bool]:
    with transaction(db) as connection:
        return begin_run(
            connection,
            stage_number=18,
            stage_key="lexical_extraction",
            implementation="workbench-aligned-content-pos-v4",
            input_identity={"alignment_run_id": 17, "alignment_sha256": "a" * 64},
            parameters={},
        )


def test_running_identity_is_resumed_with_same_durable_run_id(tmp_path: Path) -> None:
    db = tmp_path / "rocketdict.sqlite"
    bootstrap_database(db)

    first_id, first_cached = _begin(db)
    resumed_id, resumed_cached = _begin(db)

    assert first_cached is False
    assert resumed_cached is False
    assert resumed_id == first_id
    with transaction(db) as connection:
        finish_run(
            connection,
            first_id,
            {
                "schema": "rocketdict-product-stage18/1",
                "extraction_run_id": first_id,
                "stage_result_id": first_id,
            },
        )

    cached_id, cached = _begin(db)
    assert cached is True
    assert cached_id == first_id
    with transaction(db) as connection:
        row = get_run(connection, first_id)
    assert row["status"] == "completed"


def test_failed_identity_starts_a_new_attempt_but_running_identity_does_not(tmp_path: Path) -> None:
    db = tmp_path / "rocketdict.sqlite"
    bootstrap_database(db)

    first_id, _ = _begin(db)
    with transaction(db) as connection:
        fail_run(connection, first_id, {"type": "SyntheticFailure", "message": "failed cleanly"})

    retry_id, retry_cached = _begin(db)
    assert retry_cached is False
    assert retry_id != first_id
    resumed_id, resumed_cached = _begin(db)
    assert resumed_cached is False
    assert resumed_id == retry_id
