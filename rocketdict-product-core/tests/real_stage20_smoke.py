from __future__ import annotations

import json
import os
from pathlib import Path
import re

from rocketdict.database import connect, get_run
from rocketdict.sense_translation import get_stage20_revisions
from rocketdict_workbench.core import RocketDictCore


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_REAL_SMOKE_ROOT", "work/real-smoke")).resolve()
    database = root / "project" / "data" / "rocketdict.sqlite"
    if not database.is_file():
        raise FileNotFoundError(database)
    with connect(database, readonly=True) as connection:
        row = connection.execute(
            "SELECT id FROM stage_runs WHERE stage_number=19 AND status='completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("Real Stage20 smoke requires completed Stage19 evidence")
        stage19 = get_run(connection, int(row["id"]))
    expected_senses = int((stage19.get("output") or {}).get("lexical_sense_count") or 0)
    if expected_senses <= 0:
        raise RuntimeError(f"Stage19 has no lexical sense coverage: {stage19}")

    core = RocketDictCore()
    result = dict(
        core.api(
            database,
            "call",
            "product.stage20.run",
            "--params",
            json.dumps(
                {
                    "sense_induction_run_id": int(stage19["id"]),
                    "parameters": {
                        "beam_size": 12,
                        "num_hypotheses": 12,
                        "maximum_candidates_per_sense": 8,
                        "source_policy": "aligned-local-consensus",
                    },
                    "implementation": "contextual-lexical-opus-v3",
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            timeout=1800,
        )
    )
    if result.get("schema") != "rocketdict-product-stage20/1":
        raise RuntimeError(f"Unexpected Stage20 schema: {result}")
    if result.get("coverage_complete") is not True or result.get("all_selected_approved") is not True:
        raise RuntimeError(f"Stage20 did not complete/approve full sense coverage: {result}")
    if int(result.get("sense_count") or 0) != expected_senses:
        raise RuntimeError(f"Stage20 sense count drift: {result.get('sense_count')} != {expected_senses}")
    if int(result.get("selection_revision_count") or 0) != expected_senses:
        raise RuntimeError("Stage20 selection revision coverage is incomplete")
    if result.get("network_used") is not False or result.get("compute_type") != "float32":
        raise RuntimeError(f"Stage20 lost offline/float32 Product policy: {result}")

    revisions = get_stage20_revisions(database, int(result["sense_translation_run_id"]))
    if len(revisions) != expected_senses:
        raise RuntimeError(f"Persisted Stage20 revision coverage mismatch: {len(revisions)} != {expected_senses}")
    selected = []
    for revision in revisions:
        target = str(revision.get("translation_text") or "").strip()
        source = str(revision.get("normalized_lemma") or "").strip()
        if not target or not re.search(r"[А-Яа-яЁё]", target):
            raise RuntimeError(f"Stage20 selected non-Russian/empty primary: {revision}")
        if target.casefold() == source.casefold():
            raise RuntimeError(f"Stage20 selected identity primary: {revision}")
        if revision.get("approved") is not True:
            raise RuntimeError(f"Stage20 persisted unapproved primary: {revision}")
        selected.append(
            {
                "sense_id": int(revision["lexical_sense_id"]),
                "entry_id": int(revision["lexical_entry_id"]),
                "lemma": source,
                "translation": target,
                "selection_revision_id": int(revision["id"]),
                "provider_confidence": float(revision["provider_confidence"]),
                "context_compatibility": float(revision["context_compatibility"]),
                "approval_policy": str(revision["approval_policy"]),
            }
        )

    evidence = {
        "schema": "rocketdict-product-core-real-stage20-smoke/1",
        "status": "passed",
        "stage19_run_id": int(stage19["id"]),
        "stage20": result,
        "selected_primaries": selected,
        "full_sense_coverage": True,
        "real_opus": True,
        "fake_or_identity_mt": False,
        "network_used": False,
    }
    path = root / "real-stage20-smoke.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
