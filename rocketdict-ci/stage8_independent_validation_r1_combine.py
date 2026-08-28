from __future__ import annotations

"""Recombine parallel R1 forward shards and resume the unchanged R1 semantic gate.

The parallel jobs only evaluate the already-frozen v8 mechanism per unit.  This
combiner proves that the union is exactly the source-only-frozen 5143/103 set,
recomputes the original GLOBAL v8 aggregate, then calls the existing monolithic
R1 semantic/O-v2/Q-v1 continuation without re-running forward inference.

No model decision, threshold, selector, or intervention rule is changed.
"""

from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_gate as base  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_independent_validation_r1 as r1  # noqa: E402
import stage8_validation_selection_r1 as sel  # noqa: E402

SHARD_COUNT = 8
DOWNLOAD_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("downloaded-r1-forward")
COMBINE_OUT = Path("work-stage8-independent-validation-r1/evidence")


def load_shards() -> tuple[list[dict], list[dict]]:
    wrappers = []
    rows = []
    wrapper_paths = sorted(DOWNLOAD_ROOT.glob("**/forward-shard.json"))
    unit_paths = sorted(DOWNLOAD_ROOT.glob("**/units-shard.jsonl"))
    if len(wrapper_paths) != SHARD_COUNT or len(unit_paths) != SHARD_COUNT:
        raise RuntimeError(
            f"expected {SHARD_COUNT} shard wrappers/units, got "
            f"{len(wrapper_paths)}/{len(unit_paths)}"
        )
    by_dir = {p.parent: p for p in unit_paths}
    for wp in wrapper_paths:
        if wp.parent not in by_dir:
            raise RuntimeError(f"missing units beside {wp}")
        wrapper = json.loads(wp.read_text(encoding="utf-8"))
        wrappers.append(wrapper)
        shard_rows = [
            json.loads(line)
            for line in by_dir[wp.parent].read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(shard_rows) != wrapper["row_count"]:
            raise RuntimeError(f"row count drift in {wp.parent}")
        rows.extend(shard_rows)
    return wrappers, rows


def verify_union(wrappers: list[dict], rows: list[dict]) -> dict:
    shard_ids = sorted(w["shard"]["shard_index"] for w in wrappers)
    if shard_ids != list(range(SHARD_COUNT)):
        raise RuntimeError(f"shard ids are not complete: {shard_ids}")
    if any(w["shard"]["shard_count"] != SHARD_COUNT for w in wrappers):
        raise RuntimeError("shard-count contract drift")
    if any(w["mechanism_stack_changed_from_v9"] for w in wrappers):
        raise RuntimeError("a forward shard claims v9 mechanism drift")

    full_shas = {w["full_selection"]["selection_sha256"] for w in wrappers}
    occ_hashes = {w["full_occurrences_sha256"] for w in wrappers}
    if full_shas != {r1.EXPECTED_VALIDATION_SHA}:
        raise RuntimeError(f"full selection pin mismatch across shards: {full_shas}")
    if len(occ_hashes) != 1:
        raise RuntimeError("shards disagree about full occurrence identity")

    rows.sort(key=lambda x: x["occurrence"])
    occurrences = [r["occurrence"] for r in rows]
    if len(rows) != 103 or len(set(occurrences)) != 103:
        raise RuntimeError(f"combined R1 must contain 103 unique rows, got {len(rows)}/{len(set(occurrences))}")
    combined_occ_hash = base.text_sha256(",".join(map(str, occurrences)))
    if combined_occ_hash not in occ_hashes:
        raise RuntimeError("combined occurrence identity differs from every shard's full selection")

    reconstructed_units = [
        {
            "occurrence": r["occurrence"],
            "category": r["category"],
            "words": r["source_words"],
            "source": r["source"],
        }
        for r in rows
    ]
    serialized = sel.serialize(reconstructed_units)
    combined_sha = base.text_sha256(serialized)
    if combined_sha != r1.EXPECTED_VALIDATION_SHA:
        raise RuntimeError(f"combined serialized selection drift: {combined_sha}")

    return {
        "selector": "rocketdict-stage8-independent-validation-selection/1",
        "selection_sha256": combined_sha,
        "actual_words": sum(r["source_words"] for r in rows),
        "units": len(rows),
        "category_unit_counts": dict(Counter(r["category"] for r in rows)),
        "category_word_counts": {
            name: sum(r["source_words"] for r in rows if r["category"] == name)
            for name in sel.QUOTAS
        },
        "overlap_with_r0": [],
        "source_only_frozen_before_mt": True,
        "parallel_execution": {
            "shards": SHARD_COUNT,
            "partition_rule": "stable full-selection position modulo shard_count",
            "mechanism_or_threshold_change": False,
        },
    }


def global_v8_summary(rows: list[dict], selection: dict) -> dict:
    baseline_agg = v5.extended_aggregate(rows, "baseline_quality")
    candidate_agg = v5.extended_aggregate(rows, "candidate_quality")
    objective_failures = [r for r in rows if r1.row_objective_failures(r)]
    strong_intervention_failures = sum(
        r["mechanism"] != "baseline-unchanged"
        and not v6.strong_quality_gate(r["source"], r["baseline"], r["candidate"])["passed"]
        for r in rows
    )
    latin_regressions = sum(
        r["mechanism"] != "baseline-unchanged"
        and len(v6.unprotected_latin_words(r["candidate"])) > len(v6.unprotected_latin_words(r["baseline"]))
        for r in rows
    )
    global_pass = bool(
        candidate_agg["empty"] == 0
        and candidate_agg["numeric_fail_units"] == 0
        and candidate_agg["numeric_order_fail_units"] == 0
        and candidate_agg["delimiter_fail_units"] == 0
        and candidate_agg["critical_token_fail_units"] == 0
        and candidate_agg["figure_fail_units"] == 0
        and candidate_agg["length_anomaly_units"] == 0
        and candidate_agg["identity_units"] == 0
        and strong_intervention_failures == 0
        and latin_regressions == 0
        and not objective_failures
        and candidate_agg["mean_cyrillic_alpha_share"] >= baseline_agg["mean_cyrillic_alpha_share"] - 0.01
    )
    return {
        "schema": "rocketdict-stage8-independent-validation-r1-recombined-v8/1",
        "status": "NON_PROMOTIONAL_RECONSTRUCTION",
        "selection": selection,
        "baseline": baseline_agg,
        "candidate": candidate_agg,
        "comparison": {
            "changed_units": sum(r["baseline"] != r["candidate"] for r in rows),
            "intervention_counts": dict(Counter(
                r["mechanism"] for r in rows if r["mechanism"] != "baseline-unchanged"
            )),
            "strong_intervention_failures": strong_intervention_failures,
            "cyrillic_share_delta": candidate_agg["mean_cyrillic_alpha_share"] - baseline_agg["mean_cyrillic_alpha_share"],
        },
        "v6_latin_regression_units": latin_regressions,
        "objective_failure_occurrences": [r["occurrence"] for r in objective_failures],
        "local_gate_passed": global_pass,
        "execution_contract": {
            "same_v8_per_unit_code": True,
            "parallelism_only": True,
            "global_aggregate_recomputed_after_union": True,
        },
        "promotion_allowed": False,
    }


def main() -> None:
    wrappers, rows = load_shards()
    selection = verify_union(wrappers, rows)
    summary = global_v8_summary(rows, selection)

    # Materialize the exact files the existing monolithic R1 semantic continuation
    # expects, then suppress only its expensive forward rerun.
    r1.V8_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    r1.V8_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with r1.V8_UNITS.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    COMBINE_OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "rocketdict-stage8-independent-validation-r1-parallel-manifest/1",
        "selection": selection,
        "forward_shards": [
            {
                "shard_index": w["shard"]["shard_index"],
                "units": w["row_count"],
                "words": w["shard"]["actual_words"],
                "v8_parent_error": w["v8_parent_error"],
            }
            for w in sorted(wrappers, key=lambda x: x["shard"]["shard_index"])
        ],
        "recombined_v8": summary,
        "next_stage": "unchanged monolithic R1 O-v2/Q-v1 continuation",
        "mechanism_or_threshold_change": False,
        "promotion_allowed": False,
    }
    (COMBINE_OUT / "parallel-forward-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "R1_FORWARD_RECOMBINED",
        "selection_sha256": selection["selection_sha256"],
        "units": selection["units"],
        "words": selection["actual_words"],
        "global_v8_pass": summary["local_gate_passed"],
        "objective_failure_occurrences": summary["objective_failure_occurrences"],
    }, ensure_ascii=False, indent=2), flush=True)

    # Reuse the already-frozen semantic/Q code path exactly.  It will stop after
    # objective failure, or continue through pinned O-v2 and Q-v1 otherwise.
    r1.v8.main = lambda: None
    r1.main()


if __name__ == "__main__":
    main()
