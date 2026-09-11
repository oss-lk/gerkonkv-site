from __future__ import annotations

"""Read-only post-composition hard-failure/whole-context lineage audit.

This audit starts from the persisted Stage12 output after the opt-in length and
citation-boundary rescues. It independently recomputes the maintained hard
gates, rebuilds the exact split-context residual cohort from persisted planner
metadata, and joins it to the immutable canonical whole-context shadow by
source/context identity.

A canonical shadow candidate is reusable evidence only when the current
composed primary rows are byte/target-exact to the rows that candidate was
generated against. The candidate selection is then recomputed with the current
maintained selector. Finally, an in-memory counterfactual applies only those
lineage-exact, mechanically accepted raw rank-0 candidates and recomputes the
full-corpus hard gates. The database is opened read-only and is never mutated.

This is research evidence only. It does not authorize Product promotion or
change any default selector.
"""

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.numeric_integrity import CONTRACT as NUMERIC_CONTRACT
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair
from rocketdict.stages import _length_issues, _punctuation_issues
from rocketdict.translation_rescue import (
    LENGTH_MAX_RATIO,
    LENGTH_MIN_RATIO,
    SELECTOR_CONTRACT,
    evaluate_candidate_context,
)
from rocketdict.translation_rescue_stage import MAX_WHOLE_CONTEXT_NLP_TOKENS
from rocketdict.translation_stage import PLANNER_CONTRACT

SCHEMA = "rocketdict-full-opticks-composed-whole-context-residual-audit/1"
COMBINED_SCHEMA = "rocketdict-full-opticks-combined-length-citation-product-rescue-optin/1"
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


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    return {
        "type": "numeric_symbol_mismatch",
        "segment_sequence": int(row["sequence_number"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": source,
        "target_text": target,
        "numeric_contract": NUMERIC_CONTRACT,
        "verdict": verdict,
    }


def _single_gate_issue(
    row: dict[str, Any],
    *,
    gate: str,
    length_parameters: dict[str, Any],
) -> dict[str, Any] | None:
    probe = {
        "sequence_number": int(row["sequence_number"]),
        "source_start": int(row["source_start"]),
        "source_end": int(row["source_end"]),
        "source_text": str(row.get("source_text") or ""),
        "target_text": str(row.get("target_text") or ""),
    }
    if gate == "punctuation":
        issues = _punctuation_issues([probe], {})
    elif gate == "length":
        issues = _length_issues([probe], length_parameters)
    else:
        raise ValueError(gate)
    if not issues:
        return None
    if len(issues) != 1:
        raise RuntimeError(f"{gate} gate returned unexpected issue cardinality")
    return dict(issues[0])


def _inventory(
    rows: list[dict[str, Any]],
    *,
    length_parameters: dict[str, Any],
) -> dict[str, Any]:
    numeric: list[dict[str, Any]] = []
    punctuation: list[dict[str, Any]] = []
    length: list[dict[str, Any]] = []
    for row in rows:
        issue = _numeric_issue(row)
        if issue is not None:
            numeric.append(issue)
        issue = _single_gate_issue(
            row, gate="punctuation", length_parameters=length_parameters
        )
        if issue is not None:
            punctuation.append(issue)
        issue = _single_gate_issue(
            row, gate="length", length_parameters=length_parameters
        )
        if issue is not None:
            length.append(issue)
    union = {
        int(issue["segment_sequence"])
        for issues in (numeric, punctuation, length)
        for issue in issues
    }
    return {
        "numeric": numeric,
        "punctuation": punctuation,
        "length": length,
        "numeric_count": len(numeric),
        "punctuation_count": len(punctuation),
        "length_count": len(length),
        "unique_failure_count": len(union),
        "failure_sequences": sorted(union),
    }


def _failure_index(inventory: dict[str, Any]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for gate in ("numeric", "punctuation", "length"):
        for issue in inventory[gate]:
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


def _shadow_primary_rows(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": str(row.get("source_text") or ""),
            "target_text": str(row.get("target_text") or ""),
        }
        for row in list(candidate.get("primary_rows") or [])
    ]


def _current_primary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": str(row.get("source_text") or ""),
            "target_text": str(row.get("target_text") or ""),
        }
        for row in rows
    ]


