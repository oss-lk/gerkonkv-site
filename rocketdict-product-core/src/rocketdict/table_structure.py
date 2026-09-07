from __future__ import annotations

"""Source-only ASCII-table structure for maintained translation research/Product planning.

The detector is deliberately conservative.  A single pipe in prose is not a
table; a block must contain several pipe-bearing physical lines and either a
multi-column line or a separator row.  Detected blocks are immutable source
spans.

Inside a table, source-owned geometry (pipes, braces, border rows, whitespace
and line endings) and alphabet-free numeric/symbolic cell payloads are kept as
exact source pieces.  Only alpha-bearing cell payloads are marked for real MT.
This is structural decomposition, not post-hoc numeric repair: passthrough bytes
already exist at fixed source offsets before any model call.
"""

from dataclasses import dataclass
import re
from typing import Mapping

TABLE_STRUCTURE_CONTRACT = "rocketdict-ascii-table-cells/1"

_ALLOWED_SEPARATOR = set("-+_| \t\r\n")
_ALPHA_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")


@dataclass(frozen=True)
class AsciiTableBlock:
    start: int
    end: int
    first_line: int
    last_line: int
    pipe_line_count: int
    separator_line_count: int


@dataclass(frozen=True)
class TablePiece:
    index: int
    start: int
    end: int
    text: str
    kind: str  # structure | passthrough | translate
    line_index: int
    cell_index: int | None


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


def detect_ascii_table_blocks(
    text: str,
    *,
    minimum_pipe_lines: int = 3,
) -> list[AsciiTableBlock]:
    if minimum_pipe_lines < 2:
        raise ValueError("minimum_pipe_lines must be >= 2")

    rows: list[tuple[int, int, int, str]] = []
    cursor = 0
    for index, line in enumerate(text.splitlines(keepends=True)):
        start = cursor
        cursor += len(line)
        rows.append((index, start, cursor, line))
    if cursor != len(text):
        raise ValueError("ASCII table detector lost source bytes")

    blocks: list[AsciiTableBlock] = []
    run: list[tuple[int, int, int, str]] = []

    def flush() -> None:
        nonlocal run
        if not run:
            return
        pipe_lines = sum(1 for _index, _start, _end, line in run if "|" in line)
        separator_lines = sum(
            1 for _index, _start, _end, line in run if _is_separator_line(line)
        )
        max_pipes = max((line.count("|") for _i, _s, _e, line in run), default=0)
        if (
            pipe_lines >= minimum_pipe_lines
            and (max_pipes >= 2 or separator_lines >= 1)
        ):
            blocks.append(
                AsciiTableBlock(
                    start=run[0][1],
                    end=run[-1][2],
                    first_line=run[0][0],
                    last_line=run[-1][0],
                    pipe_line_count=pipe_lines,
                    separator_line_count=separator_lines,
                )
            )
        run = []

    for row in rows:
        line = row[3]
        if "|" in line or _is_separator_line(line):
            run.append(row)
        else:
            flush()
    flush()

    for left, right in zip(blocks, blocks[1:]):
        if left.end > right.start:
            raise ValueError("ASCII table detector produced overlapping blocks")
    return blocks


def _append_piece(
    output: list[TablePiece],
    *,
    start: int,
    end: int,
    text: str,
    kind: str,
    line_index: int,
    cell_index: int | None,
) -> None:
    if not text:
        return
    if end - start != len(text):
        raise ValueError("table piece source span length mismatch")
    output.append(
        TablePiece(
            index=len(output),
            start=start,
            end=end,
            text=text,
            kind=kind,
            line_index=line_index,
            cell_index=cell_index,
        )
    )


def _plan_cell_payload(
    output: list[TablePiece],
    payload: str,
    *,
    absolute_start: int,
    line_index: int,
    cell_index: int,
) -> None:
    if not payload:
        return
    if not payload.strip():
        _append_piece(
            output,
            start=absolute_start,
            end=absolute_start + len(payload),
            text=payload,
            kind="structure",
            line_index=line_index,
            cell_index=cell_index,
        )
        return

    leading = len(payload) - len(payload.lstrip())
    trailing = len(payload) - len(payload.rstrip())
    if leading:
        _append_piece(
            output,
            start=absolute_start,
            end=absolute_start + leading,
            text=payload[:leading],
            kind="structure",
            line_index=line_index,
            cell_index=cell_index,
        )

    core_start = leading
    core_end = len(payload) - trailing if trailing else len(payload)
    core = payload[core_start:core_end]
    if core:
        _append_piece(
            output,
            start=absolute_start + core_start,
            end=absolute_start + core_end,
            text=core,
            kind="translate" if _ALPHA_RE.search(core) else "passthrough",
            line_index=line_index,
            cell_index=cell_index,
        )

    if trailing:
        _append_piece(
            output,
            start=absolute_start + len(payload) - trailing,
            end=absolute_start + len(payload),
            text=payload[-trailing:],
            kind="structure",
            line_index=line_index,
            cell_index=cell_index,
        )


