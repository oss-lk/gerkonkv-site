from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from .core import CoreError, RocketDictCore
from .final_product_pipeline import DEFAULT_SET_NAME, advance_final_product
from .post_gate_pipeline import advance_post_gate_pipeline
from .product_preflight import build_product_preflight
from .product_run_state import initialize_product_run
from .quality_gate_execution import execute_quality_gates, require_quality_gate_pass
from .unified_stage20 import continue_unified_stage20_through_stage23, run_unified_stage20
from .upstream_pipeline import advance_pre_gate_upstream
from .project import WorkbenchProject

CLI_SCHEMA = "rocketdict-workbench-product-run-cli/1"


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _core(args: argparse.Namespace) -> RocketDictCore:
    return RocketDictCore(
        python=args.core_python,
        pythonpath=[Path(value) for value in args.core_pythonpath],
    )


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Product run state is not a JSON object")
    return value


def _completed_upstream(state: dict[str, Any], stage_number: int) -> bool:
    record = (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {}).get(str(stage_number))
    return isinstance(record, dict) and record.get("status") == "completed"


def _quality_passed(state_path: Path) -> bool:
    try:
        require_quality_gate_pass(state_path)
    except (OSError, ValueError, RuntimeError):
        return False
    return True


def advance_product_run(
    core: RocketDictCore,
    database: Path,
    state_path: Path,
    *,
    model_path: Path | None = None,
    cefrj_asset: Path | None = None,
    set_name: str = DEFAULT_SET_NAME,
    max_new_cards: int | None = None,
) -> dict[str, Any]:
    """Resume as far as possible without weakening any evidence boundary.

    Missing external Product assets are reported as explicit blockers. Runtime
    contract/evidence failures remain exceptions: they are correctness failures, not
    ordinary asset prompts.
    """
    state_path = state_path.expanduser().resolve()
    database = database.expanduser().resolve()
    checkpoints: list[dict[str, Any]] = []
    state = _load_state(state_path)

    if not all(_completed_upstream(state, stage) for stage in (8, 10, 12, 14)):
        pre = advance_pre_gate_upstream(core, database, state_path)
        checkpoints.append({"phase": "pre_gate", "result": pre})
        if pre.get("status") != "pre_hard_gate_core_completed":
            return {
                "schema": CLI_SCHEMA,
                "status": "blocked",
                "blocked_phase": "pre_gate",
                "checkpoints": checkpoints,
                "state_path": str(state_path),
            }

    if not _quality_passed(state_path):
        quality = execute_quality_gates(core, database, state_path)
        checkpoints.append({"phase": "stage15_quality", "result": quality})
        if quality.get("status") != "passed":
            return {
                "schema": CLI_SCHEMA,
                "status": "blocked",
                "blocked_phase": "stage15_quality",
                "checkpoints": checkpoints,
                "state_path": str(state_path),
            }

    state = _load_state(state_path)
    if not _completed_upstream(state, 19):
        post = advance_post_gate_pipeline(core, database, state_path)
        checkpoints.append({"phase": "post_gate", "result": post})
        if post.get("status") != "stage19_completed":
            return {
                "schema": CLI_SCHEMA,
                "status": "blocked",
                "blocked_phase": "post_gate",
                "checkpoints": checkpoints,
                "state_path": str(state_path),
            }

    state = _load_state(state_path)
    downstream_status = str(((state.get("steps") or {}).get("stage20_downstream") or {}).get("status") or "")
    if downstream_status not in {"stage20_completed", "completed_through_stage23"}:
        if model_path is None:
            return {
                "schema": CLI_SCHEMA,
                "status": "blocked",
                "blocked_phase": "stage20",
                "required": "--model-path",
                "reason": "pinned_offline_opus_model_path_required",
                "checkpoints": checkpoints,
                "state_path": str(state_path),
            }
        stage20 = run_unified_stage20(core, database, state_path, model_path=model_path)
        checkpoints.append({"phase": "stage20", "result": stage20})

    state = _load_state(state_path)
    downstream_status = str(((state.get("steps") or {}).get("stage20_downstream") or {}).get("status") or "")
    if downstream_status != "completed_through_stage23":
        if cefrj_asset is None:
            return {
                "schema": CLI_SCHEMA,
                "status": "blocked",
                "blocked_phase": "stage20_through_stage23",
                "required": "--cefrj-asset",
                "reason": "pinned_cefrj_1_5_asset_required",
                "checkpoints": checkpoints,
                "state_path": str(state_path),
            }
        downstream = continue_unified_stage20_through_stage23(
            core,
            database,
            state_path,
            cefrj_asset=cefrj_asset,
        )
        checkpoints.append({"phase": "stage20_through_stage23", "result": downstream})

    final = advance_final_product(
        core,
        database,
        state_path,
        set_name=set_name,
        max_new_cards=max_new_cards,
    )
    checkpoints.append({"phase": "stage24_25", "result": final})
    if final.get("status") != "product_complete_exported":
        return {
            "schema": CLI_SCHEMA,
            "status": "progressed",
            "blocked_phase": "stage24_25" if final.get("status") != "stage24_partial" else None,
            "checkpoints": checkpoints,
            "state_path": str(state_path),
        }
    return {
        "schema": CLI_SCHEMA,
        "status": "product_complete_exported",
        "checkpoints": checkpoints,
        "state_path": str(state_path),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-product-run",
        description="Evidence-driven resumable RocketDict Product pipeline",
    )
    p.add_argument("--core-python", default=sys.executable)
    p.add_argument("--core-pythonpath", action="append", default=[])
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Freeze Product preflight and create/resume unified run state")
    init.add_argument("root", type=Path)
    init.add_argument("--source-sha256")
    init.add_argument("--source-kind", choices=("subtitle", "text"))
    init.add_argument("--state", type=Path)

    advance = sub.add_parser("advance", help="Resume all Product phases as far as proven inputs/contracts allow")
    advance.add_argument("root", type=Path)
    advance.add_argument("--state", type=Path, required=True)
    advance.add_argument("--model-path", type=Path)
    advance.add_argument("--cefrj-asset", type=Path)
    advance.add_argument("--set-name", default=DEFAULT_SET_NAME)
    advance.add_argument("--max-new-cards", type=int)

    status = sub.add_parser("status", help="Print durable unified Product state")
    status.add_argument("root", type=Path)
    status.add_argument("--state", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    core = _core(args)
    try:
        project = WorkbenchProject(args.root, core)
        if args.command == "status":
            _json(_load_state(args.state.expanduser().resolve()))
            return 0
        if args.command == "init":
            preflight = build_product_preflight(
                project,
                source_sha256=args.source_sha256,
                source_kind=args.source_kind,
            )
            fingerprint = str(preflight["identity"]["fingerprint"])
            state_path = args.state or (
                project.paths.experiments / "product-run" / f"{fingerprint[:16]}.json"
            )
            state = initialize_product_run(
                core,
                project.paths.database,
                preflight,
                state_path=state_path,
            )
            _json(
                {
                    "schema": CLI_SCHEMA,
                    "status": state.get("status"),
                    "state_path": str(Path(state_path).expanduser().resolve()),
                    "preflight_fingerprint": fingerprint,
                    "core": asdict(core.doctor()),
                }
            )
            return 0
        if args.command == "advance":
            result = advance_product_run(
                core,
                project.paths.database,
                args.state,
                model_path=args.model_path,
                cefrj_asset=args.cefrj_asset,
                set_name=args.set_name,
                max_new_cards=args.max_new_cards,
            )
            _json(result)
            return 0 if result.get("status") in {"product_complete_exported", "progressed", "blocked"} else 2
        raise AssertionError(args.command)
    except (CoreError, OSError, ValueError, RuntimeError) as exc:
        payload: dict[str, Any] = {
            "schema": CLI_SCHEMA,
            "status": "error",
            "type": type(exc).__name__,
            "error": str(exc),
        }
        if isinstance(exc, CoreError):
            payload.update(
                {
                    "command": exc.command,
                    "stdout": exc.stdout[-4000:],
                    "stderr": exc.stderr[-4000:],
                }
            )
        _json(payload)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
