from __future__ import annotations

"""Research-only full-Opticks differential for major-punctuation soft cuts.

This probe rebuilds the planner-v8 plan from the immutable successful Opticks
artifact while changing only the ordinary safe split choice: at an over-budget
cut it may backtrack a configured number of lexical tokens to source-owned
``; : . ! ?`` punctuation outside protected spans.  The source text is never
rewritten.  Only contexts whose ordinary Stage12 boundaries actually change are
translated again with the same real OPUS rank0 generation and compared against
the persisted Product output using the unchanged complete strict verdict.

The result answers the promotion question that the earlier numeric shadow could
not: whether the candidate causes any hard/strict regressions outside numeric
units.  It is feasibility evidence, not Product policy.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import (
    connect,
    get_document,
    get_document_segments,
    get_run_items,
)
from rocketdict.runtime import OpusTranslator
import rocketdict.translation_stage as translation_stage
from rocketdict.translation_stage import PLANNER_CONTRACT

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-major-punctuation-differential/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
RAW_SOURCE_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
EXPECTED_BASELINE_ARTIFACT_DIGEST = (
    "sha256:7c77092dc86516983a7917931e9b000e6c2774595562e8854623a9faff4979b4"
)
MAJOR = frozenset({";", ":", ".", "!", "?"})
BATCH_SIZE = 48
FOCUS_START = 132834
FOCUS_END = 133465


def _sha(path: Path) -> str:
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


def _token_text(token: dict[str, Any]) -> str:
    value = token.get("source_text")
    return str(value if value is not None else token.get("text") or "")


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hard = sum(1 for row in rows if row["verdict"].get("product_hard_passed") is not True)
    strict = sum(1 for row in rows if row["verdict"].get("strictly_eligible") is not True)
    numeric = sum(
        1
        for row in rows
        if (row["verdict"].get("numeric_symbol") or {}).get("passed") is not True
    )
    return {
        "unit_count": len(rows),
        "hard_failure_count": hard,
        "strict_failure_count": strict,
        "numeric_failure_count": numeric,
        "all_hard_passed": hard == 0,
        "all_strictly_eligible": strict == 0,
    }


def _translate(
    translator: OpusTranslator,
    texts: list[str],
    *,
    max_decoding_length: int,
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        generated = translator.translate(
            batch,
            beam_size=6,
            num_hypotheses=1,
            max_decoding_length=max_decoding_length,
        )
        if len(generated) != len(batch):
            raise RuntimeError("major-punctuation OPUS batch cardinality mismatch")
        output.extend(generated)
    if len(output) != len(texts):
        raise RuntimeError("major-punctuation OPUS total cardinality mismatch")
    return output


def main() -> int:
    lookback = int(os.environ.get("ROCKETDICT_MAJOR_LOOKBACK_TOKENS", "8"))
    if lookback < 1 or lookback > 32:
        raise RuntimeError("major-punctuation lookback must be in 1..32")

    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/full-opticks-artifact/full-opticks-numeric-stress",
        )
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks baseline is incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError("unexpected full-Opticks baseline schema")
    if baseline.get("source_sha256") != RAW_SOURCE_SHA256:
        raise RuntimeError("pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("major-punctuation baseline planner is not current")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline artifact identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_DIGEST") != EXPECTED_BASELINE_ARTIFACT_DIGEST:
        raise RuntimeError("baseline artifact digest drift")

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
    if hashlib.sha256(content.encode("utf-8")).hexdigest() != str(baseline.get("source_text_sha256") or ""):
        raise RuntimeError("normalized Opticks source identity drift")

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
        lower = max(0, desired_index - lookback)
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
        shadow_units = translation_stage.segment_translation_units(
            content,
            segments,
            context_items,
            nlp_tokens,
            selected_format="txt",
            preferred_tokens=preferred_tokens,
        )
    finally:
        translation_stage._safe_forward_split_index = original_split

    if "".join(str(unit["text"]) for unit in shadow_units) != content:
        raise RuntimeError("major-punctuation shadow is not byte-exact")

    baseline_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in persisted:
        planner = dict((row.get("payload") or {}).get("planner") or {})
        start_sequence = planner.get("context_sentence_start")
        end_sequence = planner.get("context_sentence_end")
        if start_sequence is None or end_sequence is None or int(start_sequence) != int(end_sequence):
            continue
        if planner.get("source") != "nlp_sentence":
            continue
        baseline_by_context[int(start_sequence)].append(dict(row))

    shadow_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for unit in shadow_units:
        planner = dict(unit.get("metadata") or {})
        start_sequence = planner.get("context_sentence_start")
        end_sequence = planner.get("context_sentence_end")
        if start_sequence is None or end_sequence is None or int(start_sequence) != int(end_sequence):
            continue
        if planner.get("source") != "nlp_sentence":
            continue
        shadow_by_context[int(start_sequence)].append(unit)

    changed_contexts: list[int] = []
    for sequence in sorted(set(baseline_by_context) & set(shadow_by_context)):
        baseline_rows = sorted(baseline_by_context[sequence], key=lambda row: int(row["source_start"]))
        candidate_rows = sorted(shadow_by_context[sequence], key=lambda row: int(row["start"]))
        baseline_spans = [(int(row["source_start"]), int(row["source_end"])) for row in baseline_rows]
        candidate_spans = [(int(row["start"]), int(row["end"])) for row in candidate_rows]
        if baseline_spans != candidate_spans:
            if "".join(str(row["source_text"]) for row in baseline_rows) != "".join(str(row["text"]) for row in candidate_rows):
                raise RuntimeError("changed context source bytes drift")
            changed_contexts.append(sequence)
    if not changed_contexts:
        raise RuntimeError("major-punctuation shadow changed no ordinary contexts")
    if 669 not in changed_contexts:
        raise RuntimeError("known long-content-loss context 669 is absent")

    jobs: list[tuple[int, int, dict[str, Any]]] = []
    max_tokens = preferred_tokens
    for sequence in changed_contexts:
        rows = sorted(shadow_by_context[sequence], key=lambda row: int(row["start"]))
        for index, unit in enumerate(rows):
            planner = dict(unit.get("metadata") or {})
            max_tokens = max(max_tokens, int(planner.get("token_count") or 1))
            jobs.append((sequence, index, unit))

    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = _translate(
        translator,
        [str(unit["text"]) for _sequence, _index, unit in jobs],
        max_decoding_length=max(128, max_tokens * 8),
    )
    generated_by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})
    for (sequence, index, unit), hypotheses in zip(jobs, generated, strict=True):
        if not hypotheses:
            raise RuntimeError("OPUS returned no major-punctuation hypothesis")
        target = str(hypotheses[0].get("text") or "").strip()
        if not target:
            raise RuntimeError("OPUS returned empty major-punctuation target")
        source_row = {
            "sequence_number": index,
            "source_start": int(unit["start"]),
            "source_end": int(unit["end"]),
            "source_text": str(unit["text"]),
            "target_text": None,
        }
        generated_by_context[sequence].append(
            {
                "source_start": int(unit["start"]),
                "source_end": int(unit["end"]),
                "source_text": str(unit["text"]),
                "target_text": target,
                "verdict": _verdict(
                    source_row,
                    target,
                    punctuation_parameters=punctuation_parameters,
                    length_parameters=length_parameters,
                ),
            }
        )

    hard_rescues: list[int] = []
    hard_regressions: list[int] = []
    strict_rescues: list[int] = []
    strict_regressions: list[int] = []
    numeric_rescues: list[int] = []
    numeric_regressions: list[int] = []
    results: list[dict[str, Any]] = []
    focus: dict[str, Any] | None = None

    for sequence in changed_contexts:
        baseline_rows: list[dict[str, Any]] = []
        for row in sorted(baseline_by_context[sequence], key=lambda value: int(value["source_start"])):
            target = str(row.get("target_text") or "")
            source_row = {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": str(row["source_text"]),
                "target_text": None,
            }
            baseline_rows.append(
                {
                    "source_start": int(row["source_start"]),
                    "source_end": int(row["source_end"]),
                    "source_text": str(row["source_text"]),
                    "target_text": target,
                    "verdict": _verdict(
                        source_row,
                        target,
                        punctuation_parameters=punctuation_parameters,
                        length_parameters=length_parameters,
                    ),
                }
            )
        candidate_rows = sorted(generated_by_context[sequence], key=lambda value: int(value["source_start"]))
        before = _counts(baseline_rows)
        after = _counts(candidate_rows)
        if not before["all_hard_passed"] and after["all_hard_passed"]:
            hard_rescues.append(sequence)
        if before["all_hard_passed"] and not after["all_hard_passed"]:
            hard_regressions.append(sequence)
        if not before["all_strictly_eligible"] and after["all_strictly_eligible"]:
            strict_rescues.append(sequence)
        if before["all_strictly_eligible"] and not after["all_strictly_eligible"]:
            strict_regressions.append(sequence)
        if int(before["numeric_failure_count"]) > 0 and int(after["numeric_failure_count"]) == 0:
            numeric_rescues.append(sequence)
        if int(before["numeric_failure_count"]) == 0 and int(after["numeric_failure_count"]) > 0:
            numeric_regressions.append(sequence)
        record = {
            "context_sequence": sequence,
            "baseline": before,
            "candidate": after,
            "baseline_units": baseline_rows,
            "candidate_units": candidate_rows,
        }
        results.append(record)
        source_start = min(int(row["source_start"]) for row in baseline_rows)
        source_end = max(int(row["source_end"]) for row in baseline_rows)
        if source_start <= FOCUS_START and source_end >= FOCUS_END:
            focus = record

    if focus is None:
        raise RuntimeError("long-content-loss focus context was not captured")
    db_sha_after = _sha(database)
    if db_sha_after != db_sha_before:
        raise RuntimeError("major-punctuation differential mutated retained database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full strict/hard differential for source-derived major-punctuation backtracking",
        "promotion_allowed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "source_sha256": RAW_SOURCE_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_artifact_digest": EXPECTED_BASELINE_ARTIFACT_DIGEST,
        "baseline_json_sha256": _sha(baseline_path),
        "candidate_policy": {
            "lookback_tokens": lookback,
            "major_punctuation": sorted(MAJOR),
            "fallback": "maintained_planner_v8_split_choice",
        },
        "changed_split_choice_count": len(choices),
        "changed_context_count": len(changed_contexts),
        "changed_context_sequences": changed_contexts,
        "hard_rescue_count": len(hard_rescues),
        "hard_rescue_context_sequences": hard_rescues,
        "hard_regression_count": len(hard_regressions),
        "hard_regression_context_sequences": hard_regressions,
        "strict_rescue_count": len(strict_rescues),
        "strict_rescue_context_sequences": strict_rescues,
        "strict_regression_count": len(strict_regressions),
        "strict_regression_context_sequences": strict_regressions,
        "numeric_rescue_count": len(numeric_rescues),
        "numeric_rescue_context_sequences": numeric_rescues,
        "numeric_regression_count": len(numeric_regressions),
        "numeric_regression_context_sequences": numeric_regressions,
        "focus_result": focus,
        "database_sha256_before": db_sha_before,
        "database_sha256_after": db_sha_after,
        "results": results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(
        os.environ.get("ROCKETDICT_MAJOR_DIFFERENTIAL_ROOT", "work/major-punctuation-differential")
    ).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-major-punctuation-differential.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "candidate_policy",
                    "changed_context_count",
                    "hard_rescue_count",
                    "hard_rescue_context_sequences",
                    "hard_regression_count",
                    "hard_regression_context_sequences",
                    "strict_rescue_count",
                    "strict_rescue_context_sequences",
                    "strict_regression_count",
                    "strict_regression_context_sequences",
                    "numeric_rescue_count",
                    "numeric_rescue_context_sequences",
                    "numeric_regression_count",
                    "numeric_regression_context_sequences",
                    "evidence_sha256",
                )
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
