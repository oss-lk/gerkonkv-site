from __future__ import annotations

import json
from pathlib import Path

import pytest

import rocketdict_workbench.final_product_pipeline as final
from rocketdict_workbench.upstream_pipeline import PUBLIC_EXECUTION_CONTRACT_SCHEMA, TRANSPORT


def test_incomplete_stage24_journal_tail_is_physically_truncated_before_append(tmp_path) -> None:
    path = tmp_path / "cards.jsonl"
    first = {
        "schema": final.CARD_JOURNAL_SCHEMA,
        "lexical_sense_id": 1,
        "previous_record_sha256": None,
        "request_sha256": "a" * 64,
        "result": {"card_revision_id": 101},
        "result_sha256": final._canonical_sha256({"card_revision_id": 101}),
        "card_revision_id": 101,
        "completed_at": "2026-09-05T00:00:00+00:00",
    }
    final._append_journal(path, first)
    durable = path.read_bytes()
    with path.open("ab") as fh:
        fh.write(b'{"schema":"partial","lexical_sense_id":2')
    assert path.read_bytes() != durable

    second = {
        "schema": final.CARD_JOURNAL_SCHEMA,
        "lexical_sense_id": 2,
        "previous_record_sha256": final._canonical_sha256({**first}),
        "request_sha256": "b" * 64,
        "result": {"card_revision_id": 102},
        "result_sha256": final._canonical_sha256({"card_revision_id": 102}),
        "card_revision_id": 102,
        "completed_at": "2026-09-05T00:00:01+00:00",
    }
    # previous_record_sha256 must use the actually committed first record hash.
    first_line = json.loads(durable.decode("utf-8"))
    second["previous_record_sha256"] = first_line["record_sha256"]
    final._append_journal(path, second)

    raw = path.read_bytes()
    assert b'"schema":"partial"' not in raw
    assert raw.endswith(b"\n")
    records, last_sha = final._read_journal(path, [1, 2])
    assert [row["lexical_sense_id"] for row in records] == [1, 2]
    assert last_sha == records[-1]["record_sha256"]


def test_set_assembly_duplicate_operation_key_across_mappings_remains_ambiguous(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "db.sqlite"
    database.touch()
    state_path = tmp_path / "run.json"
    state_path.write_text("{}", encoding="utf-8")
    state = {"root_identity": {"fingerprint": "e" * 64}}
    preflight = {"identity": {"fingerprint": "f" * 64}}
    probe = {
        "database": {"path": str(database.resolve())},
        "callable_operations": [
            {
                "operation": "product.cards.assemble_set",
                "mapping_module": "rocketdict.api.operations",
                "mapping_name": "OPERATIONS",
                "callable_module": "rocketdict.api.operations",
                "callable_qualname": "assemble_set",
                "source_sha256": "1" * 64,
            },
            {
                "operation": "product.cards.assemble_set",
                "mapping_module": "rocketdict.api.other_operations",
                "mapping_name": "OTHER_OPERATIONS",
                "callable_module": "rocketdict.api.other_operations",
                "callable_qualname": "assemble_set_other",
                "source_sha256": "2" * 64,
            },
        ],
    }
    manifest = {
        "fingerprint": "3" * 64,
        "card_revision_ids": [11, 12],
    }
    contract = {
        "schema": PUBLIC_EXECUTION_CONTRACT_SCHEMA,
        "transport": TRANSPORT,
        "replay_safe": True,
        "request": {
            "params": {
                "card_revision_ids": "input:card_revision_ids",
                "set_name": "input:set_name",
            }
        },
        "result": {
            "required_fields": ["schema", "set_revision_id"],
            "identity_fields": ["set_revision_id"],
            "schema_field": "schema",
            "schema_values": ["set-result/1"],
        },
    }
    monkeypatch.setattr(final, "_load_verified_evidence", lambda path: (state, preflight, probe))
    monkeypatch.setattr(final, "require_quality_gate_pass", lambda path: {"status": "passed"})
    monkeypatch.setattr(final, "_load_complete_card_manifest", lambda path, value: manifest)
    monkeypatch.setattr(final, "_probe_generic_contract", lambda core, db, row: contract)

    discovery = final.discover_set_assembly(object(), database, state_path)
    assert discovery["status"] == "ambiguous_exact_matches"
    assert len(discovery["exact_matches"]) == 2
    assert {
        (row["mapping_module"], row["mapping_name"], row["source_sha256"])
        for row in discovery["exact_matches"]
    } == {
        ("rocketdict.api.operations", "OPERATIONS", "1" * 64),
        ("rocketdict.api.other_operations", "OTHER_OPERATIONS", "2" * 64),
    }


def test_set_assembly_requires_same_database_as_immutable_api_probe(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    state_path = tmp_path / "run.json"
    state_path.write_text("{}", encoding="utf-8")
    other_database = tmp_path / "other.sqlite"
    probe_database = tmp_path / "probe.sqlite"
    other_database.touch()
    probe_database.touch()
    state = {"root_identity": {"fingerprint": "e" * 64}}
    preflight = {"identity": {"fingerprint": "f" * 64}}
    probe = {"database": {"path": str(probe_database.resolve())}, "callable_operations": []}
    monkeypatch.setattr(final, "_load_verified_evidence", lambda path: (state, preflight, probe))
    monkeypatch.setattr(final, "require_quality_gate_pass", lambda path: {"status": "passed"})

    with pytest.raises(RuntimeError, match="database differs"):
        final.discover_set_assembly(object(), other_database, state_path)
