from __future__ import annotations

from rocketdict.translation_citation_rescue_stage import (
    CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
    CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
    CITATION_BOUNDARY_PAIR_SELECTED_PHASE,
    _base_parameters,
    _candidate_row,
    evaluate_citation_pair_candidate,
    evaluate_citation_pair_trigger,
)


def _row(
    *,
    row_id: int,
    start: int,
    source: str,
    target: str,
    planner_source: str = "nlp_sentence",
) -> dict:
    return {
        "id": row_id,
        "source_start": start,
        "source_end": start + len(source),
        "source_text": source,
        "target_text": target,
        "payload": {
            "planner": {
                "source": planner_source,
                "planner_contract": "rocketdict-stage12-protected-split/8",
            }
        },
    }


def test_base_parameters_strip_only_citation_controls() -> None:
    parameters = {
        "beam_size": 6,
        "enable_length_failure_whole_context_rescue": True,
        "length_failure_whole_context_rescue_max_nlp_tokens": 160,
        "enable_citation_boundary_pair_rescue": True,
        "citation_boundary_pair_rescue_contract": CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT,
        "citation_boundary_pair_rescue_selector_contract": CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT,
        "citation_boundary_pair_rescue_phase": CITATION_BOUNDARY_PAIR_SELECTED_PHASE,
        "citation_boundary_pair_rescue_max_source_chars": 256,
    }

    assert _base_parameters(parameters) == {
        "beam_size": 6,
        "enable_length_failure_whole_context_rescue": True,
        "length_failure_whole_context_rescue_max_nlp_tokens": 160,
    }


def test_trigger_accepts_bare_roman_length_failure_after_sect() -> None:
    previous = _row(
        row_id=10,
        start=100,
        source="Part I. Sect. ",
        target="Часть I.",
    )
    current = _row(
        row_id=11,
        start=previous["source_end"],
        source="II. ",
        target="II. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ",
    )

    trigger = evaluate_citation_pair_trigger(previous, current, max_source_chars=256)

    assert trigger["eligible"] is True
    assert trigger["contiguous"] is True
    assert trigger["ordinary"] is True
    assert trigger["roman_fragment"] is True
    assert trigger["citation_prefix"] is True
    assert trigger["current_length_failure"] is True


def test_trigger_rejects_heading_like_roman_without_sect_prefix() -> None:
    previous = _row(
        row_id=20,
        start=0,
        source="BOOK FIRST. ",
        target="КНИГА ПЕРВАЯ. ",
    )
    current = _row(
        row_id=21,
        start=previous["source_end"],
        source="IV. ",
        target="IV. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ",
    )

    trigger = evaluate_citation_pair_trigger(previous, current, max_source_chars=256)

    assert trigger["eligible"] is False
    assert trigger["citation_prefix"] is False


def test_trigger_rejects_source_owned_structure_even_when_text_matches() -> None:
    previous = _row(
        row_id=30,
        start=0,
        source="Sect. ",
        target="Раздел ",
        planner_source="structural_label",
    )
    current = _row(
        row_id=31,
        start=previous["source_end"],
        source="IV. ",
        target="IV. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ",
    )

    trigger = evaluate_citation_pair_trigger(previous, current, max_source_chars=256)

    assert trigger["eligible"] is False
    assert trigger["ordinary"] is False


def test_selector_accepts_strict_clean_pair_candidate() -> None:
    previous = _row(
        row_id=40,
        start=0,
        source="Part I. Sect. ",
        target="Часть I.",
    )
    current = _row(
        row_id=41,
        start=previous["source_end"],
        source="II. ",
        target="II. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ",
    )

    selection = evaluate_citation_pair_candidate(
        previous,
        current,
        source="Part I. Sect. II. ",
        target="Раздел II части I.",
    )

    assert selection["accepted"] is True
    assert selection["candidate_verdict"]["product_hard_passed"] is True
    assert selection["candidate_verdict"]["strict_research_passed"] is True
    assert selection["new_strict_debt"] == []


def test_selector_allows_inherited_strict_debt_but_no_new_category() -> None:
    previous = _row(
        row_id=50,
        start=0,
        source="[A] Part I. Sect. ",
        target="[А] Часть I.",
    )
    current = _row(
        row_id=51,
        start=previous["source_end"],
        source="IV. ",
        target="IV. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ",
    )

    selection = evaluate_citation_pair_candidate(
        previous,
        current,
        source="[A] Part I. Sect. IV. ",
        target="[А] Раздел IV части I.",
    )

    assert selection["accepted"] is True
    assert "critical:footnote_markers" in selection["primary_strict_debt"]
    assert selection["candidate_strict_debt"] == ["critical:footnote_markers"]
    assert selection["new_strict_debt"] == []
    assert selection["strict_debt_non_worsening"] is True


def test_selector_rejects_new_product_hard_debt() -> None:
    previous = _row(
        row_id=60,
        start=0,
        source="Part I. Sect. ",
        target="Часть I.",
    )
    current = _row(
        row_id=61,
        start=previous["source_end"],
        source="II. ",
        target="II. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ",
    )

    selection = evaluate_citation_pair_candidate(
        previous,
        current,
        source="Part I. Sect. II. ",
        target="",
    )

    assert selection["accepted"] is False
    assert selection["candidate_verdict"]["product_hard_passed"] is False


def test_candidate_row_keeps_raw_rank0_and_pair_provenance() -> None:
    previous = _row(
        row_id=70,
        start=100,
        source="Part I. Sect. ",
        target="Часть I.",
    )
    current = _row(
        row_id=71,
        start=previous["source_end"],
        source="II. ",
        target="II. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ",
    )
    source = previous["source_text"] + current["source_text"]
    target = "Раздел II части I."
    trigger = evaluate_citation_pair_trigger(previous, current, max_source_chars=256)
    selection = evaluate_citation_pair_candidate(
        previous,
        current,
        source=source,
        target=target,
    )

    row = _candidate_row(
        previous=previous,
        current=current,
        source=source,
        hypotheses=[{"text": target, "score": -1.0, "rank": 0}],
        trigger=trigger,
        selection=selection,
        generation={"beam_size": 6, "num_hypotheses": 1},
        max_source_chars=256,
    )

    assert row["source_text"] == source
    assert row["target_text"] == target
    assert row["source_start"] == previous["source_start"]
    assert row["source_end"] == current["source_end"]
    assert row["payload"]["selected_rank"] == 0
    rescue = row["payload"]["citation_boundary_pair_rescue"]
    assert rescue["contract"] == CITATION_BOUNDARY_PAIR_RESCUE_CONTRACT
    assert rescue["selector_contract"] == CITATION_BOUNDARY_PAIR_SELECTOR_CONTRACT
    assert rescue["base_translation_segment_ids"] == [70, 71]
    assert rescue["raw_model_rank0"] is True
    assert rescue["strict_debt_non_worsening"] is True
    assert rescue["source_bytes_rewritten"] is False
    assert rescue["target_rewriting"] is False
    assert rescue["placeholders"] is False
    assert rescue["post_translation_literal_injection"] is False
