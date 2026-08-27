from __future__ import annotations

"""RocketDict Stage 8 v9 NON-PROMOTIONAL frozen-5044 semantic rescue gate.

v8 is objective-integrity clean on the frozen selection, but pinned O-v2 finds
one high-confidence local repeated-term collapse in occurrence 444. Q-v1 solves
that exact class by combining whole-sentence mixed-case-normalized MT with
pre-parsed source-planned structural rendering.

v9 keeps intervention scope minimal:
1. reproduce clean v8 on the EXACT frozen 5044-word selection;
2. pinned official RU->EN O-v2 audits only units v8 actually changed;
3. invoke Q-v1 rescue ONLY when O-v2 proves a high-confidence collapse AND the
   source independently supplies a mixed-case Porter-stem signal;
4. Q candidates are whole-source OPUS beam16/n-best16; only pre-parsed symbolic
   source nodes may have their surrounding Gutenberg `_` delimiters
   canonicalized when the exact payload survives uniquely;
5. require original-source forward gates, zero ordinary Latin residue and O-v2
   PASS before replacing v8 output;
6. recompute the whole frozen-set objective aggregate and final O-v2 audit.

No glossary. No manually keyed occurrence fix. No missing-number append. No
arbitrary target prose edit. This remains reconstruction evidence and cannot
replace missing exact 0.30.40/F96 + rocketdict-numeric-integrity/3.2.
"""

from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage8_g_nbest_probe import prepare_model  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
import stage8_semantic_regression_proxy as o1  # noqa: E402
import stage8_semantic_term_retention_o2 as o2  # noqa: E402
import stage8_term_case_consistency_p1 as p1  # noqa: E402
import stage8_whole_context_structural_q1 as q1  # noqa: E402

EVIDENCE = Path("work-stage8-v9/evidence")
V8_UNITS = v5.EVIDENCE / "units.jsonl"
V8_SUMMARY = v5.EVIDENCE / "stage8-ghi-reconstruction.json"
FROZEN_SELECTION_SHA = "ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe"


def reverse_map(reverse, src_tok, tgt_tok, rows: list[dict], field: str) -> dict[int, str]:
    texts = [r[field] for r in rows]
    backs = o1.reverse_batch(reverse, src_tok, tgt_tok, texts) if texts else []
    return {r["occurrence"]: b for r, b in zip(rows, backs)}


