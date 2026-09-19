from __future__ import annotations

from datetime import datetime, time as dtime
import logging
import re
import sys
import time

from . import config
from .ai_summarizer import summarize_notice
from .lms_client import LmsSession
from .notifier import (
    build_assignments_embed,
    build_deadline_reminder_embed,
    build_lectures_embed,
    build_new_notice_alert_embed,
    build_notices_embed,
    get_kst_now,
    parse_deadline,
    patch_webhook_message,
    post_webhook_message,
    send_alert_ping,
)
from .parser import parse_board_item, parse_classroom_items
from .settings import load_settings, run_setup_wizard
from .state import load_state, save_state


class RedactingFormatter(logging.Formatter):
    """디스코드 웹훅 토큰 및 학번/비밀번호/API키 등 민감정보가 로그나 스택트레이스에 노출되지 않도록 마스킹."""
    _webhook_pat = re.compile(r"/api/webhooks/\d+/[\w-]+")

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        msg = self._webhook_pat.sub("/api/webhooks/<redacted>", orig)
        if config.HS_USER_ID and len(config.HS_USER_ID) >= 4 and config.HS_USER_ID in msg:
            msg = msg.replace(config.HS_USER_ID, "<redacted_id>")
        if config.HS_USER_PW and len(config.HS_USER_PW) >= 4 and config.HS_USER_PW in msg:
            msg = msg.replace(config.HS_USER_PW, "<redacted_pw>")
        if config.GEMINI_API_KEY and len(config.GEMINI_API_KEY) >= 8 and config.GEMINI_API_KEY in msg:
            msg = msg.replace(config.GEMINI_API_KEY, "<redacted_key>")
        return msg




_handler = logging.StreamHandler()
_handler.setFormatter(RedactingFormatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)


