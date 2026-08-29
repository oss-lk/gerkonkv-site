from __future__ import annotations

import html
import json
from pathlib import Path
from statistics import fmean
from typing import Any


REPORT_SCHEMA = "rocketdict-workbench-research-report/1"


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if abs(value) >= 1000000:
            return f"{value:,.0f}".replace(",", " ")
        if abs(value) >= 100:
            return f"{value:.1f}"
        return f"{value:.4g}"
    return str(value)


def _metric_names(analytics: dict[str, Any]) -> list[str]:
    declared = [str(x.get("name")) for x in analytics.get("objectives", []) if x.get("name")]
    observed = sorted({k for t in analytics.get("trials", []) for k in (t.get("objectives") or {})})
    return list(dict.fromkeys([*declared, *observed]))


def build_report_payload(*, analytics: dict[str, Any], plan: dict[str, Any], lab_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    trials = list(analytics.get("trials") or [])
    metric_names = _metric_names(analytics)
    completed = [t for t in trials if t.get("status") == "completed"]
    rank1 = [t for t in completed if t.get("pareto_rank") == 1]
    metric_means = {}
    for name in metric_names:
        values = [float(t["objectives"][name]) for t in completed if name in (t.get("objectives") or {})]
        metric_means[name] = fmean(values) if values else None
    return {
        "schema": REPORT_SCHEMA,
        "plan_id": analytics.get("plan_id") or plan.get("id"),
        "definition_hash": analytics.get("definition_hash") or plan.get("definition_hash"),
        "plan_hash": analytics.get("plan_hash") or plan.get("plan_hash"),
        "summary": {
            "trial_count": len(trials),
            "completed_count": len(completed),
            "failed_count": sum(1 for t in trials if t.get("status") == "failed"),
            "pareto_rank1_count": len(rank1),
            "metric_means": metric_means,
            "regression_summary": analytics.get("regression_summary") or {},
        },
        "objectives": analytics.get("objectives") or [],
        "trials": trials,
        "comparisons": analytics.get("comparisons") or [],
        "parameter_effects": analytics.get("parameter_effects") or [],
        "pairwise_objective_plots": analytics.get("pairwise_objective_plots") or [],
        "attempt_summary": analytics.get("attempt_summary") or {},
        "lab_summary": None if lab_manifest is None else lab_manifest.get("summary"),
        "invariants": {
            "no_hidden_overall_score": True,
            "pareto_rank_is_multi_objective_not_weighted_score": True,
            "failed_trials_retained": True,
            "human_readable_and_machine_readable_outputs_share_payload": True,
        },
    }


def render_html(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RocketDict — отчёт эксперимента { _esc(payload.get('plan_id')) }</title>
<style>
:root{{--bg:#f5f6f8;--paper:#fff;--ink:#18202a;--muted:#697586;--line:#dfe4ea;--accent:#315efb;--good:#16845b;--bad:#c73838;--warn:#aa6b00}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}}main{{max-width:1450px;margin:auto;padding:24px}}h1{{font-size:26px;margin:0 0 4px}}h2{{margin:0 0 14px;font-size:19px}}.sub{{color:var(--muted)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0}}.card,.panel{{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px}}.card b{{font-size:24px;display:block}}.panel{{margin:14px 0}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#fafbfc}}code{{font:12px ui-monospace,SFMono-Regular,Consolas,monospace}}.ok{{color:var(--good)}}.bad{{color:var(--bad)}}.warn{{color:var(--warn)}}.chart{{min-height:270px}}svg{{width:100%;height:270px;overflow:visible}}.legend{{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:12px}}.pill{{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:2px 7px;margin:1px 3px 1px 0}}details>summary{{cursor:pointer;font-weight:650}}@media(max-width:700px){{main{{padding:12px}}table{{font-size:11px}}}}
</style></head><body><main>
<h1>RocketDict — отчёт исследовательского запуска</h1><div class="sub">Plan { _esc(payload.get('plan_id')) } · без скрытого интегрального score · Pareto по явно объявленным метрикам</div>
<div id="app"></div>
<script type="application/json" id="payload">{encoded}</script>
<script>
const P=JSON.parse(document.getElementById('payload').textContent), app=document.getElementById('app');
const esc=x=>String(x??'').replace(/[&<>\"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const fmt=x=>x==null?'—':(typeof x==='number'?(Math.abs(x)>=1e6?Math.round(x).toLocaleString('ru-RU'):Math.abs(x)>=100?x.toFixed(1):Number(x.toPrecision(4))):x);
function barChart(name){{const rows=P.trials.filter(t=>t.status==='completed'&&t.objectives&&t.objectives[name]!=null);if(!rows.length)return '<div class=sub>Нет данных</div>';const vals=rows.map(r=>Number(r.objectives[name])),lo=Math.min(...vals),hi=Math.max(...vals),span=hi-lo||1,w=1000,h=250,p=42,bw=Math.max(5,(w-2*p)/rows.length*0.72);return `<svg viewBox="0 0 ${{w}} ${{h}}">${{rows.map((r,i)=>{{const v=Number(r.objectives[name]),x=p+i*(w-2*p)/rows.length,y=h-p-(v-lo)/span*(h-2*p),bh=h-p-y;return `<rect x="${{x}}" y="${{y}}" width="${{bw}}" height="${{Math.max(2,bh)}}" rx="2" fill="${{r.pareto_rank===1?'#16845b':'#6f87d8'}}"><title>trial ${{r.trial_id}}: ${{v}}</title></rect><text x="${{x+bw/2}}" y="${{h-16}}" text-anchor="middle" font-size="10">${{r.trial_id}}</text>`}}).join('')}}<text x="12" y="18" font-size="11">max ${{fmt(hi)}}</text><text x="12" y="${{h-46}}" font-size="11">min ${{fmt(lo)}}</text></svg>`}}
function scatter(pair){{const pts=(pair.points||[]).filter(p=>p.x!=null&&p.y!=null);if(!pts.length)return '<div class=sub>Нет данных</div>';const xs=pts.map(p=>+p.x),ys=pts.map(p=>+p.y),xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys),w=1000,h=270,p=48,sx=x=>p+(x-xmin)/(xmax-xmin||1)*(w-2*p),sy=y=>h-p-(y-ymin)/(ymax-ymin||1)*(h-2*p);return `<svg viewBox="0 0 ${{w}} ${{h}}"><line x1="${{p}}" y1="${{h-p}}" x2="${{w-p}}" y2="${{h-p}}" stroke="#b9c2cf"/><line x1="${{p}}" y1="${{p}}" x2="${{p}}" y2="${{h-p}}" stroke="#b9c2cf"/>${{pts.map(q=>`<circle cx="${{sx(+q.x)}}" cy="${{sy(+q.y)}}" r="${{q.pareto_rank===1?7:5}}" fill="${{q.pareto_rank===1?'#16845b':'#6f87d8'}}"><title>trial ${{q.trial_id}} · ${{pair.x}}=${{q.x}} · ${{pair.y}}=${{q.y}}</title></circle>`).join('')}}<text x="${{w/2}}" y="${{h-8}}" text-anchor="middle" font-size="11">${{esc(pair.x)}}</text><text x="12" y="${{h/2}}" font-size="11">${{esc(pair.y)}}</text></svg>`}}
const s=P.summary||{{}},metrics=(P.objectives||[]).map(x=>x.name);let out=`<div class=grid><div class=card><span>Вариантов</span><b>${{s.trial_count||0}}</b></div><div class=card><span>Завершено</span><b>${{s.completed_count||0}}</b></div><div class=card><span>Pareto rank 1</span><b>${{s.pareto_rank1_count||0}}</b></div><div class=card><span>Ошибок</span><b class="${{s.failed_count?'bad':'ok'}}">${{s.failed_count||0}}</b></div></div>`;
out+=`<section class=panel><h2>Варианты</h2><div style="overflow:auto"><table><thead><tr><th>Trial</th><th>Статус</th><th>Pareto</th><th>Компонент</th><th>Параметры</th>${{metrics.map(m=>`<th>${{esc(m)}}</th>`).join('')}}</tr></thead><tbody>${{P.trials.map(t=>`<tr><td>${{t.trial_id}}</td><td>${{esc(t.status)}}</td><td>${{t.pareto_rank??'—'}}</td><td>${{t.component_id??'—'}}</td><td><code>${{esc(JSON.stringify(t.parameters||{{}}))}}</code></td>${{metrics.map(m=>`<td>${{fmt((t.objectives||{{}})[m])}}</td>`).join('')}}</tr>`).join('')}}</tbody></table></div></section>`;
for(const m of metrics)out+=`<section class=panel><h2>${{esc(m)}}</h2><div class=chart>${{barChart(m)}}</div><div class=legend>Зелёный = Pareto rank 1; остальные = прочие завершённые варианты. Высота показывает только эту метрику.</div></section>`;
for(const pair of (P.pairwise_objective_plots||[]).slice(0,6))out+=`<section class=panel><h2>${{esc(pair.x)}} × ${{esc(pair.y)}}</h2><div class=chart>${{scatter(pair)}}</div></section>`;
if((P.comparisons||[]).length)out+=`<section class=panel><h2>Парные сравнения</h2><div style="overflow:auto"><table><tr><th>Метрика</th><th>Baseline</th><th>Challenger</th><th>Δ</th><th>95% CI</th><th>Классификация</th></tr>${{P.comparisons.map(c=>`<tr><td>${{esc(c.metric_name)}}</td><td>${{c.baseline_component_id}}</td><td>${{c.challenger_component_id}}</td><td>${{fmt(c.delta)}}</td><td>${{fmt(c.ci_low)}} … ${{fmt(c.ci_high)}}</td><td>${{esc(c.classification)}}</td></tr>`).join('')}}</table></div></section>`;
if((P.parameter_effects||[]).length)out+=`<section class=panel><h2>Параметры</h2><p class=sub>Это описательные группировки, не доказательство причинности.</p>${{P.parameter_effects.map(p=>`<details><summary>${{esc(p.parameter)}}</summary><pre>${{esc(JSON.stringify(p.groups,null,2))}}</pre></details>`).join('')}}</section>`;
out+=`<section class=panel><h2>Воспроизводимость</h2><div><span class=pill>definition ${{esc((P.definition_hash||'').slice(0,16))}}</span><span class=pill>plan ${{esc((P.plan_hash||'').slice(0,16))}}</span><span class=pill>failed trials retained</span><span class=pill>no hidden score</span></div></section>`;
app.innerHTML=out;
</script></main></body></html>'''


def write_report(destination: Path | str, *, analytics: dict[str, Any], plan: dict[str, Any], lab_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(destination).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    payload = build_report_payload(analytics=analytics, plan=plan, lab_manifest=lab_manifest)
    json_path = root / "research-report.json"
    html_path = root / "research-report.html"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")
    return {
        "schema": REPORT_SCHEMA,
        "plan_id": payload.get("plan_id"),
        "json": str(json_path),
        "html": str(html_path),
        "self_contained_html": True,
    }
