import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List
import json

from database import DatabaseManager
from naver_api import NaverShoppingAPI
from notification_manager import NotificationManager

class BackgroundMonitor:
    def __init__(self, db_manager: DatabaseManager, naver_api: NaverShoppingAPI, 
                 notification_manager: NotificationManager, check_interval: int = 300):
        self.db_manager = db_manager
        self.naver_api = naver_api
        self.notification_manager = notification_manager
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
        self.last_check_time = None
        self.last_order_count = 0
        
    def start_monitoring(self):
        """백그라운드 모니터링 시작"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"백그라운드 모니터링 시작 - 체크 간격: {self.check_interval}초")
    
    def stop_monitoring(self):
        """백그라운드 모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("백그라운드 모니터링 중지")
    
    def _monitor_loop(self):
        """모니터링 루프"""
        while self.monitoring:
            try:
                self._check_new_orders()
                self._check_status_changes()
                self._check_urgent_inquiries()
                
                self.last_check_time = datetime.now()
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"모니터링 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기
    
    def _check_new_orders(self):
        """신규 주문 체크"""
        if not self.naver_api:
            return
        
        try:
            # 최근 1시간 내 주문 조회
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            new_orders = self.naver_api.get_orders(
                start_time.strftime('%Y-%m-%d'),
                end_time.strftime('%Y-%m-%d'),
                status='ORDERED'
            )
            
            # 데이터베이스에 없는 신규 주문 찾기
            for order in new_orders:
                existing_orders = self.db_manager.get_orders_by_status('신규주문')
                order_exists = any(o['order_id'] == order.get('orderId') for o in existing_orders)
                
                if not order_exists:
                    # 신규 주문 데이터베이스에 추가
                    order_data = {
                        'order_id': order.get('orderId'),
                        'order_date': order.get('orderDate'),
                        'customer_name': order.get('customerName'),
                        'customer_phone': order.get('customerPhone'),
                        'product_name': order.get('productName'),
                        'quantity': order.get('quantity', 1),
                        'price': order.get('price', 0),
                        'status': '신규주문',
                        'memo': ''
                    }
                    
                    if self.db_manager.add_order(order_data):
                        # 신규 주문 알림
                        self.notification_manager.send_new_order_notification(order_data)
                        print(f"신규 주문 알림: {order_data['order_id']}")
        
        except Exception as e:
            print(f"신규 주문 체크 오류: {e}")
    
    def _check_status_changes(self):
        """주문 상태 변경 체크"""
        if not self.naver_api:
            return
        
        try:
            # 모든 주문의 최신 상태 조회
            all_orders = self.db_manager.get_all_orders()
            
            for order in all_orders:
                # 네이버 API에서 최신 주문 정보 조회
                latest_order = self.naver_api.get_order_detail(order['order_id'])
                
                if latest_order:
                    new_status = self.naver_api._map_naver_status_to_local(
                        latest_order.get('status')
                    )
                    
                    if new_status != order['status']:
                        # 상태 변경 알림
                        self.notification_manager.send_status_change_notification(
                            order['order_id'],
                            order['status'],
                            new_status
                        )
                        
                        # 데이터베이스 상태 업데이트
                        self.db_manager.update_order_status(order['order_id'], new_status)
                        print(f"주문 상태 변경: {order['order_id']} - {order['status']} → {new_status}")
        
        except Exception as e:
            print(f"상태 변경 체크 오류: {e}")
    
    def _check_urgent_inquiries(self):
        """긴급 문의 체크"""
        try:
            # 긴급 문의 키워드
            urgent_keywords = ['긴급', 'ASAP', '빠른', '즉시', '당장', '급함', '급구']
            
            # 최근 주문의 메모 확인
            recent_orders = self.db_manager.get_all_orders()
            
            for order in recent_orders:
                memo = order.get('memo', '')
                if memo:
                    for keyword in urgent_keywords:
                        if keyword in memo:
                            # 긴급 문의 알림
                            inquiry_data = {
                                'customer_name': order['customer_name'],
                                'customer_phone': order['customer_phone'],
                                'content': memo,
                                'order_id': order['order_id']
                            }
                            
                            self.notification_manager.send_urgent_inquiry_notification(inquiry_data)
                            print(f"긴급 문의 알림: {order['order_id']}")
                            break
        
        except Exception as e:
            print(f"긴급 문의 체크 오류: {e}")
    
    def get_monitoring_status(self) -> Dict:
        """모니터링 상태 정보 반환"""
        return {
            'monitoring': self.monitoring,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'check_interval': self.check_interval,
            'thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False
        }
    
    def update_check_interval(self, interval: int):
        """체크 간격 업데이트"""
        self.check_interval = interval
        print(f"모니터링 체크 간격 변경: {interval}초")
    
    def force_check(self):
        """강제 체크 실행"""
        if self.monitoring:
            threading.Thread(target=self._check_new_orders, daemon=True).start()
            threading.Thread(target=self._check_status_changes, daemon=True).start()
            threading.Thread(target=self._check_urgent_inquiries, daemon=True).start()
            print("강제 체크 실행")
    
    def get_order_statistics(self) -> Dict:
        """주문 통계 정보 반환"""
        try:
            counts = self.db_manager.get_order_counts()
            
            # 시간대별 통계
            now = datetime.now()
            today_orders = []
            yesterday_orders = []
            
            all_orders = self.db_manager.get_all_orders()
            for order in all_orders:
                order_date = datetime.strptime(order['order_date'], '%Y-%m-%d')
                if order_date.date() == now.date():
                    today_orders.append(order)
                elif order_date.date() == (now - timedelta(days=1)).date():
                    yesterday_orders.append(order)
            
            return {
                'total_orders': len(all_orders),
                'status_counts': counts,
                'today_orders': len(today_orders),
                'yesterday_orders': len(yesterday_orders),
                'new_orders_today': len([o for o in today_orders if o['status'] == '신규주문']),
                'shipped_today': len([o for o in today_orders if o['status'] == '배송중']),
                'delivered_today': len([o for o in today_orders if o['status'] == '배송완료'])
            }
        
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}


