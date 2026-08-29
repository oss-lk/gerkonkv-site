from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

from .core import RocketDictCore

PROVIDER_SCHEMA = "rocketdict-workbench-lexical-opus/3"
SNAPSHOT_VERSION = "opus-2020-02-11+workbench-lexical-v3"
VERB_ENTRY_TYPES = {"phrasal_verb", "prepositional_verb"}
OBJECT_DEPENDENCIES = {"dobj", "obj", "pobj", "nsubj", "nsubjpass"}


def normalize_lexical_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").strip()
    value = re.sub(r"^[\s\.,;:!?…\"'«»()\[\]{}]+|[\s\.,;:!?…\"'«»()\[\]{}]+$", "", value)
    return re.sub(r"\s+", " ", value).casefold().strip()


def effective_probe_pos(part_of_speech: str | None, dependency: str | None) -> tuple[str, str]:
    pos = str(part_of_speech or "X").upper()
    dep = str(dependency or "").casefold()
    if pos == "VERB" and dep in OBJECT_DEPENDENCIES:
        return "NOUN", "dependency_pos_repair"
    return pos, "declared_pos"


def probe_forms(
    lemma: str,
    part_of_speech: str | None = None,
    entry_type: str | None = None,
    dependency: str | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic POS-aware lexical probes with auditable provenance."""
    lemma = re.sub(r"\s+", " ", lemma.strip())
    if not lemma:
        return []
    effective_pos, pos_reason = effective_probe_pos(part_of_speech, dependency)
    etype = str(entry_type or "").casefold()
    title = lemma[:1].upper() + lemma[1:]
    if etype in VERB_ENTRY_TYPES:
        effective_pos = "VERB"
        pos_reason = "verb_mwe_entry_type"
        values = [
            ("verb_argument", f"to {lemma} something", 0.98),
            ("verb_infinitive", f"to {lemma}", 0.84),
            ("lemma", lemma, 0.78),
            ("titlecase", title, 0.70),
        ]
    elif effective_pos == "VERB":
        values = [
            ("verb_argument", f"to {lemma} something", 0.98),
            ("verb_infinitive", f"to {lemma}", 0.84),
            ("lemma", lemma, 0.80),
            ("titlecase", title, 0.68),
        ]
    elif effective_pos == "ADJ":
        values = [
            ("adjective_copula", f"is {lemma}", 0.98),
            ("lemma", lemma, 0.90),
            ("titlecase", title, 0.72),
        ]
    elif effective_pos in {"NOUN", "PROPN"}:
        values = [("titlecase", title, 0.96), ("lemma", lemma, 0.90)]
    else:
        values = [("titlecase", title, 0.92), ("lemma", lemma, 0.88)]
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kind, text, base_confidence in values:
        if text in seen:
            continue
        seen.add(text)
        result.append({
            "kind": kind,
            "text": text,
            "base_confidence": base_confidence,
            "effective_pos": effective_pos,
            "pos_reason": pos_reason,
        })
    return result


def clean_probe_target(target: str, probe_kind: str) -> tuple[str, str | None]:
    cleaned = target.strip().strip(" .,!;:…")
    transform = None
    if probe_kind == "verb_argument":
        stripped = re.sub(
            r"\s+(?:что(?:-|\s)?то|что(?:-|\s)?нибудь|это)\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if stripped != cleaned:
            cleaned = stripped
            transform = "strip_generic_argument"
    return cleaned, transform


def _looks_like_russian_infinitive(value: str) -> bool:
    first = normalize_lexical_text(value).split(" ", 1)[0]
    return bool(re.search(r"(?:ть|ться|ти|тись|чь|чься)$", first))


def admissible_ru_candidate(
    source_lemma: str,
    target: str,
    *,
    entry_type: str | None = None,
) -> tuple[bool, str | None]:
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
    if latin:
        return False, "latin_leakage"
    if re.fullmatch(r"[\W\d_]+", cleaned, re.UNICODE):
        return False, "numeric_or_punctuation_only"
    if any(ch.isdigit() for ch in cleaned) and not any(ch.isdigit() for ch in source_lemma):
        return False, "unlicensed_numeric_addition"
    if cleaned and not (cleaned[0].isalnum() or cleaned[0] in {'«', '"'}):
        return False, "leading_symbol_noise"
    if normalized.startswith(("чтобы ", "для того чтобы ")):
        return False, "synthetic_probe_wrapper"
    if str(entry_type or "").casefold() in VERB_ENTRY_TYPES:
        if len(re.findall(r"[А-Яа-яЁё]+", cleaned)) < 2:
            return False, "incomplete_multiword_translation"
    return True, None


def provider_confidence(
    rank: int,
    probe_kind: str,
    *,
    base_confidence: float | None = None,
    effective_pos: str | None = None,
    target: str = "",
    entry_type: str | None = None,
) -> float:
    if base_confidence is None:
        base_confidence = 0.94 if probe_kind == "titlecase" else 0.90
    score = float(base_confidence) - 0.045 * int(rank)
    is_infinitive = effective_pos == "VERB" and _looks_like_russian_infinitive(target)
    if effective_pos == "VERB":
        if is_infinitive:
            score = max(score, 0.84) + 0.08
        else:
            score -= 0.20
    if str(entry_type or "").casefold() in VERB_ENTRY_TYPES and is_infinitive:
        score += 0.05
    return round(min(0.99, max(0.52, score)), 4)


def _helper_code() -> str:
    return r'''
import json,re,sys,unicodedata
from pathlib import Path
from sqlalchemy import select
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.database.models import LexicalSense,LexicalEntry
from rocketdict.database.models.extraction import LexicalCandidate,LexicalCandidateMember
from rocketdict.translation.backends import CTranslate2MarianBackend

VERB_TYPES={"phrasal_verb","prepositional_verb"}
OBJECT_DEPS={"dobj","obj","pobj","nsubj","nsubjpass"}
def norm(v):
    v=unicodedata.normalize("NFKC",v or "").strip()
    v=re.sub(r"^[\s\.,;:!?…\"'«»()\[\]{}]+|[\s\.,;:!?…\"'«»()\[\]{}]+$","",v)
    return re.sub(r"\s+"," ",v).casefold().strip()
def effective_pos(pos,dep):
    pos=str(pos or "X").upper(); dep=str(dep or "").casefold()
    return ("NOUN","dependency_pos_repair") if pos=="VERB" and dep in OBJECT_DEPS else (pos,"declared_pos")
def probes(lemma,pos,etype,dep):
    ep,reason=effective_pos(pos,dep); etype=str(etype or "").casefold(); title=lemma[:1].upper()+lemma[1:]
    if etype in VERB_TYPES:
        ep="VERB"; reason="verb_mwe_entry_type"
        vals=[("verb_argument",f"to {lemma} something",.98),("verb_infinitive",f"to {lemma}",.84),("lemma",lemma,.78),("titlecase",title,.70)]
    elif ep=="VERB":
        vals=[("verb_argument",f"to {lemma} something",.98),("verb_infinitive",f"to {lemma}",.84),("lemma",lemma,.80),("titlecase",title,.68)]
    elif ep=="ADJ": vals=[("adjective_copula",f"is {lemma}",.98),("lemma",lemma,.90),("titlecase",title,.72)]
    elif ep in {"NOUN","PROPN"}: vals=[("titlecase",title,.96),("lemma",lemma,.90)]
    else: vals=[("titlecase",title,.92),("lemma",lemma,.88)]
    out=[]; seen=set()
    for k,t,b in vals:
        if t and t not in seen: seen.add(t); out.append((k,t,b,ep,reason))
    return out
def clean_target(tgt,kind):
    c=tgt.strip().strip(" .,!;:…"); transform=None
    if kind=="verb_argument":
        s=re.sub(r"\s+(?:что(?:-|\s)?то|что(?:-|\s)?нибудь|это)\s*$","",c,flags=re.I).strip()
        if s!=c: c=s; transform="strip_generic_argument"
    return c,transform
def infinitive(v):
    first=norm(v).split(" ",1)[0]
    return bool(re.search(r"(?:ть|ться|ти|тись|чь|чься)$",first))
def admissible(src,tgt,etype):
    n=norm(tgt)
    if not n:return False,"empty"
    if n==norm(src):return False,"identity"
    cyr=len(re.findall(r"[А-Яа-яЁё]",tgt)); latin=len(re.findall(r"[A-Za-z]",tgt))
    if cyr==0:return False,"no_cyrillic"
    if latin:return False,"latin_leakage"
    if re.fullmatch(r"[\W\d_]+",tgt,re.UNICODE):return False,"numeric_or_punctuation_only"
    if any(ch.isdigit() for ch in tgt) and not any(ch.isdigit() for ch in src):return False,"unlicensed_numeric_addition"
    if tgt and not (tgt[0].isalnum() or tgt[0] in {'«','"'}):return False,"leading_symbol_noise"
    if n.startswith(("чтобы ","для того чтобы ")):return False,"synthetic_probe_wrapper"
    if str(etype or "").casefold() in VERB_TYPES and len(re.findall(r"[А-Яа-яЁё]+",tgt))<2:return False,"incomplete_multiword_translation"
    return True,None
def confidence(rank,kind,base,ep,target,etype):
    score=float(base)-.045*int(rank); isinf=ep=="VERB" and infinitive(target)
    if ep=="VERB":
        if isinf: score=max(score,.84)+.08
        else: score-=.20
    if str(etype or "").casefold() in VERB_TYPES and isinf: score+=.05
    return round(min(.99,max(.52,score)),4)

db=Path(sys.argv[1]); model=Path(sys.argv[2]); revision=sys.argv[3]
beam=int(sys.argv[4]); hypotheses=int(sys.argv[5]); maximum=int(sys.argv[6]); requested=json.loads(sys.argv[7])
e=bootstrap_database(db); sf=create_session_factory(e)
with sf() as s:
    rows=s.execute(select(LexicalSense,LexicalEntry).join(LexicalEntry,LexicalEntry.id==LexicalSense.lexical_entry_id).order_by(LexicalSense.id)).all()
    context={}
    for sense,entry in rows:
        cand=s.scalar(select(LexicalCandidate).where(LexicalCandidate.lexical_entry_id==entry.id).order_by(LexicalCandidate.id.desc()))
        dep=None; surface=None; candidate_type=None
        if cand is not None:
            candidate_type=cand.candidate_type; surface=cand.surface_text
            members=s.scalars(select(LexicalCandidateMember).where(LexicalCandidateMember.lexical_candidate_id==cand.id).order_by(LexicalCandidateMember.member_order)).all()
            if len(members)==1: dep=members[0].dependency
        context[int(sense.id)]={"dependency":dep,"surface":surface,"candidate_type":candidate_type}
if requested:
    wanted={int(x) for x in requested}; rows=[x for x in rows if int(x[0].id) in wanted]
backend=CTranslate2MarianBackend(model,tokenizer_identifier=model,device="cpu",compute_type="float32",revision=revision)
entries={}; evidence=[]; probe_meta=[]
for sense,entry in rows:
    lemma=str(entry.normalized_lemma or entry.lemma or "").strip(); ctx=context.get(int(sense.id),{})
    etype=getattr(entry.entry_type,"value",str(entry.entry_type)); dep=ctx.get("dependency")
    ps=probes(lemma,entry.part_of_speech,etype,dep); accepted={}
    probe_meta.append({"sense_id":int(sense.id),"entry_id":int(entry.id),"lemma":lemma,"declared_pos":entry.part_of_speech,"entry_type":etype,"dependency":dep,"candidate_type":ctx.get("candidate_type"),"surface":ctx.get("surface"),"probes":[{"kind":x[0],"text":x[1],"base_confidence":x[2],"effective_pos":x[3],"pos_reason":x[4]} for x in ps]})
    for kind,text,base,ep,pos_reason in ps:
        outs=backend.translate_batch([text],generation_settings={"num_beams":beam,"num_return_sequences":hypotheses,"max_new_tokens":32})[0]
        for rank,out in enumerate(outs):
            cleaned,transform=clean_target(out.text,kind); ok,reason=admissible(lemma,cleaned,etype)
            conf=confidence(rank,kind,base,ep,cleaned,etype) if ok else None
            isinf=ep=="VERB" and infinitive(cleaned)
            target_pos="VERB" if entry.part_of_speech=="VERB" and isinf else ("ADJ" if entry.part_of_speech=="ADJ" and kind=="adjective_copula" else None)
            ev={"sense_id":int(sense.id),"entry_id":int(entry.id),"lemma":lemma,"declared_pos":entry.part_of_speech,"effective_pos":ep,"pos_reason":pos_reason,"entry_type":etype,"dependency":dep,"probe_kind":kind,"probe_text":text,"rank":rank,"target":out.text,"cleaned_target":cleaned,"target_transform":transform,"raw_score":out.raw_score,"accepted":ok,"rejection_reason":reason,"provider_confidence":conf,"target_pos_hint":target_pos}
            evidence.append(ev)
            if not ok:continue
            n=norm(cleaned); candidate={"translation":cleaned,"confidence":conf,"context_compatibility":conf,"literal":True,"target_pos":target_pos,"target_lemma":cleaned if target_pos else None}
            prior=accepted.get(n)
            if prior is None or (candidate["confidence"],candidate["context_compatibility"])>(prior["confidence"],prior["context_compatibility"]): accepted[n]=candidate
    entries[lemma]=sorted(accepted.values(),key=lambda x:(-x["confidence"],-x["context_compatibility"],norm(x["translation"])))[:maximum]
summary={"sense_count":len(rows),"entry_count":len(entries),"candidate_count":sum(len(x) for x in entries.values()),"rejected_count":sum(1 for x in evidence if not x["accepted"]),"dependency_pos_repair_count":sum(1 for x in probe_meta if any(p["pos_reason"]=="dependency_pos_repair" for p in x["probes"])),"backend_compute_type":backend.compute_type,"backend_runtime":backend.runtime_backend_key}
print(json.dumps({"entries":entries,"evidence":evidence,"probe_meta":probe_meta,"summary":summary},ensure_ascii=False)); e.dispose()
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
    beam_size: int = 12,
    num_hypotheses: int = 12,
    maximum_candidates_per_lemma: int = 8,
    model_name: str = "OPUS EN-RU dictionary-shaped lexical n-best provider",
    license_expression: str = "Apache-2.0",
) -> dict[str, Any]:
    database = Path(database).expanduser().resolve()
    model_path = Path(model_path).expanduser().resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(model_path)
    if not re.fullmatch(r"[0-9a-fA-F]{64}", archive_sha256):
        raise ValueError("archive_sha256 must be a 64-character SHA-256")
    requested = [int(x) for x in sense_ids]
    result = core._run([
        "-c", _helper_code(), str(database), str(model_path), str(revision),
        str(int(beam_size)), str(int(num_hypotheses)), str(int(maximum_candidates_per_lemma)),
        json.dumps(requested, separators=(",", ":")),
    ], timeout=900)
    payload = core._parse_json(result.stdout, context="lexical OPUS provider")
    entries = dict(payload.get("entries") or {})
    snapshot = {
        "source_type": "model",
        "name": model_name,
        "version": SNAPSHOT_VERSION,
        "revision": str(revision),
        "sha256": archive_sha256.lower(),
        "license_expression": license_expression,
        "license_class": "attribution_required",
        "commercial_allowed": True,
        "attribution_required": True,
        "license_review_status": "machine_assessed",
        "available": True,
        "network_access": False,
        "source_language": "en",
        "target_language": "ru",
        "source_uri": source_uri,
        "local_path": str(model_path),
        "entries": entries,
        "capability_claim": "production",
        "is_smoke": False,
    }
    canonical_entries = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema": PROVIDER_SCHEMA,
        "provider": "contextual-lexical-opus-v3",
        "snapshot": snapshot,
        "entries_sha256": hashlib.sha256(canonical_entries.encode("utf-8")).hexdigest(),
        "summary": payload.get("summary") or {},
        "probe_meta": payload.get("probe_meta") or [],
        "evidence": payload.get("evidence") or [],
        "settings": {
            "beam_size": int(beam_size),
            "num_hypotheses": int(num_hypotheses),
            "maximum_candidates_per_lemma": int(maximum_candidates_per_lemma),
            "probe_policy": "pos-dependency-dictionary-shape-v3",
            "generic_argument_transform": "strip-russian-placeholder-v1",
            "mwe_completeness_required": True,
            "target_language": "ru",
            "network_access": False,
        },
    }


def run_stage20_with_snapshot(
    core: RocketDictCore,
    database: Path | str,
    provider_result: dict[str, Any],
    *,
    source_policy: str = "aligned-local-consensus",
    actor: str = "rocketdict-workbench:contextual-lexical-opus-v3",
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
    settings["algorithm_key"]="deterministic-multisource-sense-translation+workbench-lexical-v3"
    result=svc.generate(int(sense.id),"ru",settings=settings,actor=actor)
    data=svc.get_selection(int(result.selection_revision_id)); items=data.get("items") or []; selected=[]
    for row in items:
        c=row.get("candidate") or {}; i=row.get("item") or {}
        selected.append({"translation":c.get("translation_text"),"position":i.get("position"),"role":i.get("role"),"confidence":i.get("confidence"),"candidate_id":c.get("id"),"target_lemma":c.get("target_lemma"),"target_pos":c.get("target_part_of_speech")})
    selected.sort(key=lambda x:(x.get("position") or 999999))
    out.append({"sense_id":int(sense.id),"entry_id":int(entry.id),"lemma":entry.lemma,"normalized_lemma":entry.normalized_lemma,"part_of_speech":entry.part_of_speech,"entry_type":getattr(entry.entry_type,"value",str(entry.entry_type)),"selection_revision_id":int(result.selection_revision_id),"generation_run_id":int(result.generation_run_id),"cache_hit":bool(result.cache_hit),"coverage_complete":bool(result.coverage_complete),"selected":selected})
print(json.dumps({"source_policy":policy,"results":out},ensure_ascii=False)); e.dispose()
'''
    requested = [int(x) for x in sense_ids]
    result = core._run([
        "-c", code, str(Path(database).expanduser().resolve()),
        json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
        source_policy, actor, json.dumps(requested, separators=(",", ":")),
    ], timeout=600)
    return dict(core._parse_json(result.stdout, context="Stage20 lexical snapshot run"))


def write_provider_evidence(path: Path | str, payload: dict[str, Any]) -> Path:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path
