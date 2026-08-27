from __future__ import annotations

"""RocketDict Stage 8 independent validation R1 for the frozen v9 mechanism stack.

This is the first EN->RU run on the source-only selection frozen by
stage8_validation_selection_r1.py. The validation set is disjoint from the
original frozen 5044/80 reconstruction screen.

Rules
-----
* Hard-pin validation selection SHA before inference.
* Do not change the selection, thresholds, or v9 mechanisms after seeing R1.
* Run the already-frozen v8 objective stack unchanged on the new units.
* Only if objective integrity passes, run the already-frozen pinned O-v2 audit.
* Q-v1 rescue is allowed only under the same data-dependent v9 trigger:
  O-v2 high-confidence collapse + source mixed-case stem signal.
* No new heuristic is introduced by this file.
* O-v1 paired scores are persisted only as diagnostics, not a hard semantic gate.

Passing remains NON-PROMOTIONAL because exact 0.30.40/F96 and
rocketdict-numeric-integrity/3.2 are still unavailable.
"""

from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_gate as base  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
import stage8_semantic_regression_proxy as o1  # noqa: E402
import stage8_semantic_term_retention_o2 as o2  # noqa: E402
import stage8_validation_selection_r1 as sel  # noqa: E402
import stage8_v9_term_rescue_gate as v9  # noqa: E402
from stage8_g_nbest_probe import prepare_model  # noqa: E402

OUT = Path("work-stage8-independent-validation-r1/evidence")
V8_UNITS = v5.EVIDENCE / "units.jsonl"
V8_SUMMARY = v5.EVIDENCE / "stage8-ghi-reconstruction.json"
EXPECTED_VALIDATION_SHA = "665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32"
EXPECTED_R0_SHA = "ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe"


def select_validation(units: list[dict]) -> tuple[list[dict], dict]:
    """Reproduce the already-frozen source-only R1 selection and hard-pin SHA."""
    r0, r0_meta = base.select_challenge(units)
    if r0_meta["selection_sha256"] != EXPECTED_R0_SHA:
        raise RuntimeError("R0 selection drift while excluding overlap")
    excluded = {u["occurrence"] for u in r0}

    eligible = []
    for u in units:
        if u["occurrence"] in excluded:
            continue
        row = dict(u)
        row["category"] = sel.source_category(row["source"])
        eligible.append(row)

    buckets = {name: [] for name in sel.QUOTAS}
    for u in eligible:
        buckets[u["category"]].append(u)

    selected: dict[int, dict] = {}
    category_words = Counter()
    for name, budget in sel.QUOTAS.items():
        used = 0
        for u in sorted(buckets[name], key=lambda x: sel.rank(x, f"{sel.SELECTOR_SALT}:{name}")):
            if used >= budget and used > 0:
                break
            selected[u["occurrence"]] = u
            used += u["words"]
            category_words[name] += u["words"]

    current = sum(u["words"] for u in selected.values())
    if current < sel.TARGET_WORDS:
        remaining = [u for u in eligible if u["occurrence"] not in selected]
        for u in sorted(remaining, key=lambda x: sel.rank(x, f"{sel.SELECTOR_SALT}:fill")):
            selected[u["occurrence"]] = u
            category_words[u["category"]] += u["words"]
            current += u["words"]
            if current >= sel.TARGET_WORDS:
                break

    out = sorted(selected.values(), key=lambda x: x["occurrence"])
    overlap = sorted(excluded & {u["occurrence"] for u in out})
    serialized = sel.serialize(out)
    sha = base.text_sha256(serialized)
    if overlap:
        raise RuntimeError(f"validation overlap with R0: {overlap}")
    if sha != EXPECTED_VALIDATION_SHA:
        raise RuntimeError(f"validation selection drift: {sha} != {EXPECTED_VALIDATION_SHA}")

    meta = {
        "selector": "rocketdict-stage8-independent-validation-selection/1",
        "selection_sha256": sha,
        "actual_words": sum(u["words"] for u in out),
        "units": len(out),
        "category_unit_counts": dict(Counter(u["category"] for u in out)),
        "category_word_counts": dict(category_words),
        "overlap_with_r0": overlap,
        "source_only_frozen_before_mt": True,
    }
    return out, meta


def reverse_map(reverse, src_tok, tgt_tok, rows: list[dict], field: str) -> dict[int, str]:
    texts = [r[field] for r in rows]
    backs = o1.reverse_batch(reverse, src_tok, tgt_tok, texts) if texts else []
    return {r["occurrence"]: b for r, b in zip(rows, backs)}


