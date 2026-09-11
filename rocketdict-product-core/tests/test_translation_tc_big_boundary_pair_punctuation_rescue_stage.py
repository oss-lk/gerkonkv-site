from __future__ import annotations

from contextlib import nullcontext
import re
from types import SimpleNamespace

import pytest

import rocketdict.translation_tc_big_boundary_pair_punctuation_rescue_stage as stage
from rocketdict.translation_tc_big_boundary_pair_punctuation_rescue_stage import (
    TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT,
    TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT,
    TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT,
    _base_parameters,
    _eligible_pairs,
    evaluate_tc_big_boundary_pair_punctuation_candidate,
    evaluate_tc_big_boundary_pair_punctuation_trigger,
)


def _row(row_id: int, sequence: int, source: str, target: str, start: int, context: int) -> dict[str, object]:
    return {
        "id": row_id,
        "sequence_number": sequence,
        "kind": "translation_segment",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {"planner": {
            "source": "nlp_sentence",
            "context_sentence_start": context,
            "context_sentence_end": context,
            "context_sentence_count": 1,
        }},
    }


def _context(sequence: int, source: str, start: int, sentence_index: int) -> dict[str, object]:
    return {
        "id": 100 + sequence,
        "sequence_number": sequence,
        "kind": "context_sentence",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": "",
        "payload": {"sentence_index": sentence_index},
    }


def _nlp_rows(parts: list[tuple[str, int]]) -> tuple[str, list[dict[str, object]]]:
    content = "".join(text for text, _index in parts)
    rows: list[dict[str, object]] = []
    cursor = 0
    token_index = 0
    for text, sentence_index in parts:
        for match in re.finditer(r"[A-Za-z]+|\d+|[^\w\s]", text):
            token = match.group(0)
            rows.append({
                "id": 200 + token_index,
                "sequence_number": token_index,
                "kind": "nlp_token",
                "source_start": cursor + match.start(),
                "source_end": cursor + match.end(),
                "source_text": token,
                "target_text": None,
                "payload": {
                    "sentence_index": sentence_index,
                    "token_index": token_index,
                    "flags": {"is_space": False, "is_punct": not token[0].isalnum()},
                },
            })
            token_index += 1
        cursor += len(text)
    return content, rows


