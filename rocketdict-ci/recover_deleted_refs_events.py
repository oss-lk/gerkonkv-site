from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request

OUT = Path('rocketdict-deleted-ref-events-recovery')
OUT.mkdir(parents=True, exist_ok=True)
REPO = os.environ['GITHUB_REPOSITORY']
TOKEN = os.environ['GITHUB_TOKEN']


def api(path: str):
    req = urllib.request.Request(
        'https://api.github.com' + path,
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {TOKEN}',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'rocketdict-deleted-ref-recovery',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    events = []
    for page in range(1, 11):
        batch = api(f'/repos/{REPO}/events?per_page=100&page={page}')
        if not batch:
            break
        events.extend(batch)
        if len(batch) < 100:
            break
    rows = []
    shas = set()
    for ev in events:
        created = ev.get('created_at') or ''
        typ = ev.get('type')
        payload = ev.get('payload') or {}
        if not created.startswith(('2026-08-26', '2026-08-27', '2026-08-28')):
            continue
        if typ not in {'PushEvent', 'CreateEvent', 'DeleteEvent'}:
            continue
        row = {
            'id': ev.get('id'),
            'type': typ,
            'created_at': created,
            'actor': (ev.get('actor') or {}).get('login'),
            'payload': payload,
        }
        rows.append(row)
        for key in ('before', 'head'):
            value = payload.get(key)
            if isinstance(value, str) and len(value) == 40 and set(value) != {'0'}:
                shas.add(value)
        for c in payload.get('commits') or []:
            value = c.get('sha')
            if isinstance(value, str) and len(value) == 40:
                shas.add(value)
    probes = []
    for sha in sorted(shas):
        try:
            commit = api(f'/repos/{REPO}/commits/{sha}')
            probes.append({
                'sha': sha,
                'resolves': True,
                'message': ((commit.get('commit') or {}).get('message') or '').splitlines()[0],
                'parents': [p.get('sha') for p in commit.get('parents') or []],
            })
        except Exception as exc:
            probes.append({'sha': sha, 'resolves': False, 'error': repr(exc)})
    report = {
        'schema': 'rocketdict-deleted-ref-events-recovery/1',
        'event_count_fetched': len(events),
        'matching_event_count': len(rows),
        'events': rows,
        'sha_probe_count': len(probes),
        'sha_probes': probes,
    }
    (OUT / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
