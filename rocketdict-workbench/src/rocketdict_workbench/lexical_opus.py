from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

from .core import RocketDictCore

PROVIDER_SCHEMA = "rocketdict-workbench-lexical-opus/1"
SNAPSHOT_VERSION = "opus-2020-02-11+workbench-lexical-v1"


def normalize_lexical_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").strip()
    value = re.sub(r"^[\s\.,;:!?…\"'«»()\[\]{}]+|[\s\.,;:!?…\"'«»()\[\]{}]+$", "", value)
    return re.sub(r"\s+", " ", value).casefold().strip()


def probe_forms(lemma: str) -> list[dict[str, Any]]:
    """Return deterministic lexical probes; all probe/rank evidence is retained."""
    lemma = re.sub(r"\s+", " ", lemma.strip())
    values: list[tuple[str, str, float]] = []
    if lemma:
        values.append(("titlecase", lemma[:1].upper() + lemma[1:], 0.0))
        values.append(("lemma", lemma, 0.04))
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kind, text, penalty in values:
        if text in seen:
            continue
        seen.add(text)
        result.append({"kind": kind, "text": text, "confidence_penalty": penalty})
    return result


def admissible_ru_candidate(source_lemma: str, target: str) -> tuple[bool, str | None]:
    cleaned = target.strip()
    normalized = normalize_lexical_text(cleaned)
    if not normalized:
        return False, "empty"
    if normalized == normalize_lexical_text(source_lemma):
        return False, "identity"
    cyr = len(re.findall(r"[А-Яа-яЁё]", cleaned))
    latin = len(re.findall(r"[A-Za-z]", cleaned))
    if cyr == 0:
        return False, "no_cyrillic"
    if latin > cyr:
        return False, "latin_leakage"
    if re.fullmatch(r"[\W\d_]+", cleaned, re.UNICODE):
        return False, "numeric_or_punctuation_only"
    return True, None


def provider_confidence(rank: int, probe_kind: str) -> float:
    penalty = 0.0 if probe_kind == "titlecase" else 0.04
    return round(max(0.52, 0.94 - 0.055 * int(rank) - penalty), 4)


def _helper_code() -> str:
    # This executes inside the selected RocketDict core Python, keeping the
    # Workbench package itself dependency-light and compatible with a separate
    # core environment.
    return r'''
import json,re,sys,unicodedata
from pathlib import Path
from sqlalchemy import select
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.database.models import LexicalSense,LexicalEntry
from rocketdict.translation.backends import CTranslate2MarianBackend

def norm(v):
    v=unicodedata.normalize("NFKC",v or "").strip()
    v=re.sub(r"^[\s\.,;:!?…\"'«»()\[\]{}]+|[\s\.,;:!?…\"'«»()\[\]{}]+$","",v)
    return re.sub(r"\s+"," ",v).casefold().strip()
def admissible(src,tgt):
    n=norm(tgt)
    if not n:return False,"empty"
    if n==norm(src):return False,"identity"
    cyr=len(re.findall(r"[А-Яа-яЁё]",tgt)); latin=len(re.findall(r"[A-Za-z]",tgt))
    if cyr==0:return False,"no_cyrillic"
    if latin>cyr:return False,"latin_leakage"
    if re.fullmatch(r"[\W\d_]+",tgt,re.UNICODE):return False,"numeric_or_punctuation_only"
    return True,None

db=Path(sys.argv[1]); model=Path(sys.argv[2]); revision=sys.argv[3]
beam=int(sys.argv[4]); hypotheses=int(sys.argv[5]); maximum=int(sys.argv[6])
requested=json.loads(sys.argv[7])
e=bootstrap_database(db); sf=create_session_factory(e)
with sf() as s:
    q=select(LexicalSense,LexicalEntry).join(LexicalEntry,LexicalEntry.id==LexicalSense.lexical_entry_id).order_by(LexicalSense.id)
    rows=s.execute(q).all()
if requested:
    wanted={int(x) for x in requested}; rows=[x for x in rows if int(x[0].id) in wanted]
backend=CTranslate2MarianBackend(model,tokenizer_identifier=model,device="cpu",compute_type="float32",revision=revision)
entries={}; evidence=[]
for sense,entry in rows:
    lemma=str(entry.normalized_lemma or entry.lemma or "").strip()
    probes=[]; title=(lemma[:1].upper()+lemma[1:]) if lemma else lemma
    for kind,text,pen in (("titlecase",title,0.0),("lemma",lemma,0.04)):
        if text and text not in [p[1] for p in probes]:probes.append((kind,text,pen))
    accepted={}
    for kind,text,pen in probes:
        outs=backend.translate_batch([text],generation_settings={"num_beams":beam,"num_return_sequences":hypotheses,"max_new_tokens":32})[0]
        for rank,out in enumerate(outs):
            cleaned=out.text.strip().strip(" .,!;:…")
            ok,reason=admissible(lemma,cleaned)
            evidence.append({"sense_id":int(sense.id),"entry_id":int(entry.id),"lemma":lemma,"probe_kind":kind,"probe_text":text,"rank":rank,"target":out.text,"cleaned_target":cleaned,"raw_score":out.raw_score,"accepted":ok,"rejection_reason":reason})
            if not ok:continue
            n=norm(cleaned); conf=round(max(.52,.94-.055*rank-pen),4)
            candidate={"translation":cleaned,"confidence":conf,"context_compatibility":.86 if kind=="titlecase" else .80,"literal":True}
            prior=accepted.get(n)
            if prior is None or (candidate["confidence"],candidate["context_compatibility"])>(prior["confidence"],prior["context_compatibility"]):accepted[n]=candidate
    entries[lemma]=sorted(accepted.values(),key=lambda x:(-x["confidence"],-x["context_compatibility"],norm(x["translation"])))[:maximum]
summary={"sense_count":len(rows),"entry_count":len(entries),"candidate_count":sum(len(x) for x in entries.values()),"rejected_count":sum(1 for x in evidence if not x["accepted"]),"backend_compute_type":backend.compute_type,"backend_runtime":backend.runtime_backend_key}
print(json.dumps({"entries":entries,"evidence":evidence,"summary":summary},ensure_ascii=False))
e.dispose()
'''


