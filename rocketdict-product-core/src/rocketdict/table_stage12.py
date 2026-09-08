from __future__ import annotations

"""Source-only Stage12 integration helpers for maintained ASCII tables.

The table detector/physical pieces and logical text grouping are independent
contracts.  This module binds them to Stage12 without making target text part of
planning.  A detected table stays one contiguous Product translation segment so
hard gates and Stage17 keep non-overlapping source spans; only its alpha-bearing
logical groups are sent to real MT.  Source-owned geometry and alpha-free
numeric/symbolic cells are rendered from their immutable pre-MT source spans.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .table_logical_structure import (
    LOGICAL_TABLE_CONTRACT,
    LogicalTableTextGroup,
    plan_logical_table_text_groups,
    render_logical_ascii_table,
)
from .table_structure import (
    TABLE_STRUCTURE_CONTRACT,
    AsciiTableBlock,
    TablePiece,
    detect_ascii_table_blocks,
    plan_ascii_table_pieces,
)

TABLE_STAGE12_CONTRACT = "rocketdict-stage12-ascii-table-logical-rank0/1"


@dataclass(frozen=True)
class Stage12TablePlan:
    source_start: int
    source_end: int
    source_text: str
    pieces: tuple[TablePiece, ...]
    groups: tuple[LogicalTableTextGroup, ...]


def _coalesce_table_split_boundary_whitespace(
    content: str, rows: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Attach table-split whitespace-only fragments to adjacent ordinary prose.

    Only fragments explicitly created by ``ascii_table_boundary_split`` are
    eligible. Table spans themselves are never extended or rewritten. If no
    ordinary neighbor exists inside the non-table slice, fail closed instead of
    inventing passthrough semantics.
    """
    output = [
        {**row, "metadata": dict(row.get("metadata") or {})}
        for row in rows
    ]

    def is_split_whitespace(row: dict[str, Any]) -> bool:
        metadata = dict(row.get("metadata") or {})
        return bool(metadata.get("ascii_table_boundary_split")) and not str(
            row.get("text") or ""
        ).strip()

    def merge(
        whitespace: dict[str, Any], neighbor: dict[str, Any], *, prepend: bool
    ) -> dict[str, Any]:
        metadata = dict(neighbor.get("metadata") or {})
        if metadata.get("source") == "ascii_table":
            raise ValueError("table boundary whitespace cannot extend an ASCII table")
        whitespace_metadata = dict(whitespace.get("metadata") or {})
        metadata.setdefault("source_before_table_split", metadata.get("source"))
        metadata["source"] = "nlp_sentence_fragment"
        metadata["ascii_table_boundary_split"] = True
        metadata["ascii_table_boundary_whitespace_coalesced"] = True

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
        raise ValueError("table partition produced isolated whitespace-only source gap")
    return output


