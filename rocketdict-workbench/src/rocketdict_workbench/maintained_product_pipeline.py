from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from .core import RocketDictCore

PIPELINE_SCHEMA = "rocketdict-workbench-maintained-product-pipeline/1"
EXECUTOR = "maintained-core-native-stage20-25-v1"
OPUS_ENV = "ROCKETDICT_OPUS_ASSET_DIR"
CEFRJ_ENV = "ROCKETDICT_CEFRJ_ASSET"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_state(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Product run state is not a JSON object")
    return value


def _save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _positive(value: Any, *, context: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{context} is boolean, not a durable id")
    result = int(value or 0)
    if result <= 0:
        raise RuntimeError(f"{context} lacks a positive durable id")
    return result


def _stage19_run_id(state: dict[str, Any]) -> int:
    record = (
        (((state.get("steps") or {}).get("upstream_execution") or {}).get("executions") or {})
        .get("19")
    )
    if not isinstance(record, dict) or record.get("status") != "completed":
        raise RuntimeError("Maintained downstream requires completed Stage19")
    result = record.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Completed Stage19 lacks its durable result object")
    return _positive(result.get("sense_induction_run_id"), context="Stage19 sense_induction_run_id")


@contextmanager
def _asset_environment(
    *,
    opus_asset: Path | None,
    cefrj_asset: Path | None,
) -> Iterator[None]:
    previous = {OPUS_ENV: os.environ.get(OPUS_ENV), CEFRJ_ENV: os.environ.get(CEFRJ_ENV)}
    try:
        if opus_asset is not None:
            os.environ[OPUS_ENV] = str(opus_asset.expanduser().resolve())
        if cefrj_asset is not None:
            os.environ[CEFRJ_ENV] = str(cefrj_asset.expanduser().resolve())
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _asset_blocker(opus_asset: Path | None, cefrj_asset: Path | None) -> dict[str, Any] | None:
    if opus_asset is None and not str(os.environ.get(OPUS_ENV) or "").strip():
        return {
            "status": "blocked",
            "blocked_phase": "stage20",
            "required": f"--opus-asset or {OPUS_ENV}",
            "reason": "verified_offline_opus_asset_required",
        }
    if cefrj_asset is None and not str(os.environ.get(CEFRJ_ENV) or "").strip():
        return {
            "status": "blocked",
            "blocked_phase": "stage21",
            "required": f"--cefrj-asset or {CEFRJ_ENV}",
            "reason": "pinned_cefrj_1_5_asset_required",
        }
    return None


_STAGE20_23_CODE = r'''
import json,re,sys
from pathlib import Path
from rocketdict.api.operations import OPERATIONS
from rocketdict.evidence import CEFRJ_SHA256

database=Path(sys.argv[1]).expanduser().resolve()
sense_induction_run_id=int(sys.argv[2])

def call(name,**params):
    value=OPERATIONS[name](database=database,**params)
    if not isinstance(value,dict):
        raise RuntimeError(f"{name} returned non-object result")
    return dict(value)

def positive(value,context):
    if isinstance(value,bool) or int(value or 0)<=0:
        raise RuntimeError(f"{context} lacks positive durable id")
    return int(value)

def real_ru(source,target,context):
    source=str(source or '').strip(); target=str(target or '').strip()
    if not target or source.casefold()==target.casefold() or not re.search(r'[А-Яа-яЁё]',target):
        raise RuntimeError(f"{context} lacks non-identity Cyrillic translation evidence")

s20=call('product.stage20.run',sense_induction_run_id=sense_induction_run_id,parameters={},implementation='contextual-lexical-opus-v3')
positive(s20.get('sense_translation_run_id'),'Stage20 sense_translation_run_id')
positive(s20.get('stage_result_id'),'Stage20 stage_result_id')
if s20.get('coverage_complete') is not True or s20.get('real_mt') is not True:
    raise RuntimeError('Stage20 maintained-core coverage/real-MT proof failed')
if s20.get('network_used') is not False or s20.get('compute_type')!='float32':
    raise RuntimeError('Stage20 maintained-core execution policy drift')
rows=list(s20.get('results') or [])
if not rows:
    raise RuntimeError('Stage20 produced no sense results')
sense_ids=[]; entry_ids=[]; seen_senses=set(); seen_entries=set()
for row in rows:
    sense_id=positive(row.get('sense_id'),'Stage20 sense_id')
    entry_id=positive(row.get('entry_id'),'Stage20 entry_id')
    positive(row.get('selection_revision_id'),'Stage20 selection_revision_id')
    real_ru(row.get('lemma'),row.get('translation'),f'Stage20 sense {sense_id}')
    if sense_id in seen_senses:
        raise RuntimeError(f'Duplicate Stage20 sense {sense_id}')
    seen_senses.add(sense_id); sense_ids.append(sense_id)
    if entry_id not in seen_entries:
        seen_entries.add(entry_id); entry_ids.append(entry_id)

stage21_cache=stage22_cache=stage23_cache=0
for entry_id in entry_ids:
    s21=call('product.stage21.run',lexical_entry_id=entry_id,parameters={'use_builtin_smoke_sources':False},implementation='cefrj-vocabulary-1.5')
    positive(s21.get('cefr_assignment_id'),f'Stage21 entry {entry_id}')
    if s21.get('source_sha256')!=CEFRJ_SHA256 or s21.get('builtin_smoke_used') is not False or s21.get('frequency_inference_used') is not False:
        raise RuntimeError(f'Stage21 degraded or unpinned evidence for entry {entry_id}')
    stage21_cache+=int(bool(s21.get('cache_hit')))
    s22=call('product.stage22.run',lexical_entry_id=entry_id,parameters={'enable_generated_fallback':False},implementation='cmudict-production')
    positive(s22.get('pronunciation_id'),f'Stage22 entry {entry_id}')
    if s22.get('generated_fallback') is not False:
        raise RuntimeError(f'Stage22 generated fallback leaked for entry {entry_id}')
    stage22_cache+=int(bool(s22.get('cache_hit')))

for sense_id in sense_ids:
    s23=call('product.stage23.run',lexical_sense_id=sense_id,parameters={'corpus_snapshots':[]},implementation='examples-current')
    positive(s23.get('example_run_id'),f'Stage23 sense {sense_id}')
    if s23.get('scope_contract')!='stage23-sense-scope-v2' or s23.get('primary_missing') is not False or not list(s23.get('example_ids') or []):
        raise RuntimeError(f'Stage23 provenance/scope evidence failed for sense {sense_id}')
    stage23_cache+=int(bool(s23.get('cache_hit')))

print(json.dumps({
    'schema':'rocketdict-workbench-maintained-stage20-23/1',
    'status':'completed_through_stage23',
    'sense_induction_run_id':sense_induction_run_id,
    'sense_translation_run_id':int(s20['sense_translation_run_id']),
    'stage20_result_id':int(s20['stage_result_id']),
    'sense_ids':sense_ids,
    'entry_ids':entry_ids,
    'sense_count':len(sense_ids),
    'entry_count':len(entry_ids),
    'cache_hits':{
        'stage20':bool(s20.get('cache_hit')),
        'stage21':stage21_cache,
        'stage22':stage22_cache,
        'stage23':stage23_cache,
    },
},ensure_ascii=False,separators=(',',':')))
'''


_STAGE24_25_CODE = r'''
import json,sys
from pathlib import Path
from rocketdict.api.operations import OPERATIONS

database=Path(sys.argv[1]).expanduser().resolve()
sense_ids=[int(x) for x in json.loads(sys.argv[2])]
set_name=str(sys.argv[3])
raw_limit=json.loads(sys.argv[4])
limit=None if raw_limit is None else int(raw_limit)
output_path=Path(sys.argv[5]).expanduser().resolve()
if not sense_ids or any(x<=0 for x in sense_ids) or len(sense_ids)!=len(set(sense_ids)):
    raise RuntimeError('Stage24 requires non-empty unique positive sense ids')
if limit is not None and limit<=0:
    raise RuntimeError('max_new_cards must be positive when provided')

def call(name,**params):
    value=OPERATIONS[name](database=database,**params)
    if not isinstance(value,dict):
        raise RuntimeError(f"{name} returned non-object result")
    return dict(value)

def positive(value,context):
    if isinstance(value,bool) or int(value or 0)<=0:
        raise RuntimeError(f"{context} lacks positive durable id")
    return int(value)

card_ids=[]; cache_hits=0; new_cards=0
for sense_id in sense_ids:
    card=call('product.stage24.run',lexical_sense_id=sense_id,parameters={},implementation='cards-current')
    card_id=positive(card.get('card_revision_id'),f'Stage24 sense {sense_id}')
    if card.get('complete') is not True or len(str(card.get('content_sha256') or ''))!=64:
        raise RuntimeError(f'Stage24 incomplete card for sense {sense_id}')
    card_ids.append(card_id)
    if card.get('cache_hit'):
        cache_hits+=1
    else:
        new_cards+=1
    if limit is not None and new_cards>=limit and len(card_ids)<len(sense_ids):
        print(json.dumps({
            'schema':'rocketdict-workbench-maintained-stage24-25/1',
            'status':'stage24_partial',
            'sense_count':len(sense_ids),
            'completed_prefix_count':len(card_ids),
            'new_card_count':new_cards,
            'stage24_cache_hits':cache_hits,
        },ensure_ascii=False,separators=(',',':')))
        raise SystemExit(0)

if len(card_ids)!=len(sense_ids) or len(set(card_ids))!=len(sense_ids):
    raise RuntimeError('Stage24 card coverage is not exactly one revision per sense')
card_set=call('product.card-set.assemble',card_revision_ids=card_ids,set_name=set_name)
set_revision_id=positive(card_set.get('set_revision_id'),'Card set revision')
if card_set.get('complete') is not True or int(card_set.get('card_count') or 0)!=len(sense_ids):
    raise RuntimeError('Card-set coverage failed')
s25=call('product.stage25.run',set_revision_id=set_revision_id,parameters={'output_path':str(output_path)},implementation='export-json')
positive(s25.get('export_run_id'),'Stage25 export_run_id')
if s25.get('complete') is not True or int(s25.get('card_count') or 0)!=len(sense_ids):
    raise RuntimeError('Stage25 export coverage failed')
if not output_path.is_file():
    raise RuntimeError(f'Stage25 export file missing: {output_path}')
print(json.dumps({
    'schema':'rocketdict-workbench-maintained-stage24-25/1',
    'status':'product_complete_exported',
    'sense_count':len(sense_ids),
    'card_count':len(card_ids),
    'new_card_count':new_cards,
    'stage24_cache_hits':cache_hits,
    'set_revision_id':set_revision_id,
    'export_run_id':int(s25['export_run_id']),
    'export_path':str(output_path),
    'export_sha256':str(s25['export_sha256']),
    'export_bytes':int(s25['export_bytes']),
    'stage25_cache_hit':bool(s25.get('cache_hit')),
},ensure_ascii=False,separators=(',',':')))
'''


def _run_json_script(
    core: RocketDictCore,
    code: str,
    args: list[str],
    *,
    context: str,
    timeout: float,
) -> dict[str, Any]:
    process = core._run(["-c", code, *args], timeout=timeout)
    value = core._parse_json(process.stdout, context=context)
    if not isinstance(value, dict):
        raise RuntimeError(f"{context} returned a non-object result")
    return value


def advance_maintained_downstream(
    core: RocketDictCore,
    database: Path | str,
    state_path: Path | str,
    *,
    opus_asset: Path | None = None,
    cefrj_asset: Path | None = None,
    set_name: str = "RocketDict Product output",
    max_new_cards: int | None = None,
) -> dict[str, Any]:
    """Resume maintained Stage20→25 without historical ORM/helper execution.

    Stage operations execute inside the installed maintained-core interpreter so a
    large dictionary does not spawn one Python process per lexical entry/sense.
    Every underlying Product operation remains replay-safe and DB-backed. Compact
    progress identities are additionally persisted into the unified Workbench run
    state; after interruption, re-entry reuses core run caches rather than inventing
    synthetic recovery state.
    """
    database = Path(database).expanduser().resolve()
    state_path = Path(state_path).expanduser().resolve()
    state = _load_state(state_path)
    sense_induction_run_id = _stage19_run_id(state)
    blocker = _asset_blocker(opus_asset, cefrj_asset)
    if blocker is not None:
        return {"schema": PIPELINE_SCHEMA, **blocker, "state_path": str(state_path)}
    if max_new_cards is not None and int(max_new_cards) <= 0:
        raise ValueError("max_new_cards must be positive when provided")

    steps = state.setdefault("steps", {})
    downstream_step = steps.setdefault("stage20_downstream", {"status": "pending", "attempts": 0})
    checkpoints: list[dict[str, Any]] = []

    with _asset_environment(opus_asset=opus_asset, cefrj_asset=cefrj_asset):
        if not (
            downstream_step.get("status") == "completed_through_stage23"
            and downstream_step.get("executor") == EXECUTOR
        ):
            downstream_step["status"] = "running"
            downstream_step["executor"] = EXECUTOR
            downstream_step["attempts"] = int(downstream_step.get("attempts") or 0) + 1
            downstream_step["started_at"] = _now()
            state["status"] = "executing_maintained_stage20_through_stage23"
            _save_state(state_path, state)
            try:
                phase = _run_json_script(
                    core,
                    _STAGE20_23_CODE,
                    [str(database), str(sense_induction_run_id)],
                    context="maintained Stage20-23",
                    timeout=86400,
                )
                if phase.get("status") != "completed_through_stage23":
                    raise RuntimeError(f"Maintained Stage20-23 did not complete: {phase}")
            except Exception as exc:
                downstream_step["status"] = "failed"
                downstream_step["failed_at"] = _now()
                downstream_step["error"] = {"type": type(exc).__name__, "message": str(exc)}
                state["status"] = "failed"
                _save_state(state_path, state)
                raise
            downstream_step.update(
                {
                    "status": "completed_through_stage23",
                    "executor": EXECUTOR,
                    "completed_at": _now(),
                    "result_sha256": _canonical_sha256(phase),
                    "sense_induction_run_id": sense_induction_run_id,
                    "sense_translation_run_id": int(phase["sense_translation_run_id"]),
                    "sense_ids": list(phase["sense_ids"]),
                    "entry_ids": list(phase["entry_ids"]),
                    "sense_count": int(phase["sense_count"]),
                    "entry_count": int(phase["entry_count"]),
                    "cache_hits": dict(phase.get("cache_hits") or {}),
                }
            )
            state["status"] = "stage23_completed_awaiting_stage24_cards"
            _save_state(state_path, state)
            checkpoints.append({"phase": "maintained_stage20_23", "result": phase})
        else:
            checkpoints.append(
                {
                    "phase": "maintained_stage20_23",
                    "cache_hit": True,
                    "sense_count": int(downstream_step.get("sense_count") or 0),
                    "entry_count": int(downstream_step.get("entry_count") or 0),
                }
            )

        sense_ids = [int(value) for value in list(downstream_step.get("sense_ids") or [])]
        if not sense_ids or any(value <= 0 for value in sense_ids):
            raise RuntimeError("Maintained Stage20-23 state lost durable sense identities")

        cards_step = steps.setdefault("cards", {"status": "pending", "attempts": 0})
        cards_step["status"] = "running"
        cards_step["executor"] = EXECUTOR
        cards_step["attempts"] = int(cards_step.get("attempts") or 0) + 1
        cards_step["started_at"] = _now()
        state["status"] = "executing_maintained_stage24_cards"
        _save_state(state_path, state)
        export_path = state_path.parent / f"{state_path.stem}.product-export.json"
        try:
            final = _run_json_script(
                core,
                _STAGE24_25_CODE,
                [
                    str(database),
                    json.dumps(sense_ids, separators=(",", ":")),
                    str(set_name),
                    json.dumps(max_new_cards),
                    str(export_path),
                ],
                context="maintained Stage24-25",
                timeout=86400,
            )
        except Exception as exc:
            cards_step["status"] = "failed"
            cards_step["failed_at"] = _now()
            cards_step["error"] = {"type": type(exc).__name__, "message": str(exc)}
            state["status"] = "failed"
            _save_state(state_path, state)
            raise

        checkpoints.append({"phase": "maintained_stage24_25", "result": final})
        if final.get("status") == "stage24_partial":
            cards_step.update(
                {
                    "status": "partial",
                    "completed_prefix_count": int(final.get("completed_prefix_count") or 0),
                    "sense_count": len(sense_ids),
                    "last_progress_at": _now(),
                }
            )
            state["status"] = "stage24_partial"
            _save_state(state_path, state)
            return {
                "schema": PIPELINE_SCHEMA,
                "status": "progressed",
                "blocked_phase": None,
                "checkpoints": checkpoints,
                "state_path": str(state_path),
            }
        if final.get("status") != "product_complete_exported":
            raise RuntimeError(f"Maintained Stage24-25 returned unexpected status: {final}")

        cards_step.update(
            {
                "status": "completed",
                "completed_at": _now(),
                "card_count": int(final["card_count"]),
                "set_revision_id": int(final["set_revision_id"]),
            }
        )
        export_step = steps.setdefault("export", {"status": "pending", "attempts": 0})
        export_step.update(
            {
                "status": "completed",
                "executor": EXECUTOR,
                "attempts": int(export_step.get("attempts") or 0) + 1,
                "completed_at": _now(),
                "export_run_id": int(final["export_run_id"]),
                "set_revision_id": int(final["set_revision_id"]),
                "export_path": str(final["export_path"]),
                "export_sha256": str(final["export_sha256"]),
                "export_bytes": int(final["export_bytes"]),
            }
        )
        state["status"] = "product_complete_exported"
        state["completed_at"] = _now()
        _save_state(state_path, state)
        return {
            "schema": PIPELINE_SCHEMA,
            "status": "product_complete_exported",
            "checkpoints": checkpoints,
            "state_path": str(state_path),
            "export": dict(export_step),
        }
