from __future__ import annotations

"""Research-only TC-big n-best audit for all 27 OPUS hard numeric failures.

The wide TC-big shadow proves the candidate is not safe as a global primary MT
model, but rank-0 still repairs a subset of immutable OPUS failures. This DOE
asks a narrower question: for only the units that already fail the maintained
OPUS Product numeric gate, does the exact pinned TC-big model contain additional
raw beam-6 hypotheses that are mechanically eligible for later semantic review?

It never changes Product policy or the Product database, never rewrites source
or target text, never injects literals/placeholders, and never treats mechanical
success as semantic acceptance or promotion authority.
"""

from collections import Counter
from difflib import SequenceMatcher
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import connect, get_document, get_run, get_run_items


HERE = Path(__file__).resolve().parent
FOCUSED_PATH = HERE / "real_translation_full_opticks_alternative_mt_feasibility.py"
FOCUSED_SPEC = importlib.util.spec_from_file_location("rocketdict_tc_big_focused", FOCUSED_PATH)
if FOCUSED_SPEC is None or FOCUSED_SPEC.loader is None:
    raise RuntimeError("cannot load pinned TC-big model helper")
FOCUSED = importlib.util.module_from_spec(FOCUSED_SPEC)
FOCUSED_SPEC.loader.exec_module(FOCUSED)

WIDE_PATH = HERE / "real_translation_full_opticks_tc_big_numeric_shadow.py"
WIDE_SPEC = importlib.util.spec_from_file_location("rocketdict_tc_big_wide", WIDE_PATH)
if WIDE_SPEC is None or WIDE_SPEC.loader is None:
    raise RuntimeError("cannot load TC-big fail-closed token helper")
WIDE = importlib.util.module_from_spec(WIDE_SPEC)
WIDE_SPEC.loader.exec_module(WIDE)

sys.path.insert(0, str(HERE))
from real_translation_nbest_feasibility import _verdict  # noqa: E402


