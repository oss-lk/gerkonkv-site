from __future__ import annotations

"""Recover the historical Stage-7 sentence stream from independent 90k evidence.

NON-PROMOTIONAL.  This script never inspects F96 selection/failure signatures.
It reconstructs the documented Stage5->Stage7 architecture on the immutable
historical 90k Opticks excerpt and ranks only against historical Stage5/7
counts that predate the Stage8 F96 challenge.

Documented architecture recovered from the original Stage5/Stage7 docs:
- Stage5 paragraph candidates are maximal non-empty physical-line blocks;
- Stage5 distinguishes lists, stanzas and hard-wrapped prose from layout only;
- Stage7 joins only confirmed hard-wrapped prose (score >= 0.62);
- list/stanza physical lines are preserved as sentence boundaries;
- ordinary English text uses spacy.blank('en') + Sentencizer;
- common abbreviations/initials are postprocessed conservatively;
- accepted headings are not ordinary paragraphs.
"""

from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import urllib.request

import spacy

ROOT = Path("work-stage7-structural-recovery")
OUT = ROOT / "output"
DL = ROOT / "downloads"
OUT.mkdir(parents=True, exist_ok=True)
DL.mkdir(parents=True, exist_ok=True)

GO_URLS = (
    "https://go.dev/src/testdata/Isaac.Newton-Opticks.txt?m=text",
    "https://raw.githubusercontent.com/golang/go/master/src/testdata/Isaac.Newton-Opticks.txt",
)
GO_SHA = "d4a9ac22462b35e7821a4f2706c211093da678620a8f9997989ee7cf8d507bbd"
EXCERPT_SHA = "9c7ad0cbf391ca31a8861c2b6d88f59aa0c85c12f1f935cb0bc340a9d2abd144"
EXCERPT_BYTES = 505979

# Independent historical heavy-run invariants (2026-07-21).
EXPECTED_CANDIDATES = 668
EXPECTED_PARAGRAPHS = 661
EXPECTED_HEADINGS = 7
EXPECTED_LISTS = 2
EXPECTED_STANZAS = 9
EXPECTED_SENTENCES = 2371
EXPECTED_PUNCT_ISSUES = 217
EXPECTED_SUSPICIOUS_LONG = 176

WORD_RE = re.compile(r"(?u)\b\w+\b")
LIST_MARKER_RE = re.compile(
    r"^\s*(?:[-+*•▪◦]|(?:\(?\d{1,3}\)?[.)])|(?:[A-Za-z][.)]))\s+"
)
TABLEISH_RE = re.compile(r"(?:\|.*\||[-=+]{8,})")
TERMINAL_RE = re.compile(r"[.!?…][\]\)\}\"'_*]*\s*$")
HEADING_MARKER_RE = re.compile(
    r"^\s*_?(?:BOOK|Book|PART|Part|CHAPTER|Chapter|SECTION|Section|Appendix|"
    r"PROPOSITION|Proposition|DEFINITION|Definition|AXIOM|Axiom|QUERY|Query|"
    r"OBSERVATION|Observation|EXPERIMENT|Experiment)\b"
)
ROMAN_RE = re.compile(r"^\s*_?[IVXLCDM]{1,8}[._]?\s*$")
NUMBER_HEADING_RE = re.compile(r"^\s*_?\d+(?:\.\d+)*[.)]?_?\s*$")

# Two documented-style abbreviation policies.  They are calibrated only against
# the historical Stage7 sentence count, never F96.
ABBREV_STRONG = {
    "mr.", "mrs.", "ms.", "dr.", "st.", "fig.", "obs.", "exper.",
    "prop.", "sect.", "defin.", "qu.", "schol.", "pag.", "min.",
    "degr.", "inch.", "inches.", "chap.", "ch.", "vol.", "no.",
}
ABBREV_CONTEXTUAL = {"etc.", "&c.", "p.m.", "a.m.", "viz.", "ibid."}


