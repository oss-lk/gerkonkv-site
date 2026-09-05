from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_stage8_recovery_members_and_fail_closed_boundary() -> None:
    repo = Path(__file__).resolve().parents[2]
    root = repo / "rocketdict" / "recovered" / "stage8-0.30.40"
    recovery = json.loads((root / "recovery.json").read_text(encoding="utf-8"))

    assert recovery["schema"] == "rocketdict-stage8-runtime-recovery/1"
    assert recovery["promotion_allowed"] is False
    assert recovery["active_product_core_recovered"] is False

    expected = {
        "src/rocketdict/__init__.py": (
            502,
            "7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c",
        ),
        "src/rocketdict/nlp/registry.py": (
            29072,
            "02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69",
        ),
    }
    members = {row["path"]: row for row in recovery["stage8_overlay_prefix"]["complete_members"]}
    assert set(members) == set(expected)
    for archive_path, (size, sha256) in expected.items():
        row = members[archive_path]
        preserved = repo / row["preserved_in_repository"]
        assert preserved.is_file()
        assert preserved.stat().st_size == size == row["bytes"]
        assert _sha256(preserved) == sha256 == row["sha256"]

    incomplete = recovery["stage8_overlay_prefix"]["next_incomplete_member"]
    assert incomplete == {
        "path": "src/rocketdict/lab/stage12_pilot.py",
        "declared_bytes": 51356,
        "complete": False,
    }

    blocker = recovery["runtime_blocker"]
    assert blocker["status"] == "exact_core_incomplete"
    assert blocker["runnable_product_core"] is False
    assert blocker["structured_callable_mapping_recovered"] is False
    assert blocker["full_required_stage_implementations_recovered"] is False
    assert blocker["missing_public_api_modules_proven_by_package_root"] == [
        "rocketdict.api.contracts",
        "rocketdict.api.client",
        "rocketdict.api.cli",
    ]


def test_recovered_package_root_proves_03040_but_is_not_imported_as_active_core() -> None:
    repo = Path(__file__).resolve().parents[2]
    package_root = repo / "rocketdict/recovered/stage8-0.30.40/src/rocketdict/__init__.py"
    text = package_root.read_text(encoding="utf-8")
    assert '__version__ = "0.30.40"' in text
    assert "from rocketdict.api.contracts import API_VERSION" in text
    assert "from rocketdict.api.client import RocketDictAPI" in text
    # Evidence lives outside rocketdict-workbench/src and is intentionally not
    # made importable as the active runtime by the Workbench package.
    assert "rocketdict/recovered/stage8-0.30.40" not in str(Path(__file__).resolve().parents[1] / "src")
