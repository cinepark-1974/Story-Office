"""STORY OFFICE 직원들 — 근거를 찾은 뒤에만 말하는 기획 회의.

버튼을 누를 때만 일합니다(그때만 Claude API 사용량이 듭니다).

회의 순서
  1. 소재 발굴 담당  전 세계 뉴스·보고서·판결·제도·직업·기술·사건을 검색해 현실 소재 후보를 가져온다.
                     영화·드라마는 찾지 않는다(따라 하지 않기 위해).
  2. 발제 담당       후보 하나를 골라 허구의 아이디어 한 장을 쓴다.
  3. 판단 담당들     욕망 · 로그라인·인물 · 구조 · 장르 · 고증 · 독창성 · 시장. 서로의 의견을 보지 않고 따로 낸다.
  4. 편성 담당       Idea Engine 판정 규칙(GO / CONDITIONAL / NOGO)과 포맷 확신도로 배정을 권고한다.

아무말 차단
  - 검색이 필수인 직원이 실제로 검색하지 않으면 그 의견은 판정에서 뺀다(응답 속 검색 기록으로 확인).
  - 모든 지적은 근거가 '아이디어 문장 인용' 또는 '실제로 검색된 주소' 둘 중 하나여야 한다.
    인용이 아이디어에 없거나, 주소가 검색 결과에 없으면 '근거 없음'으로 떨어지고 판정에 쓰지 않는다.
  - 판단 기준은 엔진 prompt.py 규칙을 옮겨 온 것이다(각 직원 criteria 옆에 출처 표시).

직원의 일을 바꾸려면 ROLES 의 criteria 를 고칩니다.
"""

from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor

MODEL = "claude-sonnet-4-6"   # 엔진들과 같은 모델
SEARCH_TOOL_TYPES = ["web_search_20260318", "web_search_20250305"]   # 새 판부터 시도
_search_type: list[str] = []  # 실제로 통한 판을 기억

# Idea Engine STEP 1 선택 목록 (Idea-Engine/main.py)
GENRES = ["범죄/스릴러", "드라마", "액션", "로맨스", "코미디", "호러/공포", "SF", "판타지",
          "코지 미스터리", "느와르", "사회파"]
MARKETS = ["한국 + 글로벌", "한국 (국내)", "일본 (인디·공동제작·리메이크 트랙)", "인도네시아 (JAFF 트랙)",
           "인도네시아 + 한국 OTT (Netflix SEA)", "베트남 (극장·OTT)", "베트남 + 한국 공동제작",
           "한국 + 베트남", "한국 + 일본 공동제작", "글로벌 (해외)"]
FORMATS = ["장편 영화", "OTT 시리즈", "미니시리즈", "숏폼 드라마", "웹소설", "웹툰"]

# 편성 담당이 점수를 매기는 포맷 → 배정
FORMAT_ROUTES = {
    "장편 영화":   "Creator 직행",
    "OTT 시리즈":  "Creator → Series",
    "웹소설":      "WebNovel 직행",
    "장편소설":    "Creator → Novel",
    "숏폼 드라마": "Shortform 직행",
    "무협":        "Wuxia 직행",
    "인터랙티브":  "FMV 직행",
}
SPECIAL_DESKS = {"무협": "wuxia", "숏폼 드라마": "shortform", "인터랙티브": "fmv"}

ASSIGNMENTS = {
    "Idea Engine":      ["IDEA"],
    "Creator 직행":      ["CREATOR"],
    "Creator → Series": ["CREATOR", "SERIES"],
    "Creator → Novel":  ["CREATOR", "NOVEL"],
    "WebNovel 직행":     ["WEBNOVEL"],
    "Wuxia 직행":        ["WUXIA"],
    "Shortform 직행":    ["SHORTFORM"],
    "FMV 직행":          ["FMV"],
    "보류":              [],
}

# 배정된 엔진 첫 화면 칸 (각 엔진 main.py 첫 입력 화면)
ENGINE_INPUTS = {
    "IDEA":      ["제목", "장르", "타겟 시장", "선호 포맷", "원본 아이디어"],
    "CREATOR":   ["원본 아이디어"],
    "WEBNOVEL":  ["가제", "로그라인", "시놉시스", "세계관/배경", "주요 인물과 각자의 목표"],
    "WUXIA":     ["가제", "로그라인", "무협 유형", "주인공", "세계관/문파"],
    "SHORTFORM": ["주인공 설정", "핵심 비밀 2~3개", "메인 악역 설정", "시즌 질문"],
    "FMV":       ["작품 제목", "주인공 시점", "한 줄 훅", "소재 키워드"],
}

