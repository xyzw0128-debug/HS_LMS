from datetime import datetime
import logging
import re
import time
from typing import Any
from zoneinfo import ZoneInfo

import requests

from . import config


logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


def get_kst_now() -> datetime:
    """서버 OS의 타임존 설정과 무관하게 항상 한국 표준시(KST) 기준 naive datetime을 반환."""
    return datetime.now(KST).replace(tzinfo=None)



def _request_with_rate_limit(method: str, url: str, **kwargs) -> requests.Response:
    """디스코드 429(Rate Limit) 발생 시 Retry-After 시간만큼 대기 후 최대 2회 재시도."""
    max_retries = 2
    for attempt in range(max_retries + 1):
        resp = requests.request(method, url, **kwargs)
        if resp.status_code == 429 and attempt < max_retries:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 1.5))
            except Exception:
                retry_after = float(resp.headers.get("Retry-After", 1.5))
            logger.warning("디스코드 속도 제한(429) 감지: %.1f초 대기 후 재시도 (%d/%d)", retry_after, attempt + 1, max_retries)
            time.sleep(retry_after + 0.3)
            continue
        return resp
    return resp


def post_webhook_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    """디스코드 웹훅으로 새 메시지를 생성하고 생성된 메시지 객체(id 포함)를 반환."""
    try:
        payload.setdefault("allowed_mentions", {"parse": []})
        resp = _request_with_rate_limit(
            "POST",
            f"{config.DISCORD_WEBHOOK_URL}?wait=true",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        time.sleep(0.5)
        return resp.json()
    except Exception:
        logger.exception("디스코드 메시지 생성 실패")
        return None


def patch_webhook_message(message_id: str, payload: dict[str, Any]) -> bool:
    """디스코드 웹훅의 기존 메시지를 수정(PATCH). 404 반환 시 False 반환."""
    try:
        payload.setdefault("allowed_mentions", {"parse": []})
        resp = _request_with_rate_limit(
            "PATCH",
            f"{config.DISCORD_WEBHOOK_URL}/messages/{message_id}",
            json=payload,
            timeout=10,
        )
        if resp.status_code == 404:
            logger.warning("메시지(ID: %s)를 찾을 수 없음 (삭제됨) — 새로 생성 필요", message_id)
            return False
        resp.raise_for_status()
        time.sleep(0.5)
        return True
    except Exception:
        logger.exception("디스코드 메시지 수정(PATCH) 실패 (ID: %s)", message_id)
        return False


def send_alert_ping(content: str, embed: dict[str, Any] | None = None, allow_here: bool = False) -> None:
    """새로운 과제/공지/강의가 발견되었을 때 멘션과 함께 알림 메시지 전송.
    멘션 인젝션을 방지하기 위해 allow_here=True(긴급 공지/마감 임박)일 때만 @here를 파싱하고 그 외에는 모든 멘션을 무효화합니다."""
    try:
        allowed = {"parse": ["everyone"]} if allow_here else {"parse": []}
        payload: dict[str, Any] = {
            "content": content,
            "allowed_mentions": allowed,
        }
        if embed:
            payload["embeds"] = [embed]
        resp = _request_with_rate_limit(
            "POST",
            config.DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        time.sleep(0.5)
    except Exception:
        logger.exception("디스코드 알림 핑 전송 실패")




# --- 날짜 및 텍스트 포맷 헬퍼 함수들 ---

def parse_deadline(date_str: str) -> datetime | None:
    """날짜 문자열에서 마감 일시(두 번째 일시 또는 첫 번째 일시)를 datetime으로 추출."""
    m = re.findall(r"(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}):(\d{2})", date_str)
    if len(m) >= 2:
        end = m[1]
        return datetime(int(end[0]), int(end[1]), int(end[2]), int(end[3]), int(end[4]))
    elif len(m) == 1:
        end = m[0]
        return datetime(int(end[0]), int(end[1]), int(end[2]), int(end[3]), int(end[4]))
    return None


def format_short_date(dt: datetime) -> str:
    """09/27(일) 23:59 형태의 콤팩트 날짜 반환."""
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    w = weekdays[dt.weekday()]
    return f"{dt.strftime('%m/%d')}({w}) {dt.strftime('%H:%M')}"


def get_d_day_info(dt: datetime | None, now: datetime) -> tuple[str, str]:
    """남은 일수에 따른 [D-Day] 문구와 색상 뱃지 반환."""
    if not dt:
        return ("", "")
    diff = (dt.date() - now.date()).days
    if diff < 0:
        return ("[마감 지남]", "⚫")
    elif diff == 0:
        return ("[D-DAY]", "🔥")
    elif diff <= 3:
        return (f"[D-{diff}]", "🔴")
    elif diff <= 7:
        return (f"[D-{diff}]", "🟡")
    else:
        return (f"[D-{diff}]", "🟢")


def clean_lecture_title(title: str) -> str:
    """[4주 1회차] - 4주 1 회차 : CPU스케줄링 같은 중복 회차 표기를 [4주 1회차] CPU스케줄링으로 정리."""
    t = re.sub(r"\[(\d+주\s*\d+회차)\]\s*-\s*\d+주\s*\d+\s*회차\s*:\s*", r"[\1] ", title)
    t = re.sub(r"\[(\d+주\s*\d+회차)\]\s*-\s*", r"[\1] ", t)
    return t.strip()


def format_notice_date(raw_date: str) -> str:
    """2026.09.15 13:05 -> 09/15 형태로 단축."""
    m = re.search(r"\b\d{4}[\.\-](\d{2})[\.\-](\d{2})", raw_date)
    return f"{m.group(1)}/{m.group(2)}" if m else raw_date


def extract_ext(fn: str) -> str:
    """파일명에서 확장자 추출 (PDF, ZIP 등)."""
    if not fn:
        return ""
    m = re.search(r"\.([a-zA-Z0-9]+)$", fn.strip())
    return m.group(1).upper() if m else ""


# --- 대시보드 Embed 빌더 함수들 ---

def format_dashboard_footer(now_str: str, settings: dict[str, Any] | None = None) -> str:
    """settings를 기반으로 대시보드 하단 footer 문구를 동적으로 생성."""
    if settings:
        interval_min = settings.get("poll_interval_sec", getattr(config, "POLL_INTERVAL_SEC", 1800)) // 60
        weekday = settings.get("weekday_active_hours", getattr(config, "WEEKDAY_ACTIVE_HOURS", "18:00-23:00"))
        weekend = settings.get("weekend_active_hours", getattr(config, "WEEKEND_ACTIVE_HOURS", "09:00-22:00"))
    else:
        interval_min = getattr(config, "POLL_INTERVAL_SEC", 1800) // 60
        weekday = getattr(config, "WEEKDAY_ACTIVE_HOURS", "18:00-23:00")
        weekend = getattr(config, "WEEKEND_ACTIVE_HOURS", "09:00-22:00")
    return f"마지막 실시간 갱신: {now_str} • {interval_min}분 주기 자동 업데이트 (평일 {weekday} / 주말 {weekend})"

def build_assignments_embed(courses_data: list[dict], now_str: str, settings: dict[str, Any] | None = None) -> dict:
    """과제 현황판 Embed 생성: 마감 임박순 D-Day 정리 + 완료 항목 분리"""
    now = get_kst_now()
    unsub: list[dict] = []
    sub: list[dict] = []

    for c in courses_data:
        course_nm = c["course_nm"]
        for a in c.get("items", []):
            if a["type"] == "assignment":
                st = a.get("status_info", "")
                dt = parse_deadline(a.get("date_info", ""))
                item_info = {
                    "course_nm": course_nm,
                    "title": a["title"],
                    "dt": dt,
                    "date_str": a.get("date_info", ""),
                    "status": st,
                }
                if "제출" in st and "미제출" not in st:
                    sub.append(item_info)
                else:
                    unsub.append(item_info)

    # 미제출 과제: 마감일 오름차순 정렬 (제일 급한 것 먼저)
    unsub.sort(key=lambda x: x["dt"] or datetime.max)

    fields = []

    # 1. 제출 필요 (마감 임박순)
    if unsub:
        lines = []
        for u in unsub:
            d_day_str, badge = get_d_day_info(u["dt"], now)
            d_tag = f"{badge} **{d_day_str}** " if d_day_str else ""
            due_text = f"`~ {format_short_date(u['dt'])} 마감`" if u["dt"] else "`마감 미정`"
            lines.append(
                f"> {d_tag}**{u['course_nm']}**\n"
                f"> **{u['title']}**\n"
                f"> {due_text} • 미제출"
            )
        fields.append({
            "name": "🔥 [제출 필요 — 마감 임박순]",
            "value": "\n\n".join(lines)[:1024],
            "inline": False,
        })
    else:
        fields.append({
            "name": "🎉 [모두 완료]",
            "value": "> 현재 제출해야 할 과제가 없습니다! 편안한 시간 보내세요.",
            "inline": False,
        })

    # 2. 제출 완료
    if sub:
        lines = []
        for s in sub:
            due_text = f" (~{format_short_date(s['dt'])})" if s["dt"] else ""
            lines.append(f"> ✅ **{s['course_nm']}** : {s['title']}{due_text}")
        fields.append({
            "name": "🌱 [제출 완료]",
            "value": "\n".join(lines)[:1024],
            "inline": False,
        })

    description = f"🚨 제출할 과제 **{len(unsub)}개** • ✅ 완료 **{len(sub)}개**"

    return {
        "title": "📝 [한신대 LMS] 이번 주 과제 현황판",
        "description": description,
        "color": 0xF59E0B,  # Amber / Orange
        "fields": fields,
        "footer": {"text": format_dashboard_footer(now_str, settings)},
    }


def build_lectures_embed(courses_data: list[dict], now_str: str, settings: dict[str, Any] | None = None) -> dict:
    """온라인 강의 현황판 Embed 생성: 미수강 강의 상단 집중 + 제목 중복 정리"""
    now = get_kst_now()
    unwatched_by_course: dict[str, list[dict]] = {}
    watched_by_course: dict[str, list[dict]] = {}

    for c in courses_data:
        course_nm = c["course_nm"]
        for lec in c.get("items", []):
            if lec["type"] == "lecture":
                st = lec.get("status_info", "")
                is_done = "100%" in st or "출석" in st or "수강완료" in st
                if is_done:
                    watched_by_course.setdefault(course_nm, []).append(lec)
                else:
                    unwatched_by_course.setdefault(course_nm, []).append(lec)

    fields = []
    total_unwatched = sum(len(v) for v in unwatched_by_course.values())
    total_watched = sum(len(v) for v in watched_by_course.values())

    # 1. 수강 필요
    if unwatched_by_course:
        lines = []
        sorted_courses = sorted(
            unwatched_by_course.items(),
            key=lambda item: parse_deadline(item[1][0].get("date_info", "")) or datetime.max,
        )
        for course_nm, lecs in sorted_courses:
            dt = parse_deadline(lecs[0].get("date_info", ""))
            d_day_str, badge = get_d_day_info(dt, now)
            due_text = f" (~{format_short_date(dt)}까지)" if dt else ""
            d_tag = f"{badge} **{d_day_str}** " if d_day_str else ""
            lines.append(f"> {d_tag}**{course_nm}**{due_text}")
            for lec in lecs:
                t = clean_lecture_title(lec["title"])
                st = lec.get("status_info", "")
                m_time = re.search(r"(\d+%)\s*\(\s*(?:.*?/\s*)?(\d+분)\s*\)", st)
                time_desc = f"진도 {m_time.group(1)} • {m_time.group(2)}" if m_time else st
                lines.append(f"> • {t} ({time_desc})")
            lines.append("")

        fields.append({
            "name": "⏳ [수강 필요 — 출석 인정 기간순]",
            "value": "\n".join(lines).strip()[:1024],
            "inline": False,
        })
    else:
        fields.append({
            "name": "🎉 [모두 출석 완료]",
            "value": "> 이번 주 수강할 온라인 동영상 강의를 모두 시청했습니다!",
            "inline": False,
        })

    # 2. 수강 완료
    if watched_by_course:
        lines = []
        for course_nm, lecs in watched_by_course.items():
            lines.append(f"> ✅ **{course_nm}** : {len(lecs)}개 강의 수강 완료")
        fields.append({
            "name": "🌱 [수강 완료]",
            "value": "\n".join(lines)[:1024],
            "inline": False,
        })

    description = f"⏳ 수강할 강의 **{total_unwatched}개** • ✅ 완료 **{total_watched}개**"

    return {
        "title": "🎥 [한신대 LMS] 이번 주 온라인 강의 현황판",
        "description": description,
        "color": 0x3B82F6,  # Blue
        "fields": fields,
        "footer": {"text": format_dashboard_footer(now_str, settings)},
    }


def build_notices_embed(
    courses_data: list[dict],
    urgent_notices: list[dict],
    now_str: str,
    settings: dict[str, Any] | None = None,
) -> dict:
    """공지사항 및 학습자료 현황판 Embed 생성: 중복 제거, 확장자 간소화, 과목당 2건 제한"""
    fields = []
    urgent_titles = {un["title"] for un in urgent_notices}

    # 1. 최상단: 긴급/주요 공지 영역
    if urgent_notices:
        urgent_lines = []
        for un in urgent_notices[-3:]:
            summary_preview = un.get("summary_preview", "")
            short_date = format_notice_date(un.get("date", ""))
            date_str = f" ({short_date})" if short_date else ""
            preview_str = f"\n> ↳ 💡 {summary_preview}" if summary_preview else ""
            urgent_lines.append(
                f"> 🔥 **[{un['course_nm']}] {un['title']}**{date_str}{preview_str}"
            )
        fields.append({
            "name": "🚨 [필독 / 긴급 공지]",
            "value": "\n\n".join(urgent_lines)[:1024],
            "inline": False,
        })

    # 2. 과목별 최근 공지 및 학습자료 (중복 제목 병합, 확장자 뱃지화)
    course_blocks: list[str] = []
    for c in courses_data:
        course_nm = c["course_nm"]
        notices = [
            it for it in c.get("items", [])
            if it["type"] == "notice" and it["title"] not in urgent_titles
        ]
        if not notices:
            continue

        grouped: dict[str, dict] = {}
        for n in notices:
            t = n["title"]
            if t not in grouped:
                grouped[t] = {
                    "sub_type": n.get("sub_type", "공지"),
                    "date": format_notice_date(n.get("date_info", "")),
                    "exts": [],
                }
            ext = extract_ext(n.get("file_name", ""))
            if ext and ext not in grouped[t]["exts"]:
                grouped[t]["exts"].append(ext)

        lines = [f"📚 **{course_nm}**"]
        for title, info in list(grouped.items())[:2]:
            icon = "📢" if info["sub_type"] == "공지" else "📁"
            ext_str = f" ({', '.join(info['exts'])})" if info["exts"] else ""
            lines.append(f"> • {icon} {title}{ext_str} ({info['date']})")

        course_blocks.append("\n".join(lines))

    if course_blocks:
        # 각 필드의 value가 1024자를 넘지 않고, 절대로 빈 필드가 생기지 않도록 안전한 청크 분할
        chunks: list[str] = []
        current_chunk = ""
        for block in course_blocks:
            safe_block = block[:1000]
            if not current_chunk:
                current_chunk = safe_block
            elif len(current_chunk) + len(safe_block) + 2 <= 1000:
                current_chunk += "\n\n" + safe_block
            else:
                chunks.append(current_chunk)
                current_chunk = safe_block
        if current_chunk:
            chunks.append(current_chunk)

        if len(chunks) == 1:
            fields.append({
                "name": "📋 [과목별 최근 소식]",
                "value": chunks[0],
                "inline": False,
            })
        else:
            for idx, ch in enumerate(chunks[:5], 1):
                if ch.strip():
                    fields.append({
                        "name": f"📋 [과목별 최근 소식 ({idx})]",
                        "value": ch,
                        "inline": False,
                    })


    description = "최근 등록된 과목별 공지사항과 학습자료입니다."

    return {
        "title": "📢 [한신대 LMS] 공지사항 & 학습자료 알림판",
        "description": description,
        "color": 0x10B981,  # Emerald Green
        "fields": fields,
        "footer": {"text": format_dashboard_footer(now_str, settings)},
    }


def build_new_notice_alert_embed(
    course_nm: str,
    title: str,
    author: str,
    date: str,
    summary_lines: list[str],
    attachments: list[str],
    is_urgent: bool,
) -> dict:
    """새 공지사항 감지 시 전송할 상세 알림 Embed (디스코드 400 에러 방지를 위한 길이 제한 적용)"""
    fields = []
    if summary_lines:
        val = "\n".join(f"• {line}" for line in summary_lines)[:1000]
        fields.append({
            "name": "💡 핵심 요약",
            "value": val,
            "inline": False,
        })

    if attachments:
        val = ", ".join(attachments)[:1000]
        fields.append({
            "name": "📎 첨부파일",
            "value": val,
            "inline": False,
        })

    color = 0xEF4444 if is_urgent else 0x3B82F6  # 긴급은 빨강, 일반은 파랑
    tag = "🚨 [긴급/필독]" if is_urgent else "📢 [새 공지]"
    embed_title = f"{tag} {course_nm} — {title}"[:250]
    footer_text = f"작성자: {author or '교수님'} | 등록일: {date or '방금'}"[:2000]

    return {
        "title": embed_title,
        "color": color,
        "fields": fields,
        "footer": {"text": footer_text},
    }


def build_deadline_reminder_embed(
    course_nm: str,
    title: str,
    dt: datetime,
    reminder_type: str,
) -> dict:
    """마감 당일 12시 또는 마감 3시간 전 리마인더 Embed 생성 (길이 제한 적용)."""
    is_urgent = (reminder_type == "3h_before")
    color = 0xEF4444 if is_urgent else 0xF59E0B
    tag = "🚨 [마감 3시간 전 긴급!]" if is_urgent else "⏰ [오늘 마감 과제 알림]"
    due_text = format_short_date(dt)
    embed_title = f"{tag} {course_nm} — {title}"[:250]

    fields = [
        {
            "name": "📅 마감 일시",
            "value": f"`{due_text}`"[:1000],
            "inline": True,
        },
        {
            "name": "📝 제출 상태",
            "value": "`미제출`",
            "inline": True,
        },
    ]

    return {
        "title": embed_title,
        "color": color,
        "fields": fields,
        "footer": {"text": "LMS 접속 없이 로컬 일정 기반으로 발송된 안전 리마인더입니다."},
    }




