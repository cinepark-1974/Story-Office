"""STORY OFFICE 직원 — Idea Engine 앞단의 아이디어 판별.

아이디어를 키우는 일은 Idea Engine이 합니다. 오피스는 그 앞에서
"이 현실 소재 안에 이야기가 있나, 없나"만 가려냅니다. AI가 로그라인·장면을 지어내지 않습니다.

  1. 소재 발굴 담당  전 세계 뉴스·보고서·판결·제도·직업·기술·사건을 검색해 현실 소재 5~8개를 가져온다.
                     영화·드라마 같은 기존 작품은 찾지 않는다. 실제 검색 주소가 없는 소재는 버린다.
  2. 판별 담당       소재마다 엔진의 최소 조건 세 가지만 본다.
                     ① 결핍 또는 상실을 가진 사람이 보이는가 (Idea:1270)
                     ② 그 사람이 원하는 것과 막는 것이 한 줄로 서는가 (Idea:114)
                     ③ 역전(BUT/EXCEPT)이 생기는가 (Creator:2614)
                     셋이 다 서면 '있음'(코드가 다시 확인), 하나라도 없으면 '없음'과 빠진 조건.

Claude 호출은 두 번(검색 포함 1번 + 판별 1번)뿐입니다.
"""

from __future__ import annotations

import json
import re
import threading

MODEL = "claude-sonnet-4-6"   # 엔진들과 같은 모델
SEARCH_TOOL_TYPES = ["web_search_20260318", "web_search_20250305"]   # 새 판부터 시도
_search_type: list[str] = []

# Idea Engine STEP 1 선택 목록 (Idea-Engine/main.py)
GENRES = ["범죄/스릴러", "드라마", "액션", "로맨스", "코미디", "호러/공포", "SF", "판타지",
          "코지 미스터리", "느와르", "사회파"]

HOUSE_RULES = (
    "공통 규칙: 한국어로 쓴다. 꾸미지 않는다. 형용사로 인물을 설명하지 않는다('정의감 강한', '상처를 가진' 금지, Creator:8156). "
    "대시 기호(— –)를 쓰지 않는다. 확인하지 않은 사실·수치를 만들지 않는다(Idea:86–89, 722). "
    "판단할 근거가 없으면 비워 둔다. 추측해서 채우지 않는다(Idea:2779)."
)

# ── 장르 담당 ─────────────────────────────────────────────
# where: 그 장르 담당이 소재를 찾는 곳(학습 방법) / core: 장르 재미의 본질 (Creator-Engine/prompt.py:3359–3370)
GENRE_DESKS = {
    "로맨틱 코미디": {"core": "주인공의 어긋남이 웃음과 설렘을 동시에 주는 것",
                  "where": "연애·결혼·동거 제도와 풍속의 변화, 데이팅 앱과 커뮤니티의 새 유행, 연애를 대신해 주는 이색 직업·서비스, 관계에 관한 설문·조사"},
    "스릴러":   {"core": "정보 비대칭이 긴장을 만드는 것",
                  "where": "판결 보도와 탐사 보도, 새로 등장한 사기·범죄 수법, 내부고발, 감시·보안 기술이 뚫린 사건"},
    "호러":     {"core": "규칙 위반이 주는 서늘함",
                  "where": "지역 괴담·민속 신앙·금기, 미해결 실종과 설명되지 않은 현상 보도, 버려진 장소와 폐쇄 공간에 얽힌 기록"},
    "드라마":   {"core": "관객이 '나라면 어떻게 할까'를 고민하게 만드는 것",
                  "where": "인물 인터뷰와 부고·회고 기사, 제도 변화로 삶의 갈림길에 선 사람들의 사연"},
    "코미디":   {"core": "자기 결함이 반복 사고를 만드는 것",
                  "where": "황당한 규제와 행정, 이색 뉴스와 동네 소동, 실수가 실수를 부른 실제 사건"},
    "액션":     {"core": "물리적 쾌감의 카타르시스",
                  "where": "특수 직업(구조대·경호·스턴트·특수청소), 밀수·국경 단속, 재난 현장 대응 기록"},
    "느와르":   {"core": "도덕적 모호함의 긴장",
                  "where": "조직범죄와 부패 보도, 법의 회색지대에서 일하는 직업, 배신과 거래가 드러난 사건"},
    "SF":       {"core": "아이디어가 감정을 움직이는 것",
                  "where": "새 기술 발표와 논문·특허, 기술 규제 논쟁, 기술이 사람의 관계를 바꾼 사례"},
    "미스터리": {"core": "관객이 추리에 참여하는 것",
                  "where": "미해결 사건, 설명되지 않는 우연, 밀실처럼 닫힌 상황에서 벌어진 실제 일"},
    "판타지":   {"core": "경이(wonder)가 테마로 작동하는 것",
                  "where": "민담·신화·전설, 역사 기록 속 기이한 사건, 사라진 풍습과 의례"},
    "시대극":   {"core": "시대가 인물의 운명이 되는 것",
                  "where": "역사 기록과 사료 속 잘 알려지지 않은 인물·사건, 시대가 바뀌며 사라진 직업과 제도"},
}