HOUSE_RULES = (
    "공통 규칙: 한국어로 쓴다. 추상적인 개념어 대신 구체적인 인물·장소·시각·행동·사건으로 말한다. "
    "칭찬으로 시작하지 않는다. 대시 기호(— –)를 쓰지 않는다. "
    "엔진이 추정한 수치, 관객 수, 흥행 수치를 쓰지 않는다(Idea:71, 86–89). 존재하지 않는 작품·기사·통계를 만들지 않는다(Idea:722). "
    "판단할 근거가 없으면 '미정'으로 쓴다. 추측해서 채우지 않는다(Idea:2779). "
    "모든 지적의 basis 는 반드시 둘 중 하나다: '인용: <아이디어에 있는 문장을 그대로>' 또는 실제로 검색해서 본 문서의 주소(https://...)."
)

# ── 직원 명단 ──────────────────────────────────────────────
# desk: 사무실 그림 자리(engines.DESKS) / group: round·evidence·judge·special / search: 검색 필수 여부·최대 횟수
ROLES = {
    "scout": {
        "title": "소재 발굴 담당", "desk": "series", "group": "evidence", "tools": [], "search": (True, 8),
        "criteria": "영화·드라마·웹소설 등 기존 작품은 찾지 않는다. 현실에서 이야기의 재료를 찾는다: 최근 뉴스, 판결, 제도·법 변화, "
                    "새로 생기거나 사라지는 직업, 기술, 지역 풍습, 사건·사고, 하위문화. 한국어뿐 아니라 영어·일본어·현지어로 전 세계를 검색한다. "
                    "후보마다 '이 현실에서 누구의 어떤 결핍 또는 상실이 생기는가'를 적는다(모든 욕망은 결핍 또는 상실에서 발생, Idea:1270).",
    },
    "pitch": {
        "title": "발제 담당", "desk": "idea", "group": "round", "tools": [], "search": (False, 2),
        "criteria": "소재 후보 하나(또는 둘의 결합)를 골라 허구의 아이디어를 짓는다. 실존 인물 실명을 쓰지 않는다. "
                    "로그라인은 누가 / 무엇을 원하는데 / 무엇이 막는가(Idea:114). 매체·회차·러닝타임 어휘를 로그라인에 넣지 않는다(Idea:140).",
    },
    "desire": {
        "title": "욕망 담당", "desk": "creator", "group": "round", "tools": [], "search": (False, 2),
        "criteria": "BJND 4축 연쇄를 본다: 발생요인(결핍 Lack 또는 상실 Loss) → 욕망(Goal + Need) → 해결전략(Strategy) → 대가(Cost) (Creator:2765). "
                    "해결전략이 창의적이지 않으면 이야기의 존재 이유가 없다(Creator:2826). Cost를 설계하지 않으면 2막이 공허해진다(Creator:2830). "
                    "엔딩에서 Strategy_1 → Strategy_2 전환이 가능한가(Creator:2860). 적대자도 4단으로 설계되고 주인공 전략과 거울 관계인가(Creator:3534, 3544). "
                    "테마와 Strategy가 같은 방향인가(Creator:3646). 욕망의 출발점이 아이디어에 근거가 없으면 '미정'(Idea:2779).",
    },
    "logline": {
        "title": "로그라인·인물 담당", "desk": "writer", "group": "round", "tools": [], "search": (False, 2),
        "criteria": "로그라인 BUT/EXCEPT 역전이 있는가, 'and then' 나열형인가(Creator:2614). 같은 장르의 다른 로그라인이 같은 주인공을 낳는다면 실패다(Creator:8156). "
                    "'정의감 강한' '과거의 상처를 가진' 같은 무색 수식 금지. Goal이 높은 판돈·긴급성·납득 가능성을 모두 갖췄는가(Creator:2621). "
                    "주인공의 능동 갈망 행동 3개, 장애물을 넘는 전술 3가지가 떠오르는가(Creator:2628, 3856). "
                    "Hook 4축을 0~10 정수로 채점한다: 구체성, 갈등 가시성, 장르 명확성, 판돈(Idea:218–249). 독창성 축은 독창성 담당이 매긴다.",
    },
    "structure": {
        "title": "구조 담당", "desk": "rewrite", "group": "round", "tools": [], "search": (False, 1),
        "criteria": "Creator 16슬롯 비트로 본다(Creator:2254). 5 도발적 사건, 6 첫번째 변곡점(돌아올 수 없는 문), 10 Midpoint(게임의 규칙이 바뀌는 전환), "
                    "12 All Is Lost(아직 반격하지 않는다), 13 빌런의 최고조, 14 클라이맥스(Beat 12에서 잃은 것이 새로운 무기가 된다)가 각각 구체적 사건으로 서는가. "
                    "서지 않는 비트는 없다고 말한다. 장벽 4유형(물리·심리·신분·시간) 중 2종 이상, Beat 6/10/13 에스컬레이션(Creator:3789). "
                    "우연에 의한 해결 금지(Creator:2637). 삭제해도 이야기가 작동하는 사건은 불필요하다(Creator:2650).",
    },
    "genre": {
        "title": "장르 담당", "desk": "revise", "group": "round", "tools": [], "search": (False, 1),
        "criteria": "장르 재미의 본질로 본다(Creator:3359): 스릴러는 정보 비대칭이 만드는 긴장, 호러는 규칙 위반이 주는 서늘함 등. "
                    "관객 기대 체크리스트(Creator:3376): 롬코 웃음·설렘 각 5회 이상, 액션 Setpiece 3개 이상, 호러 서스펜스 대 쇼크 3:1 이상, 스릴러 의심 대상 2명 이상. "
                    "하나라도 NO면 재설계 대상. 클라이맥스가 장르와 정렬되는가(어긋나면 CLIMAX_FAIL, Creator:11821). "
                    "클라이맥스에서 주인공이 반드시 '한다'. 제3자의 해결·적의 자멸·내면의 깨달음은 즉시 FAIL(Creator:8489). 자극과 도파민은 다르다(Creator:3503).",
    },
    "reality": {
        "title": "고증 담당", "desk": "webnovel", "group": "evidence", "tools": [], "search": (True, 4),
        "criteria": "Reality Gate(Creator:11853): 직업이 현실의 업무 범위를 넘는가, 법적 효력, 절차와 기간, 조직과 권한, 물리적 불가능. "
                    "공공 인프라에 없는 기능, 비현실적 군중 반응(Idea:45–84). 반드시 검색해서 확인한 것만 지적한다. 최대 5건. "
                    "오탐 1건이 미탐 1건보다 해롭다. 확인 못 한 것은 '확인 필요'로만 적는다.",
    },
    "original": {
        "title": "독창성 담당", "desk": "novel", "group": "evidence", "tools": [], "search": (True, 4),
        "criteria": "아이디어가 이미 있는 설정인지 거른다(발제에는 관여하지 않는다). 유사작을 검색해 최대 5편, 최근 3년 내 동일 소재면 치명적 유사작(Idea:671–711). "
                    "한국 작품은 kobis·cine21, 해외 작품은 imdb·variety를 우선 확인(Creator:7890). 기준 작품과 핵심 엔진이 대부분 같으면 표절 거리 경고(Idea:653). "
                    "What-if 4대 함정: 가설 의존성, 룰 위반, 결말 회피, 일회성(Idea:2228). 실패할 이유를 찾는 반대 역할을 겸한다. "
                    "Hook 독창성 축을 0~10 정수로 채점한다.",
    },
    "market": {
        "title": "시장 담당", "desk": "english", "group": "judge", "tools": ["ENGLISH", "JAPANESE"], "search": (True, 4),
        "criteria": "시장 좌표 4분류: TENTPOLE / MASTERCLASS / STREAMING / GENRE FEATURE(Idea:536). 일본은 인디·공동제작·리메이크 3트랙 외 0점(Idea:771). "
                    "장르의 최근 흥행만을 이유로 가점하지 않는다(Idea:790). 베트남은 호러를 포화·규제 주의 장르로 먼저 본다. "
                    "시장 판단으로 작품 점수나 작가 설정을 바꾸라고 하지 않는다(Rewrite:966, Idea:791). 시장성 별 0~5를 매긴다(0은 부적합).",
    },
    "editor": {
        "title": "편성 담당", "desk": "japanese", "group": "judge", "tools": [], "search": (False, 0),
        "criteria": "포맷 판단 근거는 사건 밀도와 인물 수뿐이다. 흥행성이나 트렌드를 근거로 들지 않는다(Creator main:1368). "
                    "확신이 없으면 배정하지 않는다(Idea:493). 회의는 아이디어를 고쳐 쓰지 않는다. 보완 과제는 무엇이 비었는지만 말한다.",
    },
    "wuxia":     {"title": "무협 담당", "desk": "wuxia", "group": "special", "tools": ["WUXIA"], "search": (False, 1),
                  "criteria": "정통·회빙환·시스템·학원 무협으로 옮길 여지가 있는지, 무공·문파·강호 질서로 갈등이 서는지 본다."},
    "shortform": {"title": "숏폼 담당", "desk": "shortform", "group": "special", "tools": ["SHORTFORM"], "search": (False, 1),
                  "criteria": "1~2분 × 80~100화 세로형 숏폼으로, 1화부터 훅이 서고 매화 끝에 다음 화를 누르게 만드는 비밀 2~3개가 있는지 본다."},
    "fmv":       {"title": "인터랙티브 담당", "desk": "fmv", "group": "special", "tools": ["FMV"], "search": (False, 1),
                  "criteria": "관객의 선택으로 갈라지는 실사 인터랙티브 드라마가 될 수 있는지, 갈림길이 될 장면이 있는지 본다."},
}

