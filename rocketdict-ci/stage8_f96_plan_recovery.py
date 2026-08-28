from __future__ import annotations

"""Fail-closed, NON-PROMOTIONAL recovery DOE for the lost exact F96 plan.

This script does not translate and can never promote Stage 8.  It combines
recovered byte-exact Stage12 pilot sampling semantics with independently
recorded historical invariants to search a deliberately narrow family of
missing Stage7/Stage12 planning details.

Acceptance is evidence, not identity: even a 5000/109/168 match remains a
recovery candidate until stronger hashes/receipts or an exact source snapshot
confirm it.
"""

from collections import deque
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import urllib.request
import zipfile

import sentencepiece as spm

ROOT = Path("work-stage8-f96-plan-recovery")
OUT = ROOT / "output"
DL = ROOT / "downloads"
OUT.mkdir(parents=True, exist_ok=True)
DL.mkdir(parents=True, exist_ok=True)

GO_URLS = (
    "https://go.dev/src/testdata/Isaac.Newton-Opticks.txt?m=text",
    "https://raw.githubusercontent.com/golang/go/master/src/testdata/Isaac.Newton-Opticks.txt",
)
GO_SHA = "d4a9ac22462b35e7821a4f2706c211093da678620a8f9997989ee7cf8d507bbd"
GO_BYTES = 567198
EXCERPT_SHA = "9c7ad0cbf391ca31a8861c2b6d88f59aa0c85c12f1f935cb0bc340a9d2abd144"
EXCERPT_BYTES = 505979
EXCERPT_NONWS_WORDS = 90000
HIST_SENTENCES = 2371
HIST_PARAGRAPHS = 661
HIST_PARAGRAPH_CANDIDATES = 668
HIST_STAGE12_UNITS = 461
HIST_REGEX_FULL_WORDS = 104257

GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/33504/pg33504.txt"
GUTENBERG_SHA = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
GUTENBERG_REGEX_WORDS = 104275
OPUS_URL = "https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip"
OPUS_SHA = "798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677"

TARGET_WORDS = 5000
EXPECTED_SELECTED_UNITS = 109
EXPECTED_F96_CHUNKS = 168
HARD_LIMIT = 504

# Recovered byte-exact from lost 0.30.40 stage12_pilot.py prefix.
WORD_RE = re.compile(r"(?u)\b\w+\b")
NUMBER_RE = re.compile(r"(?<![\w])(?:[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?)(?![\w])")
CRITICAL_SYMBOLS = ("=", "%", "°", "±", "×", "÷")

FAILURE_SIGNATURES = {
    "figure_15697": ("[in _Fig._ 2.]", "four Inches", "eight Feet", "three Feet"),
    "short_16200": ("15 Min. that of the exterior 3 Degr.",),
    "extreme_17795": ("1000000, 1000000000000, or 1000000000000000000",),
}

# Deliberately generic abbreviation families.  Each candidate is reported and
# calibrated on the older 90k run; no F96 signature is used to create a split.
ABBREV_GROUPS = {
    "minimal": [
        "Mr.", "Mrs.", "Dr.", "St.", "viz.", "Viz.", "Fig.", "fig.",
        "Obs.", "obs.", "Exper.", "exper.", "Prop.", "prop.", "Sect.", "sect.",
        "Defin.", "DEFIN.", "Qu.", "Schol.", "pag.", "p.", "&c.",
    ],
    "scientific": [
        "Mr.", "Mrs.", "Dr.", "St.", "viz.", "Viz.", "Fig.", "fig.",
        "Obs.", "obs.", "Exper.", "exper.", "Prop.", "prop.", "Sect.", "sect.",
        "Defin.", "DEFIN.", "Qu.", "Schol.", "pag.", "p.", "&c.", "Min.",
        "Degr.", "Inch.", "Inches.", "Part.", "Book.", "Chap.", "Ch.",
        "Ibid.", "Lect.", "Optic.", "Author.", "Febr.", "Jan.", "Mar.",
        "Apr.", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
    ],
}

