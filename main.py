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
import storage
import works

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
.so-work { background:var(--glacier); border:1px solid var(--line); border-radius:6px; padding:12px 14px; margin:8px 0 2px; }
.so-work .t { font-size:16px; font-weight:900; color:var(--ink); }
.so-work .m { font-size:12px; color:var(--muted); margin-left:6px; }
.so-work .now { font-size:12.5px; color:var(--ink); margin:4px 0 8px; }
.so-work .now b { color:var(--gold); }
.so-steps { display:flex; flex-wrap:wrap; gap:4px; align-items:center; }
.so-step { font-size:11.5px; padding:3px 8px; border:1px solid var(--line); border-radius:3px; color:var(--muted) !important;
  text-decoration:none !important; background:#FFFFFF; }
.so-step.done { background:var(--yale); border-color:var(--yale); color:#FFFFFF !important; }
.so-step.doing { background:var(--gold); border-color:var(--gold); color:var(--ink) !important; font-weight:700; }
.so-arrow { font-size:10px; color:var(--line); }
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
.so-src { display:inline-block; font-size:10.5px; font-weight:700; border-radius:3px; padding:0 5px; margin-left:2px; text-decoration:none !important; vertical-align:middle; }
.so-src.ok { background:#E8F0F5; color:var(--yale) !important; border:1px solid #C8D6DD; }
.so-src.q { background:#F7FBFC; color:var(--muted); border:1px solid #C8D6DD; }
.so-src.no { background:#F3F3F3; color:#9AA5AD; border:1px dashed #C8D6DD; }
.so-weak { color:#9AA5AD; }
.so-off { opacity:.55; } .so-excl { font-size:11.5px; font-weight:700; color:#8A1F1F; margin-top:2px; }
.so-verdict { font-size:12px; font-weight:900; border-radius:4px; padding:2px 8px; vertical-align:middle; margin-left:6px; }
.so-verdict.go { background:#E6F2EA; color:#1F6B3A; } .so-verdict.conditional { background:#FBF3E2; color:#8A5A00; } .so-verdict.nogo { background:#F8E7E7; color:#8A1F1F; }
.so-cand { border-left:3px solid var(--line); padding:6px 10px; margin:6px 0; font-size:13px; line-height:1.55; }
.so-seed { margin-top:6px; font-weight:700; color:var(--yale); font-size:14px; }
.so-cand.so-chosen { border-left-color:var(--gold); background:#FFFBF2; }
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
    """직원 두 명(소재 발굴·판별)은 기획 회의로, 나머지 자리는 각 엔진으로 연결됩니다."""
    seats, taken = [], {}
    for key, r in staff.STAFF.items():
        taken[r["desk"]] = key
        seats.append(seat_html(r["desk"], r["title"], "아이디어 판별 · 기획 회의", "#so-meeting"))
    for e in all_engines:
        d = e.get("desk")
        if d in DESKS and d not in taken:
            sub = ("쓰는 엔진 · " + e["short"]) if e["url"] else "앱 없음"
            seats.append(seat_html(d, e["name"], sub, e["url"]))
    seats.append(seat_html("partner", PARTNER["name"], "열기" if PARTNER["url"] else "주소 대기", PARTNER["url"]))
    seats.append(seat_html("boss", "MR. MOON", "결재석 · 넘길 아이디어를 고릅니다", "#so-meeting"))
    return ('<div class="so-office"><img src="app/static/office.webp" alt="STORY OFFICE">' + "".join(seats) + "</div>")


# ---------- 기획 회의 ----------
def _secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "") or "")
    except Exception:  # secrets 파일이 없을 때
        return ""


@st.cache_resource
def _archive():
    """R2 보관함. Secrets가 없거나 연결이 안 되면 (None, 이유)."""
    try:
        arc = storage.from_secrets(_secret)
        if arc is None:
            return None, ""
        arc.check()
        return arc, ""
    except Exception as e:
        print(f"[STORY OFFICE] R2 연결 실패 {type(e).__name__}: {e}", flush=True)
        return None, f"{type(e).__name__}: {e}"


def _badge(mark: str) -> str:
    cls = {"통과": "ok", "맞음": "ok", "보완": "mid", "조건부": "mid", "불가": "no", "안 맞음": "no"}.get(mark, "mid")
    return f'<span class="so-badge {cls}">{html.escape(mark or "")}</span>'


def render_scan(result: dict, scan_id: str = "", genre: str = "", ui: str = "now") -> None:
    src = {x["id"]: x for x in result["sources"]}
    items = result["items"]
    yes = [i for i in items if i["has_idea"]]
    st.markdown(f'<div class="so-gnote" style="margin:10px 0 6px">소재 {len(items)}개 중 <b>이야기 있음 {len(yes)}개</b> · '
                f'검색 {result["searches"]}회' + (f' · 출처 없는 소재 {result["dropped"]}개 버림' if result.get("dropped") else "") + '</div>',
                unsafe_allow_html=True)
    idea_url = ENGINE_BY_SHORT.get("IDEA", {}).get("url")
    arc, _err = _archive()
    decided = {}
    if arc and scan_id:
        try:
            decided = arc.decided(genre, scan_id)
        except Exception as e:
            st.caption(f"지난 결정 기록을 읽지 못했습니다. {e}")
    for n, it in enumerate(items):
        links = " ".join(f'<a class="so-src ok" href="{html.escape(src[i]["url"])}" target="_blank" title="{html.escape(src[i]["title"])}">출처{k}</a>'
                         for k, i in enumerate(it.get("ids", []), 1) if i in src)
        badge = '<span class="so-verdict go">있음</span>' if it["has_idea"] else '<span class="so-verdict nogo">없음</span>'
        if it["name"] in decided:
            badge += f' <span class="so-badge {"ok" if decided[it["name"]] == "넘김" else "no"}">{decided[it["name"]]}</span>'
        if it["has_idea"]:
            body = (f'<div class="so-seed">{html.escape(it["seed"])}</div>'
                    f'<div class="so-gnote" style="margin:4px 0 0">결핍·상실 · {html.escape(it["who"])}<br>원하는 것 · {html.escape(it["want"])} / '
                    f'막는 것 · {html.escape(it["block"])}<br>역전 · {html.escape(it["twist"])}'
                    + (f'<br>장르의 재미 · {html.escape(it["genre_core"])}' if it.get("genre_core") else "") + '</div>')
        else:
            body = f'<div class="so-gnote" style="margin:4px 0 0">빠진 조건 · {html.escape(", ".join(it["missing"]))}</div>'
        st.markdown(clean(f"""
<div class="so-cand{' so-chosen' if it['has_idea'] else ''}">
  <div>{badge} <b>{html.escape(it["name"])}</b> <span class="so-gnote">{html.escape(it.get("where_when", ""))}</span> {links}</div>
  <div style="margin-top:4px">{html.escape(it["fact"])}</div>{body}
</div>"""), unsafe_allow_html=True)
        if it["has_idea"]:
            with st.expander(f"Idea Engine으로 넘기기 · {it['name']}"):
                st.caption("복사 버튼으로 복사해 Idea Engine STEP 1의 '원본 아이디어' 칸에 붙여 넣으면 됩니다. 제목·장르는 직접 정하십시오.")
                st.code(staff.idea_engine_input(it), language=None)
                if idea_url:
                    st.link_button("Idea Engine 열기", idea_url)
                if arc and scan_id:
                    st.caption("넘김과 버림을 남기면 이 장르 담당이 다음 판별 때 읽고, 같은 소재는 다시 가져오지 않습니다.")
                    reason = st.text_input("버리는 이유 (선택)", key=f"why_{ui}_{scan_id}_{n}",
                                           placeholder="예: 이미 다큐로 나옴 / 너무 지역적")
                    c1, c2 = st.columns(2)
                    for col, label in ((c1, "넘김"), (c2, "버림")):
                        if col.button(label, key=f"{label}_{ui}_{scan_id}_{n}", use_container_width=True):
                            try:
                                arc.record(genre, scan_id, it, label, reason if label == "버림" else "")
                                st.rerun()
                            except Exception as e:
                                st.error(f"기록하지 못했습니다. {e}")
    all_text = "\n\n".join(f"■ {it['name']} ({'있음' if it['has_idea'] else '없음'})\n{it['fact']}\n"
                            + (staff.idea_engine_input(it) if it["has_idea"] else "빠진 조건: " + ", ".join(it["missing"]))
                            + "\n출처: " + " ".join(src[i]["url"] for i in it.get("ids", []) if i in src) for it in items)
    st.download_button("목록 전체를 텍스트로 받기", all_text, file_name=f"STORY_OFFICE_소재판별_{datetime.now(KST):%Y%m%d_%H%M}.txt", key=f"dl_{ui}_{scan_id}")


def meeting_section() -> None:
    st.markdown('<div id="so-meeting" class="so-group">아이디어 판별</div>'
                '<div class="so-gnote">버튼을 누를 때만 일합니다. 소재 발굴 담당이 전 세계 현실 소재 5~8개를 찾고, 판별 담당이 소재마다 '
                '① 결핍·상실을 가진 사람 ② 원하는 것과 막는 것 ③ 역전이 서는지만 가립니다. 장르 담당을 고르면 그 장르만의 자료처를 뒤지고 ④ 그 장르의 재미까지 봅니다. 이야기를 지어내지 않습니다. '
                '키우는 일은 Idea Engine이 합니다.</div>', unsafe_allow_html=True)
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

    arc, arc_err = _archive()
    if arc:
        st.caption("기록 보관함(R2) 연결됨 · 판별 결과와 넘김·버림이 저장됩니다.")
    elif arc_err:
        st.warning(f"기록 보관함(R2)에 연결하지 못했습니다. Secrets의 R2 값 네 개를 확인해 주십시오. ({arc_err})")
    else:
        st.caption("기록 보관함(R2) 없이 돌아가는 중입니다. 판별 결과는 앱이 다시 시작되면 사라집니다.")

    jobs = _jobs()
    running = any(j["status"] == "running" for j in jobs.values())
    with st.form("meeting"):
        genre = st.selectbox("담당 장르", ["장르 없이 넓게"] + list(staff.GENRE_DESKS),
                             help="장르 담당은 그 장르의 재미가 바로 생길 현실을 자기만의 곳에서 찾고, 그 장르의 재미가 서는지까지 함께 봅니다.")
        direction = st.text_input("방향 한 줄 (비워도 됩니다)",
                                  placeholder="예: 베트남 / 사라지는 직업 / 일본 지방 소도시")
        go = st.form_submit_button("소재 찾고 판별하기", type="primary", disabled=running)
    if running:
        st.caption("판별이 진행 중이라 끝난 뒤에 다시 시작할 수 있습니다.")
    if go and not running:
        jid = _start_meeting(api_key, direction, "" if genre.startswith("장르 없이") else genre, arc)
        st.session_state["job_id"] = jid
        st.rerun()

    # 진행 중이거나 가장 최근 회의 (화면을 닫았다 다시 열어도 이어집니다)
    jid = st.session_state.get("job_id") or (max(jobs, key=lambda k: jobs[k]["started"]) if jobs else None)
    job = jobs.get(jid) if jid else None
    if job and job["status"] == "running":
        _progress_view(jid)
    elif job and job["status"] == "error":
        st.error(f"판별 중 문제가 생겼습니다: {job['error']}")
        with st.expander("진행 기록"):
            st.code("\n".join(job["log"]), language=None)
    elif job and job["status"] == "done":
        st.caption(f"시작 {job['started_label']} · {job['elapsed']} 소요 · {job.get('genre') or '장르 없이'}"
                   + (f" · 방향: {job['direction']}" if job["direction"] else ""))
        if job.get("save_error"):
            st.caption(f"보관함에 저장하지 못했습니다. {job['save_error']}")
        try:
            render_scan(job["result"], jid, job.get("genre", ""))
        except Exception as e:
            st.markdown(f'<div class="so-err">결과를 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)
    if arc:
        past_scans(arc)


def past_scans(arc) -> None:
    try:
        keys = arc.list_scans()
    except Exception as e:
        st.caption(f"지난 판별 목록을 읽지 못했습니다. {e}")
        return
    if not keys:
        return
    def label(k: str) -> str:   # scans/20261107_0130_ab12cd34.json
        d = k.split("/")[-1][:13]
        return f"{d[4:6]}-{d[6:8]} {d[9:11]}:{d[11:13]}"
    with st.expander(f"지난 판별 다시 보기 ({len(keys)}건)"):
        key = st.selectbox("판별 고르기", keys, format_func=label, label_visibility="collapsed")
        data = arc.load_scan(key) if key else None
        if data:
            st.caption(f"{data.get('genre') or '장르 없이'}" + (f" · 방향: {data['direction']}" if data.get("direction") else ""))
            render_scan(data["result"], data["id"], data.get("genre", ""), ui="past")


# ---------- 회의는 서버가 따로 끝까지 진행합니다 ----------
@st.cache_resource
def _jobs() -> dict:
    """앱이 살아 있는 동안 회의 기록을 보관합니다 (화면 연결과 무관)."""
    return {}


def _log(job: dict, msg: str) -> None:
    line = f"{datetime.now(KST):%H:%M:%S} {msg}"
    job["log"].append(line)
    print(f"[STORY OFFICE] {line}", flush=True)   # Streamlit 로그에도 남김


def _start_meeting(api_key: str, direction: str, genre: str = "", arc=None) -> str:
    import threading
    import traceback
    import uuid

    jobs = _jobs()
    jid = uuid.uuid4().hex[:8]
    now = datetime.now(KST)
    job = {"status": "running", "log": [], "result": None, "error": "", "started": now.timestamp(),
           "started_label": f"{now:%m-%d %H:%M}", "elapsed": "", "direction": direction, "genre": genre}
    jobs[jid] = job
    for old in sorted(jobs, key=lambda k: jobs[k]["started"])[:-5]:   # 최근 5건만 보관
        jobs.pop(old, None)

    def work():
        import anthropic
        _log(job, f"시작 · {genre or '장르 없이'} · 방향: {direction or '자유'}")
        try:
            client = anthropic.Anthropic(api_key=api_key)
            memory = ""
            if arc:
                try:
                    memory = storage.memory_note(arc.decisions(genre))
                except Exception as e:
                    _log(job, f"지난 기록을 읽지 못해 기록 없이 진행합니다 ({e})")
            result = staff.run_scan(client, direction, progress=lambda m: _log(job, m), genre=genre, memory=memory)
            job["result"] = result
            job["status"] = "done"
            _log(job, f"끝 · 이야기 있음 {sum(i['has_idea'] for i in result['items'])}/{len(result['items'])} · 검색 {result['searches']}회")
        except Exception as e:
            job["error"] = f"{type(e).__name__}: {e}"
            job["status"] = "error"
            _log(job, "오류 " + job["error"])
            print(traceback.format_exc(), flush=True)
        finally:
            sec = int(datetime.now(KST).timestamp() - job["started"])
            job["elapsed"] = f"{sec // 60}분 {sec % 60}초"
        if arc and job["status"] == "done":
            try:
                _log(job, "보관함 저장 " + arc.save_scan(jid, job))
            except Exception as e:
                job["save_error"] = str(e)
                _log(job, f"보관함 저장 실패 {e}")

    threading.Thread(target=work, daemon=True).start()
    return jid


@st.fragment(run_every=3)
def _progress_view(jid: str) -> None:
    job = _jobs().get(jid)
    if not job:
        return
    if job["status"] != "running":
        st.rerun()   # 끝났으면 화면 전체를 다시 그려 결과를 보여줍니다
    sec = int(datetime.now(KST).timestamp() - job["started"])
    with st.status(f"진행 중 · {sec // 60}분 {sec % 60}초", expanded=True, state="running"):
        for line in job["log"]:
            st.write(line)
        st.caption("화면을 닫거나 다른 일을 하셔도 서버에서 끝까지 진행됩니다. 다시 열면 결과가 여기 나옵니다.")


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
        st.markdown(office_scene() + '<div class="so-hint">사람에게 마우스를 올리면 맡은 일이 보입니다. 소재 발굴 담당과 판별 담당은 아래 아이디어 판별로, '
                    '나머지 자리는 그 엔진으로 연결됩니다.</div>', unsafe_allow_html=True)
    except Exception as e:  # 그림이 깨져도 아래 카드는 그대로 보입니다
        st.markdown(f'<div class="so-err">사무실 그림을 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)
    try:
        meeting_section()
    except Exception as e:
        st.markdown(f'<div class="so-err">기획 회의를 열지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)
    try:
        works_board()
    except Exception as e:
        st.markdown(f'<div class="so-err">작품 현황판을 열지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)
    partner_card()
    st.markdown('<div id="so-tools" class="so-group" style="margin-top:40px">도구함</div>'
                '<div class="so-gnote">직원들이 쓰는 엔진입니다. 열기는 엔진 앱, 개발실은 그 엔진을 고치는 Claude 프로젝트입니다.</div>',
                unsafe_allow_html=True)
    engine_cards()


# ---------- 작품 현황판 ----------
def _work_card(w: dict) -> str:
    code, state = works.current(w)
    now = ("<b>완성</b>" if state == "완성" else
           f'지금 <b>{works.STAGE_LABEL[code]}</b> {state}' + (f' · {html.escape(w["note"].get(code, ""))}' if w["note"].get(code) else ""))
    chips = []
    for s in w["stages"]:
        cls = {"완료": "done", "진행": "doing"}.get(w["state"].get(s), "")
        url = ENGINE_BY_SHORT.get(s, {}).get("url")
        tip = html.escape(w["note"].get(s, "") or w["state"].get(s, ""))
        chip = (f'<a class="so-step {cls}" href="{html.escape(url)}" target="_blank" title="{tip}">{works.STAGE_LABEL[s]}</a>' if url
                else f'<span class="so-step {cls}" title="{tip}">{works.STAGE_LABEL[s]}</span>')
        chips.append(chip)
    meta = " · ".join(x for x in (w["format"], w["genre"], f'고친 날 {w["updated"][:10]}') if x)
    return (f'<div class="so-work"><span class="t">{html.escape(w["title"])}</span><span class="m">{html.escape(meta)}</span>'
            f'<div class="now">{now}</div><div class="so-steps">{"<span class=so-arrow>▶</span>".join(chips)}</div></div>')


def works_board() -> None:
    if not st.session_state.get("office_unlocked"):
        return   # 작품 목록은 비밀번호를 연 뒤에만 보입니다
    st.markdown('<div id="so-works" class="so-group">작품 현황판</div>'
                '<div class="so-gnote">엔진으로 개발 중인 작품과 단계입니다. 남색은 끝난 단계, 금색은 진행 중인 단계입니다. '
                '단계를 누르면 그 엔진이 열립니다. 엔진은 기록을 남기지 않으므로 단계는 여기서 직접 표시합니다.</div>',
                unsafe_allow_html=True)
    arc, _err = _archive()
    if not arc:
        st.info("작품 현황판은 기록 보관함(R2)에 저장됩니다. 보관함이 연결되면 열립니다.")
        return
    all_works = arc.load_works()
    shown = sorted((w for w in all_works if not w.get("archived")), key=lambda w: w["updated"], reverse=True)

    def save(msg: str) -> None:
        arc.save_works(all_works)
        st.toast(msg)
        st.rerun()

    if not shown:
        st.caption("아직 등록한 작품이 없습니다. 아래 '작품 추가'에서 넣으십시오.")
    for w in shown:
        st.markdown(_work_card(w), unsafe_allow_html=True)
        if st.session_state.get("work_reset") == w["id"]:   # 위젯을 그리기 전에 비워야 합니다
            cur = works.current(w)[0] or w["stages"][0]
            st.session_state["wst_" + w["id"]] = cur
            st.session_state["wsv_" + w["id"]] = w["state"].get(cur, "대기")
            st.session_state["wnt_" + w["id"]] = ""
            st.session_state.pop("work_reset")
        with st.expander(f"단계 표시 · {w['title']}"):
            c1, c2 = st.columns([3, 2])
            if f"wst_{w['id']}" not in st.session_state:
                cur = works.current(w)[0] or w["stages"][0]
                st.session_state[f"wst_{w['id']}"] = cur
                st.session_state[f"wsv_{w['id']}"] = w["state"].get(cur, "대기")
            stage = c1.selectbox("단계", w["stages"], format_func=lambda s: works.STAGE_LABEL[s], key=f"wst_{w['id']}")
            state = c2.radio("상태", works.STATES, horizontal=True, key=f"wsv_{w['id']}")
            note = st.text_input("메모 (선택)", key=f"wnt_{w['id']}", placeholder="예: v3.5 / 2막 다시 / Rewrite 점수 78")
            b1, b2 = st.columns([1, 1])
            if b1.button("저장", key=f"wsave_{w['id']}", type="primary", use_container_width=True):
                works.set_stage(w, stage, state, note)
                st.session_state["work_reset"] = w["id"]   # 다음 화면에서 칸을 비웁니다
                save(f"{w['title']} · {works.STAGE_LABEL[stage]} {state}")
            if b2.button("목록에서 내리기", key=f"warc_{w['id']}", use_container_width=True):
                w["archived"] = True
                w["updated"] = works._now()
                save(f"{w['title']} 목록에서 내림")
            log = [x for x in w["log"] if x["stage"]][-6:]
            if log:
                st.caption("최근 기록")
                for x in reversed(log):
                    st.caption(f"{x['date']} · {works.STAGE_LABEL.get(x['stage'], '')} {x['state']}" + (f" · {x['note']}" if x["note"] else ""))

    if st.session_state.pop("work_new_reset", False):
        st.session_state["wnew_title"] = st.session_state["wnew_genre"] = ""
    with st.expander("작품 추가"):
        title = st.text_input("제목", key="wnew_title")
        c1, c2 = st.columns(2)
        fmt = c1.selectbox("포맷", list(works.FORMATS), key="wnew_fmt")
        genre = c2.text_input("장르 (선택)", key="wnew_genre", placeholder="예: 로맨틱 코미디")
        stages = st.multiselect("거칠 엔진 단계", works.STAGE_ORDER, default=works.FORMATS[fmt], key=f"wnew_stages_{fmt}",
                                format_func=lambda s: works.STAGE_LABEL[s],
                                help="포맷에 맞춰 처음 채워 두었습니다. Rewrite·Revise·번역처럼 필요한 단계를 더하거나 빼십시오.")
        if st.button("등록", key="wnew_go", type="primary"):
            if not title.strip() or not stages:
                st.warning("제목과 단계를 하나 이상 넣어 주십시오.")
            else:
                all_works.append(works.new_work(title, fmt, genre, stages))
                st.session_state["work_new_reset"] = True
                save(f"{title.strip()} 등록")
    gone = [w for w in all_works if w.get("archived")]
    if gone:
        with st.expander(f"내린 작품 ({len(gone)}편)"):
            for w in gone:
                c1, c2 = st.columns([4, 1])
                c1.caption(f"{w['title']} · {w['format']} · 내린 날 {w['updated'][:10]}")
                if c2.button("되돌리기", key=f"wback_{w['id']}"):
                    w["archived"] = False
                    w["updated"] = works._now()
                    save(f"{w['title']} 되돌림")


# ---------- SYSTEM: 성계 쇼룸 ----------
def system_page() -> None:
    header("STORY ENGINE SYSTEM")
    try:
        page = build_html(GROUPS, PARTNER, SYSTEM_PROJECT, STREAMLIT_ADMIN)   # 이 앱이 직접 만든 HTML만 넣습니다
        if hasattr(st, "iframe"):            # Streamlit 새 방식
            st.iframe(page, height=FRAME_HEIGHT)
        else:                                # 예전 Streamlit 대비
            components.html(page, height=FRAME_HEIGHT)
        st.markdown('<div class="so-hint">행성을 누르면 그 엔진이 열립니다. 행성 위에 마우스를 올리면 전체가 잠시 멈추고 설명이 보입니다. '
                    '가운데 구체를 누르면 시스템 전체를 다루는 STORY ENGINE SYSTEM 개발실이, 오른쪽 아래 APP CONTROL을 누르면 Streamlit 앱 관리(리부트)가 열립니다.</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="so-err">성계 그림을 그리지 못했습니다. {html.escape(str(e))}</div>', unsafe_allow_html=True)


nav = st.navigation(
    [st.Page(office_page, title="OFFICE", url_path="office", default=True),
     st.Page(system_page, title="SYSTEM", url_path="system")],
    position="top",
)
nav.run()