JUDGES = ["desire", "logline", "structure", "genre", "reality", "original", "market"]


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


def _norm(s: str) -> str:
    return re.sub(r"[\s\"'“”‘’「」『』.,·…!?]", "", s or "")


def _check_points(points: list, idea_text: str, ledger: Ledger) -> list[dict]:
    """지적마다 근거를 확인합니다: 인용은 아이디어에 실제로 있어야, 주소는 실제 검색 결과여야 합니다."""
    out, idea_n = [], _norm(idea_text)
    for p in points or []:
        if isinstance(p, str):
            p = {"text": p, "basis": ""}
        basis = str(p.get("basis", "")).strip()
        status, ref = "근거 없음", ""
        if basis.startswith("인용"):
            quote = basis.split(":", 1)[-1].strip()
            if len(_norm(quote)) >= 6 and _norm(quote) in idea_n:
                status, ref = "인용", quote
        else:
            m = re.search(r"https?://\S+", basis)
            sid = ledger.sid(m.group(0)) if m else None
            if not sid:
                m2 = re.search(r"\bS\d+\b", basis)
                sid = m2.group(0) if m2 and any(s["id"] == m2.group(0) for s in ledger.items) else None
            if sid:
                status, ref = "확인됨", sid
        out.append({"text": p.get("text", ""), "status": status, "ref": ref})
    return out


