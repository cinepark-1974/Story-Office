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
"""

import json
import re
import sys
import unicodedata

ORDER = ["IDEA", "CREATOR", "WRITER", "REWRITE", "REVISE", "ENGLISH", "JAPANESE"]


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
    return None


def build(records: list[dict]) -> dict:
    """같은 작품·같은 단계는 날짜가 늦은 것을 씁니다."""
    works: dict[str, dict] = {}
    for r in records:
        key = r["title"].replace(" ", "")
        w = works.setdefault(key, {"title": r["title"], "format": "", "genre": "", "stages": {}, "notes": {}, "_date": {}})
        if r.get("format") == "영화":
            w["format"] = "장편 영화"
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
