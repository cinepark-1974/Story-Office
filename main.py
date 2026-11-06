"""STORY OFFICE — BLUE JEANS PICTURES 창작 사무실.

화면 두 장
- OFFICE : 매일 쓰는 사무실. 직원(엔진)을 누르면 그 엔진이 열립니다.
- SYSTEM : 『스토리엔진시스템 설명서』와 짝을 이루는 성계 쇼룸.
엔진을 실행하지 않습니다. 엔진 목록과 사무실 자리는 engines.py 에 있습니다.
"""

import html
from datetime import datetime, timezone, timedelta

import requests
import streamlit as st
import streamlit.components.v1 as components

from engines import DESKS, GITHUB_OWNER, GROUPS, OFFICE_H, OFFICE_W, PARTNER, SYSTEM_PROJECT
from system_view import FRAME_HEIGHT, build_html
import staff
from office_docx import build_meeting_docx

KST = timezone(timedelta(hours=9))

# Streamlit 내 앱 목록. 앱 옆 ⋮ 메뉴 → Reboot 로 엔진을 다시 시작합니다.
STREAMLIT_ADMIN = "https://share.streamlit.io/"

st.set_page_config(page_title="STORY OFFICE", page_icon="🔵", layout="wide")


def clean(block: str) -> str:
    """빈 줄과 줄 앞 공백을 지웁니다. 남겨 두면 마크다운이 HTML을 글자로 보여줍니다."""
    return "".join(line.strip() for line in block.splitlines() if line.strip())


