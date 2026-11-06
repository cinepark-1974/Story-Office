"""성계 그림 — 엔진 행성들이 중심 구체 둘레를 천천히 돕니다.

움직임은 브라우저 안의 작은 스크립트가 맡습니다(Streamlit 화면 안에 별도 창으로 들어갑니다).
- 안쪽 궤도(핵심 라인·번역)와 바깥 궤도(OSMU·파트너)는 대열을 유지한 채 함께 돕니다.
- 바통 점선, CREATOR에서 갈라지는 곁가지, 중심으로 가는 실도 행성을 따라 움직입니다.
- 궤도 밖 단독 별은 제자리에서 살짝 떠다닙니다.
- 행성 위에 마우스를 올리면 전체가 멈춰서 누르기 쉽습니다.
- 기기에서 '동작 줄이기'를 켜 둔 사람에게는 움직이지 않는 그림으로 보입니다.
"""

import base64
import html
import json
from pathlib import Path

# 한 바퀴 도는 데 걸리는 시간(초). 숫자가 클수록 느립니다.
INNER_PERIOD = 240   # 4분
OUTER_PERIOD = 420   # 7분

W, H, CX, CY = 1200, 720, 600, 350
INNER = (300, 175)   # 안쪽 궤도 가로·세로 반지름
OUTER = (500, 292)   # 바깥 궤도
CORE_R = 100         # 중심 구체 반지름 (실이 닿는 곳)
FRAME_HEIGHT = 630   # Streamlit 안에서 이 그림이 차지하는 높이(px)

CORE_TIP = ("STORY ENGINE SYSTEM 개발실 열기 — 모든 엔진의 공통 설계: GitHub 저장소 → Streamlit 앱, main.py에서 시작, "
            "Claude API 연산, 블루진픽처스 기획개발 규칙. 판단 기준은 언어모델이 아니라 엔진의 규칙에 있습니다.")

_CORE_IMG = Path(__file__).parent / "static" / "core.webp"


def _bodies(groups: list, partner: dict) -> list:
    core_names = {e["short"] for e in groups[0]["engines"]}
    out = []
    for g in groups:
        for e in g["engines"]:
            if not e["url"]:      # 앱이 없는 도구(Converter)는 성계에 넣지 않습니다
                continue
            o = e["orbit"]
            is_core = e["short"] in core_names
            body = {
                "id": e["short"], "kind": "planet", "url": e["url"],
                "label": e["short"], "sub": "" if e["url"] else "앱 없음",
                "tip": f'{e["name"]} — {e["desc"]}',
                "r": 20 if is_core else 13, "size": 15 if is_core else 12,
                "ring": o[0],
            }
            if o[0] == "free":
                body["x"], body["y"] = o[1], o[2]
            else:
                body["a"] = o[1]
            out.append(body)
    o = partner["orbit"]
    out.append({
        "id": "PARTNER", "kind": "probe", "url": partner["url"],
        "label": "WRITER'S PARTNER", "sub": "" if partner["url"] else "주소 대기",
        "tip": f'{partner["name"]} — {partner["desc"]}', "r": 9, "size": 12,
        "ring": o[0], "a": o[1],
    })
    return out


def build_html(groups: list, partner: dict, system_project: str | None = None, admin_url: str | None = None) -> str:
    core_b64 = base64.b64encode(_CORE_IMG.read_bytes()).decode()
    data = {
        "W": W, "H": H, "CX": CX, "CY": CY, "INNER": INNER, "OUTER": OUTER, "CORE_R": CORE_R,
        "PERIOD": {"inner": INNER_PERIOD, "outer": OUTER_PERIOD},
        "bodies": _bodies(groups, partner),
        "relay": [e["short"] for e in groups[0]["engines"]],   # 바통 순서
        "branchFrom": "CREATOR",
        "branchTo": [e["short"] for e in groups[1]["engines"]],
        "coreTip": CORE_TIP,
        "coreUrl": system_project,
        "admin": {"url": admin_url, "x": 1090, "y": 650} if admin_url else None,
    }
    return (_TEMPLATE
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__CORE__", f"data:image/webp;base64,{core_b64}")
            .replace("__CORE_TIP__", html.escape(CORE_TIP)))


_TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
@import url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@latest/Paperlogy.css');
html,body{margin:0;padding:0;background:#FFFFFF;height:100%;overflow:hidden;}
#wrap{position:absolute;inset:0;background:#122335;border-radius:8px;overflow:hidden;}
svg{display:block;width:100%;height:100%;font-family:'Paperlogy','Pretendard',sans-serif;}
.orbit{fill:none;stroke:rgba(143,211,228,.22);stroke-width:1.2;}
.relay{fill:none;stroke:rgba(143,211,228,.85);stroke-width:2;stroke-dasharray:6 8;animation:baton 2.4s linear infinite;}
.branch{fill:none;stroke:rgba(143,211,228,.4);stroke-width:1.2;stroke-dasharray:2 5;}
.tether{stroke:rgba(143,211,228,.13);stroke-width:1;}
.tether.on{stroke:rgba(143,211,228,.75);stroke-width:1.5;}
.tether.dim{stroke:rgba(143,211,228,.07);}
@keyframes baton{to{stroke-dashoffset:-28;}}
.halo{fill:rgba(143,211,228,.14);}
.body{fill:#DDF1F7;stroke:#8FD3E4;stroke-width:2;}
.lbl{fill:#F7FBFC;font-weight:700;text-anchor:middle;letter-spacing:.06em;}
.sub{fill:rgba(247,251,252,.55);text-anchor:middle;font-size:11px;}
.probe{fill:#DBA12C;}
.admin rect.panel{fill:rgba(143,211,228,.12);stroke:#8FD3E4;stroke-width:1.6;}
.admin line{stroke:#DDF1F7;stroke-width:2;stroke-linecap:round;}
.admin circle.knob{fill:#DBA12C;}
.admin:hover rect.panel{fill:rgba(143,211,228,.35);stroke:#FFFFFF;}
a{cursor:pointer;}
.hot .body{fill:#FFFFFF;stroke:#FFFFFF;stroke-width:3;}
.hot .halo{fill:rgba(143,211,228,.32);}
.dimg .body{fill:rgba(221,241,247,.25);stroke:rgba(143,211,228,.4);}
.dimg .lbl{fill:rgba(247,251,252,.45);}
@media (prefers-reduced-motion: reduce){.relay{animation:none;}}
</style></head>
<body><div id="wrap">
<svg id="sys" viewBox="0 0 1200 720" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="STORY ENGINE SYSTEM">
  <g id="lOrbit"></g><g id="lLines"></g>
  <g id="core"><title>__CORE_TIP__</title><image href="__CORE__" x="430" y="180" width="340" height="340"/></g>
  <g id="lBodies"></g>
</svg></div>
<script>
const D = __DATA__;
const NS = "http://www.w3.org/2000/svg";
const $ = id => document.getElementById(id);
function el(tag, attrs, parent){ const n=document.createElementNS(NS,tag); for(const k in attrs) n.setAttribute(k,attrs[k]); if(parent) parent.appendChild(n); return n; }

// 궤도
el("ellipse",{class:"orbit",cx:D.CX,cy:D.CY,rx:D.OUTER[0],ry:D.OUTER[1]},$("lOrbit"));
el("ellipse",{class:"orbit",cx:D.CX,cy:D.CY,rx:D.INNER[0],ry:D.INNER[1]},$("lOrbit"));

const relay = el("polyline",{class:"relay"},$("lLines"));
// 가운데 구체 — 누르면 STORY ENGINE SYSTEM 개발실(시스템 전체를 다루는 Claude 프로젝트)
if(D.coreUrl){ const core=$("core"); const a=el("a",{href:D.coreUrl,target:"_blank"}); core.parentNode.insertBefore(a,core); a.appendChild(core); }
const byId = {};
let paused = false;

// 행성
for(const b of D.bodies){
  const tether = el("line",{class:"tether"+(b.url?"":" dim")},$("lLines"));
  const wrap = b.url ? el("a",{href:b.url,target:"_blank"},$("lBodies")) : el("g",{class:"dimg"},$("lBodies"));
  const g = el("g",{},wrap);
  el("title",{},g).textContent = b.tip;
  if(b.kind==="probe"){
    el("circle",{class:"halo",r:18},g);
    el("rect",{class:"probe",x:-7,y:-7,width:14,height:14,transform:"rotate(45)"},g);
  }else{
    el("circle",{class:"halo",r:b.r+9},g);
    el("circle",{class:"body",r:b.r},g);
  }
  const ly = (b.kind==="probe" ? 34 : b.r + b.size + 6);
  const t = el("text",{class:"lbl",y:ly,"font-size":b.size},g); t.textContent = b.label;
  if(b.sub){ const s=el("text",{class:"sub",y:ly+15},g); s.textContent=b.sub; }
  wrap.addEventListener("mouseenter",()=>{ paused=true; wrap.classList.add("hot"); tether.classList.add("on"); });
  wrap.addEventListener("mouseleave",()=>{ paused=false; wrap.classList.remove("hot"); tether.classList.remove("on"); });
  byId[b.id] = {b, g, tether, x:0, y:0, phase:Math.random()*Math.PI*2};
}
const branches = D.branchTo.map(()=>el("line",{class:"branch"},$("lLines")));

// 앱 관리 단추 — 누르면 Streamlit 내 앱 목록(리부트). 상표 로고 대신 제어판 모양 표시.
if(D.admin){
  const a = el("a",{href:D.admin.url,target:"_blank",class:"admin"},$("lBodies"));
  const g = el("g",{transform:`translate(${D.admin.x} ${D.admin.y})`},a);
  el("title",{},g).textContent = "Streamlit 앱 관리 · 엔진을 고친 뒤 여기서 리부트합니다";
  el("rect",{class:"panel",x:-22,y:-18,width:44,height:36,rx:7},g);
  [-8,0,8].forEach((dy,i)=>{ el("line",{x1:-12,y1:dy,x2:12,y2:dy},g); el("circle",{class:"knob",cx:[-5,6,-1][i],cy:dy,r:3},g); });
  const t = el("text",{class:"lbl",y:36,"font-size":12},g); t.textContent = "APP CONTROL";
  const s2 = el("text",{class:"sub",y:51},g); s2.textContent = "Streamlit 앱 관리";
}
$("lLines").insertBefore(relay, null);

function ringPos(ring, deg){
  const [rx,ry] = ring==="inner" ? D.INNER : D.OUTER;
  const a = deg*Math.PI/180;
  return [D.CX + rx*Math.cos(a), D.CY + ry*Math.sin(a)];
}

function draw(t){
  const turn = {inner: 360*t/D.PERIOD.inner, outer: 360*t/D.PERIOD.outer};
  for(const id in byId){
    const o = byId[id], b = o.b;
    let x, y;
    if(b.ring==="free"){ x = b.x + 5*Math.cos(t/24*2*Math.PI + o.phase); y = b.y + 4*Math.sin(t/31*2*Math.PI + o.phase); }
    else { [x,y] = ringPos(b.ring, b.a + turn[b.ring]); }
    o.x=x; o.y=y;
    o.g.setAttribute("transform",`translate(${x.toFixed(1)} ${y.toFixed(1)})`);
    const d = Math.hypot(x-D.CX, y-D.CY) || 1;
    o.tether.setAttribute("x1",(D.CX+(x-D.CX)/d*D.CORE_R).toFixed(1));
    o.tether.setAttribute("y1",(D.CY+(y-D.CY)/d*D.CORE_R).toFixed(1));
    o.tether.setAttribute("x2",x.toFixed(1)); o.tether.setAttribute("y2",y.toFixed(1));
  }
  // 바통 점선 — 핵심 라인 첫 행성에서 마지막 행성까지 안쪽 궤도를 따라
  const a0 = byId[D.relay[0]].b.a + turn.inner, a1 = byId[D.relay[D.relay.length-1]].b.a + turn.inner;
  let end = a1; while(end <= a0) end += 360;
  const pts = [];
  for(let i=0;i<=48;i++){ const [x,y]=ringPos("inner", a0+(end-a0)*i/48); pts.push(x.toFixed(1)+","+y.toFixed(1)); }
  relay.setAttribute("points", pts.join(" "));
  // OSMU 곁가지
  const c = byId[D.branchFrom];
  D.branchTo.forEach((id,i)=>{ const o=byId[id];
    branches[i].setAttribute("x1",c.x.toFixed(1)); branches[i].setAttribute("y1",c.y.toFixed(1));
    branches[i].setAttribute("x2",o.x.toFixed(1)); branches[i].setAttribute("y2",o.y.toFixed(1)); });
}

const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let clock = 0, last = null;
function frame(now){
  if(last!==null && !paused) clock += Math.min((now-last)/1000, 0.1);
  last = now; draw(clock);
  if(!still) requestAnimationFrame(frame);
}
draw(0);
if(!still) requestAnimationFrame(frame);
</script></body></html>"""
