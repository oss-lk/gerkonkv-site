from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "rocketdict-f96-history-recovery"
OUT.mkdir(parents=True, exist_ok=True)

TERMS = [
    "F96",
    "rocketdict-numeric-integrity/3.2",
    "15697",
    "16200",
    "17795",
    "ddf5f409a5690fa4d2141c8a3bd30ef73f82cc9e75c27b66716791afbc6f97b7",
    "394ffcfe399deb1f83ad445cc3ac2e727c8f684a29fd06c757eee16612cfe4ab",
    "106fc9d7bee42a53b34412267923d17b3331019d2eef16300b539de8929927a1",
    "a879ccbadae6babc9c706ced0a7bbda08ad5364e869640fae30b458654bc8cc1",
    "5220ec9960680539b185997785455b35a0c1e0f4e9461366a0e73348b9ead5b8",
    "table-cells-v1",
    "stage8_rescore_integrity_doe",
    "integrity_doe",
]
TERM_RE = re.compile("|".join(re.escape(t) for t in TERMS), re.IGNORECASE)


def sh(*args: str, check: bool = False) -> str:
    p = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)
    return p.stdout


def api_json(path: str):
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "rocketdict-f96-recovery",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def api_bytes(path: str) -> bytes:
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "rocketdict-f96-recovery",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def git_history() -> dict:
    # Fetch every currently advertised ref that a normal clone is allowed to see.
    fetch = sh("git", "fetch", "--force", "--tags", "origin", "+refs/heads/*:refs/remotes/origin/*", "+refs/pull/*/head:refs/remotes/origin/pr/*")
    refs = sh("git", "for-each-ref", "--format=%(refname) %(objectname)")
    log = sh("git", "log", "--all", "--date=iso-strict", "--format=%H\t%ad\t%s")
    fsck = sh("git", "fsck", "--full", "--unreachable", "--no-reflogs")
    searches = {}
    for term in TERMS:
        searches[term] = sh("git", "log", "--all", "-i", "-S", term, "--date=iso-strict", "--format=%H\t%ad\t%s", "--name-status")
    # Also find paths/names in every reachable tree containing likely Stage-8 vocabulary.
    commits = [line.split("\t", 1)[0] for line in log.splitlines() if line]
    path_hits = []
    content_hits = []
    seen_blob = set()
    path_re = re.compile(r"(stage8|f96|integrity|vault|research|snapshot|0\.30\.3[9]|0\.30\.40)", re.I)
    for idx, commit in enumerate(commits):
        tree = sh("git", "ls-tree", "-r", "--name-only", commit)
        for path in tree.splitlines():
            if path_re.search(path):
                path_hits.append({"commit": commit, "path": path})
        # Grep commit tree itself. --full-name plus -I avoids binary noise.
        gp = subprocess.run(
            ["git", "grep", "-I", "-n", "-E", "F96|rocketdict-numeric-integrity/3\\.2|15697|16200|17795|table-cells-v1|stage8_rescore_integrity_doe|integrity_doe", commit, "--"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        for line in gp.stdout.splitlines():
            content_hits.append({"commit": commit, "hit": line})
    (OUT / "git-fetch.txt").write_text(fetch, encoding="utf-8")
    (OUT / "git-refs.txt").write_text(refs, encoding="utf-8")
    (OUT / "git-log.txt").write_text(log, encoding="utf-8")
    (OUT / "git-fsck.txt").write_text(fsck, encoding="utf-8")
    (OUT / "git-S-searches.json").write_text(json.dumps(searches, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "git-path-hits.json").write_text(json.dumps(path_hits, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "git-content-hits.json").write_text(json.dumps(content_hits, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "commit_count": len(commits),
        "ref_count": len([x for x in refs.splitlines() if x]),
        "unreachable_lines": len([x for x in fsck.splitlines() if x]),
        "path_hit_count": len(path_hits),
        "content_hit_count": len(content_hits),
        "content_hit_sample": content_hits[:40],
    }


def actions_history() -> dict:
    repo = os.environ["GITHUB_REPOSITORY"]
    owner, name = repo.split("/", 1)
    runs = []
    page = 1
    while True:
        data = api_json(f"/repos/{owner}/{name}/actions/runs?per_page=100&page={page}")
        batch = data.get("workflow_runs", [])
        if not batch:
            break
        runs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    run_rows = []
    artifact_rows = []
    log_hits = []
    for run in runs:
        rid = run["id"]
        row = {
            "id": rid,
            "name": run.get("name"),
            "display_title": run.get("display_title"),
            "head_sha": run.get("head_sha"),
            "head_branch": run.get("head_branch"),
            "event": run.get("event"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "path": run.get("path"),
        }
        run_rows.append(row)
        try:
            arts = api_json(f"/repos/{owner}/{name}/actions/runs/{rid}/artifacts?per_page=100").get("artifacts", [])
        except Exception as exc:
            arts = []
            artifact_rows.append({"run_id": rid, "artifact_error": repr(exc)})
        for a in arts:
            artifact_rows.append({
                "run_id": rid,
                "run_name": run.get("name"),
                "created_at": run.get("created_at"),
                "head_sha": run.get("head_sha"),
                "artifact_id": a.get("id"),
                "name": a.get("name"),
                "size_in_bytes": a.get("size_in_bytes"),
                "expired": a.get("expired"),
                "digest": a.get("digest"),
            })
        # Logs are small relative to model artifacts; inspect runs around Stage-8 creation and any RocketDict run.
        created = run.get("created_at") or ""
        interesting = ("RocketDict" in (run.get("name") or "")) or created.startswith("2026-08-27")
        if interesting and run.get("status") == "completed":
            try:
                raw = api_bytes(f"/repos/{owner}/{name}/actions/runs/{rid}/logs")
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    for member in zf.namelist():
                        if member.endswith("/"):
                            continue
                        try:
                            text = zf.read(member).decode("utf-8", "replace")
                        except Exception:
                            continue
                        for lineno, line in enumerate(text.splitlines(), 1):
                            if TERM_RE.search(line):
                                log_hits.append({"run_id": rid, "member": member, "line": lineno, "text": line[:4000]})
            except Exception as exc:
                log_hits.append({"run_id": rid, "log_error": repr(exc)})
    (OUT / "actions-runs.json").write_text(json.dumps(run_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "actions-artifacts.json").write_text(json.dumps(artifact_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "actions-log-hits.json").write_text(json.dumps(log_hits, indent=2, ensure_ascii=False), encoding="utf-8")
    likely_artifacts = [a for a in artifact_rows if TERM_RE.search(json.dumps(a, ensure_ascii=False)) or re.search(r"rocketdict|stage8|research|integrity|gate|handoff|source", str(a.get("name", "")), re.I)]
    return {
        "run_count": len(run_rows),
        "artifact_count": len([a for a in artifact_rows if "artifact_id" in a]),
        "likely_artifacts": likely_artifacts,
        "log_hit_count": len(log_hits),
        "log_hits": log_hits,
    }


def main() -> None:
    git = git_history()
    actions = actions_history()
    report = {
        "schema": "rocketdict-f96-history-recovery/1",
        "terms": TERMS,
        "git": git,
        "actions": actions,
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
