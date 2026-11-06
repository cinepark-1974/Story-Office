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

from engines import DESKS, GITHUB_OWNER, GROUPS, OFFICE_H, OFFICE_W, PARTNER
from system_view import FRAME_HEIGHT, build_html

KST = timezone(timedelta(hours=9))

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
.so-foot { display:flex; align-items:center; justify-content:space-between; gap:8px; border-top:1px solid var(--line); padding-top:10px; }
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
  <div class="so-meta">엔진 <b>{live}</b> / {len(all_engines)} 가동 중<br>{now:%Y-%m-%d %H:%M} 기준</div>
</div>"""), unsafe_allow_html=True)


# ---------- OFFICE: 사무실 그림 ----------
def seat_html(key: str, title: str, sub: str, url: str | None) -> str:
    l, t, r, b = DESKS[key]
    style = (f"left:{l / OFFICE_W * 100:.2f}%;top:{t / OFFICE_H * 100:.2f}%;"
             f"width:{(r - l) / OFFICE_W * 100:.2f}%;height:{(b - t) / OFFICE_H * 100:.2f}%;")
    tag = f'<span class="so-tag">{html.escape(title)}<small>{html.escape(sub)}</small></span>'
    below = " below" if t / OFFICE_H < 0.15 else ""   # 그림 맨 위쪽 자리는 이름표를 아래로
    if url:
        return f'<a class="so-seat link{below}" style="{style}" href="{html.escape(url)}" target="_blank">{tag}</a>'
    return f'<span class="so-seat{below}" style="{style}" tabindex="0">{tag}</span>'


def office_scene() -> str:
    seats = []
    for g in GROUPS:
        for e in g["engines"]:
            if e.get("desk") in DESKS:
                sub = g["name"] if e["url"] else f'{g["name"]} · 앱 없음'
                seats.append(seat_html(e["desk"], e["name"], sub, e["url"]))
    seats.append(seat_html("partner", PARTNER["name"], "열기" if PARTNER["url"] else "주소 대기", PARTNER["url"]))
    seats.append(seat_html("boss", "MR. MOON", "결재석 · 작품 보드에서 열립니다", None))
    return ('<div class="so-office"><img src="app/static/office.webp" alt="STORY OFFICE">' + "".join(seats) + "</div>")


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
    action = (f'<a class="so-go" href="{html.escape(engine["url"])}" target="_blank">열기</a>'
              if engine["url"] else '<span class="so-none">앱 없음</span>')
    return clean(f"""
<div class="so-card">
  <div class="so-name">{html.escape(engine["name"])}</div>
  <div class="so-desc">{html.escape(engine["desc"])}</div>
  <div class="so-foot">
    <div class="so-date{' fresh' if fresh else ''}">최근 수정<b>{label}</b></div>
    {action}
  </div>
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
        st.markdown(office_scene() + '<div class="so-hint">직원에게 마우스를 올리면 맡은 엔진이 보이고, 누르면 열립니다. '
                    '휴대폰에서는 아래 카드를 쓰시면 편합니다.</div>', unsafe_allow_html=True)
    except Exception as e:  # 그림이 깨져도 아래 카드는 그대로 보입니다
        st.markdown(f'<div class="so-err">사무실 그림을 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)
    partner_card()
    engine_cards()


# ---------- SYSTEM: 성계 쇼룸 ----------
def system_page() -> None:
    header("STORY ENGINE SYSTEM")
    try:
        page = build_html(GROUPS, PARTNER)   # 이 앱이 직접 만든 HTML만 넣습니다
        if hasattr(st, "iframe"):            # Streamlit 새 방식
            st.iframe(page, height=FRAME_HEIGHT)
        else:                                # 예전 Streamlit 대비
            components.html(page, height=FRAME_HEIGHT)
        st.markdown('<div class="so-hint">행성을 누르면 그 엔진이 열립니다. 행성 위에 마우스를 올리면 전체가 잠시 멈추고 설명이 보입니다. '
                    '가운데 구체에 마우스를 올리면 모든 엔진의 공통 설계가 보입니다.</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="so-err">성계 그림을 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)


nav = st.navigation(
    [st.Page(office_page, title="OFFICE", url_path="office", default=True),
     st.Page(system_page, title="SYSTEM", url_path="system")],
    position="top",
)
nav.run()