SCHEMA = "rocketdict-full-opticks-tc-big-failure-nbest/1"
ORDINARY_SOURCES = frozenset({"nlp_sentence", "nlp_sentence_fragment", "nlp_sentence_group"})
EXPECTED_BASELINE_FAILURES = 27
BATCH_SIZE = 6
BEAM_SIZE = 6
NUM_HYPOTHESES = 6
MAX_DECODING_LENGTH = 512


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_failure_rows(
    *,
    database: Path,
    baseline: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected_run_id = int((baseline.get("stage12") or {}).get("translation_run_id") or 0)
    document_version_id = int(baseline.get("document_version_id") or 0)
    if selected_run_id <= 0 or document_version_id <= 0:
        raise RuntimeError("baseline lacks persisted Product Stage12/document identities")

    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        document = get_document(connection, document_version_id)
        run_rows = get_run_items(connection, selected_run_id, kind="translation_segment")

    selected_output = dict(selected_run.get("output") or {})
    if selected_output.get("selective_resegmentation_enabled") is not False:
        raise RuntimeError("TC-big failure n-best requires fail-closed Product baseline")
    if int(selected_output.get("selective_resegmentation_attempted_context_count") or 0) != 0:
        raise RuntimeError("fail-closed Product baseline unexpectedly attempted rescue")

    content = str(document["content_text"])
    by_sequence = {int(row["sequence_number"]): row for row in run_rows}
    failures = list(baseline.get("numeric_failures") or [])
    if len(failures) != EXPECTED_BASELINE_FAILURES:
        raise RuntimeError(
            f"expected {EXPECTED_BASELINE_FAILURES} baseline numeric failures, found {len(failures)}"
        )

    output: list[dict[str, Any]] = []
    seen: set[int] = set()
    for failure in sorted(failures, key=lambda row: int(row["planned_sequence"])):
        sequence = int(failure["planned_sequence"])
        if sequence in seen:
            raise RuntimeError(f"duplicate baseline failure sequence: {sequence}")
        seen.add(sequence)
        persisted = by_sequence.get(sequence)
        if persisted is None:
            raise RuntimeError(f"baseline failure sequence {sequence} is absent from selected Stage12")
        start = int(failure["source_start"])
        end = int(failure["source_end"])
        source = str(failure["source_text"])
        if (
            int(persisted["source_start"]) != start
            or int(persisted["source_end"]) != end
            or str(persisted.get("source_text") or "") != source
            or content[start:end] != source
        ):
            raise RuntimeError(f"immutable source lineage drift for failure sequence {sequence}")
        planner = dict(failure.get("planner") or {})
        source_class = str(planner.get("source") or "")
        if source_class not in ORDINARY_SOURCES:
            raise RuntimeError(
                f"baseline failure {sequence} is no longer ordinary linguistic MT: {source_class!r}"
            )
        persisted_target = str(persisted.get("target_text") or "")
        baseline_target = str(failure.get("product_target_text") or "")
        if persisted_target != baseline_target:
            raise RuntimeError(f"baseline target lineage drift for failure sequence {sequence}")
        output.append(
            {
                "sequence_number": sequence,
                "source_start": start,
                "source_end": end,
                "source_text": source,
                "source_class": source_class,
                "planner": planner,
                "baseline_target_text": baseline_target,
                "baseline_failure_is_isolated": bool(failure.get("numeric_failure_is_isolated")),
            }
        )
    return output, selected_run


def _translate_failure_batches(
    rows: list[dict[str, Any]],
    *,
    tokenizer: Any,
    model: Any,
    torch: Any,
    punctuation_parameters: dict[str, Any],
    length_parameters: dict[str, Any],
) -> list[dict[str, Any]]:
    eos_id = WIDE._resolve_token_id("eos_token_id", tokenizer=tokenizer, model=model)
    pad_id = WIDE._resolve_token_id("pad_token_id", tokenizer=tokenizer, model=model)
    max_positions = int(getattr(model.config, "max_position_embeddings", 0) or 0)
    if max_positions <= 0:
        raise RuntimeError("TC-big model does not publish max_position_embeddings")

    output: list[dict[str, Any]] = []
    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch_rows = rows[batch_start : batch_start + BATCH_SIZE]
        model_inputs = [FOCUSED.TARGET_PREFIX + str(row["source_text"]) for row in batch_rows]
        encoded = tokenizer(
            model_inputs,
            return_tensors="pt",
            padding=True,
            add_special_tokens=True,
            truncation=False,
        )
        attention = encoded.get("attention_mask")
        if attention is None:
            raise RuntimeError("TC-big tokenizer produced no attention mask for padded batch")
        input_counts = [int(value) for value in attention.sum(dim=1).tolist()]
        if any(value > max_positions for value in input_counts):
            raise RuntimeError(
                f"TC-big failure n-best input exceeds model context: {max(input_counts)} > {max_positions}"
            )
        unk_id = tokenizer.unk_token_id
        unknown_counts: list[int] = []
        for index, count in enumerate(input_counts):
            ids = encoded["input_ids"][index, :count]
            unknown_counts.append(
                int((ids == int(unk_id)).sum().item()) if unk_id is not None else 0
            )

        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                do_sample=False,
                num_beams=BEAM_SIZE,
                num_return_sequences=NUM_HYPOTHESES,
                max_length=MAX_DECODING_LENGTH,
                return_dict_in_generate=True,
                output_scores=True,
                renormalize_logits=True,
            )
        sequences = generated.sequences.detach().cpu()
        expected = len(batch_rows) * NUM_HYPOTHESES
        if int(sequences.shape[0]) != expected:
            raise RuntimeError(
                f"TC-big n-best generation cardinality drift: {int(sequences.shape[0])} != {expected}"
            )
        scores = getattr(generated, "sequences_scores", None)
        score_values = scores.detach().cpu().tolist() if scores is not None else [None] * expected

        for row_index, row in enumerate(batch_rows):
            source = str(row["source_text"])
            source_row = {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "target_text": None,
            }
            baseline_target = str(row["baseline_target_text"])
            baseline_verdict = _verdict(
                source_row,
                baseline_target,
                punctuation_parameters=punctuation_parameters,
                length_parameters=length_parameters,
            )
            if (baseline_verdict.get("numeric_symbol") or {}).get("passed") is not False:
                raise RuntimeError(
                    f"baseline failure sequence {row['sequence_number']} no longer fails numeric gate"
                )

            hypotheses: list[dict[str, Any]] = []
            for rank in range(NUM_HYPOTHESES):
                flat_index = row_index * NUM_HYPOTHESES + rank
                ids = [int(value) for value in sequences[flat_index].tolist()]
                significant = [value for value in ids if value != pad_id]
                terminated = bool(significant and significant[-1] == eos_id)
                ceiling_hit = len(significant) >= MAX_DECODING_LENGTH
                target = tokenizer.decode(ids, skip_special_tokens=True).strip()
                mechanical = _verdict(
                    source_row,
                    target,
                    punctuation_parameters=punctuation_parameters,
                    length_parameters=length_parameters,
                )
                numeric_mechanical_pass = bool(
                    (mechanical.get("numeric_symbol") or {}).get("passed") is True
                )
                strict_mechanical_pass = bool(mechanical.get("strictly_eligible") is True)
                numeric_fail_closed = bool(numeric_mechanical_pass and terminated and not ceiling_hit)
                strict_fail_closed = bool(strict_mechanical_pass and terminated and not ceiling_hit)
                hypotheses.append(
                    {
                        "rank": rank,
                        "score": (
                            float(score_values[flat_index])
                            if score_values[flat_index] is not None
                            else None
                        ),
                        "target_text": target,
                        "target_similarity_to_opus": SequenceMatcher(
                            None, baseline_target, target
                        ).ratio(),
                        "output_token_count": len(significant),
                        "terminated_with_eos": terminated,
                        "generation_ceiling_hit": ceiling_hit,
                        "numeric_pass_fail_closed": numeric_fail_closed,
                        "strict_pass_fail_closed": strict_fail_closed,
                        "mechanical_verdict": mechanical,
                    }
                )

            numeric_ranks = [hyp["rank"] for hyp in hypotheses if hyp["numeric_pass_fail_closed"]]
            strict_ranks = [hyp["rank"] for hyp in hypotheses if hyp["strict_pass_fail_closed"]]
            output.append(
                {
                    **row,
                    "input_token_count": input_counts[row_index],
                    "input_unknown_token_count": unknown_counts[row_index],
                    "model_max_position_embeddings": max_positions,
                    "input_truncated": False,
                    "baseline_verdict": baseline_verdict,
                    "hypotheses": hypotheses,
                    "numeric_pass_rank_count": len(numeric_ranks),
                    "numeric_pass_ranks": numeric_ranks,
                    "first_numeric_pass_rank": numeric_ranks[0] if numeric_ranks else None,
                    "strict_pass_rank_count": len(strict_ranks),
                    "strict_pass_ranks": strict_ranks,
                    "first_strict_pass_rank": strict_ranks[0] if strict_ranks else None,
                    "semantic_review_required": bool(strict_ranks),
                }
            )
    return output