@dataclass
class Sentence:
    sequence: int
    paragraph: int
    text: str

@dataclass
class Unit:
    id: int
    sequence_number: int
    source_text: str
    source_tokens: int
    paragraph_start: int
    paragraph_end: int


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def download_exact(urls: tuple[str, ...], dest: Path, expected_sha: str) -> str:
    last = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RocketDict-F96-Recovery/1"})
            with urllib.request.urlopen(req, timeout=90) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
            digest = sha_bytes(dest.read_bytes())
            if digest != expected_sha:
                raise RuntimeError(f"SHA mismatch from {url}: {digest}")
            return url
        except Exception as exc:
            last = exc
            if dest.exists():
                dest.unlink()
    raise RuntimeError(f"all downloads failed for {dest}: {last}")


def derive_first_nonws(raw: bytes, count: int) -> bytes:
    # Historical source is UTF-8.  Byte offsets are safe because \S+ boundaries
    # occur on ASCII whitespace; encode prefix back to bytes and verify exact SHA.
    text = raw.decode("utf-8")
    matches = list(re.finditer(r"\S+", text, flags=re.UNICODE))
    if len(matches) < count:
        raise RuntimeError("source has fewer non-whitespace tokens than requested")
    return text[: matches[count - 1].end()].encode("utf-8")


def paragraph_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [b for b in re.split(r"\n[ \t]*\n+", text) if b.strip()]


def protect_abbrevs(text: str, names: list[str]) -> str:
    # Private-use marker, later restored.  Only periods in known lexical
    # abbreviations are protected; no corpus-location rules.
    marker = "\ue000"
    for token in sorted(set(names), key=len, reverse=True):
        protected = token.replace(".", marker)
        text = re.sub(re.escape(token), protected, text)
    # Roman-numeral / single-cap initial used in headings/citations, e.g. I.
    text = re.sub(r"(?<!\w)([IVXLCDM]{1,6})\.(?=\s+(?:[A-Z_\[]|$))", rf"\1{marker}", text)
    return text


def sentence_split_block(block: str, abbrev_mode: str, split_semicolon: bool, split_colon: bool) -> list[str]:
    marker = "\ue000"
    s = protect_abbrevs(block, ABBREV_GROUPS[abbrev_mode])
    # Hard-wrapped source lines are layout, not sentence boundaries.
    s = re.sub(r"[ \t]*\n[ \t]*", " ", s).strip()
    terminals = ".!?"
    if split_semicolon:
        terminals += ";"
    if split_colon:
        terminals += ":"
    # Stage7-style conservative boundary: punctuation followed by whitespace and
    # a plausible new sentence/structural token.  Keep quote/bracket starters.
    pattern = rf"(?<=[{re.escape(terminals)}])\s+(?=(?:[\"'\[_]*[A-Z]|_[A-Z]|\[Illustration|\[Greek|\d+\s))"
    parts = [p.replace(marker, ".").strip() for p in re.split(pattern, s) if p.strip()]
    return parts


def segment(text: str, abbrev_mode: str, split_semicolon: bool, split_colon: bool, heading_as_sentence: bool) -> tuple[list[Sentence], dict]:
    blocks = paragraph_blocks(text)
    sentences: list[Sentence] = []
    para_count = 0
    heading_like = 0
    for raw in blocks:
        norm = " ".join(raw.split())
        words = WORD_RE.findall(norm)
        alpha = [w for w in words if any(c.isalpha() for c in w)]
        heading = bool(alpha) and len(alpha) <= 10 and (
            norm.isupper() or re.fullmatch(r"_?[A-Z][A-Z ._'-]{1,80}_?", norm) is not None
        )
        if heading:
            heading_like += 1
            if heading_as_sentence:
                sentences.append(Sentence(len(sentences), para_count, norm))
            para_count += 1
            continue
        parts = sentence_split_block(raw, abbrev_mode, split_semicolon, split_colon)
        for part in parts:
            sentences.append(Sentence(len(sentences), para_count, part))
        para_count += 1
    return sentences, {
        "raw_blank_blocks": len(blocks),
        "paragraphs_modelled": para_count,
        "heading_like_blocks": heading_like,
        "sentence_count": len(sentences),
    }


