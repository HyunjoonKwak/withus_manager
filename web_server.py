#!/usr/bin/env python3
"""
WithUs Order Management Web Server (t2.micro 최적화 버전)
기존 GUI 기능을 경량 웹 서버로 구현
"""

import os
import sys
import threading
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# FastAPI 및 웹 관련
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
# SessionMiddleware 제거 - 쿠키 기반 인증 사용
import uvicorn

# 기존 모듈들
from database import DatabaseManager
from naver_api import NaverShoppingAPI
from notification_manager import NotificationManager
from env_config import config, web_config
from version_utils import get_full_title, get_detailed_version_info

# 로깅
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LightweightOrderManager:
    """경량 주문 관리 시스템"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.naver_api = None
        self.notification_manager = None
        self.monitoring_active = False
        self.monitoring_thread = None
        self.last_check_time = None
        self.order_counts = {}
        self.previous_order_counts = {}

        # API 초기화
        self._init_apis()

        # 백그라운드 모니터링 시작
        self._start_background_monitoring()

    def _init_apis(self):
        """API 초기화"""
        try:
            client_id = web_config.get('NAVER_CLIENT_ID')
            client_secret = web_config.get('NAVER_CLIENT_SECRET')

            logger.info(f"🔍 네이버 API 초기화 시도")
            logger.info(f"   - client_id: {client_id[:4] + '****' if client_id else 'None'}")
            logger.info(f"   - client_secret 길이: {len(client_secret) if client_secret else 0}")
            logger.info(f"   - .env 파일 존재: {os.path.exists('.env')}")

            # 만약 마스킹된 값이 반환되면 직접 .env 파일에서 읽기
            if client_secret == "****" or (client_secret and len(client_secret) <= 4):
                logger.info("🔧 마스킹된 값 감지, .env 파일에서 직접 로드 시도")
                try:
                    with open('.env', 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('NAVER_CLIENT_SECRET='):
                                client_secret = line.split('=', 1)[1].strip()
                                logger.info(f"✅ .env에서 직접 client_secret 로드 (길이: {len(client_secret)})")
                                break
                            elif line.startswith('NAVER_CLIENT_ID='):
                                if client_id == "****" or (client_id and len(client_id) <= 4):
                                    client_id = line.split('=', 1)[1].strip()
                                    logger.info(f"✅ .env에서 직접 client_id 로드")
                except Exception as e:
                    logger.error(f"❌ 환경 변수 직접 로드 실패: {e}")

            if client_id and client_secret and client_secret != "****":
                logger.info(f"🚀 NaverShoppingAPI 생성 시도...")
                self.naver_api = NaverShoppingAPI(client_id, client_secret)
                logger.info("✅ 네이버 API 초기화 완료")
            else:
                logger.warning(f"⚠️  네이버 API 설정 불충족: id={bool(client_id)}, secret={bool(client_secret and client_secret != '****')}")
                self.naver_api = None

            discord_webhook = web_config.get('DISCORD_WEBHOOK_URL')
            if discord_webhook:
                self.notification_manager = NotificationManager(discord_webhook)
                logger.info("Discord 알림 초기화 완료")
            else:
                logger.warning("Discord 웹훅이 설정되지 않았습니다")

        except Exception as e:
            logger.error(f"API 초기화 오류: {e}")

    def _start_background_monitoring(self):
        """백그라운드 모니터링 시작"""
        if web_config.get_bool('AUTO_REFRESH', True):
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._background_monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            logger.info("백그라운드 모니터링 시작됨")

    def _background_monitoring_loop(self):
        """백그라운드 모니터링 루프"""
        check_interval = web_config.get_int('CHECK_INTERVAL', 300)  # 기본 5분

        while self.monitoring_active:
            try:
                self._perform_monitoring_check()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"모니터링 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기

    def _perform_monitoring_check(self):
        """실제 모니터링 체크 수행"""
        try:
            logger.info("모니터링 체크 시작")

            # 대시보드 데이터 새로고침 (현재 설정된 기간 사용)
            monitoring_period = web_config.get_int('DASHBOARD_PERIOD_DAYS', 5)
            new_order_counts = self._get_dashboard_data(monitoring_period)

            # 상태 변화 감지 및 알림
            if self.previous_order_counts and new_order_counts:
                self._detect_and_notify_changes(new_order_counts)

            # 현재 상태 저장
            self.order_counts = new_order_counts
            self.previous_order_counts = new_order_counts.copy()
            self.last_check_time = datetime.now()

            logger.info("모니터링 체크 완료")

        except Exception as e:
            logger.error(f"모니터링 체크 오류: {e}")

    def _get_dashboard_data(self, period_days: Optional[int] = None) -> Dict[str, int]:
        """대시보드 데이터 조회 - 조회기간에 따른 필터링 적용"""
        try:
            # 조회기간 설정
            if period_days is None:
                period_days = web_config.get_int('DASHBOARD_PERIOD_DAYS', 5)

            # 날짜 범위 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')

            logger.info(f"대시보드 데이터 조회 - 기간: {start_date_str} ~ {end_date_str} ({period_days}일)")

            # 기간에 따른 주문 조회
            orders = self.db_manager.get_orders_by_date_range(start_date_str, end_date_str)
            logger.info(f"로컬 DB에서 {len(orders)}개 주문 조회 완료 (기간: {period_days}일)")

            # 상태별 카운팅
            order_counts = {
                '신규주문': 0,
                '발송대기': 0,
                '배송중': 0,
                '배송완료': 0,
                '구매확정': 0,
                '취소주문': 0,
                '반품주문': 0,
                '교환주문': 0
            }

            # 네이버 API 상태와 UI 상태 매핑
            status_mapping = {
                'PAYMENT_WAITING': '신규주문',
                'PAYED': '발송대기',
                'DELIVERING': '배송중',
                'DELIVERED': '배송완료',
                'PURCHASE_DECIDED': '구매확정',
                'CANCELED': '취소주문',
                'RETURNED': '반품주문',
                'EXCHANGED': '교환주문',
                'CANCELED_BY_NOPAYMENT': '취소주문'
            }

            for order in orders:
                if isinstance(order, dict):
                    # 네이버 API 응답의 경우
                    naver_status = order.get('orderStatus', order.get('status', '기타'))
                    ui_status = status_mapping.get(naver_status, '기타')
                    # 디버깅: 실제 주문 상태 확인
                    logger.info(f"주문 상태 매핑: {naver_status} -> {ui_status}")
                else:
                    # 로컬 DB 데이터의 경우
                    ui_status = getattr(order, 'status', '기타')
                    logger.info(f"로컬 DB 주문 상태: {ui_status}")

                if ui_status in order_counts:
                    order_counts[ui_status] += 1
                else:
                    logger.warning(f"매핑되지 않은 주문 상태: {ui_status}")

            logger.info(f"대시보드 데이터 조회 완료: {order_counts}")
            return order_counts

        except Exception as e:
            logger.error(f"대시보드 데이터 조회 오류: {e}")
            return {}

    def _detect_and_notify_changes(self, current_counts: Dict[str, int]):
        """상태 변화 감지 및 알림 전송"""
        if not self.notification_manager:
            return

        try:
            status_changes = {}

            for status in current_counts.keys():
                previous_count = self.previous_order_counts.get(status, 0)
                current_count = current_counts.get(status, 0)
                change = current_count - previous_count

                if change != 0:
                    status_changes[status] = change

            if status_changes:
                logger.info(f"상태 변화 감지: {status_changes}")
                self._send_enhanced_notification(
                    status_changes,
                    current_counts,
                    web_config.get_int('DASHBOARD_PERIOD_DAYS', 5)
                )

        except Exception as e:
            logger.error(f"상태 변화 감지 오류: {e}")

    def _send_enhanced_notification(self, status_changes: Dict, current_counts: Dict, query_period: int):
        """개선된 알림 전송 (기존 홈탭 로직 활용)"""
        try:
            title = "📊 주문 상태 변화 알림"
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            discord_message = f"**주문 상태가 변화했습니다**\n\n"
            discord_message += f"🕐 확인 시간: {now}\n"
            discord_message += f"📅 조회 기간: 최근 {query_period}일\n\n"

            # 상태별 이모지 매핑
            emoji_map = {
                '신규주문': '🆕',
                '발송대기': '📦',
                '배송중': '🚚',
                '배송완료': '✅',
                '구매확정': '🎉',
                '취소주문': '❌',
                '반품주문': '🔄',
                '교환주문': '🔄'
            }

            # 변화된 상태들을 메시지에 추가
            discord_message += "**📈 상태 변화 및 현재 총건수:**\n"
            for status, change in status_changes.items():
                emoji = emoji_map.get(status, '📋')
                change_text = f"+{change}" if change > 0 else str(change)
                current_total = current_counts.get(status, 0)
                discord_message += f"{emoji} **{status}**: {change_text}건 → 총 {current_total:,}건\n"

            # 변화가 없는 상태들의 현재 총건수도 추가
            discord_message += "\n**📊 기타 현재 상태:**\n"
            for status in emoji_map.keys():
                if status not in status_changes:
                    current_total = current_counts.get(status, 0)
                    if current_total > 0:
                        emoji = emoji_map.get(status, '📋')
                        discord_message += f"{emoji} **{status}**: {current_total:,}건\n"

            # 색상 결정
            color = 0x0099ff
            if status_changes.get('신규주문', 0) > 0:
                color = 0x00ff00
            elif status_changes.get('취소주문', 0) > 0 or status_changes.get('반품주문', 0) > 0:
                color = 0xff4444

            self.notification_manager.send_discord_notification(title, discord_message, color)
            logger.info("개선된 상태 변화 알림 전송 완료")

        except Exception as e:
            logger.error(f"알림 전송 오류: {e}")

# 전역 관리자 인스턴스
order_manager = LightweightOrderManager()

# FastAPI 앱 생성
app = FastAPI(
    title="WithUs Order Management",
    description="네이버 쇼핑 주문관리시스템 (경량 웹버전)",
    version=web_config.get('APP_VERSION', '1.0.0')
)

# 세션 대신 간단한 쿠키 기반 인증 사용
session_secret = web_config.get('SESSION_SECRET_KEY', 'default-secret-key-change-this')

# 인증 미들웨어
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """모든 요청에 대한 인증 체크"""
    # 인증이 필요없는 경로들
    public_paths = ["/login", "/register", "/api/login", "/api/register"]

    # 현재 경로가 public_paths에 있으면 통과
    if request.url.path in public_paths:
        response = await call_next(request)
        return response

    # 정적 파일은 통과
    if request.url.path.startswith("/static"):
        response = await call_next(request)
        return response

    # 인증 체크
    if not is_authenticated(request):
        # AJAX 요청이면 401 반환
        if request.headers.get("content-type") == "application/json" or request.url.path.startswith("/api"):
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required"}
            )
        # 일반 요청이면 로그인 페이지로 리다이렉트
        return RedirectResponse(url="/login", status_code=302)

    response = await call_next(request)
    return response

# 템플릿 및 정적 파일 설정
templates = Jinja2Templates(directory="templates")

# 인증 관련 함수들
def is_authenticated(request: Request) -> bool:
    """쿠키에서 인증 상태 확인"""
    try:
        # 인증 쿠키 확인
        auth_token = request.cookies.get("auth_token")
        if not auth_token:
            logger.debug(f"인증 토큰 없음 - 경로: {request.url.path}")
            return False

        # 간단한 토큰 검증 (실제로는 JWT나 더 안전한 방식 사용 권장)
        try:
            import base64
            import json
            decoded = base64.b64decode(auth_token.encode()).decode()
            token_data = json.loads(decoded)

            # 토큰 유효성 검증
            if token_data.get("authenticated") and token_data.get("username"):
                logger.debug(f"인증 성공 - 경로: {request.url.path}, 사용자: {token_data.get('username')}")
                return True
        except Exception as token_error:
            logger.warning(f"토큰 디코딩 오류 - 경로: {request.url.path}, 오류: {token_error}")

        return False
    except Exception as e:
        logger.warning(f"인증 확인 오류 - 경로: {request.url.path}, 오류: {e}")
        return False

def require_auth(request: Request):
    """인증이 필요한 엔드포인트에서 사용하는 의존성"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    return True

