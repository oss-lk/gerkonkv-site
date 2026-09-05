from __future__ import annotations

"""Opt-in runtime proof for a recovered RocketDict ``py3-none-any`` wheel.

The wheel is never installed and never extracted.  A fresh Python subprocess is
started in isolated mode and the wheel path is prepended to ``sys.path`` so
Python's standard zipimport machinery loads the packaged modules directly.

This is intentionally a *separate* evidence layer from structural recovery and
the base→0.30.40 compatibility plan.  A successful probe proves that the
packaged historical core can be imported in the selected Python environment; it
does not prove exact 0.30.40 compatibility or authorize Product dispatch.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import zipfile

from .core_recovery import RecoveryCandidateError
from .core_wheel_recovery import (
    WHEEL_SCHEMA,
    build_wheel_recovery_plan,
    inspect_wheel_candidate,
)

RUNTIME_SCHEMA = "rocketdict-workbench-core-wheel-runtime-probe/1"
VERIFIED_WHEEL_SCHEMA = "rocketdict-workbench-core-wheel-recovery/2"

_REQUIRED_MODULES = (
    "rocketdict",
    "rocketdict.api",
    "rocketdict.api.contracts",
    "rocketdict.api.client",
    "rocketdict.api.cli",
    "rocketdict.database",
    "rocketdict.importing.cli",
    "rocketdict.interpretation.cli",
)

_PROBE_SCRIPT = r'''
import importlib
import inspect
import json
import os
from pathlib import Path
import sys

wheel = Path(sys.argv[1]).resolve()
wheel_text = str(wheel)
# -I already excludes cwd/PYTHONPATH/user-site.  Keep stdlib/site-packages so
# legitimate declared dependencies can import, but force RocketDict itself to
# resolve from the candidate wheel first.
sys.path.insert(0, wheel_text)

names = [
    "rocketdict",
    "rocketdict.api",
    "rocketdict.api.contracts",
    "rocketdict.api.client",
    "rocketdict.api.cli",
    "rocketdict.database",
    "rocketdict.importing.cli",
    "rocketdict.interpretation.cli",
]
modules = {}
errors = {}
for name in names:
    try:
        module = importlib.import_module(name)
        file = getattr(module, "__file__", None)
        modules[name] = str(file) if file else None
    except Exception as exc:
        row = {"type": type(exc).__name__, "error": str(exc)}
        if isinstance(exc, ModuleNotFoundError):
            row["missing_module"] = getattr(exc, "name", None)
        errors[name] = row

payload = {
    "version": None,
    "api_version": None,
    "rocketdict_api": None,
    "module_files": modules,
    "import_errors": errors,
}
try:
    import rocketdict
    payload["version"] = str(getattr(rocketdict, "__version__", None))
except Exception:
    pass
try:
    from rocketdict.api.contracts import API_VERSION
    payload["api_version"] = str(API_VERSION)
except Exception:
    pass
try:
    from rocketdict.api.client import RocketDictAPI
    payload["rocketdict_api"] = {
        "module": getattr(RocketDictAPI, "__module__", None),
        "qualname": getattr(RocketDictAPI, "__qualname__", None),
        "is_class": inspect.isclass(RocketDictAPI),
    }
except Exception:
    pass
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
'''


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _inside_wheel(path_text: str | None, wheel: Path) -> bool:
    if not path_text:
        return False
    # zipimport reports virtual paths such as /x/rocketdict.whl/rocketdict/a.py.
    # Resolve only the wheel itself; the virtual child cannot exist on disk.
    expected = str(wheel.resolve()).replace("\\", "/").rstrip("/") + "/"
    observed = str(path_text).replace("\\", "/")
    return observed.startswith(expected)


def probe_wheel_runtime(
    candidate: Path | str,
    *,
    python: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or path.suffix.casefold() != ".whl":
        raise RecoveryCandidateError("runtime probe candidate must be a .whl file")
    if not zipfile.is_zipfile(path):
        raise RecoveryCandidateError("runtime probe candidate is not a valid wheel ZIP")

    python_bin = str(python or sys.executable)
    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
    ):
        env.pop(key, None)
    # Common model/package stacks honor these flags.  The probe itself performs
    # imports only and never invokes model/download APIs.
    env.update(
        {
            "PYTHONUTF8": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        }
    )

    try:
        result = subprocess.run(
            [python_bin, "-I", "-c", _PROBE_SCRIPT, str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(path.parent),
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        payload = {
            "schema": RUNTIME_SCHEMA,
            "status": "timeout",
            "attempted": True,
            "ok": False,
            "promotion_allowed": False,
            "wheel_path": str(path),
            "python": python_bin,
            "timeout_seconds": timeout,
            "error": str(exc),
        }
        payload["identity"] = {"fingerprint": _canonical_sha(payload)}
        return payload

    if result.returncode != 0:
        payload = {
            "schema": RUNTIME_SCHEMA,
            "status": "process_failed",
            "attempted": True,
            "ok": False,
            "promotion_allowed": False,
            "wheel_path": str(path),
            "python": python_bin,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        payload["identity"] = {"fingerprint": _canonical_sha(payload)}
        return payload

    try:
        observed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        payload = {
            "schema": RUNTIME_SCHEMA,
            "status": "invalid_probe_output",
            "attempted": True,
            "ok": False,
            "promotion_allowed": False,
            "wheel_path": str(path),
            "python": python_bin,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": str(exc),
        }
        payload["identity"] = {"fingerprint": _canonical_sha(payload)}
        return payload

    module_files = dict(observed.get("module_files") or {})
    import_errors = dict(observed.get("import_errors") or {})
    outside: dict[str, str] = {}
    missing_origins: list[str] = []
    for module in _REQUIRED_MODULES:
        file = module_files.get(module)
        if file is None:
            if module not in import_errors:
                missing_origins.append(module)
            continue
        if not _inside_wheel(file, path):
            outside[module] = str(file)

    dependency_failures: dict[str, dict[str, Any]] = {}
    candidate_module_failures: dict[str, dict[str, Any]] = {}
    for requested, row in import_errors.items():
        missing = str((row or {}).get("missing_module") or "")
        if missing and not (
            missing == "rocketdict" or missing.startswith("rocketdict.")
        ):
            dependency_failures[requested] = row
        else:
            candidate_module_failures[requested] = row

    client = observed.get("rocketdict_api") or {}
    client_ok = bool(
        client
        and client.get("is_class") is True
        and client.get("module") == "rocketdict.api.client"
    )
    all_required_loaded = all(
        module in module_files and module_files.get(module)
        for module in _REQUIRED_MODULES
    )
    ok = bool(
        result.returncode == 0
        and all_required_loaded
        and not import_errors
        and not outside
        and not missing_origins
        and client_ok
    )

    if ok:
        status = "runtime_import_proven"
    elif dependency_failures and not candidate_module_failures and not outside:
        status = "blocked_missing_runtime_dependencies"
    elif outside:
        status = "rejected_module_origin_escape"
    else:
        status = "runtime_import_not_proven"

    payload = {
        "schema": RUNTIME_SCHEMA,
        "status": status,
        "attempted": True,
        "ok": ok,
        "promotion_allowed": False,
        "wheel_path": str(path),
        "python": python_bin,
        "python_isolated_mode": True,
        "network_policy": "imports_only_common_offline_environment_flags_set",
        "version": observed.get("version"),
        "api_version": observed.get("api_version"),
        "rocketdict_api": observed.get("rocketdict_api"),
        "module_files": module_files,
        "all_required_modules_loaded": all_required_loaded,
        "outside_candidate_wheel": outside,
        "missing_module_origins": missing_origins,
        "import_errors": import_errors,
        "dependency_import_failures": dependency_failures,
        "candidate_module_import_failures": candidate_module_failures,
        "stderr": result.stderr,
        "rule": (
            "A successful zipimport probe proves only that required historical RocketDict "
            "modules import from this exact wheel in the selected Python environment. It "
            "does not prove exact 0.30.40 compatibility, live registry contracts, database "
            "compatibility or Product execution readiness."
        ),
    }
    payload["identity"] = {
        "fingerprint": _canonical_sha(
            {
                key: value
                for key, value in payload.items()
                if key not in {"identity", "stderr"}
            }
        )
    }
    return payload


def recover_wheel_with_runtime(
    candidate: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
    probe_runtime: bool = False,
    python: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    structural = inspect_wheel_candidate(candidate)
    plan = build_wheel_recovery_plan(
        candidate,
        target_evidence_root=target_evidence_root,
    )
    runtime = (
        probe_wheel_runtime(candidate, python=python, timeout=timeout)
        if probe_runtime
        else {
            "schema": RUNTIME_SCHEMA,
            "status": "not_requested",
            "attempted": False,
            "ok": False,
            "promotion_allowed": False,
            "rule": "Runtime probing is opt-in; structural recovery never executes a wheel.",
        }
    )
    overall = "runtime_proven_base_candidate" if runtime.get("ok") else "structural_candidate"
    return {
        "schema": VERIFIED_WHEEL_SCHEMA,
        "status": overall,
        "promotion_allowed": False,
        "structural_candidate": structural,
        "compatibility_plan": plan,
        "runtime_probe": runtime,
        "remaining_product_blockers": [
            "missing_exact_0.30.40_overlay_and_public_api_compatibility_proof",
            "live_product_preflight_api_probe_and_execution_binding_not_run",
        ],
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-wheel",
        description=(
            "Read-only historical RocketDict wheel recovery with optional isolated "
            "zipimport runtime proof"
        ),
    )
    p.add_argument("candidate", type=Path)
    p.add_argument("--target-evidence-root", type=Path)
    p.add_argument("--probe-runtime", action="store_true")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = recover_wheel_with_runtime(
            args.candidate,
            target_evidence_root=args.target_evidence_root,
            probe_runtime=args.probe_runtime,
            python=args.python,
            timeout=args.timeout,
        )
    except (
        OSError,
        RecoveryCandidateError,
        RuntimeError,
        zipfile.BadZipFile,
    ) as exc:
        report = {
            "schema": VERIFIED_WHEEL_SCHEMA,
            "status": "error",
            "promotion_allowed": False,
            "type": type(exc).__name__,
            "error": str(exc),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
