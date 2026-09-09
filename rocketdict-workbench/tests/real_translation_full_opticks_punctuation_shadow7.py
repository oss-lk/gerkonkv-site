from __future__ import annotations

"""Run the maintained punctuation-shadow probe with a seven-token search window.

Seven is the smallest search window that can inspect the semicolon immediately
before the six-token-backtracked split needed by the known full-Opticks
long-unit 25/30/40 content-loss parent.  This keeps the experiment narrower
than the already-green eight- and sixteen-token variants while preserving all
Product code, source bytes, target assembly and strict gates unchanged.
"""

import real_translation_full_opticks_punctuation_shadow as probe


if __name__ == "__main__":
    probe.BACKTRACK_TOKENS = 7
    raise SystemExit(probe.main())
