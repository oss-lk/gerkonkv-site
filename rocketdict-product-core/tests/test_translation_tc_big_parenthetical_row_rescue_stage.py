from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_parenthetical_row_rescue_stage as stage
from rocketdict.translation_tc_big_parenthetical_row_rescue_stage import (
    BEAM_SIZE,
    DEFAULT_ENABLED,
    MAX_PARENTHESES_PAIRS,
    NUM_HYPOTHESES,
    TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT,
    TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT,
    TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT,
    _base_parameters,
    _eligible_rows,
    evaluate_tc_big_parenthetical_row_candidate,
    evaluate_tc_big_parenthetical_row_trigger,
)


def _row(
    row_id: int,
    source: str,
    target: str,
    *,
    source_start: int = 0,
) -> dict[str, object]:
    return {
        "id": row_id,
        "sequence_number": row_id - 1,
        "kind": "translation_segment",
        "source_start": source_start,
        "source_end": source_start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {
            "planner": {
                "source": "neutral_fixture",
                "split": False,
                "token_count": 20,
            }
        },
    }


def test_contract_is_default_off_unique_rank0_and_strips_only_own_controls() -> None:
    assert DEFAULT_ENABLED is False
    assert BEAM_SIZE == 6
    assert NUM_HYPOTHESES == 1
    assert MAX_PARENTHESES_PAIRS == 2
    parameters = {
        "enable_emphasized_modifier_boundary_rescue": True,
        "enable_tc_big_parenthetical_row_rescue": True,
        "tc_big_parenthetical_row_rescue_contract": (
            TC_BIG_PARENTHETICAL_ROW_RESCUE_CONTRACT
        ),
        "tc_big_parenthetical_row_selector_contract": (
            TC_BIG_PARENTHETICAL_ROW_SELECTOR_CONTRACT
        ),
        "tc_big_parenthetical_row_trigger_contract": (
            TC_BIG_PARENTHETICAL_ROW_TRIGGER_CONTRACT
        ),
    }
    assert _base_parameters(parameters) == {
        "enable_emphasized_modifier_boundary_rescue": True
    }


def test_trigger_accepts_one_or_two_short_balanced_pairs_without_planner_whitelist() -> None:
    one_source = "The bright part (near orange) remains visible."
    one = _row(
        1,
        one_source,
        "Яркая часть рядом с оранжевым остается видимой.",
    )
    trigger = evaluate_tc_big_parenthetical_row_trigger(one, source_exact=True)
    assert trigger["eligible"] is True
    assert trigger["source_parenthetical_pair_count"] == 1
    assert trigger["round_parenthesis_loss_only"] is True
    assert trigger["other_hard_punctuation_exact"] is True

    two_source = "The first half (near red) and second half (near green) overlap."
    two = _row(
        2,
        two_source,
        "Первая половина рядом с красным и вторая половина рядом с зеленым перекрываются.",
    )
    trigger = evaluate_tc_big_parenthetical_row_trigger(two, source_exact=True)
    assert trigger["eligible"] is True
    assert trigger["source_parenthetical_pair_count"] == 2
    assert trigger["source_parenthetical_alpha_word_counts"] == [2, 2]


def test_trigger_fails_closed_for_non_exact_nested_three_pair_and_added_round_shapes() -> None:
    source = "The bright part (near orange) remains visible."
    row = _row(1, source, "Яркая часть рядом с оранжевым остается видимой.")
    assert evaluate_tc_big_parenthetical_row_trigger(
        row, source_exact=False
    )["eligible"] is False

    three_source = "The points (a), (b), and (c) remain fixed."
    three = _row(2, three_source, "Точки a, b и c остаются неподвижными.")
    trigger = evaluate_tc_big_parenthetical_row_trigger(three, source_exact=True)
    assert trigger["source_parenthetical_pair_count"] is None
    assert trigger["eligible"] is False

    nested_source = "The value (inside (nested) text) remains fixed."
    nested = _row(
        3,
        nested_source,
        "Значение внутри вложенного текста остается неподвижным.",
    )
    assert evaluate_tc_big_parenthetical_row_trigger(
        nested, source_exact=True
    )["eligible"] is False

    added = _row(
        4,
        source,
        "Яркая часть ((рядом с оранжевым)) остается видимой.",
    )
    trigger = evaluate_tc_big_parenthetical_row_trigger(added, source_exact=True)
    assert trigger["round_parenthesis_loss_only"] is False
    assert trigger["eligible"] is False


