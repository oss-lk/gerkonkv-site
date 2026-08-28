from __future__ import annotations

"""NON-PROMOTIONAL occurrence-level accounting for F96 recovery.

Purpose: test whether the recorded F96 fields `source_occurrences=109` and
`chunk_count=168` are naturally explained by Stage12Pilot-selected TranslationUnit
members.  Candidate configs are ranked only on older 90k machine evidence; F96
metrics never tune the candidate family.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import shutil
import zipfile

import sentencepiece as spm

import stage8_f96_plan_recovery as r

OUT = Path("work-stage8-f96-occurrence-accounting/output")
DL = Path("work-stage8-f96-occurrence-accounting/downloads")
OUT.mkdir(parents=True, exist_ok=True)
DL.mkdir(parents=True, exist_ok=True)

@dataclass
class MemberUnit:
    id: int
    sequence_number: int
    source_text: str
    source_tokens: int
    paragraph_start: int
    paragraph_end: int
    occurrence_sequences: tuple[int, ...]
    occurrence_texts: tuple[str, ...]


def exact_excerpt(raw: bytes) -> str:
    text = raw.decode("utf-8")
    matches = list(re.finditer(r"\S+", text, flags=re.UNICODE))
    data = text[:matches[r.EXCERPT_NONWS_WORDS - 1].end()].encode("utf-8") + b"\n"
    if len(data) != r.EXCERPT_BYTES or r.sha_bytes(data) != r.EXCERPT_SHA:
        raise RuntimeError("historical excerpt identity mismatch")
    return data.decode("utf-8")


def get_inputs():
    go = DL / "Isaac.Newton-Opticks.txt"
    r.download_exact(r.GO_URLS, go, r.GO_SHA)
    gut = DL / "gutenberg-opticks.txt"
    r.download_exact((r.GUTENBERG_URL,), gut, r.GUTENBERG_SHA)
    opus = DL / "opus.zip"
    r.download_exact((r.OPUS_URL,), opus, r.OPUS_SHA)
    model_root = DL / "opus-model"
    if model_root.exists(): shutil.rmtree(model_root)
    model_root.mkdir()
    with zipfile.ZipFile(opus) as zf: zf.extractall(model_root)
    spm_paths = sorted(model_root.rglob("source.spm"))
    if not spm_paths: raise RuntimeError("source.spm missing")
    sp = spm.SentencePieceProcessor(model_file=str(spm_paths[0]))
    return go.read_text(encoding="utf-8"), gut.read_text(encoding="utf-8-sig"), sp


def tc(sp, text: str) -> int:
    return len(sp.encode(text, out_type=str))


def split_preserve_occurrence(sp, s: r.Sentence) -> list[r.Sentence]:
    if tc(sp, s.text) <= r.HARD_LIMIT:
        return [s]
    # Same transparent recovery splitter as v5, but preserve original occurrence sequence.
    out=[]; remaining=s.text
    while remaining:
        if tc(sp, remaining) <= r.HARD_LIMIT:
            out.append(r.Sentence(s.sequence, s.paragraph, remaining)); break
        lo,hi,best=1,len(remaining),1
        while lo<=hi:
            mid=(lo+hi)//2
            if tc(sp, remaining[:mid]) <= r.HARD_LIMIT: best=mid; lo=mid+1
            else: hi=mid-1
        cut=best
        punct=[m.end() for m in re.finditer(r"[.!?;:]\s+", remaining[:best])]
        spaces=[m.end() for m in re.finditer(r"\s+", remaining[:best])]
        if punct: cut=punct[-1]
        elif spaces: cut=spaces[-1]
        out.append(r.Sentence(s.sequence, s.paragraph, remaining[:cut]))
        remaining=remaining[cut:]
    return out


def make_member_plan(sp, sentences, *, preferred, boundary_ratio, boundary_mode):
    expanded=[]
    for s in sentences: expanded.extend(split_preserve_occurrence(sp,s))
    units=[]; current=[]; current_text=""
    def flush():
        nonlocal current,current_text
        if not current: return
        seqs=[]; texts=[]; seen=set()
        for s in current:
            if s.sequence not in seen:
                seen.add(s.sequence); seqs.append(s.sequence); texts.append(sentences[s.sequence].text)
        txt=current_text.strip()
        units.append(MemberUnit(len(units)+1,len(units),txt,tc(sp,txt),current[0].paragraph,current[-1].paragraph,tuple(seqs),tuple(texts)))
        current=[]; current_text=""
    for s in expanded:
        proposed=current_text + (" " if current_text else "") + s.text.strip()
        proposed_tokens=tc(sp,proposed)
        para_boundary=bool(current and current[-1].paragraph != s.paragraph)
        current_tokens=tc(sp,current_text) if current_text else 0
        close=False
        if para_boundary:
            if boundary_mode=="strict": close=True
            elif boundary_mode=="ratio": close=current_tokens >= preferred*boundary_ratio
            elif boundary_mode=="ratio_next": close=(current_tokens >= preferred*boundary_ratio or proposed_tokens > preferred)
        if current and (proposed_tokens > r.HARD_LIMIT or proposed_tokens > preferred or close):
            flush(); current=[s]; current_text=s.text.strip()
        else:
            current.append(s); current_text=proposed
    flush(); return units


def candidate_configs(hist_text, sp):
    segs=[]
    for abbrev_mode in ("minimal","scientific"):
      for split_semicolon in (False,True):
       for split_colon in (False,True):
        for heading_as_sentence in (False,True):
         sc={"abbrev_mode":abbrev_mode,"split_semicolon":split_semicolon,"split_colon":split_colon,"heading_as_sentence":heading_as_sentence}
         ss,meta=r.segment(hist_text,**sc)
         segs.append((abs(meta["sentence_count"]-r.HIST_SENTENCES),abs(meta["paragraphs_modelled"]-r.HIST_PARAGRAPHS),sc,meta,ss))
    segs.sort(key=lambda x:(x[0],x[1],str(x[2])))
    rows=[]
    planner=[]
    for preferred in (224,240,256,272,288,304,320,336,352,384):
      for mode in ("ratio","ratio_next"):
       for ratio in (.25,1/3,.4,.5,.6,.7,.8): planner.append((preferred,round(ratio,6),mode))
    for _,_,sc,meta,ss in segs[:6]:
      for preferred,ratio,mode in planner:
        plan=make_member_plan(sp,ss,preferred=preferred,boundary_ratio=ratio,boundary_mode=mode)
        score=(abs(meta["sentence_count"]-r.HIST_SENTENCES),abs(len(plan)-r.HIST_STAGE12_UNITS),abs(meta["paragraphs_modelled"]-r.HIST_PARAGRAPHS))
        rows.append((score,sc,meta,{"preferred":preferred,"boundary_ratio":ratio,"boundary_mode":mode}))
    rows.sort(key=lambda x:(x[0],str(x[1]),str(x[3])))
    return rows[:20]


def account(corpus_name,text,sp,sc,pc):
    ss,meta=r.segment(text,**sc)
    plan=make_member_plan(sp,ss,**pc)
    selected,total_words,coverage = r.Stage12PilotRunner._select_stratified(plan, r.TARGET_WORDS, r.PilotSamplingPolicy()) if False else (None,None,None)
    # Use exact recovered selector semantics through transparent helper clone in base module.
    selected,sel=r.select_stratified(plan)
    occ={}
    for u in selected:
        for seq,ot in zip(u.occurrence_sequences,u.occurrence_texts): occ[seq]=ot
    occurrence_rows=[(seq,occ[seq]) for seq in sorted(occ)]
    occurrence_words=sum(r.words(t) for _,t in occurrence_rows)
    chunk96=sum(max(1,math.ceil(tc(sp,t)/96)) for _,t in occurrence_rows)
    chunk128=sum(max(1,math.ceil(tc(sp,t)/128)) for _,t in occurrence_rows)
    joined="\n".join(t for _,t in occurrence_rows)
    sig={name:all(s in joined for s in sigs) for name,sigs in r.FAILURE_SIGNATURES.items()}
    return {
      "corpus":corpus_name,"segmentation":sc,"segmentation_meta":meta,"planner":pc,
      "plan_units":len(plan),"selected_units":len(selected),"selected_unit_words":sel["selected_words"],
      "source_occurrences_unique":len(occurrence_rows),"source_occurrence_words":occurrence_words,
      "occurrence_chunk96_lower_bound":chunk96,"occurrence_chunk128_lower_bound":chunk128,
      "failure_signatures":sig,"all_three_signatures":all(sig.values()),
      "selected_occurrence_sequences":[x[0] for x in occurrence_rows],
      "selected_occurrence_hashes":[r.sha_text(x[1]) for x in occurrence_rows],
    }


def main():
    go,gut,sp=get_inputs(); hist=exact_excerpt(go.encode("utf-8"))
    cfgs=candidate_configs(hist,sp)
    out=[]
    for hist_score,sc,meta,pc in cfgs:
      for cname,text in (("canonical_go_full",go),("github_gutenberg_full",gut)):
        row=account(cname,text,sp,sc,pc); row["historical_score"]=hist_score; out.append(row)
    def score(x):
      return (0 if x["corpus"]=="canonical_go_full" else 1,
              0 if x["all_three_signatures"] else 1,
              abs(x["source_occurrences_unique"]-109),
              abs(x["source_occurrence_words"]-5000),
              abs(x["occurrence_chunk96_lower_bound"]-168))
    ranked=sorted(out,key=score)
    report={"schema":"rocketdict-stage8-f96-occurrence-accounting/1","promotion_allowed":False,
      "claim":"diagnostic-only; Stage7/planner bytes still missing",
      "expected":{"source_words":5000,"source_occurrences":109,"chunk_count_f96":168},
      "rows":ranked}
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"best_score":score(ranked[0]),"best":{k:ranked[0][k] for k in ranked[0] if k not in ("selected_occurrence_sequences","selected_occurrence_hashes")},
             "go_top10":[{k:x[k] for k in ("historical_score","planner","plan_units","selected_units","selected_unit_words","source_occurrences_unique","source_occurrence_words","occurrence_chunk96_lower_bound","failure_signatures")} for x in ranked if x["corpus"]=="canonical_go_full"][:10]}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