def token_count(sp: spm.SentencePieceProcessor, text: str) -> int:
    return len(sp.encode(text, out_type=str))


def split_oversize(sp: spm.SentencePieceProcessor, sentence: Sentence, hard: int) -> list[Sentence]:
    if token_count(sp, sentence.text) <= hard:
        return [sentence]
    # Generic exact-text recursive splitting: right-most punctuation/whitespace
    # under the token limit, otherwise char binary search.  This is recovery DOE
    # evidence only, not asserted byte-identical to the missing planner yet.
    out: list[Sentence] = []
    remaining = sentence.text
    while remaining:
        if token_count(sp, remaining) <= hard:
            out.append(Sentence(0, sentence.paragraph, remaining))
            break
        lo, hi, best = 1, len(remaining), 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if token_count(sp, remaining[:mid]) <= hard:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        cut = best
        candidates = [m.end() for m in re.finditer(r"[.!?;:]\s+", remaining[:best])]
        if candidates:
            cut = candidates[-1]
        else:
            spaces = [m.end() for m in re.finditer(r"\s+", remaining[:best])]
            if spaces:
                cut = spaces[-1]
        if cut <= 0:
            raise RuntimeError("oversize splitter made no progress")
        out.append(Sentence(0, sentence.paragraph, remaining[:cut]))
        remaining = remaining[cut:]
    return out


def make_plan(
    sp: spm.SentencePieceProcessor,
    sentences: list[Sentence],
    *,
    preferred: int,
    boundary_ratio: float,
    boundary_mode: str,
) -> list[Unit]:
    expanded: list[Sentence] = []
    for s in sentences:
        expanded.extend(split_oversize(sp, s, HARD_LIMIT))
    units: list[Unit] = []
    current: list[Sentence] = []
    current_text = ""

    def flush() -> None:
        nonlocal current, current_text
        if not current:
            return
        txt = current_text.strip()
        units.append(Unit(
            id=len(units) + 1,
            sequence_number=len(units),
            source_text=txt,
            source_tokens=token_count(sp, txt),
            paragraph_start=current[0].paragraph,
            paragraph_end=current[-1].paragraph,
        ))
        current = []
        current_text = ""

    for s in expanded:
        sep = " " if current_text else ""
        proposed = current_text + sep + s.text.strip()
        proposed_tokens = token_count(sp, proposed)
        para_boundary = bool(current and current[-1].paragraph != s.paragraph)
        current_tokens = token_count(sp, current_text) if current_text else 0
        should_close_boundary = False
        if para_boundary:
            if boundary_mode == "strict":
                should_close_boundary = True
            elif boundary_mode == "ratio":
                should_close_boundary = current_tokens >= preferred * boundary_ratio
            elif boundary_mode == "ratio_next":
                # Prefer a paragraph boundary when the current unit is already
                # reasonably filled OR adding the next sentence would cross the
                # preferred budget.
                should_close_boundary = (
                    current_tokens >= preferred * boundary_ratio
                    or proposed_tokens > preferred
                )
        if current and (proposed_tokens > HARD_LIMIT or proposed_tokens > preferred or should_close_boundary):
            flush()
            current = [s]
            current_text = s.text.strip()
        else:
            current.append(s)
            current_text = proposed
    flush()
    return units


def words(text: str) -> int:
    return len(WORD_RE.findall(text))


def contains_numeric(text: str) -> bool:
    return NUMBER_RE.search(text) is not None


