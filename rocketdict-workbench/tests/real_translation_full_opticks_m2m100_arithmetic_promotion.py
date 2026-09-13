from __future__ import annotations

"""One-shot diagnostic for the run58 -> M2M100 arithmetic promotion rejection."""

import json
import os
from pathlib import Path

from rocketdict.api.operations import run_stage12 as run_product_stage12
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.translation_m2m100_arithmetic_rescue_stage import M2M100_ARITHMETIC_RESCUE_CONTRACT
from rocketdict.translation_m2m100_arithmetic_rules import (
    M2M100_ARITHMETIC_SELECTOR_CONTRACT,
    M2M100_ARITHMETIC_TRIGGER_CONTRACT,
)

BASE_RUN_ID = 58
BASE_OUTPUT_SHA256 = "60349256eac118e9af7aa1366761342cd2041bb6ade4db04b45c78b46a8c6e5d"
BASE_PARAMETERS_SHA256 = "1cf60c7b582640c3923ea685ed329eb685a7b80e502e11507d99c752e6342315"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_SOURCE_START = 483234


def main() -> int:
    root = Path(os.environ["ROCKETDICT_M2M100_ARITHMETIC_PROMOTION_ROOT"]).resolve()
    database = Path(os.environ["ROCKETDICT_M2M100_ARITHMETIC_PROMOTION_DB"]).resolve()
    with connect(database, readonly=True) as connection:
        base = get_run(connection, BASE_RUN_ID)
        output = dict(base.get("output") or {})
        rows = get_run_items(connection, BASE_RUN_ID, kind="translation_segment")
        document = get_document(connection, int(output["document_version_id"]))
    if str(base.get("output_sha256") or "") != BASE_OUTPUT_SHA256:
        raise RuntimeError("run58 output identity drift")
    if str(base.get("parameters_sha256") or "") != BASE_PARAMETERS_SHA256:
        raise RuntimeError("run58 parameters identity drift")
    if str(document.get("text_sha256") or "") != SOURCE_TEXT_SHA256:
        raise RuntimeError("run58 source identity drift")
    matches = [row for row in rows if int(row.get("source_start") or -1) == EXPECTED_SOURCE_START]
    if len(matches) != 1:
        raise RuntimeError(f"arithmetic base-row cardinality drift: {len(matches)}")
    base_row = matches[0]

    parameters = dict(base.get("parameters") or {})
    parameters.update(
        {
            "enable_m2m100_arithmetic_rescue": True,
            "m2m100_arithmetic_rescue_contract": M2M100_ARITHMETIC_RESCUE_CONTRACT,
            "m2m100_arithmetic_selector_contract": M2M100_ARITHMETIC_SELECTOR_CONTRACT,
            "m2m100_arithmetic_trigger_contract": M2M100_ARITHMETIC_TRIGGER_CONTRACT,
        }
    )
    promoted = run_product_stage12(
        database=database,
        context_run_id=int(output["context_run_id"]),
        parameters=parameters,
        implementation="opus-en-ru-ct2",
    )
    diagnostic = {
        "base_translation_run_id": promoted.get("base_translation_run_id"),
        "base_translation_output_sha256": promoted.get("base_translation_output_sha256"),
        "attempt_count": promoted.get("m2m100_arithmetic_rescue_attempt_count"),
        "accepted_count": promoted.get("m2m100_arithmetic_rescue_accepted_count"),
        "rejected_count": promoted.get("m2m100_arithmetic_rescue_rejected_count"),
        "attempted_source_starts": promoted.get("m2m100_arithmetic_rescue_attempted_source_starts"),
        "accepted_source_starts": promoted.get("m2m100_arithmetic_rescue_accepted_source_starts"),
        "rejected": promoted.get("m2m100_arithmetic_rescue_rejected"),
        "base_source_text": base_row.get("source_text"),
        "base_target_text": base_row.get("target_text"),
        "runtime": promoted.get("m2m100_arithmetic_rescue_runtime"),
    }
    print(json.dumps({"m2m100_arithmetic_diagnostic": diagnostic}, ensure_ascii=False, sort_keys=True))
    root.mkdir(parents=True, exist_ok=True)
    (root / "m2m100-arithmetic-diagnostic.json").write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if int(promoted.get("m2m100_arithmetic_rescue_accepted_count") or 0) != 1:
        raise RuntimeError("diagnostic captured M2M100 arithmetic rank0 rejection")
    raise RuntimeError("diagnostic unexpectedly observed acceptance; restore promotion verifier")


if __name__ == "__main__":
    raise SystemExit(main())
