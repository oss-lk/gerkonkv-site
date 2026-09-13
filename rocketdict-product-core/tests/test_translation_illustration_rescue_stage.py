from __future__ import annotations

import pytest

from rocketdict.stages import StageExecutionError
from rocketdict.translation_illustration_rescue_stage import (
    DEFAULT_ENABLED,
    ILLUSTRATION_LABEL_RESCUE_CONTRACT,
    ILLUSTRATION_LABEL_SELECTED_PHASE,
    ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
    ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
    ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
    ILLUSTRATION_SOURCE_PLAN_CONTRACT,
    ILLUSTRATION_WORD_MODEL_INPUT,
    ILLUSTRATION_WORD_SOURCE,
    ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
    _base_parameters,
    _candidate_rows,
    _model_input_for_remainder,
    _structural_candidate_rows,
    _structural_word_plan,
    _unique_rank0,
    evaluate_illustration_label_candidate,
    evaluate_illustration_label_target_shape,
    evaluate_illustration_label_trigger,
    evaluate_illustration_word_target_shape,
    evaluate_structural_separator_candidate,
)


def _structural_failing_row() -> dict[str, object]:
    source = "[Illustration: FIG. 21.]\n\n_Illustration._ "
    return {
        "id": 21,
        "source_start": 72401,
        "source_end": 72401 + len(source),
        "source_text": source,
        "target_text": "[Иллюстрация: FIG. 21.] [Иллюстрация.]",
        "payload": {
            "planner": {
                "source": "nlp_sentence",
                "planner_contract": "rocketdict-stage12-protected-split/8",
                "split": False,
            }
        },
    }


def _ordinary_failing_row() -> dict[str, object]:
    source = "[Illustration: FIG. 11.]\n\nWith the Center O "
    return {
        "id": 11,
        "source_start": 203786,
        "source_end": 203786 + len(source),
        "source_text": source,
        "target_text": "С Центром O.",
        "payload": {"planner": {"source": "nlp_sentence"}},
    }


def test_wrapper_is_default_off_and_contracts_are_versioned() -> None:
    assert DEFAULT_ENABLED is False
    assert ILLUSTRATION_LABEL_RESCUE_CONTRACT.endswith("/5")
    assert ILLUSTRATION_LABEL_SELECTOR_CONTRACT.endswith("/4")
    assert ILLUSTRATION_LABEL_TRIGGER_CONTRACT.endswith("/2")
    assert ILLUSTRATION_SOURCE_PLAN_CONTRACT.endswith("/1")
    assert ILLUSTRATION_WORD_TARGET_FORM_CONTRACT.endswith("/2")
    assert ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT.endswith("/1")
    assert ILLUSTRATION_LABEL_SELECTED_PHASE == "illustration-label-selected-v5"


def test_base_parameters_strip_only_illustration_wrapper_controls() -> None:
    parameters = {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "enable_length_failure_whole_context_rescue": True,
        "enable_citation_boundary_pair_rescue": True,
        "enable_numeric_hard_failure_whole_context_rescue": True,
        "enable_illustration_label_rescue": True,
        "illustration_label_rescue_contract": ILLUSTRATION_LABEL_RESCUE_CONTRACT,
        "illustration_label_rescue_selector_contract": ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
        "illustration_label_trigger_contract": ILLUSTRATION_LABEL_TRIGGER_CONTRACT,
        "illustration_source_plan_contract": ILLUSTRATION_SOURCE_PLAN_CONTRACT,
        "illustration_word_target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "illustration_label_target_form_contract": ILLUSTRATION_LABEL_TARGET_FORM_CONTRACT,
        "illustration_label_rescue_phase": ILLUSTRATION_LABEL_SELECTED_PHASE,
    }
    assert _base_parameters(parameters) == {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "enable_length_failure_whole_context_rescue": True,
        "enable_citation_boundary_pair_rescue": True,
        "enable_numeric_hard_failure_whole_context_rescue": True,
    }


