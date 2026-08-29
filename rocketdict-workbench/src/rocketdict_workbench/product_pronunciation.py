from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .core import RocketDictCore

POLICY_KEY = "workbench-cmudict-exact-v1"


def product_pronunciation_settings(*, include_russian_hint: bool = False) -> dict[str, Any]:
    return {
        "requested_dialects": ["en-US"],
        "enable_generated_fallback": False,
        "enable_mwe_composition": True,
        "include_russian_hint": bool(include_russian_hint),
        "minimum_confidence": 0.25,
    }


def _helper_code() -> str:
    return r'''
import json,re,sys
from pathlib import Path
from sqlalchemy import select
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.database.models.linguistic import LexicalEntry
from rocketdict.pronunciation import PronunciationService
from rocketdict.pronunciation.external_sources import cmudict_snapshot

POLICY="workbench-cmudict-exact-v1"

def has_variants(snapshot):
    entries=list(snapshot.get("entries") or [])
    return bool(entries and list(entries[0].get("variants") or []))

def source_snapshots(form):
    exact=cmudict_snapshot(form)
    if has_variants(exact):
        return [exact],"exact_form",[]
    words=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",form)
    if len(words)<=1:
        return [exact],"unknown_exact_form",[form]
    rows=[];missing=[]
    for word in words:
        snap=cmudict_snapshot(word)
        if has_variants(snap):rows.append(snap)
        else:missing.append(word)
    if missing:
        # Keep the exact empty snapshot so PronunciationService records an
        # explicit unknown instead of silently generating a pronunciation.
        return [exact],"unknown_mwe_component",missing
    return rows,"exact_word_composition",[]

db=Path(sys.argv[1]); entry_ids=[int(x) for x in json.loads(sys.argv[2])]; include_hint=bool(int(sys.argv[3])); actor=sys.argv[4]; approve=bool(int(sys.argv[5]))
e=bootstrap_database(db); sf=create_session_factory(e); svc=PronunciationService(sf); out=[]
with sf() as s:
    entries={x.id:x for x in s.scalars(select(LexicalEntry).where(LexicalEntry.id.in_(entry_ids))).all()}
for entry_id in entry_ids:
    entry=entries.get(entry_id)
    if entry is None:raise RuntimeError(f"Lexical entry does not exist: {entry_id}")
    form=str(entry.canonical_text or entry.lemma or "").strip()
    snapshots,strategy,missing=source_snapshots(form)
    settings={
        "source_snapshots":snapshots,
        "requested_dialects":["en-US"],
        "enable_generated_fallback":False,
        "enable_mwe_composition":True,
        "include_russian_hint":include_hint,
        "minimum_confidence":.25,
    }
    result=svc.generate(entry_id,settings=settings,actor=actor)
    row={
        "entry_id":entry_id,"form":form,"strategy":strategy,"missing_components":missing,
        "generation_run_id":result.generation_run_id,"review_revision_id":result.review_revision_id,
        "selected_candidate_id":result.selected_candidate_id,"dialect":result.selected_dialect,
        "ipa":result.selected_ipa,"arpabet":result.selected_arpabet,"russian_hint":result.russian_hint,
        "unknown":bool(result.unknown),"candidate_count":result.candidate_count,
        "conflict_count":result.conflict_count,"blocking_conflict_count":result.blocking_conflict_count,
        "cache_hit":bool(result.cache_hit),"generated_fallback":False,
    }
    if approve:
        approved=svc.approve(result.review_revision_id,actor=actor,reason="Workbench Product Mode exact CMUdict evidence; generated pronunciation fallback is forbidden")
        row["approval_status"]=approved.status;row["pronunciation_id"]=approved.pronunciation_id;row["materialization_id"]=approved.materialization_id
    out.append(row)
print(json.dumps({"policy":POLICY,"generated_fallback_allowed":False,"results":out},ensure_ascii=False));e.dispose()
'''


def generate_product_pronunciations(
    core: RocketDictCore,
    database: Path | str,
    lexical_entry_ids: Iterable[int],
    *,
    include_russian_hint: bool = False,
    approve: bool = True,
    actor: str = "rocketdict-workbench:cmudict-exact-v1",
) -> dict[str, Any]:
    ids = [int(x) for x in lexical_entry_ids]
    result = core._run([
        "-c", _helper_code(), str(Path(database).expanduser().resolve()),
        json.dumps(ids, separators=(",", ":")), "1" if include_russian_hint else "0", actor,
        "1" if approve else "0",
    ], timeout=600)
    payload = dict(core._parse_json(result.stdout, context="Product CMUdict pronunciation"))
    for row in payload.get("results") or []:
        if row.get("strategy") in {"exact_form", "exact_word_composition"} and row.get("unknown"):
            raise RuntimeError(f"Exact CMUdict evidence unexpectedly materialized as unknown: {row}")
        if row.get("generated_fallback"):
            raise RuntimeError(f"Generated pronunciation leaked into Product Mode: {row}")
    return payload
