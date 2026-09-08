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



def _coalesce_split_boundary_whitespace(
    content: str, rows: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Attach split-created whitespace-only fragments to ordinary prose.

    Structural labels remain exact standalone source spans.  The only fragments
    eligible here are whitespace-only rows that were *created by structural-label
    slicing*. Existing semantic rows are never silently rewritten.  ASCII tables
    are not extended because their source geometry is a separate maintained
    contract; an otherwise unrepresentable whitespace-only gap fails closed.
    """
    output = [
        {**row, "metadata": dict(row.get("metadata") or {})}
        for row in rows
    ]

    def is_split_whitespace(row: dict[str, Any]) -> bool:
        metadata = dict(row.get("metadata") or {})
        return bool(metadata.get("structural_label_boundary_split")) and not str(
            row.get("text") or ""
        ).strip()

    def merge(
        whitespace: dict[str, Any], neighbor: dict[str, Any], *, prepend: bool
    ) -> dict[str, Any]:
        metadata = dict(neighbor.get("metadata") or {})
        if metadata.get("source") == "ascii_table":
            raise ValueError(
                "structural-label boundary whitespace cannot be merged into an ASCII table"
            )
        whitespace_metadata = dict(whitespace.get("metadata") or {})
        metadata.setdefault(
            "source_before_structural_label_split", metadata.get("source")
        )
        metadata["source"] = "nlp_sentence_fragment"
        metadata["structural_label_boundary_split"] = True
        metadata["structural_label_boundary_whitespace_coalesced"] = True

        starts = [
            int(value)
            for value in (
                metadata.get("context_sentence_start"),
                whitespace_metadata.get("context_sentence_start"),
            )
            if value is not None
        ]
        ends = [
            int(value)
            for value in (
                metadata.get("context_sentence_end"),
                whitespace_metadata.get("context_sentence_end"),
            )
            if value is not None
        ]
        if starts and ends:
            metadata["context_sentence_start"] = min(starts)
            metadata["context_sentence_end"] = max(ends)
            metadata["context_sentence_count"] = (
                int(metadata["context_sentence_end"])
                - int(metadata["context_sentence_start"])
                + 1
            )

        if prepend:
            start = int(whitespace["start"])
            end = int(neighbor["end"])
        else:
            start = int(neighbor["start"])
            end = int(whitespace["end"])
        return {
            "start": start,
            "end": end,
            "text": content[start:end],
            "metadata": metadata,
        }

    while len(output) > 1 and is_split_whitespace(output[0]):
        whitespace = output.pop(0)
        output[0] = merge(whitespace, output[0], prepend=True)

    while len(output) > 1 and is_split_whitespace(output[-1]):
        whitespace = output.pop()
        output[-1] = merge(whitespace, output[-1], prepend=False)

    if len(output) == 1 and is_split_whitespace(output[0]):
        raise ValueError(
            "structural-label partition produced an isolated whitespace-only source gap"
        )
    return output


def _slice_base_rows(
    content: str,
    base: Sequence[dict[str, Any]],
    *,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    """Slice existing Stage12 TXT base rows without inventing source bytes."""
    if end <= start:
        return []
    output: list[dict[str, Any]] = []
    for row in base:
        row_start = int(row["start"])
        row_end = int(row["end"])
        left = max(start, row_start)
        right = min(end, row_end)
        if right <= left:
            continue
        metadata = dict(row.get("metadata") or {})
        if left != row_start or right != row_end:
            if metadata.get("source") == "ascii_table":
                raise ValueError("supported structural label overlaps an ASCII-table unit")
            metadata["source_before_structural_label_split"] = metadata.get("source")
            metadata["source"] = "nlp_sentence_fragment"
            metadata["structural_label_boundary_split"] = True
        output.append(
            {
                "start": left,
                "end": right,
                "text": content[left:right],
                "metadata": metadata,
            }
        )
    if output and "".join(str(row["text"]) for row in output) != content[start:end]:
        raise ValueError("structural-label non-label slicing is not byte-exact")
    output = _coalesce_split_boundary_whitespace(content, output)
    if output and "".join(str(row["text"]) for row in output) != content[start:end]:
        raise ValueError("structural-label whitespace coalescing is not byte-exact")
    return output


def partition_txt_base_with_block_structural_labels(
    content: str,
    base: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Make supported block labels standalone byte-exact Stage12 base units.

    Detection runs on the complete immutable TXT source, not on already split
    context fragments. This is required because full-Opticks evidence proved
    that planner /4 cut 48/109 supported labels across Stage12 boundaries.
    Inline labels remain ordinary prose.
    """
    if not base:
        return []
    scope_start = int(base[0]["start"])
    scope_end = int(base[-1]["end"])
    if scope_end <= scope_start:
        raise ValueError("Stage12 structural-label base scope is empty")
    if "".join(str(row["text"]) for row in base) != content[scope_start:scope_end]:
        raise ValueError("Stage12 structural-label input base is not contiguous")

    labels = [
        label
        for label in detect_structural_labels(content, block_only=True)
        if label.source_end > scope_start and label.source_start < scope_end
    ]
    for label in labels:
        if label.source_start < scope_start or label.source_end > scope_end:
            raise ValueError("block structural label crosses Stage12 TXT scope")
        for row in base:
            if (row.get("metadata") or {}).get("source") != "ascii_table":
                continue
            if label.source_start < int(row["end"]) and label.source_end > int(row["start"]):
                raise ValueError("supported structural label overlaps an ASCII table")

    output: list[dict[str, Any]] = []
    cursor = scope_start
    for label_index, label in enumerate(labels):
        if label.source_start < cursor:
            raise ValueError("supported structural labels overlap")
        output.extend(_slice_base_rows(content, base, start=cursor, end=label.source_start))
        output.append(
            {
                "start": int(label.source_start),
                "end": int(label.source_end),
                "text": content[label.source_start:label.source_end],
                "metadata": {
                    "source": "structural_label",
                    "structural_label_index": label_index,
                    "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
                    "structural_label_kind": label.kind,
                    "structural_label_number": label.number,
                    "canonical_model_input": label.canonical_model_input,
                },
            }
        )
        cursor = int(label.source_end)
    output.extend(_slice_base_rows(content, base, start=cursor, end=scope_end))

    if not output:
        raise ValueError("Stage12 structural-label partition produced no source units")
    if "".join(str(row["text"]) for row in output) != content[scope_start:scope_end]:
        raise ValueError("Stage12 structural-label partition is not byte-exact")
    for left, right in zip(output, output[1:]):
        if int(left["end"]) != int(right["start"]):
            raise ValueError("Stage12 structural-label partition produced a source gap")
    return output