def spread_pick(items: list[Unit], count: int) -> list[Unit]:
    if count <= 0 or not items:
        return []
    if count >= len(items):
        return list(items)
    result: list[Unit] = []
    seen: set[int] = set()
    for index in range(count):
        position = min(len(items) - 1, int(((index + 0.5) * len(items)) / count))
        unit = items[position]
        if unit.id not in seen:
            result.append(unit); seen.add(unit.id)
    if len(result) < count:
        for unit in items:
            if unit.id not in seen:
                result.append(unit); seen.add(unit.id)
                if len(result) >= count:
                    break
    return result


def spread_order(items: list[Unit]) -> list[Unit]:
    if not items:
        return []
    q: deque[tuple[int, int]] = deque([(0, len(items))])
    out: list[Unit] = []
    while q:
        start, end = q.popleft()
        if end <= start:
            continue
        middle = start + (end - start - 1) // 2
        out.append(items[middle])
        if start < middle:
            q.append((start, middle))
        if middle + 1 < end:
            q.append((middle + 1, end))
    return out


def select_stratified(units: list[Unit], target_words: int = TARGET_WORDS) -> tuple[list[Unit], dict]:
    selected: dict[int, Unit] = {}
    reasons: dict[int, set[str]] = {}
    def add(u: Unit, reason: str) -> None:
        selected[u.id] = u
        reasons.setdefault(u.id, set()).add(reason)
    n = len(units)
    buckets = min(8, n)
    for bucket in range(buckets):
        start = bucket * n // buckets
        end = (bucket + 1) * n // buckets
        if end > start:
            center = start + (end - start - 1) // 2
            add(units[center], f"position_bucket:{bucket}")
    numeric = [u for u in units if contains_numeric(u.source_text)]
    critical = [u for u in units if any(sym in u.source_text for sym in CRITICAL_SYMBOLS)]
    long = [u for u in units if words(u.source_text) >= 24]
    for u in spread_pick(numeric, min(8, len(numeric))): add(u, "numeric")
    for u in spread_pick(critical, min(8, len(critical))): add(u, "critical_symbol")
    for u in sorted(long, key=lambda u: (-words(u.source_text), u.sequence_number, u.id))[:8]: add(u, "long_unit")
    total = sum(words(u.source_text) for u in selected.values())
    if total < target_words:
        for u in spread_order(units):
            if u.id in selected: continue
            add(u, "budget_fill"); total += words(u.source_text)
            if total >= target_words: break
    ordered = sorted(selected.values(), key=lambda u: (u.sequence_number, u.id))
    return ordered, {
        "plan_unit_count": len(units),
        "selected_unit_count": len(ordered),
        "selected_words": sum(words(u.source_text) for u in ordered),
        "selected_numeric": sum(contains_numeric(u.source_text) for u in ordered),
        "selected_critical": sum(any(sym in u.source_text for sym in CRITICAL_SYMBOLS) for u in ordered),
        "selected_long": sum(words(u.source_text) >= 24 for u in ordered),
        "selection_reasons": {str(k): sorted(v) for k, v in sorted(reasons.items())},
    }


def signature_hits(selected: list[Unit]) -> dict:
    joined = "\n".join(u.source_text for u in selected)
    result = {}
    for name, sigs in FAILURE_SIGNATURES.items():
        full = all(sig in joined for sig in sigs)
        unit_ids = [u.id for u in selected if all(sig in u.source_text for sig in sigs)]
        result[name] = {"present_anywhere": full, "single_unit_ids": unit_ids}
    return result


def sequence_sha(units: list[Unit]) -> str:
    # Recovery-only deterministic fingerprint, explicitly NOT the lost receipt
    # contract because its exact serialization is unavailable.
    rows = [sha_text(u.source_text) for u in units]
    return sha_text("\n".join(rows))


