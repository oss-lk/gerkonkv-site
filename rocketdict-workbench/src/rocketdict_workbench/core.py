from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable


class CoreError(RuntimeError):
    def __init__(self, message: str, *, command: list[str] | None = None, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.command = command or []
        self.stdout = stdout
        self.stderr = stderr


@dataclass(frozen=True)
class CoreDoctor:
    available: bool
    python: str
    rocketdict_version: str | None
    api_version: str | None
    capabilities: dict[str, bool]
    error: str | None


class RocketDictCore:
    """Strict subprocess bridge to an installed/unpacked real RocketDict core.

    Workbench never falls back to fake/identity MT or synthetic experiment outputs.
    A missing core/runtime is a visible hard failure.
    """

    def __init__(self, *, python: str | Path | None = None, pythonpath: Iterable[str | Path] = ()) -> None:
        self.python = str(python or sys.executable)
        self.pythonpath = tuple(str(Path(p).expanduser().resolve()) for p in pythonpath)

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.pythonpath:
            current = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = os.pathsep.join((*self.pythonpath, current) if current else self.pythonpath)
        env.setdefault("PYTHONUTF8", "1")
        return env

    def _run(self, args: list[str], *, timeout: float = 120.0, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        command = [self.python, *args]
        try:
            result = subprocess.run(
                command,
                input=input_text,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._env(),
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CoreError(f"RocketDict core process failed to start/finish: {exc}", command=command) from exc
        if result.returncode != 0:
            raise CoreError(
                f"RocketDict core command failed with exit code {result.returncode}",
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return result

    @staticmethod
    def _parse_json(text: str, *, context: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise CoreError(f"{context} did not return valid JSON: {exc}", stdout=text) from exc

    def doctor(self) -> CoreDoctor:
        code = (
            "import importlib.util,json,rocketdict; "
            "from rocketdict.api.contracts import API_VERSION; "
            "mods=['pysubs2','ctranslate2','sentencepiece','sqlalchemy']; "
            "print(json.dumps({'version':rocketdict.__version__,'api_version':API_VERSION,"
            "'capabilities':{m:(importlib.util.find_spec(m) is not None) for m in mods}}))"
        )
        try:
            result = self._run(["-c", code], timeout=20)
            payload = self._parse_json(result.stdout, context="RocketDict doctor")
            return CoreDoctor(True, self.python, str(payload.get("version")), str(payload.get("api_version")), dict(payload.get("capabilities") or {}), None)
        except Exception as exc:
            return CoreDoctor(False, self.python, None, None, {}, str(exc))

    def bootstrap_database(self, database: Path | str) -> dict[str, Any]:
        database = Path(database).expanduser().resolve()
        database.parent.mkdir(parents=True, exist_ok=True)
        code = (
            "import json,sys; from pathlib import Path; "
            "from rocketdict.database import bootstrap_database; "
            "p=Path(sys.argv[1]); e=bootstrap_database(p); e.dispose(); "
            "print(json.dumps({'database':str(p),'exists':p.is_file(),'bytes':p.stat().st_size}))"
        )
        return self._parse_json(self._run(["-c", code, str(database)], timeout=180).stdout, context="database bootstrap")

    def import_source(self, source: Path | str, *, data_root: Path | str, timeout: float = 300.0) -> dict[str, Any]:
        source = Path(source).expanduser().resolve()
        data_root = Path(data_root).expanduser().resolve()
        result = self._run(
            ["-m", "rocketdict.importing.cli", str(source), "--data-root", str(data_root)],
            timeout=timeout,
        )
        return self._parse_json(result.stdout, context="source import")

    def interpret_source(
        self,
        import_event_id: int,
        *,
        data_root: Path | str,
        declared_format: str | None = None,
        declared_encoding: str | None = None,
        force_text: bool = False,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        args = ["-m", "rocketdict.interpretation.cli", str(int(import_event_id)), "--data-root", str(Path(data_root).resolve())]
        if declared_encoding:
            args.extend(["--encoding", declared_encoding])
        if declared_format:
            args.extend(["--format", declared_format])
        if force_text:
            args.append("--force-text")
        result = self._run(args, timeout=timeout)
        return self._parse_json(result.stdout, context="source interpretation")

    def api(self, database: Path | str, *args: str, timeout: float = 300.0) -> Any:
        database = Path(database).expanduser().resolve()
        result = self._run(
            ["-m", "rocketdict.api.cli", str(database), "--compact", *map(str, args)],
            timeout=timeout,
        )
        envelope = self._parse_json(result.stdout, context=f"RocketDict API {' '.join(args[:2])}")
        if not isinstance(envelope, dict) or envelope.get("ok") is not True:
            raise CoreError(
                f"RocketDict API call failed: {envelope.get('error') if isinstance(envelope, dict) else envelope}",
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return envelope.get("data")

    def project_summary(self, database: Path | str) -> dict[str, Any]:
        return dict(self.api(database, "project"))

    def lab_dashboard(self, database: Path | str, *, probe_runtime: bool = False) -> dict[str, Any]:
        args = ["lab-dashboard"]
        if probe_runtime:
            args.append("--probe-runtime")
        return dict(self.api(database, *args, timeout=600 if probe_runtime else 120))

    def lab_default_config(self, database: Path | str) -> dict[str, Any]:
        return dict(self.api(database, "lab-config-default"))

    def lab_validate_config(self, database: Path | str, config: dict[str, Any]) -> dict[str, Any]:
        return dict(self.api(database, "call", "lab.config.validate", "--params", json.dumps({"config": config}, ensure_ascii=False)))

    def create_lab_campaign(self, database: Path | str, definition: dict[str, Any]) -> dict[str, Any]:
        return dict(
            self.api(
                database,
                "experiments",
                "lab-campaign",
                "--definition",
                json.dumps(definition, ensure_ascii=False, separators=(",", ":")),
                timeout=300,
            )
        )

    def create_lab_pipeline_campaign(self, database: Path | str, definition: dict[str, Any]) -> dict[str, Any]:
        return dict(
            self.api(
                database,
                "experiments",
                "lab-pipeline-campaign",
                "--definition",
                json.dumps(definition, ensure_ascii=False, separators=(",", ":")),
                timeout=300,
            )
        )

    def create_experiment_plan(self, database: Path | str, definition_version_id: int) -> dict[str, Any]:
        return dict(self.api(database, "experiments", "plan-create", str(int(definition_version_id))))

    def run_experiment_plan(self, database: Path | str, plan_id: int, *, max_new_trials: int | None = None, timeout: float = 7200) -> dict[str, Any]:
        args = ["experiments", "run", str(int(plan_id))]
        if max_new_trials is not None:
            args.extend(["--max-new-trials", str(int(max_new_trials))])
        return dict(self.api(database, *args, timeout=timeout))

    def experiment_analytics(self, database: Path | str, plan_id: int) -> dict[str, Any]:
        return dict(self.api(database, "experiments", "analytics", str(int(plan_id)), timeout=300))

    def experiment_plan(self, database: Path | str, plan_id: int) -> dict[str, Any]:
        return dict(self.api(database, "experiments", "plan", str(int(plan_id))))

    def export_experiment(self, database: Path | str, plan_id: int, destination: Path | str) -> dict[str, Any]:
        return dict(
            self.api(
                database,
                "experiments",
                "export",
                str(int(plan_id)),
                str(Path(destination).expanduser().resolve()),
                "--formats",
                "json,jsonl,csv,markdown",
                timeout=300,
            )
        )
