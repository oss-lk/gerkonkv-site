from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .core import CoreError, RocketDictCore
from .project import WorkbenchProject
from .report import write_report


def _json(value) -> None:  # type: ignore[no-untyped-def]
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _core(args) -> RocketDictCore:  # type: ignore[no-untyped-def]
    paths = [Path(x) for x in (args.core_pythonpath or [])]
    return RocketDictCore(python=args.core_python, pythonpath=paths)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rocketdict-workbench", description="RocketDict product/research workbench")
    p.add_argument("--core-python", default=sys.executable, help="Python interpreter containing the real RocketDict core")
    p.add_argument("--core-pythonpath", action="append", default=[], help="Additional PYTHONPATH entry for unpacked RocketDict core")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    create = sub.add_parser("create"); create.add_argument("root", type=Path); create.add_argument("--name", required=True)
    status = sub.add_parser("status"); status.add_argument("root", type=Path); status.add_argument("--probe-runtime", action="store_true")
    imp = sub.add_parser("import"); imp.add_argument("root", type=Path); imp.add_argument("source", type=Path); imp.add_argument("--force-text", action="store_true")
    catalog = sub.add_parser("catalog"); catalog.add_argument("root", type=Path); catalog.add_argument("--probe-runtime", action="store_true"); catalog.add_argument("--output", type=Path)
    default = sub.add_parser("default-config"); default.add_argument("root", type=Path); default.add_argument("--filename", default="research-registry-default.json")
    product = sub.add_parser("product-profile", help="Create the strict Workbench Product Mode profile")
    product.add_argument("root", type=Path); product.add_argument("--source-kind", choices=("subtitle", "text"), default="subtitle"); product.add_argument("--output", type=Path)
    product_preflight = sub.add_parser("product-preflight", help="Freeze immutable source/core/registry/Product-profile identity before execution")
    product_preflight.add_argument("root", type=Path)
    product_preflight.add_argument("--source-sha256", help="Required when the project contains multiple imported sources")
    product_preflight.add_argument("--source-kind", choices=("subtitle", "text"), help="Optional assertion; otherwise inferred from the imported source")
    product_preflight.add_argument("--output", type=Path, help="Durable Product preflight JSON evidence path")
    cefr_asset = sub.add_parser("cefrj-install", help="Install the pinned CEFR-J 1.5 asset during explicit setup")
    cefr_asset.add_argument("root", type=Path); cefr_asset.add_argument("--destination", type=Path)
    cefr = sub.add_parser("cefrj-assess", help="Run Product CEFR-J-only assessment; no smoke/frequency fallback")
    cefr.add_argument("root", type=Path); cefr.add_argument("--sense-id", type=int, action="append", required=True); cefr.add_argument("--asset", type=Path); cefr.add_argument("--no-approve", action="store_true")
    pron = sub.add_parser("pronunciation-cmudict", help="Run exact CMUdict Product pronunciation; no generated fallback")
    pron.add_argument("root", type=Path); pron.add_argument("--entry-id", type=int, action="append", required=True); pron.add_argument("--include-russian-hint", action="store_true"); pron.add_argument("--no-approve", action="store_true")
    campaign = sub.add_parser("campaign-create"); campaign.add_argument("root", type=Path); campaign.add_argument("definition", type=Path); campaign.add_argument("--pipeline", action="store_true")
    run = sub.add_parser("campaign-run"); run.add_argument("root", type=Path); run.add_argument("plan_id", type=int); run.add_argument("--max-new-trials", type=int)
    report = sub.add_parser("report"); report.add_argument("root", type=Path); report.add_argument("plan_id", type=int); report.add_argument("--destination", type=Path)
    lexical = sub.add_parser("lexical-opus", help="Generate lexical OPUS n-best evidence and optionally run Stage20/Product downstream")
    lexical.add_argument("root", type=Path); lexical.add_argument("--model-path", type=Path, required=True)
    lexical.add_argument("--revision", required=True); lexical.add_argument("--archive-sha256", required=True); lexical.add_argument("--source-uri", required=True)
    lexical.add_argument("--sense-id", type=int, action="append", default=[]); lexical.add_argument("--beam-size", type=int, default=12); lexical.add_argument("--num-hypotheses", type=int, default=12)
    lexical.add_argument("--maximum-candidates", type=int, default=8); lexical.add_argument("--source-policy", default="aligned-local-consensus")
    lexical.add_argument("--apply-stage20", action="store_true")
    lexical.add_argument(
        "--arbitrate-primaries",
        action="store_true",
        help="After Stage20, approve the frozen lexical-provider primary for every generated sense; requires --apply-stage20",
    )
    lexical.add_argument("--arbitration-output", type=Path, help="Optional durable JSON evidence path for Stage20 primary arbitration")
    lexical.add_argument(
        "--continue-product",
        action="store_true",
        help="Resume strict Product downstream: Stage20 arbitration -> CEFR-J -> exact CMUdict -> sense-scoped examples; requires --apply-stage20",
    )
    lexical.add_argument("--cefrj-asset", type=Path, help="Pinned CEFR-J 1.5 CSV; defaults to project data/assets installation")
    lexical.add_argument("--product-state", type=Path, help="Durable resumable Product downstream state JSON")
    lexical.add_argument("--include-russian-pronunciation-hint", action="store_true")
    lexical.add_argument("--output", type=Path)
    serve = sub.add_parser("serve"); serve.add_argument("root", type=Path); serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=8765)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    core = _core(args)
    try:
        if args.command == "doctor":
            result = core.doctor(); _json(asdict(result)); return 0 if result.available else 3
        if args.command == "create":
            project = WorkbenchProject.create(args.root, name=args.name, core=core)
            _json({"project": project.metadata(), "database": str(project.paths.database), "core": asdict(core.doctor())}); return 0
        project = WorkbenchProject(args.root, core)
        if args.command == "status":
            _json(project.status(probe_runtime=args.probe_runtime)); return 0
        if args.command == "import":
            _json(project.import_source(args.source, force_text=args.force_text)); return 0
        if args.command == "catalog":
            payload = project.lab_catalog(probe_runtime=args.probe_runtime)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
                _json({"output": str(args.output.resolve()), "summary": payload.get("summary")})
            else:
                _json(payload)
            return 0
        if args.command == "default-config":
            _json({"configuration": str(project.save_default_configuration(filename=args.filename)), "mode": "research-registry-derived"}); return 0
        if args.command == "product-profile":
            from .product_profile import build_product_profile
            manifest = project.lab_catalog(probe_runtime=False)
            profile = build_product_profile(manifest, source_kind=args.source_kind)
            destination = args.output or (project.paths.configurations / f"product-{args.source_kind}.json")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(profile, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            _json({"profile": str(destination.resolve()), "schema": profile.get("schema"), "source_kind": profile.get("source_kind"), "quality_gates": [x.get("implementation") for x in profile.get("quality_gates") or []]}); return 0
        if args.command == "product-preflight":
            from .product_preflight import build_product_preflight, write_product_preflight
            payload = build_product_preflight(project, source_sha256=args.source_sha256, source_kind=args.source_kind)
            fingerprint = str(payload["identity"]["fingerprint"])
            destination = args.output or (project.paths.experiments / "product-preflight" / f"{fingerprint[:16]}.json")
            write_product_preflight(destination, payload)
            _json({
                "status": payload.get("status"),
                "preflight": str(destination.resolve()),
                "fingerprint": fingerprint,
                "source_sha256": payload["identity"]["source"]["sha256"],
                "source_kind": payload["identity"]["source_kind"],
                "registry_hash": payload["identity"]["registry_hash"],
                "profile_schema": payload["profile"].get("schema"),
                "policy_warnings": payload.get("policy_warnings") or [],
            }); return 0
        if args.command == "cefrj-install":
            from .product_cefr import install_cefrj_asset
            destination = args.destination or (project.paths.data / "assets" / "cefrj-vocabulary-profile-1.5.csv")
            _json(install_cefrj_asset(destination)); return 0
        if args.command == "cefrj-assess":
            from .product_cefr import assess_product_cefr
            asset = args.asset or (project.paths.data / "assets" / "cefrj-vocabulary-profile-1.5.csv")
            _json(assess_product_cefr(core, project.paths.database, args.sense_id, cefrj_asset=asset, approve=not args.no_approve)); return 0
        if args.command == "pronunciation-cmudict":
            from .product_pronunciation import generate_product_pronunciations
            _json(generate_product_pronunciations(core, project.paths.database, args.entry_id, include_russian_hint=args.include_russian_hint, approve=not args.no_approve)); return 0
        if args.command == "campaign-create":
            definition = json.loads(args.definition.read_text(encoding="utf-8"))
            if not isinstance(definition, dict): raise ValueError("campaign definition must be a JSON object")
            _json(project.create_research_campaign(definition, pipeline=args.pipeline)); return 0
        if args.command == "campaign-run":
            _json(core.run_experiment_plan(project.paths.database, args.plan_id, max_new_trials=args.max_new_trials)); return 0
        if args.command == "lexical-opus":
            from .lexical_opus import build_opus_lexical_snapshot, run_stage20_with_snapshot, write_provider_evidence
            if args.arbitrate_primaries and not args.apply_stage20:
                raise ValueError("--arbitrate-primaries requires --apply-stage20")
            if args.continue_product and not args.apply_stage20:
                raise ValueError("--continue-product requires --apply-stage20")
            if args.arbitration_output and not (args.arbitrate_primaries or args.continue_product):
                raise ValueError("--arbitration-output requires --arbitrate-primaries or --continue-product")
            if args.product_state and not args.continue_product:
                raise ValueError("--product-state requires --continue-product")
            provider = build_opus_lexical_snapshot(core, project.paths.database, model_path=args.model_path, revision=args.revision, archive_sha256=args.archive_sha256, source_uri=args.source_uri, sense_ids=args.sense_id, beam_size=args.beam_size, num_hypotheses=args.num_hypotheses, maximum_candidates_per_lemma=args.maximum_candidates)
            destination = args.output or (project.paths.experiments / "lexical-opus" / f"{provider['entries_sha256'][:16]}.json")
            write_provider_evidence(destination, provider)
            payload = {"provider_evidence": str(destination.resolve()), "summary": provider.get("summary"), "entries_sha256": provider.get("entries_sha256")}
            if args.apply_stage20:
                stage20 = run_stage20_with_snapshot(core, project.paths.database, provider, source_policy=args.source_policy, sense_ids=args.sense_id)
                payload["stage20"] = stage20
                if args.continue_product:
                    from .product_runner import resume_product_downstream
                    from .sense_translation_arbitration import write_arbitration_evidence
                    cefr_asset = args.cefrj_asset or (project.paths.data / "assets" / "cefrj-vocabulary-profile-1.5.csv")
                    product_state = args.product_state or destination.with_name(f"{destination.stem}.product-downstream.json")
                    downstream = resume_product_downstream(
                        core,
                        project.paths.database,
                        provider,
                        stage20,
                        cefrj_asset=cefr_asset,
                        state_path=product_state,
                        include_russian_pronunciation_hint=args.include_russian_pronunciation_hint,
                    )
                    payload["product_downstream"] = downstream
                    payload["product_state"] = str(product_state.resolve())
                    if args.arbitration_output:
                        write_arbitration_evidence(args.arbitration_output, downstream["stage20_arbitration"])
                        payload["stage20_arbitration_evidence"] = str(args.arbitration_output.resolve())
                elif args.arbitrate_primaries:
                    from .sense_translation_arbitration import arbitrate_lexical_primaries, write_arbitration_evidence
                    arbitration = arbitrate_lexical_primaries(core, project.paths.database, provider, stage20)
                    arbitration_destination = args.arbitration_output or destination.with_name(f"{destination.stem}.stage20-arbitration.json")
                    write_arbitration_evidence(arbitration_destination, arbitration)
                    payload["stage20_arbitration"] = arbitration
                    payload["stage20_arbitration_evidence"] = str(arbitration_destination.resolve())
            _json(payload); return 0
        if args.command == "serve":
            from .server import serve
            serve(project, host=args.host, port=args.port); return 0
        if args.command == "report":
            analytics = core.experiment_analytics(project.paths.database, args.plan_id)
            plan = core.experiment_plan(project.paths.database, args.plan_id)
            catalog = project.lab_catalog(probe_runtime=False)
            destination = args.destination or (project.paths.reports / f"experiment-{args.plan_id}")
            machine = core.export_experiment(project.paths.database, args.plan_id, project.paths.experiments / f"plan-{args.plan_id}")
            _json({"human": write_report(destination, analytics=analytics, plan=plan, lab_manifest=catalog), "machine": machine}); return 0
        raise AssertionError(args.command)
    except (CoreError, OSError, ValueError, RuntimeError) as exc:
        payload = {"status": "error", "type": type(exc).__name__, "error": str(exc)}
        if isinstance(exc, CoreError):
            payload.update({"command": exc.command, "stdout": exc.stdout[-4000:], "stderr": exc.stderr[-4000:]})
        _json(payload); return 2


if __name__ == "__main__":
    raise SystemExit(main())