def approximate_f96_chunks(sp: spm.SentencePieceProcessor, selected: list[Unit], budget: int = 96) -> int:
    # Transparent lower-bound proxy: token pieces packed in contiguous chunks of
    # <=budget.  It does not claim the missing Stage8 preferred atomic splitter.
    return sum(max(1, math.ceil(token_count(sp, u.source_text) / budget)) for u in selected)


def find_source_spm(opus_zip: Path) -> Path:
    model_root = ROOT / "opus"
    if model_root.exists(): shutil.rmtree(model_root)
    model_root.mkdir(parents=True)
    with zipfile.ZipFile(opus_zip) as zf:
        zf.extractall(model_root)
    candidates = sorted(model_root.rglob("source.spm"))
    if not candidates:
        candidates = sorted(p for p in model_root.rglob("*.spm") if "source" in p.name.casefold())
    if not candidates:
        raise RuntimeError("source SentencePiece model not found in OPUS artifact")
    return candidates[0]


def evaluate_corpus(
    name: str,
    text: str,
    sp: spm.SentencePieceProcessor,
    segmentation_configs: list[dict],
    planner_configs: list[dict],
) -> list[dict]:
    rows = []
    for sc in segmentation_configs:
        sents, seg_meta = segment(text, **sc)
        for pc in planner_configs:
            plan = make_plan(sp, sents, **pc)
            selected, sel = select_stratified(plan)
            sig = signature_hits(selected)
            approx_chunks = approximate_f96_chunks(sp, selected, 96)
            rows.append({
                "corpus": name,
                "segmentation": sc,
                "segmentation_meta": seg_meta,
                "planner": pc,
                "plan_unit_count": len(plan),
                "plan_source_token_count": sum(u.source_tokens for u in plan),
                "plan_sequence_recovery_sha256": sequence_sha(plan),
                "selection": sel,
                "selected_sequence_recovery_sha256": sequence_sha(selected),
                "signatures": sig,
                "all_three_signatures": all(v["present_anywhere"] for v in sig.values()),
                "all_three_single_unit": all(bool(v["single_unit_ids"]) for v in sig.values()),
                "approximate_96_chunk_count": approx_chunks,
                "selected_units": [
                    {
                        "id": u.id,
                        "sequence": u.sequence_number,
                        "words": words(u.source_text),
                        "tokens": u.source_tokens,
                        "sha256": sha_text(u.source_text),
                        "source": u.source_text,
                    }
                    for u in selected
                ],
            })
    return rows


def hist_score(row: dict) -> tuple:
    meta = row["segmentation_meta"]
    return (
        abs(meta["sentence_count"] - HIST_SENTENCES),
        abs(row["plan_unit_count"] - HIST_STAGE12_UNITS),
        abs(meta["paragraphs_modelled"] - HIST_PARAGRAPHS),
    )


def f96_score(row: dict) -> tuple:
    sel = row["selection"]
    source_bonus = 0 if row["corpus"] == "canonical_go_full" else 1
    return (
        source_bonus,
        0 if row["all_three_signatures"] else 1,
        abs(sel["selected_unit_count"] - EXPECTED_SELECTED_UNITS),
        abs(sel["selected_words"] - TARGET_WORDS),
        abs(row["approximate_96_chunk_count"] - EXPECTED_F96_CHUNKS),
    )


