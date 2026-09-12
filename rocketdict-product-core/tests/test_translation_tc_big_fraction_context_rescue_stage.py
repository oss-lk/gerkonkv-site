from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_fraction_context_rescue_stage as stage
from rocketdict.translation_tc_big_fraction_context_rescue_stage import (
    TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
    TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
    _base_parameters,
    evaluate_fraction_context_trigger,
    evaluate_fraction_member_trigger,
    evaluate_tc_big_fraction_context_candidate,
)


def _row(row_id: int, source: str, target: str, *, start: int, context: int = 5):
    return {
        "id": row_id,
        "sequence_number": row_id - 1,
        "kind": "translation_segment",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {"planner": {"source": "nlp_sentence_fragment", "context_sentence_start": context, "context_sentence_end": context}},
    }


def test_base_parameters_strip_only_fraction_context_controls() -> None:
    params = {
        "enable_parenthetical_context_rescue": True,
        "enable_tc_big_fraction_context_rescue": True,
        "tc_big_fraction_context_rescue_contract": TC_BIG_FRACTION_CONTEXT_RESCUE_CONTRACT,
        "tc_big_fraction_context_selector_contract": TC_BIG_FRACTION_CONTEXT_SELECTOR_CONTRACT,
        "tc_big_fraction_context_trigger_contract": TC_BIG_FRACTION_CONTEXT_TRIGGER_CONTRACT,
        "tc_big_fraction_context_max_nlp_tokens": 120,
    }
    assert _base_parameters(params) == {"enable_parenthetical_context_rescue": True}


def test_member_trigger_requires_isolated_denominator_prefix_truncation() -> None:
    source = "Measure 121/600 and 1222/6000: for the upper "
    good = evaluate_fraction_member_trigger(_row(1, source, "Измерьте 121/600 и 1222/600: для верхнего ", start=0))
    assert good["eligible"] is True
    assert good["truncation_pair"]["required"] == "1222/6000"
    assert good["truncation_pair"]["observed"] == "1222/600"
    wrong_num = evaluate_fraction_member_trigger(_row(2, source, "Измерьте 121/600 и 1221/600: для верхнего ", start=0))
    assert wrong_num["eligible"] is False
    non_prefix = evaluate_fraction_member_trigger(_row(3, source, "Измерьте 121/600 и 1222/601: для верхнего ", start=0))
    assert non_prefix["eligible"] is False


def test_context_trigger_requires_one_fraction_failure_and_strict_clean_siblings() -> None:
    left_source = "Measure 121/600 and 1222/6000: for the upper "
    right_source = "Glass was 1/8 inch thick and the Eye was 8 inches."
    left = _row(1, left_source, "Измерьте 121/600 и 1222/600: для верхнего ", start=0)
    right = _row(2, right_source, "Стекло было толщиной 1/8 дюйма, глаз был в 8 дюймах.", start=len(left_source))
    trigger = evaluate_fraction_context_trigger([left, right])
    assert trigger["eligible"] is True
    assert trigger["hard_failure_member_indices"] == [0]
    assert trigger["fraction_trigger_member_indices"] == [0]
    assert trigger["other_members_strict"] is True
    second_bad = _row(3, right_source, "Стекло было толщиной 1/9 дюйма, глаз был в 8 дюймах.", start=len(left_source))
    assert evaluate_fraction_context_trigger([left, second_bad])["eligible"] is False


def test_candidate_requires_full_fraction_terminal_and_content_retention() -> None:
    source = "Measure 121/600 and 1222/6000: For the upper Glass was 1/8 of an Inch thick, and my Eye was distant from it 8 Inches. "
    base = "Измерено 121/600 и 1222/600: верхнее стекло 1/8 дюйма, глаз в 8 дюймах."
    pair = {"required": "1222/6000", "observed": "1222/600", "numerator": "1222", "source_denominator": "6000", "target_denominator": "600", "missing_denominator_suffix": "0"}
    good_target = "Измерено 121/600 и 1222/6000: верхнее стекло было толщиной 1/8 дюйма, а глаз находился в 8 дюймах."
    good = evaluate_tc_big_fraction_context_candidate(source, good_target, base_target=base, truncation_pair=pair)
    assert good["accepted"] is True
    assert good["required_fraction_exactly_once"] is True
    assert good["truncated_fraction_absent"] is True
    assert good["terminal_punctuation_preserved"] is True
    truncated = evaluate_tc_big_fraction_context_candidate(source, "Измерено 121/600 и 1222/600: верхнее стекло было толщиной 1/8 дюйма, а глаз находился в 8 дюймах.", base_target=base, truncation_pair=pair)
    assert truncated["accepted"] is False
    no_period = evaluate_tc_big_fraction_context_candidate(source, good_target[:-1], base_target=base, truncation_pair=pair)
    assert no_period["accepted"] is False
    assert no_period["terminal_punctuation_preserved"] is False


