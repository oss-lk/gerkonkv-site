from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from .core import CoreError, RocketDictCore
from .maintained_product_pipeline import advance_maintained_downstream
from .post_gate_pipeline import advance_post_gate_pipeline
from .product_preflight import build_product_preflight
from .product_run_state import initialize_product_run
from .quality_gate_execution import execute_quality_gates, require_quality_gate_pass
from .upstream_pipeline import advance_pre_gate_upstream
from .project import WorkbenchProject

CLI_SCHEMA = "rocketdict-workbench-product-run-cli/2"
DEFAULT_SET_NAME = "RocketDict Product output"


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
    opus_asset: Path | None = None,
    model_path: Path | None = None,
    cefrj_asset: Path | None = None,
    set_name: str = DEFAULT_SET_NAME,
    max_new_cards: int | None = None,
) -> dict[str, Any]:
    """Resume the maintained Product path as far as exact evidence allows.

    Stage8→19 keeps the existing verified Workbench binding/gate machinery. Once
    Stage19 is complete, Stage20→25 is executed exclusively by the maintained
    core implementation in a small number of core processes. The historical
    Workbench Stage20/arbitration/CEFR/pronunciation/examples/cards helpers are no
    longer on the active Product execution path.

    ``model_path`` is accepted only as a backwards-compatible alias for the new
    verified OPUS asset root. New callers should use ``opus_asset`` or configure
    ``ROCKETDICT_OPUS_ASSET_DIR``.
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

    effective_opus_asset = opus_asset or model_path
    maintained = advance_maintained_downstream(
        core,
        database,
        state_path,
        opus_asset=effective_opus_asset,
        cefrj_asset=cefrj_asset,
        set_name=set_name,
        max_new_cards=max_new_cards,
    )
    checkpoints.append({"phase": "maintained_stage20_25", "result": maintained})
    status = str(maintained.get("status") or "")
    if status == "blocked":
        return {
            "schema": CLI_SCHEMA,
            "status": "blocked",
            "blocked_phase": maintained.get("blocked_phase"),
            "required": maintained.get("required"),
            "reason": maintained.get("reason"),
            "checkpoints": checkpoints,
            "state_path": str(state_path),
        }
    if status == "progressed":
        return {
            "schema": CLI_SCHEMA,
            "status": "progressed",
            "blocked_phase": None,
            "checkpoints": checkpoints,
            "state_path": str(state_path),
        }
    if status != "product_complete_exported":
        raise RuntimeError(f"Maintained Product downstream returned unexpected status: {maintained}")
    return {
        "schema": CLI_SCHEMA,
        "status": "product_complete_exported",
        "checkpoints": checkpoints,
        "state_path": str(state_path),
        "export": maintained.get("export"),
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
    advance.add_argument(
        "--opus-asset",
        "--model-path",
        dest="opus_asset",
        type=Path,
        help="verified RocketDict OPUS asset root (legacy alias: --model-path)",
    )
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
                opus_asset=args.opus_asset,
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
