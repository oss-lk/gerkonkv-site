from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any
import zipfile

SCHEMA = "rocketdict-workbench-core-recovery-candidate/1"
EXACT_PRODUCT_VERSION = "0.30.40"
MAX_ARCHIVE_PACKAGE_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 32 * 1024 * 1024

EXACT_RECOVERED_FILES = {
    "src/rocketdict/__init__.py": {
        "bytes": 502,
        "sha256": "7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c",
    },
    "src/rocketdict/nlp/registry.py": {
        "bytes": 29072,
        "sha256": "02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69",
    },
}

REQUIRED_MODULE_PATHS = {
    "rocketdict": ("src/rocketdict/__init__.py",),
    "rocketdict.api.contracts": ("src/rocketdict/api/contracts.py",),
    "rocketdict.api.client": ("src/rocketdict/api/client.py",),
    "rocketdict.api.cli": ("src/rocketdict/api/cli.py",),
    "rocketdict.database": (
        "src/rocketdict/database.py",
        "src/rocketdict/database/__init__.py",
    ),
    "rocketdict.importing.cli": ("src/rocketdict/importing/cli.py",),
    "rocketdict.interpretation.cli": ("src/rocketdict/interpretation/cli.py",),
}

_VERSION_RE = re.compile(rb"""(?m)^\s*__version__\s*=\s*["']([^"']+)["']\s*$""")


