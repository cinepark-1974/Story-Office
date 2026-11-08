"""엔진 결과물 JSON을 읽어 작품 현황판에 붙여 넣을 글을 만듭니다.

Claude가 드라이브 폴더를 정리할 때 쓰는 도구입니다. 앱은 이 파일을 쓰지 않습니다.
사용법:  python tools/read_outputs.py 파일1.json 파일2.json ...

엔진 구분 규칙은 실제 결과물 샘플(〈부활〉, 2026-10)에서 확인한 것입니다.
  Idea       _idea_engine_meta 가 있음 → verdict, hook_score
  Creator    _meta.blue_jeans_engine == "Creator Engine" → _meta.stage (Tone완료·씬리스트잠금이면 완료)
  Writer     _meta.beats_progress "15/15" → 다 차면 완료
  Rewrite    engine_version 이 "Rewrite Engine" 으로 시작 → chris_analysis 점수와 판정
  Revise     schema_version 이 "revise_verify" 로 시작 → round_n, overall_score (검증 보고서라 '진행'으로 둠)
  번역       _meta.stage_progress + session.stage_N_result → 본문 글자로 영어·일본어 구분
아래는 샘플 대신 각 엔진의 저장 코드(GitHub)에서 확인한 형식입니다.
  Series     _meta.engine == "Series Engine" → 써진 회차 / 전체 회차
  Novel      _novel_engine 이 있음 → 제목만 (진행 정도는 저장본에 표시가 없음)
  WebNovel   _engine_version + concept_card → 써진 화 수
  Wuxia      version == "wuxia-1.0" + concept_card → 써진 화 수
  FMV        project + branches + scenes → 씬 수
  Shortform  JSON 저장이 없어 DOCX 파일 이름으로만 판단
"""

import json
import re
import sys
import unicodedata

ORDER = ["IDEA", "CREATOR", "WRITER", "SERIES", "WEBNOVEL", "NOVEL", "WUXIA", "SHORTFORM", "FMV",
         "REWRITE", "REVISE", "ENGLISH", "JAPANESE"]


def _title(t: str) -> str:
    """'부활_수정본_R2추가수정_20261003_Blue_복사본' → '부활'"""
    return re.split(r"[_]", (t or "").strip())[0].strip()


