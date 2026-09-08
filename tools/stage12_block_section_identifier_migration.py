from __future__ import annotations

"""One-shot assertion-heavy migration for source-owned block section IDs.

Full contiguous Opticks planner-v7 evidence found 26 Gutenberg-style section-ID
occurrences of form ``1.X.`` / ``1.X.N.``. Exactly 21 are block headings and five
are inline references. Current Product rank0 preserves only 12/21 block IDs
exactly; dropped/Cyrillicized IDs contribute hard numeric/technical failures.

This migration promotes only the block-heading class. Immutable identifier bytes
are kept as source-owned structure and are never sent through MT or rewritten on
the target side. Inline references remain ordinary prose. Planner boundaries
therefore change and are versioned /7 -> /8.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATION = ROOT / "rocketdict-product-core/src/rocketdict/translation_stage.py"
REGISTRY = ROOT / "rocketdict-product-core/src/rocketdict/api/registry.py"
MODULE = ROOT / "rocketdict-product-core/src/rocketdict/block_section_identifiers.py"
TEST = ROOT / "rocketdict-product-core/tests/test_block_section_identifiers.py"
PLANNER_TEST = ROOT / "rocketdict-product-core/tests/test_translation_stage_block_section_identifiers.py"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def write_module() -> None:
    MODULE.write_text(r'''from __future__ import annotations

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
''', encoding="utf-8")


def write_tests() -> None:
    TEST.write_text(r'''from __future__ import annotations

from rocketdict.block_section_identifiers import (
    BLOCK_SECTION_IDENTIFIER_CONTRACT,
    detect_block_section_identifiers,
    parse_block_section_identifier_unit,
    partition_txt_base_with_block_section_identifiers,
)


def _base(content: str) -> list[dict]:
    return [{"start": 0, "end": len(content), "text": content, "metadata": {"source": "nlp_sentence"}}]


def test_detects_only_block_identifiers_when_requested() -> None:
    content = (
        "See paragraph 1.E.8.\n\n"
        "1.B. Trademark text.\n\n"
        "1.F.\n\n1.F.1. Warranty text."
    )
    all_ids = detect_block_section_identifiers(content)
    block = detect_block_section_identifiers(content, block_only=True)
    assert [row.identifier for row in all_ids] == ["1.E.8.", "1.B.", "1.F.", "1.F.1."]
    assert [row.identifier for row in block] == ["1.B.", "1.F.", "1.F.1."]


def test_partition_is_byte_exact_and_keeps_inline_reference_in_prose() -> None:
    content = (
        "See paragraph 1.E.8.\n\n"
        "1.B. Trademark text.\n\n"
        "1.F.\n\n1.F.1. Warranty text."
    )
    rows = partition_txt_base_with_block_section_identifiers(content, _base(content))
    assert "".join(row["text"] for row in rows) == content
    structural = [row for row in rows if row["metadata"].get("source") == "block_section_identifier"]
    assert [row["metadata"]["block_section_identifier"] for row in structural] == ["1.B.", "1.F.", "1.F.1."]
    assert all(row["metadata"]["block_section_identifier_contract"] == BLOCK_SECTION_IDENTIFIER_CONTRACT for row in structural)
    assert any("paragraph 1.E.8." in row["text"] for row in rows if row not in structural)
    assert not any(not row["text"].strip() and row["metadata"].get("source") != "block_section_identifier" for row in rows)


def test_parse_identifier_allows_source_owned_surrounding_whitespace() -> None:
    parsed = parse_block_section_identifier_unit("1.F.3. \n\n")
    assert parsed.identifier == "1.F.3."
    assert parsed.block_level is True
''', encoding="utf-8")

    PLANNER_TEST.write_text(r'''from __future__ import annotations

import re

from rocketdict.api.registry import (
    STAGE12_BLOCK_SECTION_IDENTIFIER_CONTRACT,
    STAGE12_PLANNER_CONTRACT,
    lab_manifest,
)
from rocketdict.block_section_identifiers import BLOCK_SECTION_IDENTIFIER_CONTRACT
from rocketdict.translation_stage import PLANNER_CONTRACT, segment_translation_units


def _tokens(content: str) -> list[dict]:
    return [
        {
            "sequence_number": index,
            "source_start": match.start(),
            "source_end": match.end(),
            "source_text": match.group(0),
            "payload": {"flags": {"is_space": False}},
        }
        for index, match in enumerate(re.finditer(r"\S+", content))
    ]


def test_planner_v8_isolates_block_ids_and_preserves_complete_source() -> None:
    content = "Lead paragraph.\n\n1.F.\n\n1.F.1. Warranty text with paragraph 1.F.3. reference."
    context = [{
        "sequence_number": 0,
        "source_start": 0,
        "source_end": len(content),
        "source_text": content,
        "payload": {"sentence_index": 0},
    }]
    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )
    assert "".join(row["text"] for row in units) == content
    structural = [row for row in units if row["metadata"].get("source") == "block_section_identifier"]
    assert [row["metadata"]["block_section_identifier"] for row in structural] == ["1.F.", "1.F.1."]
    assert any("paragraph 1.F.3. reference" in row["text"] for row in units if row not in structural)
    assert not any(not row["text"].strip() and row["metadata"].get("source") != "block_section_identifier" for row in units)


def test_registry_pins_block_identifier_and_planner_contracts() -> None:
    assert PLANNER_CONTRACT == STAGE12_PLANNER_CONTRACT == "rocketdict-stage12-protected-split/8"
    assert BLOCK_SECTION_IDENTIFIER_CONTRACT == STAGE12_BLOCK_SECTION_IDENTIFIER_CONTRACT
    manifest = lab_manifest(probe_runtime=False)
    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)
    implementation = next(row for row in stage12["implementations"] if row["implementation_key"] == "opus-en-ru-ct2")
    controls = {row["key"]: row.get("default") for row in implementation["controls"]}
    assert controls["block_section_identifier_contract"] == BLOCK_SECTION_IDENTIFIER_CONTRACT
    assert "block-section-id-aware" in implementation["tags"]
''', encoding="utf-8")


def migrate_translation() -> None:
    text = TRANSLATION.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'Planner v7 keeps evidence-backed Gutenberg block structural labels byte-exact\n',
        'Planner v8 keeps evidence-backed Gutenberg block structural labels and block\nsection identifiers byte-exact. Section identifiers are source-owned document\nstructure and never become MT requests; inline references remain ordinary prose.\nPlanner v8 also retains the v7 behavior that keeps structural labels byte-exact\n',
        label="planner doc",
    )
    text = replace_once(
        text,
        'from .runtime import OpusTranslator, load_opus_asset\n',
        'from .runtime import OpusTranslator, load_opus_asset\nfrom .block_section_identifiers import (\n    BLOCK_SECTION_IDENTIFIER_CONTRACT,\n    parse_block_section_identifier_unit,\n    partition_txt_base_with_block_section_identifiers,\n)\n',
        label="identifier imports",
    )
    text = replace_once(
        text,
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/7"\n',
        'PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"\n',
        label="planner contract",
    )
    text = replace_once(
        text,
        '            base = partition_txt_base_with_block_structural_labels(content, base)\n',
        '            base = partition_txt_base_with_block_structural_labels(content, base)\n            base = partition_txt_base_with_block_section_identifiers(content, base)\n',
        label="source partition",
    )
    text = replace_once(
        text,
        '        if metadata.get("source") == "structural_label":\n',
        '        if metadata.get("source") == "block_section_identifier":\n            result.append(\n                {\n                    **row,\n                    "metadata": {\n                        **metadata,\n                        "planner_contract": PLANNER_CONTRACT,\n                        "split": False,\n                        "token_count": len(tokens),\n                        "protected_span_count": 1,\n                        "block_section_identifier_atomic": True,\n                    },\n                }\n            )\n            continue\n\n        if metadata.get("source") == "structural_label":\n',
        label="planner structural branch",
    )
    text = replace_once(
        text,
        '    requested_structural = str(\n        effective.get("structural_label_contract") or STRUCTURAL_LABEL_CONTRACT\n    )\n',
        '    requested_block_identifier = str(\n        effective.get("block_section_identifier_contract")\n        or BLOCK_SECTION_IDENTIFIER_CONTRACT\n    )\n    if requested_block_identifier != BLOCK_SECTION_IDENTIFIER_CONTRACT:\n        raise StageExecutionError(\n            f"Unsupported Stage12 block section identifier contract {requested_block_identifier!r}; "\n            f"expected {BLOCK_SECTION_IDENTIFIER_CONTRACT!r}"\n        )\n    effective["block_section_identifier_contract"] = BLOCK_SECTION_IDENTIFIER_CONTRACT\n    requested_structural = str(\n        effective.get("structural_label_contract") or STRUCTURAL_LABEL_CONTRACT\n    )\n',
        label="parameter validation",
    )
    text = replace_once(
        text,
        '        structural_label_plans: dict[int, StructuralLabel] = {}\n',
        '        structural_label_plans: dict[int, StructuralLabel] = {}\n        block_section_identifiers: dict[int, str] = {}\n',
        label="execution plans",
    )
    text = replace_once(
        text,
        '            elif metadata.get("source") == "structural_label":\n',
        '            elif metadata.get("source") == "block_section_identifier":\n                try:\n                    identifier = parse_block_section_identifier_unit(str(unit["text"]))\n                except ValueError as exc:\n                    raise StageExecutionError(\n                        f"Stage12 block section identifier parsing failed: {exc}"\n                    ) from exc\n                if (\n                    str(metadata.get("block_section_identifier_contract") or "")\n                    != BLOCK_SECTION_IDENTIFIER_CONTRACT\n                    or str(metadata.get("block_section_identifier") or "") != identifier.identifier\n                ):\n                    raise StageExecutionError(\n                        "Stage12 block section identifier planner/execution metadata drift"\n                    )\n                block_section_identifiers[unit_index] = identifier.identifier\n            elif metadata.get("source") == "structural_label":\n',
        label="request exclusion",
    )
    text = replace_once(
        text,
        '            elif metadata.get("source") == "structural_label":\n                selection = structural_execution["selected"].get(sequence)\n',
        '            elif metadata.get("source") == "block_section_identifier":\n                identifier = block_section_identifiers.get(sequence)\n                if not identifier:\n                    raise StageExecutionError(\n                        f"Stage12 lacks block section identifier plan for unit {sequence}"\n                    )\n                target = str(unit["text"])\n                payload = {\n                    "planner": metadata,\n                    "hypotheses": [],\n                    "selected_rank": None,\n                    "block_section_identifier": {\n                        "contract": BLOCK_SECTION_IDENTIFIER_CONTRACT,\n                        "identifier": identifier,\n                        "source_owned_structure": True,\n                        "model_request": False,\n                        "target_rewriting": False,\n                        "source_bytes_rewritten": False,\n                    },\n                }\n            elif metadata.get("source") == "structural_label":\n                selection = structural_execution["selected"].get(sequence)\n',
        label="source-owned rendering",
    )
    text = replace_once(
        text,
        '            "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,\n',
        '            "block_section_identifier_contract": BLOCK_SECTION_IDENTIFIER_CONTRACT,\n            "block_section_identifier_unit_count": len(block_section_identifiers),\n            "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,\n',
        label="output provenance",
    )
    TRANSLATION.write_text(text, encoding="utf-8")


def migrate_registry() -> None:
    text = REGISTRY.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/7"\n',
        'STAGE12_PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"\n',
        label="registry planner",
    )
    text = replace_once(
        text,
        'STAGE12_STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/1"\n',
        'STAGE12_STRUCTURAL_LABEL_CONTRACT = "rocketdict-stage12-block-structural-label-opus/1"\nSTAGE12_BLOCK_SECTION_IDENTIFIER_CONTRACT = "rocketdict-stage12-block-section-identifier/1"\n',
        label="registry identifier contract",
    )
    text = replace_once(
        text,
        '"tags": ["real-mt", "offline", "opus", "ctranslate2", "structure-aware-planner", "structural-label-aware", "bounded-batch"],',
        '"tags": ["real-mt", "offline", "opus", "ctranslate2", "structure-aware-planner", "structural-label-aware", "block-section-id-aware", "bounded-batch"],',
        label="registry tags",
    )
    text = replace_once(
        text,
        '                    _control("planner_contract", STAGE12_PLANNER_CONTRACT),\n                    _control("structural_label_contract", STAGE12_STRUCTURAL_LABEL_CONTRACT),\n',
        '                    _control("planner_contract", STAGE12_PLANNER_CONTRACT),\n                    _control("block_section_identifier_contract", STAGE12_BLOCK_SECTION_IDENTIFIER_CONTRACT),\n                    _control("structural_label_contract", STAGE12_STRUCTURAL_LABEL_CONTRACT),\n',
        label="registry controls",
    )
    REGISTRY.write_text(text, encoding="utf-8")


def main() -> int:
    write_module()
    write_tests()
    migrate_translation()
    migrate_registry()
    print("Stage12 block section identifier migration applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
