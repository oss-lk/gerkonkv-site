from __future__ import annotations

"""Run the pinned TC-big alternative MT over every current Product numeric failure.

This is a research-only inventory extension of
``real_translation_full_opticks_alternative_mt_feasibility.py``.  The focused
DOE first proved that the alternate model can materially change failure classes;
this wrapper widens the exact same model/runtime/generation contract to all 27
immutable planner-v8 Product numeric hard-failure units while retaining the
parent/chunk probes for selective context 669.
"""

import importlib.util
import json
from pathlib import Path
from typing import Any


BASE_PATH = Path(__file__).with_name(
    "real_translation_full_opticks_alternative_mt_feasibility.py"
)
SPEC = importlib.util.spec_from_file_location("rocketdict_alt_mt_focused", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load focused alternative-MT DOE")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
FOCUSED_LOAD_CASES = BASE._load_cases
BASE.SCHEMA = "rocketdict-full-opticks-alternative-mt-feasibility/2"


def _load_all_cases(
    baseline: dict[str, Any],
    optin: dict[str, Any],
) -> list[dict[str, Any]]:
    failures = list(baseline.get("numeric_failures") or [])
    if len(failures) != 27:
        raise RuntimeError(f"expected 27 Product numeric failures, got {len(failures)}")
    known = {
        int(sequence): family
        for sequence, (_start, _end, family) in BASE.EXPECTED_RESIDUALS.items()
    }
    planner_cases: list[dict[str, Any]] = []
    seen_sequences: set[int] = set()
    for row in sorted(failures, key=lambda value: int(value["planned_sequence"])):
        sequence = int(row["planned_sequence"])
        if sequence in seen_sequences:
            raise RuntimeError(f"duplicate Product failure sequence {sequence}")
        seen_sequences.add(sequence)
        planner_cases.append(
            {
                "case_id": f"planner_failure_{sequence}",
                "family": known.get(sequence, "product_numeric_hard_failure"),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "baseline_target_text": str(row["product_target_text"]),
                "baseline_planned_sequence": sequence,
                "source_origin": "planner_v8_numeric_failure",
                "baseline_rank0_verdict": dict(row.get("rank0_verdict") or {}),
            }
        )

    focused = FOCUSED_LOAD_CASES(baseline, optin)
    context_cases = [
        dict(case)
        for case in focused
        if str(case.get("source_origin") or "").startswith("selective_rescue_")
    ]
    if len(context_cases) != 4:
        raise RuntimeError("expected whole context 669 plus its three rescue chunks")
    return context_cases[:1] + planner_cases + context_cases[1:]


BASE._load_cases = _load_all_cases


def main() -> int:
    result = int(BASE.main())
    root = Path(
        __import__("os").environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/baseline/full-opticks-numeric-stress",
        )
    ).resolve()
    output = root / "full-opticks-alternative-mt-feasibility.json"
    payload = json.loads(output.read_text(encoding="utf-8"))
    if payload.get("schema") != BASE.SCHEMA:
        raise RuntimeError("full-failure alternative-MT schema drift")
    if int(payload.get("case_count") or -1) != 31:
        raise RuntimeError("full-failure alternative-MT inventory must contain 31 cases")
    planner_cases = [
        row for row in payload.get("cases") or []
        if row.get("source_origin") == "planner_v8_numeric_failure"
    ]
    if len(planner_cases) != 27:
        raise RuntimeError("full-failure alternative-MT inventory lost Product failures")
    payload["inventory_scope"] = "all_27_planner_v8_product_numeric_failures_plus_context_669"
    payload["planner_failure_case_count"] = 27
    payload["planner_failure_sequences"] = [
        int(row["baseline_planned_sequence"]) for row in planner_cases
    ]
    payload["planner_failures_with_any_strict_alternative"] = [
        int(row["baseline_planned_sequence"])
        for row in planner_cases
        if int(row.get("strict_mechanical_hypothesis_count") or 0) > 0
    ]
    payload.pop("evidence_sha256", None)
    payload["evidence_sha256"] = BASE._canonical_sha(payload)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "planner_failure_case_count": payload["planner_failure_case_count"],
                "planner_failures_with_any_strict_alternative": payload[
                    "planner_failures_with_any_strict_alternative"
                ],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
