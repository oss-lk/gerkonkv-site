from __future__ import annotations

import rocketdict.translation_dense_figure_group_rescue_stage as dense_stage
import rocketdict.translation_tc_big_fraction_context_rescue_stage as fraction_stage


def test_fraction_wrapper_composes_over_dense_figure_wrapper() -> None:
    assert fraction_stage.run_base_stage12 is dense_stage.run_stage12


def test_fraction_parameter_projection_preserves_dense_controls() -> None:
    parameters = {
        "enable_tc_big_fraction_context_rescue": True,
        "tc_big_fraction_context_max_nlp_tokens": 160,
        "enable_dense_figure_label_group_rescue": True,
        "dense_figure_label_group_max_nlp_tokens": 192,
        "beam_size": 6,
    }
    assert fraction_stage._base_parameters(parameters) == {
        "enable_dense_figure_label_group_rescue": True,
        "dense_figure_label_group_max_nlp_tokens": 192,
        "beam_size": 6,
    }
