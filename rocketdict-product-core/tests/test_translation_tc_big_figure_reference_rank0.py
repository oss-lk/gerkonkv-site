from __future__ import annotations

import pytest

from rocketdict.stages import StageExecutionError
from rocketdict.translation_tc_big_figure_reference_rescue_stage import (
    _evaluate_rank0_hypotheses,
)


SOURCE = "[in _Fig._ 15.] is the Spectator's Eye."
GOOD_RANK0 = "[В _рис._ 15.] это Глаз Зрителя."


def test_rank1_cannot_rescue_a_rejected_rank0() -> None:
    evaluated, selected_target, selected_selection = _evaluate_rank0_hypotheses(
        SOURCE,
        [
            {"rank": 0, "text": "Без ссылки.", "score": -0.1},
            {"rank": 1, "text": GOOD_RANK0, "score": -0.2},
        ],
        figure_number="15",
    )

    assert evaluated[0]["accepted"] is False
    assert evaluated[0]["selection_authorized"] is True
    assert evaluated[1]["accepted"] is True
    assert evaluated[1]["selection_authorized"] is False
    assert selected_target is None
    assert selected_selection is None


def test_rank0_is_selected_without_consulting_later_acceptance() -> None:
    evaluated, selected_target, selected_selection = _evaluate_rank0_hypotheses(
        SOURCE,
        [
            {"rank": 0, "text": GOOD_RANK0, "score": -0.1},
            {"rank": 1, "text": GOOD_RANK0, "score": -0.2},
        ],
        figure_number="15",
    )

    assert all(item["accepted"] is True for item in evaluated)
    assert evaluated[0]["selection_authorized"] is True
    assert evaluated[1]["selection_authorized"] is False
    assert selected_target == GOOD_RANK0
    assert selected_selection is not None
    assert selected_selection["accepted"] is True


def test_rank0_cardinality_drift_fails_closed() -> None:
    with pytest.raises(StageExecutionError, match="rank-0 cardinality drift"):
        _evaluate_rank0_hypotheses(
            SOURCE,
            [
                {"rank": 1, "text": GOOD_RANK0, "score": -0.1},
                {"rank": 2, "text": GOOD_RANK0, "score": -0.2},
            ],
            figure_number="15",
        )
