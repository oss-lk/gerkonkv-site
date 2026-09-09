from __future__ import annotations

"""Run the full-Opticks numeric punctuation shadow with semicolon-only backtracking.

The generic seven-token major-punctuation candidate repairs one genuine
long-content-loss numeric failure but changes 42 regions and has demonstrated
semantic regressions in ordinary prose.  This wrapper keeps the smallest
numerically effective window while restricting the candidate to semicolons,
which is the source boundary that repairs the known 25/30/40 long-unit case.
It is research-only and is evaluated against the latest fail-closed Product
baseline; Product code is not modified.
"""

import real_translation_full_opticks_punctuation_shadow as probe


if __name__ == "__main__":
    probe.BACKTRACK_TOKENS = 7
    probe.MAJOR = frozenset({";"})
    probe.EXPECTED_BASELINE_RUN_ID = "34338655735"
    probe.EXPECTED_BASELINE_ARTIFACT_ID = "10099448450"
    raise SystemExit(probe.main())
