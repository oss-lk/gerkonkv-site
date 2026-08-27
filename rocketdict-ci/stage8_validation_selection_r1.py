from __future__ import annotations

"""Stage 8 independent validation selection R1 (SOURCE-ONLY, no MT).

Purpose
-------
Freeze a second deterministic ~5k Opticks validation set BEFORE looking at any
translation result. The set must not overlap the existing frozen 5044/80 screen.
Selection uses source-only features and a fixed salt; no target/model score is
available in this program.

This selector is deliberately a separate workflow from translation. Its first
successful run records the selection SHA. That SHA is then pinned in the
independent validation runner and must never be changed in response to model
results.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

from nltk.stem import PorterStemmer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_opus_gate import OPTICKS_URL, download  # noqa: E402
import stage8_ghi_reconstruction_gate as base  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402

ROOT = Path("work-stage8-validation-r1")
CORPUS = ROOT / "corpus" / "opticks.txt"
EVIDENCE = ROOT / "evidence"
EXPECTED_OPTICKS_SHA256 = base.EXPECTED_OPTICKS_SHA256
FROZEN_R0_SHA = base.EXPECTED_SELECTION_SHA256
TARGET_WORDS = 5000
SELECTOR_SALT = "rocketdict-stage8-independent-validation-r1-2026-08-27"

# Word budgets are fixed before any MT result exists. Categories are exclusive
# in the priority order below. If a bucket is smaller than its budget, the final
# deterministic fill step uses all remaining eligible source units.
QUOTAS = {
    "technical": 1200,
    "numeric_dense": 1200,
    "mixed_case_term": 1200,
    "numeric": 700,
    "general": 700,
}

TABLE_RULE_RE = re.compile(r"(?m)^[\-+]{12,}\s*$")
STRUCTURAL_ID_RE = re.compile(r"(?ms)(?:^|\n)\d+(?:\.[A-Za-z]+)+\.\d+\.\s*$")
WORD_RE = re.compile(r"(?<![A-Za-z])([A-Za-z]+)(?![A-Za-z])")
STEMMER = PorterStemmer()


def protected_mask(text: str) -> list[bool]:
    """Source-only mask copied from P-v1 semantics without importing O-v1/O-v2."""
    mask = [False] * len(text)
    square = 0
    emphasis = False
    for i, ch in enumerate(text):
        if ch == "_" and square == 0:
            emphasis = not emphasis
            mask[i] = True
            continue
        if ch == "[" and not emphasis:
            square += 1
        if square or emphasis:
            mask[i] = True
        if ch == "]" and square and not emphasis:
            square -= 1
    return mask


def mixed_case_stems(source: str) -> dict[str, dict]:
    """Exact P-v1 source-only mixed-case stem signal, implemented locally."""
    mask = protected_mask(source)
    by_stem: dict[str, list[dict]] = defaultdict(list)
    for m in WORD_RE.finditer(source):
        if any(mask[m.start():m.end()]):
            continue
        word = m.group(1)
        if len(word) < 5:
            continue
        stem = STEMMER.stem(word.casefold())
        by_stem[stem].append({
            "surface": word,
            "start": m.start(),
            "end": m.end(),
            "titlecase": word[0].isupper() and word[1:].islower(),
            "lowercase": word.islower(),
        })
    eligible = {}
    for stem, rows in by_stem.items():
        if len(rows) < 2:
            continue
        if any(r["titlecase"] for r in rows) and any(r["lowercase"] for r in rows):
            eligible[stem] = {
                "surfaces": [r["surface"] for r in rows],
                "occurrences": rows,
            }
    return eligible


def is_technical(source: str) -> bool:
    return bool(
        v5.GREEK_SOURCE_RE.search(source)
        or v5.ILLUSTRATION_SOURCE_RE.search(source)
        or v5.FOOTNOTE_RE.search(source)
        or v5.symbolic_emphasis_sequence(source)
        or base.FIG_RE.search(source)
        or TABLE_RULE_RE.search(source)
        or STRUCTURAL_ID_RE.search(source)
    )


def source_category(source: str) -> str:
    if is_technical(source):
        return "technical"
    numeric_count = sum(base.numeric_counter(source).values())
    if numeric_count >= 4:
        return "numeric_dense"
    if mixed_case_stems(source):
        return "mixed_case_term"
    if numeric_count:
        return "numeric"
    return "general"


def rank(unit: dict, salt: str) -> str:
    return base.text_sha256(f"{salt}\0{unit['occurrence']}\0{unit['source']}")


def serialize(units: list[dict]) -> str:
    return "".join(
        f"{u['occurrence']}\t{u['category']}\t{u['words']}\t{u['source']}\n"
        for u in units
    )


def main() -> None:
    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    download(OPTICKS_URL, CORPUS)
    corpus_sha = base.sha256_path(CORPUS)
    if corpus_sha != EXPECTED_OPTICKS_SHA256:
        raise RuntimeError(f"Opticks hash mismatch: {corpus_sha} != {EXPECTED_OPTICKS_SHA256}")

    corpus = CORPUS.read_text(encoding="utf-8-sig", errors="replace")
    units = base.split_units(corpus)

    # Reproduce R0 selection only to obtain the exact excluded occurrence set.
    r0, r0_meta = base.select_challenge(units)
    if r0_meta["selection_sha256"] != FROZEN_R0_SHA:
        raise RuntimeError("existing frozen R0 selection drift")
    excluded = {u["occurrence"] for u in r0}

    eligible = []
    for u in units:
        if u["occurrence"] in excluded:
            continue
        row = dict(u)
        row["category"] = source_category(row["source"])
        eligible.append(row)

    buckets = {name: [] for name in QUOTAS}
    for u in eligible:
        buckets[u["category"]].append(u)

    selected: dict[int, dict] = {}
    bucket_words_selected = Counter()

    for name, budget in QUOTAS.items():
        used = 0
        ordered = sorted(buckets[name], key=lambda x: rank(x, f"{SELECTOR_SALT}:{name}"))
        for u in ordered:
            if used >= budget and used > 0:
                break
            selected[u["occurrence"]] = u
            used += u["words"]
            bucket_words_selected[name] += u["words"]

    current = sum(u["words"] for u in selected.values())
    if current < TARGET_WORDS:
        remaining = [u for u in eligible if u["occurrence"] not in selected]
        for u in sorted(remaining, key=lambda x: rank(x, f"{SELECTOR_SALT}:fill")):
            selected[u["occurrence"]] = u
            bucket_words_selected[u["category"]] += u["words"]
            current += u["words"]
            if current >= TARGET_WORDS:
                break

    out = sorted(selected.values(), key=lambda x: x["occurrence"])
    overlap = sorted(excluded & {u["occurrence"] for u in out})
    if overlap:
        raise RuntimeError(f"independent validation overlaps frozen R0: {overlap}")
    if sum(u["words"] for u in out) < TARGET_WORDS:
        raise RuntimeError("insufficient independent source words")

    serialized = serialize(out)
    selection_sha = base.text_sha256(serialized)
    payload = {
        "schema": "rocketdict-stage8-independent-validation-selection/1",
        "status": "SOURCE_ONLY_FROZEN_CANDIDATE",
        "source": {
            "url": OPTICKS_URL,
            "sha256": corpus_sha,
            "regex_words_full_corpus": base.word_count(corpus),
        },
        "selector": {
            "salt": SELECTOR_SALT,
            "target_words": TARGET_WORDS,
            "quotas_words": QUOTAS,
            "category_priority": list(QUOTAS),
            "category_definition": {
                "technical": "source has Greek/Illustration/footnote/symbolic-emphasis/figure/table/document-id structure",
                "numeric_dense": ">=4 explicit numeric tokens after technical exclusion",
                "mixed_case_term": "source has a repeated Porter stem in both TitleCase and lowercase forms",
                "numeric": ">=1 explicit numeric token after higher-priority exclusions",
                "general": "all other eligible source units",
            },
            "no_target_or_model_information_used": True,
            "semantic_proxy_modules_imported": False,
        },
        "excluded_frozen_r0": {
            "selection_sha256": r0_meta["selection_sha256"],
            "units": len(r0),
            "occurrences_sha256": base.text_sha256(",".join(map(str, sorted(excluded)))),
        },
        "selection": {
            "selection_sha256": selection_sha,
            "actual_words": sum(u["words"] for u in out),
            "units": len(out),
            "category_unit_counts": dict(Counter(u["category"] for u in out)),
            "category_word_counts": dict(bucket_words_selected),
            "overlap_with_r0": overlap,
        },
        "units": out,
        "promotion_allowed": False,
        "next_action": "Pin selection_sha256 in a separate validation runner before any EN->RU inference is executed.",
    }
    (EVIDENCE / "stage8-validation-selection-r1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (EVIDENCE / "selection.tsv").write_text(serialized, encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
