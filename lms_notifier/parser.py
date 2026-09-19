from __future__ import annotations

import re
from bs4 import BeautifulSoup


def _clean_text(s: str) -> str:
    """텍스트 내의 줄바꿈(\\r, \\n), 연속 공백, \\xa0 등을 단일 공백으로 정리."""
    if not s:
        return ""
    cleaned = re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()
    # '( 학습시간/기준시간 : 8분 0초 / 8분 )' 형태를 '(8분 0초 / 8분)'으로 간결하게 정리
    cleaned = re.sub(r"\(\s*학습시간/기준시간\s*:\s*", "(", cleaned)
    cleaned = re.sub(r"\s*\)", ")", cleaned)
    return cleaned


def parse_classroom_items(html: str) -> list[dict]:
    """강의실 대시보드 HTML에서 '이번주 학습활동'(강의/과제)과 공지/학습자료를 함께 추출.

    반환 항목:
    - type: "assignment" | "lecture" | "notice"
    - sub_type: "과제" | "강의" | "공지" | "학습자료"
    - key: 고유 식별자 (중복 방지 및 diff 감지용)
    - title: 제목
    - extra: 부가정보 (마감일/상태 또는 등록일)
    - board_no: 게시판 번호 (공지/자료일 경우)
    - boarditem_no: 게시글 번호 (공지/자료일 경우)
    - file_name: 첨부파일명 (있을 경우)
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []

    # 1. 이번주 학습활동 (과제, 동영상 강의)
    for node in soup.select("#lenAct .lenact_list"):
        subject = node.select_one(".lec_subject")
        date = node.select_one(".date")
        status = node.select_one("dd.lec_dotline")
        icon = node.select_one(".len_icon img")
        raw_title = subject.get_text() if subject else ""
        title = _clean_text(raw_title)
        if not title:
            continue

        alt = icon.get("alt", "") if icon else ""
        kind = "assignment" if "과제" in alt else "lecture"
        sub_type = "과제" if kind == "assignment" else "온라인강의"

        # 고유 ID 추출 (fncModifyReport('55435', ...) 등)
        btn = node.select_one(".btn_lecture_view a")
        onclick = btn.get("onclick", "") if btn else ""
        m_act = re.search(r"fncModifyReport\('(\d+)'", onclick)
        act_id = m_act.group(1) if m_act else ""
        key = f"{kind}_{act_id}" if act_id else f"{kind}_{title}"

        date_str = _clean_text(date.get_text() if date else "")
        status_str = _clean_text(status.get_text() if status else "")
        extra_parts = [p for p in [date_str, status_str] if p]

        items.append(
            {
                "type": kind,
                "sub_type": sub_type,
                "key": key,
                "title": title,
                "date_info": date_str,
                "status_info": status_str,
                "extra": " | ".join(extra_parts),
                "board_no": "",
                "boarditem_no": "",
                "file_name": "",
            }
        )

    # 2. 최근 공지 및 학습자료 (최근 7일 게시물 박스)
    for node in soup.select(".std_act_box .act_row"):
        subj = node.select_one(".subject")
        time_el = node.select_one(".time")
        cata_el = node.select_one(".cata_name")
        file_el = node.select_one(".file_down")
        raw_title = subj.get_text() if subj else ""
        title = _clean_text(raw_title)
        if not title:
            continue

        href = subj.get("href", "") if subj else ""
        m_link = re.search(r"fncBoardItemViewGo\('(\d+)',\s*'(\d+)'\)", href)
        board_no = m_link.group(1) if m_link else ""
        boarditem_no = m_link.group(2) if m_link else ""

        cata_name = _clean_text(cata_el.get_text() if cata_el else "")
        sub_type = "공지" if ("공지" in cata_name or board_no == "7") else "학습자료"
        file_name = _clean_text(file_el.get_text() if file_el else "")
        time_str = _clean_text(time_el.get_text() if time_el else "")

        key = f"board_{board_no}_{boarditem_no}" if (board_no and boarditem_no) else f"notice_{title}"

        items.append(
            {
                "type": "notice",
                "sub_type": sub_type,
                "key": key,
                "title": title,
                "date_info": time_str,
                "status_info": "",
                "extra": time_str,
                "board_no": board_no,
                "boarditem_no": boarditem_no,
                "file_name": file_name,
            }
        )

    return items



def parse_board_item(html: str) -> dict:
    """공지/자료 상세 페이지 HTML(doViewBoardItem.dunet)에서 제목, 작성자, 작성일, 본문, 첨부파일 추출."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.table_view_basic")
    if not table:
        return {
            "title": "",
            "author": "",
            "date": "",
            "body": "",
            "attachments": [],
        }

    trs = table.select("tr")
    title = trs[0].get_text(strip=True) if len(trs) > 0 else ""
    meta_text = trs[1].get_text(" ", strip=True) if len(trs) > 1 else ""

    author = ""
    date = ""
    m_author = re.search(r"작성자\s*:\s*([^|]+)", meta_text)
    if m_author:
        author = m_author.group(1).strip()
    m_date = re.search(r"등록일\s*:\s*([\d\-\.\:\s]+)", meta_text)
    if m_date:
        date = m_date.group(1).strip()

    body = trs[2].get_text("\n", strip=True) if len(trs) > 2 else ""

    attachments = []
    if len(trs) > 3:
        for a in trs[3].select("a"):
            fn = a.get_text(strip=True)
            if fn:
                attachments.append(fn)
        if not attachments:
            file_text = trs[3].get_text(strip=True)
            if "첨부파일" in file_text:
                attachments.append(file_text.replace("첨부파일 :", "").strip())

    return {
        "title": title,
        "author": author,
        "date": date,
        "body": body,
        "attachments": attachments,
    }