def poll_once(lms: LmsSession, state: dict, settings: dict | None = None) -> None:
    lms.ensure_login()
    courses = lms.get_course_list()

    course_state = state.setdefault("courses", {})
    dashboard_msg_ids = state.setdefault("dashboard_message_ids", {})
    urgent_notices = state.setdefault("urgent_notices", [])
    active_assignments = state.setdefault("active_assignments", {})

    is_initial_setup = not dashboard_msg_ids

    courses_data: list[dict] = []

    for c in courses:
        course_id = c["course_id"]
        class_no = c["class_no"]
        course_nm = c["course_nm"]

        first_course_seen = course_id not in course_state
        prev = course_state.get(course_id, {"seen_items": []})
        seen = set(prev.get("seen_items", []))


        html = lms.get_classroom_detail(course_id, class_no)
        items = parse_classroom_items(html)
        new_items = [it for it in items if it["key"] not in seen]

        for it in new_items:
            # 1. 공지사항 / 학습자료 처리
            if it["type"] == "notice":
                detail_title = it["title"]
                author = ""
                date_str = it.get("date_info", "")
                body_text = ""
                attachments: list[str] = [it["file_name"]] if it.get("file_name") else []

                # 상세 본문 스크랩 (게시글 번호가 있는 경우)
                if it.get("board_no") and it.get("boarditem_no"):
                    try:
                        detail_html = lms.get_board_item_detail(
                            course_id, class_no, it["board_no"], it["boarditem_no"]
                        )
                        detail_data = parse_board_item(detail_html)
                        if detail_data.get("title"):
                            detail_title = detail_data["title"]
                            author = detail_data.get("author", "")
                            date_str = detail_data.get("date", date_str)
                            body_text = detail_data.get("body", "")
                            if detail_data.get("attachments"):
                                attachments = detail_data["attachments"]
                    except Exception:
                        logger.warning("게시글 상세 조회 실패 (%s - %s)", course_nm, it["title"])

                # AI 요약 및 긴급 여부 판별
                summary_res = summarize_notice(detail_title, body_text, attachments)
                is_urgent = summary_res.get("is_urgent", False)

                if is_urgent:
                    # 긴급 공지 목록에 추가 (중복 방지)
                    if not any(un.get("title") == detail_title and un.get("course_nm") == course_nm for un in urgent_notices):
                        urgent_notices.append({
                            "course_nm": course_nm,
                            "title": detail_title,
                            "date": date_str,
                            "summary_preview": summary_res["summary_lines"][0] if summary_res.get("summary_lines") else "",
                        })

                # 최초 실행이 아닐 때만 디스코드에 알림 핑 발송
                if not is_initial_setup and not first_course_seen:
                    alert_embed = build_new_notice_alert_embed(
                        course_nm=course_nm,
                        title=detail_title,
                        author=author,
                        date=date_str,
                        summary_lines=summary_res.get("summary_lines", []),
                        attachments=attachments,
                        is_urgent=is_urgent,
                    )
                    ping_prefix = "@here 🚨 " if is_urgent else "🔔 "
                    send_alert_ping(
                        f"{ping_prefix}**[{course_nm}]** 새 공지가 등록되었습니다!",
                        alert_embed,
                        allow_here=is_urgent,
                    )

            # 2. 과제 및 온라인 강의 처리
            else:
                if not is_initial_setup and not first_course_seen:
                    badge = "📝 새 과제" if it["type"] == "assignment" else "🎥 새 온라인 강의"
                    send_alert_ping(
                        f"🔔 **[{course_nm}] {badge}** 등록!\n"
                        f"**{it['title']}**\n↳ {it['extra']}",
                        allow_here=False,
                    )


        # 과제 정보를 active_assignments에 기록 (LMS 미접속 시 마감 리마인더용)
        for it in items:
            if it["type"] == "assignment":
                key = it["key"]
                prev_a = active_assignments.get(key, {})
                active_assignments[key] = {
                    "course_nm": course_nm,
                    "title": it["title"],
                    "date_info": it.get("date_info", ""),
                    "status_info": it.get("status_info", ""),
                    "sent_reminders": prev_a.get("sent_reminders", []),
                }

        # 현재 수집된 모든 아이템을 seen 집합에 추가
        course_state[course_id] = {
            "seen_items": list(seen | {it["key"] for it in items}),
        }

        courses_data.append({
            "course_id": course_id,
            "course_nm": course_nm,
            "items": items,
        })


    # --- 3개 카테고리별 실시간 대시보드(전광판) 생성 및 PATCH 갱신 ---
    now_str = get_kst_now().strftime("%Y-%m-%d %H:%M:%S")

    dashboards = [
        ("assignments", build_assignments_embed(courses_data, now_str, settings)),
        ("lectures", build_lectures_embed(courses_data, now_str, settings)),
        ("notices", build_notices_embed(courses_data, urgent_notices, now_str, settings)),
    ]

    for category, embed in dashboards:
        msg_id = dashboard_msg_ids.get(category)
        payload = {"embeds": [embed]}

        success = False
        if msg_id:
            success = patch_webhook_message(msg_id, payload)

        # 기존 메시지가 없거나(초기 실행) 사용자가 디스코드에서 삭제한 경우(404) 새로 생성
        if not success:
            logger.info("대시보드 메시지 신규 생성 (%s)", category)
            new_msg = post_webhook_message(payload)
            if new_msg and "id" in new_msg:
                dashboard_msg_ids[category] = str(new_msg["id"])

    save_state(state)
    logger.info("폴링 및 대시보드 갱신 완료 (%s)", now_str)


# --- 스케줄러 및 작동 시간대 제어 헬퍼 ---

def parse_time_range(range_str: str) -> tuple[dtime, dtime] | None:
    """'18:00-23:00' 형태의 문자열을 파싱해 (시작시각, 종료시각) time 객체 튜플 반환."""
    try:
        parts = range_str.split("-")
        if len(parts) != 2:
            return None
        start_h, start_m = map(int, parts[0].strip().split(":"))
        end_h, end_m = map(int, parts[1].strip().split(":"))
        return dtime(start_h, start_m), dtime(end_h, end_m)
    except Exception:
        return None


