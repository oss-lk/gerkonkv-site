from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .product_policy import validate_product_configuration
from .product_profile import PROFILE_SCHEMA, QUALITY_GATES, build_product_profile
from .project import WorkbenchProject

PREFLIGHT_SCHEMA = "rocketdict-workbench-product-preflight/3"
REQUIRED_CORE_STAGES = (8, 10, 12, 14, 16, 17, 19)
HARD_QUALITY_STAGE = 15
SUBTITLE_SUFFIXES = {".srt", ".vtt", ".ass", ".ssa"}


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_kind_from_suffix(suffix: str) -> str:
    suffix = suffix.casefold()
    if suffix in SUBTITLE_SUFFIXES:
        return "subtitle"
    if suffix == ".txt":
        return "text"
    raise RuntimeError(f"Product preflight does not accept source suffix {suffix!r}")


def _select_source(project: WorkbenchProject, source_sha256: str | None) -> dict[str, Any]:
    inputs = list(project.metadata().get("inputs") or [])
    if not inputs:
        raise RuntimeError("Product preflight requires an imported immutable source")
    if source_sha256:
        wanted = source_sha256.casefold()
        rows = [row for row in inputs if str(row.get("sha256") or "").casefold() == wanted]
        if len(rows) != 1:
            raise RuntimeError(f"Imported source SHA is not unique/present: {source_sha256}")
        return dict(rows[0])
    if len(inputs) != 1:
        raise RuntimeError("Project has multiple imported sources; --source-sha256 is required for Product Mode")
    return dict(inputs[0])


def _verify_source_copy(project: WorkbenchProject, source: dict[str, Any]) -> dict[str, Any]:
    expected_sha = str(source.get("sha256") or "").casefold()
    if len(expected_sha) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha):
        raise RuntimeError("Imported source metadata lacks a valid SHA-256")
    relative = Path(str(source.get("copied_path") or ""))
    if not relative.parts or relative.is_absolute():
        raise RuntimeError("Imported source copied_path must be project-relative")
    root = project.paths.root.resolve()
    copied = (root / relative).resolve()
    try:
        copied.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Imported source copied_path escapes the Workbench project") from exc
    if not copied.is_file():
        raise RuntimeError(f"Immutable source copy is missing: {copied}")
    actual_sha = _file_sha256(copied)
    if actual_sha != expected_sha:
        raise RuntimeError(f"Immutable source copy SHA changed: {actual_sha} != {expected_sha}")
    actual_bytes = copied.stat().st_size
    expected_bytes = int(source.get("byte_size") or 0)
    if expected_bytes <= 0 or actual_bytes != expected_bytes:
        raise RuntimeError(f"Immutable source copy size changed: {actual_bytes} != {expected_bytes}")

    import_payload = dict(source.get("import") or {})
    interpretation_payload = dict(source.get("interpretation") or {})
    import_event_id = int(import_payload.get("import_event_id") or 0)
    document_version_id = int(interpretation_payload.get("document_version_id") or 0)
    selected_format = str(interpretation_payload.get("selected_format") or "").casefold()
    if import_event_id <= 0:
        raise RuntimeError("Imported source metadata lacks durable import_event_id")
    if document_version_id <= 0:
        raise RuntimeError("Imported source metadata lacks durable document_version_id")
    if not selected_format:
        raise RuntimeError("Imported source metadata lacks selected interpretation format")

    return {
        "sha256": actual_sha,
        "byte_size": actual_bytes,
        "suffix": str(source.get("suffix") or "").casefold(),
        "copied_path": str(relative.as_posix()),
        "source_name": str(source.get("source_name") or ""),
        "import_event_id": import_event_id,
        "document_version_id": document_version_id,
        "selected_format": selected_format,
        "import_identity_sha256": _canonical_sha256(import_payload),
        "interpretation_identity_sha256": _canonical_sha256(interpretation_payload),
    }


def _execution_config(profile: dict[str, Any]) -> dict[str, Any]:
    stages = []
    for key, stage in sorted((profile.get("stages") or {}).items(), key=lambda item: int(item[0])):
        stages.append(
            {
                "stage_number": int(key),
                "enabled": True,
                "implementation": stage.get("implementation"),
                "parameters": dict(stage.get("parameters") or {}),
            }
        )
    return {"stages": stages}


def _execution_contract(row: dict[str, Any], number: int, *, label: str = "stage") -> tuple[str, list[str]]:
    stage_key = str(row.get("stage_key") or "")
    if not stage_key:
        raise RuntimeError(f"Product {label} {number} lacks live registry stage_key execution identity")
    if "required_inputs" not in row:
        raise RuntimeError(f"Product {label} {number} lacks live registry required_inputs execution contract")
    required_inputs = row.get("required_inputs")
    if not isinstance(required_inputs, list) or any(not isinstance(value, str) or not value for value in required_inputs):
        raise RuntimeError(f"Product {label} {number} has invalid live registry required_inputs execution contract")
    if len(set(required_inputs)) != len(required_inputs):
        raise RuntimeError(f"Product {label} {number} has duplicate live registry required_inputs")
    return stage_key, list(required_inputs)


def _descriptor(row: dict[str, Any], context: str) -> str:
    value = str(row.get("adapter_descriptor_hash") or "").casefold()
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise RuntimeError(f"{context} lacks a valid SHA-256 adapter descriptor identity")
    return value


