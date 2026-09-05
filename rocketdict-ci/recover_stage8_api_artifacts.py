from __future__ import annotations

"""Search surviving Actions artifacts for exact RocketDict public API/core bytes.

Recovery-only: findings are evidence candidates and can never promote Product
execution by themselves. The older Stage8 artifact scanner searched
numeric-integrity/F96 terms, while this scanner targets the public API modules
that now block real Product execution. Nested ZIP and TAR-family archives are
inspected in memory so source bundles are not missed merely because they are
wrapped inside an Actions ZIP.
"""

import io
import json
import os
from pathlib import Path
import re
import tarfile
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
ARCHIVE_FORMATS = ("zip", "tar")

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
TAR_SUFFIXES = (
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.xz",
    ".txz",
    ".tar.bz2",
    ".tbz",
    ".tbz2",
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


def _archive_kind(name: str, raw: bytes) -> str | None:
    lowered = name.casefold()
    if raw.startswith(b"PK\x03\x04") or lowered.endswith(".zip"):
        return "zip"
    if lowered.endswith(TAR_SUFFIXES):
        return "tar"
    if raw.startswith((b"\x1f\x8b", b"\xfd7zXZ\x00", b"BZh")):
        return "tar"
    # Plain tar has no mandatory magic at byte zero; POSIX ustar normally has
    # it at offset 257. The suffix check above catches non-ustar legacy tars.
    if len(raw) >= 262 and raw[257:262] == b"ustar":
        return "tar"
    return None


def _hit_row(
    artifact: dict,
    logical_name: str,
    depth: int,
    archive_format: str,
    *,
    member_size: int | None = None,
) -> dict:
    row = {
        "artifact_id": artifact["id"],
        "artifact_name": artifact.get("name"),
        "artifact_created_at": artifact.get("created_at"),
        "logical_member": logical_name,
        "nested_depth": depth,
        "archive_format": archive_format,
    }
    if member_size is not None:
        row["member_size"] = member_size
    return row


def text_hits(
    raw: bytes,
    logical_name: str,
    artifact: dict,
    depth: int,
    archive_format: str,
) -> list[dict]:
    latin = raw.decode("latin-1", "ignore")
    hits = []
    for match in TERM_RE.finditer(latin):
        lo = max(0, match.start() - 240)
        hi = min(len(raw), match.end() + 480)
        row = _hit_row(artifact, logical_name, depth, archive_format)
        row.update(
            {
                "artifact_size": artifact.get("size_in_bytes"),
                "term": match.group(0),
                "offset": match.start(),
                "context": raw[lo:hi].decode("utf-8", "replace"),
            }
        )
        hits.append(row)
        if len(hits) >= 200:
            break
    return hits


def _scan_member(
    member: bytes,
    member_name: str,
    logical: str,
    artifact: dict,
    depth: int,
    parent_format: str,
):
    content_hits = text_hits(member, logical, artifact, depth, parent_format)
    path_hits: list[dict] = []
    errors: list[dict] = []
    if PATH_RE.search(member_name):
        path_hits.append(
            _hit_row(
                artifact,
                logical,
                depth,
                parent_format,
                member_size=len(member),
            )
        )
    if depth < MAX_NESTED_DEPTH:
        kind = _archive_kind(member_name, member)
        if kind is not None:
            h2, p2, e2 = scan_archive(
                member,
                artifact,
                prefix=logical,
                depth=depth + 1,
                hint_name=member_name,
                forced_kind=kind,
            )
            content_hits.extend(h2)
            path_hits.extend(p2)
            errors.extend(e2)
    return content_hits, path_hits, errors


def scan_zip(raw: bytes, artifact: dict, prefix: str = "", depth: int = 0):
    content_hits: list[dict] = []
    path_hits: list[dict] = []
    errors: list[dict] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        return content_hits, path_hits, [{"where": prefix or "artifact", "archive_format": "zip", "error": repr(exc)}]
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            logical = f"{prefix}!{info.filename}" if prefix else info.filename
            if info.file_size > MAX_MEMBER_BYTES:
                if PATH_RE.search(info.filename):
                    row = _hit_row(artifact, logical, depth, "zip", member_size=info.file_size)
                    row["content_skipped"] = "member_over_size_limit"
                    path_hits.append(row)
                continue
            try:
                member = zf.read(info)
            except Exception as exc:
                errors.append({"where": logical, "archive_format": "zip", "error": repr(exc)})
                continue
            h2, p2, e2 = _scan_member(member, info.filename, logical, artifact, depth, "zip")
            content_hits.extend(h2)
            path_hits.extend(p2)
            errors.extend(e2)
    return content_hits, path_hits, errors


def scan_tar(raw: bytes, artifact: dict, prefix: str = "", depth: int = 0):
    content_hits: list[dict] = []
    path_hits: list[dict] = []
    errors: list[dict] = []
    try:
        tf = tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")
    except Exception as exc:
        return content_hits, path_hits, [{"where": prefix or "artifact", "archive_format": "tar", "error": repr(exc)}]
    with tf:
        for info in tf:
            if not info.isfile():
                continue
            logical = f"{prefix}!{info.name}" if prefix else info.name
            if info.size > MAX_MEMBER_BYTES:
                if PATH_RE.search(info.name):
                    row = _hit_row(artifact, logical, depth, "tar", member_size=info.size)
                    row["content_skipped"] = "member_over_size_limit"
                    path_hits.append(row)
                continue
            try:
                extracted = tf.extractfile(info)
                if extracted is None:
                    raise RuntimeError("tar member has no extractable stream")
                member = extracted.read(MAX_MEMBER_BYTES + 1)
                if len(member) > MAX_MEMBER_BYTES:
                    raise RuntimeError("tar member exceeded declared recovery member limit while reading")
            except Exception as exc:
                errors.append({"where": logical, "archive_format": "tar", "error": repr(exc)})
                continue
            h2, p2, e2 = _scan_member(member, info.name, logical, artifact, depth, "tar")
            content_hits.extend(h2)
            path_hits.extend(p2)
            errors.extend(e2)
    return content_hits, path_hits, errors


def scan_archive(
    raw: bytes,
    artifact: dict,
    *,
    prefix: str = "",
    depth: int = 0,
    hint_name: str = "artifact.zip",
    forced_kind: str | None = None,
):
    kind = forced_kind or _archive_kind(hint_name, raw)
    if kind == "zip":
        return scan_zip(raw, artifact, prefix, depth)
    if kind == "tar":
        return scan_tar(raw, artifact, prefix, depth)
    return [], [], [{"where": prefix or hint_name, "archive_format": None, "error": "unrecognized_archive_format"}]


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
            h, p, e = scan_archive(
                raw,
                artifact,
                hint_name=f"{artifact.get('name') or artifact['id']}.zip",
                forced_kind="zip",
            )
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
        "schema": "rocketdict-stage8-api-artifact-recovery/2",
        "promotion_allowed": False,
        "search_terms": list(TERMS),
        "archive_formats": list(ARCHIVE_FORMATS),
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
            "Recovery-only ZIP+TAR scan. Hits may identify exact source/evidence candidates, "
            "but no hit may be promoted until bytes, runtime identity and Workbench live "
            "contracts verify. Absence is bounded by the recorded artifact inventory, expiry "
            "state and size limits."
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
