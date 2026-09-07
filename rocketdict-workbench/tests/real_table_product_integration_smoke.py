from __future__ import annotations

"""Real production-lineage smoke for maintained ASCII-table translation.

This is intentionally narrower than the ordinary Stage8→25 smoke: it exercises
the table-specific risk surface end to end through lexical/sense evidence using
real spaCy and the pinned OPUS model.  Generic Stage20→25 behavior is already
covered by the ordinary real Product smoke.
"""

import json
import os
from pathlib import Path
import shutil

from rocketdict.database import connect, get_run_items
from rocketdict.lexical import lexical_snapshot
from rocketdict.translation_stage import PLANNER_CONTRACT
from rocketdict.table_stage12 import TABLE_STAGE12_CONTRACT
from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_preflight import build_product_preflight
from rocketdict_workbench.project import WorkbenchProject

SCHEMA = "rocketdict-real-table-product-integration-smoke/1"


def _call(core: RocketDictCore, database: Path, operation: str, **params):  # type: ignore[no-untyped-def]
    return dict(
        core.api(
            database,
            "call",
            operation,
            "--params",
            json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            timeout=1800,
        )
    )


def _positive(payload: dict, name: str) -> int:
    value = int(payload.get(name) or 0)
    if value <= 0:
        raise RuntimeError(f"missing positive {name}: {payload}")
    return value


