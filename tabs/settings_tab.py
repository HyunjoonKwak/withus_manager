"""
설정 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import re
import requests
import webbrowser

from ui_utils import BaseTab, enable_context_menu, run_in_thread
from env_config import config


class SettingsTab(BaseTab):
    """설정 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.setup_styles()
        self.create_settings_tab()
        self.setup_copy_paste_bindings()
        self.load_settings()
        self.refresh_current_ip()
    
    def setup_styles(self):
        """스타일 설정"""
        try:
            style = ttk.Style()
            
            # 섹션 라벨프레임 스타일
            style.configure("Section.TLabelframe", 
                          borderwidth=2, 
                          relief="solid",
                          background="#f0f0f0")
            style.configure("Section.TLabelframe.Label", 
                          font=("", 10, "bold"),
                          foreground="#2c3e50")
                          
        except Exception as e:
            print(f"스타일 설정 오류: {e}")
    
    def add_separator(self):
        """구분선 추가"""
        separator_frame = ttk.Frame(self.scrollable_frame, height=1)
        separator_frame.pack(fill="x", padx=15, pady=10)
        
        separator = ttk.Separator(separator_frame, orient="horizontal")
        separator.pack(fill="x")
    
    def setup_scrollable_frame(self):
        """스크롤 가능한 프레임 설정"""
        # 캔버스와 스크롤바 생성
        self.canvas = tk.Canvas(self.frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        
        # 스크롤 가능한 내용을 담을 프레임
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 스크롤 영역 설정
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # 캔버스에 프레임 추가
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 캔버스와 스크롤바 배치
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 마우스 휠 스크롤 지원
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind("<MouseWheel>", on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))  # Linux
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))   # Linux
        
        # 캔버스 크기 조정 시 스크롤 프레임 너비 맞추기
        def configure_scroll_region(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas.find_all()[0], width=canvas_width)
        
        self.canvas.bind("<Configure>", configure_scroll_region)
    
    def create_settings_tab(self):
        """설정 탭 UI 생성"""
        # 스크롤 가능한 프레임 설정
        self.setup_scrollable_frame()
        
        # API 설정
        api_frame = ttk.LabelFrame(self.scrollable_frame, text="🔑 API 설정", style="Section.TLabelframe")
        api_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # Client ID
        client_id_frame = ttk.Frame(api_frame)
        client_id_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(client_id_frame, text="Client ID:").pack(side="left", padx=5)
        self.client_id_var = tk.StringVar()
        self.client_id_entry = ttk.Entry(client_id_frame, textvariable=self.client_id_var, width=50)
        self.client_id_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Client Secret
        client_secret_frame = ttk.Frame(api_frame)
        client_secret_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(client_secret_frame, text="Client Secret:").pack(side="left", padx=5)
        self.client_secret_var = tk.StringVar()
        self.client_secret_entry = ttk.Entry(client_secret_frame, textvariable=self.client_secret_var, width=50, show="*")
        self.client_secret_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # API 설정 버튼
        api_buttons_frame = ttk.Frame(api_frame)
        api_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(api_buttons_frame, text="API 설정 저장", command=self.save_api_settings).pack(side="left", padx=5)
        ttk.Button(api_buttons_frame, text="API 연결 테스트", command=self.test_api_connection).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # 상품 상태 설정
        product_status_frame = ttk.LabelFrame(self.scrollable_frame, text="📦 상품 상태 설정", style="Section.TLabelframe")
        product_status_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 상품 상태 체크박스들
        self.product_status_vars = {}
        status_options = [
            ('SALE', '판매중'),
            ('WAIT', '판매대기'),
            ('OUTOFSTOCK', '품절'),
            ('SUSPENSION', '판매중지'),
            ('CLOSE', '판매종료'),
            ('PROHIBITION', '판매금지')
        ]
        
        for i, (status, label) in enumerate(status_options):
            var = tk.BooleanVar()
            self.product_status_vars[status] = var
            
            cb = ttk.Checkbutton(product_status_frame, text=label, variable=var)
            cb.pack(side="left", padx=5, pady=2)
        
        # 상품 상태 저장 버튼
        product_status_buttons_frame = ttk.Frame(product_status_frame)
        product_status_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(product_status_buttons_frame, text="상품 상태 설정 저장", command=self.save_product_status_settings).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # 알림 설정
        notification_frame = ttk.LabelFrame(self.scrollable_frame, text="🔔 알림 설정", style="Section.TLabelframe")
        notification_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 데스크탑 알림
        desktop_notification_frame = ttk.Frame(notification_frame)
        desktop_notification_frame.pack(fill="x", padx=5, pady=2)
        
        self.desktop_notifications_var = tk.BooleanVar()
        self.desktop_notifications_cb = ttk.Checkbutton(
            desktop_notification_frame, 
            text="데스크탑 알림 활성화", 
            variable=self.desktop_notifications_var
        )
        self.desktop_notifications_cb.pack(side="left", padx=5)
        
        # Discord 알림
        discord_frame = ttk.Frame(notification_frame)
        discord_frame.pack(fill="x", padx=5, pady=2)
        
        self.discord_enabled_var = tk.BooleanVar()
        self.discord_enabled_cb = ttk.Checkbutton(
            discord_frame, 
            text="Discord 알림 활성화", 
            variable=self.discord_enabled_var
        )
        self.discord_enabled_cb.pack(side="left", padx=5)
        
        # Discord Webhook URL
        webhook_frame = ttk.Frame(notification_frame)
        webhook_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(webhook_frame, text="Discord Webhook URL:").pack(side="left", padx=5)
        self.discord_webhook_var = tk.StringVar()
        self.discord_webhook_entry = ttk.Entry(webhook_frame, textvariable=self.discord_webhook_var, width=50)
        self.discord_webhook_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # 알림 설정 저장 버튼
        notification_buttons_frame = ttk.Frame(notification_frame)
        notification_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(notification_buttons_frame, text="알림 설정 저장", command=self.save_notification_settings).pack(side="left", padx=5)
        ttk.Button(notification_buttons_frame, text="알림 테스트", command=self.test_notifications).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # 주문 컬럼 설정
        order_column_frame = ttk.LabelFrame(self.scrollable_frame, text="📋 주문 컬럼 설정", style="Section.TLabelframe")
        order_column_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 컬럼 선택 체크박스들
        self.order_column_vars = {}
        column_options = [
            ('주문ID', '주문ID'),
            ('상품주문ID', '상품주문ID'),
            ('주문자', '주문자'),
            ('상품명', '상품명'),
            ('옵션정보', '옵션정보'),
            ('판매자상품코드', '판매자상품코드'),
            ('수량', '수량'),
            ('단가', '단가'),
            ('할인금액', '할인금액'),
            ('금액', '금액'),
            ('결제방법', '결제방법'),
            ('배송지주소', '배송지주소'),
            ('배송예정일', '배송예정일'),
            ('주문일시', '주문일시'),
            ('상태', '상태')
        ]
        
        # 체크박스를 한 줄로 배치
        column_checkboxes_frame = ttk.Frame(order_column_frame)
        column_checkboxes_frame.pack(fill="x", padx=5, pady=2)
        
        for i, (column, label) in enumerate(column_options):
            var = tk.BooleanVar()
            self.order_column_vars[column] = var
            
            cb = ttk.Checkbutton(column_checkboxes_frame, text=label, variable=var)
            cb.pack(side="left", padx=3, pady=2)
        
        # 주문 컬럼 설정 버튼
        order_column_buttons_frame = ttk.Frame(order_column_frame)
        order_column_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(order_column_buttons_frame, text="컬럼 설정 저장", command=self.save_order_column_settings).pack(side="left", padx=5)
        ttk.Button(order_column_buttons_frame, text="전체 선택", command=self.select_all_columns).pack(side="left", padx=5)
        ttk.Button(order_column_buttons_frame, text="전체 해제", command=self.deselect_all_columns).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # 주문 상태 설정
        order_status_frame = ttk.LabelFrame(self.scrollable_frame, text="📊 주문 상태 설정", style="Section.TLabelframe")
        order_status_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 상태 선택 체크박스들
        self.order_status_vars = {}
        status_options = [
            ('PAYMENT_WAITING', '결제대기'),
            ('PAYED', '결제완료'),
            ('DELIVERING', '배송중'),
            ('DELIVERED', '배송완료'),
            ('PURCHASE_DECIDED', '구매확정'),
            ('EXCHANGED', '교환'),
            ('CANCELED', '취소'),
            ('RETURNED', '반품'),
            ('CANCELED_BY_NOPAYMENT', '미결제취소')
        ]
        
        # 체크박스를 두 줄로 배치 (첫 번째 줄 5개, 두 번째 줄 4개)
        status_checkboxes_frame1 = ttk.Frame(order_status_frame)
        status_checkboxes_frame1.pack(fill="x", padx=5, pady=2)
        
        status_checkboxes_frame2 = ttk.Frame(order_status_frame)
        status_checkboxes_frame2.pack(fill="x", padx=5, pady=2)
        
        for i, (status_code, status_label) in enumerate(status_options):
            var = tk.BooleanVar()
            self.order_status_vars[status_code] = var
            
            # 첫 번째 줄에 5개, 두 번째 줄에 4개
            parent_frame = status_checkboxes_frame1 if i < 5 else status_checkboxes_frame2
            cb = ttk.Checkbutton(parent_frame, text=f"{status_label}({status_code})", variable=var)
            cb.pack(side="left", padx=3, pady=2)
        
        # 주문 상태 설정 버튼
        order_status_buttons_frame = ttk.Frame(order_status_frame)
        order_status_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(order_status_buttons_frame, text="상태 설정 저장", command=self.save_order_status_settings).pack(side="left", padx=5)
        ttk.Button(order_status_buttons_frame, text="전체 선택", command=self.select_all_statuses).pack(side="left", padx=5)
        ttk.Button(order_status_buttons_frame, text="전체 해제", command=self.deselect_all_statuses).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # 대시보드 기간 설정
        dashboard_frame = ttk.LabelFrame(self.scrollable_frame, text="📊 대시보드 설정", style="Section.TLabelframe")
        dashboard_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 대시보드 조회 기간 설정
        period_setting_frame = ttk.Frame(dashboard_frame)
        period_setting_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(period_setting_frame, text="기본 조회 기간:").pack(side="left", padx=5)
        
        self.dashboard_period_var = tk.StringVar()
        period_combo = ttk.Combobox(period_setting_frame, textvariable=self.dashboard_period_var, 
                                   values=['1', '3', '7'], width=5, state="readonly")
        period_combo.pack(side="left", padx=5)
        
        ttk.Label(period_setting_frame, text="일").pack(side="left", padx=5)
        
        # 대시보드 설정 버튼
        dashboard_buttons_frame = ttk.Frame(dashboard_frame)
        dashboard_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(dashboard_buttons_frame, text="대시보드 설정 저장", command=self.save_dashboard_settings).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # IP 관리 설정 (컴팩트 버전)
        ip_management_frame = ttk.LabelFrame(self.scrollable_frame, text="🌐 허가된 공인 IP 관리", style="Section.TLabelframe")
        ip_management_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 현재 IP 상태 (한 줄)
        current_ip_frame = ttk.Frame(ip_management_frame)
        current_ip_frame.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(current_ip_frame, text="현재 공인 IP:").pack(side="left", padx=5)
        self.current_ip_var = tk.StringVar()
        self.current_ip_var.set("확인 중...")
        self.current_ip_label = ttk.Label(current_ip_frame, textvariable=self.current_ip_var, foreground="blue", font=("", 9, "bold"))
        self.current_ip_label.pack(side="left", padx=5)
        
        self.ip_status_var = tk.StringVar()
        self.ip_status_var.set("")
        self.ip_status_label = ttk.Label(current_ip_frame, textvariable=self.ip_status_var, font=("", 9, "bold"))
        self.ip_status_label.pack(side="left", padx=5)
        
        ttk.Button(current_ip_frame, text="새로고침", command=self.refresh_current_ip).pack(side="right", padx=2)
        
        # IP 목록과 관리 (컴팩트하게)
        ip_manage_frame = ttk.Frame(ip_management_frame)
        ip_manage_frame.pack(fill="x", padx=5, pady=3)
        
        # 허가된 IP 목록 (높이 축소)
        ttk.Label(ip_manage_frame, text="허가된 IP 목록 (최대 5개):").pack(anchor="w")
        self.ip_listbox = tk.Listbox(ip_manage_frame, height=2, font=("Consolas", 9))
        self.ip_listbox.pack(fill="x", pady=(2, 5))
        
        # IP 관리 컨트롤을 한 줄로 배치
        ip_control_frame = ttk.Frame(ip_manage_frame)
        ip_control_frame.pack(fill="x", pady=2)
        
        # IP 입력
        self.new_ip_var = tk.StringVar()
        self.new_ip_entry = ttk.Entry(ip_control_frame, textvariable=self.new_ip_var, width=15)
        self.new_ip_entry.pack(side="left", padx=(0, 5))
        
        # 모든 버튼을 한 줄로
        ttk.Button(ip_control_frame, text="현재IP", command=self.add_current_ip).pack(side="left", padx=2)
        ttk.Button(ip_control_frame, text="추가", command=self.add_ip).pack(side="left", padx=2)
        ttk.Button(ip_control_frame, text="삭제", command=self.delete_selected_ip).pack(side="left", padx=2)
        ttk.Button(ip_control_frame, text="저장", command=self.save_ip_settings).pack(side="left", padx=2)
        
        # 도움말 버튼을 맨 아래로
        help_frame = ttk.Frame(ip_management_frame)
        help_frame.pack(fill="x", padx=5, pady=(5, 3))
        ttk.Button(help_frame, text="도움말", command=self.show_ip_help).pack(anchor="w")
        
        # 컨텍스트 메뉴 활성화
        enable_context_menu(self.client_id_entry)
        enable_context_menu(self.client_secret_entry)
        enable_context_menu(self.discord_webhook_entry)
        enable_context_menu(self.new_ip_entry)
    
    def load_settings(self):
        """설정 로드"""
        try:
            # API 설정 로드
            self.client_id_var.set(config.get('NAVER_CLIENT_ID', ''))
            self.client_secret_var.set(config.get('NAVER_CLIENT_SECRET', ''))
            
            # 상품 상태 설정 로드
            saved_statuses = config.get('PRODUCT_STATUS_TYPES', 'SALE,OUTOFSTOCK,CLOSE')
            status_list = [s.strip() for s in saved_statuses.split(',')]
            
            print(f"설정 로드 - 저장된 상품상태 문자열: {saved_statuses}")
            print(f"설정 로드 - 저장된 상품상태 리스트: {status_list}")
            
            for status, var in self.product_status_vars.items():
                is_checked = status in status_list
                var.set(is_checked)
                print(f"설정 로드 - {status}: {is_checked}")
            
            # 알림 설정 로드
            self.desktop_notifications_var.set(config.get('DESKTOP_NOTIFICATIONS', 'false').lower() == 'true')
            self.discord_enabled_var.set(config.get('DISCORD_ENABLED', 'false').lower() == 'true')
            self.discord_webhook_var.set(config.get('DISCORD_WEBHOOK_URL', ''))
            
            # 주문 컬럼 설정 로드
            self.load_order_column_settings()
            
            # 주문 상태 설정 로드
            self.load_order_status_settings()
            
            # 대시보드 기간 설정 로드
            self.load_dashboard_settings()
            
            # IP 설정 로드
            self.load_ip_settings()
            
        except Exception as e:
            print(f"설정 로드 오류: {e}")
    
    def save_api_settings(self):
        """API 설정 저장"""
        try:
            client_id = self.client_id_var.get().strip()
            client_secret = self.client_secret_var.get().strip()
            
            if not client_id or not client_secret:
                messagebox.showwarning("경고", "Client ID와 Client Secret을 모두 입력해주세요.")
                return
            
            # .env 파일에 저장
            config.set('NAVER_CLIENT_ID', client_id)
            config.set('NAVER_CLIENT_SECRET', client_secret)
            config.save()
            
            # API 재초기화
            self.app.initialize_api()
            
            messagebox.showinfo("성공", "API 설정이 저장되었습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"API 설정 저장 실패: {str(e)}")
    
    def test_api_connection(self):
        """API 연결 테스트"""
        try:
            if not self.app.naver_api:
                messagebox.showwarning("API 설정 필요", "네이버 커머스 API가 설정되지 않았습니다.\nAPI 정보를 입력해주세요.")
                return
            
            # API 연결 테스트
            response = self.app.naver_api.get_seller_account()
            
            if response and response.get('success'):
                messagebox.showinfo("성공", "API 연결이 성공했습니다.")
            else:
                messagebox.showerror("실패", "API 연결에 실패했습니다.")
                
        except Exception as e:
            messagebox.showerror("오류", f"API 연결 테스트 실패: {str(e)}")
    
    def save_product_status_settings(self):
        """상품 상태 설정 저장"""
        try:
            selected_statuses = [status for status, var in self.product_status_vars.items() if var.get()]
            status_string = ','.join(selected_statuses)
            
            print(f"설정 저장 - product_status_vars: {self.product_status_vars}")
            print("설정 저장 - 각 상태별 값:")
            for status, var in self.product_status_vars.items():
                print(f"  {status}: {var.get()}")
            
            print(f"설정 저장 - 선택된 상품상태: {selected_statuses}")
            
            # .env 파일에 저장
            config.set('PRODUCT_STATUS_TYPES', status_string)
            config.save()
            
            # 홈 탭의 상품 상태 표시 업데이트
            try:
                if hasattr(self.app, 'home_tab') and self.app.home_tab:
                    self.app.home_tab.refresh_product_status_display()
                    print("홈 탭 상품 상태 표시 업데이트 완료")
            except Exception as update_error:
                print(f"홈 탭 업데이트 오류: {update_error}")
            
            messagebox.showinfo("성공", f"상품 상태 설정이 저장되었습니다.\n선택된 상태: {status_string}")
            
        except Exception as e:
            messagebox.showerror("오류", f"상품 상태 설정 저장 실패: {str(e)}")
    
    def save_notification_settings(self):
        """알림 설정 저장"""
        try:
            desktop_enabled = self.desktop_notifications_var.get()
            discord_enabled = self.discord_enabled_var.get()
            webhook_url = self.discord_webhook_var.get().strip()
            
            # .env 파일에 저장
            config.set('DESKTOP_NOTIFICATIONS', str(desktop_enabled).lower())
            config.set('DISCORD_ENABLED', str(discord_enabled).lower())
            config.set('DISCORD_WEBHOOK_URL', webhook_url)
            config.save()
            
            messagebox.showinfo("성공", "알림 설정이 저장되었습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"알림 설정 저장 실패: {str(e)}")
    
    def test_notifications(self):
        """알림 테스트"""
        try:
            if not self.app.notification_manager:
                messagebox.showwarning("경고", "알림 매니저가 초기화되지 않았습니다.")
                return
            
            # 테스트 주문 데이터 생성
            test_order = {
                'orderId': 'TEST_ORDER_001',
                'ordererName': '테스트 주문자',
                'productName': '테스트 상품',
                'orderDate': '2025-01-10T10:00:00Z',
                'totalAmount': 50000,
                'price': 50000
            }
            
            # 데스크탑 알림 테스트
            if self.desktop_notifications_var.get():
                self.app.notification_manager.send_new_order_notification(test_order)
            
            # Discord 알림 테스트
            if self.discord_enabled_var.get():
                self.app.notification_manager.send_new_order_notification(test_order)
            
            messagebox.showinfo("성공", "알림 테스트가 완료되었습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"알림 테스트 실패: {str(e)}")
    
    def load_order_column_settings(self):
        """주문 컬럼 설정 로드"""
        try:
            # 기본값: 모든 컬럼 선택
            default_columns = "주문ID,상품주문ID,주문자,상품명,옵션정보,판매자상품코드,수량,단가,할인금액,금액,결제방법,배송지주소,배송예정일,주문일시,상태"
            saved_columns = config.get('ORDER_COLUMNS', default_columns)
            column_list = [col.strip() for col in saved_columns.split(',')]
            
            print(f"주문 컬럼 설정 로드: {column_list}")
            
            for column, var in self.order_column_vars.items():
                is_checked = column in column_list
                var.set(is_checked)
                
        except Exception as e:
            print(f"주문 컬럼 설정 로드 오류: {e}")
            # 오류 시 모든 컬럼 선택
            for var in self.order_column_vars.values():
                var.set(True)
    
    def save_order_column_settings(self):
        """주문 컬럼 설정 저장"""
        try:
            selected_columns = [column for column, var in self.order_column_vars.items() if var.get()]
            
            if not selected_columns:
                messagebox.showwarning("경고", "최소 하나의 컬럼을 선택해야 합니다.")
                return
            
            column_string = ','.join(selected_columns)
            
            print(f"주문 컬럼 설정 저장: {selected_columns}")
            
            # .env 파일에 저장
            config.set('ORDER_COLUMNS', column_string)
            config.save()
            
            # 주문 탭의 컬럼 업데이트
            try:
                if hasattr(self.app, 'orders_tab') and self.app.orders_tab:
                    self.app.orders_tab.update_column_display()
                    
                    # 기존 주문 데이터가 있다면 다시 로드
                    if hasattr(self.app.orders_tab, 'last_orders_data') and self.app.orders_tab.last_orders_data:
                        self.app.orders_tab._update_orders_tree(self.app.orders_tab.last_orders_data)
                        print("기존 주문 데이터 다시 로드 완료")
                    
                    print("주문 탭 컬럼 표시 업데이트 완료")
            except Exception as update_error:
                print(f"주문 탭 업데이트 오류: {update_error}")
            
            messagebox.showinfo("성공", f"주문 컬럼 설정이 저장되었습니다.\n선택된 컬럼: {len(selected_columns)}개")
            
        except Exception as e:
            messagebox.showerror("오류", f"주문 컬럼 설정 저장 실패: {str(e)}")
    
    def select_all_columns(self):
        """모든 컬럼 선택"""
        for var in self.order_column_vars.values():
            var.set(True)
    
    def deselect_all_columns(self):
        """모든 컬럼 선택 해제"""
        for var in self.order_column_vars.values():
            var.set(False)
    
    def load_order_status_settings(self):
        """주문 상태 설정 로드"""
        try:
            # 기본값: 결제완료, 배송중, 배송완료 선택
            default_statuses = "PAYED,DELIVERING,DELIVERED"
            saved_statuses = config.get('ORDER_STATUS_TYPES', default_statuses)
            status_list = [status.strip() for status in saved_statuses.split(',')]
            
            print(f"주문 상태 설정 로드: {status_list}")
            
            for status, var in self.order_status_vars.items():
                is_checked = status in status_list
                var.set(is_checked)
                
        except Exception as e:
            print(f"주문 상태 설정 로드 오류: {e}")
            # 오류 시 기본값 설정
            default_statuses = ["PAYED", "DELIVERING", "DELIVERED"]
            for status, var in self.order_status_vars.items():
                var.set(status in default_statuses)
    
    def save_order_status_settings(self):
        """주문 상태 설정 저장"""
        try:
            selected_statuses = [status for status, var in self.order_status_vars.items() if var.get()]
            
            if not selected_statuses:
                messagebox.showwarning("경고", "최소 하나의 상태를 선택해야 합니다.")
                return
            
            status_string = ','.join(selected_statuses)
            
            print(f"주문 상태 설정 저장: {selected_statuses}")
            
            # .env 파일에 저장
            config.set('ORDER_STATUS_TYPES', status_string)
            config.save()
            
            # 주문 탭 상태 표시 업데이트 (있는 경우)
            try:
                if hasattr(self.app, 'orders_tab') and self.app.orders_tab:
                    # 주문 상태 표시 업데이트
                    if hasattr(self.app.orders_tab, 'update_order_status_display'):
                        self.app.orders_tab.update_order_status_display()
                        print("주문 탭 상태 표시 업데이트 완료")
            except Exception as update_error:
                print(f"주문 탭 업데이트 오류: {update_error}")
            
            messagebox.showinfo("성공", f"주문 상태 설정이 저장되었습니다.\n선택된 상태: {len(selected_statuses)}개")
            
        except Exception as e:
            messagebox.showerror("오류", f"주문 상태 설정 저장 실패: {str(e)}")
    
    def select_all_statuses(self):
        """모든 주문 상태 선택"""
        for var in self.order_status_vars.values():
            var.set(True)
    
    def deselect_all_statuses(self):
        """모든 주문 상태 선택 해제"""
        for var in self.order_status_vars.values():
            var.set(False)
    
    # 대시보드 설정 메서드들
    def load_dashboard_settings(self):
        """대시보드 설정 로드"""
        try:
            current_period = config.get_int('DASHBOARD_PERIOD_DAYS', 1)
            self.dashboard_period_var.set(str(current_period))
            print(f"대시보드 기간 설정 로드: {current_period}일")
        except Exception as e:
            print(f"대시보드 설정 로드 오류: {e}")
            self.dashboard_period_var.set('1')
    
    def save_dashboard_settings(self):
        """대시보드 설정 저장"""
        try:
            new_period = int(self.dashboard_period_var.get())
            config.set('DASHBOARD_PERIOD_DAYS', str(new_period))
            config.save()
            
            messagebox.showinfo("성공", f"대시보드 조회 기간이 {new_period}일로 설정되었습니다.")
            print(f"대시보드 기간 설정 저장: {new_period}일")
            
        except Exception as e:
            messagebox.showerror("오류", f"대시보드 설정 저장 실패: {str(e)}")
    
    # IP 관리 메서드들
    def load_ip_settings(self):
        """IP 설정 로드"""
        try:
            # 기본 허가된 IP들
            default_ips = "121.190.40.153,175.125.204.97"
            saved_ips = config.get('ALLOWED_IPS', default_ips)
            
            # IP 목록 파싱
            ip_list = [ip.strip() for ip in saved_ips.split(',') if ip.strip()]
            
            # 리스트박스 업데이트
            self.ip_listbox.delete(0, tk.END)
            for ip in ip_list:
                self.ip_listbox.insert(tk.END, ip)
                
            print(f"IP 설정 로드: {ip_list}")
            
        except Exception as e:
            print(f"IP 설정 로드 오류: {e}")
            # 기본값으로 설정
            self.ip_listbox.delete(0, tk.END)
            self.ip_listbox.insert(tk.END, "121.190.40.153")
            self.ip_listbox.insert(tk.END, "175.125.204.97")
    
    def get_current_public_ip(self):
        """현재 공인 IP 주소 가져오기"""
        try:
            services = [
                "https://api.ipify.org",
                "https://ipinfo.io/ip", 
                "https://ident.me",
                "https://checkip.amazonaws.com"
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        public_ip = response.text.strip()
                        if public_ip and '.' in public_ip and re.match(r'^[\d.]+$', public_ip):
                            return public_ip
                except Exception as e:
                    print(f"{service} 서비스 오류: {e}")
                    continue
            
            return None
        except Exception as e:
            print(f"공인 IP 확인 오류: {e}")
            return None
    
    def is_ip_allowed(self, ip):
        """IP가 허가된 목록에 있는지 확인"""
        try:
            allowed_ips = []
            for i in range(self.ip_listbox.size()):
                allowed_ips.append(self.ip_listbox.get(i))
            return ip in allowed_ips
        except Exception as e:
            print(f"IP 허가 확인 오류: {e}")
            return False
    
    def refresh_current_ip(self):
        """현재 IP 새로고침"""
        run_in_thread(self._refresh_current_ip_thread)
    
    def _refresh_current_ip_thread(self):
        """현재 IP 새로고침 스레드"""
        try:
            self.app.root.after(0, lambda: self.current_ip_var.set("확인 중..."))
            self.app.root.after(0, lambda: self.ip_status_var.set(""))
            
            current_ip = self.get_current_public_ip()
            
            if current_ip:
                self.app.root.after(0, lambda: self.current_ip_var.set(current_ip))
                
                # IP 허가 상태 확인
                if self.is_ip_allowed(current_ip):
                    self.app.root.after(0, lambda: self.ip_status_var.set("✓ 허가됨"))
                    self.app.root.after(0, lambda: self.ip_status_label.config(foreground="green"))
                else:
                    self.app.root.after(0, lambda: self.ip_status_var.set("✗ 허가되지 않음"))
                    self.app.root.after(0, lambda: self.ip_status_label.config(foreground="red"))
                    # 허가되지 않은 IP일 때 도움말 자동 표시
                    self.app.root.after(1000, self.show_ip_authorization_warning)
            else:
                self.app.root.after(0, lambda: self.current_ip_var.set("확인 실패"))
                self.app.root.after(0, lambda: self.ip_status_var.set(""))
                
        except Exception as e:
            print(f"IP 새로고침 오류: {e}")
            self.app.root.after(0, lambda: self.current_ip_var.set("오류"))
            self.app.root.after(0, lambda: self.ip_status_var.set(""))
    
    def validate_ip_format(self, ip):
        """IP 주소 형식 검증"""
        try:
            pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            return bool(re.match(pattern, ip))
        except:
            return False
    
    def add_ip(self):
        """새 IP 추가 (최대 5개 제한)"""
        try:
            # 5개 제한 확인
            if self.ip_listbox.size() >= 5:
                messagebox.showwarning("제한", "최대 5개의 IP만 관리할 수 있습니다.")
                return
            
            new_ip = self.new_ip_var.get().strip()
            
            if not new_ip:
                messagebox.showwarning("경고", "IP 주소를 입력해주세요.")
                return
            
            if not self.validate_ip_format(new_ip):
                messagebox.showerror("오류", "올바른 IP 주소 형식이 아닙니다.")
                return
            
            # 중복 확인
            for i in range(self.ip_listbox.size()):
                if self.ip_listbox.get(i) == new_ip:
                    messagebox.showwarning("경고", "이미 추가된 IP 주소입니다.")
                    return
            
            # IP 추가
            self.ip_listbox.insert(tk.END, new_ip)
            self.new_ip_var.set("")
            
            print(f"IP 추가: {new_ip} (총 {self.ip_listbox.size()}개)")
            
        except Exception as e:
            messagebox.showerror("오류", f"IP 추가 실패: {str(e)}")
    
    def delete_selected_ip(self):
        """선택된 IP 삭제"""
        try:
            selection = self.ip_listbox.curselection()
            if not selection:
                messagebox.showwarning("경고", "삭제할 IP를 선택해주세요.")
                return
            
            selected_ip = self.ip_listbox.get(selection[0])
            
            # 확인 대화상자
            result = messagebox.askyesno("확인", f"IP '{selected_ip}'를 삭제하시겠습니까?")
            if result:
                self.ip_listbox.delete(selection[0])
                print(f"IP 삭제: {selected_ip}")
                
        except Exception as e:
            messagebox.showerror("오류", f"IP 삭제 실패: {str(e)}")
    
    def add_current_ip(self):
        """현재 IP를 허가 목록에 추가 (최대 5개 제한)"""
        try:
            # 5개 제한 확인
            if self.ip_listbox.size() >= 5:
                messagebox.showwarning("제한", "최대 5개의 IP만 관리할 수 있습니다.")
                return
            
            current_ip = self.current_ip_var.get()
            
            if current_ip in ["확인 중...", "확인 실패", "오류"]:
                messagebox.showwarning("경고", "현재 IP를 먼저 확인해주세요.")
                return
            
            if not self.validate_ip_format(current_ip):
                messagebox.showerror("오류", "현재 IP 주소가 올바르지 않습니다.")
                return
            
            # 중복 확인
            for i in range(self.ip_listbox.size()):
                if self.ip_listbox.get(i) == current_ip:
                    messagebox.showinfo("정보", "현재 IP는 이미 허가 목록에 있습니다.")
                    return
            
            # IP 추가
            self.ip_listbox.insert(tk.END, current_ip)
            
            # 상태 업데이트
            self.ip_status_var.set("✓ 허가됨")
            self.ip_status_label.config(foreground="green")
            
            print(f"현재 IP 추가: {current_ip} (총 {self.ip_listbox.size()}개)")
            
        except Exception as e:
            messagebox.showerror("오류", f"현재 IP 추가 실패: {str(e)}")
    
    def save_ip_settings(self):
        """IP 설정 저장"""
        try:
            # 리스트박스에서 IP 목록 가져오기
            ip_list = []
            for i in range(self.ip_listbox.size()):
                ip_list.append(self.ip_listbox.get(i))
            
            if not ip_list:
                messagebox.showwarning("경고", "최소 하나의 IP 주소가 필요합니다.")
                return
            
            # 설정 저장
            ip_string = ','.join(ip_list)
            config.set('ALLOWED_IPS', ip_string)
            config.save()
            
            messagebox.showinfo("성공", f"IP 설정이 저장되었습니다.\n허가된 IP: {len(ip_list)}개")
            
            # 현재 IP 상태 다시 확인
            self.refresh_current_ip()
            
            print(f"IP 설정 저장: {ip_list}")
            
        except Exception as e:
            messagebox.showerror("오류", f"IP 설정 저장 실패: {str(e)}")
    
    def show_ip_help(self):
        """IP 관리 도움말 표시"""
        help_text = """
💡 허가된 공인 IP 관리 도움말

🔹 현재 공인 IP
   - 앱이 실행되는 환경의 공인 IP 주소입니다
   - "새로고침" 버튼으로 최신 정보를 확인할 수 있습니다

🔹 허가된 IP 목록 (최대 5개)
   - 네이버 커머스 API 사용이 허가된 IP 주소 목록입니다
   - 기본값: 121.190.40.153, 175.125.204.97

🔹 IP 추가/삭제
   - "추가": 입력창에 IP 주소를 입력하여 추가
   - "현재IP": 현재 공인 IP를 허가 목록에 추가
   - "삭제": 목록에서 선택한 IP 삭제

🔹 허가되지 않은 IP로 실행 시
   - 빨간색 "✗ 허가되지 않음" 표시
   - 네이버 커머스 API 관리 페이지에서 IP 추가 필요

📋 네이버 커머스 API 관리 페이지
   - URL: https://apicenter.commerce.naver.com/ko/member/application/manage/list
   - 이 페이지에서 동일한 IP를 허가해야 API 사용 가능

⚠️ 주의사항
   - IP 변경 후 "저장" 버튼을 눌러 저장하세요
   - 네이버 커머스 API에서도 동일한 IP를 허가해야 합니다
   - 최대 5개의 IP만 관리할 수 있습니다
        """
        
        messagebox.showinfo("IP 관리 도움말", help_text)
    
    def show_ip_authorization_warning(self):
        """허가되지 않은 IP 경고 및 도움말"""
        try:
            current_ip = self.current_ip_var.get()
            
            if current_ip in ["확인 중...", "확인 실패", "오류"]:
                return
                
            if not self.is_ip_allowed(current_ip):
                result = messagebox.askyesno(
                    "IP 허가 필요", 
                    f"현재 공인 IP ({current_ip})가 허가되지 않았습니다.\n\n"
                    "네이버 커머스 API를 사용하려면 IP 허가가 필요합니다.\n\n"
                    "1. 현재 IP를 허가 목록에 추가하거나\n"
                    "2. 네이버 커머스 API 관리 페이지에서 IP를 추가하세요.\n\n"
                    "네이버 커머스 API 관리 페이지를 열시겠습니까?"
                )
                
                if result:
                    webbrowser.open("https://apicenter.commerce.naver.com/ko/member/application/manage/list")
                    
        except Exception as e:
            print(f"IP 허가 경고 표시 오류: {e}")
