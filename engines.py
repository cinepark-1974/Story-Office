"""STORY ENGINE SYSTEM 엔진 목록.

엔진을 추가하거나 주소가 바뀌면 이 파일만 고치면 됩니다.
- repo : GitHub 저장소 이름 (cinepark-1974 계정 아래)
- url  : Streamlit 앱 주소. 배포 안 된 엔진은 None
- orbit: 성계 그림에서의 자리
    ("inner", 각도)  안쪽 궤도 — 핵심 라인과 번역
    ("outer", 각도)  바깥 궤도 — OSMU 라인
    ("free", x, y)   궤도 밖 단독 별 (그림 좌표 1200×720 기준)
  각도는 시계 방향, 0 = 오른쪽, 90 = 아래, 180 = 왼쪽, 270 = 위
- 묶음과 순서는 『스토리엔진시스템 설명서』(2026.09) 34~39쪽 기준
"""

GITHUB_OWNER = "cinepark-1974"

# 엔진 개발실 — 각 엔진의 "project" 는 그 엔진을 고치는 claude.ai 프로젝트방입니다.
# 시스템 전체(공통 설계·공통 팩)를 다루는 방:
SYSTEM_PROJECT = "https://claude.ai/project/01a08683-2355-7541-9453-28d80286f266"  # STORY ENGINE SYSTEM

# Writer's Partner — 엔진이 아니라 엔진들이 못 하는 손질을 맡는 파트너.
PARTNER = {
    "name": "Writer's Partner",
    "url": "https://claude.ai/project/019e39e3-69f1-72c6-89b8-852f834158b7",  # claude.ai Writer's Partner 프로젝트
    "desc": "엔진이 못 하는 손질을 맡습니다. 문장 호흡, 장면 정서, 대사 결, 엔진 출력물 다듬기를 대화로 함께합니다.",
    "orbit": ("outer", 90),  # 보는 사람 쪽, 성계의 맨 앞
}

# 사무실 그림(static/office.webp, 1672×941) 위의 자리. (왼쪽, 위, 오른쪽, 아래) 픽셀 좌표.
# 엔진의 "desk" 값이 여기 이름과 같으면 그 사람을 누를 때 그 엔진이 열립니다.
OFFICE_W, OFFICE_H = 1672, 941
DESKS = {
    # 원형 테이블 — 핵심 라인 (바통은 화면에서 시계 방향)
    "idea":      (660, 375, 790, 560),    # 앞 왼쪽
    "creator":   (590, 240, 700, 372),    # 왼쪽, OSMU 테이블 쪽
    "writer":    (790, 170, 885, 290),    # 뒤쪽
    "rewrite":   (1030, 245, 1135, 372),  # 오른쪽, 결재석 쪽
    "revise":    (955, 375, 1080, 560),   # 앞 오른쪽, 번역 데스크 쪽
    # 왼쪽 벽 긴 테이블 — OSMU
    "series":    (262, 105, 350, 230),
    "webnovel":  (185, 150, 262, 270),
    "novel":     (100, 190, 185, 330),
    # 단독 책상
    "wuxia":     (50, 380, 170, 515),     # 책 읽는 사람
    "shortform": (215, 445, 325, 600),    # 휴대폰 든 사람
    "fmv":       (425, 545, 560, 720),    # 분기도 모니터 앞 사람
    # 번역 데스크 — 출구 쪽
    "english":   (1240, 485, 1370, 665),
    "japanese":  (1415, 425, 1535, 580),
    # 사람이 아닌 자리
    "converter": (415, 75, 540, 230),     # 복합기
    "partner":   (730, 690, 950, 878),    # 문 앞 로봇 (바닥을 천천히 돌아다니는 범위까지)
    "boss":      (1165, 45, 1310, 175),   # MR. MOON 결재석
}

