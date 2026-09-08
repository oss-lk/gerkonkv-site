from __future__ import annotations

"""Research-only full-Opticks shadow plan with conservative major-punctuation backtracking.

The maintained planner is not modified.  This probe reconstructs the current
planner-v8 plan from the immutable successful full-Opticks database while
temporarily changing only the soft-budget split-index choice:

- when a unit exceeds the preferred token budget, inspect at most 16 lexical
  tokens immediately before the existing desired cut;
- if a source token ``;``, ``:``, ``.``, ``!`` or ``?`` yields a protected-span-
  safe boundary, cut after that token;
- otherwise delegate exactly to the maintained planner-v8 split function.

All source-structure partitions (tables, structural labels, block section IDs)
remain the maintained Product implementation.  The complete shadow plan must
cover immutable source bytes exactly.  Numeric-bearing ordinary shadow units
are translated with real rank0 OPUS; table units use the maintained composite
renderer; structural labels and block IDs retain their already-proven Product
handling by exact immutable span.  Nothing rewrites a target or inserts a
literal after MT.  This is feasibility evidence, not Product policy.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_document_segments, get_run_items
from rocketdict.numeric_integrity import extract_numeric_literals
from rocketdict.runtime import OpusTranslator
from rocketdict.structural_labels import STRUCTURAL_LABEL_CONTRACT
from rocketdict.table_stage12 import (
    TABLE_STAGE12_CONTRACT,
    build_stage12_table_plan,
    render_stage12_table_rank0,
)
import rocketdict.translation_stage as translation_stage
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-punctuation-shadow/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
BACKTRACK_TOKENS = 16
MAJOR_PUNCTUATION = frozenset({";", ":", ".", "!", "?"})
BATCH_SIZE = 48


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _translate_batches(
    translator: OpusTranslator,
    texts: list[str],
    *,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=6,
                num_hypotheses=1,
                max_decoding_length=max_decoding_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("punctuation-shadow translation cardinality mismatch")
    return output


def _source_token(token: dict[str, Any]) -> str:
    return str(token.get("source_text") if token.get("source_text") is not None else token.get("text") or "")


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-artifact/full-opticks-numeric-stress")).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks baseline is incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA or baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("unexpected pinned full-Opticks baseline")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("punctuation-shadow baseline planner is not current")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline artifact identity drift")

    document_version_id = int(baseline["document_version_id"])
    nlp_run_id = int((baseline.get("stage8") or {})["nlp_run_id"])
    context_run_id = int((baseline.get("stage10") or {})["context_run_id"])
    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    preferred_tokens = int((baseline.get("stage12_parameters") or {}).get("plan_preferred_unit_tokens") or 64)

    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        document_segments = get_document_segments(connection, document_version_id)
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        context_items = get_run_items(connection, context_run_id, kind="context_sentence")
        persisted = get_run_items(connection, translation_run_id, kind="translation_segment")
    content = str(document["content_text"])
    if hashlib.sha256(content.encode("utf-8")).hexdigest() != OPTICKS_SHA256:
        raise RuntimeError("immutable Opticks text identity drift")

    exact_product: dict[tuple[int, int], dict[str, Any]] = {
        (int(item["source_start"]), int(item["source_end"])): dict(item)
        for item in persisted
    }
    current_boundaries = {int(item["source_end"]) for item in persisted[:-1]}
    original_split = translation_stage._safe_forward_split_index
    changed_choices: list[dict[str, Any]] = []

    def punctuation_split(
        tokens: list[dict[str, Any]],
        *,
        desired_index: int,
        spans: list[tuple[int, int, str]],
    ) -> int:
        if desired_index >= len(tokens):
            return len(tokens)
        lower = max(0, desired_index - BACKTRACK_TOKENS)
        for punctuation_index in range(desired_index - 1, lower - 1, -1):
            if _source_token(tokens[punctuation_index]) not in MAJOR_PUNCTUATION:
                continue
            split_index = punctuation_index + 1
            if split_index >= len(tokens):
                return len(tokens)
            cut = int(tokens[split_index]["source_start"])
            if translation_stage._cut_inside_span(cut, spans):
                continue
            maintained = original_split(tokens, desired_index=desired_index, spans=spans)
            if split_index != maintained:
                changed_choices.append(
                    {
                        "desired_index": desired_index,
                        "maintained_split_index": maintained,
                        "shadow_split_index": split_index,
                        "backtrack_tokens": desired_index - split_index,
                        "punctuation": _source_token(tokens[punctuation_index]),
                        "cut": cut,
                    }
                )
            return split_index
        return original_split(tokens, desired_index=desired_index, spans=spans)

    database_sha_before = _sha(database)
    translation_stage._safe_forward_split_index = punctuation_split
    try:
        shadow_units = translation_stage.segment_translation_units(
            content,
            document_segments,
            context_items,
            nlp_tokens,
            selected_format="txt",
            preferred_tokens=preferred_tokens,
        )
    finally:
        translation_stage._safe_forward_split_index = original_split

    if "".join(str(unit["text"]) for unit in shadow_units) != content:
        raise RuntimeError("punctuation-shadow plan is not byte-exact")
    cursor = 0
    for unit in shadow_units:
        if int(unit["start"]) != cursor or int(unit["end"]) <= cursor:
            raise RuntimeError("punctuation-shadow plan source coverage is discontinuous")
        cursor = int(unit["end"])
    if cursor != len(content):
        raise RuntimeError("punctuation-shadow plan does not cover complete source")

    shadow_boundaries = {int(unit["end"]) for unit in shadow_units[:-1]}
    numeric_units = [
        (index, unit)
        for index, unit in enumerate(shadow_units)
        if extract_numeric_literals(str(unit["text"]))
    ]
    if not numeric_units:
        raise RuntimeError("punctuation-shadow plan produced no numeric units")

    requests: list[str] = []
    refs: list[tuple[int, int | None]] = []
    table_plans: dict[int, Any] = {}
    reused_targets: dict[int, str] = {}
    proxy_counts: list[int] = []
    for sequence, unit in numeric_units:
        metadata = dict(unit.get("metadata") or {})
        source = str(metadata.get("source") or "")
        span = (int(unit["start"]), int(unit["end"]))
        if source == "structural_label":
            item = exact_product.get(span)
            if item is None or not isinstance((item.get("payload") or {}).get("structural_label"), dict):
                raise RuntimeError("shadow structural label lacks exact proven Product target")
            reused_targets[sequence] = str(item.get("target_text") or "")
            continue
        if source == "block_section_identifier":
            reused_targets[sequence] = str(unit["text"])
            continue
        if source == "ascii_table":
            plan = build_stage12_table_plan(str(unit["text"]), absolute_start=int(unit["start"]))
            table_plans[sequence] = plan
            for group in plan.groups:
                requests.append(group.source_text)
                refs.append((sequence, int(group.index)))
                proxy_counts.append(max(1, len(group.source_text.split())))
            continue
        requests.append(str(unit["text"]))
        refs.append((sequence, None))
        proxy_counts.append(max(1, int(metadata.get("token_count") or 0)))

    max_proxy = max(proxy_counts, default=preferred_tokens)
    max_decoding_length = max(128, max(preferred_tokens, max_proxy) * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated_rows = _translate_batches(translator, requests, max_decoding_length=max_decoding_length) if requests else []
    generated = {ref: hypotheses for ref, hypotheses in zip(refs, generated_rows, strict=True)}

    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})
    failures: list[dict[str, Any]] = []
    passes = 0
    long_parent_rows: list[dict[str, Any]] = []
    for sequence, unit in numeric_units:
        if sequence in reused_targets:
            target = reused_targets[sequence]
            target_origin = "maintained_source_structure_or_exact_product"
        elif sequence in table_plans:
            plan = table_plans[sequence]
            mapping = {int(group.index): generated[(sequence, int(group.index))] for group in plan.groups}
            target, _ = render_stage12_table_rank0(plan, mapping)
            target_origin = "maintained_table_composite"
        else:
            hypotheses = generated[(sequence, None)]
            if not hypotheses:
                raise RuntimeError(f"OPUS returned no rank0 hypothesis for shadow unit {sequence}")
            target = str(hypotheses[0].get("text") or "")
            if not target.strip():
                raise RuntimeError(f"OPUS returned empty rank0 target for shadow unit {sequence}")
            target_origin = "real_opus_rank0"
        source_row = {
            "sequence_number": sequence,
            "source_start": int(unit["start"]),
            "source_end": int(unit["end"]),
            "source_text": str(unit["text"]),
            "target_text": None,
        }
        verdict = _verdict(
            source_row,
            target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        record = {
            "shadow_sequence": sequence,
            "source_start": int(unit["start"]),
            "source_end": int(unit["end"]),
            "source_text": str(unit["text"]),
            "target_text": target,
            "target_origin": target_origin,
            "planner": dict(unit.get("metadata") or {}),
            "verdict": verdict,
        }
        if verdict.get("strictly_eligible") is True:
            passes += 1
        if (verdict.get("numeric_symbol") or {}).get("passed") is False:
            failures.append(record)
        if int(unit["start"]) < 133465 and int(unit["end"]) > 132834:
            long_parent_rows.append(record)

    database_sha_after = _sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("punctuation-shadow inference mutated retained Product database")

    baseline_failure_spans = {
        (int(row["source_start"]), int(row["source_end"]))
        for row in baseline.get("numeric_failures") or []
    }
    shadow_failure_spans = {(int(row["source_start"]), int(row["source_end"])) for row in failures}
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-corpus numeric shadow of conservative major-punctuation backtracking before soft-budget cuts",
        "promotion_allowed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": OPTICKS_SHA256,
        "maintained_planner_contract": PLANNER_CONTRACT,
        "candidate_policy": {
            "backtrack_tokens": BACKTRACK_TOKENS,
            "major_punctuation": sorted(MAJOR_PUNCTUATION),
            "fallback": "maintained_planner_v8_split_choice",
        },
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_json_sha256": _sha(baseline_path),
        "baseline_planned_unit_count": int(baseline.get("planned_unit_count") or 0),
        "shadow_planned_unit_count": len(shadow_units),
        "changed_split_choice_count": len(changed_choices),
        "changed_split_choices": changed_choices,
        "removed_boundary_count": len(current_boundaries - shadow_boundaries),
        "added_boundary_count": len(shadow_boundaries - current_boundaries),
        "baseline_numeric_bearing_unit_count": int(baseline.get("numeric_bearing_unit_count") or 0),
        "shadow_numeric_bearing_unit_count": len(numeric_units),
        "baseline_numeric_failure_count": int(baseline.get("product_numeric_failure_count") or 0),
        "shadow_numeric_failure_count": len(failures),
        "shadow_strict_pass_count": passes,
        "baseline_failure_span_count": len(baseline_failure_spans),
        "shadow_failure_span_count": len(shadow_failure_spans),
        "same_exact_failure_span_count": len(baseline_failure_spans & shadow_failure_spans),
        "long_parent_rows": long_parent_rows,
        "shadow_numeric_failures": failures,
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(os.environ.get("ROCKETDICT_PUNCTUATION_SHADOW_ROOT", "work/punctuation-shadow")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-punctuation-shadow.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "baseline_planned_unit_count": payload["baseline_planned_unit_count"],
        "shadow_planned_unit_count": payload["shadow_planned_unit_count"],
        "changed_split_choice_count": payload["changed_split_choice_count"],
        "baseline_numeric_failure_count": payload["baseline_numeric_failure_count"],
        "shadow_numeric_failure_count": payload["shadow_numeric_failure_count"],
        "same_exact_failure_span_count": payload["same_exact_failure_span_count"],
        "evidence_sha256": payload["evidence_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
