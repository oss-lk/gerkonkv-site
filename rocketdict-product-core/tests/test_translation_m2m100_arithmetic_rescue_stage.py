from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_m2m100_arithmetic_rescue_stage as stage
from rocketdict.stages import StageExecutionError


SOURCE = (
    "And therefore the elastick force of this\n"
    "Medium, in proportion to its density, must be above 700000 x 700000\n"
    "(that is, above 490,000,000,000) times greater than the elastick force\n"
    "of the Air is in proportion to its density. "
)
BASE = (
    "Таким образом, эластичная сила этого Среднего, пропорциональная его плотности, "
    "должна быть более 700000 х 700 000 (т.е. более 490 000 000 000 000) в раз больше, "
    "чем эластичная сила воздуха пропорционально его плотности."
)
CANDIDATE = (
    "И поэтому эластичная сила этого Среднего, в пропорции к его плотности, должна быть "
    "выше 700 000 x 700 000 (то есть выше 490 000 000 000) раз больше, чем эластичная "
    "сила воздуха в пропорции к его плотности."
)


def _row(row_id: int, source: str, target: str, *, start: int = 0) -> dict[str, object]:
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
            "planner": {"source": "neutral_fixture", "split": False, "token_count": 40},
        },
    }


def _runtime() -> dict[str, object]:
    return {
        "available": True,
        "asset_manifest_sha256": "c" * 64,
        "asset_payload_tree_sha256": "d" * 64,
        "repository": "facebook/m2m100_418M",
        "revision": "revision-1",
        "model_sha256": "e" * 64,
        "compute_type": "float32",
        "source_language": "en",
        "target_language": "ru",
    }


def _patch_base(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rows: list[dict[str, object]],
    content: str,
) -> dict[str, object]:
    base_output: dict[str, object] = {
        "translation_run_id": 58,
        "document_version_id": 7,
        "model_request_count": 600,
    }
    base_run = {"id": 58, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}
    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(stage, "get_run_items", lambda connection, run_id, *, kind: rows)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    return base_output


def test_contract_is_default_off_and_wraps_run58_outer_layer_controls() -> None:
    assert stage.DEFAULT_ENABLED is False
    assert stage.BEAM_SIZE == 6
    assert stage.NUM_HYPOTHESES == 1
    assert stage.MAX_DECODING_LENGTH == 512
    parameters = {
        "enable_tc_big_numeric_row_rescue": True,
        "enable_m2m100_arithmetic_rescue": True,
        "m2m100_arithmetic_rescue_contract": stage.M2M100_ARITHMETIC_RESCUE_CONTRACT,
        "m2m100_arithmetic_selector_contract": stage.M2M100_ARITHMETIC_SELECTOR_CONTRACT,
        "m2m100_arithmetic_trigger_contract": stage.M2M100_ARITHMETIC_TRIGGER_CONTRACT,
    }
    assert stage._base_parameters(parameters) == {"enable_tc_big_numeric_row_rescue": True}


def test_disabled_run_delegates_without_runtime_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 58}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "m2m100_status",
        lambda: (_ for _ in ()).throw(AssertionError("runtime must not be probed")),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_numeric_row_rescue": True,
            "enable_m2m100_arithmetic_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_tc_big_numeric_row_rescue": True}