def main() -> int:
    root = Path(
        os.environ.get("ROCKETDICT_REAL_TABLE_SMOKE_ROOT", "work/real-table-product-smoke")
    ).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    table = (
        "-------------------+-------------\n"
        "Angle of Incidence | Diameter    \n"
        "      on Air.      | of Ring.    \n"
        "-------------------+-------------\n"
        "Blue               | 23          \n"
        "Green              | 42          \n"
        "Red                | 77          \n"
        "-------------------+-------------\n"
    )
    source_path = root / "table.txt"
    source_path.write_text(table, encoding="utf-8")

    core = RocketDictCore()
    project = WorkbenchProject.create(root / "project", name="real-table-product-smoke", core=core)
    imported = project.import_source(source_path)
    preflight = build_product_preflight(project, source_kind="text")
    if preflight.get("status") != "ready":
        raise RuntimeError(f"table Product preflight not ready: {preflight}")
    database = project.paths.database
    document_version_id = int(imported["interpretation"]["document_version_id"])

    s8 = _call(
        core,
        database,
        "product.stage8.run",
        document_version_id=document_version_id,
        parameters={},
        implementation="en-sm",
    )
    s10 = _call(
        core,
        database,
        "product.stage10.run",
        nlp_run_id=_positive(s8, "nlp_run_id"),
        parameters={},
        implementation="structural-entity-term-discourse-pronoun-v1",
    )
    s12 = _call(
        core,
        database,
        "product.stage12.run",
        context_run_id=_positive(s10, "context_run_id"),
        parameters={
            "allow_download": False,
            "device": "cpu",
            "compute_type": "float32",
            "run_assemble": True,
        },
        implementation="opus-en-ru-ct2",
    )
    translation_run_id = _positive(s12, "translation_run_id")
    if s12.get("planner_contract") != PLANNER_CONTRACT:
        raise RuntimeError(f"table Stage12 planner contract drift: {s12}")
    if s12.get("table_stage12_contract") != TABLE_STAGE12_CONTRACT:
        raise RuntimeError(f"table Stage12 structural contract drift: {s12}")
    if int(s12.get("table_block_count") or 0) != 1:
        raise RuntimeError(f"table Stage12 did not detect exactly one table: {s12}")
    if int(s12.get("table_logical_group_count") or 0) < 5:
        raise RuntimeError(f"table Stage12 logical grouping unexpectedly small: {s12}")
    if s12.get("real_mt") is not True or s12.get("network_used") is not False:
        raise RuntimeError(f"table Stage12 lost real offline MT evidence: {s12}")

    with connect(database, readonly=True) as connection:
        translated = get_run_items(connection, translation_run_id, kind="translation_segment")
    if len(translated) != 1:
        raise RuntimeError(f"table source must remain one Product translation segment: {len(translated)}")
    segment = translated[0]
    if str(segment.get("source_text") or "") != table:
        raise RuntimeError("table Stage12 segment source is not byte-exact")
    target = str(segment.get("target_text") or "")
    for literal in ("23", "42", "77"):
        if literal not in target:
            raise RuntimeError(f"table Stage12 lost source-owned literal {literal}: {target}")
    if target.count("|") != table.count("|") or target.count("\n") != table.count("\n"):
        raise RuntimeError("table Stage12 changed source-owned geometry")
    payload = dict(segment.get("payload") or {})
    if payload.get("composite_real_mt") is not True:
        raise RuntimeError(f"table Stage12 segment lacks composite real-MT evidence: {payload}")
    logical_groups = list(((payload.get("table") or {}).get("logical_groups") or []))
    if len(logical_groups) != int(s12["table_logical_group_count"]):
        raise RuntimeError("table Stage12 persisted logical-group cardinality drift")
    if any(int(group.get("selected_rank") or 0) != 0 for group in logical_groups):
        raise RuntimeError("Product table Stage12 used non-rank0 model hypothesis")

    s14 = _call(
        core,
        database,
        "product.stage14.run",
        translation_run_id=translation_run_id,
        parameters={},
        implementation="glossary_refinement-current",
    )
    assembly_id = _positive(s14, "assembly_id")
    gates: dict[str, dict] = {}
    for operation, implementation in (
        ("product.stage15.numeric-symbol", "rocketdict-numeric-symbol-preservation"),
        ("product.stage15.punctuation", "rocketdict-punctuation-preservation"),
        ("product.stage15.length-ratio", "rocketdict-length-ratio-proxy"),
    ):
        result = _call(
            core,
            database,
            operation,
            assembly_id=assembly_id,
            parameters={},
            implementation=implementation,
        )
        gates[implementation] = result
        if result.get("passed") is not True:
            raise RuntimeError(f"table Product hard gate failed: {implementation}: {result}")

    s16 = _call(
        core,
        database,
        "product.stage16.run",
        assembly_id=assembly_id,
        parameters={},
        implementation="approve-if-clean-finalization",
    )
    s17 = _call(
        core,
        database,
        "product.stage17.run",
        translation_revision_id=_positive(s16, "translation_revision_id"),
        parameters={},
        implementation="deterministic-structural-global",
    )
    s18 = _call(
        core,
        database,
        "product.stage18.run",
        alignment_run_id=_positive(s17, "alignment_run_id"),
        parameters={},
        implementation="workbench-aligned-content-pos-v5",
    )
    if s18.get("coverage_complete") is not True or int(s18.get("uncovered_token_count") or 0) != 0:
        raise RuntimeError(f"table Stage18 lexical coverage failed: {s18}")
    table_scoped = int(s18.get("table_scoped_target_evidence_count") or 0)
    if table_scoped <= 0 or table_scoped != int(s18.get("occurrence_count") or 0):
        raise RuntimeError(f"not every table lexical occurrence used logical target evidence: {s18}")

    snapshot = lexical_snapshot(database, extraction_run_id=_positive(s18, "extraction_run_id"))
    occurrences = list(snapshot.get("occurrences") or [])
    if not occurrences:
        raise RuntimeError("table Stage18 persisted no lexical occurrences")
    whole_table_target = target.strip()
    for occurrence in occurrences:
        evidence = dict(occurrence.get("evidence") or {})
        if evidence.get("target_evidence_scope") != "table_logical_group":
            raise RuntimeError(f"table lexical occurrence escaped logical target scope: {occurrence}")
        local_target = str(occurrence.get("target_evidence_text") or "").strip()
        if not local_target or local_target == whole_table_target:
            raise RuntimeError(f"table lexical target evidence is not local: {occurrence}")

    s19 = _call(
        core,
        database,
        "product.stage19.run",
        extraction_run_id=_positive(s18, "extraction_run_id"),
        parameters={},
        implementation="deterministic-context-target-graph",
    )
    if s19.get("coverage_complete") is not True or int(s19.get("lexical_sense_count") or 0) <= 0:
        raise RuntimeError(f"table Stage19 sense coverage failed: {s19}")

    evidence = {
        "schema": SCHEMA,
        "status": "passed",
        "source_sha256": imported["sha256"],
        "planner_contract": s12["planner_contract"],
        "table_stage12_contract": s12["table_stage12_contract"],
        "table_block_count": s12["table_block_count"],
        "logical_group_count": s12["table_logical_group_count"],
        "hard_gates": gates,
        "stage18": s18,
        "stage19": s19,
        "lexical_occurrence_count": len(occurrences),
        "target_evidence_scopes": sorted(
            {str((row.get("evidence") or {}).get("target_evidence_scope")) for row in occurrences}
        ),
        "no_synthetic_target_repair": True,
        "real_opus_rank0_only": True,
    }
    output = root / "real-table-product-integration-smoke.json"
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
