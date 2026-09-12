from __future__ import annotations

import pytest

from rocketdict.stages import StageExecutionError
from rocketdict.translation_tc_big_angular_minute_rescue_stage import (
    _evaluate_rank0_hypotheses,
)

SOURCE = "The Halo was about 22 Degrees 35' distant."
GOOD = "Гало находилось на расстоянии около 22 градусов 35'."
BAD = "Гало находилось на расстоянии около 22 градусов 35 минут."


def test_rank1_cannot_rescue_rejected_rank0() -> None:
    evaluated, selected_target, selected_selection = _evaluate_rank0_hypotheses(
        SOURCE,
        [
            {"rank": 0, "text": BAD, "score": -0.1},
            {"rank": 1, "text": GOOD, "score": -0.2},
        ],
    )
    assert evaluated[0]["accepted"] is False
    assert evaluated[0]["selection_authorized"] is True
    assert evaluated[1]["accepted"] is True
    assert evaluated[1]["selection_authorized"] is False
    assert selected_target is None
    assert selected_selection is None


def test_rank0_is_selected_even_when_later_beam_also_passes() -> None:
    evaluated, selected_target, selected_selection = _evaluate_rank0_hypotheses(
        SOURCE,
        [
            {"rank": 0, "text": GOOD, "score": -0.1},
            {"rank": 1, "text": GOOD, "score": -0.2},
        ],
    )
    assert all(item["accepted"] is True for item in evaluated)
    assert selected_target == GOOD
    assert selected_selection is not None
    assert selected_selection["accepted"] is True


def test_rank0_cardinality_drift_fails_closed() -> None:
    with pytest.raises(StageExecutionError, match="rank-0 cardinality drift"):
        _evaluate_rank0_hypotheses(
            SOURCE,
            [
                {"rank": 1, "text": GOOD, "score": -0.1},
                {"rank": 2, "text": GOOD, "score": -0.2},
            ],
        )
