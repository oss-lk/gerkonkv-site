from __future__ import annotations

"""Checkpointed latency probe for frozen R1 occurrence 24.

Diagnostic only.  Replays the exact v8 per-unit decision path while writing a
checkpoint before and after every potentially expensive model operation.  This
file must never be used as validation evidence or as a replacement result.
"""

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_gate as base  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_ghi_reconstruction_v7 as v7  # noqa: E402
import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
import stage8_independent_validation_r1 as r1  # noqa: E402
from stage8_g_nbest_probe import prepare_model  # noqa: E402
from real_opus_gate import OPTICKS_URL, download  # noqa: E402

OUT = Path("work-stage8-r1-occ24-probe")
PROGRESS = OUT / "progress.json"
CORPUS = OUT / "opticks.txt"
EVENTS: list[dict] = []
STARTED = time.perf_counter()


def mark(stage: str, **extra) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    row = {
        "stage": stage,
        "elapsed_seconds": time.perf_counter() - STARTED,
        **extra,
    }
    EVENTS.append(row)
    PROGRESS.write_text(json.dumps({
        "schema": "rocketdict-stage8-r1-occ24-phase-probe/1",
        "diagnostic_only": True,
        "occurrence": 24,
        "selection_sha256": r1.EXPECTED_VALIDATION_SHA,
        "events": EVENTS,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(row, ensure_ascii=False), flush=True)


def candidate_gate(source: str, baseline: str, probe: dict) -> tuple[str | None, dict]:
    target = probe.get("target") or probe.get("selected_text")
    if target is None:
        return None, {"passed": False, "reasons": ["no_target"]}
    gate = v6.strong_quality_gate(source, baseline, target)
    return (target if gate["passed"] else None), gate


def qbrief(q: dict) -> dict:
    return {
        "empty": q["empty"],
        "numeric": q["numeric"]["passed"],
        "numeric_order": q["numeric_order"]["passed"],
        "delimiters": q["delimiters"]["passed"],
        "critical_tokens": q["critical_tokens"]["passed"],
        "figure": q["figure"]["passed"],
        "length_anomaly": q["length_anomaly"],
        "identity": q["identity"],
        "cyrillic_alpha_share": q["cyrillic_alpha_share"],
    }


def main() -> None:
    mark("start")
    download(OPTICKS_URL, CORPUS)
    corpus_sha = base.sha256_path(CORPUS)
    if corpus_sha != base.EXPECTED_OPTICKS_SHA256:
        raise RuntimeError("Opticks SHA mismatch")
    units = base.split_units(CORPUS.read_text(encoding="utf-8-sig", errors="replace"))
    selected, meta = r1.select_validation(units)
    if meta["selection_sha256"] != r1.EXPECTED_VALIDATION_SHA:
        raise RuntimeError("R1 selection drift")
    unit = next(u for u in selected if u["occurrence"] == 24)
    source = unit["source"]
    mark("selection_ready", words=unit["words"], source=source)

    mark("prepare_model_begin")
    translator, source_tok, target_tok, model_identity = prepare_model()
    mark("prepare_model_end", model_identity=model_identity)

    # Exact v8 monkey patches used by v8.main().
    v6.PROSE_DECISIONS.clear()
    v7.CLAUSE_DECISIONS.clear()
    v8.CASE_RETRY_DECISIONS.clear()
    v5.translate_one = v8.translate_prose_case_retry
    v5.strong_quality_gate = v6.strong_quality_gate
    v7.clause_nbest = v8.clause_nbest_case_retry
    v5.ast_candidate = v7.clause_first_ast_candidate

    mark("baseline_begin")
    baseline = v5.translate_batch(translator, source_tok, target_tok, [source])[0]
    baseline_q = v5.extended_row(source, baseline)
    mark("baseline_end", baseline=baseline, quality=qbrief(baseline_q), latin=v6.unprotected_latin_words(baseline))

    chosen = baseline
    mechanism = "baseline-unchanged"

    if not baseline_q["numeric"]["passed"]:
        mark("I_begin")
        p = v5.i_structural_candidate(translator, source_tok, target_tok, source)
        cand, gate = candidate_gate(source, baseline, p)
        mark("I_end", candidate=p.get("target") or p.get("selected_text"), gate=gate)
        if cand is not None:
            chosen, mechanism = cand, "I-v2"

    if mechanism == "baseline-unchanged" and not baseline_q["numeric"]["passed"]:
        mark("H_table_begin")
        p = v5.h_table_candidate(translator, source_tok, target_tok, source)
        cand, gate = candidate_gate(source, baseline, p)
        mark("H_table_end", applicable=p.get("applicable"), candidate=p.get("target") or p.get("selected_text"), gate=gate)
        if cand is not None:
            chosen, mechanism = cand, "H-table"

    if mechanism == "baseline-unchanged" and not baseline_q["numeric"]["passed"]:
        mark("H_document_id_begin")
        p = v5.h_document_id_candidate(translator, source_tok, target_tok, source)
        cand, gate = candidate_gate(source, baseline, p)
        mark("H_document_id_end", applicable=p.get("applicable"), candidate=p.get("target") or p.get("selected_text"), gate=gate)
        if cand is not None:
            chosen, mechanism = cand, "H-document-id"

    if mechanism == "baseline-unchanged" and not baseline_q["figure"]["passed"]:
        mark("H_figure_begin")
        p = v5.h_figure_candidate(translator, source_tok, target_tok, source)
        cand, gate = candidate_gate(source, baseline, p)
        mark("H_figure_end", applicable=p.get("applicable"), candidate=p.get("target") or p.get("selected_text"), gate=gate)
        if cand is not None:
            chosen, mechanism = cand, "H-figure"

    if mechanism == "baseline-unchanged" and v5.numeric_counter(source) and not baseline_q["numeric"]["passed"]:
        mark("G_nbest_begin")
        g = v5.g_nbest_rescue(translator, source_tok, target_tok, source, baseline)
        selected_text = g.get("selected_text")
        gate = v6.strong_quality_gate(source, baseline, selected_text) if selected_text is not None else {"passed": False, "reasons": ["no_target"]}
        mark("G_nbest_end", selected_text=selected_text, gate=gate)
        if selected_text is not None and gate["passed"]:
            chosen, mechanism = selected_text, "G-nbest-8x8-critical-gated"

    current_q = v5.extended_row(source, chosen)
    needs_ast = (
        not current_q["numeric"]["passed"]
        or not current_q["numeric_order"]["passed"]
        or not current_q["delimiters"]["passed"]
        or not current_q["critical_tokens"]["passed"]
    )
    mark("pre_AST", mechanism=mechanism, quality=qbrief(current_q), needs_ast=needs_ast)
    if needs_ast:
        mark("AST_begin")
        p = v5.ast_candidate(translator, source_tok, target_tok, source)
        mark("AST_generated", candidate=p.get("target"), clauses=len(p.get("clauses", [])))
        cand, gate = candidate_gate(source, baseline, p)
        mark("AST_gate_end", gate=gate)
        if cand is not None:
            chosen, mechanism = cand, "M-v1-clause-first-integrity-translation"

    final_q = v5.extended_row(source, chosen)
    mark(
        "complete",
        mechanism=mechanism,
        baseline=baseline,
        candidate=chosen,
        final_quality=qbrief(final_q),
        prose_decisions=len(v6.PROSE_DECISIONS),
        clause_decisions=len(v7.CLAUSE_DECISIONS),
        case_retry_decisions=len(v8.CASE_RETRY_DECISIONS),
    )


if __name__ == "__main__":
    main()
