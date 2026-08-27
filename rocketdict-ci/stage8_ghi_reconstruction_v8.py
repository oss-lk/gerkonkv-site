from __future__ import annotations

"""RocketDict Stage 8 NON-PROMOTIONAL reconstruction gate, revision 8.

v7 reduced the frozen 5044-word screen to two rejected units. Their source-side
AST candidates already pass numeric/order/delimiter/critical-token integrity;
the remaining blocker is ordinary English residue that OPUS systematically
leaves when Newton's sentence-internal common nouns are capitalized (Intervals,
Spaces, Line, Fits, Rays, ...).

N-v1 tests a conservative source-normalization retry:
* translate the original source first;
* detect ordinary unprotected Latin words in that generated target;
* lowercase only matching TitleCase source prose words, outside [] and _..._;
* ask the same OPUS model to generate new beam8/n-best8 hypotheses;
* accept a normalized-source hypothesis only when it reduces ordinary Latin
  residue and passes every unchanged source-based integrity/language gate.

No glossary is introduced. No target word is edited. No numeric/technical token
is lowercased or synthesized. The frozen selection is unchanged. This remains
reconstruction evidence only, not exact F96 promotion evidence.
"""

from collections import Counter
import json
import re
import sys

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import stage8_ghi_reconstruction_v5 as v5
import stage8_ghi_reconstruction_v6 as v6
import stage8_ghi_reconstruction_v7 as v7

CASE_RETRY_DECISIONS: list[dict] = []

TITLE_WORD_RE = re.compile(r"(?<![A-Za-z])([A-Z][a-z]{2,})(?![A-Za-z])")


def protected_mask(text: str) -> list[bool]:
    """Mask bracket and Gutenberg emphasis payloads from source normalization."""
    mask = [False] * len(text)
    square = 0
    emphasis = False
    for i, ch in enumerate(text):
        if ch == '_' and square == 0:
            emphasis = not emphasis
            mask[i] = True
            continue
        if ch == '[' and not emphasis:
            square += 1
        if square or emphasis:
            mask[i] = True
        if ch == ']' and square and not emphasis:
            square -= 1
    return mask


def residual_case_variant(source: str, generated_target: str) -> tuple[str, list[dict]]:
    """Lower only source TitleCase words that actually leaked into target prose."""
    residual = {w.casefold() for w in v6.unprotected_latin_words(generated_target)}
    if not residual:
        return source, []

    mask = protected_mask(source)
    pieces: list[str] = []
    changes: list[dict] = []
    cursor = 0
    for m in TITLE_WORD_RE.finditer(source):
        if any(mask[m.start():m.end()]):
            continue
        word = m.group(1)
        if word.casefold() not in residual:
            continue
        pieces.append(source[cursor:m.start()])
        pieces.append(word.lower())
        changes.append({
            "source_start": m.start(),
            "source_end": m.end(),
            "from": word,
            "to": word.lower(),
        })
        cursor = m.end()
    if not changes:
        return source, []
    pieces.append(source[cursor:])
    return "".join(pieces), changes


def _decode_hypotheses(translator, source_tok, target_tok, text: str) -> tuple[list[str], list[float | None]]:
    tokens = source_tok.encode(text, out_type=str)
    result = translator.translate_batch(
        [tokens],
        beam_size=8,
        num_hypotheses=8,
        return_scores=True,
        max_batch_size=1,
    )[0]
    hypotheses = [target_tok.decode(h).strip() for h in result.hypotheses]
    scores = [result.scores[i] if i < len(result.scores) else None for i in range(len(hypotheses))]
    return hypotheses, scores


def translate_prose_case_retry(translator, source_tok, target_tok, text: str) -> str:
    """v6 prose decoder plus a residue-driven source-case retry."""
    original = v6.translate_prose_nbest(translator, source_tok, target_tok, text)
    original_latin = v6.unprotected_latin_words(original)
    variant, changes = residual_case_variant(text, original)
    if not changes:
        return original

    hypotheses, scores = _decode_hypotheses(translator, source_tok, target_tok, variant)
    src_words = max(1, v6.prose_word_count(text))
    candidates = []
    for rank, candidate in enumerate(hypotheses):
        ratio = v6.prose_word_count(candidate) / src_words
        latin = v6.unprotected_latin_words(candidate)
        cyr = v6.cyrillic_share(candidate)
        passed = bool(
            candidate.strip()
            and len(latin) < len(original_latin)
            and cyr >= v6.cyrillic_share(original) - 0.02
            and 0.20 <= ratio <= 2.5
        )
        candidates.append({
            "rank": rank,
            "score": scores[rank],
            "target": candidate,
            "unprotected_latin": latin,
            "cyrillic_share": cyr,
            "word_ratio": ratio,
            "passed": passed,
        })

    passing = [c for c in candidates if c["passed"]]
    if not passing:
        CASE_RETRY_DECISIONS.append({
            "scope": "prose-fragment",
            "source": text,
            "original_target": original,
            "original_unprotected_latin": original_latin,
            "normalized_source": variant,
            "source_changes": changes,
            "selected": False,
            "candidates": candidates,
        })
        return original

    selected = min(passing, key=lambda c: (len(c["unprotected_latin"]), c["rank"]))
    CASE_RETRY_DECISIONS.append({
        "scope": "prose-fragment",
        "source": text,
        "original_target": original,
        "original_unprotected_latin": original_latin,
        "normalized_source": variant,
        "source_changes": changes,
        "selected": True,
        "selected_rank": selected["rank"],
        "selected_target": selected["target"],
        "selected_unprotected_latin": selected["unprotected_latin"],
        "candidates": candidates,
    })
    return selected["target"]


