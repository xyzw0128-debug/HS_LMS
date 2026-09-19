from __future__ import annotations

import json
import logging
import re

import requests

from . import config

logger = logging.getLogger(__name__)


def _login_ip(session: requests.Session) -> str:
    """SSO 로그인 페이지가 내려주는 hidden input(loginIp)에서 서버 인식 발신 IP를 가져온다.
    외부 서비스(ipify) 없이 SSO 자체 페이지에서 뽑아 쓰는 게 더 정확함."""
    try:
        r = session.get(f"{config.SSO_BASE}/", timeout=5)
        m = re.search(r'id="loginIp"\s+value="([^"]*)"', r.text)
        return m.group(1) if m else ""
    except Exception:
        logger.warning("SSO 로그인 페이지에서 IP 추출 실패 — client_ip 없이 로그인 시도")
        return ""


class LmsSession:
    """SSO(sso2.hs.ac.kr) OAuth2 흐름으로 로그인해 LMS(lms.hs.ac.kr) 세션을 유지하는 클라이언트."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self._logged_in = False

    def login(self) -> None:
        client_ip = _login_ip(self.session)

        # 1단계: 인증 코드 발급
        auth_resp = self.session.post(
            f"{config.SSO_BASE}/oauth2/authoriza.do",
            data={
                "response_type": "code",
                "client_id": config.SSO_CLIENT_ID,
                "state": "123456789",
                "scope": "http://sso.hs.ac.kr",
                "redirect_uri": "https://sso.hs.ac.kr/sso/loginSuccess.jsp",
                "user_id": config.HS_USER_ID,
                "user_pwd": config.HS_USER_PW,
                "client_ip": client_ip,
            },
            headers={"Origin": config.SSO_BASE, "Referer": f"{config.SSO_BASE}/"},
            timeout=10,
        )
        try:
            auth_data = auth_resp.json()
        except ValueError as e:
            raise RuntimeError(f"SSO 1단계 응답이 JSON이 아님: {auth_resp.text[:200]}") from e

        if auth_data.get("error") != "0000":
            raise RuntimeError(f"SSO 인증 실패 (아이디/비밀번호 확인 필요): {auth_data}")
        code = auth_data["code"]

        # 2단계: 액세스 토큰 발급 (자동 제출 폼 HTML로 반환됨)
        token_resp = self.session.post(
            f"{config.SSO_BASE}/oauth2/token2.do",
            data={
                "grant_type": "authorization_code",
                "client_id": config.SSO_CLIENT_ID,
                "code": code,
                "scope": "http://sso.hs.ac.kr",
                "client_ip": client_ip,
                "redirect_uri": f"{config.LMS_BASE}/main/MainView.dunet",
            },
            headers={"Origin": config.SSO_BASE, "Referer": f"{config.SSO_BASE}/"},
            timeout=10,
        )
        m = re.search(r'name="access_token"\s+value="([^"]+)"', token_resp.text)
        if not m:
            raise RuntimeError(
                "access_token을 못 찾음 — token2.do 응답 형식이 바뀌었을 수 있음: "
                + token_resp.text[:200]
            )
        access_token = m.group(1)

        # 3단계: LMS에 access_token 제출 → JSESSIONID 세션 발급
        self.session.post(
            f"{config.LMS_BASE}/main/MainView.dunet",
            data={"access_token": access_token},
            timeout=10,
        )
        self._logged_in = True
        logger.info("LMS 로그인 성공")

    def ensure_login(self) -> None:
        if not self._logged_in:
            self.login()

    def get_course_list(self) -> list[dict]:
        """나의 강의실에서 myCourseList JS 배열을 파싱해 과목 목록(+alarm_count)을 반환."""
        resp = self.session.get(
            f"{config.LMS_BASE}/lms/myLecture/doListView.dunet",
            params={"mnid": config.MY_LECTURE_MNID},
            headers={"Referer": f"{config.LMS_BASE}/main/MainView.dunet"},
            timeout=10,
        )
        if self._looks_logged_out(resp.text):
            self._logged_in = False
            self.login()
            resp = self.session.get(
                f"{config.LMS_BASE}/lms/myLecture/doListView.dunet",
                params={"mnid": config.MY_LECTURE_MNID},
                headers={"Referer": f"{config.LMS_BASE}/main/MainView.dunet"},
                timeout=10,
            )

        courses = []
        for block in re.findall(r"myCourseList\.push\((\{.*?\})\);", resp.text, re.S):
            # 마지막 속성 뒤에 트레일링 콤마가 붙어있어 json.loads가 그냥은 실패함
            cleaned = re.sub(r",\s*\}", "}", block)
            try:
                courses.append(json.loads(cleaned))
            except json.JSONDecodeError:
                logger.warning("myCourseList 항목 파싱 실패: %s", block[:100])
        return courses

    def get_classroom_detail(self, course_id: str, class_no: str) -> str:
        """개별 강의실 대시보드(이번주 학습활동 + 공지) HTML 원문을 반환."""
        resp = self.session.post(
            f"{config.LMS_BASE}/lms/class/classroom/doViewClassRoom.dunet",
            data={
                "mnid": config.CLASSROOM_MNID,
                "course_id": course_id,
                "class_no": class_no,
                "change_role_no": "",
            },
            headers={
                "Referer": f"{config.LMS_BASE}/lms/myLecture/doListView.dunet?mnid={config.MY_LECTURE_MNID}",
                "Origin": config.LMS_BASE,
            },
            timeout=10,
        )
        return resp.text

    def get_board_item_detail(
        self, course_id: str, class_no: str, board_no: str, boarditem_no: str
    ) -> str:
        """공지사항 또는 학습자료실 게시글 상세 HTML 원문을 반환."""
        # 1. 강의실 활성 세션 설정
        self.session.post(
            f"{config.LMS_BASE}/lms/class/classroom/doSetSessionClassRoom.dunet",
            data={"course_id": course_id, "class_no": class_no},
            headers={"Referer": f"{config.LMS_BASE}/lms/class/classroom/doViewClassRoom.dunet"},
            timeout=10,
        )

        mnid = config.NOTICE_MNID if board_no == "7" else config.MATERIAL_MNID
        resp = self.session.post(
            f"{config.LMS_BASE}/lms/class/boardItem/doViewBoardItem.dunet",
            data={
                "mnid": mnid,
                "course_id": course_id,
                "class_no": class_no,
                "board_no": board_no,
                "boarditem_no": boarditem_no,
                "dataType": "C",
            },
            headers={
                "Referer": f"{config.LMS_BASE}/lms/class/classroom/doViewClassRoom.dunet",
                "Origin": config.LMS_BASE,
            },
            timeout=10,
        )
        return resp.text

    @staticmethod
    def _looks_logged_out(html: str) -> bool:
        # "sso2.hs.ac.kr"는 정상 로그인 상태에도 스크립트 변수로 항상 포함돼서 오판별이었음.
        # 로그인 상태면 doListView.dunet 응답에 myCourseList가 항상 있음.
        return "myCourseList" not in html