def generic_q_hypotheses(translator, source_tok, target_tok, source: str, baseline: str) -> tuple[dict, str, list[dict], list[dict]]:
    eligible = p1.mixed_case_stems(source)
    normalized, source_changes = p1.normalize_source(source, eligible)
    if not source_changes:
        return eligible, normalized, source_changes, []
    nodes = q1.parse_symbolic_nodes(source)

    tokens = source_tok.encode(normalized, out_type=str)
    result = translator.translate_batch(
        [tokens], beam_size=16, num_hypotheses=16, return_scores=True, max_batch_size=1
    )[0]
    rows = []
    for rank, hyp in enumerate(result.hypotheses):
        raw = target_tok.decode(hyp).strip()
        canonical, structure = q1.canonicalize_symbolic_nodes(raw, nodes)
        if canonical is None:
            rows.append({
                "rank": rank,
                "score": result.scores[rank] if rank < len(result.scores) else None,
                "raw_target": raw,
                "canonical_target": None,
                "structure_render": structure,
                "forward_eligible": False,
                "reject_reason": "preparsed-symbolic-payload-not-unique",
            })
            continue
        gate = v6.strong_quality_gate(source, baseline, canonical)
        latin = v6.unprotected_latin_words(canonical)
        rows.append({
            "rank": rank,
            "score": result.scores[rank] if rank < len(result.scores) else None,
            "raw_target": raw,
            "canonical_target": canonical,
            "structure_render": structure,
            "forward_gate": gate,
            "unprotected_latin": latin,
            "forward_eligible": bool(gate["passed"] and not latin),
        })
    return eligible, normalized, source_changes, rows


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    # Reproduce clean v8 first. It owns the frozen selector hard-pin.
    v8.main()
    v8_summary = json.loads(V8_SUMMARY.read_text(encoding="utf-8"))
    if v8_summary["selection"]["selection_sha256"] != FROZEN_SELECTION_SHA:
        raise RuntimeError("v9 frozen selection drift")
    if not v8_summary.get("local_gate_passed"):
        raise RuntimeError("v9 parent clean-v8 no longer passes its objective gate")

    rows = [
        json.loads(line)
        for line in V8_UNITS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    changed = [r for r in rows if r["baseline"] != r["candidate"]]
    if len(changed) != 10:
        raise RuntimeError(f"v9 expected 10 clean-v8 changed units, got {len(changed)}")

    # Pinned reverse model: O-v2 semantic trigger must itself be reproducible.
    o1.EXPECTED_RU_EN_SHA256 = o2.PINNED_RU_EN_SHA256
    reverse, rev_src_tok, rev_tgt_tok, reverse_identity = o1.prepare_reverse_model()
    baseline_back = reverse_map(reverse, rev_src_tok, rev_tgt_tok, changed, "baseline")
    v8_back = reverse_map(reverse, rev_src_tok, rev_tgt_tok, changed, "candidate")

    initial_audits = {}
    failed = []
    for r in changed:
        audit = o2.unit_term_audit({
            "occurrence": r["occurrence"],
            "mechanism": r["mechanism"],
            "source": r["source"],
            "baseline_ru": r["baseline"],
            "candidate_ru": r["candidate"],
            "baseline_back_en": baseline_back[r["occurrence"]],
            "candidate_back_en": v8_back[r["occurrence"]],
        })
        initial_audits[r["occurrence"]] = audit
        if not audit["passed"]:
            failed.append(r)

    # Q-v1 only exists because a pinned O-v2 failure justifies the extra work.
    translator, source_tok, target_tok, forward_identity = prepare_model()
    rescues = []
    rescue_back: dict[int, str] = {}

    for row in failed:
        occ = row["occurrence"]
        eligible, normalized, source_changes, candidates = generic_q_hypotheses(
            translator, source_tok, target_tok, row["source"], row["baseline"]
        )
        forward_eligible = [c for c in candidates if c.get("forward_eligible")]
        candidate_backs = o1.reverse_batch(
            reverse,
            rev_src_tok,
            rev_tgt_tok,
            [c["canonical_target"] for c in forward_eligible],
        ) if forward_eligible else []

        selected = None
        for c, back in zip(forward_eligible, candidate_backs):
            audit = o2.unit_term_audit({
                "occurrence": occ,
                "mechanism": "Q-v1-pinned-O2-rescue",
                "source": row["source"],
                "baseline_ru": row["baseline"],
                "candidate_ru": c["canonical_target"],
                "baseline_back_en": baseline_back[occ],
                "candidate_back_en": back,
            })
            c["candidate_back_en"] = back
            c["o2_term_audit"] = audit
            c["o2_passed"] = audit["passed"]
            if selected is None and audit["passed"]:
                selected = c

        rescue_record = {
            "occurrence": occ,
            "initial_o2": initial_audits[occ],
            "mixed_case_signal": eligible,
            "normalized_source": normalized,
            "source_changes": source_changes,
            "candidate_count": len(candidates),
            "forward_eligible_count": len(forward_eligible),
            "selected": selected,
            "all_candidates": candidates,
        }
        rescues.append(rescue_record)
        if selected is None:
            continue

        row["candidate"] = selected["canonical_target"]
        row["mechanism"] = "Q-v1-pinned-O2-rescue"
        row["candidate_quality"] = v5.extended_row(row["source"], row["candidate"])
        rescue_back[occ] = selected["candidate_back_en"]

    # Whole frozen-set objective recheck after any rescue replacements.
    candidate_agg = v5.extended_aggregate(rows, "candidate_quality")
    strong_intervention_failures = sum(
        r["mechanism"] != "baseline-unchanged"
        and not v6.strong_quality_gate(r["source"], r["baseline"], r["candidate"])["passed"]
        for r in rows
    )
    latin_intervention_failures = sum(
        r["mechanism"] != "baseline-unchanged"
        and len(v6.unprotected_latin_words(r["candidate"])) > len(v6.unprotected_latin_words(r["baseline"]))
        for r in rows
    )

    # Final O-v2 on all changed outputs. Reuse clean-v8 reverse outputs unless a
    # Q rescue replaced that unit.
    final_audits = []
    final_failures = []
    for r in rows:
        if r["baseline"] == r["candidate"]:
            continue
        occ = r["occurrence"]
        if occ in rescue_back:
            back = rescue_back[occ]
        elif occ in v8_back:
            back = v8_back[occ]
        else:
            back = o1.reverse_batch(reverse, rev_src_tok, rev_tgt_tok, [r["candidate"]])[0]
        if occ not in baseline_back:
            baseline_back[occ] = o1.reverse_batch(reverse, rev_src_tok, rev_tgt_tok, [r["baseline"]])[0]
        audit = o2.unit_term_audit({
            "occurrence": occ,
            "mechanism": r["mechanism"],
            "source": r["source"],
            "baseline_ru": r["baseline"],
            "candidate_ru": r["candidate"],
            "baseline_back_en": baseline_back[occ],
            "candidate_back_en": back,
        })
        final_audits.append(audit)
        if not audit["passed"]:
            final_failures.append(audit)

    intervention_counts = Counter(r["mechanism"] for r in rows if r["mechanism"] != "baseline-unchanged")
    objective_pass = bool(
        candidate_agg["empty"] == 0
        and candidate_agg["numeric_fail_units"] == 0
        and candidate_agg["numeric_order_fail_units"] == 0
        and candidate_agg["delimiter_fail_units"] == 0
        and candidate_agg["critical_token_fail_units"] == 0
        and candidate_agg["figure_fail_units"] == 0
        and candidate_agg["length_anomaly_units"] == 0
        and candidate_agg["identity_units"] == 0
        and strong_intervention_failures == 0
        and latin_intervention_failures == 0
    )
    passed = bool(objective_pass and not final_failures and len(rescue_back) == len(failed))

    payload = {
        "schema": "rocketdict-stage8-v9-pinned-term-rescue/1",
        "status": "PASS" if passed else "FAIL",
        "scope": "NON_PROMOTIONAL frozen 5044-word reconstruction DOE",
        "selection_sha256": FROZEN_SELECTION_SHA,
        "parent_v8": {
            "local_gate_passed": v8_summary.get("local_gate_passed"),
            "changed_units": len(changed),
            "initial_o2_failed_occurrences": [r["occurrence"] for r in failed],
        },
        "forward_model": forward_identity,
        "reverse_model": {
            **reverse_identity,
            "required_opus_zip_sha256": o2.PINNED_RU_EN_SHA256,
            "hash_pin_passed": reverse_identity["opus_zip_sha256"] == o2.PINNED_RU_EN_SHA256,
        },
        "rescues": rescues,
        "rescue_count": len(rescue_back),
        "rescued_occurrences": sorted(rescue_back),
        "final_candidate": candidate_agg,
        "intervention_counts": dict(intervention_counts),
        "strong_intervention_failures": strong_intervention_failures,
        "latin_intervention_failures": latin_intervention_failures,
        "final_o2_failed_occurrences": [x["occurrence"] for x in final_failures],
        "final_o2_audits": final_audits,
        "contract": {
            "o2_trigger": "stage8-high-confidence-term-collapse/1 pinned RU->EN",
            "q_rescue": "mixed-case source stem + whole-context beam16/n-best16 + source-planned exact symbolic delimiter render",
            "glossary_used": False,
            "arbitrary_target_prose_editing": False,
            "missing_number_append": False,
            "semantic_correctness_claimed": False,
            "exact_F96_replaced": False,
        },
        "promotion_allowed": False,
        "promotion_blocker": "missing exact 0.30.40/F96 payload and rocketdict-numeric-integrity/3.2",
        "passed": passed,
    }
    (EVIDENCE / "stage8-v9-pinned-term-rescue.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (EVIDENCE / "units-v9.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not passed:
        raise SystemExit("Stage 8 v9 frozen reconstruction failed objective and/or pinned O-v2 gate")


if __name__ == "__main__":
    main()
