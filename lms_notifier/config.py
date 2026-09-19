import os

from dotenv import load_dotenv

load_dotenv()

# --- 필수 환경변수 (.env 로 관리) ---
HS_USER_ID = os.environ["HS_USER_ID"]
HS_USER_PW = os.environ["HS_USER_PW"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

# --- 선택 환경변수 ---
POLL_INTERVAL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", "1800"))  # 기본 30분
WEEKDAY_ACTIVE_HOURS = os.environ.get("WEEKDAY_ACTIVE_HOURS", "18:00-23:00")  # 평일: 18시~23시
WEEKEND_ACTIVE_HOURS = os.environ.get("WEEKEND_ACTIVE_HOURS", "09:00-22:00")  # 주말: 09시~22시
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
SETTINGS_FILE = os.environ.get("SETTINGS_FILE", "settings.json")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")




# --- HAR 캡처로 확인된 상수 (한신대 LMS/SSO) ---
SSO_CLIENT_ID = "5f0869ab6c0f4178874754fbd6c5bf64"
SSO_BASE = "https://sso2.hs.ac.kr"
LMS_BASE = "https://lms.hs.ac.kr"

MY_LECTURE_MNID = "201008840728"   # 나의 강의실 (doListView.dunet)
CLASSROOM_MNID = "201008254671"    # 개별 강의실 대시보드 (doViewClassRoom.dunet)
NOTICE_MNID = "201008945595"       # 공지사항 (board_no 7)
MATERIAL_MNID = "20100863099"      # 학습자료실 (board_no 6)

USER_AGENT = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

