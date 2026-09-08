from __future__ import annotations

"""Source-owned block section identifiers for maintained Stage12.

The contract recognizes only paragraph/block-start identifiers of the narrow
form ``1.A.`` or ``1.F.3.``. Inline references such as ``paragraph 1.F.3`` stay
ordinary prose. The identifier is document structure, not linguistic content:
its immutable source bytes are preserved exactly and are not sent to OPUS.
"""

from dataclasses import dataclass
import re
from typing import Any, Sequence

BLOCK_SECTION_IDENTIFIER_CONTRACT = "rocketdict-stage12-block-section-identifier/1"

_IDENTIFIER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<identifier>\d+\.[A-Z]\.(?:\d+\.)?)(?![A-Za-z0-9])"
)


@dataclass(frozen=True)
class BlockSectionIdentifier:
    source_start: int
    source_end: int
    source_text: str
    identifier: str
    block_level: bool


def _is_block_start(text: str, offset: int) -> bool:
    if offset == 0:
        return True
    prefix = text[:offset]
    return bool(re.search(r"(?:\r?\n)[ \t]*(?:\r?\n)[ \t]*\Z", prefix))


def detect_block_section_identifiers(
    text: str, *, absolute_start: int = 0, block_only: bool = False
) -> list[BlockSectionIdentifier]:
    result: list[BlockSectionIdentifier] = []
    for match in _IDENTIFIER_RE.finditer(text):
        block = _is_block_start(text, match.start())
        if block_only and not block:
            continue
        result.append(
            BlockSectionIdentifier(
                source_start=absolute_start + match.start(),
                source_end=absolute_start + match.end(),
                source_text=match.group("identifier"),
                identifier=match.group("identifier"),
                block_level=block,
            )
        )
    return result


def parse_block_section_identifier_unit(source_text: str) -> BlockSectionIdentifier:
    stripped = source_text.strip()
    match = _IDENTIFIER_RE.fullmatch(stripped)
    if match is None:
        raise ValueError("block section identifier unit contains non-identifier content")
    value = match.group("identifier")
    return BlockSectionIdentifier(
        source_start=0,
        source_end=len(source_text),
        source_text=value,
        identifier=value,
        block_level=True,
    )


