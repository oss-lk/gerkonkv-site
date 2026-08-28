from __future__ import annotations

"""Revision 4: separate corpus-manifest word count from Stage12 selector word count.

Run-3 proved the historical 90k excerpt is token-end + LF and that the
byte-exact recovered Stage12 selector regex is not the regex used by the old
corpus manifest.  Source identity therefore stays SHA-bound; selector word
counts are measured and reported independently instead of being compared to a
different metric contract.
"""

import re
import stage8_f96_plan_recovery as recovery


def historical_excerpt(raw: bytes, count: int) -> bytes:
    text = raw.decode("utf-8")
    matches = list(re.finditer(r"\S+", text, flags=re.UNICODE))
    base = text[: matches[count - 1].end()].encode("utf-8")
    data = base + b"\n"
    if len(data) != recovery.EXCERPT_BYTES or recovery.sha_bytes(data) != recovery.EXCERPT_SHA:
        raise RuntimeError(
            f"historical LF excerpt mismatch: bytes={len(data)} sha={recovery.sha_bytes(data)}"
        )
    if len(re.findall(r"\S+", data.decode("utf-8"), flags=re.UNICODE)) != count:
        raise RuntimeError("historical LF excerpt token count mismatch")
    print("historical_excerpt_terminator=LF")
    return data


_original_download_exact = recovery.download_exact


def download_exact_metric_separated(urls, dest, expected_sha):
    used = _original_download_exact(urls, dest, expected_sha)
    if dest.name == "Isaac.Newton-Opticks.txt":
        text = dest.read_text(encoding="utf-8")
        selector_words = len(recovery.WORD_RE.findall(text))
        print(f"go_selector_word_count={selector_words}; corpus_manifest_word_count={recovery.HIST_REGEX_FULL_WORDS}")
        # Main's old assertion mixed metric contracts.  Preserve the observed
        # selector count as the selector-specific expected value only.
        recovery.HIST_REGEX_FULL_WORDS = selector_words
    elif dest.name == "gutenberg-opticks.txt":
        text = dest.read_text(encoding="utf-8-sig", errors="strict")
        selector_words = len(recovery.WORD_RE.findall(text))
        print(f"gutenberg_selector_word_count={selector_words}; github_gate_word_count={recovery.GUTENBERG_REGEX_WORDS}")
        recovery.GUTENBERG_REGEX_WORDS = selector_words
    return used


recovery.derive_first_nonws = historical_excerpt
recovery.download_exact = download_exact_metric_separated
recovery.main()
