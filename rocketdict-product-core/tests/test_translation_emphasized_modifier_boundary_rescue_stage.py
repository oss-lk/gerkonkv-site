from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_emphasized_modifier_boundary_rescue_stage as stage
from rocketdict.translation_emphasized_modifier_boundary_rescue_stage import (
    EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT,
    EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT,
    EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT,
    _base_parameters,
    discover_emphasized_modifier_groups,
    evaluate_emphasized_modifier_boundary,
    evaluate_emphasized_modifier_candidate,
    evaluate_emphasized_modifier_group_trigger,
)


def _context(sequence: int, source: str, *, start: int, tokens: int = 8):
    return {
        "id": 100 + sequence,
        "sequence_number": sequence,
        "kind": "context_sentence",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": "",
        "payload": {"token_count": tokens},
    }


def _row(
    row_id: int,
    source: str,
    target: str,
    *,
    start: int,
):
    return {
        "id": row_id,
        "sequence_number": row_id - 1,
        "kind": "translation_segment",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {"planner": {"source": "nlp_sentence"}},
    }


def test_base_parameters_strip_only_wrapper_controls() -> None:
    params = {
        "enable_tc_big_fraction_context_rescue": True,
        "enable_emphasized_modifier_boundary_rescue": True,
        "emphasized_modifier_boundary_rescue_contract": (
            EMPHASIZED_MODIFIER_BOUNDARY_RESCUE_CONTRACT
        ),
        "emphasized_modifier_boundary_selector_contract": (
            EMPHASIZED_MODIFIER_BOUNDARY_SELECTOR_CONTRACT
        ),
        "emphasized_modifier_boundary_trigger_contract": (
            EMPHASIZED_MODIFIER_BOUNDARY_TRIGGER_CONTRACT
        ),
        "emphasized_modifier_boundary_max_nlp_tokens": 100,
    }
    assert _base_parameters(params) == {
        "enable_tc_big_fraction_context_rescue": True
    }


def test_source_boundary_is_generic_and_fail_closed() -> None:
    left = _context(1, "Distance 10 _Foreign_ ", start=0)
    right = _context(2, "Units were measured.", start=left["source_end"])
    good = evaluate_emphasized_modifier_boundary(left, right)
    assert good["eligible"] is True
    assert good["emphasized_single_word"] == "Foreign"
    assert good["right_lexical_start"] == "Units"

    multi = _context(1, "Distance _very Foreign_ ", start=0)
    assert (
        evaluate_emphasized_modifier_boundary(
            multi,
            _context(2, "Units.", start=multi["source_end"]),
        )["eligible"]
        is False
    )
    heading = _context(1, "BOOK _PART I._ ", start=0)
    assert (
        evaluate_emphasized_modifier_boundary(
            heading,
            _context(2, "Proposition.", start=heading["source_end"]),
        )["eligible"]
        is False
    )
    paragraph = _context(1, "Distance _Foreign_\n\n", start=0)
    assert (
        evaluate_emphasized_modifier_boundary(
            paragraph,
            _context(2, "Units.", start=paragraph["source_end"]),
        )["eligible"]
        is False
    )
    lower = _context(1, "Distance _Foreign_ ", start=0)
    assert (
        evaluate_emphasized_modifier_boundary(
            lower,
            _context(2, "units.", start=lower["source_end"]),
        )["eligible"]
        is False
    )


def test_group_discovery_coalesces_consecutive_boundaries() -> None:
    a = _context(10, "Speed 10 _Foreign_ ", start=0)
    b = _context(11, "Feet and 20 _Foreign_ ", start=a["source_end"])
    c = _context(12, "Miles.", start=b["source_end"])
    d = _context(13, " Next sentence.", start=c["source_end"])
    groups = discover_emphasized_modifier_groups([a, b, c, d])
    assert [row["context_sequences"] for row in groups] == [[10, 11, 12]]
    assert len(groups[0]["boundaries"]) == 2


def test_trigger_requires_one_numeric_hard_failure_and_clean_sibling() -> None:
    left_source = "Distance is 70,000,000 _Foreign_ "
    right_source = "Miles and parallax is 12''. "
    left = _row(
        1,
        left_source,
        "Расстояние 70 000 000 _Foreign_ ",
        start=0,
    )
    right = _row(
        2,
        right_source,
        "Миль, параллакс 12'. ",
        start=len(left_source),
    )
    trigger = evaluate_emphasized_modifier_group_trigger(
        [left, right],
        boundaries=[{"eligible": True}],
    )
    assert trigger["eligible"] is True
    assert trigger["numeric_failure_member_indices"] == [1]
    assert trigger["hard_failure_member_indices"] == [1]

    second_bad = _row(
        3,
        left_source,
        "Расстояние 71 000 000 _Foreign_ ",
        start=0,
    )
    assert (
        evaluate_emphasized_modifier_group_trigger(
            [second_bad, right],
            boundaries=[{"eligible": True}],
        )["eligible"]
        is False
    )


