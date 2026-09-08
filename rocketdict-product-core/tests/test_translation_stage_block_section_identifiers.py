from __future__ import annotations

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
