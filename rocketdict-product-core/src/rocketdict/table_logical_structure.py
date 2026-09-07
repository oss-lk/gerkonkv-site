from __future__ import annotations

"""Logical text grouping over byte-exact maintained ASCII-table pieces.

``table_structure`` deliberately exposes physical source pieces.  Real full-
Opticks review showed that translating each physical line fragment separately
preserves numbers/geometry but can badly damage multi-line headers and labels.
This module adds a second, independently versioned source-only layer which groups
only alpha-bearing pieces that visibly belong to one logical table text unit.

No target text participates in grouping.  Numeric-bearing text pieces remain
singletons.  Horizontal separator rows are hard boundaries.  Header sections
without digits are grouped vertically by visual column.  In data sections,
indented text continues the preceding text in the same visual lane; Newton's
brace-grouped colour table additionally uses its repeated source brace column to
identify sparse left-hand order labels.  This is a forward maintained contract,
not a claim of recovered historical implementation.
"""

from dataclasses import dataclass
from collections import Counter, defaultdict
import re
from typing import Mapping, Sequence

from .numeric_integrity import extract_numeric_literals
from .table_structure import TablePiece

LOGICAL_TABLE_CONTRACT = "rocketdict-ascii-table-logical-cells/1"
_ALLOWED_SEPARATOR = set("-+_| \t\r\n")


@dataclass(frozen=True)
class LogicalTableTextGroup:
    index: int
    piece_indices: tuple[int, ...]
    source_text: str
    first_line: int
    last_line: int
    lane: int
    section: int
    numeric_bearing: bool
    grouping_reason: str


def _is_separator_line(line: str) -> bool:
    stripped = line.strip(" \t\r\n")
    if len(stripped) < 5:
        return False
    if any(char.isalnum() for char in stripped):
        return False
    if any(char not in _ALLOWED_SEPARATOR for char in line):
        return False
    return (
        ("+" in stripped or "|" in stripped)
        and sum(char in "-_" for char in stripped) >= 4
    )


def _line_starts(text: str) -> list[int]:
    output: list[int] = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        output.append(cursor)
        cursor += len(line)
    if cursor != len(text):
        raise ValueError("logical table grouping lost source line bytes")
    return output


def _visual_boundaries(text: str) -> tuple[list[int], bool]:
    counts: Counter[int] = Counter()
    brace_counts: Counter[int] = Counter()
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        for column, char in enumerate(body):
            if char in "|{":
                counts[column] += 1
                if char == "{":
                    brace_counts[column] += 1
    # One-off punctuation must never manufacture a visual lane.  Repeated pipes
    # and the repeated Newton brace are source structure.
    boundaries = sorted(column for column, count in counts.items() if count >= 2)
    repeated_brace = any(count >= 2 for count in brace_counts.values())
    return boundaries, repeated_brace


def _sections(text: str) -> tuple[dict[int, int], dict[int, list[int]]]:
    by_line: dict[int, int] = {}
    lines_by_section: dict[int, list[int]] = defaultdict(list)
    section = -1
    inside = False
    for line_index, line in enumerate(text.splitlines(keepends=True)):
        if _is_separator_line(line):
            inside = False
            continue
        if not inside:
            section += 1
            inside = True
        by_line[line_index] = section
        lines_by_section[section].append(line_index)
    return by_line, dict(lines_by_section)


def _join_group_source(pieces: Sequence[TablePiece]) -> str:
    parts = [piece.text.strip() for piece in pieces if piece.text.strip()]
    if not parts:
        raise ValueError("logical table group contains no source text")
    return " ".join(parts)