# ── 1. 소재 발굴 ─────────────────────────────────────────
def scout(client, direction: str, ledger: Ledger) -> dict:
    r = ROLES["scout"]
    system = f"너는 BLUE JEANS PICTURES 기획실의 {r['title']}다. 직무: {r['criteria']} {HOUSE_RULES}"
    user = (
        "웹 검색을 여러 번 해서 현실 소재 후보 3~5개를 찾고 JSON으로만 답하라. 영화·드라마·소설 작품은 후보로 삼지 않는다.\n"
        '{"candidates":[{"name":"소재 이름","fact":"실제로 무슨 일이 있었나 (확인한 사실만, 2~3문장)","where_when":"나라와 시기",'
        '"urls":["이 사실을 확인한 문서 주소"],"lack_or_loss":"이 현실에서 누가 어떤 결핍 또는 상실을 겪는가","genre_fit":"어울리는 장르 1~2개"}]}\n'
        "urls 에는 이번에 실제로 검색해서 본 주소만 넣는다.\n"
        + (f"이번 발굴 방향 (Mr. MOON 지시): {direction}" if direction.strip() else "이번 발굴 방향: 자유. 나라와 분야를 넓게 본다.")
    )
    data, res = _ask_json(client, system, user, 6000, r["search"][1], r["title"])
    ledger.count(res["searches"])
    ledger.add(res["sources"], r["title"])
    data = _clean(data)
    kept = []
    for c in data.get("candidates", []):
        ids = [ledger.sid(u) for u in c.get("urls", []) if ledger.sid(u)]
        if ids:   # 실제 검색 주소가 없는 후보는 버립니다
            c["ids"] = ids
            kept.append(c)
    return {"candidates": kept, "searches": res["searches"], "dropped": len(data.get("candidates", [])) - len(kept)}