def _fixture_rows() -> tuple[str, list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    left_source = "And whence is it "
    right_source = "but from water?"
    third_source = " Next."
    content, nlp = _nlp_rows([(left_source, 0), (right_source, 1), (third_source, 2)])
    left = _row(11, 0, left_source, "И откуда это? ", 0, 0)
    right = _row(12, 1, right_source, "но из воды?", len(left_source), 1)
    third = _row(13, 2, third_source, " Далее.", len(left_source) + len(right_source), 2)
    contexts = [
        _context(0, left_source, 0, 0),
        _context(1, right_source, len(left_source), 1),
        _context(2, third_source, len(left_source) + len(right_source), 2),
    ]
    return content, [left, right, third], contexts, nlp


def _group(nlp_rows: list[dict[str, object]]) -> dict[int, list[dict[str, object]]]:
    result: dict[int, list[dict[str, object]]] = {}
    for row in nlp_rows:
        payload = row["payload"]
        assert isinstance(payload, dict)
        index = int(payload["sentence_index"])
        result.setdefault(index, []).append(row)
    return result


def test_base_parameters_strip_only_boundary_pair_controls() -> None:
    parameters = {
        "enable_tc_big_short_angular_dms_rescue": True,
        "enable_tc_big_boundary_pair_punctuation_rescue": True,
        "tc_big_boundary_pair_punctuation_rescue_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_RESCUE_CONTRACT,
        "tc_big_boundary_pair_punctuation_selector_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_SELECTOR_CONTRACT,
        "tc_big_boundary_pair_punctuation_trigger_contract": TC_BIG_BOUNDARY_PAIR_PUNCTUATION_TRIGGER_CONTRACT,
    }
    assert _base_parameters(parameters) == {"enable_tc_big_short_angular_dms_rescue": True}


def test_trigger_requires_source_proven_punctuation_only_false_boundary() -> None:
    content, rows, contexts, nlp = _fixture_rows()
    trigger = evaluate_tc_big_boundary_pair_punctuation_trigger(
        content=content,
        left=rows[0],
        right=rows[1],
        left_context=contexts[0],
        right_context=contexts[1],
        stage8_grouped=_group(nlp),
    )
    assert trigger["eligible"] is True
    assert trigger["stage10_v2_boundary_proven"] is True
    assert trigger["punctuation_only_hard_family"] is True
    assert trigger["base_pair_failure_counts"] == {
        "numeric_symbol": 0,
        "punctuation": 1,
        "length": 0,
    }

    numeric_left = dict(rows[0])
    numeric_left["source_text"] = "And 16 whence is it "
    numeric_left["source_end"] = len(str(numeric_left["source_text"]))
    numeric_left["target_text"] = "И откуда это? "
    numeric_right = dict(rows[1])
    numeric_right["source_start"] = int(numeric_left["source_end"])
    numeric_right["source_end"] = int(numeric_right["source_start"]) + len(str(numeric_right["source_text"]))
    numeric_content, numeric_nlp = _nlp_rows([
        (str(numeric_left["source_text"]), 0),
        (str(numeric_right["source_text"]), 1),
    ])
    numeric_contexts = [
        _context(0, str(numeric_left["source_text"]), 0, 0),
        _context(1, str(numeric_right["source_text"]), int(numeric_right["source_start"]), 1),
    ]
    numeric_trigger = evaluate_tc_big_boundary_pair_punctuation_trigger(
        content=numeric_content,
        left=numeric_left,
        right=numeric_right,
        left_context=numeric_contexts[0],
        right_context=numeric_contexts[1],
        stage8_grouped=_group(numeric_nlp),
    )
    assert numeric_trigger["eligible"] is False
    assert numeric_trigger["base_pair_failure_counts"]["numeric_symbol"] == 1


def test_trigger_rejects_terminal_uppercase_and_long_boundaries() -> None:
    def build(left_source: str, right_source: str) -> dict[str, object]:
        content, nlp = _nlp_rows([(left_source, 0), (right_source, 1)])
        left = _row(1, 0, left_source, "Левая? ", 0, 0)
        right = _row(2, 1, right_source, "правая?", len(left_source), 1)
        contexts = [
            _context(0, left_source, 0, 0),
            _context(1, right_source, len(left_source), 1),
        ]
        return evaluate_tc_big_boundary_pair_punctuation_trigger(
            content=content,
            left=left,
            right=right,
            left_context=contexts[0],
            right_context=contexts[1],
            stage8_grouped=_group(nlp),
        )

    assert build("And whence is it. ", "but from water?")["stage10_v2_boundary_proven"] is False
    assert build("And whence is it ", "But from water?")["stage10_v2_boundary_proven"] is False
    long_left = " ".join(["word"] * 25) + " "
    long_right = "and " + " ".join(["word"] * 20) + "?"
    long_trigger = build(long_left, long_right)
    assert long_trigger["eligible"] is False
    assert long_trigger["source_complexity_passed"] is False


def test_candidate_requires_strict_clean_emphasis_preserving_raw_rank0() -> None:
    source = "And whence is it but from water?"
    accepted = evaluate_tc_big_boundary_pair_punctuation_candidate(
        source, "И откуда это, как не из воды?"
    )
    assert accepted["accepted"] is True
    assert accepted["strictly_eligible"] is True

    punctuation_bad = evaluate_tc_big_boundary_pair_punctuation_candidate(
        source, "И откуда это, как не из воды."
    )
    assert punctuation_bad["accepted"] is False

    emphasized = "And _whence_ is it but from water?"
    emphasis_bad = evaluate_tc_big_boundary_pair_punctuation_candidate(
        emphasized, "И откуда это, как не из воды?"
    )
    assert emphasis_bad["emphasis_markup"]["passed"] is False
    assert emphasis_bad["accepted"] is False


def test_eligible_pairs_excludes_clean_and_split_geometry() -> None:
    content, rows, contexts, nlp = _fixture_rows()
    assert len(_eligible_pairs(content=content, base_rows=rows, context_rows=contexts, nlp_rows=nlp)) == 1

    clean = [dict(row) for row in rows]
    clean[0]["target_text"] = "И откуда это "
    assert _eligible_pairs(content=content, base_rows=clean, context_rows=contexts, nlp_rows=nlp) == []

    split = [dict(row) for row in rows]
    split_payload = dict(split[0]["payload"])
    split_payload["planner"] = {**dict(split_payload["planner"]), "split": True}
    split[0]["payload"] = split_payload
    assert _eligible_pairs(content=content, base_rows=split, context_rows=contexts, nlp_rows=nlp) == []


def test_disabled_run_delegates_without_tc_big_probe(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    expected = {"translation_run_id": 16, "sentinel": "base"}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "tc_big_status",
        lambda: (_ for _ in ()).throw(
            AssertionError("TC-big must not be probed while boundary-pair rescue is disabled")
        ),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_tc_big_short_angular_dms_rescue": True,
            "enable_tc_big_boundary_pair_punctuation_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_tc_big_short_angular_dms_rescue": True}


def _mock_enabled_database(monkeypatch: pytest.MonkeyPatch, content, rows, contexts, nlp):  # type: ignore[no-untyped-def]
    base_output = {
        "translation_run_id": 16,
        "document_version_id": 7,
        "context_run_id": 2,
        "model_request_count": 300,
    }
    base_run = {
        "id": 16,
        "stage_number": 12,
        "status": "completed",
        "output": base_output,
        "output_sha256": "a" * 64,
    }
    context_run = {
        "id": 2,
        "stage_number": 10,
        "status": "completed",
        "implementation": "structural-entity-term-discourse-pronoun-v1",
        "output": {"nlp_run_id": 8, "document_version_id": 7},
        "output_sha256": "c" * 64,
    }
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}
    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(
        stage,
        "get_run",
        lambda connection, run_id: base_run if int(run_id) == 16 else context_run,
    )

    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 16 and kind == "translation_segment":
            return rows
        if int(run_id) == 2 and kind == "context_sentence":
            return contexts
        if int(run_id) == 8 and kind == "nlp_token":
            return nlp
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (17, None))
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    monkeypatch.setattr(stage, "tc_big_status", lambda: {"available": True})
    return base_output


