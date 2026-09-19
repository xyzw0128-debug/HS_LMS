# 🛠️ LMS Notifier — 개발자 및 기여자를 위한 기술 문서 (DEVELOPER.md)

본 문서는 **한신대학교 LMS 디스코드 알림봇**의 내부 아키텍처, 프로토콜 리버스 엔지니어링 분석, 모듈별 인터페이스 및 로컬 개발/기여 가이드를 다룹니다.

---

## 📐 1. 시스템 전체 아키텍처 (System Architecture)

본 프로그램은 상시 동작하는 **경량 단일 프로세스 폴링 데몬(Polling Daemon)**으로 설계되었으며, 불필요한 WebSocket 게이트웨이 상시 연결 없이 **Discord Webhook REST API (`PATCH`/`POST`)**만으로 대시보드 상태를 동기화합니다.

```mermaid
flowchart TB
    subgraph CoreLoop ["Main Loop (main.py)"]
        A[Start / Tick] --> B[Hot-Reload settings.json]
        B --> C[Check Local Deadline Reminders]
        C --> D{Is Active Time?}
        D -- No --> E[Sleep 60s & Loop]
        D -- Yes --> F{Auth Locked?}
        F -- Yes --> E
        F -- No --> G[poll_once]
        G --> H[Sleep poll_interval_sec]
        H --> A
    end

    subgraph LMSClient ["LmsSession (lms_client.py)"]
        G --> L1[SSO Auth Handshake]
        L1 --> L2[Scrape Course List]
        L2 --> L3[Scrape Classroom Detail]
        L3 --> L4[Scrape Board Item Detail]
    end

    subgraph ParserEngine ["Parser Engine (parser.py)"]
        L2 & L3 & L4 --> P1[BeautifulSoup4 HTML Parse]
        P1 --> P2[Extract Assignments / Lectures / Notices]
    end

    subgraph AIModule ["AI & Heuristics (ai_summarizer.py)"]
        P2 --> S1{Gemini API Key?}
        S1 -- Yes --> S2[Gemini 3.8 Flash SDK]
        S1 -- No / Fallback --> S3[Local Regex Heuristic Engine]
    end

    subgraph NotifierEngine ["Discord Notifier (notifier.py)"]
        P2 & S2 & S3 --> N1[Build Embeds]
        N1 --> N2[Discord Webhook PATCH / POST]
        N1 --> N3[Send Alert Ping on New Items]
    end

    subgraph Storage ["State & Persistence"]
        N2 --> ST1[state.json (Seen Items & Message IDs)]
        B --> ST2[settings.json (Active Hours & Interval)]
    end
```

---

## 🔍 2. 한신대 SSO / LMS 프로토콜 리버스 엔지니어링

웹 브라우저의 HAR 네트워크 트래픽 캡처를 기반으로 규명된 한신대학교 포털 인증 및 데이터 수집 흐름입니다.

### 2.1 인증 플로우 (SSO Handshake)
* **SSO Base**: `https://sso2.hs.ac.kr`
* **LMS Base**: `https://lms.hs.ac.kr`
* **SSO Client ID**: `5f0869ab6c0f4178874754fbd6c5bf64`
1. `LmsSession` 초기화 시 `requests.Session`을 생성하고 사용자 에이전트(User-Agent)를 최신 데스크톱 브라우저로 위장합니다.
2. `POST https://sso2.hs.ac.kr/sso/login`:
   - Payload: `user_id`, `user_pw`, `client_id`
   - 인증 성공 시 SSO 세션 쿠키 발급 및 리다이렉트 처리.
3. `GET https://lms.hs.ac.kr/sso/login.dunet`:
   - SSO 토큰을 통해 LMS 도메인의 세션 쿠키(`WMONID`, `SESSION` 등)를 획득합니다.
4. **세션 유지 정책**:
   - 디스크에 세션 쿠키를 캐싱하지 않고 인메모리에서만 관리합니다.
   - 요청 전 `ensure_login()`을 통해 세션 유효성을 체크하며, 만료 감지 시 자동 재인증을 수행합니다.