# ── 2. 발제 ─────────────────────────────────────────────
def write_pitch(client, direction: str, scouting: dict, ledger: Ledger, no: int, date: str) -> dict:
    r = ROLES["pitch"]
    cands = "\n".join(f"- [{','.join(c['ids'])}] {c['name']}: {c['fact']} / 결핍·상실: {c['lack_or_loss']} / 장르: {c['genre_fit']}"
                      for c in scouting["candidates"])
    system = f"너는 BLUE JEANS PICTURES 기획실의 {r['title']}다. 직무: {r['criteria']} {HOUSE_RULES}"
    user = (
        "아래 소재 후보 중 하나(또는 둘의 결합)를 골라 허구의 아이디어 한 장을 JSON으로만 써라.\n"
        f"장르는 {GENRES} 중 하나, 타겟 시장은 {MARKETS} 중 하나, 선호 포맷은 {FORMATS} 중 하나.\n"
        '{"title":"가제","genre":"","market":"","format":"","material_ids":["출발한 소재의 S번호"],'
        '"logline":"누가 / 무엇을 원하는데 / 무엇이 막는가 한두 문장",'
        '"raw_idea":"Idea Engine 원본 아이디어 칸에 붙일 문단. 주인공 이름·나이·직업, 장소, 첫 사건, 갈등이 커지는 방향을 6~9문장",'
        '"scenes":["핵심 장면 1 (장소·시각·인물의 행동)","핵심 장면 2","핵심 장면 3"],'
        '"why_now":"이 현실 소재가 왜 지금 이야기가 되는가 2~3문장"}\n\n'
        f"[소재 후보]\n{cands}\n\n" + (f"[Mr. MOON 지시] {direction}" if direction.strip() else "")
    )
    idea, _res = _ask_json(client, system, user, 3500, 0, r["title"])
    idea = _clean(idea)
    idea["material_ids"] = [i for i in idea.get("material_ids", []) if any(s["id"] == i for s in ledger.items)]
    idea["no"], idea["date"] = no, date
    idea.setdefault("scenes", [])
    return idea


def idea_sheet(idea: dict) -> str:
    scenes = "\n".join(f"{i}. {s}" for i, s in enumerate(idea.get("scenes", []), 1))
    return (f"[가제] {idea.get('title')}\n[장르] {idea.get('genre')}  [시장] {idea.get('market')}  [포맷] {idea.get('format')}\n"
            f"[로그라인] {idea.get('logline')}\n[원본 아이디어] {idea.get('raw_idea')}\n[핵심 장면]\n{scenes}\n"
            f"[왜 지금인가] {idea.get('why_now')}")


# ── 3. 판단 담당들 ────────────────────────────────────────
_EXTRA = {
    "logline":  ',"hook":{"구체성":0,"갈등 가시성":0,"장르 명확성":0,"판돈":0}',
    "original": ',"hook_originality":0,"fatal_similar":false,"similar":[{"title":"작품명 (연도, 나라)","basis":"https://..."}]',
    "market":   ',"stars":0,"coordinate":"TENTPOLE|MASTERCLASS|STREAMING|GENRE FEATURE","jp_track":"인디|공동제작|리메이크|해당 없음"',
}


