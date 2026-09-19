from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from . import config

logger = logging.getLogger(__name__)


def validate_time_range(range_str: str) -> bool:
    """'18:00-23:00' 형태의 시간 범위 문자열 유효성 검증."""
    try:
        parts = range_str.split("-")
        if len(parts) != 2:
            return False
        for p in parts:
            sub = p.strip().split(":")
            if len(sub) != 2:
                return False
            h, m = int(sub[0]), int(sub[1])
            if not (0 <= h <= 24 and 0 <= m <= 59):
                return False
        return True
    except Exception:
        return False


def load_settings() -> dict[str, Any]:
    """settings.json 파일이 있으면 읽고, 없으면 .env 및 기본값으로 구성하여 반환."""
    settings_path = getattr(config, "SETTINGS_FILE", "settings.json")
    settings: dict[str, Any] = {
        "weekday_active_hours": getattr(config, "WEEKDAY_ACTIVE_HOURS", "18:00-23:00"),
        "weekend_active_hours": getattr(config, "WEEKEND_ACTIVE_HOURS", "09:00-22:00"),
        "poll_interval_sec": getattr(config, "POLL_INTERVAL_SEC", 1800),
    }

    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "weekday_active_hours" in data and validate_time_range(data["weekday_active_hours"]):
                        settings["weekday_active_hours"] = data["weekday_active_hours"].strip()
                    if "weekend_active_hours" in data and validate_time_range(data["weekend_active_hours"]):
                        settings["weekend_active_hours"] = data["weekend_active_hours"].strip()
                    if "poll_interval_sec" in data:
                        try:
                            val = int(data["poll_interval_sec"])
                            if val >= 60:
                                settings["poll_interval_sec"] = val
                        except (ValueError, TypeError):
                            pass
        except Exception:
            logger.warning("settings.json 읽기 실패 — 기본 설정을 사용합니다.")

    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """설정을 settings.json에 원자적으로 안전하게 저장 (0o600 권한)."""
    settings_path = getattr(config, "SETTINGS_FILE", "settings.json")
    tmp_path = settings_path + ".tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(tmp_path, flags, 0o600)
    with open(fd, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, settings_path)


def run_setup_wizard() -> None:
    """터미널에서 사용자가 질문에 답하며 시간대와 주기를 변경하는 대화형 마법사."""
    current = load_settings()

    print("\n" + "=" * 55)
    print("   🎓 [한신대 LMS 알림봇] 대화형 스케줄 설정 마법사")
    print("=" * 55)
    print("수정 없이 기존 값을 유지하려면 그냥 [Enter]를 누르세요.\n")

    # 1. 평일 작동 시간대
    curr_weekday = current["weekday_active_hours"]
    while True:
        prompt = f"1. 평일 작동 시간대 (기본: {curr_weekday}) [HH:MM-HH:MM]: "
        try:
            ans = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n설정이 취소되었습니다.")
            return

        if not ans:
            new_weekday = curr_weekday
            break
        elif validate_time_range(ans):
            new_weekday = ans
            break
        else:
            print("   ⚠️ 올바른 시간 형식이 아닙니다 (예: 18:00-23:00, 19:30-24:00). 다시 입력해주세요.")

    # 2. 주말 작동 시간대
    curr_weekend = current["weekend_active_hours"]
    while True:
        prompt = f"2. 주말 작동 시간대 (기본: {curr_weekend}) [HH:MM-HH:MM]: "
        try:
            ans = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n설정이 취소되었습니다.")
            return

        if not ans:
            new_weekend = curr_weekend
            break
        elif validate_time_range(ans):
            new_weekend = ans
            break
        else:
            print("   ⚠️ 올바른 시간 형식이 아닙니다 (예: 09:00-22:00, 10:00-24:00). 다시 입력해주세요.")

    # 3. 갱신 주기
    curr_min = current["poll_interval_sec"] // 60
    while True:
        prompt = f"3. 대시보드 갱신 주기 (기본: {curr_min}분) [분 단위 숫자 입력]: "
        try:
            ans = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n설정이 취소되었습니다.")
            return

        if not ans:
            new_interval_sec = current["poll_interval_sec"]
            break
        else:
            try:
                min_val = int(ans)
                if min_val < 5:
                    print("   ⚠️ 학교 서버 부하 및 차단 방지를 위해 최소 5분 이상을 권장합니다.")
                    continue
                new_interval_sec = min_val * 60
                break
            except ValueError:
                print("   ⚠️ 숫자만 입력해주세요 (예: 15, 30).")

    new_settings = {
        "weekday_active_hours": new_weekday,
        "weekend_active_hours": new_weekend,
        "poll_interval_sec": new_interval_sec,
    }

    save_settings(new_settings)

    print("\n" + "-" * 55)
    print("✅ 새 설정이 settings.json에 성공적으로 저장되었습니다!")
    print(f" • 평일 작동 시간: {new_weekday}")
    print(f" • 주말 작동 시간: {new_weekend}")
    print(f" • 갱신 주기: {new_interval_sec // 60}분 ({new_interval_sec}초)")
    print("-" * 55)
    print("💡 봇이 이미 실행 중이라면 재시작할 필요 없이 자동으로 새 설정이 반영됩니다.")
    print("=" * 55 + "\n")
