from __future__ import annotations

"""Correlate current full-Opticks hard failures with whole-context shadow evidence.

This is a research-only artifact audit. It never changes the Product database or
selection policy. The cohort is source-derived: only split Stage10 contexts that
already contain at least one maintained Product hard-gate failure are included.
Whole-context candidates are then classified using the existing strict selector
recorded by the corpus-wide shadow run.
"""

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_run, get_run_items
from rocketdict.translation_rescue import SELECTOR_CONTRACT
from rocketdict.translation_rescue_stage import (
    MAX_WHOLE_CONTEXT_NLP_TOKENS,
    WHOLE_CONTEXT_RESCUE_CONTRACT,
)
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-whole-context-hard-failure-cohort/1"
HARD_GATE_SCHEMA = "rocketdict-full-opticks-hard-gate-inventory/2"
SHADOW_SCHEMA = "rocketdict-full-opticks-whole-context-shadow/2"
OPTICKS_SHA256 = "1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217"


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


def _failure_index(inventory: dict[str, Any]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for gate, key in (
        ("numeric", "numeric_failures"),
        ("punctuation", "punctuation_failures"),
        ("length", "length_failures"),
    ):
        for issue in list(inventory.get(key) or []):
            sequence = int(issue["segment_sequence"])
            row = indexed.setdefault(
                sequence,
                {
                    "segment_sequence": sequence,
                    "source_start": int(issue["source_start"]),
                    "source_end": int(issue["source_end"]),
                    "source_text": str(issue.get("source_text") or ""),
                    "target_text": str(issue.get("target_text") or ""),
                    "gates": [],
                },
            )
            if (
                int(issue["source_start"]) != row["source_start"]
                or int(issue["source_end"]) != row["source_end"]
                or str(issue.get("source_text") or "") != row["source_text"]
                or str(issue.get("target_text") or "") != row["target_text"]
            ):
                raise RuntimeError(
                    f"Hard-gate issue identity disagrees for segment {sequence}"
                )
            row["gates"].append(gate)
    for row in indexed.values():
        row["gates"] = sorted(set(row["gates"]))
    return indexed


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_NUMERIC_STRESS_ROOT", "work/full-opticks-numeric-stress")
    ).resolve()
    hard_path = root / "full-opticks-hard-gate-inventory.json"
    shadow_path = root / "full-opticks-whole-context-shadow.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not hard_path.is_file() or not shadow_path.is_file() or not database.is_file():
        raise RuntimeError("Hard-gate, whole-context shadow, or Product database evidence is missing")

    hard = json.loads(hard_path.read_text(encoding="utf-8"))
    shadow = json.loads(shadow_path.read_text(encoding="utf-8"))
    if hard.get("schema") != HARD_GATE_SCHEMA:
        raise RuntimeError(f"Unexpected hard-gate schema: {hard.get('schema')!r}")
    if shadow.get("schema") != SHADOW_SCHEMA:
        raise RuntimeError(f"Unexpected whole-context shadow schema: {shadow.get('schema')!r}")
    if hard.get("source_sha256") != OPTICKS_SHA256 or shadow.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Pinned Opticks source identity drift")
    for field in (
        "source_text_sha256",
        "document_version_id",
        "selected_translation_run_id",
        "selected_translation_output_sha256",
    ):
        if hard.get(field) != shadow.get(field):
            raise RuntimeError(f"Hard-gate/shadow identity mismatch for {field}")
    if hard.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Hard-gate inventory planner contract drift")
    if shadow.get("primary_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Whole-context shadow planner contract drift")
    if int(shadow.get("maximum_whole_context_nlp_tokens") or 0) != MAX_WHOLE_CONTEXT_NLP_TOKENS:
        raise RuntimeError("Whole-context shadow token cap drift")

    selected_run_id = int(hard["selected_translation_run_id"])
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        rows = get_run_items(connection, selected_run_id, kind="translation_segment")
    if str(selected_run.get("output_sha256") or "") != str(hard["selected_translation_output_sha256"]):
        raise RuntimeError("Persisted selected Stage12 output identity drift")

    ordered = sorted(rows, key=lambda row: int(row["sequence_number"]))
    by_context: dict[int, list[dict[str, Any]]] = defaultdict(list)
    segment_context: dict[int, int] = {}
    for row in ordered:
        context = _context_sequence(row)
        if context is None:
            continue
        sequence = int(row["sequence_number"])
        segment_context[sequence] = context
        by_context[context].append(row)
    split_contexts = {
        context: context_rows
        for context, context_rows in by_context.items()
        if len(context_rows) >= 2
    }

    failures = _failure_index(hard)
    recomputed_hard_union = sorted(failures)
    expected_hard_union = sorted(
        {
            int(issue["segment_sequence"])
            for key in ("numeric_failures", "punctuation_failures", "length_failures")
            for issue in list(hard.get(key) or [])
        }
    )
    if recomputed_hard_union != expected_hard_union:
        raise RuntimeError("Hard-gate failure union reconstruction drift")

    split_hard_sequences = sorted(
        sequence
        for sequence in failures
        if segment_context.get(sequence) in split_contexts
    )
    if split_hard_sequences != sorted(
        int(value) for value in hard.get("split_hard_failure_segment_sequences", [])
    ):
        raise RuntimeError("Hard-gate split-failure inventory drift")

    hard_contexts: dict[int, list[int]] = defaultdict(list)
    for sequence in split_hard_sequences:
        hard_contexts[segment_context[sequence]].append(sequence)

    candidates = {
        int(row["context_sequence"]): row
        for row in list(shadow.get("all_candidates") or [])
    }
    if len(candidates) != int(shadow.get("split_context_count_within_cap") or -1):
        raise RuntimeError("Whole-context shadow candidate cardinality drift")
    over_cap = {
        int(value) for value in shadow.get("split_context_sequences_over_cap", [])
    }
    if len(over_cap) != int(shadow.get("split_context_count_over_cap") or -1):
        raise RuntimeError("Whole-context over-cap cardinality drift")

    review: list[dict[str, Any]] = []
    accepted_contexts: list[int] = []
    rejected_contexts: list[int] = []
    over_cap_contexts: list[int] = []
    gate_context_counts: Counter[str] = Counter()
    for context in sorted(hard_contexts):
        sequences = sorted(hard_contexts[context])
        context_failures = [failures[sequence] for sequence in sequences]
        gates = sorted({gate for failure in context_failures for gate in failure["gates"]})
        for gate in gates:
            gate_context_counts[gate] += 1

        candidate = candidates.get(context)
        if candidate is None:
            if context not in over_cap:
                raise RuntimeError(
                    f"Hard-failing split context {context} is neither shadowed nor over cap"
                )
            over_cap_contexts.append(context)
            review.append(
                {
                    "context_sequence": context,
                    "status": "over_cap",
                    "hard_failure_segment_sequences": sequences,
                    "hard_failure_gates": gates,
                    "hard_failures": context_failures,
                    "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
                }
            )
            continue
        if context in over_cap:
            raise RuntimeError(f"Context {context} is both shadowed and marked over cap")

        selection = dict(candidate.get("selection") or {})
        if selection.get("selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError(f"Context {context} selector contract drift")
        accepted = selection.get("accepted") is True
        strict_clean = selection.get("strict_clean") is True
        alpha_non_decreasing = selection.get("target_alpha_non_decreasing") is True
        if accepted != bool(strict_clean and alpha_non_decreasing):
            raise RuntimeError(f"Context {context} acceptance invariant drift")

        if accepted:
            accepted_contexts.append(context)
            status = "mechanically_accepted"
        else:
            rejected_contexts.append(context)
            status = "mechanically_rejected"

        review.append(
            {
                "context_sequence": context,
                "status": status,
                "hard_failure_segment_sequences": sequences,
                "hard_failure_gates": gates,
                "hard_failures": context_failures,
                "source_start": int(candidate["source_start"]),
                "source_end": int(candidate["source_end"]),
                "nlp_token_count": int(candidate["nlp_token_count"]),
                "source_text": str(candidate.get("source_text") or ""),
                "primary_target_concatenated": str(
                    candidate.get("primary_target_concatenated") or ""
                ),
                "whole_context_rank0_target": str(
                    candidate.get("whole_context_rank0_target") or ""
                ),
                "whole_context_rank0_score": candidate.get("whole_context_rank0_score"),
                "selection": selection,
            }
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only cohort of already-hard-failing split Product contexts "
            "against existing strict whole-context shadow candidates"
        ),
        "promotion_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(hard["source_text_sha256"]),
        "document_version_id": int(hard["document_version_id"]),
        "selected_translation_run_id": selected_run_id,
        "selected_translation_output_sha256": str(
            hard["selected_translation_output_sha256"]
        ),
        "planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": hard.get("structural_label_contract"),
        "whole_context_rescue_contract": WHOLE_CONTEXT_RESCUE_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        "hard_failure_segment_union_count": len(failures),
        "split_hard_failure_segment_count": len(split_hard_sequences),
        "split_hard_failure_context_count": len(hard_contexts),
        "within_cap_hard_failure_context_count": len(accepted_contexts)
        + len(rejected_contexts),
        "over_cap_hard_failure_context_count": len(over_cap_contexts),
        "mechanically_accepted_hard_failure_context_count": len(accepted_contexts),
        "mechanically_rejected_hard_failure_context_count": len(rejected_contexts),
        "accepted_context_sequences": accepted_contexts,
        "rejected_context_sequences": rejected_contexts,
        "over_cap_context_sequences": over_cap_contexts,
        "hard_failure_context_count_by_gate": dict(sorted(gate_context_counts.items())),
        "review_candidates": review,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)

    output = root / "full-opticks-whole-context-hard-failure-cohort.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "split_hard_failure_segment_count": len(split_hard_sequences),
                "split_hard_failure_context_count": len(hard_contexts),
                "within_cap_hard_failure_context_count": (
                    len(accepted_contexts) + len(rejected_contexts)
                ),
                "over_cap_hard_failure_context_count": len(over_cap_contexts),
                "mechanically_accepted_hard_failure_context_count": len(
                    accepted_contexts
                ),
                "accepted_context_sequences": accepted_contexts,
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
