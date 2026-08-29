from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable
import urllib.request

from .core import RocketDictCore

POLICY_KEY = "workbench-cefrj-exact-v1"
CEFRJ_URL = "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/cefrj-vocabulary-profile-1.5.csv"
CEFRJ_SHA256 = "b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498"
CEFRJ_BYTES = 233214
CEFRJ_ROWS = 7799
CEFRJ_HEADER = ["headword", "pos", "CEFR", "CoreInventory 1", "CoreInventory 2", "Threshold"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_cefrj_asset(path: Path | str) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = _sha256(path)
    if actual != CEFRJ_SHA256:
        raise RuntimeError(f"CEFR-J asset SHA mismatch: {actual} != {CEFRJ_SHA256}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != CEFRJ_HEADER:
            raise RuntimeError(f"Unexpected CEFR-J columns: {reader.fieldnames!r}")
        count = sum(1 for _ in reader)
    if count != CEFRJ_ROWS or path.stat().st_size != CEFRJ_BYTES:
        raise RuntimeError(
            f"CEFR-J asset shape mismatch: bytes={path.stat().st_size}, rows={count}; "
            f"expected bytes={CEFRJ_BYTES}, rows={CEFRJ_ROWS}"
        )
    return {
        "dataset": "CEFR-J Vocabulary Profile 1.5",
        "path": str(path),
        "sha256": actual,
        "bytes": path.stat().st_size,
        "rows": count,
        "source_url": CEFRJ_URL,
        "commercial_allowed": True,
        "attribution_required": True,
        "redistribution_assumed": False,
    }


def install_cefrj_asset(destination: Path | str, *, timeout: int = 60) -> dict[str, Any]:
    """Explicit setup-time download. Product processing itself remains offline."""
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        req = urllib.request.Request(CEFRJ_URL, headers={"User-Agent": "RocketDict-Workbench/CEFRJ-setup"})
        with urllib.request.urlopen(req, timeout=timeout) as response, tmp.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        verified = verify_cefrj_asset(tmp)
        tmp.replace(destination)
    finally:
        if tmp.exists():
            tmp.unlink()
    verified["path"] = str(destination)
    verified["installed_from_upstream"] = True
    return verified


def _helper_code() -> str:
    return r'''
import json,sys
from pathlib import Path
from rocketdict.cefr.alternatives import load_cefrj
from rocketdict.cefr.service import CefrAssessmentService
from rocketdict.database import bootstrap_database,create_session_factory

POLICY="workbench-cefrj-exact-v1"
db=Path(sys.argv[1]); asset=Path(sys.argv[2]); sense_ids=[int(x) for x in json.loads(sys.argv[3])]; actor=sys.argv[4]; approve=bool(int(sys.argv[5]))
e=bootstrap_database(db); sf=create_session_factory(e); svc=CefrAssessmentService(sf); snap=load_cefrj(asset); out=[]
for sense_id in sense_ids:
    settings={
        "algorithm_key":POLICY,
        "target_scope":"lexical_sense",
        "scope_policy":"conservative",
        "selection_strategy":"scope-policy",
        "minimum_confidence":.42,
        "inheritance_penalty":.14,
        "conflict_penalty":.16,
        "include_frequency_inference":False,
        "include_document_usage":False,
        "use_builtin_smoke_sources":False,
        "network_access":False,
        "source_snapshots":[snap],
    }
    result=svc.assess(sense_id,settings=settings,actor=actor)
    row={
        "sense_id":sense_id,"assessment_run_id":result.assessment_run_id,"review_revision_id":result.review_revision_id,
        "level":result.level,"scope":result.scope,"confidence":result.confidence,
        "candidate_count":result.candidate_count,"conflict_count":result.conflict_count,
        "blocking_conflict_count":result.blocking_conflict_count,"cache_hit":bool(result.cache_hit),
        "source":"CEFR-J Vocabulary Profile 1.5","source_sha256":snap["sha256"],
        "builtin_smoke_used":False,"frequency_inference_used":False,
    }
    if approve:
        approved=svc.approve(result.review_revision_id,actor=actor,reason="Workbench Product Mode CEFR-J 1.5 source evidence only; no builtin smoke or frequency fallback")
        row["approval_status"]=approved.status;row["cefr_assignment_id"]=approved.cefr_assignment_id;row["materialization_id"]=approved.materialization_id
    out.append(row)
print(json.dumps({"policy":POLICY,"source_sha256":snap["sha256"],"results":out},ensure_ascii=False));e.dispose()
'''


def assess_product_cefr(
    core: RocketDictCore,
    database: Path | str,
    lexical_sense_ids: Iterable[int],
    *,
    cefrj_asset: Path | str,
    approve: bool = True,
    actor: str = "rocketdict-workbench:cefrj-exact-v1",
) -> dict[str, Any]:
    asset = Path(cefrj_asset).expanduser().resolve()
    verify_cefrj_asset(asset)
    ids = [int(x) for x in lexical_sense_ids]
    result = core._run([
        "-c", _helper_code(), str(Path(database).expanduser().resolve()), str(asset),
        json.dumps(ids, separators=(",", ":")), actor, "1" if approve else "0",
    ], timeout=900)
    payload = dict(core._parse_json(result.stdout, context="Product CEFR-J assessment"))
    if payload.get("source_sha256") != CEFRJ_SHA256:
        raise RuntimeError(f"Product CEFR source identity changed: {payload.get('source_sha256')}")
    for row in payload.get("results") or []:
        if row.get("builtin_smoke_used") or row.get("frequency_inference_used"):
            raise RuntimeError(f"Non-source CEFR inference leaked into Product Mode: {row}")
    return payload
