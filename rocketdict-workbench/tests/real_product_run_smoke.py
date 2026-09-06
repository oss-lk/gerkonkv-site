from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import traceback
from typing import Callable, TypeVar

from rocketdict_workbench.core import RocketDictCore
from rocketdict_workbench.product_preflight import build_product_preflight
from rocketdict_workbench.product_run_cli import advance_product_run
from rocketdict_workbench.product_run_state import initialize_product_run
from rocketdict_workbench.project import WorkbenchProject

T = TypeVar("T")
FAILURE_SCHEMA = "rocketdict-workbench-real-product-run-failure/1"


def _exception_stream(exc: Exception, name: str) -> str | None:
    value = getattr(exc, name, None)
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _write_failure_evidence(failure_path: Path, *, phase: str, exc: Exception) -> None:
    payload: dict[str, object] = {
        "schema": FAILURE_SCHEMA,
        "status": "failed",
        "phase": phase,
        "exception_type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }
    returncode = getattr(exc, "returncode", None)
    if returncode is not None:
        payload["returncode"] = returncode
    command = getattr(exc, "cmd", None)
    if command is not None:
        payload["command"] = repr(command)
    for name in ("stdout", "stderr"):
        stream = _exception_stream(exc, name)
        if stream:
            payload[name] = stream

    state_path = failure_path.parent / "product-run.json"
    if state_path.is_file():
        try:
            payload["product_run_state"] = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as state_exc:
            payload["product_run_state_read_error"] = (
                f"{type(state_exc).__name__}: {state_exc}"
            )

    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"::notice title=RocketDict failure evidence::{failure_path}", flush=True)


def _phase(name: str, fn: Callable[[], T], *, failure_path: Path) -> T:
    print(f"::notice title=RocketDict phase::{name}", flush=True)
    try:
        value = fn()
    except Exception as exc:
        _write_failure_evidence(failure_path, phase=name, exc=exc)
        print(
            f"::error title=RocketDict {name}::{type(exc).__name__}: {exc}",
            flush=True,
        )
        traceback.print_exc()
        raise
    print(f"::notice title=RocketDict phase completed::{name}", flush=True)
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{name} is boolean")
    result = int(value or 0)
    if result <= 0:
        raise RuntimeError(f"{name} is not a positive durable id: {value!r}")
    return result