def clause_nbest_case_retry(translator, source_tok, target_tok, clause: str) -> dict:
    """v7 whole-clause search plus the same conservative source-case variant."""
    original = v7.clause_nbest(translator, source_tok, target_tok, clause)
    reference_target = original.get("target") or original.get("top1")
    if not reference_target:
        return original

    variant, changes = residual_case_variant(clause, reference_target)
    if not changes:
        return original

    hypotheses, scores = _decode_hypotheses(translator, source_tok, target_tok, variant)
    # Gate normalized-source outputs against the *original* source semantics and
    # original generated top1, never against the normalized spelling itself.
    baseline_for_gate = original.get("top1") or reference_target
    rows = []
    passing = []
    for rank, target in enumerate(hypotheses):
        gate = v6.strong_quality_gate(clause, baseline_for_gate, target)
        row = {
            "variant": "residual-titlecase-normalized",
            "rank": rank,
            "score": scores[rank],
            "target": target,
            "unprotected_latin": v6.unprotected_latin_words(target),
            "cyrillic_share": v6.cyrillic_share(target),
            "gate_passed": gate["passed"],
            "gate_reasons": gate["reasons"],
        }
        rows.append(row)
        if gate["passed"]:
            passing.append(row)

    original_latin = v6.unprotected_latin_words(reference_target)
    better = [r for r in passing if len(r["unprotected_latin"]) < len(original_latin)]
    decision = {
        "scope": "whole-clause",
        "source": clause,
        "original_target": reference_target,
        "original_unprotected_latin": original_latin,
        "normalized_source": variant,
        "source_changes": changes,
        "selected": False,
        "candidates": rows,
    }

    if not better:
        CASE_RETRY_DECISIONS.append(decision)
        # Preserve v7 evidence and append normalized hypotheses for audit.
        out = dict(original)
        out["normalized_case_retry"] = decision
        return out

    selected = min(better, key=lambda r: (len(r["unprotected_latin"]), r["rank"]))
    decision.update({
        "selected": True,
        "selected_rank": selected["rank"],
        "selected_target": selected["target"],
        "selected_unprotected_latin": selected["unprotected_latin"],
    })
    CASE_RETRY_DECISIONS.append(decision)
    return {
        "passed": True,
        "target": selected["target"],
        "selected_rank": selected["rank"],
        "top1": original.get("top1") or reference_target,
        "hypotheses": original.get("hypotheses", []),
        "normalized_case_retry": decision,
    }


def postprocess(old_error: BaseException | None) -> bool:
    # Reuse v7 mechanism relabelling/audit first.
    base_passed = v7.postprocess(old_error)
    evidence = v5.EVIDENCE / "stage8-ghi-reconstruction.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["schema"] = "rocketdict-stage8-ghi-reconstruction-gate/8"
    payload["v8_contract"] = {
        "inherits_v7": True,
        "variable_changed": "source casing retry only",
        "mechanism": "N-v1 residual-driven archaic capitalization normalization",
        "normalization_scope": "only matching TitleCase source prose words that leaked as ordinary unprotected Latin target words; excludes []/_..._",
        "decoder": "same OPUS beam8/n-best8",
        "acceptance": "strictly fewer ordinary Latin residue + unchanged source-based integrity/no-new-Latin/Cyrillic/length gates",
        "glossary": False,
        "target_editing": False,
        "semantic_quality_claimed": False,
        "exact_F96_replaced": False,
    }
    payload["v8_case_retry"] = {
        "attempts": len(CASE_RETRY_DECISIONS),
        "selected": sum(bool(x.get("selected")) for x in CASE_RETRY_DECISIONS),
        "details": CASE_RETRY_DECISIONS,
    }
    payload["local_gate_passed"] = bool(base_passed and old_error is None)
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload["local_gate_passed"]


def main() -> None:
    v6.PROSE_DECISIONS.clear()
    v7.CLAUSE_DECISIONS.clear()
    CASE_RETRY_DECISIONS.clear()

    # Keep every v7/v6 gate; change only model-input casing on conservative retry.
    v5.translate_one = translate_prose_case_retry
    v5.strong_quality_gate = v6.strong_quality_gate
    v7.clause_nbest = clause_nbest_case_retry
    v5.ast_candidate = v7.clause_first_ast_candidate

    old_error: BaseException | None = None
    try:
        v5.main()
    except SystemExit as exc:
        old_error = exc

    passed = postprocess(old_error)
    if not passed:
        if old_error is not None:
            raise SystemExit(f"v8 failed inherited gate: {old_error}")
        raise SystemExit("NON_PROMOTIONAL Stage 8 reconstruction v8 found unresolved evidence")


if __name__ == "__main__":
    main()
