from __future__ import annotations

"""Read-only rank0 geometry DOE for failures re-exposed by clean lineage.

This experiment is deliberately non-promoting.  It starts from the exact
rank0-clean run41 database and tests only source-owned segmentation geometries
that were not used to obtain the historical rank>0 rescues:

* exact illustration label/suffix splits with raw rank0 OPUS and TC-big;
* exact short angular-DMS phrase splits with raw rank0 OPUS and TC-big.

No source text is normalized before MT, no target literal is inserted, no
higher beam is generated for selection, and the database is never mutated.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-clean-returned-family-geometry-doe/1"
BASE_DATABASE_SHA256 = "e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e"
BASE_RUN_ID = 41
BASE_OUTPUT_SHA256 = "d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_BASE_COUNTS = {"numeric_symbol": 18, "punctuation": 16, "length": 0, "unique": 33}
EXPECTED_ILLUSTRATION_STARTS = [72401, 90105]
EXPECTED_DMS_STARTS = [110881]

_ILLUSTRATION_RE = re.compile(
    r"\A(?P<label>\[Illustration:\s*FIG\.\s*\d+\.\])"
    r"(?P<gap>\r?\n[ \t]*\r?\n)"
    r"(?P<suffix>_Illustration\._)"
    r"(?P<trailing>[ \t]*)\Z",
    flags=re.IGNORECASE,
)
_DMS_RE = re.compile(
    r"\A(?P<lead>.*?\bAngle\s+is\s+)"
    r"(?P<degrees>\d+\s+deg\.\s+)"
    r"(?P<prime>\d+'\.\s+\d+''\.\s*)\Z",
    flags=re.IGNORECASE,
)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _gate_flags(source: str, target: str) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(source, target)
    return {
        "numeric_symbol": (verdict.get("numeric_symbol") or {}).get("passed") is not True,
        "punctuation": verdict.get("punctuation_passed") is not True,
        "length": verdict.get("length_passed") is not True,
    }


def _inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric: list[int] = []
    punctuation: list[int] = []
    length: list[int] = []
    for row in _ordered(rows):
        seq = int(row["sequence_number"])
        flags = _gate_flags(
            str(row.get("source_text") or ""),
            str(row.get("target_text") or ""),
        )
        if flags["numeric_symbol"]:
            numeric.append(seq)
        if flags["punctuation"]:
            punctuation.append(seq)
        if flags["length"]:
            length.append(seq)
    return {
        "numeric_symbol": numeric,
        "punctuation": punctuation,
        "length": length,
        "counts": {
            "numeric_symbol": len(numeric),
            "punctuation": len(punctuation),
            "length": len(length),
            "unique": len(set(numeric) | set(punctuation) | set(length)),
        },
    }


def _rank0_batch(translator: Any, texts: list[str]) -> list[dict[str, Any]]:
    if not texts:
        return []
    generated = translator.translate(
        texts,
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=256,
    )
    if len(generated) != len(texts):
        raise RuntimeError("rank0 DOE translation batch cardinality drift")
    result: list[dict[str, Any]] = []
    for source, hypotheses in zip(texts, generated, strict=True):
        if len(hypotheses) != 1:
            raise RuntimeError("rank0 DOE hypothesis cardinality drift")
        hypothesis = hypotheses[0]
        rank = int(hypothesis.get("rank", -1))
        target = str(hypothesis.get("text") or "")
        if rank != 0 or not target.strip():
            raise RuntimeError(
                f"rank0 DOE malformed hypothesis: rank={rank}, source={source!r}"
            )
        result.append(
            {
                "rank": rank,
                "text": target,
                "score": hypothesis.get("score"),
            }
        )
    return result


def _boundary_passed(targets: list[str]) -> bool:
    """Reject raw split outputs that fuse alphanumeric tokens at a boundary."""
    for left, right in zip(targets, targets[1:]):
        left = left.rstrip("\r\n")
        right = right.lstrip("\r\n")
        if not left or not right:
            continue
        if left[-1].isalnum() and right[0].isalnum():
            return False
    return True


def _candidate_evidence(
    *,
    candidate_id: str,
    family: str,
    row: dict[str, Any],
    parts: list[dict[str, str]],
    translated: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    source = str(row.get("source_text") or "")
    if "".join(part["source_text"] for part in parts) != source:
        raise RuntimeError(f"{candidate_id}: candidate source coverage drift")

    target_parts: list[str] = []
    piece_evidence: list[dict[str, Any]] = []
    offset = int(row["source_start"])
    for index, part in enumerate(parts):
        source_part = part["source_text"]
        model = part["model"]
        raw = translated[(model, source_part)]
        target = str(raw["text"])
        verdict = evaluate_rescue_pair(source_part, target)
        emphasis = compare_emphasis_markup_preservation(source_part, target)
        piece_evidence.append(
            {
                "index": index,
                "model": model,
                "source_start": offset,
                "source_end": offset + len(source_part),
                "source_text": source_part,
                "raw_rank": int(raw["rank"]),
                "raw_score": raw.get("score"),
                "raw_target": target,
                "mechanical_verdict": verdict,
                "emphasis_markup": emphasis,
                "strictly_eligible": verdict.get("strictly_eligible") is True,
            }
        )
        offset += len(source_part)
        target_parts.append(target)

    joined_target = "".join(target_parts)
    aggregate = evaluate_rescue_pair(source, joined_target)
    emphasis = compare_emphasis_markup_preservation(source, joined_target)
    boundary_ok = _boundary_passed(target_parts)
    mechanical_passed = bool(
        all(piece["strictly_eligible"] for piece in piece_evidence)
        and aggregate.get("strictly_eligible") is True
        and emphasis.get("passed") is True
        and boundary_ok
    )
    return {
        "candidate_id": candidate_id,
        "family": family,
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": source,
        "base_target": str(row.get("target_text") or ""),
        "parts": piece_evidence,
        "joined_raw_target": joined_target,
        "aggregate_mechanical_verdict": aggregate,
        "aggregate_emphasis_markup": emphasis,
        "boundary_passed": boundary_ok,
        "mechanical_passed": mechanical_passed,
        "raw_rank0_only": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "automatic_n_best_cherry_picking": False,
    }


def _model_assignments(part_count: int) -> list[tuple[str, ...]]:
    if part_count == 1:
        return [("opus",), ("tc_big",)]
    if part_count != 2:
        raise ValueError(part_count)
    return [
        ("opus", "opus"),
        ("opus", "tc_big"),
        ("tc_big", "opus"),
        ("tc_big", "tc_big"),
    ]


def _candidate_specs(
    illustration_rows: list[dict[str, Any]], dms_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []

    for row in illustration_rows:
        source = str(row["source_text"])
        match = _ILLUSTRATION_RE.fullmatch(source)
        if match is None:
            raise RuntimeError("illustration DOE regex drift")
        geometries = {
            "whole": [source],
            "label_gap__suffix": [
                match.group("label") + match.group("gap"),
                match.group("suffix") + match.group("trailing"),
            ],
            "label__gap_suffix": [
                match.group("label"),
                match.group("gap") + match.group("suffix") + match.group("trailing"),
            ],
        }
        for geometry, parts in geometries.items():
            for assignment in _model_assignments(len(parts)):
                specs.append(
                    {
                        "family": "illustration_pair",
                        "row": row,
                        "candidate_id": (
                            f"illustration:{int(row['source_start'])}:{geometry}:"
                            + "+".join(assignment)
                        ),
                        "parts": [
                            {"source_text": part, "model": model}
                            for part, model in zip(parts, assignment, strict=True)
                        ],
                    }
                )

    for row in dms_rows:
        source = str(row["source_text"])
        match = _DMS_RE.fullmatch(source)
        if match is None:
            raise RuntimeError("short-DMS DOE regex drift")
        geometries = {
            "whole": [source],
            "lead__measurement": [
                match.group("lead"),
                match.group("degrees") + match.group("prime"),
            ],
            "lead_degrees__prime": [
                match.group("lead") + match.group("degrees"),
                match.group("prime"),
            ],
        }
        for geometry, parts in geometries.items():
            for assignment in _model_assignments(len(parts)):
                specs.append(
                    {
                        "family": "short_angular_dms",
                        "row": row,
                        "candidate_id": (
                            f"dms:{int(row['source_start'])}:{geometry}:"
                            + "+".join(assignment)
                        ),
                        "parts": [
                            {"source_text": part, "model": model}
                            for part, model in zip(parts, assignment, strict=True)
                        ],
                    }
                )
    return specs


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_CLEAN_RETURNED_GEOMETRY_DOE_ROOT",
            "work/clean-returned-family-geometry-doe",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file() or _sha_file(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("DOE requires exact authenticated rank0-clean run41 database")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run41 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("source identity drift")
    content = str(document["content_text"])
    ordered = _ordered(rows)
    if "".join(str(row.get("source_text") or "") for row in ordered) != content:
        raise RuntimeError("run41 source coverage is not byte-exact")

    base_inventory = _inventory(rows)
    if base_inventory["counts"] != EXPECTED_BASE_COUNTS:
        raise RuntimeError(f"run41 hard-gate inventory drift: {base_inventory['counts']!r}")

    illustration_rows: list[dict[str, Any]] = []
    dms_rows: list[dict[str, Any]] = []
    for row in ordered:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        flags = _gate_flags(source, target)
        if _ILLUSTRATION_RE.fullmatch(source) and flags["punctuation"]:
            illustration_rows.append(row)
        if _DMS_RE.fullmatch(source) and flags["numeric_symbol"]:
            dms_rows.append(row)

    illustration_starts = [int(row["source_start"]) for row in illustration_rows]
    dms_starts = [int(row["source_start"]) for row in dms_rows]
    if illustration_starts != EXPECTED_ILLUSTRATION_STARTS:
        raise RuntimeError(f"illustration clean-returned cohort drift: {illustration_starts!r}")
    if dms_starts != EXPECTED_DMS_STARTS:
        raise RuntimeError(f"short-DMS clean-returned cohort drift: {dms_starts!r}")

    specs = _candidate_specs(illustration_rows, dms_rows)
    requests: dict[str, list[str]] = {"opus": [], "tc_big": []}
    for spec in specs:
        for part in spec["parts"]:
            model = str(part["model"])
            source_part = str(part["source_text"])
            if source_part not in requests[model]:
                requests[model].append(source_part)

    opus = OpusTranslator(device="cpu", compute_type="float32")
    tc_big = TcBigTranslator(device="cpu", compute_type="float32")
    translated: dict[tuple[str, str], dict[str, Any]] = {}
    for model, translator in (("opus", opus), ("tc_big", tc_big)):
        hypotheses = _rank0_batch(translator, requests[model])
        for source_part, raw in zip(requests[model], hypotheses, strict=True):
            translated[(model, source_part)] = raw

    candidates = [
        _candidate_evidence(
            candidate_id=str(spec["candidate_id"]),
            family=str(spec["family"]),
            row=spec["row"],
            parts=spec["parts"],
            translated=translated,
        )
        for spec in specs
    ]
    mechanically_passed = [
        str(candidate["candidate_id"])
        for candidate in candidates
        if candidate["mechanical_passed"] is True
    ]

    if _sha_file(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("read-only DOE mutated the rank0-clean database")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "read-only exact-source raw-rank0 geometry DOE for illustration-pair "
            "and short-angular-DMS failures re-exposed by clean lineage"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_hard_gate_counts": base_inventory["counts"],
        "illustration_source_starts": illustration_starts,
        "short_dms_source_starts": dms_starts,
        "candidate_count": len(candidates),
        "mechanically_passed_candidate_ids": mechanically_passed,
        "candidates": candidates,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "raw_rank0_only": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "automatic_n_best_cherry_picking": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "full-opticks-clean-returned-family-geometry-doe.json"
    destination.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "base_counts": base_inventory["counts"],
                "illustration_source_starts": illustration_starts,
                "short_dms_source_starts": dms_starts,
                "candidate_count": len(candidates),
                "mechanically_passed_candidate_ids": mechanically_passed,
                "candidate_targets": [
                    {
                        "candidate_id": candidate["candidate_id"],
                        "mechanical_passed": candidate["mechanical_passed"],
                        "joined_raw_target": candidate["joined_raw_target"],
                    }
                    for candidate in candidates
                ],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
