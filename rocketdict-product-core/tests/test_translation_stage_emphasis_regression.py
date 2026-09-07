from __future__ import annotations

import re

from rocketdict.translation_stage import _balanced_protected_spans, segment_translation_units


def _context(sequence: int, start: int, end: int, content: str) -> dict:
    return {
        "sequence_number": sequence,
        "source_start": start,
        "source_end": end,
        "source_text": content[start:end],
        "payload": {"sentence_index": sequence},
    }


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


def _emphasis_texts(content: str) -> list[str]:
    return [
        content[start:end]
        for start, end, kind in _balanced_protected_spans(content, absolute_start=0)
        if kind == "emphasis"
    ]


def test_unmatched_leading_close_does_not_shift_gutenberg_emphasis_pairing() -> None:
    content = (
        "Since Sir_ Isaac, _which he read of_\n"
        "Cambridge _in these_ Opticks.\n\n"
        "Transcriber's Note.\n\n_"
    )

    assert _emphasis_texts(content) == ["_which he read of_", "_in these_"]


def test_unmatched_emphasis_does_not_cross_blank_paragraph_boundary() -> None:
    content = "Prefix _unclosed text\n\nNext paragraph with _valid words_."

    assert _emphasis_texts(content) == ["_valid words_"]


def test_valid_emphasis_may_span_an_ordinary_wrapped_line() -> None:
    content = "Prefix _wrapped emphasis\ncontinues here_ suffix."

    assert _emphasis_texts(content) == ["_wrapped emphasis\ncontinues here_"]


def test_inline_symbolic_gutenberg_emphasis_remains_protected() -> None:
    content = "TQ be to ET as E_t_ to _tq_, taking _tq_ again."

    assert _emphasis_texts(content) == ["_t_", "_tq_", "_tq_"]


def test_malformed_leading_close_does_not_coalesce_next_paragraph() -> None:
    content = (
        "Since Sir_ Isaac, _which he read of_ Cambridge _in these_ Opticks.\n\n"
        "Transcriber's Note.\n\n_"
    )
    boundary = content.index("Transcriber's")
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
    assert units[0]["text"] == content[:boundary]
    assert units[1]["text"] == content[boundary:]
    assert all(
        "protected_sentence_boundary_coalesced" not in row["metadata"]
        for row in units
    )
    assert "".join(row["text"] for row in units) == content
