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
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

# 기존 모듈들
from database import DatabaseManager
from naver_api import NaverShoppingAPI
from notification_manager import NotificationManager
from env_config import config
from version_utils import get_full_title, get_detailed_version_info

# 로깅
import logging
logging.basicConfig(level=logging.INFO)
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
            client_id = config.get('NAVER_CLIENT_ID')
            client_secret = config.get('NAVER_CLIENT_SECRET')

            if client_id and client_secret:
                self.naver_api = NaverShoppingAPI(client_id, client_secret)
                logger.info("네이버 API 초기화 완료")
            else:
                logger.warning("네이버 API 설정이 없습니다")

            discord_webhook = config.get('DISCORD_WEBHOOK_URL')
            if discord_webhook:
                self.notification_manager = NotificationManager(discord_webhook)
                logger.info("Discord 알림 초기화 완료")
            else:
                logger.warning("Discord 웹훅이 설정되지 않았습니다")

        except Exception as e:
            logger.error(f"API 초기화 오류: {e}")

    def _start_background_monitoring(self):
        """백그라운드 모니터링 시작"""
        if config.get_bool('AUTO_REFRESH', True):
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._background_monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            logger.info("백그라운드 모니터링 시작됨")

    def _background_monitoring_loop(self):
        """백그라운드 모니터링 루프"""
        check_interval = config.get_int('CHECK_INTERVAL', 300)  # 기본 5분

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

            # 대시보드 데이터 새로고침
            new_order_counts = self._get_dashboard_data()

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

    def _get_dashboard_data(self) -> Dict[str, int]:
        """대시보드 데이터 조회"""
        try:
            period_days = config.get_int('DASHBOARD_PERIOD_DAYS', 5)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            # 기존 홈탭 로직 활용
            from tabs.home_tab import HomeTab

            # 임시 홈탭 인스턴스로 데이터 조회
            # 실제로는 데이터베이스에서 직접 조회하도록 최적화 필요
            orders = self.db_manager.get_all_orders()

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

            for order in orders:
                status = getattr(order, 'status', '기타')
                if status in order_counts:
                    order_counts[status] += 1

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
                    config.get_int('DASHBOARD_PERIOD_DAYS', 5)
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
    version=config.get('APP_VERSION', '1.0.0')
)

# 템플릿 및 정적 파일 설정
templates = Jinja2Templates(directory="templates")

# 정적 파일이 있다면 마운트 (선택사항)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """홈 페이지"""
    try:
        # 대시보드 데이터 조회
        dashboard_data = order_manager._get_dashboard_data()

        context = {
            "request": request,
            "title": get_full_title(),
            "version_info": get_detailed_version_info(),
            "order_counts": dashboard_data,
            "last_check": order_manager.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if order_manager.last_check_time else "미확인",
            "monitoring_active": order_manager.monitoring_active,
            "total_orders": sum(dashboard_data.values())
        }

        return templates.TemplateResponse("home.html", context)

    except Exception as e:
        logger.error(f"홈 페이지 오류: {e}")
        raise HTTPException(status_code=500, detail="페이지 로딩 중 오류가 발생했습니다")

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """주문 목록 페이지"""
    context = {
        "request": request,
        "title": "주문 관리 - " + get_full_title(),
        "version_info": get_detailed_version_info()
    }
    return templates.TemplateResponse("orders.html", context)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """설정 페이지"""
    context = {
        "request": request,
        "title": "설정 - " + get_full_title(),
        "version_info": get_detailed_version_info()
    }
    return templates.TemplateResponse("settings.html", context)

@app.get("/api/dashboard/refresh")
async def refresh_dashboard():
    """대시보드 수동 새로고침"""
    try:
        order_counts = order_manager._get_dashboard_data()

        return {
            "success": True,
            "data": order_counts,
            "last_check": datetime.now().isoformat(),
            "total_orders": sum(order_counts.values())
        }
    except Exception as e:
        logger.error(f"대시보드 새로고침 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/monitoring/status")