def row_objective_failures(row: dict) -> list[str]:
    q = row["candidate_quality"]
    failed = []
    if q["empty"]:
        failed.append("empty")
    if not q["numeric"]["passed"]:
        failed.append("numeric")
    if not q["numeric_order"]["passed"]:
        failed.append("numeric_order")
    if not q["delimiters"]["passed"]:
        failed.append("delimiters")
    if not q["critical_tokens"]["passed"]:
        failed.append("critical_tokens")
    if not q["figure"]["passed"]:
        failed.append("figure")
    if q["length_anomaly"]:
        failed.append("length")
    if q["identity"]:
        failed.append("identity")
    if row["mechanism"] != "baseline-unchanged":
        gate = v6.strong_quality_gate(row["source"], row["baseline"], row["candidate"])
        if not gate["passed"]:
            failed.append("strong_intervention_gate")
        if len(v6.unprotected_latin_words(row["candidate"])) > len(v6.unprotected_latin_words(row["baseline"])):
            failed.append("new_unprotected_latin")
    return failed


def write_failure(stage: str, selection: dict, v8_summary: dict, rows: list[dict], error: str | None) -> None:
    failures = [
        {
            "occurrence": r["occurrence"],
            "category": r["category"],
            "mechanism": r["mechanism"],
            "reasons": row_objective_failures(r),
            "source": r["source"],
            "baseline": r["baseline"],
            "candidate": r["candidate"],
        }
        for r in rows
        if row_objective_failures(r)
    ]
    payload = {
        "schema": "rocketdict-stage8-independent-validation-r1/1",
        "status": "FAIL",
        "failed_stage": stage,
        "selection": selection,
        "parent_v8_summary": v8_summary,
        "parent_v8_error": error,
        "objective_failure_units": failures,
        "promotion_allowed": False,
        "rule": "Do not alter the frozen validation selection or existing v9 gates in response to this result. Classify any new failure before a separate DOE branch is attempted.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage8-independent-validation-r1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (OUT / "units-r1.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Swap only the selector. The v8 mechanism/gates themselves remain unchanged.
    v5.select_challenge = select_validation

    parent_error: str | None = None
    try:
        v8.main()
    except SystemExit as exc:
        parent_error = str(exc)

    v8_summary = json.loads(V8_SUMMARY.read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in V8_UNITS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selection = v8_summary["selection"]
    if selection["selection_sha256"] != EXPECTED_VALIDATION_SHA:
        raise RuntimeError("independent R1 evidence selection SHA drift")
    if len(rows) != selection["units"]:
        raise RuntimeError("independent R1 row count mismatch")

    objective_failures = [r for r in rows if row_objective_failures(r)]
    parent_objective_pass = bool(v8_summary.get("local_gate_passed") and parent_error is None and not objective_failures)
    if not parent_objective_pass:
        write_failure("v8_objective_stack", selection, v8_summary, rows, parent_error)
        raise SystemExit("Independent validation R1 failed frozen v8 objective stack")

    changed = [r for r in rows if r["baseline"] != r["candidate"]]

    # Pinned reverse model and unchanged O-v2 term-collapse gate.
    o1.EXPECTED_RU_EN_SHA256 = o2.PINNED_RU_EN_SHA256
    reverse, rev_src_tok, rev_tgt_tok, reverse_identity = o1.prepare_reverse_model()
    baseline_back = reverse_map(reverse, rev_src_tok, rev_tgt_tok, changed, "baseline")
    candidate_back = reverse_map(reverse, rev_src_tok, rev_tgt_tok, changed, "candidate")

    initial_audits: dict[int, dict] = {}
    initial_failed = []
    for r in changed:
        occ = r["occurrence"]
        audit = o2.unit_term_audit({
            "occurrence": occ,
            "mechanism": r["mechanism"],
            "source": r["source"],
            "baseline_ru": r["baseline"],
            "candidate_ru": r["candidate"],
            "baseline_back_en": baseline_back[occ],
            "candidate_back_en": candidate_back[occ],
        })
        initial_audits[occ] = audit
        if not audit["passed"]:
            initial_failed.append(r)

    # Same Q rescue as v9, only for pinned O-v2 failures.
    rescue_records = []
    rescue_back: dict[int, str] = {}
    forward_identity = None
    if initial_failed:
        translator, source_tok, target_tok, forward_identity = prepare_model()
        for row in initial_failed:
            occ = row["occurrence"]
            eligible, normalized, source_changes, candidates = v9.generic_q_hypotheses(
                translator, source_tok, target_tok, row["source"], row["baseline"]
            )
            forward_eligible = [c for c in candidates if c.get("forward_eligible")]
            backs = o1.reverse_batch(
                reverse, rev_src_tok, rev_tgt_tok,
                [c["canonical_target"] for c in forward_eligible],
            ) if forward_eligible else []

            selected = None
            for c, back in zip(forward_eligible, backs):
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

            rescue_records.append({
                "occurrence": occ,
                "initial_o2": initial_audits[occ],
                "mixed_case_signal": eligible,
                "normalized_source": normalized,
                "source_changes": source_changes,
                "candidate_count": len(candidates),
                "forward_eligible_count": len(forward_eligible),
                "selected": selected,
                "all_candidates": candidates,
            })
            if selected is not None:
                row["candidate"] = selected["canonical_target"]
                row["mechanism"] = "Q-v1-pinned-O2-rescue"
                row["candidate_quality"] = v5.extended_row(row["source"], row["candidate"])
                rescue_back[occ] = selected["candidate_back_en"]

    candidate_agg = v5.extended_aggregate(rows, "candidate_quality")
    objective_failures_after = [r for r in rows if row_objective_failures(r)]

    # Final O-v2 and diagnostic O-v1 on all interventions.
    final_audits = []
    final_o1 = []
    final_failures = []
    for r in rows:
        if r["baseline"] == r["candidate"]:
            continue
        occ = r["occurrence"]
        if occ in rescue_back:
            back = rescue_back[occ]
        elif occ in candidate_back:
            back = candidate_back[occ]
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
        final_o1.append({
            "occurrence": occ,
            "mechanism": r["mechanism"],
            "scores": o1.score_pair(r["source"], baseline_back[occ], back),
        })

    intervention_counts = Counter(r["mechanism"] for r in rows if r["mechanism"] != "baseline-unchanged")
    passed = bool(
        not objective_failures_after
        and not final_failures
        and len(rescue_back) == len(initial_failed)
    )

    o1_deltas = [x["scores"]["delta_candidate_minus_baseline"]["composite"] for x in final_o1]
    payload = {
        "schema": "rocketdict-stage8-independent-validation-r1/1",
        "status": "PASS" if passed else "FAIL",
        "scope": "NON_PROMOTIONAL independent source-only-frozen validation of v9 mechanisms",
        "selection": selection,
        "selection_contract": {
            "expected_sha256": EXPECTED_VALIDATION_SHA,
            "disjoint_from_r0_sha256": EXPECTED_R0_SHA,
            "selection_was_frozen_before_first_mt": True,
            "selection_tuning_after_results_allowed": False,
        },
        "parent_v8": {
            "objective_pass": parent_objective_pass,
            "changed_units": len(changed),
            "initial_o2_failed_occurrences": [r["occurrence"] for r in initial_failed],
        },
        "forward_model_for_q": forward_identity,
        "reverse_model": {
            **reverse_identity,
            "required_opus_zip_sha256": o2.PINNED_RU_EN_SHA256,
            "hash_pin_passed": reverse_identity["opus_zip_sha256"] == o2.PINNED_RU_EN_SHA256,
        },
        "rescues": rescue_records,
        "rescue_count": len(rescue_back),
        "rescued_occurrences": sorted(rescue_back),
        "final_candidate": candidate_agg,
        "intervention_counts": dict(intervention_counts),
        "objective_failure_occurrences_after": [r["occurrence"] for r in objective_failures_after],
        "final_o2_failed_occurrences": [x["occurrence"] for x in final_failures],
        "final_o2_audits": final_audits,
        "o1_diagnostic": {
            "hard_gate": False,
            "interventions": len(final_o1),
            "mean_composite_delta": (sum(o1_deltas) / len(o1_deltas)) if o1_deltas else 0.0,
            "min_composite_delta": min(o1_deltas) if o1_deltas else 0.0,
            "max_composite_delta": max(o1_deltas) if o1_deltas else 0.0,
            "candidate_better": sum(d > 0 for d in o1_deltas),
            "candidate_worse": sum(d < 0 for d in o1_deltas),
            "rows": sorted(final_o1, key=lambda x: x["scores"]["delta_candidate_minus_baseline"]["composite"]),
        },
        "contract": {
            "mechanism_stack_changed_from_v9": False,
            "new_heuristics_introduced": False,
            "o2_trigger": "stage8-high-confidence-term-collapse/1",
            "q_rescue": "Q-v1 only after pinned O-v2 failure and source mixed-case signal",
            "glossary_used": False,
            "arbitrary_target_prose_editing": False,
            "semantic_correctness_claimed": False,
            "exact_F96_replaced": False,
        },
        "promotion_allowed": False,
        "promotion_blocker": "missing exact 0.30.40/F96 payload and rocketdict-numeric-integrity/3.2",
        "passed": passed,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage8-independent-validation-r1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (OUT / "units-r1.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not passed:
        raise SystemExit("Stage 8 independent validation R1 failed frozen v9 objective and/or pinned O-v2 contract")


if __name__ == "__main__":
    main()
