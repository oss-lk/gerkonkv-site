from __future__ import annotations

"""Recover lost Stage 8 payload/source from historical GitHub Pages TAR snapshots.

Pages artifacts can outlive force-pushed/deleted Git commits. This recovery is
strictly forensic: it records hashes and extracts only the Stage 8 handoff paths
needed to prove an exact recovery. It does not promote reconstructed code.
"""

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "rocketdict-stage8-pages-snapshot-recovery"
RECOVERED = OUT / "recovered"
OUT.mkdir(parents=True, exist_ok=True)
RECOVERED.mkdir(parents=True, exist_ok=True)
USER_AGENT = "rocketdict-stage8-pages-snapshot-recovery"

INTERESTING_BASENAMES = {
    "integrity.py",
    "integrity_doe.py",
    "stage8_rescore_integrity_doe.py",
    "test_stage8_integrity_research.py",
    "stage12_pilot.py",
    "materialize_handoff.py",
}
PAYLOAD_RE = re.compile(r"(?:^|/)rocketdict/payload/(?:stage8-overlay/part-\d{3}\.b64|research-vault/part-\d{3}\.b85)$")
SOURCE_RE = re.compile(
    r"(?:^|/)(?:src/rocketdict/translation/integrity\.py|src/rocketdict/research/integrity_doe\.py|"
    r"scripts/stage8_rescore_integrity_doe\.py|tests/test_stage8_integrity_research\.py)$"
)


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
    with urllib.request.urlopen(gh_request(path), timeout=60) as response:
        return json.load(response)


def artifact_bytes(path: str) -> bytes:
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(gh_request(path), timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in {301, 302, 303, 307, 308}:
            raise
        location = exc.headers.get("Location")
        if not location:
            raise RuntimeError(f"artifact redirect {exc.code} without Location") from exc
    with urllib.request.urlopen(
        urllib.request.Request(location, headers={"User-Agent": USER_AGENT}), timeout=180
    ) as response:
        return response.read()


def artifacts(owner: str, repo: str) -> list[dict]:
    rows = []
    page = 1
    while True:
        payload = api_json(f"/repos/{owner}/{repo}/actions/artifacts?per_page=100&page={page}")
        batch = payload.get("artifacts", [])
        rows.extend(batch)
        if len(batch) < 100:
            return rows
        page += 1


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_rel(name: str) -> Path:
    pure = PurePosixPath(name)
    parts = [re.sub(r"[^A-Za-z0-9._-]+", "_", part) for part in pure.parts if part not in {"", ".", ".."}]
    return Path(*parts)


def main() -> None:
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    page_artifacts = [
        row for row in artifacts(owner, repo)
        if row.get("name") == "github-pages" and not row.get("expired")
    ]
    snapshots = []
    recovered_index = []
    errors = []

    for art in sorted(page_artifacts, key=lambda row: row.get("created_at") or ""):
        aid = int(art["id"])
        snap = {
            "artifact_id": aid,
            "created_at": art.get("created_at"),
            "digest": art.get("digest"),
            "artifact_size": art.get("size_in_bytes"),
            "tar_member_count": 0,
            "rocketdict_member_count": 0,
            "payload_members": [],
            "exact_source_members": [],
            "other_integrity_named_members": [],
        }
        try:
            outer = artifact_bytes(f"/repos/{owner}/{repo}/actions/artifacts/{aid}/zip")
            with zipfile.ZipFile(io.BytesIO(outer)) as zf:
                tar_names = [name for name in zf.namelist() if name.endswith(".tar")]
                if not tar_names:
                    raise RuntimeError(f"Pages artifact {aid} has no .tar member")
                tar_raw = zf.read(tar_names[0])
            with tarfile.open(fileobj=io.BytesIO(tar_raw), mode="r:*") as tf:
                members = [member for member in tf.getmembers() if member.isfile()]
                snap["tar_member_count"] = len(members)
                for member in members:
                    name = member.name.lstrip("./")
                    if "rocketdict" in name.casefold():
                        snap["rocketdict_member_count"] += 1
                    payload_match = bool(PAYLOAD_RE.search(name))
                    exact_source_match = bool(SOURCE_RE.search(name))
                    basename_match = PurePosixPath(name).name in INTERESTING_BASENAMES
                    if payload_match:
                        snap["payload_members"].append(name)
                    if exact_source_match:
                        snap["exact_source_members"].append(name)
                    elif basename_match:
                        snap["other_integrity_named_members"].append(name)
                    if not (payload_match or exact_source_match or basename_match):
                        continue
                    extracted = tf.extractfile(member)
                    if extracted is None:
                        continue
                    raw = extracted.read()
                    target = RECOVERED / str(aid) / safe_rel(name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                    recovered_index.append(
                        {
                            "artifact_id": aid,
                            "created_at": art.get("created_at"),
                            "member": name,
                            "bytes": len(raw),
                            "sha256": sha256(raw),
                            "saved_as": str(target.relative_to(OUT)),
                            "payload_match": payload_match,
                            "exact_source_match": exact_source_match,
                        }
                    )
        except Exception as exc:
            errors.append({"artifact_id": aid, "created_at": art.get("created_at"), "error": repr(exc)})
        snapshots.append(snap)

    unique_payload_names = sorted({item["member"] for item in recovered_index if item["payload_match"]})
    exact_source_hits = [item for item in recovered_index if item["exact_source_match"]]
    report = {
        "schema": "rocketdict-stage8-pages-snapshot-recovery/1",
        "promotion_allowed": False,
        "pages_artifact_count": len(page_artifacts),
        "snapshot_count": len(snapshots),
        "error_count": len(errors),
        "unique_payload_member_count": len(unique_payload_names),
        "unique_payload_members": unique_payload_names,
        "exact_source_hit_count": len(exact_source_hits),
        "exact_source_hits": exact_source_hits,
        "recovered_file_count": len(recovered_index),
        "snapshots": snapshots,
        "recovered_index": recovered_index,
        "errors": errors,
        "interpretation": (
            "A Pages snapshot can prove recovery only when recovered bytes satisfy the existing "
            "materialize_handoff.py inventory and SHA contracts. Presence alone is not promotion."
        ),
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