async def get_monitoring_status():
    """모니터링 상태 조회"""
    return {
        "active": order_manager.monitoring_active,
        "last_check": order_manager.last_check_time.isoformat() if order_manager.last_check_time else None,
        "check_interval": config.get_int('CHECK_INTERVAL', 300),
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
async def get_orders():
    """주문 목록 조회 API"""
    try:
        orders = order_manager.db_manager.get_all_orders()

        # 간단한 직렬화
        order_list = []
        for order in orders:
            order_data = {
                "order_id": getattr(order, 'order_id', ''),
                "customer_name": getattr(order, 'customer_name', ''),
                "product_name": getattr(order, 'product_name', ''),
                "status": getattr(order, 'status', ''),
                "order_date": getattr(order, 'order_date', ''),
                "price": getattr(order, 'price', 0)
            }
            order_list.append(order_data)

        return {"success": True, "orders": order_list}

    except Exception as e:
        logger.error(f"주문 조회 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": config.get('APP_VERSION', '1.0.0'),
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
        # 보안상 실제 값은 마스킹하여 반환
        settings = {
            # 기본설정
            "client_id": config.get('NAVER_CLIENT_ID', ''),
            "client_secret": config.get('NAVER_CLIENT_SECRET', ''),
            "discord_webhook": config.get('DISCORD_WEBHOOK_URL', ''),
            "discord_enabled": config.get_bool('DISCORD_ENABLED', False),
            "check_interval": config.get_int('CHECK_INTERVAL', 300),
            "refresh_interval": config.get_int('REFRESH_INTERVAL', 60),
            "auto_refresh": config.get_bool('AUTO_REFRESH', True),

            # 조건설정
            "dashboard_period": config.get_int('DASHBOARD_PERIOD_DAYS', 5),
            "quick_period": config.get_int('QUICK_PERIOD_SETTING', 3),

            # IP 설정
            "allowed_ips": config.get('ALLOWED_IPS', '121.190.40.153,175.125.204.97'),

            # 탭별 기간 설정
            "new_order_days": config.get_int('NEW_ORDER_DEFAULT_DAYS', 3),
            "shipping_pending_days": config.get_int('SHIPPING_PENDING_DEFAULT_DAYS', 3),
            "shipping_in_progress_days": config.get_int('SHIPPING_IN_PROGRESS_DEFAULT_DAYS', 30),
            "shipping_completed_days": config.get_int('SHIPPING_COMPLETED_DEFAULT_DAYS', 7),
            "purchase_decided_days": config.get_int('PURCHASE_DECIDED_DEFAULT_DAYS', 3),
            "cancel_days": config.get_int('CANCEL_DEFAULT_DAYS', 30),
            "return_exchange_days": config.get_int('RETURN_EXCHANGE_DEFAULT_DAYS', 15),
            "cancel_return_exchange_days": config.get_int('CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS', 7),

            # 체크박스 설정들
            "order_status_types": config.get('ORDER_STATUS_TYPES', 'PAYMENT_WAITING,PAYED,DELIVERING'),
            "product_status_types": config.get('PRODUCT_STATUS_TYPES', 'SALE,WAIT,OUTOFSTOCK'),
            "order_columns": config.get('ORDER_COLUMNS', '주문ID,주문자,상품명,옵션정보,수량,금액,배송지주소,배송예정일,주문일시,상태')
        }

        # 민감한 정보 마스킹
        if settings["client_id"]:
            settings["client_id"] = settings["client_id"][-4:] if len(settings["client_id"]) > 4 else "****"
        if settings["client_secret"]:
            settings["client_secret"] = "****"
        if settings["discord_webhook"]:
            settings["discord_webhook"] = "****"

        return {"success": True, "data": settings}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/settings")
async def save_settings(settings_data: dict):
    """설정 저장 (실제로는 파일 수정이 필요하므로 현재는 시뮬레이션)"""
    try:
        # 실제 구현 시에는 .env 파일을 수정해야 함
        # 여기서는 간단한 확인만 수행
        return {"success": True, "message": "설정이 저장되었습니다. (실제 저장을 위해서는 .env 파일을 직접 수정해주세요)"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/test-api")
async def test_api():
    """네이버 API 연결 테스트"""
    try:
        client_id = config.get('NAVER_CLIENT_ID')
        client_secret = config.get('NAVER_CLIENT_SECRET')

        if not client_id or not client_secret:
            return {"success": False, "error": "API 키가 설정되지 않았습니다"}

        return {"success": True, "message": "API 설정이 확인되었습니다"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test-discord")
async def test_discord():
    """Discord 알림 테스트"""
    try:
        webhook_url = config.get('DISCORD_WEBHOOK_URL')
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