# ---------- 디자인 ----------
CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@latest/Paperlogy.css');
:root{ --yale:#0F3B59; --glacier:#F7FBFC; --gold:#DBA12C; --line:#C8D6DD; --ink:#142C3C; --muted:#5B7282;
  --space:#122335; --orb:#8FD3E4; }
html, body, [class*="css"], .stApp, .stMarkdown, button, input { font-family:'Paperlogy','Pretendard',sans-serif !important; }
.stApp { background:#FFFFFF; color:var(--ink); }
header[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:2.2rem; max-width:1200px; }
.so-top { display:flex; align-items:flex-end; justify-content:space-between; border-bottom:2px solid var(--yale);
  padding-bottom:14px; margin-bottom:8px; gap:16px; flex-wrap:wrap; }
.so-brand { font-size:12px; letter-spacing:.18em; color:var(--muted); font-weight:700; }
.so-title { font-size:34px; font-weight:900; color:var(--yale); line-height:1.1; margin-top:4px; }
.so-meta { font-size:13px; color:var(--muted); text-align:right; }
.so-admin { display:inline-block; margin-top:6px; font-size:12px; font-weight:700; color:var(--yale) !important;
  text-decoration:none !important; border:1px solid var(--line); border-radius:4px; padding:4px 9px; background:var(--glacier); }
.so-admin:hover { border-color:var(--yale); }
.so-meta b { color:var(--gold); font-weight:900; font-size:18px; }
.so-sys { background:var(--space); border-radius:8px; margin:22px 0 6px; overflow:hidden; }
.so-sys svg { display:block; width:100%; height:auto; }
.so-sys .orbit { fill:none; stroke:rgba(143,211,228,.22); stroke-width:1.2; }
.so-sys .relay { fill:none; stroke:rgba(143,211,228,.85); stroke-width:2; stroke-dasharray:6 8; animation:baton 2.4s linear infinite; }
.so-sys .branch { fill:none; stroke:rgba(143,211,228,.4); stroke-width:1.2; stroke-dasharray:2 5; }
@keyframes baton { to { stroke-dashoffset:-28; } }
@media (prefers-reduced-motion: reduce) { .so-sys .relay { animation:none; } }
.so-sys .body { fill:#DDF1F7; stroke:var(--orb); stroke-width:2; }
.so-sys .halo { fill:rgba(143,211,228,.14); }
.so-sys .lbl { fill:#F7FBFC; font-weight:700; text-anchor:middle; letter-spacing:.06em; }
.so-sys .sub { fill:rgba(247,251,252,.55); text-anchor:middle; font-size:11px; }
.so-sys a { cursor:pointer; }
.so-sys a:hover .body { fill:#FFFFFF; stroke:#FFFFFF; stroke-width:3; }
.so-sys a:hover .halo { fill:rgba(143,211,228,.32); }
.so-sys .dim .body { fill:rgba(221,241,247,.25); stroke:rgba(143,211,228,.4); }
.so-sys .dim .lbl { fill:rgba(247,251,252,.45); }
.so-sys .probe { fill:var(--gold); }
.so-sys .tether { stroke:rgba(143,211,228,.13); stroke-width:1; }
.so-sys a:hover .tether { stroke:rgba(143,211,228,.7); stroke-width:1.5; }
.so-sys .dim .tether { stroke:rgba(143,211,228,.07); }
.so-hint { font-size:12px; color:var(--muted); margin-bottom:6px; }
.so-group { font-size:15px; font-weight:900; color:var(--yale); margin:30px 0 2px; padding-left:10px; border-left:4px solid var(--yale); }
.so-gnote { font-size:12.5px; color:var(--muted); margin:0 0 10px 14px; }
.so-card { background:var(--glacier); border:1px solid var(--line); border-radius:6px; padding:16px 16px 14px;
  min-height:176px; display:flex; flex-direction:column; margin-bottom:14px; }
.so-name { font-size:17px; font-weight:900; color:var(--ink); }
.so-desc { font-size:13.5px; color:var(--ink); line-height:1.55; margin:8px 0 12px; flex:1; }
.so-foot { display:flex; align-items:center; justify-content:flex-end; gap:6px; border-top:1px solid var(--line); padding-top:10px; margin-top:8px; }
.so-dev { display:inline-block; color:var(--yale) !important; text-decoration:none !important; font-size:13px; font-weight:700;
  padding:6px 11px; border:1px solid var(--yale); border-radius:4px; white-space:nowrap; background:#FFFFFF; }
.so-dev:hover { background:var(--glacier); }
.so-date { font-size:11.5px; color:var(--muted); line-height:1.45; }
.so-date b { display:block; white-space:nowrap; color:var(--ink); font-weight:700; }
.so-date.fresh b { color:var(--gold); }
.so-go { display:inline-block; background:var(--yale); color:#FFFFFF !important; text-decoration:none !important;
  font-size:13px; font-weight:700; padding:7px 14px; border-radius:4px; white-space:nowrap; }
.so-go:hover { background:var(--ink); }
.so-none { font-size:12px; color:var(--muted); border:1px dashed var(--line); padding:6px 10px; border-radius:4px; white-space:nowrap; }
.so-partner { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  background:#FFFFFF; border:1px solid var(--yale); border-radius:6px; padding:14px 18px; margin:18px 0 0; }
.so-partner .so-name { color:var(--yale); }
.so-partner .so-desc { margin:4px 0 0; }
.so-err { background:#FFFFFF; border:1px dashed var(--line); border-radius:6px; padding:14px; font-size:13px; color:var(--muted); margin-bottom:14px; }
.so-office { position:relative; width:100%; margin:22px 0 6px; }
.so-office img { display:block; width:100%; height:auto; border-radius:8px; }
.so-seat { position:absolute; display:block; border-radius:8px; }
.so-seat.link { cursor:pointer; }
.so-seat:hover, .so-seat:focus { outline:2px solid #FFFFFF; background:rgba(15,59,89,.14); z-index:5; }
.so-tag { display:none; position:absolute; left:50%; bottom:100%; transform:translate(-50%,-6px); background:var(--yale);
  color:#FFFFFF; border-radius:4px; padding:6px 10px; font-size:12.5px; font-weight:700; white-space:nowrap; z-index:6; text-align:center; line-height:1.4; }
.so-seat.below .so-tag { bottom:auto; top:100%; transform:translate(-50%,6px); }
.so-tag small { display:block; font-weight:400; opacity:.8; font-size:11.5px; }
.so-seat:hover .so-tag, .so-seat:focus .so-tag { display:block; }
.so-assign { display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;
  border:2px solid var(--yale); border-radius:6px; padding:14px 18px; margin:16px 0 12px; background:#FFFFFF; }
.so-alabel { font-size:11.5px; font-weight:700; color:var(--muted); letter-spacing:.04em; margin-bottom:4px; }
.so-aname { font-size:22px; font-weight:900; color:var(--yale); margin-bottom:4px; }
.so-paper { background:var(--glacier); border:1px solid var(--line); border-radius:6px; padding:16px 18px; margin-bottom:12px; font-size:13.5px; line-height:1.6; }
.so-paper p { margin:4px 0 10px; } .so-paper ol, .so-paper ul { margin:2px 0 10px; padding-left:20px; }
.so-ptitle { font-size:22px; font-weight:900; color:var(--yale); margin:2px 0 6px; }
.so-chips span { display:inline-block; font-size:11.5px; font-weight:700; color:var(--yale); border:1px solid var(--line);
  background:#FFFFFF; border-radius:4px; padding:2px 8px; margin:0 6px 8px 0; }
.so-op { background:#FFFFFF; border:1px solid var(--line); border-radius:6px; padding:12px 14px; margin-bottom:12px; font-size:13px; line-height:1.55; min-height:150px; }
.so-op ul { margin:6px 0 0; padding-left:18px; color:var(--ink); }
.so-opname { font-weight:900; color:var(--yale); font-size:14px; }
.so-opline { margin-top:4px; font-weight:700; }
.so-badge { font-size:11px; font-weight:700; border-radius:3px; padding:1px 6px; margin-left:4px; vertical-align:middle; }
.so-badge.ok { background:#E6F2EA; color:#1F6B3A; } .so-badge.mid { background:#FBF3E2; color:#8A5A00; } .so-badge.no { background:#F8E7E7; color:#8A1F1F; }
.so-note { font-size:12px; color:var(--muted); margin-top:36px; border-top:1px solid var(--line); padding-top:12px; }
</style>
"""
st.markdown("\n".join(l for l in CSS.splitlines() if l.strip()), unsafe_allow_html=True)


# ---------- GitHub 최근 수정일 ----------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pushed_dates(owner: str) -> dict:
    """계정의 공개 저장소 전체를 한 번에 읽어 {저장소이름: 마지막 수정 시각} 을 돌려줍니다."""
    r = requests.get(
        f"https://api.github.com/users/{owner}/repos",
        params={"per_page": 100, "type": "owner"},
        headers={"Accept": "application/vnd.github+json"},
        timeout=10,
    )
    r.raise_for_status()
    return {repo["name"]: repo["pushed_at"] for repo in r.json()}


def describe_date(iso: str | None) -> tuple[str, bool]:
    """'2026-10-29 · 7일 전' 같은 표기와, 최근 7일 이내인지 여부."""
    if not iso:
        return "수정일 확인 불가", False
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KST)
    days = (datetime.now(KST).date() - dt.date()).days
    ago = "오늘" if days <= 0 else "어제" if days == 1 else f"{days}일 전"
    return f"{dt:%Y-%m-%d} · {ago}", days <= 7


try:
    pushed = fetch_pushed_dates(GITHUB_OWNER)
    date_error = None
except Exception as e:  # GitHub가 응답하지 않아도 화면은 열립니다
    pushed = {}
    date_error = str(e)


# ---------- 공통 머리 ----------
all_engines = [e for g in GROUPS for e in g["engines"]]


def header(title: str) -> None:
    live = sum(1 for e in all_engines if e["url"])
    now = datetime.now(KST)
    st.markdown(clean(f"""
<div class="so-top">
  <div><div class="so-brand">BLUE JEANS PICTURES · STORY ENGINE SYSTEM</div><div class="so-title">{title}</div></div>
  <div class="so-meta">엔진 <b>{live}</b> / {len(all_engines)} 가동 중<br>{now:%Y-%m-%d %H:%M} 기준<br>
  <a class="so-admin" href="{STREAMLIT_ADMIN}" target="_blank" title="엔진을 고친 뒤 리부트할 때 씁니다">Streamlit 앱 관리 · 리부트</a></div>
</div>"""), unsafe_allow_html=True)


# ---------- OFFICE: 사무실 그림 ----------
def seat_html(key: str, title: str, sub: str, url: str | None) -> str:
    l, t, r, b = DESKS[key]
    style = (f"left:{l / OFFICE_W * 100:.2f}%;top:{t / OFFICE_H * 100:.2f}%;"
             f"width:{(r - l) / OFFICE_W * 100:.2f}%;height:{(b - t) / OFFICE_H * 100:.2f}%;")
    tag = f'<span class="so-tag">{html.escape(title)}<small>{html.escape(sub)}</small></span>'
    below = " below" if t / OFFICE_H < 0.15 else ""   # 그림 맨 위쪽 자리는 이름표를 아래로
    if url:
        target = "" if url.startswith("#") else ' target="_blank"'
        return f'<a class="so-seat link{below}" style="{style}" href="{html.escape(url)}"{target}>{tag}</a>'
    return f'<span class="so-seat{below}" style="{style}" tabindex="0">{tag}</span>'


ENGINE_BY_SHORT = {e["short"]: e for e in all_engines}


def office_scene() -> str:
    """직원은 역할로 앉아 있습니다. 엔진은 직원이 쓰는 도구입니다."""
    seats = []
    for key, r in staff.ROLES.items():
        if r["desk"] not in DESKS:
            continue
        tools = [ENGINE_BY_SHORT[t] for t in r["tools"] if t in ENGINE_BY_SHORT]
        if r["group"] == "round":
            sub, url = "기획 회의 상설 멤버", "#so-meeting"
        else:
            sub = "쓰는 엔진 · " + ", ".join(t["short"] for t in tools) if tools else "기획 회의 참석"
            url = tools[0]["url"] if len(tools) == 1 else ("#so-tools" if tools else "#so-meeting")
        seats.append(seat_html(r["desk"], r["title"], sub, url))
    conv = ENGINE_BY_SHORT.get("CONVERTER")
    if conv:
        seats.append(seat_html("converter", conv["name"], "복합기 · 앱 없음" if not conv["url"] else "복합기", conv["url"]))
    seats.append(seat_html("partner", PARTNER["name"], "열기" if PARTNER["url"] else "주소 대기", PARTNER["url"]))
    seats.append(seat_html("boss", "MR. MOON", "결재석 · 회의 배정을 결정합니다", "#so-meeting"))
    return ('<div class="so-office"><img src="app/static/office.webp" alt="STORY OFFICE">' + "".join(seats) + "</div>")


# ---------- 기획 회의 ----------
def _secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "") or "")
    except Exception:  # secrets 파일이 없을 때
        return ""


def _badge(mark: str) -> str:
    cls = {"통과": "ok", "맞음": "ok", "보완": "mid", "조건부": "mid", "불가": "no", "안 맞음": "no"}.get(mark, "mid")
    return f'<span class="so-badge {cls}">{html.escape(mark or "")}</span>'


def render_meeting(result: dict) -> None:
    idea, m = result["idea"], result["minutes"]
    titles = {k: r["title"] for k, r in staff.ROLES.items()}

    # 배정
    path = staff.ASSIGNMENTS.get(m.get("assignment"), {}).get("path", [])
    first = ENGINE_BY_SHORT.get(path[0]) if path else None
    open_btn = (f'<a class="so-go" href="{html.escape(first["url"])}" target="_blank">{html.escape(first["name"])} 열기</a>'
                if first and first.get("url") else "")
    st.markdown(clean(f"""
<div class="so-assign">
  <div><div class="so-alabel">배정 권고 · 최종 결정은 Mr. MOON</div>
  <div class="so-aname">{html.escape(m.get("assignment", ""))}</div>
  <div class="so-desc">{html.escape(m.get("reason", ""))}</div>
  {f'<div class="so-gnote" style="margin:4px 0 0">다른 길 · {html.escape(m["alternative"])}</div>' if m.get("alternative") else ""}</div>
  {open_btn}
</div>"""), unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        scenes = "".join(f"<li>{html.escape(x)}</li>" for x in idea.get("scenes", []))
        refs = " / ".join(html.escape(x) for x in idea.get("references", []))
        st.markdown(clean(f"""
<div class="so-paper">
  <div class="so-alabel">발제 담당 · 아이디어 한 장</div>
  <div class="so-ptitle">{html.escape(idea.get("title", ""))}</div>
  <div class="so-chips"><span>{html.escape(idea.get("genre", ""))}</span><span>{html.escape(idea.get("market", ""))}</span><span>{html.escape(idea.get("format", ""))}</span></div>
  <p><b>{html.escape(idea.get("logline", ""))}</b></p>
  <p>{html.escape(idea.get("raw_idea", ""))}</p>
  <div class="so-alabel">핵심 장면</div><ol>{scenes}</ol>
  <div class="so-alabel">왜 지금인가</div><p>{html.escape(idea.get("why_now", ""))}</p>
  {f'<div class="so-alabel">레퍼런스</div><p>{refs}</p>' if refs else ""}
</div>"""), unsafe_allow_html=True)
    with c2:
        tasks = "".join(f"<li>{html.escape(x)}</li>" for x in m.get("tasks", []))
        issues = "".join(f"<li>{html.escape(x)}</li>" for x in m.get("issues", []))
        st.markdown(clean(f"""
<div class="so-paper">
  <div class="so-alabel">회의록 담당 · 결론</div><p>{html.escape(m.get("summary", ""))}</p>
  {f'<div class="so-alabel">쟁점</div><ul>{issues}</ul>' if issues else ""}
  <div class="so-alabel">보완 과제 (고치는 것은 작가 몫)</div><ol>{tasks}</ol>
</div>"""), unsafe_allow_html=True)

    st.markdown('<div class="so-alabel" style="margin:14px 0 6px">참석자 의견</div>', unsafe_allow_html=True)
    ops = result["opinions"]
    for i in range(0, len(ops), 3):
        cols = st.columns(3)
        for col, o in zip(cols, ops[i:i + 3]):
            pts = "".join(f"<li>{html.escape(p)}</li>" for p in o.get("points", [])[:3])
            with col:
                st.markdown(clean(f"""
<div class="so-op"><div class="so-opname">{html.escape(titles.get(o["role"], o["role"]))} {_badge(o.get("verdict") or o.get("fit"))}</div>
<div class="so-opline">{html.escape(o.get("one_line", ""))}</div><ul>{pts}</ul></div>"""), unsafe_allow_html=True)

    ei = m.get("engine_input") or {}
    hand = "\n".join(f"[{k}]\n{v}\n" for k, v in ei.items())
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("회의 결과 워드 파일 받기", build_meeting_docx(result, titles),
                           file_name=f"STORY_OFFICE_{idea.get('date', '')}_{idea.get('title', '회의')}.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)
    with d2:
        if PARTNER.get("url"):
            st.link_button("Writer's Partner로 가져가기", PARTNER["url"], use_container_width=True)
    if hand:
        st.caption("엔진 입력 준비 · 오른쪽 위 복사 버튼으로 복사해 배정된 엔진 첫 화면에 옮기면 됩니다.")
        st.code(hand, language=None)
    partner_text = (f"「{idea.get('title')}」 STORY OFFICE 회의 결과입니다. 이 아이디어를 같이 다듬고 싶습니다.\n\n"
                    f"{staff._idea_sheet(idea)}\n\n[회의 결론] {m.get('summary', '')}\n[배정 권고] {m.get('assignment')}\n"
                    "[보완 과제]\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(m.get("tasks", []), 1)))
    with st.expander("Writer's Partner에 붙여 넣을 내용"):
        st.code(partner_text, language=None)


def meeting_section() -> None:
    st.markdown('<div id="so-meeting" class="so-group">기획 회의</div>'
                '<div class="so-gnote">버튼을 누를 때만 직원들이 일합니다. 발제 담당이 아이디어 한 장을 쓰고, 참석자가 각자 따로 읽고 의견을 낸 뒤, '
                '회의록 담당이 어느 책상으로 보낼지 권고합니다. 회의는 아이디어를 고쳐 쓰지 않습니다.</div>', unsafe_allow_html=True)
    api_key, password = _secret("ANTHROPIC_API_KEY"), _secret("OFFICE_PASSWORD")
    if not api_key or not password:
        st.info("회의를 열려면 Streamlit Secrets에 ANTHROPIC_API_KEY와 OFFICE_PASSWORD를 넣어야 합니다. "
                "버튼 하나가 API 사용량을 쓰므로, 비밀번호 없이는 열리지 않게 해 두었습니다.")
        return
    if not st.session_state.get("office_unlocked"):
        with st.form("unlock"):
            pw = st.text_input("사무실 비밀번호", type="password")
            if st.form_submit_button("들어가기"):
                if pw == password:
                    st.session_state["office_unlocked"] = True
                    st.rerun()
                else:
                    st.error("비밀번호가 맞지 않습니다.")
        return

    with st.form("meeting"):
        direction = st.text_input("발제 방향 한 줄 (비워 두면 발제 담당이 알아서)",
                                  placeholder="예: 베트남 시장을 겨냥한 호러 / 이번엔 코미디로 / 숏폼 드라마로")
        scale = st.radio("회의 규모", ["기본 회의 (발제 + 6명)", "전체 회의 (발제 + 12명)"], horizontal=True,
                         help="기본 회의: 구조·인물·장르·반대 담당 + 해당 포맷 담당 + 국내 시장 담당. "
                              "전체 회의: 포맷·시장 담당 모두. 전체 회의는 사용량이 두 배쯤 듭니다.")
        go = st.form_submit_button("발제부터 회의 시작", type="primary")
    if go:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        n = st.session_state.get("meeting_no", 0) + 1
        try:
            with st.status("회의를 시작합니다", expanded=True) as box:
                result = staff.run_meeting(client, direction, full=scale.startswith("전체"), no=n,
                                           date=datetime.now(KST).strftime("%Y-%m-%d"), progress=box.write)
                box.update(label="회의가 끝났습니다", state="complete", expanded=False)
            st.session_state["meeting_result"], st.session_state["meeting_no"] = result, n
        except Exception as e:
            st.error(f"회의 중 문제가 생겼습니다: {type(e).__name__}: {e}")
    if st.session_state.get("meeting_result"):
        try:
            render_meeting(st.session_state["meeting_result"])
        except Exception as e:
            st.markdown(f'<div class="so-err">회의 결과를 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)


def partner_card() -> None:
    try:
        p_action = (f'<a class="so-go" href="{html.escape(PARTNER["url"])}" target="_blank">열기</a>'
                    if PARTNER["url"] else '<span class="so-none">주소 대기</span>')
        st.markdown(clean(f"""
<div class="so-partner"><div><div class="so-name">{html.escape(PARTNER["name"])}</div>
<div class="so-desc">{html.escape(PARTNER["desc"])}</div></div>{p_action}</div>"""), unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="so-err">파트너 카드를 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)


def render_card(engine: dict) -> str:
    label, fresh = describe_date(pushed.get(engine["repo"]))
    action = (f'<a class="so-go" href="{html.escape(engine["url"])}" target="_blank" title="엔진 앱 열기">열기</a>'
              if engine["url"] else '<span class="so-none">앱 없음</span>')
    dev = (f'<a class="so-dev" href="{html.escape(engine["project"])}" target="_blank" '
           f'title="이 엔진을 고치는 Claude 프로젝트방">개발실</a>' if engine.get("project") else "")
    return clean(f"""
<div class="so-card">
  <div class="so-name">{html.escape(engine["name"])}</div>
  <div class="so-desc">{html.escape(engine["desc"])}</div>
  <div class="so-date{' fresh' if fresh else ''}">최근 수정<b>{label}</b></div>
  <div class="so-foot">{dev}{action}</div>
</div>""")


def engine_cards() -> None:
    cols_n = 5
    for group in GROUPS:
        st.markdown(f'<div class="so-group">{html.escape(group["name"])}</div>'
                    + (f'<div class="so-gnote">{html.escape(group["note"])}</div>' if group["note"] else ""),
                    unsafe_allow_html=True)
        engines = group["engines"]
        for start in range(0, len(engines), cols_n):
            cols = st.columns(cols_n)
            for col, engine in zip(cols, engines[start:start + cols_n]):
                with col:
                    try:
                        st.markdown(render_card(engine), unsafe_allow_html=True)
                    except Exception as e:  # 카드 하나가 깨져도 나머지는 그대로 보입니다
                        st.markdown(f'<div class="so-err">{html.escape(engine.get("name", "엔진"))} 카드를 그리지 못했습니다.'
                                    f'<br>{html.escape(str(e))}</div>', unsafe_allow_html=True)
    note = "최근 수정일은 GitHub 기록을 1시간마다 다시 읽습니다. 최근 7일 이내에 고친 엔진은 날짜가 금색으로 표시됩니다."
    if date_error:
        note = f"GitHub 기록을 읽지 못해 최근 수정일을 표시하지 못했습니다. 엔진 바로 가기는 정상입니다. ({html.escape(date_error[:120])})"
    st.markdown(f'<div class="so-note">{note}</div>', unsafe_allow_html=True)


def office_page() -> None:
    header("STORY OFFICE")
    try:
        st.markdown(office_scene() + '<div class="so-hint">직원에게 마우스를 올리면 역할과 쓰는 엔진이 보입니다. '
                    '원형 테이블 사람들을 누르면 기획 회의로, 단독 책상 사람들을 누르면 그 엔진으로 갑니다.</div>', unsafe_allow_html=True)
    except Exception as e:  # 그림이 깨져도 아래 카드는 그대로 보입니다
        st.markdown(f'<div class="so-err">사무실 그림을 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)
    try:
        meeting_section()
    except Exception as e:
        st.markdown(f'<div class="so-err">기획 회의를 열지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)
    partner_card()
    st.markdown('<div id="so-tools" class="so-group" style="margin-top:40px">도구함</div>'
                '<div class="so-gnote">직원들이 쓰는 엔진입니다. 열기는 엔진 앱, 개발실은 그 엔진을 고치는 Claude 프로젝트입니다.</div>',
                unsafe_allow_html=True)
    engine_cards()


# ---------- SYSTEM: 성계 쇼룸 ----------
def system_page() -> None:
    header("STORY ENGINE SYSTEM")
    try:
        page = build_html(GROUPS, PARTNER, SYSTEM_PROJECT)   # 이 앱이 직접 만든 HTML만 넣습니다
        if hasattr(st, "iframe"):            # Streamlit 새 방식
            st.iframe(page, height=FRAME_HEIGHT)
        else:                                # 예전 Streamlit 대비
            components.html(page, height=FRAME_HEIGHT)
        st.markdown('<div class="so-hint">행성을 누르면 그 엔진이 열립니다. 행성 위에 마우스를 올리면 전체가 잠시 멈추고 설명이 보입니다. '
                    '가운데 구체를 누르면 시스템 전체를 다루는 STORY ENGINE SYSTEM 개발실이 열립니다.</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="so-err">성계 그림을 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)


nav = st.navigation(
    [st.Page(office_page, title="OFFICE", url_path="office", default=True),
     st.Page(system_page, title="SYSTEM", url_path="system")],
    position="top",
)
nav.run()
