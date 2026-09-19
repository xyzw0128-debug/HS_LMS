from __future__ import annotations

import json
import os
from typing import Any

from . import config


def load_state() -> dict[str, Any]:
    if not os.path.exists(config.STATE_FILE):
        return {
            "dashboard_message_ids": {},
            "urgent_notices": [],
            "active_assignments": {},
            "courses": {},
        }
    with open(config.STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("dashboard_message_ids", {})
    state.setdefault("urgent_notices", [])
    state.setdefault("active_assignments", {})
    state.setdefault("courses", {})
    return state



def save_state(state: dict[str, Any]) -> None:
    tmp_path = config.STATE_FILE + ".tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(tmp_path, flags, 0o600)
    with open(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, config.STATE_FILE)