### 2.2 강의실 및 게시판 조회 프로토콜
* **나의 강의실 목록**: `doListView.dunet?mnid=201008840728`
* **개별 강의실 활성화**: 한신대 LMS는 특정 강의실 정보를 읽기 전에 반드시 세션 활성화 요청(`doSetSessionClassRoom.dunet?course_id={id}&class_no={no}`)을 호출해야 해당 과목의 세션 컨텍스트가 로드됩니다.
* **강의실 대시보드 스크랩**: `doViewClassRoom.dunet?mnid=201008254671`
* **게시글 상세 본문 조회**: `doViewBoardItem.dunet?board_no={no}&boarditem_no={no}`

---

## 📂 3. 모듈별 역할 및 인터페이스 정의

```text
lms_notifier/
├── config.py          # 환경변수 로딩 (.env) 및 고정 프로토콜 상수
├── lms_client.py      # SSO 로그인 세션 및 LMS HTTP 통신 래퍼
├── parser.py          # BeautifulSoup 기반 HTML 파싱 엔진
├── ai_summarizer.py   # Gemini 3.8 Flash 연동 및 규칙 기반 로컬 요약 엔진
├── notifier.py        # Discord Embed 빌더 및 Webhook PATCH/POST 클라이언트
├── settings.py        # settings.json 관리, 유효성 검증, CLI 대화형 마법사
├── state.py           # state.json 관리 (원자적 파일 저장 0o600)
└── main.py            # 메인 루프 데몬, 스케줄러, 리마인더 타이머, CLI 진입점
```

### 3.1 `lms_notifier/notifier.py`
* **`patch_webhook_message(message_id, payload)`**:
  - `PATCH /api/webhooks/{id}/{token}/messages/{message_id}` 엔드포인트를 호출합니다.
  - 디스코드에서 사용자가 메시지를 수동 삭제하여 `404 Not Found`가 반환되면 `False`를 반환하고, 상위 호출자가 `post_webhook_message`로 재생성하도록 유도합니다.
* **`_request_with_rate_limit(method, url, **kwargs)`**:
  - 디스코드 `429 Too Many Requests` 감지 시 응답 본문 또는 헤더의 `Retry-After` 초를 파싱하여 백오프 슬립 후 최대 2회 자동 재시도합니다.
* **`format_dashboard_footer(now_str, settings)`**:
  - 현재 로드된 `settings` 딕셔너리(`weekday_active_hours`, `weekend_active_hours`, `poll_interval_sec`)를 기반으로 Embed 풋터 문자열을 동적 포맷팅합니다.

### 3.2 `lms_notifier/settings.py` & `main.py` (Hot-Reload Architecture)
* **무중단 실시간 핫리로드(Hot-Reloading)**:
  - 데몬 프로세스가 종료되지 않고 실행 중인 상태에서 매 루프(`while True`) 시작 시 `settings = load_settings()`를 호출합니다.
  - 직전 설정 객체(`prev_settings`)와 변경 여부를 딥 비교(`!=`)하여, 파일 변경 시 재시작 없이 즉시 새 시간대와 주기로 수렴합니다.
* **대화형 마법사 (`run_setup_wizard`)**:
  - `python -m lms_notifier.main --setup` 진입 시 stdin/stdout을 통한 대화형 CLI를 제공합니다.
  - `validate_time_range()` 함수를 통해 정규식 `^([0-1]?\d|2[0-3]):[0-5]\d-([0-1]?\d|2[0-4]):[0-5]\d$` 유효성을 검증합니다.

### 3.3 `lms_notifier/ai_summarizer.py`
* **OWASP LLM01 방어**:
  - Google GenAI SDK 사용 시 `system_instruction`에 요약 지침을 분리 주입하고, 입력 텍스트를 `<notice>{body}</notice>`로 감쌉니다.
