from __future__ import annotations

"""Evidence-backed legacy Gutenberg block headings for maintained Stage12.

Newton's *Opticks* contains block headings such as ``DEFIN. II.``, ``AX. IV.``,
``_PROP._ IV. PROB. I.`` and ``_PROP._ VII. THEOR. VI.``.  spaCy may split
these headings across sentence boundaries, so treating each fragment as ordinary
prose creates model hallucinations and truncated heading/title regions.

The contract is source-derived and raw-model only.  The immutable source heading
is detected on the complete document and isolated byte-exactly.  A separate
model input expands only the documented English abbreviations.  The selected
Russian target must be an unmodified OPUS hypothesis with the same Roman
identifiers in the same order and one of the full-corpus forms proven by the
pinned Opticks feasibility DOE.
"""

from dataclasses import dataclass
import re
from typing import Any, Sequence


LEGACY_BLOCK_HEADING_CONTRACT = "rocketdict-stage12-legacy-block-heading-opus/1"
LEGACY_BLOCK_HEADING_GENERATION_CELLS: tuple[tuple[int, int], ...] = (
    (6, 6),
    (12, 12),
)

_ROMAN = r"[IVXLCDM]+"
_HEADING_RE = re.compile(
    rf"(?:"
    rf"(?P<definition>DEFIN\.\s+(?P<definition_id>{_ROMAN})\.)"
    rf"|(?P<axiom>AX\.\s+(?P<axiom_id>{_ROMAN})\.)"
    rf"|(?P<prop_problem>_PROP\._\s+(?P<prop_problem_id>{_ROMAN})\.\s+PROB\.\s+(?P<problem_id>{_ROMAN})\.)"
    rf"|(?P<prop_theorem>_PROP\._\s+(?P<prop_theorem_id>{_ROMAN})\.\s+THEOR\.\s+(?P<theorem_id>{_ROMAN})\.)"
    rf"|(?P<proposition>PROP\.\s+(?P<proposition_id>{_ROMAN})\.)"
    rf")",
    flags=re.IGNORECASE,
)
_TARGET_ROMAN_RE = re.compile(
    r"(?<![A-Za-zА-Яа-яЁё])[IVXLCDM]+(?![A-Za-zА-Яа-яЁё])",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class LegacyBlockHeading:
    source_start: int
    source_end: int
    source_text: str
    family: str
    roman_identifiers: tuple[str, ...]
    canonical_model_input: str
    block_level: bool


def _is_block_start(text: str, offset: int) -> bool:
    if offset == 0:
        return True
    return bool(re.search(r"(?:\r?\n)[ \t]*(?:\r?\n)[ \t]*\Z", text[:offset]))


def _from_match(
    match: re.Match[str], *, absolute_start: int = 0, block_level: bool
) -> LegacyBlockHeading:
    if match.group("definition") is not None:
        identifiers = (str(match.group("definition_id")).upper(),)
        family = "definition"
        canonical = f"Definition {identifiers[0]}."
    elif match.group("axiom") is not None:
        identifiers = (str(match.group("axiom_id")).upper(),)
        family = "axiom"
        canonical = f"Axiom {identifiers[0]}."
    elif match.group("prop_problem") is not None:
        identifiers = (
            str(match.group("prop_problem_id")).upper(),
            str(match.group("problem_id")).upper(),
        )
        family = "proposition_problem"
        canonical = f"Proposition {identifiers[0]}. Problem {identifiers[1]}."
    elif match.group("prop_theorem") is not None:
        identifiers = (
            str(match.group("prop_theorem_id")).upper(),
            str(match.group("theorem_id")).upper(),
        )
        family = "proposition_theorem"
        canonical = f"Proposition {identifiers[0]}. Theorem {identifiers[1]}."
    elif match.group("proposition") is not None:
        identifiers = (str(match.group("proposition_id")).upper(),)
        family = "proposition"
        canonical = f"Proposition {identifiers[0]}."
    else:  # pragma: no cover - regular expression exhaustiveness guard
        raise ValueError("unsupported legacy block heading family")
    return LegacyBlockHeading(
        source_start=absolute_start + match.start(),
        source_end=absolute_start + match.end(),
        source_text=match.group(0),
        family=family,
        roman_identifiers=identifiers,
        canonical_model_input=canonical,
        block_level=block_level,
    )


def detect_legacy_block_headings(
    text: str, *, absolute_start: int = 0, block_only: bool = False
) -> list[LegacyBlockHeading]:
    output: list[LegacyBlockHeading] = []
    for match in _HEADING_RE.finditer(text):
        block_level = _is_block_start(text, match.start())
        if block_only and not block_level:
            continue
        output.append(
            _from_match(
                match,
                absolute_start=absolute_start,
                block_level=block_level,
            )
        )
    return output


def parse_legacy_block_heading_unit(source_text: str) -> LegacyBlockHeading:
    stripped = source_text.strip()
    match = _HEADING_RE.fullmatch(stripped)
    if match is None:
        raise ValueError("legacy block heading unit contains non-heading content")
    parsed = _from_match(match, block_level=True)
    return LegacyBlockHeading(
        source_start=0,
        source_end=len(source_text),
        source_text=parsed.source_text,
        family=parsed.family,
        roman_identifiers=parsed.roman_identifiers,
        canonical_model_input=parsed.canonical_model_input,
        block_level=True,
    )


def _strict_target_form(heading: LegacyBlockHeading, target: str) -> bool:
    identifiers = heading.roman_identifiers
    if heading.family == "definition":
        patterns = (rf"Определение\s+{re.escape(identifiers[0])}\.",)
    elif heading.family == "axiom":
        patterns = (rf"Аксиома\s+{re.escape(identifiers[0])}\.",)
    elif heading.family == "proposition":
        patterns = (rf"Предложение\s+{re.escape(identifiers[0])}\.",)
    elif heading.family == "proposition_theorem":
        patterns = (
            rf"Предложение\s+{re.escape(identifiers[0])}\.\s+"
            rf"Теорема\s+{re.escape(identifiers[1])}\.",
        )
    elif heading.family == "proposition_problem":
        patterns = (
            rf"Предложение\s+{re.escape(identifiers[0])}\.\s+"
            rf"Задача\s+{re.escape(identifiers[1])}\.",
            rf"Предложение\s+{re.escape(identifiers[0])}\.\s+"
            rf"Проблема\s+{re.escape(identifiers[1])}\.",
        )
    else:  # pragma: no cover - dataclass construction guard
        return False
    return any(
        re.fullmatch(pattern, target.strip(), flags=re.IGNORECASE) is not None
        for pattern in patterns
    )


def evaluate_legacy_block_heading_hypotheses(
    heading: LegacyBlockHeading,
    hypotheses: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    expected_identifiers = list(heading.roman_identifiers)
    for model_index, hypothesis in enumerate(hypotheses):
        target = str(hypothesis.get("text") or "").strip()
        identifiers = [value.upper() for value in _TARGET_ROMAN_RE.findall(target)]
        strict_target = _strict_target_form(heading, target)
        roman_preserved = identifiers == expected_identifiers
        candidate = {
            "model_index": model_index,
            "rank": int(
                hypothesis.get("rank")
                if hypothesis.get("rank") is not None
                else model_index
            ),
            "score": hypothesis.get("score"),
            "target_text": target,
            "roman_identifiers_expected": expected_identifiers,
            "roman_identifiers_target": identifiers,
            "roman_identifiers_preserved": roman_preserved,
            "strict_target_form": strict_target,
            "acceptable": bool(strict_target and roman_preserved),
        }
        candidates.append(candidate)
        if selected is None and candidate["acceptable"]:
            selected = candidate
    return {
        "contract": LEGACY_BLOCK_HEADING_CONTRACT,
        "source_text": heading.source_text,
        "family": heading.family,
        "roman_identifiers": expected_identifiers,
        "canonical_model_input": heading.canonical_model_input,
        "selected": selected,
        "candidates": candidates,
    }


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
                "legacy_block_heading",
            }:
                raise ValueError("legacy block heading overlaps source-owned structure")
            metadata["source_before_legacy_block_heading_split"] = metadata.get("source")
            metadata["source"] = "nlp_sentence_fragment"
            metadata["legacy_block_heading_boundary_split"] = True
        output.append(
            {
                "start": left,
                "end": right,
                "text": content[left:right],
                "metadata": metadata,
            }
        )
    if output and "".join(str(row["text"]) for row in output) != content[start:end]:
        raise ValueError("legacy block heading slicing is not byte-exact")
    return output


def _merge_boundary_whitespace(
    content: str, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = [{**row, "metadata": dict(row.get("metadata") or {})} for row in rows]
    index = 0
    while index < len(rows):
        row = rows[index]
        metadata = dict(row.get("metadata") or {})
        if str(row.get("text") or "").strip() or metadata.get("source") == "legacy_block_heading":
            index += 1
            continue
        if not metadata.get("legacy_block_heading_boundary_split"):
            index += 1
            continue

        # Whitespace following a heading is source layout. Preserve it with the
        # heading so it never becomes an empty model request.
        if index > 0 and (rows[index - 1].get("metadata") or {}).get("source") == "legacy_block_heading":
            previous = rows[index - 1]
            previous_meta = dict(previous.get("metadata") or {})
            previous_meta["legacy_block_heading_trailing_whitespace_preserved"] = True
            rows[index - 1] = {
                **previous,
                "end": int(row["end"]),
                "text": content[int(previous["start"]):int(row["end"])],
                "metadata": previous_meta,
            }
            rows.pop(index)
            continue

        if index + 1 < len(rows):
            neighbor = rows[index + 1]
            neighbor_meta = dict(neighbor.get("metadata") or {})
            if neighbor_meta.get("source") not in {
                "ascii_table",
                "structural_label",
                "block_section_identifier",
            }:
                neighbor_meta["legacy_block_heading_boundary_whitespace_coalesced"] = True
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
            if neighbor_meta.get("source") not in {
                "ascii_table",
                "structural_label",
                "block_section_identifier",
            }:
                neighbor_meta["legacy_block_heading_boundary_whitespace_coalesced"] = True
                rows[index - 1] = {
                    **neighbor,
                    "end": int(row["end"]),
                    "text": content[int(neighbor["start"]):int(row["end"])],
                    "metadata": neighbor_meta,
                }
                rows.pop(index)
                index = max(0, index - 1)
                continue

        raise ValueError("legacy block heading split left an unrepresentable whitespace-only gap")
    return rows


def partition_txt_base_with_legacy_block_headings(
    content: str, base: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Isolate supported legacy block headings across NLP sentence boundaries."""
    if not base:
        return []
    scope_start = int(base[0]["start"])
    scope_end = int(base[-1]["end"])
    if scope_end <= scope_start:
        raise ValueError("legacy block heading base scope is empty")
    if "".join(str(row["text"]) for row in base) != content[scope_start:scope_end]:
        raise ValueError("legacy block heading input base is not contiguous")

    headings = [
        heading
        for heading in detect_legacy_block_headings(content, block_only=True)
        if heading.source_end > scope_start and heading.source_start < scope_end
    ]
    for heading in headings:
        if heading.source_start < scope_start or heading.source_end > scope_end:
            raise ValueError("legacy block heading crosses Stage12 TXT scope")
        for row in base:
            metadata = dict(row.get("metadata") or {})
            if metadata.get("source") not in {
                "ascii_table",
                "structural_label",
                "block_section_identifier",
            }:
                continue
            if heading.source_start < int(row["end"]) and heading.source_end > int(row["start"]):
                raise ValueError("legacy block heading overlaps another source-owned structure")

    output: list[dict[str, Any]] = []
    cursor = scope_start
    for heading_index, heading in enumerate(headings):
        if heading.source_start < cursor:
            raise ValueError("legacy block headings overlap")
        output.extend(_slice_rows(content, base, start=cursor, end=heading.source_start))
        overlapping = [
            row
            for row in base
            if heading.source_start < int(row["end"])
            and heading.source_end > int(row["start"])
        ]
        context_starts = [
            int((row.get("metadata") or {}).get("context_sentence_start"))
            for row in overlapping
            if (row.get("metadata") or {}).get("context_sentence_start") is not None
        ]
        context_ends = [
            int((row.get("metadata") or {}).get("context_sentence_end"))
            for row in overlapping
            if (row.get("metadata") or {}).get("context_sentence_end") is not None
        ]
        metadata: dict[str, Any] = {
            "source": "legacy_block_heading",
            "legacy_block_heading_index": heading_index,
            "legacy_block_heading_contract": LEGACY_BLOCK_HEADING_CONTRACT,
            "legacy_block_heading_family": heading.family,
            "legacy_block_heading_roman_identifiers": list(heading.roman_identifiers),
            "canonical_model_input": heading.canonical_model_input,
        }
        if context_starts and context_ends:
            metadata["context_sentence_start"] = min(context_starts)
            metadata["context_sentence_end"] = max(context_ends)
            metadata["context_sentence_count"] = (
                metadata["context_sentence_end"] - metadata["context_sentence_start"] + 1
            )
        output.append(
            {
                "start": int(heading.source_start),
                "end": int(heading.source_end),
                "text": content[heading.source_start:heading.source_end],
                "metadata": metadata,
            }
        )
        cursor = int(heading.source_end)
    output.extend(_slice_rows(content, base, start=cursor, end=scope_end))
    output = _merge_boundary_whitespace(content, output)

    if not output:
        raise ValueError("legacy block heading partition produced no source units")
    if "".join(str(row["text"]) for row in output) != content[scope_start:scope_end]:
        raise ValueError("legacy block heading partition is not byte-exact")
    for left, right in zip(output, output[1:]):
        if int(left["end"]) != int(right["start"]):
            raise ValueError("legacy block heading partition produced a source gap")
    return output
