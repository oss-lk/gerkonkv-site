from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import rocketdict.translation_dense_figure_group_rescue_stage as stage
from rocketdict.translation_dense_figure_group_rescue_stage import (
    DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
    DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
    DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
    MAX_GROUP_NLP_TOKENS,
    _base_parameters,
    evaluate_dense_figure_group_candidate,
    evaluate_dense_figure_group_trigger,
)


def _planner() -> dict[str, object]:
    return {
        "source": "nlp_sentence_group",
        "context_sentence_start": 10,
        "context_sentence_end": 11,
        "context_sentence_count": 2,
        "protected_sentence_boundary_coalesced": True,
        "protected_span_count": 1,
        "split": True,
        "token_count": 20,
        "planner_contract": "rocketdict-stage12-protected-split/8",
    }


def _context(sequence: int, source: str, *, start: int, token_count: int) -> dict[str, object]:
    return {
        "id": 100 + sequence,
        "sequence_number": sequence,
        "kind": "context_sentence",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": "",
        "payload": {"sentence_index": sequence, "token_count": token_count},
    }


def _row(
    row_id: int,
    source: str,
    target: str,
    *,
    start: int,
) -> dict[str, object]:
    return {
        "id": row_id,
        "sequence_number": row_id - 1,
        "kind": "translation_segment",
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {"planner": _planner(), "hypotheses": []},
    }


def _fixture() -> tuple[str, list[dict[str, object]], list[dict[str, object]]]:
    first_context = "[Illustration: FIG. 2.]\n\n"
    second_context = (
        "Let A1 A2 B3 4C 5D 6E 7F 8G 9H 10I and 11J mark the rays; "
        "the light returns through A1 and 4C."
    )
    content = first_context + second_context
    cut1 = len(first_context) + 30
    cut2 = len(first_context) + 67
    parts = [content[:cut1], content[cut1:cut2], content[cut2:]]
    targets = [
        parts[0].replace("[Illustration:", "[Иллюстрация:"),
        parts[1].replace("7F 8G", "7F"),
        parts[2],
    ]
    rows: list[dict[str, object]] = []
    cursor = 0
    for row_id, (source, target) in enumerate(zip(parts, targets, strict=True), start=1):
        rows.append(_row(row_id, source, target, start=cursor))
        cursor += len(source)
    contexts = [
        _context(10, first_context, start=0, token_count=5),
        _context(11, second_context, start=len(first_context), token_count=60),
    ]
    return content, contexts, rows


def test_base_parameters_strip_only_dense_figure_controls() -> None:
    parameters = {
        "enable_parenthetical_whole_context_rescue": True,
        "enable_dense_figure_label_group_rescue": True,
        "dense_figure_label_group_rescue_contract": DENSE_FIGURE_GROUP_RESCUE_CONTRACT,
        "dense_figure_label_group_selector_contract": DENSE_FIGURE_GROUP_SELECTOR_CONTRACT,
        "dense_figure_label_group_trigger_contract": DENSE_FIGURE_GROUP_TRIGGER_CONTRACT,
        "dense_figure_label_group_max_nlp_tokens": MAX_GROUP_NLP_TOKENS,
    }
    assert _base_parameters(parameters) == {"enable_parenthetical_whole_context_rescue": True}


def test_trigger_accepts_dense_cross_context_missing_only_group() -> None:
    content, contexts, rows = _fixture()
    trigger = evaluate_dense_figure_group_trigger(
        content=content,
        context_by_sequence={int(row["sequence_number"]): row for row in contexts},
        primary_rows=rows,
    )
    assert trigger["eligible"] is True
    assert trigger["planner_group"] == [10, 11]
    assert trigger["group_nlp_token_count"] == 65
    assert trigger["technical_label_occurrences"] >= 10
    assert trigger["technical_label_distinct_count"] >= 8
    assert trigger["single_source_illustration_marker"] is True
    assert trigger["exactly_one_missing_only_numeric_failure"] is True


def test_trigger_rejects_sparse_and_over_cap() -> None:
    content, contexts, rows = _fixture()
    sparse_content = content.replace(" A2 B3 4C 5D 6E 7F 8G 9H 10I and 11J", "")
    first_context = "[Illustration: FIG. 2.]\n\n"
    sparse_contexts = [
        _context(10, first_context, start=0, token_count=5),
        _context(11, sparse_content[len(first_context):], start=len(first_context), token_count=20),
    ]
    cut = len(sparse_content) // 2
    sparse_rows = [
        _row(1, sparse_content[:cut], sparse_content[:cut], start=0),
        _row(2, sparse_content[cut:], sparse_content[cut:].replace("4C", ""), start=cut),
    ]
    assert evaluate_dense_figure_group_trigger(
        content=sparse_content,
        context_by_sequence={int(row["sequence_number"]): row for row in sparse_contexts},
        primary_rows=sparse_rows,
    )["eligible"] is False

    over = [dict(contexts[0]), {**contexts[1], "payload": {"sentence_index": 11, "token_count": 188}}]
    assert evaluate_dense_figure_group_trigger(
        content=content,
        context_by_sequence={int(row["sequence_number"]): row for row in over},
        primary_rows=rows,
    )["eligible"] is False


