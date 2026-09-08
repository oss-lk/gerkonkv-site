from __future__ import annotations

"""Research-only full-Opticks clause-boundary Stage12 planner feasibility.

The maintained planner uses a 64-token soft budget and protects balanced source
spans, but ordinary long sentences otherwise cut at the first safe token
boundary at/after the budget.  The pinned planner-v8 acceptance contains a real
content-loss failure where this creates ``...gross be | rarer...`` and every
raw beam-6 hypothesis drops the preceding clause containing source literal 25.

This probe keeps all maintained source-structure partitions out of scope and
changes only ordinary Stage10 sentences that are currently represented solely
by ``nlp_sentence`` Stage12 units.  At each ordinary 64-token cut it looks at
most six tokens backward for a source-derived clause boundary:

* after ``;`` or ``:``; or
* after ``,`` when the next token is a conservative conjunction/subordinator.

If none exists, the maintained protected-span forward rule is used unchanged.
All candidate chunks preserve immutable source bytes exactly.  Every candidate
chunk is translated by the same real OPUS model with Product rank-0 generation
(beam 6, one hypothesis).  Existing Product output is re-scored read-only with
the same strict verdict so changed sentences can be classified as rescues or
regressions.  No target rewriting, placeholders, literal injection or database
mutation is permitted.  This is feasibility evidence, not Product policy.
"""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any

