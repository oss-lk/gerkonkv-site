from __future__ import annotations

"""RocketDict Stage 8 / Q-v1: whole-context MT + source-planned structure render.

P-v1 and P-v2 expose a clean trade-off on occurrence 444:
* whole-sentence mixed-case-normalized MT gives the desired `refract` behaviour
  but damages one source technical emphasis delimiter (`_3p 3t_` -> `3p 3t_`);
* clause/AST translation preserves the token but shorter context causes local
  semantic collapse (`refraction` -> `отвлечение`).

Q-v1 keeps whole-sentence context and pre-parses symbolic emphasis nodes BEFORE
MT.  After a model hypothesis is generated, the renderer is allowed to
canonicalize ONLY the already-parsed technical node surface when:
* its alphanumeric payload is present exactly once in the target;
* payload characters/order are unchanged;
* the only difference is missing/extra surrounding Gutenberg `_` delimiters.

This is source-planned structural rendering.  It does not add a missing number,
invent a translation, consult a glossary, or repair arbitrary target prose.
Ambiguous/mutated payloads fail closed.

Acceptance: inherited forward integrity/no-Latin + frozen pinned O-v2 term
retention. Exact occurrence-444 mechanism probe only.
"""

import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage8_g_nbest_probe import prepare_model  # noqa: E402
import stage8_ghi_reconstruction_v5 as v5  # noqa: E402
import stage8_ghi_reconstruction_v6 as v6  # noqa: E402
import stage8_semantic_regression_proxy as o1  # noqa: E402
import stage8_semantic_term_retention_o2 as o2  # noqa: E402
import stage8_term_case_consistency_p1 as p1  # noqa: E402

OUT = Path("work-stage8-q1/evidence")
EMPH_RE = re.compile(r"_([^_\n]+)_")


def parse_symbolic_nodes(source: str) -> list[dict]:
    nodes = []
    for m in EMPH_RE.finditer(source):
        inner = m.group(1)
        if not v5.is_symbolic_emphasis(inner):
            continue
        nodes.append({
            "kind": "symbolic-emphasis",
            "source_start": m.start(),
            "source_end": m.end(),
            "source_text": m.group(0),
            "payload": inner,
            "target_render": m.group(0),
        })
    return nodes


def canonicalize_symbolic_nodes(target: str, nodes: list[dict]) -> tuple[str | None, list[dict]]:
    rendered = target
    evidence = []
    for node in nodes:
        payload = node["payload"]
        # Exact source node already survived: record and leave untouched.
        if rendered.count(node["target_render"]) == 1:
            evidence.append({**node, "mode": "exact-survival", "changed": False})
            continue

        # Only delimiters may differ. Whitespace inside the payload is permitted
        # to normalize to one-or-more spaces; letters/digits and their order are exact.
        atoms = re.split(r"(\s+)", payload)
        body = "".join(r"\s+" if x.isspace() else re.escape(x) for x in atoms if x)
        pattern = re.compile(
            rf"(?<![A-Za-z0-9])(?P<lead>_?)(?P<body>{body})(?P<trail>_?)(?![A-Za-z0-9])"
        )
        matches = list(pattern.finditer(rendered))
        if len(matches) != 1:
            evidence.append({
                **node,
                "mode": "ambiguous-or-missing-payload",
                "match_count": len(matches),
                "changed": False,
            })
            return None, evidence
        m = matches[0]
        # Do not touch an exact-looking but payload-mutated string: the regex has
        # already required exact alphanumerics/order; only underscores/spacing vary.
        before = m.group(0)
        replacement = node["target_render"]
        rendered = rendered[:m.start()] + replacement + rendered[m.end():]
        evidence.append({
            **node,
            "mode": "source-planned-delimiter-canonicalization",
            "target_before": before,
            "target_after": replacement,
            "changed": before != replacement,
        })
    return rendered, evidence


def decode_forward(translator, source_tok, target_tok, normalized_source: str, nodes: list[dict]) -> list[dict]:
    tokens = source_tok.encode(normalized_source, out_type=str)
    result = translator.translate_batch(
        [tokens], beam_size=16, num_hypotheses=16, return_scores=True, max_batch_size=1
    )[0]
    rows = []
    for rank, hyp in enumerate(result.hypotheses):
        raw = target_tok.decode(hyp).strip()
        canonical, structure = canonicalize_symbolic_nodes(raw, nodes)
        if canonical is None:
            rows.append({
                "rank": rank,
                "score": result.scores[rank] if rank < len(result.scores) else None,
                "raw_target": raw,
                "canonical_target": None,
                "structure_render": structure,
                "forward_eligible": False,
                "reject_reason": "symbolic-node-payload-not-unique",
            })
            continue
        gate = v6.strong_quality_gate(p1.SOURCE, p1.BASELINE_RU, canonical)
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
    return rows