def _opinion(client, key: str, idea: dict, ledger: Ledger) -> dict:
    r = ROLES[key]
    must, n = r["search"]
    system = f"너는 BLUE JEANS PICTURES 기획 회의의 {r['title']}다. 판단 기준: {r['criteria']} {HOUSE_RULES}"
    if must:
        system += " 너는 반드시 웹 검색으로 확인한 뒤에만 말한다. 한국어·영어·현지어로 전 세계를 검색한다."
    mark = '"fit":"맞음|조건부|안 맞음"' if r["group"] == "special" else '"verdict":"통과|보완|불가"'
    user = (
        "아래 아이디어를 네 판단 기준으로만 보고 JSON으로만 답하라. 지적은 최대 4개.\n"
        f'{{{mark},"one_line":"한 문장 판단","points":[{{"text":"사건·장면 단위 지적","basis":"인용: 아이디어 문장 그대로 | https://검색한 주소"}}],'
        f'"undecided":["근거가 없어 판단 못 한 항목"]{_EXTRA.get(key, "")}}}\n\n{idea_sheet(idea)}'
    )
    out, res = _ask_json(client, system, user, 3000, n, r["title"])
    ledger.count(res["searches"])
    ledger.add(res["sources"], r["title"])
    out = _clean(out)
    out["role"], out["searches"] = key, res["searches"]
    out["points"] = _check_points(out.get("points"), idea_sheet(idea), ledger)
    out["excluded"] = bool(must and res["searches"] == 0)
    if key == "original":
        out["similar"] = [s for s in out.get("similar", []) if ledger.sid(str(s.get("basis", "")))]
        for s in out["similar"]:
            s["ref"] = ledger.sid(s["basis"])
    return out


# ── 4. 편성 ─────────────────────────────────────────────
def _num(x, lo=0, hi=10) -> int:
    try:
        return max(lo, min(hi, int(round(float(x)))))
    except Exception:
        return lo


def judge(opinions: dict) -> dict:
    """Idea Engine 최종 판정 규칙(Idea:982–985)을 코드로 계산합니다."""
    lg, og, mk = opinions.get("logline", {}), opinions.get("original", {}), opinions.get("market", {})
    hook = {k: _num(v) for k, v in (lg.get("hook") or {}).items()} if not lg.get("excluded") else {}
    hook["독창성"] = _num(og.get("hook_originality")) if og and not og.get("excluded") else 0
    total = sum(hook.values())
    stars = _num(mk.get("stars"), 0, 5) if mk and not mk.get("excluded") else None
    fatal = bool(og.get("fatal_similar")) and bool(og.get("similar"))   # 근거 있는 유사작이 있을 때만
    if total < 25 or fatal or stars == 0:
        verdict = "NOGO"
    elif total >= 35 and (stars or 0) >= 3 and not fatal:
        verdict = "GO"
    else:
        verdict = "CONDITIONAL"
    return {"hook": hook, "hook_total": total, "stars": stars, "fatal": fatal, "verdict": verdict}


def format_confidence(scores: dict) -> dict:
    """포맷 확신도(Idea:498–500)."""
    ranked = sorted(((k, _num(v)) for k, v in scores.items()), key=lambda x: -x[1])
    if not ranked:
        return {"ranked": [], "level": "미정", "top": None}
    (f1, s1), s2 = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0)
    if s1 >= 8 and s1 - s2 >= 2:
        level = "확정"
    elif s1 >= 6:
        level = "잠정"
    else:
        level = "미정"
    return {"ranked": ranked, "level": level, "top": f1}


