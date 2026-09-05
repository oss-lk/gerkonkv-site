from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import zipfile

from rocketdict_workbench.core_scan_runtime import scan_recovery_frontier
from rocketdict_workbench.core_wheel_runtime import (
    parser,
    probe_wheel_runtime,
    recover_wheel_with_runtime,
)


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _target() -> Path:
    return _repo() / "rocketdict" / "recovered" / "stage8-0.30.40"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wheel(
    path: Path,
    *,
    version: str = "0.30.34",
    missing_dependency: bool = False,
    network_attempt: bool = False,
) -> Path:
    package_root = (_target() / "src/rocketdict/__init__.py").read_bytes()
    package_root = package_root.replace(b"0.30.40", version.encode("ascii"))
    if missing_dependency:
        database = b"import definitely_missing_rocketdict_recovery_dependency\n"
    elif network_attempt:
        database = b'import socket\nsocket.getaddrinfo("example.com", 443)\n'
    else:
        database = b"def bootstrap_database(path):\n    return None\n"
    files = {
        "rocketdict/__init__.py": package_root,
        "rocketdict/nlp/__init__.py": b"",
        "rocketdict/nlp/registry.py": (
            _target() / "src/rocketdict/nlp/registry.py"
        ).read_bytes(),
        "rocketdict/api/__init__.py": b"",
        "rocketdict/api/contracts.py": b'API_VERSION = "wheel-runtime-test/1"\n',
        "rocketdict/api/client.py": b"class RocketDictAPI:\n    pass\n",
        "rocketdict/api/cli.py": b"",
        "rocketdict/database.py": database,
        "rocketdict/importing/__init__.py": b"",
        "rocketdict/importing/cli.py": b"",
        "rocketdict/interpretation/__init__.py": b"",
        "rocketdict/interpretation/cli.py": b"",
        f"rocketdict-{version}.dist-info/METADATA": (
            f"Metadata-Version: 2.1\nName: rocketdict\nVersion: {version}\n"
        ).encode("utf-8"),
        f"rocketdict-{version}.dist-info/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, raw in files.items():
            zf.writestr(name, raw)
    return path


def test_opt_in_zipimport_probe_loads_all_required_modules_from_exact_stable_wheel(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.34-py3-none-any.whl")
    expected_sha = _sha256(wheel)

    runtime = probe_wheel_runtime(wheel, python=sys.executable)

    assert runtime["schema"] == "rocketdict-workbench-core-wheel-runtime-probe/2"
    assert runtime["status"] == "runtime_import_proven"
    assert runtime["attempted"] is True
    assert runtime["ok"] is True
    assert runtime["promotion_allowed"] is False
    assert runtime["wheel_sha256"] == expected_sha
    assert runtime["wheel_bytes"] == wheel.stat().st_size
    assert runtime["wheel_stable_during_probe"] is True
    assert runtime["python_isolated_mode"] is True
    assert "audit_hook" in runtime["network_policy"]
    assert runtime["blocked_network_events"] == []
    assert runtime["version"] == "0.30.34"
    assert runtime["api_version"] == "wheel-runtime-test/1"
    assert runtime["rocketdict_api"] == {
        "module": "rocketdict.api.client",
        "qualname": "RocketDictAPI",
        "is_class": True,
    }
    assert runtime["all_required_modules_loaded"] is True
    assert runtime["outside_candidate_wheel"] == {}
    assert runtime["outside_candidate_wheel_transitive"] == {}
    assert runtime["missing_module_origins"] == []
    assert runtime["import_errors"] == {}
    assert runtime["dependency_import_failures"] == {}
    assert runtime["network_attempt_failures"] == {}
    assert len(runtime["identity"]["fingerprint"]) == 64
    prefix = str(wheel.resolve()).replace("\\", "/") + "/"
    assert all(
        str(value).replace("\\", "/").startswith(prefix)
        for value in runtime["module_files"].values()
        if value
    )
    assert all(
        str(value).replace("\\", "/").startswith(prefix)
        for value in runtime["all_loaded_rocketdict_module_files"].values()
        if value
    )


def test_missing_external_dependency_is_reported_as_dependency_blocker(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "rocketdict-0.30.34-py3-none-any.whl",
        missing_dependency=True,
    )

    runtime = probe_wheel_runtime(wheel, python=sys.executable)

    assert runtime["status"] == "blocked_missing_runtime_dependencies"
    assert runtime["ok"] is False
    assert runtime["wheel_stable_during_probe"] is True
    assert "rocketdict.database" in runtime["dependency_import_failures"]
    row = runtime["dependency_import_failures"]["rocketdict.database"]
    assert row["type"] == "ModuleNotFoundError"
    assert row["missing_module"] == "definitely_missing_rocketdict_recovery_dependency"
    assert runtime["candidate_module_import_failures"] == {}
    assert runtime["outside_candidate_wheel"] == {}
    assert runtime["network_attempt_failures"] == {}


def test_runtime_probe_rejects_network_or_dns_attempt_during_import(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "rocketdict-0.30.34-py3-none-any.whl",
        network_attempt=True,
    )

    runtime = probe_wheel_runtime(wheel, python=sys.executable)

    assert runtime["status"] == "rejected_runtime_network_attempt"
    assert runtime["ok"] is False
    assert runtime["promotion_allowed"] is False
    assert runtime["blocked_network_events"]
    assert "rocketdict.database" in runtime["network_attempt_failures"]
    assert runtime["network_attempt_failures"]["rocketdict.database"]["type"] == "NetworkDisabledError"


def test_runtime_proven_wheel_stays_blocked_by_exact_03040_compatibility(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.34-py3-none-any.whl")
    expected_sha = _sha256(wheel)

    report = recover_wheel_with_runtime(
        wheel,
        probe_runtime=True,
        python=sys.executable,
    )

    assert report["schema"] == "rocketdict-workbench-core-wheel-recovery/3"
    assert report["status"] == "runtime_proven_base_candidate"
    assert report["promotion_allowed"] is False
    assert report["artifact_sha256"] == expected_sha
    assert report["artifact_identity_consistent"] is True
    assert len(report["identity"]["fingerprint"]) == 64
    assert report["runtime_probe"]["ok"] is True
    assert report["runtime_probe"]["wheel_sha256"] == expected_sha
    assert report["structural_candidate"]["candidate"]["archive_sha256"] == expected_sha
    assert report["structural_candidate"]["promotion_allowed"] is False
    plan = report["compatibility_plan"]
    assert plan["candidate"]["source"]["archive_sha256"] == expected_sha
    assert plan["promotion_allowed"] is False
    assert plan["target"]["overlay_member_count"] == 19
    assert plan["target"]["exact_target_available_count"] == 2
    assert plan["target"]["exact_target_missing_count"] == 17
    assert plan["target"]["public_api_exact_bytes_recovered"] is False
    assert "missing_exact_overlay_targets:17" in plan["blockers"]
    assert report["remaining_product_blockers"] == [
        "missing_exact_0.30.40_overlay_and_public_api_compatibility_proof",
        "live_product_preflight_api_probe_and_execution_binding_not_run",
    ]


def test_unified_scan_opt_in_wheel_probe_adds_hash_consistent_runtime_fingerprint(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "rocketdict-0.30.34-py3-none-any.whl")

    structural = scan_recovery_frontier(wheel, probe_wheels=False)
    structural_row = structural["candidates"][0]
    assert structural["schema"] == "rocketdict-workbench-core-recovery-scan/5"
    assert structural["probe_wheels"] is False
    assert structural["wheel_runtime_probe_count"] == 0
    assert structural_row["runtime_probe_ok"] is False
    assert structural_row["runtime_artifact_identity_consistent"] is None
    assert structural_row["runtime_proof_status"] == "not_requested"
    assert structural_row["runtime_probe_fingerprint"] is None

    probed = scan_recovery_frontier(
        wheel,
        probe_wheels=True,
        python=sys.executable,
    )
    row = probed["candidates"][0]
    assert probed["probe_wheels"] is True
    assert probed["wheel_runtime_probe_count"] == 1
    assert probed["wheel_runtime_probe_hash_consistent_count"] == 1
    assert probed["wheel_runtime_probe_ok_count"] == 1
    assert row["runtime_artifact_identity_consistent"] is True
    assert row["runtime_probe_ok"] is True
    assert row["runtime_proof_status"] == "runtime_import_proven"
    assert row["wheel_runtime_probe"]["wheel_sha256"] == row["archive_sha256"]
    assert len(row["runtime_probe_fingerprint"]) == 64
    assert row["promotion_allowed"] is False
    assert row["compatibility_plan_status"] == "blocked_missing_exact_overlay_bytes"


def test_wheel_runtime_cli_exposes_explicit_probe_flag() -> None:
    args = parser().parse_args(
        ["candidate.whl", "--probe-runtime", "--timeout", "12.5"]
    )
    assert args.probe_runtime is True
    assert args.timeout == 12.5