def main() -> int:
    root = Path(
        os.environ.get(
            "ROCKETDICT_NUMERIC_STRESS_ROOT",
            "work/baseline/full-opticks-numeric-stress",
        )
    ).resolve()
    model_dir = Path(
        os.environ.get("ROCKETDICT_ALT_MT_MODEL_DIR", "work/alt-mt-model")
    ).resolve()
    baseline_path = root / "full-opticks-numeric-stress.json"
    database = root / "project" / "data" / "rocketdict.sqlite"
    for path in (baseline_path, database):
        if not path.is_file():
            raise RuntimeError(f"TC-big failure n-best input missing: {path}")

    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    if baseline.get("schema") != FOCUSED.BASELINE_SCHEMA:
        raise RuntimeError("TC-big failure n-best baseline schema drift")
    if baseline.get("source_sha256") != FOCUSED.OPTICKS_SHA256:
        raise RuntimeError("TC-big failure n-best Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != FOCUSED.PLANNER_CONTRACT:
        raise RuntimeError("TC-big failure n-best requires planner-v8 baseline")
    if int(baseline.get("numeric_bearing_unit_count") or -1) != 688:
        raise RuntimeError("TC-big failure n-best expected exactly 688 Product numeric units")
    if int(baseline.get("product_numeric_failure_count") or -1) != EXPECTED_BASELINE_FAILURES:
        raise RuntimeError("TC-big failure n-best baseline hard-failure count drift")

    database_sha_before = _sha(database)
    model_identity = FOCUSED._model_identity(model_dir)
    failures, selected_run = _load_failure_rows(database=database, baseline=baseline)
    source_class_counts = Counter(row["source_class"] for row in failures)

    quality = dict(baseline.get("quality_gate_parameters") or {})
    punctuation_parameters = dict(quality.get("punctuation") or {})
    length_parameters = dict(quality.get("length_ratio") or {})

    import torch
    from transformers import MarianMTModel, MarianTokenizer

    tokenizer = MarianTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = MarianMTModel.from_pretrained(
        str(model_dir), local_files_only=True, use_safetensors=True
    )
    model = model.to(device="cpu", dtype=torch.float32)
    model.eval()
    if str(model.config.model_type) != "marian":
        raise RuntimeError(f"unexpected TC-big model type: {model.config.model_type!r}")

    results = _translate_failure_batches(
        failures,
        tokenizer=tokenizer,
        model=model,
        torch=torch,
        punctuation_parameters=punctuation_parameters,
        length_parameters=length_parameters,
    )
    if len(results) != EXPECTED_BASELINE_FAILURES:
        raise RuntimeError("TC-big failure n-best result cardinality drift")

    rank0_numeric = [row["sequence_number"] for row in results if row["first_numeric_pass_rank"] == 0]
    any_numeric = [row["sequence_number"] for row in results if row["first_numeric_pass_rank"] is not None]
    rank0_strict = [row["sequence_number"] for row in results if row["first_strict_pass_rank"] == 0]
    any_strict = [row["sequence_number"] for row in results if row["first_strict_pass_rank"] is not None]
    higher_rank_only_strict = [
        row["sequence_number"]
        for row in results
        if row["first_strict_pass_rank"] is not None and row["first_strict_pass_rank"] > 0
    ]
    ceiling_hypotheses = sum(
        1 for row in results for hyp in row["hypotheses"] if hyp["generation_ceiling_hit"]
    )
    nonterminated_hypotheses = sum(
        1 for row in results for hyp in row["hypotheses"] if not hyp["terminated_with_eos"]
    )

    database_sha_after = _sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("TC-big failure n-best mutated immutable Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only failure-triggered TC-big beam-6 differential over all maintained OPUS "
            "hard numeric failures; mechanical candidates require complete semantic review"
        ),
        "promotion_allowed": False,
        "semantic_review_required": True,
        "automatic_semantic_selector": False,
        "product_baseline_changed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
        "corpus_specific_target_patches": False,
        "source_sha256": FOCUSED.OPTICKS_SHA256,
        "source_text_sha256": str(baseline.get("source_text_sha256") or ""),
        "planner_contract": FOCUSED.PLANNER_CONTRACT,
        "baseline_json_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "baseline_evidence_sha256": str(baseline.get("evidence_sha256") or ""),
        "selected_stage12_run_id": int((baseline.get("stage12") or {})["translation_run_id"]),
        "selected_stage12_output_sha256": str(selected_run.get("output_sha256") or ""),
        "database_sha256_before": database_sha_before,
        "database_sha256_after": database_sha_after,
        "database_mutated": False,
        "model": model_identity,
        "runtime": {
            "torch_version": str(torch.__version__),
            "torch_compute_dtype": "float32",
            "device": "cpu",
            "transformers_class": "MarianMTModel",
            "beam_size": BEAM_SIZE,
            "num_hypotheses": NUM_HYPOTHESES,
            "batch_size": BATCH_SIZE,
            "max_decoding_length": MAX_DECODING_LENGTH,
        },
        "baseline_failure_count": len(results),
        "source_class_counts": dict(sorted(source_class_counts.items())),
        "rank0_numeric_pass_count": len(rank0_numeric),
        "rank0_numeric_pass_sequences": rank0_numeric,
        "any_rank_numeric_pass_count": len(any_numeric),
        "any_rank_numeric_pass_sequences": any_numeric,
        "rank0_strict_pass_count": len(rank0_strict),
        "rank0_strict_pass_sequences": rank0_strict,
        "any_rank_strict_pass_count": len(any_strict),
        "any_rank_strict_pass_sequences": any_strict,
        "higher_rank_only_strict_pass_count": len(higher_rank_only_strict),
        "higher_rank_only_strict_pass_sequences": higher_rank_only_strict,
        "generation_ceiling_hypothesis_count": ceiling_hypotheses,
        "decoder_nonterminated_hypothesis_count": nonterminated_hypotheses,
        "cases": results,
    }
    payload["evidence_sha256"] = FOCUSED._canonical_sha(payload)
    output_path = root / "full-opticks-tc-big-failure-nbest.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "baseline_failure_count": len(results),
                "rank0_numeric_pass_count": len(rank0_numeric),
                "any_rank_numeric_pass_count": len(any_numeric),
                "rank0_strict_pass_count": len(rank0_strict),
                "any_rank_strict_pass_count": len(any_strict),
                "higher_rank_only_strict_pass_count": len(higher_rank_only_strict),
                "generation_ceiling_hypothesis_count": ceiling_hypotheses,
                "decoder_nonterminated_hypothesis_count": nonterminated_hypotheses,
                "database_mutated": False,
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