def test_enabled_run_accepts_exact_source_raw_rank0_and_records_runtime_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    clean_source = "Clean row."
    clean_target = "Чистая строка."
    rows = [
        _row(31, SOURCE, BASE, start=0),
        _row(32, clean_source, clean_target, start=len(SOURCE)),
    ]
    content = SOURCE + clean_source
    _patch_base(monkeypatch, rows=rows, content=content)
    monkeypatch.setattr(stage, "m2m100_status", lambda: dict(_runtime()))
    start_observed: dict[str, object] = {}

    def fake_start(database, *, stage_number, implementation, input_identity, parameters):  # type: ignore[no-untyped-def]
        start_observed["identity"] = input_identity
        return 59, None

    monkeypatch.setattr(stage, "_start", fake_start)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    observed: dict[str, object] = {}

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            observed["texts"] = texts
            observed["generation"] = (beam_size, num_hypotheses, max_decoding_length)
            return [[{"rank": 0, "text": CANDIDATE, "score": -0.25}]]

    monkeypatch.setattr(stage, "M2M100Translator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_m2m100_arithmetic_rescue": True},
    )

    assert result["translation_run_id"] == 59
    assert result["base_translation_run_id"] == 58
    assert result["m2m100_arithmetic_rescue_attempt_count"] == 1
    assert result["m2m100_arithmetic_rescue_accepted_count"] == 1
    assert result["m2m100_arithmetic_rescue_rejected_count"] == 0
    assert result["m2m100_arithmetic_rescue_selected_ranks"] == [0]
    assert result["m2m100_arithmetic_rescue_accepted_source_starts"] == [0]
    assert result["model_request_count"] == 601
    assert observed["texts"] == [SOURCE]
    assert observed["generation"] == (6, 1, 512)

    identity = start_observed["identity"]
    assert identity["base_translation_run_id"] == 58
    assert identity["m2m100_runtime_identity"]["revision"] == "revision-1"
    assert identity["m2m100_runtime_identity"]["asset_payload_tree_sha256"] == "d" * 64

    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["source_text"] == SOURCE
    assert items[0]["target_text"] == CANDIDATE
    rescue = items[0]["payload"]["m2m100_arithmetic_rescue"]
    assert rescue["model_input"] == SOURCE
    assert rescue["model_input_equals_source"] is True
    assert rescue["raw_model_selected"] is True
    assert rescue["raw_model_rank"] == 0
    assert rescue["runtime_identity"]["revision"] == "revision-1"
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert items[1]["target_text"] == clean_target
    assert items[1]["payload"]["m2m100_arithmetic_rescue"]["applied"] is False
    assert "".join(str(item["source_text"]) for item in items) == content


def test_rejected_rank0_leaves_base_target_exact(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    row = _row(41, SOURCE, BASE)
    _patch_base(monkeypatch, rows=[row], content=SOURCE)
    monkeypatch.setattr(stage, "m2m100_status", lambda: dict(_runtime()))
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (59, None))
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)

    class BadTranslator:
        def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

        def translate(self, texts, **kwargs):  # type: ignore[no-untyped-def]
            bad = CANDIDATE.replace(" x ", " на ")
            return [[{"rank": 0, "text": bad, "score": -0.1}]]

    monkeypatch.setattr(stage, "M2M100Translator", BadTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_m2m100_arithmetic_rescue": True},
    )
    assert result["m2m100_arithmetic_rescue_attempt_count"] == 1
    assert result["m2m100_arithmetic_rescue_accepted_count"] == 0
    assert result["m2m100_arithmetic_rescue_rejected_count"] == 1
    items = completed["items"]
    assert items[0]["target_text"] == BASE
    assert items[0]["payload"]["m2m100_arithmetic_rescue"]["applied"] is False


def test_eligible_row_requires_available_runtime_and_exact_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    row = _row(51, SOURCE, BASE)
    _patch_base(monkeypatch, rows=[row], content=SOURCE)
    monkeypatch.setattr(stage, "m2m100_status", lambda: {"available": False, "reason": "missing"})
    with pytest.raises(StageExecutionError, match="runtime unavailable"):
        stage.run_stage12(
            tmp_path / "rocketdict.sqlite",
            context_run_id=2,
            parameters={"enable_m2m100_arithmetic_rescue": True},
        )

    mismatched_content = "X" + SOURCE[1:]
    _patch_base(monkeypatch, rows=[row], content=mismatched_content)
    monkeypatch.setattr(
        stage,
        "m2m100_status",
        lambda: (_ for _ in ()).throw(AssertionError("runtime must not be probed")),
    )
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (59, None))
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "_complete", lambda database, run_id, output, *, items: output)
    with pytest.raises(StageExecutionError, match="source coverage"):
        stage.run_stage12(
            tmp_path / "rocketdict.sqlite",
            context_run_id=2,
            parameters={"enable_m2m100_arithmetic_rescue": True},
        )


def test_controls_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    with pytest.raises(StageExecutionError, match="must be boolean"):
        stage.run_stage12(
            tmp_path / "rocketdict.sqlite",
            context_run_id=2,
            parameters={"enable_m2m100_arithmetic_rescue": "yes"},
        )

    with pytest.raises(StageExecutionError, match="Unsupported M2M100 arithmetic rescue contract"):
        stage.run_stage12(
            tmp_path / "rocketdict.sqlite",
            context_run_id=2,
            parameters={
                "enable_m2m100_arithmetic_rescue": True,
                "m2m100_arithmetic_rescue_contract": "wrong",
            },
        )

    with pytest.raises(StageExecutionError, match="internal"):
        stage.run_stage12(
            tmp_path / "rocketdict.sqlite",
            context_run_id=2,
            parameters={
                "enable_m2m100_arithmetic_rescue": True,
                "m2m100_arithmetic_rescue_phase": "wrong",
            },
        )
