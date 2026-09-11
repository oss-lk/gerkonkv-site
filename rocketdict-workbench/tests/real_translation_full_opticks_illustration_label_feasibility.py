from __future__ import annotations

"""Research-only full-Opticks illustration-label structural split feasibility.

Version 2 keeps the immutable source split from v1 but closes a semantic hole
found during review. Direct OPUS translation of the exact Gutenberg suffix
``_Illustration._`` produced malformed raw output ``*Иллюстрация._`` even
though the maintained hard gates were green. For that one source-defined
structural word, v2 records a separate canonical model input ``Illustration.``
and accepts only an unmodified raw OPUS target with the exact Russian
``Иллюстрация`` lexical form and no markup artifacts. Ordinary linguistic
suffixes still use their exact immutable source as model input.

The standalone ``[Illustration: ...]`` line plus following blank-line separator
remains source-owned and byte-exact. This is read-only research evidence; no
Product planner/default is changed here.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-illustration-label-feasibility/2"
SOURCE_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
BASE_DATABASE_SHA256 = "a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2"
BASE_RUN_ID = 8
BASE_OUTPUT_SHA256 = "d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346"
EXPECTED_SOURCE_STARTS = [72401, 90105, 203786]
EXPECTED_NORMALIZED_SOURCE_STARTS = [72401, 90105]
EXPECTED_CORPUS_LABEL_COUNT = 57
ILLUSTRATION_WORD_SOURCE = "_Illustration._"
ILLUSTRATION_WORD_MODEL_INPUT = "Illustration."
ILLUSTRATION_WORD_TARGET = "иллюстрация"
_LABEL_LINE_RE = re.compile(r"(?m)^\[Illustration:[^\]\r\n]+\](?=\r?$)")
_PREFIX_RE = re.compile(
    r"\A(?P<label>\[Illustration:[^\]\r\n]+\])(?P<gap>\r?\n[ \t]*\r?\n)"
)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row["sequence_number"]))


def _gate_flags(row: dict[str, Any]) -> dict[str, bool]:
    verdict = evaluate_rescue_pair(
        str(row.get("source_text") or ""), str(row.get("target_text") or "")
    )
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
        sequence = int(row["sequence_number"])
        flags = _gate_flags(row)
        if flags["numeric_symbol"]:
            numeric.append(sequence)
        if flags["punctuation"]:
            punctuation.append(sequence)
        if flags["length"]:
            length.append(sequence)
    unique = set(numeric) | set(punctuation) | set(length)
    return {
        "numeric_symbol": numeric,
        "punctuation": punctuation,
        "length": length,
        "counts": {
            "numeric_symbol": len(numeric),
            "punctuation": len(punctuation),
            "length": len(length),
            "unique": len(unique),
        },
    }


def _split_prefix(source: str) -> tuple[str, str] | None:
    match = _PREFIX_RE.match(source)
    if match is None:
        return None
    structural = match.group("label") + match.group("gap")
    remainder = source[match.end() :]
    if not remainder.strip():
        return None
    return structural, remainder


def _model_input_for_remainder(remainder: str) -> tuple[str, bool, str]:
    if remainder.strip() == ILLUSTRATION_WORD_SOURCE:
        return ILLUSTRATION_WORD_MODEL_INPUT, True, "standalone_illustration_word"
    return remainder, False, "ordinary_linguistic_suffix"


def _illustration_word_target_shape(target: str) -> dict[str, Any]:
    stripped = target.strip()
    no_markup_artifacts = not any(char in stripped for char in "_*[]{}")
    canonical = stripped.rstrip(".").strip().casefold()
    exact_lexical_form = canonical == ILLUSTRATION_WORD_TARGET
    return {
        "contract": "rocketdict-illustration-word-target-form/1",
        "target_text": target,
        "canonical_target": canonical,
        "expected_target": ILLUSTRATION_WORD_TARGET,
        "no_markup_artifacts": no_markup_artifacts,
        "exact_lexical_form": exact_lexical_form,
        "passed": no_markup_artifacts and exact_lexical_form,
    }


def _candidate_rows(
    row: dict[str, Any], *, structural: str, remainder: str, target: str
) -> list[dict[str, Any]]:
    start = int(row["source_start"])
    boundary = start + len(structural)
    end = int(row["source_end"])
    if boundary >= end or end - boundary != len(remainder):
        raise RuntimeError("illustration split source bounds drift")
    return [
        {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": start,
            "source_end": boundary,
            "source_text": structural,
            "target_text": structural,
            "payload": {"research_source_owned_illustration_label": True},
        },
        {
            "sequence_number": 0,
            "kind": "translation_segment",
            "source_start": boundary,
            "source_end": end,
            "source_text": remainder,
            "target_text": target,
            "payload": {"research_raw_rank0_remainder": True},
        },
    ]


def _counterfactual(
    base_rows: list[dict[str, Any]], replacements: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in _ordered(base_rows):
        replacement = replacements.get(int(row["source_start"]))
        if replacement is None:
            result.append(dict(row))
        else:
            result.extend(dict(item) for item in replacement)
    result.sort(key=lambda row: int(row["source_start"]))
    for sequence, row in enumerate(result):
        row["sequence_number"] = sequence
    return result


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_ILLUSTRATION_FEASIBILITY_ROOT",
            "work/illustration-feasibility",
        )
    ).resolve()
    database = root / "rocketdict.sqlite"
    if not database.is_file():
        raise RuntimeError("illustration feasibility requires persisted run-8 database")
    if _sha_file(database) != BASE_DATABASE_SHA256:
        raise RuntimeError("illustration feasibility database identity drift")

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        output = dict(run.get("output") or {})
        document_version_id = int(output["document_version_id"])
        document = get_document(connection, document_version_id)
    if str(run.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("illustration feasibility Stage12 output identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("illustration feasibility normalized source identity drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in _ordered(rows)) != content:
        raise RuntimeError("run-8 source coverage is not byte-exact")

    corpus_labels = [match.group(0) for match in _LABEL_LINE_RE.finditer(content)]
    if len(corpus_labels) != EXPECTED_CORPUS_LABEL_COUNT:
        raise RuntimeError(
            f"standalone illustration-label corpus count drift: {len(corpus_labels)}"
        )

    base_inventory = _inventory(rows)
    if base_inventory["counts"] != {
        "numeric_symbol": 25,
        "punctuation": 33,
        "length": 0,
        "unique": 55,
    }:
        raise RuntimeError(f"run-8 hard-gate inventory drift: {base_inventory['counts']}")

    attempts: list[dict[str, Any]] = []
    for row in _ordered(rows):
        split = _split_prefix(str(row.get("source_text") or ""))
        if split is None:
            continue
        flags = _gate_flags(row)
        if not any(flags.values()):
            continue
        structural, remainder = split
        model_input, normalized, candidate_kind = _model_input_for_remainder(remainder)
        attempts.append(
            {
                "row": row,
                "structural": structural,
                "remainder": remainder,
                "model_input": model_input,
                "source_model_input_normalized": normalized,
                "candidate_kind": candidate_kind,
                "base_gate_failures": [name for name, failed in flags.items() if failed],
            }
        )
    starts = [int(item["row"]["source_start"]) for item in attempts]
    if starts != EXPECTED_SOURCE_STARTS:
        raise RuntimeError(f"illustration hard-failure cohort drift: {starts}")
    normalized_starts = [
        int(item["row"]["source_start"])
        for item in attempts
        if item["source_model_input_normalized"]
    ]
    if normalized_starts != EXPECTED_NORMALIZED_SOURCE_STARTS:
        raise RuntimeError(f"illustration normalized-input cohort drift: {normalized_starts}")

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = translator.translate(
        [str(item["model_input"]) for item in attempts],
        beam_size=6,
        num_hypotheses=1,
        max_decoding_length=128,
    )
    if len(generated) != len(attempts):
        raise RuntimeError("illustration feasibility backend cardinality drift")

    replacements: dict[int, list[dict[str, Any]]] = {}
    evidence_rows: list[dict[str, Any]] = []
    accepted_starts: list[int] = []
    for attempt, hypotheses in zip(attempts, generated, strict=True):
        if not hypotheses:
            raise RuntimeError("illustration feasibility empty hypothesis set")
        rank0 = str(hypotheses[0].get("text") or "")
        if not rank0.strip():
            raise RuntimeError("illustration feasibility empty rank0 target")
        base = attempt["row"]
        candidate = _candidate_rows(
            base,
            structural=str(attempt["structural"]),
            remainder=str(attempt["remainder"]),
            target=rank0,
        )
        structural_verdict = evaluate_rescue_pair(
            candidate[0]["source_text"], candidate[0]["target_text"]
        )
        remainder_verdict = evaluate_rescue_pair(
            candidate[1]["source_text"], candidate[1]["target_text"]
        )
        target_shape = (
            _illustration_word_target_shape(rank0)
            if bool(attempt["source_model_input_normalized"])
            else {
                "contract": "rocketdict-illustration-word-target-form/1",
                "applicable": False,
                "passed": True,
            }
        )
        accepted = (
            structural_verdict.get("strictly_eligible") is True
            and remainder_verdict.get("strictly_eligible") is True
            and target_shape.get("passed") is True
        )
        start = int(base["source_start"])
        if accepted:
            replacements[start] = candidate
            accepted_starts.append(start)
        evidence_rows.append(
            {
                "source_start": start,
                "source_end": int(base["source_end"]),
                "base_source": str(base.get("source_text") or ""),
                "base_target": str(base.get("target_text") or ""),
                "base_gate_failures": list(attempt["base_gate_failures"]),
                "structural_source": str(attempt["structural"]),
                "remainder_source": str(attempt["remainder"]),
                "model_input": str(attempt["model_input"]),
                "source_model_input_normalized": bool(
                    attempt["source_model_input_normalized"]
                ),
                "candidate_kind": str(attempt["candidate_kind"]),
                "remainder_rank0_target": rank0,
                "remainder_rank0_score": hypotheses[0].get("score"),
                "structural_verdict": structural_verdict,
                "remainder_verdict": remainder_verdict,
                "illustration_word_target_shape": target_shape,
                "accepted": accepted,
                "raw_model_rank0": True,
                "source_bytes_rewritten": False,
                "target_rewriting": False,
            }
        )

    candidate_rows = _counterfactual(rows, replacements)
    if "".join(str(row.get("source_text") or "") for row in candidate_rows) != content:
        raise RuntimeError("illustration counterfactual source coverage is not byte-exact")
    counterfactual = _inventory(candidate_rows)
    database_sha_after = _sha_file(database)
    if database_sha_after != BASE_DATABASE_SHA256:
        raise RuntimeError("illustration feasibility mutated read-only database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only source-owned standalone illustration-label split with "
            "source-derived model-input normalization for exact _Illustration._ suffix"
        ),
        "v1_negative_evidence": {
            "direct_immutable_suffix_model_input": ILLUSTRATION_WORD_SOURCE,
            "observed_raw_rank0_target": "*Иллюстрация._",
            "mechanical_hard_gates_missed_markup_corruption": True,
            "promotion_rejected": True,
        },
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": SOURCE_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "base_database_sha256": BASE_DATABASE_SHA256,
        "base_translation_run_id": BASE_RUN_ID,
        "base_translation_output_sha256": BASE_OUTPUT_SHA256,
        "standalone_illustration_label_count": len(corpus_labels),
        "attempted_source_starts": starts,
        "normalized_model_input_source_starts": normalized_starts,
        "accepted_source_starts": accepted_starts,
        "attempt_count": len(attempts),
        "accepted_count": len(accepted_starts),
        "base_hard_gate_counts": base_inventory["counts"],
        "counterfactual_hard_gate_counts": counterfactual["counts"],
        "base_segment_count": len(rows),
        "counterfactual_segment_count": len(candidate_rows),
        "cases": evidence_rows,
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    out = root / "full-opticks-illustration-label-feasibility.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
