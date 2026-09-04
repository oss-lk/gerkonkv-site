from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .product_preflight import PREFLIGHT_SCHEMA

RUN_STATE_SCHEMA = "rocketdict-workbench-product-run/1"
API_PROBE_SCHEMA = "rocketdict-core-api-surface-probe/1"
STEP_ORDER = (
    "preflight",
    "upstream_contract_probe",
    "upstream_execution",
    "stage20_downstream",
    "cards",
    "export",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").casefold()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _validate_preflight(preflight: dict[str, Any]) -> dict[str, Any]:
    if preflight.get("schema") != PREFLIGHT_SCHEMA:
        raise RuntimeError(f"Unsupported Product preflight schema: {preflight.get('schema')!r}")
    if preflight.get("status") != "ready":
        raise RuntimeError(f"Product preflight is not ready: {preflight.get('status')!r}")
    identity = preflight.get("identity") or {}
    fingerprint = str(identity.get("fingerprint") or "").casefold()
    if not _valid_sha256(fingerprint):
        raise RuntimeError("Product preflight lacks a valid immutable fingerprint")
    source = identity.get("source") or {}
    if int(source.get("import_event_id") or 0) <= 0:
        raise RuntimeError("Product preflight lacks durable import_event_id")
    if int(source.get("document_version_id") or 0) <= 0:
        raise RuntimeError("Product preflight lacks durable document_version_id")
    if not str(source.get("selected_format") or ""):
        raise RuntimeError("Product preflight lacks selected source format")
    core = identity.get("core") or {}
    if not str(core.get("rocketdict_version") or "") or not str(core.get("api_version") or ""):
        raise RuntimeError("Product preflight lacks real core/API identity")
    if not str(identity.get("registry_hash") or ""):
        raise RuntimeError("Product preflight lacks registry_hash")
    return dict(identity)


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _root_identity(preflight_identity: dict[str, Any]) -> dict[str, Any]:
    source = preflight_identity["source"]
    root = {
        "preflight_fingerprint": str(preflight_identity["fingerprint"]).casefold(),
        "source_sha256": str(source.get("sha256") or "").casefold(),
        "import_event_id": int(source["import_event_id"]),
        "document_version_id": int(source["document_version_id"]),
        "selected_format": str(source["selected_format"]),
        "registry_hash": str(preflight_identity["registry_hash"]),
        "core": dict(preflight_identity["core"]),
    }
    root["fingerprint"] = _canonical_sha256(root)
    return root


def _new_state(preflight: dict[str, Any], root_identity: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    steps = {name: {"status": "pending", "attempts": 0} for name in STEP_ORDER}
    steps["preflight"] = {
        "status": "completed",
        "attempts": 1,
        "completed_at": now,
        "result_sha256": _canonical_sha256(preflight),
        "result": preflight,
    }
    return {
        "schema": RUN_STATE_SCHEMA,
        "created_at": now,
        "updated_at": now,
        "status": "awaiting_upstream_binding",
        "root_identity": root_identity,
        "steps": steps,
    }


def _load_or_create_state(path: Path, preflight: dict[str, Any], root_identity: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        state = _new_state(preflight, root_identity)
        _save_state(path, state)
        return state
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != RUN_STATE_SCHEMA:
        raise RuntimeError(f"Unsupported Product run state schema: {state.get('schema')!r}")
    existing = state.get("root_identity") or {}
    if existing.get("fingerprint") != root_identity["fingerprint"]:
        raise RuntimeError(
            "Product run state belongs to different immutable preflight inputs: "
            f"{existing.get('fingerprint')} != {root_identity['fingerprint']}"
        )
    step = (state.get("steps") or {}).get("preflight") or {}
    if step.get("status") != "completed":
        raise RuntimeError("Product run state lost its completed preflight root")
    if step.get("result_sha256") != _canonical_sha256(preflight):
        raise RuntimeError("Product run preflight payload changed while immutable fingerprint stayed constant")
    return state


_API_PROBE_CODE = r'''
import argparse
import hashlib
import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path

import rocketdict
import rocketdict.api as api_pkg
from rocketdict.api.contracts import API_VERSION


def canon(value):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def source_sha(module):
    try:
        text=inspect.getsource(module)
    except Exception:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parser_paths(parser,prefix=()):
    out=[]
    for action in getattr(parser,"_actions",[]):
        choices=getattr(action,"choices",None)
        if isinstance(choices,dict):
            for name,sub in choices.items():
                if isinstance(name,str) and isinstance(sub,argparse.ArgumentParser):
                    path=" ".join((*prefix,name))
                    out.append(path)
                    out.extend(parser_paths(sub,(*prefix,name)))
    return out


def no_required_parameters(fn):
    try:
        sig=inspect.signature(fn)
    except Exception:
        return False
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL,p.VAR_KEYWORD):
            continue
        if p.default is p.empty:
            return False
    return True

modules=[api_pkg.__name__]
try:
    modules.extend(sorted(info.name for info in pkgutil.iter_modules(api_pkg.__path__,api_pkg.__name__+".")))
except Exception:
    pass

module_rows=[]
parser_commands=set()
mapping_keys=set()
for name in modules:
    row={"module":name,"imported":False,"source_sha256":None,"parser_builders":[],"callable_mapping_names":[]}
    try:
        mod=importlib.import_module(name)
        row["imported"]=True
        row["source_sha256"]=source_sha(mod)
        for attr,obj in vars(mod).items():
            if attr.startswith("_"):
                continue
            if isinstance(obj,dict) and obj and all(isinstance(k,str) for k in obj):
                callable_keys=sorted(k for k,v in obj.items() if callable(v))
                if callable_keys:
                    row["callable_mapping_names"].append({"name":attr,"keys":callable_keys})
                    mapping_keys.update(callable_keys)
            if callable(obj) and "parser" in attr.casefold() and getattr(obj,"__module__",None)==name and no_required_parameters(obj):
                try:
                    candidate=obj()
                except Exception:
                    continue
                if isinstance(candidate,argparse.ArgumentParser):
                    paths=sorted(set(parser_paths(candidate)))
                    row["parser_builders"].append({"name":attr,"commands":paths})
                    parser_commands.update(paths)
    except Exception as exc:
        row["error"]={"type":type(exc).__name__,"message":str(exc)}
    module_rows.append(row)

payload={
    "schema":"rocketdict-core-api-surface-probe/1",
    "status":"observed",
    "database":{"path":str(Path(sys.argv[1]).resolve()),"exists":Path(sys.argv[1]).is_file()},
    "core":{"rocketdict_version":str(getattr(rocketdict,"__version__","")),"api_version":str(API_VERSION)},
    "api_modules":module_rows,
    "parser_commands":sorted(parser_commands),
    "callable_mapping_keys":sorted(mapping_keys),
}
payload["operation_candidates"]=sorted(set(payload["parser_commands"])|set(payload["callable_mapping_keys"]))
payload["fingerprint"]=canon({k:v for k,v in payload.items() if k!="fingerprint"})
print(json.dumps(payload,ensure_ascii=False))
'''


def probe_core_api_surface(core: RocketDictCore, database: Path | str) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    result = core._run(["-c", _API_PROBE_CODE, str(database)], timeout=120)
    payload = core._parse_json(result.stdout, context="RocketDict API execution-surface probe")
    if not isinstance(payload, dict) or payload.get("schema") != API_PROBE_SCHEMA:
        raise RuntimeError(f"Unexpected RocketDict API probe payload: {payload}")
    if payload.get("status") != "observed":
        raise RuntimeError(f"RocketDict API probe did not complete: {payload.get('status')!r}")
    if not _valid_sha256(payload.get("fingerprint")):
        raise RuntimeError("RocketDict API probe lacks a valid fingerprint")
    if not isinstance(payload.get("api_modules"), list) or not payload["api_modules"]:
        raise RuntimeError("RocketDict API probe observed no API modules")
    return payload


def _validate_probe_against_preflight(probe: dict[str, Any], preflight_identity: dict[str, Any]) -> None:
    core = probe.get("core") or {}
    expected = preflight_identity.get("core") or {}
    if str(core.get("rocketdict_version") or "") != str(expected.get("rocketdict_version") or ""):
        raise RuntimeError(
            "RocketDict API probe core version drift: "
            f"{core.get('rocketdict_version')!r} != {expected.get('rocketdict_version')!r}"
        )
    if str(core.get("api_version") or "") != str(expected.get("api_version") or ""):
        raise RuntimeError(
            "RocketDict API probe API version drift: "
            f"{core.get('api_version')!r} != {expected.get('api_version')!r}"
        )


def initialize_product_run(
    core: RocketDictCore,
    database: Path | str,
    preflight: dict[str, Any],
    *,
    state_path: Path | str,
) -> dict[str, Any]:
    """Create/resume the unified Product run root and capture real-core API evidence.

    This deliberately does not execute Stage8-19 yet. The probe records the exact
    public API/CLI surface observed in the same runtime frozen by Product preflight;
    upstream execution stays pending until an operation binding is proven.
    """
    preflight_identity = _validate_preflight(preflight)
    root_identity = _root_identity(preflight_identity)
    state_path = Path(state_path).expanduser().resolve()
    state = _load_or_create_state(state_path, preflight, root_identity)
    step = state["steps"]["upstream_contract_probe"]
    cache_hit = False

    if step.get("status") == "completed":
        probe = step.get("result")
        if not isinstance(probe, dict):
            raise RuntimeError("Completed upstream contract probe has no durable result")
        if step.get("result_sha256") != _canonical_sha256(probe):
            raise RuntimeError("Completed upstream contract probe evidence was mutated")
        _validate_probe_against_preflight(probe, preflight_identity)
        cache_hit = True
    else:
        step["status"] = "running"
        step["attempts"] = int(step.get("attempts") or 0) + 1
        step["started_at"] = _now()
        step.pop("error", None)
        state["status"] = "probing_upstream_contract"
        _save_state(state_path, state)
        try:
            probe = probe_core_api_surface(core, database)
            _validate_probe_against_preflight(probe, preflight_identity)
        except Exception as exc:
            step["status"] = "failed"
            step["failed_at"] = _now()
            step["error"] = {"type": type(exc).__name__, "message": str(exc)}
            state["status"] = "failed"
            _save_state(state_path, state)
            raise
        step["status"] = "completed"
        step["completed_at"] = _now()
        step["result_sha256"] = _canonical_sha256(probe)
        step["result"] = probe

    state["status"] = "awaiting_upstream_binding"
    upstream = state["steps"]["upstream_execution"]
    if upstream.get("status") == "pending":
        upstream["blocked_reason"] = "no_verified_stage8_19_operation_binding"
    _save_state(state_path, state)
    return {
        "schema": RUN_STATE_SCHEMA,
        "status": state["status"],
        "state_path": str(state_path),
        "root_identity": root_identity,
        "probe_cache_hit": cache_hit,
        "api_probe_fingerprint": probe["fingerprint"],
        "parser_commands": list(probe.get("parser_commands") or []),
        "callable_mapping_keys": list(probe.get("callable_mapping_keys") or []),
        "operation_candidates": list(probe.get("operation_candidates") or []),
        "upstream_execution": dict(upstream),
    }
