from __future__ import annotations

"""RocketDict Stage 8 / P-v2: case consistency inside clause/source-AST.

P-v1 proved that mixed-case source normalization repairs the local `refract`
translation behaviour, but whole-source OPUS hypotheses all corrupted `_3p 3t_`.
P-v2 changes only the integration level: apply the same source-derived casing
normalization BEFORE the already successful M/N clause-first + structural AST
pipeline, so protected technical tokens are rendered from source structure.

Acceptance is fail-closed:
* original-source numeric/order/delimiter/critical-token integrity;
* no ordinary Latin residue regression;
* frozen pinned O-v2 high-confidence term-retention pass;
* no glossary and no target editing.

Exact occurrence-444 mechanism probe only; not the full frozen 5044-word gate.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage8_g_nbest_probe import prepare_model  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_ghi_reconstruction_v7 as v7  # noqa: E402
import stage8_ghi_reconstruction_v8 as v8  # noqa: E402
import stage8_semantic_regression_proxy as o1  # noqa: E402
import stage8_semantic_term_retention_o2 as o2  # noqa: E402
import stage8_term_case_consistency_p1 as p1  # noqa: E402

OUT = Path("work-stage8-p2/evidence")


def main() -> None:
    eligible = p1.mixed_case_stems(p1.SOURCE)
    normalized, changes = p1.normalize_source(p1.SOURCE, eligible)
    if not changes:
        raise RuntimeError("P-v2 missing source case-consistency signal")

    translator, source_tok, target_tok, forward_identity = prepare_model()

    # Configure the already tested v8 decoding stack in this process. P-v2 only
    # changes the source casing that enters it.
    v6.PROSE_DECISIONS.clear()
    v7.CLAUSE_DECISIONS.clear()
    v8.CASE_RETRY_DECISIONS.clear()
    v5.translate_one = v8.translate_prose_case_retry
    v5.strong_quality_gate = v6.strong_quality_gate
    v7.clause_nbest = v8.clause_nbest_case_retry

    probe = v7.clause_first_ast_candidate(
        translator, source_tok, target_tok, normalized
    )
    target = probe["target"]
    forward_gate = v6.strong_quality_gate(p1.SOURCE, p1.BASELINE_RU, target)
    latin = v6.unprotected_latin_words(target)
    forward_passed = bool(forward_gate["passed"] and not latin)

    o1.EXPECTED_RU_EN_SHA256 = o2.PINNED_RU_EN_SHA256
    reverse, reverse_src_tok, reverse_tgt_tok, reverse_identity = o1.prepare_reverse_model()
    baseline_back, v8_back, candidate_back = o1.reverse_batch(
        reverse,
        reverse_src_tok,
        reverse_tgt_tok,
        [p1.BASELINE_RU, p1.V8_RU, target],
    )

    v8_term = o2.unit_term_audit({
        "occurrence": 444,
        "mechanism": "clean-v8",
        "source": p1.SOURCE,
        "baseline_ru": p1.BASELINE_RU,
        "candidate_ru": p1.V8_RU,
        "baseline_back_en": baseline_back,
        "candidate_back_en": v8_back,
    })
    p2_term = o2.unit_term_audit({
        "occurrence": 444,
        "mechanism": "P-v2-case-consistency-clause-AST",
        "source": p1.SOURCE,
        "baseline_ru": p1.BASELINE_RU,
        "candidate_ru": target,
        "baseline_back_en": baseline_back,
        "candidate_back_en": candidate_back,
    })

    passed = bool(forward_passed and p2_term["passed"])
    payload = {
        "schema": "rocketdict-stage8-term-case-consistency-probe/2",
        "status": "PASS" if passed else "FAIL",
        "case_id": "reconstruction-occurrence-444",
        "scope": "exact mechanism probe only",
        "source": p1.SOURCE,
        "mixed_case_signal": eligible,
        "normalized_source": normalized,
        "source_changes": changes,
        "forward_model": forward_identity,
        "reverse_model": {
            **reverse_identity,
            "required_opus_zip_sha256": o2.PINNED_RU_EN_SHA256,
            "hash_pin_passed": reverse_identity["opus_zip_sha256"] == o2.PINNED_RU_EN_SHA256,
        },
        "baseline": {"ru": p1.BASELINE_RU, "back_en": baseline_back},
        "clean_v8": {
            "ru": p1.V8_RU,
            "back_en": v8_back,
            "term_audit": v8_term,
        },
        "p2": {
            "ru": target,
            "back_en": candidate_back,
            "forward_gate": forward_gate,
            "unprotected_latin": latin,
            "term_audit": p2_term,
            "clause_ast": probe,
        },
        "mechanism": {
            "name": "P-v2-source-case-consistency-inside-clause-AST",
            "source_signal": "same Porter stem has TitleCase and lowercase source surfaces",
            "translation_glossary_used": False,
            "target_editing": False,
            "technical_token_handling": "existing source-side M/N clause/AST stack",
            "acceptance": "inherited forward integrity/no-Latin + frozen O-v2 term-retention",
        },
        "promotion_allowed": False,
        "next_action": (
            "If PASS, implement P-v2 generically as a new full frozen-5044 DOE cell and rerun the identical selection plus O-v2."
            if passed else
            "Reject P-v2 and preserve the negative result; do not weaken technical-token or O-v2 gates."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage8-term-case-consistency-p2.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not passed:
        raise SystemExit("P-v2 failed forward integrity and/or O-v2 term retention")


if __name__ == "__main__":
    main()
