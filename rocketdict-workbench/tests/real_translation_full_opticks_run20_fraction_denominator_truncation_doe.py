from __future__ import annotations

"""Exact run20 TC-big rank-0 DOE for simple fraction-denominator truncation.

The trigger is derived from maintained numeric evidence.  It requires exactly
one missing simple ``N/D`` source fraction and exactly one unlicensed simple
``N/d`` target fraction with the same numerator, where ``d`` is a strict prefix
of ``D``.  No duplicate-required, critical-symbol or prime-notation defect may
co-occur.  This distinguishes a denominator truncation from nested formulas,
angle notation, large-integer corruption, or generic fraction-bearing prose.
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
from rocketdict.numeric_integrity import evaluate_numeric_symbol_pair
from rocketdict.translation_rescue import evaluate_rescue_pair

SCHEMA = "rocketdict-full-opticks-run20-fraction-denominator-truncation-doe/1"
BASE_DATABASE_SHA256 = "879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d"
BASE_RUN_ID = 20
BASE_OUTPUT_SHA256 = "e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85"
SOURCE_TEXT_SHA256 = "436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a"
EXPECTED_TRIGGER_SEQUENCES = [1570]
BEAM_SIZE = 6
NUM_HYPOTHESES = 1
MAX_DECODING_LENGTH = 768
MIN_SOURCE_ALPHA_RATIO = 0.65
MAX_SOURCE_ALPHA_RATIO = 1.50
_SIMPLE_FRACTION_RE = re.compile(r"\A(?P<n>\d+)/(?P<d>\d+)\Z")


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def _alpha(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def evaluate_fraction_denominator_trigger(source: str,target: str) -> dict[str,Any]:
    verdict=evaluate_numeric_symbol_pair(source,target)
    numeric=dict(verdict.get('numeric') or {})
    missing=dict(numeric.get('missing') or {})
    additions=dict(numeric.get('unlicensed_additions') or {})
    duplicate=dict(numeric.get('duplicate_required') or {})
    prime=dict(numeric.get('prime_notation') or {})
    missing_items=[key for key,count in missing.items() if int(count)==1]
    addition_items=[key for key,count in additions.items() if int(count)==1]
    pair=None
    if len(missing_items)==1 and len(addition_items)==1 and sum(missing.values())==1 and sum(additions.values())==1:
        required=_SIMPLE_FRACTION_RE.fullmatch(missing_items[0])
        observed=_SIMPLE_FRACTION_RE.fullmatch(addition_items[0])
        if required and observed:
            same_numerator=required.group('n')==observed.group('n')
            source_denominator=required.group('d'); target_denominator=observed.group('d')
            strict_prefix=source_denominator.startswith(target_denominator) and len(target_denominator)<len(source_denominator)
            if same_numerator and strict_prefix:
                pair={'required':missing_items[0],'observed':addition_items[0],'numerator':required.group('n'),'source_denominator':source_denominator,'target_denominator':target_denominator,'missing_denominator_suffix':source_denominator[len(target_denominator):]}
    eligible=bool(pair is not None and not duplicate and not verdict.get('symbol_mismatch') and prime.get('passed') is True)
    return {'eligible':eligible,'truncation_pair':pair,'numeric_symbol_verdict':verdict,'single_missing_literal':len(missing_items)==1 and sum(missing.values())==1,'single_unlicensed_addition':len(addition_items)==1 and sum(additions.values())==1,'no_duplicate_required':not duplicate,'no_symbol_mismatch':not verdict.get('symbol_mismatch'),'prime_notation_passed':prime.get('passed') is True}


def main() -> int:
    root=Path(os.environ.get('ROCKETDICT_RUN20_FRACTION_TRUNCATION_DOE_ROOT','work/run20-fraction-denominator-truncation-doe')).resolve(); root.mkdir(parents=True,exist_ok=True)
    database=root/'rocketdict.sqlite'
    if not database.is_file() or _sha(database)!=BASE_DATABASE_SHA256: raise RuntimeError('fraction DOE requires exact run20 database')
    with connect(database,readonly=True) as connection:
        run=get_run(connection,BASE_RUN_ID); output=dict(run.get('output') or {})
        rows=sorted(get_run_items(connection,BASE_RUN_ID,kind='translation_segment'),key=lambda r:int(r['sequence_number']))
        document=get_document(connection,int(output['document_version_id']))
    if str(run.get('output_sha256') or '')!=BASE_OUTPUT_SHA256: raise RuntimeError('run20 output identity drift')
    if str(document.get('text_sha256') or '')!=SOURCE_TEXT_SHA256: raise RuntimeError('source identity drift')
    content=str(document['content_text'])
    if ''.join(str(r.get('source_text') or '') for r in rows)!=content: raise RuntimeError('source coverage drift')
    attempts=[]
    for row in rows:
        source=str(row.get('source_text') or ''); target=str(row.get('target_text') or '')
        trigger=evaluate_fraction_denominator_trigger(source,target)
        if trigger['eligible']: attempts.append({'row':row,'trigger':trigger})
    sequences=[int(a['row']['sequence_number']) for a in attempts]
    if sequences!=EXPECTED_TRIGGER_SEQUENCES: raise RuntimeError(f'fraction-denominator trigger census drift: {sequences!r}')

    tc=TcBigTranslator(device='cpu',compute_type='float32'); records=[]
    for attempt in attempts:
        row=attempt['row']; source=str(row.get('source_text') or '')
        generated=tc.translate([source],beam_size=BEAM_SIZE,num_hypotheses=NUM_HYPOTHESES,max_decoding_length=MAX_DECODING_LENGTH)
        if len(generated)!=1 or len(generated[0])!=1: raise RuntimeError('TC-big cardinality drift')
        hyp=generated[0][0]; target=str(hyp.get('text') or '')
        verdict=evaluate_rescue_pair(source,target); emphasis=compare_emphasis_markup_preservation(source,target)
        ratio=_alpha(target)/_alpha(source) if _alpha(source) else 1.0
        accepted=bool(target.strip() and verdict.get('strictly_eligible') is True and emphasis.get('passed') is True and MIN_SOURCE_ALPHA_RATIO<=ratio<=MAX_SOURCE_ALPHA_RATIO)
        records.append({'sequence_number':int(row['sequence_number']),'source_start':int(row['source_start']),'source_end':int(row['source_end']),'source_text':source,'current_target_text':str(row.get('target_text') or ''),'trigger':attempt['trigger'],'candidate_target_text':target,'candidate_score':hyp.get('score'),'candidate_verdict':verdict,'emphasis_markup':emphasis,'source_alpha_ratio':ratio,'mechanically_admissible':accepted})
    asset=load_tc_big_asset()
    evidence={'schema':SCHEMA,'purpose':'exact run20 TC-big rank0 DOE for simple fraction denominator truncation','promotion_allowed':False,'automatic_product_default_allowed':False,'semantic_review_required':True,'base_database_sha256':BASE_DATABASE_SHA256,'base_translation_run_id':BASE_RUN_ID,'base_translation_output_sha256':BASE_OUTPUT_SHA256,'source_text_sha256':SOURCE_TEXT_SHA256,'trigger_sequences':sequences,'records':records,'tc_big_asset':{'manifest_sha256':asset.manifest_sha256,'payload_tree_sha256':asset.payload_tree_sha256,'payload_file_count':asset.payload_file_count,'payload_bytes':asset.payload_bytes},'source_coverage_byte_exact':True,'database_unchanged':True,'source_bytes_rewritten':False,'target_rewriting':False,'placeholders':False,'post_translation_literal_injection':False,'corpus_specific_target_patches':False,'evaluator_weakened':False,'n_best_cherry_picking':False}
    if _sha(database)!=BASE_DATABASE_SHA256: raise RuntimeError('fraction DOE mutated run20 database')
    evidence['evidence_sha256']=_canonical_sha(evidence)
    (root/'full-opticks-run20-fraction-denominator-truncation-doe.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    summary={'trigger_sequences':sequences,'mechanically_admissible_sequences':[r['sequence_number'] for r in records if r['mechanically_admissible']],'evidence_sha256':evidence['evidence_sha256']}
    (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
