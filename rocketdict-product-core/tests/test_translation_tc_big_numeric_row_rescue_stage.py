from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_numeric_row_rescue_stage as stage
from rocketdict.translation_tc_big_numeric_row_rules import (
    VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
    VARIANT_DENSE_FORMULA_MISSING,
    VARIANT_PROGRESSION_DUPLICATE,
)


def _row(row_id: int, source: str, target: str, *, start: int) -> dict[str, object]:
    return {
        "id": row_id,
        "sequence_number": row_id - 1,
        "kind": "translation_segment",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {
            "selected_rank": 0,
            "hypotheses": [{"rank": 0, "text": target, "score": -0.4}],
            "planner": {"source": "neutral_fixture", "split": False, "token_count": 20},
        },
    }


def _cases() -> list[tuple[str, str, str, str]]:
    return [
        (
            "The progression is 1, 3, 5, 7, 9, 11, &c. in the table. ",
            "Прогрессия равна 1, 3, 5, 7, 9, 11, 11, &c. в таблице. ",
            "Прогрессия равна 1, 3, 5, 7, 9, 11, &c. в таблице. ",
            VARIANT_PROGRESSION_DUPLICATE,
        ),
        (
            "The formula values 3/8A, 5/16A, 9A and 8A remain fixed in the table. ",
            "Значения формулы 3/8A, 5/16A и 9A остаются фиксированными в таблице. ",
            "Значения формулы 3/8A, 5/16A, 9A и 8A остаются фиксированными в таблице. ",
            VARIANT_DENSE_FORMULA_MISSING,
        ),
        (
            "The measured values are 1'688, 2'389, 2'925, 3'375 inches in order. ",
            "Измеренные значения равны 1'688, 2'38, 2'925, 3'375 дюйма по порядку. ",
            "Измеренные значения равны 1'688, 2'389, 2'925, 3'375 дюйма по порядку. ",
            VARIANT_APOSTROPHE_DECIMAL_TRUNCATION,
        ),
    ]


def test_contract_is_default_off_and_strips_only_own_controls() -> None:
    assert stage.DEFAULT_ENABLED is False
    assert stage.BEAM_SIZE == 6
    assert stage.NUM_HYPOTHESES == 1
    parameters = {
        "enable_tc_big_parenthetical_row_rescue": True,
        "enable_tc_big_numeric_row_rescue": True,
        "tc_big_numeric_row_rescue_contract": stage.TC_BIG_NUMERIC_ROW_RESCUE_CONTRACT,
        "tc_big_numeric_row_selector_contract": stage.SELECTOR_CONTRACT,
        "tc_big_numeric_row_trigger_contract": stage.TRIGGER_CONTRACT,
    }
    assert stage._base_parameters(parameters) == {
        "enable_tc_big_parenthetical_row_rescue": True
    }


def test_disabled_run_delegates_without_runtime_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 57}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "tc_big_status",
        lambda: (_ for _ in ()).throw(AssertionError("runtime must not be probed")),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_parenthetical_row_rescue": True,
            "enable_tc_big_numeric_row_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_tc_big_parenthetical_row_rescue": True}


