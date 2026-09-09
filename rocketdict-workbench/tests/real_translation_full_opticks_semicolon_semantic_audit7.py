from __future__ import annotations

"""Run complete changed-region semantic audit for semicolon-only backtracking."""

import real_translation_full_opticks_punctuation_semantic_audit as probe


if __name__ == "__main__":
    probe.BACKTRACK_TOKENS = 7
    probe.MAJOR = frozenset({";"})
    raise SystemExit(probe.main())
