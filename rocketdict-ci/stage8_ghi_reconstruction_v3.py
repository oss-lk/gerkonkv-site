from __future__ import annotations

"""Stage 8 NON-PROMOTIONAL reconstruction gate, revision 3.

Revision 2 reduced the frozen 5044-word challenge to two real numeric failures.
Neither n-best nor sentinel shielding solved them.  This revision tests a more
general source-side mechanism: a numeric-list AST.

The AST is built *before* translation. Adjacent numeric literals whose gaps
contain only punctuation and small list connectors are grouped into one node.
Larger prose spans between nodes are translated normally; numeric nodes are
rendered deterministically from source-derived canonical values with explicit
provenance. No failed target is edited or patched after inspection.

This file imports the frozen selector and v2 evaluator from
stage8_ghi_reconstruction_gate.py. It remains non-promotional and cannot replace
the lost exact F96 pipeline / rocketdict-numeric-integrity/3.2.
"""

from collections import Counter
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_opus_gate import OPTICKS_URL, download  # noqa: E402
from stage8_g_nbest_probe import prepare_model  # noqa: E402
from stage8_ghi_reconstruction_gate import (  # noqa: E402
    ALPHA_RE,
    CORPUS,
    EVAL_NUMERIC_RE,
    EVIDENCE,
    EXPECTED_OPTICKS_SHA256,
    OUTPUT,
    TARGET_WORDS,
    aggregate,
    figure_guard,
    g_nbest_rescue,
    h_document_id_candidate,
    h_figure_candidate,
    h_table_candidate,
    i_structural_candidate,
    intervention_quality_gate,
    normalize_numeric,
    numeric_counter,
    quality_row,
    select_challenge,
    sha256_path,
    split_units,
    text_sha256,
    translate_batch,
    translate_one,
    word_count,
)


def connector_only(gap: str) -> bool:
    """True when a gap carries list syntax rather than lexical prose."""
    scrubbed = re.sub(r"\b(?:and|or|to)\b", "", gap, flags=re.IGNORECASE)
    return not bool(re.search(r"[A-Za-zА-Яа-яЁё]", scrubbed))


def render_numeric_group(source: str, matches: list[re.Match[str]], start: int, end: int) -> tuple[str, list[dict]]:
    """Render one numeric group from source spans, localising only connectors."""
    pieces: list[str] = []
    provenance: list[dict] = []
    cursor = start
    for m in matches:
        if m.start() < start or m.end() > end:
            continue
        pieces.append(source[cursor:m.start()])
        raw = m.group(1)
        canonical = normalize_numeric(raw)
        pieces.append(canonical)
        provenance.append({
            "source_start": m.start(),
            "source_end": m.end(),
            "source_text": raw,
            "canonical_numeric": canonical,
        })
        cursor = m.end()
    pieces.append(source[cursor:end])
    rendered = "".join(pieces)
    rendered = re.sub(r"\band\b", "и", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\bor\b", "или", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\bto\b", "к", rendered, flags=re.IGNORECASE)
    return rendered, provenance


def numeric_ast_nodes(source: str) -> list[dict]:
    """Group adjacent numeric literals connected only by list syntax."""
    matches = list(EVAL_NUMERIC_RE.finditer(source))
    if not matches:
        return []

    groups: list[list[re.Match[str]]] = [[matches[0]]]
    for m in matches[1:]:
        prev = groups[-1][-1]
        gap = source[prev.end():m.start()]
        if connector_only(gap):
            groups[-1].append(m)
        else:
            groups.append([m])

    nodes = []
    for group in groups:
        start = group[0].start()
        end = group[-1].end()
        rendered, provenance = render_numeric_group(source, group, start, end)
        nodes.append({
            "kind": "numeric-list-node" if len(group) > 1 else "numeric-literal-node",
            "source_start": start,
            "source_end": end,
            "source_text": source[start:end],
            "rendered": rendered,
            "values": [p["canonical_numeric"] for p in provenance],
            "literals": provenance,
        })
    return nodes


def clean_join(parts: list[str]) -> str:
    target = " ".join(p.strip() for p in parts if p and p.strip())
    target = re.sub(r"\s+([,;:.!?])", r"\1", target)
    target = re.sub(r"([\(\[])\s+", r"\1", target)
    target = re.sub(r"\s+([\)\]])", r"\1", target)
    target = re.sub(r"\s+", " ", target).strip()
    return target