def _plan_cell(
    output: list[TablePiece],
    cell: str,
    *,
    absolute_start: int,
    line_index: int,
    cell_index: int,
) -> None:
    local = 0
    # Opticks uses a left brace as a table grouping glyph.  Keep brace bytes at
    # their source positions while translating alpha payload on either side.
    for match in re.finditer(r"[{}]", cell):
        before = cell[local : match.start()]
        if before:
            _plan_cell_payload(
                output,
                before,
                absolute_start=absolute_start + local,
                line_index=line_index,
                cell_index=cell_index,
            )
        _append_piece(
            output,
            start=absolute_start + match.start(),
            end=absolute_start + match.end(),
            text=match.group(0),
            kind="structure",
            line_index=line_index,
            cell_index=cell_index,
        )
        local = match.end()
    tail = cell[local:]
    if tail:
        _plan_cell_payload(
            output,
            tail,
            absolute_start=absolute_start + local,
            line_index=line_index,
            cell_index=cell_index,
        )


def plan_ascii_table_pieces(
    text: str,
    *,
    absolute_start: int = 0,
) -> list[TablePiece]:
    """Partition one detected table block into byte-exact source pieces."""
    output: list[TablePiece] = []
    cursor = 0
    for line_index, line in enumerate(text.splitlines(keepends=True)):
        line_start = cursor
        cursor += len(line)
        body = line.rstrip("\r\n")
        newline = line[len(body) :]

        if "|" not in body:
            _append_piece(
                output,
                start=absolute_start + line_start,
                end=absolute_start + line_start + len(body),
                text=body,
                kind="structure",
                line_index=line_index,
                cell_index=None,
            )
        else:
            local = 0
            cell_index = 0
            for match in re.finditer(r"\|", body):
                _plan_cell(
                    output,
                    body[local : match.start()],
                    absolute_start=absolute_start + line_start + local,
                    line_index=line_index,
                    cell_index=cell_index,
                )
                _append_piece(
                    output,
                    start=absolute_start + line_start + match.start(),
                    end=absolute_start + line_start + match.end(),
                    text="|",
                    kind="structure",
                    line_index=line_index,
                    cell_index=None,
                )
                local = match.end()
                cell_index += 1
            _plan_cell(
                output,
                body[local:],
                absolute_start=absolute_start + line_start + local,
                line_index=line_index,
                cell_index=cell_index,
            )

        if newline:
            _append_piece(
                output,
                start=absolute_start + line_start + len(body),
                end=absolute_start + line_start + len(line),
                text=newline,
                kind="structure",
                line_index=line_index,
                cell_index=None,
            )

    if cursor != len(text):
        raise ValueError("table piece planner lost source bytes")
    if "".join(piece.text for piece in output) != text:
        raise ValueError("table piece planner is not byte-exact")
    if output:
        if output[0].start != absolute_start:
            raise ValueError("table piece planner does not start at table source start")
        if output[-1].end != absolute_start + len(text):
            raise ValueError("table piece planner does not end at table source end")
        for left, right in zip(output, output[1:]):
            if left.end != right.start:
                raise ValueError("table piece planner produced a source gap")
    return output


def render_ascii_table(
    text: str,
    pieces: list[TablePiece],
    translations: Mapping[int, str],
) -> str:
    """Render raw-model translations into the structural table projection."""
    if "".join(piece.text for piece in pieces) != text:
        raise ValueError("table render pieces do not belong to source text")

    rendered: list[str] = []
    expected_translation_indices = {
        piece.index for piece in pieces if piece.kind == "translate"
    }
    if set(translations) != expected_translation_indices:
        missing = sorted(expected_translation_indices - set(translations))
        extra = sorted(set(translations) - expected_translation_indices)
        raise ValueError(
            f"table translation mapping mismatch: missing={missing}, extra={extra}"
        )

    for piece in pieces:
        if piece.kind == "translate":
            target = str(translations[piece.index]).strip()
            if not target:
                raise ValueError(f"empty translation for table piece {piece.index}")
            rendered.append(target)
        else:
            rendered.append(piece.text)
    return "".join(rendered)
