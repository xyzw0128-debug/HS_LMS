# 🎓 LMS Notifier — 한신대 LMS 실시간 디스코드 알림봇

![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat)

> **"과제 마감, 강의 진도, 새 공지사항을 디스코드 한 곳에서 확인하세요!"**  
> 매번 LMS에 일일이 로그인할 필요 없이, 채널에 고정된 실시간 3단 현황판과 마감 멘션 알림을 제공하는 개인용 알림봇입니다.

---

<span id="toc"></span>

## 📑 빠른 이동 목차 (Table of Contents)

* 📸 **[디스코드 현황판 미리보기](#preview)**
* ✨ **[이런 걸 해줘요 (핵심 기능 요약)](#features)**
* ⚠️ **[시작하기 전에 꼭 읽어주세요 (주의사항)](#precautions)**
* 🧰 **[준비물 체크리스트](#requirements)**
* 🛠️ **[설치 가이드 (5분 완성)](#installation)**
  * [1단계. 디스코드 웹후크 만들기](#step-1)
  * [2단계. 프로그램 내려받기](#step-2)
  * [3단계. 터미널 열기](#step-3)
  * [4단계. 패키지 설치 (Windows / Mac / Linux)](#step-4)
  * [5단계. `.env` 파일 채우기](#step-5)
  * [6단계. 실행](#step-6)
* ✅ **[잘 동작하는지 확인하기](#verify)**
* ⏱️ **[내 맞춤 시간 설정 (`--setup`)](#setup)**
* 🖥️ **[항상 켜두기 (상시 구동 안내)](#always-on)**
* 🔒 **[개인정보는 어떻게 다뤄지나요? (투명성 표)](#privacy)**
* 🔧 **[문제가 생겼어요 (자주 묻는 질문 FAQ)](#faq)**
* 👩‍💻 **[개발자를 위한 기술 문서](#developer)**
* 📄 **[면책 조항 & 라이선스](#license)**

---

<span id="preview"></span>

## 📸 디스코드 현황판 미리보기 (Preview)

채팅방을 알림으로 도배하지 않고, **채널에 고정된 3개의 현황판 메시지가 제자리에서 실시간으로 갱신(PATCH)**됩니다.

```text
📝 [한신대 LMS] 이번 주 과제 현황판
🚨 제출할 과제 1개 • ✅ 완료 3개
────────────────────────────────────────────────────────
🔥 [제출 필요 — 마감 임박순]
> 🔴 [D-3] 소프트웨어공학
> 요구사항 명세서 작성
> `~ 09/27(일) 23:59 마감` • 미제출

🌱 [제출 완료]
> ✅ 컴퓨터네트워크 : 소켓 프로그래밍 과제 (~09/20(일) 23:59)
> ✅ 웹프로그래밍 : 3주차 실습 제출 (~09/18(금) 18:00)
────────────────────────────────────────────────────────
마지막 실시간 갱신: 2026-09-19 18:30:00 • 30분 주기 자동 업데이트 (평일 18:00-23:00 / 주말 09:00-22:00)
```

```text
🎥 [한신대 LMS] 이번 주 온라인 강의 현황판
⏳ 수강할 강의 1개 • ✅ 완료 4개
────────────────────────────────────────────────────────
⏳ [수강 필요 — 출석 인정 기간순]
> 🔴 [D-2] 운영체제 (~09/21(월) 23:59까지)
> • [4주 1회차] CPU 스케줄링 (진도 0% • 43분)

🌱 [수강 완료]
> ✅ 데이터베이스 : 2개 강의 수강 완료
> ✅ 인공지능개론 : 2개 강의 수강 완료
```

```text
📢 [한신대 LMS] 공지사항 & 학습자료 알림판
최근 등록된 과목별 공지사항과 학습자료입니다.
────────────────────────────────────────────────────────
🚨 [필독 / 긴급 공지]
> 🔥 [소프트웨어공학] 9월 25일(목) 보강 안내 (09/19)
> ↳ 💡 9월 25일 목요일 3교시 비대면 화상강의(Zoom)로 보강 진행

📋 [과목별 최근 소식]
📚 운영체제
> • 📢 4주차 강의자료 업로드 (PDF) (09/18)
> • 📁 프로세스 동기화 실습 소스코드 (ZIP) (09/17)
```

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="features"></span>

## ✨ 이런 걸 해줘요 (핵심 기능)

| | 기능 | 설명 |
|---|---|---|
| 📝 | **과제 현황판** | 마감 임박순 정렬 및 `🔥 D-DAY`, `🔴 D-3` 시각적 뱃지 표시. 제출 완료된 과제는 하단 분리 표기. |
| 🎥 | **온라인 강의 현황판** | 안 들은 강의를 맨 위에 모아 진도율과 러닝타임을 표시해 출석 누락 방지. |
| 📢 | **공지·학습자료 알림** | 새 글 감지 시 실시간 알림. 휴강·보강·시험·강의실 변경 등 **긴급 공지는 `@here` 멘션 및 상단 고정**. |
| 🤖 | **AI 3줄 요약** | 긴 공지사항 본문을 핵심 3줄로 요약. *(선택 — Gemini API 키가 없어도 내장 규칙 엔진으로 자동 동작)* |
| ⏰ | **마감 리마인더** | 과제 마감 **당일 낮 12시**와 **마감 3시간 전**에 자동 멘션 알림. 이미 제출한 과제는 자동 제외. |

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="precautions"></span>

## ⚠️ 시작하기 전에 꼭 읽어주세요

- **한신대학교 재학생 전용**이며, 학교 공식 서비스가 아닌 **비공식 오픈소스 소프트웨어**입니다.
- 🔒 **비밀번호는 안전한가요?**  
  학번과 비밀번호는 **내 컴퓨터의 `.env` 파일에만 저장**되며, 학교 공식 SSO 서버(`hs.ac.kr`) 로그인 외에 **외부 서버나 제3자에게 절대 전송되지 않습니다.** ([자세히 보기](#privacy))
- **브라우저 세션 충돌 방지**:  
  봇이 내 계정으로 LMS에 로그인할 때, **같은 시간에 브라우저로 LMS를 쓰고 있으면 브라우저가 로그아웃될 수 있습니다.** (중복 로그인 방지 정책)  
  따라서 기본 설정은 수업이 없는 시간대(평일 18~23시, 주말 9~22시)에만 동작하며, [`--setup`](#setup)으로 언제든 시간대를 변경할 수 있습니다.
- **프로그램이 켜져 있는 동안에만 동작**: 컴퓨터를 끄거나 터미널을 닫으면 봇도 멈춥니다.
- **계정 잠금 방지 안전장치**: 비밀번호를 **연속 3번 틀리면 포털 계정 잠금을 막기 위해 봇이 자동으로 정지**합니다. 포털 비밀번호를 바꾸셨다면 `.env`도 꼭 함께 수정해주세요.

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="requirements"></span>

## 🧰 준비물 체크리스트

- [ ] **Python 3.10 이상** — 터미널에서 `python --version` 또는 `python3 --version`으로 확인해요. 없으면 [python.org](https://www.python.org/downloads/)에서 설치하세요. *(Windows 사용자는 설치 첫 화면에서 **"Add Python to PATH"를 반드시 체크**하세요!)*
- [ ] **디스코드 계정과 알림을 받을 서버** — 나 혼자 쓰는 **개인 서버를 추천**해요. (내 수강 과목과 과제 현황이 채널에 올라오기 때문이에요.)
- [ ] **한신대 종합정보시스템(LMS) 학번 / 비밀번호**
- [ ] *(선택)* **Gemini API 키** — 공지 AI 3줄 요약을 쓰고 싶을 때만 필요. [Google AI Studio](https://aistudio.google.com/apikey)에서 무료로 발급받을 수 있어요.

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="installation"></span>

## 🛠 설치 가이드 (약 5분 소요)

<span id="step-1"></span>

### 1단계. 디스코드 웹후크 만들기
1. 알림을 받을 **채널 옆 톱니바퀴(채널 편집)** 클릭
2. **연동 → 웹후크 → 새 웹후크** 클릭
3. **웹후크 URL 복사** 버튼 클릭 (잠시 메모장에 붙여넣어 두세요)

> 🔑 **웹훅 주소는 비밀번호처럼 다뤄주세요.** 주소를 아는 사람은 누구나 그 채널에 메시지를 보낼 수 있습니다.

<span id="step-2"></span>

### 2단계. 프로그램 내려받기
이 페이지 우측 상단의 초록색 **`Code` → `Download ZIP`** 을 눌러 다운로드한 뒤 원하는 폴더에 압축을 풀어주세요.  
*(Git 사용자는 `git clone https://github.com/xyzw0128-debug/HS_LMS.git`)*

<span id="step-3"></span>

### 3단계. 터미널 열기
압축을 푼 폴더 안에서 터미널을 엽니다.
- **Windows**: 폴더를 연 상태에서 우클릭 **`powershell`에서 열기**
- **macOS**: 폴더를 우클릭 ➔ **폴더에서 새로운 터미널**
- **Linux**: 폴더 안에서 우클릭 ➔ **터미널에서 열기**

<span id="step-4"></span>

### 4단계. 패키지 설치
운영체제에 맞는 명령어를 한 줄씩 차례대로 입력하세요.

#### 🪟 Windows (PowerShell)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
> 💡 `venv\Scripts\activate` 실행 시 *"스크립트를 실행할 수 없다"*는 오류가 발생하면, 아래 명령어를 한 번 입력한 후 다시 시도하세요:  
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

#### 🍎 macOS / 🐧 Linux (Bash)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

> 터미널 프롬프트 맨 앞에 `(venv)`가 붙어 있다면 정상적으로 활성화된 것입니다.

<span id="step-5"></span>

### 5단계. `.env` 파일 채우기
방금 복사된 `.env` 파일을 텍스트 에디터로 엽니다. (Windows는 `notepad .env` 입력)

| 항목 | 넣을 값 | 필수 여부 | 예시 |
|---|---|:---:|---|
| `HS_USER_ID` | LMS 아이디 | ✅ 필수 | `myID1234!` |
| `HS_USER_PW` | LMS 비밀번호 | ✅ 필수 | `mypassword!` |
| `DISCORD_WEBHOOK_URL` | 1단계에서 복사한 디스코드 웹훅 주소 | ✅ 필수 | `https://discord.com/api/webhooks/...` |
| `GEMINI_API_KEY` | Gemini API 키 (AI 공지 요약용) | 선택 | 비워두셔도 자체 엔진으로 동작합니다 |

> 💡 값 앞뒤에 따옴표(`"`)나 공백 없이, `=` 바로 뒤에 붙여 쓰시면 됩니다.

<span id="step-6"></span>

### 6단계. 실행
```bash
python -m lms_notifier.main
```

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="verify"></span>

## ✅ 잘 동작하는지 확인하기

- 터미널에 `한신대학교 LMS 디스코드 알림봇 시작` 로그가 출력됩니다.
- **작동 시간대라면**: 잠시 후 디스코드 채널에 **현황판 메시지 3개(과제 / 강의 / 공지)**가 한꺼번에 생성됩니다! 첫 실행 시에는 기존 항목으로 채팅방을 도배하지 않고 현황판만 채웁니다.
- **작동 시간대가 아니라면**: 로그에 `현재 비작동 시간대입니다`라고 나오며 대기 상태로 들어갑니다. (정상 동작입니다.)
  - 낮 시간에 바로 테스트하고 싶다면 아래 [`--setup`](#setup)으로 시간대를 현재 시각이 포함되도록 넓혀보세요!

**봇을 종료하려면**: 터미널에서 `Ctrl + C`를 누르세요.  
**다음에 다시 켤 때는**: 터미널을 열고 **가상환경 켜기 ➔ 실행**만 하시면 됩니다.
```bash
# 가상환경 켜기
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 실행
python -m lms_notifier.main
```

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="setup"></span>

## ⏱ 내 맞춤 스케줄 시간 설정 (`--setup`)

`.env` 파일을 직접 열 필요 없이 터미널 질문에 답하면서 언제든지 바꿀 수 있습니다:

```bash
python -m lms_notifier.main --setup
# 또는 축약형:
python -m lms_notifier.main -s
```

```text
=======================================================
   🎓 [한신대 LMS 알림봇] 대화형 스케줄 설정 마법사
=======================================================
수정 없이 기존 값을 유지하려면 그냥 [Enter]를 누르세요.

1. 평일 작동 시간대 (기본: 18:00-23:00) [HH:MM-HH:MM]: 
2. 주말 작동 시간대 (기본: 09:00-22:00) [HH:MM-HH:MM]: 
3. 대시보드 갱신 주기 (기본: 30분) [분 단위 숫자 입력]: 
```

- 바꾸고 싶지 않은 항목은 그냥 **[Enter]**를 누르시면 기존 설정이 유지됩니다.
- 갱신 주기는 학교 서버 부하를 방지하기 위해 최소 5분 이상만 설정 가능합니다. (기본값 30분 권장)
- **💡 무중단 실시간 핫리로드**: 봇이 백그라운드에서 이미 실행 중이어도, 다른 터미널에서 설정을 변경하면 **봇을 재시작하지 않아도 다음 주기에서 새 설정이 즉시 반영**됩니다.
- 작동 시간대 밖에는 LMS 서버에 로그인하지 않지만, **과제 마감 리마인더는 비작동 시간대에도 로컬 타이머로 24시간 안전하게 작동**합니다.

| 기본 설정 | 기본 작동 시간대 | 기본 주기 |
|---|---|:---:|
| 평일 (월~금) | `18:00 ~ 23:00` (저녁 집중 시간) | 30분 |
| 주말 (토~일) | `09:00 ~ 22:00` | 30분 |

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="always-on"></span>

## 🖥️ 항상 켜두기 (상시 구동 안내)

봇은 터미널 창이 켜져 있는 동안에만 동작합니다. 24시간 알림을 받고 싶다면 다음과 같은 방법이 있습니다:

- **내 컴퓨터에서 쓰기**: 과제나 수업하는 동안 터미널 창을 백그라운드로 띄워두세요. (가장 간단)
- **Windows에서 부팅 시 자동 실행**: Windows [작업 스케줄러]에 프로그램 `venv\Scripts\python.exe`, 인수 `-m lms_notifier.main`, 시작 위치를 프로젝트 폴더 경로로 등록할 수 있습니다.
- **라즈베리파이 / 리눅스 서버 / 클라우드 VPS**: 상시 켜져 있는 미니 서버나 클라우드(Oracle Cloud Free Tier, AWS 등)에 `systemd` 서비스로 등록하면 부팅 시 자동 실행됩니다.

<details>
<summary><b>🐧 리눅스 systemd 서비스 등록 방법 (클릭해서 펼치기)</b></summary>

1. [`lms-notifier.service`](./lms-notifier.service) 파일을 열어 내 계정 환경에 맞게 수정합니다:
   - `User=<사용자명>` ➔ 내 리눅스 계정명 (예: `ubuntu`, `pi`)
   - `WorkingDirectory`, `EnvironmentFile`, `ExecStart`의 경로를 실제 프로젝트 절대 경로로 변경
2. 서비스 등록 및 시작:
   ```bash
   sudo cp lms-notifier.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now lms-notifier
   ```
3. 동작 상태 및 로그 확인:
   ```bash
   sudo systemctl status lms-notifier
   journalctl -u lms-notifier -f
   ```
</details>

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="privacy"></span>

## 🔒 개인정보는 어떻게 다뤄지나요?

| 정보 | 어디에 저장되나요? | 어디로 전송되나요? |
|---|---|---|
| **학번 / 비밀번호** | 내 컴퓨터의 `.env` 파일 | **한신대 공식 로그인 서버**(`sso2.hs.ac.kr`)로만 직접 전송 |
| **웹훅 주소** | 내 컴퓨터의 `.env` 파일 | Discord API 서버 |
| **과제·강의·공지 기록** | 내 컴퓨터의 `state.json` | **내 디스코드 채널** (해당 채널 멤버만 볼 수 있습니다) |
| **공지 본문 내용** | 디스크에 저장하지 않음 | **Gemini API 키를 넣은 경우에만** 요약을 위해 Google AI 서버로 전송 |

- 개발자가 운영하는 별도의 외부 중계 서버는 일체 없습니다. 봇은 오직 사용자 PC와 학교 서버, 디스코드 사이에서만 직접 통신합니다.
- 예외 로그 발생 시 콘솔 및 로그에 학번, 비밀번호, 웹훅 토큰, API 키가 자동으로 가려집니다(`RedactingFormatter`).
- 공지사항 속 외부 URL은 피싱 방지를 위해 `[외부 링크]`로 마스킹 처리됩니다.
- 상세한 보안 위협 분석 및 방어 아키텍처는 [SECURITY.md](./SECURITY.md)를 참고하세요.

> ⚠️ **꼭 지켜주세요**: `.env`와 `state.json`은 **절대로 다른 사람에게 공유하거나 GitHub 공개 저장소에 올리지 마세요.**

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="faq"></span>

## 🔧 문제가 생겼어요 (자주 묻는 질문 FAQ)

<details>
<summary><b>Q1. <code>python</code>을 찾을 수 없다고 나와요.</b></summary>

Python이 설치되지 않았거나 시스템 환경변수(PATH)에 등록되지 않은 경우입니다. Windows는 Python을 재설치하면서 첫 화면의 **"Add Python to PATH"** 체크박스를 꼭 체크해주세요. macOS/Linux는 `python` 대신 `python3` 명령어를 사용하세요.
</details>

<details>
<summary><b>Q2. <code>KeyError: 'HS_USER_ID'</code> 오류가 나며 꺼져요.</b></summary>

`.env` 파일을 찾지 못했거나 필수 항목이 누락된 경우입니다:
- 파일 이름이 `.env.txt`로 저장되었거나 `.env.example` 그대로인지 확인해주세요. (정확히 `.env`여야 합니다.)
- `.env` 파일이 `lms_notifier` 폴더 안이 아니라, **프로젝트 최상위 폴더**에 위치하는지 확인하세요.
- 학번, 비밀번호, 웹훅 URL 3가지 필수 항목이 모두 작성되어 있는지 확인하세요.
</details>

<details>
<summary><b>Q3. 디스코드 채널에 아무것도 안 떠요.</b></summary>

1. 터미널 로그에 `현재 비작동 시간대입니다`라고 나오는지 확인하세요. 비작동 시간대라면 정상 대기 중인 상태입니다. 작동 시간대가 되거나 `--setup`으로 시간대를 넓히면 나타납니다.
2. `DISCORD_WEBHOOK_URL`이 정확한지 확인하세요.
3. 터미널 로그에 빨간색 오류 메시지가 출력되어 있는지 확인하세요.
</details>

<details>
<summary><b>Q4. "🚨 긴급 정지 — 계정 잠금 방지" 알림이 오고 봇이 멈췄어요.</b></summary>

LMS 로그인에 연속 3회 실패하여 포털 계정이 잠기는 것을 방지하기 위해 봇이 자동으로 폴링을 중단한 상태입니다:
1. 브라우저에서 한신대 LMS에 직접 로그인하여 학번/비밀번호가 올바른지 확인하세요.
2. `.env` 파일의 `HS_USER_ID`, `HS_USER_PW`를 올바르게 수정하세요.
3. **봇 프로세스를 껐다가 다시 실행**(`Ctrl + C` 누른 후 재실행)하면 서킷 브레이커가 해제됩니다. (마감 리마인더는 정지 중에도 정상 작동합니다.)
</details>

<details>
<summary><b>Q5. 브라우저로 LMS를 보고 있는데 갑자기 로그아웃돼요.</b></summary>

봇이 LMS에 로그인하면서 기존 브라우저 세션이 만료된 것입니다. `python -m lms_notifier.main --setup`을 실행하여 **수업이나 과제를 진행하는 낮 시간대를 작동 시간대에서 제외**해주세요.
</details>

<details>
<summary><b>Q6. 디스코드 현황판 메시지를 실수로 삭제했어요!</b></summary>

걱정하지 마세요. 봇이 디스코드 404를 자동 감지하여 다음 갱신 주기에 3개의 현황판 메시지를 제자리에 다시 생성합니다.
</details>

<details>
<summary><b>Q7. 처음부터 완전히 초기화하고 다시 시작하고 싶어요.</b></summary>

봇을 종료한 뒤 폴더 안의 `state.json` 파일을 삭제하고 다시 실행하세요. 현황판 메시지를 처음부터 새로 생성합니다. (이전에 생성되었던 디스코드 현황판 메시지는 채널에서 직접 삭제해주시면 됩니다.)
</details>

<details>
<summary><b>Q8. 사용을 완전히 그만두고 싶어요 (삭제 방법).</b></summary>

터미널에서 `Ctrl + C`로 봇을 끄고 프로그램 폴더 전체를 삭제하시면 됩니다. 디스코드 채널에서 웹후크(채널 편집 ➔ 연동 ➔ 웹후크 ➔ 삭제)를 삭제하면 깔끔하게 정리됩니다. 비밀번호는 로컬 `.env`에만 보관되므로 폴더 삭제 시 완전히 소멸합니다.
</details>

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="developer"></span>

## 👩‍💻 개발자를 위한 정보

| 문서 / 디렉토리 | 설명 |
|---|---|
| [**`DEVELOPER.md`**](./DEVELOPER.md) | **시스템 아키텍처 다이어그램, LMS/SSO 프로토콜 분석, 내부 인터페이스 및 기여 가이드** |
| [**`SECURITY.md`**](./SECURITY.md) | 2026 OWASP Top 10 for LLM 방어, 피싱 링크 살균, 로그 마스킹, umask 0600 등 보안 아키텍처 상세 |
| [**`CHANGELOG.md`**](./CHANGELOG.md) | v3.0부터 최신 v3.2까지의 버전별 상세 릴리즈 노트 |
| `lms_notifier/` | 소스 코드 (`main.py` 스케줄러, `lms_client.py` 세션 수집, `parser.py` 파싱, `notifier.py` 디스코드 전송, `settings.py` 설정 마법사) |

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>

---

<span id="license"></span>

## 📄 면책 조항 (Disclaimer)

- 본 프로젝트는 학생 개인의 학업 편의를 위해 제작된 **비공식 오픈소스 소프트웨어**이며, 한신대학교의 공식 서비스가 아닙니다.
- 학교 서버에 과도한 부하를 주지 않도록 기본 30분 폴링 주기 및 수업 시간대 로그인 차단 스케줄러가 적용되어 있습니다. 갱신 주기를 지나치게 짧게 설정하지 마세요.
- 본 프로그램의 사용, 계정 관리, 설정 미흡 등으로 인해 발생하는 모든 문제와 책임은 사용자 본인에게 있습니다.

## 📜 라이선스 (License)

이 프로젝트는 [MIT License](./LICENSE)를 따릅니다.

<div align="right"><a href="#toc">⬆️ 목차로 돌아가기</a></div>
