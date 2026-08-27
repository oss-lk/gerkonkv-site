from __future__ import annotations

"""RocketDict Stage 8 / P-v1: source case-consistency retry probe.

O-v2 isolated one high-confidence local semantic collapse in clean v8:
occurrence 444, source stem `refract` (Refraction/refracting).  This probe tests
a source-derived correction mechanism without a translation glossary.

Mechanism
---------
1. Parse ordinary source prose before MT (exclude [] and _..._ payloads).
2. Porter-stem alphabetic tokens.
3. A stem is eligible only when the same source unit contains BOTH:
   - at least one TitleCase surface form; and
   - at least one already-lowercase morphological surface form.
4. Lowercase only the TitleCase occurrences of those eligible stems.
5. Ask the SAME official OPUS EN->RU model for beam16/n-best16 hypotheses.
6. A hypothesis is eligible only if it passes all inherited forward integrity /
   language gates against the ORIGINAL source, has no ordinary Latin residue,
   and passes the frozen O-v2 high-confidence term-collapse gate after pinned
   official RU->EN round-trip evaluation.

No Russian translation is prescribed. No glossary is used. No generated target
is edited. The source itself supplies the casing-consistency signal.

This is an exact mechanism probe for occurrence 444, not a full 5044-word gate
and not exact F96 promotion evidence.
"""

from collections import defaultdict
import json
from pathlib import Path
import re
import sys

from nltk.stem import PorterStemmer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage8_g_nbest_probe import prepare_model  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_semantic_regression_proxy as o1  # noqa: E402
import stage8_semantic_term_retention_o2 as o2  # noqa: E402

OUT = Path("work-stage8-p1/evidence")
PINNED_RU_EN_SHA256 = o2.PINNED_RU_EN_SHA256

SOURCE = """And when the Refraction of the second Prism
was equal to the Refraction of the first, the refracting Angles of them
both being about 60 Degrees, the Axis of the Spectrum _3p 3t_ made by
that Refraction, did when produced pass also through the middle of the
same white round Image S."""

# Original OPUS top-1 and clean-v8 target are durable O-v1/O-v2 evidence. They
# are included here to make this exact mechanism probe auditable without
# pretending to reconstruct the lost F96 pipeline.
BASELINE_RU = """И когда Рефракция второй Призма была равна Рефракции первой, рефлексирующие углы обоих из них были примерно 60 градусов, ось Спектрума 3p 3t_, сделанная этим Рефракцией, сделала, когда производилась также через середину того же белого круглого изображения S."""
V8_RU = """И когда отвращение второй Призма было равно Отклонению первой, Рефлексирующие углы обоих из них составляют около 60 градусов, ось Спектрума_3p 3t_, сделанная этим Рефракцией, сделала, когда производилась также через середину того же белого круглого изображения S."""

WORD_RE = re.compile(r"(?<![A-Za-z])([A-Za-z]+)(?![A-Za-z])")
STEMMER = PorterStemmer()


def protected_mask(text: str) -> list[bool]:
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


def normalize_source(source: str, eligible: dict[str, dict]) -> tuple[str, list[dict]]:
    eligible_stems = set(eligible)
    mask = protected_mask(source)
    parts = []
    changes = []
    cursor = 0
    for m in WORD_RE.finditer(source):
        if any(mask[m.start():m.end()]):
            continue
        word = m.group(1)
        stem = STEMMER.stem(word.casefold())
        is_title = word[0].isupper() and word[1:].islower()
        if stem not in eligible_stems or not is_title:
            continue
        parts.append(source[cursor:m.start()])
        parts.append(word.lower())
        changes.append({
            "stem": stem,
            "source_start": m.start(),
            "source_end": m.end(),
            "from": word,
            "to": word.lower(),
        })
        cursor = m.end()
    parts.append(source[cursor:])
    return "".join(parts), changes


def forward_hypotheses(translator, source_tok, target_tok, source: str) -> list[dict]:
    tokens = source_tok.encode(source, out_type=str)
    result = translator.translate_batch(
        [tokens],
        beam_size=16,
        num_hypotheses=16,
        return_scores=True,
        max_batch_size=1,
    )[0]
    rows = []
    for rank, hyp in enumerate(result.hypotheses):
        target = target_tok.decode(hyp).strip()
        gate = v6.strong_quality_gate(SOURCE, BASELINE_RU, target)
        latin = v6.unprotected_latin_words(target)
        rows.append({
            "rank": rank,
            "score": result.scores[rank] if rank < len(result.scores) else None,
            "target": target,
            "forward_gate": gate,
            "unprotected_latin": latin,
            "forward_eligible": bool(gate["passed"] and not latin),
        })
    return rows


