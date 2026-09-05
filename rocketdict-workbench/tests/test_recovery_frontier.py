from __future__ import annotations

import json
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def test_recovery_frontier_keeps_runtime_proof_separate_from_product_promotion() -> None:
    path = _repo() / "rocketdict" / "recovered" / "recovery-frontier-2026-09-05.json"
    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["schema"] == "rocketdict-core-recovery-frontier/1"
    assert report["promotion_allowed"] is False
    assert report["exact_03040_core_complete"] is False
    assert report["known_late_artifact_bytes_available_in_current_runtime"] is False

    preferred = report["preferred_recovery_candidate"]
    assert preferred["version"] == "0.30.34"
    assert preferred["artifact_kind"] == "wheel"
    assert preferred["name"] == "rocketdict-0.30.34-py3-none-any.whl"
    assert preferred["sha256"] == "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a"
    assert len(preferred["sha256"]) == 64
    assert preferred["release_zip_available"] is False
    assert preferred["promotion_allowed"] is False

    assert [row["version"] for row in report["recovery_priority"]] == [
        "0.30.34",
        "0.30.33",
        "0.30.32",
        "0.30.31",
        "0.30.30",
        "0.30.29",
        "0.30.8",
    ]
    assert [row["priority"] for row in report["recovery_priority"]] == list(range(1, 8))

    exact = report["current_exact_03040_overlay"]
    assert exact == {
        "intended_members": 19,
        "exact_target_available": 2,
        "exact_target_missing": 17,
        "exact_public_api_modules_recovered": 0,
    }

    tooling = report["tooling"]
    assert tooling["wheel_recovery_schema"] == "rocketdict-workbench-core-wheel-recovery/2"
    assert tooling["wheel_runtime_probe_schema"] == "rocketdict-workbench-core-wheel-runtime-probe/1"
    assert tooling["unified_scan_schema"] == "rocketdict-workbench-core-recovery-scan/4"
    probe = tooling["wheel_runtime_probe"]
    assert probe["default"] == "not_requested"
    assert probe["opt_in_flag"] == "--probe-runtime"
    assert probe["scan_opt_in_flag"] == "--probe-wheels"
    assert "exact 0.30.40 compatibility" in probe["not_proven"]
    assert "Product dispatch readiness" in probe["not_proven"]

    failed = report["validation"]["failed_evidence_run"]
    green = report["validation"]["corrected_green_run"]
    assert failed["workflow_run"] == 33967461124
    assert "2 failed, 170 passed, 1 skipped" == failed["test_summary"]
    assert green["commit"] == "a016d1a739f2885cfbeb0923d571c2d177270a7a"
    assert green["workflow_run"] == 33967582970
    assert green["test_summary"] == "172 passed, 1 skipped in 1.80s"