def test_structural_plan_is_complete_source_owned_and_generic() -> None:
    source = "[Illustration: FIG. 123.]\r\n \t\r\n_Illustration._  "
    plan = _structural_word_plan(source)
    assert plan is not None
    assert plan["contract"] == ILLUSTRATION_SOURCE_PLAN_CONTRACT
    assert plan["figure_number"] == "123"
    assert plan["label_source"] == "[Illustration: FIG. 123.]"
    assert plan["separator_source"] == "\r\n \t\r\n"
    assert plan["suffix_source"] == ILLUSTRATION_WORD_SOURCE
    assert plan["trailing_source"] == "  "
    assert (
        plan["label_source"]
        + plan["separator_source"]
        + plan["suffix_source"]
        + plan["trailing_source"]
        == source
    )
    assert plan["source_plan_created_before_mt"] is True
    assert plan["source_owned_structural_passthrough"] is True


def test_trigger_selects_source_planned_structural_path_for_proven_shape() -> None:
    trigger = evaluate_illustration_label_trigger(_structural_failing_row())
    assert trigger["eligible"] is True
    assert trigger["candidate_kind"] == "source_planned_structural_illustration"
    assert trigger["source_planned_structural_illustration"] is True
    assert trigger["ordinary_linguistic_suffix"] is False
    plan = trigger["source_plan"]
    assert plan["label_source"] == "[Illustration: FIG. 21.]"
    assert plan["separator_source"] == "\n\n"
    assert plan["suffix_source"] == "_Illustration._"
    assert plan["trailing_source"] == " "


def test_trigger_preserves_run41_ordinary_suffix_path() -> None:
    trigger = evaluate_illustration_label_trigger(_ordinary_failing_row())
    assert trigger["eligible"] is True
    assert trigger["candidate_kind"] == "ordinary_linguistic_suffix"
    assert trigger["source_planned_structural_illustration"] is False
    assert trigger["ordinary_linguistic_suffix"] is True
    assert trigger["structural_source"] == "[Illustration: FIG. 11.]\n\n"
    assert trigger["remainder_source"] == "With the Center O "


def test_trigger_fails_closed_for_unproven_standalone_word_geometry() -> None:
    source = "[Illustration: A prism.]\n\n_Illustration._ "
    row = {
        "source_text": source,
        "target_text": "Иллюстрация",
    }
    trigger = evaluate_illustration_label_trigger(row)
    assert trigger["standalone_illustration_prefix"] is True
    assert trigger["source_planned_structural_illustration"] is False
    assert trigger["ordinary_linguistic_suffix"] is False
    assert trigger["eligible"] is False


def test_trigger_rejects_inline_missing_blankline_and_clean_row() -> None:
    inline = {
        "source_text": "See [Illustration: FIG. 21.] in the text.",
        "target_text": "См. [Illustration: FIG. 21.] в тексте.",
    }
    assert evaluate_illustration_label_trigger(inline)["eligible"] is False

    no_blank = {
        "source_text": "[Illustration: FIG. 21.]\n_Illustration._ ",
        "target_text": "[Иллюстрация: FIG. 21.] Иллюстрация.",
    }
    assert evaluate_illustration_label_trigger(no_blank)["eligible"] is False

    clean_source = "[Illustration: FIG. 21.]\n\n_Illustration._ "
    clean = {"source_text": clean_source, "target_text": clean_source}
    clean_trigger = evaluate_illustration_label_trigger(clean)
    assert clean_trigger["source_planned_structural_illustration"] is True
    assert clean_trigger["already_product_hard_failing"] is False
    assert clean_trigger["eligible"] is False


def test_exact_ordinary_remainder_model_input_is_never_rewritten() -> None:
    assert ILLUSTRATION_WORD_MODEL_INPUT == ILLUSTRATION_WORD_SOURCE
    assert _model_input_for_remainder("With the Center O ") == (
        "With the Center O ",
        False,
        "ordinary_linguistic_suffix",
    )


