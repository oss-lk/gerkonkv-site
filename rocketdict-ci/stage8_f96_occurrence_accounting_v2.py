from __future__ import annotations

"""Revision 2: frozen-v5 occurrence accounting.

The candidate planner cells below are NOT selected by F96 metrics. They are the
first 20 independently ranked historical-recovery candidates from successful
run 33164205772 / artifact 9682915882. This revision skips recomputing that
expensive historical sweep and only asks how those already-frozen candidates
account at underlying fragment-occurrence level.
"""

import stage8_f96_occurrence_accounting as accounting
import stage8_f96_plan_recovery as r

SC = {
    "abbrev_mode": "scientific",
    "split_semicolon": False,
    "split_colon": True,
    "heading_as_sentence": True,
}

# (preferred, boundary_ratio, boundary_mode, historical plan_unit_count)
FROZEN_V5 = [
    (352, 0.5, "ratio", 465),
    (352, 0.5, "ratio_next", 465),
    (320, 0.8, "ratio", 466),
    (320, 0.8, "ratio_next", 466),
    (384, 0.4, "ratio", 455),
    (384, 0.4, "ratio_next", 455),
    (336, 0.6, "ratio", 471),
    (336, 0.6, "ratio_next", 471),
    (336, 0.7, "ratio", 449),
    (336, 0.7, "ratio_next", 449),
    (352, 0.6, "ratio", 449),
    (352, 0.6, "ratio_next", 449),
    (320, 0.7, "ratio", 474),
    (320, 0.7, "ratio_next", 474),
    (336, 0.8, "ratio", 440),
    (336, 0.8, "ratio_next", 440),
    (384, 0.5, "ratio", 434),
    (384, 0.5, "ratio_next", 434),
    (336, 0.5, "ratio", 489),
    (336, 0.5, "ratio_next", 489),
]


def frozen_candidate_configs(hist_text, sp):
    _, meta = r.segment(hist_text, **SC)
    if meta["sentence_count"] != 2383:
        raise RuntimeError(f"frozen v5 Stage7 identity drift: {meta}")
    rows = []
    for preferred, ratio, mode, historical_units in FROZEN_V5:
        # Score is reconstructed from the already-persisted independent v5
        # invariants, not recalculated by fitting to F96.
        score = (
            abs(meta["sentence_count"] - r.HIST_SENTENCES),
            abs(historical_units - r.HIST_STAGE12_UNITS),
            abs(meta["paragraphs_modelled"] - r.HIST_PARAGRAPHS),
        )
        rows.append((
            score,
            dict(SC),
            dict(meta),
            {"preferred": preferred, "boundary_ratio": ratio, "boundary_mode": mode},
        ))
    return rows


accounting.candidate_configs = frozen_candidate_configs
accounting.main()
