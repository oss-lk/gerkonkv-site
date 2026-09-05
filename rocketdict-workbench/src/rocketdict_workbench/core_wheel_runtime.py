from __future__ import annotations

"""Opt-in runtime proof for a recovered RocketDict ``py3-none-any`` wheel.

The wheel is never installed and never extracted. A fresh Python subprocess is
started in isolated mode and imports the packaged core through Python's native
zipimport path. Runtime evidence is bound to the exact wheel SHA-256 before and
after the subprocess, rejects network/DNS attempts through an audit hook, and
checks the origins of both required and transitively imported ``rocketdict.*``
modules.

This remains a separate evidence layer from structural recovery and the
base→0.30.40 compatibility plan. Even a successful historical wheel import does
not prove exact 0.30.40 compatibility or authorize Product dispatch.
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
from .core_wheel_recovery import build_wheel_recovery_plan, inspect_wheel_candidate

RUNTIME_SCHEMA = "rocketdict-workbench-core-wheel-runtime-probe/2"
VERIFIED_WHEEL_SCHEMA = "rocketdict-workbench-core-wheel-recovery/3"

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
from pathlib import Path
import platform
import sys

wheel = Path(sys.argv[1]).resolve()
wheel_text = str(wheel)

class NetworkDisabledError(RuntimeError):
    pass

blocked_network_events = []
def _audit(event, args):
    if event in {
        "socket.connect",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
    }:
        blocked_network_events.append(event)
        raise NetworkDisabledError("network access disabled during RocketDict wheel recovery probe: " + event)

sys.addaudithook(_audit)

# -I excludes cwd, PYTHONPATH and user-site. Keep interpreter stdlib/system
# site-packages so legitimate preinstalled dependencies may import, but force
# RocketDict itself to resolve from the candidate wheel first.
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
    "blocked_network_events": blocked_network_events,
    "python": {
        "version": sys.version,
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
    },
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

transitive = {}
for name, module in sorted(sys.modules.items()):
    if name == "rocketdict" or name.startswith("rocketdict."):
        file = getattr(module, "__file__", None)
        transitive[name] = str(file) if file else None
payload["all_loaded_rocketdict_module_files"] = transitive

print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
'''


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            total += len(block)
    return digest.hexdigest(), total


def _inside_wheel(path_text: str | None, wheel: Path) -> bool:
    if not path_text:
        return False
    expected = str(wheel.resolve()).replace("\\", "/").rstrip("/") + "/"
    observed = str(path_text).replace("\\", "/")
    return observed.startswith(expected)


def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
    payload["identity"] = {
        "fingerprint": _canonical_sha(
            {
                key: value
                for key, value in payload.items()
                if key not in {"identity", "stderr", "stdout"}
            }
        )
    }
    return payload


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

    before_sha, before_bytes = _file_sha256(path)
    python_bin = str(python or sys.executable)
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CONDA_PREFIX"):
        env.pop(key, None)
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
        after_sha, after_bytes = _file_sha256(path)
        return _finalize(
            {
                "schema": RUNTIME_SCHEMA,
                "status": "timeout",
                "attempted": True,
                "ok": False,
                "promotion_allowed": False,
                "wheel_path": str(path),
                "wheel_sha256_before": before_sha,
                "wheel_sha256_after": after_sha,
                "wheel_bytes_before": before_bytes,
                "wheel_bytes_after": after_bytes,
                "wheel_stable_during_probe": before_sha == after_sha and before_bytes == after_bytes,
                "python": python_bin,
                "timeout_seconds": timeout,
                "error": str(exc),
            }
        )

    after_sha, after_bytes = _file_sha256(path)
    stable = before_sha == after_sha and before_bytes == after_bytes
    if not stable:
        return _finalize(
            {
                "schema": RUNTIME_SCHEMA,
                "status": "rejected_wheel_changed_during_probe",
                "attempted": True,
                "ok": False,
                "promotion_allowed": False,
                "wheel_path": str(path),
                "wheel_sha256_before": before_sha,
                "wheel_sha256_after": after_sha,
                "wheel_bytes_before": before_bytes,
                "wheel_bytes_after": after_bytes,
                "wheel_stable_during_probe": False,
                "python": python_bin,
                "returncode": result.returncode,
                "stderr": result.stderr,
            }
        )

    if result.returncode != 0:
        return _finalize(
            {
                "schema": RUNTIME_SCHEMA,
                "status": "process_failed",
                "attempted": True,
                "ok": False,
                "promotion_allowed": False,
                "wheel_path": str(path),
                "wheel_sha256": before_sha,
                "wheel_bytes": before_bytes,
                "wheel_stable_during_probe": True,
                "python": python_bin,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )

    try:
        observed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return _finalize(
            {
                "schema": RUNTIME_SCHEMA,
                "status": "invalid_probe_output",
                "attempted": True,
                "ok": False,
                "promotion_allowed": False,
                "wheel_path": str(path),
                "wheel_sha256": before_sha,
                "wheel_bytes": before_bytes,
                "wheel_stable_during_probe": True,
                "python": python_bin,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": str(exc),
            }
        )

    module_files = dict(observed.get("module_files") or {})
    transitive_files = dict(observed.get("all_loaded_rocketdict_module_files") or {})
    import_errors = dict(observed.get("import_errors") or {})
    blocked_network_events = list(observed.get("blocked_network_events") or [])

    outside_required: dict[str, str] = {}
    missing_origins: list[str] = []
    for module in _REQUIRED_MODULES:
        file = module_files.get(module)
        if file is None:
            if module not in import_errors:
                missing_origins.append(module)
            continue
        if not _inside_wheel(file, path):
            outside_required[module] = str(file)

    outside_transitive = {
        name: str(file)
        for name, file in transitive_files.items()
        if file and not _inside_wheel(str(file), path)
    }

    dependency_failures: dict[str, dict[str, Any]] = {}
    candidate_module_failures: dict[str, dict[str, Any]] = {}
    network_attempt_failures: dict[str, dict[str, Any]] = {}
    for requested, row in import_errors.items():
        row = dict(row or {})
        if row.get("type") == "NetworkDisabledError":
            network_attempt_failures[requested] = row
            continue
        missing = str(row.get("missing_module") or "")
        if missing and not (missing == "rocketdict" or missing.startswith("rocketdict.")):
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
        module in module_files and module_files.get(module) for module in _REQUIRED_MODULES
    )
    origin_clean = not outside_required and not outside_transitive and not missing_origins
    network_clean = not blocked_network_events and not network_attempt_failures
    ok = bool(
        all_required_loaded
        and not import_errors
        and origin_clean
        and network_clean
        and client_ok
        and stable
    )

    if ok:
        status = "runtime_import_proven"
    elif not network_clean:
        status = "rejected_runtime_network_attempt"
    elif outside_required or outside_transitive:
        status = "rejected_module_origin_escape"
    elif dependency_failures and not candidate_module_failures:
        status = "blocked_missing_runtime_dependencies"
    else:
        status = "runtime_import_not_proven"

    return _finalize(
        {
            "schema": RUNTIME_SCHEMA,
            "status": status,
            "attempted": True,
            "ok": ok,
            "promotion_allowed": False,
            "wheel_path": str(path),
            "wheel_sha256": before_sha,
            "wheel_bytes": before_bytes,
            "wheel_stable_during_probe": stable,
            "python": python_bin,
            "python_observed": observed.get("python"),
            "python_isolated_mode": True,
            "network_policy": "python_audit_hook_denies_socket_connect_and_name_resolution_plus_common_offline_flags",
            "blocked_network_events": blocked_network_events,
            "version": observed.get("version"),
            "api_version": observed.get("api_version"),
            "rocketdict_api": observed.get("rocketdict_api"),
            "module_files": module_files,
            "all_loaded_rocketdict_module_files": transitive_files,
            "all_required_modules_loaded": all_required_loaded,
            "outside_candidate_wheel": outside_required,
            "outside_candidate_wheel_transitive": outside_transitive,
            "missing_module_origins": missing_origins,
            "import_errors": import_errors,
            "dependency_import_failures": dependency_failures,
            "candidate_module_import_failures": candidate_module_failures,
            "network_attempt_failures": network_attempt_failures,
            "stderr": result.stderr,
            "rule": (
                "A successful zipimport probe proves only that this exact, stable wheel SHA-256 "
                "loads the required historical RocketDict modules from inside the wheel in the "
                "selected isolated Python environment without an observed socket/DNS attempt. "
                "It does not prove exact 0.30.40 compatibility, live registry contracts, database "
                "compatibility or Product execution readiness."
            ),
        }
    )


def recover_wheel_with_runtime(
    candidate: Path | str,
    *,
    target_evidence_root: Path | str | None = None,
    probe_runtime: bool = False,
    python: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    structural = inspect_wheel_candidate(candidate)
    plan = build_wheel_recovery_plan(candidate, target_evidence_root=target_evidence_root)
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

    structural_sha = ((structural.get("candidate") or {}).get("archive_sha256"))
    plan_sha = (((plan.get("candidate") or {}).get("source") or {}).get("archive_sha256"))
    runtime_sha = runtime.get("wheel_sha256") if runtime.get("attempted") else None
    observed_hashes = [value for value in (structural_sha, plan_sha, runtime_sha) if value]
    artifact_identity_consistent = bool(observed_hashes) and len(set(observed_hashes)) == 1

    runtime_proven = bool(runtime.get("ok") and artifact_identity_consistent)
    overall = "runtime_proven_base_candidate" if runtime_proven else "structural_candidate"
    blockers = [
        "missing_exact_0.30.40_overlay_and_public_api_compatibility_proof",
        "live_product_preflight_api_probe_and_execution_binding_not_run",
    ]
    if not artifact_identity_consistent:
        blockers.insert(0, "cross_layer_wheel_identity_mismatch")

    identity_payload = {
        "schema": VERIFIED_WHEEL_SCHEMA,
        "structural_fingerprint": ((structural.get("identity") or {}).get("fingerprint")),
        "plan_fingerprint": ((plan.get("identity") or {}).get("fingerprint")),
        "runtime_fingerprint": ((runtime.get("identity") or {}).get("fingerprint")),
        "artifact_sha256": structural_sha,
        "artifact_identity_consistent": artifact_identity_consistent,
        "runtime_proven": runtime_proven,
    }
    return {
        "schema": VERIFIED_WHEEL_SCHEMA,
        "status": overall,
        "promotion_allowed": False,
        "artifact_sha256": structural_sha,
        "artifact_identity_consistent": artifact_identity_consistent,
        "structural_candidate": structural,
        "compatibility_plan": plan,
        "runtime_probe": runtime,
        "remaining_product_blockers": blockers,
        "identity": {"fingerprint": _canonical_sha(identity_payload)},
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-wheel",
        description=(
            "Read-only historical RocketDict wheel recovery with optional isolated, "
            "network-denied zipimport runtime proof"
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
    except (OSError, RecoveryCandidateError, RuntimeError, zipfile.BadZipFile) as exc:
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