# ── 형식 ──────────────────────────────────────────────
# fit: 그 형식이 서려면 현실 소재 안에 이미 있어야 하는 구조 / engine: 넘길 엔진 (engines.py short)
# idea_format: Idea Engine STEP 1 '선호 포맷' 선택지
FORMAT_DESKS = {
    "장편 영화": {"fit": "두 시간 안에 시작과 끝이 닫히는 사건 하나와 되돌릴 수 없는 선택 하나",
                 "engine": "IDEA", "idea_format": "장편 영화"},
    "OTT 시리즈": {"fit": "회마다 새 사건이 생기는 무대나 관계망, 그리고 시즌 전체를 끌고 갈 큰 질문 하나",
                  "engine": "IDEA", "idea_format": "OTT 시리즈"},
    "숏폼 드라마 (실사)": {"fit": "1분 안에 터지는 폭로나 반전이 수십 번 반복될 수 있는 관계 구도와 숨긴 비밀",
                        "engine": "SHORTFORM"},
    "숏폼 애니메이션": {"fit": "대사 없이 행동 하나로 보이는 상황이 매회 변주되는 것, 실사로 찍기 어려운 시점(동물·사물·신·아이)",
                     "engine": "SHORTFORM"},
    "웹소설": {"fit": "회차마다 보상(작은 승리나 폭로)이 나오는 긴 성장·복수·역전의 사다리",
              "engine": "IDEA", "idea_format": "웹소설"},
    "장편소설·e북": {"fit": "한 인물의 내면을 오래 따라갈 수 있는 감정의 변화와 끝까지 숨겨진 사실 하나",
                   "engine": "IDEA", "idea_format": "미정 (Idea Engine이 추천)"},
    "인터랙티브 (FMV)": {"fit": "보는 사람이 실제로 고를 만한 갈림길이 있고, 선택마다 결과가 크게 갈리는 상황",
                       "engine": "FMV"},
}


def format_route(fmt: str) -> str:
    """이 형식의 소재를 넘길 엔진 (engines.py short). 형식 미정이면 Idea Engine."""
    return FORMAT_DESKS.get(fmt, {}).get("engine", "IDEA")


# 사무실 그림 자리 (engines.DESKS 이름)
STAFF = {
    "scout": {"title": "소재 발굴 담당", "desk": "series"},
    "gate":  {"title": "판별 담당", "desk": "idea"},
}


# ── Claude 호출과 검색 기록 확인 ─────────────────────────────
def _call(client, system: str, user: str, max_tokens: int, max_search: int = 0) -> dict:
    """응답 글, 실제로 검색된 문서 목록, 검색 횟수를 돌려줍니다. 긴 검색은 pause_turn 을 이어 받습니다."""
    messages = [{"role": "user", "content": user}]
    types = _search_type or SEARCH_TOOL_TYPES
    sources, searches, texts, stop = [], 0, [], ""
    for t_i, ttype in enumerate(types if max_search else [None]):
        kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system, messages=list(messages))
        if ttype:
            kwargs["tools"] = [{"type": ttype, "name": "web_search", "max_uses": max_search}]
        try:
            for _round in range(4):
                resp = client.messages.create(**kwargs)
                for b in resp.content:
                    bt = getattr(b, "type", "")
                    if bt == "server_tool_use" and getattr(b, "name", "") == "web_search":
                        searches += 1
                    elif bt == "web_search_tool_result":
                        content = getattr(b, "content", None)
                        if isinstance(content, list):
                            for r in content:
                                url = getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else None)
                                if url:
                                    title = getattr(r, "title", None) or (r.get("title") if isinstance(r, dict) else "") or ""
                                    age = getattr(r, "page_age", None) or (r.get("page_age") if isinstance(r, dict) else "") or ""
                                    sources.append({"url": url, "title": title, "page_age": age})
                    elif bt == "text":
                        texts.append(getattr(b, "text", ""))
                stop = getattr(resp, "stop_reason", "") or ""
                if stop == "pause_turn":
                    kwargs["messages"] = kwargs["messages"] + [{"role": "assistant", "content": resp.content}]
                    continue
                break
            if ttype and not _search_type:
                _search_type.append(ttype)
            break
        except Exception as e:
            # 검색 도구 판이 맞지 않으면 다음 판으로. 다른 오류는 그대로 올립니다.
            if ttype and t_i < len(types) - 1 and ("tool" in str(e).lower() or "400" in str(e)):
                continue
            raise
    return {"text": "".join(texts).strip(), "sources": sources, "searches": searches, "stop": stop}