def get_users() -> dict:
    """사용자 목록 가져오기 (하위 호환성용)"""
    users_str = web_config.get('WEB_USERS', '')
    users = {}

    if users_str:
        # 다중 사용자 형식: admin:password123,user:pass456
        for user_pair in users_str.split(','):
            if ':' in user_pair:
                username, password = user_pair.strip().split(':', 1)
                users[username.strip()] = password.strip()

    # 하위 호환성: 기존 WEB_PASSWORD가 있으면 admin 계정으로 추가
    fallback_password = web_config.get('WEB_PASSWORD', '')
    if fallback_password and 'admin' not in users:
        users['admin'] = fallback_password

    return users

def check_user_credentials(username: str, password: str) -> Optional[Dict]:
    """사용자 자격증명 검증 (데이터베이스 기반)"""
    # 먼저 데이터베이스에서 확인
    user = order_manager.db_manager.verify_user(username, password)
    if user:
        return user

    # 하위 호환성: .env 파일 기반 인증도 시도
    env_users = get_users()
    if username in env_users and env_users[username] == password:
        return {
            'username': username,
            'full_name': username,
            'is_admin': username == 'admin',  # env 기반에서는 admin만 관리자
            'is_active': True
        }

    return None

def get_current_user(request: Request) -> Optional[Dict]:
    """현재 로그인된 사용자 정보 반환"""
    try:
        auth_token = request.cookies.get("auth_token")
        if not auth_token:
            return None

        import base64
        import json
        decoded = base64.b64decode(auth_token.encode()).decode()
        token_data = json.loads(decoded)

        if token_data.get("authenticated") and token_data.get("user_info"):
            return token_data.get("user_info")
        return None
    except Exception as e:
        logger.debug(f"사용자 정보 조회 오류: {e}")
        return None

def require_admin(request: Request):
    """관리자 권한이 필요한 엔드포인트용"""
    user = get_current_user(request)
    if not user or not user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def check_password(password: str) -> bool:
    """패스워드 검증 (하위 호환성)"""
    correct_password = web_config.get('WEB_PASSWORD', 'withus2023')
    return password == correct_password

