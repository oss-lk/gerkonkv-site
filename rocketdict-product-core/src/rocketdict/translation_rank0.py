from __future__ import annotations

"""Shared fail-closed policy for diagnostic n-best rescue evidence.

Rescue wrappers may retain and evaluate multiple raw model hypotheses for
research, but automatic Product/research persistence is authorized only by the
unique raw rank-0 hypothesis. A later beam can never rescue a rejected rank0.
"""

from typing import Any

from .stages import StageExecutionError


def select_rank0_evaluation(
    evaluated_hypotheses: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return accepted unique rank0 evidence, or ``None`` when rank0 fails.

    Missing, duplicate, or malformed rank evidence is a provenance/cardinality
    error. Higher ranks remain diagnostic evidence and have no selection
    authority.
    """

    rank0: list[dict[str, Any]] = []
    for row in evaluated_hypotheses:
        try:
            rank = int(row["rank"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StageExecutionError(
                "rank0-only rescue encountered malformed evaluated rank evidence"
            ) from exc
        if rank == 0:
            rank0.append(row)
    if len(rank0) != 1:
        raise StageExecutionError(
            "rank0-only rescue requires exactly one evaluated rank0 hypothesis"
        )
    choice = rank0[0]
    if choice.get("accepted") is not True:
        return None
    selection = choice.get("selection")
    if not isinstance(selection, dict):
        raise StageExecutionError(
            "accepted rank0 rescue evaluation is missing selector evidence"
        )
    return choice
