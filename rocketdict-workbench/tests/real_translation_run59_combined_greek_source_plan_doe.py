from __future__ import annotations

"""Read-only DOE for source-planned combined Gutenberg Greek technical atoms.

A combined atom such as ``_A[Greek: a]_`` is source-owned technical notation,
not ordinary English prose.  The plan is created from immutable source before
MT: exact lexical prefix/suffix spans go to pinned OPUS raw rank0, while the
adjacent source whitespace and the complete combined Greek atom are rendered
from source bytes.  This mirrors the accepted illustration semantic-carrier
architecture and never rewrites model output or injects a token after MT.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.research_diagnostics import compare_critical_technical_tokens
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run59-combined-greek-source-plan-doe/1"
SOURCE_PLAN_CONTRACT = "rocketdict-combined-greek-source-planned-technical-atom/1"
BASE_RUN_ID = 59
BASE_DATABASE_SHA256 = "41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d"
BASE_OUTPUT_SHA256 = "5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 512
_COMBINED_SOURCE_RE = re.compile(r"_([A-Za-z]{1,3})\[Greek:\s*([^\]]+)\]_", re.IGNORECASE)
_COMBINED_TARGET_RE = re.compile(
    r"_([A-Za-z]{1,3})\[(?:Greek|греч\.?|греческ[^:\]]*)\s*:\s*([^\]]+)\]_",
    re.IGNORECASE,
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _combined(regex: re.Pattern[str], text: str) -> list[list[str]]:
    return [[m.group(1), m.group(2).strip()] for m in regex.finditer(text)]


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def _plan(source: str, match: re.Match[str]) -> dict[str, Any] | None:
    atom_start, atom_end = match.span()
    left = atom_start
    while left > 0 and source[left - 1] in " \t":
        left -= 1
    right = atom_end
    while right < len(source) and source[right] in " \t":
        right += 1
    prefix = source[:left]
    left_gap = source[left:atom_start]
    atom = source[atom_start:atom_end]
    right_gap = source[atom_end:right]
    suffix = source[right:]
    if not prefix.strip() or not suffix.strip() or not left_gap or not right_gap:
        return None
    pieces = [prefix, left_gap, atom, right_gap, suffix]
    if "".join(pieces) != source:
        raise RuntimeError("combined Greek source plan coverage drift")
    return {
        "contract": SOURCE_PLAN_CONTRACT,
        "created_before_mt": True,
        "prefix_source": prefix,
        "left_separator_source": left_gap,
        "technical_atom_source": atom,
        "right_separator_source": right_gap,
        "suffix_source": suffix,
        "technical_symbol": match.group(1),
        "greek_payload": match.group(2).strip(),
        "source_owned_technical_passthrough": True,
    }


def _piece_selection(source: str, target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    return {
        "accepted": bool(target.strip() and verdict.get("strictly_eligible") is True and emphasis.get("passed") is True),
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN59_COMBINED_GREEK_DOE_ROOT", "work/run59-combined-greek-source-plan-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    before_sha = _sha(database)
    if before_sha != BASE_DATABASE_SHA256:
        raise RuntimeError("canonical run59 database identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda r: int(r["sequence_number"]))
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run59 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    if len(rows) != 3335:
        raise RuntimeError("run59 segment census drift")
    content = str(document["content_text"])

    combined_rows: list[dict[str, Any]] = []
    trigger_rows: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source_text") or "")
        matches = list(_COMBINED_SOURCE_RE.finditer(source))
        if not matches:
            continue
        target = str(row.get("target_text") or "")
        source_combined = _combined(_COMBINED_SOURCE_RE, source)
        target_combined = _combined(_COMBINED_TARGET_RE, target)
        entry = {
            "sequence": int(row["sequence_number"]),
            "source_start": int(row["source_start"]),
            "source_combined": source_combined,
            "target_combined": target_combined,
            "preserved": source_combined == target_combined,
        }
        combined_rows.append(entry)
        if len(matches) != 1 or source_combined == target_combined:
            continue
        critical = compare_critical_technical_tokens(source, target)
        if critical.get("passed") is True:
            continue
        plan = _plan(source, matches[0])
        if plan is None:
            continue
        if content[int(row["source_start"]):int(row["source_end"])] != source:
            raise RuntimeError("combined Greek row differs from immutable source")
        trigger_rows.append({"row": row, "plan": plan, "base_critical": critical})

    # Generic census identity assertions after discovery, never routing whitelists.
    if len(combined_rows) != 2 or sum(int(x["preserved"]) for x in combined_rows) != 1:
        raise RuntimeError(f"combined Greek corpus census drift: {combined_rows!r}")
    if len(trigger_rows) != 1:
        raise RuntimeError(f"combined Greek trigger cohort drift: {len(trigger_rows)}")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    trigger = trigger_rows[0]
    row = trigger["row"]
    plan = trigger["plan"]
    model_inputs = [str(plan["prefix_source"]), str(plan["suffix_source"])]
    generated = translator.translate(model_inputs, beam_size=BEAM_SIZE, num_hypotheses=NUM_HYPOTHESES, max_decoding_length=MAX_DECODING_LENGTH)
    if len(generated) != 2 or any(len(group) != 1 for group in generated):
        raise RuntimeError("combined Greek OPUS cardinality drift")
    lexical: list[dict[str, Any]] = []
    for role, source, hypotheses in zip(("prefix", "suffix"), model_inputs, generated, strict=True):
        hyp = hypotheses[0]
        if int(hyp.get("rank", -1)) != 0:
            raise RuntimeError("combined Greek DOE permits raw rank0 only")
        target = str(hyp.get("text") or "")
        lexical.append({
            "role": role,
            "model_input": source,
            "hypothesis": dict(hyp),
            "raw_rank0_target": target,
            "selection": _piece_selection(source, target),
        })

    candidate_target = (
        lexical[0]["raw_rank0_target"]
        + str(plan["left_separator_source"])
        + str(plan["technical_atom_source"])
        + str(plan["right_separator_source"])
        + lexical[1]["raw_rank0_target"]
    )
    source = str(row.get("source_text") or "")
    base_target = str(row.get("target_text") or "")
    aggregate = evaluate_rescue_pair(source, candidate_target)
    emphasis = compare_emphasis_markup_preservation(source, candidate_target)
    critical = compare_critical_technical_tokens(source, candidate_target)
    accepted = bool(
        all(item["selection"]["accepted"] for item in lexical)
        and aggregate.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and critical.get("passed") is True
        and _alpha(candidate_target) >= _alpha(base_target)
    )

    after_sha = _sha(database)
    if after_sha != before_sha:
        raise RuntimeError("read-only combined Greek DOE mutated database")
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only source-planned rendering for a lost combined Gutenberg Greek technical atom",
        "base_run_id": BASE_RUN_ID,
        "base_database_sha256": before_sha,
        "base_run_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "segment_count": len(rows),
        "combined_greek_row_census": combined_rows,
        "combined_greek_row_count": len(combined_rows),
        "preserved_combined_greek_row_count": sum(int(x["preserved"]) for x in combined_rows),
        "trigger_count": len(trigger_rows),
        "trigger_sequence": int(row["sequence_number"]),
        "trigger_source_start": int(row["source_start"]),
        "source_plan": plan,
        "lexical_candidates": lexical,
        "candidate_target": candidate_target,
        "base_target": base_target,
        "aggregate_selection": {
            "accepted": accepted,
            "mechanical_verdict": aggregate,
            "emphasis_markup": emphasis,
            "critical_technical_tokens": critical,
            "base_target_alpha_count": _alpha(base_target),
            "candidate_target_alpha_count": _alpha(candidate_target),
            "target_alpha_non_decreasing": _alpha(candidate_target) >= _alpha(base_target),
        },
        "generation": {"implementation": "opus-en-ru-ct2", "beam_size": BEAM_SIZE, "num_hypotheses": NUM_HYPOTHESES, "max_decoding_length": MAX_DECODING_LENGTH, "selected_rank": 0},
        "database_unchanged": after_sha == before_sha,
        "database_sha256_after": after_sha,
        "source_coverage_byte_exact": True,
        "source_plan_created_before_mt": True,
        "source_owned_structural_passthrough": True,
        "source_bytes_rewritten": False,
        "model_input_source_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "run59-combined-greek-source-plan-doe.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": SCHEMA, "trigger_sequence": evidence["trigger_sequence"], "candidate_target": candidate_target, "accepted": accepted, "evidence_sha256": evidence["evidence_sha256"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
