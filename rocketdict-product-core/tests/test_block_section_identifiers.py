from __future__ import annotations

from rocketdict.api.registry import (
    STAGE12_BLOCK_SECTION_IDENTIFIER_CONTRACT,
    STAGE12_PLANNER_CONTRACT,
    lab_manifest,
)
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


def test_registry_publishes_planner_v8_block_identifier_contract() -> None:
    assert STAGE12_PLANNER_CONTRACT == "rocketdict-stage12-protected-split/8"
    assert STAGE12_BLOCK_SECTION_IDENTIFIER_CONTRACT == BLOCK_SECTION_IDENTIFIER_CONTRACT
    manifest = lab_manifest(probe_runtime=False)
    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)
    implementation = next(
        row
        for row in stage12["implementations"]
        if row["implementation_key"] == "opus-en-ru-ct2"
    )
    controls = {row["key"]: row.get("default") for row in implementation["controls"]}
    assert controls["planner_contract"] == STAGE12_PLANNER_CONTRACT
    assert controls["block_section_identifier_contract"] == BLOCK_SECTION_IDENTIFIER_CONTRACT
    assert "block-section-id-aware" in implementation["tags"]