# 정적 파일이 있다면 마운트 (선택사항)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== 인증 관련 라우트 ====================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지"""
    # 로그인 페이지는 항상 표시 (세션 체크 없이)
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """회원가입 페이지"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/api/login")
async def login(request: Request):
    """로그인 API (다중 사용자 지원)"""
    try:
        from fastapi.responses import JSONResponse
        import base64
        import json

        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        # 다중 사용자 방식 우선 시도
        if username:
            user = check_user_credentials(username, password)
            if user:
                # 인증 토큰 생성
                token_data = {
                    "authenticated": True,
                    "username": username,
                    "user_info": user,
                    "login_time": datetime.now().isoformat()
                }

                # Base64로 인코딩 (실제로는 JWT 사용 권장)
                token = base64.b64encode(json.dumps(token_data).encode()).decode()

                logger.info(f"사용자 로그인 성공 - 사용자: {username}, IP: {request.client.host}")

                response = JSONResponse({
                    "success": True,
                    "message": f"환영합니다, {user.get('full_name', username)}님!",
                    "username": username,
                    "is_admin": user.get('is_admin', False)
                })

                # 인증 쿠키 설정
                response.set_cookie(
                    key="auth_token",
                    value=token,
                    max_age=60*60*24*7,  # 7일
                    httponly=True,
                    samesite="lax"
                )

                return response
        logger.warning(f"로그인 실패 시도 - 사용자: {username or '없음'}, IP: {request.client.host}")
        return {
            "success": False,
            "message": "사용자명 또는 패스워드가 잘못되었습니다."
        }
    except Exception as e:
        logger.error(f"로그인 처리 오류: {e}")
        return {
            "success": False,
            "message": "로그인 처리 중 오류가 발생했습니다."
        }

@app.post("/api/logout")
async def logout(request: Request):
    """로그아웃 API"""
    from fastapi.responses import JSONResponse

    logger.info(f"사용자 로그아웃 - IP: {request.client.host}")
    response = JSONResponse({"success": True, "message": "로그아웃 되었습니다."})
    # 인증 쿠키 삭제
    response.delete_cookie(key="auth_token")
    return response

# ==================== 사용자 관리 API ====================

@app.post("/api/register")
async def register_user(request: Request):
    """사용자 등록 API"""
    try:
        data = await request.json()
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        email = (data.get("email") or "").strip() or None
        full_name = (data.get("full_name") or "").strip() or None

        # 입력 검증
        if not username or not password:
            return {
                "success": False,
                "message": "사용자명과 패스워드는 필수 항목입니다."
            }

        if len(username) < 3:
            return {
                "success": False,
                "message": "사용자명은 3자 이상이어야 합니다."
            }

        if len(password) < 6:
            return {
                "success": False,
                "message": "패스워드는 6자 이상이어야 합니다."
            }

        # 사용자 생성
        if order_manager.db_manager.create_user(username, password, email, full_name, is_admin=False):
            logger.info(f"새 사용자 등록 성공 - 사용자: {username}, IP: {request.client.host}")
            return {
                "success": True,
                "message": "회원가입이 완료되었습니다."
            }
        else:
            return {
                "success": False,
                "message": "사용자명이 이미 존재합니다."
            }

    except Exception as e:
        logger.error(f"사용자 등록 오류: {e}")
        return {
            "success": False,
            "message": "회원가입 처리 중 오류가 발생했습니다."
        }

@app.get("/api/users")
async def get_users_api(request: Request):
    """사용자 목록 조회 API (관리자 전용)"""
    require_admin(request)

    try:
        users = order_manager.db_manager.get_all_users()
        return {
            "success": True,
            "users": users
        }
    except Exception as e:
        logger.error(f"사용자 목록 조회 오류: {e}")
        return {
            "success": False,
            "message": "사용자 목록 조회 중 오류가 발생했습니다."
        }

@app.post("/api/users/{username}/admin")
async def toggle_admin_status(request: Request, username: str):
    """사용자 관리자 권한 토글 API (관리자 전용)"""
    require_admin(request)

    try:
        data = await request.json()
        is_admin = data.get("is_admin", False)

        if order_manager.db_manager.update_user_admin_status(username, is_admin):
            action = "부여" if is_admin else "제거"
            logger.info(f"사용자 관리자 권한 {action} - 대상: {username}, 처리자: {get_current_user(request)['username']}")
            return {
                "success": True,
                "message": f"관리자 권한이 {action}되었습니다."
            }
        else:
            return {
                "success": False,
                "message": "사용자를 찾을 수 없습니다."
            }

    except Exception as e:
        logger.error(f"관리자 권한 변경 오류: {e}")
        return {
            "success": False,
            "message": "권한 변경 중 오류가 발생했습니다."
        }

@app.post("/api/users/{username}/status")
async def toggle_user_status(request: Request, username: str):
    """사용자 활성 상태 토글 API (관리자 전용)"""
    require_admin(request)

    try:
        data = await request.json()
        is_active = data.get("is_active", True)

        if order_manager.db_manager.update_user_active_status(username, is_active):
            status = "활성화" if is_active else "비활성화"
            logger.info(f"사용자 {status} - 대상: {username}, 처리자: {get_current_user(request)['username']}")
            return {
                "success": True,
                "message": f"사용자가 {status}되었습니다."
            }
        else:
            return {
                "success": False,
                "message": "사용자를 찾을 수 없습니다."
            }

    except Exception as e:
        logger.error(f"사용자 상태 변경 오류: {e}")
        return {
            "success": False,
            "message": "상태 변경 중 오류가 발생했습니다."
        }

@app.delete("/api/users/{username}")
async def delete_user_api(request: Request, username: str):
    """사용자 삭제 API (관리자 전용)"""
    require_admin(request)
    current_user = get_current_user(request)

    try:
        # 자기 자신은 삭제할 수 없음
        if username == current_user['username']:
            return {
                "success": False,
                "message": "자기 자신은 삭제할 수 없습니다."
            }

        if order_manager.db_manager.delete_user(username):
            logger.info(f"사용자 삭제 - 대상: {username}, 처리자: {current_user['username']}")
            return {
                "success": True,
                "message": "사용자가 삭제되었습니다."
            }
        else:
            return {
                "success": False,
                "message": "사용자를 찾을 수 없습니다."
            }

    except Exception as e:
        logger.error(f"사용자 삭제 오류: {e}")
        return {
            "success": False,
            "message": "사용자 삭제 중 오류가 발생했습니다."
        }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """홈 페이지"""
    try:
        # 대시보드 데이터 조회
        # 현재 설정된 기간 사용
        period_days = web_config.get_int('DASHBOARD_PERIOD_DAYS', 10)
        dashboard_data = order_manager._get_dashboard_data(period_days)

        # 기간 정보 생성
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        period_info = {
            "days": period_days,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }

        context = {
            "request": request,
            "title": get_full_title(),
            "version_info": get_detailed_version_info(),
            "order_counts": dashboard_data,
            "dashboard_data": {"period": period_info},
            "last_check": order_manager.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if order_manager.last_check_time else "미확인",
            "monitoring_active": order_manager.monitoring_active,
            "total_orders": sum(dashboard_data.values()),
            "user_info": get_current_user(request)
        }

        return templates.TemplateResponse("home.html", context)

    except Exception as e:
        logger.error(f"홈 페이지 오류: {e}")
        raise HTTPException(status_code=500, detail="페이지 로딩 중 오류가 발생했습니다")

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """전체 주문 목록 페이지"""
    context = {
        "request": request,
        "title": "전체주문 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "all_orders"
    }
    return templates.TemplateResponse("orders.html", context)

@app.get("/new-orders", response_class=HTMLResponse)
async def new_orders_page(request: Request):
    """신규주문 관리 페이지"""
    context = {
        "request": request,
        "title": "신규주문 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "new_orders",
        "order_status": "PAYMENT_WAITING",  # 수정: 신규주문 상태는 PAYMENT_WAITING
        "description": "신규주문이란 구매자가 결제완료후 판매자 주문확인 전 주문건입니다. [주문확인] 또는 [발송지연안내], [판매취소]를 할수 있습니다."
    }
    return templates.TemplateResponse("order_management.html", context)

@app.get("/shipping-pending", response_class=HTMLResponse)
async def shipping_pending_page(request: Request):
    """발송대기 주문 페이지"""
    context = {
        "request": request,
        "title": "발송대기 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "shipping_pending",
        "order_status": "CONFIRMED",
        "description": "발송대기 주문이란 판매자가 [주문확인]후 [발송처리]전 주문건입니다. [발송처리]를 할수 있습니다."
    }
    return templates.TemplateResponse("order_management.html", context)

@app.get("/shipping-in-progress", response_class=HTMLResponse)
async def shipping_in_progress_page(request: Request):
    """배송중 주문 페이지"""
    context = {
        "request": request,
        "title": "배송중 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "shipping_in_progress",
        "order_status": "DISPATCHED",
        "description": "배송중 주문이란 상품이 택배사에 인도되어 배송중인 주문건입니다."
    }
    return templates.TemplateResponse("order_management.html", context)

@app.get("/shipping-completed", response_class=HTMLResponse)
async def shipping_completed_page(request: Request):
    """배송완료 주문 페이지"""
    context = {
        "request": request,
        "title": "배송완료 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "shipping_completed",
        "order_status": "DELIVERED",
        "description": "배송완료 주문이란 상품이 구매자에게 배송완료된 주문건입니다."
    }
    return templates.TemplateResponse("order_management.html", context)

@app.get("/purchase-decided", response_class=HTMLResponse)
async def purchase_decided_page(request: Request):
    """구매확정 주문 페이지"""
    context = {
        "request": request,
        "title": "구매확정 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "purchase_decided",
        "order_status": "PURCHASE_DECIDED",
        "description": "구매확정 주문이란 구매자가 구매확정을 완료한 주문건입니다."
    }
    return templates.TemplateResponse("order_management.html", context)

@app.get("/cancel", response_class=HTMLResponse)
async def cancel_orders_page(request: Request):
    """취소주문 페이지"""
    context = {
        "request": request,
        "title": "취소주문 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "cancel",
        "order_status": "CANCELED",
        "description": "취소주문이란 구매자가 주문을 취소한 주문건입니다."
    }
    return templates.TemplateResponse("order_management.html", context)

@app.get("/returns-exchanges", response_class=HTMLResponse)
async def returns_exchanges_page(request: Request):
    """반품교환 주문 페이지"""
    context = {
        "request": request,
        "title": "반품교환 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "page_type": "returns_exchanges",
        "order_status": "RETURN_REQUESTED",
        "description": "반품교환 주문이란 구매자가 반품이나 교환을 요청한 주문건입니다."
    }
    return templates.TemplateResponse("order_management.html", context)

@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    """상품관리 페이지"""
    context = {
        "request": request,
        "title": "상품관리 - " + get_full_title(),
        "version_info": get_detailed_version_info()
    }
    return templates.TemplateResponse("products.html", context)

@app.get("/api-test", response_class=HTMLResponse)
async def api_test_page(request: Request):
    """API 테스트 페이지"""
    context = {
        "request": request,
        "title": "API 테스트 - " + get_full_title(),
        "version_info": get_detailed_version_info()
    }
    return templates.TemplateResponse("api_test.html", context)

@app.get("/advanced-settings")
async def advanced_settings_redirect():
    """조건설정 페이지 리다이렉트 (통합된 설정 페이지로)"""
    return RedirectResponse(url="/settings#conditions", status_code=301)

@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    """도움말 페이지"""
    context = {
        "request": request,
        "title": "도움말 - " + get_full_title(),
        "version_info": get_detailed_version_info()
    }
    return templates.TemplateResponse("help.html", context)

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """사용자 관리 페이지 (관리자 전용)"""
    require_admin(request)
    context = {
        "request": request,
        "title": "사용자 관리 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "last_check": "방금 전"
    }
    return templates.TemplateResponse("users.html", context)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """설정 페이지"""
    context = {
        "request": request,
        "title": "설정 - " + get_full_title(),
        "version_info": get_detailed_version_info(),
        "config": web_config,
        "user_info": get_current_user(request)
    }
    return templates.TemplateResponse("settings.html", context)


@app.get("/api/dashboard/refresh")
async def refresh_dashboard():
    """대시보드 수동 새로고침 - 네이버 API 호출하여 최신 데이터 갱신"""
    try:
        # 조회기간 설정 (한 번만 계산)
        period_days = web_config.get_int('DASHBOARD_PERIOD_DAYS', 5)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        logger.info(f"🔄 대시보드 새로고침: {start_date_str} ~ {end_date_str} ({period_days}일)")

        total_refreshed = 0

        # 네이버 API에서 최신 데이터 갱신
        if order_manager.naver_api:
            logger.info("📡 네이버 API 갱신 중...")

            # 단일 API 호출로 모든 상태 주문 한번에 조회 (더 효율적)
            try:
                api_response = order_manager.naver_api.get_orders(
                    start_date=start_date_str,
                    end_date=end_date_str,
                    limit=200  # 기간내 모든 주문 조회
                )

                if api_response and api_response.get('success'):
                    orders_data = api_response.get('data', {}).get('data', [])
                    if orders_data:
                        total_refreshed = order_manager.naver_api.save_orders_to_database(
                            order_manager.db_manager, orders_data
                        )
                        logger.info(f"📊 네이버 API 갱신 완료: {total_refreshed}건 갱신됨")
                    else:
                        logger.info("📝 새 주문 없음")
                else:
                    logger.warning("❌ API 응답 실패")
            except Exception as api_error:
                logger.error(f"⚠️ API 갱신 오류: {api_error}")
        else:
            logger.warning("⚠️ 네이버 API 미설정 - 로컬 데이터만 반환")

        # 갱신된 데이터로 대시보드 생성
        order_counts = order_manager._get_dashboard_data(period_days)

        return {
            "success": True,
            "data": order_counts,
            "period": {
                "days": period_days,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "description": f"최근 {period_days}일간 주문현황"
            },
            "last_check": datetime.now().isoformat(),
            "total_orders": sum(order_counts.values()),
            "api_refreshed": bool(order_manager.naver_api),
            "total_refreshed_from_api": total_refreshed if order_manager.naver_api else 0
        }
    except Exception as e:
        logger.error(f"대시보드 새로고침 오류: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/dashboard/period")
async def update_dashboard_period(request: Request):
    """대시보드 조회 기간 변경"""
    try:
        data = await request.json()
        new_period_days = int(data.get('days', data.get('period_days', 5)))
        save_to_env = data.get('save_to_env', True)  # 기본값은 저장

        # 유효성 검사
        if new_period_days < 1 or new_period_days > 365:
            return {
                "success": False,
                "message": "조회 기간은 1일에서 365일 사이여야 합니다."
            }

        # env 설정 업데이트 (항상 메모리에는 설정)
        web_config.set('DASHBOARD_PERIOD_DAYS', str(new_period_days))

        # save_to_env가 True일 때만 .env 파일에 저장
        if save_to_env:
            web_config.save_to_env_file()
            logger.info(f"대시보드 조회 기간이 {new_period_days}일로 변경되고 .env 파일에 저장됨")
        else:
            logger.info(f"대시보드 조회 기간이 {new_period_days}일로 임시 변경됨 (저장하지 않음)")

        # 새로운 기간으로 대시보드 데이터 새로고침
        order_counts = order_manager._get_dashboard_data(new_period_days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=new_period_days)

        return {
            "success": True,
            "data": order_counts,
            "saved_to_env": save_to_env,
            "period": {
                "days": new_period_days,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "description": f"최근 {new_period_days}일간 주문현황"
            },
            "period_dates": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            "message": f"대시보드 조회 기간이 {new_period_days}일로 {'저장되었습니다' if save_to_env else '변경되었습니다'}."
        }

    except Exception as e:
        logger.error(f"대시보드 기간 변경 오류: {e}")
        return {
            "success": False,
            "message": f"기간 변경 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/monitoring/status")
async def get_monitoring_status():
    """모니터링 상태 조회"""
    return {
        "active": order_manager.monitoring_active,
        "last_check": order_manager.last_check_time.isoformat() if order_manager.last_check_time else None,
        "check_interval": web_config.get_int('CHECK_INTERVAL', 300),
        "discord_enabled": bool(order_manager.notification_manager),
        "naver_api_enabled": bool(order_manager.naver_api)
    }

@app.post("/api/monitoring/force-check")
async def force_monitoring_check(background_tasks: BackgroundTasks):
    """수동 모니터링 체크"""
    try:
        background_tasks.add_task(order_manager._perform_monitoring_check)
        return {
            "success": True,
            "message": "모니터링 체크를 실행합니다",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"수동 체크 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/orders")
async def get_orders_from_db(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    order_status: Optional[str] = None,
    page_type: Optional[str] = None,
    limit: int = 100
):
    """주문 목록 조회 API - 데이터베이스 전용 (탭 최초 진입용)"""
    try:
        # 기본 날짜 설정 (페이지별 기간 설정 사용)
        if not start_date or not end_date:
            # 페이지 타입별 기본 기간 가져오기
            default_days = 30  # 전역 기본값

            if page_type:
                # 페이지 타입 매핑
                period_mapping = {
                    'new-orders': 'NEW_ORDER_DEFAULT_DAYS',
                    'new_orders': 'NEW_ORDER_DEFAULT_DAYS',  # 신규주문 별칭
                    'shipping-pending': 'SHIPPING_PENDING_DEFAULT_DAYS',
                    'shipping-in-progress': 'SHIPPING_IN_PROGRESS_DEFAULT_DAYS',
                    'shipping-completed': 'SHIPPING_COMPLETED_DEFAULT_DAYS',
                    'purchase-decided': 'PURCHASE_DECIDED_DEFAULT_DAYS',
                    'cancel': 'CANCEL_DEFAULT_DAYS',
                    'cancel_orders': 'CANCEL_DEFAULT_DAYS',  # 취소주문 페이지 별칭
                    'return-exchange': 'RETURN_EXCHANGE_DEFAULT_DAYS',
                    'cancel-return-exchange': 'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS'
                }

                if page_type in period_mapping:
                    env_key = period_mapping[page_type]
                    default_days = web_config.get_int(env_key, default_days)
                    logger.info(f"📅 {page_type} 페이지 기본 기간: {default_days}일 ({env_key}) [DB 전용]")

            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=default_days)
            start_date_str = start_date_obj.strftime('%Y-%m-%d')
            end_date_str = end_date_obj.strftime('%Y-%m-%d')
        else:
            start_date_str = start_date
            end_date_str = end_date

        logger.info(f"📚 데이터베이스에서 주문 조회 (API 호출 없음): {start_date_str} ~ {end_date_str}")

        # 로컬 DB에서 날짜 범위로 조회 (대시보드와 동일한 방식)
        orders = order_manager.db_manager.get_orders_by_date_range(start_date_str, end_date_str)

        # 디버깅 정보 추가
        debug_info = {
            "total_orders_in_db": len(orders),
            "db_path": order_manager.db_manager.db_path,
            "orders_sample": [order.get('status') for order in orders[:5]] if orders else []
        }

        order_list = []

        # Status mapping for filtering
        korean_to_english_status = {
            '취소주문': 'CANCELED',
            '신규주문': 'PAYMENT_WAITING',
            '발송대기': 'PAYED',
            '배송중': 'DELIVERING',
            '배송완료': 'DELIVERED',
            '구매확정': 'PURCHASE_DECIDED',
            '반품주문': 'RETURNED',
            '교환주문': 'EXCHANGED'
        }

        for order in orders:
            # 상태 필터링 - 한국어 상태를 영어 상태로 변환하여 비교
            if order_status:
                english_filter_status = korean_to_english_status.get(order_status, order_status)
                if order.get('status') != english_filter_status:
                    continue

            # 날짜 필터링은 이미 데이터베이스에서 처리됨 (get_orders_by_date_range 사용)

            # Status mapping from English to Korean
            english_status = order.get('status', '')
            status_mapping = {
                'CANCELED': '취소주문',
                'PAYMENT_WAITING': '신규주문',
                'PAYED': '발송대기',
                'DELIVERING': '배송중',
                'DELIVERED': '배송완료',
                'PURCHASE_DECIDED': '구매확정',
                'RETURNED': '반품주문',
                'EXCHANGED': '교환주문',
                'CANCELED_BY_NOPAYMENT': '취소주문'
            }
            korean_status = status_mapping.get(english_status, english_status)

            order_data = {
                "order_id": order.get('order_id', ''),
                "customer_name": order.get('customer_name', ''),
                "product_name": order.get('product_name', ''),
                "order_status": korean_status,
                "order_date": order.get('order_date', ''),
                "price": order.get('price', 0),
                "delivery_address": order.get('shipping_address', ''),
                "quantity": order.get('quantity', 1)
            }
            order_list.append(order_data)

        return {
            "success": True,
            "orders": order_list,
            "count": len(order_list),
            "source": "local_db_only",
            "filter": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "status": order_status
            },
            "debug": debug_info
        }

    except Exception as e:
        logger.error(f"데이터베이스 주문 조회 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/orders/refresh")
async def refresh_orders_from_api(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    order_status: Optional[str] = None,
    page_type: Optional[str] = None,
    limit: int = 100
):
    """주문 목록 갱신 API - 네이버 API 호출 후 DB 저장 (조회 버튼용)"""
    try:
        # 기본 날짜 설정 (페이지별 기간 설정 사용)
        if not start_date or not end_date:
            # 페이지 타입별 기본 기간 가져오기
            default_days = 30  # 전역 기본값

            if page_type:
                # 페이지 타입 매핑
                period_mapping = {
                    'new-orders': 'NEW_ORDER_DEFAULT_DAYS',
                    'new_orders': 'NEW_ORDER_DEFAULT_DAYS',  # 신규주문 별칭
                    'shipping-pending': 'SHIPPING_PENDING_DEFAULT_DAYS',
                    'shipping-in-progress': 'SHIPPING_IN_PROGRESS_DEFAULT_DAYS',
                    'shipping-completed': 'SHIPPING_COMPLETED_DEFAULT_DAYS',
                    'purchase-decided': 'PURCHASE_DECIDED_DEFAULT_DAYS',
                    'cancel': 'CANCEL_DEFAULT_DAYS',
                    'cancel_orders': 'CANCEL_DEFAULT_DAYS',  # 취소주문 페이지 별칭
                    'return-exchange': 'RETURN_EXCHANGE_DEFAULT_DAYS',
                    'cancel-return-exchange': 'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS'
                }

                if page_type in period_mapping:
                    env_key = period_mapping[page_type]
                    default_days = web_config.get_int(env_key, default_days)
                    logger.info(f"📅 {page_type} 페이지 기본 기간: {default_days}일 ({env_key}) [API 갱신]")

            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=default_days)
            start_date_str = start_date_obj.strftime('%Y-%m-%d')
            end_date_str = end_date_obj.strftime('%Y-%m-%d')
        else:
            start_date_str = start_date
            end_date_str = end_date

        # 네이버 API에서 주문 조회 후 데이터베이스에 저장
        logger.info(f"API 조건 확인: naver_api={bool(order_manager.naver_api)}, order_status='{order_status}'")

        if order_manager.naver_api and order_status:
            # 신규주문(PAYMENT_WAITING)과 발송대기(PAYED)는 모두 네이버 API에서 PAYED 상태로 조회
            naver_api_status = order_status
            if order_status == 'PAYMENT_WAITING':
                naver_api_status = 'PAYED'
                logger.info(f"🚀 네이버 API 갱신 시작: {start_date_str} ~ {end_date_str}, 요청 상태: {order_status} → API 상태: {naver_api_status}")
            else:
                logger.info(f"🚀 네이버 API 갱신 시작: {start_date_str} ~ {end_date_str}, 상태: {order_status}")

            # 1단계: 네이버 API에서 주문 조회
            api_response = order_manager.naver_api.get_orders(
                start_date=start_date_str,
                end_date=end_date_str,
                order_status=naver_api_status,
                limit=limit
            )

            if api_response and api_response.get('success'):
                total_orders = api_response.get('data', {}).get('total', 0)
                chunks_processed = api_response.get('chunks_processed', 0)
                logger.info(f"📥 네이버 API 조회 완료: {chunks_processed}개 청크, 총 {total_orders}건")

                # 2단계: 조회된 데이터를 데이터베이스에 저장 (중복 API 호출 방지)
                if total_orders > 0:
                    logger.info("💾 데이터베이스 저장 시작...")
                    try:
                        orders_data = api_response.get('data', {}).get('data', [])
                        saved_count = order_manager.naver_api.save_orders_to_database(
                            order_manager.db_manager, orders_data
                        )
                        logger.info(f"✅ 데이터베이스 저장 완료: {saved_count}건 저장")
                    except Exception as sync_error:
                        logger.error(f"❌ 데이터베이스 저장 실패: {sync_error}")
                        # 저장 실패해도 계속 진행
                else:
                    logger.info("📝 조회된 주문이 없어 저장 생략")
            else:
                logger.warning("❌ 네이버 API 응답 없음")
        else:
            logger.warning(f"⚠️  네이버 API 호출 조건 불충족: api={bool(order_manager.naver_api)}, status='{order_status}'")

        # 로컬 DB에서 날짜 범위로 조회 (대시보드와 동일한 방식)
        orders = order_manager.db_manager.get_orders_by_date_range(start_date_str, end_date_str)

        # 디버깅 정보 추가
        debug_info = {
            "total_orders_in_db": len(orders),
            "db_path": order_manager.db_manager.db_path,
            "orders_sample": [order.get('status') for order in orders[:5]] if orders else []
        }

        order_list = []

        # Status mapping for filtering
        korean_to_english_status = {
            '취소주문': 'CANCELED',
            '신규주문': 'PAYMENT_WAITING',
            '발송대기': 'PAYED',
            '배송중': 'DELIVERING',
            '배송완료': 'DELIVERED',
            '구매확정': 'PURCHASE_DECIDED',
            '반품주문': 'RETURNED',
            '교환주문': 'EXCHANGED'
        }

        for order in orders:
            # 상태 필터링 - 한국어 상태를 영어 상태로 변환하여 비교
            if order_status:
                english_filter_status = korean_to_english_status.get(order_status, order_status)
                if order.get('status') != english_filter_status:
                    continue

            # 날짜 필터링은 이미 데이터베이스에서 처리됨 (get_orders_by_date_range 사용)

            # Status mapping from English to Korean
            english_status = order.get('status', '')
            status_mapping = {
                'CANCELED': '취소주문',
                'PAYMENT_WAITING': '신규주문',
                'PAYED': '발송대기',
                'DELIVERING': '배송중',
                'DELIVERED': '배송완료',
                'PURCHASE_DECIDED': '구매확정',
                'RETURNED': '반품주문',
                'EXCHANGED': '교환주문',
                'CANCELED_BY_NOPAYMENT': '취소주문'
            }
            korean_status = status_mapping.get(english_status, english_status)

            order_data = {
                "order_id": order.get('order_id', ''),
                "customer_name": order.get('customer_name', ''),
                "product_name": order.get('product_name', ''),
                "order_status": korean_status,
                "order_date": order.get('order_date', ''),
                "price": order.get('price', 0),
                "delivery_address": order.get('shipping_address', ''),
                "quantity": order.get('quantity', 1)
            }
            order_list.append(order_data)

        return {
            "success": True,
            "orders": order_list,
            "count": len(order_list),
            "source": "api_refreshed",
            "filter": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "status": order_status
            },
            "debug": debug_info
        }

    except Exception as e:
        logger.error(f"주문 갱신 오류: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/orders/action")
async def perform_order_action(action_data: dict):
    """주문 액션 수행 API (주문확인, 발송처리, 취소 등)"""
    try:
        action = action_data.get('action')
        order_id = action_data.get('order_id')
        additional_data = action_data.get('data', {})

        if not action or not order_id:
            return {"success": False, "error": "액션과 주문 ID가 필요합니다"}

        result = {"success": False, "message": "지원하지 않는 액션입니다"}

        # 액션별 처리
        if action == "confirm_order":
            result = {"success": True, "message": f"주문 {order_id} 확인 완료"}
        elif action == "dispatch_order":
            tracking_number = additional_data.get('tracking_number')
            result = {"success": True, "message": f"주문 {order_id} 발송 처리 완료"}
        elif action == "cancel_order":
            cancel_reason = additional_data.get('cancel_reason')
            result = {"success": True, "message": f"주문 {order_id} 취소 처리 완료"}

        return result

    except Exception as e:
        logger.error(f"주문 액션 수행 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/products")
async def get_products():
    """상품 목록 조회 API"""
    import time
    import asyncio

    try:
        logger.info("상품 목록 조회 API 호출")
        products = order_manager.db_manager.get_all_products()
        logger.info(f"데이터베이스에서 조회된 상품 수: {len(products)}")

        if products:
            logger.info(f"첫 번째 상품 데이터: {products[0]}")

        products_data = []
        for i, product in enumerate(products):
            # 기본 상품 정보 구성
            product_dict = {
                'id': product.get('channel_product_no', ''),
                'product_id': product.get('channel_product_no', ''),
                'origin_product_no': product.get('origin_product_no', ''),
                'name': product.get('product_name', ''),
                'price': product.get('sale_price', 0),
                'sale_price': product.get('sale_price', 0),
                'discounted_price': product.get('discounted_price', 0),
                'stock': product.get('stock_quantity', 0),
                'category': product.get('category_name', ''),
                'status': product.get('status_type', ''),
                'brand': product.get('brand_name', ''),
                'image_url': product.get('representative_image_url', ''),
                'created_at': product.get('reg_date', ''),
                'sales_count': 0,
                'options': []
            }

            # 원상품ID가 있는 경우 옵션 정보 로드
            if product.get('origin_product_no'):
                origin_product_no = product.get('origin_product_no')

                try:
                    # 먼저 데이터베이스에서 캐시 여부 확인
                    has_cache = order_manager.db_manager.has_cached_options(origin_product_no)
                    logger.info(f"🔍 캐시 확인: 상품 {origin_product_no} - {'있음' if has_cache else '없음'}")

                    if has_cache:
                        # 캐시가 있으면 옵션 정보 로드
                        cached_options = order_manager.db_manager.get_product_options(origin_product_no)
                        logger.info(f"💾 캐시 사용: 상품 {product.get('product_name')} - {len(cached_options)}개 옵션")

                        # 원상품의 실제 판매가 계산 (원가 - 셀러할인가)
                        original_price = product.get('sale_price', 0)
                        seller_discount = product.get('sale_price', 0) - product.get('discounted_price', 0)
                        actual_selling_price = original_price - seller_discount

                        options = []
                        for option in cached_options:
                            # 옵션별 실제 판매가 계산 (실제 판매가 + 옵션 가격)
                            option_price = option.get('price', 0)
                            option_actual_price = actual_selling_price + option_price

                            option_data = {
                                'id': option.get('id', ''),
                                'name': option.get('optionName', ''),
                                'optionName1': option.get('optionName1', ''),
                                'price': option_price,
                                'actual_price': option_actual_price,  # 계산된 실제 판매가
                                'stock': option.get('stockQuantity', 0),
                                'status': option.get('statusType', ''),
                                'manage_code': option.get('sellerManagerCode', ''),
                                'option_values': []
                            }

                            # 옵션 값들 추가
                            if 'optionItems' in option and option['optionItems']:
                                for item in option['optionItems']:
                                    option_data['option_values'].append({
                                        'group_name': item.get('groupName', ''),
                                        'value': item.get('value', '')
                                    })

                            options.append(option_data)

                        product_dict['options'] = options

                    else:
                        # 캐시된 정보가 없으면 API에서 조회 후 저장
                        # 요청 간 지연시간 추가 (API 레이트 리미트 방지)
                        if i > 0:
                            time.sleep(0.5)  # 0.5초 지연

                        logger.info(f"🌐 API 호출: 상품 {product.get('product_name')} 옵션 조회")
                        option_response = order_manager.naver_api.get_origin_product(origin_product_no)

                        if option_response.get('success') and option_response.get('data'):
                            option_info = option_response['data'].get('originProduct', {}).get('detailAttribute', {}).get('optionInfo')

                            if option_info and option_info.get('optionCombinations'):
                                # 데이터베이스에 옵션 정보 저장
                                save_result = order_manager.db_manager.save_product_options(origin_product_no, option_info['optionCombinations'])
                                logger.info(f"옵션 정보 DB 저장 결과: {save_result}, 상품ID: {origin_product_no}, 옵션 개수: {len(option_info['optionCombinations'])}")
                            else:
                                logger.info(f"상품 {product.get('product_name')} (ID: {origin_product_no})에는 옵션이 없습니다.")
                                # 옵션이 없다는 것도 캐시에 저장 (빈 배열로 저장)
                                order_manager.db_manager.save_product_options(origin_product_no, [])

                                # 원상품의 실제 판매가 계산 (원가 - 셀러할인가)
                                original_price = product.get('sale_price', 0)
                                seller_discount = product.get('sale_price', 0) - product.get('discounted_price', 0)
                                actual_selling_price = original_price - seller_discount

                                options = []
                                for option in option_info['optionCombinations']:
                                    # 옵션별 실제 판매가 계산 (실제 판매가 + 옵션 가격)
                                    option_price = option.get('price', 0)
                                    option_actual_price = actual_selling_price + option_price

                                    option_data = {
                                        'id': option.get('id', ''),
                                        'name': option.get('optionName', ''),
                                        'optionName1': option.get('optionName1', ''),  # 추가
                                        'price': option_price,
                                        'actual_price': option_actual_price,  # 계산된 실제 판매가
                                        'stock': option.get('stockQuantity', 0),
                                        'status': option.get('statusType', ''),
                                        'manage_code': option.get('sellerManageCode', ''),
                                        'option_values': []
                                    }

                                    # 옵션 값들 추가
                                    if 'optionItems' in option:
                                        for item in option['optionItems']:
                                            option_data['option_values'].append({
                                                'group_name': item.get('groupName', ''),
                                                'value': item.get('value', '')
                                            })

                                    options.append(option_data)

                                product_dict['options'] = options
                                logger.info(f"상품 {product.get('product_name')}에 {len(options)}개 옵션 로드 완료 (DB 저장)")

                except Exception as option_error:
                    logger.warning(f"상품 {product.get('product_name')}의 옵션 로드 실패: {option_error}")
                    # 옵션 로드 실패해도 상품 자체는 표시
                    product_dict['options'] = []

            products_data.append(product_dict)

        return {
            "success": True,
            "products": products_data,
            "count": len(products_data)
        }

    except Exception as e:
        logger.error(f"상품 조회 API 오류: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/products")
async def create_product(request: Request):
    """상품 등록 API"""
    try:
        logger.info("상품 등록 API 호출")
        data = await request.json()
        logger.info(f"받은 상품 데이터: {data}")

        # 필수 필드 검증
        required_fields = ['name', 'price', 'stock', 'status']
        for field in required_fields:
            if not data.get(field):
                return {"success": False, "error": f"필수 필드 '{field}'가 누락되었습니다."}

        # 데이터베이스에 상품 저장
        # 임시 상품 ID 생성 (실제로는 네이버 API 연동이 필요)
        import time
        product_id = f"TEMP_{int(time.time())}"

        product_data = {
            'channel_product_no': product_id,
            'product_name': data.get('name', ''),
            'brand_name': data.get('brand', ''),
            'sale_price': data.get('price', 0),
            'discounted_price': data.get('discounted_price', 0),
            'stock_quantity': data.get('stock', 0),
            'status_type': data.get('status', ''),
            'image_url': data.get('image_url', ''),
            'description': data.get('description', ''),
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # 데이터베이스에 삽입 (실제 구현 필요)
        # 현재는 임시로 성공 응답 반환
        logger.info(f"상품 등록 완료: {product_data}")

        return {
            "success": True,
            "message": f"상품 '{data['name']}'이(가) 성공적으로 등록되었습니다.",
            "product_id": product_id
        }

    except Exception as e:
        logger.error(f"상품 등록 API 오류: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/products/filter-settings")
async def save_product_filter_settings(request: Request):
    """상품 필터 설정 저장 - 설정 페이지와 연동"""
    try:
        data = await request.json()
        selected_statuses = data.get('selectedStatuses', [])

        # 설정 페이지의 product_status_types에 저장 (메인 설정)
        web_config.set('PRODUCT_STATUS_TYPES', ','.join(selected_statuses))
        # 하위 호환성을 위해 기존 키도 유지
        web_config.set('PRODUCT_FILTER_STATUSES', ','.join(selected_statuses))
        web_config.save_to_env_file()

        logger.info(f"상품 필터 설정 저장: {selected_statuses}")
        return {"success": True, "message": "필터 설정이 저장되었습니다."}
    except Exception as e:
        logger.error(f"상품 필터 설정 저장 실패: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/products/{origin_product_id}/detail")
async def get_product_detail(origin_product_id: str):
    """원상품 상세 정보 조회 API - 네이버 API 원본 응답 반환"""
    try:
        logger.info(f"원상품 상세 조회 API 호출: {origin_product_id}")

        # 네이버 API에서 원상품 정보 조회
        response = order_manager.naver_api.get_origin_product(origin_product_id)

        logger.info(f"네이버 API 응답 성공: {origin_product_id}")
        return {
            "success": True,
            "data": response,
            "origin_product_id": origin_product_id
        }

    except Exception as e:
        logger.error(f"원상품 상세 조회 API 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/products/filter-settings")
async def get_product_filter_settings():
    """상품 필터 설정 조회 - 설정 페이지와 연동"""
    try:
        # 설정 페이지의 product_status_types를 우선적으로 확인
        product_status_types = web_config.get('PRODUCT_STATUS_TYPES', '')
        if product_status_types:
            selected_statuses = [s.strip() for s in product_status_types.split(',') if s.strip()]
        else:
            # 없으면 기존 PRODUCT_FILTER_STATUSES 사용 (하위 호환성)
            saved_statuses = web_config.get('PRODUCT_FILTER_STATUSES', '')
            selected_statuses = [s.strip() for s in saved_statuses.split(',') if s.strip()] if saved_statuses else []

        # 기본값 설정 (아무 설정이 없을 경우)
        if not selected_statuses:
            selected_statuses = ['SALE', 'WAIT', 'OUTOFSTOCK']

        logger.info(f"상품 필터 설정 조회: {selected_statuses}")
        return {
            "success": True,
            "settings": {
                "selectedStatuses": selected_statuses
            }
        }
    except Exception as e:
        logger.error(f"상품 필터 설정 조회 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/products/refresh")
async def refresh_products_from_api():
    """상품 목록 갱신 API - 네이버 API에서 상품 데이터 새로고침"""
    try:
        logger.info("상품 API 새로고침 시작")

        # 네이버 API에서 상품 데이터 가져오기
        response = order_manager.naver_api.get_products()

        if not response or 'success' not in response:
            logger.error("네이버 API 응답이 올바르지 않음")
            return {
                "success": False,
                "error": "네이버 API 응답이 올바르지 않습니다"
            }

        if not response.get('success'):
            error_msg = response.get('error', '알 수 없는 오류')
            logger.error(f"네이버 API 오류: {error_msg}")
            return {
                "success": False,
                "error": f"네이버 API 오류: {error_msg}"
            }

        # 상품 데이터 처리 및 DB 저장
        api_data = response.get('data', {})
        products_data = api_data.get('contents', []) if isinstance(api_data, dict) else []
        logger.info(f"네이버 API에서 {len(products_data)}개 상품 조회됨")

        # 데이터베이스에 상품 저장
        saved_count = 0
        for product in products_data:
            try:
                if isinstance(product, dict) and 'channelProducts' in product:
                    channel_products = product.get('channelProducts', [])
                    if channel_products and len(channel_products) > 0:
                        channel_product = channel_products[0]

                        # 상품 정보 추출 (실제 API 응답 구조에 맞게 수정)
                        product_data = {
                            'channel_product_no': str(channel_product.get('channelProductNo', '')),
                            'origin_product_no': str(product.get('originProductNo', '')),
                            'product_name': channel_product.get('name', ''),  # name은 channelProduct에 있음
                            'status_type': channel_product.get('statusType', ''),
                            'sale_price': channel_product.get('salePrice', 0),
                            'discounted_price': channel_product.get('discountedPrice', 0),
                            'stock_quantity': channel_product.get('stockQuantity', 0),
                            'category_id': channel_product.get('categoryId', ''),
                            'category_name': channel_product.get('wholeCategoryName', '').split('>')[-1] if channel_product.get('wholeCategoryName') else '',
                            'brand_name': channel_product.get('brandName', ''),
                            'manufacturer_name': channel_product.get('manufacturerName', ''),
                            'model_name': channel_product.get('modelName', ''),
                            'seller_management_code': channel_product.get('sellerManagementCode', ''),
                            'reg_date': channel_product.get('regDate', ''),
                            'modified_date': channel_product.get('modifiedDate', ''),
                            'representative_image_url': channel_product.get('representativeImage', {}).get('url', '') if isinstance(channel_product.get('representativeImage'), dict) else '',
                            'whole_category_name': channel_product.get('wholeCategoryName', ''),
                            'whole_category_id': channel_product.get('wholeCategoryId', ''),
                            'delivery_fee': channel_product.get('deliveryFee', 0),
                            'return_fee': channel_product.get('returnFee', 0),
                            'exchange_fee': channel_product.get('exchangeFee', 0),
                            'discount_method': channel_product.get('discountMethod', ''),
                            'customer_benefit': channel_product.get('customerBenefit', '')
                        }

                        # 데이터베이스에 저장
                        order_manager.db_manager.save_product(product_data)
                        saved_count += 1
                        logger.debug(f"상품 저장 완료: {product_data['product_name']}")

            except Exception as save_error:
                logger.warning(f"상품 저장 오류: {save_error}")
                continue

        logger.info(f"상품 새로고침 완료: {saved_count}개 저장됨")

        # 업데이트된 상품 목록 조회
        products = order_manager.db_manager.get_all_products()

        # 웹 인터페이스용 데이터 포맷
        formatted_products = []
        for product in products:
            product_dict = {
                'id': product.get('channel_product_no', ''),
                'product_id': product.get('channel_product_no', ''),
                'name': product.get('product_name', ''),
                'price': product.get('sale_price', 0),
                'stock': product.get('stock_quantity', 0),
                'category': product.get('category_name', ''),
                'status': product.get('status_type', ''),
                'brand': product.get('brand_name', ''),
                'image_url': product.get('representative_image_url', ''),
                'created_at': product.get('reg_date', ''),
                'sales_count': 0
            }
            formatted_products.append(product_dict)

        return {
            "success": True,
            "products": formatted_products,
            "count": len(formatted_products),
            "refreshed_from_api": True,
            "saved_count": saved_count,
            "message": f"네이버 API에서 {saved_count}개 상품을 새로고침했습니다"
        }

    except Exception as e:
        logger.error(f"상품 새로고침 API 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": web_config.get('APP_VERSION', '1.0.0'),
        "timestamp": datetime.now().isoformat(),
        "monitoring_active": order_manager.monitoring_active,
        "memory_usage": "lightweight"
    }

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    logger.info(f"{get_detailed_version_info()} 웹서버 시작")
    logger.info(f"모니터링 상태: {order_manager.monitoring_active}")
    logger.info("경량 웹서버 시작 완료 - t2.micro 최적화 버전")

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행"""
    order_manager.monitoring_active = False
    logger.info("웹서버 종료")

