from __future__ import annotations

"""Reusable persisted hard-failure census for any maintained Stage12 translation run.

The census is diagnostic only. It never mutates the database or source/target
text, never changes Product gate semantics, and deliberately records the full
maintained verdict alongside source-derived feature tags so later research can
cluster failures without corpus-position whitelists.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-translation-residual-census/1"
_ANGLE_WORD_RE = re.compile(r"\b(?:deg(?:ree)?s?|degree)\b", re.IGNORECASE)
_PRIME_NUMERIC_RE = re.compile(r"(?<!\d)\d+\s*'{1,3}")
_FRACTION_RE = re.compile(r"(?<!\d)\d+\s*/\s*\d+(?!\d)")
_FIGURE_RE = re.compile(r"\b(?:Fig|Figure)\.?\s*\d+", re.IGNORECASE)
_APOSTROPHE_DECIMAL_RE = re.compile(r"(?<!\d)\d+'\d+(?!')")
_BIG_INTEGER_RE = re.compile(r"(?<!\d)\d{6,}(?!\d)")
_ALNUM_LABEL_RE = re.compile(r"(?<![A-Za-z0-9])(?:\d+[A-Z]|[A-Z]\d+)(?![A-Za-z0-9])")
_FORMULA_SUFFIX_RE = re.compile(r"(?<![A-Za-z0-9])(?:\d+(?:/\d+)?|\(.*?\))[A-Z](?![A-Za-z0-9])")


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


def _planner(row: dict[str, Any]) -> dict[str, Any]:
    return dict((row.get("payload") or {}).get("planner") or {})


def _source_features(source: str) -> dict[str, Any]:
    labels = _ALNUM_LABEL_RE.findall(source)
    return {
        "contains_angle_word": bool(_ANGLE_WORD_RE.search(source)),
        "contains_numeric_prime_notation": bool(_PRIME_NUMERIC_RE.search(source)),
        "contains_fraction": bool(_FRACTION_RE.search(source)),
        "contains_figure_reference": bool(_FIGURE_RE.search(source)),
        "contains_apostrophe_decimal": bool(_APOSTROPHE_DECIMAL_RE.search(source)),
        "contains_big_integer": bool(_BIG_INTEGER_RE.search(source)),
        "contains_ascii_x": " x " in source,
        "contains_unicode_multiplication": "×" in source,
        "contains_square_bracket": "[" in source or "]" in source,
        "contains_round_parenthesis": "(" in source or ")" in source,
        "contains_formula_suffix": bool(_FORMULA_SUFFIX_RE.search(source)),
        "alphanumeric_technical_labels": labels,
        "alphanumeric_technical_label_count": len(labels),
        "source_char_count": len(source),
        "source_alpha_count": sum(ch.isalpha() for ch in source),
        "source_digit_count": sum(ch.isdigit() for ch in source),
    }


def _numeric_class(verdict: dict[str, Any]) -> str | None:
    numeric_symbol = dict(verdict.get("numeric_symbol") or {})
    if numeric_symbol.get("passed") is True:
        return None
    numeric = dict(numeric_symbol.get("numeric") or {})
    prime = dict(numeric.get("prime_notation") or {})
    missing = dict(numeric.get("missing") or {})
    additions = dict(numeric.get("unlicensed_additions") or {})
    duplicate = dict(numeric.get("duplicate_required") or {})
    symbol = dict(numeric_symbol.get("symbol_mismatch") or {})
    parts: list[str] = []
    if prime.get("passed") is not True:
        parts.append("prime_notation")
    if missing:
        parts.append("missing_literal")
    if additions:
        parts.append("unlicensed_addition")
    if duplicate:
        parts.append("duplicate_required")
    if symbol:
        parts.append("critical_symbol")
    return "+".join(parts) if parts else "numeric_other"


def _hard_classes(verdict: dict[str, Any]) -> list[str]:
    classes: list[str] = []
    if dict(verdict.get("numeric_symbol") or {}).get("passed") is not True:
        classes.append("numeric_symbol")
    if verdict.get("punctuation_passed") is not True:
        classes.append("punctuation")
    if verdict.get("length_passed") is not True:
        classes.append("length")
    return classes


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_RESIDUAL_CENSUS_ROOT", "work/residual-census")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Path(os.environ.get("ROCKETDICT_RESIDUAL_CENSUS_DB", root / "rocketdict.sqlite")).resolve()
    run_id = int(os.environ.get("ROCKETDICT_RESIDUAL_TRANSLATION_RUN_ID", "0"))
    expected_db_sha = os.environ.get("ROCKETDICT_RESIDUAL_EXPECTED_DB_SHA256", "").strip()
    if run_id <= 0:
        raise RuntimeError("ROCKETDICT_RESIDUAL_TRANSLATION_RUN_ID must be positive")
    if not database.is_file():
        raise RuntimeError(f"residual census database missing: {database}")
    database_sha_before = _sha(database)
    if expected_db_sha and database_sha_before != expected_db_sha:
        raise RuntimeError("residual census database SHA drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, run_id)
        rows = sorted(
            get_run_items(connection, run_id, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        output = dict(run.get("output") or {})
        document = get_document(connection, int(output["document_version_id"]))
    content = str(document["content_text"])
    cursor = 0
    for sequence, row in enumerate(rows):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError("translation sequence drift")
        start, end = int(row["source_start"]), int(row["source_end"])
        if start != cursor or end <= start or content[start:end] != str(row.get("source_text") or ""):
            raise RuntimeError(f"source coverage drift at translation sequence {sequence}")
        cursor = end
    if cursor != len(content):
        raise RuntimeError("translation run does not cover immutable source")

    records: list[dict[str, Any]] = []
    hard_counts: Counter[str] = Counter()
    numeric_classes: Counter[str] = Counter()
    planner_sources: Counter[str] = Counter()
    source_feature_counts: Counter[str] = Counter()
    for row in rows:
        source = str(row.get("source_text") or "")
        target = str(row.get("target_text") or "")
        verdict = evaluate_rescue_pair(source, target)
        hard = _hard_classes(verdict)
        if not hard:
            continue
        for name in hard:
            hard_counts[name] += 1
        numeric_class = _numeric_class(verdict)
        if numeric_class is not None:
            numeric_classes[numeric_class] += 1
        planner = _planner(row)
        planner_source = str(planner.get("source") or "unknown")
        planner_sources[planner_source] += 1
        features = _source_features(source)
        for key, value in features.items():
            if key.startswith("contains_") and value is True:
                source_feature_counts[key] += 1
        emphasis = compare_emphasis_markup_preservation(source, target)
        records.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "target_text": target,
                "hard_failure_classes": hard,
                "numeric_defect_class": numeric_class,
                "planner": planner,
                "source_features": features,
                "verdict": verdict,
                "emphasis_markup": emphasis,
            }
        )

    unique_count = len(records)
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "read-only reusable census of maintained Stage12 hard failures and source-defined feature clusters",
        "translation_run_id": run_id,
        "translation_output_sha256": str(run.get("output_sha256") or ""),
        "database_sha256": database_sha_before,
        "source_text_sha256": str(document["text_sha256"]),
        "source_char_count": len(content),
        "translation_segment_count": len(rows),
        "hard_gate_counts": {
            "numeric_symbol": int(hard_counts["numeric_symbol"]),
            "punctuation": int(hard_counts["punctuation"]),
            "length": int(hard_counts["length"]),
            "unique": unique_count,
        },
        "numeric_defect_class_counts": dict(sorted(numeric_classes.items())),
        "planner_source_counts": dict(sorted(planner_sources.items())),
        "source_feature_counts": dict(sorted(source_feature_counts.items())),
        "residual_sequences": [record["sequence_number"] for record in records],
        "records": records,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "evaluator_weakened": False,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
    }
    if _sha(database) != database_sha_before:
        raise RuntimeError("read-only residual census mutated database")
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    evidence_path = root / "translation-residual-census.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "translation_run_id": run_id,
        "hard_gate_counts": evidence["hard_gate_counts"],
        "numeric_defect_class_counts": evidence["numeric_defect_class_counts"],
        "residual_sequences": evidence["residual_sequences"],
        "evidence_sha256": evidence["evidence_sha256"],
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