@dataclass(frozen=True)
class Block:
    index: int
    text: str
    lines: tuple[str, ...]
    blank_before: int
    blank_after: int


@dataclass
class Features:
    line_count: int
    lengths: list[int]
    median_len: float
    mean_len: float
    stdev_len: float
    cv_len: float
    terminal_share_nonlast: float
    lowercase_continuation_share: float
    indent_stability: float
    marker_share: float
    punctuation_density: float
    tableish_share: float
    alpha_words: int
    chars: int


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def download_exact() -> bytes:
    dest = DL / "Isaac.Newton-Opticks.txt"
    last = None
    for url in GO_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RocketDict-Stage7-Recovery/1"})
            with urllib.request.urlopen(req, timeout=90) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
            raw = dest.read_bytes()
            if sha_bytes(raw) != GO_SHA:
                raise RuntimeError(f"full source SHA mismatch: {sha_bytes(raw)}")
            return raw
        except Exception as exc:
            last = exc
            if dest.exists():
                dest.unlink()
    raise RuntimeError(f"could not download exact Go source: {last}")


def historical_excerpt(raw: bytes) -> str:
    text = raw.decode("utf-8")
    matches = list(re.finditer(r"\S+", text, flags=re.UNICODE))
    prefix = (text[: matches[89999].end()] + "\n").encode("utf-8")
    if len(prefix) != EXCERPT_BYTES or sha_bytes(prefix) != EXCERPT_SHA:
        raise RuntimeError(
            f"historical excerpt mismatch: bytes={len(prefix)} sha={sha_bytes(prefix)}"
        )
    return prefix.decode("utf-8")


def blocks_from_text(text: str) -> list[Block]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines()
    blocks: list[Block] = []
    i = 0
    previous_end = -1
    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break
        start = i
        while i < len(lines) and lines[i].strip():
            i += 1
        end = i
        b_lines = tuple(lines[start:end])
        before = 0
        j = start - 1
        while j >= 0 and not lines[j].strip():
            before += 1; j -= 1
        after = 0
        j = end
        while j < len(lines) and not lines[j].strip():
            after += 1; j += 1
        blocks.append(Block(len(blocks), "\n".join(b_lines), b_lines, before, after))
        previous_end = end
    return blocks


def block_features(block: Block) -> Features:
    stripped = [ln.strip() for ln in block.lines if ln.strip()]
    lengths = [len(x) for x in stripped]
    n = len(stripped)
    median_len = statistics.median(lengths) if lengths else 0.0
    mean_len = statistics.mean(lengths) if lengths else 0.0
    stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    cv = stdev / mean_len if mean_len else 0.0
    nonlast = stripped[:-1]
    terminal_share = (
        sum(bool(TERMINAL_RE.search(x)) for x in nonlast) / len(nonlast)
        if nonlast else 0.0
    )
    continuations = stripped[1:]
    lower_share = (
        sum(bool(re.match(r"^[\"'_(\[]*[a-z]", x)) for x in continuations) / len(continuations)
        if continuations else 0.0
    )
    indents = [len(ln) - len(ln.lstrip(" \t")) for ln in block.lines if ln.strip()]
    indent_stability = 1.0
    if len(indents) > 1:
        indent_stability = 1.0 / (1.0 + statistics.pstdev(indents))
    marker_share = sum(bool(LIST_MARKER_RE.match(x)) for x in stripped) / n if n else 0.0
    punct_chars = sum(sum(not c.isalnum() and not c.isspace() for c in x) for x in stripped)
    total_chars = sum(len(x) for x in stripped)
    punctuation_density = punct_chars / total_chars if total_chars else 0.0
    tableish_share = sum(bool(TABLEISH_RE.search(x)) for x in stripped) / n if n else 0.0
    alpha_words = sum(any(c.isalpha() for c in w) for w in WORD_RE.findall(" ".join(stripped)))
    return Features(
        line_count=n, lengths=lengths, median_len=float(median_len), mean_len=float(mean_len),
        stdev_len=float(stdev), cv_len=float(cv), terminal_share_nonlast=terminal_share,
        lowercase_continuation_share=lower_share, indent_stability=indent_stability,
        marker_share=marker_share, punctuation_density=punctuation_density,
        tableish_share=tableish_share, alpha_words=alpha_words, chars=total_chars,
    )


