from __future__ import annotations

import json
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def test_recovery_frontier_keeps_historical_runtime_proof_separate_from_product_promotion() -> None:
    path = _repo() / "rocketdict" / "recovered" / "recovery-frontier-2026-09-05.json"
    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["schema"] == "rocketdict-core-recovery-frontier/2"
    assert report["promotion_allowed"] is False
    assert report["product_execution_allowed"] is False
    assert report["exact_03040_core_complete"] is False
    assert report["known_late_artifact_bytes_available_in_current_runtime"] is False

    preferred = report["preferred_recovery_candidate"]
    assert preferred["version"] == "0.30.34"
    assert preferred["artifact_kind"] == "wheel"
    assert preferred["name"] == "rocketdict-0.30.34-py3-none-any.whl"
    assert preferred["sha256"] == "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a"
    assert len(preferred["sha256"]) == 64
    assert preferred["release_zip_available"] is False
    assert preferred["exact_catalog_identity_required_for_this_known_name"] is True
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
    assert tooling["wheel_integrity_schema"] == "rocketdict-workbench-wheel-integrity/2"
    assert tooling["wheel_recovery_schema"] == "rocketdict-workbench-core-wheel-recovery/5"
    assert tooling["wheel_runtime_probe_schema"] == "rocketdict-workbench-core-wheel-runtime-probe/2"
    assert tooling["unified_scan_schema"] == "rocketdict-workbench-core-recovery-scan/7"
    assert tooling["wheel_proof_order"] == [
        "container/METADATA/WHEEL/RECORD integrity",
        "known historical checkpoint catalog identity when basename matches",
        "packaged RocketDict structural inspection",
        "historical-base to recovered-0.30.40 compatibility plan",
        "optional isolated network-denied zipimport runtime proof",
    ]
    assert "wheel_record_missing" in tooling["wheel_integrity_hard_failures"]
    assert "wheel_record_verification_failed" in tooling["wheel_integrity_hard_failures"]
    assert "wrong exact SHA" in tooling["known_name_identity_rule"]

    probe = tooling["wheel_runtime_probe"]
    assert probe["default"] == "not_requested"
    assert probe["wheel_opt_in_flag"] == "--probe-runtime"
    assert probe["scan_opt_in_flag"] == "--probe-wheels"
    assert "SHA-256 before/after" in probe["artifact_binding"]
    assert "audit hook" in probe["network_guard"]
    assert "transitively loaded rocketdict.*" in probe["module_origin_guard"]
    assert "exact 0.30.40 compatibility" in probe["not_proven"]
    assert "Product dispatch readiness" in probe["not_proven"]

    failed = report["validation"]["preserved_failed_runs"]
    assert failed[0]["workflow_run"] == 33967461124
    assert failed[0]["test_summary"] == "2 failed, 170 passed, 1 skipped"
    assert failed[1]["commit"] == "223bd14c000f56210942eb2b13776368f2685c4c"
    assert failed[1]["workflow_run"] == 33967891342

    intermediate = report["validation"]["intermediate_green_runs"]
    assert intermediate[0]["commit"] == "95a232722afa7e80b7a1e322f3d84f1abdc35ced"
    assert intermediate[0]["test_summary"] == "179 passed, 1 skipped in 1.98s"
    assert intermediate[1]["commit"] == "bf47ca6564fea9d827d7efc23f87ed527a3c1ee1"
    assert intermediate[1]["test_summary"] == "184 passed, 1 skipped in 2.17s"

    green = report["validation"]["latest_green_run"]
    assert green["commit"] == "202fbf58b450f35ef631009f65356d5cdf562547"
    assert green["workflow_run"] == 33968651171
    assert green["job"] == 101313136601
    assert green["python"] == "3.13.15"
    assert green["compile"] == "success"
    assert green["test_summary"] == "187 passed, 1 skipped in 3.29s"
    assert green["result"] == "success"

    next_input = report["next_required_input"]
    assert next_input["highest_value_exact_identity"].endswith(
        "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a"
    )