def _slice_rows(
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
            if metadata.get("source") in {
                "ascii_table",
                "structural_label",
                "block_section_identifier",
            }:
                raise ValueError("block section identifier overlaps another source-owned structure")
            metadata["source_before_block_section_identifier_split"] = metadata.get("source")
            metadata["source"] = "nlp_sentence_fragment"
            metadata["block_section_identifier_boundary_split"] = True
        output.append(
            {
                "start": left,
                "end": right,
                "text": content[left:right],
                "metadata": metadata,
            }
        )
    if output and "".join(str(row["text"]) for row in output) != content[start:end]:
        raise ValueError("block section identifier slicing is not byte-exact")
    return output


def _merge_whitespace(
    content: str, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Remove split-created whitespace-only ordinary requests without data loss.

    Prefer attaching whitespace following an identifier to that identifier; it
    is source-owned layout and can be preserved byte-for-byte with the ID.
    Otherwise attach it to adjacent ordinary prose. Never extend tables or the
    OPUS-translated structural-label contract.
    """
    rows = [{**row, "metadata": dict(row.get("metadata") or {})} for row in rows]
    index = 0
    while index < len(rows):
        row = rows[index]
        metadata = dict(row.get("metadata") or {})
        if str(row.get("text") or "").strip() or metadata.get("source") == "block_section_identifier":
            index += 1
            continue
        if not metadata.get("block_section_identifier_boundary_split"):
            index += 1
            continue

        if index > 0 and (rows[index - 1].get("metadata") or {}).get("source") == "block_section_identifier":
            previous = rows[index - 1]
            previous_meta = dict(previous.get("metadata") or {})
            previous_meta["block_section_identifier_trailing_whitespace_preserved"] = True
            merged = {
                **previous,
                "end": int(row["end"]),
                "text": content[int(previous["start"]):int(row["end"])],
                "metadata": previous_meta,
            }
            rows[index - 1] = merged
            rows.pop(index)
            continue

        if index + 1 < len(rows):
            neighbor = rows[index + 1]
            neighbor_meta = dict(neighbor.get("metadata") or {})
            if neighbor_meta.get("source") not in {"ascii_table", "structural_label"}:
                neighbor_meta["block_section_identifier_boundary_whitespace_coalesced"] = True
                rows[index + 1] = {
                    **neighbor,
                    "start": int(row["start"]),
                    "text": content[int(row["start"]):int(neighbor["end"])],
                    "metadata": neighbor_meta,
                }
                rows.pop(index)
                continue

        if index > 0:
            neighbor = rows[index - 1]
            neighbor_meta = dict(neighbor.get("metadata") or {})
            if neighbor_meta.get("source") not in {"ascii_table", "structural_label"}:
                neighbor_meta["block_section_identifier_boundary_whitespace_coalesced"] = True
                rows[index - 1] = {
                    **neighbor,
                    "end": int(row["end"]),
                    "text": content[int(neighbor["start"]):int(row["end"])],
                    "metadata": neighbor_meta,
                }
                rows.pop(index)
                index = max(0, index - 1)
                continue

        raise ValueError("block section identifier split left an unrepresentable whitespace-only gap")
    return rows


def partition_txt_base_with_block_section_identifiers(
    content: str, base: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Isolate supported block IDs while leaving inline references untouched."""
    if not base:
        return []
    scope_start = int(base[0]["start"])
    scope_end = int(base[-1]["end"])
    if scope_end <= scope_start:
        raise ValueError("Stage12 block-section base scope is empty")
    if "".join(str(row["text"]) for row in base) != content[scope_start:scope_end]:
        raise ValueError("Stage12 block-section input base is not contiguous")

    identifiers = [
        item
        for item in detect_block_section_identifiers(content, block_only=True)
        if item.source_end > scope_start and item.source_start < scope_end
    ]
    for item in identifiers:
        if item.source_start < scope_start or item.source_end > scope_end:
            raise ValueError("block section identifier crosses Stage12 TXT scope")
        for row in base:
            row_meta = dict(row.get("metadata") or {})
            if row_meta.get("source") not in {"ascii_table", "structural_label"}:
                continue
            if item.source_start < int(row["end"]) and item.source_end > int(row["start"]):
                raise ValueError("block section identifier overlaps another source-owned structure")

    output: list[dict[str, Any]] = []
    cursor = scope_start
    for identifier_index, item in enumerate(identifiers):
        if item.source_start < cursor:
            raise ValueError("block section identifiers overlap")
        output.extend(_slice_rows(content, base, start=cursor, end=item.source_start))
        output.append(
            {
                "start": int(item.source_start),
                "end": int(item.source_end),
                "text": content[item.source_start:item.source_end],
                "metadata": {
                    "source": "block_section_identifier",
                    "block_section_identifier_index": identifier_index,
                    "block_section_identifier_contract": BLOCK_SECTION_IDENTIFIER_CONTRACT,
                    "block_section_identifier": item.identifier,
                    "block_section_identifier_core_start": int(item.source_start),
                    "block_section_identifier_core_end": int(item.source_end),
                },
            }
        )
        cursor = int(item.source_end)
    output.extend(_slice_rows(content, base, start=cursor, end=scope_end))
    output = _merge_whitespace(content, output)

    if not output:
        raise ValueError("Stage12 block-section partition produced no source units")
    if "".join(str(row["text"]) for row in output) != content[scope_start:scope_end]:
        raise ValueError("Stage12 block-section partition is not byte-exact")
    for left, right in zip(output, output[1:]):
        if int(left["end"]) != int(right["start"]):
            raise ValueError("Stage12 block-section partition produced a source gap")
    return output
