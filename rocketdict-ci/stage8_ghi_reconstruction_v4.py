from __future__ import annotations

"""RocketDict Stage 8 NON-PROMOTIONAL reconstruction gate, revision 4.

Revision 3 reached numeric=0 on the frozen 5044-word reconstruction set but a
post-artifact audit found structural damage in occurrence 743: square-bracket
nodes were merged/lost and a parenthesized aside lost its delimiters.  Revision
4 therefore strengthens the gate and mechanism rather than accepting the green
run.

New invariants:
* every explicit source numeric sequence must remain in source order (subsequence
  rule permits legitimate target digits licensed from spelled source numbers);
* balanced source square/round delimiters must remain count-exact in the target;
* generic source-side structural nodes are parsed before MT and rendered with
  provenance;
* numeric nodes are source-derived and rendered before any failed target exists;
* no post-hoc literal append or sentinel placeholder restoration.

The exact 0.30.40/F96 payload is still missing.  This gate is useful regression
evidence only and can never authorize promotion or the 10k screen.
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
    translate_batch,
    translate_one,
    word_count,
)


KNOWN_BRACKET_RENDERERS = {
    "illustration": "Иллюстрация",
    "greek": "греч.",
}


def connector_only(gap: str) -> bool:
    scrubbed = re.sub(r"\b(?:and|or|to)\b", "", gap, flags=re.IGNORECASE)
    return not bool(re.search(r"[A-Za-zА-Яа-яЁё]", scrubbed))


def explicit_numeric_sequence(text: str) -> list[str]:
    return [normalize_numeric(m.group(1)) for m in EVAL_NUMERIC_RE.finditer(text)]


def is_subsequence(required: list[str], observed: list[str]) -> bool:
    j = 0
    for value in observed:
        if j < len(required) and value == required[j]:
            j += 1
    return j == len(required)


def numeric_order_guard(source: str, target: str) -> dict:
    required = explicit_numeric_sequence(source)
    observed = explicit_numeric_sequence(target)
    passed = is_subsequence(required, observed)
    return {
        "contract": "stage8-explicit-numeric-order/1",
        "required_sequence": required,
        "observed_sequence": observed,
        "passed": passed,
    }


def delimiter_guard(source: str, target: str) -> dict:
    rows = {}
    passed = True
    for name, left, right in (
        ("square", "[", "]"),
        ("round", "(", ")"),
    ):
        s_left, s_right = source.count(left), source.count(right)
        t_left, t_right = target.count(left), target.count(right)
        source_balanced = s_left == s_right
        exact = (t_left == s_left and t_right == s_right) if source_balanced else (t_left == t_right)
        rows[name] = {
            "source_open": s_left,
            "source_close": s_right,
            "target_open": t_left,
            "target_close": t_right,
            "source_balanced": source_balanced,
            "passed": exact,
        }
        if not exact:
            passed = False
    return {"contract": "stage8-balanced-delimiter-integrity/1", "delimiters": rows, "passed": passed}


def strong_quality_gate(source: str, baseline: str, candidate: str) -> dict:
    base = intervention_quality_gate(source, baseline, candidate)
    order = numeric_order_guard(source, candidate)
    delimiters = delimiter_guard(source, candidate)
    reasons = list(base["reasons"])
    if not order["passed"]:
        reasons.append("explicit_numeric_order")
    if not delimiters["passed"]:
        reasons.append("balanced_delimiter_integrity")
    return {
        "passed": not reasons,
        "reasons": reasons,
        "base_quality_gate": base,
        "numeric_order": order,
        "delimiters": delimiters,
    }


def _render_numeric_group(source: str, matches: list[re.Match[str]]) -> tuple[str, list[dict]]:
    start, end = matches[0].start(), matches[-1].end()
    pieces: list[str] = []
    provenance: list[dict] = []
    cursor = start
    for m in matches:
        pieces.append(source[cursor:m.start()])
        raw = m.group(1)
        canonical = normalize_numeric(raw)
        pieces.append(canonical)
        provenance.append({
            "kind": "numeric-literal",
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


def render_numeric_prose(translator, source_tok, target_tok, source: str, source_offset: int = 0) -> tuple[str, list[dict]]:
    matches = list(EVAL_NUMERIC_RE.finditer(source))
    if not matches:
        if ALPHA_RE.search(source):
            return translate_one(translator, source_tok, target_tok, source), []
        return source, []

    groups: list[list[re.Match[str]]] = [[matches[0]]]
    for m in matches[1:]:
        previous = groups[-1][-1]
        if connector_only(source[previous.end():m.start()]):
            groups[-1].append(m)
        else:
            groups.append([m])

    parts: list[str] = []
    provenance: list[dict] = []
    cursor = 0
    for group in groups:
        start, end = group[0].start(), group[-1].end()
        prose = source[cursor:start]
        if prose:
            parts.append(translate_one(translator, source_tok, target_tok, prose) if ALPHA_RE.search(prose) else prose)
        rendered, literals = _render_numeric_group(source, group)
        parts.append(rendered)
        provenance.append({
            "kind": "numeric-list-node" if len(group) > 1 else "numeric-literal-node",
            "source_start": source_offset + start,
            "source_end": source_offset + end,
            "source_text": source[start:end],
            "target_render": rendered,
            "literals": [
                {
                    **p,
                    "source_start": source_offset + p["source_start"],
                    "source_end": source_offset + p["source_end"],
                }
                for p in literals
            ],
        })
        cursor = end
    tail = source[cursor:]
    if tail:
        parts.append(translate_one(translator, source_tok, target_tok, tail) if ALPHA_RE.search(tail) else tail)
    return smart_join(parts), provenance


def find_matching(text: str, start: int, left: str, right: str) -> int | None:
    depth = 0
    for i in range(start, len(text)):
        if text[i] == left:
            depth += 1
        elif text[i] == right:
            depth -= 1
            if depth == 0:
                return i
    return None


def render_bracket_node(inner: str) -> str:
    m = re.match(r"\s*(Illustration|Greek)\s*:\s*(.*)\s*\Z", inner, flags=re.IGNORECASE | re.DOTALL)
    if m:
        label = KNOWN_BRACKET_RENDERERS[m.group(1).casefold()]
        payload = m.group(2).strip()
        return f"[{label}: {payload}]"
    # Footnotes such as [G] and unknown Gutenberg structural markers are source
    # metadata. Preserve them exactly rather than asking MT to hallucinate them.
    return f"[{inner}]"


def smart_join(parts: list[str]) -> str:
    text = " ".join(p.strip() for p in parts if p is not None and p.strip())
    text = re.sub(r"\s+([,;:.!?])", r"\1", text)
    text = re.sub(r"([\(\[])\s+", r"\1", text)
    text = re.sub(r"\s+([\)\]])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def render_structure_numeric_ast(
    translator,
    source_tok,
    target_tok,
    source: str,
    source_offset: int = 0,
) -> tuple[str, list[dict]]:
    """Recursively preserve [] / () / emphasis and protect numeric nodes."""
    parts: list[str] = []
    provenance: list[dict] = []
    cursor = 0

    while cursor < len(source):
        positions = [(source.find(ch, cursor), ch) for ch in "[(_"]
        positions = [(pos, ch) for pos, ch in positions if pos >= 0]
        if not positions:
            rendered, prov = render_numeric_prose(
                translator, source_tok, target_tok, source[cursor:], source_offset + cursor
            )
            parts.append(rendered)
            provenance.extend(prov)
            break

        pos, ch = min(positions, key=lambda x: x[0])
        if pos > cursor:
            rendered, prov = render_numeric_prose(
                translator, source_tok, target_tok, source[cursor:pos], source_offset + cursor
            )
            parts.append(rendered)
            provenance.extend(prov)

        if ch == "[":
            end = find_matching(source, pos, "[", "]")
            if end is None:
                rendered, prov = render_numeric_prose(
                    translator, source_tok, target_tok, source[pos:], source_offset + pos
                )
                parts.append(rendered)
                provenance.extend(prov)
                break
            inner = source[pos + 1:end]
            target = render_bracket_node(inner)
            parts.append(target)
            provenance.append({
                "kind": "square-bracket-structure",
                "source_start": source_offset + pos,
                "source_end": source_offset + end + 1,
                "source_text": source[pos:end + 1],
                "target_render": target,
            })
            cursor = end + 1
            continue

        if ch == "(":
            end = find_matching(source, pos, "(", ")")
            if end is None:
                rendered, prov = render_numeric_prose(
                    translator, source_tok, target_tok, source[pos:], source_offset + pos
                )
                parts.append(rendered)
                provenance.extend(prov)
                break
            inner_target, inner_prov = render_structure_numeric_ast(
                translator, source_tok, target_tok, source[pos + 1:end], source_offset + pos + 1
            )
            target = f"({inner_target})"
            parts.append(target)
            provenance.append({
                "kind": "parenthesized-structure",
                "source_start": source_offset + pos,
                "source_end": source_offset + end + 1,
                "source_text_sha256": __import__("hashlib").sha256(source[pos:end + 1].encode("utf-8")).hexdigest(),
                "target_render": target,
            })
            provenance.extend(inner_prov)
            cursor = end + 1
            continue

        # Gutenberg emphasis marker: preserve wrapper/source token exactly. This
        # covers editorial abbreviations (_viz._), variable markup, and prevents
        # underscore damage. If no closing underscore exists, fall back to MT.
        end = source.find("_", pos + 1)
        if end is None:
            rendered, prov = render_numeric_prose(
                translator, source_tok, target_tok, source[pos:], source_offset + pos
            )
            parts.append(rendered)
            provenance.extend(prov)
            break
        node = source[pos:end + 1]
        parts.append(node)
        provenance.append({
            "kind": "gutenberg-emphasis",
            "source_start": source_offset + pos,
            "source_end": source_offset + end + 1,
            "source_text": node,
            "target_render": node,
        })
        cursor = end + 1

    return smart_join(parts), provenance


def ast_candidate(translator, source_tok, target_tok, source: str, mechanism: str) -> dict:
    target, provenance = render_structure_numeric_ast(translator, source_tok, target_tok, source)
    return {
        "mechanism": mechanism,
        "applicable": True,
        "target": target,
        "provenance": provenance,
        "source_numeric_sequence": explicit_numeric_sequence(source),
        "target_numeric_sequence": explicit_numeric_sequence(target),
        "numeric_order": numeric_order_guard(source, target),
        "delimiters": delimiter_guard(source, target),
        "post_hoc_target_repair": False,
    }


def try_candidate(source: str, baseline: str, probe: dict, attempts: list[dict]) -> str | None:
    if not probe.get("applicable", True):
        return None
    target = probe.get("target") or probe.get("selected_text")
    if target is None:
        attempts.append(probe)
        return None
    gate = strong_quality_gate(source, baseline, target)
    row = dict(probe)
    row["strong_selection_gate"] = gate
    attempts.append(row)
    return target if gate["passed"] else None


def extended_row(source: str, target: str) -> dict:
    q = quality_row(source, target)
    q["numeric_order"] = numeric_order_guard(source, target)
    q["delimiters"] = delimiter_guard(source, target)
    return q


def extended_aggregate(rows: list[dict], key: str) -> dict:
    base = aggregate(rows, key)
    qualities = [r[key] for r in rows]
    base["numeric_order_fail_units"] = sum(not q["numeric_order"]["passed"] for q in qualities)
    base["delimiter_fail_units"] = sum(not q["delimiters"]["passed"] for q in qualities)
    return base


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
        baseline_q = extended_row(source, baseline)
        chosen = baseline
        mechanism = "baseline-unchanged"
        attempts: list[dict] = []

        # Keep successful narrow mechanisms first to minimize translation changes.
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
            if g.get("selected_text") is not None and strong_quality_gate(source, baseline, g["selected_text"])["passed"]:
                chosen, mechanism = g["selected_text"], "G-nbest-8x8-strong-gated"

        # General integrity AST is used only when a real numeric/order/delimiter
        # defect remains. It also repairs structural losses discovered in the
        # frozen baseline ([G], _A[Greek:a]_, illustration/Greek nodes).
        current_q = extended_row(source, chosen)
        needs_ast = (
            not current_q["numeric"]["passed"]
            or not current_q["numeric_order"]["passed"]
            or not current_q["delimiters"]["passed"]
        )
        if needs_ast:
            label = "I-v4-structure-numeric-AST" if numeric_counter(source) else "K-v1-structure-AST"
            candidate = try_candidate(
                source, baseline,
                ast_candidate(translator, source_tok, target_tok, source, label),
                attempts,
            )
            if candidate is not None:
                chosen, mechanism = candidate, label

        candidate_q = extended_row(source, chosen)
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
    baseline_agg = extended_aggregate(rows, "baseline_quality")
    candidate_agg = extended_aggregate(rows, "candidate_quality")
    changed_units = sum(r["baseline"] != r["candidate"] for r in rows)
    strong_intervention_failures = sum(
        r["mechanism"] != "baseline-unchanged"
        and not strong_quality_gate(r["source"], r["baseline"], r["candidate"])["passed"]
        for r in rows
    )

    local_gate_passed = (
        candidate_agg["empty"] == 0
        and candidate_agg["numeric_fail_units"] == 0
        and candidate_agg["numeric_order_fail_units"] == 0
        and candidate_agg["delimiter_fail_units"] == 0
        and candidate_agg["figure_fail_units"] == 0
        and candidate_agg["length_anomaly_units"] == 0
        and candidate_agg["identity_units"] == 0
        and strong_intervention_failures == 0
        and candidate_agg["mean_cyrillic_alpha_share"] >= baseline_agg["mean_cyrillic_alpha_share"] - 0.01
    )

    payload = {
        "schema": "rocketdict-stage8-ghi-reconstruction-gate/4",
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
            "strong_intervention_failures": strong_intervention_failures,
            "cyrillic_share_delta": candidate_agg["mean_cyrillic_alpha_share"] - baseline_agg["mean_cyrillic_alpha_share"],
        },
        "timing_seconds": {"baseline_translation": baseline_seconds, "candidate_additional_work": candidate_seconds},
        "v4_contract": {
            "numeric_multiset": "stage8-ghi-reconstruction-explicit-numeric/2",
            "numeric_order": "stage8-explicit-numeric-order/1",
            "balanced_delimiters": "stage8-balanced-delimiter-integrity/1",
            "generic_ast": "source-side [] / () / Gutenberg-emphasis + numeric-list AST",
            "post_hoc_target_repair": False,
            "sentinel_placeholders": False,
            "explicit_warning": "none of these reconstruction checks is rocketdict-numeric-integrity/3.2",
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
        raise SystemExit("NON_PROMOTIONAL Stage 8 reconstruction v4 found unresolved integrity/regression evidence")


if __name__ == "__main__":
    main()
