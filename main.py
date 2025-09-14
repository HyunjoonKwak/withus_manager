"""
쇼핑몰 주문관리시스템 - 메인 애플리케이션 (동적 버전 관리)
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, timedelta
import json
import os
import sys

# 로깅 설정 - 콘솔과 파일에 모두 출력
class TeeOutput:
    def __init__(self):
        self.terminal = sys.stdout
        self.log_file = None
        try:
            # 로그 파일을 현재 디렉토리에 생성
            log_path = os.path.join(os.getcwd(), 'withus_app.log')
            self.log_file = open(log_path, 'a', encoding='utf-8', buffering=1)  # 라인 버퍼링
            self.log_path = log_path  # 로그 경로 저장
            # 시작 시점 기록
            self.log_file.write(f"\n{'='*50}\n")
            self.log_file.write(f"{get_detailed_version_info()} 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_file.write(f"로그 파일 경로: {log_path}\n")
            self.log_file.write(f"{'='*50}\n")

            # 터미널에도 로그 파일 위치 출력
            startup_msg = f"💾 로그 파일 위치: {log_path}\n🚀 {get_detailed_version_info()} 시작 중...\n"
            print(startup_msg)

        except Exception as e:
            error_msg = f"로그 파일 생성 실패: {e}"
            print(error_msg)

    def write(self, message):
        # 터미널에 출력 (강제로 시도)
        try:
            # print 함수 직접 사용하여 터미널 출력 강제
            import sys
            import os

            # stderr로도 출력하여 확실히 보이도록
            if hasattr(sys, 'stderr') and sys.stderr:
                sys.stderr.write(message)
                sys.stderr.flush()

            # stdout으로도 출력
            if hasattr(sys, '__stdout__') and sys.__stdout__:
                sys.__stdout__.write(message)
                sys.__stdout__.flush()

            # macOS에서 Console.app으로 출력
            if os.name == 'posix':  # macOS/Linux
                try:
                    os.system(f'echo "{message.strip()}" > /dev/console')
                except:
                    pass

        except Exception as e:
            pass

        # 파일에 출력
        if self.log_file:
            try:
                self.log_file.write(message)
                self.log_file.flush()
            except:
                pass

    def flush(self):
        try:
            self.terminal.flush()
        except:
            pass
        if self.log_file:
            try:
                self.log_file.flush()
            except:
                pass

# stdout 및 stderr 리다이렉트 임시 비활성화 (무한 루프 방지)
# sys.stdout = TeeOutput()
# sys.stderr = TeeOutput()
# 동적 버전 정보를 위해 import 추가
from version_utils import get_detailed_version_info as get_version_for_log

try:
    version_info = get_version_for_log()
    print(f"💾 {version_info} - 로그 시스템 임시 비활성화")
except:
    print("💾 쇼핑몰 주문관리시스템 - 로그 시스템 임시 비활성화")

from database import DatabaseManager
from naver_api import NaverShoppingAPI
from notification_manager import NotificationManager
from env_config import config
from ui_utils import enable_context_menu
from version_utils import get_full_title, get_detailed_version_info
from tabs import HomeTab, APITestTab, BasicSettingsTab, ConditionSettingsTab, OrdersTab, NewOrderTab, ProductsTab, HelpTab, ShippingPendingTab, ShippingInProgressTab, ShippingCompletedTab, PurchaseDecidedTab, CancelTab, ReturnExchangeTab


class WithUsOrderManager:
    """쇼핑몰 주문관리시스템 메인 클래스 - 동적 버전 관리"""
    
    def __init__(self):
        import time
        app_start_time = time.time()
        # 동적 버전 정보 가져오기
        app_title = get_full_title()
        detailed_info = get_detailed_version_info()

        print(f"=== {detailed_info} 시작 ===")

        self.root = tk.Tk()
        self.root.title(app_title)
        self.root.geometry("1400x900")
        print(f"Tkinter 루트 윈도우 생성: {time.time() - app_start_time:.3f}초")
        
        # 라이트모드 강제 설정 (다크모드 비활성화)
        self.root.configure(bg='white')
        
        # 시스템 다크모드 비활성화
        try:
            # macOS Monterey+ 다크모드 강제 비활성화
            self.root.tk.call("tk", "::tk::unsupported::MacWindowStyle", "style", self.root._w, "document", "closeBox collapseBox resizable")
            # ttk 스타일을 라이트 테마로 강제 설정
            self.setup_light_theme()
        except Exception as e:
            print(f"다크모드 비활성화 시도 중 오류: {e}")
            self.root.configure(bg='white')
        
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
    
    def setup_light_theme(self):
        """라이트 테마 강제 설정"""
        style = ttk.Style()
        
        # 사용 가능한 테마 확인
        available_themes = style.theme_names()
        print(f"사용 가능한 테마: {available_themes}")
        
        # 라이트 테마 우선순위로 설정
        light_themes = ['aqua', 'clam', 'alt', 'default', 'classic']
        
        for theme in light_themes:
            if theme in available_themes:
                try:
                    style.theme_use(theme)
                    print(f"테마 설정 완료: {theme}")
                    break
                except Exception as e:
                    print(f"테마 {theme} 설정 실패: {e}")
                    continue
        
        # 모든 위젯에 라이트 색상 강제 적용
        try:
            # 기본 배경색과 전경색 설정
            style.configure('TFrame', background='white', foreground='black')
            style.configure('TLabel', background='white', foreground='black')
            style.configure('TButton', background='white', foreground='black')
            style.configure('TEntry', background='white', foreground='black', fieldbackground='white')
            style.configure('TCombobox', background='white', foreground='black', fieldbackground='white')
            style.configure('TText', background='white', foreground='black')
            style.configure('TNotebook', background='white', foreground='black')
            style.configure('TNotebook.Tab', background='lightgray', foreground='black')
            style.configure('Treeview', background='white', foreground='black', fieldbackground='white')
            style.configure('Treeview.Heading', background='lightgray', foreground='black')
            style.configure('TLabelFrame', background='white', foreground='black')
            
            print("라이트 테마 색상 설정 완료")
        except Exception as e:
            print(f"색상 설정 실패: {e}")
    
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

        self.new_order_tab = NewOrderTab(self.notebook, self)
        self.notebook.add(self.new_order_tab.frame, text="신규주문")

        self.shipping_pending_tab = ShippingPendingTab(self.notebook, self)
        self.notebook.add(self.shipping_pending_tab.frame, text="발송대기")

        self.shipping_in_progress_tab = ShippingInProgressTab(self.notebook, self)
        self.notebook.add(self.shipping_in_progress_tab.frame, text="배송중")

        self.shipping_completed_tab = ShippingCompletedTab(self.notebook, self)
        self.notebook.add(self.shipping_completed_tab.frame, text="배송완료")

        self.purchase_decided_tab = PurchaseDecidedTab(self.notebook, self)
        self.notebook.add(self.purchase_decided_tab.frame, text="구매확정")

        self.cancel_tab = CancelTab(self.notebook, self)
        self.notebook.add(self.cancel_tab.frame, text="취소")

        self.return_exchange_tab = ReturnExchangeTab(self.notebook, self)
        self.notebook.add(self.return_exchange_tab.frame, text="반품교환")

        self.products_tab = ProductsTab(self.notebook, self)
        self.notebook.add(self.products_tab.frame, text="상품관리")

        self.api_test_tab = APITestTab(self.notebook, self)
        self.notebook.add(self.api_test_tab.frame, text="API 테스트")
        
        self.basic_settings_tab = BasicSettingsTab(self.notebook, self)
        self.notebook.add(self.basic_settings_tab.frame, text="기본설정")
        
        self.condition_settings_tab = ConditionSettingsTab(self.notebook, self)
        self.notebook.add(self.condition_settings_tab.frame, text="조건설정")
        
        self.help_tab = HelpTab(self.notebook, self)
        self.notebook.add(self.help_tab.frame, text="도움말")
        
        # 탭 변경 이벤트 바인딩
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 상태바
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side="bottom", fill="x")
    
    def on_tab_changed(self, event):
        """탭 변경 이벤트 핸들러 - 성능 최적화"""
        try:
            import time
            start_time = time.time()

            # 즉시 화면 업데이트 강제 (탭 변경 시각적 피드백)
            self.root.update_idletasks()

            # 현재 선택된 탭 가져오기
            selected_tab = self.notebook.select()
            tab_index = self.notebook.index(selected_tab)
            tab_text = self.notebook.tab(selected_tab, "text")

            print(f"탭 변경 시작: '{tab_text}' (인덱스 {tab_index})")

            # 주문수집 탭 (인덱스 1)이 선택된 경우
            if tab_index == 1:  # 주문수집 탭
                if hasattr(self.orders_tab, 'is_first_load') and not self.orders_tab.is_first_load:
                    # 첫 로드가 아닌 경우 캐시된 데이터 표시
                    self.orders_tab.show_cached_orders()
                elif hasattr(self.orders_tab, 'is_first_load') and self.orders_tab.is_first_load:
                    # 첫 로드인 경우 자동으로 주문 조회
                    self.orders_tab.query_orders_from_api()

            # 기본설정/조건설정/도움말 탭의 점진적 로딩 트리거
            elif tab_index == 10:  # 기본설정 탭
                if hasattr(self.basic_settings_tab, 'create_detailed_ui') and not hasattr(self.basic_settings_tab, 'detailed_ui_created'):
                    # 비동기 UI 생성 시작 (블로킹 방지)
                    self.root.after(1, self.basic_settings_tab.create_detailed_ui)
            elif tab_index == 11:  # 조건설정 탭
                if hasattr(self.condition_settings_tab, 'create_detailed_ui') and not hasattr(self.condition_settings_tab, 'detailed_ui_created'):
                    # 비동기 UI 생성 시작 (블로킹 방지)
                    self.root.after(1, self.condition_settings_tab.create_detailed_ui)
            elif tab_index == 12:  # 도움말 탭
                if hasattr(self.help_tab, 'create_detailed_ui') and not hasattr(self.help_tab, 'detailed_ui_created'):
                    # 비동기 UI 생성 시작 (블로킹 방지)
                    self.root.after(1, self.help_tab.create_detailed_ui)

            # 최종적으로 전체 화면 강제 업데이트
            self.root.update()  # update_idletasks() 대신 강력한 update() 사용

            print(f"탭 변경 처리 완료: {time.time() - start_time:.3f}초")

        except Exception as e:
            print(f"탭 변경 이벤트 오류: {e}")
            import traceback
            traceback.print_exc()
    
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
            # 환경 설정에서 디스코드 웹훅 URL 가져오기
            discord_webhook_url = config.get('DISCORD_WEBHOOK_URL', '')

            # NotificationManager 초기화
            self.notification_manager = NotificationManager(discord_webhook_url)

            # 알림 설정 로드
            desktop_enabled = config.get('DESKTOP_NOTIFICATIONS', 'true').lower() == 'true'
            discord_enabled = config.get('DISCORD_ENABLED', 'false').lower() == 'true'

            # 알림 타입별 활성화/비활성화 설정
            self.notification_manager.enable_notification('desktop', desktop_enabled)
            self.notification_manager.enable_notification('discord', discord_enabled and bool(discord_webhook_url))

            print(f"알림 매니저 초기화 완료 - 데스크탑: {desktop_enabled}, 디스코드: {discord_enabled and bool(discord_webhook_url)}")

        except Exception as e:
            print(f"알림 매니저 초기화 오류: {e}")
            # 실패 시 기본 알림 매니저 생성
            self.notification_manager = NotificationManager()
    
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
