from __future__ import annotations

"""Revision 3: identify the historical excerpt's one-byte canonical terminator."""

import re
import stage8_f96_plan_recovery as recovery


def historical_excerpt_with_exact_terminator(raw: bytes, count: int) -> bytes:
    base = recovery.derive_first_nonws_original(raw, count) if hasattr(recovery, "derive_first_nonws_original") else None
    if base is None:
        # Call the original implementation before monkey-patching.
        text = raw.decode("utf-8")
        matches = list(re.finditer(r"\S+", text, flags=re.UNICODE))
        base = text[: matches[count - 1].end()].encode("utf-8")
    candidates = {
        "raw_next": base + raw[len(base):len(base)+1],
        "LF": base + b"\n",
        "space": base + b" ",
        "CR": base + b"\r",
        "tab": base + b"\t",
    }
    diagnostics = {name: recovery.sha_bytes(data) for name, data in candidates.items()}
    for name, data in candidates.items():
        if len(data) == recovery.EXCERPT_BYTES and diagnostics[name] == recovery.EXCERPT_SHA:
            actual = len(re.findall(r"\S+", data.decode("utf-8"), flags=re.UNICODE))
            if actual != count:
                raise RuntimeError(f"matched SHA but token count differs: {name} {actual}")
            print(f"historical_excerpt_terminator={name}")
            return data
    raise RuntimeError(
        "historical excerpt is not token-end plus one canonical terminator; "
        f"base_bytes={len(base)} base_sha={recovery.sha_bytes(base)} candidates={diagnostics}"
    )


# Preserve a stable handle for diagnostics if this module is reused.
recovery.derive_first_nonws_original = recovery.derive_first_nonws
recovery.derive_first_nonws = historical_excerpt_with_exact_terminator
recovery.main()
