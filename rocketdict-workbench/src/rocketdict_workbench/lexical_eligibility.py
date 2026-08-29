from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import RocketDictCore

POLICY_KEY = "workbench-content-pos-v1"
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
FUNCTION_POS = {"DET", "AUX", "ADP", "PRON", "PART", "CCONJ", "SCONJ", "PUNCT", "SPACE", "SYM", "NUM"}


def candidate_is_product_eligible(candidate: dict[str, Any]) -> tuple[bool, str]:
    tokens = list(candidate.get("tokens") or [])
    if not tokens:
        return False, "no_token_evidence"
    if len(tokens) > 1:
        if any(str(t.get("pos") or "X") in CONTENT_POS for t in tokens):
            return True, "multiword_has_content_head"
        return False, "multiword_without_content_pos"
    token = tokens[0]
    pos = str(token.get("pos") or "X")
    text = str(token.get("text") or "")
    ctype = str(candidate.get("type") or "")
    if pos in CONTENT_POS:
        return True, "content_pos"
    if ctype == "abbreviation" and text.isalpha() and text.upper() == text and 2 <= len(text) <= 8:
        return True, "alphabetic_abbreviation"
    if pos in FUNCTION_POS:
        return False, f"non_dictionary_pos:{pos}"
    if any(ch.isdigit() for ch in text):
        return False, "numeric_or_designation"
    return False, f"unsupported_pos:{pos}"


def _helper_code() -> str:
    return r'''
import json,sys
from collections import Counter
from pathlib import Path
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.extraction.source_service import SourceLexicalExtractionService

CONTENT={"NOUN","PROPN","VERB","ADJ","ADV"}
FUNCTION={"DET","AUX","ADP","PRON","PART","CCONJ","SCONJ","PUNCT","SPACE","SYM","NUM"}
POLICY="workbench-content-pos-v1"

class ProductSourceLexicalExtractionService(SourceLexicalExtractionService):
    @classmethod
    def _settings(cls,supplied):
        out=super()._settings(supplied)
        out["workbench_lexical_eligibility_policy"]=POLICY
        return out

    @staticmethod
    def _product_word_token(token):
        if not SourceLexicalExtractionService._word_token(token): return False
        pos=str(token.get("pos") or "X")
        text=str(token.get("text") or "")
        if pos in CONTENT:return True
        if pos in FUNCTION:return False
        # Uppercase alphabetic abbreviations remain lexical evidence.
        return text.isalpha() and text.upper()==text and 2<=len(text)<=8

    @staticmethod
    def _word_token(token):
        # Used by coverage materialization: non-dictionary function/number tokens
        # are retained as rejected/non-significant rather than deleted.
        return ProductSourceLexicalExtractionService._product_word_token(token)

    @staticmethod
    def _eligible_candidate(candidate):
        tokens=list(candidate.get("tokens") or [])
        if not tokens:return False
        if len(tokens)>1:
            return any(str(t.get("pos") or "X") in CONTENT for t in tokens)
        token=tokens[0]; pos=str(token.get("pos") or "X"); text=str(token.get("text") or "")
        if pos in CONTENT:return True
        if candidate.get("type")=="abbreviation" and text.isalpha() and text.upper()==text and 2<=len(text)<=8:return True
        return False

    def _generate(self,segments,tokens_by_analysis,spans_by_analysis,settings):
        # Generation itself must see function words so phrasal/prepositional MWEs
        # such as "look at" remain discoverable. Temporarily bind the historical
        # broad token predicate only during candidate generation.
        self.__dict__["_word_token"]=SourceLexicalExtractionService._word_token
        try:
            candidates,_old_word_map,_old_multi=super()._generate(segments,tokens_by_analysis,spans_by_analysis,settings)
        finally:
            self.__dict__.pop("_word_token",None)
        candidates=[c for c in candidates if self._eligible_candidate(c)]
        candidates.sort(key=lambda c:(c["segment_sequence"],c["start"],c["end"],c["type"],c["normalized"]))
        word_map={}; multi=Counter()
        for number,c in enumerate(candidates):
            if len(c["tokens"])==1 and any(x.get("evidence")=="saved_nlp_token" for x in c.get("evidences") or []):
                t=c["tokens"][0]; word_map[(c["fragment_occurrence_id"],int(t["token_index"]))]=number
            if len(c["tokens"])>1:
                for t in c["tokens"]:multi[(c["fragment_occurrence_id"],int(t["token_index"]))]+=1
        return candidates,word_map,dict(multi)

db=Path(sys.argv[1]); nlp_run_id=int(sys.argv[2]); supplied=json.loads(sys.argv[3]); actor=sys.argv[4]
e=bootstrap_database(db); sf=create_session_factory(e)
svc=ProductSourceLexicalExtractionService(sf)
result=svc.extract_from_nlp(nlp_run_id,settings=supplied,name="Workbench product lexical extraction",actor=actor)
print(json.dumps({
 "policy":POLICY,
 "extraction_run_id":result.extraction_run_id,
 "stage_result_id":result.stage_result_id,
 "candidate_count":result.candidate_count,
 "occurrence_count":result.occurrence_count,
 "lexical_entry_count":result.lexical_entry_count,
 "coverage_complete":result.coverage_complete,
 "uncovered_token_count":result.uncovered_token_count,
 "cache_hit":result.cache_hit,
},ensure_ascii=False))
e.dispose()
'''


def run_product_lexical_extraction(
    core: RocketDictCore,
    database: Path | str,
    nlp_run_id: int,
    *,
    actor: str = "rocketdict-workbench:product-content-pos-v1",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    supplied = dict(settings or {})
    supplied["workbench_lexical_eligibility_policy"] = POLICY_KEY
    result = core._run(
        ["-c", _helper_code(), str(Path(database).expanduser().resolve()), str(int(nlp_run_id)), json.dumps(supplied, ensure_ascii=False, separators=(",", ":")), actor],
        timeout=600,
    )
    return dict(core._parse_json(result.stdout, context="Product lexical extraction"))