def test_structural_suffix_target_shape_requires_source_emphasis() -> None:
    accepted = evaluate_illustration_word_target_shape(
        "_Иллюстрация._", require_emphasis=True
    )
    assert accepted["passed"] is True
    assert accepted["emphasis_wrapped"] is True
    assert accepted["canonical_target"] == "иллюстрация"

    assert evaluate_illustration_word_target_shape(
        "Иллюстрация.", require_emphasis=True
    )["passed"] is False
    assert evaluate_illustration_word_target_shape(
        "_Пример._", require_emphasis=True
    )["passed"] is False
    assert evaluate_illustration_word_target_shape(
        "_[Иллюстрация]._", require_emphasis=True
    )["passed"] is False


def test_structural_label_target_shape_preserves_semantics_number_and_delimiters() -> None:
    source = "[Illustration: FIG. 21.]"
    good = evaluate_illustration_label_target_shape(
        source, "[Иллюстрация: FIG. 21.]"
    )
    assert good["passed"] is True
    assert good["same_figure_number"] is True
    assert good["semantic_term"] == "иллюстрация"
    assert evaluate_illustration_label_target_shape(
        source, "Иллюстрация: FIG. 21."
    )["passed"] is False
    assert evaluate_illustration_label_target_shape(
        source, "[Иллюстрация: FIG. 22.]"
    )["passed"] is False
    assert evaluate_illustration_label_target_shape(
        source, "[Пример: FIG. 21.]"
    )["passed"] is False


def test_ordinary_suffix_candidate_remains_eligible_without_word_shape() -> None:
    row = _ordinary_failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    selection = evaluate_illustration_label_candidate(
        row,
        structural_source=str(trigger["structural_source"]),
        remainder_source=str(trigger["remainder_source"]),
        target="С центром O",
        normalized_model_input=False,
    )
    assert selection["accepted"] is True
    assert selection["candidate_kind"] == "ordinary_linguistic_suffix"
    assert selection["illustration_word_target_shape"]["applicable"] is False


def test_structural_candidate_accepts_only_the_doe_rank0_geometry() -> None:
    row = _structural_failing_row()
    plan = _structural_word_plan(str(row["source_text"]))
    assert plan is not None
    selection = evaluate_structural_separator_candidate(
        row,
        label_source=str(plan["label_source"]),
        separator_source=str(plan["separator_source"]),
        suffix_source=str(plan["suffix_source"]),
        trailing_source=str(plan["trailing_source"]),
        label_target="[Иллюстрация: FIG. 21.]",
        suffix_target="_Иллюстрация._",
    )
    assert selection["accepted"] is True
    assert selection["aggregate_target"] == (
        "[Иллюстрация: FIG. 21.]\n\n_Иллюстрация._ "
    )
    assert selection["aggregate_verdict"]["strictly_eligible"] is True
    assert selection["aggregate_emphasis_markup"]["passed"] is True
    assert selection["exact_source_separator_preserved"] is True
    assert selection["exact_trailing_source_preserved"] is True


def test_structural_candidate_rejects_semantic_or_identity_drift() -> None:
    row = _structural_failing_row()
    plan = _structural_word_plan(str(row["source_text"]))
    assert plan is not None
    wrong_number = evaluate_structural_separator_candidate(
        row,
        label_source=str(plan["label_source"]),
        separator_source=str(plan["separator_source"]),
        suffix_source=str(plan["suffix_source"]),
        trailing_source=str(plan["trailing_source"]),
        label_target="[Иллюстрация: FIG. 22.]",
        suffix_target="_Иллюстрация._",
    )
    assert wrong_number["accepted"] is False
    wrong_semantics = evaluate_structural_separator_candidate(
        row,
        label_source=str(plan["label_source"]),
        separator_source=str(plan["separator_source"]),
        suffix_source=str(plan["suffix_source"]),
        trailing_source=str(plan["trailing_source"]),
        label_target="[Иллюстрация: FIG. 21.]",
        suffix_target="_Пример._",
    )
    assert wrong_semantics["accepted"] is False


