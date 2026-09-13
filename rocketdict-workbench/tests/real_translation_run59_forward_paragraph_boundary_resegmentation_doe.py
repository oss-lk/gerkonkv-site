from __future__ import annotations

"""Read-only DOE for a narrow forward paragraph-terminal Stage12 resegmentation.

The maintained run59 translation remains immutable.  This experiment discovers
eligible adjacent split rows from source/planner geometry only, moves the current
cut forward through a short question tail and blank paragraph boundary, and
translates the two resulting exact source spans with raw OPUS rank0.  It never
rewrites source or target bytes and never mutates the database.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-run59-forward-paragraph-boundary-resegmentation-doe/1"
BASE_RUN_ID = 59
BASE_DATABASE_SHA256 = "a12cefa073d51250a29ee3ad9ad72ef97795536466dd1771c9d6a1036e81b2a"
BASE_RUN_OUTPUT_SHA256 = "5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
PLANNER_CONTRACT = "rocketdict-stage12-protected-split/8"
MAX_FORWARD_NLP_TOKENS = 8
MIN_SUFFIX_ALPHA_WORDS = 20
MAX_PREFIX_CHARS = 160
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768
_ALPHA_WORD_RE = re.compile(r"[A-Za-z]+")
_PREFIX_RE = re.compile(
    rf"^(.{{1,{MAX_PREFIX_CHARS}}}?\?[ \t]*\r?\n[ \t\r]*\n)",
    re.DOTALL,
)


def _sha(path: Path) -> str:
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


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row.get("payload") or {})


def _planner(row: dict[str, Any]) -> dict[str, Any]:
    return dict(_payload(row).get("planner") or {})


def _alpha_count(text: str) -> int:
    return sum(char.isalpha() for char in text)


def _alpha_word_count(text: str) -> int:
    return len(_ALPHA_WORD_RE.findall(text))


def _strict_non_punctuation_clean(verdict: dict[str, Any]) -> bool:
    return bool(
        (verdict.get("numeric_symbol") or {}).get("passed") is True
        and verdict.get("length_passed") is True
        and (verdict.get("numeric_order") or {}).get("passed") is True
        and (verdict.get("delimiter_preservation") or {}).get("passed") is True
        and (verdict.get("critical_technical_tokens") or {}).get("passed") is True
        and (verdict.get("output_artifacts") or {}).get("passed") is True
    )


def _single_split_context(row: dict[str, Any]) -> tuple[int, int, int] | None:
    planner = _planner(row)
    if (
        planner.get("planner_contract") != PLANNER_CONTRACT
        or planner.get("source") != "nlp_sentence"
        or planner.get("split") is not True
    ):
        return None
    try:
        first = int(planner["context_sentence_start"])
        last = int(planner["context_sentence_end"])
        count = int(planner.get("context_sentence_count", 1))
        token_count = int(planner["token_count"])
        preferred = int(planner["preferred_token_budget"])
    except (KeyError, TypeError, ValueError):
        return None
    if first < 0 or first != last or count != 1 or token_count <= 0 or preferred <= 0:
        return None
    return first, token_count, preferred


def _non_space_nlp_tokens(
    nlp_tokens: list[dict[str, Any]], *, start: int, end: int
) -> list[dict[str, Any]]:
    return [
        token
        for token in nlp_tokens
        if int(token["source_start"]) >= start
        and int(token["source_end"]) <= end
        and not bool((_payload(token).get("flags") or {}).get("is_space"))
    ]


def discover_trigger(
    *,
    content: str,
    left: dict[str, Any],
    right: dict[str, Any],
    nlp_tokens: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return source-owned trigger evidence, never a corpus row whitelist."""
    left_geometry = _single_split_context(left)
    right_geometry = _single_split_context(right)
    if left_geometry is None or right_geometry is None:
        return None
    left_context, left_token_count, preferred = left_geometry
    right_context, right_token_count, right_preferred = right_geometry
    if left_context != right_context or preferred != right_preferred:
        return None

    left_start = int(left["source_start"])
    left_end = int(left["source_end"])
    right_start = int(right["source_start"])
    right_end = int(right["source_end"])
    left_source = str(left.get("source_text") or "")
    right_source = str(right.get("source_text") or "")
    left_target = str(left.get("target_text") or "")
    right_target = str(right.get("target_text") or "")

    if left_end != right_start:
        return None
    if not (
        0 <= left_start < left_end < right_end <= len(content)
        and content[left_start:left_end] == left_source
        and content[right_start:right_end] == right_source
    ):
        return None

    match = _PREFIX_RE.match(right_source)
    if match is None:
        return None
    prefix = match.group(1)
    suffix = right_source[len(prefix) :]
    if not suffix.strip() or _alpha_word_count(suffix) < MIN_SUFFIX_ALPHA_WORDS:
        return None
    if prefix.count("?") != 1 or suffix.count("?") != 0:
        return None

    new_boundary = right_start + len(prefix)
    prefix_tokens = _non_space_nlp_tokens(
        nlp_tokens, start=right_start, end=new_boundary
    )
    if not (1 <= len(prefix_tokens) <= MAX_FORWARD_NLP_TOKENS):
        return None
    if left_token_count < preferred:
        return None
    if left_token_count + len(prefix_tokens) > preferred + MAX_FORWARD_NLP_TOKENS:
        return None

    left_verdict = evaluate_rescue_pair(left_source, left_target)
    right_verdict = evaluate_rescue_pair(right_source, right_target)
    if left_verdict.get("strictly_eligible") is not True:
        return None
    if right_verdict.get("punctuation_passed") is True:
        return None
    if not _strict_non_punctuation_clean(right_verdict):
        return None
    if right_source.count("?") <= right_target.count("?"):
        return None

    candidate_left = content[left_start:new_boundary]
    candidate_right = content[new_boundary:right_end]
    if candidate_left != left_source + prefix or candidate_right != suffix:
        raise RuntimeError("forward paragraph resegmentation source coverage drift")
    return {
        "eligible": True,
        "context_sequence": left_context,
        "left_sequence": int(left["sequence_number"]),
        "right_sequence": int(right["sequence_number"]),
        "old_boundary": right_start,
        "new_boundary": new_boundary,
        "forward_char_count": len(prefix),
        "forward_nlp_token_count": len(prefix_tokens),
        "preferred_token_budget": preferred,
        "base_left_nlp_token_count": left_token_count,
        "base_right_nlp_token_count": right_token_count,
        "candidate_left_nlp_token_count": left_token_count + len(prefix_tokens),
        "candidate_right_nlp_token_count": right_token_count - len(prefix_tokens),
        "prefix": prefix,
        "suffix_alpha_word_count": _alpha_word_count(suffix),
        "base_left_source": left_source,
        "base_right_source": right_source,
        "base_left_target": left_target,
        "base_right_target": right_target,
        "candidate_left_source": candidate_left,
        "candidate_right_source": candidate_right,
        "base_left_verdict": left_verdict,
        "base_right_verdict": right_verdict,
    }