def _slice_base_rows(
    content: str,
    base: Sequence[dict[str, Any]],
    *,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
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
            metadata["source_before_table_split"] = metadata.get("source")
            metadata["source"] = "nlp_sentence_fragment"
            metadata["ascii_table_boundary_split"] = True
        output.append(
            {
                "start": left,
                "end": right,
                "text": content[left:right],
                "metadata": metadata,
            }
        )
    if output and "".join(str(row["text"]) for row in output) != content[start:end]:
        raise ValueError("Stage12 non-table base slicing is not byte-exact")
    output = _coalesce_table_split_boundary_whitespace(content, output)
    if output and "".join(str(row["text"]) for row in output) != content[start:end]:
        raise ValueError("Stage12 table-boundary whitespace coalescing is not byte-exact")
    return output


def partition_txt_base_with_ascii_tables(
    content: str,
    base: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace source spans occupied by detected tables with one table unit each.

    Existing NLP sentence boundaries remain intact outside tables.  If a table
    begins/ends inside one NLP sentence, only that sentence is split at the
    source-owned table boundary.  The output covers exactly the same source
    scope as ``base`` and never invents bytes outside it.
    """
    if not base:
        return []
    scope_start = int(base[0]["start"])
    scope_end = int(base[-1]["end"])
    if scope_end <= scope_start:
        raise ValueError("Stage12 TXT base scope is empty")
    if "".join(str(row["text"]) for row in base) != content[scope_start:scope_end]:
        raise ValueError("Stage12 TXT base is not contiguous before table partition")

    blocks = [
        block
        for block in detect_ascii_table_blocks(content)
        if block.end > scope_start and block.start < scope_end
    ]
    for block in blocks:
        if block.start < scope_start or block.end > scope_end:
            raise ValueError("detected ASCII table crosses Stage12 context scope")

    output: list[dict[str, Any]] = []
    cursor = scope_start
    for block_index, block in enumerate(blocks):
        if block.start < cursor:
            raise ValueError("ASCII table blocks overlap during Stage12 partition")
        output.extend(
            _slice_base_rows(content, base, start=cursor, end=block.start)
        )
        output.append(
            {
                "start": int(block.start),
                "end": int(block.end),
                "text": content[block.start:block.end],
                "metadata": {
                    "source": "ascii_table",
                    "table_block_index": block_index,
                    "table_structure_contract": TABLE_STRUCTURE_CONTRACT,
                    "table_logical_contract": LOGICAL_TABLE_CONTRACT,
                    "table_stage12_contract": TABLE_STAGE12_CONTRACT,
                    "table_first_line": int(block.first_line),
                    "table_last_line": int(block.last_line),
                    "table_pipe_line_count": int(block.pipe_line_count),
                    "table_separator_line_count": int(block.separator_line_count),
                },
            }
        )
        cursor = int(block.end)
    output.extend(_slice_base_rows(content, base, start=cursor, end=scope_end))

    if not output:
        raise ValueError("Stage12 table partition produced no source units")
    if "".join(str(row["text"]) for row in output) != content[scope_start:scope_end]:
        raise ValueError("Stage12 table partition is not byte-exact")
    for left, right in zip(output, output[1:]):
        if int(left["end"]) != int(right["start"]):
            raise ValueError("Stage12 table partition produced a source gap")
    return output


def build_stage12_table_plan(
    text: str,
    *,
    absolute_start: int,
) -> Stage12TablePlan:
    pieces = tuple(plan_ascii_table_pieces(text, absolute_start=absolute_start))
    groups = tuple(
        plan_logical_table_text_groups(
            text,
            pieces,
            absolute_start=absolute_start,
        )
    )
    translated_alpha = sum(
        sum(char.isalpha() for char in piece.text)
        for piece in pieces
        if piece.kind == "translate"
    )
    grouped_alpha = sum(
        sum(char.isalpha() for char in group.source_text)
        for group in groups
    )
    if translated_alpha != grouped_alpha:
        raise ValueError(
            "Stage12 logical table grouping lost alpha source coverage: "
            f"{grouped_alpha} != {translated_alpha}"
        )
    return Stage12TablePlan(
        source_start=absolute_start,
        source_end=absolute_start + len(text),
        source_text=text,
        pieces=pieces,
        groups=groups,
    )


def table_group_source_spans(
    plan: Stage12TablePlan,
    group: LogicalTableTextGroup,
) -> list[dict[str, int]]:
    by_index = {piece.index: piece for piece in plan.pieces}
    spans: list[dict[str, int]] = []
    for piece_index in group.piece_indices:
        piece = by_index[piece_index]
        spans.append({"start": int(piece.start), "end": int(piece.end)})
    return spans


def render_stage12_table_rank0(
    plan: Stage12TablePlan,
    hypotheses_by_group: Mapping[int, Sequence[dict[str, Any]]],
) -> tuple[str, list[dict[str, Any]]]:
    """Render only rank-0 raw model hypotheses into immutable table structure."""
    expected = {group.index for group in plan.groups}
    if set(hypotheses_by_group) != expected:
        raise ValueError(
            "Stage12 table hypothesis mapping mismatch: "
            f"missing={sorted(expected - set(hypotheses_by_group))}, "
            f"extra={sorted(set(hypotheses_by_group) - expected)}"
        )

    translations: dict[int, str] = {}
    evidence: list[dict[str, Any]] = []
    for group in plan.groups:
        hypotheses = list(hypotheses_by_group[group.index])
        if not hypotheses:
            raise ValueError(f"OPUS returned no hypothesis for table group {group.index}")
        rank0 = hypotheses[0]
        if int(rank0.get("rank") or 0) != 0:
            raise ValueError("Stage12 table rank-0 hypothesis ordering drift")
        target = str(rank0.get("text") or "").strip()
        if not target:
            raise ValueError(f"OPUS returned empty target for table group {group.index}")
        translations[group.index] = target
        evidence.append(
            {
                "group_index": int(group.index),
                "piece_indices": [int(value) for value in group.piece_indices],
                "source_spans": table_group_source_spans(plan, group),
                "source_text": group.source_text,
                "target_text": target,
                "first_line": int(group.first_line),
                "last_line": int(group.last_line),
                "lane": int(group.lane),
                "section": int(group.section),
                "numeric_bearing": bool(group.numeric_bearing),
                "grouping_reason": group.grouping_reason,
                "selected_rank": 0,
                "hypotheses": hypotheses,
            }
        )

    target = render_logical_ascii_table(
        plan.source_text,
        plan.pieces,
        plan.groups,
        translations,
    )
    if not target.strip():
        raise ValueError("Stage12 rendered an empty table target")
    return target, evidence


def table_plan_metrics(plan: Stage12TablePlan) -> dict[str, int]:
    preserved = [piece for piece in plan.pieces if piece.kind != "translate"]
    translated = [piece for piece in plan.pieces if piece.kind == "translate"]
    return {
        "piece_count": len(plan.pieces),
        "physical_translate_piece_count": len(translated),
        "logical_group_count": len(plan.groups),
        "multi_piece_group_count": sum(
            1 for group in plan.groups if len(group.piece_indices) > 1
        ),
        "preserved_piece_count": len(preserved),
        "preserved_source_character_count": sum(len(piece.text) for piece in preserved),
        "translated_source_character_count": sum(len(piece.text) for piece in translated),
        "max_logical_group_word_proxy": max(
            (len(group.source_text.split()) for group in plan.groups),
            default=0,
        ),
    }
