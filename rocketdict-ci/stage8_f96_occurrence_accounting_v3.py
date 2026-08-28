from __future__ import annotations

"""Revision 3: compute-identical fast occurrence accounting.

Uses the same frozen-v5 candidate family as v2. In the current transparent
recovery planner, ratio and ratio_next are algebraically identical because
`proposed_tokens > preferred` is already an unconditional flush condition.
Therefore each duplicated pair is evaluated once. SentencePiece counts are
memoized. No F96 metric affects candidate choice.
"""

import stage8_f96_occurrence_accounting as accounting
import stage8_f96_plan_recovery as r

SC = {
    "abbrev_mode": "scientific",
    "split_semicolon": False,
    "split_colon": True,
    "heading_as_sentence": True,
}

# Unique representatives of frozen-v5 top-20 pairs.
FROZEN_UNIQUE = [
    (352, 0.5, 465),
    (320, 0.8, 466),
    (384, 0.4, 455),
    (336, 0.6, 471),
    (336, 0.7, 449),
    (352, 0.6, 449),
    (320, 0.7, 474),
    (336, 0.8, 440),
    (384, 0.5, 434),
    (336, 0.5, 489),
]

_cache: dict[str, int] = {}
_orig_tc = accounting.tc


def cached_tc(sp, text: str) -> int:
    value = _cache.get(text)
    if value is None:
        value = _orig_tc(sp, text)
        _cache[text] = value
    return value


def frozen_candidate_configs(hist_text, sp):
    _, meta = r.segment(hist_text, **SC)
    if meta["sentence_count"] != 2383:
        raise RuntimeError(f"frozen v5 Stage7 identity drift: {meta}")
    rows = []
    for preferred, ratio, historical_units in FROZEN_UNIQUE:
        score = (
            abs(meta["sentence_count"] - r.HIST_SENTENCES),
            abs(historical_units - r.HIST_STAGE12_UNITS),
            abs(meta["paragraphs_modelled"] - r.HIST_PARAGRAPHS),
        )
        rows.append((
            score,
            dict(SC),
            dict(meta),
            {"preferred": preferred, "boundary_ratio": ratio, "boundary_mode": "ratio"},
        ))
    return rows


accounting.tc = cached_tc
accounting.candidate_configs = frozen_candidate_configs
accounting.main()