def _counterfactual_rows(
    ordered: list[dict[str, Any]],
    *,
    split_contexts: dict[int, list[dict[str, Any]]],
    accepted_candidates: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    replacement_by_first_sequence: dict[int, dict[str, Any]] = {}
    consumed_sequences: set[int] = set()
    for context, candidate in accepted_candidates.items():
        current = split_contexts[context]
        sequences = [int(row["sequence_number"]) for row in current]
        if not sequences:
            raise RuntimeError(f"Context {context} has no current rows")
        if any(sequence in consumed_sequences for sequence in sequences):
            raise RuntimeError("Counterfactual contexts overlap")
        consumed_sequences.update(sequences)
        replacement_by_first_sequence[min(sequences)] = {
            "sequence_number": min(sequences),
            "kind": "translation_segment",
            "source_start": int(candidate["source_start"]),
            "source_end": int(candidate["source_end"]),
            "source_text": str(candidate["source_text"]),
            "target_text": str(candidate["whole_context_rank0_target"]),
            "payload": {
                "research_counterfactual": True,
                "context_sequence": int(context),
                "selector_contract": SELECTOR_CONTRACT,
            },
        }

    out: list[dict[str, Any]] = []
    for row in ordered:
        sequence = int(row["sequence_number"])
        replacement = replacement_by_first_sequence.get(sequence)
        if replacement is not None:
            out.append(replacement)
        if sequence not in consumed_sequences:
            out.append(row)

    for sequence, row in enumerate(out):
        row = dict(row)
        row["sequence_number"] = sequence
        out[sequence] = row
    return out


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_COMPOSED_RESIDUAL_ROOT",
            "work/composed-whole-context-residual",
        )
    ).resolve()
    combined_path = root / "full-opticks-combined-length-citation-product-rescue-optin.json"
    shadow_path = root / "full-opticks-whole-context-shadow.json"
    database = root / "rocketdict.sqlite"
    if not combined_path.is_file() or not shadow_path.is_file() or not database.is_file():
        raise RuntimeError("Composed Product database/evidence or whole-context shadow is missing")

    combined = json.loads(combined_path.read_text(encoding="utf-8"))
    shadow = json.loads(shadow_path.read_text(encoding="utf-8"))
    if combined.get("schema") != COMBINED_SCHEMA:
        raise RuntimeError(f"Unexpected composed schema: {combined.get('schema')!r}")
    if shadow.get("schema") != SHADOW_SCHEMA:
        raise RuntimeError(f"Unexpected shadow schema: {shadow.get('schema')!r}")
    if combined.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Composed Opticks source identity drift")
    if shadow.get("source_sha256") != OPTICKS_SHA256:
        raise RuntimeError("Shadow Opticks source identity drift")
    if combined.get("source_text_sha256") != shadow.get("source_text_sha256"):
        raise RuntimeError("Composed/shadow normalized source identity mismatch")
    if int(combined["document_version_id"]) != int(shadow["document_version_id"]):
        raise RuntimeError("Composed/shadow document version mismatch")
    if combined.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Composed planner contract drift")
    if shadow.get("primary_planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Shadow planner contract drift")
    if (
        str(combined["canonical_translation_output_sha256"])
        != str(shadow["selected_translation_output_sha256"])
    ):
        raise RuntimeError("Shadow does not belong to the composed run's canonical baseline")
    if int(shadow.get("maximum_whole_context_nlp_tokens") or 0) != MAX_WHOLE_CONTEXT_NLP_TOKENS:
        raise RuntimeError("Whole-context token cap drift")

    database_sha_before = _sha_file(database)
    selected_run_id = int(combined["enabled_translation_run_id"])
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        ordered = sorted(
            get_run_items(connection, selected_run_id, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        document = get_document(connection, int(combined["document_version_id"]))
    if str(selected_run.get("output_sha256") or "") != str(
        combined["enabled_translation_output_sha256"]
    ):
        raise RuntimeError("Persisted composed Stage12 output identity drift")
    if len(ordered) != int(combined["enabled_segment_count"]):
        raise RuntimeError("Persisted composed segment count drift")
    content = str(document["content_text"])
    if "".join(str(row.get("source_text") or "") for row in ordered) != content:
        raise RuntimeError("Composed Stage12 source coverage is not byte-exact")

    length_parameters = {
        "min_ratio": LENGTH_MIN_RATIO,
        "max_ratio": LENGTH_MAX_RATIO,
    }
    current = _inventory(ordered, length_parameters=length_parameters)
    expected_counts = dict(combined.get("enabled_hard_gate_counts") or {})
    expected = {
        "numeric_count": int(expected_counts.get("numeric_symbol") or 0),
        "punctuation_count": int(expected_counts.get("punctuation") or 0),
        "length_count": int(expected_counts.get("length") or 0),
        "unique_failure_count": int(combined["enabled_unique_hard_failure_count"]),
    }
    actual = {
        key: int(current[key])
        for key in (
            "numeric_count",
            "punctuation_count",
            "length_count",
            "unique_failure_count",
        )
    }
    if actual != expected:
        raise RuntimeError(f"Composed hard-gate recomputation drift: {actual} != {expected}")

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
        context: rows for context, rows in by_context.items() if len(rows) >= 2
    }

    failures = _failure_index(current)
    split_failures: dict[int, list[int]] = defaultdict(list)
    for sequence in sorted(failures):
        context = segment_context.get(sequence)
        if context in split_contexts:
            split_failures[int(context)].append(sequence)

    shadow_candidates = {
        int(row["context_sequence"]): row
        for row in list(shadow.get("all_candidates") or [])
    }
    over_cap = {
        int(value) for value in list(shadow.get("split_context_sequences_over_cap") or [])
    }

    review: list[dict[str, Any]] = []
    accepted_candidates: dict[int, dict[str, Any]] = {}
    lineage_exact_count = 0
    gate_context_counts: Counter[str] = Counter()
    accepted_gate_context_counts: Counter[str] = Counter()
    for context in sorted(split_failures):
        sequences = sorted(split_failures[context])
        current_context_rows = split_contexts[context]
        context_failures = [failures[sequence] for sequence in sequences]
        gates = sorted({gate for row in context_failures for gate in row["gates"]})
        for gate in gates:
            gate_context_counts[gate] += 1

        candidate = shadow_candidates.get(context)
        if candidate is None:
            if context not in over_cap:
                raise RuntimeError(
                    f"Residual split context {context} is neither shadowed nor over cap"
                )
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
            raise RuntimeError(f"Context {context} is both shadowed and over cap")

        current_primary = _current_primary_rows(current_context_rows)
        shadow_primary = _shadow_primary_rows(candidate)
        source_exact = (
            int(candidate["source_start"]) == int(current_context_rows[0]["source_start"])
            and int(candidate["source_end"]) == int(current_context_rows[-1]["source_end"])
            and str(candidate.get("source_text") or "")
            == "".join(str(row.get("source_text") or "") for row in current_context_rows)
        )
        primary_lineage_exact = source_exact and current_primary == shadow_primary
        if primary_lineage_exact:
            lineage_exact_count += 1

        recorded_selection = dict(candidate.get("selection") or {})
        if recorded_selection.get("selector_contract") != SELECTOR_CONTRACT:
            raise RuntimeError(f"Context {context} shadow selector contract drift")
        candidate_row = {
            "source_text": str(candidate.get("source_text") or ""),
            "target_text": str(candidate.get("whole_context_rank0_target") or ""),
        }
        recomputed_selection = evaluate_candidate_context(current_primary, [candidate_row])
        selection_invariant_exact = (
            bool(recomputed_selection.get("accepted"))
            == bool(recorded_selection.get("accepted"))
            and bool(recomputed_selection.get("strict_clean"))
            == bool(recorded_selection.get("strict_clean"))
            and bool(recomputed_selection.get("numeric_clean"))
            == bool(recorded_selection.get("numeric_clean"))
            and int(recomputed_selection.get("target_alpha_primary") or 0)
            == int(recorded_selection.get("target_alpha_primary") or 0)
            and int(recomputed_selection.get("target_alpha_candidate") or 0)
            == int(recorded_selection.get("target_alpha_candidate") or 0)
            and bool(recomputed_selection.get("target_alpha_non_decreasing"))
            == bool(recorded_selection.get("target_alpha_non_decreasing"))
        )
        if primary_lineage_exact and not selection_invariant_exact:
            raise RuntimeError(
                f"Context {context} current selector disagrees with immutable shadow"
            )

        reusable_accepted = (
            primary_lineage_exact
            and selection_invariant_exact
            and recomputed_selection.get("accepted") is True
        )
        if reusable_accepted:
            accepted_candidates[context] = candidate
            for gate in gates:
                accepted_gate_context_counts[gate] += 1
            status = "lineage_exact_mechanically_accepted"
        elif not primary_lineage_exact:
            status = "lineage_changed_not_reusable"
        else:
            status = "lineage_exact_mechanically_rejected"

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
                "primary_lineage_exact": primary_lineage_exact,
                "selection_invariant_exact": selection_invariant_exact,
                "primary_target_concatenated": str(
                    candidate.get("primary_target_concatenated") or ""
                ),
                "whole_context_rank0_target": str(
                    candidate.get("whole_context_rank0_target") or ""
                ),
                "whole_context_rank0_score": candidate.get("whole_context_rank0_score"),
                "recorded_selection": recorded_selection,
                "recomputed_selection": recomputed_selection,
            }
        )

    counterfactual_rows = _counterfactual_rows(
        ordered,
        split_contexts=split_contexts,
        accepted_candidates=accepted_candidates,
    )
    if "".join(str(row.get("source_text") or "") for row in counterfactual_rows) != content:
        raise RuntimeError("Counterfactual source coverage is not byte-exact")
    counterfactual = _inventory(
        counterfactual_rows,
        length_parameters=length_parameters,
    )
    if any(
        int(counterfactual[key]) > int(current[key])
        for key in ("numeric_count", "punctuation_count", "length_count", "unique_failure_count")
    ):
        raise RuntimeError("Mechanically accepted counterfactual regressed a maintained hard gate")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "read-only post-composition residual hard-gate inventory, canonical "
            "whole-context shadow lineage proof, and mechanically accepted "
            "counterfactual; not Product promotion"
        ),
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
        "automatic_product_selection_allowed": False,
        "semantic_review_required": True,
        "source_sha256": OPTICKS_SHA256,
        "source_text_sha256": str(combined["source_text_sha256"]),
        "document_version_id": int(combined["document_version_id"]),
        "composed_translation_run_id": selected_run_id,
        "composed_translation_output_sha256": str(
            combined["enabled_translation_output_sha256"]
        ),
        "canonical_translation_output_sha256": str(
            combined["canonical_translation_output_sha256"]
        ),
        "planner_contract": PLANNER_CONTRACT,
        "numeric_contract": NUMERIC_CONTRACT,
        "selector_contract": SELECTOR_CONTRACT,
        "maximum_whole_context_nlp_tokens": MAX_WHOLE_CONTEXT_NLP_TOKENS,
        "length_parameters": length_parameters,
        "segment_count": len(ordered),
        "split_context_count": len(split_contexts),
        "split_segment_count": sum(len(value) for value in split_contexts.values()),
        "current_hard_gate_counts": {
            "numeric": current["numeric_count"],
            "punctuation": current["punctuation_count"],
            "length": current["length_count"],
            "unique": current["unique_failure_count"],
        },
        "split_hard_failure_segment_count": sum(len(v) for v in split_failures.values()),
        "split_hard_failure_context_count": len(split_failures),
        "split_hard_failure_context_sequences": sorted(split_failures),
        "split_hard_failure_context_count_by_gate": dict(sorted(gate_context_counts.items())),
        "shadowed_residual_context_count": len(split_failures)
        - sum(1 for row in review if row["status"] == "over_cap"),
        "over_cap_residual_context_count": sum(
            1 for row in review if row["status"] == "over_cap"
        ),
        "lineage_exact_shadow_context_count": lineage_exact_count,
        "lineage_exact_mechanically_accepted_context_count": len(accepted_candidates),
        "lineage_exact_mechanically_accepted_context_sequences": sorted(accepted_candidates),
        "accepted_context_count_by_gate": dict(sorted(accepted_gate_context_counts.items())),
        "counterfactual_hard_gate_counts": {
            "numeric": counterfactual["numeric_count"],
            "punctuation": counterfactual["punctuation_count"],
            "length": counterfactual["length_count"],
            "unique": counterfactual["unique_failure_count"],
        },
        "counterfactual_segment_count": len(counterfactual_rows),
        "review_candidates": review,
        "current_numeric_failures": current["numeric"],
        "current_punctuation_failures": current["punctuation"],
        "current_length_failures": current["length"],
        "counterfactual_numeric_failures": counterfactual["numeric"],
        "counterfactual_punctuation_failures": counterfactual["punctuation"],
        "counterfactual_length_failures": counterfactual["length"],
        "source_coverage_byte_exact": True,
        "database_unchanged": True,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
    }
    payload["evidence_sha256"] = _canonical_sha(payload)

    if _sha_file(database) != database_sha_before:
        raise RuntimeError("Residual audit mutated the persisted Product database")

    output = root / "full-opticks-composed-whole-context-residual-audit.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "current_hard_gate_counts": payload["current_hard_gate_counts"],
                "split_hard_failure_segment_count": payload[
                    "split_hard_failure_segment_count"
                ],
                "split_hard_failure_context_count": payload[
                    "split_hard_failure_context_count"
                ],
                "lineage_exact_mechanically_accepted_context_sequences": payload[
                    "lineage_exact_mechanically_accepted_context_sequences"
                ],
                "counterfactual_hard_gate_counts": payload[
                    "counterfactual_hard_gate_counts"
                ],
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
