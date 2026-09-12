from __future__ import annotations

import inspect

import pytest

from rocketdict.stages import StageExecutionError
from rocketdict.translation_rank0 import select_rank0_evaluation
import rocketdict.translation_illustration_rescue_stage as illustration
import rocketdict.translation_tc_big_delimiter_rescue_stage as delimiter
import rocketdict.translation_tc_big_footnote_reference_rescue_stage as footnote
import rocketdict.translation_tc_big_semicolon_question_rescue_stage as semicolon_question
import rocketdict.translation_tc_big_equals_addition_rescue_stage as equals_addition


def _row(rank: int, accepted: bool) -> dict[str, object]:
    row: dict[str, object] = {
        "rank": rank,
        "target_text": f"candidate-{rank}",
        "accepted": accepted,
    }
    if accepted:
        row["selection"] = {"accepted": True, "rank": rank}
    return row


def test_rank0_policy_rejects_good_later_beam() -> None:
    evaluated = [_row(0, False), _row(1, True), _row(2, True)]
    assert select_rank0_evaluation(evaluated) is None


def test_rank0_policy_accepts_only_good_rank0_and_preserves_diagnostics() -> None:
    evaluated = [_row(0, True), _row(1, True)]
    selected = select_rank0_evaluation(evaluated)
    assert selected is evaluated[0]
    assert evaluated[1]["accepted"] is True


def test_rank0_policy_fails_closed_on_missing_or_duplicate_rank0() -> None:
    with pytest.raises(StageExecutionError):
        select_rank0_evaluation([_row(1, True)])
    with pytest.raises(StageExecutionError):
        select_rank0_evaluation([_row(0, True), _row(0, False)])


@pytest.mark.parametrize(
    ("module", "rescue_contract", "selector_contract"),
    [
        (illustration, illustration.ILLUSTRATION_LABEL_RESCUE_CONTRACT, illustration.ILLUSTRATION_LABEL_SELECTOR_CONTRACT),
        (delimiter, delimiter.TC_BIG_DELIMITER_RESCUE_CONTRACT, delimiter.TC_BIG_DELIMITER_SELECTOR_CONTRACT),
        (footnote, footnote.TC_BIG_FOOTNOTE_RESCUE_CONTRACT, footnote.TC_BIG_FOOTNOTE_SELECTOR_CONTRACT),
        (semicolon_question, semicolon_question.TC_BIG_SEMICOLON_QUESTION_RESCUE_CONTRACT, semicolon_question.TC_BIG_SEMICOLON_QUESTION_SELECTOR_CONTRACT),
        (equals_addition, equals_addition.TC_BIG_EQUALS_RESCUE_CONTRACT, equals_addition.TC_BIG_EQUALS_SELECTOR_CONTRACT),
    ],
)
def test_nbest_rescue_modules_are_structurally_rank0_only(
    module, rescue_contract: str, selector_contract: str
) -> None:  # type: ignore[no-untyped-def]
    assert rescue_contract.endswith("/2")
    assert selector_contract.endswith("/2")
    source = inspect.getsource(module.run_stage12)
    assert "select_rank0_evaluation(evaluated)" in source
    assert "automatic_n_best_cherry_picking" in inspect.getsource(module._safety_flags)