def main() -> None:
    go_path = DL / "Isaac.Newton-Opticks.txt"
    go_used = download_exact(GO_URLS, go_path, GO_SHA)
    go_raw = go_path.read_bytes()
    if len(go_raw) != GO_BYTES: raise RuntimeError(f"Go source byte size changed: {len(go_raw)}")
    excerpt = derive_first_nonws(go_raw, EXCERPT_NONWS_WORDS)
    if len(excerpt) != EXCERPT_BYTES or sha_bytes(excerpt) != EXCERPT_SHA:
        raise RuntimeError(f"historical 90k excerpt mismatch: bytes={len(excerpt)} sha={sha_bytes(excerpt)}")
    go_text = go_raw.decode("utf-8")
    if len(WORD_RE.findall(go_text)) != HIST_REGEX_FULL_WORDS:
        raise RuntimeError(f"historical full regex word mismatch: {len(WORD_RE.findall(go_text))}")

    gut_path = DL / "gutenberg-opticks.txt"
    download_exact((GUTENBERG_URL,), gut_path, GUTENBERG_SHA)
    gut_text = gut_path.read_text(encoding="utf-8-sig", errors="strict")
    if len(WORD_RE.findall(gut_text)) != GUTENBERG_REGEX_WORDS:
        raise RuntimeError(f"Gutenberg regex word mismatch: {len(WORD_RE.findall(gut_text))}")

    opus_zip = DL / "opus-2020-02-11.zip"
    download_exact((OPUS_URL,), opus_zip, OPUS_SHA)
    source_spm = find_source_spm(opus_zip)
    sp = spm.SentencePieceProcessor(model_file=str(source_spm))

    segmentation_configs = []
    for abbrev_mode in ("minimal", "scientific"):
        for split_semicolon in (False, True):
            for split_colon in (False, True):
                for heading_as_sentence in (False, True):
                    segmentation_configs.append({
                        "abbrev_mode": abbrev_mode,
                        "split_semicolon": split_semicolon,
                        "split_colon": split_colon,
                        "heading_as_sentence": heading_as_sentence,
                    })
    planner_configs = []
    for preferred in (224, 240, 256, 272, 288, 304, 320, 336, 352, 384):
        for boundary_mode in ("ratio", "ratio_next"):
            for ratio in (0.25, 1/3, 0.40, 0.50, 0.60, 0.70, 0.80):
                planner_configs.append({
                    "preferred": preferred,
                    "boundary_ratio": round(ratio, 6),
                    "boundary_mode": boundary_mode,
                })
    planner_configs.append({"preferred": 320, "boundary_ratio": 0.0, "boundary_mode": "strict"})

    hist_rows = evaluate_corpus(
        "historical_go_first90k",
        excerpt.decode("utf-8"), sp, segmentation_configs, planner_configs,
    )
    hist_ranked = sorted(hist_rows, key=hist_score)
    # Keep only distinct config combinations among the strongest calibration rows.
    top_hist = hist_ranked[:40]

    # Narrow current/full evaluation to the Stage7/planner configs that best
    # reproduce the old 90k machine evidence.  This prevents combinatorial
    # fishing on F96 itself.
    chosen_pairs = []
    seen = set()
    for row in top_hist:
        key = (json.dumps(row["segmentation"], sort_keys=True), json.dumps(row["planner"], sort_keys=True))
        if key in seen: continue
        seen.add(key)
        chosen_pairs.append((row["segmentation"], row["planner"]))
        if len(chosen_pairs) >= 20: break

    full_rows = []
    for corpus_name, corpus_text in (
        ("canonical_go_full", go_text),
        ("github_gutenberg_full", gut_text),
    ):
        for sc, pc in chosen_pairs:
            sents, seg_meta = segment(corpus_text, **sc)
            plan = make_plan(sp, sents, **pc)
            selected, sel = select_stratified(plan)
            sig = signature_hits(selected)
            full_rows.append({
                "corpus": corpus_name,
                "segmentation": sc,
                "segmentation_meta": seg_meta,
                "planner": pc,
                "plan_unit_count": len(plan),
                "plan_source_token_count": sum(u.source_tokens for u in plan),
                "plan_sequence_recovery_sha256": sequence_sha(plan),
                "selection": sel,
                "selected_sequence_recovery_sha256": sequence_sha(selected),
                "signatures": sig,
                "all_three_signatures": all(v["present_anywhere"] for v in sig.values()),
                "all_three_single_unit": all(bool(v["single_unit_ids"]) for v in sig.values()),
                "approximate_96_chunk_count": approximate_f96_chunks(sp, selected, 96),
                "selected_units": [{
                    "id": u.id, "sequence": u.sequence_number, "words": words(u.source_text),
                    "tokens": u.source_tokens, "sha256": sha_text(u.source_text), "source": u.source_text,
                } for u in selected],
            })
    full_ranked = sorted(full_rows, key=f96_score)

    report = {
        "schema": "rocketdict-stage8-f96-plan-recovery/1",
        "promotion_allowed": False,
        "identity_claim": "none-recovery-candidates-only",
        "inputs": {
            "go_source_url_used": go_used,
            "go_sha256": sha_bytes(go_raw),
            "go_bytes": len(go_raw),
            "go_regex_words": len(WORD_RE.findall(go_text)),
            "first90k_sha256": sha_bytes(excerpt),
            "first90k_bytes": len(excerpt),
            "gutenberg_sha256": sha_bytes(gut_path.read_bytes()),
            "gutenberg_regex_words": len(WORD_RE.findall(gut_text)),
            "opus_sha256": sha_bytes(opus_zip.read_bytes()),
            "source_spm": str(source_spm),
        },
        "independent_expected_invariants": {
            "historical_90k": {
                "paragraph_candidate_count": HIST_PARAGRAPH_CANDIDATES,
                "paragraph_count": HIST_PARAGRAPHS,
                "sentence_count": HIST_SENTENCES,
                "stage12_unit_count": HIST_STAGE12_UNITS,
            },
            "f96": {
                "source_words": TARGET_WORDS,
                "selected_occurrences": EXPECTED_SELECTED_UNITS,
                "inference_chunks": EXPECTED_F96_CHUNKS,
                "known_failure_signatures": list(FAILURE_SIGNATURES),
            },
        },
        "recovered_exact_contracts": {
            "pilot_selector": "coverage-stratified-v1 byte-exact semantics from 0.30.40 gzip prefix",
            "word_regex": WORD_RE.pattern,
            "critical_symbols": CRITICAL_SYMBOLS,
            "position_buckets": 8,
            "min_numeric_units": 8,
            "min_critical_units": 8,
            "min_long_units": 8,
            "long_min_words": 24,
            "hard_token_limit_documented": HARD_LIMIT,
        },
        "limitations": [
            "Stage7 sentence/paragraph implementation bytes are missing; a narrow generic candidate family is calibrated on older exact machine evidence.",
            "Stage12 paragraph-boundary close heuristic bytes are missing; candidate family is calibrated before F96 scoring.",
            "The 96-chunk value is an explicit ceil(source_spm_tokens/96) proxy, not the missing Stage8 atomic splitter contract.",
            "Recovery sequence SHA values use a new transparent serialization and are not the lost full-plan receipt hashes.",
        ],
        "historical_top40": top_hist,
        "full_top40": full_ranked[:40],
        "exact_shape_candidates": [
            r for r in full_ranked
            if r["selection"]["selected_unit_count"] == EXPECTED_SELECTED_UNITS
            and r["selection"]["selected_words"] == TARGET_WORDS
            and r["all_three_signatures"]
        ],
    }
    (OUT / "stage8-f96-plan-recovery.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "historical_best_score": hist_score(hist_ranked[0]),
        "historical_best": {
            "segmentation": hist_ranked[0]["segmentation"],
            "segmentation_meta": hist_ranked[0]["segmentation_meta"],
            "planner": hist_ranked[0]["planner"],
            "plan_unit_count": hist_ranked[0]["plan_unit_count"],
        },
        "full_best_score": f96_score(full_ranked[0]),
        "full_best": {k: full_ranked[0][k] for k in (
            "corpus", "segmentation", "segmentation_meta", "planner", "plan_unit_count",
            "selection", "signatures", "all_three_signatures", "all_three_single_unit",
            "approximate_96_chunk_count", "selected_sequence_recovery_sha256",
        )},
        "exact_shape_candidate_count": len(report["exact_shape_candidates"]),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
