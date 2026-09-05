from __future__ import annotations

import json
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def test_recovery_frontier_keeps_historical_recovery_separate_from_product_promotion() -> None:
    path = _repo() / "rocketdict" / "recovered" / "recovery-frontier-2026-09-05.json"
    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["schema"] == "rocketdict-core-recovery-frontier/4"
    assert report["promotion_allowed"] is False
    assert report["product_execution_allowed"] is False
    assert report["exact_03040_core_complete"] is False
    assert report["known_late_artifact_bytes_available_in_current_runtime"] is False

    preferred = report["preferred_recovery_candidate"]
    assert preferred["version"] == "0.30.34"
    assert preferred["artifact_kind"] == "full_checkpoint_zip"
    assert preferred["name"] == "RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip"
    assert preferred["sha256"] == "3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387"
    assert preferred["historical_bytes"] is None
    assert preferred["exact_catalog_identity_required_for_this_known_name"] is True
    assert preferred["historical_verification"] == {
        "unzip_test_ok": True,
        "fault_injection_tests": "7/7 passed",
        "targeted_regressions": "34/34 passed",
        "compileall_ok": True,
        "wheel_install_check_ok": True,
        "source_wheel_parity_ok": True,
        "explicit_user_handoff": True,
    }
    assert preferred["promotion_allowed"] is False

    alternate = report["alternate_recovery_candidate"]
    assert alternate["artifact_kind"] == "wheel"
    assert alternate["name"] == "rocketdict-0.30.34-py3-none-any.whl"
    assert alternate["sha256"] == "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a"
    assert alternate["promotion_allowed"] is False

    correction = report["correction"]
    assert correction["superseded_claim"] == "Stage6Y release ZIP packaging did not finish"
    assert "was created" in correction["corrected_fact"]
    assert correction["fabricated_metadata"] is False
    assert correction["unknown_zip_byte_size_left_null"] is True

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
    assert report["recovery_priority"][0]["preferred_artifact"] == "exact full ZIP; exact wheel alternate"

    exact = report["current_exact_03040_overlay"]
    assert exact == {
        "intended_members": 19,
        "exact_target_available": 2,
        "exact_target_missing": 17,
        "exact_public_api_modules_recovered": 0,
    }

    tooling = report["tooling"]
    assert tooling["lower_level_zip_scan_schema"] == "rocketdict-workbench-core-recovery-scan/3"
    assert tooling["full_checkpoint_recovery_schema"] == "rocketdict-workbench-full-checkpoint-recovery/2"
    assert tooling["wheel_integrity_schema"] == "rocketdict-workbench-wheel-integrity/2"
    assert tooling["wheel_recovery_schema"] == "rocketdict-workbench-core-wheel-recovery/5"
    assert tooling["wheel_runtime_probe_schema"] == "rocketdict-workbench-core-wheel-runtime-probe/2"
    assert tooling["unified_scan_schema"] == "rocketdict-workbench-core-recovery-scan/8"
    assert "rocketdict-recover-checkpoint" in tooling["commands"]

    identity_rule = tooling["archive_identity_rule"]
    assert "exact SHA-256 is sufficient" in identity_rule
    assert "historical size is known" in identity_rule
    assert "must also match" in identity_rule
    assert "Filename alone never proves identity" in identity_rule
    assert "never guessed" in identity_rule

    assert tooling["full_checkpoint_proof_order"] == [
        "outer ZIP safety, duplicate-name and CRC checks",
        "known historical checkpoint catalog identity",
        "unique RocketDict source-root discovery and source version/API SHA inventory",
        "nested RocketDict wheel ZIP/METADATA/WHEEL/RECORD integrity",
        "nested wheel historical catalog SHA/optional-size identity",
        "source-to-wheel package byte parity",
        "explicitly bounded README/report/manifest/state evidence inventory with non-silent truncation",
        "historical-base to exact 0.30.40 compatibility plan",
    ]
    blockers = tooling["full_checkpoint_fail_closed_blockers"]
    assert "nested_rocketdict_wheel_integrity_failed" in blockers
    assert "nested_rocketdict_wheel_historical_catalog_exact_identity_mismatch" in blockers
    assert "source_wheel_parity_incomplete" in blockers
    assert tooling["full_checkpoint_api_inventory"] == [
        "src/rocketdict/api/contracts.py",
        "src/rocketdict/api/client.py",
        "src/rocketdict/api/cli.py",
    ]
    evidence = tooling["full_checkpoint_evidence_inventory"]
    assert evidence == {
        "member_limit": 200,
        "member_hash_limit_bytes": 8388608,
        "publishes_eligible_count": True,
        "publishes_selected_count": True,
        "publishes_truncated": True,
        "silent_truncation_allowed": False,
    }

    assert tooling["wheel_proof_order"] == [
        "container/METADATA/WHEEL/RECORD integrity",
        "known historical checkpoint catalog identity when basename matches",
        "packaged RocketDict structural inspection",
        "historical-base to recovered-0.30.40 compatibility plan",
        "optional isolated network-denied zipimport runtime proof",
    ]
    assert "wheel_record_missing" in tooling["wheel_integrity_hard_failures"]
    assert "wheel_record_verification_failed" in tooling["wheel_integrity_hard_failures"]

    probe = tooling["wheel_runtime_probe"]
    assert probe["default"] == "not_requested"
    assert probe["wheel_opt_in_flag"] == "--probe-runtime"
    assert probe["scan_opt_in_flag"] == "--probe-wheels"
    assert "SHA-256 before/after" in probe["artifact_binding"]
    assert "audit hook" in probe["network_guard"]
    assert "transitively loaded rocketdict.*" in probe["module_origin_guard"]
    assert "exact 0.30.40 compatibility" in probe["not_proven"]
    assert "Product dispatch readiness" in probe["not_proven"]

    assert set(tooling["ci_installed_cli_smoke"]) == {
        "rocketdict-recover-core",
        "rocketdict-recover-plan",
        "rocketdict-recover-checkpoint",
        "rocketdict-recover-wheel",
        "rocketdict-recover-scan",
        "rocketdict-product-run",
    }

    failed = report["validation"]["preserved_failed_runs"]
    schema_failure = next(row for row in failed if row.get("workflow_run") == 33975210119)
    assert schema_failure["commit"] == "a887bf1bfb11ff99ed2e41171f9871e6cef4d24c"
    assert schema_failure["test_summary"] == "1 failed, 200 passed, 1 skipped in 2.49s"
    assert "expected unified scan schema /7 instead of /8" in schema_failure["finding"]

    green = report["validation"]["latest_green_run"]
    assert green["commit"] == "ed86467011efb5a680647e56007728d0cbb16157"
    assert green["workflow_run"] == 33975530978
    assert green["job"] == 101331437743
    assert green["runner"] == "Ubuntu 24.04.4"
    assert green["python"] == "3.13.15"
    assert green["compile"] == "success"
    assert green["installed_cli_smoke"] == "success"
    assert green["test_summary"] == "203 passed, 1 skipped in 2.46s"
    assert green["result"] == "success"
    assert any("never silently truncates" in item for item in green["proved"])
    assert any("unified scan /8" in item for item in green["proved"])

    next_input = report["next_required_input"]
    assert next_input["highest_value_exact_identity"].endswith(
        "3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387"
    )
    assert next_input["alternate_exact_identity"].endswith(
        "76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a"
    )
    steps = "\n".join(report["next_steps_when_bytes_exist"])
    assert "rocketdict-recover-checkpoint" in steps
    assert "source-to-wheel parity" in steps
    assert "17 missing exact 0.30.40 overlay targets" in steps
