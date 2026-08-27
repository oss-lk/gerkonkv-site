from __future__ import annotations

"""RocketDict Stage 8 NON-PROMOTIONAL reconstruction gate, revision 6.

v5 passed every objective integrity contract on the frozen 5044-word screen, but
manual review found four AST interventions that introduced additional ordinary
Latin prose words (Image; Spaces/Line; Rays/Space; Fits/the/Oblique/Rays/Secants).
That is an objective language-regression signal even though aggregate Cyrillic
share stayed within tolerance.

v6 keeps the exact v5 structure/numeric mechanism and frozen selection. It adds:
* conservative prose n-best decoding: rank-0 remains default; a later model
  hypothesis is chosen only when it has fewer ordinary unprotected Latin words,
  no material Cyrillic-share loss, and no length anomaly;
* whole-unit hard gate: an intervention may not increase unprotected Latin-word
  count versus the original baseline translation.

This is a regression screen, not a semantic-quality metric and not a replacement
for the missing exact F96 / rocketdict-numeric-integrity/3.2 gate.
"""

import json
from pathlib import Path
import re
import sys

import stage8_ghi_reconstruction_v5 as v5

LATIN_WORD_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]{3,}(?![A-Za-z])")
CYR_RE = re.compile(r"[А-Яа-яЁё]")
ALPHA_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")
PROSE_DECISIONS: list[dict] = []

BASE_STRONG_GATE = v5.strong_quality_gate
BASE_TRANSLATE_ONE = v5.translate_one


def strip_protected(text: str) -> str:
    # Structural payloads are governed by dedicated integrity contracts and may
    # legitimately contain FIG, Greek payload letters, technical IDs, etc.
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"_[^_]*_", " ", text)
    return text


def unprotected_latin_words(text: str) -> list[str]:
    return LATIN_WORD_RE.findall(strip_protected(text))


def cyrillic_share(text: str) -> float:
    alpha = ALPHA_RE.findall(text)
    return len(CYR_RE.findall(text)) / len(alpha) if alpha else 0.0


def prose_word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


def translate_prose_nbest(translator, source_tok, target_tok, text: str) -> str:
    if not text.strip():
        return ""
    tokens = source_tok.encode(text, out_type=str)
    result = translator.translate_batch(
        [tokens],
        beam_size=8,
        num_hypotheses=8,
        return_scores=True,
        max_batch_size=1,
    )[0]
    hypotheses = [target_tok.decode(h).strip() for h in result.hypotheses]
    if not hypotheses:
        return BASE_TRANSLATE_ONE(translator, source_tok, target_tok, text)

    top = hypotheses[0]
    top_latin = len(unprotected_latin_words(top))
    top_cyr = cyrillic_share(top)
    src_words = max(1, prose_word_count(text))
    selected_rank = 0

    # Conservative: model order is respected. The first later hypothesis that
    # objectively removes residual Latin prose without introducing a length
    # anomaly or material Cyrillic loss may replace rank 0.
    for rank, candidate in enumerate(hypotheses[1:], start=1):
        cand_latin = len(unprotected_latin_words(candidate))
        cand_cyr = cyrillic_share(candidate)
        ratio = prose_word_count(candidate) / src_words
        if (
            cand_latin < top_latin
            and cand_cyr >= top_cyr - 0.02
            and 0.20 <= ratio <= 2.5
            and candidate.strip()
        ):
            selected_rank = rank
            break

    chosen = hypotheses[selected_rank]
    PROSE_DECISIONS.append({
        "source": text,
        "top1": top,
        "selected": chosen,
        "selected_rank": selected_rank,
        "top1_unprotected_latin": unprotected_latin_words(top),
        "selected_unprotected_latin": unprotected_latin_words(chosen),
        "top1_cyrillic_share": top_cyr,
        "selected_cyrillic_share": cyrillic_share(chosen),
    })
    return chosen


def strong_quality_gate(source: str, baseline: str, candidate: str) -> dict:
    base = BASE_STRONG_GATE(source, baseline, candidate)
    baseline_latin = unprotected_latin_words(baseline)
    candidate_latin = unprotected_latin_words(candidate)
    latin_passed = len(candidate_latin) <= len(baseline_latin)
    reasons = list(base["reasons"])
    if not latin_passed:
        reasons.append("new_unprotected_latin_words")
    return {
        **base,
        "passed": not reasons,
        "reasons": reasons,
        "unprotected_latin_regression": {
            "contract": "stage8-no-new-unprotected-latin/1",
            "baseline": baseline_latin,
            "candidate": candidate_latin,
            "baseline_count": len(baseline_latin),
            "candidate_count": len(candidate_latin),
            "passed": latin_passed,
        },
    }


def postprocess(old_error: BaseException | None) -> bool:
    evidence = v5.EVIDENCE / "stage8-ghi-reconstruction.json"
    units_path = v5.EVIDENCE / "units.jsonl"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in units_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    regressions = []
    changed = []
    for row in rows:
        if row["baseline"] == row["candidate"]:
            continue
        b = unprotected_latin_words(row["baseline"])
        c = unprotected_latin_words(row["candidate"])
        item = {
            "occurrence": row["occurrence"],
            "mechanism": row["mechanism"],
            "baseline": b,
            "candidate": c,
            "baseline_count": len(b),
            "candidate_count": len(c),
            "passed": len(c) <= len(b),
        }
        changed.append(item)
        if not item["passed"]:
            regressions.append(item)

    payload["schema"] = "rocketdict-stage8-ghi-reconstruction-gate/6"
    payload["v6_contract"] = {
        "inherits_v5": True,
        "prose_decoder": "conservative beam8/n-best8; later rank only for fewer unprotected Latin words without material Cyrillic/length loss",
        "whole_unit_latin_regression": "stage8-no-new-unprotected-latin/1",
        "semantic_quality_claimed": False,
        "exact_F96_replaced": False,
    }
    payload["v6_changed_unit_latin_audit"] = changed
    payload["v6_latin_regression_units"] = len(regressions)
    payload["v6_prose_nbest_decisions"] = {
        "calls": len(PROSE_DECISIONS),
        "non_top1_selected": sum(x["selected_rank"] != 0 for x in PROSE_DECISIONS),
        "details": PROSE_DECISIONS,
    }
    payload["local_gate_passed"] = bool(
        payload.get("local_gate_passed") and not regressions and old_error is None
    )
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload["local_gate_passed"]


def main() -> None:
    # v5 functions resolve globals in the v5 module; patch only for this process.
    v5.translate_one = translate_prose_nbest
    v5.strong_quality_gate = strong_quality_gate

    old_error: BaseException | None = None
    try:
        v5.main()
    except SystemExit as exc:
        old_error = exc

    passed = postprocess(old_error)
    if not passed:
        if old_error is not None:
            raise SystemExit(f"v6 failed inherited v5 gate: {old_error}")
        raise SystemExit("NON_PROMOTIONAL Stage 8 reconstruction v6 found language/integrity regression evidence")


if __name__ == "__main__":
    main()
