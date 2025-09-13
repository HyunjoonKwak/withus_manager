"""
WithUs 주문 관리 시스템 - 메인 애플리케이션
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, timedelta
import json
import os

from database import DatabaseManager
from naver_api import NaverShoppingAPI
from notification_manager import NotificationManager
from env_config import config
from ui_utils import enable_context_menu
from tabs import HomeTab, APITestTab, BasicSettingsTab, ConditionSettingsTab, OrdersTab, ShippingTab, ProductsTab


class WithUsOrderManager:
    """WithUs 주문 관리 시스템 메인 클래스"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WithUs 주문 관리 시스템")
        self.root.geometry("1400x900")
        
        # 데이터베이스 매니저 초기화
        print("데이터베이스 매니저 초기화 시작")
        self.db_manager = DatabaseManager()
        print("데이터베이스 매니저 초기화 완료")
        
        # API 및 알림 매니저 초기화
        self.naver_api = None
        self.notification_manager = None
        self.all_orders = []
        self.initialize_api()
        self.initialize_notifications()
        
        # UI 설정
        self.setup_ui()
        
        # 자동 로드
        self.auto_load_products()
        
        # 주기적 대시보드 새로고침
        self.start_dashboard_refresh()
    
    def setup_ui(self):
        """UI 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 탭 생성
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # 각 탭 생성
        self.home_tab = HomeTab(self.notebook, self)
        self.notebook.add(self.home_tab.frame, text="홈")
        
        self.orders_tab = OrdersTab(self.notebook, self)
        self.notebook.add(self.orders_tab.frame, text="주문관리")
        
        self.products_tab = ProductsTab(self.notebook, self)
        self.notebook.add(self.products_tab.frame, text="상품관리")
        
        self.shipping_tab = ShippingTab(self.notebook, self)
        self.notebook.add(self.shipping_tab.frame, text="배송관리")
        
        self.api_test_tab = APITestTab(self.notebook, self)
        self.notebook.add(self.api_test_tab.frame, text="API 테스트")
        
        self.basic_settings_tab = BasicSettingsTab(self.notebook, self)
        self.notebook.add(self.basic_settings_tab.frame, text="기본설정")
        
        self.condition_settings_tab = ConditionSettingsTab(self.notebook, self)
        self.notebook.add(self.condition_settings_tab.frame, text="조건설정")
        
        # 탭 변경 이벤트 바인딩
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 상태바
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side="bottom", fill="x")
    
    def on_tab_changed(self, event):
        """탭 변경 이벤트 핸들러"""
        try:
            # 현재 선택된 탭 가져오기
            selected_tab = self.notebook.select()
            tab_index = self.notebook.index(selected_tab)
            
            # 주문수집 탭 (인덱스 1)이 선택된 경우
            if tab_index == 1:  # 주문수집 탭
                if hasattr(self.orders_tab, 'is_first_load') and not self.orders_tab.is_first_load:
                    # 첫 로드가 아닌 경우 캐시된 데이터 표시
                    self.orders_tab.show_cached_orders()
                elif hasattr(self.orders_tab, 'is_first_load') and self.orders_tab.is_first_load:
                    # 첫 로드인 경우 자동으로 주문 조회
                    self.orders_tab.query_orders_from_api()
                    
        except Exception as e:
            print(f"탭 변경 이벤트 오류: {e}")
    
    def initialize_api(self):
        """API 초기화"""
        try:
            client_id = config.get('NAVER_CLIENT_ID')
            client_secret = config.get('NAVER_CLIENT_SECRET')
            
            if client_id and client_secret:
                self.naver_api = NaverShoppingAPI(client_id, client_secret)
                print("API 초기화 완료")
                return True
            else:
                print("API 설정이 없습니다. 설정 탭에서 API 정보를 입력해주세요.")
                self.naver_api = None
                return False
        except Exception as e:
            print(f"API 초기화 오류: {e}")
            self.naver_api = None
            return False
    
    def initialize_notifications(self):
        """알림 매니저 초기화"""
        try:
            self.notification_manager = NotificationManager()
            print("알림 매니저 초기화 완료")
        except Exception as e:
            print(f"알림 매니저 초기화 오류: {e}")
    
    def auto_load_products(self):
        """저장된 상품 자동 로드"""
        try:
            # 상품 상태 설정 로드
            saved_statuses = config.get('PRODUCT_STATUS_TYPES', 'SALE,OUTOFSTOCK,CLOSE')
            status_list = [s.strip() for s in saved_statuses.split(',')]
            
            # 데이터베이스에서 상품 로드
            products = self.db_manager.get_products()
            
            if products:
                # 상태별 필터링
                filtered_products = []
                for product in products:
                    if product.get('status_type') in status_list:
                        filtered_products.append(product)
                
                print(f"저장된 상품 {len(products)}개 중 {len(filtered_products)}개 필터링됨")
                
                # 홈 탭의 상품 트리뷰 업데이트 (UI가 준비된 후)
                self.root.after(1000, self.home_tab._update_products_tree, filtered_products)
            
        except Exception as e:
            print(f"자동 로드 오류: {e}")
    
    def start_dashboard_refresh(self):
        """대시보드 주기적 새로고침 시작"""
        # env 설정에서 자동 새로고침 설정 확인
        auto_refresh = config.get_bool('AUTO_REFRESH', False)
        refresh_interval = config.get_int('REFRESH_INTERVAL', 300)  # 기본값 300초
        
        print(f"자동 새로고침 설정: {auto_refresh}, 간격: {refresh_interval}초")
        
        if not auto_refresh:
            print("자동 새로고침이 비활성화되어 있습니다.")
            return
        
        def refresh_loop():
            while True:
                try:
                    time.sleep(refresh_interval)
                    if self.naver_api:
                        print(f"자동 대시보드 새로고침 실행 ({refresh_interval}초 간격)")
                        self.root.after(0, self.home_tab.refresh_dashboard)
                except Exception as e:
                    print(f"대시보드 새로고침 오류: {e}")
        
        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()
    
    def remove_duplicate_orders(self, orders):
        """중복된 주문 제거 (orderId 기준)"""
        if not isinstance(orders, list):
            return []
        
        seen_order_ids = set()
        unique_orders = []
        
        for order in orders:
            if isinstance(order, dict):
                order_id = order.get('orderId')
                if order_id and order_id not in seen_order_ids:
                    seen_order_ids.add(order_id)
                    unique_orders.append(order)
                elif order_id:
                    print(f"중복 주문 발견: {order_id}")
        
        print(f"중복 제거: {len(orders)}건 → {len(unique_orders)}건")
        return unique_orders
    
    def run(self):
        """애플리케이션 실행"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("애플리케이션 종료")
        except Exception as e:
            print(f"애플리케이션 실행 오류: {e}")


def main():
    """메인 함수"""
    try:
        app = WithUsOrderManager()
        app.run()
    except Exception as e:
        print(f"애플리케이션 시작 오류: {e}")
        messagebox.showerror("오류", f"애플리케이션 시작 실패: {str(e)}")


if __name__ == "__main__":
    main()
