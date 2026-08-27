from __future__ import annotations

"""RocketDict Stage 8 / O-v2: high-confidence local term-retention gate.

O-v1 showed that sentence-level round-trip similarity is useful diagnostically
but insufficient as a hard semantic gate: occurrence 444 improved globally even
though repeated source `Refraction/refracting` semantics collapsed locally to
`revulsion/rejection` in the Russian candidate.

O-v2 freezes a deliberately narrow rule BEFORE its first run.  It does not use
a translation glossary and it does not require a source term to map to any
particular Russian word.  Instead it asks whether a repeated lexical source stem
that the BASELINE round-trip could reliably recover almost disappears from the
CANDIDATE round-trip.

A source stem is a high-confidence collapse only when ALL are true:
* alphabetic source token length >= 5 after tokenization;
* not in a fixed function/common-word exclusion list;
* source stem occurs at least 2 times in the unit;
* baseline RU->EN round-trip retains >= 75% of source occurrences;
* candidate RU->EN round-trip retains <= 25% of source occurrences;
* candidate loses at least 2 retained occurrences relative to baseline.

The rule is intentionally asymmetric and conservative.  It is designed to catch
local terminology collapse without rejecting ordinary paraphrases just because
back-translation chose a synonym.

O-v2 pins the official RU->EN OPUS archive hash observed by immutable O-v1.
This remains NON-PROMOTIONAL reconstruction evidence and cannot replace exact
F96 / rocketdict-numeric-integrity/3.2.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

from nltk.stem import PorterStemmer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage8_semantic_regression_proxy as o1  # noqa: E402

PINNED_RU_EN_SHA256 = "b4bad9451bc4c4a1e292a33568a41db88a6b3349d6feaec97c4cd748305de243"
EVIDENCE = o1.EVIDENCE
O1_PATH = EVIDENCE / "stage8-semantic-regression-proxy.json"
O2_PATH = EVIDENCE / "stage8-semantic-term-retention-o2.json"

TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
STEMMER = PorterStemmer()

# Fixed before O-v2 first execution.  This excludes high-frequency grammatical
# and generic discourse words, not scientific vocabulary.  A term never needs
# to appear in this list to pass; the list only reduces false alarms.
EXCLUDE = {
    "about", "above", "after", "again", "against", "almost", "along", "also",
    "among", "another", "because", "before", "being", "below", "between", "both",
    "could", "did", "does", "doing", "during", "each", "either", "enough", "every",
    "first", "following", "from", "further", "having", "here", "however", "into",
    "itself", "least", "made", "make", "making", "many", "might", "more", "most",
    "much", "must", "neither", "other", "otherwise", "over", "same", "second",
    "several", "should", "since", "some", "such", "than", "that", "their", "them",
    "then", "there", "these", "they", "third", "this", "those", "though", "through",
    "thus", "under", "until", "upon", "very", "were", "what", "when", "where",
    "which", "while", "whose", "with", "within", "without", "would", "whole",
}

MIN_SOURCE_COUNT = 2
MIN_BASELINE_RETENTION = 0.75
MAX_CANDIDATE_RETENTION = 0.25
MIN_ABSOLUTE_LOSS = 2


def lexical_stems(text: str) -> tuple[Counter[str], dict[str, list[str]]]:
    counts: Counter[str] = Counter()
    surfaces: dict[str, list[str]] = defaultdict(list)
    for m in TOKEN_RE.finditer(text):
        raw = m.group(0)
        word = raw.casefold()
        if len(word) < 5 or word in EXCLUDE:
            continue
        stem = STEMMER.stem(word)
        counts[stem] += 1
        surfaces[stem].append(raw)
    return counts, dict(surfaces)


def retained_count(source_count: int, roundtrip_count: int) -> int:
    return min(source_count, roundtrip_count)


def unit_term_audit(unit: dict) -> dict:
    src_counts, src_surfaces = lexical_stems(unit["source"])
    base_counts, _ = lexical_stems(unit["baseline_back_en"])
    cand_counts, _ = lexical_stems(unit["candidate_back_en"])

    repeated = []
    collapses = []
    warnings = []
    for stem, src_n in sorted(src_counts.items()):
        if src_n < MIN_SOURCE_COUNT:
            continue
        base_retained = retained_count(src_n, base_counts[stem])
        cand_retained = retained_count(src_n, cand_counts[stem])
        base_ratio = base_retained / src_n
        cand_ratio = cand_retained / src_n
        absolute_loss = base_retained - cand_retained
        row = {
            "stem": stem,
            "source_surfaces": src_surfaces.get(stem, []),
            "source_count": src_n,
            "baseline_roundtrip_count": base_counts[stem],
            "candidate_roundtrip_count": cand_counts[stem],
            "baseline_retained": base_retained,
            "candidate_retained": cand_retained,
            "baseline_retention_ratio": base_ratio,
            "candidate_retention_ratio": cand_ratio,
            "absolute_retention_loss": absolute_loss,
        }
        repeated.append(row)
        if cand_retained < base_retained:
            warnings.append(row)
        if (
            base_ratio >= MIN_BASELINE_RETENTION
            and cand_ratio <= MAX_CANDIDATE_RETENTION
            and absolute_loss >= MIN_ABSOLUTE_LOSS
        ):
            collapses.append(row)

    return {
        "occurrence": unit["occurrence"],
        "mechanism": unit["mechanism"],
        "source": unit["source"],
        "baseline_ru": unit["baseline_ru"],
        "candidate_ru": unit["candidate_ru"],
        "baseline_back_en": unit["baseline_back_en"],
        "candidate_back_en": unit["candidate_back_en"],
        "repeated_source_stems": repeated,
        "retention_warnings": warnings,
        "high_confidence_collapses": collapses,
        "passed": not collapses,
    }


def main() -> None:
    # Pin the exact reverse-model artifact before reproducing O-v1.
    o1.EXPECTED_RU_EN_SHA256 = PINNED_RU_EN_SHA256
    o1.main()
    base = json.loads(O1_PATH.read_text(encoding="utf-8"))

    observed = base["reverse_model"]["opus_zip_sha256"]
    if observed != PINNED_RU_EN_SHA256:
        raise RuntimeError(f"O-v2 reverse-model hash drift: {observed}")
    if base["selection_sha256"] != "ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe":
        raise RuntimeError("O-v2 frozen selection drift")
    if base["changed_units"] != 10:
        raise RuntimeError(f"O-v2 expected 10 v8 interventions, got {base['changed_units']}")

    audits = [unit_term_audit(unit) for unit in base["units"]]
    failed = [row for row in audits if not row["passed"]]
    payload = {
        "schema": "rocketdict-stage8-semantic-term-retention/2",
        "status": "FAIL" if failed else "PASS",
        "parent": "clean v8 + O-v1 paired round-trip evidence",
        "selection_sha256": base["selection_sha256"],
        "reverse_model": {
            **base["reverse_model"],
            "required_opus_zip_sha256": PINNED_RU_EN_SHA256,
            "hash_pin_passed": observed == PINNED_RU_EN_SHA256,
        },
        "contract": {
            "name": "stage8-high-confidence-term-collapse/1",
            "stemmer": "NLTK PorterStemmer",
            "min_source_count": MIN_SOURCE_COUNT,
            "min_baseline_retention_ratio": MIN_BASELINE_RETENTION,
            "max_candidate_retention_ratio": MAX_CANDIDATE_RETENTION,
            "min_absolute_retention_loss": MIN_ABSOLUTE_LOSS,
            "token_min_alpha_length": 5,
            "fixed_exclusion_words": sorted(EXCLUDE),
            "translation_glossary_used": False,
            "semantic_correctness_claimed": False,
            "purpose": "fail-closed detection of local repeated-term collapse missed by sentence-level O-v1",
        },
        "aggregate": {
            "changed_units": len(audits),
            "failed_units": len(failed),
            "failed_occurrences": [row["occurrence"] for row in failed],
            "high_confidence_collapses": sum(len(row["high_confidence_collapses"]) for row in failed),
            "warning_units": sum(bool(row["retention_warnings"]) for row in audits),
        },
        "units": audits,
        "promotion_allowed": False,
        "next_action": (
            "If a high-confidence collapse exists, reject the affected v8 intervention and test a source-side/model-generated retry that restores the local term without weakening any integrity/language gate."
            if failed
            else "Term-retention layer passes; continue with independent semantic review rather than treating O-v2 as a semantic oracle."
        ),
    }
    O2_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)

    if failed:
        raise SystemExit(
            "O-v2 detected high-confidence local term collapse in occurrences: "
            + ",".join(str(row["occurrence"]) for row in failed)
        )


if __name__ == "__main__":
    main()
