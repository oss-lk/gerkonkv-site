from __future__ import annotations

"""Stage7 recovery v2: preserve ambiguous multiline blocks as blocks.

This is the same pre-F96 recovery experiment as stage7_structural_recovery.py,
with one corrected interpretation of the documented Stage5->Stage7 contract:
only list/stanza physical lines are sentence boundaries.  A generic multiline
block that is not confidently hard-wrapped remains one prepared block with its
newlines preserved and is passed as a whole to SentenceSegmenter.  It is NOT
split into one pseudo-sentence per source line.

F96 selection, its three failure literals, 5000/109/168 and any translation
output are deliberately absent from this experiment.
"""

import hashlib
import json
from pathlib import Path

import spacy

import stage7_structural_recovery as r

OUT = r.OUT


def sha_sequence(sentences: list[str]) -> str:
    h = hashlib.sha256()
    for i, text in enumerate(sentences):
        h.update(str(i).encode("ascii")); h.update(b"\0")
        h.update(text.encode("utf-8")); h.update(b"\0")
    return h.hexdigest()


def run_cell(nlp, blocks, features, headings, lists, stanzas, hard_family: str, threshold: float, abbrev_mode: str) -> dict:
    sentences: list[str] = []
    prepared_units: list[str] = []
    hardwraps: set[int] = set()
    ambiguous_multiline: set[int] = set()

    for i, (block, feat) in enumerate(zip(blocks, features)):
        if i in headings:
            continue
        if i in lists or i in stanzas:
            for line in block.lines:
                text = line.strip()
                if text:
                    prepared_units.append(text)
                    sentences.append(text)
            continue

        hard_score = r.hardwrap_score(feat, hard_family)
        if hard_score >= threshold:
            hardwraps.add(i)
            prepared = r.normalize_join(block.lines)
        elif feat.line_count == 1:
            prepared = block.lines[0].strip()
        else:
            # Corrected contract: preserve the physical line breaks in the
            # prepared block, but do not promote each line to a sentence.
            ambiguous_multiline.add(i)
            prepared = "\n".join(line.strip() for line in block.lines if line.strip())

        if not prepared:
            continue
        prepared_units.append(prepared)
        sentences.extend(r.sentencize(nlp, prepared, abbrev_mode))

    suspicious = r.suspicious_long_count(sentences)
    punct = r.punctuation_issue_proxy(prepared_units)
    return {
        "hardwrap_family": hard_family,
        "hardwrap_threshold": threshold,
        "abbrev_mode": abbrev_mode,
        "stage5_candidate_count": len(blocks),
        "heading_count": len(headings),
        "paragraph_count": len(blocks) - len(headings),
        "list_count": len(lists),
        "stanza_count": len(stanzas),
        "hardwrap_count": len(hardwraps),
        "ambiguous_multiline_count": len(ambiguous_multiline),
        "sentence_count": len(sentences),
        "sentence_delta": len(sentences) - r.EXPECTED_SENTENCES,
        "suspicious_long_proxy": suspicious,
        "suspicious_long_delta": suspicious - r.EXPECTED_SUSPICIOUS_LONG,
        "punctuation_issue_proxy": punct,
        "punctuation_issue_delta": punct - r.EXPECTED_PUNCT_ISSUES,
        "sentence_sequence_sha256": sha_sequence(sentences),
        "prepared_units_sha256": sha_sequence(prepared_units),
        "hardwrap_indices": sorted(hardwraps),
        "ambiguous_multiline_indices": sorted(ambiguous_multiline),
        "sentences": sentences,
    }


