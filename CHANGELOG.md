# 📝 변경 내역 (Changelog)

이 프로젝트의 모든 주요 변경 사항과 버전별 업데이트 내역을 기록합니다.  
본 프로젝트는 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/) 원칙을 따릅니다.

---

## [v3.2] - 2026-09-19

### Added
* **대화형 스케줄 설정 마법사 CLI (`--setup`, `-s`)**:
  * 터미널 질의응답 방식으로 평일/주말 작동 시간대와 대시보드 갱신 주기를 간편하게 변경할 수 있는 CLI 도구 추가.
  * 시간 포맷(`HH:MM-HH:MM`) 및 분 단위 숫자 유효성 검증 로직 내장.
* **스케줄 설정 분리 (`settings.json`) 및 무중단 실시간 핫리로드 (Live Hot-Reloading)**:
  * 보안 시크릿(`.env`)과 일반 런타임 스케줄 설정을 물리적으로 분리.
  * 봇 데몬 실행 중에도 `settings.json` 변경 사항을 실시간 감지하여 재시작 없이 즉시 새 주기 적용.
* **동적 디스코드 임베드 풋터**:
  * 사용자가 변경한 시간대와 주기가 디스코드 전광판 하단 안내 문구(`footer`)에 실시간 반영.

### Changed
* **사용자 중심 문서 구조 전면 개편 (UX 리팩터링)**:
  * **`README.md`**: 디스코드 현황판 실제 텍스트 목업(Preview) 및 이모지 기능 요약표 최상단 배치.
  * **플랫폼별 설치 가이드**: Windows(PowerShell) 탐색기 주소창 꿀팁, 스크립트 실행 권한(`Set-ExecutionPolicy`) 해결법, `notepad .env` 안내 및 macOS/Linux 분기 명령어 병기.
  * **개인정보 투명성 표**: `정보 | 저장 위치 | 전송 대상` 3열 표로 학생들의 비밀번호 불안감 완벽 해소.
  * **FAQ 아코디언화(`<details>`)**: `KeyError: 'HS_USER_ID'`, 계정 잠금 서킷 브레이커 해제법, 초기화(`state.json` 삭제) 및 사용 중단 가이드 추가.
  * **배포 가이드 완급 조절**: 리눅스 `systemd` 서비스 등록법을 `<details>`로 감싸 일반 사용자 스크롤 피로도 방지.
* **`.env.example` 단순화**: 스케줄 관련 변수를 정리하고 필수 3개(`HS_USER_ID`, `HS_USER_PW`, `DISCORD_WEBHOOK_URL`)와 선택 1개(`GEMINI_API_KEY`)만 남겨 직관성 개선.
* **`lms-notifier.service` 템플릿화**: 사용자 계정명 및 디렉토리 경로에 대한 플레이스홀더 및 안내 주석 보강.

### Security
* 보안 아키텍처 기술 백서([`SECURITY.md`](./SECURITY.md)) 독립 분리: 2026 OWASP Top 10 for LLM, 피싱 살균, 로그 마스킹, umask 0600, 통신/공급망 보안, 취약점 제보 절차 수립.

---

## [v3.1] - 2026-09-18

### Security & Reliability
* **2026 OWASP Top 10 for LLM Applications 보안 체계 적용**:
  * `system_instruction` 분리 및 XML 태그(`<notice>`) 컨텍스트 격리를 통한 간접 프롬프트 인젝션(OWASP LLM01:2026) 차단.
  * 공지 본문 3,000자 제한을 통한 자원 고갈 및 DoS(OWASP LLM06:2026) 방지.
* **피싱 및 악성 하이퍼링크 살균 (Anti-Phishing / CWE-451)**:
  * 마크다운 하이퍼링크 변조 해제 및 `http/https/www` 패턴의 모든 외부 웹 링크를 `[외부 링크]`로 일괄 마스킹.
* **디스코드 속도 제한 대응**: HTTP 429 감지 시 `Retry-After` 헤더 기반 지수 백오프 및 재시도 로직 추가.
* **디스코드 임베드 안정성**: 단일 과목 대용량 공지 분할 시 빈 문자열(`""`) 필드로 인한 HTTP 400 Bad Request 에러 방어.
* **로깅 보안 강화**: 학번(`HS_USER_ID`) 마스킹 커스텀 포매터(`RedactingFormatter`) 적용으로 개인정보 유출 방지.
* **파일 권한 레이스 컨디션 제거**: `os.open(..., 0o600)`으로 `state.json` 원자적 파일 생성.
* **공급망 보안**: `requirements.txt` 내 패키지 버전 완전 고정(Pinning).

---

## [v3.0] - 2026-09-15

### Added
* **대시보드 실시간 Embed PATCH 시스템 구축**: 3개의 Embed(과제, 강의, 공지) 제자리 업데이트로 채팅방 도배 원천 차단.
* **과제 D-Day 시스템 & 제출/미제출 자동 분류**: 마감 임박순 정렬 및 시각적 뱃지(`🔥 [D-DAY]`, `🔴 [D-3]` 등) 적용.
* **LMS 세션 보호 스케줄러**: 수업 시간대 LMS 로그인 차단 및 작동 시간대(평일 저녁/주말) 분리.
* **로컬 무중단 마감 리마인더**: LMS 비접속 상태에서도 당일 12시 / 마감 3시간 전 과제 멘션 알림 발송.
* **공지 요약 엔진**: Google Gemini Flash AI 연동 및 로컬 규칙 기반 Fallback 구현.
