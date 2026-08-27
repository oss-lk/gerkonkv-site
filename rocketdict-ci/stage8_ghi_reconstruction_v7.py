from __future__ import annotations

"""RocketDict Stage 8 NON-PROMOTIONAL reconstruction gate, revision 7.

v6 showed that the remaining rejected integrity-valid AST candidates are a
segmentation/context problem: 743/941/1797 pass numeric/order/delimiter/critical
checks after source-side AST rendering, but fine-grained prose fragments create
additional ordinary English words.

v7 changes one variable only: segmentation/context.

M-v1 clause-first strategy
--------------------------
1. Keep the exact frozen 5044-word selection and every v6 hard gate.
2. Split a high-risk unit only at top-level clause boundaries (semicolon, or a
   comma followed by a conjunction/subordinator/determiner after a sufficiently
   large clause). Never split inside [], (), or Gutenberg _..._ spans.
3. For each clause, first ask the same OPUS model for beam8/n-best8 and choose a
   generated hypothesis only if it passes the clause-local v6 strong integrity
   + no-new-Latin gate. Among passing hypotheses, prefer fewer ordinary Latin
   prose words, then model rank.
4. Only if no whole-clause hypothesis passes, fall back to the already tested
   v5 source-side structure/numeric AST *inside that clause*.
5. The reassembled whole unit must still pass the unchanged v6 whole-unit gate.

No failed target is patched. Numeric/technical nodes are parsed from source
before MT. This remains reconstruction evidence only and cannot replace the
missing exact F96 / rocketdict-numeric-integrity/3.2 gate.
"""

from collections import Counter
import json
import re
import sys

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import stage8_ghi_reconstruction_v5 as v5
import stage8_ghi_reconstruction_v6 as v6

CLAUSE_DECISIONS: list[dict] = []

# Generic syntactic starters. This is deliberately not keyed to occurrence IDs
# or Opticks vocabulary. The minimum word count avoids fragmenting short lists.
CLAUSE_START_RE = re.compile(
    r"\s*(?:"
    r"and|but|or|yet|so|for|nor|"
    r"as|since|if|when|while|whereas|although|though|because|"
    r"the|their|its|this|that|these|those|another|other"
    r")\b",
    flags=re.IGNORECASE,
)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


def top_level_clause_slices(source: str) -> list[tuple[int, int]]:
    """Return source slices without cutting protected/nested structures."""
    if not source:
        return [(0, 0)]

    square = 0
    round_ = 0
    emphasis = False
    start = 0
    slices: list[tuple[int, int]] = []
    i = 0

    while i < len(source):
        ch = source[i]
        if ch == '_' and square == 0:
            emphasis = not emphasis
            i += 1
            continue
        if emphasis:
            i += 1
            continue
        if ch == '[':
            square += 1
            i += 1
            continue
        if ch == ']' and square:
            square -= 1
            i += 1
            continue
        if square:
            i += 1
            continue
        if ch == '(':
            round_ += 1
            i += 1
            continue
        if ch == ')' and round_:
            round_ -= 1
            i += 1
            continue
        if round_:
            i += 1
            continue

        split = False
        if ch == ';':
            split = _word_count(source[start:i + 1]) >= 8
        elif ch == ',':
            tail = source[i + 1:i + 48]
            split = (
                _word_count(source[start:i + 1]) >= 14
                and CLAUSE_START_RE.match(tail) is not None
            )

        if split:
            end = i + 1
            slices.append((start, end))
            start = end
        i += 1

    if start < len(source):
        slices.append((start, len(source)))
    return [(a, b) for a, b in slices if source[a:b].strip()]


def clause_nbest(translator, source_tok, target_tok, clause: str) -> dict:
    """Try whole-clause generated hypotheses under the unchanged v6 gate."""
    if not clause.strip():
        return {"passed": True, "target": "", "selected_rank": 0, "hypotheses": []}

    tokens = source_tok.encode(clause, out_type=str)
    result = translator.translate_batch(
        [tokens],
        beam_size=8,
        num_hypotheses=8,
        return_scores=True,
        max_batch_size=1,
    )[0]
    hypotheses = [target_tok.decode(h).strip() for h in result.hypotheses]
    if not hypotheses:
        return {"passed": False, "target": None, "selected_rank": None, "hypotheses": []}

    top1 = hypotheses[0]
    rows = []
    passing = []
    for rank, target in enumerate(hypotheses):
        gate = v6.strong_quality_gate(clause, top1, target)
        latin = v6.unprotected_latin_words(target)
        row = {
            "rank": rank,
            "score": result.scores[rank] if rank < len(result.scores) else None,
            "target": target,
            "unprotected_latin": latin,
            "cyrillic_share": v6.cyrillic_share(target),
            "gate_passed": gate["passed"],
            "gate_reasons": gate["reasons"],
        }
        rows.append(row)
        if gate["passed"]:
            passing.append(row)

    if not passing:
        return {
            "passed": False,
            "target": None,
            "selected_rank": None,
            "top1": top1,
            "hypotheses": rows,
        }

    # Quality-first but conservative: fewer ordinary English residue wins; ties
    # keep model rank. All candidates here have already passed every local gate.
    selected = min(passing, key=lambda r: (len(r["unprotected_latin"]), r["rank"]))
    return {
        "passed": True,
        "target": selected["target"],
        "selected_rank": selected["rank"],
        "top1": top1,
        "hypotheses": rows,
    }


