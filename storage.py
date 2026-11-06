"""STORY OFFICE 기록 보관함 (Cloudflare R2).

R2는 파일을 넣어 두는 클라우드 창고입니다. 스토리오피스는 버킷 안의
storyoffice/ 폴더에만 씁니다.

  storyoffice/scans/20261107_0130_ab12cd34.json   판별 한 번의 결과 전체
  storyoffice/decisions/thriller.json             장르 담당별로 Mr. MOON이 넘긴 것과 버린 것

Secrets 네 개(R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET)가
없으면 보관함 없이도 사무실은 그대로 돌아갑니다.
"""

import json
from datetime import datetime, timedelta, timezone

PREFIX = "storyoffice/"
KST = timezone(timedelta(hours=9))

# 장르 담당 이름 → 파일 이름 (R2 파일 이름은 영문이 안전합니다)
DESK_SLUG = {
    "": "general", "로맨틱 코미디": "romcom", "스릴러": "thriller", "호러": "horror", "드라마": "drama",
    "코미디": "comedy", "액션": "action", "느와르": "noir", "SF": "sf", "미스터리": "mystery",
    "판타지": "fantasy", "시대극": "period",
}
SECRET_NAMES = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


class Archive:
    def __init__(self, account_id: str, key_id: str, secret: str, bucket: str, endpoint: str | None = None):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint or f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            region_name="auto",
            config=Config(retries={"max_attempts": 3}, connect_timeout=5, read_timeout=15),
        )

    # ── 기본 읽기·쓰기 ──
    def _put(self, key: str, data) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
        self.s3.put_object(Bucket=self.bucket, Key=PREFIX + key, Body=body,
                           ContentType="application/json; charset=utf-8")

    def _get(self, key: str, default=None):
        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key=PREFIX + key)
        except self.s3.exceptions.NoSuchKey:
            return default
        return json.loads(obj["Body"].read().decode("utf-8"))

    def check(self) -> None:
        """연결 확인. 열쇠나 버킷 이름이 틀리면 여기서 오류가 납니다."""
        self.s3.list_objects_v2(Bucket=self.bucket, Prefix=PREFIX, MaxKeys=1)

    # ── 판별 결과 ──
    def save_scan(self, scan_id: str, job: dict) -> str:
        now = datetime.fromtimestamp(job["started"], KST)
        key = f"scans/{now:%Y%m%d_%H%M}_{scan_id}.json"
        self._put(key, {"id": scan_id, "started_label": job["started_label"], "elapsed": job["elapsed"],
                        "direction": job["direction"], "genre": job["genre"], "result": job["result"]})
        return key

    def list_scans(self, limit: int = 30) -> list[str]:
        keys, token = [], None
        while True:
            kw = {"Bucket": self.bucket, "Prefix": PREFIX + "scans/"}
            if token:
                kw["ContinuationToken"] = token
            res = self.s3.list_objects_v2(**kw)
            keys += [o["Key"][len(PREFIX):] for o in res.get("Contents", [])]
            if not res.get("IsTruncated"):
                break
            token = res.get("NextContinuationToken")
        return sorted(keys, reverse=True)[:limit]   # 파일 이름이 날짜순이라 최신이 위로

    def load_scan(self, key: str) -> dict | None:
        return self._get(key)

    # ── 넘김·버림 기록 ──
    def decisions(self, genre: str) -> list[dict]:
        return self._get(f"decisions/{DESK_SLUG.get(genre, 'general')}.json", default=[])

    def record(self, genre: str, scan_id: str, item: dict, decision: str, reason: str = "") -> None:
        rows = [r for r in self.decisions(genre)
                if not (r.get("scan") == scan_id and r.get("name") == item["name"])]   # 같은 소재는 마지막 결정만
        rows.append({
            "date": f"{datetime.now(KST):%Y-%m-%d %H:%M}", "scan": scan_id, "decision": decision,
            "reason": reason.strip(), "name": item["name"], "where_when": item.get("where_when", ""),
            "fact": item.get("fact", ""), "seed": item.get("seed", ""),
        })
        self._put(f"decisions/{DESK_SLUG.get(genre, 'general')}.json", rows)

    def decided(self, genre: str, scan_id: str) -> dict:
        """이번 판별에서 이미 결정한 소재: {소재 이름: '넘김'|'버림'}"""
        return {r["name"]: r["decision"] for r in self.decisions(genre) if r.get("scan") == scan_id}


def from_secrets(get) -> "Archive | None":
    """get(이름) -> 값. 네 값이 다 있을 때만 보관함을 엽니다."""
    vals = [str(get(n) or "").strip() for n in SECRET_NAMES]
    if not all(vals):
        return None
    return Archive(*vals)


def memory_note(rows: list[dict], keep: int = 12) -> str:
    """장르 담당이 소재를 찾기 전에 읽는 지난 기록. 최근 것만 짧게."""
    passed = [r for r in rows if r["decision"] == "넘김"][-keep:]
    dropped = [r for r in rows if r["decision"] == "버림"][-keep:]
    if not passed and not dropped:
        return ""
    lines = ["[지난 기록] Mr. MOON이 이 담당의 소재를 고른 결과다. 같은 소재는 다시 가져오지 않는다. "
             "넘긴 소재와 겹치는 결은 더 찾고, 버린 이유에 해당하는 소재는 피한다. 소재를 흉내 내지 않는다."]
    if passed:
        lines.append("넘김: " + " / ".join(f"{r['name']} ({r['where_when']})" for r in passed))
    if dropped:
        lines.append("버림: " + " / ".join(f"{r['name']}" + (f" (이유: {r['reason']})" if r.get("reason") else "")
                                         for r in dropped))
    return "\n".join(lines)
