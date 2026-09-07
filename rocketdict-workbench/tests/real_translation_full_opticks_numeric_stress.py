from __future__ import annotations

"""Full contiguous Opticks numeric-integrity stress for current Stage12 planning.

This research harness deliberately stops before the full Product translation
pipeline.  It runs the real maintained Stage8/10 interpretation on the complete
pinned Opticks source, asks the current Stage12 planner to materialize its
byte-exact translation units, and then translates *every planned unit containing
an explicit numeric literal* with the pinned OPUS float32 model.

Rank-0 is the current Product baseline.  Beam-6 n-best is requested only for
units where rank-0 actually fails numeric/symbol integrity.  Nothing is repaired
or inserted after MT, the research project DB is not mutated by translation
inference, and every candidate is evaluated against the maintained hard/strict
semantics.  The result is evidence for or against a narrow numeric retry policy,
not automatic Product promotion.
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
from rocketdict.translation_stage import PLANNER_CONTRACT, segment_translation_units
from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_preflight import build_product_preflight
from rocketdict_workbench.project import WorkbenchProject

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-numeric-stress/1"
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
            timeout=1800,
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

    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        document_segments = get_document_segments(connection, document_version_id)
        nlp_tokens = get_run_items(connection, int(stage8["nlp_run_id"]), kind="nlp_token")
        context_rows = get_run_items(connection, int(stage10["context_run_id"]), kind="context_sentence")
    content = str(document["content_text"])
    units = segment_translation_units(
        content,
        document_segments,
        context_rows,
        nlp_tokens,
        selected_format=str(document["selected_format"]),
        preferred_tokens=preferred_tokens,
    )
    if "".join(str(unit["text"]) for unit in units) != content:
        raise RuntimeError("Current Stage12 planner did not cover full Opticks byte-exactly")

    numeric_units = [
        (index, unit)
        for index, unit in enumerate(units)
        if extract_numeric_literals(str(unit["text"]))
    ]
    if not numeric_units:
        raise RuntimeError("Full Opticks planner produced no numeric-bearing translation units")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    max_unit_tokens = max(int((unit.get("metadata") or {}).get("token_count") or 0) for _, unit in numeric_units)
    max_decoding_length = max(128, max(preferred_tokens, max_unit_tokens) * 8)
    database_sha_before_inference = _sha_file(database)
    baseline_generated = _translate_batches(
        translator,
        [str(unit["text"]) for _, unit in numeric_units],
        beam_size=int(params12.get("beam_size") or 6),
        num_hypotheses=1,
        max_decoding_length=max_decoding_length,
    )

    baseline_rows: list[dict[str, Any]] = []
    numeric_failures: list[dict[str, Any]] = []
    for (sequence, unit), hypotheses in zip(numeric_units, baseline_generated, strict=True):
        if not hypotheses:
            raise RuntimeError(f"OPUS returned no rank-0 hypothesis for planned unit {sequence}")
        target = str(hypotheses[0].get("text") or "")
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
            "rank0_target_text": target,
            "rank0_score": hypotheses[0].get("score"),
            "rank0_verdict": verdict,
            "source_numeric_literal_count": len(extract_numeric_literals(str(unit["text"]))),
        }
        baseline_rows.append(record)
        if (verdict.get("numeric_symbol") or {}).get("passed") is False:
            numeric_failures.append(record)

    retry_generated = _translate_batches(
        translator,
        [str(row["source_text"]) for row in numeric_failures],
        beam_size=NBEST_GENERATION["beam_size"],
        num_hypotheses=NBEST_GENERATION["num_hypotheses"],
        max_decoding_length=max_decoding_length,
    ) if numeric_failures else []

    retry_results: list[dict[str, Any]] = []
    for failed, hypotheses in zip(numeric_failures, retry_generated, strict=True):
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
                "similarity_to_rank0": _similarity(str(failed["rank0_target_text"]), target),
                "verdict": verdict,
            }
            candidates.append(candidate)
            if selected is None and verdict.get("strictly_eligible") is True:
                selected = candidate
        retry_results.append(
            {
                **failed,
                "numeric_failure_is_isolated": bool(
                    not list((failed["rank0_verdict"] or {}).get("punctuation_issues") or [])
                    and not list((failed["rank0_verdict"] or {}).get("length_issues") or [])
                    and ((failed["rank0_verdict"] or {}).get("delimiter_preservation") or {}).get("passed") is True
                    and ((failed["rank0_verdict"] or {}).get("critical_technical_tokens") or {}).get("passed") is True
                    and ((failed["rank0_verdict"] or {}).get("output_artifacts") or {}).get("passed") is True
                ),
                "retry_generation": dict(NBEST_GENERATION),
                "selected_strict_candidate": selected,
                "candidates": candidates,
            }
        )

    database_sha_after_inference = _sha_file(database)
    if database_sha_after_inference != database_sha_before_inference:
        raise RuntimeError("Numeric stress inference mutated the Stage8/10 research database")

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
    asset = translator.asset
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full contiguous Opticks numeric-integrity stress for current Stage12 planner and raw n-best retry",
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
        "stage12_parameters": params12,
        "planned_unit_count": len(units),
        "max_planned_unit_tokens": max_unit_tokens,
        "numeric_bearing_unit_count": len(numeric_units),
        "rank0_numeric_failure_count": len(numeric_failures),
        "rank0_numeric_failure_sequences": [int(row["planned_sequence"]) for row in numeric_failures],
        "isolated_numeric_failure_count": len(isolated_failures),
        "isolated_numeric_failure_sequences": [int(row["planned_sequence"]) for row in isolated_failures],
        "strict_nbest_rescue_count": len(all_rescued),
        "strict_nbest_rescue_sequences": [int(row["planned_sequence"]) for row in all_rescued],
        "isolated_strict_nbest_rescue_count": len(isolated_rescued),
        "isolated_strict_nbest_rescue_sequences": [int(row["planned_sequence"]) for row in isolated_rescued],
        "selected_rank_distribution": {str(key): value for key, value in sorted(selected_ranks.items())},
        "retry_generation": dict(NBEST_GENERATION),
        "model": {
            "revision": asset.revision,
            "source_archive_sha256": asset.source_archive_sha256,
            "manifest_sha256": asset.manifest_sha256,
            "payload_tree_sha256": asset.payload_tree_sha256,
            "compute_type": "float32",
            "device": "cpu",
        },
        "database_sha256_before_inference": database_sha_before_inference,
        "database_sha256_after_inference": database_sha_after_inference,
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
                "rank0_numeric_failure_count": len(numeric_failures),
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