@app.get("/api/settings")
async def get_settings():
    """설정 조회"""
    try:
        # 설정값 전체 반환 (웹 관리자용)
        settings = {
            # 기본설정
            "client_id": web_config.get('NAVER_CLIENT_ID', ''),
            "client_secret": web_config.get('NAVER_CLIENT_SECRET', ''),
            "discord_webhook": web_config.get('DISCORD_WEBHOOK_URL', ''),
            "discord_enabled": web_config.get_bool('DISCORD_ENABLED', False),
            "check_interval": web_config.get_int('CHECK_INTERVAL', 300),
            "refresh_interval": web_config.get_int('REFRESH_INTERVAL', 60),
            "auto_refresh": web_config.get_bool('AUTO_REFRESH', True),

            # 조건설정
            "dashboard_period": web_config.get_int('DASHBOARD_PERIOD_DAYS', 5),
            "quick_period": web_config.get_int('QUICK_PERIOD_SETTING', 3),

            # IP 설정
            "allowed_ips": web_config.get('ALLOWED_IPS', '121.190.40.153,175.125.204.97'),

            # 탭별 기간 설정
            "new_order_days": web_config.get_int('NEW_ORDER_DEFAULT_DAYS', 3),
            "shipping_pending_days": web_config.get_int('SHIPPING_PENDING_DEFAULT_DAYS', 3),
            "shipping_in_progress_days": web_config.get_int('SHIPPING_IN_PROGRESS_DEFAULT_DAYS', 30),
            "shipping_completed_days": web_config.get_int('SHIPPING_COMPLETED_DEFAULT_DAYS', 7),
            "purchase_decided_days": web_config.get_int('PURCHASE_DECIDED_DEFAULT_DAYS', 3),
            "cancel_days": web_config.get_int('CANCEL_DEFAULT_DAYS', 30),
            "return_exchange_days": web_config.get_int('RETURN_EXCHANGE_DEFAULT_DAYS', 15),
            "cancel_return_exchange_days": web_config.get_int('CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS', 7),

            # 체크박스 설정들
            "order_status_types": web_config.get('ORDER_STATUS_TYPES', 'PAYMENT_WAITING,PAYED,DELIVERING'),
            "product_status_types": web_config.get('PRODUCT_STATUS_TYPES', 'SALE,WAIT,OUTOFSTOCK'),
            "order_columns": web_config.get('ORDER_COLUMNS', '주문ID,주문자,상품명,옵션정보,수량,금액,배송지주소,배송예정일,주문일시,상태')
        }

        # API 자격증명은 확인용으로 실제 값 표시 (편집은 .env 파일에서만)
        # 마스킹 제거 - 설정 확인 및 연결 테스트용

        return {"success": True, "data": settings}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/settings/period/{page_type}")
