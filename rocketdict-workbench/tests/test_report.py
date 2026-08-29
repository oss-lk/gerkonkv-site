from pathlib import Path
import json
from rocketdict_workbench.report import build_report_payload, write_report


def test_report_keeps_pareto_and_no_hidden_score(tmp_path: Path) -> None:
    analytics = {
        "plan_id": 7,
        "definition_hash": "d"*64,
        "plan_hash": "p"*64,
        "objectives": [{"name":"quality","direction":"maximize"},{"name":"runtime_ms","direction":"minimize"}],
        "trials": [
            {"trial_id":1,"component_id":10,"status":"completed","parameters":{"beam":4},"objectives":{"quality":0.91,"runtime_ms":120},"pareto_rank":1},
            {"trial_id":2,"component_id":11,"status":"completed","parameters":{"beam":8},"objectives":{"quality":0.93,"runtime_ms":180},"pareto_rank":1},
            {"trial_id":3,"component_id":12,"status":"failed","parameters":{},"objectives":{},"pareto_rank":None},
        ],
        "comparisons": [], "parameter_effects": [], "pairwise_objective_plots": [],
    }
    payload = build_report_payload(analytics=analytics, plan={"id":7})
    assert payload["summary"]["trial_count"] == 3
    assert payload["summary"]["failed_count"] == 1
    assert payload["summary"]["pareto_rank1_count"] == 2
    assert payload["invariants"]["no_hidden_overall_score"] is True
    result = write_report(tmp_path, analytics=analytics, plan={"id":7})
    rendered = Path(result["html"]).read_text(encoding="utf-8")
    assert "Pareto" in rendered
    assert "quality" in rendered
    assert "runtime_ms" in rendered
    assert "скрытого интегрального score" in rendered
    json.loads(Path(result["json"]).read_text(encoding="utf-8"))