def list_score(block: Block, f: Features) -> float:
    if f.line_count < 2:
        return 0.0
    score = 0.70 * f.marker_share
    score += 0.10 * min(1.0, f.line_count / 4.0)
    score += 0.10 * (1.0 if f.median_len <= 90 else 0.0)
    score += 0.10 * (1.0 - min(1.0, f.tableish_share * 2.0))
    return max(0.0, min(1.0, score))


def stanza_score(block: Block, f: Features) -> float:
    if f.line_count < 2 or f.marker_share >= 0.4 or f.tableish_share >= 0.25:
        return 0.0
    short = max(0.0, min(1.0, (78.0 - f.median_len) / 45.0))
    regular = max(0.0, 1.0 - min(1.0, f.cv_len / 0.55))
    line_signal = min(1.0, f.line_count / 5.0)
    # Stanza lines are relatively short and intentionally line-broken; a high
    # lowercase continuation share is evidence for wrapped prose, not verse.
    return max(0.0, min(1.0,
        0.38 * short + 0.22 * regular + 0.20 * line_signal
        + 0.12 * f.terminal_share_nonlast + 0.08 * (1.0 - f.lowercase_continuation_share)
    ))


def heading_score(block: Block, f: Features) -> float:
    txt = " ".join(x.strip() for x in block.lines).strip()
    if f.line_count != 1 or not txt:
        return 0.0
    words = [w for w in WORD_RE.findall(txt) if any(c.isalpha() for c in w)]
    explicit = bool(HEADING_MARKER_RE.match(txt))
    numbered = bool(ROMAN_RE.match(txt) or NUMBER_HEADING_RE.match(txt))
    short = len(txt) <= 120 and len(words) <= 12
    upper_chars = [c for c in txt if c.isalpha()]
    upper_share = sum(c.isupper() for c in upper_chars) / len(upper_chars) if upper_chars else 0.0
    title_words = [w for w in words if w]
    title_share = sum(w[:1].isupper() for w in title_words) / len(title_words) if title_words else 0.0
    no_terminal = not bool(TERMINAL_RE.search(txt))
    score = 0.0
    score += 0.42 if explicit else 0.0
    score += 0.28 if numbered else 0.0
    score += 0.10 if short else 0.0
    score += 0.06 if block.blank_before else 0.0
    score += 0.06 if block.blank_after else 0.0
    score += 0.12 * upper_share
    score += 0.08 * title_share
    score += 0.08 if no_terminal else -0.12
    if len(words) > 16 or len(txt) > 180:
        score -= 0.35
    return max(0.0, min(1.0, score))


def hardwrap_score(f: Features, family: str) -> float:
    if f.line_count < 2 or f.marker_share >= 0.4 or f.tableish_share >= 0.35:
        return 0.0
    # All families use only the documented physical-layout features; weights are
    # the unknown part of the lost Stage5 code and are calibrated on pre-F96 counts.
    width = max(0.0, min(1.0, (f.median_len - 28.0) / 48.0))
    regular = max(0.0, 1.0 - min(1.0, f.cv_len / 0.65))
    no_terminal = 1.0 - f.terminal_share_nonlast
    lower = f.lowercase_continuation_share
    indent = f.indent_stability
    low_punct = max(0.0, 1.0 - min(1.0, f.punctuation_density / 0.18))
    if family == "balanced":
        weights = (0.27, 0.14, 0.20, 0.20, 0.09, 0.10)
    elif family == "continuation":
        weights = (0.20, 0.10, 0.18, 0.32, 0.08, 0.12)
    elif family == "width":
        weights = (0.36, 0.18, 0.18, 0.12, 0.08, 0.08)
    elif family == "punctuation":
        weights = (0.22, 0.10, 0.30, 0.18, 0.08, 0.12)
    else:
        raise KeyError(family)
    vals = (width, regular, no_terminal, lower, indent, low_punct)
    return sum(w * v for w, v in zip(weights, vals))