def _json(text: str) -> dict:
    """응답에서 JSON 객체를 찾습니다. ```json 블록 → 괄호 짝이 맞는 가장 큰 객체 순."""
    for block in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S):
        try:
            return json.loads(block)
        except Exception:
            pass
    best = None
    for start in [m.start() for m in re.finditer(r"\{", text)]:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if best is None or len(text[start:i + 1]) > best[0]:
                            best = (i + 1 - start, obj)
                    except Exception:
                        pass
                    break
        if best and best[0] > len(text) * 0.5:
            break
    if best is None:
        raise ValueError("응답에서 JSON을 찾지 못했습니다.")
    return best[1]


def _ask_json(client, system: str, user: str, max_tokens: int, max_search: int = 0, who: str = "") -> tuple[dict, dict]:
    """한 번 묻고, 형식이 어긋나면(길이 초과로 끊김 포함) 찾은 문서를 들고 한 번 더 형식만 다시 받습니다."""
    res = _call(client, system, user, max_tokens, max_search)
    try:
        return _json(res["text"]), res
    except Exception:
        pass
    found = "\n".join(f"- {x['title']} {x['url']}" for x in res["sources"][:30])
    retry = (
        f"{user}\n\n[앞선 답] 형식에 맞지 않았거나 길이 초과로 끊겼다(stop={res['stop']}). 아래 내용을 바탕으로 지정한 JSON만 다시 써라. "
        "설명 문장 없이 JSON만, 각 항목은 더 짧게. 주소는 아래 '찾은 문서'에 있는 것만 쓴다.\n"
        f"[앞선 답 일부]\n{res['text'][-3000:]}\n[찾은 문서]\n{found or '(없음)'}"
    )
    res2 = _call(client, system, retry, int(max_tokens * 1.5), 0)
    try:
        data = _json(res2["text"])
    except Exception:
        head = (res2["text"] or res["text"])[:200].replace("\n", " ")
        raise ValueError(f"{who}: 형식에 맞는 답을 두 번 다 받지 못했습니다 (stop={res2['stop'] or res['stop']}). 응답 앞부분: {head}")
    res["text"] = res2["text"]
    return data, res