from rocketdict.runtime import OpusTranslator
from rocketdict.translation_stage import (
    PLANNER_CONTRACT,
    _balanced_protected_spans,
    _safe_forward_split_index,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-clause-boundary-feasibility/1"
BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"
EXPECTED_BASELINE_RUN_ID = "34244876537"
EXPECTED_BASELINE_ARTIFACT_ID = "10064356708"
EXPECTED_BASELINE_ARTIFACT_DIGEST = (
    "sha256:7c77092dc86516983a7917931e9b000e6c2774595562e8854623a9faff4979b4"
)
PREFERRED_TOKENS = 64
LOOKBACK_TOKENS = 6
BATCH_SIZE = 48
GENERATION = {"beam_size": 6, "num_hypotheses": 1}
CLAUSE_CONTINUATIONS = {
    "and",
    "or",
    "but",
    "yet",
    "so",
    "for",
    "because",
    "if",
    "when",
    "while",
    "whereas",
    "although",
    "though",
    "since",
}
FOCUS_SOURCE_SPANS = {
    "long_content_loss": [133139, 133431],
    "ring_measurement": [267212, 267543],
    "compact_formula": [401232, 401532],
    "extreme_integer_tail": [507544, 507698],
}


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


def _decode_payload(raw: str | None) -> dict[str, Any]:
    value = json.loads(str(raw or "{}"))
    if not isinstance(value, dict):
        raise RuntimeError("persisted payload_json is not an object")
    return value


def _non_space_token(row: sqlite3.Row) -> dict[str, Any] | None:
    payload = _decode_payload(row["payload_json"])
    if bool((payload.get("flags") or {}).get("is_space")):
        return None
    return {
        "sequence_number": int(row["sequence_number"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row["source_text"]),
        "payload": payload,
    }


def _is_clause_boundary(tokens: list[dict[str, Any]], cut_index: int) -> bool:
    if cut_index <= 0 or cut_index >= len(tokens):
        return False
    previous = str(tokens[cut_index - 1]["source_text"])
    following = str(tokens[cut_index]["source_text"]).lower()
    if previous in {";", ":"}:
        return True
    return previous == "," and following in CLAUSE_CONTINUATIONS


def _candidate_cut_indices(
    tokens: list[dict[str, Any]],
    *,
    source_text: str,
    source_start: int,
) -> list[int]:
    spans = _balanced_protected_spans(source_text, absolute_start=source_start)
    cuts: list[int] = []
    token_index = 0
    while token_index < len(tokens):
        desired_index = min(token_index + PREFERRED_TOKENS, len(tokens))
        if desired_index >= len(tokens):
            cuts.append(len(tokens))
            break
        chosen: int | None = None
        lower = max(token_index + 1, desired_index - LOOKBACK_TOKENS)
        for cut_index in range(desired_index, lower - 1, -1):
            if not _is_clause_boundary(tokens, cut_index):
                continue
            cut = int(tokens[cut_index]["source_start"])
            if any(start < cut < end for start, end, _kind in spans):
                continue
            chosen = cut_index
            break
        if chosen is None:
            chosen = _safe_forward_split_index(
                tokens,
                desired_index=desired_index,
                spans=spans,
            )
        if chosen <= token_index:
            raise RuntimeError("candidate clause planner failed to advance token coverage")
        cuts.append(chosen)
        token_index = chosen
    return cuts


def _chunks_from_cuts(
    tokens: list[dict[str, Any]],
    cuts: list[int],
    *,
    source_text: str,
    source_start: int,
    source_end: int,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    cursor_char = source_start
    cursor_token = 0
    for cut_index in cuts:
        if cut_index >= len(tokens):
            cut_char = source_end
            cut_index = len(tokens)
        else:
            cut_char = int(tokens[cut_index]["source_start"])
        if cut_char <= cursor_char or cut_index <= cursor_token:
            raise RuntimeError("candidate clause planner produced a non-positive chunk")
        text = source_text[cursor_char - source_start : cut_char - source_start]
        output.append(
            {
                "source_start": cursor_char,
                "source_end": cut_char,
                "source_text": text,
                "token_start": cursor_token,
                "token_end": cut_index,
                "token_count": cut_index - cursor_token,
            }
        )
        cursor_char = cut_char
        cursor_token = cut_index
    if cursor_char != source_end or cursor_token != len(tokens):
        raise RuntimeError("candidate clause planner failed complete token/source coverage")
    if "".join(row["source_text"] for row in output) != source_text:
        raise RuntimeError("candidate clause planner source coverage is not byte-exact")
    return output


def _source_row(sequence: int, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence_number": sequence,
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row["source_text"]),
        "target_text": None,
    }


def _translate_batches(
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
            beam_size=int(GENERATION["beam_size"]),
            num_hypotheses=int(GENERATION["num_hypotheses"]),
            max_decoding_length=max_decoding_length,
        )
        if len(generated) != len(batch):
            raise RuntimeError("candidate clause OPUS batch cardinality mismatch")
        output.extend(generated)
    if len(output) != len(texts):
        raise RuntimeError("candidate clause OPUS total cardinality mismatch")
    return output


def _sentence_verdict_counts(rows: list[dict[str, Any]]) -> dict[str, int | bool]:
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


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/full-opticks-artifact/full-opticks-numeric-stress",
        )
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not baseline_path.is_file() or not database.is_file():
        raise RuntimeError("planner-v8 full-Opticks evidence is incomplete")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != BASE_SCHEMA:
        raise RuntimeError(f"unexpected baseline schema: {baseline.get('schema')!r}")
    if baseline.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("pinned Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("clause feasibility baseline planner is not current")
    if os.environ.get("ROCKETDICT_BASELINE_RUN_ID") != EXPECTED_BASELINE_RUN_ID:
        raise RuntimeError("baseline run identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_ID") != EXPECTED_BASELINE_ARTIFACT_ID:
        raise RuntimeError("baseline artifact identity drift")
    if os.environ.get("ROCKETDICT_BASELINE_ARTIFACT_DIGEST") != EXPECTED_BASELINE_ARTIFACT_DIGEST:
        raise RuntimeError("baseline artifact digest drift")

    punctuation_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("punctuation") or {})
    length_parameters = dict((baseline.get("quality_gate_parameters") or {}).get("length_ratio") or {})
    database_sha_before = _sha_file(database)

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        stage_runs = {
            int(row["stage_number"]): int(row["id"])
            for row in connection.execute(
                "SELECT id, stage_number FROM stage_runs WHERE status='completed' AND stage_number IN (8,10,12)"
            )
        }
        if sorted(stage_runs) != [8, 10, 12]:
            raise RuntimeError("planner-v8 artifact lacks completed Stage8/10/12 runs")
        stage8_rows = connection.execute(
            "SELECT sequence_number, source_start, source_end, source_text, payload_json "
            "FROM run_items WHERE run_id=? AND kind='nlp_token' ORDER BY sequence_number",
            (stage_runs[8],),
        ).fetchall()
        stage10_rows = connection.execute(
            "SELECT sequence_number, source_start, source_end, source_text, payload_json "
            "FROM run_items WHERE run_id=? AND kind='context_sentence' ORDER BY sequence_number",
            (stage_runs[10],),
        ).fetchall()
        stage12_rows = connection.execute(
            "SELECT sequence_number, source_start, source_end, source_text, target_text, payload_json "
            "FROM run_items WHERE run_id=? AND kind='translation_segment' ORDER BY sequence_number",
            (stage_runs[12],),
        ).fetchall()
    finally:
        connection.close()

    tokens_by_sentence: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in stage8_rows:
        token = _non_space_token(row)
        if token is None:
            continue
        sentence_index = int((token["payload"] or {}).get("sentence_index"))
        tokens_by_sentence[sentence_index].append(token)
    context_by_sequence = {int(row["sequence_number"]): row for row in stage10_rows}
    stage12_by_context: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in stage12_rows:
        planner = dict((_decode_payload(row["payload_json"]).get("planner") or {}))
        start_sequence = planner.get("context_sentence_start")
        end_sequence = planner.get("context_sentence_end")
        if start_sequence is None or end_sequence is None or int(start_sequence) != int(end_sequence):
            continue
        stage12_by_context[int(start_sequence)].append(row)

    changed_sentences: list[dict[str, Any]] = []
    candidate_jobs: list[dict[str, Any]] = []
    for sequence, context in context_by_sequence.items():
        tokens = tokens_by_sentence.get(sequence) or []
        if len(tokens) <= PREFERRED_TOKENS:
            continue
        current_rows = sorted(
            stage12_by_context.get(sequence) or [], key=lambda row: int(row["source_start"])
        )
        if not current_rows:
            continue
        current_planners = [
            dict((_decode_payload(row["payload_json"]).get("planner") or {}))
            for row in current_rows
        ]
        if any(planner.get("source") != "nlp_sentence" for planner in current_planners):
            continue
        source_text = str(context["source_text"])
        if "".join(str(row["source_text"]) for row in current_rows) != source_text:
            continue
        source_start = int(context["source_start"])
        source_end = int(context["source_end"])
        current_cuts = [
            sum(1 for token in tokens if int(token["source_end"]) <= int(row["source_end"]))
            for row in current_rows
        ]
        candidate_cuts = _candidate_cut_indices(
            tokens,
            source_text=source_text,
            source_start=source_start,
        )
        if current_cuts == candidate_cuts:
            continue
        chunks = _chunks_from_cuts(
            tokens,
            candidate_cuts,
            source_text=source_text,
            source_start=source_start,
            source_end=source_end,
        )
        changed_index = len(changed_sentences)
        changed_sentences.append(
            {
                "context_sequence": sequence,
                "source_start": source_start,
                "source_end": source_end,
                "source_text": source_text,
                "non_space_token_count": len(tokens),
                "current_cut_indices": current_cuts,
                "candidate_cut_indices": candidate_cuts,
                "current_rows": current_rows,
                "candidate_chunks": chunks,
            }
        )
        for chunk_index, chunk in enumerate(chunks):
            candidate_jobs.append(
                {
                    "changed_index": changed_index,
                    "chunk_index": chunk_index,
                    **chunk,
                }
            )

    if len(changed_sentences) != 129:
        raise RuntimeError(
            f"pinned clause-boundary changed-sentence inventory drift: {len(changed_sentences)} != 129"
        )
    if not any(row["context_sequence"] == 669 for row in changed_sentences):
        raise RuntimeError("known long-content-loss context 669 is absent from candidate inventory")

    max_candidate_tokens = max(int(row["token_count"]) for row in candidate_jobs)
    translator = OpusTranslator(device="cpu", compute_type="float32")
    generated = _translate_batches(
        translator,
        [str(row["source_text"]) for row in candidate_jobs],
        max_decoding_length=max(128, max(PREFERRED_TOKENS, max_candidate_tokens) * 8),
    )
    candidate_results: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for job, hypotheses in zip(candidate_jobs, generated, strict=True):
        if not hypotheses:
            raise RuntimeError("OPUS returned no clause-boundary candidate hypothesis")
        target = str(hypotheses[0].get("text") or "").strip()
        if not target:
            raise RuntimeError("OPUS returned empty clause-boundary candidate target")
        verdict = _verdict(
            _source_row(int(job["chunk_index"]), job),
            target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        candidate_results[int(job["changed_index"])].append(
            {
                "chunk_index": int(job["chunk_index"]),
                "source_start": int(job["source_start"]),
                "source_end": int(job["source_end"]),
                "source_text": str(job["source_text"]),
                "token_count": int(job["token_count"]),
                "target_text": target,
                "rank": int(hypotheses[0].get("rank") or 0),
                "score": hypotheses[0].get("score"),
                "verdict": verdict,
            }
        )

    sentence_results: list[dict[str, Any]] = []
    hard_rescues: list[int] = []
    hard_regressions: list[int] = []
    strict_rescues: list[int] = []
    strict_regressions: list[int] = []
    numeric_rescues: list[int] = []
    numeric_regressions: list[int] = []
    focus_results: dict[str, Any] = {}

    for changed_index, changed in enumerate(changed_sentences):
        baseline_rows: list[dict[str, Any]] = []
        for row in changed["current_rows"]:
            target = str(row["target_text"] or "")
            baseline_rows.append(
                {
                    "planned_sequence": int(row["sequence_number"]),
                    "source_start": int(row["source_start"]),
                    "source_end": int(row["source_end"]),
                    "source_text": str(row["source_text"]),
                    "target_text": target,
                    "verdict": _verdict(
                        {
                            "sequence_number": int(row["sequence_number"]),
                            "source_start": int(row["source_start"]),
                            "source_end": int(row["source_end"]),
                            "source_text": str(row["source_text"]),
                            "target_text": None,
                        },
                        target,
                        punctuation_parameters=punctuation_parameters,
                        length_parameters=length_parameters,
                    ),
                }
            )
        candidates = sorted(
            candidate_results[changed_index], key=lambda row: int(row["chunk_index"])
        )
        baseline_counts = _sentence_verdict_counts(baseline_rows)
        candidate_counts = _sentence_verdict_counts(candidates)
        sequence = int(changed["context_sequence"])
        if not baseline_counts["all_hard_passed"] and candidate_counts["all_hard_passed"]:
            hard_rescues.append(sequence)
        if baseline_counts["all_hard_passed"] and not candidate_counts["all_hard_passed"]:
            hard_regressions.append(sequence)
        if not baseline_counts["all_strictly_eligible"] and candidate_counts["all_strictly_eligible"]:
            strict_rescues.append(sequence)
        if baseline_counts["all_strictly_eligible"] and not candidate_counts["all_strictly_eligible"]:
            strict_regressions.append(sequence)
        if int(baseline_counts["numeric_failure_count"]) > 0 and int(candidate_counts["numeric_failure_count"]) == 0:
            numeric_rescues.append(sequence)
        if int(baseline_counts["numeric_failure_count"]) == 0 and int(candidate_counts["numeric_failure_count"]) > 0:
            numeric_regressions.append(sequence)

        record = {
            "context_sequence": sequence,
            "source_start": int(changed["source_start"]),
            "source_end": int(changed["source_end"]),
            "source_text": str(changed["source_text"]),
            "non_space_token_count": int(changed["non_space_token_count"]),
            "current_cut_indices": list(changed["current_cut_indices"]),
            "candidate_cut_indices": list(changed["candidate_cut_indices"]),
            "baseline": baseline_counts,
            "candidate": candidate_counts,
            "baseline_units": baseline_rows,
            "candidate_units": candidates,
        }
        sentence_results.append(record)
        for name, span in FOCUS_SOURCE_SPANS.items():
            if int(changed["source_start"]) <= int(span[0]) and int(changed["source_end"]) >= int(span[1]):
                focus_results[name] = record

    if "long_content_loss" not in focus_results:
        raise RuntimeError("known long-content-loss focus span was not captured")

    database_sha_after = _sha_file(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("clause-boundary feasibility mutated retained Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": "full-corpus rank0 feasibility of conservative backward clause-boundary preference for ordinary Stage12 long-sentence splits",
        "promotion_allowed": False,
        "source_sha256": OPTICKS_SHA256,
        "planner_contract": PLANNER_CONTRACT,
        "baseline_run_id": EXPECTED_BASELINE_RUN_ID,
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "baseline_artifact_digest": EXPECTED_BASELINE_ARTIFACT_DIGEST,
        "baseline_numeric_json_sha256": _sha_file(baseline_path),
        "preferred_tokens": PREFERRED_TOKENS,
        "lookback_tokens": LOOKBACK_TOKENS,
        "generation": dict(GENERATION),
        "source_text_changed": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "candidate_boundary_classes": ["semicolon", "colon", "comma_before_conjunction"],
        "changed_sentence_count": len(changed_sentences),
        "candidate_unit_count": len(candidate_jobs),
        "hard_rescue_count": len(hard_rescues),
        "hard_rescue_context_sequences": sorted(hard_rescues),
        "hard_regression_count": len(hard_regressions),
        "hard_regression_context_sequences": sorted(hard_regressions),
        "strict_rescue_count": len(strict_rescues),
        "strict_rescue_context_sequences": sorted(strict_rescues),
        "strict_regression_count": len(strict_regressions),
        "strict_regression_context_sequences": sorted(strict_regressions),
        "numeric_rescue_count": len(numeric_rescues),
        "numeric_rescue_context_sequences": sorted(numeric_rescues),
        "numeric_regression_count": len(numeric_regressions),
        "numeric_regression_context_sequences": sorted(numeric_regressions),
        "focus_results": focus_results,
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "sentence_results": sentence_results,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)
    output_root = Path(
        os.environ.get("ROCKETDICT_CLAUSE_FEASIBILITY_ROOT", "work/clause-boundary-feasibility")
    ).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "full-opticks-clause-boundary-feasibility.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "schema",
                    "changed_sentence_count",
                    "candidate_unit_count",
                    "hard_rescue_count",
                    "hard_rescue_context_sequences",
                    "hard_regression_count",
                    "hard_regression_context_sequences",
                    "strict_rescue_count",
                    "strict_regression_count",
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
