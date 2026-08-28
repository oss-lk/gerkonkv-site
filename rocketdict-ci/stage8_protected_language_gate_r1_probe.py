from __future__ import annotations

"""R-v1 probe: protected-aware Cyrillic-share gate for the R1 occurrence-25 class.

Frozen independent R1 exposed a conflict: source-derived exact technical payload
preservation can reduce the raw target Cyrillic ratio even though the ordinary
translated prose is fully Russian.  R-v1 changes exactly one evaluator input:
the two existing Cyrillic-share thresholds are calculated after removing the
same protected [] and _..._ regions already excluded by the frozen v6
no-new-Latin prose gate.

Thresholds, numeric/order/delimiter/critical-token rules, OPUS decoder settings,
source AST, and no-new-Latin rule are unchanged.  No word/occurrence exception,
glossary, or target patch exists.

This is a mechanism/evaluator probe after the original R1 failure was preserved;
it is not a rewritten R1 result and is NON-PROMOTIONAL.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage8_ghi_reconstruction_gate as base  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_ghi_reconstruction_v7 as v7  # noqa: E402
import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
from stage8_g_nbest_probe import prepare_model  # noqa: E402

OUT = Path("work-stage8-protected-language-r1/evidence")
SOURCE = "They are signified by [Greek:\nletter]."


def prose_cyrillic_share(text: str) -> float:
    prose = v6.strip_protected(text)
    alpha = v6.ALPHA_RE.findall(prose)
    return len(v6.CYR_RE.findall(prose)) / len(alpha) if alpha else 0.0


def protected_intervention_gate(source: str, baseline: str, candidate: str) -> dict:
    old = base.intervention_quality_gate(source, baseline, candidate)
    reasons = [
        r for r in old["reasons"]
        if r not in {"cyrillic_share_regression", "low_cyrillic_share"}
    ]
    b_share = prose_cyrillic_share(baseline)
    c_share = prose_cyrillic_share(candidate)
    if c_share < b_share - 0.08:
        reasons.append("cyrillic_share_regression")
    if c_share < 0.60 and b_share >= 0.60:
        reasons.append("low_cyrillic_share")
    return {
        **old,
        "passed": not reasons,
        "reasons": reasons,
        "protected_language_share": {
            "contract": "stage8-protected-aware-language-share/1",
            "strip_function": "v6.strip_protected ([] and _..._)",
            "baseline_raw_share": old["baseline"]["cyrillic_alpha_share"],
            "candidate_raw_share": old["candidate"]["cyrillic_alpha_share"],
            "baseline_prose_share": b_share,
            "candidate_prose_share": c_share,
            "regression_threshold": 0.08,
            "absolute_floor": 0.60,
        },
    }


def protected_v5_strong_gate(source: str, baseline: str, candidate: str) -> dict:
    base_gate = protected_intervention_gate(source, baseline, candidate)
    order = v5.numeric_order_guard(source, candidate)
    delimiters = v5.delimiter_guard(source, candidate)
    critical = v5.critical_token_guard(source, candidate)
    reasons = list(base_gate["reasons"])
    if not order["passed"]:
        reasons.append("explicit_numeric_order")
    if not delimiters["passed"]:
        reasons.append("balanced_delimiter_integrity")
    if not critical["passed"]:
        reasons.append("critical_technical_tokens")
    return {
        "passed": not reasons,
        "reasons": reasons,
        "base_quality_gate": base_gate,
        "numeric_order": order,
        "delimiters": delimiters,
        "critical_tokens": critical,
    }


def protected_v6_strong_gate(source: str, baseline: str, candidate: str) -> dict:
    inherited = protected_v5_strong_gate(source, baseline, candidate)
    baseline_latin = v6.unprotected_latin_words(baseline)
    candidate_latin = v6.unprotected_latin_words(candidate)
    latin_passed = len(candidate_latin) <= len(baseline_latin)
    reasons = list(inherited["reasons"])
    if not latin_passed:
        reasons.append("new_unprotected_latin_words")
    return {
        **inherited,
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    translator, source_tok, target_tok, model_identity = prepare_model()
    baseline = v5.translate_batch(translator, source_tok, target_tok, [SOURCE])[0]
    baseline_quality = v5.extended_row(SOURCE, baseline)

    v6.PROSE_DECISIONS.clear()
    v7.CLAUSE_DECISIONS.clear()
    v8.CASE_RETRY_DECISIONS.clear()
    v5.translate_one = v8.translate_prose_case_retry
    v5.strong_quality_gate = protected_v6_strong_gate
    v7.clause_nbest = v8.clause_nbest_case_retry
    v5.ast_candidate = v7.clause_first_ast_candidate
    v6.strong_quality_gate = protected_v6_strong_gate

    probe = v5.ast_candidate(translator, source_tok, target_tok, SOURCE)
    candidate = probe["target"]
    old_gate = v6.BASE_STRONG_GATE(SOURCE, baseline, candidate)
    old_v6_gate = {
        **old_gate,
        "unprotected_latin_regression": {
            "baseline": v6.unprotected_latin_words(baseline),
            "candidate": v6.unprotected_latin_words(candidate),
        },
    }
    new_gate = protected_v6_strong_gate(SOURCE, baseline, candidate)

    payload = {
        "schema": "rocketdict-stage8-protected-aware-language-share-probe/1",
        "status": "PASS" if new_gate["passed"] else "FAIL",
        "scope": "NON_PROMOTIONAL post-R1 evaluator/mechanism probe",
        "failure_class_source": "independent R1 occurrence 25",
        "model_identity": model_identity,
        "source": SOURCE,
        "baseline": baseline,
        "baseline_quality": baseline_quality,
        "candidate": candidate,
        "candidate_mechanism": probe.get("mechanism"),
        "critical_tokens": v5.critical_token_guard(SOURCE, candidate),
        "old_raw_gate": old_v6_gate,
        "new_protected_gate": new_gate,
        "contract": {
            "changed_variable": "Cyrillic-share measurement surface only",
            "old_surface": "entire target including protected []/_..._ payloads",
            "new_surface": "ordinary target prose after existing v6.strip_protected",
            "regression_threshold_changed": False,
            "absolute_floor_changed": False,
            "numeric_rules_changed": False,
            "technical_token_rules_changed": False,
            "no_new_latin_rule_changed": False,
            "decoder_changed": False,
            "source_AST_changed": False,
            "occurrence_or_word_exception": False,
            "glossary_used": False,
            "target_patch_used": False,
            "original_R1_result_rewritten": False,
            "exact_F96_replaced": False
        },
        "promotion_allowed": False
    }
    (OUT / "stage8-protected-aware-language-share-probe.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not new_gate["passed"]:
        raise SystemExit("R-v1 protected-aware language gate did not close occurrence-25 failure class")


if __name__ == "__main__":
    main()
