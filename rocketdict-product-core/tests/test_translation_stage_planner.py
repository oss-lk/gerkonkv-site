from __future__ import annotations

import re

from rocketdict.api.registry import STAGE12_PLANNER_CONTRACT, lab_manifest
from rocketdict.translation_stage import PLANNER_CONTRACT, segment_translation_units


def _context(sequence: int, start: int, end: int, content: str) -> dict:
    return {
        "sequence_number": sequence,
        "source_start": start,
        "source_end": end,
        "source_text": content[start:end],
        "payload": {"sentence_index": sequence},
    }


def _tokens(content: str) -> list[dict]:
    rows = []
    for index, match in enumerate(re.finditer(r"\S+", content)):
        rows.append(
            {
                "sequence_number": index,
                "source_start": match.start(),
                "source_end": match.end(),
                "source_text": match.group(0),
                "payload": {"flags": {"is_space": False}},
            }
        )
    return rows


def test_registry_identity_pins_current_planner_contract() -> None:
    assert STAGE12_PLANNER_CONTRACT == PLANNER_CONTRACT
    manifest = lab_manifest(probe_runtime=False)
    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)
    implementation = next(
        row
        for row in stage12["implementations"]
        if row["implementation_key"] == "opus-en-ru-ct2"
    )
    controls = {row["key"]: row.get("default") for row in implementation["controls"]}
    assert controls["planner_contract"] == PLANNER_CONTRACT
    assert "structure-aware-planner" in implementation["tags"]


def test_txt_coalesces_nlp_sentence_boundary_inside_square_span() -> None:
    content = "[Illustration: FIG. 10.]\n\nNext sentence."
    first_end = len("[Illustration: FIG. ")
    second_end = len("[Illustration: FIG. 10.]\n\n")
    context = [
        _context(0, 0, first_end, content),
        _context(1, first_end, second_end, content),
        _context(2, second_end, len(content), content),
    ]

    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )

    assert [row["text"] for row in units] == [
        "[Illustration: FIG. 10.]\n\n",
        "Next sentence.",
    ]
    first = units[0]["metadata"]
    assert first["source"] == "nlp_sentence_group"
    assert first["context_sentence_count"] == 2
    assert first["protected_sentence_boundary_coalesced"] is True
    assert first["planner_contract"] == PLANNER_CONTRACT


def test_txt_coalesces_sentence_boundary_inside_round_span() -> None:
    content = "Prefix (Boyle. citation) continues. Tail."
    first_end = content.index("citation")
    second_end = content.index(" Tail.") + 1
    context = [
        _context(0, 0, first_end, content),
        _context(1, first_end, second_end, content),
        _context(2, second_end, len(content), content),
    ]

    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )

    assert len(units) == 2
    assert units[0]["text"] == content[:second_end]
    assert units[0]["text"].count("(") == units[0]["text"].count(")") == 1
    assert units[0]["metadata"]["context_sentence_count"] == 2


def test_token_budget_cut_is_deferred_past_balanced_protected_span() -> None:
    content = "one two [Greek: alpha beta gamma] four five six seven"
    context = [_context(0, 0, len(content), content)]

    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=4,
    )

    assert len(units) >= 2
    assert units[0]["metadata"]["protected_split_deferred"] is True
    assert units[0]["text"].count("[") == units[0]["text"].count("]") == 1
    assert "[Greek: alpha beta gamma]" in units[0]["text"]
    assert "".join(row["text"] for row in units) == content


def test_unmatched_source_delimiter_is_not_synthetically_coalesced() -> None:
    content = "[Broken sentence. Next sentence."
    boundary = len("[Broken sentence. ")
    context = [
        _context(0, 0, boundary, content),
        _context(1, boundary, len(content), content),
    ]

    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )

    assert len(units) == 2
    assert units[0]["text"] == "[Broken sentence. "
    assert units[0]["metadata"]["source"] == "nlp_sentence"
    assert "protected_sentence_boundary_coalesced" not in units[0]["metadata"]
    assert "".join(row["text"] for row in units) == content


def test_subtitle_segments_keep_cue_boundaries() -> None:
    content = "[Greek: x]"
    document_segments = [
        {
            "sequence_number": 0,
            "start_char": 0,
            "end_char": 8,
            "text": content[:8],
            "start_ms": 0,
            "end_ms": 1000,
        },
        {
            "sequence_number": 1,
            "start_char": 8,
            "end_char": len(content),
            "text": content[8:],
            "start_ms": 1000,
            "end_ms": 2000,
        },
    ]

    units = segment_translation_units(
        content,
        document_segments,
        [],
        _tokens(content),
        selected_format="srt",
        preferred_tokens=64,
    )

    assert [row["text"] for row in units] == [content[:8], content[8:]]
    assert all(row["metadata"]["source"] == "subtitle_segment" for row in units)
