from __future__ import annotations

"""RocketDict Stage 8 NON-PROMOTIONAL reconstruction gate, revision 5.

v4 proved that numeric/order/delimiter integrity can be restored on almost the
entire frozen 5044-word challenge, but a manual artifact audit exposed another
objective class: technical-token identity can be corrupted while brackets stay
balanced. Examples in the frozen set include [Greek: ph] -> fh, [Greek: ch] ->
empty, _3p 3t_ losing a marker, and the _rv_/_m_/... variable sequence acquiring
an extra _t_ and losing later variables.

v5 adds fail-closed critical technical-token identity/order and improves the
source-side AST:
* short symbolic Gutenberg emphasis tokens are preserved exactly;
* long emphasized prose is translated recursively while retaining _..._;
* [Greek: payload] structural labels are localized but payload identity is
  exact;
* combined _A[Greek: a]_ keeps A/a exact while localizing the label;
* footnote and Illustration bracket payloads are source-derived;
* numeric multiset + numeric order + []/() remain hard gates.

This remains reconstruction evidence only. Missing exact 0.30.40/F96 payload and
rocketdict-numeric-integrity/3.2 still block promotion.
"""

from collections import Counter
import json
import re
import sys
import time
from pathlib import Path

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
from stage8_ghi_reconstruction_v4 import (  # noqa: E402
    delimiter_guard,
    explicit_numeric_sequence,
    numeric_order_guard,
    smart_join,
)

GREEK_SOURCE_RE = re.compile(r"\[Greek:\s*([^\]]*)\]", flags=re.IGNORECASE)
GREEK_TARGET_RE = re.compile(
    r"\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]*)\]",
    flags=re.IGNORECASE,
)
ILLUSTRATION_SOURCE_RE = re.compile(r"\[Illustration:\s*([^\]]*)\]", flags=re.IGNORECASE)
ILLUSTRATION_TARGET_RE = re.compile(r"\[(?:Illustration|Иллюстрация)\s*:\s*([^\]]*)\]", flags=re.IGNORECASE)
FOOTNOTE_RE = re.compile(r"\[([A-Z])\]")
EMPH_RE = re.compile(r"_([^_\n]{1,80})_")
COMBINED_GREEK_SOURCE_RE = re.compile(
    r"_([A-Za-z]{1,3})\[Greek:\s*([^\]]+)\]_",
    flags=re.IGNORECASE,
)
COMBINED_GREEK_TARGET_RE = re.compile(
    r"_([A-Za-z]{1,3})\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]+)\]_",
    flags=re.IGNORECASE,
)
KNOWN_EDITORIAL_EMPHASIS = {"fig.", "prop.", "viz."}


def connector_only(gap: str) -> bool:
    scrubbed = re.sub(r"\b(?:and|or|to)\b", "", gap, flags=re.IGNORECASE)
    return not bool(re.search(r"[A-Za-zА-Яа-яЁё]", scrubbed))


def is_symbolic_emphasis(inner: str) -> bool:
    x = inner.strip()
    if re.fullmatch(r"[A-Za-z]{1,3}", x):
        return True
    atom = r"(?:\d+[A-Za-z]|[A-Za-z]\d+)"
    return bool(re.fullmatch(rf"{atom}(?:\s+{atom})*", x))


def symbolic_emphasis_sequence(text: str) -> list[str]:
    out = []
    for m in EMPH_RE.finditer(text):
        inner = m.group(1).strip()
        if is_symbolic_emphasis(inner):
            out.append(inner)
    return out


def _payloads(regex: re.Pattern[str], text: str) -> list[str]:
    return [m.group(1).strip() for m in regex.finditer(text)]


def _combined(regex: re.Pattern[str], text: str) -> list[list[str]]:
    return [[m.group(1), m.group(2).strip()] for m in regex.finditer(text)]


def critical_token_guard(source: str, target: str) -> dict:
    checks = {
        "greek_payloads": {
            "source": _payloads(GREEK_SOURCE_RE, source),
            "target": _payloads(GREEK_TARGET_RE, target),
        },
        "combined_greek_variables": {
            "source": _combined(COMBINED_GREEK_SOURCE_RE, source),
            "target": _combined(COMBINED_GREEK_TARGET_RE, target),
        },
        "symbolic_emphasis": {
            "source": symbolic_emphasis_sequence(source),
            "target": symbolic_emphasis_sequence(target),
        },
        "footnote_markers": {
            "source": _payloads(FOOTNOTE_RE, source),
            "target": _payloads(FOOTNOTE_RE, target),
        },
        "illustration_payloads": {
            "source": _payloads(ILLUSTRATION_SOURCE_RE, source),
            "target": _payloads(ILLUSTRATION_TARGET_RE, target),
        },
    }
    failed = [name for name, row in checks.items() if row["source"] != row["target"]]
    return {
        "contract": "stage8-critical-technical-token-integrity/1",
        "checks": checks,
        "failed_checks": failed,
        "passed": not failed,
    }


