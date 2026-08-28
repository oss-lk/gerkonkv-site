from __future__ import annotations

"""Revision 2: exact historical 90k byte-boundary recovery.

The original metadata stores both the excerpt byte length and SHA.  Run-1
proved that trimming immediately after token 90,000 is one byte too short, so
this revision binds the excerpt to the stronger historical byte+SHA evidence
and independently verifies that the prefix contains exactly 90,000 non-space
tokens before invoking the unchanged recovery DOE.
"""

import re
import stage8_f96_plan_recovery as recovery


def exact_historical_excerpt(raw: bytes, count: int) -> bytes:
    prefix = raw[: recovery.EXCERPT_BYTES]
    digest = recovery.sha_bytes(prefix)
    if digest != recovery.EXCERPT_SHA:
        raise RuntimeError(
            f"historical prefix SHA mismatch: bytes={len(prefix)} sha={digest}"
        )
    text = prefix.decode("utf-8")
    actual = len(re.findall(r"\S+", text, flags=re.UNICODE))
    if actual != count:
        raise RuntimeError(
            f"historical prefix token-count mismatch: expected={count} actual={actual}"
        )
    return prefix


recovery.derive_first_nonws = exact_historical_excerpt
recovery.main()
