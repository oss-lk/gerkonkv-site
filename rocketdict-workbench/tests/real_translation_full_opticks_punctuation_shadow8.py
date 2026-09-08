from __future__ import annotations

"""Run the maintained punctuation-shadow probe with an eight-token backtrack window.

This wrapper intentionally changes only the research candidate's maximum
backtrack distance. Product code, source bytes, target assembly and strict gates
remain unchanged. The underlying evidence payload records the actual policy
value, so this run remains directly comparable with the 16-token shadow.
"""

import real_translation_full_opticks_punctuation_shadow as probe


if __name__ == "__main__":
    probe.BACKTRACK_TOKENS = 8
    raise SystemExit(probe.main())
