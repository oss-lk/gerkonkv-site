from __future__ import annotations

"""Research-only source-owned structural-island feasibility probe on R1.

Unlike the rejected placeholder/numeric-islands branch, this mechanism never
asks OPUS to reproduce a placeholder and never appends a missing value after a
translation.  It deterministically parses a narrow set of source-owned
non-prose structures, translates only the surrounding prose, and carries those
exact source spans through in source order.  The experiment is read-only and is
not Product policy or promotion evidence by itself.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_run, get_run_items
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair
from rocketdict.research_diagnostics import (
    compare_critical_technical_tokens,
    compare_delimiter_preservation,
    compare_numeric_order,
    compare_output_artifacts,
)
from rocketdict.runtime import OpusTranslator
from rocketdict.stages import _length_issues, _punctuation_issues

SCHEMA = "rocketdict-maintained-r1-structural-island-feasibility/1"
EXPECTED_SELECTION_SHA256 = "665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32"

_TECHNICAL_BRACKET_RE = re.compile(
    r"\[(?:Greek|Illustration):[^\]]*\]", flags=re.IGNORECASE
)
_FOOTNOTE_RE = re.compile(r"\[[A-Z]\]")
_STRUCTURAL_ID_RE = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:\.[A-Za-z]+)+\.\d+\.(?![A-Za-z0-9])"
)
_SYMBOLIC_EMPH_RE = re.compile(r"_([A-Za-z]{1,3})_")


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


def _parameters(raw: str | None) -> dict[str, Any]:
    value = json.loads(str(raw or "{}"))
    if not isinstance(value, dict):
        raise RuntimeError("Stage15 parameters_json is not an object")
    return value


def _islands(text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for kind, regex in (
        ("technical_bracket", _TECHNICAL_BRACKET_RE),
        ("footnote_marker", _FOOTNOTE_RE),
        ("structural_identifier", _STRUCTURAL_ID_RE),
        ("symbolic_emphasis", _SYMBOLIC_EMPH_RE),
    ):
        for match in regex.finditer(text):
            matches.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "kind": kind,
                    "text": match.group(0),
                }
            )
    matches.sort(key=lambda row: (int(row["start"]), -int(row["end"])))
    accepted: list[dict[str, Any]] = []
    for row in matches:
        if accepted and int(row["start"]) < int(accepted[-1]["end"]):
            # A broader technical bracket wins over any nested pattern.  Other
            # overlap would make the source parser ambiguous and must fail.
            if (
                int(row["start"]) >= int(accepted[-1]["start"])
                and int(row["end"]) <= int(accepted[-1]["end"])
            ):
                continue
            raise RuntimeError(f"Overlapping structural-island spans: {accepted[-1]!r} vs {row!r}")
        accepted.append(row)
    return accepted


def _split_plan(text: str) -> list[dict[str, Any]]:
    islands = _islands(text)
    parts: list[dict[str, Any]] = []
    cursor = 0
    for island in islands:
        start, end = int(island["start"]), int(island["end"])
        if start > cursor:
            parts.append({"kind": "prose", "start": cursor, "end": start, "text": text[cursor:start]})
        parts.append(dict(island))
        cursor = end
    if cursor < len(text):
        parts.append({"kind": "prose", "start": cursor, "end": len(text), "text": text[cursor:]})
    if "".join(str(part["text"]) for part in parts) != text:
        raise RuntimeError("Structural-island plan is not byte-exact over source")
    return parts


def _prose_core(fragment: str) -> tuple[str, str, str]:
    if not fragment.strip():
        return fragment, "", ""
    left = len(fragment) - len(fragment.lstrip())
    right = len(fragment) - len(fragment.rstrip())
    leading = fragment[:left]
    trailing = fragment[len(fragment) - right :] if right else ""
    core_end = len(fragment) - right if right else len(fragment)
    return leading, fragment[left:core_end], trailing


def _candidate_row(source_row: dict[str, Any], target: str) -> dict[str, Any]:
    return {
        "sequence_number": int(source_row["sequence_number"]),
        "source_start": source_row.get("source_start"),
        "source_end": source_row.get("source_end"),
        "source_text": str(source_row.get("source_text") or ""),
        "target_text": target,
    }


def _verdict(
    source_row: dict[str, Any],
    target: str,
    *,
    punctuation_parameters: dict[str, Any],
    length_parameters: dict[str, Any],
) -> dict[str, Any]:
    source = str(source_row.get("source_text") or "")
    probe = _candidate_row(source_row, target)
    numeric = evaluate_numeric_symbol_pair(source, target)
    punctuation = _punctuation_issues([probe], punctuation_parameters)
    length = _length_issues([probe], length_parameters)
    numeric_order = compare_numeric_order(source, target)
    delimiters = compare_delimiter_preservation(source, target)
    critical = compare_critical_technical_tokens(source, target)
    artifacts = compare_output_artifacts(source, target)
    product_hard = numeric["passed"] is True and not punctuation and not length and bool(target.strip())
    research = (
        numeric_order["passed"] is True
        and delimiters["passed"] is True
        and critical["passed"] is True
        and artifacts["passed"] is True
    )
    return {
        "product_hard_passed": product_hard,
        "strict_research_passed": research,
        "strictly_eligible": product_hard and research,
        "numeric_symbol": numeric,
        "punctuation_issues": punctuation,
        "length_issues": length,
        "numeric_order": numeric_order,
        "delimiter_preservation": delimiters,
        "critical_technical_tokens": critical,
        "output_artifacts": artifacts,
    }


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_TRANSLATION_CHALLENGE_ROOT", "work/translation-challenge")
    ).resolve()
    baseline_path = root / "maintained-r1-baseline.json"
    nbest_path = root / "maintained-r1-nbest-feasibility.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not nbest_path.is_file() or not database.is_file():
        raise RuntimeError("R1 baseline, strict n-best evidence, or Product database is missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    nbest = json.loads(nbest_path.read_text(encoding="utf-8"))
    selection_sha = str((baseline.get("selection") or {}).get("selection_sha256") or "")
    if selection_sha != EXPECTED_SELECTION_SHA256 or nbest.get("selection_sha256") != selection_sha:
        raise RuntimeError("Frozen R1 selection identity drifted across structural-island probe inputs")
    unrescued = {int(value) for value in nbest.get("unrescued_sequences") or []}
    if not unrescued:
        raise RuntimeError("Structural-island probe has no strict n-best failures to investigate")

    assembly_id = int((baseline.get("stage14") or {})["assembly_id"])
    translation_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        rows = get_run_items(connection, assembly_id, kind="assembly_segment")
        translation_run = get_run(connection, translation_run_id)
        gate_rows = connection.execute(
            "SELECT implementation, parameters_json FROM stage_runs "
            "WHERE stage_number=15 AND status='completed' ORDER BY id"
        ).fetchall()
    by_sequence = {int(row["sequence_number"]): row for row in rows}
    missing = sorted(unrescued - set(by_sequence))
    if missing:
        raise RuntimeError(f"Strict n-best evidence references missing assembly sequences: {missing}")

    gate_parameters = {
        str(row["implementation"]): _parameters(row["parameters_json"])
        for row in gate_rows
    }
    punctuation_parameters = dict(gate_parameters.get("rocketdict-punctuation-preservation") or {})
    length_parameters = dict(gate_parameters.get("rocketdict-length-ratio-proxy") or {})
    if not length_parameters:
        raise RuntimeError("R1 database lacks recorded length-ratio parameters")

    scoped: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    no_island_sequences: list[int] = []
    prose_jobs: list[str] = []
    job_locations: list[tuple[int, int]] = []
    plans: dict[int, list[dict[str, Any]]] = {}
    for sequence in sorted(unrescued):
        row = by_sequence[sequence]
        source = str(row.get("source_text") or "")
        plan = _split_plan(source)
        if not any(part["kind"] != "prose" for part in plan):
            no_island_sequences.append(sequence)
            continue
        plans[sequence] = plan
        scoped.append((row, plan))
        for part_index, part in enumerate(plan):
            if part["kind"] != "prose":
                continue
            leading, core, trailing = _prose_core(str(part["text"]))
            part["leading_whitespace"] = leading
            part["core"] = core
            part["trailing_whitespace"] = trailing
            if core:
                job_locations.append((sequence, part_index))
                prose_jobs.append(core)

    if not scoped:
        raise RuntimeError("No strict n-best failure contains a recognized source-owned structural island")

    translation_output = dict(translation_run.get("output") or {})
    max_unit_tokens = int(translation_output.get("max_translation_unit_tokens") or 64)
    max_decoding_length = max(128, max_unit_tokens * 8)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    translated = translator.translate(
        prose_jobs,
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=max_decoding_length,
    ) if prose_jobs else []
    if len(translated) != len(job_locations):
        raise RuntimeError("Structural-island prose translation cardinality mismatch")
    for (sequence, part_index), hypotheses in zip(job_locations, translated, strict=True):
        if not hypotheses:
            raise RuntimeError(f"OPUS returned no prose hypothesis for sequence {sequence}")
        plans[sequence][part_index]["translated_core"] = str(hypotheses[0].get("text") or "")
        plans[sequence][part_index]["model_rank"] = int(hypotheses[0].get("rank") or 0)
        plans[sequence][part_index]["model_score"] = hypotheses[0].get("score")

    results: list[dict[str, Any]] = []
    for row, plan in scoped:
        target_parts: list[str] = []
        public_plan: list[dict[str, Any]] = []
        for part in plan:
            if part["kind"] == "prose":
                if "core" not in part:
                    leading, core, trailing = _prose_core(str(part["text"]))
                    part["leading_whitespace"] = leading
                    part["core"] = core
                    part["trailing_whitespace"] = trailing
                core = str(part.get("core") or "")
                translated_core = str(part.get("translated_core") or "") if core else ""
                target_piece = (
                    str(part.get("leading_whitespace") or "")
                    + translated_core
                    + str(part.get("trailing_whitespace") or "")
                ) if core else str(part["text"])
                target_parts.append(target_piece)
                public_plan.append(
                    {
                        "kind": "prose",
                        "source_text": part["text"],
                        "translated_core": translated_core,
                        "model_rank": part.get("model_rank"),
                        "model_score": part.get("model_score"),
                    }
                )
            else:
                target_parts.append(str(part["text"]))
                public_plan.append(
                    {
                        "kind": part["kind"],
                        "source_text": part["text"],
                        "passthrough_exact": True,
                    }
                )
        candidate = "".join(target_parts)
        verdict = _verdict(
            row,
            candidate,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        results.append(
            {
                "segment_sequence": int(row["sequence_number"]),
                "source_text": str(row.get("source_text") or ""),
                "baseline_target_text": str(row.get("target_text") or ""),
                "islands": [
                    {"kind": part["kind"], "text": part["text"]}
                    for part in plan
                    if part["kind"] != "prose"
                ],
                "plan": public_plan,
                "candidate_target_text": candidate,
                "verdict": verdict,
                "rescued": verdict["strictly_eligible"] is True,
            }
        )

    rescued = [int(row["segment_sequence"]) for row in results if row["rescued"] is True]
    failed = [int(row["segment_sequence"]) for row in results if row["rescued"] is not True]
    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("Structural-island feasibility probe mutated frozen R1 database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "mechanism feasibility only; source-owned islands are parsed before MT and never synthesized after MT",
        "promotion_allowed": False,
        "no_placeholder_roundtrip": True,
        "no_post_translation_literal_injection": True,
        "selection_sha256": selection_sha,
        "nbest_evidence_sha256": str(nbest.get("evidence_sha256") or ""),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "recognized_island_kinds": [
            "technical_bracket",
            "footnote_marker",
            "structural_identifier",
            "symbolic_emphasis",
        ],
        "generation": {
            "beam_size": 6,
            "num_hypotheses": 1,
            "compute_type": "float32",
            "device": "cpu",
            "max_decoding_length": max_decoding_length,
        },
        "strict_nbest_unrescued_sequences": sorted(unrescued),
        "scoped_sequences": [int(row[0]["sequence_number"]) for row in scoped],
        "no_recognized_island_sequences": no_island_sequences,
        "rescued_count": len(rescued),
        "rescued_sequences": rescued,
        "failed_count": len(failed),
        "failed_sequences": failed,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output = root / "maintained-r1-structural-island-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "scoped_sequences": payload["scoped_sequences"],
                "no_recognized_island_sequences": no_island_sequences,
                "rescued_sequences": rescued,
                "failed_sequences": failed,
                "evidence_sha256": payload["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
