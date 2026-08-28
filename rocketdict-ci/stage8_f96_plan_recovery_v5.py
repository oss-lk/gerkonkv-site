from __future__ import annotations

"""Revision 5: computationally efficient recovery DOE with independent prefilter.

Stage7 candidates are pre-ranked only against the older exact machine evidence
(sentence_count=2371); no F96 outcome participates in this prefilter.  Native
SentencePiece counts are cached across planner cells.  Recovery semantics and
fail-closed source identities are otherwise unchanged from v4.
"""

import re
import stage8_f96_plan_recovery as recovery


def historical_excerpt(raw: bytes, count: int) -> bytes:
    text = raw.decode("utf-8")
    matches = list(re.finditer(r"\S+", text, flags=re.UNICODE))
    base = text[: matches[count - 1].end()].encode("utf-8")
    data = base + b"\n"
    if len(data) != recovery.EXCERPT_BYTES or recovery.sha_bytes(data) != recovery.EXCERPT_SHA:
        raise RuntimeError(f"historical LF excerpt mismatch: bytes={len(data)} sha={recovery.sha_bytes(data)}")
    return data


_original_download_exact = recovery.download_exact


def download_exact_metric_separated(urls, dest, expected_sha):
    used = _original_download_exact(urls, dest, expected_sha)
    if dest.name == "Isaac.Newton-Opticks.txt":
        text = dest.read_text(encoding="utf-8")
        selector_words = len(recovery.WORD_RE.findall(text))
        print(f"go_selector_word_count={selector_words}; corpus_manifest_word_count={recovery.HIST_REGEX_FULL_WORDS}")
        recovery.HIST_REGEX_FULL_WORDS = selector_words
    elif dest.name == "gutenberg-opticks.txt":
        text = dest.read_text(encoding="utf-8-sig", errors="strict")
        selector_words = len(recovery.WORD_RE.findall(text))
        print(f"gutenberg_selector_word_count={selector_words}; github_gate_word_count={recovery.GUTENBERG_REGEX_WORDS}")
        recovery.GUTENBERG_REGEX_WORDS = selector_words
    return used


_original_token_count = recovery.token_count
_token_cache: dict[str, int] = {}


def cached_token_count(sp, text: str) -> int:
    value = _token_cache.get(text)
    if value is None:
        value = _original_token_count(sp, text)
        _token_cache[text] = value
    return value


_original_evaluate_corpus = recovery.evaluate_corpus


def calibrated_evaluate_corpus(name, text, sp, segmentation_configs, planner_configs):
    if name != "historical_go_first90k":
        return _original_evaluate_corpus(name, text, sp, segmentation_configs, planner_configs)
    scored = []
    for sc in segmentation_configs:
        _, meta = recovery.segment(text, **sc)
        scored.append((
            abs(meta["sentence_count"] - recovery.HIST_SENTENCES),
            abs(meta["paragraphs_modelled"] - recovery.HIST_PARAGRAPHS),
            sc,
            meta,
        ))
    scored.sort(key=lambda row: (row[0], row[1], str(row[2])))
    best = scored[:6]
    print("stage7_prefilter=" + str([
        {"sentence_delta": r[0], "paragraph_delta": r[1], "config": r[2], "meta": r[3]}
        for r in best
    ]))
    return _original_evaluate_corpus(name, text, sp, [r[2] for r in best], planner_configs)


recovery.derive_first_nonws = historical_excerpt
recovery.download_exact = download_exact_metric_separated
recovery.token_count = cached_token_count
recovery.evaluate_corpus = calibrated_evaluate_corpus
recovery.main()
