from __future__ import annotations

"""Read-only source-owned split DOE for leading ``[in _Fig._ N.]`` references.

Run20 contains a corpus-wide family of leading Gutenberg figure references. One
member currently loses the complete reference and therefore its figure number.
This experiment does not fallback the whole sentence.  It partitions immutable
source into ``reference lead | whitespace | prose body``; the reference and
body are translated independently with raw rank-0 OPUS/TC-big and the exact
source whitespace is retained as a source-owned structural separator.

The experiment enumerates every member of the source-defined family, records
which current rows actually trigger the hard-failure+missing-reference
predicate, and never authorizes Product promotion without semantic review and a
later full-corpus replay.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-figure-lead-split-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_FAMILY_COUNT = 17
EXPECTED_TRIGGER_SEQUENCES = [325]
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768
MIN_SOURCE_ALPHA_RATIO = 0.60
MAX_SOURCE_ALPHA_RATIO = 1.60
_SOURCE_REFERENCE_RE = re.compile(
    r"\A(?P<lead>\[in\s+_Fig\._\s+(?P<number>\d+)\.\])(?P<gap>\s*)",
    flags=re.IGNORECASE,
)
_TARGET_REFERENCE_RE_TEMPLATE = (
    r"\A\[[^\]]*_(?:Fig\.|Фиг\.|рис\.)_[^\]]*"
    r"(?<!\d){number}(?!\d)[^\]]*\.\]"
)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def _reference_preserved(target: str, number: str) -> bool:
    pattern = re.compile(
        _TARGET_REFERENCE_RE_TEMPLATE.format(number=re.escape(number)),
        flags=re.IGNORECASE,
    )
    return pattern.search(target) is not None


def _current_trigger(source: str, target: str) -> dict[str, Any]:
    match = _SOURCE_REFERENCE_RE.match(source)
    verdict = evaluate_rescue_pair(source, target)
    if match is None:
        return {"eligible": False, "reason": "no_source_reference"}
    number = str(match.group("number"))
    preserved = _reference_preserved(target, number)
    return {
        "eligible": bool(verdict.get("product_hard_passed") is not True and not preserved),
        "source_figure_number": number,
        "current_product_hard_passed": verdict.get("product_hard_passed") is True,
        "current_reference_preserved": preserved,
        "current_verdict": verdict,
    }


def _translate_pair(translator: Any, lead: str, body: str) -> tuple[str, str, list[Any]]:
    generated = translator.translate(
        [lead, body],
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(generated) != 2 or any(len(rows) != 1 for rows in generated):
        raise RuntimeError("figure-lead split translation cardinality drift")
    return (
        str(generated[0][0].get("text") or ""),
        str(generated[1][0].get("text") or ""),
        [generated[0][0].get("score"), generated[1][0].get("score")],
    )


def _candidate(
    source: str,
    *,
    lead: str,
    gap: str,
    body: str,
    lead_target: str,
    body_target: str,
    figure_number: str,
) -> dict[str, Any]:
    # ``gap`` is immutable source-owned structure, not generated or injected text.
    target = lead_target + gap + body_target
    lead_eval = evaluate_rescue_pair(lead, lead_target)
    body_eval = evaluate_rescue_pair(body, body_target)
    aggregate_eval = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    reference_preserved = _reference_preserved(target, figure_number)
    source_alpha = _alpha(source)
    target_alpha = _alpha(target)
    ratio = target_alpha / source_alpha if source_alpha else (1.0 if target_alpha == 0 else float("inf"))
    accepted = bool(
        lead_eval.get("strictly_eligible") is True
        and body_eval.get("strictly_eligible") is True
        and aggregate_eval.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and reference_preserved
        and MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO
    )
    return {
        "candidate_target_text": target,
        "reference_target_text": lead_target,
        "body_target_text": body_target,
        "source_owned_gap": gap,
        "source_owned_gap_exact": True,
        "target_separator_injected": False,
        "reference_evaluation": lead_eval,
        "body_evaluation": body_eval,
        "aggregate_evaluation": aggregate_eval,
        "emphasis_markup": emphasis,
        "reference_preserved": reference_preserved,
        "source_alpha_ratio": ratio,
        "source_alpha_ratio_range": [MIN_SOURCE_ALPHA_RATIO, MAX_SOURCE_ALPHA_RATIO],
        "mechanically_admissible": accepted,
    }


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RUN20_FIGURE_LEAD_SPLIT_DOE_ROOT", "work/run20-figure-lead-split-doe")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("figure-lead split DOE requires exact run20 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        output = dict(run.get("output") or {})
        rows = sorted(get_run_items(connection, BASE_RUN_ID, kind="translation_segment"), key=lambda row: int(row["sequence_number"]))
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run20 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run20 source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in rows) != content:
        raise RuntimeError("run20 source coverage drift")

    family: list[dict[str, Any]] = []
    for row in rows:
        source = str(row.get("source_text") or "")
        match = _SOURCE_REFERENCE_RE.match(source)
        if match is None:
            continue
        lead = str(match.group("lead"))
        gap = str(match.group("gap"))
        body = source[match.end():]
        if not body.strip():
            # A bare structural reference is already represented safely by the
            # current row and is not a prose-body split candidate.
            continue
        if lead + gap + body != source:
            raise RuntimeError("figure-lead source partition drift")
        family.append({
            "row": row,
            "source": source,
            "lead": lead,
            "gap": gap,
            "body": body,
            "figure_number": str(match.group("number")),
            "trigger": _current_trigger(source, str(row.get("target_text") or "")),
        })
    if len(family) != EXPECTED_FAMILY_COUNT:
        raise RuntimeError(f"figure-lead family census drift: {len(family)}")
    triggers = [int(item["row"]["sequence_number"]) for item in family if item["trigger"]["eligible"] is True]
    if triggers != EXPECTED_TRIGGER_SEQUENCES:
        raise RuntimeError(f"figure-lead trigger census drift: {triggers!r}")

    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    records: list[dict[str, Any]] = []
    for item in family:
        model_rows: dict[str, Any] = {}
        for name, translator in (("opus", opus), ("tc_big", tc_big)):
            lead_target, body_target, scores = _translate_pair(translator, item["lead"], item["body"])
            model_rows[name] = {
                "scores": scores,
                **_candidate(
                    item["source"],
                    lead=item["lead"],
                    gap=item["gap"],
                    body=item["body"],
                    lead_target=lead_target,
                    body_target=body_target,
                    figure_number=item["figure_number"],
                ),
            }
        records.append({
            "sequence_number": int(item["row"]["sequence_number"]),
            "source_start": int(item["row"]["source_start"]),
            "source_end": int(item["row"]["source_end"]),
            "source_text": item["source"],
            "current_target_text": str(item["row"].get("target_text") or ""),
            "figure_number": item["figure_number"],
            "reference_source_text": item["lead"],
            "source_owned_gap": item["gap"],
            "body_source_text": item["body"],
            "trigger": item["trigger"],
            "models": model_rows,
        })

    trigger_record = next(row for row in records if row["sequence_number"] == EXPECTED_TRIGGER_SEQUENCES[0])
    asset = load_tc_big_asset()
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only source-owned leading figure-reference split DOE across complete run20 source family",
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "family_count": len(records),
        "family_sequences": [row["sequence_number"] for row in records],
        "trigger_sequences": triggers,
        "records": records,
        "trigger_model_admissibility": {
            model: bool(trigger_record["models"][model]["mechanically_admissible"])
            for model in ("opus", "tc_big")
        },
        "tc_big_asset": {
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "payload_file_count": asset.payload_file_count,
            "payload_bytes": asset.payload_bytes,
        },
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "source_owned_whitespace_preserved_exactly": True,
        "target_separator_injected": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
    }
    if _sha(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("figure-lead DOE mutated run20 database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    (root / "full-opticks-run20-figure-lead-split-doe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "family_count": len(records),
        "family_sequences": evidence["family_sequences"],
        "trigger_sequences": triggers,
        "trigger_model_admissibility": evidence["trigger_model_admissibility"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