class RecoveryCandidateError(RuntimeError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256(raw)


def _safe_archive_name(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and ".." not in p.parts and ":" not in p.parts[0]


def _extract_version(package_root: bytes) -> str | None:
    match = _VERSION_RE.search(package_root)
    return match.group(1).decode("utf-8", "strict") if match else None


def _tree_sha(files: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(files):
        raw = files[path]
        h.update(path.encode("utf-8"))
        h.update(b"\0")
        h.update(str(len(raw)).encode("ascii"))
        h.update(b"\0")
        h.update(_sha256(raw).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _module_presence(files: dict[str, bytes]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for module, alternatives in REQUIRED_MODULE_PATHS.items():
        present = [path for path in alternatives if path in files]
        out[module] = {
            "available": bool(present),
            "matched_paths": present,
            "accepted_paths": list(alternatives),
        }
    return out


def _exact_evidence(files: dict[str, bytes]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path, expected in EXACT_RECOVERED_FILES.items():
        raw = files.get(path)
        if raw is None:
            out[path] = {
                "present": False,
                "match": False,
                "expected_bytes": expected["bytes"],
                "expected_sha256": expected["sha256"],
            }
            continue
        observed = {"bytes": len(raw), "sha256": _sha256(raw)}
        out[path] = {
            "present": True,
            "match": observed == expected,
            "expected_bytes": expected["bytes"],
            "expected_sha256": expected["sha256"],
            "observed_bytes": observed["bytes"],
            "observed_sha256": observed["sha256"],
        }
    return out


def _normalize_dir(path: Path) -> tuple[Path, Path]:
    """Return (candidate_root, python_source_root) without guessing layouts."""
    path = path.expanduser().resolve()
    options = []
    for source_root in (path / "src", path, path / "active_source" / "src"):
        if (source_root / "rocketdict" / "__init__.py").is_file():
            options.append(source_root.resolve())
    unique = []
    for item in options:
        if item not in unique:
            unique.append(item)
    if not unique:
        raise RecoveryCandidateError(
            f"candidate has no supported RocketDict package root: {path}"
        )
    if len(unique) != 1:
        raise RecoveryCandidateError(
            f"candidate has ambiguous RocketDict package roots: {[str(x) for x in unique]}"
        )
    return path, unique[0]


def _read_directory(path: Path) -> tuple[dict[str, bytes], dict[str, Any], Path]:
    candidate_root, source_root = _normalize_dir(path)
    package = source_root / "rocketdict"
    files: dict[str, bytes] = {}
    symlinks: list[str] = []
    for item in sorted(package.rglob("*.py")):
        if item.is_symlink():
            symlinks.append(str(item.relative_to(source_root)).replace("\\", "/"))
            continue
        if not item.is_file():
            continue
        relative = item.relative_to(source_root).as_posix()
        logical = f"src/{relative}"
        files[logical] = item.read_bytes()
    if symlinks:
        raise RecoveryCandidateError(
            f"candidate package contains source symlinks: {symlinks[:10]}"
        )
    meta = {
        "kind": "directory",
        "candidate_path": str(candidate_root),
        "python_source_root": str(source_root),
        "package_python_file_count": len(files),
        "package_python_bytes": sum(map(len, files.values())),
    }
    return files, meta, source_root


def _zip_layout(names: list[str]) -> tuple[str, str]:
    candidates: list[tuple[str, str]] = []
    for name in names:
        parts = PurePosixPath(name).parts
        if len(parts) >= 3 and parts[-3:] == ("src", "rocketdict", "__init__.py"):
            prefix = "/".join(parts[:-3])
            candidates.append((prefix, "src"))
        if len(parts) >= 2 and parts[-2:] == ("rocketdict", "__init__.py"):
            if len(parts) >= 3 and parts[-3] == "src":
                continue
            prefix = "/".join(parts[:-2])
            candidates.append((prefix, "direct"))
    unique = []
    for item in candidates:
        if item not in unique:
            unique.append(item)
    if not unique:
        raise RecoveryCandidateError("ZIP has no supported RocketDict package root")
    if len(unique) != 1:
        raise RecoveryCandidateError(f"ZIP has ambiguous RocketDict package roots: {unique}")
    return unique[0]


def _read_zip(path: Path) -> tuple[dict[str, bytes], dict[str, Any], None]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise RecoveryCandidateError(f"candidate ZIP is not a file: {path}")
    with zipfile.ZipFile(path) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise RecoveryCandidateError("ZIP contains duplicate member names")
        unsafe = [name for name in names if not _safe_archive_name(name)]
        if unsafe:
            raise RecoveryCandidateError(f"ZIP contains unsafe member names: {unsafe[:10]}")
        prefix, source_kind = _zip_layout(names)

        def package_relative(name: str) -> str | None:
            p = PurePosixPath(name)
            prefix_parts = PurePosixPath(prefix).parts if prefix else ()
            parts = p.parts
            if parts[: len(prefix_parts)] != prefix_parts:
                return None
            rest = parts[len(prefix_parts) :]
            if source_kind == "src":
                if len(rest) < 3 or rest[:2] != ("src", "rocketdict"):
                    return None
                rel = rest
            else:
                if len(rest) < 2 or rest[0] != "rocketdict":
                    return None
                rel = ("src", *rest)
            logical = PurePosixPath(*rel).as_posix()
            return logical if logical.endswith(".py") else None

        selected: list[tuple[zipfile.ZipInfo, str]] = []
        total = 0
        for info in infos:
            logical = package_relative(info.filename)
            if logical is None:
                continue
            if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                raise RecoveryCandidateError(
                    f"ZIP package member exceeds recovery limit: {info.filename} ({info.file_size})"
                )
            total += int(info.file_size)
            if total > MAX_ARCHIVE_PACKAGE_BYTES:
                raise RecoveryCandidateError(
                    f"ZIP RocketDict package exceeds recovery limit: {total}"
                )
            selected.append((info, logical))

        files: dict[str, bytes] = {}
        for info, logical in selected:
            raw = zf.read(info)
            if len(raw) != info.file_size:
                raise RecoveryCandidateError(
                    f"ZIP member length mismatch: {info.filename}"
                )
            if logical in files:
                raise RecoveryCandidateError(
                    f"ZIP maps multiple members to one logical path: {logical}"
                )
            files[logical] = raw

    meta = {
        "kind": "zip",
        "candidate_path": str(path),
        "archive_sha256": _sha256_file(path),
        "archive_bytes": path.stat().st_size,
        "archive_prefix": prefix,
        "source_layout": source_kind,
        "package_python_file_count": len(files),
        "package_python_bytes": sum(map(len, files.values())),
    }
    return files, meta, None


_RUNTIME_PROBE = r"""
import importlib
import inspect
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
sys.path[:] = [str(root)] + [p for p in sys.path if p and Path(p or ".").resolve() != root]
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
mods = {}
errors = {}
for name in names:
    try:
        module = importlib.import_module(name)
        file = getattr(module, "__file__", None)
        mods[name] = str(Path(file).resolve()) if file else None
    except Exception as exc:
        errors[name] = {"type": type(exc).__name__, "error": str(exc)}

payload = {
    "version": None,
    "api_version": None,
    "rocketdict_api": None,
    "module_files": mods,
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
"""


def _runtime_probe(
    source_root: Path,
    *,
    python: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    python_bin = str(python or sys.executable)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.setdefault("PYTHONUTF8", "1")
    result = subprocess.run(
        [python_bin, "-c", _RUNTIME_PROBE, str(source_root)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout,
        check=False,
        cwd=str(source_root.parent),
    )
    if result.returncode != 0:
        return {
            "attempted": True,
            "ok": False,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": "candidate_runtime_probe_process_failed",
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "attempted": True,
            "ok": False,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": f"candidate_runtime_probe_invalid_json:{exc}",
        }
    expected_root = source_root.resolve()
    outside: dict[str, str] = {}
    for module, file in (payload.get("module_files") or {}).items():
        if not file:
            continue
        resolved = Path(file).resolve()
        try:
            resolved.relative_to(expected_root)
        except ValueError:
            outside[module] = str(resolved)
    import_errors = dict(payload.get("import_errors") or {})
    ok = not outside and not import_errors
    return {
        "attempted": True,
        "ok": ok,
        "python": python_bin,
        "version": payload.get("version"),
        "api_version": payload.get("api_version"),
        "rocketdict_api": payload.get("rocketdict_api"),
        "module_files": payload.get("module_files") or {},
        "import_errors": import_errors,
        "outside_candidate_source_root": outside,
        "stderr": result.stderr,
    }


def inspect_core_candidate(
    candidate: Path | str,
    *,
    python: str | Path | None = None,
    probe_runtime: bool = True,
) -> dict[str, Any]:
    candidate_path = Path(candidate).expanduser().resolve()
    if candidate_path.is_dir():
        files, source, source_root = _read_directory(candidate_path)
    elif candidate_path.is_file() and candidate_path.suffix.casefold() == ".zip":
        files, source, source_root = _read_zip(candidate_path)
    else:
        raise RecoveryCandidateError(
            "candidate must be a RocketDict source directory or .zip checkpoint"
        )
    if "src/rocketdict/__init__.py" not in files:
        raise RecoveryCandidateError(
            "candidate package root was detected but __init__.py was not read"
        )

    version = _extract_version(files["src/rocketdict/__init__.py"])
    modules = _module_presence(files)
    exact = _exact_evidence(files)
    missing_modules = [name for name, row in modules.items() if not row["available"]]
    exact_matches = [path for path, row in exact.items() if row["match"]]
    exact_mismatches = [path for path, row in exact.items() if not row["match"]]
    package_tree = {
        "python_file_count": len(files),
        "python_bytes": sum(map(len, files.values())),
        "sha256": _tree_sha(files),
    }

    runtime: dict[str, Any]
    if source_root is None:
        runtime = {
            "attempted": False,
            "ok": False,
            "reason": "zip_is_structural_evidence_only_extract_to_directory_for_runtime_probe",
        }
    elif probe_runtime:
        runtime = _runtime_probe(source_root, python=python)
    else:
        runtime = {
            "attempted": False,
            "ok": False,
            "reason": "runtime_probe_disabled",
        }

    structural_complete = not missing_modules
    exact_version = version == EXACT_PRODUCT_VERSION
    exact_recovered_files_match = not exact_mismatches
    if structural_complete and exact_version and exact_recovered_files_match:
        status = "exact_version_structural_candidate"
    elif structural_complete:
        status = "base_candidate_requires_compatibility_proof"
    else:
        status = "incomplete_candidate"

    promotion_blockers = []
    if not structural_complete:
        promotion_blockers.append("required_workbench_bridge_modules_missing")
    if not exact_version:
        promotion_blockers.append("candidate_is_not_exact_0.30.40")
    if not exact_recovered_files_match:
        promotion_blockers.append(
            "candidate_disagrees_with_exact_recovered_0.30.40_bytes"
        )
    if not runtime.get("ok"):
        promotion_blockers.append("runtime_import_probe_not_proven")
    promotion_blockers.append(
        "live_product_preflight_api_probe_and_execution_binding_not_run"
    )

    evidence = {
        "schema": SCHEMA,
        "status": status,
        "promotion_allowed": False,
        "candidate": source,
        "observed": {
            "rocketdict_version": version,
            "package_tree": package_tree,
            "required_modules": modules,
            "missing_required_modules": missing_modules,
            "exact_recovered_03040_files": exact,
            "exact_recovered_match_paths": exact_matches,
            "exact_recovered_mismatch_paths": exact_mismatches,
        },
        "runtime_probe": runtime,
        "promotion_blockers": promotion_blockers,
        "promotion_rule": (
            "This report is recovery evidence only. Even an exact-version structural "
            "candidate must be extracted/installed as a real runtime and pass Workbench "
            "doctor, immutable Product preflight, live registry/API probe, exact callable "
            "binding, execution-contract verification and quality PASS semantics before "
            "Product dispatch."
        ),
    }
    evidence["identity"] = {
        "fingerprint": _canonical_sha(
            {
                "schema": SCHEMA,
                "candidate_kind": source["kind"],
                "candidate_archive_sha256": source.get("archive_sha256"),
                "rocketdict_version": version,
                "package_tree_sha256": package_tree["sha256"],
                "required_modules": {
                    key: row["matched_paths"] for key, row in modules.items()
                },
                "exact_recovered_03040_files": {
                    key: {
                        "present": row["present"],
                        "observed_sha256": row.get("observed_sha256"),
                        "match": row["match"],
                    }
                    for key, row in exact.items()
                },
                "runtime": {
                    "attempted": runtime.get("attempted"),
                    "ok": runtime.get("ok"),
                    "version": runtime.get("version"),
                    "api_version": runtime.get("api_version"),
                    "module_files": runtime.get("module_files"),
                    "outside_candidate_source_root": runtime.get(
                        "outside_candidate_source_root"
                    ),
                },
            }
        )
    }
    return evidence


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rocketdict-recover-core",
        description=(
            "Read-only verifier for recovered RocketDict core/checkpoint candidates. "
            "It never promotes a candidate into Product execution."
        ),
    )
    p.add_argument("candidate", type=Path)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--no-runtime-probe", action="store_true")
    p.add_argument("--output", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = inspect_core_candidate(
            args.candidate,
            python=args.python,
            probe_runtime=not args.no_runtime_probe,
        )
    except (OSError, RecoveryCandidateError, subprocess.SubprocessError) as exc:
        report = {
            "schema": SCHEMA,
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
