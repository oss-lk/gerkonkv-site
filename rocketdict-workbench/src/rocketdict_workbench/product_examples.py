from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .core import RocketDictCore

SCOPE_CONTRACT = "stage23-sense-scope-v1"


def _helper_code() -> str:
    return r'''
import json,sys
from pathlib import Path
from rocketdict.database import bootstrap_database,create_session_factory
from rocketdict.examples.service import ExampleSelectionService

db=Path(sys.argv[1]); sense_ids=[int(x) for x in json.loads(sys.argv[2])]; supplied=json.loads(sys.argv[3]); actor=sys.argv[4]; approve=bool(int(sys.argv[5]))
e=bootstrap_database(db); sf=create_session_factory(e); svc=ExampleSelectionService(sf); out=[]
for sense_id in sense_ids:
    settings=dict(supplied)
    settings["workbench_example_scope"]={"lexical_sense_id":sense_id,"compatibility_contract":"stage23-sense-scope-v1"}
    settings.setdefault("corpus_snapshots",[])
    result=svc.select_examples(sense_id,settings=settings,actor=actor)
    row={"sense_id":sense_id,"selection_run_id":result.selection_run_id,"review_revision_id":result.review_revision_id,
         "candidate_count":result.candidate_count,"primary_missing":result.primary_missing,"secondary_missing":result.secondary_missing,
         "cache_hit":result.cache_hit}
    if approve:
        approved=svc.approve(result.review_revision_id,actor=actor,reason="Workbench Product Mode automatic approval of provenance-complete document example; missing roles remain explicitly covered")
        row["approval_status"]=approved.status; row["example_ids"]=list(approved.example_ids); row["materialization_ids"]=list(approved.materialization_ids)
    out.append(row)
print(json.dumps({"scope_contract":"stage23-sense-scope-v1","corpus_smoke_disabled":True,"results":out},ensure_ascii=False)); e.dispose()
'''


def select_product_examples(
    core: RocketDictCore,
    database: Path | str,
    sense_ids: Iterable[int],
    *,
    settings: dict[str, Any] | None = None,
    approve: bool = True,
    actor: str = "rocketdict-workbench:product-examples-v1",
) -> dict[str, Any]:
    ids = [int(x) for x in sense_ids]
    result = core._run([
        "-c", _helper_code(), str(Path(database).expanduser().resolve()), json.dumps(ids, separators=(",", ":")),
        json.dumps(dict(settings or {}), ensure_ascii=False, separators=(",", ":")), actor, "1" if approve else "0",
    ], timeout=600)
    return dict(core._parse_json(result.stdout, context="Product Stage23 examples"))
