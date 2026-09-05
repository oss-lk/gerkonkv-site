from __future__ import annotations

"""Search surviving Actions artifacts for exact RocketDict public API/core bytes.

Recovery-only: findings are evidence candidates and can never promote Product
execution by themselves.  The scanner exists because the older Stage8 artifact
scanner searched numeric-integrity/F96 terms rather than the public API modules
that now block real Product execution.
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
OUT = ROOT / "rocketdict-stage8-api-artifact-recovery"
OUT.mkdir(parents=True, exist_ok=True)

MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_NESTED_DEPTH = 3
USER_AGENT = "rocketdict-stage8-api-artifact-recovery"

TERMS = (
    "rocketdict.api.contracts",
    "rocketdict.api.client",
    "rocketdict.api.cli",
    "RocketDictAPI",
    "API_VERSION",
    "PUBLIC_EXECUTION_CONTRACT",
    "ROCKETDICT_EXECUTION_CONTRACT",
    "execution_contract",
    "binding_metadata",
    "callable_operations",
)
TERM_RE = re.compile("|".join(re.escape(term) for term in TERMS), re.IGNORECASE)
PATH_RE = re.compile(
    r"(?:^|/)(?:src/)?rocketdict/api/(?:[^/]+\.py|[^/]+/[^/]+\.py)$|"
    r"(?:^|/)(?:src/)?rocketdict/(?:lab|translation)/[^/]+\.py$|"
    r"(?:^|/)pyproject\.toml$|(?:^|/)setup\.cfg$",
    re.IGNORECASE,
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


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
    with urllib.request.urlopen(request(path), timeout=60) as response:
        return json.load(response)


def artifact_bytes(path: str, timeout: int = 180) -> bytes:
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request(path), timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in {301, 302, 303, 307, 308}:
            raise
        location = exc.headers.get("Location")
        if not location:
            raise RuntimeError(f"artifact redirect {exc.code} has no Location") from exc
    with urllib.request.urlopen(
        urllib.request.Request(location, headers={"User-Agent": USER_AGENT}), timeout=timeout
    ) as response:
        return response.read()


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
    for match in TERM_RE.finditer(latin):
        lo = max(0, match.start() - 240)
        hi = min(len(raw), match.end() + 480)
        hits.append(
            {
                "artifact_id": artifact["id"],
                "artifact_name": artifact.get("name"),
                "artifact_size": artifact.get("size_in_bytes"),
                "artifact_created_at": artifact.get("created_at"),
                "logical_member": logical_name,
                "nested_depth": depth,
                "term": match.group(0),
                "offset": match.start(),
                "context": raw[lo:hi].decode("utf-8", "replace"),
            }
        )
        if len(hits) >= 200:
            break
    return hits


def scan_zip(raw: bytes, artifact: dict, prefix: str = "", depth: int = 0):
    content_hits: list[dict] = []
    path_hits: list[dict] = []
    errors: list[dict] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        return content_hits, path_hits, [{"where": prefix or "artifact", "error": repr(exc)}]
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
            content_hits.extend(text_hits(member, logical, artifact, depth))
            if depth < MAX_NESTED_DEPTH and member.startswith(b"PK\x03\x04"):
                h2, p2, e2 = scan_zip(member, artifact, logical, depth + 1)
                content_hits.extend(h2)
                path_hits.extend(p2)
                errors.extend(e2)
    return content_hits, path_hits, errors


def main() -> None:
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    artifacts = list(iter_artifacts(owner, repo))
    inventory = []
    hits = []
    path_hits = []
    errors = []
    skipped = []
    downloaded = 0

    for artifact in artifacts:
        row = {
            "id": artifact.get("id"),
            "name": artifact.get("name"),
            "size_in_bytes": artifact.get("size_in_bytes"),
            "created_at": artifact.get("created_at"),
            "expired": artifact.get("expired"),
            "digest": artifact.get("digest"),
        }
        inventory.append(row)
        if artifact.get("expired"):
            skipped.append({**row, "reason": "expired"})
            continue
        if int(artifact.get("size_in_bytes") or 0) > MAX_ARTIFACT_BYTES:
            skipped.append({**row, "reason": "over_size_limit"})
            continue
        try:
            raw = artifact_bytes(
                f"/repos/{owner}/{repo}/actions/artifacts/{artifact['id']}/zip"
            )
            downloaded += 1
            h, p, e = scan_zip(raw, artifact)
            hits.extend(h)
            path_hits.extend(p)
            errors.extend(
                {"artifact_id": artifact["id"], "artifact_name": artifact.get("name"), **err}
                for err in e
            )
        except Exception as exc:
            errors.append(
                {
                    "artifact_id": artifact.get("id"),
                    "artifact_name": artifact.get("name"),
                    "where": "download",
                    "error": repr(exc),
                }
            )

    report = {
        "schema": "rocketdict-stage8-api-artifact-recovery/1",
        "promotion_allowed": False,
        "search_terms": list(TERMS),
        "limits": {
            "max_artifact_bytes": MAX_ARTIFACT_BYTES,
            "max_member_bytes": MAX_MEMBER_BYTES,
            "max_nested_depth": MAX_NESTED_DEPTH,
        },
        "artifact_inventory_count": len(inventory),
        "downloaded_artifact_count": downloaded,
        "skipped": skipped,
        "path_hit_count": len(path_hits),
        "content_hit_count": len(hits),
        "error_count": len(errors),
        "path_hits": path_hits,
        "content_hits": hits,
        "errors": errors,
        "interpretation": (
            "Recovery-only scan. Hits may identify exact source/evidence candidates, but no hit "
            "may be promoted until bytes, runtime identity and Workbench live contracts verify. "
            "Absence is bounded by the recorded artifact inventory and size limits."
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
