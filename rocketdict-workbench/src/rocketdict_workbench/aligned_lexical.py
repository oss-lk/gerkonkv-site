from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore

POLICY_KEY = "workbench-aligned-content-pos-v3"
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
FUNCTION_POS = {"DET", "AUX", "ADP", "PRON", "PART", "CCONJ", "SCONJ", "PUNCT", "SPACE", "SYM", "NUM"}
ALLOWED_MWE_TYPES = {
    "phrasal_verb", "prepositional_verb", "idiom", "collocation",
    "compound_term", "technical_term", "grammar_expression",
    "discontinuous_expression",
}


def candidate_is_product_eligible(candidate: dict[str, Any]) -> tuple[bool, str]:
    tokens = list(candidate.get("tokens") or [])
    if not tokens:
        return False, "no_token_evidence"
    if len(tokens) == 1:
        token = tokens[0]
        pos = str(token.get("pos") or "X")
        text = str(token.get("text") or "")
        if pos in CONTENT_POS:
            return True, "content_pos"
        if candidate.get("type") == "abbreviation" and text.isalpha() and text.upper() == text and 2 <= len(text) <= 8:
            return True, "alphabetic_abbreviation"
        if pos in FUNCTION_POS:
            return False, f"non_dictionary_pos:{pos}"
        if any(ch.isdigit() for ch in text):
            return False, "numeric_or_designation"
        return False, f"unsupported_pos:{pos}"
    kind = str(candidate.get("type") or "")
    if kind not in ALLOWED_MWE_TYPES:
        return False, f"non_dictionary_mwe:{kind}"
    if any(str(token.get("pos") or "X") in CONTENT_POS for token in tokens):
        return True, "dictionary_mwe_with_content_head"
    return False, "mwe_without_content_pos"


