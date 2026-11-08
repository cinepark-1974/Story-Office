# STORY OFFICE

BLUE JEANS PICTURES 창작 사무실. STORY ENGINE SYSTEM의 엔진 14개를 한 화면에서 보고 바로 엽니다.

- **OFFICE** — 사무실 그림. 직원(엔진)을 누르면 그 엔진의 Streamlit 앱이 열립니다.
- **SYSTEM** — 『스토리엔진시스템 설명서』와 짝을 이루는 성계 쇼룸. 엔진 행성들이 중심 구체 둘레를 천천히 돕니다.

- **아이디어 판별** — 버튼을 누를 때만 일합니다. Claude 호출 두 번.
  1. 소재 발굴 담당(또는 고른 장르 담당)이 전 세계 현실 소재 5~8개를 검색합니다. 장르 담당은 그 장르만의 자료처를 뒤집니다.
  2. 판별 담당이 소재마다 ① 결핍·상실을 가진 사람 ② 원하는 것과 막는 것 ③ 역전 (장르 담당이면 ④ 장르의 재미)이 서는지만 가립니다.
  - 이야기를 지어내지 않습니다. '있음'인 소재만 Idea Engine으로 넘기고, 키우는 일은 Idea Engine이 합니다.

  - '있음' 소재마다 넘김·버림을 남기면, 그 장르 담당이 다음 판별 때 자기 기록을 읽고 시작합니다.

- **작품 현황판** — 엔진으로 개발 중인 작품과 단계(아이디어 ▶ 기획개발 ▶ 시나리오 ▶ 진단 ▶ 각색·윤문 등). 엔진은 기록을 남기지 않으므로 단계는 사무실에서 직접 표시합니다.

장르 담당의 자료처와 장르 기준은 `staff.py` 의 GENRE_DESKS 에서 고칩니다.

## Streamlit Secrets

```
ANTHROPIC_API_KEY = "엔진들이 쓰는 키"
OFFICE_PASSWORD = "사무실 비밀번호"
R2_ACCOUNT_ID = "Cloudflare MY AI OFFICE 계정 ID"
R2_ACCESS_KEY_ID = "..."
R2_SECRET_ACCESS_KEY = "..."
R2_BUCKET = "story-office"
```

앞의 둘이 없으면 판별 버튼이 열리지 않습니다. R2 넷이 없으면 판별은 되지만 기록 보관, 지난 판별, 작품 현황판이 꺼집니다.

## R2 보관함 (버킷 story-office, storyoffice/ 폴더만 씀)

| 위치 | 내용 |
|---|---|
| `storyoffice/scans/날짜_번호.json` | 판별 한 번의 결과 전체 |
| `storyoffice/decisions/장르.json` | 장르 담당별 넘김·버림 기록 (thriller, horror …, 장르 없음은 general) |
| `storyoffice/works.json` | 작품 현황판 |

## 파일

| 파일 | 하는 일 |
|---|---|
| `main.py` | 화면 전체 (Streamlit 시작 파일) |
| `engines.py` | 엔진 목록, 한 줄 설명, 앱 주소, 사무실 자리, 성계 궤도 — **엔진을 추가하거나 주소가 바뀌면 이 파일만 고칩니다** |
| `staff.py` | 소재 발굴·판별 담당과 장르 담당(GENRE_DESKS) |
| `storage.py` | R2 보관함 읽기·쓰기 |
| `works.py` | 작품 현황판의 포맷별 단계와 상태 |
| `system_view.py` | 성계 그림과 움직임. 맨 위 숫자 두 개가 한 바퀴 도는 시간(초) |
| `static/office.webp` | 사무실 그림 |
| `static/core.webp` | 성계 중심 구체 |

최근 수정일은 GitHub 공개 기록을 1시간마다 읽어 옵니다.