def test_ordinary_candidate_rows_preserve_run41_exact_source_provenance() -> None:
    row = _ordinary_failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    structural = str(trigger["structural_source"])
    remainder = str(trigger["remainder_source"])
    hypotheses = [{"rank": 0, "text": "С центром O", "score": -0.1}]
    selection = evaluate_illustration_label_candidate(
        row,
        structural_source=structural,
        remainder_source=remainder,
        target="С центром O",
        normalized_model_input=False,
    )
    rows = _candidate_rows(
        base=row,
        structural_source=structural,
        remainder_source=remainder,
        model_input=remainder,
        normalized_model_input=False,
        candidate_kind="ordinary_linguistic_suffix",
        hypotheses=hypotheses,
        selected_rank=0,
        trigger=trigger,
        selection=selection,
        generation={"beam_size": 6, "num_hypotheses": 1},
    )
    assert len(rows) == 2
    assert "".join(r["source_text"] for r in rows) == row["source_text"]
    assert rows[0]["target_text"] == rows[0]["source_text"]
    assert rows[1]["target_text"] == "С центром O"
    rescue = rows[1]["payload"]["illustration_label_rescue"]
    assert rescue["model"] == "opus"
    assert rescue["model_input"] == remainder
    assert rescue["model_input_source_exact"] is True
    assert rescue["source_model_input_normalized"] is False
    assert rescue["selected_rank"] == 0
    assert rescue["raw_rank0_only"] is True
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert rescue["post_translation_literal_injection"] is False