def plan_logical_table_text_groups(
    text: str,
    pieces: Sequence[TablePiece],
    *,
    absolute_start: int = 0,
) -> list[LogicalTableTextGroup]:
    """Group all physical ``translate`` pieces exactly once using source only."""
    translate_pieces = [piece for piece in pieces if piece.kind == "translate"]
    if not translate_pieces:
        return []

    line_starts = _line_starts(text)
    boundaries, repeated_brace = _visual_boundaries(text)
    section_by_line, lines_by_section = _sections(text)

    enriched: list[tuple[TablePiece, int, int, int]] = []
    for piece in translate_pieces:
        if piece.line_index not in section_by_line:
            raise ValueError("translate piece lies on a structural separator line")
        if not (absolute_start <= piece.start < piece.end <= absolute_start + len(text)):
            raise ValueError("logical table piece lies outside table source span")
        line_start = line_starts[piece.line_index]
        column = piece.start - absolute_start - line_start
        if column < 0:
            raise ValueError("logical table piece has a negative visual column")
        lane = sum(1 for boundary in boundaries if column > boundary)
        enriched.append((piece, column, lane, section_by_line[piece.line_index]))

    buckets: dict[tuple[int, int], list[tuple[TablePiece, int]]] = defaultdict(list)
    for piece, column, lane, section in enriched:
        buckets[(section, lane)].append((piece, column))

    provisional: list[tuple[list[TablePiece], int, int, str]] = []
    lines = text.splitlines(keepends=True)

    for (section, lane), entries in sorted(buckets.items()):
        entries.sort(key=lambda item: (item[0].line_index, item[0].start))
        section_lines = lines_by_section[section]
        section_has_digit = any(
            any(char.isdigit() for char in lines[line_index])
            for line_index in section_lines
        )

        # A non-data/header section is one vertical logical cell per visual lane.
        if not section_has_digit:
            provisional.append(
                ([piece for piece, _column in entries], lane, section, "header_vertical_lane")
            )
            continue

        numeric_entries: list[tuple[TablePiece, int]] = []
        text_entries: list[tuple[TablePiece, int]] = []
        for entry in entries:
            if extract_numeric_literals(entry[0].text):
                numeric_entries.append(entry)
            else:
                text_entries.append(entry)

        # Numeric-bearing alpha text such as ``23 to 14`` is already one
        # semantic relation.  Never merge it with a neighbouring row.
        for piece, _column in numeric_entries:
            provisional.append(([piece], lane, section, "numeric_text_singleton"))

        if not text_entries:
            continue

        # Opticks' colour-order table has a repeated source brace which creates
        # a nested visual lane.  The sparse left-hand label (e.g. "Their Colours
        # of the / first Order") spans the section; colour names to its right
        # begin at their lane origin and remain separate rows.
        if lane == 0 and repeated_brace and len(text_entries) > 1:
            provisional.append(
                (
                    [piece for piece, _column in text_entries],
                    lane,
                    section,
                    "repeated_brace_section_label",
                )
            )
            continue

        lane_left = 0 if lane == 0 else boundaries[lane - 1] + 1
        current: list[TablePiece] = []
        for piece, column in text_entries:
            starts_record = column <= lane_left + 1
            if not current or starts_record:
                if current:
                    provisional.append((current, lane, section, "indentation_record"))
                current = [piece]
            else:
                current.append(piece)
        if current:
            provisional.append((current, lane, section, "indentation_record"))

    provisional.sort(key=lambda row: min(piece.start for piece in row[0]))
    groups: list[LogicalTableTextGroup] = []
    covered: set[int] = set()
    for index, (members, lane, section, reason) in enumerate(provisional):
        member_indices = tuple(piece.index for piece in members)
        if any(piece_index in covered for piece_index in member_indices):
            raise ValueError("translate table piece belongs to multiple logical groups")
        covered.update(member_indices)
        source_text = _join_group_source(members)
        groups.append(
            LogicalTableTextGroup(
                index=index,
                piece_indices=member_indices,
                source_text=source_text,
                first_line=min(piece.line_index for piece in members),
                last_line=max(piece.line_index for piece in members),
                lane=lane,
                section=section,
                numeric_bearing=bool(extract_numeric_literals(source_text)),
                grouping_reason=reason,
            )
        )

    expected = {piece.index for piece in translate_pieces}
    if covered != expected:
        raise ValueError(
            "logical table grouping does not cover every translate piece exactly once: "
            f"missing={sorted(expected - covered)}, extra={sorted(covered - expected)}"
        )
    return groups


def render_logical_ascii_table(
    text: str,
    pieces: Sequence[TablePiece],
    groups: Sequence[LogicalTableTextGroup],
    translations: Mapping[int, str],
) -> str:
    """Render one raw-model translation per logical group into source geometry.

    The translated string occupies the first physical text slot of the group;
    later physical fragments are blanked while their surrounding source-owned
    whitespace, delimiters, numeric cells and line endings remain untouched.
    No target token is synthesized from source data during rendering.
    """
    if "".join(piece.text for piece in pieces) != text:
        raise ValueError("logical table render pieces do not belong to source text")
    expected_groups = {group.index for group in groups}
    if set(translations) != expected_groups:
        raise ValueError(
            "logical table translation mapping mismatch: "
            f"missing={sorted(expected_groups - set(translations))}, "
            f"extra={sorted(set(translations) - expected_groups)}"
        )

    piece_to_group: dict[int, LogicalTableTextGroup] = {}
    for group in groups:
        for piece_index in group.piece_indices:
            if piece_index in piece_to_group:
                raise ValueError("logical render piece belongs to multiple groups")
            piece_to_group[piece_index] = group

    expected_translate = {piece.index for piece in pieces if piece.kind == "translate"}
    if set(piece_to_group) != expected_translate:
        raise ValueError("logical render group coverage differs from translate pieces")

    rendered: list[str] = []
    for piece in pieces:
        if piece.kind != "translate":
            rendered.append(piece.text)
            continue
        group = piece_to_group[piece.index]
        if piece.index != group.piece_indices[0]:
            rendered.append("")
            continue
        target = str(translations[group.index]).strip()
        if not target:
            raise ValueError(f"empty translation for logical table group {group.index}")
        rendered.append(target)
    return "".join(rendered)
