from __future__ import annotations

"""Full-Opticks research shadow for conservative punctuation-aware soft cuts.

Product code is not modified. The probe rebuilds planner-v8 from the immutable
successful acceptance DB, but for an over-budget ordinary unit it may move the
existing desired cut at most 16 lexical tokens backward to a source ``; : . ! ?``
boundary that is outside protected spans. If none exists, the maintained v8
split function is used unchanged. All table/label/block-ID contracts remain the
maintained implementation. Numeric shadow units are then evaluated with real
rank0 OPUS and the unchanged strict verdict. No source/target repair occurs.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_document_segments, get_run_items
from rocketdict.numeric_integrity import extract_numeric_literals
from rocketdict.runtime import OpusTranslator
from rocketdict.table_stage12 import build_stage12_table_plan, render_stage12_table_rank0
import rocketdict.translation_stage as translation_stage
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-punctuation-shadow/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
RAW_SOURCE_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
BACKTRACK_TOKENS = 16
MAJOR = frozenset({";", ":", ".", "!", "?"})
BATCH_SIZE = 48


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _token_text(token: dict[str, Any]) -> str:
    value = token.get("source_text")
    return str(value if value is not None else token.get("text") or "")


def _translate(translator: OpusTranslator, texts: list[str], max_length: int) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=6,
                num_hypotheses=1,
                max_decoding_length=max_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("punctuation-shadow translation cardinality mismatch")
    return output


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-artifact/full-opticks-numeric-stress")).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks baseline is incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("unexpected full-Opticks baseline schema")
    if baseline.get("source_sha256") != RAW_SOURCE_SHA256:
        raise RuntimeError("raw pinned Opticks identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("shadow baseline planner is not current")
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
        segments = get_document_segments(connection, document_version_id)
        nlp_tokens = get_run_items(connection, nlp_run_id, kind="nlp_token")
        context_items = get_run_items(connection, context_run_id, kind="context_sentence")
        persisted = get_run_items(connection, translation_run_id, kind="translation_segment")
    content = str(document["content_text"])
    document_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if document_sha != str(baseline.get("source_text_sha256") or ""):
        raise RuntimeError("persisted normalized Opticks text identity drift")

    exact_product = {
        (int(item["source_start"]), int(item["source_end"])): dict(item)
        for item in persisted
    }
    maintained_boundaries = {int(item["source_end"]) for item in persisted[:-1]}
    original_split = translation_stage._safe_forward_split_index
    choices: list[dict[str, Any]] = []

    def shadow_split(
        tokens: list[dict[str, Any]],
        *,
        desired_index: int,
        spans: list[tuple[int, int, str]],
    ) -> int:
        if desired_index >= len(tokens):
            return len(tokens)
        maintained = original_split(tokens, desired_index=desired_index, spans=spans)
        lower = max(0, desired_index - BACKTRACK_TOKENS)
        for punctuation_index in range(desired_index - 1, lower - 1, -1):
            if _token_text(tokens[punctuation_index]) not in MAJOR:
                continue
            split_index = punctuation_index + 1
            if split_index >= len(tokens):
                return len(tokens)
            cut = int(tokens[split_index]["source_start"])
            if translation_stage._cut_inside_span(cut, spans):
                continue
            if split_index != maintained:
                choices.append(
                    {
                        "desired_index": desired_index,
                        "maintained_split_index": maintained,
                        "shadow_split_index": split_index,
                        "backtrack_tokens": desired_index - split_index,
                        "punctuation": _token_text(tokens[punctuation_index]),
                        "cut": cut,
                    }
                )
            return split_index
        return maintained

    db_sha_before = _sha(database)
    translation_stage._safe_forward_split_index = shadow_split
    try:
        units = translation_stage.segment_translation_units(
            content,
            segments,
            context_items,
            nlp_tokens,
            selected_format="txt",
            preferred_tokens=preferred_tokens,
        )
    finally:
        translation_stage._safe_forward_split_index = original_split

    if "".join(str(unit["text"]) for unit in units) != content:
        raise RuntimeError("shadow plan is not byte-exact")
    cursor = 0
    for unit in units:
        if int(unit["start"]) != cursor or int(unit["end"]) <= cursor:
            raise RuntimeError("shadow plan source coverage is discontinuous")
        cursor = int(unit["end"])
    if cursor != len(content):
        raise RuntimeError("shadow plan does not cover the complete source")

    numeric_units = [(i, unit) for i, unit in enumerate(units) if extract_numeric_literals(str(unit["text"]))]
    requests: list[str] = []
    refs: list[tuple[int, int | None]] = []
    table_plans: dict[int, Any] = {}
    reused: dict[int, str] = {}
    proxies: list[int] = []
    for sequence, unit in numeric_units:
        metadata = dict(unit.get("metadata") or {})
        source_kind = str(metadata.get("source") or "")
        span = (int(unit["start"]), int(unit["end"]))
        if source_kind == "structural_label":
            product = exact_product.get(span)
            if product is None or not isinstance((product.get("payload") or {}).get("structural_label"), dict):
                raise RuntimeError("shadow structural label lost exact Product provenance")
            reused[sequence] = str(product.get("target_text") or "")
        elif source_kind == "block_section_identifier":
            reused[sequence] = str(unit["text"])
        elif source_kind == "ascii_table":
            plan = build_stage12_table_plan(str(unit["text"]), absolute_start=int(unit["start"]))
            table_plans[sequence] = plan
            for group in plan.groups:
                requests.append(group.source_text)
                refs.append((sequence, int(group.index)))
                proxies.append(max(1, len(group.source_text.split())))
        else:
            requests.append(str(unit["text"]))
            refs.append((sequence, None))
            proxies.append(max(1, int(metadata.get("token_count") or 0)))

    max_length = max(128, max([preferred_tokens, *proxies], default=preferred_tokens) * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    rows = _translate(translator, requests, max_length) if requests else []
    generated = {ref: hypotheses for ref, hypotheses in zip(refs, rows, strict=True)}

    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation = dict(quality.get("punctuation") or {})
    length_ratio = dict(quality.get("length_ratio") or {})
    failures: list[dict[str, Any]] = []
    long_parent_rows: list[dict[str, Any]] = []
    for sequence, unit in numeric_units:
        if sequence in reused:
            target = reused[sequence]
            origin = "maintained_source_structure_or_exact_product"
        elif sequence in table_plans:
            plan = table_plans[sequence]
            mapping = {int(group.index): generated[(sequence, int(group.index))] for group in plan.groups}
            target, _ = render_stage12_table_rank0(plan, mapping)
            origin = "maintained_table_composite"
        else:
            hypotheses = generated[(sequence, None)]
            if not hypotheses:
                raise RuntimeError(f"OPUS returned no shadow rank0 hypothesis for {sequence}")
            target = str(hypotheses[0].get("text") or "")
            if not target.strip():
                raise RuntimeError(f"OPUS returned empty shadow rank0 target for {sequence}")
            origin = "real_opus_rank0"
        source_row = {
            "sequence_number": sequence,
            "source_start": int(unit["start"]),
            "source_end": int(unit["end"]),
            "source_text": str(unit["text"]),
            "target_text": None,
        }
        verdict = _verdict(source_row, target, punctuation_parameters=punctuation, length_parameters=length_ratio)
        record = {
            "shadow_sequence": sequence,
            "source_start": int(unit["start"]),
            "source_end": int(unit["end"]),
            "source_text": str(unit["text"]),
            "target_text": target,
            "target_origin": origin,
            "planner": dict(unit.get("metadata") or {}),
            "verdict": verdict,
        }
        if (verdict.get("numeric_symbol") or {}).get("passed") is False:
            failures.append(record)
        if int(unit["start"]) < 133465 and int(unit["end"]) > 132834:
            long_parent_rows.append(record)

    db_sha_after = _sha(database)
    if db_sha_after != db_sha_before:
        raise RuntimeError("shadow inference mutated retained Product database")

    shadow_boundaries = {int(unit["end"]) for unit in units[:-1]}
    baseline_failure_spans = {
        (int(row["source_start"]), int(row["source_end"]))
        for row in baseline.get("numeric_failures") or []
    }
    shadow_failure_spans = {(int(row["source_start"]), int(row["source_end"])) for row in failures}
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-corpus numeric shadow of conservative major-punctuation backtracking",
        "promotion_allowed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "raw_source_sha256": RAW_SOURCE_SHA256,
        "normalized_source_sha256": document_sha,
        "maintained_planner_contract": PLANNER_CONTRACT,
        "candidate_policy": {
            "backtrack_tokens": BACKTRACK_TOKENS,
            "major_punctuation": sorted(MAJOR),
            "fallback": "maintained_planner_v8_split_choice",
        },
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_json_sha256": _sha(baseline_path),
        "baseline_planned_unit_count": int(baseline.get("planned_unit_count") or 0),
        "shadow_planned_unit_count": len(units),
        "changed_split_choice_count": len(choices),
        "changed_split_choices": choices,
        "removed_boundary_count": len(maintained_boundaries - shadow_boundaries),
        "added_boundary_count": len(shadow_boundaries - maintained_boundaries),
        "baseline_numeric_bearing_unit_count": int(baseline.get("numeric_bearing_unit_count") or 0),
        "shadow_numeric_bearing_unit_count": len(numeric_units),
        "baseline_numeric_failure_count": int(baseline.get("product_numeric_failure_count") or 0),
        "shadow_numeric_failure_count": len(failures),
        "same_exact_failure_span_count": len(baseline_failure_spans & shadow_failure_spans),
        "long_parent_rows": long_parent_rows,
        "shadow_numeric_failures": failures,
        "database_sha256_before": db_sha_before,
        "database_sha256_after": db_sha_after,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(os.environ.get("ROCKETDICT_PUNCTUATION_SHADOW_ROOT", "work/punctuation-shadow")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "full-opticks-punctuation-shadow.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