def i_v3_numeric_ast_candidate(translator, source_tok, target_tok, source: str) -> dict:
    nodes = numeric_ast_nodes(source)
    if len(nodes) < 2 or len(numeric_counter(source)) < 4:
        return {"mechanism": "I-v3-numeric-list-AST", "applicable": False}

    prose_segments: list[str] = []
    cursor = 0
    for node in nodes:
        prose_segments.append(source[cursor:node["source_start"]])
        cursor = node["source_end"]
    prose_segments.append(source[cursor:])

    # Translate only lexical prose. Punctuation-only spans are preserved. Larger
    # spans remain intact; unlike per-number splitting, numeric lists are one AST
    # node, reducing fragmentation.
    lexical_indexes = [i for i, s in enumerate(prose_segments) if ALPHA_RE.search(s)]
    lexical_sources = [prose_segments[i] for i in lexical_indexes]
    translated_map: dict[int, str] = {}
    if lexical_sources:
        translated = translate_batch(translator, source_tok, target_tok, lexical_sources)
        translated_map = dict(zip(lexical_indexes, translated))

    parts: list[str] = []
    for i, segment in enumerate(prose_segments):
        if i in translated_map:
            parts.append(translated_map[i])
        elif segment.strip():
            parts.append(segment)
        if i < len(nodes):
            parts.append(nodes[i]["rendered"])

    target = clean_join(parts)
    return {
        "mechanism": "I-v3-numeric-list-AST",
        "applicable": True,
        "target": target,
        "node_count": len(nodes),
        "literal_count": sum(len(n["literals"]) for n in nodes),
        "nodes": nodes,
        "source_numeric_multiset": dict(numeric_counter(source)),
        "target_numeric_multiset": dict(numeric_counter(target)),
    }


def try_candidate(source: str, baseline: str, probe: dict, attempts: list[dict]) -> str | None:
    if not probe.get("applicable", True):
        return None
    target = probe.get("target") or probe.get("selected_text")
    if target is None:
        attempts.append(probe)
        return None
    gate = intervention_quality_gate(source, baseline, target)
    probe = dict(probe)
    probe["selection_quality_gate"] = gate
    attempts.append(probe)
    return target if gate["passed"] else None