def editor(client, idea: dict, opinions: dict, ledger: Ledger, progress) -> dict:
    r = ROLES["editor"]
    valid = [o for o in opinions.values() if not o.get("excluded")]
    lines = []
    for o in valid:
        pts = [f"{p['text']} ({p['status']}{' ' + p['ref'] if p['status'] == '확인됨' else ''})"
               for p in o["points"] if p["status"] != "근거 없음"]
        lines.append(f"- {ROLES[o['role']]['title']} [{o.get('verdict') or o.get('fit')}] {o.get('one_line', '')}\n  " + "\n  ".join(pts))
    system = f"너는 BLUE JEANS PICTURES 기획 회의의 {r['title']}다. 기준: {r['criteria']} {HOUSE_RULES}"

    # 4-1 포맷 점수 (사건 밀도와 인물 수로만)
    fmt, _r = _ask_json(client, system, (
        "아래 아이디어의 사건 밀도와 인물 수만 근거로 각 포맷의 적합도를 0~10 정수로 매겨 JSON으로만 답하라.\n"
        f'{{"scores":{{{",".join(f"{json.dumps(k, ensure_ascii=False)}:0" for k in FORMAT_ROUTES)}}},"basis":"사건 수와 인물 수를 근거로 한두 문장"}}\n\n'
        f"{idea_sheet(idea)}"), 1200, 0, r["title"])
    fmt = _clean(fmt)
    conf = format_confidence(fmt.get("scores", {}))

    # 4-2 특수 포맷이 1·2순위면 그 담당을 부른다
    for f, _s in conf["ranked"][:2]:
        if f in SPECIAL_DESKS:
            key = SPECIAL_DESKS[f]
            progress(f"{ROLES[key]['title']}을 회의에 부릅니다")
            try:
                opinions[key] = _opinion(client, key, idea, ledger)
            except Exception as e:
                opinions[key] = {"role": key, "fit": "불참", "one_line": f"의견을 받지 못했습니다 ({type(e).__name__})",
                                 "points": [], "excluded": True}

    verdict = judge(opinions)
    if verdict["verdict"] == "NOGO":
        assignment = "보류"
    elif verdict["verdict"] == "GO" and conf["level"] == "확정":
        assignment = FORMAT_ROUTES.get(conf["top"], "Idea Engine")
    else:
        assignment = "Idea Engine"
    path = ASSIGNMENTS.get(assignment, [])
    fields = ENGINE_INPUTS.get(path[0], []) if path else []

    # 4-3 회의록
    minutes, _r = _ask_json(client, system, (
        "아래 회의 결과를 정리해 JSON으로만 답하라. 판정과 배정은 이미 규칙으로 정해졌으니 바꾸지 말고 이유만 쓴다.\n"
        f"[판정] {verdict['verdict']} (Hook {verdict['hook_total']}/50, 시장성 별 {verdict['stars']}, 치명적 유사작 {'있음' if verdict['fatal'] else '없음'})\n"
        f"[포맷 확신도] {conf['level']} {conf['ranked'][:3]}\n[배정] {assignment}\n"
        '{"summary":"회의 결론 2~3문장","issues":["쟁점"],"tasks":["보완 과제 1","보완 과제 2","보완 과제 3"],'
        '"reason":"판정과 배정을 가른 지적 1~2문장","engine_input":{' + ",".join(f'"{f}":""' for f in fields) + "}}\n"
        "보완 과제는 아이디어를 고쳐 쓰지 말고 무엇이 비었는지만 말한다. engine_input 은 아이디어에 있는 내용만으로 채운다.\n\n"
        f"{idea_sheet(idea)}\n\n[근거가 확인된 참석자 의견]\n" + "\n".join(lines)), 3500, 0, r["title"])
    minutes = _clean(minutes)
    minutes.update({"assignment": assignment, "verdict": verdict, "format": conf, "format_basis": fmt.get("basis", "")})
    return minutes


# ── 회의 전체 ───────────────────────────────────────────
def run_meeting(client, direction: str = "", no: int = 1, date: str = "", progress=None) -> dict:
    say = progress or (lambda _m: None)
    ledger = Ledger()

    say("소재 발굴 담당이 전 세계 뉴스·보고서·제도를 검색하고 있습니다")
    scouting = scout(client, direction, ledger)
    if not scouting["candidates"]:
        raise RuntimeError("소재 발굴 담당이 실제 검색 근거가 있는 소재를 찾지 못했습니다. 방향을 바꿔 다시 시도해 주십시오.")

    say(f"발제 담당이 소재 후보 {len(scouting['candidates'])}개 중 하나로 아이디어를 쓰고 있습니다")
    idea = write_pitch(client, direction, scouting, ledger, no, date)

    say("판단 담당들이 각자 따로 검토하고 있습니다: " + ", ".join(ROLES[k]["title"] for k in JUDGES))
    with ThreadPoolExecutor(max_workers=7) as pool:
        futures = {k: pool.submit(_opinion, client, k, idea, ledger) for k in JUDGES}
    opinions = {}
    for k, f in futures.items():
        try:
            opinions[k] = f.result()
        except Exception as e:  # 한 사람이 실패해도 회의는 계속
            opinions[k] = {"role": k, "verdict": "불참", "one_line": f"의견을 받지 못했습니다 ({type(e).__name__})",
                           "points": [], "excluded": True, "searches": 0}

    say("편성 담당이 판정과 배정을 정리하고 있습니다")
    minutes = editor(client, idea, opinions, ledger, say)
    return {"scouting": scouting, "idea": idea, "opinions": list(opinions.values()), "minutes": minutes,
            "sources": ledger.items, "searches": ledger.searches, "direction": direction}
