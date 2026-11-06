"""STORY OFFICE 직원들 — 기획 회의를 실제로 엽니다.

버튼을 누를 때만 일합니다(그때만 Claude API 사용량이 듭니다).
1) 발제 담당이 아이디어 한 장을 씁니다.
2) 구조·인물·장르·반대 담당, 포맷 담당, 시장 담당이 각자 따로 의견을 냅니다
   (서로의 의견을 보지 않고 아이디어 한 장과 자기 직무만 봅니다).
3) 회의록 담당이 정리하고, 어느 책상(엔진)으로 보낼지 배정을 권고합니다.
   최종 결정은 Mr. MOON이 합니다. 회의는 아이디어를 고쳐 쓰지 않습니다.

직원의 직무는 아래 ROLES 의 "brief" 를 고치면 바뀝니다.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

MODEL = "claude-sonnet-4-6"   # 엔진들과 같은 모델

# Idea Engine STEP 1 선택 목록 (Idea-Engine/main.py 에서 그대로 옮김)
GENRES = ["범죄/스릴러", "드라마", "액션", "로맨스", "코미디", "호러/공포", "SF", "판타지",
          "코지 미스터리", "느와르", "사회파"]
MARKETS = ["한국 + 글로벌", "한국 (국내)", "일본 (인디·공동제작·리메이크 트랙)", "인도네시아 (JAFF 트랙)",
           "인도네시아 + 한국 OTT (Netflix SEA)", "베트남 (극장·OTT)", "베트남 + 한국 공동제작",
           "한국 + 베트남", "한국 + 일본 공동제작", "글로벌 (해외)"]
FORMATS = ["장편 영화", "OTT 시리즈", "미니시리즈", "숏폼 드라마", "웹소설", "웹툰"]

# ── 직원 명단 ──────────────────────────────────────────────
# desk: 사무실 그림 자리(engines.DESKS), group: 회의에서의 위치, tools: 쓰는 엔진(engines 의 short)
ROLES = {
    "pitch":     {"title": "발제 담당", "desk": "idea", "group": "round", "tools": [],
                  "brief": "매일 아이디어 한 장을 써서 회의에 올린다."},
    "structure": {"title": "구조 담당", "desk": "creator", "group": "round", "tools": [],
                  "brief": "이 아이디어로 3막이 서는지 본다. 1막 전환점, 중간점, 2막 끝 위기, 클라이맥스가 "
                           "각각 구체적인 사건으로 나오는지 하나씩 짚는다. 없는 지점은 없다고 말한다."},
    "character": {"title": "인물 담당", "desk": "writer", "group": "round", "tools": [],
                  "brief": "주인공이 무엇을 원하고 무엇이 모자라며 끝에서 어떻게 달라지는지, 주인공이 이 사건에 "
                           "매달려야 할 개인적인 이유가 있는지, 적대자가 누구인지 본다."},
    "genre":     {"title": "장르 담당", "desk": "rewrite", "group": "round", "tools": [],
                  "brief": "아이디어에 적힌 장르의 규칙으로 본다. 스릴러면 긴장 장면, 호러면 공포 장면, 코미디면 "
                           "웃음 장면, 로맨스면 감정이 터지는 장면이 몇 개나 떠오르는지 구체적으로 세고, 장르가 "
                           "흔들리는 지점을 짚는다."},
    "devil":     {"title": "반대 담당", "desk": "revise", "group": "round", "tools": [],
                  "brief": "이 아이디어가 실패할 이유만 찾는다. 칭찬하지 않는다. 이미 본 듯한 설정, 2막에서 "
                           "무너질 지점, 관객이 먼저 알아챌 반전, 제작이 어려운 요소를 짚는다."},
    "film":      {"title": "영화 담당", "desk": "series", "group": "format", "tools": ["IDEA", "CREATOR", "WRITER", "REWRITE", "REVISE"],
                  "format": "장편 영화", "brief": "100~120분 한국 상업 장편 영화로 될 수 있는지 본다."},
    "series":    {"title": "시리즈 담당", "desk": "webnovel", "group": "format", "tools": ["CREATOR", "SERIES"],
                  "format": "OTT 시리즈", "brief": "사건이 회차로 쪼개지고 시즌 질문이 서는 OTT 시리즈가 될 수 있는지 본다."},
    "novel":     {"title": "소설 담당", "desk": "novel", "group": "format", "tools": ["WEBNOVEL", "CREATOR", "NOVEL"],
                  "format": "웹소설", "brief": "연재 웹소설 또는 장편소설로 펼칠 수 있는지 본다."},
    "wuxia":     {"title": "무협 담당", "desk": "wuxia", "group": "format", "tools": ["WUXIA"],
                  "format": None, "brief": "무협(정통·회빙환·시스템·학원 무협)으로 옮길 여지가 있는지 본다."},
    "shortform": {"title": "숏폼 담당", "desk": "shortform", "group": "format", "tools": ["SHORTFORM"],
                  "format": "숏폼 드라마", "brief": "1~2분 × 80~100화 세로형 숏폼 드라마로, 1화부터 훅이 서고 매화 끝에 "
                                                  "다음 화를 누르게 만들 수 있는지 본다."},
    "fmv":       {"title": "인터랙티브 담당", "desk": "fmv", "group": "format", "tools": ["FMV"],
                  "format": None, "brief": "관객의 선택으로 갈라지는 실사 인터랙티브 드라마가 될 수 있는지, 갈림길이 "
                                         "될 장면이 있는지 본다."},
    "market_kr": {"title": "국내 시장 담당", "desk": "english", "group": "market", "tools": [],
                  "brief": "한국 극장과 OTT 기준으로 시장성을 본다. 비슷한 한국 작품, 타깃 관객, 대략의 제작 규모."},
    "market_os": {"title": "해외 시장 담당", "desk": "japanese", "group": "market", "tools": ["ENGLISH", "JAPANESE"],
                  "brief": "일본(인디·공동제작·리메이크), 인도네시아, 베트남 트랙 기준으로 해외 시장성을 본다."},
}

# 배정 선택지와 그 길
ASSIGNMENTS = {
    "Idea Engine":        {"desk": "film", "path": ["IDEA"], "note": "아직 진단이 필요함"},
    "Creator 직행":        {"desk": "film", "path": ["CREATOR"], "note": "장편 영화로 바로 기획"},
    "Creator → Series":   {"desk": "series", "path": ["CREATOR", "SERIES"], "note": "Series는 Creator 결과 파일을 받음"},
    "Creator → Novel":    {"desk": "novel", "path": ["CREATOR", "NOVEL"], "note": "Novel은 Creator 결과 파일을 받음"},
    "WebNovel 직행":       {"desk": "novel", "path": ["WEBNOVEL"], "note": ""},
    "Wuxia 직행":          {"desk": "wuxia", "path": ["WUXIA"], "note": ""},
    "Shortform 직행":      {"desk": "shortform", "path": ["SHORTFORM"], "note": ""},
    "FMV 직행":            {"desk": "fmv", "path": ["FMV"], "note": ""},
    "보류":                {"desk": None, "path": [], "note": ""},
    "폐기":                {"desk": None, "path": [], "note": ""},
}

# 배정된 엔진 첫 화면에 넣을 칸 (각 엔진 main.py 의 첫 입력 화면에서 옮김)
ENGINE_INPUTS = {
    "IDEA":      ["제목", "장르", "타겟 시장", "선호 포맷", "원본 아이디어"],
    "CREATOR":   ["원본 아이디어"],
    "WEBNOVEL":  ["가제", "로그라인", "시놉시스", "세계관/배경", "주요 인물과 각자의 목표"],
    "WUXIA":     ["가제", "로그라인", "무협 유형", "주인공", "세계관/문파"],
    "SHORTFORM": ["주인공 설정", "핵심 비밀 2~3개", "메인 악역 설정", "시즌 질문"],
    "FMV":       ["작품 제목", "주인공 시점", "한 줄 훅", "소재 키워드"],
}

HOUSE_RULES = (
    "공통 규칙: 한국어로 쓴다. 추상적인 개념어 대신 구체적인 인물 이름, 장소, 시각, 행동, 사건으로 말한다. "
    "점수를 매기지 않는다. 칭찬으로 시작하지 않는다. 대시 기호(— –)를 쓰지 않는다. "
    "실제로 존재하는지 확인하지 않은 작품·통계·기사를 사실처럼 쓰지 않는다."
)


# ── Claude 호출 ───────────────────────────────────────────
def _text(resp) -> str:
    return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text").strip()


def _json(text: str) -> dict:
    """응답에서 첫 JSON 객체를 꺼냅니다."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("응답에서 JSON을 찾지 못했습니다.")
    return json.loads(m.group(0))


