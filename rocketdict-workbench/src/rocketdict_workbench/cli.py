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
    default = sub.add_parser("default-config"); default.add_argument("root", type=Path); default.add_argument("--filename", default="production-default.json")
    campaign = sub.add_parser("campaign-create"); campaign.add_argument("root", type=Path); campaign.add_argument("definition", type=Path); campaign.add_argument("--pipeline", action="store_true")
    run = sub.add_parser("campaign-run"); run.add_argument("root", type=Path); run.add_argument("plan_id", type=int); run.add_argument("--max-new-trials", type=int)
    report = sub.add_parser("report"); report.add_argument("root", type=Path); report.add_argument("plan_id", type=int); report.add_argument("--destination", type=Path)
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
            _json({"configuration": str(project.save_default_configuration(filename=args.filename))}); return 0
        if args.command == "campaign-create":
            definition = json.loads(args.definition.read_text(encoding="utf-8"))
            if not isinstance(definition, dict): raise ValueError("campaign definition must be a JSON object")
            _json(project.create_research_campaign(definition, pipeline=args.pipeline)); return 0
        if args.command == "campaign-run":
            _json(core.run_experiment_plan(project.paths.database, args.plan_id, max_new_trials=args.max_new_trials)); return 0
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