def main() -> None:
    eligible = p1.mixed_case_stems(p1.SOURCE)
    normalized, source_changes = p1.normalize_source(p1.SOURCE, eligible)
    nodes = parse_symbolic_nodes(p1.SOURCE)
    if not source_changes or not nodes:
        raise RuntimeError("Q-v1 expected both mixed-case and symbolic source nodes")

    translator, source_tok, target_tok, forward_identity = prepare_model()
    rows = decode_forward(translator, source_tok, target_tok, normalized, nodes)
    forward_eligible = [r for r in rows if r.get("forward_eligible")]

    o1.EXPECTED_RU_EN_SHA256 = o2.PINNED_RU_EN_SHA256
    reverse, reverse_src_tok, reverse_tgt_tok, reverse_identity = o1.prepare_reverse_model()
    baseline_back = o1.reverse_batch(reverse, reverse_src_tok, reverse_tgt_tok, [p1.BASELINE_RU])[0]
    v8_back = o1.reverse_batch(reverse, reverse_src_tok, reverse_tgt_tok, [p1.V8_RU])[0]
    backs = o1.reverse_batch(
        reverse,
        reverse_src_tok,
        reverse_tgt_tok,
        [r["canonical_target"] for r in forward_eligible],
    ) if forward_eligible else []

    selected = None
    for row, back in zip(forward_eligible, backs):
        audit = o2.unit_term_audit({
            "occurrence": 444,
            "mechanism": "Q-v1-whole-context-source-planned-structure",
            "source": p1.SOURCE,
            "baseline_ru": p1.BASELINE_RU,
            "candidate_ru": row["canonical_target"],
            "baseline_back_en": baseline_back,
            "candidate_back_en": back,
        })
        row["candidate_back_en"] = back
        row["o2_term_audit"] = audit
        row["o2_passed"] = audit["passed"]
        if selected is None and audit["passed"]:
            selected = row

    v8_audit = o2.unit_term_audit({
        "occurrence": 444,
        "mechanism": "clean-v8",
        "source": p1.SOURCE,
        "baseline_ru": p1.BASELINE_RU,
        "candidate_ru": p1.V8_RU,
        "baseline_back_en": baseline_back,
        "candidate_back_en": v8_back,
    })

    payload = {
        "schema": "rocketdict-stage8-whole-context-structural-probe/1",
        "status": "PASS" if selected is not None else "FAIL",
        "case_id": "reconstruction-occurrence-444",
        "scope": "exact mechanism probe only",
        "source": p1.SOURCE,
        "mixed_case_signal": eligible,
        "normalized_source": normalized,
        "source_case_changes": source_changes,
        "preparsed_structural_nodes": nodes,
        "forward_model": forward_identity,
        "reverse_model": {
            **reverse_identity,
            "required_opus_zip_sha256": o2.PINNED_RU_EN_SHA256,
            "hash_pin_passed": reverse_identity["opus_zip_sha256"] == o2.PINNED_RU_EN_SHA256,
        },
        "baseline": {"ru": p1.BASELINE_RU, "back_en": baseline_back},
        "clean_v8": {"ru": p1.V8_RU, "back_en": v8_back, "term_audit": v8_audit},
        "hypotheses": rows,
        "selected": selected,
        "mechanism": {
            "name": "Q-v1-whole-context-source-planned-structural-canonicalization",
            "whole_sentence_context": True,
            "structure_parsed_before_mt": True,
            "allowed_target_surface_change": "only surrounding Gutenberg underscores/whitespace of a uniquely preserved exact symbolic payload",
            "translation_glossary_used": False,
            "missing_number_append": False,
            "arbitrary_target_prose_editing": False,
            "acceptance": "inherited forward gates + zero ordinary Latin + pinned O-v2 term-retention",
        },
        "promotion_allowed": False,
        "next_action": (
            "If PASS, integrate Q-v1 generically as a new full frozen-5044 DOE cell and rerun all objective integrity/language + O-v2 checks."
            if selected is not None else
            "Reject Q-v1; do not broaden target canonicalization beyond pre-parsed exact structural payloads."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage8-whole-context-structural-q1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if selected is None:
        raise SystemExit("Q-v1 failed to find a forward+O-v2-valid whole-context hypothesis")


if __name__ == "__main__":
    main()
