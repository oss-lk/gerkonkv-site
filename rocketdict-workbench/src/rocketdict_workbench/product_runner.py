from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .core import RocketDictCore
from .product_cefr import assess_product_cefr, verify_cefrj_asset
from .product_examples import select_product_examples
from .product_pronunciation import generate_product_pronunciations
from .sense_translation_arbitration import arbitrate_lexical_primaries

STATE_SCHEMA = "rocketdict-workbench-product-downstream/2"
STEP_ORDER = (
    "stage20_arbitration",
    "cefrj",
    "pronunciation",
    "examples",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stage20_identity(stage20_result: dict[str, Any]) -> tuple[list[int], list[int], str]:
    rows = list(stage20_result.get("results") or [])
    if not rows:
        raise RuntimeError("Product downstream runner requires at least one Stage20 result")
    normalized: list[dict[str, int]] = []
    sense_ids: list[int] = []
    entry_ids: list[int] = []
    seen_senses: set[int] = set()
    seen_entries: set[int] = set()
    for row in rows:
        sense_id = int(row.get("sense_id") or 0)
        entry_id = int(row.get("entry_id") or 0)
        revision_id = int(row.get("selection_revision_id") or 0)
        generation_run_id = int(row.get("generation_run_id") or 0)
        if min(sense_id, entry_id, revision_id, generation_run_id) <= 0:
            raise RuntimeError(f"Stage20 result lacks durable identity fields: {row}")
        if sense_id in seen_senses:
            raise RuntimeError(f"Duplicate Stage20 sense id: {sense_id}")
        seen_senses.add(sense_id)
        sense_ids.append(sense_id)
        if entry_id not in seen_entries:
            seen_entries.add(entry_id)
            entry_ids.append(entry_id)
        normalized.append(
            {
                "sense_id": sense_id,
                "entry_id": entry_id,
                "selection_revision_id": revision_id,
                "generation_run_id": generation_run_id,
            }
        )
    return sense_ids, entry_ids, _canonical_sha256(normalized)


def _input_identity(
    provider_result: dict[str, Any],
    stage20_result: dict[str, Any],
    cefr_asset: dict[str, Any],
    database: Path,
    *,
    include_russian_pronunciation_hint: bool,
) -> dict[str, Any]:
    provider_sha = str(provider_result.get("entries_sha256") or "").lower()
    if len(provider_sha) != 64 or any(c not in "0123456789abcdef" for c in provider_sha):
        raise RuntimeError("Product downstream runner requires provider entries_sha256")
    sense_ids, entry_ids, stage20_sha = _stage20_identity(stage20_result)
    identity = {
        "database": str(database.resolve()),
        "provider_entries_sha256": provider_sha,
        "provider_payload_sha256": _canonical_sha256(provider_result),
        "stage20_identity_sha256": stage20_sha,
        "stage20_payload_sha256": _canonical_sha256(stage20_result),
        "sense_ids": sense_ids,
        "entry_ids": entry_ids,
        "cefrj_sha256": str(cefr_asset.get("sha256") or "").lower(),
        "settings": {
            "include_russian_pronunciation_hint": bool(include_russian_pronunciation_hint),
            "approve_stage20_arbitration": True,
            "approve_cefrj": True,
            "approve_pronunciation": True,
            "approve_examples": True,
        },
    }
    identity["fingerprint"] = _canonical_sha256(identity)
    return identity


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _step_artifact_path(state_path: Path, name: str) -> Path:
    root = state_path.parent / f"{state_path.stem}.steps"
    return root / f"{name}.json"


def _write_step_artifact(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return {
        "path": str(path.resolve()),
        "sha256": _file_sha256(path),
        "payload_sha256": _canonical_sha256(payload),
        "byte_size": path.stat().st_size,
    }


def _load_step_artifact(reference: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(reference, dict):
        raise RuntimeError(f"Completed product step {context} has no durable artifact reference")
    path = Path(str(reference.get("path") or "")).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"Completed product step {context} artifact is missing: {path}")
    expected_bytes = int(reference.get("byte_size") or 0)
    if expected_bytes <= 0 or path.stat().st_size != expected_bytes:
        raise RuntimeError(f"Completed product step {context} artifact byte size changed")
    if str(reference.get("sha256") or "").lower() != _file_sha256(path):
        raise RuntimeError(f"Completed product step {context} artifact bytes were mutated")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Completed product step {context} artifact is not a JSON object")
    if str(reference.get("payload_sha256") or "").lower() != _canonical_sha256(payload):
        raise RuntimeError(f"Completed product step {context} canonical payload hash drift")
    return payload


def _load_or_create_state(path: Path, identity: dict[str, Any]) -> dict[str, Any]:
    if path.is_file():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("schema") != STATE_SCHEMA:
            raise RuntimeError(f"Unsupported product runner state schema: {state.get('schema')!r}")
        existing = state.get("input_identity") or {}
        if existing.get("fingerprint") != identity["fingerprint"]:
            raise RuntimeError(
                "Product runner state belongs to different immutable inputs: "
                f"{existing.get('fingerprint')} != {identity['fingerprint']}"
            )
        return state
    now = _now()
    state = {
        "schema": STATE_SCHEMA,
        "created_at": now,
        "updated_at": now,
        "status": "pending",
        "input_identity": identity,
        "steps": {name: {"status": "pending", "attempts": 0} for name in STEP_ORDER},
    }
    _save_state(path, state)
    return state


def _coverage(rows: list[dict[str, Any]], key: str, expected: list[int], *, context: str) -> None:
    actual = [int(row.get(key) or 0) for row in rows]
    if actual != expected:
        raise RuntimeError(f"{context} coverage/order mismatch: {actual} != {expected}")


def _run_step(
    state_path: Path,
    state: dict[str, Any],
    name: str,
    operation: Callable[[], dict[str, Any]],
    validator: Callable[[dict[str, Any]], None],
) -> tuple[dict[str, Any], bool]:
    step = state["steps"][name]
    if step.get("status") == "completed":
        result = _load_step_artifact(step.get("artifact"), context=name)
        validator(result)
        return result, True
    if step.get("status") in {"running", "failed"} and step.get("blocked_reason") == "manual_reconciliation_required_before_replay":
        raise RuntimeError(
            f"Product step {name} may have mutated the database during an earlier incomplete/failed attempt; "
            "manual reconciliation is required before replay"
        )

    step["status"] = "running"
    step["attempts"] = int(step.get("attempts") or 0) + 1
    step["started_at"] = _now()
    step["input_fingerprint"] = str((state.get("input_identity") or {}).get("fingerprint") or "")
    step.pop("error", None)
    step.pop("failed_at", None)
    step.pop("blocked_reason", None)
    state["status"] = "running"
    _save_state(state_path, state)
    try:
        result = operation()
        if not isinstance(result, dict):
            raise RuntimeError(f"Product step {name} returned a non-object result")
        validator(result)
        artifact = _write_step_artifact(_step_artifact_path(state_path, name), result)
    except Exception as exc:
        step["status"] = "failed"
        step["failed_at"] = _now()
        step["error"] = {"type": type(exc).__name__, "message": str(exc)}
        step["blocked_reason"] = "manual_reconciliation_required_before_replay"
        state["status"] = "failed"
        _save_state(state_path, state)
        raise
    step["status"] = "completed"
    step["completed_at"] = _now()
    step["artifact"] = artifact
    step["result_sha256"] = artifact["payload_sha256"]
    step.pop("result", None)
    step.pop("blocked_reason", None)
    state["status"] = "running"
    _save_state(state_path, state)
    return result, False


def resume_product_downstream(
    core: RocketDictCore,
    database: Path | str,
    provider_result: dict[str, Any],
    stage20_result: dict[str, Any],
    *,
    cefrj_asset: Path | str,
    state_path: Path | str,
    include_russian_pronunciation_hint: bool = False,
) -> dict[str, Any]:
    """Resume the strict Product path from Stage20 through Stage23 evidence.

    Version 2 binds the state to the exact database path and complete provider/Stage20
    payloads. Completed step payloads live in byte- and canonical-hash-verified
    sidecar artifacts. An exception after a DB-mutating step starts is fail-closed:
    replay is blocked until external/manual reconciliation rather than assuming
    undocumented idempotence.
    """
    database = Path(database).expanduser().resolve()
    state_path = Path(state_path).expanduser().resolve()
    cefr_meta = verify_cefrj_asset(cefrj_asset)
    identity = _input_identity(
        provider_result,
        stage20_result,
        cefr_meta,
        database,
        include_russian_pronunciation_hint=include_russian_pronunciation_hint,
    )
    sense_ids = list(identity["sense_ids"])
    entry_ids = list(identity["entry_ids"])
    state = _load_or_create_state(state_path, identity)
    cache_hits: dict[str, bool] = {}

    def validate_arbitration(payload: dict[str, Any]) -> None:
        rows = list(payload.get("results") or [])
        _coverage(rows, "sense_id", sense_ids, context="Stage20 arbitration")
        for row in rows:
            if row.get("status") != "approved":
                raise RuntimeError(f"Stage20 arbitration is not approved: {row}")

    arbitration, cache_hits["stage20_arbitration"] = _run_step(
        state_path,
        state,
        "stage20_arbitration",
        lambda: arbitrate_lexical_primaries(core, database, provider_result, stage20_result),
        validate_arbitration,
    )
    approved_revision_by_sense = {
        int(row["sense_id"]): int(row["selection_revision_id"])
        for row in arbitration.get("results") or []
    }

    def validate_cefr(payload: dict[str, Any]) -> None:
        _coverage(list(payload.get("results") or []), "sense_id", sense_ids, context="CEFR-J")
        if str(payload.get("source_sha256") or "").lower() != identity["cefrj_sha256"]:
            raise RuntimeError("CEFR-J result source identity differs from pinned runner input")

    cefr, cache_hits["cefrj"] = _run_step(
        state_path,
        state,
        "cefrj",
        lambda: assess_product_cefr(core, database, sense_ids, cefrj_asset=cefrj_asset, approve=True),
        validate_cefr,
    )

    def validate_pronunciation(payload: dict[str, Any]) -> None:
        rows = list(payload.get("results") or [])
        _coverage(rows, "entry_id", entry_ids, context="Pronunciation")
        if payload.get("generated_fallback_allowed") is not False:
            raise RuntimeError("Product pronunciation result did not explicitly forbid generated fallback")
        if any(row.get("generated_fallback") for row in rows):
            raise RuntimeError("Generated pronunciation leaked into Product downstream runner")

    pronunciation, cache_hits["pronunciation"] = _run_step(
        state_path,
        state,
        "pronunciation",
        lambda: generate_product_pronunciations(
            core,
            database,
            entry_ids,
            include_russian_hint=include_russian_pronunciation_hint,
            approve=True,
        ),
        validate_pronunciation,
    )

    def validate_examples(payload: dict[str, Any]) -> None:
        rows = list(payload.get("results") or [])
        _coverage(rows, "sense_id", sense_ids, context="Examples")
        if payload.get("scope_contract") != "stage23-sense-scope-v2":
            raise RuntimeError(f"Unexpected Stage23 scope contract: {payload.get('scope_contract')!r}")
        for row in rows:
            sense_id = int(row["sense_id"])
            actual_revision = int(row.get("approved_sense_translation_revision_id") or 0)
            expected_revision = approved_revision_by_sense[sense_id]
            if actual_revision != expected_revision:
                raise RuntimeError(
                    f"Stage23 review identity drift for sense {sense_id}: "
                    f"approved Stage20 revision {actual_revision} != arbitration revision {expected_revision}"
                )

    examples, cache_hits["examples"] = _run_step(
        state_path,
        state,
        "examples",
        lambda: select_product_examples(core, database, sense_ids, approve=True),
        validate_examples,
    )

    state["status"] = "completed"
    state["completed_at"] = _now()
    _save_state(state_path, state)
    return {
        "schema": STATE_SCHEMA,
        "status": "completed",
        "state_path": str(state_path),
        "input_identity": identity,
        "cache_hits": cache_hits,
        "stage20_arbitration": arbitration,
        "cefrj": cefr,
        "pronunciation": pronunciation,
        "examples": examples,
    }