def main() -> None:
    for d in (CORPUS.parent, EVIDENCE, OUTPUT):
        d.mkdir(parents=True, exist_ok=True)

    translator, source_tok, target_tok, model_identity = prepare_model()
    download(OPTICKS_URL, CORPUS)
    corpus_sha = sha256_path(CORPUS)
    if corpus_sha != EXPECTED_OPTICKS_SHA256:
        raise RuntimeError(f"Opticks hash mismatch: {corpus_sha} != {EXPECTED_OPTICKS_SHA256}")

    corpus = CORPUS.read_text(encoding="utf-8-sig", errors="replace")
    selected, selection = select_challenge(split_units(corpus))
    if selection["actual_words"] < TARGET_WORDS:
        raise RuntimeError(f"reconstructed selection too small: {selection}")

    sources = [u["source"] for u in selected]
    started = time.time()
    baseline_targets: list[str] = []
    for i in range(0, len(sources), 16):
        baseline_targets.extend(translate_batch(translator, source_tok, target_tok, sources[i:i + 16]))
    baseline_seconds = time.time() - started

    rows = []
    intervention_counts: Counter[str] = Counter()
    candidate_started = time.time()

    for unit, baseline in zip(selected, baseline_targets):
        source = unit["source"]
        baseline_q = quality_row(source, baseline)
        chosen = baseline
        mechanism = "baseline-unchanged"
        attempts: list[dict] = []

        if not baseline_q["numeric"]["passed"]:
            candidate = try_candidate(
                source, baseline,
                i_structural_candidate(translator, source_tok, target_tok, source),
                attempts,
            )
            if candidate is not None:
                chosen, mechanism = candidate, "I-v2"

        if mechanism == "baseline-unchanged" and not baseline_q["numeric"]["passed"]:
            candidate = try_candidate(
                source, baseline,
                h_table_candidate(translator, source_tok, target_tok, source),
                attempts,
            )
            if candidate is not None:
                chosen, mechanism = candidate, "H-table"

        if mechanism == "baseline-unchanged" and not baseline_q["numeric"]["passed"]:
            candidate = try_candidate(
                source, baseline,
                h_document_id_candidate(translator, source_tok, target_tok, source),
                attempts,
            )
            if candidate is not None:
                chosen, mechanism = candidate, "H-document-id"

        if mechanism == "baseline-unchanged" and not baseline_q["figure"]["passed"]:
            candidate = try_candidate(
                source, baseline,
                h_figure_candidate(translator, source_tok, target_tok, source),
                attempts,
            )
            if candidate is not None:
                chosen, mechanism = candidate, "H-figure"

        if mechanism == "baseline-unchanged" and numeric_counter(source) and not baseline_q["numeric"]["passed"]:
            g = g_nbest_rescue(translator, source_tok, target_tok, source, baseline)
            attempts.append(g)
            if g["selected_text"] is not None:
                chosen, mechanism = g["selected_text"], "G-nbest-8x8-quality-gated"

        if mechanism == "baseline-unchanged" and numeric_counter(source) and not baseline_q["numeric"]["passed"]:
            candidate = try_candidate(
                source, baseline,
                i_v3_numeric_ast_candidate(translator, source_tok, target_tok, source),
                attempts,
            )
            if candidate is not None:
                chosen, mechanism = candidate, "I-v3-numeric-list-AST"

        candidate_q = quality_row(source, chosen)
        if mechanism != "baseline-unchanged":
            intervention_counts[mechanism] += 1

        rows.append({
            "occurrence": unit["occurrence"],
            "category": unit["category"],
            "source_words": unit["words"],
            "source": source,
            "baseline": baseline,
            "candidate": chosen,
            "mechanism": mechanism,
            "attempts": attempts,
            "baseline_quality": baseline_q,
            "candidate_quality": candidate_q,
        })

    candidate_seconds = time.time() - candidate_started
    baseline_agg = aggregate(rows, "baseline_quality")
    candidate_agg = aggregate(rows, "candidate_quality")
    new_length_regressions = sum(
        (not r["baseline_quality"]["length_anomaly"]) and r["candidate_quality"]["length_anomaly"]
        for r in rows
    )
    new_identity_regressions = sum(
        (not r["baseline_quality"]["identity"]) and r["candidate_quality"]["identity"]
        for r in rows
    )
    per_intervention_quality_failures = sum(
        r["mechanism"] != "baseline-unchanged"
        and not intervention_quality_gate(r["source"], r["baseline"], r["candidate"])["passed"]
        for r in rows
    )
    changed_units = sum(r["baseline"] != r["candidate"] for r in rows)

    local_gate_passed = (
        candidate_agg["empty"] == 0
        and candidate_agg["numeric_fail_units"] == 0
        and candidate_agg["figure_fail_units"] == 0
        and new_length_regressions == 0
        and new_identity_regressions == 0
        and per_intervention_quality_failures == 0
        and candidate_agg["mean_cyrillic_alpha_share"] >= baseline_agg["mean_cyrillic_alpha_share"] - 0.01
    )

    payload = {
        "schema": "rocketdict-stage8-ghi-reconstruction-gate/3",
        "status": "NON_PROMOTIONAL_RECONSTRUCTION",
        "stage8_parent_full_gate": "F96",
        "promotion_allowed": False,
        "promotion_blocker": "exact 0.30.40 overlay/F96 selection and rocketdict-numeric-integrity/3.2 remain unavailable until missing handoff payload is restored",
        "source": {"url": OPTICKS_URL, "sha256": corpus_sha, "regex_words_full_corpus": word_count(corpus)},
        "model_identity": model_identity,
        "selection": selection,
        "baseline": baseline_agg,
        "candidate": candidate_agg,
        "comparison": {
            "changed_units": changed_units,
            "intervention_counts": dict(intervention_counts),
            "new_length_regressions": new_length_regressions,
            "new_identity_regressions": new_identity_regressions,
            "per_intervention_quality_failures": per_intervention_quality_failures,
            "cyrillic_share_delta": candidate_agg["mean_cyrillic_alpha_share"] - baseline_agg["mean_cyrillic_alpha_share"],
        },
        "timing_seconds": {"baseline_translation": baseline_seconds, "candidate_additional_work": candidate_seconds},
        "v3_hypothesis": {
            "mechanism": "source-side numeric-list AST",
            "grouping": "adjacent numerics are grouped only when the gap has no lexical content beyond and/or/to",
            "rendering": "source canonical numerics plus localized list connectors; surrounding prose translated separately",
            "post_hoc_target_repair": False,
            "sentinel_placeholders": False,
        },
        "local_gate_contract": {
            "numeric": "stage8-ghi-reconstruction-explicit-numeric/2",
            "figure": "source figure numbers must remain addressable in target",
            "empty": 0,
            "new_length_regressions": 0,
            "new_identity_regressions": 0,
            "per_intervention_quality_failures": 0,
            "cyrillic_share_tolerance_aggregate": -0.01,
            "cyrillic_share_tolerance_per_intervention": -0.08,
            "explicit_warning": "this contract is deliberately not rocketdict-numeric-integrity/3.2",
        },
        "local_gate_passed": local_gate_passed,
    }

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "stage8-ghi-reconstruction.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (EVIDENCE / "units.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (OUTPUT / "comparison.tsv").open("w", encoding="utf-8") as f:
        f.write("occurrence\tcategory\tmechanism\tsource\tbaseline\tcandidate\n")
        for row in rows:
            vals = [str(row["occurrence"]), row["category"], row["mechanism"], row["source"], row["baseline"], row["candidate"]]
            f.write("\t".join(v.replace("\t", " ").replace("\n", " ") for v in vals) + "\n")

    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not local_gate_passed:
        raise SystemExit("NON_PROMOTIONAL Stage 8 reconstruction v3 found unresolved integrity/regression evidence")


if __name__ == "__main__":
    main()