def _assert_runtime_available(profile: dict[str, Any]) -> None:
    stages = profile.get("stages") or {}
    for number in REQUIRED_CORE_STAGES:
        row = stages.get(str(number))
        if not isinstance(row, dict):
            raise RuntimeError(f"Product profile is missing required core stage {number}")
        availability = row.get("availability") or {}
        if availability.get("available") is not True:
            raise RuntimeError(
                f"Product stage {number} implementation {row.get('implementation')!r} is not locally available: {availability}"
            )
        _execution_contract(row, number)
        _descriptor(row, f"Product stage {number}")

    gates = list(profile.get("quality_gates") or [])
    actual = tuple(str(row.get("implementation") or "") for row in gates)
    if actual != QUALITY_GATES:
        raise RuntimeError(f"Product hard quality gate identity changed: {actual} != {QUALITY_GATES}")
    if len(gates) != len(QUALITY_GATES):
        raise RuntimeError("Product hard quality gate set is incomplete")
    for row in gates:
        implementation = str(row.get("implementation") or "")
        if int(row.get("stage_number") or 0) != HARD_QUALITY_STAGE:
            raise RuntimeError(f"Product hard gate {implementation!r} is not explicitly Stage15")
        if row.get("hard_gate") is not True:
            raise RuntimeError(f"Product quality gate {implementation!r} is not marked hard")
        if row.get("requires_reference") is not False:
            raise RuntimeError(f"Product hard gate {implementation!r} unexpectedly requires a reference")
        availability = row.get("availability") or {}
        if availability.get("available") is not True:
            raise RuntimeError(f"Product hard gate {implementation!r} is not locally available: {availability}")
        _execution_contract(row, HARD_QUALITY_STAGE, label=f"hard gate {implementation!r} at stage")
        _descriptor(row, f"Product hard gate {implementation!r}")


def _freeze_execution_identity(row: dict[str, Any], number: int, *, label: str = "stage") -> dict[str, Any]:
    stage_key, required_inputs = _execution_contract(row, number, label=label)
    descriptor = _descriptor(row, f"Product {label} {number}")
    implementation = str(row.get("implementation") or "")
    if not implementation:
        raise RuntimeError(f"Product {label} {number} lacks implementation identity")
    parameters = dict(row.get("parameters") or {})
    contract = {
        "stage_number": number,
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters": parameters,
        "required_inputs": required_inputs,
    }
    return {
        "stage_number": number,
        "stage_key": stage_key,
        "implementation": implementation,
        "adapter_descriptor_hash": descriptor,
        "parameters_sha256": _canonical_sha256(parameters),
        "required_inputs": required_inputs,
        "execution_contract_sha256": _canonical_sha256(contract),
    }


def build_product_preflight(
    project: WorkbenchProject,
    *,
    source_sha256: str | None = None,
    source_kind: str | None = None,
) -> dict[str, Any]:
    """Freeze exact source, core, registry, Product stages and Stage15 hard gates."""
    doctor = project.core.doctor()
    if not doctor.available:
        raise RuntimeError(f"Real RocketDict core is unavailable: {doctor.error}")
    source_record = _select_source(project, source_sha256)
    source = _verify_source_copy(project, source_record)
    inferred_kind = _source_kind_from_suffix(source["suffix"])
    if source_kind is not None and source_kind != inferred_kind:
        raise RuntimeError(f"Requested Product source kind {source_kind!r} conflicts with imported {inferred_kind!r} source")

    manifest = project.lab_catalog(probe_runtime=True)
    registry_hash = str(manifest.get("registry_hash") or "")
    if not registry_hash:
        raise RuntimeError("Live Lab Registry did not provide registry_hash")
    profile = build_product_profile(manifest, source_kind=inferred_kind)
    if profile.get("schema") != PROFILE_SCHEMA:
        raise RuntimeError(f"Unexpected Product profile schema: {profile.get('schema')!r}")
    if profile.get("registry_hash") != registry_hash:
        raise RuntimeError("Product profile registry identity differs from live Lab Registry")
    _assert_runtime_available(profile)
    warnings = validate_product_configuration(_execution_config(profile), manifest)

    selected = {
        str(number): _freeze_execution_identity(profile["stages"][str(number)], number)
        for number in REQUIRED_CORE_STAGES
    }
    quality_gates = []
    for row in profile.get("quality_gates") or []:
        implementation = str(row.get("implementation") or "")
        frozen = _freeze_execution_identity(
            row,
            HARD_QUALITY_STAGE,
            label=f"hard gate {implementation!r} at stage",
        )
        frozen.update(
            {
                "hard_gate": True,
                "requires_reference": False,
            }
        )
        quality_gates.append(frozen)

    gate_set_identity = {
        "stage_number": HARD_QUALITY_STAGE,
        "implementations": [row["implementation"] for row in quality_gates],
        "gates": quality_gates,
    }
    identity = {
        "source": source,
        "source_kind": inferred_kind,
        "core": {
            "python": doctor.python,
            "rocketdict_version": doctor.rocketdict_version,
            "api_version": doctor.api_version,
        },
        "registry_hash": registry_hash,
        "required_core_stages": selected,
        "quality_gates": quality_gates,
        "quality_gate_set_sha256": _canonical_sha256(gate_set_identity),
        "profile_sha256": _canonical_sha256(profile),
    }
    identity["fingerprint"] = _canonical_sha256(identity)
    return {
        "schema": PREFLIGHT_SCHEMA,
        "status": "ready",
        "identity": identity,
        "profile": profile,
        "policy_warnings": list(warnings),
        "network_required_during_processing": False,
        "fake_or_identity_mt_allowed": False,
    }


def write_product_preflight(path: Path | str, payload: dict[str, Any]) -> Path:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path