def test_disabled_delegates_without_tc_big_probe(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    expected = {"translation_run_id": 20}
    seen = {}
    def fake_base(database, *, context_run_id, parameters, implementation):
        seen["parameters"] = parameters
        return expected
    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(stage, "tc_big_status", lambda: (_ for _ in ()).throw(AssertionError("no probe")))
    result = stage.run_stage12(tmp_path / "db.sqlite", context_run_id=2, parameters={"enable_parenthetical_context_rescue": True, "enable_tc_big_fraction_context_rescue": False})
    assert result is expected
    assert seen["parameters"] == {"enable_parenthetical_context_rescue": True}


def test_enabled_merges_only_eligible_context_with_raw_rank0(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    left_source = "Measure 121/600 and 1222/6000: for the upper "
    right_source = "Glass was 1/8 inch thick and the Eye was 8 inches. "
    tail_source = "Tail."
    source = left_source + right_source
    content = source + tail_source
    left = _row(11, left_source, "Измерьте 121/600 и 1222/600: для верхнего ", start=0, context=5)
    right = _row(12, right_source, "Стекло было толщиной 1/8 дюйма, глаз был в 8 дюймах. ", start=len(left_source), context=5)
    tail = _row(13, tail_source, "Хвост.", start=len(source), context=6)
    context_rows = [
        {"id": 101, "sequence_number": 5, "kind": "context_sentence", "source_start": 0, "source_end": len(source), "source_text": source, "target_text": "", "payload": {"token_count": 30}},
        {"id": 102, "sequence_number": 6, "kind": "context_sentence", "source_start": len(source), "source_end": len(content), "source_text": tail_source, "target_text": "", "payload": {"token_count": 1}},
    ]
    base_output = {"translation_run_id": 20, "document_version_id": 7, "model_request_count": 400}
    base_run = {"id": 20, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}
    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)
    def fake_items(connection, run_id, *, kind):
        if int(run_id) == 20 and kind == "translation_segment": return [left, right, tail]
        if int(run_id) == 2 and kind == "context_sentence": return context_rows
        raise AssertionError((run_id, kind))
    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (21, None))
    completed = {}
    def fake_complete(database, run_id, output, *, items):
        completed["items"] = items
        return output
    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    raw_target = "Измерено 121/600 и 1222/6000: верхнее стекло было толщиной 1/8 дюйма, а глаз находился в 8 дюймах."
    class FakeTranslator:
        def __init__(self, *, device, compute_type):
            assert device == "cpu" and compute_type == "float32"
        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):
            assert texts == [source]
            assert beam_size == 6 and num_hypotheses == 1
            return [[{"rank": 0, "text": raw_target, "score": -0.1}]]
    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(tmp_path / "db.sqlite", context_run_id=2, parameters={"enable_tc_big_fraction_context_rescue": True})
    assert result["translation_run_id"] == 21
    assert result["base_translation_run_id"] == 20
    assert result["tc_big_fraction_context_rescue_attempt_count"] == 1
    assert result["tc_big_fraction_context_rescue_accepted_count"] == 1
    assert result["tc_big_fraction_context_rescue_accepted_context_sequences"] == [5]
    assert result["tc_big_fraction_context_rescue_selected_ranks"] == [0]
    assert result["n_best_cherry_picking"] is False
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["source_text"] == source
    assert items[0]["target_text"] == raw_target
    rescue = items[0]["payload"]["tc_big_fraction_context_rescue"]
    assert rescue["raw_model_selected"] is True and rescue["raw_model_rank"] == 0
    assert items[1]["source_text"] == tail_source and items[1]["target_text"] == tail["target_text"]
    assert "".join(str(row["source_text"]) for row in items) == content
