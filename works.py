"""작품 현황판 — 엔진으로 개발 중인 작품과 단계.

엔진들은 결과를 파일로 내려받게만 되어 있어서 어디에도 기록을 남기지 않습니다.
그래서 작품과 단계는 Mr. MOON이 사무실에서 직접 표시하고, R2의
storyoffice/works.json 한 파일에 보관합니다.

단계 코드는 engines.py 의 short 값(IDEA, CREATOR …)과 같습니다.
"""

import unicodedata
import uuid
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

STAGE_LABEL = {
    "IDEA": "아이디어", "CREATOR": "기획개발", "WRITER": "시나리오", "SERIES": "시리즈 대본",
    "WEBNOVEL": "웹소설 연재", "NOVEL": "장편소설", "WUXIA": "무협 집필", "SHORTFORM": "숏폼 대본",
    "FMV": "분기 각본", "REWRITE": "진단", "REVISE": "각색·윤문", "ENGLISH": "영어판", "JAPANESE": "일본어판",
}
STAGE_ORDER = list(STAGE_LABEL)   # 화면에 늘어놓는 순서

# 포맷을 고르면 처음에 채워 주는 단계. 작품마다 고칠 수 있습니다.
FORMATS = {
    "장편 영화": ["IDEA", "CREATOR", "WRITER", "REWRITE", "REVISE"],
    "OTT 시리즈": ["IDEA", "CREATOR", "SERIES"],
    "웹소설": ["IDEA", "CREATOR", "WEBNOVEL"],
    "장편소설": ["IDEA", "CREATOR", "NOVEL"],
    "무협": ["WUXIA"],
    "숏폼 드라마": ["SHORTFORM"],
    "인터랙티브(FMV)": ["FMV"],
}
STATES = ["대기", "진행", "완료"]


def _now() -> str:
    return f"{datetime.now(KST):%Y-%m-%d %H:%M}"


def norm(title: str) -> str:
    """Mac에서 온 한글(자모 분리, NFD)도 같은 제목으로 봅니다."""
    return unicodedata.normalize("NFC", str(title or "")).strip()


def new_work(title: str, fmt: str, genre: str, stages: list[str]) -> dict:
    title = norm(title)
    stages = [s for s in STAGE_ORDER if s in stages]   # 순서를 바로잡습니다
    return {"id": uuid.uuid4().hex[:8], "title": title, "format": fmt, "genre": genre.strip(),
            "stages": stages, "state": {s: "대기" for s in stages}, "note": {s: "" for s in stages},
            "log": [{"date": _now(), "stage": "", "state": "", "note": "등록"}],
            "created": _now(), "updated": _now(), "archived": False}


def set_stage(work: dict, stage: str, state: str, note: str = "") -> None:
    if stage not in work["stages"] or state not in STATES:
        raise ValueError("없는 단계나 상태입니다.")
    work["state"][stage] = state
    if note.strip():
        work["note"][stage] = note.strip()
    work["log"].append({"date": _now(), "stage": stage, "state": state, "note": note.strip()})
    work["log"] = work["log"][-40:]
    work["updated"] = _now()


def current(work: dict) -> tuple[str, str]:
    """지금 단계: 진행 중인 마지막 단계, 없으면 아직 끝나지 않은 첫 단계. 다 끝났으면 ('', '완성')."""
    doing = [s for s in work["stages"] if work["state"].get(s) == "진행"]
    if doing:
        return doing[-1], "진행"
    for s in work["stages"]:
        if work["state"].get(s) != "완료":
            return s, "대기"
    return "", "완성"


def merge(all_works: list[dict], payload: list[dict]) -> tuple[list[str], list[str]]:
    """Claude가 정리한 목록을 현황판에 합칩니다. 제목이 같으면 고치고, 없으면 새로 넣습니다.

    payload 한 줄: {"title": "...", "format": "장편 영화", "genre": "...",
                    "stages": {"IDEA": "완료", "WRITER": "진행"}, "notes": {"WRITER": "v2.1"}}
    """
    added, updated = [], []
    by_title = {norm(w["title"]).replace(" ", ""): w for w in all_works}
    for row in payload:
        title = norm(row.get("title", ""))
        stages = {k: v for k, v in (row.get("stages") or {}).items() if k in STAGE_LABEL and v in STATES}
        if not title or not stages:
            continue
        notes = row.get("notes") or {}
        w = by_title.get(title.replace(" ", ""))
        if w is None:
            fmt = row.get("format") if row.get("format") in FORMATS else "장편 영화"
            w = new_work(title, fmt, str(row.get("genre", "")), FORMATS[fmt] + list(stages))   # 포맷 기본 단계 + 정리된 단계
            all_works.append(w)
            by_title[title.replace(" ", "")] = w
            added.append(title)
        else:
            new = [s for s in stages if s not in w["stages"]]
            if new:   # 정리된 단계가 작품에 없으면 순서대로 끼워 넣습니다
                w["stages"] = [s for s in STAGE_ORDER if s in w["stages"] or s in new]
                for s in new:
                    w["state"][s], w["note"][s] = "대기", ""
            w["archived"] = False
            updated.append(title)
        for s, state in stages.items():
            note = str(notes.get(s, "")).strip()
            if w["state"].get(s) != state or (note and note != w["note"].get(s)):
                set_stage(w, s, state, note)
    return added, updated