def build_opus_lexical_snapshot(
    core: RocketDictCore,
    database: Path | str,
    *,
    model_path: Path | str,
    revision: str,
    archive_sha256: str,
    source_uri: str,
    sense_ids: Iterable[int] = (),
    beam_size: int = 8,
    num_hypotheses: int = 8,
    maximum_candidates_per_lemma: int = 8,
    model_name: str = "OPUS EN-RU lexical n-best provider",
    license_expression: str = "Apache-2.0",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    model_path = Path(model_path).expanduser().resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(model_path)
    if not re.fullmatch(r"[0-9a-fA-F]{64}", archive_sha256):
        raise ValueError("archive_sha256 must be a 64-character SHA-256")
    requested = [int(x) for x in sense_ids]
    result = core._run(
        ["-c", _helper_code(), str(database), str(model_path), str(revision), str(int(beam_size)), str(int(num_hypotheses)), str(int(maximum_candidates_per_lemma)), json.dumps(requested, separators=(",", ":"))],
        timeout=600,
    )
    payload = core._parse_json(result.stdout, context="lexical OPUS provider")
    entries = dict(payload.get("entries") or {})
    evidence = list(payload.get("evidence") or [])
    snapshot = {
        "source_type": "model", "name": model_name, "version": SNAPSHOT_VERSION, "revision": str(revision),
        "sha256": archive_sha256.lower(), "license_expression": license_expression,
        "license_class": "attribution_required", "commercial_allowed": True, "attribution_required": True,
        "license_review_status": "machine_assessed", "available": True, "network_access": False,
        "source_language": "en", "target_language": "ru", "source_uri": source_uri,
        "local_path": str(model_path), "entries": entries, "capability_claim": "production", "is_smoke": False,
    }
    canonical_entries = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema": PROVIDER_SCHEMA, "provider": "contextual-lexical-opus-v1", "snapshot": snapshot,
        "entries_sha256": hashlib.sha256(canonical_entries.encode("utf-8")).hexdigest(),
        "summary": payload.get("summary") or {}, "evidence": evidence,
        "settings": {"beam_size": int(beam_size), "num_hypotheses": int(num_hypotheses), "maximum_candidates_per_lemma": int(maximum_candidates_per_lemma), "probe_order": ["titlecase", "lemma"], "target_language": "ru", "network_access": False},
    }


def run_stage20_with_snapshot(
    core: RocketDictCore,
    database: Path | str,
    provider_result: dict[str, Any],
    *,
    source_policy: str = "local-snapshots-only",
    actor: str = "rocketdict-workbench:contextual-lexical-opus-v1",
    sense_ids: Iterable[int] = (),
) -> dict[str, Any]:
    snapshot = provider_result.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("provider_result does not contain a snapshot")
    code = r'''
import json,sys
from pathlib import Path
from sqlalchemy import select
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.database.models import LexicalSense,LexicalEntry
from rocketdict.sense_translation.service import SenseTranslationService

db=Path(sys.argv[1]); snapshot=json.loads(sys.argv[2]); policy=sys.argv[3]; actor=sys.argv[4]; requested=json.loads(sys.argv[5])
e=bootstrap_database(db); sf=create_session_factory(e); svc=SenseTranslationService(sf)
with sf() as s:
    rows=s.execute(select(LexicalSense,LexicalEntry).join(LexicalEntry,LexicalEntry.id==LexicalSense.lexical_entry_id).order_by(LexicalSense.id)).all()
if requested:
    wanted={int(x) for x in requested}; rows=[x for x in rows if int(x[0].id) in wanted]
out=[]
for sense,entry in rows:
    settings=dict(svc.DEFAULT_SETTINGS); settings["source_policy"]=policy; settings["source_snapshots"]=[snapshot]
    result=svc.generate(int(sense.id),"ru",settings=settings,actor=actor)
    data=svc.get_selection(int(result.selection_revision_id)); items=data.get("items") or []; selected=[]
    for row in items:
        c=row.get("candidate") or {}; i=row.get("item") or {}
        selected.append({"translation":c.get("translation_text"),"position":i.get("position"),"role":i.get("role"),"confidence":i.get("confidence"),"candidate_id":c.get("id")})
    selected.sort(key=lambda x:(x.get("position") or 999999))
    out.append({"sense_id":int(sense.id),"entry_id":int(entry.id),"lemma":entry.lemma,"normalized_lemma":entry.normalized_lemma,"selection_revision_id":int(result.selection_revision_id),"generation_run_id":int(result.generation_run_id),"cache_hit":bool(result.cache_hit),"coverage_complete":bool(result.coverage_complete),"selected":selected})
print(json.dumps({"source_policy":policy,"results":out},ensure_ascii=False)); e.dispose()
'''
    requested = [int(x) for x in sense_ids]
    result = core._run(["-c", code, str(Path(database).expanduser().resolve()), json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), source_policy, actor, json.dumps(requested, separators=(",", ":"))], timeout=600)
    return dict(core._parse_json(result.stdout, context="Stage20 lexical snapshot run"))


def write_provider_evidence(path: Path | str, payload: dict[str, Any]) -> Path:
    path = Path(path).expanduser().resolve(); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path