def is_active_time(now: datetime | None = None, settings: dict | None = None) -> bool:
    """현재 시각이 설정된 작동 시간대(평일/주말) 범위 내인지 판별 (한국 표준시 KST 기준)."""
    if now is None:
        now = get_kst_now()

    is_weekend = now.weekday() >= 5
    if settings:
        range_str = settings.get("weekend_active_hours" if is_weekend else "weekday_active_hours")
    else:
        range_str = config.WEEKEND_ACTIVE_HOURS if is_weekend else config.WEEKDAY_ACTIVE_HOURS

    if not range_str:
        range_str = config.WEEKEND_ACTIVE_HOURS if is_weekend else config.WEEKDAY_ACTIVE_HOURS

    t_range = parse_time_range(range_str)
    if not t_range:
        return True

    start_time, end_time = t_range
    cur_time = now.time()

    if start_time <= end_time:
        return start_time <= cur_time <= end_time
    else:
        return cur_time >= start_time or cur_time <= end_time


def check_deadline_reminders(state: dict) -> None:
    """LMS 접속 없이 로컬에 저장된 과제 마감 일시를 감시하여 당일 낮 12시 / 마감 3시간 전 알림 전송."""
    active_assignments = state.get("active_assignments", {})
    if not active_assignments:
        return

    now = get_kst_now()
    state_changed = False

    for key, item in list(active_assignments.items()):
        st = item.get("status_info", "")
        # 이미 제출 완료한 과제는 리마인더 제외
        if "제출" in st and "미제출" not in st:
            continue

        dt = parse_deadline(item.get("date_info", ""))
        if not dt:
            continue

        # 마감된 지 2일 이상 지난 과제는 active 목록에서 정리
        if (now - dt).total_seconds() > 86400 * 2:
            active_assignments.pop(key, None)
            state_changed = True
            continue

        sent_reminders = item.setdefault("sent_reminders", [])
        course_nm = item.get("course_nm", "")
        title = item.get("title", "")

        # 1. 마감 당일 낮 12:00 리마인더 (당일 낮 12시 이후, 아직 마감 전)
        is_same_day = (now.date() == dt.date())
        is_after_12pm = (now.hour >= 12)
        if is_same_day and is_after_12pm and now < dt:
            if "dday_12pm" not in sent_reminders:
                embed = build_deadline_reminder_embed(
                    course_nm=course_nm,
                    title=title,
                    dt=dt,
                    reminder_type="dday_12pm",
                )
                send_alert_ping(
                    f"@here ⏰ **[오늘 마감 과제]** **[{course_nm}] {title}** (~{dt.strftime('%H:%M')} 마감)",
                    embed,
                    allow_here=True,
                )
                sent_reminders.append("dday_12pm")
                state_changed = True
                logger.info("마감 당일 낮 12시 리마인더 발송 완료: %s - %s", course_nm, title)

        # 2. 마감 3시간 전 리마인더 (마감 3시간 이내 남은 경우)
        hours_left = (dt - now).total_seconds() / 3600
        if 0 < hours_left <= 3.0:
            if "3h_before" not in sent_reminders:
                embed = build_deadline_reminder_embed(
                    course_nm=course_nm,
                    title=title,
                    dt=dt,
                    reminder_type="3h_before",
                )
                minutes_left = max(1, int((dt - now).total_seconds() // 60))
                send_alert_ping(
                    f"@here 🚨 **[마감 3시간 전 긴급 알림!]** **[{course_nm}] {title}** (남은 시간: 약 {minutes_left}분)",
                    embed,
                    allow_here=True,
                )
                sent_reminders.append("3h_before")
                state_changed = True
                logger.info("마감 3시간 전 리마인더 발송 완료: %s - %s", course_nm, title)

    if state_changed:
        save_state(state)


def main() -> None:
    lms = LmsSession()
    state = load_state()
    initial_settings = load_settings()
    logger.info(
        "한신대학교 LMS 디스코드 알림봇 시작 (설정 작동 시간 — 평일: %s, 주말: %s, 주기: %s초)",
        initial_settings["weekday_active_hours"],
        initial_settings["weekend_active_hours"],
        initial_settings["poll_interval_sec"],
    )

    last_logged_active = None
    consecutive_auth_failures = 0
    auth_locked = False
    prev_settings = initial_settings.copy()

    while True:
        # 매 루프마다 settings.json 변경 사항 실시간 핫리로드 (Live Hot-Reload)
        settings = load_settings()
        if settings != prev_settings:
            logger.info(
                "⚙️ 스케줄 설정 변경 감지 및 실시간 적용: 평일 %s, 주말 %s, 주기 %s분(%s초)",
                settings["weekday_active_hours"],
                settings["weekend_active_hours"],
                settings["poll_interval_sec"] // 60,
                settings["poll_interval_sec"],
            )
            prev_settings = settings.copy()

        now = get_kst_now()

        # 1. LMS 로그인 없이 언제나 로컬 마감 알림 체크 (비작동 시간대에도 항상 감시!)
        try:
            check_deadline_reminders(state)
        except Exception:
            logger.exception("마감 리마인더 체크 중 오류 발생")

        active = is_active_time(now, settings)

        if not active:
            if last_logged_active is not False:
                logger.info(
                    "현재 비작동 시간대입니다 (수업/수면 보호 모드). "
                    "LMS 로그인은 중단하며, 과제 마감 리마인더만 로컬 감시합니다. (평일: %s, 주말: %s)",
                    settings["weekday_active_hours"],
                    settings["weekend_active_hours"],
                )
                last_logged_active = False
            time.sleep(60)
            continue

        if last_logged_active is False:
            logger.info("작동 시간대에 진입했습니다. LMS 폴링을 재개합니다.")
        last_logged_active = True

        # 계정 잠금 방지 서킷 브레이커: 연속 실패 시 LMS 폴링 중단
        if auth_locked:
            time.sleep(60)
            continue

        try:
            poll_once(lms, state, settings)
            consecutive_auth_failures = 0
        except Exception as e:
            err_str = str(e)
            if "SSO 인증 실패" in err_str or "아이디/비밀번호" in err_str or "401" in err_str or "403" in err_str:
                consecutive_auth_failures += 1
                logger.error("SSO 인증 실패 감지 (%d/3 회)", consecutive_auth_failures)
                if consecutive_auth_failures >= 3:
                    auth_locked = True
                    logger.critical("연속 3회 SSO 인증 실패: 포털 계정 잠금 방지를 위해 LMS 폴링을 일시 중단합니다.")
                    send_alert_ping(
                        "🚨 **[한신대 LMS 봇 긴급 정지 — 계정 잠금 방지]**\n"
                        "연속 3회 SSO 로그인에 실패하여, **포털 계정 잠금을 방지하기 위해 봇 폴링을 일시 중단**했습니다.\n"
                        "학번/비밀번호(`.env`) 또는 학교 SSO 서버 상태를 확인한 후 봇을 재시작해주세요.\n"
                        "(과제 마감 로컬 리마인더는 정상 작동 중입니다)",
                        allow_here=False,
                    )
            logger.exception("폴링 중 오류 발생")

        time.sleep(settings["poll_interval_sec"])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--setup", "-s", "setup"):
            run_setup_wizard()
            sys.exit(0)
        elif arg in ("--help", "-h", "help"):
            print("""🎓 한신대학교 LMS 디스코드 알림봇

사용법:
  python -m lms_notifier.main           봇 데몬 실행 (settings.json 자동 핫리로드)
  python -m lms_notifier.main --setup   대화형 스케줄 및 주기 설정 마법사 실행 (-s)
  python -m lms_notifier.main --help    도움말 출력 (-h)
""")
            sys.exit(0)
    main()
