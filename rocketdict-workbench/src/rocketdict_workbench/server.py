from __future__ import annotations

from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import parse_qs, urlparse

from .core import CoreError
from .project import WorkbenchProject
from .report import write_report

MAX_UPLOAD = 250 * 1024 * 1024


def _index_html() -> bytes:
    return r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RocketDict Workbench</title>
<style>:root{--bg:#f3f5f8;--paper:#fff;--ink:#151b23;--muted:#697586;--line:#dce2ea;--blue:#315efb;--ok:#16845b;--bad:#c73838}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px system-ui,sans-serif}header{background:var(--paper);border-bottom:1px solid var(--line);padding:18px 24px;position:sticky;top:0;z-index:3}header h1{margin:0;font-size:21px}nav{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}button,.button,select,input,textarea{font:inherit}button,.button{border:1px solid var(--line);background:var(--paper);padding:8px 12px;border-radius:8px;cursor:pointer}button.primary{background:var(--blue);color:white;border-color:var(--blue)}main{max-width:1450px;margin:auto;padding:20px}.panel{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.metric{border:1px solid var(--line);padding:12px;border-radius:10px}.metric b{display:block;font-size:22px}.muted{color:var(--muted)}.ok{color:var(--ok)}.bad{color:var(--bad)}table{width:100%;border-collapse:collapse}th,td{padding:7px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.stage{border-top:1px solid var(--line);padding:9px 0}.impl{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 7px;margin:2px}.hidden{display:none}textarea{width:100%;min-height:110px;border:1px solid var(--line);border-radius:8px;padding:8px}input[type=text],input[type=number],select{border:1px solid var(--line);border-radius:8px;padding:7px;max-width:100%}pre{overflow:auto;background:#f8f9fb;border:1px solid var(--line);padding:10px;border-radius:8px}.tabs section{display:none}.tabs section.active{display:block}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.grow{flex:1}.notice{padding:10px;border-left:4px solid var(--blue);background:#f7f9ff;margin:10px 0}@media(max-width:700px){main{padding:10px}}</style></head><body>
<header><h1>RocketDict Workbench <span class="muted">product + research</span></h1><nav><button data-tab="product">Создать словарик</button><button data-tab="research">Исследование</button><button data-tab="tools">Инструменты</button><button data-tab="reports">Отчёты</button></nav></header><main class="tabs">
<section id="product" class="active"><div class="panel"><h2>Проект</h2><div id="status">Загрузка…</div></div><div class="panel"><h2>1. Исходник</h2><p class="muted">SRT / VTT / ASS / SSA / TXT. Файл копируется в проект до обработки.</p><form id="upload"><input type=file name=file accept=".srt,.vtt,.ass,.ssa,.txt" required> <button class=primary>Импортировать</button></form><pre id="uploadResult" class=hidden></pre></div><div class="panel"><h2>2. Производственный pipeline</h2><div class=notice>Workbench 0.1 уже использует реальный RocketDict core и умеет импорт/интерпретацию. Автоматический проход structure → NLP → MT → senses → cards → export подключается в следующем milestone; отсутствующий backend никогда не заменяется фиктивным.</div><button disabled>Запустить полный словарик (0.2)</button></div></section>
<section id="research"><div class="panel"><h2>Новый single-stage эксперимент</h2><p class=muted>Выберите стадию и несколько реализаций. Это создаёт настоящий immutable ExperimentBench definition/plan.</p><div class=row><label>Стадия <select id=stageSelect></select></label><label>Seeds <input id=seeds value="0" size=10></label><label class=grow>Название <input id=campaignName value="Workbench comparison" style="width:100%"></label></div><div id=implSelect style="margin:12px 0"></div><label>Inputs JSON<textarea id=inputsJson>{}</textarea></label><label>Objectives JSON<textarea id=objectivesJson>[{"name":"wall_time_ms","direction":"minimize","unit":"ms"}]</textarea></label><button id=createCampaign class=primary>Создать plan</button><pre id=campaignResult class=hidden></pre></div><div class=panel><h2>Запуск / отчёт</h2><div class=row><label>Plan ID <input id=planId type=number min=1></label><button id=runPlan>Запустить plan</button><button id=makeReport>Сформировать отчёт</button></div><pre id=runResult class=hidden></pre></div></section>
<section id="tools"><div class=panel><h2>Lab Registry</h2><p class=muted>Каталог не захардкожен в UI: он загружается из того же registry/ABI, которым пользуется исполнение.</p><input id=toolFilter type=text placeholder="Фильтр стадии / реализации" style="width:100%"><div id=catalog>Загрузка…</div></div></section>
<section id="reports"><div class=panel><h2>Отчёты проекта</h2><div id=reportsList>Отчёты появятся после запуска эксперимента.</div></div></section>
</main><script>
let C=null;const $=x=>document.getElementById(x),esc=x=>String(x??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function api(path,opt={}){const r=await fetch(path,opt),j=await r.json();if(!r.ok||j.status==='error')throw new Error(j.error||JSON.stringify(j));return j}
function tab(id){document.querySelectorAll('.tabs section').forEach(x=>x.classList.toggle('active',x.id===id))}document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));
async function loadStatus(){try{const s=await api('/api/status');$('status').innerHTML=`<div class=grid><div class=metric><span>Core</span><b class="${s.core.available?'ok':'bad'}">${esc(s.core.rocketdict_version||'нет')}</b></div><div class=metric><span>Inputs</span><b>${(s.project.inputs||[]).length}</b></div><div class=metric><span>Research plans</span><b>${(s.project.research_runs||[]).length}</b></div><div class=metric><span>Lab implementations</span><b>${s.lab_summary?.implementation_count??'—'}</b></div></div>${s.core.capabilities?.pysubs2?'':'<div class="notice bad">В runtime нет pysubs2: старое ядро не сможет принять subtitle format без деградации. Workbench это блокирует.</div>'}`;}catch(e){$('status').textContent=e}}
async function loadCatalog(){try{C=await api('/api/catalog');renderCatalog();$('stageSelect').innerHTML=C.stages.map(s=>`<option value="${s.number}">${s.number}. ${esc(s.title)}</option>`).join('');renderImpls()}catch(e){$('catalog').textContent=e}};
function renderCatalog(){if(!C)return;const q=$('toolFilter').value.toLowerCase();$('catalog').innerHTML=C.stages.filter(s=>(s.title+' '+s.key+' '+s.implementations.map(i=>i.label+' '+i.implementation_key).join(' ')).toLowerCase().includes(q)).map(s=>`<div class=stage><b>${s.number}. ${esc(s.title)}</b> <span class=muted>${s.implementation_count} реализаций</span><div>${s.implementations.slice(0,20).map(i=>`<span class=impl title="${esc((i.availability.blockers||[]).join(', '))}">${esc(i.implementation_key)}</span>`).join('')}${s.implementations.length>20?' …':''}</div></div>`).join('')};$('toolFilter').oninput=renderCatalog;
function renderImpls(){if(!C)return;const s=C.stages.find(x=>x.number==+$('stageSelect').value);$('implSelect').innerHTML=(s?.implementations||[]).map(i=>`<label class=impl><input type=checkbox name=impl value="${esc(i.implementation_key)}"> ${esc(i.label)} <span class=muted>${esc(i.implementation_key)}</span></label>`).join('')}$('stageSelect').onchange=renderImpls;
$('upload').onsubmit=async e=>{e.preventDefault();const fd=new FormData(e.target);$('uploadResult').classList.remove('hidden');$('uploadResult').textContent='Импорт…';try{$('uploadResult').textContent=JSON.stringify(await api('/api/import',{method:'POST',body:fd}),null,2);loadStatus()}catch(x){$('uploadResult').textContent=x}};
$('createCampaign').onclick=async()=>{const impl=[...document.querySelectorAll('input[name=impl]:checked')].map(x=>x.value);const body={stage_number:+$('stageSelect').value,implementation_keys:impl,seeds:$('seeds').value.split(',').map(x=>+x.trim()).filter(Number.isFinite),display_name:$('campaignName').value,inputs_payload:JSON.parse($('inputsJson').value),objectives:JSON.parse($('objectivesJson').value)};$('campaignResult').classList.remove('hidden');try{const r=await api('/api/campaign/single',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('campaignResult').textContent=JSON.stringify(r,null,2);const id=r.plan?.id||r.plan?.plan_id;if(id)$('planId').value=id;loadStatus()}catch(x){$('campaignResult').textContent=x}};
$('runPlan').onclick=async()=>{$('runResult').classList.remove('hidden');$('runResult').textContent='Запуск…';try{$('runResult').textContent=JSON.stringify(await api('/api/campaign/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan_id:+$('planId').value})}),null,2)}catch(x){$('runResult').textContent=x}};
$('makeReport').onclick=async()=>{$('runResult').classList.remove('hidden');try{const r=await api('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan_id:+$('planId').value})});$('runResult').textContent=JSON.stringify(r,null,2);$('reportsList').innerHTML=`<a class=button target=_blank href="${esc(r.url)}">Открыть отчёт plan ${r.plan_id}</a>`;tab('reports')}catch(x){$('runResult').textContent=x}};
loadStatus();loadCatalog();
</script></body></html>'''.encode('utf-8')


class WorkbenchHTTPServer(ThreadingHTTPServer):
    def __init__(self, address, project: WorkbenchProject):  # type: ignore[no-untyped-def]
        self.project = project
        super().__init__(address, WorkbenchHandler)


class WorkbenchHandler(BaseHTTPRequestHandler):
    server: WorkbenchHTTPServer

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json(self, value: Any, status: int = 200) -> None:
        raw = json.dumps(value, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def _error(self, exc: Exception, status: int = 400) -> None:
        payload = {"status":"error","type":type(exc).__name__,"error":str(exc)}
        if isinstance(exc, CoreError): payload.update({"stderr":exc.stderr[-3000:],"stdout":exc.stdout[-3000:]})
        self._json(payload, status)

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or "0")
        if length > MAX_UPLOAD: raise ValueError(f"Request exceeds {MAX_UPLOAD} bytes")
        return self.rfile.read(length)

    def _json_body(self) -> dict[str, Any]:
        value = json.loads(self._body() or b"{}")
        if not isinstance(value, dict): raise ValueError("JSON body must be an object")
        return value

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                raw=_index_html(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw); return
            if parsed.path == "/api/status": self._json(self.server.project.status(probe_runtime=False)); return
            if parsed.path == "/api/catalog":
                probe = parse_qs(parsed.query).get("probe", ["0"])[0] in {"1","true","yes"}
                self._json(self.server.project.lab_catalog(probe_runtime=probe)); return
            if parsed.path.startswith("/reports/"):
                rel = parsed.path.removeprefix("/reports/")
                target = (self.server.project.paths.reports / rel).resolve()
                if self.server.project.paths.reports.resolve() not in target.parents or not target.is_file(): raise FileNotFoundError(rel)
                raw=target.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8" if target.suffix==".html" else "application/octet-stream"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw); return
            self._json({"status":"error","error":"not found"},404)
        except Exception as exc: self._error(exc,500)

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path == "/api/import":
                ctype=self.headers.get("Content-Type","")
                if "multipart/form-data" not in ctype: raise ValueError("multipart/form-data required")
                raw=self._body(); msg=BytesParser(policy=email_policy).parsebytes((f"Content-Type: {ctype}\r\nMIME-Version: 1.0\r\n\r\n").encode()+raw)
                part=next((p for p in msg.iter_parts() if p.get_param("name",header="content-disposition")=="file"),None)
                if part is None: raise ValueError("file field missing")
                filename=Path(part.get_filename() or "upload.txt").name; data=part.get_payload(decode=True) or b""
                with tempfile.TemporaryDirectory(prefix="rd-workbench-upload-") as td:
                    path=Path(td)/filename; path.write_bytes(data); result=self.server.project.import_source(path)
                self._json(result); return
            if self.path == "/api/campaign/single":
                b=self._json_body(); keys=[str(x) for x in b.get("implementation_keys") or []]
                if not keys: raise ValueError("Select at least one implementation")
                definition={"definition_key":f"workbench-stage-{int(b['stage_number'])}-{len(self.server.project.metadata().get('research_runs',[]))+1}","display_name":str(b.get("display_name") or "Workbench comparison"),"stage_number":int(b["stage_number"]),"implementation_keys":keys,"inputs_payload":dict(b.get("inputs_payload") or {}),"settings_by_implementation":dict(b.get("settings_by_implementation") or {}),"objectives":list(b.get("objectives") or []),"seeds":list(b.get("seeds") or [0]),"guardrails":list(b.get("guardrails") or []),"author":"rocketdict-workbench","reason":"User-created Workbench research comparison"}
                self._json(self.server.project.create_research_campaign(definition)); return
            if self.path == "/api/campaign/run":
                b=self._json_body(); self._json(self.server.project.core.run_experiment_plan(self.server.project.paths.database,int(b["plan_id"]),max_new_trials=b.get("max_new_trials"),timeout=7200)); return
            if self.path == "/api/report":
                b=self._json_body(); pid=int(b["plan_id"]); core=self.server.project.core; analytics=core.experiment_analytics(self.server.project.paths.database,pid); plan=core.experiment_plan(self.server.project.paths.database,pid); catalog=self.server.project.lab_catalog(probe_runtime=False); dest=self.server.project.paths.reports/f"experiment-{pid}"; machine=core.export_experiment(self.server.project.paths.database,pid,self.server.project.paths.experiments/f"plan-{pid}"); human=write_report(dest,analytics=analytics,plan=plan,lab_manifest=catalog); self._json({"plan_id":pid,"human":human,"machine":machine,"url":f"/reports/experiment-{pid}/research-report.html"}); return
            self._json({"status":"error","error":"not found"},404)
        except Exception as exc: self._error(exc,400)


def serve(project: WorkbenchProject, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = WorkbenchHTTPServer((host, int(port)), project)
    print(f"RocketDict Workbench: http://{host}:{server.server_address[1]}")
    print("Local-only by default. Ctrl+C to stop.")
    try: server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt: pass
    finally: server.server_close()
