from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .lexical_opus import (
    PROVIDER_SCHEMA,
    build_opus_lexical_snapshot,
    run_stage20_with_snapshot,
)
from .product_runner import _stage20_identity, resume_product_downstream
from .quality_gate_execution import require_quality_gate_pass
from .upstream_binding import _canonical_sha256, _load_verified_evidence, _valid_sha256
from .upstream_pipeline import _record_fingerprint

OFFICIAL_OPUS_REVISION = "opus-2020-02-11"
OFFICIAL_OPUS_ARCHIVE_SHA256 = "798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677"
OFFICIAL_OPUS_SOURCE_URI = "https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip"
STAGE20_UNIFIED_SCHEMA = "rocketdict-workbench-unified-stage20/1"
STAGE20_INPUT_SCHEMA = "rocketdict-workbench-unified-stage20-input/1"
STAGE20_PROVIDER_POLICY = "contextual-lexical-opus-v3"
DEFAULT_SETTINGS = {
    "beam_size": 12,
    "num_hypotheses": 12,
    "maximum_candidates_per_lemma": 8,
    "source_policy": "aligned-local-consensus",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _model_tree_identity(model_path: Path) -> dict[str, Any]:
    model_path = model_path.expanduser().resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(model_path)
    rows = []
    total = 0
    for path in sorted((p for p in model_path.rglob("*") if p.is_file()), key=lambda p: p.relative_to(model_path).as_posix()):
        relative = path.relative_to(model_path).as_posix()
        size = path.stat().st_size
        total += size
        rows.append({"path": relative, "bytes": size, "sha256": _file_sha256(path)})
    if not rows:
        raise RuntimeError("Unified Stage20 OPUS model directory is empty")
    identity = {
        "path": str(model_path),
        "file_count": len(rows),
        "byte_size": total,
        "files": rows,
    }
    identity["tree_sha256"] = _canonical_sha256(rows)
    return identity


def _stage19_identity(state: dict[str, Any]) -> dict[str, Any]:
    record = (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {}).get("19")
    if not isinstance(record, dict) or record.get("status") != "completed":
        raise RuntimeError("Unified Stage20 requires completed Stage19")
    _record_fingerprint(record)
    result = record.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Completed Stage19 lacks durable result object")
    result_sha = str(record.get("result_sha256") or "").casefold()
    if not _valid_sha256(result_sha) or result_sha != _canonical_sha256(result):
        raise RuntimeError("Completed Stage19 result evidence was mutated")
    identities = record.get("durable_identities")
    if not isinstance(identities, dict) or not identities:
        raise RuntimeError("Completed Stage19 lacks durable identities")
    for name, value in identities.items():
        if name not in result or result[name] != value:
            raise RuntimeError(f"Stage19 durable identity {name!r} is not backed by its hashed result")
    return {
        "execution_fingerprint": str(record["fingerprint"]).casefold(),
        "result_sha256": result_sha,
        "durable_identities_sha256": _canonical_sha256(identities),
    }


def _stage20_policy(preflight: dict[str, Any]) -> dict[str, Any]:
    row = (((preflight.get("profile") or {}).get("workbench_stages") or {}).get("20_provider"))
    if not isinstance(row, dict):
        raise RuntimeError("Product profile lacks Workbench Stage20 provider policy")
    if str(row.get("implementation") or "") != STAGE20_PROVIDER_POLICY:
        raise RuntimeError(
            f"Product Stage20 provider policy drift: {row.get('implementation')!r} != {STAGE20_PROVIDER_POLICY!r}"
        )
    if row.get("retain_nbest_evidence") is not True:
        raise RuntimeError("Product Stage20 policy must retain n-best evidence")
    return dict(row)


def build_stage20_input_identity(
    state_path: Path | str,
    *,
    model_path: Path | str,
    revision: str = OFFICIAL_OPUS_REVISION,
    archive_sha256: str = OFFICIAL_OPUS_ARCHIVE_SHA256,
    source_uri: str = OFFICIAL_OPUS_SOURCE_URI,
    beam_size: int = 12,
    num_hypotheses: int = 12,
    maximum_candidates_per_lemma: int = 8,
    source_policy: str = "aligned-local-consensus",
) -> dict[str, Any]:
    path = Path(state_path).expanduser().resolve()
    state, preflight, _probe = _load_verified_evidence(path)
    pass_evidence = require_quality_gate_pass(path)
    stage19 = _stage19_identity(state)
    policy = _stage20_policy(preflight)
    if revision != OFFICIAL_OPUS_REVISION:
        raise RuntimeError(f"Product Stage20 requires pinned OPUS revision {OFFICIAL_OPUS_REVISION!r}")
    if archive_sha256.casefold() != OFFICIAL_OPUS_ARCHIVE_SHA256:
        raise RuntimeError("Product Stage20 OPUS archive SHA-256 differs from verified official release")
    if source_uri != OFFICIAL_OPUS_SOURCE_URI:
        raise RuntimeError("Product Stage20 OPUS source URI differs from verified official release")
    settings = {
        "beam_size": int(beam_size),
        "num_hypotheses": int(num_hypotheses),
        "maximum_candidates_per_lemma": int(maximum_candidates_per_lemma),
        "source_policy": str(source_policy),
    }
    if min(settings["beam_size"], settings["num_hypotheses"], settings["maximum_candidates_per_lemma"]) <= 0:
        raise ValueError("Stage20 lexical generation settings must be positive")
    model = _model_tree_identity(Path(model_path))
    identity = {
        "schema": STAGE20_INPUT_SCHEMA,
        "product_run_root_fingerprint": str((state.get("root_identity") or {}).get("fingerprint") or "").casefold(),
        "preflight_fingerprint": str((preflight.get("identity") or {}).get("fingerprint") or "").casefold(),
        "stage15_pass_fingerprint": str(pass_evidence["fingerprint"]).casefold(),
        "stage19": stage19,
        "provider_policy_sha256": _canonical_sha256(policy),
        "provider": STAGE20_PROVIDER_POLICY,
        "model": {
            "revision": revision,
            "archive_sha256": archive_sha256.casefold(),
            "source_uri": source_uri,
            "local_tree_sha256": model["tree_sha256"],
            "local_file_count": model["file_count"],
            "local_byte_size": model["byte_size"],
        },
        "settings": settings,
        "full_sense_set_required": True,
        "network_access": False,
    }
    identity["fingerprint"] = _canonical_sha256(identity)
    identity["model_tree"] = model
    return identity


def _artifact_paths(state_path: Path) -> dict[str, Path]:
    root = state_path.parent / f"{state_path.stem}.artifacts"
    return {
        "root": root,
        "provider": root / "stage20-provider.json",
        "stage20": root / "stage20-result.json",
        "downstream_state": root / "stage20-through-stage23.json",
    }


def _artifact_ref(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _atomic_json(path, payload)
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "payload_sha256": _canonical_sha256(payload),
        "byte_size": path.stat().st_size,
    }


def _load_artifact(ref: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(ref, dict):
        raise RuntimeError(f"{context} artifact reference is missing")
    path = Path(str(ref.get("path") or "")).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"{context} artifact file is missing: {path}")
    if str(ref.get("sha256") or "").casefold() != _file_sha256(path):
        raise RuntimeError(f"{context} artifact bytes were mutated")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{context} artifact payload is not an object")
    if str(ref.get("payload_sha256") or "").casefold() != _canonical_sha256(payload):
        raise RuntimeError(f"{context} artifact canonical payload hash drift")
    return payload


def _validate_provider(payload: dict[str, Any], identity: dict[str, Any]) -> None:
    if payload.get("schema") != PROVIDER_SCHEMA or payload.get("provider") != STAGE20_PROVIDER_POLICY:
        raise RuntimeError("Stage20 lexical OPUS provider schema/policy drift")
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict):
        raise RuntimeError("Stage20 provider lacks model snapshot")
    expected_model = identity["model"]
    if str(snapshot.get("revision") or "") != expected_model["revision"]:
        raise RuntimeError("Stage20 provider revision drift")
    if str(snapshot.get("sha256") or "").casefold() != expected_model["archive_sha256"]:
        raise RuntimeError("Stage20 provider archive SHA drift")
    if str(snapshot.get("source_uri") or "") != expected_model["source_uri"]:
        raise RuntimeError("Stage20 provider source URI drift")
    if snapshot.get("network_access") is not False or snapshot.get("is_smoke") is not False:
        raise RuntimeError("Stage20 provider violated offline/non-smoke Product policy")
    entries_sha = str(payload.get("entries_sha256") or "").casefold()
    if not _valid_sha256(entries_sha):
        raise RuntimeError("Stage20 provider lacks entries_sha256")
    entries = snapshot.get("entries")
    if not isinstance(entries, dict) or not entries:
        raise RuntimeError("Stage20 provider produced no lexical entries")
    if entries_sha != hashlib.sha256(
        json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest():
        raise RuntimeError("Stage20 provider entries_sha256 does not match snapshot entries")
    summary = payload.get("summary") or {}
    if int(summary.get("sense_count") or 0) <= 0:
        raise RuntimeError("Stage20 provider processed zero senses")
    if str(summary.get("backend_compute_type") or "") != "float32":
        raise RuntimeError("Stage20 provider did not use quality-acceptance float32 compute")


def _validate_stage20(payload: dict[str, Any], provider: dict[str, Any]) -> dict[str, Any]:
    rows = list(payload.get("results") or [])
    if not rows:
        raise RuntimeError("Stage20 application produced no sense results")
    expected_count = int((provider.get("summary") or {}).get("sense_count") or 0)
    if len(rows) != expected_count:
        raise RuntimeError(f"Stage20 full-sense coverage mismatch: {len(rows)} != {expected_count}")
    seen = set()
    for row in rows:
        sense_id = int(row.get("sense_id") or 0)
        if sense_id <= 0 or sense_id in seen:
            raise RuntimeError(f"Stage20 result has invalid/duplicate sense_id: {sense_id}")
        seen.add(sense_id)
        if row.get("coverage_complete") is not True:
            raise RuntimeError(f"Stage20 sense {sense_id} does not have complete lexical translation coverage")
        selected = list(row.get("selected") or [])
        if not selected or not any(str(item.get("translation") or "").strip() for item in selected):
            raise RuntimeError(f"Stage20 sense {sense_id} has no selected translation")
    sense_ids, entry_ids, stage20_identity_sha = _stage20_identity(payload)
    return {
        "sense_ids": sense_ids,
        "entry_ids": entry_ids,
        "stage20_identity_sha256": stage20_identity_sha,
        "result_count": len(rows),
    }


def run_unified_stage20(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    model_path: Path | str,
    revision: str = OFFICIAL_OPUS_REVISION,
    archive_sha256: str = OFFICIAL_OPUS_ARCHIVE_SHA256,
    source_uri: str = OFFICIAL_OPUS_SOURCE_URI,
    beam_size: int = 12,
    num_hypotheses: int = 12,
    maximum_candidates_per_lemma: int = 8,
    source_policy: str = "aligned-local-consensus",
) -> dict[str, Any]:
    state_path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    identity = build_stage20_input_identity(
        state_path,
        model_path=model_path,
        revision=revision,
        archive_sha256=archive_sha256,
        source_uri=source_uri,
        beam_size=beam_size,
        num_hypotheses=num_hypotheses,
        maximum_candidates_per_lemma=maximum_candidates_per_lemma,
        source_policy=source_policy,
    )
    state, _preflight, probe = _load_verified_evidence(state_path)
    probe_database = Path(str((probe.get("database") or {}).get("path") or "")).expanduser().resolve()
    if probe_database != database_path:
        raise RuntimeError("Unified Stage20 database differs from immutable API-probe database")
    step = state["steps"]["stage20_downstream"]
    existing_identity = step.get("input_identity")
    if existing_identity is not None and (not isinstance(existing_identity, dict) or existing_identity.get("fingerprint") != identity["fingerprint"]):
        raise RuntimeError("Unified Stage20 state belongs to different immutable Stage19/model/settings inputs")
    step["input_identity"] = identity
    artifacts = _artifact_paths(state_path)

    provider_step = step.setdefault("provider", {"status": "pending", "attempts": 0})
    if provider_step.get("status") == "completed":
        provider = _load_artifact(provider_step.get("artifact"), context="Stage20 provider")
        _validate_provider(provider, identity)
        provider_cache = True
    else:
        provider_step["status"] = "running"
        provider_step["attempts"] = int(provider_step.get("attempts") or 0) + 1
        provider_step["started_at"] = _now()
        step["status"] = "running_provider"
        state["status"] = "executing_stage20_lexical_provider"
        _save_state(state_path, state)
        try:
            provider = build_opus_lexical_snapshot(
                core,
                database_path,
                model_path=Path(model_path).expanduser().resolve(),
                revision=revision,
                archive_sha256=archive_sha256,
                source_uri=source_uri,
                sense_ids=(),
                beam_size=beam_size,
                num_hypotheses=num_hypotheses,
                maximum_candidates_per_lemma=maximum_candidates_per_lemma,
            )
            _validate_provider(provider, identity)
        except Exception as exc:
            provider_step["status"] = "failed"
            provider_step["failed_at"] = _now()
            provider_step["error"] = {"type": type(exc).__name__, "message": str(exc)}
            step["status"] = "failed"
            state["status"] = "failed"
            _save_state(state_path, state)
            raise
        provider_step["artifact"] = _artifact_ref(artifacts["provider"], provider)
        provider_step["status"] = "completed"
        provider_step["completed_at"] = _now()
        provider_cache = False
        _save_state(state_path, state)

    application = step.setdefault("stage20", {"status": "pending", "attempts": 0})
    if application.get("status") == "completed":
        stage20 = _load_artifact(application.get("artifact"), context="Stage20 result")
        stage20_identity = _validate_stage20(stage20, provider)
        application_cache = True
    else:
        if application.get("status") in {"running", "dispatch_failed_ambiguous"}:
            raise RuntimeError(
                "Previous Stage20 application may have mutated the database; no public replay-safety contract exists, manual reconciliation is required"
            )
        application["status"] = "running"
        application["attempts"] = int(application.get("attempts") or 0) + 1
        application["started_at"] = _now()
        step["status"] = "running_stage20"
        state["status"] = "executing_stage20_sense_translation"
        _save_state(state_path, state)
        try:
            stage20 = run_stage20_with_snapshot(
                core,
                database_path,
                provider,
                source_policy=source_policy,
                sense_ids=(),
            )
            stage20_identity = _validate_stage20(stage20, provider)
        except Exception as exc:
            application["status"] = "dispatch_failed_ambiguous"
            application["failed_at"] = _now()
            application["error"] = {"type": type(exc).__name__, "message": str(exc)}
            step["status"] = "failed"
            step["blocked_reason"] = "manual_reconciliation_required_before_stage20_replay"
            state["status"] = "failed"
            _save_state(state_path, state)
            raise
        application["artifact"] = _artifact_ref(artifacts["stage20"], stage20)
        application["identity"] = stage20_identity
        application["status"] = "completed"
        application["completed_at"] = _now()
        application_cache = False

    step["status"] = "stage20_completed"
    step["blocked_reason"] = "product_stage20_23_downstream_not_yet_resumed"
    state["status"] = "stage20_completed_awaiting_arbitration_cefr_pronunciation_examples"
    _save_state(state_path, state)
    return {
        "schema": STAGE20_UNIFIED_SCHEMA,
        "status": "stage20_completed",
        "input_identity": identity,
        "provider_artifact": provider_step["artifact"],
        "stage20_artifact": application["artifact"],
        "stage20_identity": stage20_identity,
        "cache_hits": {"provider": provider_cache, "stage20": application_cache},
        "state_path": str(state_path),
    }


def continue_unified_stage20_through_stage23(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    cefrj_asset: Path | str,
    include_russian_pronunciation_hint: bool = False,
) -> dict[str, Any]:
    state_path = Path(state_path).expanduser().resolve()
    database_path = Path(database).expanduser().resolve()
    state, _preflight, _probe = _load_verified_evidence(state_path)
    step = state["steps"]["stage20_downstream"]
    if step.get("status") not in {"stage20_completed", "completed_through_stage23"}:
        raise RuntimeError("Unified Product run has no completed Stage20 to continue")
    provider = _load_artifact((step.get("provider") or {}).get("artifact"), context="Stage20 provider")
    stage20 = _load_artifact((step.get("stage20") or {}).get("artifact"), context="Stage20 result")
    identity = step.get("input_identity")
    if not isinstance(identity, dict):
        raise RuntimeError("Unified Stage20 lost immutable input identity")
    _validate_provider(provider, identity)
    stage20_identity = _validate_stage20(stage20, provider)
    if (step.get("stage20") or {}).get("identity") != stage20_identity:
        raise RuntimeError("Unified Stage20 durable identity drift before downstream continuation")
    paths = _artifact_paths(state_path)
    downstream = step.setdefault("stage20_through_stage23", {"status": "pending", "attempts": 0})
    downstream["attempts"] = int(downstream.get("attempts") or 0) + 1
    downstream["status"] = "running"
    downstream["started_at"] = _now()
    state["status"] = "executing_stage20_through_stage23"
    _save_state(state_path, state)
    try:
        result = resume_product_downstream(
            core,
            database_path,
            provider,
            stage20,
            cefrj_asset=cefrj_asset,
            state_path=paths["downstream_state"],
            include_russian_pronunciation_hint=include_russian_pronunciation_hint,
        )
        if result.get("status") != "completed":
            raise RuntimeError("Product Stage20-through-Stage23 runner did not complete")
    except Exception as exc:
        downstream["status"] = "failed"
        downstream["failed_at"] = _now()
        downstream["error"] = {"type": type(exc).__name__, "message": str(exc)}
        step["status"] = "failed"
        state["status"] = "failed"
        _save_state(state_path, state)
        raise
    if not paths["downstream_state"].is_file():
        raise RuntimeError("Product downstream runner completed without durable state file")
    downstream.update(
        {
            "status": "completed",
            "completed_at": _now(),
            "runner_state_path": str(paths["downstream_state"]),
            "runner_state_sha256": _file_sha256(paths["downstream_state"]),
            "runner_input_fingerprint": str((result.get("input_identity") or {}).get("fingerprint") or ""),
            "cache_hits": dict(result.get("cache_hits") or {}),
        }
    )
    step["status"] = "completed_through_stage23"
    step["blocked_reason"] = "stage24_cards_not_yet_integrated_into_unified_product_run"
    state["status"] = "stage23_completed_awaiting_stage24_cards"
    _save_state(state_path, state)
    return {
        "schema": STAGE20_UNIFIED_SCHEMA,
        "status": "completed_through_stage23",
        "stage20_identity": stage20_identity,
        "downstream": dict(downstream),
        "state_path": str(state_path),
    }