def _clean(obj):
    """대시 기호를 쉼표로 바꿉니다 (블루진 문서 규칙)."""
    if isinstance(obj, str):
        return re.sub(r"\s*[—–]\s*", ", ", obj)
    if isinstance(obj, list):
        return [_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    return obj


def _ask(client, system: str, user: str, max_tokens: int, search: bool = False) -> dict:
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system,
                  messages=[{"role": "user", "content": user}])
    if search:
        try:
            resp = client.messages.create(**kwargs, tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}])
            return _clean(_json(_text(resp)))
        except Exception:
            pass  # 검색이 안 되면 검색 없이 다시 씁니다
    resp = client.messages.create(**kwargs)
    return _clean(_json(_text(resp)))


# ── 1. 발제 ─────────────────────────────────────────────
def write_pitch(client, direction: str = "", no: int = 1, date: str = "") -> dict:
    system = (
        f"너는 BLUE JEANS PICTURES 기획실의 {ROLES['pitch']['title']}다. {ROLES['pitch']['brief']} {HOUSE_RULES}\n"
        "요즘 소식이나 사회 현상에서 출발점을 찾을 수 있으면 웹 검색으로 확인하고, 확인한 것만 근거로 적는다."
    )
    user = (
        "아이디어 한 장을 아래 JSON 형식으로만 답하라. 설명 문장 없이 JSON만.\n"
        f"장르는 {GENRES} 중 하나, 타겟 시장은 {MARKETS} 중 하나, 선호 포맷은 {FORMATS} 중 하나로 고른다.\n"
        '{"title":"가제","genre":"","market":"","format":"","logline":"한두 문장",'
        '"raw_idea":"Idea Engine 원본 아이디어 칸에 그대로 붙일 문단. 주인공 이름과 나이, 직업, 장소, 첫 사건, 갈등이 커지는 방향을 6~9문장으로",'
        '"scenes":["핵심 장면 1 (장소, 시각, 인물의 행동이 보이게)","핵심 장면 2","핵심 장면 3"],'
        '"why_now":"왜 지금 이 이야기인가 2~3문장","references":["실제 존재를 확인한 작품명 (연도)"],'
        '"sources":["확인한 근거 자료 제목과 주소"]}\n'
        "확인하지 못한 레퍼런스와 근거는 빈 목록으로 둔다.\n"
        + (f"이번 발제 방향 (Mr. MOON 지시): {direction}" if direction.strip() else "이번 발제 방향: 자유")
    )
    idea = _ask(client, system, user, max_tokens=2500, search=True)
    idea["no"], idea["date"] = no, date
    for k in ("references", "sources", "scenes"):
        idea.setdefault(k, [])
    return idea


