from __future__ import annotations

"""Full contiguous Opticks numeric-integrity stress for current Stage12 planning.

The harness runs real maintained Stage8/10 over the complete pinned Opticks
source and materializes the current byte-exact Stage12 plan.  Every
numeric-bearing planned unit is then translated with the same rank-0 semantics
as Product Stage12.  Ordinary units go directly to OPUS; detected ASCII-table
units send only their source-only logical text groups to OPUS and render
source-owned geometry/numeric cells unchanged from their pre-MT spans.

Beam-6 n-best remains a research retry only for ordinary rank-0 numeric
failures.  Composite table segments are never retried by translating the whole
table as prose, because that would no longer represent Product behavior.
Nothing is repaired or inserted after MT and inference must not mutate the
Stage8/10 research DB.
"""

from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import shutil
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
from rocketdict.translation_stage import PLANNER_CONTRACT, segment_translation_units
from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_preflight import build_product_preflight
from rocketdict_workbench.project import WorkbenchProject

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
NBEST_GENERATION = {"beam_size": 6, "num_hypotheses": 6}
BATCH_SIZE = 48


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


def _call(core: RocketDictCore, database: Path, operation: str, **params: Any) -> dict[str, Any]:
    return dict(
        core.api(
            database,
            "call",
            operation,
            "--params",
            json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            timeout=7200,
        )
    )


def _profile_stage(preflight: dict[str, Any], stage_number: int) -> tuple[str, dict[str, Any]]:
    row = ((preflight.get("profile") or {}).get("stages") or {}).get(str(stage_number))
    if not isinstance(row, dict):
        raise RuntimeError(f"Product preflight lacks Stage{stage_number}")
    return str(row["implementation"]), dict(row.get("parameters") or {})