GROUPS = [
    {
        "name": "핵심 라인",
        "note": "IDEA → CREATOR → WRITER → REWRITE → REVISE 순서로 바통을 넘깁니다.",
        "engines": [
            {
                "name": "Idea Engine", "short": "IDEA", "desk": "idea", "repo": "Idea-Engine",
                "project": "https://claude.ai/project/019e2b9d-142f-72d9-8f32-194dba0d1b77",
                "url": "https://idea-engine.streamlit.app/", "orbit": ("inner", 180),
                "desc": "모호한 아이디어 한 줄을 조사·판정해 Creator가 이어받을 시드로 만듭니다.",
            },
            {
                "name": "Creator Engine", "short": "CREATOR", "desk": "creator", "repo": "Creator-Engine",
                "project": "https://claude.ai/project/019e34e4-d885-731c-8f22-acf7838a5726",
                "url": "https://creator-engine.streamlit.app/", "orbit": ("inner", 225),
                "desc": "아이디어를 구조화해 트리트먼트를 포함한 기획개발 보고서로 펼칩니다.",
            },
            {
                "name": "Writer Engine", "short": "WRITER", "desk": "writer", "repo": "Writer-Engine",
                "project": "https://claude.ai/project/019e34ba-3fdd-774f-ae45-ccdb62e9b7f3",
                "url": "https://writer-engine.streamlit.app/", "orbit": ("inner", 270),
                "desc": "기획개발 보고서에서 출발해 15비트를 거쳐 시나리오를 출력합니다.",
            },
            {
                "name": "Rewrite Engine", "short": "REWRITE", "desk": "rewrite", "repo": "Rewrite-Engine",
                "project": "https://claude.ai/project/019e3499-004f-753f-b857-e8e21206bdcc",
                "url": "https://rewriteengine.streamlit.app/", "orbit": ("inner", 315),
                "desc": "원고를 분석·진단해 커버리지를 내고 처방을 Revise로 넘깁니다.",
            },
            {
                "name": "Revise Engine", "short": "REVISE", "desk": "revise", "repo": "Revise-Engine",
                "project": "https://claude.ai/project/019e352c-07c9-7751-9aca-f60b954eaccb",
                "url": "https://revise-engine.streamlit.app/", "orbit": ("inner", 0),
                "desc": "Writer의 원고와 Rewrite의 처방전을 들고 각색과 윤문을 합니다.",
            },
        ],
    },
    {
        "name": "OSMU 라인",
        "note": "Creator의 기획 데이터를 함께 씁니다.",
        "engines": [
            {
                "name": "Series Engine", "short": "SERIES", "desk": "series", "repo": "Series-Engine",
                "project": "https://claude.ai/project/019e2eb3-5515-7678-aa01-80b0ccdd94c7",
                "url": "https://seriesengine.streamlit.app/", "orbit": ("outer", 196),
                "desc": "OTT 시리즈 시즌 1을 시즌 아크부터 회차 대본까지 씁니다.",
            },
            {
                "name": "WebNovel Engine", "short": "WEBNOVEL", "desk": "webnovel", "repo": "WebNovel-Engine",
                "project": "https://claude.ai/project/019e3954-6444-770f-b6dc-e68b57e47e77",
                "url": "https://webnovel-engine.streamlit.app/", "orbit": ("outer", 222),
                "desc": "한국 웹소설 시장 기준으로 연재물을 처음부터 끝까지 씁니다.",
            },
            {
                "name": "Novel Engine", "short": "NOVEL", "desk": "novel", "repo": "Novel-Engine",
                "project": "https://claude.ai/project/019f8398-9c69-7443-b5db-5f1e72e6aae6",
                "url": "https://novel-engine.streamlit.app/", "orbit": ("outer", 248),
                "desc": "영화의 속도감을 가진 시네마틱 장편소설을 씁니다.",
            },
        ],
    },
    {
        "name": "단독 엔진",
        "note": "기획부터 집필까지 혼자 진행합니다.",
        "engines": [
            {
                "name": "Wuxia Engine", "short": "WUXIA", "desk": "wuxia", "repo": "Wuxia-Engine",
                "project": "https://claude.ai/project/019e3dda-5d7d-73a6-904d-8162c0b03b9d",
                "url": "https://wuxia-engine.streamlit.app/", "orbit": ("free", 110, 560),
                "desc": "정통 무협과 회빙환·시스템·학원 무협 웹소설을 씁니다.",
            },
            {
                "name": "Shortform Engine", "short": "SHORTFORM", "desk": "shortform", "repo": "Shortform-Engine",
                "url": "https://shortform-engine.streamlit.app/", "orbit": ("free", 230, 655),
                "desc": "1~2분 × 80~100화 세로형 숏폼 드라마 대본을 씁니다.",
            },
            {
                "name": "FMV Engine", "short": "FMV", "desk": "fmv", "repo": "FMVWriting-Engine",
                "project": "https://claude.ai/project/019f7fd9-5839-74ec-b344-b99c10e7d106",
                "url": "https://fmvwriting-engine.streamlit.app/", "orbit": ("free", 1090, 110),
                "desc": "실사 인터랙티브 드라마의 분기 설계와 각본을 씁니다.",
            },
        ],
    },
    {
        "name": "해외",
        "note": "완성 원고를 다른 시장의 언어로 옮깁니다.",
        "engines": [
            {
                "name": "English Translator", "short": "ENGLISH", "desk": "english", "repo": "English-Translator",
                "project": "https://claude.ai/project/019e903b-93a7-75c2-a509-e8bd7f00ab27",
                "url": "https://english-translator.streamlit.app/", "orbit": ("inner", 38),
                "desc": "한국어 시나리오를 네이티브 수준 영문 시나리오로 옮깁니다.",
            },
            {
                "name": "Japanese Translator", "short": "JAPANESE", "desk": "japanese", "repo": "Japanese-Translator",
                "project": "https://claude.ai/project/019e903b-93a7-75c2-a509-e8bd7f00ab27",
                "url": "https://japanese-translator.streamlit.app/", "orbit": ("inner", 70),
                "desc": "한국어 시나리오를 일본 시장에 맞춘 일본어 시나리오로 옮깁니다.",
            },
        ],
    },
    {
        "name": "도구",
        "note": "",
        "engines": [
            {
                "name": "Screenplay Converter", "short": "CONVERTER", "desk": "converter", "repo": "ScreeplayConverter",
                "url": None, "orbit": ("free", 1090, 650),
                "desc": "TXT·DOCX 원고의 메타 텍스트를 걷어내고 시나리오 서식 DOCX로 바꿉니다.",
            },
        ],
    },
]