def main() -> None:
    eligible = mixed_case_stems(SOURCE)
    normalized, changes = normalize_source(SOURCE, eligible)
    if not eligible or not changes:
        raise RuntimeError("P-v1 source contained no mixed-case stem signal")

    translator, source_tok, target_tok, forward_identity = prepare_model()
    forward = forward_hypotheses(translator, source_tok, target_tok, normalized)
    eligible_rows = [r for r in forward if r["forward_eligible"]]

    o1.EXPECTED_RU_EN_SHA256 = PINNED_RU_EN_SHA256
    reverse, reverse_src_tok, reverse_tgt_tok, reverse_identity = o1.prepare_reverse_model()
    baseline_back = o1.reverse_batch(reverse, reverse_src_tok, reverse_tgt_tok, [BASELINE_RU])[0]
    v8_back = o1.reverse_batch(reverse, reverse_src_tok, reverse_tgt_tok, [V8_RU])[0]

    if eligible_rows:
        backs = o1.reverse_batch(
            reverse,
            reverse_src_tok,
            reverse_tgt_tok,
            [r["target"] for r in eligible_rows],
        )
    else:
        backs = []

    selected = None
    for row, back in zip(eligible_rows, backs):
        fake = {
            "occurrence": 444,
            "mechanism": "P-v1-source-case-consistency",
            "source": SOURCE,
            "baseline_ru": BASELINE_RU,
            "candidate_ru": row["target"],
            "baseline_back_en": baseline_back,
            "candidate_back_en": back,
        }
        audit = o2.unit_term_audit(fake)
        row["candidate_back_en"] = back
        row["o2_term_audit"] = audit
        row["o2_passed"] = audit["passed"]
        if selected is None and audit["passed"]:
            selected = row

    payload = {
        "schema": "rocketdict-stage8-term-case-consistency-probe/1",
        "status": "PASS" if selected is not None else "FAIL",
        "case_id": "reconstruction-occurrence-444",
        "scope": "exact mechanism probe only",
        "source": SOURCE,
        "mixed_case_signal": eligible,
        "normalized_source": normalized,
        "source_changes": changes,
        "forward_model": forward_identity,
        "reverse_model": {
            **reverse_identity,
            "required_opus_zip_sha256": PINNED_RU_EN_SHA256,
            "hash_pin_passed": reverse_identity["opus_zip_sha256"] == PINNED_RU_EN_SHA256,
        },
        "baseline": {
            "ru": BASELINE_RU,
            "back_en": baseline_back,
        },
        "clean_v8": {
            "ru": V8_RU,
            "back_en": v8_back,
            "term_audit": o2.unit_term_audit({
                "occurrence": 444,
                "mechanism": "clean-v8",
                "source": SOURCE,
                "baseline_ru": BASELINE_RU,
                "candidate_ru": V8_RU,
                "baseline_back_en": baseline_back,
                "candidate_back_en": v8_back,
            }),
        },
        "forward_hypotheses": forward,
        "selected": selected,
        "mechanism": {
            "name": "P-v1-source-case-consistency",
            "translation_glossary_used": False,
            "target_editing": False,
            "source_signal": "same Porter stem appears both TitleCase and lowercase in ordinary source prose",
            "decoder": "official OPUS EN->RU beam16/n-best16",
            "acceptance": "all inherited forward gates + zero ordinary Latin residue + frozen O-v2 term-retention pass",
        },
        "promotion_allowed": False,
        "next_action": (
            "If PASS, integrate the generic source case-consistency normalization as a separate reconstruction DOE cell and rerun the identical frozen 5044-word selection before considering it a survivor."
            if selected is not None
            else "Reject P-v1; do not add a glossary or patch the target. Test a different source/model-generated terminology mechanism."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage8-term-case-consistency-p1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if selected is None:
        raise SystemExit("P-v1 failed to produce a forward+O-v2-valid model-generated hypothesis")


if __name__ == "__main__":
    main()
