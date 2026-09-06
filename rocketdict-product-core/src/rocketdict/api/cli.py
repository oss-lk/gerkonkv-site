from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from rocketdict.database import bootstrap_database, project_summary
from . import operations as product_operations
from .registry import lab_manifest


def _default_lab_config() -> dict[str, Any]:
    manifest = lab_manifest(probe_runtime=False)
    stages = []
    for stage in manifest["stages"]:
        candidates = [
            row
            for row in stage["implementations"]
            if row.get("production_eligible") and not row.get("testing_only")
        ]
        if not candidates:
            continue
        selected = candidates[0]
        stages.append(
            {
                "stage_number": int(stage["number"]),
                "stage_key": str(stage["key"]),
                "enabled": True,
                "implementation": str(selected["implementation_key"]),
                "parameters": {
                    str(control["key"]): control.get("default")
                    for control in selected.get("controls") or []
                    if control.get("default") is not None
                },
            }
        )
    return {
        "format_version": "rocketdict-product-core-config/1",
        "source_language": "en",
        "target_language": "ru",
        "registry_hash": manifest["registry_hash"],
        "stages": stages,
    }


def _validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ValueError("config must be a JSON object")
    manifest = lab_manifest(probe_runtime=False)
    catalog = {
        (int(stage["number"]), str(row["implementation_key"]))
        for stage in manifest["stages"]
        for row in stage["implementations"]
    }
    errors: list[str] = []
    for row in config.get("stages") or []:
        if not isinstance(row, dict):
            errors.append("stage entry is not an object")
            continue
        key = (int(row.get("stage_number") or 0), str(row.get("implementation") or ""))
        if key not in catalog:
            errors.append(f"unregistered stage/implementation {key}")
    return {
        "schema": "rocketdict-product-core-config-validation/1",
        "valid": not errors,
        "errors": errors,
        "registry_hash": manifest["registry_hash"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rocketdict-core")
    parser.add_argument("database", type=Path)
    parser.add_argument("--compact", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("project")

    dashboard = commands.add_parser("lab-dashboard")
    dashboard.add_argument("--probe-runtime", action="store_true")

    commands.add_parser("lab-config-default")

    call = commands.add_parser("call")
    call.add_argument("operation")
    call.add_argument("--params", default="{}")
    return parser


def _dispatch(args: argparse.Namespace) -> Any:
    database = Path(args.database).expanduser().resolve()
    bootstrap_database(database)
    if args.command == "project":
        return project_summary(database)
    if args.command == "lab-dashboard":
        return lab_manifest(probe_runtime=bool(args.probe_runtime))
    if args.command == "lab-config-default":
        return _default_lab_config()
    if args.command == "call":
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--params is not valid JSON: {exc}") from exc
        if not isinstance(params, dict):
            raise ValueError("--params must decode to a JSON object")
        operation = str(args.operation)
        if operation == "lab.config.validate":
            return _validate_config(params.get("config"))
        fn = product_operations.OPERATIONS.get(operation)
        if fn is None:
            raise KeyError(f"Unknown Product Core operation {operation!r}")
        return fn(database=database, **params)
    raise AssertionError(args.command)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = _dispatch(args)
    except Exception as exc:
        payload = {
            "ok": False,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
        print(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":") if args.compact else None),
            file=sys.stderr,
        )
        return 2
    payload = {"ok": True, "data": data}
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if args.compact else None,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())