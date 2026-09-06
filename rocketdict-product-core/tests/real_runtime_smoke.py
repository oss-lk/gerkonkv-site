from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil

from rocketdict.database import connect, get_run_items
from rocketdict.downstream import downstream_snapshot
from rocketdict.evidence import CEFRJ_SHA256
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


def _positive_id(payload: dict, name: str, *, context: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool):
        raise RuntimeError(f"{context} returned boolean {name}: {value!r}")
    result = int(value or 0)
    if result <= 0:
        raise RuntimeError(f"{context} lacks positive durable {name}: {payload}")
    return result


def _assert_real_ru_translation(source: str, target: str, *, context: str) -> None:
    source = source.strip()
    target = target.strip()
    if not target:
        raise RuntimeError(f"{context} produced empty translation")
    if source.casefold() == target.casefold():
        raise RuntimeError(f"{context} produced identity translation: {source!r}")
    if not re.search(r"[А-Яа-яЁё]", target):
        raise RuntimeError(f"{context} contains no Cyrillic evidence: {target!r}")


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
    _positive_id(s8, "nlp_run_id", context="Stage8")
    if s8.get("schema") != "rocketdict-product-stage8/1":
        raise RuntimeError(f"Unexpected Stage8 schema: {s8}")
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
    _positive_id(s10, "context_run_id", context="Stage10")

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
    _positive_id(s12, "translation_run_id", context="Stage12")
    if s12.get("real_mt") is not True or s12.get("network_used") is not False:
        raise RuntimeError(f"Stage12 did not prove offline real MT lineage: {s12}")

    with connect(database, readonly=True) as connection:
        translation_items = get_run_items(connection, int(s12["translation_run_id"]))
    pairs = [
        (str(row.get("source_text") or "").strip(), str(row.get("target_text") or "").strip())
        for row in translation_items
        if str(row.get("target_text") or "").strip()
    ]
    if not pairs:
        raise RuntimeError("Stage12 persisted no translated target text")
    for source_text, target_text in pairs:
        _assert_real_ru_translation(source_text, target_text, context="Stage12")
    targets = [target for _source, target in pairs]

    s14 = _call(
        core,
        database,
        "product.stage14.run",
        translation_run_id=int(s12["translation_run_id"]),
        parameters={},
        implementation="glossary_refinement-current",
    )
    _positive_id(s14, "assembly_id", context="Stage14")
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
        _positive_id(result, "quality_gate_run_id", context=f"Stage15 {implementation}")
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
    _positive_id(s16, "translation_revision_id", context="Stage16")
    _positive_id(s16, "stage_result_id", context="Stage16")
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
    _positive_id(s17, "alignment_run_id", context="Stage17")
    _positive_id(s17, "stage_result_id", context="Stage17")
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
    for identity in ("extraction_run_id", "stage_result_id", "alignment_run_id", "nlp_run_id"):
        _positive_id(s18, identity, context="Stage18")
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
    if s19.get("schema") != "rocketdict-product-stage19/1":
        raise RuntimeError(f"Unexpected Stage19 schema: {s19}")
    _positive_id(s19, "sense_induction_run_id", context="Stage19")
    _positive_id(s19, "stage_result_id", context="Stage19")
    sense_count = int(s19.get("lexical_sense_count") or 0)
    if s19.get("coverage_complete") is not True or sense_count <= 0:
        raise RuntimeError(f"Stage19 sense induction failed: {s19}")

    # Stage20 uses real OPUS again, this time as contextual lexical/sense MT.
    # Defaults are production defaults (beam/n-best 12); this is a correctness
    # smoke, not a quality-downshifted alternate configuration.
    s20 = _call(
        core,
        database,
        "product.stage20.run",
        sense_induction_run_id=int(s19["sense_induction_run_id"]),
        parameters={},
        implementation="contextual-lexical-opus-v3",
    )
    _positive_id(s20, "sense_translation_run_id", context="Stage20")
    _positive_id(s20, "stage_result_id", context="Stage20")
    if s20.get("coverage_complete") is not True or s20.get("real_mt") is not True:
        raise RuntimeError(f"Stage20 real sense translation coverage failed: {s20}")
    if s20.get("network_used") is not False or s20.get("compute_type") != "float32":
        raise RuntimeError(f"Stage20 execution policy drifted: {s20}")
    results20 = list(s20.get("results") or [])
    if len(results20) != sense_count:
        raise RuntimeError(
            f"Stage20 sense coverage mismatch: {len(results20)} != {sense_count}"
        )
    sense_ids: list[int] = []
    entry_ids: list[int] = []
    for row in results20:
        sense_id = _positive_id(row, "sense_id", context="Stage20 result")
        entry_id = _positive_id(row, "entry_id", context="Stage20 result")
        _positive_id(row, "selection_revision_id", context="Stage20 result")
        _assert_real_ru_translation(str(row.get("lemma") or ""), str(row.get("translation") or ""), context=f"Stage20 sense {sense_id}")
        sense_ids.append(sense_id)
        entry_ids.append(entry_id)
    if len(set(sense_ids)) != sense_count:
        raise RuntimeError("Stage20 returned duplicate/missing sense identities")

    s21_by_entry: dict[int, dict] = {}
    s22_by_entry: dict[int, dict] = {}
    for entry_id in sorted(set(entry_ids)):
        s21 = _call(
            core,
            database,
            "product.stage21.run",
            lexical_entry_id=entry_id,
            parameters={"use_builtin_smoke_sources": False},
            implementation="cefrj-vocabulary-1.5",
        )
        _positive_id(s21, "cefr_assignment_id", context=f"Stage21 entry {entry_id}")
        if s21.get("source_sha256") != CEFRJ_SHA256:
            raise RuntimeError(f"Stage21 did not bind pinned CEFR-J: {s21}")
        if s21.get("builtin_smoke_used") is not False or s21.get("frequency_inference_used") is not False:
            raise RuntimeError(f"Stage21 used degraded evidence: {s21}")
        s21_by_entry[entry_id] = s21

        s22 = _call(
            core,
            database,
            "product.stage22.run",
            lexical_entry_id=entry_id,
            parameters={"enable_generated_fallback": False},
            implementation="cmudict-production",
        )
        _positive_id(s22, "pronunciation_id", context=f"Stage22 entry {entry_id}")
        if s22.get("generated_fallback") is not False:
            raise RuntimeError(f"Stage22 used generated pronunciation fallback: {s22}")
        s22_by_entry[entry_id] = s22

    s23_by_sense: dict[int, dict] = {}
    cards: list[dict] = []
    card_ids: list[int] = []
    for sense_id in sense_ids:
        s23 = _call(
            core,
            database,
            "product.stage23.run",
            lexical_sense_id=sense_id,
            parameters={"corpus_snapshots": []},
            implementation="examples-current",
        )
        _positive_id(s23, "example_run_id", context=f"Stage23 sense {sense_id}")
        if s23.get("scope_contract") != "stage23-sense-scope-v2" or s23.get("primary_missing") is not False:
            raise RuntimeError(f"Stage23 scope/example evidence failed: {s23}")
        if not list(s23.get("example_ids") or []):
            raise RuntimeError(f"Stage23 produced no examples for sense {sense_id}")
        s23_by_sense[sense_id] = s23

        s24 = _call(
            core,
            database,
            "product.stage24.run",
            lexical_sense_id=sense_id,
            parameters={},
            implementation="cards-current",
        )
        card_id = _positive_id(s24, "card_revision_id", context=f"Stage24 sense {sense_id}")
        if s24.get("complete") is not True or len(str(s24.get("content_sha256") or "")) != 64:
            raise RuntimeError(f"Stage24 card is incomplete: {s24}")
        cards.append(s24)
        card_ids.append(card_id)

    if len(card_ids) != sense_count or len(set(card_ids)) != sense_count:
        raise RuntimeError("Stage24 card coverage is not one immutable revision per sense")

    card_set = _call(
        core,
        database,
        "product.card-set.assemble",
        card_revision_ids=card_ids,
        set_name="RocketDict real-runtime smoke",
    )
    set_revision_id = _positive_id(card_set, "set_revision_id", context="Card set")
    if card_set.get("complete") is not True or int(card_set.get("card_count") or 0) != sense_count:
        raise RuntimeError(f"Card-set coverage failed: {card_set}")

    export_path = root / "product-export.json"
    s25 = _call(
        core,
        database,
        "product.stage25.run",
        set_revision_id=set_revision_id,
        parameters={"output_path": str(export_path)},
        implementation="export-json",
    )
    _positive_id(s25, "export_run_id", context="Stage25")
    if s25.get("complete") is not True or int(s25.get("card_count") or 0) != sense_count:
        raise RuntimeError(f"Stage25 export coverage failed: {s25}")
    if not export_path.is_file():
        raise RuntimeError(f"Stage25 export file is missing: {export_path}")
    exported = json.loads(export_path.read_text(encoding="utf-8"))
    if exported.get("schema") != "rocketdict-product-export/1":
        raise RuntimeError(f"Unexpected Product export schema: {exported.get('schema')}")
    if int(exported.get("card_count") or 0) != sense_count or len(exported.get("cards") or []) != sense_count:
        raise RuntimeError("Stage25 JSON export lost card/sense coverage")
    for card in exported["cards"]:
        _assert_real_ru_translation(
            str(card.get("lemma") or ""),
            str(card.get("translation") or ""),
            context=f"export card {card.get('lexical_sense_id')}",
        )
        if (card.get("pronunciation") or {}).get("generated_fallback") is not False:
            raise RuntimeError(f"Export card contains generated pronunciation fallback: {card}")
        if not list(card.get("examples") or []):
            raise RuntimeError(f"Export card lacks sense-scoped examples: {card}")

    downstream = downstream_snapshot(
        database,
        sense_translation_run_id=int(s20["sense_translation_run_id"]),
    )
    counts = downstream["counts"]
    expected_minimum = {
        "sense_translation_revisions": sense_count,
        "cefr_assignments": len(set(entry_ids)),
        "pronunciations": len(set(entry_ids)),
        "sense_examples": sense_count,
        "card_revisions": sense_count,
        "card_sets": 1,
    }
    for key, minimum in expected_minimum.items():
        if int(counts.get(key) or 0) < minimum:
            raise RuntimeError(f"Maintained downstream DB evidence incomplete for {key}: {counts}")

    evidence = {
        "schema": "rocketdict-product-core-real-runtime-smoke/2",
        "status": "passed",
        "scope": "real maintained-core source-to-Stage25 export smoke",
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
        "stage20": s20,
        "stage21_by_entry": s21_by_entry,
        "stage22_by_entry": s22_by_entry,
        "stage23_by_sense": s23_by_sense,
        "stage24_cards": cards,
        "card_set": card_set,
        "stage25": s25,
        "downstream_counts": counts,
        "export_sha256": s25["export_sha256"],
        "export_card_count": sense_count,
        "fake_or_identity_mt": False,
        "real_opus_required": True,
        "pinned_cefrj_required": True,
        "generated_pronunciation_fallback": False,
    }
    evidence_path = root / "real-runtime-smoke.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