def test_candidate_requires_exact_label_sequence_illustration_and_content_volume() -> None:
    content, _contexts, rows = _fixture()
    primary = "".join(str(row["target_text"]) for row in rows)
    good = content.replace("[Illustration:", "[Иллюстрация:")
    selection = evaluate_dense_figure_group_candidate(content, good, primary_target=primary)
    assert selection["accepted"] is True
    assert selection["technical_label_sequence_exact"] is True
    assert selection["illustration_payload_exact"] is True
    assert selection["target_alpha_non_decreasing"] is True

    reordered = good.replace("8G 9H", "9H 8G")
    bad_order = evaluate_dense_figure_group_candidate(content, reordered, primary_target=primary)
    assert bad_order["technical_label_sequence_exact"] is False
    assert bad_order["accepted"] is False

    no_marker = good.replace("[Иллюстрация: FIG. 2.]", "FIG. 2.")
    bad_marker = evaluate_dense_figure_group_candidate(content, no_marker, primary_target=primary)
    assert bad_marker["illustration_payload_exact"] is False
    assert bad_marker["accepted"] is False


def test_disabled_run_delegates_without_opus_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    expected = {"translation_run_id": 20}
    observed: dict[str, object] = {}

    def fake_base(database, *, context_run_id, parameters, implementation):  # type: ignore[no-untyped-def]
        observed["parameters"] = parameters
        return expected

    monkeypatch.setattr(stage, "run_base_stage12", fake_base)
    monkeypatch.setattr(
        stage,
        "OpusTranslator",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("OPUS must not be constructed")),
    )
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={
            "enable_parenthetical_whole_context_rescue": True,
            "enable_dense_figure_label_group_rescue": False,
        },
    )
    assert result is expected
    assert observed["parameters"] == {"enable_parenthetical_whole_context_rescue": True}


def test_enabled_run_merges_only_source_defined_dense_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    content, contexts, rows = _fixture()
    base_output = {
        "translation_run_id": 20,
        "document_version_id": 7,
        "model_request_count": 600,
    }
    base_run = {"id": 20, "output": base_output, "output_sha256": "a" * 64}
    document = {"id": 7, "content_text": content, "text_sha256": "b" * 64}

    monkeypatch.setattr(stage, "run_base_stage12", lambda *args, **kwargs: dict(base_output))
    monkeypatch.setattr(stage, "connect", lambda *args, **kwargs: nullcontext(SimpleNamespace()))
    monkeypatch.setattr(stage, "get_run", lambda connection, run_id: base_run)

    def fake_items(connection, run_id, *, kind):  # type: ignore[no-untyped-def]
        if int(run_id) == 20 and kind == "translation_segment":
            return rows
        if int(run_id) == 2 and kind == "context_sentence":
            return contexts
        raise AssertionError((run_id, kind))

    monkeypatch.setattr(stage, "get_run_items", fake_items)
    monkeypatch.setattr(stage, "get_document", lambda connection, document_version_id: document)
    monkeypatch.setattr(stage, "_start", lambda *args, **kwargs: (21, None))
    completed: dict[str, object] = {}

    def fake_complete(database, run_id, output, *, items):  # type: ignore[no-untyped-def]
        completed["items"] = items
        return output

    monkeypatch.setattr(stage, "_complete", fake_complete)
    monkeypatch.setattr(stage, "_fail", lambda *args, **kwargs: None)
    raw_target = content.replace("[Illustration:", "[Иллюстрация:")

    class FakeTranslator:
        def __init__(self, *, device: str, compute_type: str) -> None:
            assert device == "cpu" and compute_type == "float32"

        def translate(self, texts, *, beam_size, num_hypotheses, max_decoding_length):  # type: ignore[no-untyped-def]
            assert texts == [content]
            assert beam_size == 6 and num_hypotheses == 1
            return [[{"rank": 0, "text": raw_target, "score": -0.1}]]

    monkeypatch.setattr(stage, "OpusTranslator", FakeTranslator)
    result = stage.run_stage12(
        tmp_path / "rocketdict.sqlite",
        context_run_id=2,
        parameters={"enable_dense_figure_label_group_rescue": True},
    )
    assert result["translation_run_id"] == 21
    assert result["base_translation_run_id"] == 20
    assert result["dense_figure_label_group_rescue_attempt_count"] == 1
    assert result["dense_figure_label_group_rescue_accepted_count"] == 1
    assert result["dense_figure_label_group_rescue_accepted_groups"] == [[10, 11]]
    assert result["dense_figure_label_group_rescue_selected_ranks"] == [0]
    items = completed["items"]
    assert isinstance(items, list) and len(items) == 1
    rescue = items[0]["payload"]["dense_figure_label_group_rescue"]
    assert rescue["raw_model_selected"] is True
    assert rescue["raw_model_rank"] == 0
    assert rescue["base_translation_segment_ids"] == [1, 2, 3]
    assert items[0]["source_text"] == content
    assert items[0]["target_text"] == raw_target
