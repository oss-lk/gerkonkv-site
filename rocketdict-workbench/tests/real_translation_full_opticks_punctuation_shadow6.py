from __future__ import annotations

"""Run the maintained punctuation-shadow probe with a six-token backtrack window.

The known full-Opticks long-unit content-loss parent needs exactly a six-token
backtrack to reach its preceding semicolon.  This wrapper tests that smallest
window capable of addressing the observed class while minimizing unrelated
planner boundary changes.  Product code and strict gates remain unchanged.
"""

import real_translation_full_opticks_punctuation_shadow as probe


if __name__ == "__main__":
    probe.BACKTRACK_TOKENS = 6
    raise SystemExit(probe.main())