def main() -> None:
    raw = r.download_exact()
    text = r.historical_excerpt(raw)
    blocks = r.blocks_from_text(text)
    features = [r.block_features(block) for block in blocks]
    if len(blocks) != r.EXPECTED_CANDIDATES:
        raise RuntimeError(f"Stage5 candidate count mismatch: {len(blocks)} != {r.EXPECTED_CANDIDATES}")

    heading_scores = [(r.heading_score(b, f), i) for i, (b, f) in enumerate(zip(blocks, features))]
    headings = r.top_n_disjoint(heading_scores, r.EXPECTED_HEADINGS)
    list_scores = [(r.list_score(b, f), i) for i, (b, f) in enumerate(zip(blocks, features))]
    lists = r.top_n_disjoint(list_scores, r.EXPECTED_LISTS, headings)
    stanza_scores = [(r.stanza_score(b, f), i) for i, (b, f) in enumerate(zip(blocks, features))]
    stanzas = r.top_n_disjoint(stanza_scores, r.EXPECTED_STANZAS, headings | lists)

    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    rows = []
    for hard_family in ("balanced", "continuation", "width", "punctuation"):
        for threshold in (0.58, 0.60, 0.62, 0.64, 0.66):
            for abbrev_mode in ("minimal", "scientific"):
                rows.append(run_cell(
                    nlp, blocks, features, headings, lists, stanzas,
                    hard_family, threshold, abbrev_mode,
                ))

    rows.sort(key=lambda row: (
        abs(row["sentence_delta"]),
        abs(row["suspicious_long_delta"]),
        abs(row["punctuation_issue_delta"]),
        abs(row["hardwrap_threshold"] - 0.62),
        row["hardwrap_family"], row["abbrev_mode"],
    ))

    compact = [
        {k: v for k, v in row.items() if k not in {"sentences", "hardwrap_indices", "ambiguous_multiline_indices"}}
        for row in rows
    ]
    exact = [row for row in rows if row["sentence_count"] == r.EXPECTED_SENTENCES]
    report = {
        "schema": "rocketdict-stage7-structural-recovery/2",
        "non_promotional": True,
        "f96_holdout_not_used": True,
        "change_from_v1": "ambiguous multiline block is sentencized as one preserved block; only list/stanza lines are forced sentence boundaries",
        "source": {
            "full_go_sha256": r.GO_SHA,
            "historical_excerpt_sha256": r.EXCERPT_SHA,
            "historical_excerpt_bytes": r.EXCERPT_BYTES,
            "spacy_version": spacy.__version__,
            "sentence_engine": "spacy.blank(en)+sentencizer+abbrev-initial-postprocess",
        },
        "historical_invariants": {
            "paragraph_candidates": r.EXPECTED_CANDIDATES,
            "paragraphs": r.EXPECTED_PARAGRAPHS,
            "headings": r.EXPECTED_HEADINGS,
            "lists": r.EXPECTED_LISTS,
            "stanzas": r.EXPECTED_STANZAS,
            "sentences": r.EXPECTED_SENTENCES,
            "punctuation_issues": r.EXPECTED_PUNCT_ISSUES,
            "suspicious_long_units": r.EXPECTED_SUSPICIOUS_LONG,
        },
        "recovered_structure": {
            "heading_indices": sorted(headings),
            "list_indices": sorted(lists),
            "stanza_indices": sorted(stanzas),
        },
        "exact_sentence_count_cells": len(exact),
        "exact_cells": [
            {k: v for k, v in row.items() if k not in {"sentences", "hardwrap_indices", "ambiguous_multiline_indices"}}
            for row in exact
        ],
        "best_cells": compact[:20],
        "interpretation": "F96 remains unopened. Exact 2371 cells, if any, are candidates chosen only from pre-F96 Stage7 evidence.",
    }
    (OUT / "stage7-recovery-summary-v2.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "stage7-recovery-cells-v2.json").write_text(json.dumps(compact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for rank, row in enumerate(rows[:8]):
        with (OUT / f"v2-candidate-{rank:02d}-sentences.tsv").open("w", encoding="utf-8") as fh:
            for i, sentence in enumerate(row["sentences"]):
                fh.write(f"{i}\t{r.sha_text(sentence)}\t{sentence.replace(chr(9), ' ')}\n")
        (OUT / f"v2-candidate-{rank:02d}.json").write_text(
            json.dumps({k: v for k, v in row.items() if k != "sentences"}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