def test_structural_candidate_rows_persist_one_semantic_carrier() -> None:
    row = _structural_failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    plan = dict(trigger["source_plan"])
    label_hypotheses = [
        {"rank": 0, "text": "[Иллюстрация: FIG. 21.]", "score": -0.1}
    ]
    suffix_hypotheses = [
        {"rank": 0, "text": "_Иллюстрация._", "score": -0.2}
    ]
    selection = evaluate_structural_separator_candidate(
        row,
        label_source=str(plan["label_source"]),
        separator_source=str(plan["separator_source"]),
        suffix_source=str(plan["suffix_source"]),
        trailing_source=str(plan["trailing_source"]),
        label_target=str(label_hypotheses[0]["text"]),
        suffix_target=str(suffix_hypotheses[0]["text"]),
    )
    rows = _structural_candidate_rows(
        base=row,
        plan=plan,
        label_model_input=str(plan["label_source"]),
        suffix_model_input=str(plan["suffix_source"]),
        label_hypotheses=label_hypotheses,
        suffix_hypotheses=suffix_hypotheses,
        label_selected_rank=0,
        suffix_selected_rank=0,
        trigger=trigger,
        selection=selection,
    )
    assert len(rows) == 1
    carrier = rows[0]
    assert carrier["source_start"] == row["source_start"]
    assert carrier["source_end"] == row["source_end"]
    assert carrier["source_text"] == row["source_text"]
    assert carrier["target_text"] == selection["aggregate_target"]
    assert selection["aggregate_verdict"]["strictly_eligible"] is True

    rescue = carrier["payload"]["illustration_label_rescue"]
    assert rescue["role"] == "semantic_carrier"
    assert rescue["rendering"] == "source_planned_semantic_carrier"
    assert rescue["source_owned_passthrough"] is False
    assert rescue["source_owned_structural_passthrough"] is True
    assert rescue["raw_model_selected"] is False
    assert rescue["component_raw_model_selected"] is True
    assert rescue["raw_rank0_only"] is True
    assert rescue["rendered_target"] == carrier["target_text"]
    assert rescue["source_plan_contract"] == ILLUSTRATION_SOURCE_PLAN_CONTRACT
    assert rescue["source_plan_created_before_mt"] is True
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["model_input_source_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert rescue["post_translation_literal_injection"] is False
    assert rescue["automatic_n_best_cherry_picking"] is False

    pieces = rescue["source_plan"]["pieces"]
    assert [piece["role"] for piece in pieces] == [
        "label", "separator", "suffix", "trailing"
    ]
    assert "".join(piece["source_text"] for piece in pieces) == row["source_text"]
    assert pieces[0]["model"] == "opus"
    assert pieces[0]["model_input"] == pieces[0]["source_text"]
    assert pieces[0]["model_input_source_exact"] is True
    assert pieces[0]["selected_rank"] == 0
    assert pieces[0]["selected_target"] == "[Иллюстрация: FIG. 21.]"
    assert pieces[1]["source_owned"] is True
    assert pieces[1]["rendered_text"] == pieces[1]["source_text"] == "\n\n"
    assert pieces[2]["model"] == "tc_big"
    assert pieces[2]["model_input"] == pieces[2]["source_text"]
    assert pieces[2]["model_input_source_exact"] is True
    assert pieces[2]["selected_rank"] == 0
    assert pieces[2]["selected_target"] == "_Иллюстрация._"
    assert pieces[3]["source_owned"] is True
    assert pieces[3]["rendered_text"] == pieces[3]["source_text"] == " "
    rendered = (
        pieces[0]["selected_target"]
        + pieces[1]["rendered_text"]
        + pieces[2]["selected_target"]
        + pieces[3]["rendered_text"]
    )
    assert rendered == carrier["target_text"]


def test_structural_rows_reject_any_non_exact_model_input() -> None:
    row = _structural_failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    plan = dict(trigger["source_plan"])
    label_hypotheses = [
        {"rank": 0, "text": "[Иллюстрация: FIG. 21.]", "score": -0.1}
    ]
    suffix_hypotheses = [
        {"rank": 0, "text": "_Иллюстрация._", "score": -0.2}
    ]
    selection = evaluate_structural_separator_candidate(
        row,
        label_source=str(plan["label_source"]),
        separator_source=str(plan["separator_source"]),
        suffix_source=str(plan["suffix_source"]),
        trailing_source=str(plan["trailing_source"]),
        label_target=str(label_hypotheses[0]["text"]),
        suffix_target=str(suffix_hypotheses[0]["text"]),
    )
    with pytest.raises(ValueError, match="model input must equal exact source piece"):
        _structural_candidate_rows(
            base=row,
            plan=plan,
            label_model_input="Illustration: FIG. 21.",
            suffix_model_input=str(plan["suffix_source"]),
            label_hypotheses=label_hypotheses,
            suffix_hypotheses=suffix_hypotheses,
            label_selected_rank=0,
            suffix_selected_rank=0,
            trigger=trigger,
            selection=selection,
        )


def test_structural_rows_reject_non_rank0_selection() -> None:
    row = _structural_failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    plan = dict(trigger["source_plan"])
    with pytest.raises(ValueError, match="rank0-only"):
        _structural_candidate_rows(
            base=row,
            plan=plan,
            label_model_input=str(plan["label_source"]),
            suffix_model_input=str(plan["suffix_source"]),
            label_hypotheses=[
                {"rank": 0, "text": "[Иллюстрация: FIG. 21.]", "score": -0.1}
            ],
            suffix_hypotheses=[
                {"rank": 0, "text": "_Иллюстрация._", "score": -0.2}
            ],
            label_selected_rank=1,
            suffix_selected_rank=0,
            trigger=trigger,
            selection={"accepted": True},
        )


def test_unique_rank0_fails_closed_on_missing_duplicate_or_empty() -> None:
    with pytest.raises(StageExecutionError, match="cardinality drift"):
        _unique_rank0([], label="x")
    with pytest.raises(StageExecutionError, match="cardinality drift"):
        _unique_rank0(
            [
                {"rank": 0, "text": "a"},
                {"rank": 0, "text": "b"},
            ],
            label="x",
        )
    with pytest.raises(StageExecutionError, match="target is empty"):
        _unique_rank0([{"rank": 0, "text": "  "}], label="x")


def test_ordinary_candidate_rejects_normalized_model_input_flag() -> None:
    row = _ordinary_failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    with pytest.raises(ValueError, match="forbids normalized model input"):
        evaluate_illustration_label_candidate(
            row,
            structural_source=str(trigger["structural_source"]),
            remainder_source=str(trigger["remainder_source"]),
            target="С центром O",
            normalized_model_input=True,
        )
