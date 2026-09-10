from __future__ import annotations

"""Research-only TC-big shadow over every ordinary numeric-bearing Opticks unit.

This experiment asks whether the pinned ``opus-mt-tc-big-en-zle`` checkpoint is
credible as a broader ordinary-text MT candidate, rather than merely a fallback
for the 27 current OPUS failures.  It replays the exact full-Opticks Product
artifact and translates every numeric-bearing *linguistic* Stage12 unit with
TC-big rank-0 beam-6 generation.

Source-owned block identifiers, structural labels with their narrow Product
selector, and ASCII-table composites are deliberately not retranslated: this is
an ordinary-MT model differential, not a rewrite of already-proven document
structure contracts.  The Product database is read-only, no source/target text
is repaired, and mechanical improvements never authorize promotion without
semantic review and a later full-corpus shadow.
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
from rocketdict.numeric_integrity import extract_numeric_literals


HERE = Path(__file__).resolve().parent
FOCUSED_PATH = HERE / "real_translation_full_opticks_alternative_mt_feasibility.py"
SPEC = importlib.util.spec_from_file_location("rocketdict_tc_big_focused", FOCUSED_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load pinned TC-big focused DOE helper")
FOCUSED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FOCUSED)

sys.path.insert(0, str(HERE))
from real_translation_nbest_feasibility import _verdict  # noqa: E402

SCHEMA = "rocketdict-full-opticks-tc-big-numeric-shadow/1"
ORDINARY_SOURCES = frozenset(
    {"nlp_sentence", "nlp_sentence_fragment", "nlp_sentence_group"}
)
SOURCE_OWNED_OR_SPECIAL = frozenset(
    {"structural_label", "block_section_identifier", "ascii_table"}
)
BATCH_SIZE = 12
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 512


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _single_token_id(value: Any, *, name: str, source: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise RuntimeError(f"TC-big {name} from {source} is not scalar: {value!r}")
        value = value[0]
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"TC-big {name} from {source} is invalid: {value!r}") from exc


def _resolve_token_id(name: str, *, tokenizer: Any, model: Any) -> int:
    values: list[tuple[str, int]] = []
    for source, raw in (
        ("tokenizer", getattr(tokenizer, name, None)),
        ("generation_config", getattr(getattr(model, "generation_config", None), name, None)),
        ("model_config", getattr(getattr(model, "config", None), name, None)),
    ):
        value = _single_token_id(raw, name=name, source=source)
        if value is not None:
            values.append((source, value))
    if not values:
        raise RuntimeError(f"TC-big runtime publishes no {name}")
    distinct = {value for _source, value in values}
    if len(distinct) != 1:
        raise RuntimeError(f"TC-big {name} disagreement: {values!r}")
    return values[0][1]


def _selected_rows(database: Path, baseline: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    selected_run_id = int((baseline.get("stage12") or {}).get("translation_run_id") or 0)
    document_version_id = int(baseline.get("document_version_id") or 0)
    if selected_run_id <= 0 or document_version_id <= 0:
        raise RuntimeError("baseline lacks persisted Product Stage12/document identities")
    with connect(database, readonly=True) as connection:
        selected_run = get_run(connection, selected_run_id)
        rows = get_run_items(connection, selected_run_id, kind="translation_segment")
        document = get_document(connection, document_version_id)
        primary_run_id = int((selected_run.get("output") or {}).get("primary_translation_run_id") or 0)
        if primary_run_id <= 0:
            raise RuntimeError("selected Stage12 lacks immutable primary lineage")
        primary_run = get_run(connection, primary_run_id)
    output = dict(selected_run.get("output") or {})
    if output.get("selective_resegmentation_enabled") is not False:
        raise RuntimeError("TC-big shadow requires fail-closed selected Product Stage12")
    if int(output.get("selective_resegmentation_attempted_context_count") or 0) != 0:
        raise RuntimeError("fail-closed selected Product Stage12 unexpectedly attempted rescue")
    if str(primary_run.get("output_sha256") or "") != str(
        output.get("primary_translation_output_sha256") or ""
    ):
        raise RuntimeError("selected Stage12 primary output identity drift")
    content = str(document["content_text"])
    cursor = 0
    ordered = sorted(rows, key=lambda row: int(row["sequence_number"]))
    for sequence, row in enumerate(ordered):
        if int(row["sequence_number"]) != sequence:
            raise RuntimeError("selected Stage12 sequence drift")
        start = int(row["source_start"])
        end = int(row["source_end"])
        source = str(row.get("source_text") or "")
        if start != cursor or end <= start or content[start:end] != source:
            raise RuntimeError("selected Stage12 source coverage is not byte-exact")
        cursor = end
    if cursor != len(content):
        raise RuntimeError("selected Stage12 does not cover immutable Opticks source")
    return selected_run, ordered, content


def _translate_batches(rows: list[dict[str, Any]], *, tokenizer: Any, model: Any, torch: Any) -> list[dict[str, Any]]:
    eos_id = _resolve_token_id("eos_token_id", tokenizer=tokenizer, model=model)
    pad_id = _resolve_token_id("pad_token_id", tokenizer=tokenizer, model=model)
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
                f"TC-big shadow input exceeds model context: {max(input_counts)} > {max_positions}"
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
        if int(sequences.shape[0]) != len(batch_rows):
            raise RuntimeError("TC-big shadow generation cardinality drift")
        scores = getattr(generated, "sequences_scores", None)
        score_values = scores.detach().cpu().tolist() if scores is not None else [None] * len(batch_rows)

        for index, (row, tensor) in enumerate(zip(batch_rows, sequences, strict=True)):
            ids = [int(value) for value in tensor.tolist()]
            significant = [value for value in ids if value != pad_id]
            terminated = bool(significant and significant[-1] == eos_id)
            ceiling_hit = len(significant) >= MAX_DECODING_LENGTH
            target = tokenizer.decode(ids, skip_special_tokens=True).strip()
            output.append(
                {
                    "row": row,
                    "target_text": target,
                    "score": (
                        float(score_values[index])
                        if score_values[index] is not None
                        else None
                    ),
                    "input_token_count": input_counts[index],
                    "input_unknown_token_count": unknown_counts[index],
                    "output_token_count": len(significant),
                    "terminated_with_eos": terminated,
                    "generation_ceiling_hit": ceiling_hit,
                    "model_max_position_embeddings": max_positions,
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
            raise RuntimeError(f"TC-big numeric shadow input missing: {path}")

    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    if baseline.get("schema") != FOCUSED.BASELINE_SCHEMA:
        raise RuntimeError("TC-big numeric shadow baseline schema drift")
    if baseline.get("source_sha256") != FOCUSED.OPTICKS_SHA256:
        raise RuntimeError("TC-big numeric shadow Opticks source identity drift")
    if baseline.get("stage12_planner_contract") != FOCUSED.PLANNER_CONTRACT:
        raise RuntimeError("TC-big numeric shadow requires planner-v8 baseline")
    if int(baseline.get("numeric_bearing_unit_count") or -1) != 688:
        raise RuntimeError("TC-big numeric shadow expected exactly 688 Product numeric units")
    if int(baseline.get("product_numeric_failure_count") or -1) != 27:
        raise RuntimeError("TC-big numeric shadow expected 27 baseline hard failures")

    database_sha_before = _sha(database)
    model_identity = FOCUSED._model_identity(model_dir)
    selected_run, selected_rows, content = _selected_rows(database, baseline)
    del content

    numeric_rows: list[dict[str, Any]] = []
    source_class_counts: Counter[str] = Counter()
    for row in selected_rows:
        source = str(row.get("source_text") or "")
        if not extract_numeric_literals(source):
            continue
        payload = dict(row.get("payload") or {})
        planner = dict(payload.get("planner") or {})
        source_class = str(planner.get("source") or "")
        source_class_counts[source_class] += 1
        numeric_rows.append(
            {
                "sequence_number": int(row["sequence_number"]),
                "source_start": int(row["source_start"]),
                "source_end": int(row["source_end"]),
                "source_text": source,
                "baseline_target_text": str(row.get("target_text") or ""),
                "source_class": source_class,
                "planner": planner,
            }
        )
    if len(numeric_rows) != 688:
        raise RuntimeError(f"replayed numeric unit count drift: {len(numeric_rows)} != 688")
    unknown_classes = set(source_class_counts) - ORDINARY_SOURCES - SOURCE_OWNED_OR_SPECIAL
    if unknown_classes:
        raise RuntimeError(f"TC-big numeric shadow found unknown planner sources: {sorted(unknown_classes)}")
    ordinary_rows = [row for row in numeric_rows if row["source_class"] in ORDINARY_SOURCES]
    special_rows = [row for row in numeric_rows if row["source_class"] in SOURCE_OWNED_OR_SPECIAL]
    if len(ordinary_rows) + len(special_rows) != len(numeric_rows):
        raise RuntimeError("TC-big numeric shadow scope accounting drift")

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

    translated = _translate_batches(
        ordinary_rows, tokenizer=tokenizer, model=model, torch=torch
    )
    if len(translated) != len(ordinary_rows):
        raise RuntimeError("TC-big numeric shadow result cardinality drift")

    records: list[dict[str, Any]] = []
    baseline_numeric_failures = 0
    tc_fail_closed_numeric_failures = 0
    baseline_strict_failures = 0
    tc_fail_closed_strict_failures = 0
    numeric_improvements: list[int] = []
    numeric_regressions: list[int] = []
    strict_improvements: list[int] = []
    strict_regressions: list[int] = []
    ceiling_sequences: list[int] = []
    nonterminated_sequences: list[int] = []

    for generated in translated:
        row = dict(generated["row"])
        source = str(row["source_text"])
        baseline_target = str(row["baseline_target_text"])
        tc_target = str(generated["target_text"])
        source_row = {
            "sequence_number": int(row["sequence_number"]),
            "source_start": int(row["source_start"]),
            "source_end": int(row["source_end"]),
            "source_text": source,
            "target_text": None,
        }
        baseline_verdict = _verdict(
            source_row,
            baseline_target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        tc_verdict = _verdict(
            source_row,
            tc_target,
            punctuation_parameters=punctuation_parameters,
            length_parameters=length_parameters,
        )
        baseline_numeric_pass = bool(
            (baseline_verdict.get("numeric_symbol") or {}).get("passed") is True
        )
        tc_mechanical_numeric_pass = bool(
            (tc_verdict.get("numeric_symbol") or {}).get("passed") is True
        )
        ceiling_hit = bool(generated["generation_ceiling_hit"])
        terminated = bool(generated["terminated_with_eos"])
        tc_numeric_pass = bool(tc_mechanical_numeric_pass and terminated and not ceiling_hit)
        baseline_strict = bool(baseline_verdict.get("strictly_eligible") is True)
        tc_mechanical_strict = bool(tc_verdict.get("strictly_eligible") is True)
        tc_strict = bool(tc_mechanical_strict and terminated and not ceiling_hit)
        sequence = int(row["sequence_number"])

        if not baseline_numeric_pass:
            baseline_numeric_failures += 1
        if not tc_numeric_pass:
            tc_fail_closed_numeric_failures += 1
        if not baseline_strict:
            baseline_strict_failures += 1
        if not tc_strict:
            tc_fail_closed_strict_failures += 1
        if not baseline_numeric_pass and tc_numeric_pass:
            numeric_improvements.append(sequence)
        if baseline_numeric_pass and not tc_numeric_pass:
            numeric_regressions.append(sequence)
        if not baseline_strict and tc_strict:
            strict_improvements.append(sequence)
        if baseline_strict and not tc_strict:
            strict_regressions.append(sequence)
        if ceiling_hit:
            ceiling_sequences.append(sequence)
        if not terminated:
            nonterminated_sequences.append(sequence)

        records.append(
            {
                **row,
                "baseline_target_text": baseline_target,
                "tc_big_target_text": tc_target,
                "tc_big_score": generated["score"],
                "target_similarity": SequenceMatcher(None, baseline_target, tc_target).ratio(),
                "input_token_count": int(generated["input_token_count"]),
                "input_unknown_token_count": int(generated["input_unknown_token_count"]),
                "output_token_count": int(generated["output_token_count"]),
                "terminated_with_eos": terminated,
                "generation_ceiling_hit": ceiling_hit,
                "baseline_verdict": baseline_verdict,
                "tc_big_mechanical_verdict": tc_verdict,
                "baseline_numeric_pass": baseline_numeric_pass,
                "tc_big_numeric_pass_fail_closed": tc_numeric_pass,
                "baseline_strict": baseline_strict,
                "tc_big_strict_fail_closed": tc_strict,
            }
        )

    # All 27 Product numeric failures are ordinary linguistic rows in the pinned
    # baseline. If this changes, model comparison scope must be reconsidered.
    if baseline_numeric_failures != 27:
        raise RuntimeError(
            f"ordinary replay no longer accounts for all 27 Product numeric failures: {baseline_numeric_failures}"
        )

    database_sha_after = _sha(database)
    if database_sha_after != database_sha_before:
        raise RuntimeError("TC-big numeric shadow mutated immutable Product database")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "purpose": (
            "research-only candidate-primary differential over every ordinary numeric-bearing "
            "Product Stage12 unit; source-owned/special structure remains on maintained Product contracts"
        ),
        "promotion_allowed": False,
        "semantic_review_required": True,
        "full_corpus_shadow_required_before_model_promotion": True,
        "product_baseline_changed": False,
        "source_rewriting": False,
        "target_rewriting": False,
        "placeholders": False,
        "post_translation_literal_injection": False,
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
        "numeric_bearing_unit_count": len(numeric_rows),
        "planner_source_class_counts": dict(sorted(source_class_counts.items())),
        "ordinary_numeric_unit_count": len(ordinary_rows),
        "source_owned_or_special_numeric_unit_count": len(special_rows),
        "source_owned_or_special_policy": "retained_from_product_not_retranslated",
        "baseline_ordinary_numeric_failure_count": baseline_numeric_failures,
        "tc_big_fail_closed_numeric_failure_count": tc_fail_closed_numeric_failures,
        "numeric_improvement_count": len(numeric_improvements),
        "numeric_improvement_sequences": numeric_improvements,
        "numeric_regression_count": len(numeric_regressions),
        "numeric_regression_sequences": numeric_regressions,
        "baseline_ordinary_strict_failure_count": baseline_strict_failures,
        "tc_big_fail_closed_strict_failure_count": tc_fail_closed_strict_failures,
        "strict_improvement_count": len(strict_improvements),
        "strict_improvement_sequences": strict_improvements,
        "strict_regression_count": len(strict_regressions),
        "strict_regression_sequences": strict_regressions,
        "generation_ceiling_count": len(ceiling_sequences),
        "generation_ceiling_sequences": ceiling_sequences,
        "decoder_nonterminated_count": len(nonterminated_sequences),
        "decoder_nonterminated_sequences": nonterminated_sequences,
        "records": records,
    }
    payload["evidence_sha256"] = FOCUSED._canonical_sha(payload)
    output_path = root / "full-opticks-tc-big-numeric-shadow.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "ordinary_numeric_unit_count": len(ordinary_rows),
                "baseline_numeric_failures": baseline_numeric_failures,
                "tc_big_fail_closed_numeric_failures": tc_fail_closed_numeric_failures,
                "numeric_improvements": len(numeric_improvements),
                "numeric_regressions": len(numeric_regressions),
                "strict_improvements": len(strict_improvements),
                "strict_regressions": len(strict_regressions),
                "generation_ceiling_count": len(ceiling_sequences),
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