def _quality_parameters(preflight: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    by_key = {
        str(row.get("implementation") or ""): dict(row.get("parameters") or {})
        for row in ((preflight.get("profile") or {}).get("quality_gates") or [])
    }
    length = dict(by_key.get("rocketdict-length-ratio-proxy") or {})
    punctuation = dict(by_key.get("rocketdict-punctuation-preservation") or {})
    if not length:
        raise RuntimeError("Product preflight lacks length-ratio gate parameters")
    return punctuation, length


def _translate_batches(
    translator: OpusTranslator,
    texts: list[str],
    *,
    beam_size: int,
    num_hypotheses: int,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        output.extend(
            translator.translate(
                texts[start : start + BATCH_SIZE],
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                max_decoding_length=max_decoding_length,
            )
        )
    if len(output) != len(texts):
        raise RuntimeError("Numeric stress translation batch cardinality mismatch")
    return output


def _row(unit: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {
        "sequence_number": sequence,
        "source_start": int(unit["start"]),
        "source_end": int(unit["end"]),
        "source_text": str(unit["text"]),
        "target_text": None,
    }


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(a=left, b=right, autojunk=False).ratio()


def _production_rank0_targets(
    translator: OpusTranslator,
    numeric_units: list[tuple[int, dict[str, Any]]],
    *,
    beam_size: int,
    preferred_tokens: int,
) -> tuple[dict[int, dict[str, Any]], int, int]:
    requests: list[str] = []
    refs: list[tuple[int, int | None]] = []
    proxy_counts: list[int] = []
    table_plans: dict[int, Any] = {}

    for sequence, unit in numeric_units:
        metadata = dict(unit.get("metadata") or {})
        if metadata.get("source") == "ascii_table":
            plan = build_stage12_table_plan(
                str(unit["text"]), absolute_start=int(unit["start"])
            )
            table_plans[sequence] = plan
            for group in plan.groups:
                requests.append(group.source_text)
                refs.append((sequence, int(group.index)))
                proxy_counts.append(max(1, len(group.source_text.split())))
        else:
            requests.append(str(unit["text"]))
            refs.append((sequence, None))
            proxy_counts.append(max(1, int(metadata.get("token_count") or 0)))

    max_request_proxy = max(proxy_counts, default=0)
    max_decoding_length = max(128, max(preferred_tokens, max_request_proxy) * 8)
    generated_rows = _translate_batches(
        translator,
        requests,
        beam_size=beam_size,
        num_hypotheses=1,
        max_decoding_length=max_decoding_length,
    ) if requests else []
    generated = {
        ref: hypotheses
        for ref, hypotheses in zip(refs, generated_rows, strict=True)
    }

    output: dict[int, dict[str, Any]] = {}
    table_request_count = 0
    for sequence, unit in numeric_units:
        if sequence in table_plans:
            plan = table_plans[sequence]
            mapping = {
                int(group.index): generated[(sequence, int(group.index))]
                for group in plan.groups
            }
            target, group_evidence = render_stage12_table_rank0(plan, mapping)
            table_request_count += len(plan.groups)
            output[sequence] = {
                "target_text": target,
                "rank0_score": None,
                "production_table_composite": True,
                "table_stage12_contract": TABLE_STAGE12_CONTRACT,
                "table_logical_group_count": len(plan.groups),
                "table_logical_groups": group_evidence,
            }
            continue
        hypotheses = generated[(sequence, None)]
        if not hypotheses:
            raise RuntimeError(f"OPUS returned no rank-0 hypothesis for planned unit {sequence}")
        target = str(hypotheses[0].get("text") or "")
        if not target.strip():
            raise RuntimeError(f"OPUS returned empty rank-0 target for planned unit {sequence}")
        output[sequence] = {
            "target_text": target,
            "rank0_score": hypotheses[0].get("score"),
            "production_table_composite": False,
        }
    return output, max_decoding_length, table_request_count


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")).resolve()
    source_path = Path(os.environ["ROCKETDICT_OPTICKS_SOURCE"]).resolve()
    if _sha_file(source_path) != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source hash drift")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    core = RocketDictCore()
    project = WorkbenchProject.create(root / "project", name="full-opticks-numeric-stress", core=core)
    imported = project.import_source(source_path)
    preflight = build_product_preflight(project, source_kind="text")
    if preflight.get("status") != "ready":
        raise RuntimeError(f"Numeric stress Product preflight is not ready: {preflight}")
    database = project.paths.database
    document_version_id = int(imported["interpretation"]["document_version_id"])

    impl8, params8 = _profile_stage(preflight, 8)
    stage8 = _call(
        core,
        database,
        "product.stage8.run",
        document_version_id=document_version_id,
        parameters=params8,
        implementation=impl8,
    )
    impl10, params10 = _profile_stage(preflight, 10)
    stage10 = _call(
        core,
        database,
        "product.stage10.run",
        nlp_run_id=int(stage8["nlp_run_id"]),
        parameters=params10,
        implementation=impl10,
    )
    impl12, params12 = _profile_stage(preflight, 12)
    if impl12 != "opus-en-ru-ct2":
        raise RuntimeError(f"Numeric stress requires pinned OPUS Product MT, got {impl12!r}")
    preferred_tokens = int(params12.get("plan_preferred_unit_tokens") or 64)
    punctuation_parameters, length_parameters = _quality_parameters(preflight)

    stage12 = _call(
        core,
        database,
        "product.stage12.run",
        context_run_id=int(stage10["context_run_id"]),
        parameters=params12,
        implementation=impl12,
    )
    if stage12.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Full Opticks Product Stage12 planner contract drift")
    if stage12.get("structural_label_contract") != STRUCTURAL_LABEL_CONTRACT:
        raise RuntimeError("Full Opticks Product Stage12 structural-label contract drift")
    if int(stage12.get("structural_label_unit_count") or -1) != 108:
        raise RuntimeError(
            "Pinned Opticks Product Stage12 must isolate exactly 108 supported block structural labels"
        )
    if int(stage12.get("structural_label_escalated_unit_count") or -1) != 3:
        raise RuntimeError(
            "Pinned Opticks Product Stage12 expected exactly three Observation-1 beam12 escalations"
        )

    translation_run_id = int(stage12["translation_run_id"])
    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        translation_items = get_run_items(
            connection, translation_run_id, kind="translation_segment"
        )
    content = str(document["content_text"])
    if not translation_items:
        raise RuntimeError("Full Opticks Product Stage12 persisted no translation segments")

    units: list[dict[str, Any]] = []
    cursor = 0
    for expected_sequence, item in enumerate(translation_items):
        sequence = int(item["sequence_number"])
        start = int(item["source_start"])
        end = int(item["source_end"])
        source_text = str(item["source_text"])
        target_text = str(item.get("target_text") or "")
        payload = dict(item.get("payload") or {})
        if sequence != expected_sequence:
            raise RuntimeError("Full Opticks Product Stage12 sequence numbering drift")
        if start != cursor or end <= start or content[start:end] != source_text:
            raise RuntimeError("Full Opticks Product Stage12 source coverage is not byte-exact")
        if not target_text.strip():
            raise RuntimeError(f"Full Opticks Product Stage12 emitted empty target at {sequence}")
        units.append(
            {
                "start": start,
                "end": end,
                "text": source_text,
                "target_text": target_text,
                "payload": payload,
                "metadata": dict(payload.get("planner") or {}),
            }
        )
        cursor = end
    if cursor != len(content) or "".join(str(unit["text"]) for unit in units) != content:
        raise RuntimeError("Full Opticks Product Stage12 does not cover the immutable source exactly")
    if len(units) != int(stage12.get("segment_count") or -1):
        raise RuntimeError("Full Opticks Product Stage12 output segment count drift")

    numeric_units = [
        (index, unit)
        for index, unit in enumerate(units)
        if extract_numeric_literals(str(unit["text"]))
    ]
    if not numeric_units:
        raise RuntimeError("Full Opticks Product Stage12 produced no numeric-bearing units")

    max_unit_tokens = max(
        int((unit.get("metadata") or {}).get("token_count") or 0)
        for _, unit in numeric_units
    )
    max_decoding_length = max(128, max(preferred_tokens, max_unit_tokens) * 8)
    database_sha_after_product_stage12 = _sha_file(database)
    baseline_rows: list[dict[str, Any]] = []
    numeric_failures: list[dict[str, Any]] = []
    for sequence, unit in numeric_units:
        target = str(unit["target_text"])
        product_payload = dict(unit.get("payload") or {})
        source_row = _row(unit, sequence)
        verdict = _verdict(
            source_row,
            target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        record = {
            "planned_sequence": sequence,
            "source_start": int(unit["start"]),
            "source_end": int(unit["end"]),
            "source_text": str(unit["text"]),
            "planner": dict(unit.get("metadata") or {}),
            "product_target_text": target,
            "product_selected_rank": int(product_payload.get("selected_rank") or 0),
            "production_table_composite": isinstance(product_payload.get("table"), dict),
            "production_structural_label": isinstance(product_payload.get("structural_label"), dict),
            "table_stage12_contract": (
                (product_payload.get("table") or {}).get("stage12_contract")
                if isinstance(product_payload.get("table"), dict)
                else None
            ),
            "table_logical_group_count": (
                len((product_payload.get("table") or {}).get("logical_groups") or [])
                if isinstance(product_payload.get("table"), dict)
                else None
            ),
            "structural_label_contract": (
                (product_payload.get("structural_label") or {}).get("contract")
                if isinstance(product_payload.get("structural_label"), dict)
                else None
            ),
            "rank0_verdict": verdict,
            "source_numeric_literal_count": len(extract_numeric_literals(str(unit["text"]))),
        }
        baseline_rows.append(record)
        if (verdict.get("numeric_symbol") or {}).get("passed") is False:
            numeric_failures.append(record)

    ordinary_failures = [
        row
        for row in numeric_failures
        if not bool(row["production_table_composite"])
        and not bool(row["production_structural_label"])
    ]
    translator = OpusTranslator(device="cpu", compute_type="float32")
    retry_generated = _translate_batches(
        translator,
        [str(row["source_text"]) for row in ordinary_failures],
        beam_size=NBEST_GENERATION["beam_size"],
        num_hypotheses=NBEST_GENERATION["num_hypotheses"],
        max_decoding_length=max_decoding_length,
    ) if ordinary_failures else []
    retries_by_sequence = {
        int(row["planned_sequence"]): hypotheses
        for row, hypotheses in zip(ordinary_failures, retry_generated, strict=True)
    }

    retry_results: list[dict[str, Any]] = []
    for failed in numeric_failures:
        if failed["production_table_composite"] or failed["production_structural_label"]:
            retry_results.append(
                {
                    **failed,
                    "numeric_failure_is_isolated": False,
                    "retry_applicable": False,
                    "retry_skip_reason": (
                        "composite_table_must_not_be_retranslated_as_prose"
                        if failed["production_table_composite"]
                        else "structural_label_uses_narrow_product_selector_not_generic_nbest"
                    ),
                    "retry_generation": None,
                    "selected_strict_candidate": None,
                    "candidates": [],
                }
            )
            continue
        hypotheses = retries_by_sequence[int(failed["planned_sequence"])]
        source_row = {
            "sequence_number": int(failed["planned_sequence"]),
            "source_start": int(failed["source_start"]),
            "source_end": int(failed["source_end"]),
            "source_text": str(failed["source_text"]),
            "target_text": None,
        }
        candidates: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        for hypothesis in hypotheses:
            target = str(hypothesis.get("text") or "")
            verdict = _verdict(
                source_row,
                target,
                punctuation_parameters=punctuation_parameters,
                length_parameters=length_parameters,
            )
            candidate = {
                "rank": int(hypothesis.get("rank") or 0),
                "score": hypothesis.get("score"),
                "target_text": target,
                "similarity_to_product_target": _similarity(str(failed["product_target_text"]), target),
                "verdict": verdict,
            }
            candidates.append(candidate)
            if selected is None and verdict.get("strictly_eligible") is True:
                selected = candidate
        isolated = bool(
            not list((failed["rank0_verdict"] or {}).get("punctuation_issues") or [])
            and not list((failed["rank0_verdict"] or {}).get("length_issues") or [])
            and ((failed["rank0_verdict"] or {}).get("delimiter_preservation") or {}).get("passed") is True
            and ((failed["rank0_verdict"] or {}).get("critical_technical_tokens") or {}).get("passed") is True
            and ((failed["rank0_verdict"] or {}).get("output_artifacts") or {}).get("passed") is True
        )
        retry_results.append(
            {
                **failed,
                "numeric_failure_is_isolated": isolated,
                "retry_applicable": True,
                "retry_generation": dict(NBEST_GENERATION),
                "selected_strict_candidate": selected,
                "candidates": candidates,
            }
        )

    database_sha_after_research_inference = _sha_file(database)
    if database_sha_after_research_inference != database_sha_after_product_stage12:
        raise RuntimeError("Numeric stress research inference mutated the persisted Product Stage12 database")

    isolated_failures = [row for row in retry_results if row["numeric_failure_is_isolated"]]
    isolated_rescued = [
        row for row in isolated_failures if row["selected_strict_candidate"] is not None
    ]
    all_rescued = [row for row in retry_results if row["selected_strict_candidate"] is not None]
    selected_ranks = Counter(
        int(row["selected_strict_candidate"]["rank"])
        for row in all_rescued
        if row["selected_strict_candidate"] is not None
    )
    table_numeric_units = [
        row for row in baseline_rows if row["production_table_composite"]
    ]
    table_numeric_failures = [
        row for row in numeric_failures if row["production_table_composite"]
    ]
    structural_label_numeric_units = [
        row for row in baseline_rows if row["production_structural_label"]
    ]
    structural_label_numeric_failures = [
        row for row in numeric_failures if row["production_structural_label"]
    ]
    if len(structural_label_numeric_units) != 108:
        raise RuntimeError("Full Opticks numeric audit did not observe all 108 Product structural-label units")
    if structural_label_numeric_failures:
        raise RuntimeError("Product structural-label selector emitted a numeric-integrity failure")
    asset = translator.asset
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full contiguous Opticks numeric-integrity audit over actual persisted Product Stage12 output plus ordinary-unit research n-best retry",
        "actual_product_stage12_execution": True,
        "promotion_allowed": False,
        "no_synthetic_target_repair": True,
        "source_sha256": OPTICKS_SHA256,
        "source_char_count": len(content),
        "source_text_sha256": str(document["text_sha256"]),
        "document_version_id": document_version_id,
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or ""),
        "stage8": {
            "implementation": impl8,
            "nlp_run_id": int(stage8["nlp_run_id"]),
            "token_count": int(stage8.get("token_count") or 0),
        },
        "stage10": {
            "implementation": impl10,
            "context_run_id": int(stage10["context_run_id"]),
            "sentence_count": int(stage10.get("sentence_count") or 0),
        },
        "stage12_planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
        "table_stage12_contract": TABLE_STAGE12_CONTRACT,
        "stage12_parameters": params12,
        "stage12": {
            "translation_run_id": translation_run_id,
            "segment_count": int(stage12.get("segment_count") or 0),
            "source_character_sum": int(stage12.get("source_character_sum") or 0),
            "structural_label_unit_count": int(stage12.get("structural_label_unit_count") or 0),
            "structural_label_escalated_unit_count": int(stage12.get("structural_label_escalated_unit_count") or 0),
            "structural_label_model_request_count": int(stage12.get("structural_label_model_request_count") or 0),
            "table_block_count": int(stage12.get("table_block_count") or 0),
            "table_logical_group_count": int(stage12.get("table_logical_group_count") or 0),
            "model_request_count": int(stage12.get("model_request_count") or 0),
            "real_mt": stage12.get("real_mt") is True,
        },
        "planned_unit_count": len(units),
        "max_planned_unit_tokens": max_unit_tokens,
        "numeric_bearing_unit_count": len(numeric_units),
        "table_numeric_bearing_unit_count": len(table_numeric_units),
        "table_numeric_model_request_count": sum(
            int(row.get("table_logical_group_count") or 0) for row in table_numeric_units
        ),
        "structural_label_numeric_bearing_unit_count": len(structural_label_numeric_units),
        "structural_label_numeric_failure_count": len(structural_label_numeric_failures),
        "product_numeric_failure_count": len(numeric_failures),
        "product_numeric_failure_sequences": [int(row["planned_sequence"]) for row in numeric_failures],
        "table_rank0_numeric_failure_count": len(table_numeric_failures),
        "table_rank0_numeric_failure_sequences": [
            int(row["planned_sequence"]) for row in table_numeric_failures
        ],
        "isolated_numeric_failure_count": len(isolated_failures),
        "isolated_numeric_failure_sequences": [int(row["planned_sequence"]) for row in isolated_failures],
        "strict_nbest_rescue_count": len(all_rescued),
        "strict_nbest_rescue_sequences": [int(row["planned_sequence"]) for row in all_rescued],
        "isolated_strict_nbest_rescue_count": len(isolated_rescued),
        "isolated_strict_nbest_rescue_sequences": [int(row["planned_sequence"]) for row in isolated_rescued],
        "selected_rank_distribution": {str(key): value for key, value in sorted(selected_ranks.items())},
        "retry_generation": dict(NBEST_GENERATION),
        "retry_scope": "ordinary_units_only; Product composite tables and structural labels are never retranslated by generic n-best",
        "model": {
            "revision": asset.revision,
            "source_archive_sha256": asset.source_archive_sha256,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "compute_type": "float32",
            "device": "cpu",
        },
        "database_sha256_after_product_stage12": database_sha_after_product_stage12,
        "database_sha256_after_research_inference": database_sha_after_research_inference,
        "quality_gate_parameters": {
            "punctuation": punctuation_parameters,
            "length_ratio": length_parameters,
        },
        "numeric_failures": retry_results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "full-opticks-numeric-stress.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "planned_unit_count": len(units),
                "numeric_bearing_unit_count": len(numeric_units),
                "table_numeric_bearing_unit_count": len(table_numeric_units),
                "product_numeric_failure_count": len(numeric_failures),
                "structural_label_numeric_bearing_unit_count": len(structural_label_numeric_units),
                "structural_label_numeric_failure_count": len(structural_label_numeric_failures),
                "table_rank0_numeric_failure_count": len(table_numeric_failures),
                "isolated_numeric_failure_count": len(isolated_failures),
                "strict_nbest_rescue_count": len(all_rescued),
                "isolated_strict_nbest_rescue_count": len(isolated_rescued),
                "selected_rank_distribution": payload["selected_rank_distribution"],
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
