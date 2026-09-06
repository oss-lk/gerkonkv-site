from __future__ import annotations

from pathlib import Path
from typing import Any

from rocketdict.database import bootstrap_database, project_summary


class RocketDictAPI:
    """Small in-process facade matching the maintained public API surface.

    Workbench intentionally uses the subprocess CLI for process isolation; this
    class exists for direct local integrations and for explicit API identity.
    """

    def __init__(self, database: Path | str) -> None:
        self.database = Path(database).expanduser().resolve()
        bootstrap_database(self.database)

    def project(self) -> dict[str, Any]:
        return project_summary(self.database)

    def lab_dashboard(self, *, probe_runtime: bool = False) -> dict[str, Any]:
        from .registry import lab_manifest

        return lab_manifest(probe_runtime=probe_runtime)

    def call(self, operation: str, **params: Any) -> Any:
        from .operations import OPERATIONS

        if operation not in OPERATIONS:
            raise KeyError(f"Unknown RocketDict Product Core operation {operation!r}")
        return OPERATIONS[operation](database=self.database, **params)