def top_n_disjoint(scores: list[tuple[float, int]], n: int, blocked: set[int] | None = None) -> set[int]:
    blocked = blocked or set()
    eligible = [(s, i) for s, i in scores if i not in blocked]
    eligible.sort(key=lambda x: (-x[0], x[1]))
    return {i for _, i in eligible[:n]}


def normalize_join(lines: tuple[str, ...]) -> str:
    out = ""
    for raw in lines:
        x = raw.strip()
        if not x:
            continue
        if not out:
            out = x
            continue
        if out.endswith("\u00ad"):
            out = out[:-1] + x
        elif out.endswith("-") and re.match(r"^[a-z]", x):
            out += x
        else:
            out += " " + x
    return out


def starts_upper(text: str) -> bool:
    return bool(re.match(r"^[\s\"'\(\[_{]*[A-Z]", text))


def ends_abbrev(text: str, mode: str) -> bool:
    low = text.rstrip().casefold()
    if any(low.endswith(x) for x in ABBREV_STRONG):
        return True
    # Single initial / Roman initial.
    if re.search(r"(?:^|\s)[A-Za-zIVXLCDM]\.\s*$", text):
        return True
    if mode == "scientific":
        # Scientific Newton abbreviations are nonterminal unless punctuation or
        # context clearly says otherwise; contextual abbreviations may end a
        # sentence before a new capitalized sentence.
        if any(low.endswith(x) for x in {"viz.", "&c.", "ibid."}):
            return True
    return False