async def get_period_setting(page_type: str):
    """페이지 타입별 기본 기간 설정 반환"""
    try:
        # 페이지 타입에 따른 환경변수 키 매핑
        period_mapping = {
            'new-orders': 'NEW_ORDER_DEFAULT_DAYS',
            'new_orders': 'NEW_ORDER_DEFAULT_DAYS',  # 신규주문 별칭
            'shipping-pending': 'SHIPPING_PENDING_DEFAULT_DAYS',
            'shipping_pending': 'SHIPPING_PENDING_DEFAULT_DAYS',  # 발송대기 별칭
            'shipping-in-progress': 'SHIPPING_IN_PROGRESS_DEFAULT_DAYS',
            'shipping_in_progress': 'SHIPPING_IN_PROGRESS_DEFAULT_DAYS',  # 배송중 별칭
            'shipping-completed': 'SHIPPING_COMPLETED_DEFAULT_DAYS',
            'shipping_completed': 'SHIPPING_COMPLETED_DEFAULT_DAYS',  # 배송완료 별칭
            'purchase-decided': 'PURCHASE_DECIDED_DEFAULT_DAYS',
            'purchase_decided': 'PURCHASE_DECIDED_DEFAULT_DAYS',  # 구매확정 별칭
            'cancel': 'CANCEL_DEFAULT_DAYS',
            'cancel_orders': 'CANCEL_DEFAULT_DAYS',  # 취소주문 페이지 별칭
            'return-exchange': 'RETURN_EXCHANGE_DEFAULT_DAYS',
            'return_exchange': 'RETURN_EXCHANGE_DEFAULT_DAYS',  # 반품교환 별칭
            'returns_exchanges': 'RETURN_EXCHANGE_DEFAULT_DAYS',  # 반품교환 별칭2
            'cancel-return-exchange': 'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS',
            'cancel_return_exchange': 'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS'  # 취소반품교환 별칭
        }

        # 기본값 매핑
        default_values = {
            'new-orders': 3,
            'new_orders': 3,  # 신규주문 별칭
            'shipping-pending': 3,
            'shipping_pending': 3,  # 발송대기 별칭
            'shipping-in-progress': 3,
            'shipping_in_progress': 3,  # 배송중 별칭
            'shipping-completed': 3,
            'shipping_completed': 3,  # 배송완료 별칭
            'purchase-decided': 3,
            'purchase_decided': 3,  # 구매확정 별칭
            'cancel': 3,
            'cancel_orders': 3,  # 취소주문 페이지 별칭
            'return-exchange': 3,
            'return_exchange': 3,  # 반품교환 별칭
            'returns_exchanges': 3,  # 반품교환 별칭2
            'cancel-return-exchange': 3,
            'cancel_return_exchange': 3  # 취소반품교환 별칭
        }

        if page_type not in period_mapping:
            return {"success": False, "error": f"지원하지 않는 페이지 타입: {page_type}"}

        env_key = period_mapping[page_type]
        default_days = default_values[page_type]

        days = web_config.get_int(env_key, default_days)

        return {
            "success": True,
            "data": {
                "page_type": page_type,
                "days": days,
                "env_key": env_key
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/settings/period/{page_type}")
async def save_period_setting(page_type: str, request_data: dict):
    """페이지 타입별 기본 기간 설정 저장"""
    try:
        # 페이지 타입에 따른 환경변수 키 매핑
        period_mapping = {
            'new-orders': 'NEW_ORDER_DEFAULT_DAYS',
            'new_orders': 'NEW_ORDER_DEFAULT_DAYS',  # 신규주문 별칭
            'shipping-pending': 'SHIPPING_PENDING_DEFAULT_DAYS',
            'shipping_pending': 'SHIPPING_PENDING_DEFAULT_DAYS',  # 발송대기 별칭
            'shipping-in-progress': 'SHIPPING_IN_PROGRESS_DEFAULT_DAYS',
            'shipping_in_progress': 'SHIPPING_IN_PROGRESS_DEFAULT_DAYS',  # 배송중 별칭
            'shipping-completed': 'SHIPPING_COMPLETED_DEFAULT_DAYS',
            'shipping_completed': 'SHIPPING_COMPLETED_DEFAULT_DAYS',  # 배송완료 별칭
            'purchase-decided': 'PURCHASE_DECIDED_DEFAULT_DAYS',
            'purchase_decided': 'PURCHASE_DECIDED_DEFAULT_DAYS',  # 구매확정 별칭
            'cancel': 'CANCEL_DEFAULT_DAYS',
            'cancel_orders': 'CANCEL_DEFAULT_DAYS',  # 취소주문 페이지 별칭
            'return-exchange': 'RETURN_EXCHANGE_DEFAULT_DAYS',
            'return_exchange': 'RETURN_EXCHANGE_DEFAULT_DAYS',  # 반품교환 별칭
            'returns_exchanges': 'RETURN_EXCHANGE_DEFAULT_DAYS',  # 반품교환 별칭2
            'cancel-return-exchange': 'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS',
            'cancel_return_exchange': 'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS'  # 취소반품교환 별칭
        }

        if page_type not in period_mapping:
            return {"success": False, "error": f"지원하지 않는 페이지 타입: {page_type}"}

        if 'days' not in request_data:
            return {"success": False, "error": "days 값이 필요합니다"}

        days = int(request_data['days'])
        if days < 1 or days > 365:
            return {"success": False, "error": "기간은 1일에서 365일 사이여야 합니다"}

        env_key = period_mapping[page_type]

        # 환경 설정에 저장
        web_config.set(env_key, str(days))

        # .env 파일에 저장
        web_config.save()

        logger.info(f"페이지별 기간 설정 저장: {page_type} -> {days}일 ({env_key})")

        return {
            "success": True,
            "data": {
                "page_type": page_type,
                "days": days,
                "env_key": env_key,
                "message": f"{page_type} 페이지의 기본 기간이 {days}일로 저장되었습니다"
            }
        }
    except ValueError:
        return {"success": False, "error": "올바른 숫자를 입력해주세요"}
    except Exception as e:
        logger.error(f"기간 설정 저장 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/settings")
async def save_settings(settings_data: dict):
    """설정 저장 - 실제로 .env 파일에 저장 (상세 로깅 포함)"""
    import os
    import time

    try:
        logger.info("=" * 60)
        logger.info(f"🔧 설정 저장 프로세스 시작 - 받은 데이터: {len(settings_data)}개 항목")
        logger.info(f"📝 요청된 설정 데이터: {settings_data}")

        # .env 파일 상태 확인 (저장 전)
        env_file_path = '.env'
        if os.path.exists(env_file_path):
            file_stat_before = os.stat(env_file_path)
            logger.info(f"📄 저장 전 .env 파일 상태:")
            logger.info(f"   - 크기: {file_stat_before.st_size} bytes")
            logger.info(f"   - 마지막 수정: {time.ctime(file_stat_before.st_mtime)}")
        else:
            logger.warning(f"⚠️  .env 파일이 존재하지 않음: {env_file_path}")

        # 웹 폼 필드명을 환경변수명에 매핑 (보안 관련 자격증명 제외하여 덮어쓰기 방지)
        field_mapping = {
            # 'client_id': 'NAVER_CLIENT_ID',  # 보안상 설정 화면에서 변경 불가
            # 'client_secret': 'NAVER_CLIENT_SECRET',  # 보안상 설정 화면에서 변경 불가
            # 'discord_webhook': 'DISCORD_WEBHOOK_URL',  # 보안상 설정 화면에서 변경 불가
            'discord_enabled': 'DISCORD_ENABLED',
            'check_interval': 'CHECK_INTERVAL',
            'refresh_interval': 'REFRESH_INTERVAL',
            'auto_refresh': 'AUTO_REFRESH',
            'dashboard_period': 'DASHBOARD_PERIOD_DAYS',
            'quick_period': 'QUICK_PERIOD_SETTING',
            'allowed_ips': 'ALLOWED_IPS',
            'new_order_days': 'NEW_ORDER_DEFAULT_DAYS',
            'shipping_pending_days': 'SHIPPING_PENDING_DEFAULT_DAYS',
            'shipping_in_progress_days': 'SHIPPING_IN_PROGRESS_DEFAULT_DAYS',
            'shipping_completed_days': 'SHIPPING_COMPLETED_DEFAULT_DAYS',
            'purchase_decided_days': 'PURCHASE_DECIDED_DEFAULT_DAYS',
            'cancel_days': 'CANCEL_DEFAULT_DAYS',
            'return_exchange_days': 'RETURN_EXCHANGE_DEFAULT_DAYS',
            'cancel_return_exchange_days': 'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS',
            'order_status_types': 'ORDER_STATUS_TYPES',
            'product_status_types': 'PRODUCT_STATUS_TYPES',
            'order_columns': 'ORDER_COLUMNS'
        }

        # 변경 전 값들 기록 (실제 환경변수명으로)
        original_values = {}
        for web_key, env_key in field_mapping.items():
            if web_key in settings_data:
                original_values[web_key] = web_config.get(env_key)
        logger.info(f"🔍 변경 전 원본 값들: {original_values}")

        # 각 설정값을 환경 변수에 설정
        saved_settings = {}
        logger.info("🔄 환경 변수 설정 시작...")

        for web_key, value in settings_data.items():
            # 웹 필드명을 환경변수명으로 변환
            env_key = field_mapping.get(web_key, web_key.upper())

            # 값 타입에 따른 변환
            if isinstance(value, bool):
                str_value = 'true' if value else 'false'
            elif isinstance(value, (int, float)):
                str_value = str(value)
            else:
                str_value = str(value) if value is not None else ''

            # 환경 변수에 설정 (실제 환경변수명으로)
            logger.info(f"   🏷️  {web_key}({env_key}): '{original_values.get(web_key, 'None')}' → '{str_value}'")
            web_config.set(env_key, str_value)
            saved_settings[env_key] = str_value

        logger.info(f"✅ 환경 변수 설정 완료 - {len(saved_settings)}개 항목")

        # .env 파일에 저장
        logger.info("💾 .env 파일 저장 시작...")
        save_start_time = time.time()

        try:
            web_config.save_to_env_file()
            save_end_time = time.time()
            logger.info(f"✅ .env 파일 저장 완료 - 소요시간: {save_end_time - save_start_time:.3f}초")
        except Exception as save_error:
            logger.error(f"❌ .env 파일 저장 실패: {save_error}")
            raise save_error

        # .env 파일 상태 확인 (저장 후)
        if os.path.exists(env_file_path):
            file_stat_after = os.stat(env_file_path)
            logger.info(f"📄 저장 후 .env 파일 상태:")
            logger.info(f"   - 크기: {file_stat_after.st_size} bytes (변화: {file_stat_after.st_size - file_stat_before.st_size:+d})")
            logger.info(f"   - 마지막 수정: {time.ctime(file_stat_after.st_mtime)}")

            # 파일이 실제로 변경되었는지 확인
            if file_stat_after.st_mtime > file_stat_before.st_mtime:
                logger.info("✅ 파일이 성공적으로 업데이트됨")
            else:
                logger.warning("⚠️  파일 수정 시간이 변경되지 않음")

        # 파일 내용 일부 확인
        try:
            with open(env_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                logger.info(f"📖 .env 파일 내용 확인 - 총 {len(lines)}줄")

                # 저장된 설정들이 파일에 실제로 있는지 확인
                for key, value in saved_settings.items():
                    expected_line = f"{key}={value}"
                    found = any(expected_line in line for line in lines)
                    logger.info(f"   🔍 {key}={value}: {'✅ 발견' if found else '❌ 없음'}")

        except Exception as read_error:
            logger.error(f"❌ .env 파일 읽기 실패: {read_error}")

        # 설정 다시 로드하여 확인
        logger.info("🔄 설정 파일 다시 로드 시작...")
        reload_start_time = time.time()
        web_config.reload()
        reload_end_time = time.time()
        logger.info(f"✅ 설정 파일 다시 로드 완료 - 소요시간: {reload_end_time - reload_start_time:.3f}초")

        # 저장된 설정값들 최종 확인
        verification_results = {}
        all_verified = True

        logger.info("🔍 저장 결과 검증 시작...")
        for key, expected_value in saved_settings.items():
            current_value = web_config.get(key)
            is_match = current_value == expected_value
            verification_results[key] = {
                'expected': expected_value,
                'actual': current_value,
                'match': is_match
            }

            status_icon = "✅" if is_match else "❌"
            logger.info(f"   {status_icon} {key}: 예상='{expected_value}', 실제='{current_value}', 일치={is_match}")

            if not is_match:
                all_verified = False

        if all_verified:
            logger.info("🎉 모든 설정이 성공적으로 저장되고 검증됨!")
        else:
            logger.warning("⚠️  일부 설정의 검증에 실패함")

        logger.info("=" * 60)

        return {
            "success": True,
            "message": f"설정이 성공적으로 저장되었습니다. ({len(saved_settings)}개 항목)",
            "saved_count": len(saved_settings),
            "saved_settings": saved_settings,
            "verification_results": verification_results,
            "all_verified": all_verified,
            "file_updated": file_stat_after.st_mtime > file_stat_before.st_mtime if 'file_stat_after' in locals() else False
        }

    except Exception as e:
        logger.error(f"💥 설정 저장 중 치명적 오류 발생: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📋 상세 오류 트레이스:\n{traceback.format_exc()}")
        return {"success": False, "error": str(e), "error_type": type(e).__name__}

@app.get("/api/debug-init")
async def debug_initialization():
    """서버 초기화 상태 디버깅"""
    try:
        return {
            "success": True,
            "debug_info": {
                "naver_api_initialized": bool(order_manager.naver_api),
                "client_id": web_config.get('NAVER_CLIENT_ID')[:4] + "****" if web_config.get('NAVER_CLIENT_ID') else None,
                "client_secret_length": len(web_config.get('NAVER_CLIENT_SECRET', '')),
                "notification_manager": bool(order_manager.notification_manager),
                "discord_webhook_set": bool(web_config.get('DISCORD_WEBHOOK_URL')),
                "env_file_exists": os.path.exists('.env')
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/test-api")
async def test_api():
    """네이버 API 실제 토큰 발급 테스트"""
    try:
        client_id = web_config.get('NAVER_CLIENT_ID')
        client_secret = web_config.get('NAVER_CLIENT_SECRET')

        print(f"[DEBUG] 웹에서 가져온 client_id: {client_id}")
        print(f"[DEBUG] 웹에서 가져온 client_secret: {client_secret}")
        print(f"[DEBUG] client_secret 길이: {len(client_secret) if client_secret else 0}")

        # 직접 .env 파일에서 읽어서 비교
        import os
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('NAVER_CLIENT_SECRET='):
                        direct_secret = line.split('=', 1)[1].strip()
                        print(f"[DEBUG] .env 파일에서 직접 읽은 client_secret: {direct_secret}")
                        print(f"[DEBUG] .env 파일 secret 길이: {len(direct_secret)}")
                        break
                    elif line.startswith('NAVER_CLIENT_ID='):
                        direct_id = line.split('=', 1)[1].strip()
                        if client_id == "****" or len(client_id) <= 4:
                            print(f"[DEBUG] .env 파일에서 직접 읽은 client_id: {direct_id}")
                            client_id = direct_id
                else:
                    direct_secret = ''
        except Exception as e:
            print(f"[DEBUG] .env 파일 직접 읽기 실패: {e}")
            direct_secret = ''

        # 만약 config.get()이 마스킹된 값을 반환한다면, 직접 파일에서 읽은 값 사용
        if client_secret == "****" or len(client_secret) <= 4:
            print(f"[DEBUG] 마스킹된 값 감지! .env 파일에서 직접 읽은 값 사용")
            client_secret = direct_secret

        if not client_id or not client_secret:
            return {"success": False, "error": "API 키가 설정되지 않았습니다"}

        # 실제 네이버 API 토큰 발급 테스트
        api = NaverShoppingAPI(client_id, client_secret)
        token_success = api.get_access_token()

        if token_success:
            return {
                "success": True,
                "message": "네이버 API 토큰 발급 성공",
                "token_available": True
            }
        else:
            return {
                "success": False,
                "error": "네이버 API 토큰 발급 실패",
                "token_available": False
            }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test-discord")
async def test_discord():
    """Discord 알림 테스트"""
    try:
        webhook_url = web_config.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            return {"success": False, "error": "Discord 웹훅 URL이 설정되지 않았습니다"}

        # 테스트 알림 전송
        order_manager.notification_manager.send_discord_notification(
            "🧪 테스트 알림",
            "WithUs 주문관리 시스템에서 발송하는 테스트 알림입니다.\n\n설정이 정상적으로 작동하고 있습니다! ✅",
            0x00ff00
        )

        return {"success": True, "message": "Discord 알림이 전송되었습니다"}
    except Exception as e:
        logger.error(f"Discord 테스트 오류: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/test-notifications")
async def test_notifications():
    """알림 테스트 (대시보드용)"""
    try:
        if not order_manager.notification_manager:
            return {"success": False, "error": "알림 관리자가 초기화되지 않았습니다"}

        # 대시보드용 테스트 알림 전송
        order_manager.notification_manager.send_discord_notification(
            "🔔 대시보드 알림 테스트",
            f"WithUs 주문관리 웹 대시보드에서 발송하는 테스트 알림입니다.\n\n**테스트 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**상태**: ✅ 정상 작동",
            0x0099ff
        )

        return {"success": True, "message": "알림 테스트가 완료되었습니다"}
    except Exception as e:
        logger.error(f"알림 테스트 오류: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/test-settings-save")
async def test_settings_save():
    """설정 저장 테스트 - 실제 .env 파일 저장 확인"""
    try:
        logger.info("=== 설정 저장 테스트 시작 ===")

        # 테스트용 설정 데이터
        test_settings = {
            'CHECK_INTERVAL': 600,  # 10분으로 변경
            'DASHBOARD_PERIOD_DAYS': 7,  # 7일로 변경
            'DISCORD_ENABLED': True,
            'AUTO_REFRESH': True,
            'NOTIFY_NEW_ORDERS': True,
            'STOCK_THRESHOLD': 15
        }

        logger.info(f"테스트 설정: {test_settings}")

        # 변경 전 값 기록
        before_values = {}
        for key in test_settings.keys():
            before_values[key] = config.get(key)

        logger.info(f"변경 전 값: {before_values}")

        # 설정 저장 호출
        result = await save_settings(test_settings)

        if result['success']:
            # 변경 후 값 확인
            after_values = {}
            for key in test_settings.keys():
                after_values[key] = config.get(key)

            logger.info(f"변경 후 값: {after_values}")

            # .env 파일 내용 확인
            try:
                with open('.env', 'r', encoding='utf-8') as f:
                    env_content = f.read()
                    logger.info(f".env 파일 마지막 10줄:")
                    lines = env_content.split('\n')
                    for line in lines[-10:]:
                        if line.strip():
                            logger.info(f"  {line}")

            except Exception as e:
                logger.error(f".env 파일 읽기 실패: {e}")

            return {
                "success": True,
                "message": "설정 저장 테스트 완료",
                "test_settings": test_settings,
                "before_values": before_values,
                "after_values": after_values,
                "save_result": result
            }
        else:
            return {
                "success": False,
                "error": "설정 저장 실패",
                "save_result": result
            }

    except Exception as e:
        logger.error(f"설정 저장 테스트 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/current-ip")
async def get_current_server_ip():
    """서버의 현재 공인 IP 확인 (네이버 API 호출용)"""
    try:
        import requests

        # 여러 IP 확인 서비스 시도
        services = [
            'https://api.ipify.org?format=json',
            'https://ipapi.co/json/',
            'https://httpbin.org/ip'
        ]

        for service in services:
            try:
                response = requests.get(service, timeout=10)
                if response.status_code == 200:
                    data = response.json()

                    # 서비스별 응답 형식 처리
                    if 'ip' in data:
                        ip = data['ip']
                    elif 'origin' in data:  # httpbin
                        ip = data['origin']
                    else:
                        continue

                    # IP 형식 검증
                    import re
                    pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
                    if re.match(pattern, ip):
                        # 허가 여부 확인
                        allowed_ips = web_config.get('ALLOWED_IPS', '121.190.40.153,175.125.204.97').split(',')
                        allowed_ips = [ip.strip() for ip in allowed_ips if ip.strip()]
                        is_allowed = ip in allowed_ips

                        return {
                            "success": True,
                            "ip": ip,
                            "is_allowed": is_allowed,
                            "service_used": service
                        }
            except Exception as e:
                logger.warning(f"IP 서비스 {service} 실패: {e}")
                continue

        return {"success": False, "error": "모든 IP 확인 서비스에서 실패했습니다"}

    except Exception as e:
        logger.error(f"서버 IP 확인 오류: {e}")
        return {"success": False, "error": str(e)}

# ==================== API 테스트 엔드포인트 ====================

@app.post("/api/test-api-token")
async def test_api_token():
    """네이버 API 토큰 발급 테스트"""
    try:
        logger.info("네이버 API 토큰 발급 테스트 시작")

        # 네이버 API 인스턴스 생성
        client_id = web_config.get('NAVER_CLIENT_ID')
        client_secret = web_config.get('NAVER_CLIENT_SECRET')

        if not client_id or not client_secret:
            return {
                "success": False,
                "error": "네이버 API 자격증명이 설정되지 않았습니다. 기본 설정 탭에서 클라이언트 ID와 시크릿을 설정해주세요."
            }

        from naver_api import NaverShoppingAPI
        naver_api = NaverShoppingAPI(client_id, client_secret)

        # 토큰 발급 시도
        token_success = naver_api.get_access_token()

        if token_success and naver_api.access_token:
            logger.info(f"토큰 발급 성공: {naver_api.access_token[:20]}...")
            return {
                "success": True,
                "token": naver_api.access_token,
                "message": "네이버 API 토큰 발급에 성공했습니다."
            }
        else:
            return {
                "success": False,
                "error": "토큰 발급에 실패했습니다. 클라이언트 ID와 시크릿을 확인해주세요."
            }

    except Exception as e:
        logger.error(f"API 토큰 테스트 오류: {e}")
        return {"success": False, "error": f"토큰 테스트 중 오류가 발생했습니다: {str(e)}"}

@app.post("/api/test-orders-api")
async def test_orders_api():
    """네이버 주문 API 연결 테스트"""
    try:
        logger.info("네이버 주문 API 연결 테스트 시작")

        # 네이버 API 인스턴스 생성
        client_id = web_config.get('NAVER_CLIENT_ID')
        client_secret = web_config.get('NAVER_CLIENT_SECRET')

        if not client_id or not client_secret:
            return {
                "success": False,
                "error": "네이버 API 자격증명이 설정되지 않았습니다."
            }

        from naver_api import NaverShoppingAPI
        naver_api = NaverShoppingAPI(client_id, client_secret)

        # 최근 1일 주문 조회 테스트 (간단한 테스트)
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        response = naver_api.get_orders(
            start_date=start_date_str,
            end_date=end_date_str,
            order_status='PAYED'  # 단일 상태로 테스트
        )

        if response and 'body' in response:
            orders = response['body'].get('orderInfoList', [])
            order_count = len(orders)

            logger.info(f"주문 API 테스트 성공: {order_count}건 조회")
            return {
                "success": True,
                "order_count": order_count,
                "test_period": f"{start_date_str} ~ {end_date_str}",
                "message": f"주문 API 연결에 성공했습니다. (테스트 기간: 최근 1일)"
            }
        else:
            return {
                "success": False,
                "error": "주문 API 응답 형식이 올바르지 않습니다."
            }

    except Exception as e:
        logger.error(f"주문 API 테스트 오류: {e}")
        return {"success": False, "error": f"주문 API 테스트 중 오류가 발생했습니다: {str(e)}"}

@app.post("/api/test-products-api")
async def test_products_api():
    """네이버 상품 API 연결 테스트"""
    try:
        logger.info("네이버 상품 API 연결 테스트 시작")

        # 네이버 API 인스턴스 생성
        client_id = web_config.get('NAVER_CLIENT_ID')
        client_secret = web_config.get('NAVER_CLIENT_SECRET')

        if not client_id or not client_secret:
            return {
                "success": False,
                "error": "네이버 API 자격증명이 설정되지 않았습니다."
            }

        from naver_api import NaverShoppingAPI
        naver_api = NaverShoppingAPI(client_id, client_secret)

        # 상품 목록 조회 테스트 (첫 페이지만)
        response = naver_api.get_products(
            product_status_type='SALE',  # 판매중인 상품만
            page=1,
            size=10  # 작은 크기로 테스트
        )

        if response and 'body' in response:
            products = response['body'].get('productInfoList', [])
            product_count = len(products)
            total_count = response['body'].get('totalCount', 0)

            logger.info(f"상품 API 테스트 성공: {product_count}개 조회 (전체: {total_count}개)")
            return {
                "success": True,
                "product_count": product_count,
                "total_count": total_count,
                "message": f"상품 API 연결에 성공했습니다. (테스트: 10개 조회, 전체: {total_count}개)"
            }
        else:
            return {
                "success": False,
                "error": "상품 API 응답 형식이 올바르지 않습니다."
            }

    except Exception as e:
        logger.error(f"상품 API 테스트 오류: {e}")
        return {"success": False, "error": f"상품 API 테스트 중 오류가 발생했습니다: {str(e)}"}

if __name__ == "__main__":
    # 개발용 서버 실행
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"""
    🚀 {get_full_title()} 웹서버 시작

    📡 서버 주소: http://{host}:{port}
    💾 메모리 최적화: t2.micro 호환
    🔄 백그라운드 모니터링: {'활성화' if order_manager.monitoring_active else '비활성화'}

    서버를 중지하려면 Ctrl+C를 누르세요.
    """)

    uvicorn.run(
        "web_server:app",
        host=host,
        port=port,
        reload=False,  # 메모리 절약을 위해 비활성화
        log_level="info"
    )