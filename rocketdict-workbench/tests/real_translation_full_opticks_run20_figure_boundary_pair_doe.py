from __future__ import annotations

"""Read-only whole-pair DOE for syntactically split leading figure references.

In run20 every prose-bearing ``[in _Fig._ N.]`` row follows a short preceding
row whose source phrase is syntactically incomplete (for example ``Let the
second Prism DH ``).  This is a source-defined parser/planner boundary family.
The current hard failure at sequence 325 loses the complete figure-reference
lead.  This DOE translates each contiguous previous+figure row as one immutable
source unit with rank-0 OPUS and TC-big, without target repair or separator
injection.  Only already-hard-failing members may ever become rescue triggers.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from rocketdict.alternative_mt_runtime import TcBigTranslator, load_tc_big_asset
from rocketdict.database import connect, get_document, get_run, get_run_items
from rocketdict.emphasis_markup import compare_emphasis_markup_preservation
from rocketdict.runtime import OpusTranslator
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-figure-boundary-pair-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_FAMILY_COUNT = 15
EXPECTED_TRIGGER_SEQUENCES = [325]
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 1024
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.50
_REFERENCE_RE = re.compile(r"\A\[in\s+_Fig\._\s+(?P<number>\d+)\.\]", re.IGNORECASE)
_TARGET_REF_TEMPLATE = r"\[[^\]]*_(?:Fig\.|Фиг\.|рис\.)_[^\]]*(?<!\d){number}(?!\d)[^\]]*\.\]"
_TERMINAL_RE = re.compile(r"[.!?][\"'’”\]\)]*\s*\Z")


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False).encode()).hexdigest()


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def _ref_preserved(target: str, number: str) -> bool:
    return re.search(_TARGET_REF_TEMPLATE.format(number=re.escape(number)), target, re.IGNORECASE) is not None


def _candidate(source: str, target: str, *, figure_number: str) -> dict[str, Any]:
    verdict=evaluate_rescue_pair(source,target)
    emphasis=compare_emphasis_markup_preservation(source,target)
    ratio=_alpha(target)/_alpha(source) if _alpha(source) else 1.0
    ref=_ref_preserved(target,figure_number)
    accepted=bool(target.strip() and verdict.get('strictly_eligible') is True and emphasis.get('passed') is True and ref and MIN_SOURCE_ALPHA_RATIO <= ratio <= MAX_SOURCE_ALPHA_RATIO)
    return {'mechanically_admissible':accepted,'mechanical_verdict':verdict,'emphasis_markup':emphasis,'reference_preserved':ref,'source_alpha_ratio':ratio,'source_alpha_ratio_range':[MIN_SOURCE_ALPHA_RATIO,MAX_SOURCE_ALPHA_RATIO]}


def main() -> int:
    root=Path(os.environ.get('ROCKETDICT_RUN20_FIGURE_PAIR_DOE_ROOT','work/run20-figure-boundary-pair-doe')).resolve()
    root.mkdir(parents=True,exist_ok=True)
    database=root/'rocketdict.sqlite'
    if not database.is_file() or _sha(database)!=BASE_DATABASE_SHA256: raise RuntimeError('figure-pair DOE requires exact run20 database')
    with connect(database,readonly=True) as connection:
        run=get_run(connection,BASE_RUN_ID); output=dict(run.get('output') or {})
        rows=sorted(get_run_items(connection,BASE_RUN_ID,kind='translation_segment'),key=lambda r:int(r['sequence_number']))
        document=get_document(connection,int(output['document_version_id']))
    if str(run.get('output_sha256') or '')!=BASE_OUTPUT_SHA256: raise RuntimeError('run20 output identity drift')
    if str(document.get('text_sha256') or '')!=SOURCE_TEXT_SHA256: raise RuntimeError('run20 source identity drift')
    content=str(document['content_text'])
    if ''.join(str(r.get('source_text') or '') for r in rows)!=content: raise RuntimeError('run20 source coverage drift')

    family=[]
    for index,row in enumerate(rows):
        source=str(row.get('source_text') or '')
        match=_REFERENCE_RE.match(source)
        if match is None or index==0: continue
        # Two bare-reference rows have no prose body and are not this family.
        if not source[match.end():].strip(): continue
        previous=rows[index-1]
        previous_source=str(previous.get('source_text') or '')
        if int(previous['source_end'])!=int(row['source_start']): raise RuntimeError('figure boundary pair is not source-contiguous')
        if _TERMINAL_RE.search(previous_source): raise RuntimeError('figure boundary predecessor unexpectedly terminal')
        current_verdict=evaluate_rescue_pair(source,str(row.get('target_text') or ''))
        number=str(match.group('number'))
        current_ref=_ref_preserved(str(row.get('target_text') or ''),number)
        family.append({'previous':previous,'row':row,'figure_number':number,'source':previous_source+source,'base_target':str(previous.get('target_text') or '')+str(row.get('target_text') or ''),'trigger':bool(current_verdict.get('product_hard_passed') is not True and not current_ref),'current_verdict':current_verdict,'current_reference_preserved':current_ref})
    if len(family)!=EXPECTED_FAMILY_COUNT: raise RuntimeError(f'figure boundary family census drift: {len(family)}')
    triggers=[int(x['row']['sequence_number']) for x in family if x['trigger']]
    if triggers!=EXPECTED_TRIGGER_SEQUENCES: raise RuntimeError(f'figure boundary trigger census drift: {triggers!r}')

    opus=OpusTranslator(device='cpu',compute_type='float32')
    tc=TcBigTranslator(device='cpu',compute_type='float32')
    records=[]
    for item in family:
        models={}
        for name,translator in (('opus',opus),('tc_big',tc)):
            generated=translator.translate([item['source']],beam_size=BEAM_SIZE,num_hypotheses=NUM_HYPOTHESES,max_decoding_length=MAX_DECODING_LENGTH)
            if len(generated)!=1 or len(generated[0])!=1: raise RuntimeError('figure boundary translation cardinality drift')
            hyp=generated[0][0]; target=str(hyp.get('text') or '')
            models[name]={'score':hyp.get('score'),'candidate_target_text':target,**_candidate(item['source'],target,figure_number=item['figure_number'])}
        records.append({'sequence_number':int(item['row']['sequence_number']),'previous_sequence_number':int(item['previous']['sequence_number']),'source_start':int(item['previous']['source_start']),'source_end':int(item['row']['source_end']),'figure_number':item['figure_number'],'source_text':item['source'],'base_target_text':item['base_target'],'trigger':item['trigger'],'current_reference_preserved':item['current_reference_preserved'],'current_verdict':item['current_verdict'],'models':models})

    trigger_record=next(r for r in records if r['sequence_number']==325)
    asset=load_tc_big_asset()
    evidence={'schema':SCHEMA,'purpose':'read-only whole-boundary-pair DOE for syntactically split leading figure references','promotion_allowed':False,'automatic_product_default_allowed':False,'semantic_review_required':True,'base_database_sha256':BASE_DATABASE_SHA256,'base_translation_run_id':BASE_RUN_ID,'base_translation_output_sha256':BASE_OUTPUT_SHA256,'source_text_sha256':SOURCE_TEXT_SHA256,'family_count':len(records),'family_sequences':[r['sequence_number'] for r in records],'trigger_sequences':triggers,'records':records,'trigger_model_admissibility':{m:bool(trigger_record['models'][m]['mechanically_admissible']) for m in ('opus','tc_big')},'tc_big_asset':{'manifest_sha256':asset.manifest_sha256,'payload_tree_sha256':asset.payload_tree_sha256,'payload_file_count':asset.payload_file_count,'payload_bytes':asset.payload_bytes},'source_coverage_byte_exact':True,'database_unchanged':True,'source_bytes_rewritten':False,'target_rewriting':False,'target_separator_injected':False,'placeholders':False,'post_translation_literal_injection':False,'corpus_specific_target_patches':False,'evaluator_weakened':False,'n_best_cherry_picking':False}
    if _sha(database)!=BASE_DATABASE_SHA256: raise RuntimeError('figure boundary DOE mutated run20 database')
    evidence['evidence_sha256']=_canonical_sha(evidence)
    (root/'full-opticks-run20-figure-boundary-pair-doe.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    summary={'family_count':len(records),'family_sequences':evidence['family_sequences'],'trigger_sequences':triggers,'trigger_model_admissibility':evidence['trigger_model_admissibility'],'evidence_sha256':evidence['evidence_sha256']}
    (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
