from __future__ import annotations

"""Fail-closed recovery scan of historical GitHub Actions artifact contents.

This closes a gap in recover_f96_history.py: that scanner covered Git history,
run metadata and run logs, but did not inspect the bytes stored inside Actions
artifacts. This program is recovery-only and cannot promote Stage 8.
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
OUT = ROOT / "rocketdict-stage8-artifact-content-recovery"
OUT.mkdir(parents=True, exist_ok=True)

MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_NESTED_DEPTH = 2
TERMS = [
    "contains_numeric_literal",
    "compare_numeric_integrity",
    "rocketdict.translation.integrity",
    "translation/integrity.py",
    "integrity.py",
    "research/integrity_doe.py",
    "integrity_doe.py",
    "rocketdict-numeric-integrity/3.2",
    "numeric-integrity/3.2",
    "stage8_rescore_integrity_doe",
    "table-cells-v1",
    "F96",
    "15697",
    "16200",
    "17795",
]
TERM_RE = re.compile("|".join(re.escape(x) for x in TERMS), re.IGNORECASE)
PATH_RE = re.compile(
    r"(?:integrity(?:_doe)?\.py|stage12_pilot\.py|test_stage8_integrity|test.*integrity)",
    re.IGNORECASE,
)
USER_AGENT = "rocketdict-stage8-artifact-content-recovery"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def request(path: str, *, accept: str = "application/vnd.github+json") -> urllib.request.Request:
    token = os.environ["GITHUB_TOKEN"]
    return urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )


def api_json(path: str):
    with urllib.request.urlopen(request(path), timeout=60) as r:
        return json.load(r)


def artifact_bytes(path: str, timeout: int = 180) -> bytes:
    """Download an Actions artifact without leaking GitHub auth to signed blob host.

    GitHub's artifact endpoint redirects to a temporary Azure/object-store URL.
    Sending the GitHub Authorization header to that signed URL causes the blob
    service to reject the request. Stop automatic redirects, capture Location,
    then fetch the signed URL with no Authorization header.
    """
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request(path), timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in {301, 302, 303, 307, 308}:
            raise
        location = exc.headers.get("Location")
        if not location:
            raise RuntimeError(f"artifact redirect {exc.code} has no Location") from exc
    signed = urllib.request.Request(location, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(signed, timeout=timeout) as r:
        return r.read()


def iter_artifacts(owner: str, repo: str):
    page = 1
    while True:
        data = api_json(f"/repos/{owner}/{repo}/actions/artifacts?per_page=100&page={page}")
        batch = data.get("artifacts", [])
        if not batch:
            return
        yield from batch
        if len(batch) < 100:
            return
        page += 1


def text_hits(raw: bytes, logical_name: str, artifact: dict, depth: int) -> list[dict]:
    latin = raw.decode("latin-1", "ignore")
    hits = []
    for m in TERM_RE.finditer(latin):
        lo = max(0, m.start() - 240)
        hi = min(len(latin), m.end() + 480)
        context = raw[lo:hi].decode("utf-8", "replace")
        hits.append(
            {
                "artifact_id": artifact["id"],
                "artifact_name": artifact.get("name"),
                "artifact_size": artifact.get("size_in_bytes"),
                "artifact_created_at": artifact.get("created_at"),
                "logical_member": logical_name,
                "nested_depth": depth,
                "term": m.group(0),
                "offset": m.start(),
                "context": context,
            }
        )
        if len(hits) >= 100:
            break
    return hits


def scan_zip(
    raw: bytes, artifact: dict, prefix: str = "", depth: int = 0
) -> tuple[list[dict], list[dict], list[dict]]:
    hits: list[dict] = []
    path_hits: list[dict] = []
    errors: list[dict] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        return hits, path_hits, [{"where": prefix or "artifact", "error": repr(exc)}]
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            logical = f"{prefix}!{info.filename}" if prefix else info.filename
            if PATH_RE.search(info.filename):
                path_hits.append(
                    {
                        "artifact_id": artifact["id"],
                        "artifact_name": artifact.get("name"),
                        "artifact_created_at": artifact.get("created_at"),
                        "logical_member": logical,
                        "nested_depth": depth,
                        "member_size": info.file_size,
                    }
                )
            if info.file_size > MAX_MEMBER_BYTES:
                continue
            try:
                member = zf.read(info)
            except Exception as exc:
                errors.append({"where": logical, "error": repr(exc)})
                continue
            hits.extend(text_hits(member, logical, artifact, depth))
            if depth < MAX_NESTED_DEPTH and member.startswith(b"PK\x03\x04"):
                h2, p2, e2 = scan_zip(member, artifact, logical, depth + 1)
                hits.extend(h2)
                path_hits.extend(p2)
                errors.extend(e2)
    return hits, path_hits, errors


def main() -> None:
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    artifacts = list(iter_artifacts(owner, repo))
    inventory = []
    hits = []
    path_hits = []
    errors = []
    skipped = []
    attempted = 0
    downloaded = 0
    for art in artifacts:
        row = {
            "id": art.get("id"),
            "name": art.get("name"),
            "size_in_bytes": art.get("size_in_bytes"),
            "created_at": art.get("created_at"),
            "expired": art.get("expired"),
            "digest": art.get("digest"),
        }
        inventory.append(row)
        if art.get("expired"):
            skipped.append({**row, "reason": "expired"})
            continue
        size = int(art.get("size_in_bytes") or 0)
        if size > MAX_ARTIFACT_BYTES:
            skipped.append({**row, "reason": "over_size_limit"})
            continue
        aid = art["id"]
        attempted += 1
        try:
            raw = artifact_bytes(f"/repos/{owner}/{repo}/actions/artifacts/{aid}/zip")
            downloaded += 1
            h, p, e = scan_zip(raw, art)
            hits.extend(h)
            path_hits.extend(p)
            for err in e:
                errors.append({"artifact_id": aid, "artifact_name": art.get("name"), **err})
        except Exception as exc:
            errors.append(
                {
                    "artifact_id": aid,
                    "artifact_name": art.get("name"),
                    "where": "download",
                    "error": repr(exc),
                }
            )

    report = {
        "schema": "rocketdict-stage8-artifact-content-recovery/2",
        "promotion_allowed": False,
        "terms": TERMS,
        "limits": {
            "max_artifact_bytes": MAX_ARTIFACT_BYTES,
            "max_member_bytes": MAX_MEMBER_BYTES,
            "max_nested_depth": MAX_NESTED_DEPTH,
        },
        "artifact_inventory_count": len(inventory),
        "attempted_artifact_count": attempted,
        "downloaded_artifact_count": downloaded,
        "skipped": skipped,
        "path_hit_count": len(path_hits),
        "content_hit_count": len(hits),
        "error_count": len(errors),
        "path_hits": path_hits,
        "content_hits": hits,
        "errors": errors,
        "interpretation": (
            "Artifact-content recovery only. A hit can recover evidence/source bytes; "
            "absence is not proof that the original local ChatGPT snapshot never existed."
        ),
    }
    (OUT / "artifact-inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