def evaluate_candidate(source: str, target: str) -> dict[str, Any]:
    verdict = evaluate_rescue_pair(source, target)
    emphasis = compare_emphasis_markup_preservation(source, target)
    return {
        "accepted": bool(
            target.strip()
            and verdict.get("strictly_eligible") is True
            and emphasis.get("passed") is True
        ),
        "strictly_eligible": verdict.get("strictly_eligible") is True,
        "mechanical_verdict": verdict,
        "emphasis_markup": emphasis,
        "source_alpha_count": _alpha_count(source),
        "target_alpha_count": _alpha_count(target),
    }


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_RUN59_FORWARD_PARAGRAPH_DOE_ROOT",
            "work/run59-forward-paragraph-boundary-resegmentation-doe",
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "rocketdict.sqlite"
    before_sha = _sha(database)
    if before_sha != BASE_DATABASE_SHA256:
        raise RuntimeError(
            f"run59 DOE database identity drift: {before_sha} != {BASE_DATABASE_SHA256}"
        )

    with connect(database, readonly=True) as connection:
        run = get_run(connection, BASE_RUN_ID)
        if str(run.get("output_sha256") or "") != BASE_RUN_OUTPUT_SHA256:
            raise RuntimeError("run59 stage output identity drift")
        rows = sorted(
            get_run_items(connection, BASE_RUN_ID, kind="translation_segment"),
            key=lambda row: int(row["sequence_number"]),
        )
        output = dict(run.get("output") or {})
        context_run_id = int(output["context_run_id"])
        document = get_document(connection, int(output["document_version_id"]))
        context_run = get_run(connection, context_run_id)
        context_output = dict(context_run.get("output") or {})
        nlp_run_id = int(context_output["nlp_run_id"])
        nlp_tokens = sorted(
            get_run_items(connection, nlp_run_id, kind="nlp_token"),
            key=lambda row: int(row["sequence_number"]),
        )

    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("canonical source identity drift")
    content = str(document["content_text"])
    if len(rows) != 3335:
        raise RuntimeError(f"run59 segment census drift: {len(rows)}")

    attempts: list[dict[str, Any]] = []
    for left, right in zip(rows, rows[1:]):
        trigger = discover_trigger(
            content=content,
            left=left,
            right=right,
            nlp_tokens=nlp_tokens,
        )
        if trigger is not None:
            attempts.append(trigger)

    # This is a corpus-level identity assertion after a generic trigger, not a
    # sequence whitelist. Drift fails closed and requires renewed research.
    if len(attempts) != 1:
        raise RuntimeError(
            f"forward paragraph-boundary trigger cohort drift: {len(attempts)}"
        )

    translator = OpusTranslator(device="cpu", compute_type="float32")
    model_inputs: list[str] = []
    for attempt in attempts:
        model_inputs.extend(
            [attempt["candidate_left_source"], attempt["candidate_right_source"]]
        )
    translated = translator.translate(
        model_inputs,
        beam_size=BEAM_SIZE,
        num_hypotheses=NUM_HYPOTHESES,
        max_decoding_length=MAX_DECODING_LENGTH,
    )
    if len(translated) != len(model_inputs):
        raise RuntimeError("OPUS forward-resegmentation cardinality drift")

    cursor = 0
    accepted_attempts: list[dict[str, Any]] = []
    for attempt in attempts:
        candidate_rows: list[dict[str, Any]] = []
        for side in ("left", "right"):
            hypotheses = translated[cursor]
            cursor += 1
            if len(hypotheses) != 1 or int(hypotheses[0].get("rank", -1)) != 0:
                raise RuntimeError("DOE permits only one raw rank0 hypothesis")
            source = str(attempt[f"candidate_{side}_source"])
            target = str(hypotheses[0].get("text") or "")
            selection = evaluate_candidate(source, target)
            candidate_rows.append(
                {
                    "side": side,
                    "model_input": source,
                    "hypothesis": dict(hypotheses[0]),
                    "raw_rank0_target": target,
                    "selection": selection,
                }
            )

        base_alpha = _alpha_count(
            str(attempt["base_left_target"]) + str(attempt["base_right_target"])
        )
        candidate_alpha = sum(
            int(item["selection"]["target_alpha_count"]) for item in candidate_rows
        )
        aggregate_alpha_non_decreasing = candidate_alpha >= base_alpha
        aggregate_source = (
            str(attempt["candidate_left_source"])
            + str(attempt["candidate_right_source"])
        )
        aggregate_target = "".join(
            str(item["raw_rank0_target"]) for item in candidate_rows
        )
        aggregate_verdict = evaluate_rescue_pair(aggregate_source, aggregate_target)
        aggregate_emphasis = compare_emphasis_markup_preservation(
            aggregate_source, aggregate_target
        )
        accepted = bool(
            all(item["selection"]["accepted"] for item in candidate_rows)
            and aggregate_verdict.get("strictly_eligible") is True
            and aggregate_emphasis.get("passed") is True
            and aggregate_alpha_non_decreasing
        )
        attempt["candidate_rows"] = candidate_rows
        attempt["aggregate_selection"] = {
            "accepted": accepted,
            "base_target_alpha_count": base_alpha,
            "candidate_target_alpha_count": candidate_alpha,
            "target_alpha_non_decreasing": aggregate_alpha_non_decreasing,
            "mechanical_verdict": aggregate_verdict,
            "emphasis_markup": aggregate_emphasis,
        }
        if accepted:
            accepted_attempts.append(attempt)

    after_sha = _sha(database)
    if after_sha != before_sha:
        raise RuntimeError("read-only DOE mutated the canonical database")

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "read-only generic forward resegmentation at a short question tail "
            "followed by a blank paragraph boundary"
        ),
        "base_run_id": BASE_RUN_ID,
        "base_database_sha256": before_sha,
        "base_run_output_sha256": BASE_RUN_OUTPUT_SHA256,
        "source_text_sha256": SOURCE_TEXT_SHA256,
        "segment_count": len(rows),
        "trigger_contract": {
            "planner_contract": PLANNER_CONTRACT,
            "maximum_forward_nlp_tokens": MAX_FORWARD_NLP_TOKENS,
            "minimum_suffix_alpha_words": MIN_SUFFIX_ALPHA_WORDS,
            "maximum_prefix_chars": MAX_PREFIX_CHARS,
            "requires_same_split_context": True,
            "requires_left_at_soft_budget": True,
            "requires_right_question_deficit_only": True,
            "corpus_sequence_whitelist": False,
            "source_start_whitelist": False,
        },
        "generation": {
            "implementation": "opus-en-ru-ct2",
            "beam_size": BEAM_SIZE,
            "num_hypotheses": NUM_HYPOTHESES,
            "max_decoding_length": MAX_DECODING_LENGTH,
            "selected_rank": 0,
        },
        "attempt_count": len(attempts),
        "attempted_pairs": [
            [int(item["left_sequence"]), int(item["right_sequence"])]
            for item in attempts
        ],
        "accepted_count": len(accepted_attempts),
        "accepted_pairs": [
            [int(item["left_sequence"]), int(item["right_sequence"])]
            for item in accepted_attempts
        ],
        "attempts": attempts,
        "database_unchanged": after_sha == before_sha,
        "database_sha256_after": after_sha,
        "source_bytes_rewritten": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "evaluator_weakened": False,
        "n_best_cherry_picking": False,
        "promotion_allowed": False,
        "automatic_product_default_allowed": False,
    }
    evidence["evidence_sha256"] = _canonical_sha(evidence)
    destination = root / "run59-forward-paragraph-boundary-resegmentation-doe.json"
    destination.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "attempted_pairs": evidence["attempted_pairs"],
                "accepted_pairs": evidence["accepted_pairs"],
                "candidate_targets": [
                    [row["raw_rank0_target"] for row in item["candidate_rows"]]
                    for item in attempts
                ],
                "database_unchanged": evidence["database_unchanged"],
                "evidence_sha256": evidence["evidence_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