def test_enabled_run_merges_only_accepted_pair_and_keeps_other_target_exact(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    content, rows, contexts, nlp = _fixture_rows()
    _mock_enabled_database(monkeypatch, content, rows, contexts, nlp)
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    raw_target = "И откуда это, как не из воды?"

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [str(rows[0]["source_text"]) + str(rows[1]["source_text"])]
            assert beam_size == 6 and num_hypotheses == 1 and max_decoding_length == 512
            return [[{"rank": 0, "text": raw_target, "score": -0.1}]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_boundary_pair_punctuation_rescue": True},
    )
    assert result["translation_run_id"] == 17
    assert result["base_translation_run_id"] == 16
    assert result["tc_big_boundary_pair_punctuation_rescue_attempt_count"] == 1
    assert result["tc_big_boundary_pair_punctuation_rescue_accepted_count"] == 1
    assert result["tc_big_boundary_pair_punctuation_rescue_selected_ranks"] == [0]
    assert result["segment_count"] == 2

    items = completed["items"]
    assert isinstance(items, list) and len(items) == 2
    merged, untouched = items
    assert merged["source_text"] == str(rows[0]["source_text"]) + str(rows[1]["source_text"])
    assert merged["target_text"] == raw_target
    rescue = merged["payload"]["tc_big_boundary_pair_punctuation_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["base_translation_segment_ids"] == [11, 12]
    assert merged["payload"]["planner"]["context_sentence_count"] == 2
    assert untouched["target_text"] == rows[2]["target_text"]
    assert "".join(str(item["source_text"]) for item in items) == content


def test_enabled_run_rejects_rank0_without_target_surgery(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    content, rows, contexts, nlp = _fixture_rows()
    _mock_enabled_database(monkeypatch, content, rows, contexts, nlp)
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)

    class FakeTranslator:
        def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

        def translate(self, texts, **kwargs):  # type: ignore[no-untyped-def]
            return [[{"rank": 0, "text": "И откуда это, как не из воды.", "score": -0.1}]]

    monkeypatch.setattr(stage, "TcBigTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_tc_big_boundary_pair_punctuation_rescue": True},
    )
    assert result["tc_big_boundary_pair_punctuation_rescue_accepted_count"] == 0
    assert result["tc_big_boundary_pair_punctuation_rescue_rejected_count"] == 1
    items = completed["items"]
    assert [item["target_text"] for item in items] == [row["target_text"] for row in rows]
    assert [item["source_text"] for item in items] == [row["source_text"] for row in rows]
