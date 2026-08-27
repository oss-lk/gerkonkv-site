from __future__ import annotations

"""RocketDict Stage 8: NON-PROMOTIONAL reconstructed ~5k integrity gate.

The exact 0.30.40 / F96 payload is incomplete in the public handoff, so this
runner can never promote a branch. It keeps one independently reproducible
~5k selection and compares official OPUS top-1 with conservative source-side
integrity mechanisms.

Revision 2 preserves the v1 selection algorithm/hash while fixing checker
canonicalization defects found by run 33081805252. It also makes quality
fail-closed per intervention and adds source-side structural handling for
numeric tables/document identifiers plus a generic pre-MT numeric shield.

Nothing here is called rocketdict-numeric-integrity/3.2. The exact F96 rerun is
still mandatory before any 10k promotion screen.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_opus_gate import OPTICKS_URL, download  # noqa: E402
from stage8_g_nbest_probe import prepare_model  # noqa: E402

ROOT = Path("work-stage8-ghi-reconstruction")
CORPUS = ROOT / "corpus" / "opticks.txt"
EVIDENCE = ROOT / "evidence"
OUTPUT = ROOT / "output"
EXPECTED_OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_SELECTION_SHA256 = "ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe"
TARGET_WORDS = 5000

WORD_RE = re.compile(r"\b[\w’'-]+\b", flags=re.UNICODE)

# IMPORTANT: selection categorisation intentionally keeps the v1 detector so
# revision 2 reuses exactly the same selected units and selection SHA.
SELECT_NUMERIC_RE = re.compile(
    r"(?<!\w)(?:\d+-\d+/\d+|\d+/\d+|\d{1,3}(?:[\s\u00a0\u202f]\d{3})+|\d+)(?!\w)",
    flags=re.UNICODE,
)

# Evaluation detector v2. Numeric identity is formatting-insensitive for:
# - mixed fractions with optional spaces and English ordinal suffix;
# - simple fractions;
# - comma/space/NBSP thousands groups;
# - digits adjacent to structural underscores/letters (digit boundaries, not
#   Python word boundaries), e.g. S_pc_50 and _Prop._1.
EVAL_NUMERIC_RE = re.compile(
    r"(?<!\d)("
    r"\d+\s*-\s*\d+\s*/\s*\d+(?:st|nd|rd|th)?"
    r"|\d+\s*/\s*\d+(?:st|nd|rd|th)?"
    r"|\d{1,3}(?:(?:,\d{3})|(?:[\s\u00a0\u202f]\d{3}))+(?:st|nd|rd|th)?"
    r"|\d+(?:st|nd|rd|th)?"
    r")(?!\d)",
    flags=re.IGNORECASE | re.UNICODE,
)

FIG_RE = re.compile(r"\[in\s+_Fig\._\s+(?P<number>\d+)\.\]", flags=re.IGNORECASE)
EXTREME_CLAUSE_RE = re.compile(
    r"at\s+the\s+height\s+of\s+"
    r"(?P<h1>\d+)\s*,\s*(?P<h2>\d+)\s*,\s*(?P<h3>\d+)\s+Miles\s*,\s*"
    r"it\s+is\s+about\s+"
    r"(?P<x>\d{7,})\s*,\s*(?P<y>\d{7,})\s*,\s*or\s+(?P<z>\d{7,})\s+"
    r"times\s+rarer",
    flags=re.IGNORECASE,
)
STRUCTURAL_ID_RE = re.compile(
    r"(?ms)(?:^|\n)(?P<label>\d+(?:\.[A-Za-z]+)+\.\d+\.)\s*$"
)
TABLE_RULE_RE = re.compile(r"(?m)^[\-+]{12,}\s*$")
CYR_RE = re.compile(r"[А-Яа-яЁё]")
ALPHA_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")

NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90",
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def normalize_numeric(token: str) -> str:
    token = token.casefold()
    token = re.sub(r"(?:st|nd|rd|th)$", "", token)
    token = re.sub(r"[\s,\u00a0\u202f]", "", token)
    return token


def numeric_counter(text: str) -> Counter[str]:
    return Counter(normalize_numeric(m.group(1)) for m in EVAL_NUMERIC_RE.finditer(text))


def spelled_numeric_licenses(source: str) -> Counter[str]:
    low = source.casefold()
    out: Counter[str] = Counter()
    for word, value in NUMBER_WORDS.items():
        out[value] += len(re.findall(rf"(?<!\w){re.escape(word)}(?!\w)", low))
    return out


def numeric_guard(source: str, target: str) -> dict:
    required = numeric_counter(source)
    observed = numeric_counter(target)
    licensed = spelled_numeric_licenses(source)
    allowed = required + licensed
    missing = {v: n - observed[v] for v, n in required.items() if observed[v] < n}
    duplicate_required = {
        v: observed[v] - allowed[v]
        for v in required
        if observed[v] > allowed[v]
    }
    additions = {
        v: n - allowed[v]
        for v, n in observed.items()
        if v not in required and n > allowed[v]
    }
    return {
        "contract": "stage8-ghi-reconstruction-explicit-numeric/2",
        "required": dict(required),
        "observed": dict(observed),
        "licensed_spelled": dict(licensed),
        "missing": missing,
        "duplicate_required": duplicate_required,
        "unlicensed_additions_observed": additions,
        "passed": not missing and not duplicate_required,
    }


def protect_fig_dots(text: str) -> str:
    # Retained byte-for-byte in selector logic contract v1. In current Opticks
    # the period in _Fig._ is followed by '_' before whitespace, so even if this
    # helper does not fire, the sentence boundary regex does not split there.
    return re.sub(
        r"(_Fig)_\.(?=\s+\d+\.\])",
        lambda m: m.group(1) + "_§FIGDOT§",
        text,
        flags=re.IGNORECASE,
    )


def split_units(text: str) -> list[dict]:
    protected = protect_fig_dots(text.replace("\r\n", "\n"))
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z_\[\"'])", protected)
    units = []
    for i, item in enumerate(raw):
        item = item.replace("§FIGDOT§", ".").strip()
        wc = word_count(item)
        if 4 <= wc <= 220:
            units.append({"occurrence": i, "source": item, "words": wc})
    return units


def category(source: str) -> str:
    if EXTREME_CLAUSE_RE.search(source):
        return "I-extreme"
    if FIG_RE.search(source):
        return "H-figure"
    if SELECT_NUMERIC_RE.search(source):
        return "G-numeric"
    return "general"


def stable_rank(unit: dict, salt: str) -> str:
    return text_sha256(f"{salt}\0{unit['occurrence']}\0{unit['source']}")


def select_challenge(units: list[dict]) -> tuple[list[dict], dict]:
    buckets: dict[str, list[dict]] = {k: [] for k in ("I-extreme", "H-figure", "G-numeric", "general")}
    for u in units:
        u = dict(u)
        u["category"] = category(u["source"])
        buckets[u["category"]].append(u)
    quotas = {"I-extreme": 500, "H-figure": 900, "G-numeric": 2400, "general": 1200}
    selected: dict[int, dict] = {}

    def take_bucket(name: str, budget: int) -> None:
        used = 0
        for u in sorted(buckets[name], key=lambda x: stable_rank(x, f"stage8-ghi-{name}-v1")):
            if u["occurrence"] in selected:
                continue
            if used >= budget and selected:
                break
            selected[u["occurrence"]] = u
            used += u["words"]

    for name in ("I-extreme", "H-figure", "G-numeric", "general"):
        take_bucket(name, quotas[name])

    current = sum(u["words"] for u in selected.values())
    if current < TARGET_WORDS:
        remaining = [u for u in units if u["occurrence"] not in selected]
        for u in sorted(remaining, key=lambda x: stable_rank(x, "stage8-ghi-fill-v1")):
            u = dict(u)
            u["category"] = category(u["source"])
            selected[u["occurrence"]] = u
            current += u["words"]
            if current >= TARGET_WORDS:
                break

    out = sorted(selected.values(), key=lambda x: x["occurrence"])
    serialized = "".join(f"{u['occurrence']}\t{u['category']}\t{u['source']}\n" for u in out)
    meta = {
        "selector": "rocketdict-stage8-ghi-reconstruction-selection/1",
        "target_words": TARGET_WORDS,
        "actual_words": sum(u["words"] for u in out),
        "units": len(out),
        "category_unit_counts": dict(Counter(u["category"] for u in out)),
        "category_word_counts": {
            name: sum(u["words"] for u in out if u["category"] == name)
            for name in buckets
        },
        "selection_sha256": text_sha256(serialized),
        "quotas_words": quotas,
    }
    if meta["selection_sha256"] != EXPECTED_SELECTION_SHA256:
        raise RuntimeError(
            "revision changed the frozen reconstruction selection: "
            f"{meta['selection_sha256']} != {EXPECTED_SELECTION_SHA256}"
        )
    return out, meta


def translate_batch(translator, source_tok, target_tok, texts: list[str], beam_size: int = 4) -> list[str]:
    tokenized = [source_tok.encode(t, out_type=str) for t in texts]
    result = translator.translate_batch(tokenized, beam_size=beam_size, max_batch_size=16)
    return [target_tok.decode(x.hypotheses[0]).strip() for x in result]


def translate_one(translator, source_tok, target_tok, text: str) -> str:
    if not text.strip():
        return ""
    return translate_batch(translator, source_tok, target_tok, [text])[0]


def figure_guard(source: str, target: str) -> dict:
    refs = [m.group("number") for m in FIG_RE.finditer(source)]
    missing = [n for n in refs if not re.search(rf"(?<!\d){re.escape(n)}(?!\d)", target)]
    return {"source_refs": refs, "missing_refs": missing, "passed": not missing}


def quality_row(source: str, target: str) -> dict:
    src_words = max(1, word_count(source))
    tgt_words = word_count(target)
    ratio = tgt_words / src_words
    alpha = ALPHA_RE.findall(target)
    cyr = CYR_RE.findall(target)
    return {
        "empty": not bool(target.strip()),
        "word_ratio": ratio,
        "length_anomaly": ratio < 0.15 or ratio > 3.0,
        "identity": source.strip().casefold() == target.strip().casefold(),
        "cyrillic_alpha_share": (len(cyr) / len(alpha)) if alpha else 0.0,
        "numeric": numeric_guard(source, target),
        "figure": figure_guard(source, target),
    }


def intervention_quality_gate(source: str, baseline: str, candidate: str) -> dict:
    b = quality_row(source, baseline)
    c = quality_row(source, candidate)
    reasons = []
    if c["empty"]:
        reasons.append("empty")
    if c["length_anomaly"] and not b["length_anomaly"]:
        reasons.append("new_length_anomaly")
    if c["identity"] and not b["identity"]:
        reasons.append("new_identity")
    if not c["numeric"]["passed"]:
        reasons.append("numeric_integrity")
    if not c["figure"]["passed"]:
        reasons.append("figure_integrity")
    # The run1 occurrence-744 regression dropped 1.0 -> 0.617. Reject a much
    # smaller drop already; this is deliberately conservative.
    if c["cyrillic_alpha_share"] < b["cyrillic_alpha_share"] - 0.08:
        reasons.append("cyrillic_share_regression")
    if c["cyrillic_alpha_share"] < 0.60 and b["cyrillic_alpha_share"] >= 0.60:
        reasons.append("low_cyrillic_share")
    return {"passed": not reasons, "reasons": reasons, "baseline": b, "candidate": c}


def g_nbest_rescue(translator, source_tok, target_tok, source: str, baseline: str) -> dict:
    tokens = source_tok.encode(source, out_type=str)
    result = translator.translate_batch(
        [tokens], beam_size=8, num_hypotheses=8, return_scores=True, max_batch_size=1
    )[0]
    candidates = []
    selected = None
    for rank, hyp in enumerate(result.hypotheses):
        text = target_tok.decode(hyp).strip()
        gate = intervention_quality_gate(source, baseline, text)
        row = {
            "rank": rank,
            "score": result.scores[rank] if rank < len(result.scores) else None,
            "text": text,
            "quality_gate": gate,
        }
        candidates.append(row)
        if selected is None and gate["passed"]:
            selected = row
    return {
        "mechanism": "G-nbest-8x8-quality-gated",
        "selected_rank": selected["rank"] if selected else None,
        "selected_text": selected["text"] if selected else None,
        "candidates": candidates,
    }


def h_figure_candidate(translator, source_tok, target_tok, source: str) -> dict:
    matches = list(FIG_RE.finditer(source))
    if not matches:
        return {"mechanism": "H-figure", "applicable": False}
    parts = []
    provenance = []
    cursor = 0
    for m in matches:
        prose = source[cursor:m.start()]
        if prose.strip():
            parts.append(translate_one(translator, source_tok, target_tok, prose))
        rendered = f"[на рис. {m.group('number')}]"
        parts.append(rendered)
        provenance.append({
            "kind": "figure-reference",
            "source_start": m.start(), "source_end": m.end(),
            "source_text": m.group(0), "figure_number": m.group("number"),
            "target_render": rendered,
        })
        cursor = m.end()
    tail = source[cursor:]
    if tail.strip():
        parts.append(translate_one(translator, source_tok, target_tok, tail))
    return {
        "mechanism": "H-figure",
        "applicable": True,
        "target": " ".join(p.strip() for p in parts if p.strip()),
        "provenance": provenance,
    }


def h_document_id_candidate(translator, source_tok, target_tok, source: str) -> dict:
    m = STRUCTURAL_ID_RE.search(source)
    if not m:
        return {"mechanism": "H-document-id", "applicable": False}
    prose = source[:m.start("label")].strip()
    label = m.group("label")
    translated = translate_one(translator, source_tok, target_tok, prose)
    target = f"{translated}\n\n{label}".strip()
    return {
        "mechanism": "H-document-id",
        "applicable": True,
        "target": target,
        "provenance": {
            "kind": "document-section-identifier",
            "source_start": m.start("label"), "source_end": m.end("label"),
            "source_text": label, "target_render": label,
        },
    }


def h_table_candidate(translator, source_tok, target_tok, source: str) -> dict:
    rules = list(TABLE_RULE_RE.finditer(source))
    pipe_lines = [line for line in source.splitlines() if "|" in line]
    if not rules or len(pipe_lines) < 3:
        return {"mechanism": "H-table", "applicable": False}
    # Preserve the table as source-derived structure through the last rule; only
    # localize the unambiguous time header. Translate prose outside the table.
    table_start = source.find(pipe_lines[0])
    table_end = rules[-1].end()
    prefix = source[:table_start]
    table = source[table_start:table_end]
    suffix = source[table_end:]
    prefix_t = translate_one(translator, source_tok, target_tok, prefix)
    suffix_t = translate_one(translator, source_tok, target_tok, suffix)
    rendered_table = re.sub(r"(?m)^Min\.(?=\s*\|)", "Мин.", table, count=1)
    target = "\n".join(p for p in (prefix_t.strip(), rendered_table.strip(), suffix_t.strip()) if p)
    return {
        "mechanism": "H-table",
        "applicable": True,
        "target": target,
        "provenance": {
            "kind": "numeric-table",
            "source_start": table_start, "source_end": table_end,
            "source_sha256": text_sha256(table),
            "renderer": "preserve-grid-localize-min-v1",
        },
    }


def i_structural_candidate(translator, source_tok, target_tok, source: str) -> dict:
    m = EXTREME_CLAUSE_RE.search(source)
    if not m:
        return {"mechanism": "I-v2", "applicable": False}
    left = translate_one(translator, source_tok, target_tok, source[:m.start()])
    right = translate_one(translator, source_tok, target_tok, source[m.end():])
    h = [m.group("h1"), m.group("h2"), m.group("h3")]
    x = [m.group("x"), m.group("y"), m.group("z")]
    rendered = (
        f"на высоте {h[0]}, {h[1]}, {h[2]} миль он примерно в "
        f"{x[0]}, {x[1]} или {x[2]} раз разреженнее"
    )
    target = " ".join(p for p in (left.strip(), rendered, right.strip()) if p)
    return {
        "mechanism": "I-v2",
        "applicable": True,
        "target": target,
        "protected_values": [*h, *x],
        "source_span": [m.start(), m.end()],
        "source_text": m.group(0),
        "target_render": rendered,
    }


def alpha_code(index: int) -> str:
    # Fixed-width alphabetic index so sentinels contain no digits that could
    # contaminate numeric evaluation.
    chars = []
    n = index
    for _ in range(4):
        chars.append(chr(ord("A") + (n % 26)))
        n //= 26
    return "".join(reversed(chars))


def shield_strategy(source: str, template: str) -> tuple[str, list[dict]]:
    spans = list(EVAL_NUMERIC_RE.finditer(source))
    pieces = []
    nodes = []
    cursor = 0
    for i, m in enumerate(spans):
        sentinel = template.format(code=alpha_code(i))
        pieces.append(source[cursor:m.start()])
        pieces.append(sentinel)
        raw = m.group(1)
        nodes.append({
            "sentinel": sentinel,
            "source_start": m.start(), "source_end": m.end(),
            "source_text": raw,
            "canonical_numeric": normalize_numeric(raw),
        })
        cursor = m.end()
    pieces.append(source[cursor:])
    return "".join(pieces), nodes


def j_numeric_shield_candidates(translator, source_tok, target_tok, source: str, baseline: str) -> dict:
    strategies = [
        "RDXQ{code}QXDR",
        "ZXQNUM{code}MUNQXZ",
        "ROCKETDICTNUM{code}TOKEN",
    ]
    rows = []
    selected = None
    for template in strategies:
        shielded, nodes = shield_strategy(source, template)
        translated = translate_one(translator, source_tok, target_tok, shielded)
        counts_ok = all(translated.count(n["sentinel"]) == 1 for n in nodes)
        restored = translated
        if counts_ok:
            for n in nodes:
                # Render canonical source numeric semantics, not English ordinal
                # suffixes such as "th".
                restored = restored.replace(n["sentinel"], n["canonical_numeric"])
        gate = intervention_quality_gate(source, baseline, restored) if counts_ok else {
            "passed": False, "reasons": ["sentinel_loss_or_duplication"]
        }
        row = {
            "template": template,
            "shielded_source_sha256": text_sha256(shielded),
            "numeric_nodes": nodes,
            "sentinels_exactly_once": counts_ok,
            "translated_with_sentinels": translated,
            "restored": restored if counts_ok else None,
            "quality_gate": gate,
        }
        rows.append(row)
        if selected is None and gate["passed"]:
            selected = row
    return {
        "mechanism": "J-preMT-numeric-shield",
        "selected_template": selected["template"] if selected else None,
        "selected_text": selected["restored"] if selected else None,
        "strategies": rows,
    }


def aggregate(rows: list[dict], key: str) -> dict:
    qualities = [r[key] for r in rows]
    nonempty = [q for q in qualities if not q["empty"]]
    return {
        "units": len(rows),
        "empty": sum(q["empty"] for q in qualities),
        "numeric_fail_units": sum(not q["numeric"]["passed"] for q in qualities),
        "numeric_missing_values": sum(sum(q["numeric"]["missing"].values()) for q in qualities),
        "numeric_duplicate_values": sum(sum(q["numeric"]["duplicate_required"].values()) for q in qualities),
        "figure_fail_units": sum(not q["figure"]["passed"] for q in qualities),
        "length_anomaly_units": sum(q["length_anomaly"] for q in qualities),
        "identity_units": sum(q["identity"] for q in qualities),
        "mean_cyrillic_alpha_share": (
            sum(q["cyrillic_alpha_share"] for q in nonempty) / len(nonempty) if nonempty else 0.0
        ),
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
    units = split_units(corpus)
    selected, selection = select_challenge(units)
    if selection["actual_words"] < TARGET_WORDS:
        raise RuntimeError(f"reconstructed selection too small: {selection}")

    sources = [u["source"] for u in selected]
    started = time.time()
    baseline_targets = []
    for i in range(0, len(sources), 16):
        baseline_targets.extend(translate_batch(translator, source_tok, target_tok, sources[i:i+16]))
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
            p = i_structural_candidate(translator, source_tok, target_tok, source)
            candidate = try_candidate(source, baseline, p, attempts)
            if candidate is not None:
                chosen, mechanism = candidate, "I-v2"

        if mechanism == "baseline-unchanged" and not baseline_q["numeric"]["passed"]:
            p = h_table_candidate(translator, source_tok, target_tok, source)
            candidate = try_candidate(source, baseline, p, attempts)
            if candidate is not None:
                chosen, mechanism = candidate, "H-table"

        if mechanism == "baseline-unchanged" and not baseline_q["numeric"]["passed"]:
            p = h_document_id_candidate(translator, source_tok, target_tok, source)
            candidate = try_candidate(source, baseline, p, attempts)
            if candidate is not None:
                chosen, mechanism = candidate, "H-document-id"

        if mechanism == "baseline-unchanged" and not baseline_q["figure"]["passed"]:
            p = h_figure_candidate(translator, source_tok, target_tok, source)
            candidate = try_candidate(source, baseline, p, attempts)
            if candidate is not None:
                chosen, mechanism = candidate, "H-figure"

        if mechanism == "baseline-unchanged" and numeric_counter(source) and not baseline_q["numeric"]["passed"]:
            p = g_nbest_rescue(translator, source_tok, target_tok, source, baseline)
            attempts.append(p)
            if p["selected_text"] is not None:
                chosen, mechanism = p["selected_text"], "G-nbest-8x8-quality-gated"

        if mechanism == "baseline-unchanged" and numeric_counter(source) and not baseline_q["numeric"]["passed"]:
            p = j_numeric_shield_candidates(translator, source_tok, target_tok, source, baseline)
            attempts.append(p)
            if p["selected_text"] is not None:
                chosen, mechanism = p["selected_text"], "J-preMT-numeric-shield"

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
        "schema": "rocketdict-stage8-ghi-reconstruction-gate/2",
        "status": "NON_PROMOTIONAL_RECONSTRUCTION",
        "stage8_parent_full_gate": "F96",
        "promotion_allowed": False,
        "promotion_blocker": "exact 0.30.40 overlay/F96 selection and rocketdict-numeric-integrity/3.2 are unavailable until the missing public handoff payload is restored",
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
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (OUTPUT / "comparison.tsv").open("w", encoding="utf-8") as f:
        f.write("occurrence\tcategory\tmechanism\tsource\tbaseline\tcandidate\n")
        for r in rows:
            vals = [str(r["occurrence"]), r["category"], r["mechanism"], r["source"], r["baseline"], r["candidate"]]
            f.write("\t".join(v.replace("\t", " ").replace("\n", " ") for v in vals) + "\n")

    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if not local_gate_passed:
        raise SystemExit("NON_PROMOTIONAL Stage 8 reconstruction v2 found unresolved integrity/regression evidence")


if __name__ == "__main__":
    main()
