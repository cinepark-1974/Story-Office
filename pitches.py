"""제안 현황 — 작품을 누구에게 언제 제안했고 어떤 답을 받았는지.

Mr. MOON의 엑셀 양식(시트 이름 = 작품, 열 = 제안 날짜·피드백 날짜·제안 대상 이름·
제안 대상 소속·피드백 주요 내용·비고)을 그대로 읽어 R2의 storyoffice/pitches.json에
보관합니다. 실제 사람 이름과 평가가 들어 있으므로 저장소(GitHub)에는 넣지 않습니다.
"""

import io
import re
import statistics
import uuid
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
RESULTS = ["", "긍정", "보류", "거절", "진행", "무응답"]   # 빈칸 = 아직 분류 안 함
STALE = 180   # 이보다 오래 답이 없으면 기다리는 목록에서 빼고 따로 모읍니다
HEADERS = {"제안 날짜": "sent", "피드백 날짜": "reply", "제안 대상 이름": "person",
           "제안 대상 소속": "company", "피드백 주요 내용": "feedback", "비고": "memo"}
DEFAULT_WAIT = 21   # 지난 기록이 부족할 때 쓰는 기본 대기 일수


def _today() -> date:
    return datetime.now(KST).date()


def _day(v) -> str:
    """엑셀 칸 → 'YYYY-MM-DD' 또는 원래 글자('3월' 같은 것)."""
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    m = re.match(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", s)
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else s


def _as_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def new_pitch(work: str, sent: str = "", person: str = "", company: str = "", reply: str = "",
              feedback: str = "", memo: str = "", result: str = "") -> dict:
    return {"id": uuid.uuid4().hex[:8], "work": work.strip(), "sent": sent, "person": person.strip(),
            "company": company.strip(), "reply": reply, "feedback": feedback.strip(), "memo": memo.strip(),
            "result": result if result in RESULTS else ""}


def read_excel(raw: bytes) -> list[dict]:
    """엑셀 파일 → 제안 기록 목록. 시트 이름이 작품 제목입니다."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    rows = []
    for ws in wb.worksheets:
        header = [str(c.value or "").strip() for c in ws[1]]
        cols = {HEADERS[h]: i for i, h in enumerate(header) if h in HEADERS}
        if "person" not in cols and "company" not in cols:
            continue   # 양식이 다른 시트는 건너뜁니다
        for r in ws.iter_rows(min_row=2, values_only=True):
            get = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else None
            if not any(get(k) for k in ("sent", "person", "company", "feedback", "memo")):
                continue
            rows.append(new_pitch(ws.title, _day(get("sent")), str(get("person") or ""), str(get("company") or ""),
                                  _day(get("reply")), str(get("feedback") or ""), str(get("memo") or "")))
    return rows


def merge(all_rows: list[dict], new_rows: list[dict]) -> int:
    """같은 작품·날짜·사람·소속이면 같은 제안으로 보고 빈칸만 채웁니다. 새로 더한 수를 돌려줍니다."""
    key = lambda p: (p["work"], p["sent"], p["person"], p["company"])
    have = {key(p): p for p in all_rows}
    added = 0
    for p in new_rows:
        old = have.get(key(p))
        if old is None:
            all_rows.append(p)
            have[key(p)] = p
            added += 1
        else:
            for k in ("reply", "feedback", "memo"):
                if p[k] and not old[k]:
                    old[k] = p[k]
    return added


def wait_days(rows: list[dict]) -> int:
    """지금까지 답이 오기까지 걸린 날의 가운데 값. 기록이 적으면 기본 21일."""
    gaps = []
    for p in rows:
        a, b = _as_date(p["sent"]), _as_date(p["reply"])
        if a and b and b >= a:
            gaps.append((b - a).days)
    return int(statistics.median(gaps)) if len(gaps) >= 5 else DEFAULT_WAIT


def check(rows: list[dict]) -> dict:
    """사무실이 점검하는 것: 답을 기다리는 제안, 날짜가 이상한 기록, 작품별·회사별 요약."""
    today, wait = _today(), wait_days(rows)
    waiting, stale, odd = [], [], []
    for p in rows:
        sent = _as_date(p["sent"])
        if not p["reply"] and not p["feedback"] and p["result"] != "무응답":
            days = (today - sent).days if sent else None
            item = {**p, "days": days, "late": days is not None and days > wait}
            (stale if days is not None and days > STALE else waiting).append(item)
        reply = _as_date(p["reply"])
        if sent and reply and reply < sent:
            odd.append(p)
    waiting.sort(key=lambda p: -(p["days"] or 0))
    by_work, by_company = {}, {}
    for p in rows:
        w = by_work.setdefault(p["work"], {"sent": 0, "answered": 0, "results": {}, "last": ""})
        w["sent"] += 1
        w["answered"] += bool(p["reply"] or p["feedback"])
        if p["result"]:
            w["results"][p["result"]] = w["results"].get(p["result"], 0) + 1
        w["last"] = max(w["last"], p["sent"] if _as_date(p["sent"]) else "")
        if p["company"]:   # '씨제이 중국팀'과 '씨제이 투자'는 같은 회사로 묶습니다
            by_company.setdefault(p["company"].split()[0], []).append(p)
    return {"wait": wait, "waiting": waiting, "stale": stale, "odd": odd, "by_work": by_work, "by_company": by_company}


def from_paste(payload: dict) -> list[dict]:
    """Claude가 메일함을 정리해 준 글 → 제안 기록. {"pitches":[{"work","sent","person","company","reply","feedback","memo"}]}"""
    out = []
    for r in (payload.get("pitches") or []):
        if not str(r.get("work", "")).strip():
            continue
        out.append(new_pitch(str(r["work"]), _day(r.get("sent")), str(r.get("person", "")), str(r.get("company", "")),
                             _day(r.get("reply")), str(r.get("feedback", "")), str(r.get("memo", "")),
                             str(r.get("result", ""))))
    return out