* **피싱 URL 살균**:
  - `re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)`로 마크다운 링크 위장을 해제하고, `http://`, `https://`, `www.` 링크를 `[외부 링크]`로 치환합니다.
* **로컬 폴백 엔진 (`local_summarize_notice`)**:
  - Gemini API 키가 없거나 네트워크 오류 시, 본문 문장을 분리한 후 중요 키워드(`과제`, `제출`, `마감`, `시험`, `휴강`, `보강`, `장소` 등) 가중치 점수를 매겨 상위 3개 문장을 자동 추출합니다.

---

## 🔒 4. 보안 및 신뢰성 설계 패턴

1. **원자적 파일 교체 (Atomic File Swap)**:
   - `state.py`와 `settings.py`의 디스크 저장 로직은 `os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)`으로 임시 파일을 생성한 후 `os.replace`로 원자적으로 치환합니다.
   - 비정상 프로세스 종료 시에도 원본 파일이 깨지지 않는 원자성을 보장합니다.
2. **로그 마스킹 (`RedactingFormatter`)**:
   - `logging.Formatter`를 상속받은 커스텀 포매터가 `/api/webhooks/\d+/[\w-]+`, `HS_USER_ID`, `HS_USER_PW`, `GEMINI_API_KEY`를 정규식으로 감지하여 `<redacted_*>`로 치환합니다.
   - 예외 스택트레이스가 터져도 민감정보가 stdout 및 journald에 남지 않습니다.
3. **계정 잠금 방지 서킷 브레이커 (Circuit Breaker)**:
   - SSO 로그인 실패가 연속 3회 발생하면 내부 플래그 `auth_locked = True`를 활성화하고 LMS 폴링을 영구 대기 상태로 전환합니다.
   - 단, 로컬에 이미 저장된 과제 마감 리마인더 감시 타이머는 중단 없이 정상 작동합니다.

---

## 💻 5. 로컬 개발 및 테스트 환경 구축

### 5.1 요구사항
* Python 3.10 이상 (`dict | None` 유니온 타입 힌트 및 `zoneinfo.ZoneInfo` 사용)
* 가상환경 사용 필수

### 5.2 개발 환경 셋업
```bash
# 저장소 클론 및 가상환경 구성
git clone https://github.com/xyzw0128-debug/HS_LMS.git
cd HS_LMS
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발용 .env 생성
cp .env.example .env
# .env에 테스트용 HS_USER_ID, HS_USER_PW, DISCORD_WEBHOOK_URL 작성
```

### 5.3 단위 테스트 및 정적 검증
```bash
# 구문 컴파일 무결성 검증
venv/bin/python -m py_compile lms_notifier/*.py

# CLI 플래그 및 마법사 테스트
venv/bin/python -m lms_notifier.main --help
venv/bin/python -m lms_notifier.main --setup

# 임베드 포매팅 및 풋터 동적 생성 테스트
venv/bin/python -c "
from lms_notifier.settings import load_settings
from lms_notifier.notifier import format_dashboard_footer
s = load_settings()
print(format_dashboard_footer('2026-09-19 12:00:00', s))
"
```

---

## 🤝 6. 기여 가이드라인 (Contributing)

1. **코딩 스타일**:
   - PEP 8 가이드라인을 준수하며, 명시적인 타입 힌트(`typing`)를 반드시 작성해주세요.
   - 모듈 최상단에 `from __future__ import annotations`를 선언합니다.
2. **보안 원칙 준수**:
   - 새 파일 생성 시 반드시 `0o600` 권한 제어가 적용되었는지 확인하세요.
   - 로그 출력부에 원시 웹훅 URL이나 인증 토큰이 그대로 노출되지 않도록 주의하세요.
3. **풀 리퀘스트(PR) 프로세스**:
   - `git checkout -b feature/your-feature-name`
   - 변경 사항을 작업한 뒤 `py_compile` 무결성 검사를 통과해야 합니다.
   - PR 설명에 변경 동기와 테스트 결과를 명확히 기재해주세요.
