from __future__ import annotations

"""One-shot migration of full-Opticks evidence to actual Product Stage12 output.

The old numeric-stress harness reconstructed Product-shaped planner/MT behavior
outside the Product run. Stage12 planner v5 now has narrow structural-label
execution, so acceptance evidence must consume the actual persisted Product
Stage12 translation segments. The invoking workflow commits only after compile
and dependency-light checks pass. Remove this helper after migration.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUMERIC = "rocketdict-workbench/tests/real_translation_full_opticks_numeric_stress.py"
PRIME = "rocketdict-workbench/tests/real_translation_full_opticks_prime_stress.py"
NBEST = "rocketdict-workbench/tests/real_translation_full_opticks_nbest_escalation.py"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


# Numeric stress v3: actual full Product Stage12 is the baseline.
replace_once(
    NUMERIC,
    'SCHEMA = "rocketdict-full-opticks-numeric-stress/2"',
    'SCHEMA = "rocketdict-full-opticks-numeric-stress/3"',
)
replace_once(NUMERIC, "            timeout=1800,", "            timeout=7200,")
replace_once(
    NUMERIC,
    "from rocketdict.runtime import OpusTranslator\n",
    "from rocketdict.runtime import OpusTranslator\n"
    "from rocketdict.structural_labels import STRUCTURAL_LABEL_CONTRACT\n",
)

numeric = read(NUMERIC)
main_start = numeric.index("def main() -> int:")
block_start = numeric.index("    with connect(database, readonly=True) as connection:\n", main_start)
block_end = numeric.index("    baseline_rows: list[dict[str, Any]] = []\n", block_start)
old_block = numeric[block_start:block_end]
if "_production_rank0_targets" not in old_block or "rank0_by_sequence" not in old_block:
    raise RuntimeError("numeric-stress old Product-shaped baseline block drifted")
new_block = r'''    stage12 = _call(
        core,
        database,
        "product.stage12.run",
        context_run_id=int(stage10["context_run_id"]),
        parameters=params12,
        implementation=impl12,
    )
    if stage12.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError("Full Opticks Product Stage12 planner contract drift")
    if stage12.get("structural_label_contract") != STRUCTURAL_LABEL_CONTRACT:
        raise RuntimeError("Full Opticks Product Stage12 structural-label contract drift")
    if int(stage12.get("structural_label_unit_count") or -1) != 108:
        raise RuntimeError(
            "Pinned Opticks Product Stage12 must isolate exactly 108 supported block structural labels"
        )
    if int(stage12.get("structural_label_escalated_unit_count") or -1) != 3:
        raise RuntimeError(
            "Pinned Opticks Product Stage12 expected exactly three Observation-1 beam12 escalations"
        )

    translation_run_id = int(stage12["translation_run_id"])
    with connect(database, readonly=True) as connection:
        document = get_document(connection, document_version_id)
        translation_items = get_run_items(
            connection, translation_run_id, kind="translation_segment"
        )
    content = str(document["content_text"])
    if not translation_items:
        raise RuntimeError("Full Opticks Product Stage12 persisted no translation segments")

    units: list[dict[str, Any]] = []
    cursor = 0
    for expected_sequence, item in enumerate(translation_items):
        sequence = int(item["sequence_number"])
        start = int(item["source_start"])
        end = int(item["source_end"])
        source_text = str(item["source_text"])
        target_text = str(item.get("target_text") or "")
        payload = dict(item.get("payload") or {})
        if sequence != expected_sequence:
            raise RuntimeError("Full Opticks Product Stage12 sequence numbering drift")
        if start != cursor or end <= start or content[start:end] != source_text:
            raise RuntimeError("Full Opticks Product Stage12 source coverage is not byte-exact")
        if not target_text.strip():
            raise RuntimeError(f"Full Opticks Product Stage12 emitted empty target at {sequence}")
        units.append(
            {
                "start": start,
                "end": end,
                "text": source_text,
                "target_text": target_text,
                "payload": payload,
                "metadata": dict(payload.get("planner") or {}),
            }
        )
        cursor = end
    if cursor != len(content) or "".join(str(unit["text"]) for unit in units) != content:
        raise RuntimeError("Full Opticks Product Stage12 does not cover the immutable source exactly")
    if len(units) != int(stage12.get("segment_count") or -1):
        raise RuntimeError("Full Opticks Product Stage12 output segment count drift")

    numeric_units = [
        (index, unit)
        for index, unit in enumerate(units)
        if extract_numeric_literals(str(unit["text"]))
    ]
    if not numeric_units:
        raise RuntimeError("Full Opticks Product Stage12 produced no numeric-bearing units")

    max_unit_tokens = max(
        int((unit.get("metadata") or {}).get("token_count") or 0)
        for _, unit in numeric_units
    )
    max_decoding_length = max(128, max(preferred_tokens, max_unit_tokens) * 8)
    database_sha_after_product_stage12 = _sha_file(database)
'''
numeric = numeric[:block_start] + new_block + numeric[block_end:]
write(NUMERIC, numeric)

replace_once(
    NUMERIC,
    '''    for sequence, unit in numeric_units:
        baseline = rank0_by_sequence[sequence]
        target = str(baseline["target_text"])
        source_row = _row(unit, sequence)
''',
    '''    for sequence, unit in numeric_units:
        target = str(unit["target_text"])
        product_payload = dict(unit.get("payload") or {})
        source_row = _row(unit, sequence)
''',
)
replace_once(
    NUMERIC,
    '''            "rank0_target_text": target,
            "rank0_score": baseline.get("rank0_score"),
            "production_table_composite": bool(baseline["production_table_composite"]),
            "table_stage12_contract": baseline.get("table_stage12_contract"),
            "table_logical_group_count": baseline.get("table_logical_group_count"),
''',
    '''            "product_target_text": target,
            "product_selected_rank": int(product_payload.get("selected_rank") or 0),
            "production_table_composite": isinstance(product_payload.get("table"), dict),
            "production_structural_label": isinstance(product_payload.get("structural_label"), dict),
            "table_stage12_contract": (
                (product_payload.get("table") or {}).get("stage12_contract")
                if isinstance(product_payload.get("table"), dict)
                else None
            ),
            "table_logical_group_count": (
                len((product_payload.get("table") or {}).get("logical_groups") or [])
                if isinstance(product_payload.get("table"), dict)
                else None
            ),
            "structural_label_contract": (
                (product_payload.get("structural_label") or {}).get("contract")
                if isinstance(product_payload.get("structural_label"), dict)
                else None
            ),
''',
)
replace_once(
    NUMERIC,
    '''    ordinary_failures = [
        row for row in numeric_failures if not bool(row["production_table_composite"])
    ]
    retry_generated = _translate_batches(
''',
    '''    ordinary_failures = [
        row
        for row in numeric_failures
        if not bool(row["production_table_composite"])
        and not bool(row["production_structural_label"])
    ]
    translator = OpusTranslator(device="cpu", compute_type="float32")
    retry_generated = _translate_batches(
''',
)
replace_once(
    NUMERIC,
    '"similarity_to_rank0": _similarity(str(failed["rank0_target_text"]), target),',
    '"similarity_to_product_target": _similarity(str(failed["product_target_text"]), target),',
)
replace_once(
    NUMERIC,
    '''        if failed["production_table_composite"]:
''',
    '''        if failed["production_table_composite"] or failed["production_structural_label"]:
''',
)
replace_once(
    NUMERIC,
    '"retry_skip_reason": "composite_table_must_not_be_retranslated_as_prose",',
    '''"retry_skip_reason": (
                        "composite_table_must_not_be_retranslated_as_prose"
                        if failed["production_table_composite"]
                        else "structural_label_uses_narrow_product_selector_not_generic_nbest"
                    ),''',
)
replace_once(
    NUMERIC,
    '''    database_sha_after_inference = _sha_file(database)
    if database_sha_after_inference != database_sha_before_inference:
        raise RuntimeError("Numeric stress inference mutated the Stage8/10 research database")
''',
    '''    database_sha_after_research_inference = _sha_file(database)
    if database_sha_after_research_inference != database_sha_after_product_stage12:
        raise RuntimeError("Numeric stress research inference mutated the persisted Product Stage12 database")
''',
)
replace_once(
    NUMERIC,
    '''    table_numeric_failures = [
        row for row in numeric_failures if row["production_table_composite"]
    ]
''',
    '''    table_numeric_failures = [
        row for row in numeric_failures if row["production_table_composite"]
    ]
    structural_label_numeric_units = [
        row for row in baseline_rows if row["production_structural_label"]
    ]
    structural_label_numeric_failures = [
        row for row in numeric_failures if row["production_structural_label"]
    ]
    if len(structural_label_numeric_units) != 108:
        raise RuntimeError("Full Opticks numeric audit did not observe all 108 Product structural-label units")
    if structural_label_numeric_failures:
        raise RuntimeError("Product structural-label selector emitted a numeric-integrity failure")
''',
)
replace_once(
    NUMERIC,
    '''        "purpose": "full contiguous Opticks numeric-integrity stress for exact Product Stage12 rank-0 semantics and ordinary-unit raw n-best retry",
''',
    '''        "purpose": "full contiguous Opticks numeric-integrity audit over actual persisted Product Stage12 output plus ordinary-unit research n-best retry",
        "actual_product_stage12_execution": True,
''',
)
replace_once(
    NUMERIC,
    '''        "stage12_planner_contract": PLANNER_CONTRACT,
        "table_stage12_contract": TABLE_STAGE12_CONTRACT,
        "stage12_parameters": params12,
''',
    '''        "stage12_planner_contract": PLANNER_CONTRACT,
        "structural_label_contract": STRUCTURAL_LABEL_CONTRACT,
        "table_stage12_contract": TABLE_STAGE12_CONTRACT,
        "stage12_parameters": params12,
        "stage12": {
            "translation_run_id": translation_run_id,
            "segment_count": int(stage12.get("segment_count") or 0),
            "source_character_sum": int(stage12.get("source_character_sum") or 0),
            "structural_label_unit_count": int(stage12.get("structural_label_unit_count") or 0),
            "structural_label_escalated_unit_count": int(stage12.get("structural_label_escalated_unit_count") or 0),
            "structural_label_model_request_count": int(stage12.get("structural_label_model_request_count") or 0),
            "table_block_count": int(stage12.get("table_block_count") or 0),
            "table_logical_group_count": int(stage12.get("table_logical_group_count") or 0),
            "model_request_count": int(stage12.get("model_request_count") or 0),
            "real_mt": stage12.get("real_mt") is True,
        },
''',
)
replace_once(
    NUMERIC,
    '''        "table_model_request_count": table_model_request_count,
        "rank0_numeric_failure_count": len(numeric_failures),
        "rank0_numeric_failure_sequences": [int(row["planned_sequence"]) for row in numeric_failures],
''',
    '''        "table_numeric_model_request_count": sum(
            int(row.get("table_logical_group_count") or 0) for row in table_numeric_units
        ),
        "structural_label_numeric_bearing_unit_count": len(structural_label_numeric_units),
        "structural_label_numeric_failure_count": len(structural_label_numeric_failures),
        "product_numeric_failure_count": len(numeric_failures),
        "product_numeric_failure_sequences": [int(row["planned_sequence"]) for row in numeric_failures],
''',
)
replace_once(
    NUMERIC,
    '''        "retry_scope": "ordinary_units_only; composite tables retain production logical-rank0 semantics",
''',
    '''        "retry_scope": "ordinary_units_only; Product composite tables and structural labels are never retranslated by generic n-best",
''',
)
replace_once(
    NUMERIC,
    '''        "database_sha256_before_inference": database_sha_before_inference,
        "database_sha256_after_inference": database_sha_after_inference,
''',
    '''        "database_sha256_after_product_stage12": database_sha_after_product_stage12,
        "database_sha256_after_research_inference": database_sha_after_research_inference,
''',
)
replace_once(
    NUMERIC,
    '''                "rank0_numeric_failure_count": len(numeric_failures),
''',
    '''                "product_numeric_failure_count": len(numeric_failures),
                "structural_label_numeric_bearing_unit_count": len(structural_label_numeric_units),
                "structural_label_numeric_failure_count": len(structural_label_numeric_failures),
''',
)

# No stale variables or schema-v2 wording may survive in executable v3 main.
numeric = read(NUMERIC)
for forbidden in (
    "rank0_by_sequence",
    "database_sha_before_inference",
    "table_model_request_count",
    'SCHEMA = "rocketdict-full-opticks-numeric-stress/2"',
):
    if forbidden in numeric[numeric.index("def main() -> int:"):]:
        raise RuntimeError(f"numeric-stress v3 retained stale main symbol {forbidden!r}")

# Prime audit consumes v3 baseline. Prime units cannot be structural labels, so
# its narrow Product-shaped translation helper remains equivalent for that scope.
replace_once(
    PRIME,
    'BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/2"',
    'BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"',
)
replace_once(
    PRIME,
    "same\nrank-0 OPUS semantics as Product Stage12, including the maintained composite\nASCII-table path.\n",
    "same\nordinary/table OPUS semantics as Product Stage12. Structural-label units do not\ncontain numeric prime notation and therefore are outside this audit scope.\n",
)

# Generic n-best consumes only ordinary v3 Product failures.
replace_once(
    NBEST,
    'BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/2"',
    'BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"',
)
replace_once(
    NBEST,
    '''        if row.get("production_table_composite") is not True
        and row.get("numeric_failure_is_isolated") is True
''',
    '''        if row.get("production_table_composite") is not True
        and row.get("production_structural_label") is not True
        and row.get("numeric_failure_is_isolated") is True
''',
)
replace_once(
    NBEST,
    '''            "rank0_target_text": str(row["rank0_target_text"]),
''',
    '''            "product_baseline_target_text": str(row["product_target_text"]),
''',
)

# Compile-time/static contract checks.
assert 'SCHEMA = "rocketdict-full-opticks-numeric-stress/3"' in read(NUMERIC)
assert 'BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"' in read(PRIME)
assert 'BASE_SCHEMA = "rocketdict-full-opticks-numeric-stress/3"' in read(NBEST)
assert "actual_product_stage12_execution" in read(NUMERIC)
assert "production_structural_label" in read(NUMERIC)
print("Full Opticks Product Stage12 evidence v3 migration applied", flush=True)