def strong_quality_gate(source: str, baseline: str, candidate: str) -> dict:
    base = intervention_quality_gate(source, baseline, candidate)
    order = numeric_order_guard(source, candidate)
    delimiters = delimiter_guard(source, candidate)
    critical = critical_token_guard(source, candidate)
    reasons = list(base["reasons"])
    if not order["passed"]:
        reasons.append("explicit_numeric_order")
    if not delimiters["passed"]:
        reasons.append("balanced_delimiter_integrity")
    if not critical["passed"]:
        reasons.append("critical_technical_tokens")
    return {
        "passed": not reasons,
        "reasons": reasons,
        "base_quality_gate": base,
        "numeric_order": order,
        "delimiters": delimiters,
        "critical_tokens": critical,
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
    m = re.match(r"\s*Illustration\s*:\s*(.*)\s*\Z", inner, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return f"[Иллюстрация: {m.group(1).strip()}]"
    m = re.match(r"\s*Greek\s*:\s*(.*)\s*\Z", inner, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return f"[греч.: {m.group(1).strip()}]"
    # Source metadata/footnotes/unknown bracket payloads are safer preserved
    # exactly than translated through MT.
    return f"[{inner}]"


def render_structure_numeric_ast(
    translator,
    source_tok,
    target_tok,
    source: str,
    source_offset: int = 0,
) -> tuple[str, list[dict]]:
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
                "source_text": source[pos:end + 1],
                "target_render": target,
            })
            provenance.extend(inner_prov)
            cursor = end + 1
            continue

        end = source.find("_", pos + 1)
        if end is None:
            rendered, prov = render_numeric_prose(
                translator, source_tok, target_tok, source[pos:], source_offset + pos
            )
            parts.append(rendered)
            provenance.extend(prov)
            break
        inner = source[pos + 1:end]

        combined = re.fullmatch(r"([A-Za-z]{1,3})\[Greek:\s*([^\]]+)\]", inner, flags=re.IGNORECASE)
        if combined:
            target = f"_{combined.group(1)}[греч.: {combined.group(2).strip()}]_"
            inner_prov: list[dict] = []
            mode = "combined-greek-variable"
        elif is_symbolic_emphasis(inner):
            target = f"_{inner}_"
            inner_prov = []
            mode = "symbolic-preserve"
        elif inner.strip().casefold() in KNOWN_EDITORIAL_EMPHASIS:
            target = f"_{inner}_"
            inner_prov = []
            mode = "editorial-preserve"
        else:
            translated_inner, inner_prov = render_structure_numeric_ast(
                translator, source_tok, target_tok, inner, source_offset + pos + 1
            )
            target = f"_{translated_inner}_"
            mode = "emphasized-prose-translate"

        parts.append(target)
        provenance.append({
            "kind": "gutenberg-emphasis",
            "mode": mode,
            "source_start": source_offset + pos,
            "source_end": source_offset + end + 1,
            "source_text": source[pos:end + 1],
            "target_render": target,
        })
        provenance.extend(inner_prov)
        cursor = end + 1

    return smart_join(parts), provenance


def ast_candidate(translator, source_tok, target_tok, source: str) -> dict:
    target, provenance = render_structure_numeric_ast(translator, source_tok, target_tok, source)
    return {
        "mechanism": "L-v1-critical-structure-numeric-AST",
        "applicable": True,
        "target": target,
        "provenance": provenance,
        "source_numeric_sequence": explicit_numeric_sequence(source),
        "target_numeric_sequence": explicit_numeric_sequence(target),
        "numeric_order": numeric_order_guard(source, target),
        "delimiters": delimiter_guard(source, target),
        "critical_tokens": critical_token_guard(source, target),
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
    q["critical_tokens"] = critical_token_guard(source, target)
    return q


def extended_aggregate(rows: list[dict], key: str) -> dict:
    base = aggregate(rows, key)
    qualities = [r[key] for r in rows]
    base["numeric_order_fail_units"] = sum(not q["numeric_order"]["passed"] for q in qualities)
    base["delimiter_fail_units"] = sum(not q["delimiters"]["passed"] for q in qualities)
    base["critical_token_fail_units"] = sum(not q["critical_tokens"]["passed"] for q in qualities)
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
                chosen, mechanism = g["selected_text"], "G-nbest-8x8-critical-gated"

        current_q = extended_row(source, chosen)
        needs_ast = (
            not current_q["numeric"]["passed"]
            or not current_q["numeric_order"]["passed"]
            or not current_q["delimiters"]["passed"]
            or not current_q["critical_tokens"]["passed"]
        )
        if needs_ast:
            candidate = try_candidate(
                source, baseline,
                ast_candidate(translator, source_tok, target_tok, source),
                attempts,
            )
            if candidate is not None:
                chosen, mechanism = candidate, "L-v1-critical-structure-numeric-AST"

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
        and candidate_agg["critical_token_fail_units"] == 0
        and candidate_agg["figure_fail_units"] == 0
        and candidate_agg["length_anomaly_units"] == 0
        and candidate_agg["identity_units"] == 0
        and strong_intervention_failures == 0
        and candidate_agg["mean_cyrillic_alpha_share"] >= baseline_agg["mean_cyrillic_alpha_share"] - 0.01
    )

    payload = {
        "schema": "rocketdict-stage8-ghi-reconstruction-gate/5",
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
        "v5_contract": {
            "numeric_multiset": "stage8-ghi-reconstruction-explicit-numeric/2",
            "numeric_order": "stage8-explicit-numeric-order/1",
            "balanced_delimiters": "stage8-balanced-delimiter-integrity/1",
            "critical_tokens": "stage8-critical-technical-token-integrity/1",
            "generic_ast": "source-side [] / () / recursive emphasis + numeric-list AST",
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
        raise SystemExit("NON_PROMOTIONAL Stage 8 reconstruction v5 found unresolved integrity/regression evidence")


if __name__ == "__main__":
    main()