def test_enabled_run_batches_exact_sources_and_applies_all_three_variants(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    rows: list[dict[str, object]] = []
    expected_targets: list[str] = []
    expected_variants: list[str] = []
    cursor = 0
    for row_id, (source, base, clean, variant) in enumerate(_cases(), start=21):
        rows.append(_row(row_id, source, base, start=cursor))
        cursor += len(source)
        expected_targets.append(clean)
        expected_variants.append(variant)
    clean_source = "Clean row."
    clean_target = "Чистая строка."
    rows.append(_row(24, clean_source, clean_target, start=cursor))
    content = "".join(str(row["source_text"]) for row in rows)

    base_output = {
        "translation_run_id": 57,
        "document_version_id": 7,
        "model_request_count": 500,
    }
    base_run = {"id": 57, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(
        stage,
        "get_run_items",
        lambda connection, run_id, *, kind: rows
        if int(run_id) == 57 and kind == "translation_segment"
        else (_ for _ in ()).throw(AssertionError((run_id, kind))),
    )
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)

    runtime = {
        "available": True,
        "asset_manifest_sha256": "c" * 64,
        "asset_payload_tree_sha256": "d" * 64,
        "repository": "neutral/tc-big",
        "revision": "revision-1",
        "model_safetensors_sha256": "e" * 64,
        "compute_type": "float32",
    }
    monkeypatch.setattr(stage, "tc_big_status", lambda: dict(runtime))
    start_observed: dict[str, object] = {}

    def fake_start(database, *, stage_number, implementation, input_identity, parameters):  # type: ignore[no-untyped-def]
        start_observed["identity"] = input_identity
        return 58, None

    monkeypatch.setattr(stage, "_start", fake_start)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [case[0] for case in _cases()]
            assert beam_size == 6 and num_hypotheses == 1
            return [
                [{"rank": 0, "text": target, "score": -0.2}]
                for target in expected_targets
            ]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_numeric_row_rescue": True},
    )

    assert result["translation_run_id"] == 58
    assert result["base_translation_run_id"] == 57
    assert result["tc_big_numeric_row_rescue_attempt_count"] == 3
    assert result["tc_big_numeric_row_rescue_accepted_count"] == 3
    assert result["tc_big_numeric_row_rescue_rejected_count"] == 0
    assert result["tc_big_numeric_row_rescue_selected_ranks"] == [0, 0, 0]
    assert result["tc_big_numeric_row_rescue_selected_variants"] == expected_variants
    assert result["model_request_count"] == 503
    identity = start_observed["identity"]
    assert identity["base_translation_run_id"] == 57
    assert identity["tc_big_runtime_identity"]["revision"] == "revision-1"
    assert identity["tc_big_runtime_identity"]["asset_payload_tree_sha256"] == "d" * 64

    items = completed["items"]
    assert isinstance(items, list) and len(items) == 4
    assert [item["target_text"] for item in items[:3]] == expected_targets
    assert items[3]["target_text"] == clean_target
    assert items[3]["payload"]["tc_big_numeric_row_rescue"]["applied"] is False
    for item, (source, _base, clean, variant) in zip(items[:3], _cases(), strict=True):
        rescue = item["payload"]["tc_big_numeric_row_rescue"]
        assert item["source_text"] == source
        assert item["target_text"] == clean
        assert rescue["variant"] == variant
        assert rescue["model_input"] == source
        assert rescue["model_input_equals_source"] is True
        assert rescue["raw_model_selected"] is True
        assert rescue["raw_model_rank"] == 0
        assert rescue["runtime_identity"]["revision"] == "revision-1"
    assert "".join(str(item["source_text"]) for item in items) == content


def test_rejected_rank0_leaves_base_row_exact(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    source, base, _clean, _variant = _cases()[0]
    row = _row(31, source, base, start=0)
    base_output = {"translation_run_id": 57, "document_version_id": 9, "model_request_count": 10}
    base_run = {"id": 57, "output": base_output, "output_sha256": "f" * 64}
    document = {"id": 9, "content_text": source, "text_sha256": "a" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(stage, "get_run_items", lambda connection, run_id, *, kind: [row])
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (58, None))
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    completed: dict[str, object] = {}
    monkeypatch.setattr(
        stage,
        "_complete",
        lambda database, run_id, output, *, items: completed.setdefault("result", (output, items))[0],
    )

    class BadTranslator:
        def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

        def translate(self, texts, **kwargs):  # type: ignore[no-untyped-def]
            return [[{"rank": 0, "text": "Прогрессия равна 1, 3, 5, 7, 9, 11 в таблице.", "score": -0.1}]]

    monkeypatch.setattr(stage, "TcBigTranslator", BadTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_numeric_row_rescue": True},
    )
    assert result["tc_big_numeric_row_rescue_attempt_count"] == 1
    assert result["tc_big_numeric_row_rescue_accepted_count"] == 0
    assert result["tc_big_numeric_row_rescue_rejected_count"] == 1
    items = completed["result"][1]
    assert items[0]["source_text"] == source
    assert items[0]["target_text"] == base
    assert items[0]["payload"]["tc_big_numeric_row_rescue"]["applied"] is False
