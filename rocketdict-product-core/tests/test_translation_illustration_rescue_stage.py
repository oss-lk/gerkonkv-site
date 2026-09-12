from __future__ import annotations

from rocketdict.translation_illustration_rescue_stage import (
    ILLUSTRATION_LABEL_RESCUE_CONTRACT,
    ILLUSTRATION_LABEL_SELECTED_PHASE,
    ILLUSTRATION_LABEL_SELECTOR_CONTRACT,
    ILLUSTRATION_WORD_MODEL_INPUT,
    ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
    _base_parameters,
    _candidate_rows,
    _model_input_for_remainder,
    evaluate_illustration_label_candidate,
    evaluate_illustration_label_trigger,
    evaluate_illustration_word_target_shape,
)


def _failing_row() -> dict[str, object]:
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
        "illustration_word_target_form_contract": ILLUSTRATION_WORD_TARGET_FORM_CONTRACT,
        "illustration_label_rescue_phase": ILLUSTRATION_LABEL_SELECTED_PHASE,
    }
    assert _base_parameters(parameters) == {
        "planner_contract": "rocketdict-stage12-protected-split/8",
        "beam_size": 6,
        "enable_length_failure_whole_context_rescue": True,
        "enable_citation_boundary_pair_rescue": True,
        "enable_numeric_hard_failure_whole_context_rescue": True,
    }


def test_trigger_is_exact_standalone_prefix_plus_existing_hard_failure() -> None:
    trigger = evaluate_illustration_label_trigger(_failing_row())
    assert trigger["eligible"] is True
    assert trigger["standalone_illustration_prefix"] is True
    assert trigger["already_product_hard_failing"] is True
    assert trigger["structural_source"] == "[Illustration: FIG. 21.]\n\n"
    assert trigger["remainder_source"] == "_Illustration._ "


def test_trigger_rejects_inline_or_missing_blankline_or_clean_row() -> None:
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
    assert clean_trigger["standalone_illustration_prefix"] is True
    assert clean_trigger["already_product_hard_failing"] is False
    assert clean_trigger["eligible"] is False


def test_exact_illustration_word_uses_canonical_model_input_only() -> None:
    assert _model_input_for_remainder("_Illustration._ ") == (
        ILLUSTRATION_WORD_MODEL_INPUT,
        True,
        "standalone_illustration_word",
    )
    assert _model_input_for_remainder("With the Center O ") == (
        "With the Center O ",
        False,
        "ordinary_linguistic_suffix",
    )


def test_structural_word_target_shape_rejects_wrong_sense_and_markup_corruption() -> None:
    assert evaluate_illustration_word_target_shape("Пример.")["passed"] is False
    assert evaluate_illustration_word_target_shape("*Иллюстрация._")["passed"] is False
    assert evaluate_illustration_word_target_shape("Иллюстрация.")["passed"] is True
    assert evaluate_illustration_word_target_shape("Рисунок.")["passed"] is True


def test_selector_matches_v3_raw_nbest_acceptance_boundary() -> None:
    row = _failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    structural = str(trigger["structural_source"])
    remainder = str(trigger["remainder_source"])
    raw_targets = ["Пример.", "Примеры.", "Образец.", "Иллюстрация.", "Рисунок.", "Пример"]
    accepted = []
    for rank, target in enumerate(raw_targets):
        selection = evaluate_illustration_label_candidate(
            row,
            structural_source=structural,
            remainder_source=remainder,
            target=target,
            normalized_model_input=True,
        )
        if selection["accepted"]:
            accepted.append((rank, target))
    assert accepted == [(3, "Иллюстрация."), (4, "Рисунок.")]
    assert accepted[0] == (3, "Иллюстрация.")


def test_ordinary_suffix_raw_rank0_is_eligible_without_structural_word_shape() -> None:
    source = "[Illustration: FIG. 11.]\n\nWith the Center O "
    row = {
        "id": 11,
        "source_start": 203786,
        "source_end": 203786 + len(source),
        "source_text": source,
        "target_text": "С Центром О.",
        "payload": {"planner": {"source": "nlp_sentence"}},
    }
    trigger = evaluate_illustration_label_trigger(row)
    selection = evaluate_illustration_label_candidate(
        row,
        structural_source=str(trigger["structural_source"]),
        remainder_source=str(trigger["remainder_source"]),
        target="С центром O",
        normalized_model_input=False,
    )
    assert selection["accepted"] is True
    assert selection["illustration_word_target_shape"]["applicable"] is False


def test_candidate_rows_preserve_source_bytes_raw_rank_and_provenance() -> None:
    row = _failing_row()
    trigger = evaluate_illustration_label_trigger(row)
    structural = str(trigger["structural_source"])
    remainder = str(trigger["remainder_source"])
    hypotheses = [
        {"rank": 0, "text": "Иллюстрация.", "score": -0.1},
        {"text": "Примеры.", "score": -0.2},
        {"text": "Образец.", "score": -0.3},
        {"text": "Иллюстрация.", "score": -0.4},
        {"text": "Рисунок.", "score": -0.5},
        {"text": "Пример", "score": -0.6},
    ]
    selection = evaluate_illustration_label_candidate(
        row,
        structural_source=structural,
        remainder_source=remainder,
        target="Иллюстрация.",
        normalized_model_input=True,
    )
    rows = _candidate_rows(
        base=row,
        structural_source=structural,
        remainder_source=remainder,
        model_input=ILLUSTRATION_WORD_MODEL_INPUT,
        normalized_model_input=True,
        candidate_kind="standalone_illustration_word",
        hypotheses=hypotheses,
        selected_rank=0,
        trigger=trigger,
        selection=selection,
        generation={"beam_size": 6, "num_hypotheses": 6},
    )
    assert len(rows) == 2
    assert rows[0]["source_text"] + rows[1]["source_text"] == row["source_text"]
    assert rows[0]["target_text"] == rows[0]["source_text"]
    assert rows[1]["target_text"] == "Иллюстрация."
    assert rows[1]["payload"]["selected_rank"] == 0
    rescue = rows[1]["payload"]["illustration_label_rescue"]
    assert rescue["contract"] == ILLUSTRATION_LABEL_RESCUE_CONTRACT
    assert rescue["selector_contract"] == ILLUSTRATION_LABEL_SELECTOR_CONTRACT
    assert rescue["target_form_contract"] == ILLUSTRATION_WORD_TARGET_FORM_CONTRACT
    assert rescue["raw_model_selected"] is True
    assert rescue["source_model_input_normalized"] is True
    assert rescue["model_input"] == ILLUSTRATION_WORD_MODEL_INPUT
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert rescue["placeholders"] is False
    assert rescue["post_translation_literal_injection"] is False