def _idea_sheet(idea: dict) -> str:
    scenes = "\n".join(f"{i}. {s}" for i, s in enumerate(idea.get("scenes", []), 1))
    return (f"[가제] {idea.get('title')}\n[장르] {idea.get('genre')}  [시장] {idea.get('market')}  [포맷] {idea.get('format')}\n"
            f"[로그라인] {idea.get('logline')}\n[원본 아이디어] {idea.get('raw_idea')}\n[핵심 장면]\n{scenes}\n"
            f"[왜 지금인가] {idea.get('why_now')}")


# ── 2. 각자 의견 ─────────────────────────────────────────
def _opinion(client, key: str, idea: dict) -> dict:
    r = ROLES[key]
    system = f"너는 BLUE JEANS PICTURES 기획 회의의 {r['title']}다. 직무: {r['brief']} {HOUSE_RULES}"
    if r["group"] == "format":
        shape = '{"fit":"맞음|조건부|안 맞음","one_line":"한 문장 판단","points":["근거 1","근거 2"]}'
    else:
        shape = '{"verdict":"통과|보완|불가","one_line":"한 문장 판단","points":["사건·장면 단위 지적 1","지적 2","지적 3"]}'
    user = (f"아래 아이디어를 네 직무로만 보고 JSON으로만 답하라. 지적은 최대 3개, 각 지적은 아이디어 속 구체적인 장면이나 "
            f"사건을 짚어서.\n형식: {shape}\n\n{_idea_sheet(idea)}")
    out = _ask(client, system, user, max_tokens=900)
    out["role"] = key
    return out