def _frac(s: str) -> tuple[int, int]:
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(s or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _lang(session: dict) -> str:
    text = " ".join(str(v) for k, v in session.items() if k.startswith("stage_") and isinstance(v, str))[:20000]
    kana = len(re.findall(r"[぀-ヿ]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "JAPANESE" if kana > latin * 0.2 else "ENGLISH"


def read(d: dict) -> dict | None:
    """결과물 하나 → {"title", "stage", "state", "note", "date"} 또는 None(모르는 파일)"""
    r = _read(d)
    if r:   # Mac에서 온 제목은 한글 자모가 쪼개져 있어(NFD) 같은 제목도 다르게 보입니다
        r["title"] = unicodedata.normalize("NFC", r["title"]).strip()
    return r


def _read(d: dict) -> dict | None:
    if "_idea_engine_meta" in d:
        m = d["_idea_engine_meta"]
        return {"title": d.get("title", ""), "stage": "IDEA", "state": "완료",
                "note": f"{m.get('verdict', '')} · Hook {m.get('hook_score', '')}".strip(" ·"),
                "date": str(m.get("generated_at", ""))[:10], "format": d.get("format", ""), "genre": d.get("genre", "")}
    meta = d.get("_meta") or {}
    if meta.get("blue_jeans_engine") == "Creator Engine":
        p = d.get("project") or {}
        stage = meta.get("stage", "")
        done = stage in ("Tone완료", "씬리스트잠금")
        return {"title": p.get("title") or (p.get("seed_locked") or {}).get("title_kr", ""), "stage": "CREATOR",
                "state": "완료" if done else "진행", "note": stage, "date": str(meta.get("saved_at", ""))[:10]}
    if "beats_progress" in meta:
        n, t = _frac(meta["beats_progress"])
        return {"title": meta.get("title", ""), "stage": "WRITER", "state": "완료" if t and n >= t else "진행",
                "note": f"{n}/{t}비트", "date": str(meta.get("saved_at", ""))[:10]}
    if str(d.get("engine_version", "")).startswith("Rewrite Engine"):
        ca = d.get("chris_analysis") or {}
        score = (ca.get("mark") or {}).get("final", "")
        verdict = (ca.get("verdict") or {}).get("status", "")
        return {"title": d.get("title", ""), "stage": "REWRITE", "state": "완료",
                "note": f"{score}점 {verdict}".strip(), "date": str(d.get("report_date", ""))[:10]}
    if str(d.get("schema_version", "")).startswith("revise_verify"):
        return {"title": d.get("title", ""), "stage": "REVISE", "state": "진행",
                "note": f"R{d.get('round_n', '')} {d.get('overall_score', '')}점", "date": str(d.get("report_date", ""))[:10]}
    if "stage_progress" in meta and isinstance(d.get("session"), dict):
        n, t = _frac(meta["stage_progress"])
        lang = "JAPANESE" if meta.get("engine") == "Japanese-Translator" else _lang(d["session"])
        return {"title": _title(meta.get("title", "")), "stage": lang, "state": "완료" if t and n >= t else "진행",
                "note": f"{n}/{t}단계", "date": str(meta.get("saved_at", ""))[:10]}
    if meta.get("engine") == "Series Engine":
        n, t = int(meta.get("beats_written") or 0), int(meta.get("num_episodes") or 0)
        return {"title": meta.get("project_title", ""), "stage": "SERIES", "state": "완료" if t and n >= t else "진행",
                "note": f"{n}/{t}화" if t else "", "date": str(meta.get("saved_at", ""))[:10], "format": "OTT 시리즈"}
    if isinstance(d.get("_novel_engine"), dict):
        m = d["_novel_engine"]
        return {"title": m.get("title", ""), "stage": "NOVEL", "state": "진행", "note": "저장본",
                "date": str(m.get("saved_at", ""))[:10], "format": "장편소설"}
    if isinstance(d.get("concept_card"), dict) and ("_engine_version" in d or d.get("version") == "wuxia-1.0"):
        wuxia = d.get("version") == "wuxia-1.0"
        eps = len(d.get("episodes_19") or {}) or len(d.get("episodes_15") or {})
        return {"title": d["concept_card"].get("title", ""), "stage": "WUXIA" if wuxia else "WEBNOVEL", "state": "진행",
                "note": f"{eps}화 원고" if eps else "기획", "date": str(d.get("saved_at") or d.get("_saved_at") or "")[:10],
                "format": "무협" if wuxia else "웹소설"}
    if isinstance(d.get("project"), dict) and "branches" in d and "scenes" in d:
        return {"title": d["project"].get("title", ""), "stage": "FMV", "state": "진행",
                "note": f"씬 {len(d.get('scenes') or [])}개", "date": "", "format": "인터랙티브(FMV)"}
    return None


# 드라이브 작품 폴더 규칙 (Mr. MOON 확정): 폴더 이름 = 작품 제목, 기획과 원고가 있으면 완성
WRITE_STAGE = {"장편 영화": "WRITER", "OTT 시리즈": "SERIES", "웹소설": "WEBNOVEL", "장편소설": "NOVEL",
               "무협": "WUXIA", "숏폼 드라마": "SHORTFORM", "인터랙티브(FMV)": "FMV"}


FOLDER_FORMAT = {"영화": "장편 영화", "시리즈": "OTT 시리즈", "드라마": "OTT 시리즈", "웹소설": "웹소설", "소설": "장편소설",
                 "무협": "무협", "숏폼": "숏폼 드라마", "FMV": "인터랙티브(FMV)"}


def parse_folder_name(name: str) -> tuple[str, str, str]:
    """'01.영화_TAKE OFF(인도네시아)' → ('TAKE OFF', '장편 영화', '인도네시아')"""
    name = unicodedata.normalize("NFC", name).strip()
    name = re.sub(r"^\d+\s*[._]\s*", "", name)            # 앞 번호
    fmt = "장편 영화"
    m = re.match(r"([^_]+)_(.+)", name)
    if m and m.group(1).strip() in FOLDER_FORMAT:
        fmt, name = FOLDER_FORMAT[m.group(1).strip()], m.group(2)
    extra = ""
    m = re.match(r"(.+?)\s*\(([^)]*)\)\s*$", name)
    if m:
        name, extra = m.group(1), m.group(2)
    return name.strip(), fmt, extra.strip()


def from_folder(title: str, folders: dict, fmt: str = "장편 영화") -> dict:
    """folders: {"02_기획개발": [파일 이름…], "03_원고": [...], "04_번역": [...]} → 붙여 넣을 한 줄"""
    def has(prefix: str) -> list:
        return [f for k, v in folders.items() if k.startswith(prefix) for f in (v or [])]
    plan, draft, trans = has("02"), has("03"), has("04")
    stages, notes = {}, {}
    if plan or draft:
        stages["IDEA"] = "완료"
    if plan:
        stages["CREATOR"] = "완료"
    w = WRITE_STAGE.get(fmt, "WRITER")
    if draft:
        stages[w] = "완료"
    elif plan:
        stages[w] = "대기"
    for f in has("01"):   # 엔진 보고서는 이름으로 덤 표시
        if re.search(r"rewrite|리라이트", unicodedata.normalize("NFC", f), re.I):
            stages["REWRITE"] = "완료"
    for f in trans:
        name = unicodedata.normalize("NFC", f)
        if re.search(r"영어|english|_eng?[_.]", name, re.I):
            stages["ENGLISH"] = "완료"
        elif re.search(r"일본|japanese|_ja[_.]|_jp[_.]", name, re.I):
            stages["JAPANESE"] = "완료"
    return {"title": unicodedata.normalize("NFC", title).strip(), "format": fmt, "genre": "",
            "stages": {s: stages[s] for s in ORDER if s in stages}, "notes": notes}


def build(records: list[dict]) -> dict:
    """같은 작품·같은 단계는 날짜가 늦은 것을 씁니다."""
    works: dict[str, dict] = {}
    for r in records:
        key = r["title"].replace(" ", "")
        w = works.setdefault(key, {"title": r["title"], "format": "", "genre": "", "stages": {}, "notes": {}, "_date": {}})
        fmt = {"영화": "장편 영화"}.get(r.get("format", ""), r.get("format", ""))
        if fmt and not w["format"]:
            w["format"] = fmt
        if r.get("genre") and not w["genre"]:
            w["genre"] = r["genre"]
        if r["date"] >= w["_date"].get(r["stage"], ""):
            w["stages"][r["stage"]] = r["state"]
            w["notes"][r["stage"]] = r["note"]
            w["_date"][r["stage"]] = r["date"]
    out = []
    for w in works.values():
        w.pop("_date")
        w["stages"] = {s: w["stages"][s] for s in ORDER if s in w["stages"]}
        out.append(w)
    return {"works": out}


if __name__ == "__main__":
    recs, unknown = [], []
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            r = read(json.load(f))
        (recs.append(r) if r else unknown.append(path))
    for r in recs:
        print(f"{r['title']:<10} {r['stage']:<9} {r['state']}  {r['note']}  ({r['date']})", file=sys.stderr)
    for u in unknown:
        print("모르는 파일:", u, file=sys.stderr)
    print(json.dumps(build(recs), ensure_ascii=False))