def test_candidate_requires_strict_emphasis_content_and_terminal_punctuation() -> None:
    source = (
        "Light travels about 70,000,000 _Foreign_ Miles, "
        "with parallax about 12''. "
    )
    base = (
        "Свет проходит около 70 000 000 _Foreign_ Майлз, "
        "параллакс около 12'."
    )
    good_target = (
        "Свет проходит около 70 000 000 _Foreign_ миль, "
        "параллакс около 12''."
    )
    good = evaluate_emphasized_modifier_candidate(
        source, good_target, base_target=base
    )
    assert good["accepted"] is True

    no_emphasis = evaluate_emphasized_modifier_candidate(
        source,
        "Свет проходит около 70 000 000 иностранных миль, параллакс около 12''.",
        base_target=base,
    )
    assert no_emphasis["accepted"] is False
    assert no_emphasis["emphasis_markup"]["passed"] is False

    no_period = evaluate_emphasized_modifier_candidate(
        source, good_target[:-1], base_target=base
    )
    assert no_period["accepted"] is False
    assert no_period["terminal_punctuation_preserved"] is False


def test_disabled_delegates_without_opus_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    expected = {"translation_run_id": 22}
    seen = {}

    def fake_base(database, *, context_run_id, parameters, implementation):
        seen["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "OpusTranslator",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("no translator")
        ),
    )
    result = stage.run_stage12(
        tmp_path / "db.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_fraction_context_rescue": True,
            "enable_emphasized_modifier_boundary_rescue": False,
        },
    )
    assert result is expected
    assert seen["parameters"] == {
        "enable_tc_big_fraction_context_rescue": True
    }


def test_enabled_accepts_only_raw_rank0_eligible_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    left_source = "Light is 70,000,000 _Foreign_ "
    right_source = "Miles and parallax is 12''. "
    tail_source = "Tail."
    source = left_source + right_source
    content = source + tail_source

    left_context = _context(5, left_source, start=0, tokens=7)
    right_context = _context(
        6, right_source, start=left_context["source_end"], tokens=6
    )
    tail_context = _context(
        7, tail_source, start=right_context["source_end"], tokens=1
    )
    left = _row(
        11,
        left_source,
        "Свет 70 000 000 _Foreign_ ",
        start=0,
    )
    right = _row(
        12,
        right_source,
        "Майлз и параллакс 12'. ",
        start=len(left_source),
    )
    tail = _row(13, tail_source, "Хвост.", start=len(source))

    base_output = {
        "translation_run_id": 22,
        "document_version_id": 7,
        "model_request_count": 400,
    }
    base_run = {
        "id": 22,
        "output": base_output,
        "output_sha256": "a" * 64,
    }
    context_run = {"id": 2, "output_sha256": "c" * 64}
    document = {
        "id": 7,
        "content_text": content,
        "text_sha256": "b" * 64,
    }

    monkeypatch.setattr(
        stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output)
    )
    monkeypatch.setattr(
        stage,
        "connect",
        lambda *args, **kwargs: nullcontext(SimpleNamespace()),
    )

    def fake_get_run(connection, run_id):
        return base_run if int(run_id) == 22 else context_run

    monkeypatch.setattr(stage, "get_run", fake_get_run)

    def fake_items(connection, run_id, *, kind):
        if int(run_id) == 22 and kind == "translation_segment":
            return [left, right, tail]
        if int(run_id) == 2 and kind == "context_sentence":
            return [left_context, right_context, tail_context]
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(
        stage,
        "get_document",
        lambda connection, document_version_id: document,
    )
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (23, None))
    completed = {}

    def fake_complete(database, run_id, output, *, items):
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)

    raw_target = (
        "Свет находится в 70 000 000 _Foreign_ миль, "
        "и параллакс равен 12''."
    )

    class FakeTranslator:
        def __init__(self, *, device, compute_type):
            assert device == "cpu" and compute_type == "float32"

        def translate(
            self,
            texts,
            *,
            beam_size,
            num_hypotheses,
            max_decoding_length,
        ):
            assert texts == [source]
            assert beam_size == 6
            assert num_hypotheses == 1
            assert max_decoding_length == stage.MAX_DECODING_LENGTH
            return [[{"rank": 0, "text": raw_target, "score": -0.1}]]

    monkeypatch.setattr(stage, "OpusTranslator", FakeTranslator)

    result = stage.run_stage12(
        tmp_path / "db.sqlite",
        context_run_id=2,
        parameters={"enable_emphasized_modifier_boundary_rescue": True},
    )
    assert result["translation_run_id"] == 23
    assert result["base_translation_run_id"] == 22
    assert result["emphasized_modifier_boundary_attempt_count"] == 1
    assert result["emphasized_modifier_boundary_accepted_count"] == 1
    assert result["emphasized_modifier_boundary_accepted_context_groups"] == [
        [5, 6]
    ]
    assert result["emphasized_modifier_boundary_selected_ranks"] == [0]
    assert result["n_best_cherry_picking"] is False

    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    assert items[0]["source_text"] == source
    assert items[0]["target_text"] == raw_target
    rescue = items[0]["payload"]["emphasized_modifier_boundary_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["raw_model_rank"] == 0
    assert items[1]["source_text"] == tail_source
    assert items[1]["target_text"] == tail["target_text"]
    assert "".join(str(row["source_text"]) for row in items) == content
