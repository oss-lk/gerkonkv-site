from __future__ import annotations

"""Run the maintained punctuation-shadow probe with a six-token search window.

This is retained as negative boundary evidence.  The full-Opticks run proved
that a six-token punctuation-index search window does *not* reach the known
long-unit semicolon: the desired split must move six token positions, which
requires inspecting the punctuation token one position before that split.
Consequently this variant leaves the 25/30/40 content-loss failure unresolved.
Product code and strict gates remain unchanged.
"""

import real_translation_full_opticks_punctuation_shadow as probe


if __name__ == "__main__":
    probe.BACKTRACK_TOKENS = 6
    raise SystemExit(probe.main())
