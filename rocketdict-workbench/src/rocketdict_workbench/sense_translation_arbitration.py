from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore
from .lexical_opus import normalize_lexical_text

POLICY_KEY = "lexical-primary-arbitration-v1"


def desired_primary_map(provider_result: dict[str, Any], stage20_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve the frozen lexical-provider primary for each generated sense.

    The provider result is source evidence; this function does not invent or
    rewrite translations. The selected surface must already exist as a Stage20
    candidate with accepted model evidence before it can be approved.
    """
    snapshot = provider_result.get("snapshot") or {}
    entries = snapshot.get("entries") or {}
    resolved: list[dict[str, Any]] = []
    for row in stage20_result.get("results") or []:
        lemma = str(row.get("normalized_lemma") or row.get("lemma") or "").strip()
        candidates = entries.get(lemma) or []
        if not candidates:
            raise RuntimeError(f"Lexical OPUS snapshot has no candidates for Stage20 sense {row.get('sense_id')} lemma={lemma!r}")
        top = candidates[0]
        translation = str(top.get("translation") or "").strip()
        if not translation:
            raise RuntimeError(f"Lexical OPUS primary is empty for lemma {lemma!r}")
        resolved.append({
            "sense_id": int(row["sense_id"]),
            "automatic_selection_revision_id": int(row["selection_revision_id"]),
            "lemma": lemma,
            "desired_translation": translation,
            "desired_normalized": normalize_lexical_text(translation),
            "provider_confidence": top.get("confidence"),
            "provider_target_pos": top.get("target_pos"),
        })
    return resolved


def _helper_code() -> str:
    return r'''
import json,sys,unicodedata,re
from pathlib import Path
from sqlalchemy import select
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.database.models.sense_translation import (
    SenseTranslationCandidate,SenseTranslationEvidence,SenseTranslationGenerationRun,
    SenseTranslationRunCandidate,SenseTranslationSelectionItem,SenseTranslationSelectionRevision,
)
from rocketdict.sense_translation.service import SenseTranslationService

POLICY="lexical-primary-arbitration-v1"
def norm(v):
    v=unicodedata.normalize("NFKC",v or "").strip()
    v=re.sub(r"^[\s\.,;:!?…\"'«»()\[\]{}]+|[\s\.,;:!?…\"'«»()\[\]{}]+$","",v)
    return re.sub(r"\s+"," ",v).casefold().strip()

db=Path(sys.argv[1]); requests=json.loads(sys.argv[2]); actor=sys.argv[3]
e=bootstrap_database(db);sf=create_session_factory(e);svc=SenseTranslationService(sf);out=[]
for req in requests:
    sense_id=int(req["sense_id"]);parent_id=int(req["automatic_selection_revision_id"]);desired_norm=str(req["desired_normalized"])
    with sf() as s:
        parent=s.get(SenseTranslationSelectionRevision,parent_id)
        if parent is None:raise RuntimeError(f"Stage20 parent selection missing: {parent_id}")
        run=s.get(SenseTranslationGenerationRun,parent.generation_run_id)
        if run is None or int(run.lexical_sense_id)!=sense_id:raise RuntimeError("Stage20 parent/sense provenance mismatch")
        rows=s.execute(select(SenseTranslationRunCandidate,SenseTranslationCandidate).join(
            SenseTranslationCandidate,SenseTranslationCandidate.id==SenseTranslationRunCandidate.sense_translation_candidate_id
        ).where(SenseTranslationRunCandidate.generation_run_id==run.id)).all()
        matches=[(rc,c) for rc,c in rows if norm(c.translation_text)==desired_norm]
        if not matches:raise RuntimeError(f"Desired lexical primary is absent from generation run {run.id}: {req['desired_translation']!r}")
        # Require accepted immutable model evidence for the exact candidate.
        eligible=[]
        for rc,c in matches:
            ev=s.scalar(select(SenseTranslationEvidence).where(
                SenseTranslationEvidence.generation_run_id==run.id,
                SenseTranslationEvidence.run_candidate_id==rc.id,
                SenseTranslationEvidence.source_type=="model",
                SenseTranslationEvidence.decision=="accepted",
            ).limit(1))
            if ev is not None:eligible.append((rc,c,ev))
        if not eligible:raise RuntimeError(f"Desired primary lacks accepted model evidence: {req['desired_translation']!r}")
        eligible.sort(key=lambda x:(-float(x[0].final_score or 0.0),x[1].id))
        desired_rc,desired,model_ev=eligible[0]
        current=s.scalar(select(SenseTranslationSelectionRevision).where(
            SenseTranslationSelectionRevision.generation_run_id==run.id,
            SenseTranslationSelectionRevision.is_current.is_(True),
        ).order_by(SenseTranslationSelectionRevision.revision_number.desc()))
        if current is not None and current.status=="approved":
            current_items=s.scalars(select(SenseTranslationSelectionItem).where(
                SenseTranslationSelectionItem.selection_revision_id==current.id
            ).order_by(SenseTranslationSelectionItem.position)).all()
            if len(current_items)==1 and current_items[0].sense_translation_candidate_id==desired.id:
                out.append({"sense_id":sense_id,"generation_run_id":run.id,"selection_revision_id":current.id,"candidate_id":desired.id,
                            "translation":desired.translation_text,"status":"approved","cache_hit":True,"model_evidence_id":model_ev.id,"policy":POLICY})
                continue
        parent_items=s.scalars(select(SenseTranslationSelectionItem).where(
            SenseTranslationSelectionItem.selection_revision_id==parent.id
        ).order_by(SenseTranslationSelectionItem.position)).all()
        selected=[x.sense_translation_candidate_id for x in parent_items]
    operations=[]
    for cid in selected:
        if cid!=desired.id:operations.append({"type":"reject","candidate_id":cid,"reason":"Product lexical form arbitration: sentence alignment remains context evidence, not headword-form authority"})
    if desired.id not in selected:
        operations.append({"type":"accept","candidate_id":desired.id,"reason":"Product lexical form arbitration: accepted immutable OPUS lexical-provider candidate with model provenance"})
    child=svc.create_manual_revision(parent_id,operations=operations,actor=actor,reason="Workbench Product Mode lexical-primary-arbitration-v1")
    approved=svc.approve(child.selection_revision_id,actor=actor,reason="Primary dictionary translation is an existing OPUS lexical candidate; alignment evidence remains preserved in the generation run")
    out.append({"sense_id":sense_id,"generation_run_id":child.generation_run_id,"selection_revision_id":approved.selection_revision_id,
                "candidate_id":desired.id,"translation":desired.translation_text,"status":approved.status,"cache_hit":False,
                "model_evidence_id":model_ev.id,"policy":POLICY})
print(json.dumps({"policy":POLICY,"results":out},ensure_ascii=False));e.dispose()
'''


def arbitrate_lexical_primaries(
    core: RocketDictCore,
    database: Path | str,
    provider_result: dict[str, Any],
    stage20_result: dict[str, Any],
    *,
    actor: str = "rocketdict-workbench:lexical-primary-arbitration-v1",
) -> dict[str, Any]:
    requests = desired_primary_map(provider_result, stage20_result)
    result = core._run([
        "-c", _helper_code(), str(Path(database).expanduser().resolve()),
        json.dumps(requests, ensure_ascii=False, separators=(",", ":")), actor,
    ], timeout=600)
    payload = dict(core._parse_json(result.stdout, context="Stage20 lexical primary arbitration"))
    rows = list(payload.get("results") or [])
    if len(rows) != len(requests):
        raise RuntimeError(f"Stage20 arbitration coverage mismatch: {len(rows)} != {len(requests)}")
    for request, row in zip(requests, rows, strict=True):
        if row.get("status") != "approved":
            raise RuntimeError(f"Stage20 arbitration did not approve sense {request['sense_id']}: {row}")
        if normalize_lexical_text(str(row.get("translation") or "")) != request["desired_normalized"]:
            raise RuntimeError(f"Stage20 arbitration changed the frozen lexical primary: expected {request}, got {row}")
    return {"policy": POLICY_KEY, "requests": requests, "results": rows}