def _helper_code() -> str:
    return r'''
import json,sys
from pathlib import Path
from sqlalchemy import select
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.database.base import RunStatus
from rocketdict.database.models.linguistic import NlpRun,NlpRunAnalysisLink,NlpAnalysis,Token,LexicalEntry
from rocketdict.database.models.structure import FragmentOccurrence,CanonicalFragment
from rocketdict.database.models.extraction import LexicalExtractionOccurrence,LexicalExtractionRun
from rocketdict.extraction.service import LexicalExtractionService

CONTENT={"NOUN","PROPN","VERB","ADJ","ADV"}
FUNCTION={"DET","AUX","ADP","PRON","PART","CCONJ","SCONJ","PUNCT","SPACE","SYM","NUM"}
ALLOWED_MWE={"phrasal_verb","prepositional_verb","idiom","collocation","compound_term","technical_term","grammar_expression","discontinuous_expression"}
POLICY="workbench-aligned-content-pos-v3"

class ProductAlignedLexicalExtractionService(LexicalExtractionService):
    @classmethod
    def _settings(cls,supplied):
        out=super()._settings(supplied)
        out["algorithm_key"]=POLICY
        out["workbench_lexical_eligibility_policy"]=POLICY
        return out

    @classmethod
    def _product_word(cls,token):
        if not LexicalExtractionService._word(token): return False
        pos=str(token.get("pos") or "X"); text=str(token.get("text") or "")
        if pos in CONTENT:return True
        if pos in FUNCTION:return False
        return text.isalpha() and text.upper()==text and 2<=len(text)<=8

    @classmethod
    def _word(cls,token):
        return cls._product_word(token)

    @classmethod
    def _eligible_candidate(cls,candidate):
        tokens=list(candidate.get("tokens") or [])
        if not tokens:return False
        if len(tokens)==1:
            token=tokens[0]; pos=str(token.get("pos") or "X"); text=str(token.get("text") or "")
            return pos in CONTENT or (candidate.get("type")=="abbreviation" and text.isalpha() and text.upper()==text and 2<=len(text)<=8)
        return str(candidate.get("type") or "") in ALLOWED_MWE and any(str(t.get("pos") or "X") in CONTENT for t in tokens)

    def _generate_candidates(self,segments_tokens,settings):
        self.__dict__["_word"]=LexicalExtractionService._word
        try:
            candidates=super()._generate_candidates(segments_tokens,settings)
        finally:
            self.__dict__.pop("_word",None)
        return [c for c in candidates if self._eligible_candidate(c)]

    def _select_candidates(self,candidates):
        super()._select_candidates(candidates)
        for candidate in candidates:
            if len(candidate.get("tokens") or [])==1 and self._eligible_candidate(candidate):
                candidate["selected"]=True; candidate["review_status"]="automatic"

    def _saved_tokens(self,session,alignment,segment):
        run_id,tokens=super()._saved_tokens(session,alignment,segment)
        if tokens:
            return run_id,tokens
        runs=session.scalars(select(NlpRun).where(
            NlpRun.document_version_id==alignment.document_version_id,
            NlpRun.status.in_([RunStatus.COMPLETED,RunStatus.COMPLETED_WITH_WARNINGS]),
        ).order_by(NlpRun.id.desc())).all()
        for run in runs:
            rows=session.execute(
                select(NlpRunAnalysisLink,NlpAnalysis,FragmentOccurrence,CanonicalFragment)
                .join(NlpAnalysis,NlpAnalysis.id==NlpRunAnalysisLink.nlp_analysis_id)
                .join(FragmentOccurrence,FragmentOccurrence.id==NlpRunAnalysisLink.fragment_occurrence_id)
                .join(CanonicalFragment,CanonicalFragment.id==NlpAnalysis.canonical_fragment_id)
                .where(
                    NlpRunAnalysisLink.nlp_run_id==run.id,
                    FragmentOccurrence.start_char<=segment.stream_start,
                    FragmentOccurrence.end_char>=segment.stream_end,
                ).order_by(NlpRunAnalysisLink.sequence_number)
            ).all()
            for _link,analysis,occurrence,fragment in rows:
                rel_start=int(segment.stream_start)-int(occurrence.start_char)
                rel_end=int(segment.stream_end)-int(occurrence.start_char)
                if rel_start<0 or rel_end>len(fragment.normalized_text):continue
                if self._normalize(fragment.normalized_text[rel_start:rel_end])!=self._normalize(segment.text):continue
                saved=session.scalars(select(Token).where(Token.nlp_analysis_id==analysis.id).order_by(Token.token_index)).all()
                converted=[]
                for token in saved:
                    start=int(occurrence.start_char)+int(token.start_char); end=int(occurrence.start_char)+int(token.end_char)
                    if start<segment.stream_start or end>segment.stream_end or end<=start:continue
                    converted.append({
                        "token_id":token.id,"nlp_analysis_id":analysis.id,"token_index":token.token_index,
                        "text":token.text,"start":start,"end":end,
                        "local_start":start-segment.stream_start,"local_end":end-segment.stream_start,
                        "lemma":token.lemma or token.lower or token.text,"pos":token.pos or "X","tag":token.tag,
                        "dependency":token.dependency,"head_token_index":token.head_token_index,
                        "entity_type":token.entity_type,"entity_iob":token.entity_iob,
                        "morph":token.morph_json or {},"flags":token.flags_json or {},
                        "source":"saved_nlp_offset_projection",
                    })
                if converted:return run.id,converted
        return None,[]

db=Path(sys.argv[1]); alignment_run_id=int(sys.argv[2]); supplied=json.loads(sys.argv[3]); actor=sys.argv[4]
e=bootstrap_database(db); sf=create_session_factory(e); svc=ProductAlignedLexicalExtractionService(sf)
result=svc.extract(alignment_run_id,settings=supplied,name="Workbench aligned product lexical extraction",actor=actor)
with sf() as s:
    run=s.get(LexicalExtractionRun,result.extraction_run_id)
    rows=s.execute(select(LexicalExtractionOccurrence,LexicalEntry).join(
        LexicalEntry,LexicalEntry.id==LexicalExtractionOccurrence.lexical_entry_id
    ).where(LexicalExtractionOccurrence.extraction_run_id==run.id).order_by(
        LexicalExtractionOccurrence.source_stream_start,LexicalExtractionOccurrence.id
    )).all()
    occurrences=[{
        "occurrence_id":occ.id,"entry_id":entry.id,"lemma":entry.normalized_lemma,
        "part_of_speech":entry.part_of_speech,"surface":occ.surface_text,
        "source_segment_id":occ.source_segment_id,"alignment_candidate_id":occ.alignment_candidate_id,
        "target_evidence":occ.target_evidence_text,
    } for occ,entry in rows]
print(json.dumps({
    "policy":POLICY,"extraction_run_id":result.extraction_run_id,"stage_result_id":result.stage_result_id,
    "alignment_run_id":result.alignment_run_id,"nlp_run_id":result.nlp_run_id,"source_mode":result.source_mode,
    "candidate_count":result.candidate_count,"selected_candidate_count":result.selected_candidate_count,
    "occurrence_count":result.occurrence_count,"lexical_entry_count":result.lexical_entry_count,
    "coverage_complete":result.coverage_complete,"uncovered_token_count":result.uncovered_token_count,
    "cache_hit":result.cache_hit,"target_evidence_occurrence_count":sum(1 for x in occurrences if x["target_evidence"]),
    "occurrences":occurrences,
},ensure_ascii=False))
e.dispose()
'''


def run_product_aligned_lexical_extraction(
    core: RocketDictCore,
    database: Path | str,
    alignment_run_id: int,
    *,
    settings: dict[str, Any] | None = None,
    actor: str = "rocketdict-workbench:aligned-content-pos-v3",
) -> dict[str, Any]:
    result = core._run([
        "-c", _helper_code(), str(Path(database).expanduser().resolve()), str(int(alignment_run_id)),
        json.dumps(dict(settings or {}), ensure_ascii=False, separators=(",", ":")), actor,
    ], timeout=600)
    payload = dict(core._parse_json(result.stdout, context="Product aligned lexical extraction"))
    if not payload.get("coverage_complete") or int(payload.get("uncovered_token_count") or 0) != 0:
        raise RuntimeError(f"Product lexical coverage is incomplete: {payload}")
    if payload.get("source_mode") != "aligned":
        raise RuntimeError(f"Product lexical extraction unexpectedly lost alignment: {payload.get('source_mode')}")
    return payload
