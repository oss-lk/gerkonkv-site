from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .core import RocketDictCore


PROJECT_SCHEMA = "rocketdict-workbench-project/1"
SUPPORTED_SOURCE_SUFFIXES = {".srt", ".vtt", ".ass", ".ssa", ".txt"}


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data: Path
    database: Path
    uploads: Path
    configurations: Path
    experiments: Path
    reports: Path
    exports: Path
    logs: Path
    metadata: Path


def paths(root: Path | str) -> ProjectPaths:
    root = Path(root).expanduser().resolve()
    data = root / "data"
    return ProjectPaths(
        root=root,
        data=data,
        database=data / "rocketdict.sqlite",
        uploads=root / "uploads",
        configurations=root / "configurations",
        experiments=root / "experiments",
        reports=root / "reports",
        exports=root / "exports",
        logs=root / "logs",
        metadata=root / "workbench.json",
    )


class WorkbenchProject:
    def __init__(self, root: Path | str, core: RocketDictCore) -> None:
        self.paths = paths(root)
        self.core = core
        if not self.paths.metadata.is_file():
            raise FileNotFoundError(f"Workbench project metadata not found: {self.paths.metadata}")

    @classmethod
    def create(cls, root: Path | str, *, name: str, core: RocketDictCore, overwrite_empty: bool = False) -> "WorkbenchProject":
        p = paths(root)
        if p.root.exists() and any(p.root.iterdir()) and not overwrite_empty:
            raise FileExistsError(f"Project directory is not empty: {p.root}")
        for folder in (p.root, p.data, p.uploads, p.configurations, p.experiments, p.reports, p.exports, p.logs):
            folder.mkdir(parents=True, exist_ok=True)
        doctor = core.doctor()
        if not doctor.available:
            raise RuntimeError(f"Real RocketDict core is unavailable: {doctor.error}")
        core.bootstrap_database(p.database)
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "schema": PROJECT_SCHEMA,
            "name": str(name),
            "created_at": now,
            "updated_at": now,
            "core": asdict(doctor),
            "inputs": [],
            "research_runs": [],
            "invariants": {
                "fake_or_identity_mt_allowed": False,
                "research_results_overwrite_product_results": False,
                "source_files_copied_before_processing": True,
                "reports_self_contained": True,
            },
        }
        p.metadata.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return cls(p.root, core)

    def metadata(self) -> dict[str, Any]:
        return json.loads(self.paths.metadata.read_text(encoding="utf-8"))

    def _save_metadata(self, value: dict[str, Any]) -> None:
        value["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = self.paths.metadata.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.paths.metadata)

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def import_source(self, source: Path | str, *, force_text: bool = False) -> dict[str, Any]:
        source = Path(source).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        suffix = source.suffix.lower()
        if suffix not in SUPPORTED_SOURCE_SUFFIXES:
            raise ValueError(f"Unsupported source type {suffix!r}; supported: {', '.join(sorted(SUPPORTED_SOURCE_SUFFIXES))}")
        digest = self._sha256(source)
        copied = self.paths.uploads / f"{digest[:16]}-{source.name}"
        if not copied.exists():
            shutil.copy2(source, copied)
        imported = self.core.import_source(copied, data_root=self.paths.data)
        declared_format = suffix.lstrip(".")
        interpreted = self.core.interpret_source(
            int(imported["import_event_id"]),
            data_root=self.paths.data,
            declared_format=declared_format,
            force_text=force_text,
        )
        if suffix in {".srt", ".vtt", ".ass", ".ssa"} and interpreted.get("selected_format") != declared_format:
            doctor = self.core.doctor()
            detail = ""
            if not doctor.capabilities.get("pysubs2", False):
                detail = " Subtitle runtime pysubs2 is unavailable in the selected RocketDict environment."
            raise RuntimeError(
                f"Subtitle source {source.name!r} was not accepted as {declared_format}; "
                f"core selected {interpreted.get('selected_format')!r}. Refusing silent subtitle→TXT degradation.{detail}"
            )
        record = {
            "source_name": source.name,
            "copied_path": str(copied.relative_to(self.paths.root)),
            "sha256": digest,
            "byte_size": source.stat().st_size,
            "suffix": suffix,
            "import": imported,
            "interpretation": interpreted,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
        meta = self.metadata()
        existing = [x for x in meta.get("inputs", []) if x.get("sha256") == digest]
        if not existing:
            meta.setdefault("inputs", []).append(record)
            self._save_metadata(meta)
        return record

    def status(self, *, probe_runtime: bool = False) -> dict[str, Any]:
        doctor = asdict(self.core.doctor())
        project = self.core.project_summary(self.paths.database)
        dashboard = self.core.lab_dashboard(self.paths.database, probe_runtime=probe_runtime)
        return {
            "project": self.metadata(),
            "core": doctor,
            "core_project": project,
            "lab_summary": dashboard.get("summary"),
            "database": str(self.paths.database),
        }

    def lab_catalog(self, *, probe_runtime: bool = False) -> dict[str, Any]:
        return self.core.lab_dashboard(self.paths.database, probe_runtime=probe_runtime)

    def save_default_configuration(self, *, filename: str = "production-default.json") -> Path:
        manifest = self.lab_catalog(probe_runtime=False)
        stages = []
        for stage in manifest.get("stages", []):
            implementations = list(stage.get("implementations") or [])
            selected = next((x for x in implementations if x.get("production_eligible") and not x.get("testing_only") and x.get("availability", {}).get("available")), None)
            if selected is None:
                selected = next((x for x in implementations if x.get("production_eligible") and not x.get("testing_only")), implementations[0] if implementations else None)
            if selected is None:
                continue
            params = {c["key"]: c.get("default") for c in selected.get("controls", []) if c.get("default") is not None}
            stages.append({
                "stage_number": stage["number"],
                "stage_key": stage["key"],
                "enabled": True,
                "implementation": selected["implementation_key"],
                "parameters": params,
                "analytics": {"enabled": True, "resource_sampling": True, "retain_diagnostics": True},
            })
        config = {
            "format_version": "rocketdict-lab-config/1.0",
            "source_language": manifest.get("source_language", "en"),
            "target_language": manifest.get("target_language", "ru"),
            "registry_hash": manifest.get("registry_hash"),
            "plugins": [],
            "policy": {
                "commercial_only": False, "redistributable_only": False,
                "allow_testing_profiles": False, "allow_unavailable_profiles": False,
                "retain_alternative_outputs": True, "analytics_enabled": True,
            },
            "stages": stages,
            "workbench_note": "Registry-derived candidate; authoritative core validation/preflight is required before execution",
        }
        target = self.paths.configurations / filename
        target.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def create_research_campaign(self, definition: dict[str, Any], *, pipeline: bool = False) -> dict[str, Any]:
        created = (
            self.core.create_lab_pipeline_campaign(self.paths.database, definition)
            if pipeline
            else self.core.create_lab_campaign(self.paths.database, definition)
        )
        definition_id = int(created.get("id") or created.get("definition_version_id"))
        plan = self.core.create_experiment_plan(self.paths.database, definition_id)
        plan_id = int(plan.get("id") or plan.get("plan_id"))
        meta = self.metadata()
        meta.setdefault("research_runs", []).append(
            {
                "definition_version_id": definition_id,
                "plan_id": plan_id,
                "pipeline": bool(pipeline),
                "definition": definition,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._save_metadata(meta)
        return {"definition": created, "plan": plan}
