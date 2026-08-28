from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import urllib.request

ROOT = Path('work-rule-tokenizer-recovery')
ROOT.mkdir(exist_ok=True)
GO_URL = 'https://go.dev/src/testdata/Isaac.Newton-Opticks.txt?m=text'
GO_SHA = 'd4a9ac22462b35e7821a4f2706c211093da678620a8f9997989ee7cf8d507bbd'
EXCERPT_SHA = '9c7ad0cbf391ca31a8861c2b6d88f59aa0c85c12f1f935cb0bc340a9d2abd144'
EXPECTED_HEAVY_TOTAL = 107423
EXPECTED_UNITS = 461

DEMOS = {
    'Hello world.': 4,
    'The sensor works.': 5,
    'It is stable.': 5,
    'Second sentence.': 4,
}

PATTERNS = {
    'word_or_single_nonspace_punct': r'(?u)\w+|[^\w\s]',
    'word_or_punct_run': r'(?u)\w+|[^\w\s]+',
    'apostrophe_word_or_single_punct': r"(?u)\w+(?:['’]\w+)*|[^\w\s]",
    'hyphen_apostrophe_word_or_single_punct': r"(?u)\w+(?:[-'’]\w+)*|[^\w\s]",
    'ascii_word_or_single_punct': r'[A-Za-z0-9_]+|[^A-Za-z0-9_\s]',
    'nonspace_runs': r'\S+',
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get_source() -> bytes:
    p = ROOT / 'opticks.txt'
    req = urllib.request.Request(GO_URL, headers={'User-Agent':'RocketDict-RuleTokenizer-Recovery/1'})
    with urllib.request.urlopen(req, timeout=60) as src, p.open('wb') as out:
        shutil.copyfileobj(src, out)
    b = p.read_bytes()
    if sha(b) != GO_SHA:
        raise RuntimeError(f'Go SHA mismatch: {sha(b)}')
    return b


def excerpt(raw: bytes) -> str:
    text = raw.decode('utf-8')
    ms = list(re.finditer(r'\S+', text, re.UNICODE))
    prefix = (text[:ms[89999].end()] + '\n').encode('utf-8')
    if sha(prefix) != EXCERPT_SHA:
        raise RuntimeError(f'excerpt mismatch: {len(prefix)} {sha(prefix)}')
    return prefix.decode('utf-8')


def main() -> None:
    text = excerpt(get_source())
    rows=[]
    for name, pat in PATTERNS.items():
        rx=re.compile(pat)
        raw_count=len(rx.findall(text))
        for overhead in range(0,4):
            demo={s:len(rx.findall(s))+overhead for s in DEMOS}
            demo_ok=demo==DEMOS
            heavy=raw_count + overhead*EXPECTED_UNITS
            rows.append({
                'pattern':name,'regex':pat,'overhead_per_unit':overhead,
                'demo_counts':demo,'demo_exact':demo_ok,
                'raw_excerpt_tokens':raw_count,
                'heavy_total_if_461_units':heavy,
                'heavy_delta':heavy-EXPECTED_HEAVY_TOTAL,
                'heavy_exact':heavy==EXPECTED_HEAVY_TOTAL,
                'joint_exact':demo_ok and heavy==EXPECTED_HEAVY_TOTAL,
            })
    rows.sort(key=lambda r:(not r['demo_exact'],abs(r['heavy_delta']),r['pattern'],r['overhead_per_unit']))
    report={
        'schema':'rocketdict-rule-tokenizer-recovery/1',
        'inputs':{'go_sha256':GO_SHA,'excerpt_sha256':EXCERPT_SHA,'expected_units':EXPECTED_UNITS,'expected_source_token_count':EXPECTED_HEAVY_TOTAL},
        'joint_exact_count':sum(r['joint_exact'] for r in rows),
        'demo_exact_rows':[r for r in rows if r['demo_exact']],
        'top_rows':rows[:20],
    }
    (ROOT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
