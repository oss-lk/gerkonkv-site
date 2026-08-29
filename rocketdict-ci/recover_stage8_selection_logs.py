from __future__ import annotations

"""Recovery-only scan of historical GitHub Actions logs for Stage8 selection metadata."""

import io
import json
import os
from pathlib import Path
import re
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "rocketdict-stage8-selection-log-recovery"
OUT.mkdir(parents=True, exist_ok=True)
USER_AGENT = "rocketdict-stage8-selection-log-recovery"

# Search terms are deliberately tied to the historical 5051/111 -> 5000/109
# transition. Numeric `111` alone is not searched because it is too noisy.
TERM_RE = re.compile(
    r"budget_clipped|selection_changed|challenge[_ -]?selection|selection_sha256|"
    r"source_words.{0,16}5051|actual_words.{0,16}5051|"
    r"occurrences.{0,16}111|units.{0,16}111|"
    r"source_words.{0,16}5000|occurrences.{0,16}109",
    re.IGNORECASE,
)


def request(path: str) -> urllib.request.Request:
    return urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )


def api_json(path: str):
    with urllib.request.urlopen(request(path), timeout=60) as r:
        return json.load(r)


def api_bytes(path: str) -> bytes:
    with urllib.request.urlopen(request(path), timeout=120) as r:
        return r.read()


def iter_runs(owner: str, repo: str):
    page = 1
    while True:
        batch = api_json(f"/repos/{owner}/{repo}/actions/runs?per_page=100&page={page}").get("workflow_runs", [])
        if not batch:
            return
        yield from batch
        if len(batch) < 100:
            return
        page += 1


def main() -> None:
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    considered = []
    hits = []
    errors = []
    for run in iter_runs(owner, repo):
        created = run.get("created_at") or ""
        name = run.get("name") or ""
        # Original Stage8 handoff/research activity happened on Aug 26-28. Keep
        # the window broad enough to include the real OPUS gate and all early
        # Stage8 research, but exclude today's recovery self-references.
        if not ("2026-08-26" <= created[:10] <= "2026-08-28"):
            continue
        if "RocketDict" not in name:
            continue
        row = {
            "id": run["id"],
            "name": name,
            "created_at": created,
            "head_sha": run.get("head_sha"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
        }
        considered.append(row)
        if run.get("status") != "completed":
            continue
        try:
            raw = api_bytes(f"/repos/{owner}/{repo}/actions/runs/{run['id']}/logs")
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    text = zf.read(info).decode("utf-8", "replace")
                    lines = text.splitlines()
                    for lineno, line in enumerate(lines, 1):
                        if not TERM_RE.search(line):
                            continue
                        lo = max(0, lineno - 4)
                        hi = min(len(lines), lineno + 3)
                        hits.append({
                            "run_id": run["id"],
                            "run_name": name,
                            "run_created_at": created,
                            "head_sha": run.get("head_sha"),
                            "member": info.filename,
                            "line": lineno,
                            "context": "\n".join(lines[lo:hi]),
                        })
        except Exception as exc:
            errors.append({"run_id": run["id"], "name": name, "error": repr(exc)})

    report = {
        "schema": "rocketdict-stage8-selection-log-recovery/1",
        "promotion_allowed": False,
        "considered_run_count": len(considered),
        "hit_count": len(hits),
        "error_count": len(errors),
        "runs": considered,
        "hits": hits,
        "errors": errors,
        "interpretation": "Historical log recovery only; no selection identity is inferred from aggregate counts.",
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
