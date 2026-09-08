from __future__ import annotations

import re

import pytest

from rocketdict.api.registry import (
    STAGE12_PLANNER_CONTRACT,
    STAGE12_STRUCTURAL_LABEL_CONTRACT,
    lab_manifest,
)
from rocketdict.stages import StageExecutionError
from rocketdict.structural_labels import (
    STRUCTURAL_LABEL_CONTRACT,
    parse_structural_label_unit,
)
from rocketdict.translation_stage import (
    PLANNER_CONTRACT,
    _translate_structural_label_units,
    segment_translation_units,
)


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


def test_planner_v5_isolates_block_label_even_when_old_context_splits_it_three_ways() -> None:
    content = "Lead paragraph.\n\n_Exper._ 11. Following prose."
    label_start = content.index("_Exper._")
    boundary1 = label_start + 4
    boundary2 = content.index(" 11.") + 1
    context = [
        _context(0, 0, boundary1, content),
        _context(1, boundary1, boundary2, content),
        _context(2, boundary2, len(content), content),
    ]

    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )

    labels = [row for row in units if row["metadata"].get("source") == "structural_label"]
    assert len(labels) == 1
    label = labels[0]
    assert label["text"] == "_Exper._ 11."
    assert label["start"] == label_start
    assert label["end"] == label_start + len("_Exper._ 11.")
    assert label["metadata"]["planner_contract"] == PLANNER_CONTRACT
    assert label["metadata"]["structural_label_contract"] == STRUCTURAL_LABEL_CONTRACT
    assert label["metadata"]["canonical_model_input"] == "Experiment 11."
    assert label["metadata"]["structural_label_atomic"] is True
    assert "".join(str(row["text"]) for row in units) == content


def test_planner_v5_leaves_inline_supported_label_on_ordinary_text_path() -> None:
    content = "Inline (_Exper._ 10. _Part_ 2.) remains ordinary prose."
    context = [_context(0, 0, len(content), content)]
    units = segment_translation_units(
        content,
        [],
        context,
        _tokens(content),
        selected_format="txt",
        preferred_tokens=64,
    )
    assert not [row for row in units if row["metadata"].get("source") == "structural_label"]
    assert "".join(str(row["text"]) for row in units) == content


class _FakeTranslator:
    def __init__(self, *, never_accept: bool = False) -> None:
        self.calls: list[tuple[tuple[str, ...], int, int]] = []
        self.never_accept = never_accept

    def translate(
        self,
        texts: list[str],
        *,
        beam_size: int,
        num_hypotheses: int,
        max_decoding_length: int,
    ) -> list[list[dict]]:
        assert max_decoding_length == 128
        self.calls.append((tuple(texts), beam_size, num_hypotheses))
        rows: list[list[dict]] = []
        for text in texts:
            if self.never_accept:
                rows.append([{"rank": 0, "text": "Неверная метка 999."}])
            elif text == "Experiment 11.":
                rows.append([{"rank": 0, "text": "Эксперимент 11."}])
            elif text == "Observation 1." and beam_size == 6:
                rows.append([{"rank": 0, "text": "Замечание 1."}])
            elif text == "Observation 1." and beam_size == 12:
                rows.append([
                    {"rank": 0, "text": "Примечание 1."},
                    {"rank": 5, "text": "Наблюдение 1."},
                ])
            else:
                raise AssertionError((text, beam_size, num_hypotheses))
        return rows


def test_structural_label_execution_escalates_only_unresolved_label() -> None:
    translator = _FakeTranslator()
    labels = {
        7: parse_structural_label_unit("_Exper._ 11."),
        9: parse_structural_label_unit("_Obs._ 1."),
    }
    result = _translate_structural_label_units(translator, labels)

    assert translator.calls == [
        (("Experiment 11.", "Observation 1."), 6, 6),
        (("Observation 1.",), 12, 12),
    ]
    assert result["request_count"] == 3
    assert result["escalated_count"] == 1
    assert result["selected"][7]["target_text"] == "Эксперимент 11."
    assert result["selected"][7]["generation"]["beam_size"] == 6
    assert result["selected"][9]["target_text"] == "Наблюдение 1."
    assert result["selected"][9]["rank"] == 5
    assert result["selected"][9]["generation"]["beam_size"] == 12


def test_structural_label_execution_fails_closed_without_raw_acceptable_candidate() -> None:
    with pytest.raises(StageExecutionError, match="no acceptable structural-label"):
        _translate_structural_label_units(
            _FakeTranslator(never_accept=True),
            {3: parse_structural_label_unit("_Exper._ 11.")},
        )


def test_registry_publishes_planner_v5_and_structural_label_contract() -> None:
    assert PLANNER_CONTRACT == "rocketdict-stage12-protected-split/5"
    assert STAGE12_PLANNER_CONTRACT == PLANNER_CONTRACT
    assert STAGE12_STRUCTURAL_LABEL_CONTRACT == STRUCTURAL_LABEL_CONTRACT
    manifest = lab_manifest(probe_runtime=False)
    stage12 = next(row for row in manifest["stages"] if int(row["number"]) == 12)
    implementation = next(
        row
        for row in stage12["implementations"]
        if row["implementation_key"] == "opus-en-ru-ct2"
    )
    controls = {row["key"]: row.get("default") for row in implementation["controls"]}
    assert controls["planner_contract"] == PLANNER_CONTRACT
    assert controls["structural_label_contract"] == STRUCTURAL_LABEL_CONTRACT
    assert "structural-label-aware" in implementation["tags"]
