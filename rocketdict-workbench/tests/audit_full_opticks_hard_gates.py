from __future__ import annotations

"""Read-only full-Opticks inventory for all maintained Product hard gates.

The historical full-Opticks numeric-stress harness deliberately evaluates only
units whose *source* contains ``extract_numeric_literals``. Product Stage15 is
broader: ``rocketdict-maintained-numeric-integrity/5`` evaluates every selected
translation row because symbol-only corruption and unlicensed target numbers
are hard failures too.

This audit therefore keeps two independently checkable surfaces:

* the literal-bearing subset must reproduce the baseline stress JSON exactly;
* the complete numeric/symbol gate is recomputed across every persisted Stage12
  row, alongside punctuation and length-ratio gates.

The distinction is evidence, not evaluator weakening. No database writes,
target repair, threshold changes or automatic Product promotion occur here.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.numeric_integrity import CONTRACT as NUMERIC_CONTRACT
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair, extract_numeric_literals
from rocketdict.stages import _length_issues, _punctuation_issues
from rocketdict.structural_labels import STRUCTURAL_LABEL_CONTRACT
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-hard-gate-inventory/3"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"


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


def _context_sequence(row: dict[str, Any]) -> int | None:
    planner = dict((row.get("payload") or {}).get("planner") or {})
    start = planner.get("context_sentence_start")
    end = planner.get("context_sentence_end")
    if start is None or end is None or int(start) != int(end):
        return None
    if planner.get("source") != "nlp_sentence":
        return None
    return int(start)


def _numeric_issue(row: dict[str, Any]) -> dict[str, Any] | None:
    source = str(row.get("source_text") or "")
    target = str(row.get("target_text") or "")
    verdict = evaluate_numeric_symbol_pair(source, target)
    if verdict.get("passed") is True:
        return None
    source_numeric_literals = extract_numeric_literals(source)
    return {
        "type": "numeric_symbol_mismatch",
        "segment_sequence": int(row["sequence_number"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": source,
        "target_text": target,
        "source_has_numeric_literal": bool(source_numeric_literals),
        "source_numeric_literal_count": len(source_numeric_literals),
        "numeric_contract": NUMERIC_CONTRACT,
        "verdict": verdict,
    }


def _single_gate_issue(
    row: dict[str, Any],
    *,
    gate: str,
    parameters: dict[str, Any],
) -> dict[str, Any] | None:
    probe = {
        "sequence_number": int(row["sequence_number"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row.get("source_text") or ""),
        "target_text": str(row.get("target_text") or ""),
    }
    if gate == "punctuation":
        issues = _punctuation_issues([probe], parameters)
    elif gate == "length":
        issues = _length_issues([probe], parameters)
    else:  # pragma: no cover - internal programming guard
        raise ValueError(gate)
    if not issues:
        return None
    if len(issues) != 1:
        raise RuntimeError(f"{gate} gate returned unexpected issue cardinality")
    return dict(issues[0])


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("Full Opticks Product baseline evidence is missing")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"Unexpected baseline schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Hard-gate inventory requires current planner baseline")
    if baseline.get("structural_label_contract") != STRUCTURAL_LABEL_CONTRACT:
        raise RuntimeError("Hard-gate inventory requires current structural-label contract")

    reported_literal_failure_count = int(
        baseline.get("product_numeric_failure_count")
        if baseline.get("product_numeric_failure_count") is not None
        else -1
    )
    reported_literal_failure_sequences = sorted(
        int(value) for value in baseline.get("product_numeric_failure_sequences", [])
    )
    if reported_literal_failure_count < 0:
        raise RuntimeError("Full Opticks baseline lacks its numeric-stress failure count")
    if len(reported_literal_failure_sequences) != reported_literal_failure_count:
        raise RuntimeError("Full Opticks baseline numeric-stress failure sequence count drift")

    selected_run_id = int((baseline.get("stage12") or {})["translation_run_id"])
    document_version_id = int(baseline["document_version_id"])
    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})
    if not length_parameters:
        raise RuntimeError("Full Opticks baseline lacks length-ratio parameters")

    database_sha_before = _sha_file(database)
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        rows = get_run_items(connection, selected_run_id, kind="translation_segment")
        document = get_document(connection, document_version_id)
    selected_output = dict(selected_run.get("output") or {})
    if selected_output.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Persisted selected Stage12 planner contract drift")
    if selected_output.get("structural_label_contract") != STRUCTURAL_LABEL_CONTRACT:
        raise RuntimeError("Persisted selected Stage12 structural-label contract drift")

    content = str(document["content_text"])
    ordered = sorted(rows, key=lambda row: int(row["sequence_number"]))
    if "".join(str(row.get("source_text") or "") for row in ordered) != content:
        raise RuntimeError("Selected Stage12 rows do not byte-exactly cover immutable Opticks")

    by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in ordered:
        sequence = _context_sequence(row)
        if sequence is not None:
            by_context[sequence].append(row)
    split_contexts = {
        sequence: context_rows
        for sequence, context_rows in by_context.items()
        if len(context_rows) >= 2
    }
    split_segment_sequences = {
        int(row["sequence_number"])
        for context_rows in split_contexts.values()
        for row in context_rows
    }

    numeric: list[dict[str, Any]] = []
    punctuation: list[dict[str, Any]] = []
    length: list[dict[str, Any]] = []
    for row in ordered:
        numeric_issue = _numeric_issue(row)
        if numeric_issue is not None:
            numeric.append(numeric_issue)
        punctuation_issue = _single_gate_issue(
            row,
            gate="punctuation",
            parameters=punctuation_parameters,
        )
        if punctuation_issue is not None:
            punctuation.append(punctuation_issue)
        length_issue = _single_gate_issue(
            row,
            gate="length",
            parameters=length_parameters,
        )
        if length_issue is not None:
            length.append(length_issue)

    literal_numeric = [
        issue for issue in numeric if issue["source_has_numeric_literal"] is True
    ]
    nonliteral_numeric = [
        issue for issue in numeric if issue["source_has_numeric_literal"] is not True
    ]
    literal_sequences = sorted(int(issue["segment_sequence"]) for issue in literal_numeric)
    if len(literal_numeric) != reported_literal_failure_count:
        raise RuntimeError(
            "Recomputed literal-bearing numeric/symbol subset disagrees with numeric-stress baseline: "
            f"{len(literal_numeric)} != {reported_literal_failure_count}"
        )
    if literal_sequences != reported_literal_failure_sequences:
        raise RuntimeError(
            "Recomputed literal-bearing numeric/symbol failure identities disagree with "
            "numeric-stress baseline"
        )

    def split_count(issues: list[dict[str, Any]]) -> int:
        return sum(
            int(issue["segment_sequence"]) in split_segment_sequences
            for issue in issues
        )

    hard_union = {
        int(issue["segment_sequence"])
        for issues in (numeric, punctuation, length)
        for issue in issues
    }
    split_hard_union = sorted(hard_union & split_segment_sequences)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only complete inventory of current Product Stage12 hard-gate failures on full Opticks",
        "promotion_allowed": False,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(document["text_sha256"]),
        "document_version_id": document_version_id,
        "selected_translation_run_id": selected_run_id,
        "selected_translation_output_sha256": str(selected_run.get("output_sha256") or ""),
        "planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
        "structural_label_family_counts": dict(
            baseline.get("structural_label_family_counts") or {}
        ),
        "numeric_contract": NUMERIC_CONTRACT,
        "numeric_stress_baseline_scope": "source rows containing extract_numeric_literals(source)",
        "baseline_reported_literal_bearing_numeric_failure_count": reported_literal_failure_count,
        "baseline_reported_literal_bearing_numeric_failure_sequences": reported_literal_failure_sequences,
        "segment_count": len(ordered),
        "split_context_count": len(split_contexts),
        "split_segment_count": len(split_segment_sequences),
        "numeric_failure_count": len(numeric),
        "literal_bearing_numeric_failure_count": len(literal_numeric),
        "nonliteral_source_numeric_failure_count": len(nonliteral_numeric),
        "nonliteral_source_numeric_failure_sequences": [
            int(issue["segment_sequence"]) for issue in nonliteral_numeric
        ],
        "punctuation_failure_count": len(punctuation),
        "length_failure_count": len(length),
        "hard_failure_segment_union_count": len(hard_union),
        "split_numeric_failure_count": split_count(numeric),
        "split_literal_bearing_numeric_failure_count": split_count(literal_numeric),
        "split_nonliteral_source_numeric_failure_count": split_count(nonliteral_numeric),
        "split_punctuation_failure_count": split_count(punctuation),
        "split_length_failure_count": split_count(length),
        "split_hard_failure_segment_union_count": len(split_hard_union),
        "split_hard_failure_segment_sequences": split_hard_union,
        "quality_gate_parameters": {
            "punctuation": punctuation_parameters,
            "length_ratio": length_parameters,
        },
        "numeric_failures": numeric,
        "literal_bearing_numeric_failures": literal_numeric,
        "nonliteral_source_numeric_failures": nonliteral_numeric,
        "punctuation_failures": punctuation,
        "length_failures": length,
        "database_unchanged": True,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)

    if _sha_file(database) != database_sha_before:
        raise RuntimeError("Hard-gate inventory mutated the persisted Product database")

    output = root / "full-opticks-hard-gate-inventory.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "segment_count": len(ordered),
                "split_context_count": len(split_contexts),
                "numeric_failure_count": len(numeric),
                "literal_bearing_numeric_failure_count": len(literal_numeric),
                "nonliteral_source_numeric_failure_count": len(nonliteral_numeric),
                "nonliteral_source_numeric_failure_sequences": [
                    int(issue["segment_sequence"]) for issue in nonliteral_numeric
                ],
                "punctuation_failure_count": len(punctuation),
                "length_failure_count": len(length),
                "hard_failure_segment_union_count": len(hard_union),
                "split_numeric_failure_count": split_count(numeric),
                "split_punctuation_failure_count": split_count(punctuation),
                "split_length_failure_count": split_count(length),
                "split_hard_failure_segment_union_count": len(split_hard_union),
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