def _run(root: Path, failure_path: Path) -> int:
    source = root / "source.txt"
    source.write_text(
        "Light passes through a glass prism and forms a spectrum. "
        "The prism separates light into visible colors.",
        encoding="utf-8",
    )

    opus_asset = Path(os.environ["ROCKETDICT_OPUS_ASSET_DIR"]).resolve()
    cefrj_asset = Path(os.environ["ROCKETDICT_CEFRJ_ASSET"]).resolve()
    core = RocketDictCore()
    project = _phase(
        "create-workbench-project",
        lambda: WorkbenchProject.create(root / "project", name="real-product-run-smoke", core=core),
        failure_path=failure_path,
    )
    imported = _phase(
        "import-source",
        lambda: project.import_source(source),
        failure_path=failure_path,
    )
    preflight = _phase(
        "build-product-preflight",
        lambda: build_product_preflight(project, source_kind="text"),
        failure_path=failure_path,
    )
    if preflight.get("status") != "ready":
        raise RuntimeError(f"Product preflight is not ready: {preflight}")

    state_path = root / "product-run.json"
    initialized = _phase(
        "initialize-product-run",
        lambda: initialize_product_run(
            core,
            project.paths.database,
            preflight,
            state_path=state_path,
        ),
        failure_path=failure_path,
    )
    if not state_path.is_file():
        raise RuntimeError("Product run did not persist its unified state")

    result = _phase(
        "first-advance-source-through-stage25",
        lambda: advance_product_run(
            core,
            project.paths.database,
            state_path,
            opus_asset=opus_asset,
            cefrj_asset=cefrj_asset,
            set_name="RocketDict unified real smoke",
        ),
        failure_path=failure_path,
    )
    if result.get("status") != "product_complete_exported":
        raise RuntimeError(f"Unified product-run did not finish: {result}")

    def validate_final_product() -> tuple[dict, dict, dict, int, Path, list]:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("status") != "product_complete_exported":
            raise RuntimeError(f"Unified state did not reach Product completion: {state.get('status')!r}")
        steps = state.get("steps") or {}
        downstream = steps.get("stage20_downstream") or {}
        if downstream.get("executor") != "maintained-core-native-stage20-25-v1":
            raise RuntimeError(f"Product-run did not use maintained downstream executor: {downstream}")
        if downstream.get("status") != "completed_through_stage23":
            raise RuntimeError(f"Maintained downstream stopped before Stage23: {downstream}")
        sense_count = int(downstream.get("sense_count") or 0)
        if sense_count <= 0:
            raise RuntimeError("Unified product-run produced no lexical senses")

        cards = steps.get("cards") or {}
        export = steps.get("export") or {}
        if cards.get("status") != "completed" or int(cards.get("card_count") or 0) != sense_count:
            raise RuntimeError(f"Unified Stage24 coverage failed: {cards}")
        _positive(cards.get("set_revision_id"), "set_revision_id")
        if export.get("status") != "completed":
            raise RuntimeError(f"Unified Stage25 did not complete: {export}")
        _positive(export.get("export_run_id"), "export_run_id")
        export_path = Path(str(export.get("export_path") or ""))
        if not export_path.is_file():
            raise RuntimeError(f"Unified Product export is missing: {export_path}")
        exported = json.loads(export_path.read_text(encoding="utf-8"))
        if exported.get("schema") != "rocketdict-product-export/1":
            raise RuntimeError(f"Unexpected export schema: {exported.get('schema')!r}")
        cards_payload = list(exported.get("cards") or [])
        if int(exported.get("card_count") or 0) != sense_count or len(cards_payload) != sense_count:
            raise RuntimeError("Unified product-run lost sense/card coverage")
        for card in cards_payload:
            lemma = str(card.get("lemma") or "").strip()
            translation = str(card.get("translation") or "").strip()
            if not translation or lemma.casefold() == translation.casefold() or not re.search(r"[А-Яа-яЁё]", translation):
                raise RuntimeError(f"Export contains non-real lexical translation: {card}")
            if (card.get("pronunciation") or {}).get("generated_fallback") is not False:
                raise RuntimeError(f"Generated pronunciation fallback leaked into export: {card}")
            if not list(card.get("examples") or []):
                raise RuntimeError(f"Sense-scoped example missing from export: {card}")
        return state, downstream, export, sense_count, export_path, cards_payload

    state, downstream, export, sense_count, export_path, cards_payload = _phase(
        "validate-final-product",
        validate_final_product,
        failure_path=failure_path,
    )
    cards = (state.get("steps") or {}).get("cards") or {}

    # Replay proves that the unified state resumes rather than rebuilding a second
    # semantic Product lineage. Core operations are already replay-safe; this check
    # verifies the user-facing driver honors that persisted boundary too.
    replay = _phase(
        "replay-completed-product-run",
        lambda: advance_product_run(
            core,
            project.paths.database,
            state_path,
            opus_asset=opus_asset,
            cefrj_asset=cefrj_asset,
            set_name="RocketDict unified real smoke",
        ),
        failure_path=failure_path,
    )
    if replay.get("status") != "product_complete_exported":
        raise RuntimeError(f"Unified product-run replay failed: {replay}")
    replay_state = json.loads(state_path.read_text(encoding="utf-8"))
    replay_export = (replay_state.get("steps") or {}).get("export") or {}
    if int(replay_export.get("export_run_id") or 0) != int(export.get("export_run_id") or 0):
        raise RuntimeError("Unified replay changed immutable Stage25 export identity")
    if str(replay_export.get("export_sha256") or "") != str(export.get("export_sha256") or ""):
        raise RuntimeError("Unified replay changed Stage25 export bytes")

    evidence = {
        "schema": "rocketdict-workbench-real-product-run-smoke/1",
        "status": "passed",
        "source_sha256": imported["sha256"],
        "preflight_fingerprint": preflight["identity"]["fingerprint"],
        "initialized_status": initialized.get("status"),
        "final_status": result["status"],
        "executor": downstream["executor"],
        "sense_count": sense_count,
        "card_count": int(cards["card_count"]),
        "set_revision_id": int(cards["set_revision_id"]),
        "export_run_id": int(export["export_run_id"]),
        "export_sha256": str(export["export_sha256"]),
        "export_path": str(export_path),
        "replay_same_export_identity": True,
        "real_mt_required": True,
        "generated_pronunciation_fallback": False,
        "validated_export_card_count": len(cards_payload),
    }
    evidence_path = root / "real-product-run-smoke.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
    return 0


def main() -> int:
    root = Path(os.environ.get("ROCKETDICT_PRODUCT_RUN_SMOKE_ROOT", "work/product-run-smoke")).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    failure_path = root / "real-product-run-failure.json"
    try:
        return _run(root, failure_path)
    except Exception as exc:
        if not failure_path.is_file():
            _write_failure_evidence(failure_path, phase="main", exc=exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