def attendees(idea: dict, full: bool) -> list[str]:
    round_table = [k for k, r in ROLES.items() if r["group"] == "round" and k != "pitch"]
    if full:
        return round_table + [k for k, r in ROLES.items() if r["group"] in ("format", "market")]
    fmt = idea.get("format", "")
    desk = next((k for k, r in ROLES.items() if r["group"] == "format" and r.get("format") == fmt), "film")
    return round_table + [desk, "market_kr"]


# ── 3. 회의록과 배정 ───────────────────────────────────────
def write_minutes(client, idea: dict, opinions: list[dict]) -> dict:
    lines = []
    for o in opinions:
        r = ROLES[o["role"]]
        mark = o.get("verdict") or o.get("fit") or ""
        lines.append(f"- {r['title']} [{mark}] {o.get('one_line', '')}\n  " + "\n  ".join(o.get("points", [])))
    system = (f"너는 BLUE JEANS PICTURES 기획 회의의 회의록 담당이다. 참석자 의견을 정리하고 다음 책상 배정을 권고한다. "
              f"아이디어를 고쳐 쓰지 않는다. 보완 과제는 작가가 직접 고칠 수 있게 무엇이 비었는지만 말한다. {HOUSE_RULES}")
    user = (
        "아래 아이디어와 참석자 의견을 보고 JSON으로만 답하라.\n"
        f"배정(assignment)은 {list(ASSIGNMENTS)} 중 하나. 큰 과제가 두 개 이상 남았으면 'Idea Engine'. "
        "Series와 Novel은 Creator 결과 파일을 받으므로 'Creator → Series', 'Creator → Novel'로 쓴다.\n"
        "engine_input 은 배정된 길의 첫 엔진 입력 칸에 옮겨 넣을 값이다. 칸 이름은 다음을 따른다: "
        f"{json.dumps(ENGINE_INPUTS, ensure_ascii=False)}\n"
        '{"summary":"회의 결론 2~3문장","issues":["쟁점 1","쟁점 2"],"tasks":["보완 과제 1","보완 과제 2","보완 과제 3"],'
        '"assignment":"","reason":"판정을 가른 지적을 사건 단위로 1~2문장","alternative":"다른 길 한 문장 (없으면 빈 문자열)",'
        '"engine_input":{"칸 이름":"값"}}\n\n'
        f"{_idea_sheet(idea)}\n\n[참석자 의견]\n" + "\n".join(lines)
    )
    out = _ask(client, system, user, max_tokens=2000)
    if out.get("assignment") not in ASSIGNMENTS:
        out["assignment"] = "Idea Engine"
    return out


def run_meeting(client, direction: str = "", full: bool = False, no: int = 1, date: str = "", progress=None) -> dict:
    """회의 전체. progress(문구) 로 진행 상황을 알립니다."""
    say = progress or (lambda _m: None)
    say("발제 담당이 아이디어를 쓰고 있습니다")
    idea = write_pitch(client, direction, no, date)
    who = attendees(idea, full)
    say("참석자가 각자 아이디어를 읽고 있습니다: " + ", ".join(ROLES[k]["title"] for k in who))
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {k: pool.submit(_opinion, client, k, idea) for k in who}
    opinions = []
    for k, f in futures.items():
        try:
            opinions.append(f.result())
        except Exception as e:  # 한 사람이 실패해도 회의는 계속
            opinions.append({"role": k, "verdict": "불참", "one_line": f"의견을 받지 못했습니다 ({type(e).__name__})", "points": []})
    say("회의록 담당이 정리하고 배정을 권고하고 있습니다")
    minutes = write_minutes(client, idea, opinions)
    return {"idea": idea, "opinions": opinions, "minutes": minutes, "full": full, "direction": direction}