def sentencize(nlp, text: str, mode: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    doc = nlp(text)
    raw = [s.text.strip() for s in doc.sents if s.text.strip()]
    if not raw:
        return [text]
    merged: list[str] = []
    for part in raw:
        if merged and ends_abbrev(merged[-1], mode):
            merged[-1] = merged[-1].rstrip() + " " + part.lstrip()
        else:
            merged.append(part)
    # Contextual etc./p.m./a.m. can remain sentence-final before a capital;
    # merge only before a lowercase continuation.
    out: list[str] = []
    for part in merged:
        if out:
            prev_low = out[-1].rstrip().casefold()
            contextual = any(prev_low.endswith(x) for x in ABBREV_CONTEXTUAL)
            if contextual and not starts_upper(part):
                out[-1] = out[-1].rstrip() + " " + part.lstrip()
                continue
        out.append(part)
    return out


def suspicious_long_count(sentences: list[str]) -> int:
    # Historical settings: long_unpunctuated_words=80; oversized warning 140
    # words or 3000 chars.  Preserve both diagnostics separately.
    return sum(
        len(WORD_RE.findall(s)) >= 80 and len(re.findall(r"[.!?…]", s)) <= 1
        for s in sentences
    )


def punctuation_issue_proxy(units: list[str]) -> int:
    # Only documented deterministic rule-auditor families.  This is diagnostic,
    # not used as a hard identity proof unless exact count emerges naturally.
    count = 0
    for text in units:
        count += len(re.findall(r"\s+[,.;:!?]", text))
        count += len(re.findall(r"(?<=[A-Za-z])[,;:!?](?=[A-Za-z])", text))
        count += len(re.findall(r",{2,}|;{2,}", text))
        if len(WORD_RE.findall(text)) >= 80 and len(re.findall(r"[.!?…]", text)) <= 1:
            count += 1
        if text.strip() and not TERMINAL_RE.search(text) and len(WORD_RE.findall(text)) > 3:
            count += 1
    return count


def sha_sequence(sentences: list[str]) -> str:
    h = hashlib.sha256()
    for i, s in enumerate(sentences):
        h.update(str(i).encode()); h.update(b"\0"); h.update(s.encode("utf-8")); h.update(b"\0")
    return h.hexdigest()


def main() -> None:
    raw = download_exact()
    text = historical_excerpt(raw)
    blocks = blocks_from_text(text)
    features = [block_features(b) for b in blocks]

    if len(blocks) != EXPECTED_CANDIDATES:
        raise RuntimeError(
            f"Stage5 blank-block candidate invariant failed before DOE: {len(blocks)} != {EXPECTED_CANDIDATES}"
        )

    # Recover structural classes only from independent historical counts.  The
    # score functions are source-generic; no F96 literals/metrics are present.
    heading_scores = [(heading_score(b, f), i) for i, (b, f) in enumerate(zip(blocks, features))]
    headings = top_n_disjoint(heading_scores, EXPECTED_HEADINGS)
    list_scores = [(list_score(b, f), i) for i, (b, f) in enumerate(zip(blocks, features))]
    lists = top_n_disjoint(list_scores, EXPECTED_LISTS, headings)
    stanza_scores = [(stanza_score(b, f), i) for i, (b, f) in enumerate(zip(blocks, features))]
    stanzas = top_n_disjoint(stanza_scores, EXPECTED_STANZAS, headings | lists)

    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    families = []
    for hard_family in ("balanced", "continuation", "width", "punctuation"):
        for threshold in (0.58, 0.60, 0.62, 0.64, 0.66):
            for abbrev_mode in ("minimal", "scientific"):
                sentences: list[str] = []
                prepared_units: list[str] = []
                hardwraps: set[int] = set()
                classes: dict[int, str] = {}
                for i, (block, f) in enumerate(zip(blocks, features)):
                    if i in headings:
                        classes[i] = "heading"
                        # Historical paragraph_count + heading_count == Stage5
                        # candidates; headings are structural units, not normal
                        # paragraph sentence-occurrences.
                        continue
                    if i in lists:
                        classes[i] = "list_candidate"
                        for line in block.lines:
                            t = line.strip()
                            if t:
                                prepared_units.append(t)
                                sentences.append(t)
                        continue
                    if i in stanzas:
                        classes[i] = "stanza_candidate"
                        for line in block.lines:
                            t = line.strip()
                            if t:
                                prepared_units.append(t)
                                sentences.append(t)
                        continue
                    hs = hardwrap_score(f, hard_family)
                    if hs >= threshold:
                        classes[i] = "hard_wrapped_prose_candidate"
                        hardwraps.add(i)
                        prepared = normalize_join(block.lines)
                    elif f.line_count == 1:
                        classes[i] = "single_line"
                        prepared = block.lines[0].strip()
                    else:
                        classes[i] = "multiline_block_candidate"
                        # Ambiguous physical breaks remain visible. Segment each
                        # physical line independently rather than silently join.
                        line_parts = []
                        for line in block.lines:
                            t = line.strip()
                            if t:
                                line_parts.extend(sentencize(nlp, t, abbrev_mode))
                        prepared_units.append("\n".join(x.strip() for x in block.lines if x.strip()))
                        sentences.extend(line_parts)
                        continue
                    if prepared:
                        prepared_units.append(prepared)
                        sentences.extend(sentencize(nlp, prepared, abbrev_mode))

                row = {
                    "hardwrap_family": hard_family,
                    "hardwrap_threshold": threshold,
                    "abbrev_mode": abbrev_mode,
                    "stage5_candidate_count": len(blocks),
                    "heading_count": len(headings),
                    "paragraph_count": len(blocks) - len(headings),
                    "list_count": len(lists),
                    "stanza_count": len(stanzas),
                    "hardwrap_count": len(hardwraps),
                    "sentence_count": len(sentences),
                    "sentence_delta": len(sentences) - EXPECTED_SENTENCES,
                    "suspicious_long_proxy": suspicious_long_count(sentences),
                    "suspicious_long_delta": suspicious_long_count(sentences) - EXPECTED_SUSPICIOUS_LONG,
                    "punctuation_issue_proxy": punctuation_issue_proxy(prepared_units),
                    "punctuation_issue_delta": punctuation_issue_proxy(prepared_units) - EXPECTED_PUNCT_ISSUES,
                    "sentence_sequence_sha256": sha_sequence(sentences),
                    "prepared_units_sha256": sha_sequence(prepared_units),
                    "sentences": sentences,
                    "hardwrap_indices": sorted(hardwraps),
                    "classes": classes,
                }
                families.append(row)

    families.sort(key=lambda r: (
        abs(r["sentence_delta"]),
        abs(r["suspicious_long_delta"]),
        abs(r["punctuation_issue_delta"]),
        abs(r["hardwrap_threshold"] - 0.62),
        r["hardwrap_family"], r["abbrev_mode"],
    ))

    # Save full top candidates with sentence streams, compact all-cell table, and
    # structural ranking diagnostics.  No F96 field is computed here.
    compact = [{k: v for k, v in r.items() if k not in {"sentences", "classes", "hardwrap_indices"}} for r in families]
    top = families[:8]
    report = {
        "schema": "rocketdict-stage7-structural-recovery/1",
        "non_promotional": True,
        "f96_holdout_not_used": True,
        "source": {
            "full_go_sha256": GO_SHA,
            "historical_excerpt_sha256": EXCERPT_SHA,
            "historical_excerpt_bytes": EXCERPT_BYTES,
            "spacy_version": spacy.__version__,
            "sentence_engine": "spacy.blank(en)+sentencizer+abbrev-initial-postprocess",
        },
        "historical_invariants": {
            "paragraph_candidates": EXPECTED_CANDIDATES,
            "paragraphs": EXPECTED_PARAGRAPHS,
            "headings": EXPECTED_HEADINGS,
            "lists": EXPECTED_LISTS,
            "stanzas": EXPECTED_STANZAS,
            "sentences": EXPECTED_SENTENCES,
            "punctuation_issues": EXPECTED_PUNCT_ISSUES,
            "suspicious_long_units": EXPECTED_SUSPICIOUS_LONG,
        },
        "recovered_structure": {
            "candidate_count": len(blocks),
            "heading_indices": sorted(headings),
            "heading_scores": sorted(heading_scores, reverse=True)[:16],
            "list_indices": sorted(lists),
            "list_scores": sorted(list_scores, reverse=True)[:12],
            "stanza_indices": sorted(stanzas),
            "stanza_scores": sorted(stanza_scores, reverse=True)[:20],
        },
        "exact_sentence_count_cells": sum(r["sentence_count"] == EXPECTED_SENTENCES for r in families),
        "best_cells": compact[:20],
        "interpretation": (
            "An exact 2371 cell is a Stage7 recovery candidate, not proof of byte-identical code. "
            "F96 is intentionally not evaluated until the Stage7 choice is frozen from these independent invariants."
        ),
    }
    (OUT / "stage7-recovery-summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "stage7-recovery-cells.json").write_text(json.dumps(compact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for rank, r in enumerate(top):
        payload = {k: v for k, v in r.items() if k != "classes"}
        (OUT / f"candidate-{rank:02d}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        with (OUT / f"candidate-{rank:02d}-sentences.tsv").open("w", encoding="utf-8") as f:
            for i, s in enumerate(r["sentences"]):
                f.write(f"{i}\t{sha_text(s)}\t{s.replace(chr(9), ' ')}\n")
    (OUT / "blocks.json").write_text(json.dumps([
        {"block": asdict(b), "features": asdict(f), "heading_score": heading_score(b, f),
         "list_score": list_score(b, f), "stanza_score": stanza_score(b, f)}
        for b, f in zip(blocks, features)
    ], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