def clause_first_ast_candidate(translator, source_tok, target_tok, source: str) -> dict:
    slices = top_level_clause_slices(source)
    parts: list[str] = []
    provenance: list[dict] = []
    clauses = []

    for index, (start, end) in enumerate(slices):
        clause = source[start:end]
        whole = clause_nbest(translator, source_tok, target_tok, clause)
        if whole["passed"]:
            rendered = whole["target"] or ""
            mode = "whole-clause-nbest"
            clause_provenance = []
        else:
            rendered, clause_provenance = v5.render_structure_numeric_ast(
                translator,
                source_tok,
                target_tok,
                clause,
                source_offset=start,
            )
            mode = "clause-source-AST-fallback"

        parts.append(rendered)
        provenance.extend(clause_provenance)
        item = {
            "index": index,
            "source_start": start,
            "source_end": end,
            "source": clause,
            "mode": mode,
            "whole_clause_selected_rank": whole.get("selected_rank"),
            "whole_clause_passing": whole.get("passed", False),
            "whole_clause_hypotheses": whole.get("hypotheses", []),
            "target": rendered,
            "target_unprotected_latin": v6.unprotected_latin_words(rendered),
        }
        clauses.append(item)
        CLAUSE_DECISIONS.append(item)

    target = v5.smart_join(parts)
    return {
        "mechanism": "M-v1-clause-first-integrity-translation",
        "applicable": True,
        "target": target,
        "clauses": clauses,
        "provenance": provenance,
        "source_numeric_sequence": v5.explicit_numeric_sequence(source),
        "target_numeric_sequence": v5.explicit_numeric_sequence(target),
        "numeric_order": v5.numeric_order_guard(source, target),
        "delimiters": v5.delimiter_guard(source, target),
        "critical_tokens": v5.critical_token_guard(source, target),
        "post_hoc_target_repair": False,
    }


def postprocess(old_error: BaseException | None) -> bool:
    evidence = v5.EVIDENCE / "stage8-ghi-reconstruction.json"
    units_path = v5.EVIDENCE / "units.jsonl"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in units_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    changed_audit = []
    latin_regressions = 0
    mechanism_counts: Counter[str] = Counter()

    for row in rows:
        # v5.main hard-codes the old L mechanism label after ast_candidate wins.
        # Re-label only when the accepted target is exactly the M-v1 attempt.
        if row["mechanism"] == "L-v1-critical-structure-numeric-AST":
            accepted = None
            for attempt in reversed(row.get("attempts", [])):
                if (
                    attempt.get("mechanism") == "M-v1-clause-first-integrity-translation"
                    and attempt.get("target") == row.get("candidate")
                ):
                    accepted = attempt
                    break
            if accepted is not None:
                row["mechanism"] = "M-v1-clause-first-integrity-translation"

        if row["mechanism"] != "baseline-unchanged":
            mechanism_counts[row["mechanism"]] += 1

        if row["baseline"] != row["candidate"]:
            b = v6.unprotected_latin_words(row["baseline"])
            c = v6.unprotected_latin_words(row["candidate"])
            passed = len(c) <= len(b)
            changed_audit.append({
                "occurrence": row["occurrence"],
                "mechanism": row["mechanism"],
                "baseline": b,
                "candidate": c,
                "baseline_count": len(b),
                "candidate_count": len(c),
                "passed": passed,
            })
            if not passed:
                latin_regressions += 1

    # Persist corrected mechanism labels in the per-unit evidence.
    with units_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    payload["schema"] = "rocketdict-stage8-ghi-reconstruction-gate/7"
    payload["comparison"]["intervention_counts"] = dict(mechanism_counts)
    payload["v7_contract"] = {
        "inherits_v6": True,
        "variable_changed": "segmentation/context only",
        "mechanism": "M-v1 clause-first whole-clause n-best then source-AST fallback",
        "clause_split": "top-level semicolon or guarded comma syntax; never inside []/()/_..._",
        "whole_clause_nbest": "beam8/n-best8; unchanged local v6 strong gate; prefer fewer unprotected Latin words then model rank",
        "whole_unit_latin_regression": "stage8-no-new-unprotected-latin/1",
        "post_hoc_target_repair": False,
        "semantic_quality_claimed": False,
        "exact_F96_replaced": False,
    }
    payload["v7_changed_unit_latin_audit"] = changed_audit
    payload["v7_latin_regression_units"] = latin_regressions
    payload["v7_clause_decisions"] = {
        "count": len(CLAUSE_DECISIONS),
        "whole_clause_nbest": sum(x["mode"] == "whole-clause-nbest" for x in CLAUSE_DECISIONS),
        "ast_fallback": sum(x["mode"] == "clause-source-AST-fallback" for x in CLAUSE_DECISIONS),
        "details": CLAUSE_DECISIONS,
    }
    payload["local_gate_passed"] = bool(
        payload.get("local_gate_passed") and latin_regressions == 0 and old_error is None
    )
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload["local_gate_passed"]


def main() -> None:
    # Keep v6 decoding/gating, replace only the AST candidate with M-v1.
    v5.translate_one = v6.translate_prose_nbest
    v5.strong_quality_gate = v6.strong_quality_gate
    v5.ast_candidate = clause_first_ast_candidate

    old_error: BaseException | None = None
    try:
        v5.main()
    except SystemExit as exc:
        old_error = exc

    passed = postprocess(old_error)
    if not passed:
        if old_error is not None:
            raise SystemExit(f"v7 failed inherited gate: {old_error}")
        raise SystemExit("NON_PROMOTIONAL Stage 8 reconstruction v7 found language/integrity regression evidence")


if __name__ == "__main__":
    main()