def _clean(obj):
    """대시 기호를 쉼표로 바꿉니다 (블루진 문서 규칙)."""
    if isinstance(obj, str):
        return re.sub(r"\s*[—–]\s*", ", ", obj)
    if isinstance(obj, list):
        return [_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    return obj


class Ledger:
    """회의 전체의 출처 장부. 실제로 검색된 주소에만 S번호를 붙입니다."""

    def __init__(self):
        self.items: list[dict] = []
        self.by_url: dict[str, str] = {}
        self.searches = 0
        self.lock = threading.Lock()

    def count(self, n: int) -> None:
        with self.lock:
            self.searches += n

    def add(self, sources: list[dict], who: str) -> None:
        with self.lock:
            self._add(sources, who)

    def _add(self, sources: list[dict], who: str) -> None:
        for s in sources:
            u = s["url"].strip()
            if u and u not in self.by_url:
                sid = f"S{len(self.items) + 1}"
                self.by_url[u] = sid
                self.items.append({**s, "url": u, "id": sid, "found_by": who})

    def sid(self, url: str) -> str | None:
        u = (url or "").strip().rstrip(".,)")
        return self.by_url.get(u) or self.by_url.get(u.rstrip("/")) or self.by_url.get(u + "/")

    def listing(self, ids: list[str] | None = None) -> str:
        rows = [s for s in self.items if ids is None or s["id"] in ids]
        return "\n".join(f"{s['id']} {s['title']} ({s['page_age']}) {s['url']}" for s in rows)


# ── 1. 소재 발굴 ─────────────────────────────────────────
def scout(client, direction: str, ledger: Ledger, genre: str = "", memory: str = "", fmt: str = "") -> dict:
    desk = GENRE_DESKS.get(genre)
    form = FORMAT_DESKS.get(fmt)
    system = (
        "너는 BLUE JEANS PICTURES 기획실의 소재 발굴 담당이다. 영화·드라마·웹소설 등 기존 작품은 찾지 않는다. "
        "현실에서 이야기의 재료를 찾는다: 최근 뉴스, 판결, 제도·법 변화, 새로 생기거나 사라지는 직업, 기술, 지역 풍습, 사건·사고, 하위문화. "
        "한국어뿐 아니라 영어·일본어·현지어로 전 세계를 검색한다. " + HOUSE_RULES
        + (f" 너는 {genre} 담당이다. 이 장르의 재미는 '{desk['core']}'에서 나온다. 그 재미가 바로 생길 현실을 이런 곳에서 찾는다: {desk['where']}."
           if desk else "")
        + (f" 이번 형식은 {fmt}이다. 이 형식이 서려면 '{form['fit']}'이 필요하다. 그런 구조가 현실 안에 이미 들어 있는 소재를 우선 찾는다."
           if form else "")
    )
    user = (
        "웹 검색을 여러 번 해서 현실 소재 5~8개를 찾고 JSON으로만 답하라.\n"
        '{"candidates":[{"name":"소재 이름 (짧게)","fact":"실제로 무슨 일이 있었나. 확인한 사실만 2문장","where_when":"나라와 시기",'
        '"urls":["이 사실을 확인한 문서 주소"]}]}\n'
        "urls 에는 이번에 실제로 검색해서 본 주소만 넣는다. 해석이나 이야기 아이디어는 쓰지 않는다.\n"
        + (f"이번 발굴 방향 (Mr. MOON 지시): {direction}" if direction.strip() else "이번 발굴 방향: 자유. 나라와 분야를 넓게 본다.")
        + (f"\n\n{memory}" if memory else "")
    )
    who = f"{genre} 담당" if desk else "소재 발굴 담당"
    data, res = _ask_json(client, system, user, 5000, 8, who)
    ledger.count(res["searches"])
    ledger.add(res["sources"], who)
    data = _clean(data)
    kept = []
    for c in data.get("candidates", []):
        ids = [ledger.sid(u) for u in c.get("urls", []) if ledger.sid(u)]
        if ids:   # 실제 검색 주소가 없는 소재는 버립니다
            c["ids"] = sorted(set(ids), key=ids.index)
            kept.append(c)
    return {"candidates": kept, "searches": res["searches"], "dropped": len(data.get("candidates", [])) - len(kept)}


# ── 2. 판별 ─────────────────────────────────────────────
_GENERIC = re.compile(r"(정의감|상처를 가진|평범한|강인한|따뜻한|냉철한|원칙주의)")


def gate(client, candidates: list[dict], direction: str = "", genre: str = "", fmt: str = "") -> list[dict]:
    desk = GENRE_DESKS.get(genre)
    form = FORMAT_DESKS.get(fmt)
    listing = "\n".join(f"{i}. {c['name']} ({c.get('where_when', '')}): {c['fact']}" for i, c in enumerate(candidates, 1))
    system = (
        "너는 BLUE JEANS PICTURES 기획실의 판별 담당이다. 이야기를 지어내지 않는다. 소재 안에 이야기의 씨앗이 이미 있는지만 가린다. "
        "엄격하게 본다. 애매하면 없음이다. " + HOUSE_RULES
    )
    user = (
        "각 소재에 대해 아래 조건을 본다.\n"
        "① who: 이 사실 안에서 결핍 또는 상실을 겪는 사람(직업·처지·잃은 것으로 구체적으로). 사실에 근거가 없으면 빈 문자열.\n"
        "② want / block: 그 사람이 원하는 것, 그것을 막는 것. 한 줄로 서지 않으면 빈 문자열.\n"
        "③ twist: 원하는 것을 쫓을수록 상황이 뒤집히는 역전(BUT/EXCEPT). 없으면 빈 문자열.\n"
        + (f"④ genre_core: {genre}의 재미는 '{desk['core']}'다. 이 소재에서 그 재미가 구체적으로 어떻게 생기는지 한 문장. 생기지 않으면 빈 문자열.\n"
           if desk else "")
        + (f"형식 format_fit: 이번 형식은 {fmt}이고, '{form['fit']}'이 있어야 선다. 이 소재 안에서 그 구조가 구체적으로 무엇인지 한 문장. 없으면 빈 문자열.\n"
           if form else "")
        + "모든 조건이 서면"
        " has_idea=true, seed 에 '누가 무엇을 원하는데 무엇이 막는다' 한 문장을 다듬지 말고 쓴다. "
        "하나라도 비면 has_idea=false, missing 에 빠진 조건 번호.\nJSON으로만 답하라.\n"
        '{"results":[{"no":1,"has_idea":true,"who":"","want":"","block":"","twist":"","genre_core":"","format_fit":"","seed":"","missing":[]}]}\n\n'
        + (f"[Mr. MOON 관심 방향] {direction}\n" if direction.strip() else "") + f"[소재]\n{listing}"
    )
    data, _res = _ask_json(client, system, user, 3500, 0, "판별 담당")
    data = _clean(data)
    by_no = {int(r.get("no", 0)): r for r in data.get("results", []) if str(r.get("no", "")).isdigit()}
    out = []
    for i, c in enumerate(candidates, 1):
        r = by_no.get(i, {})
        parts = {k: str(r.get(k, "") or "").strip() for k in ("who", "want", "block", "twist", "genre_core", "format_fit", "seed")}
        missing = []
        if not parts["who"] or _GENERIC.search(parts["who"]):
            missing.append("① 결핍·상실을 가진 사람")
        if not parts["want"] or not parts["block"]:
            missing.append("② 원하는 것과 막는 것")
        if not parts["twist"]:
            missing.append("③ 역전")
        if desk and not parts["genre_core"]:
            missing.append(f"④ {genre}의 재미({desk['core']})")
        if form and not parts["format_fit"]:
            missing.append(f"{fmt} 형식 요건")
        has = bool(r.get("has_idea")) and not missing and bool(parts["seed"])   # 코드가 다시 확인
        out.append({**c, **parts, "has_idea": has, "missing": missing if not has else []})
    return out


# ── 전체 ───────────────────────────────────────────────
def run_scan(client, direction: str = "", progress=None, genre: str = "", memory: str = "", fmt: str = "") -> dict:
    say = progress or (lambda _m: None)
    ledger = Ledger()
    if genre in GENRE_DESKS:
        say(f"{genre} 담당이 찾고 있습니다: {GENRE_DESKS[genre]['where']}")
    else:
        say("소재 발굴 담당이 전 세계 뉴스·보고서·제도를 검색하고 있습니다")
    if fmt in FORMAT_DESKS:
        say(f"형식은 {fmt}입니다. 소재 안에 '{FORMAT_DESKS[fmt]['fit']}'이 있는지까지 봅니다")
    if memory:
        say("지난 넘김·버림 기록을 읽고 시작합니다")
    sc = scout(client, direction, ledger, genre, memory, fmt)
    if not sc["candidates"]:
        raise RuntimeError("실제 검색 근거가 있는 소재를 찾지 못했습니다. 방향을 바꿔 다시 시도해 주십시오.")
    say(f"판별 담당이 소재 {len(sc['candidates'])}개에 이야기가 있는지 가리고 있습니다")
    items = gate(client, sc["candidates"], direction, genre, fmt)
    items.sort(key=lambda x: not x["has_idea"])
    return {"items": items, "sources": ledger.items, "searches": ledger.searches,
            "dropped": sc["dropped"], "direction": direction, "genre": genre, "format": fmt}


def idea_engine_input(item: dict, fmt: str = "") -> str:
    """넘길 엔진의 아이디어 칸에 붙일 글. 형식이 정해져 있으면 형식 요건도 함께 붙입니다."""
    form = FORMAT_DESKS.get(fmt)
    head = ""
    if form:
        head = f"[형식] {fmt}" + (f" (Idea Engine 선호 포맷: {form['idea_format']})" if form.get("idea_format") else "") + "\n"
    return (head + f"{item['seed']}\n\n"
            f"[현실 소재] {item['name']} ({item.get('where_when', '')}): {item['fact']}\n"
            f"[결핍·상실] {item['who']}\n[원하는 것] {item['want']}\n[막는 것] {item['block']}\n[역전] {item['twist']}"
            + (f"\n[장르의 재미] {item['genre_core']}" if item.get("genre_core") else "")
            + (f"\n[형식 요건] {item['format_fit']}" if item.get("format_fit") else ""))
