from __future__ import annotations

"""Recovery-only scan for lost Stage8 challenge-selection/clipping evidence.

Unlike the general F96 source scanner, this searches historical Actions artifact
*contents* for the exact metadata vocabulary around the original 5051/111 ->
5000/109 transition. It cannot promote Stage8 and does not infer missing IDs.
"""

import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "rocketdict-stage8-selection-artifact-recovery"
OUT.mkdir(parents=True, exist_ok=True)
MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_DEPTH = 2
USER_AGENT = "rocketdict-stage8-selection-artifact-recovery"

TERMS = [
    "budget_clipped",
    "selection_changed",
    "challenge_selection",
    "challenge selection",
    "selection_sha256",
    "selected_occurrence_ids",
    "selected_occurrences",
    "occurrence_ids",
    "source_words\": 5051",
    "source_words\":5051",
    "actual_words\": 5051",
    "actual_words\":5051",
    "occurrences\": 111",
    "occurrences\":111",
    "units\": 111",
    "units\":111",
    "source_words\": 5000",
    "occurrences\": 109",
]
TERM_RE = re.compile("|".join(re.escape(x) for x in TERMS), re.IGNORECASE)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def gh_request(path: str) -> urllib.request.Request:
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
    with urllib.request.urlopen(gh_request(path), timeout=60) as r:
        return json.load(r)


def artifact_bytes(path: str) -> bytes:
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(gh_request(path), timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in {301, 302, 303, 307, 308}:
            raise
        location = exc.headers.get("Location")
        if not location:
            raise RuntimeError("artifact redirect missing Location") from exc
    req = urllib.request.Request(location, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def iter_artifacts(owner: str, repo: str):
    page = 1
    while True:
        batch = api_json(f"/repos/{owner}/{repo}/actions/artifacts?per_page=100&page={page}").get("artifacts", [])
        if not batch:
            return
        yield from batch
        if len(batch) < 100:
            return
        page += 1


def scan_text(raw: bytes, artifact: dict, logical: str, depth: int) -> list[dict]:
    text = raw.decode("utf-8", "replace")
    hits = []
    for m in TERM_RE.finditer(text):
        lo = max(0, m.start() - 700)
        hi = min(len(text), m.end() + 1800)
        hits.append({
            "artifact_id": artifact["id"],
            "artifact_name": artifact.get("name"),
            "artifact_created_at": artifact.get("created_at"),
            "logical_member": logical,
            "nested_depth": depth,
            "term": m.group(0),
            "offset": m.start(),
            "context": text[lo:hi],
        })
        if len(hits) >= 250:
            break
    return hits


def scan_zip(raw: bytes, artifact: dict, prefix: str = "", depth: int = 0) -> tuple[list[dict], list[dict]]:
    hits, errors = [], []
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        return hits, [{"logical_member": prefix or "artifact", "error": repr(exc)}]
    with zf:
        for info in zf.infolist():
            if info.is_dir() or info.file_size > MAX_MEMBER_BYTES:
                continue
            logical = f"{prefix}!{info.filename}" if prefix else info.filename
            try:
                member = zf.read(info)
            except Exception as exc:
                errors.append({"logical_member": logical, "error": repr(exc)})
                continue
            hits.extend(scan_text(member, artifact, logical, depth))
            if depth < MAX_DEPTH and member.startswith(b"PK\x03\x04"):
                h2, e2 = scan_zip(member, artifact, logical, depth + 1)
                hits.extend(h2); errors.extend(e2)
    return hits, errors


def main() -> None:
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    inventory, skipped, hits, errors = [], [], [], []
    attempted = downloaded = 0
    for art in iter_artifacts(owner, repo):
        row = {k: art.get(k) for k in ("id", "name", "size_in_bytes", "created_at", "expired", "digest")}
        inventory.append(row)
        if art.get("expired"):
            skipped.append({**row, "reason": "expired"}); continue
        if int(art.get("size_in_bytes") or 0) > MAX_ARTIFACT_BYTES:
            skipped.append({**row, "reason": "over_size_limit"}); continue
        attempted += 1
        try:
            raw = artifact_bytes(f"/repos/{owner}/{repo}/actions/artifacts/{art['id']}/zip")
            downloaded += 1
            h, e = scan_zip(raw, art)
            hits.extend(h)
            errors.extend({"artifact_id": art["id"], "artifact_name": art.get("name"), **x} for x in e)
        except Exception as exc:
            errors.append({"artifact_id": art["id"], "artifact_name": art.get("name"), "logical_member": "download", "error": repr(exc)})

    # Deduplicate identical hit contexts emitted because multiple query terms occur nearby.
    unique = []
    seen = set()
    for h in hits:
        key = (h["artifact_id"], h["logical_member"], h["context"])
        if key not in seen:
            seen.add(key); unique.append(h)

    report = {
        "schema": "rocketdict-stage8-selection-artifact-recovery/1",
        "promotion_allowed": False,
        "artifact_inventory_count": len(inventory),
        "attempted_artifact_count": attempted,
        "downloaded_artifact_count": downloaded,
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "raw_hit_count": len(hits),
        "unique_hit_count": len(unique),
        "terms": TERMS,
        "hits": unique,
        "errors": errors,
        "interpretation": "Exact artifact-content recovery only. No missing occurrence IDs or selection hashes are inferred from aggregate counts.",
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
