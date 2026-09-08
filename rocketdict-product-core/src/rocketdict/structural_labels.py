from __future__ import annotations

"""Source-owned structural labels for maintained Stage12 EN→RU execution.

The contract is deliberately narrow and evidence-backed.  It recognizes only
numbered Gutenberg-style block labels whose abbreviations were validated on the
complete pinned Opticks corpus: ``_Exper._``, ``_Obs._`` and ``_Qu._``.

The immutable source bytes are never rewritten.  A label carries a separate,
recorded model input in which only the abbreviation is expanded to its literal
English full form (Experiment / Observation / Query).  Target candidates must
remain raw OPUS hypotheses and are accepted only when they preserve the source
number and have the exact validated Russian heading form ending in a period.
No target-side insertion or repair is performed here.
"""

from dataclasses import dataclass
import re
from typing import Any, Sequence

from .numeric_integrity import compare_numeric_integrity

STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/1"
STRUCTURAL_LABEL_GENERATION_CELLS: tuple[tuple[int, int], ...] = (
    (6, 6),
    (12, 12),
)

SOURCE_EXPANSIONS = {
    "exper": "Experiment",
    "obs": "Observation",
    "qu": "Query",
}
TARGET_TERMS = {
    "exper": "Эксперимент",
    "obs": "Наблюдение",
    "qu": "Вопрос",
}

_LABEL_RE = re.compile(
    r"_(?P<kind>Exper|Obs|Qu)\._\s+(?P<number>\d+)\.",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class StructuralLabel:
    source_start: int
    source_end: int
    source_text: str
    kind: str
    number: str
    canonical_model_input: str
    block_level: bool


def _is_block_start(text: str, offset: int) -> bool:
    if offset == 0:
        return True
    # Gutenberg block headings are separated from the preceding prose by a
    # blank line.  Support LF and CRLF plus horizontal indentation without
    # treating a label embedded in ordinary prose as a block heading.
    prefix = text[:offset]
    return bool(re.search(r"(?:\r?\n)[ \t]*(?:\r?\n)[ \t]*\Z", prefix))


def detect_structural_labels(
    text: str,
    *,
    absolute_start: int = 0,
    block_only: bool = False,
) -> list[StructuralLabel]:
    """Return exact source spans for supported structural labels.

    ``block_only`` must be evaluated on a source slice whose beginning has the
    same paragraph-boundary meaning as the immutable source.  The maintained
    planner therefore calls it on the complete document and only later maps the
    resulting absolute spans into context units.
    """
    labels: list[StructuralLabel] = []
    for match in _LABEL_RE.finditer(text):
        block_level = _is_block_start(text, match.start())
        if block_only and not block_level:
            continue
        kind = str(match.group("kind")).lower()
        number = str(match.group("number"))
        labels.append(
            StructuralLabel(
                source_start=absolute_start + match.start(),
                source_end=absolute_start + match.end(),
                source_text=match.group(0),
                kind=kind,
                number=number,
                canonical_model_input=f"{SOURCE_EXPANSIONS[kind]} {number}.",
                block_level=block_level,
            )
        )
    return labels


def parse_structural_label_unit(source_text: str) -> StructuralLabel:
    """Parse one isolated label unit, allowing source-owned surrounding whitespace."""
    stripped = source_text.strip()
    matches = list(_LABEL_RE.finditer(stripped))
    if len(matches) != 1:
        raise ValueError("structural-label unit must contain exactly one supported label")
    match = matches[0]
    if match.start() != 0 or match.end() != len(stripped):
        raise ValueError("structural-label unit contains non-whitespace content outside the label")
    kind = str(match.group("kind")).lower()
    number = str(match.group("number"))
    return StructuralLabel(
        source_start=0,
        source_end=len(source_text),
        source_text=match.group(0),
        kind=kind,
        number=number,
        canonical_model_input=f"{SOURCE_EXPANSIONS[kind]} {number}.",
        block_level=True,
    )


def _strict_target_form(label: StructuralLabel, target: str) -> bool:
    term = TARGET_TERMS[label.kind]
    return bool(
        re.fullmatch(
            rf"\s*{re.escape(term)}\s+{re.escape(label.number)}\.\s*",
            target,
            flags=re.IGNORECASE,
        )
    )


def evaluate_structural_label_hypotheses(
    label: StructuralLabel,
    hypotheses: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate raw model hypotheses without changing target text."""
    candidates: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for model_index, hypothesis in enumerate(hypotheses):
        target = str(hypothesis.get("text") or "").strip()
        numeric = compare_numeric_integrity(label.source_text, target)
        strict_target = _strict_target_form(label, target)
        candidate = {
            "model_index": model_index,
            "rank": int(
                hypothesis.get("rank")
                if hypothesis.get("rank") is not None
                else model_index
            ),
            "score": hypothesis.get("score"),
            "target_text": target,
            "numeric_integrity": numeric,
            "expected_target_term": TARGET_TERMS[label.kind],
            "strict_target_form": strict_target,
            "acceptable": bool(numeric["passed"] is True and strict_target),
        }
        candidates.append(candidate)
        if selected is None and candidate["acceptable"]:
            selected = candidate
    return {
        "contract": STRUCTURAL_LABEL_CONTRACT,
        "source_text": label.source_text,
        "kind": label.kind,
        "number": label.number,
        "canonical_model_input": label.canonical_model_input,
        "expected_target_term": TARGET_TERMS[label.kind],
        "selected": selected,
        "candidates": candidates,
    }