def test_trigger_rejects_other_hard_punctuation_and_unrelated_gate_debt() -> None:
    question_source = "Does the bright part (near orange) remain visible?"
    question = _row(
        1,
        question_source,
        "Яркая часть рядом с оранжевым остается видимой.",
    )
    trigger = evaluate_tc_big_parenthetical_row_trigger(
        question, source_exact=True
    )
    assert trigger["other_hard_punctuation_exact"] is False
    assert trigger["eligible"] is False

    numeric_source = "The band (near orange) contains 37 rays."
    numeric = _row(
        2,
        numeric_source,
        "Полоса рядом с оранжевым содержит лучи.",
    )
    trigger = evaluate_tc_big_parenthetical_row_trigger(numeric, source_exact=True)
    assert trigger["base_clean_except_round_parentheses"] is False
    assert trigger["eligible"] is False


def test_candidate_requires_strict_punctuation_emphasis_volume_and_base_retention() -> None:
    source = "The _bright_ part (near orange) remains visible."
    base = "Яркая часть рядом с оранжевым остается видимой."
    clean = "Яркая _светлая_ часть (рядом с оранжевым) остается видимой."
    selection = evaluate_tc_big_parenthetical_row_candidate(
        source, clean, base_target=base
    )
    assert selection["accepted"] is True
    assert selection["hard_punctuation_exact"] is True
    assert selection["emphasis_markup"]["passed"] is True
    assert selection["base_alpha_retained"] is True

    missing_emphasis = evaluate_tc_big_parenthetical_row_candidate(
        source,
        "Яркая часть (рядом с оранжевым) остается видимой.",
        base_target=base,
    )
    assert missing_emphasis["emphasis_markup"]["passed"] is False
    assert missing_emphasis["accepted"] is False

    missing_parens = evaluate_tc_big_parenthetical_row_candidate(
        source,
        "Яркая _светлая_ часть рядом с оранжевым остается видимой.",
        base_target=base,
    )
    assert missing_parens["hard_punctuation_exact"] is False
    assert missing_parens["accepted"] is False

    compressed = evaluate_tc_big_parenthetical_row_candidate(
        source,
        "_Часть_ (рядом).",
        base_target=base,
    )
    assert (
        compressed["source_alpha_ratio_passed"] is False
        or compressed["base_alpha_retained"] is False
        or compressed["strictly_eligible"] is False
    )
    assert compressed["accepted"] is False


def test_eligible_rows_require_exact_document_slice() -> None:
    source = "The bright part (near orange) remains visible. "
    row = _row(
        1,
        source,
        "Яркая часть рядом с оранжевым остается видимой. ",
    )
    assert len(_eligible_rows(content=source, base_rows=[row])) == 1
    assert _eligible_rows(content="X" + source[1:], base_rows=[row]) == []


def test_disabled_run_delegates_without_tc_big_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 17}
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
            "enable_emphasized_modifier_boundary_rescue": True,
            "enable_tc_big_parenthetical_row_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {
        "enable_emphasized_modifier_boundary_rescue": True
    }


