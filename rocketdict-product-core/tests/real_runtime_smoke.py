from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil

from rocketdict.database import connect, get_run_items
from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_preflight import build_product_preflight
from rocketdict_workbench.project import WorkbenchProject


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


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_REAL_SMOKE_ROOT", "work/real-smoke")).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    source = root / "source.txt"
    source.write_text(
        "Light passes through a glass prism and forms a spectrum",
        encoding="utf-8",
    )

    project_root = root / "project"
    core = RocketDictCore()
    project = WorkbenchProject.create(project_root, name="real-runtime-smoke", core=core)
    imported = project.import_source(source)
    preflight = build_product_preflight(project, source_kind="text")
    if preflight.get("status") != "ready":
        raise RuntimeError(f"Product preflight did not become ready: {preflight}")

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
    if s8.get("coverage_complete") is not True or int(s8.get("token_count") or 0) <= 0:
        raise RuntimeError(f"Stage8 real NLP coverage failed: {s8}")

    s10 = _call(
        core,
        database,
        "product.stage10.run",
        nlp_run_id=int(s8["nlp_run_id"]),
        parameters={},
        implementation="structural-entity-term-discourse-pronoun-v1",
    )
    s12 = _call(
        core,
        database,
        "product.stage12.run",
        context_run_id=int(s10["context_run_id"]),
        parameters={
            "allow_download": False,
            "device": "cpu",
            "compute_type": "float32",
            "run_assemble": True,
        },
        implementation="opus-en-ru-ct2",
    )
    if s12.get("real_mt") is not True:
        raise RuntimeError(f"Stage12 did not prove real MT lineage: {s12}")

    with connect(database, readonly=True) as connection:
        translation_items = get_run_items(connection, int(s12["translation_run_id"]))
    targets = [str(row.get("target_text") or "").strip() for row in translation_items]
    targets = [value for value in targets if value]
    if not targets:
        raise RuntimeError("Stage12 persisted no translated target text")
    if not any(re.search(r"[А-Яа-яЁё]", value) for value in targets):
        raise RuntimeError(f"Stage12 targets contain no Cyrillic evidence: {targets}")
    if all(value.casefold() == str(row.get("source_text") or "").strip().casefold() for value, row in zip(targets, translation_items)):
        raise RuntimeError("Stage12 appears to have produced identity translation")

    s14 = _call(
        core,
        database,
        "product.stage14.run",
        translation_run_id=int(s12["translation_run_id"]),
        parameters={},
        implementation="glossary_refinement-current",
    )
    if s14.get("real_mt_lineage") is not True:
        raise RuntimeError(f"Stage14 lost real MT lineage: {s14}")

    gates = {}
    for operation, implementation in (
        ("product.stage15.numeric-symbol", "rocketdict-numeric-symbol-preservation"),
        ("product.stage15.punctuation", "rocketdict-punctuation-preservation"),
        ("product.stage15.length-ratio", "rocketdict-length-ratio-proxy"),
    ):
        result = _call(
            core,
            database,
            operation,
            assembly_id=int(s14["assembly_id"]),
            parameters={},
            implementation=implementation,
        )
        gates[implementation] = result
        if result.get("passed") is not True:
            raise RuntimeError(f"Real smoke hard gate failed: {implementation}: {result}")

    s16 = _call(
        core,
        database,
        "product.stage16.run",
        assembly_id=int(s14["assembly_id"]),
        parameters={},
        implementation="approve-if-clean-finalization",
    )
    if s16.get("approved") is not True:
        raise RuntimeError(f"Stage16 did not approve clean translation: {s16}")

    s17 = _call(
        core,
        database,
        "product.stage17.run",
        translation_revision_id=int(s16["translation_revision_id"]),
        parameters={},
        implementation="deterministic-structural-global",
    )
    if s17.get("coverage_complete") is not True:
        raise RuntimeError(f"Stage17 alignment coverage failed: {s17}")

    s18 = _call(
        core,
        database,
        "product.stage18.run",
        alignment_run_id=int(s17["alignment_run_id"]),
        parameters={},
        implementation="workbench-aligned-content-pos-v4",
    )
    if s18.get("coverage_complete") is not True or int(s18.get("uncovered_token_count") or 0) != 0:
        raise RuntimeError(f"Stage18 lexical coverage failed: {s18}")
    if int(s18.get("lexical_entry_count") or 0) <= 0:
        raise RuntimeError(f"Stage18 produced no lexical entries: {s18}")

    s19 = _call(
        core,
        database,
        "product.stage19.run",
        extraction_run_id=int(s18["extraction_run_id"]),
        parameters={},
        implementation="deterministic-context-target-graph",
    )
    if s19.get("coverage_complete") is not True or int(s19.get("sense_count") or 0) <= 0:
        raise RuntimeError(f"Stage19 sense induction failed: {s19}")

    evidence = {
        "schema": "rocketdict-product-core-real-runtime-smoke/1",
        "status": "passed",
        "source": {
            "sha256": imported["sha256"],
            "document_version_id": document_version_id,
            "selected_format": imported["interpretation"]["selected_format"],
        },
        "preflight_fingerprint": preflight["identity"]["fingerprint"],
        "core": preflight["identity"]["core"],
        "registry_hash": preflight["identity"]["registry_hash"],
        "stage8": s8,
        "stage10": s10,
        "stage12": s12,
        "stage12_targets": targets,
        "stage14": s14,
        "stage15": gates,
        "stage16": s16,
        "stage17": s17,
        "stage18": s18,
        "stage19": s19,
        "fake_or_identity_mt": False,
        "real_opus_required": True,
    }
    evidence_path = root / "real-runtime-smoke.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
