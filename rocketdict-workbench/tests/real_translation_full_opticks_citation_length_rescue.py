from __future__ import annotations

"""Research-only local rescue for isolated Roman citation length hallucinations.

The broad citation-boundary feasibility experiment is intentionally not a
Product candidate: moving ordinary planner boundaries around every ``Sect.``
reference can introduce new omissions. This follow-up starts from a *proven
primary defect* instead. A row is eligible only when:

* its immutable source is only a Roman numeral plus period;
* Product hard checks fail solely because the target/source alpha length ratio
  exceeds the maintained maximum; and
* all non-length research diagnostics remain clean; and
* the row lies inside a narrow source-derived ``Sect. ...`` bibliographic span.

For an eligible failure, the source-derived local citation region is translated
again as raw rank-0 OPUS. If the containing Stage10 sentence extends beyond the
citation, the region is split immediately after the citation separator rather
than moving the normal 64-token planner cut through unrelated prose.

This is feasibility evidence only. Lower target alpha is explicitly *not* a
rejection here because the failing primary target is verbose hallucinated text.
Candidates must instead be mechanically strict-clean and remain subject to
semantic/QE review before any Product policy can be considered.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.structural_labels import STRUCTURAL_LABEL_CONTRACT
from rocketdict.translation_rescue import evaluate_rescue_pair
from rocketdict.translation_stage import PLANNER_CONTRACT, _balanced_protected_spans

SCHEMA = "rocketdict-full-opticks-citation-length-rescue-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_JSON_SHA256 = "48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133"
EXPECTED_DATABASE_SHA256 = "eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c"
EXPECTED_TRIGGER_COUNT = 2
CITATION_SPAN_CONTRACT = "rocketdict-research-abbreviated-section-citation-span/2"
TRIGGER_CONTRACT = "rocketdict-research-isolated-roman-citation-length-trigger/1"
SELECTOR_CONTRACT = "rocketdict-research-citation-length-strict-selector/1"

_ROMAN_FRAGMENT_RE = re.compile(r"\s*[IVXLCDM]+\.\s*", flags=re.IGNORECASE)
_CITATION_RE = re.compile(
    r"\bSect\.\s+(?:[IVXLCDM]+|\d+)\."
    r"(?:\s+(?:Prop|Sec)\.?\s*\d+(?:\s*,\s*\d+)*\.?)?",
    flags=re.IGNORECASE,
)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _alpha(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _inside_span(position: int, spans: list[tuple[int, int, str]]) -> bool:
    return any(start < position < end for start, end, _kind in spans)


def _trigger(row: dict[str, Any]) -> dict[str, Any] | None:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    if _ROMAN_FRAGMENT_RE.fullmatch(source) is None:
        return None
    verdict = evaluate_rescue_pair(source, target)
    numeric = dict(verdict.get("numeric_symbol") or {})
    eligible = bool(
        verdict.get("product_hard_passed") is False
        and verdict.get("length_passed") is False
        and verdict.get("punctuation_passed") is True
        and numeric.get("passed") is True
        and verdict.get("strict_research_passed") is True
    )
    if not eligible:
        return None
    return {
        "contract": TRIGGER_CONTRACT,
        "eligible": True,
        "source_text": source,
        "target_text": target,
        "primary_verdict": verdict,
    }


def _citation_for_row(
    content: str, row: dict[str, Any]
) -> re.Match[str] | None:
    start = int(row["source_start"])
    end = int(row["source_end"])
    for match in _CITATION_RE.finditer(content):
        if match.start() <= start and match.end() >= end:
            return match
    return None


def _context_index_for_position(
    contexts: list[dict[str, Any]], position: int
) -> int:
    for index, row in enumerate(contexts):
        if int(row["source_start"]) <= position < int(row["source_end"]):
            return index
    raise RuntimeError(f"No Stage10 context owns source position {position}")


def _consume_citation_separator(content: str, cursor: int, limit: int) -> int:
    # Keep punctuation/layout that terminates the local citation with the
    # citation chunk so the following prose starts lexically rather than with a
    # dangling comma/newline. Never cross into the next alphanumeric token.
    while cursor < limit and content[cursor] in " ,;:\t\r\n":
        cursor += 1
    return cursor


def _non_space_token_count(
    tokens: list[dict[str, Any]], start: int, end: int
) -> int:
    return sum(
        1
        for row in tokens
        if int(row["source_start"]) >= start
        and int(row["source_end"]) <= end
        and not bool((row.get("payload") or {}).get("flags", {}).get("is_space"))
    )


def _translate_chunks(
    translator: OpusTranslator,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    max_tokens = max(int(row["token_count"]) for row in chunks)
    hypotheses = translator.translate(
        [str(row["source_text"]) for row in chunks],
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=max(128, max_tokens * 8),
    )
    if len(hypotheses) != len(chunks):
        raise RuntimeError("Citation length rescue OPUS cardinality drift")
    result: list[dict[str, Any]] = []
    for chunk, generated in zip(chunks, hypotheses, strict=True):
        if not generated:
            raise RuntimeError("Citation length rescue OPUS returned no rank-0 hypothesis")
        target = str(generated[0].get("text") or "")
        if not target.strip():
            raise RuntimeError("Citation length rescue OPUS returned empty rank-0 target")
        verdict = evaluate_rescue_pair(str(chunk["source_text"]), target)
        result.append(
            {
                **chunk,
                "target_text": target,
                "rank": int(generated[0].get("rank") or 0),
                "score": generated[0].get("score"),
                "verdict": verdict,
            }
        )
    return result


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_CITATION_ROOT", "work/citation-input")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Citation length rescue immutable baseline inputs are missing")
    if _sha_file(baseline_path) != EXPECTED_BASELINE_JSON_SHA256:
        raise RuntimeError("Citation length rescue baseline JSON identity drift")
    if _sha_file(database) != EXPECTED_DATABASE_SHA256:
        raise RuntimeError("Citation length rescue Product database identity drift")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("Citation length rescue baseline schema drift")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Citation length rescue pinned source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Citation length rescue requires planner-v8 baseline")
    if baseline.get("structural_label_contract") != STRUCTURAL_LABEL_CONTRACT:
        raise RuntimeError("Citation length rescue structural-label contract drift")

    selected_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    nlp_run_id = int((baseline.get("stage8") or {})["nlp_run_id"])
    document_version_id = int(baseline["document_version_id"])

    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        selected_rows = sorted(
            get_run_items(connection, selected_run_id, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        contexts = sorted(
            get_run_items(connection, context_run_id, kind="context_sentence"),
            key=lambda row: int(row["sequence_number"]),
        )
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        document = get_document(connection, document_version_id)
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in selected_rows) != content:
        raise RuntimeError("Citation length rescue selected Stage12 coverage drift")

    triggers: list[tuple[dict[str, Any], dict[str, Any], re.Match[str]]] = []
    for row in selected_rows:
        trigger = _trigger(row)
        if trigger is None:
            continue
        citation = _citation_for_row(content, row)
        if citation is None:
            continue
        triggers.append((row, trigger, citation))
    if len(triggers) != EXPECTED_TRIGGER_COUNT:
        raise RuntimeError(
            f"Pinned isolated citation-length trigger drift: {len(triggers)} != {EXPECTED_TRIGGER_COUNT}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    balanced = _balanced_protected_spans(content, absolute_start=0)
    cases: list[dict[str, Any]] = []
    for failing_row, trigger, citation in triggers:
        citation_start_context = _context_index_for_position(contexts, citation.start())
        citation_end_context = _context_index_for_position(contexts, citation.end() - 1)
        group_start = int(contexts[citation_start_context]["source_start"])
        group_end = int(contexts[citation_end_context]["source_end"])
        local_end = _consume_citation_separator(content, citation.end(), group_end)
        if local_end <= group_start or local_end > group_end:
            raise RuntimeError("Citation length rescue local source boundary is invalid")
        if _inside_span(local_end, balanced):
            raise RuntimeError("Citation length rescue would cut inside existing protected structure")

        primary_rows = [
            row
            for row in selected_rows
            if int(row["source_start"]) >= group_start
            and int(row["source_end"]) <= group_end
        ]
        if not primary_rows:
            raise RuntimeError("Citation length rescue group has no primary rows")
        if int(primary_rows[0]["source_start"]) != group_start:
            raise RuntimeError("Citation length rescue primary group start drift")
        if int(primary_rows[-1]["source_end"]) != group_end:
            raise RuntimeError("Citation length rescue primary group end drift")
        if "".join(str(row.get("source_text") or "") for row in primary_rows) != content[group_start:group_end]:
            raise RuntimeError("Citation length rescue primary group is not byte-exact")

        chunks: list[dict[str, Any]] = []
        boundaries = [(group_start, local_end)]
        if local_end < group_end:
            boundaries.append((local_end, group_end))
        for start, end in boundaries:
            source = content[start:end]
            if not source:
                raise RuntimeError("Citation length rescue produced an empty source chunk")
            token_count = _non_space_token_count(nlp_tokens, start, end)
            if token_count <= 0:
                raise RuntimeError("Citation length rescue produced a tokenless source chunk")
            chunks.append(
                {
                    "source_start": start,
                    "source_end": end,
                    "source_text": source,
                    "token_count": token_count,
                }
            )
        if "".join(row["source_text"] for row in chunks) != content[group_start:group_end]:
            raise RuntimeError("Citation length rescue candidate is not byte-exact")

        candidate_rows = _translate_chunks(translator, chunks)
        strict_clean = all(
            (row.get("verdict") or {}).get("strictly_eligible") is True
            for row in candidate_rows
        )
        primary_target = "".join(
            str(row.get("target_text") or "") for row in primary_rows
        )
        candidate_target = "".join(str(row["target_text"]) for row in candidate_rows)
        cases.append(
            {
                "failing_primary_sequence": int(failing_row["sequence_number"]),
                "trigger": trigger,
                "citation_source_start": citation.start(),
                "citation_source_end": citation.end(),
                "citation_source_text": citation.group(0),
                "group_source_start": group_start,
                "group_source_end": group_end,
                "group_source_text": content[group_start:group_end],
                "local_citation_end": local_end,
                "primary_rows": [
                    {
                        "sequence_number": int(row["sequence_number"]),
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                        "source_text": str(row.get("source_text") or ""),
                        "target_text": str(row.get("target_text") or ""),
                        "verdict": evaluate_rescue_pair(
                            str(row.get("source_text") or ""),
                            str(row.get("target_text") or ""),
                        ),
                    }
                    for row in primary_rows
                ],
                "candidate_chunks": candidate_rows,
                "strict_clean_candidate": strict_clean,
                "selector_contract": SELECTOR_CONTRACT,
                "target_alpha_primary": _alpha(primary_target),
                "target_alpha_candidate": _alpha(candidate_target),
                "target_alpha_delta": _alpha(candidate_target) - _alpha(primary_target),
                "alpha_non_decreasing_required": False,
                "semantic_review_required": True,
                "source_bytes_rewritten": False,
                "target_rewriting": False,
                "placeholders": False,
                "post_translation_literal_injection": False,
            }
        )

    if _sha_file(database) != database_sha_before:
        raise RuntimeError("Citation length rescue mutated immutable Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only source-derived local resegmentation for isolated Roman "
            "citation length hallucinations"
        ),
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "baseline_json_sha256": EXPECTED_BASELINE_JSON_SHA256,
        "baseline_database_sha256": EXPECTED_DATABASE_SHA256,
        "selected_translation_run_id": selected_run_id,
        "selected_translation_output_sha256": str(selected_run.get("output_sha256") or ""),
        "planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
        "citation_span_contract": CITATION_SPAN_CONTRACT,
        "trigger_contract": TRIGGER_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "trigger_count": len(cases),
        "strict_clean_candidate_count": sum(
            row["strict_clean_candidate"] is True for row in cases
        ),
        "cases": cases,
        "alpha_non_decreasing_required": False,
        "alpha_policy_reason": (
            "primary trigger is a proven overlong hallucination; requiring candidate alpha "
            "to match hallucinated verbosity would reward the defect"
        ),
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "database_unchanged": True,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-citation-length-rescue-feasibility.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "trigger_count": len(cases),
                "strict_clean_candidate_count": payload[
                    "strict_clean_candidate_count"
                ],
                "candidate_sequences": [
                    row["failing_primary_sequence"] for row in cases
                ],
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