def test_enabled_run_uses_exact_source_raw_rank0_and_preserves_unrelated_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    first_source = "The bright part (near orange) remains visible. "
    second_source = "Clean row."
    content = first_source + second_source
    first = _row(
        21,
        first_source,
        "Яркая часть рядом с оранжевым остается видимой. ",
        source_start=0,
    )
    second = _row(
        22,
        second_source,
        "Чистая строка.",
        source_start=len(first_source),
    )
    base_output = {
        "translation_run_id": 17,
        "document_version_id": 7,
        "model_request_count": 500,
    }
    base_run = {"id": 17, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}

    monkeypatch.setattr(
        stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output)
    )
    monkeypatch.setattr(
        stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace())
    )
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(
        stage,
        "get_run_items",
        lambda connection, run_id, *, kind: [first, second]
        if int(run_id) == 17 and kind == "translation_segment"
        else (_ for _ in ()).throw(AssertionError((run_id, kind))),
    )
    monkeypatch.setattr(
        stage, "get_document", lambda connection, document_version_id: document
    )
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (18, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    raw_rank0 = "Яркая часть (рядом с оранжевым) остается видимой. "

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(
            self, texts, *, beam_size, num_hypotheses, max_decoding_length
        ):  # type: ignore[no-untyped-def]
            assert texts == [first_source]
            assert beam_size == BEAM_SIZE
            assert num_hypotheses == 1
            return [[{"rank": 0, "text": raw_rank0, "score": -0.1}]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_parenthetical_row_rescue": True},
    )
    assert result["translation_run_id"] == 18
    assert result["base_translation_run_id"] == 17
    assert result["tc_big_parenthetical_row_rescue_attempt_count"] == 1
    assert result["tc_big_parenthetical_row_rescue_accepted_count"] == 1
    assert result["tc_big_parenthetical_row_rescue_rejected_count"] == 0
    assert result["tc_big_parenthetical_row_rescue_selected_ranks"] == [0]
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["source_text"] == first_source
    assert items[0]["target_text"] == raw_rank0
    rescue = items[0]["payload"]["tc_big_parenthetical_row_rescue"]
    assert rescue["model_input"] == first_source
    assert rescue["model_input_equals_source"] is True
    assert rescue["raw_model_selected"] is True
    assert rescue["raw_model_rank"] == 0
    assert items[0]["payload"]["hypotheses"][0]["text"] == raw_rank0
    assert items[1]["target_text"] == second["target_text"]
    assert (
        items[1]["payload"]["tc_big_parenthetical_row_rescue"]["applied"] is False
    )
    assert "".join(str(item["source_text"]) for item in items) == content


def test_enabled_run_rejects_bad_rank0_without_partial_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    source = "The _bright_ part (near orange) remains visible."
    base_target = "Яркая часть рядом с оранжевым остается видимой."
    row = _row(31, source, base_target)
    base_output = {
        "translation_run_id": 27,
        "document_version_id": 9,
        "model_request_count": 12,
    }
    base_run = {"id": 27, "output": base_output, "output_sha256": "c" * 64}
    document = {"id": 9, "content_text": source, "text_sha256": "d" * 64}

    monkeypatch.setattr(
        stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output)
    )
    monkeypatch.setattr(
        stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace())
    )
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    monkeypatch.setattr(
        stage,
        "get_run_items",
        lambda connection, run_id, *, kind: [row],
    )
    monkeypatch.setattr(
        stage, "get_document", lambda connection, document_version_id: document
    )
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (28, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            pass

        def translate(
            self, texts, *, beam_size, num_hypotheses, max_decoding_length
        ):  # type: ignore[no-untyped-def]
            return [[{
                "rank": 0,
                "text": "Яркая часть (рядом с оранжевым) остается видимой.",
                "score": -0.2,
            }]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_parenthetical_row_rescue": True},
    )
    assert result["tc_big_parenthetical_row_rescue_attempt_count"] == 1
    assert result["tc_big_parenthetical_row_rescue_accepted_count"] == 0
    assert result["tc_big_parenthetical_row_rescue_rejected_count"] == 1
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 1
    assert items[0]["source_text"] == source
    assert items[0]["target_text"] == base_target
    assert (
        items[0]["payload"]["tc_big_parenthetical_row_rescue"]["applied"] is False
    )
