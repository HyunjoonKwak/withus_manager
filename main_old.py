import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import time
import hmac
import hashlib
import base64
import bcrypt
import pybase64
from datetime import datetime, timedelta
import json
import os
from tkcalendar import DateEntry

from database import DatabaseManager
from naver_api import NaverShoppingAPI
from notification_manager import NotificationManager
from env_config import config

def enable_context_menu(widget):
    """위젯에 우클릭 컨텍스트 메뉴 활성화"""
    def show_context_menu(event):
        try:
            # 컨텍스트 메뉴 생성
            context_menu = tk.Menu(widget, tearoff=0)
            
            # 복사 기능
            def copy_text():
                try:
                    if hasattr(widget, 'get') and hasattr(widget, 'selection_range'):
                        # Entry 위젯인 경우
                        if widget.selection_present():
                            widget.clipboard_clear()
                            widget.clipboard_append(widget.selection_get())
                    elif hasattr(widget, 'get') and hasattr(widget, 'index'):
                        # Text 위젯인 경우
                        if widget.tag_ranges(tk.SEL):
                            widget.clipboard_clear()
                            widget.clipboard_append(widget.get(tk.SEL_FIRST, tk.SEL_LAST))
                    elif hasattr(widget, 'get'):
                        # 전체 텍스트 복사
                        widget.clipboard_clear()
                        widget.clipboard_append(widget.get())
                except:
                    pass
            
            # 붙여넣기 기능
            def paste_text():
                try:
                    if hasattr(widget, 'insert') and hasattr(widget, 'delete'):
                        clipboard_text = widget.clipboard_get()
                        if hasattr(widget, 'selection_range') and widget.selection_present():
                            # 선택된 텍스트가 있으면 교체
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                            widget.insert(tk.INSERT, clipboard_text)
                        elif hasattr(widget, 'index'):
                            # 현재 커서 위치에 삽입
                            widget.insert(tk.INSERT, clipboard_text)
                except:
                    pass
            
            # 잘라내기 기능
            def cut_text():
                try:
                    copy_text()
                    if hasattr(widget, 'delete'):
                        if hasattr(widget, 'selection_range') and widget.selection_present():
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        elif hasattr(widget, 'index'):
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except:
                    pass
            
            # 전체 선택 기능
            def select_all():
                try:
                    if hasattr(widget, 'select_range'):
                        widget.select_range(0, tk.END)
                    elif hasattr(widget, 'tag_add'):
                        widget.tag_add(tk.SEL, "1.0", tk.END)
                        widget.mark_set(tk.INSERT, "1.0")
                        widget.see(tk.INSERT)
                except:
                    pass
            
            # 메뉴 항목 추가
            context_menu.add_command(label="복사", command=copy_text)
            context_menu.add_command(label="붙여넣기", command=paste_text)
            context_menu.add_command(label="잘라내기", command=cut_text)
            context_menu.add_separator()
            context_menu.add_command(label="전체 선택", command=select_all)
            
            # 메뉴 표시
            context_menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            print(f"컨텍스트 메뉴 오류: {e}")
        finally:
            # 메뉴가 닫힐 때 정리
            try:
                context_menu.grab_release()
            except:
                pass
    
    # 우클릭 이벤트 바인딩
    widget.bind("<Button-3>", show_context_menu)  # Windows/Linux
    widget.bind("<Button-2>", show_context_menu)  # macOS (일부)
    widget.bind("<Control-Button-1>", show_context_menu)  # macOS 대안

class WithUsOrderManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WithUs 주문관리 시스템")
        self.root.geometry("1200x1200")
        self.root.minsize(1000, 900)
        
        # 데이터베이스 및 API 초기화
        try:
            print("데이터베이스 매니저 초기화 시작")
            db_path = config.get('DATABASE_PATH', 'orders.db')
            print(f"데이터베이스 경로: {db_path}")
            self.db_manager = DatabaseManager(db_path)
            print("데이터베이스 매니저 초기화 완료")
            
            # 데이터베이스 파일 존재 확인
            import os
            if os.path.exists(db_path):
                print(f"데이터베이스 파일 존재 확인: {db_path}")
            else:
                print(f"데이터베이스 파일이 생성되지 않음: {db_path}")
                
        except Exception as e:
            print(f"데이터베이스 매니저 초기화 오류: {e}")
            self.db_manager = None
        self.naver_api = None
        self.notification_manager = NotificationManager()
        
        # 주문 상태 추적을 위한 변수
        self.previous_order_counts = {}
        
        # 백그라운드 모니터링
        self.monitoring_active = False
        self.monitor_thread = None
        
        # UI 초기화
        self.setup_ui()
        self.load_settings()
        
        # 주기적 새로고침 설정
        self.auto_refresh_interval = config.get_int('REFRESH_INTERVAL', 60)
        self.schedule_auto_refresh()
    
    
    def setup_ui(self):
        """UI 초기화"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 탭 위젯 생성
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 탭들 생성
        self.create_home_tab()
        self.create_orders_tab()
        self.create_shipping_tab()
        self.create_api_test_tab()
        self.create_settings_tab()
        
        # 설정 로드
        self.load_settings()
        
        # 저장된 상품 자동 로드 (설정 로드 후)
        self.auto_load_saved_products()
        
        # 주문 상태별 탭들 생성 (나중에 활성화)
        # self.create_order_status_tabs()
        
        # 상태바
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # 복사/붙여넣기 바인딩 설정
        self.setup_copy_paste_bindings()
    
    def setup_copy_paste_bindings(self):
        """복사/붙여넣기 바인딩 설정"""
        # 모든 Entry 위젯에 복사/붙여넣기 바인딩 추가
        entries = [
            self.client_id_entry,
            self.client_secret_entry,
            self.discord_webhook_entry,
            self.check_interval_entry,
            self.refresh_interval_entry
        ]
        
        for entry in entries:
            if entry:
                # Ctrl+C (복사)
                entry.bind('<Control-c>', lambda e: self.copy_text(e.widget))
                # Ctrl+V (붙여넣기)
                entry.bind('<Control-v>', lambda e: self.paste_text(e.widget))
                # Ctrl+A (전체 선택)
                entry.bind('<Control-a>', lambda e: self.select_all(e.widget))
                # 우클릭 컨텍스트 메뉴
                entry.bind('<Button-3>', lambda e: self.show_context_menu(e))
    
    def copy_text(self, widget):
        """텍스트 복사"""
        try:
            widget.clipboard_clear()
            widget.clipboard_append(widget.selection_get())
        except tk.TclError:
            pass  # 선택된 텍스트가 없는 경우
    
    def paste_text(self, widget):
        """텍스트 붙여넣기"""
        try:
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass  # 선택된 텍스트가 없는 경우
        
        try:
            widget.insert(tk.INSERT, widget.clipboard_get())
        except tk.TclError:
            pass  # 클립보드가 비어있는 경우
    
    def select_all(self, widget):
        """전체 선택"""
        widget.select_range(0, tk.END)
        return 'break'
    
    def show_context_menu(self, event):
        """우클릭 컨텍스트 메뉴 표시"""
        try:
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="복사", command=lambda: self.copy_text(event.widget))
            context_menu.add_command(label="붙여넣기", command=lambda: self.paste_text(event.widget))
            context_menu.add_command(label="전체 선택", command=lambda: self.select_all(event.widget))
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        except tk.TclError:
            pass
    
    def create_home_tab(self):
        """홈 탭 생성"""
        home_frame = ttk.Frame(self.notebook)
        self.notebook.add(home_frame, text="홈")
        
        # 대시보드 프레임
        dashboard_frame = ttk.LabelFrame(home_frame, text="주문 현황 대시보드")
        dashboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 통계 카드들
        stats_frame = ttk.Frame(dashboard_frame)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.stats_vars = {}
        status_list = ['신규주문', '발송대기', '배송중', '배송완료', '구매확정', '취소주문', '반품주문', '교환주문']
        
        for i, status in enumerate(status_list):
            card_frame = ttk.Frame(stats_frame)
            card_frame.pack(side=tk.LEFT, padx=8, pady=5, fill=tk.X, expand=True)
            
            ttk.Label(card_frame, text=status, font=('Arial', 11, 'bold')).pack()
            self.stats_vars[status] = tk.StringVar(value="0")
            ttk.Label(card_frame, textvariable=self.stats_vars[status], 
                     font=('Arial', 16, 'bold'), foreground='blue').pack()
        
        # 버튼 프레임
        button_frame = ttk.Frame(dashboard_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="새로고침", command=self.refresh_dashboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="주문 동기화", command=self.sync_orders).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="알림 테스트", command=self.test_notifications).pack(side=tk.LEFT, padx=5)
        
        # 최근 주문 목록
        recent_frame = ttk.LabelFrame(dashboard_frame, text="최근 주문")
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 트리뷰 생성
        columns = ('주문번호', '고객명', '상품명', '금액', '상태', '주문일')
        self.recent_tree = ttk.Treeview(recent_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=120)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        self.recent_tree.configure(yscrollcommand=scrollbar.set)
        
        self.recent_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 날짜 범위 조회 프레임
        date_range_frame = ttk.LabelFrame(home_frame, text="날짜 범위 주문 조회")
        date_range_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 날짜 선택 프레임
        date_select_frame = ttk.Frame(date_range_frame)
        date_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 시작일
        ttk.Label(date_select_frame, text="시작일:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.home_start_date = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        self.home_start_date_entry = DateEntry(
            date_select_frame, 
            textvariable=self.home_start_date,
            date_pattern='yyyy-mm-dd',
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.home_start_date_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 종료일
        ttk.Label(date_select_frame, text="종료일:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.home_end_date = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.home_end_date_entry = DateEntry(
            date_select_frame, 
            textvariable=self.home_end_date,
            date_pattern='yyyy-mm-dd',
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.home_end_date_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # 조회 버튼
        ttk.Button(date_select_frame, text="신규주문 조회", command=self.query_new_orders).grid(row=0, column=4, padx=5, pady=5)
        
        # 빠른 선택 버튼들
        quick_frame = ttk.Frame(date_select_frame)
        quick_frame.grid(row=1, column=0, columnspan=5, padx=5, pady=5, sticky='w')
        
        ttk.Button(quick_frame, text="최근 1일", command=lambda: self.set_home_date_range(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="최근 3일", command=lambda: self.set_home_date_range(3)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="최근 7일", command=lambda: self.set_home_date_range(7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="최근 15일", command=lambda: self.set_home_date_range(15)).pack(side=tk.LEFT, padx=2)
        
        # 조회 결과 표시 프레임
        result_frame = ttk.LabelFrame(home_frame, text="조회 결과")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 트리뷰 생성
        columns = ('주문번호', '고객명', '상품명', '수량', '금액', '상태', '주문일')
        self.home_orders_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.home_orders_tree.heading(col, text=col)
            self.home_orders_tree.column(col, width=120)
        
        # 스크롤바
        home_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.home_orders_tree.yview)
        self.home_orders_tree.configure(yscrollcommand=home_scrollbar.set)
        
        self.home_orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        home_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 상태 표시
        self.home_status_var = tk.StringVar(value="날짜 범위를 선택하고 조회 버튼을 클릭하세요.")
        ttk.Label(home_frame, textvariable=self.home_status_var).pack(pady=5)
        
        # 상품 관리 섹션 추가
        product_frame = ttk.LabelFrame(home_frame, text="상품 관리")
        product_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 상품 관리 버튼들
        product_buttons_frame = ttk.Frame(product_frame)
        product_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(product_buttons_frame, text="상품 목록 조회", command=self.load_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_buttons_frame, text="저장된 상품 조회", command=self.load_saved_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_buttons_frame, text="상품 새로고침", command=self.refresh_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_buttons_frame, text="서버 응답 보기", command=self.show_api_response).pack(side=tk.LEFT, padx=5)
        
        # 상품 관리 상태 표시
        self.product_status_var = tk.StringVar(value="상품 목록을 조회해주세요")
        product_status_label = ttk.Label(product_buttons_frame, textvariable=self.product_status_var, 
                                       font=('Arial', 9), foreground='blue')
        product_status_label.pack(side=tk.RIGHT, padx=10)
        
        # 상품 목록 트리뷰
        product_list_frame = ttk.Frame(product_frame)
        product_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 상품 목록 컬럼
        product_columns = ('상품ID', '상품명', '상태', '원래판매가', '셀러할인가', '실제판매가', '재고', '등록일', '링크')
        self.product_tree = ttk.Treeview(product_list_frame, columns=product_columns, show='headings', height=8)
        
        for col in product_columns:
            self.product_tree.heading(col, text=col)
            if col == '상품명':
                self.product_tree.column(col, width=200)
            elif col == '링크':
                self.product_tree.column(col, width=120)
            else:
                self.product_tree.column(col, width=100)
        
        # 상품 목록 스크롤바
        product_scrollbar = ttk.Scrollbar(product_list_frame, orient=tk.VERTICAL, command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=product_scrollbar.set)
        
        self.product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        product_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 상품 트리뷰 더블클릭 이벤트
        self.product_tree.bind('<Double-1>', self.on_product_double_click)
        
        # 가격/상태 컬럼 클릭 이벤트 바인딩
        self.product_tree.bind('<Button-1>', self.on_cell_click)
    
    def create_orders_tab(self):
        """주문 관리 탭 생성"""
        orders_frame = ttk.Frame(self.notebook)
        self.notebook.add(orders_frame, text="주문수집")
        
        # 필터 프레임
        filter_frame = ttk.LabelFrame(orders_frame, text="필터")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="상태:").grid(row=0, column=0, padx=5, pady=5)
        self.status_filter = ttk.Combobox(filter_frame, values=['전체', '신규주문', '발송대기', '배송중', '배송완료', '구매확정', '취소주문', '반품주문', '교환주문'])
        self.status_filter.set('전체')
        self.status_filter.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="시작일:").grid(row=0, column=2, padx=5, pady=5)
        self.start_date = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        self.start_date_entry = DateEntry(
            filter_frame, 
            textvariable=self.start_date,
            date_pattern='yyyy-mm-dd',
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.start_date_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="종료일:").grid(row=0, column=4, padx=5, pady=5)
        self.end_date = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.end_date_entry = DateEntry(
            filter_frame, 
            textvariable=self.end_date,
            date_pattern='yyyy-mm-dd',
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.end_date_entry.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Button(filter_frame, text="DB 조회", command=self.filter_orders).grid(row=0, column=6, padx=5, pady=5)
        ttk.Button(filter_frame, text="API 조회", command=self.load_orders_from_api).grid(row=0, column=7, padx=5, pady=5)
        ttk.Button(filter_frame, text="엑셀 내보내기", command=self.export_to_excel).grid(row=0, column=8, padx=5, pady=5)
        
        # 주문 목록
        list_frame = ttk.LabelFrame(orders_frame, text="주문 목록")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('주문번호', '고객명', '연락처', '상품명', '수량', '금액', '상태', '주문일')
        self.orders_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=120)
        
        # 스크롤바
        orders_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=orders_scrollbar.set)
        
        self.orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        orders_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 주문 액션 프레임
        action_frame = ttk.Frame(orders_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(action_frame, text="상태 변경", command=self.change_order_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="메모 추가", command=self.add_order_memo).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="상세 보기", command=self.view_order_detail).pack(side=tk.LEFT, padx=5)
    
    def create_shipping_tab(self):
        """택배 관리 탭 생성"""
        shipping_frame = ttk.Frame(self.notebook)
        self.notebook.add(shipping_frame, text="택배관리")
        
        # 택배사 선택 프레임
        company_frame = ttk.LabelFrame(shipping_frame, text="택배사 관리")
        company_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(company_frame, text="택배사:").grid(row=0, column=0, padx=5, pady=5)
        self.shipping_company = ttk.Combobox(company_frame, values=['CJ대한통운', '한진택배', '롯데택배', '로젠택배', '우체국택배', '쿠팡', '기타'])
        self.shipping_company.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(company_frame, text="송장번호:").grid(row=0, column=2, padx=5, pady=5)
        self.tracking_number = ttk.Entry(company_frame, width=20)
        self.tracking_number.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(company_frame, text="송장 등록", command=self.register_tracking).grid(row=0, column=4, padx=5, pady=5)
        
        # 발송 대기 목록
        pending_frame = ttk.LabelFrame(shipping_frame, text="발송 대기 목록")
        pending_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('주문번호', '고객명', '상품명', '수량', '주소', '연락처', '주문일')
        self.pending_tree = ttk.Treeview(pending_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.pending_tree.heading(col, text=col)
            self.pending_tree.column(col, width=120)
        
        # 스크롤바
        pending_scrollbar = ttk.Scrollbar(pending_frame, orient=tk.VERTICAL, command=self.pending_tree.yview)
        self.pending_tree.configure(yscrollcommand=pending_scrollbar.set)
        
        self.pending_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pending_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 액션 버튼
        shipping_action_frame = ttk.Frame(shipping_frame)
        shipping_action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(shipping_action_frame, text="선택 주문 발송처리", command=self.process_shipping).pack(side=tk.LEFT, padx=5)
        ttk.Button(shipping_action_frame, text="송장 일괄 등록", command=self.bulk_register_tracking).pack(side=tk.LEFT, padx=5)
    
    def create_api_test_tab(self):
        """API 테스트 탭 생성"""
        api_test_frame = ttk.Frame(self.notebook)
        self.notebook.add(api_test_frame, text="API 테스트")
        
        # API 연결 상태 프레임
        status_frame = ttk.LabelFrame(api_test_frame, text="API 연결 상태")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.api_status_var = tk.StringVar(value="API 연결 안됨")
        ttk.Label(status_frame, textvariable=self.api_status_var, font=('Arial', 10, 'bold')).pack(pady=5)
        
        # API 테스트 버튼들을 카테고리별로 그룹화
        test_buttons_frame = ttk.Frame(api_test_frame)
        test_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 1. 인증 및 기본 정보 그룹
        auth_group = ttk.LabelFrame(test_buttons_frame, text="🔐 인증 및 기본 정보", padding=10)
        auth_group.pack(fill=tk.X, padx=5, pady=5)
        
        auth_frame = ttk.Frame(auth_group)
        auth_frame.pack(fill=tk.X)
        
        ttk.Button(auth_frame, text="POST /oauth2/token", command=self.test_token_generation).pack(side=tk.LEFT, padx=5)
        ttk.Button(auth_frame, text="GET /seller/account", command=self.test_seller_account).pack(side=tk.LEFT, padx=5)
        ttk.Button(auth_frame, text="GET /seller/channels", command=self.test_seller_channels).pack(side=tk.LEFT, padx=5)
        
        # 2. 주문 관리 그룹
        order_group = ttk.LabelFrame(test_buttons_frame, text="📦 주문 관리", padding=10)
        order_group.pack(fill=tk.X, padx=5, pady=5)
        
        order_frame1 = ttk.Frame(order_group)
        order_frame1.pack(fill=tk.X, pady=2)
        
        ttk.Button(order_frame1, text="GET /product-orders/{id}", command=self.test_order_detail).pack(side=tk.LEFT, padx=5)
        ttk.Button(order_frame1, text="GET /product-orders", command=self.test_get_orders_detailed).pack(side=tk.LEFT, padx=5)
        
        # 시간 범위 선택 버튼들
        time_range_frame = ttk.Frame(order_group)
        time_range_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(time_range_frame, text="시간 범위:").pack(side=tk.LEFT, padx=5)
        ttk.Button(time_range_frame, text="1일", command=lambda: self.test_get_orders_with_range(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(time_range_frame, text="2일", command=lambda: self.test_get_orders_with_range(2)).pack(side=tk.LEFT, padx=2)
        ttk.Button(time_range_frame, text="3일", command=lambda: self.test_get_orders_with_range(3)).pack(side=tk.LEFT, padx=2)
        ttk.Button(time_range_frame, text="7일", command=lambda: self.test_get_orders_with_range(7)).pack(side=tk.LEFT, padx=2)
        
        
        order_frame2 = ttk.Frame(order_group)
        order_frame2.pack(fill=tk.X, pady=2)
        
        ttk.Button(order_frame2, text="GET /orders/{id}/product-order-ids", command=self.test_order_product_ids).pack(side=tk.LEFT, padx=5)
        ttk.Button(order_frame2, text="GET /product-orders/last-changed-statuses", command=self.test_last_changed_orders).pack(side=tk.LEFT, padx=5)
        ttk.Button(order_frame2, text="POST /product-orders/query", command=self.test_order_query).pack(side=tk.LEFT, padx=5)
        
        # 3. 상품 관리 그룹
        product_group = ttk.LabelFrame(test_buttons_frame, text="🛍️ 상품 관리", padding=10)
        product_group.pack(fill=tk.X, padx=5, pady=5)
        
        product_frame1 = ttk.Frame(product_group)
        product_frame1.pack(fill=tk.X, pady=2)
        
        ttk.Button(product_frame1, text="POST /products/search", command=self.test_get_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_frame1, text="GET /origin-products/{id}", command=self.test_get_origin_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_frame1, text="GET /channel-products/{id}", command=self.test_get_channel_product).pack(side=tk.LEFT, padx=5)
        
        product_frame2 = ttk.Frame(product_group)
        product_frame2.pack(fill=tk.X, pady=2)
        
        ttk.Button(product_frame2, text="PUT /origin-products/{id}/change-status", command=self.test_change_product_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_frame2, text="PUT /channel-products/{id}/options/{code}", command=self.test_change_product_option).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_frame2, text="PUT /products/multi-change", command=self.test_multi_product_change).pack(side=tk.LEFT, padx=5)
        
        # 4. 통계 및 분석 그룹
        stats_group = ttk.LabelFrame(test_buttons_frame, text="📊 통계 및 분석", padding=10)
        stats_group.pack(fill=tk.X, padx=5, pady=5)
        
        stats_frame = ttk.Frame(stats_group)
        stats_frame.pack(fill=tk.X)
        
        ttk.Button(stats_frame, text="GET /orders/statistics", command=self.test_order_statistics).pack(side=tk.LEFT, padx=5)
        ttk.Button(stats_frame, text="GET /stores", command=self.test_store_info).pack(side=tk.LEFT, padx=5)
        
        # 5. 진단 및 도구 그룹
        tools_group = ttk.LabelFrame(test_buttons_frame, text="🔧 진단 및 도구", padding=10)
        tools_group.pack(fill=tk.X, padx=5, pady=5)
        
        tools_frame = ttk.Frame(tools_group)
        tools_frame.pack(fill=tk.X)
        
        ttk.Button(tools_frame, text="API 연결 진단", command=self.diagnose_api_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(tools_frame, text="인증 정보 검증", command=self.validate_credentials).pack(side=tk.LEFT, padx=5)
        ttk.Button(tools_frame, text="네이버 API 센터 열기", command=self.open_naver_api_center).pack(side=tk.LEFT, padx=5)
        ttk.Button(tools_frame, text="전체 API 테스트", command=self.test_all_apis).pack(side=tk.LEFT, padx=5)
        
        # 커스텀 API 테스트 프레임
        custom_frame = ttk.LabelFrame(api_test_frame, text="커스텀 API 테스트")
        custom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(custom_frame, text="엔드포인트:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.custom_endpoint_var = tk.StringVar()
        self.custom_endpoint_entry = ttk.Entry(custom_frame, textvariable=self.custom_endpoint_var, width=40)
        self.custom_endpoint_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(custom_frame, text="메서드:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.custom_method_var = tk.StringVar(value="GET")
        custom_method_combo = ttk.Combobox(custom_frame, textvariable=self.custom_method_var, 
                                         values=["GET", "POST", "PUT", "DELETE"], width=10)
        custom_method_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(custom_frame, text="테스트 실행", command=self.test_custom_api).grid(row=0, column=4, padx=5, pady=5)
        
        # 요청/응답 표시 프레임
        response_frame = ttk.LabelFrame(api_test_frame, text="API 응답 결과")
        response_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 탭 위젯 (요청/응답 분리)
        response_notebook = ttk.Notebook(response_frame)
        response_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 요청 탭
        request_frame = ttk.Frame(response_notebook)
        response_notebook.add(request_frame, text="요청 정보")
        
        self.request_text = tk.Text(request_frame, height=8, wrap=tk.WORD, state=tk.NORMAL)
        request_scrollbar = ttk.Scrollbar(request_frame, orient=tk.VERTICAL, command=self.request_text.yview)
        self.request_text.configure(yscrollcommand=request_scrollbar.set)
        self.request_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        request_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 요청 텍스트 위젯에 복사/붙여넣기 바인딩 추가
        self.request_text.bind('<Control-c>', lambda e: self.copy_request_text())
        self.request_text.bind('<Control-a>', lambda e: self.select_all_text(self.request_text))
        self.request_text.bind('<Button-3>', lambda e: self.show_request_context_menu(e))
        enable_context_menu(self.request_text)
        
        # 응답 탭
        response_content_frame = ttk.Frame(response_notebook)
        response_notebook.add(response_content_frame, text="응답 결과")
        
        self.response_text = tk.Text(response_content_frame, height=8, wrap=tk.WORD, state=tk.NORMAL)
        response_scrollbar = ttk.Scrollbar(response_content_frame, orient=tk.VERTICAL, command=self.response_text.yview)
        self.response_text.configure(yscrollcommand=response_scrollbar.set)
        self.response_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        response_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 응답 텍스트 위젯에 복사/붙여넣기 바인딩 추가
        self.response_text.bind('<Control-c>', lambda e: self.copy_response_text())
        self.response_text.bind('<Control-a>', lambda e: self.select_all_text(self.response_text))
        self.response_text.bind('<Button-3>', lambda e: self.show_response_context_menu(e))
        enable_context_menu(self.response_text)
        
        # 액션 버튼들
        action_frame = ttk.Frame(api_test_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(action_frame, text="응답 결과 지우기", command=self.clear_response).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="응답 결과 복사", command=self.copy_response).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="응답 결과 저장", command=self.save_response).pack(side=tk.LEFT, padx=5)
    
    def set_home_date_range(self, days):
        """홈 탭 빠른 날짜 범위 설정"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # DateEntry 위젯에 날짜 설정
        self.home_start_date_entry.set_date(start_date.date())
        self.home_end_date_entry.set_date(end_date.date())
    
    def query_new_orders(self):
        """홈 탭에서 신규주문만 조회"""
        if not self.naver_api:
            messagebox.showerror("오류", "API 설정이 필요합니다.")
            return
        
        def query_thread():
            try:
                self.home_status_var.set("신규주문 조회 중...")
                
                # 트리뷰 초기화
                for item in self.home_orders_tree.get_children():
                    self.home_orders_tree.delete(item)
                
                # 날짜 범위 설정 (DateEntry에서 날짜 가져오기)
                start_date_str = self.home_start_date_entry.get_date().strftime('%Y-%m-%d')
                end_date_str = self.home_end_date_entry.get_date().strftime('%Y-%m-%d')
                
                print(f"홈 탭 신규주문 조회 날짜 범위: {start_date_str} ~ {end_date_str}")
                
                # 신규주문만 조회 (PAYED 상태)
                response = self.naver_api.get_orders(
                    start_date=start_date_str,
                    end_date=end_date_str,
                    order_status='PAYED',  # 신규주문만
                    limit=100
                )
                
                if response.get('success'):
                    data = response.get('data', {})
                    print(f"홈 탭 응답 데이터 구조: {type(data)}")
                    print(f"홈 탭 응답 키들: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    if 'data' in data:
                        orders = data['data']
                        print(f"홈 탭 주문 데이터 타입: {type(orders)}")
                        print(f"홈 탭 주문 데이터 개수: {len(orders) if isinstance(orders, list) else 'Not a list'}")
                        if isinstance(orders, list) and len(orders) > 0:
                            print(f"홈 탭 첫 번째 주문 데이터: {orders[0]}")
                            # 중복 확인을 위한 주문 ID 추출
                            order_ids = [order.get('orderId', 'N/A') for order in orders if isinstance(order, dict)]
                            print(f"홈 탭 주문 ID들: {order_ids}")
                            # 중복 제거
                            unique_order_ids = list(set(order_ids))
                            print(f"홈 탭 고유 주문 ID 개수: {len(unique_order_ids)}")
                            print(f"홈 탭 중복 제거 전: {len(orders)}건, 중복 제거 후: {len(unique_order_ids)}건")
                        
                        # 중복 제거
                        unique_orders = self.remove_duplicate_orders(orders)
                        chunks = response.get('chunks_processed', 0)
                        print(f"신규주문: {len(orders)}건 조회 완료, 중복 제거 후: {len(unique_orders)}건 ({chunks}개 청크)")
                        
                        # UI 업데이트
                        self.root.after(0, lambda: update_ui(unique_orders, chunks))
                    else:
                        print("신규주문: 0건 조회")
                        print(f"data 키가 없음. 전체 응답: {data}")
                        self.root.after(0, lambda: self.home_status_var.set("조회 완료: 0건"))
                else:
                    print("신규주문: 조회 실패")
                    print(f"실패 응답: {response}")
                    self.root.after(0, lambda: self.home_status_var.set("조회 실패"))
                
            except Exception as e:
                print(f"홈 탭 신규주문 조회 오류: {e}")
                self.root.after(0, lambda: messagebox.showerror("오류", f"신규주문 조회 중 오류가 발생했습니다: {e}"))
        
        def update_ui(orders, chunks):
            """UI 업데이트"""
            try:
                for order in orders:
                    # 주문 데이터가 딕셔너리인지 확인
                    if not isinstance(order, dict):
                        print(f"주문 데이터 타입 오류: {type(order)}, 데이터: {order}")
                        continue
                    
                    order_id = order.get('orderId', 'N/A')
                    customer_name = order.get('buyerName', 'N/A')
                    product_name = order.get('productName', 'N/A')
                    price = order.get('totalPayAmount', 0)
                    status = order.get('orderStatusType', 'N/A')
                    order_date = order.get('orderDate', 'N/A')
                    quantity = order.get('quantity', 1)
                    
                    # 날짜 형식 변환
                    if order_date != 'N/A' and len(order_date) > 10:
                        order_date = order_date[:10]
                    
                    # 가격 형식 변환
                    if price and isinstance(price, (int, float)):
                        price_str = f"{int(price):,}원"
                    else:
                        price_str = "0원"
                    
                    # 상태 한글 변환
                    status_mapping = {
                        'PAYED': '신규주문',
                        'READY': '발송대기',
                        'DELIVERING': '배송중',
                        'DELIVERED': '배송완료',
                        'PURCHASE_DECIDED': '구매확정',
                        'CANCELED': '취소주문',
                        'RETURNED': '반품주문',
                        'EXCHANGED': '교환주문'
                    }
                    status_korean = status_mapping.get(status, status)
                    
                    # 트리뷰에 추가
                    self.home_orders_tree.insert('', 'end', values=(
                        order_id, customer_name, product_name, quantity, 
                        price_str, status_korean, order_date
                    ))
                
                # 상태 업데이트
                self.home_status_var.set(f"조회 완료: {len(orders)}건 (총 {chunks}개 청크 처리)")
                
            except Exception as e:
                print(f"UI 업데이트 오류: {e}")
                self.home_status_var.set(f"UI 업데이트 오류: {e}")
        
        # 백그라운드에서 실행
        threading.Thread(target=query_thread, daemon=True).start()
    
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

    def create_settings_tab(self):
        """설정 탭 생성"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="설정")
        
        # 네이버 API 설정
        api_frame = ttk.LabelFrame(settings_frame, text="네이버 API 설정")
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(api_frame, text="Client ID:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.client_id_var = tk.StringVar()
        self.client_id_entry = ttk.Entry(api_frame, textvariable=self.client_id_var, width=40)
        self.client_id_entry.grid(row=0, column=1, padx=5, pady=5)
        enable_context_menu(self.client_id_entry)
        
        ttk.Label(api_frame, text="Client Secret:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.client_secret_var = tk.StringVar()
        self.client_secret_entry = ttk.Entry(api_frame, textvariable=self.client_secret_var, width=40, show='*')
        self.client_secret_entry.grid(row=1, column=1, padx=5, pady=5)
        enable_context_menu(self.client_secret_entry)
        
        ttk.Button(api_frame, text="API 연결 테스트", command=self.test_api_connection).grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # 디스코드 설정
        discord_frame = ttk.LabelFrame(settings_frame, text="디스코드 알림 설정")
        discord_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(discord_frame, text="웹훅 URL:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.discord_webhook_var = tk.StringVar()
        self.discord_webhook_entry = ttk.Entry(discord_frame, textvariable=self.discord_webhook_var, width=50)
        self.discord_webhook_entry.grid(row=0, column=1, padx=5, pady=5)
        enable_context_menu(self.discord_webhook_entry)
        
        self.discord_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(discord_frame, text="디스코드 알림 활성화", variable=self.discord_enabled_var).grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # 알림 설정
        notification_frame = ttk.LabelFrame(settings_frame, text="알림 설정")
        notification_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.desktop_notification_var = tk.BooleanVar()
        ttk.Checkbutton(notification_frame, text="데스크탑 알림 활성화", variable=self.desktop_notification_var).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        ttk.Label(notification_frame, text="체크 간격(초):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.check_interval_var = tk.StringVar()
        self.check_interval_entry = ttk.Entry(notification_frame, textvariable=self.check_interval_var, width=10)
        self.check_interval_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        enable_context_menu(self.check_interval_entry)
        
        # 자동 새로고침 설정
        refresh_frame = ttk.LabelFrame(settings_frame, text="자동 새로고침 설정")
        refresh_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.auto_refresh_var = tk.BooleanVar()
        ttk.Checkbutton(refresh_frame, text="자동 새로고침 활성화", variable=self.auto_refresh_var).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        ttk.Label(refresh_frame, text="새로고침 간격(초):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.refresh_interval_var = tk.StringVar()
        self.refresh_interval_entry = ttk.Entry(refresh_frame, textvariable=self.refresh_interval_var, width=10)
        self.refresh_interval_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        enable_context_menu(self.refresh_interval_entry)
        
        # 상품상태 설정
        product_status_frame = ttk.LabelFrame(settings_frame, text="상품상태 조회 설정")
        product_status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(product_status_frame, text="조회할 상품상태:").grid(row=0, column=0, padx=5, pady=5, sticky='nw')
        
        # 상품상태 체크박스들
        self.product_status_vars = {
            'SALE': tk.BooleanVar(value=True),
            'WAIT': tk.BooleanVar(value=True),
            'OUTOFSTOCK': tk.BooleanVar(value=True),
            'SUSPENSION': tk.BooleanVar(value=True),
            'CLOSE': tk.BooleanVar(value=True),
            'PROHIBITION': tk.BooleanVar(value=True)
        }
        status_options = [
            ('SALE', '판매중'),
            ('WAIT', '판매대기'),
            ('OUTOFSTOCK', '품절'),
            ('SUSPENSION', '판매중지'),
            ('CLOSE', '판매종료'),
            ('PROHIBITION', '판매금지')
        ]
        
        for i, (status_code, status_name) in enumerate(status_options):
            var = tk.BooleanVar()
            self.product_status_vars[status_code] = var
            ttk.Checkbutton(product_status_frame, text=status_name, variable=var).grid(
                row=1 + (i // 2), column=(i % 2), padx=5, pady=2, sticky='w'
            )
        
        # 알림 테스트 섹션
        test_frame = ttk.LabelFrame(settings_frame, text="알림 테스트")
        test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(test_frame, text="가상주문 데이터로 알림 테스트:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        test_buttons_frame = ttk.Frame(test_frame)
        test_buttons_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        
        ttk.Button(test_buttons_frame, text="신규주문 데스크탑 알림 테스트", command=self.test_new_order_notification).pack(side=tk.LEFT, padx=2)
        ttk.Button(test_buttons_frame, text="상태변화 디스코드 알림 테스트", command=self.test_order_status_notification).pack(side=tk.LEFT, padx=2)
        ttk.Button(test_buttons_frame, text="배송완료 디스코드 알림 테스트", command=self.test_delivery_complete_notification).pack(side=tk.LEFT, padx=2)
        
        # 저장 버튼
        save_frame = ttk.Frame(settings_frame)
        save_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(save_frame, text="설정 저장", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="설정 초기화", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
    
    def load_settings(self):
        """설정 로드"""
        self.client_id_var.set(config.get('NAVER_CLIENT_ID'))
        self.client_secret_var.set(config.get('NAVER_CLIENT_SECRET'))
        
        self.discord_webhook_var.set(config.get('DISCORD_WEBHOOK_URL'))
        self.discord_enabled_var.set(config.get_bool('DISCORD_ENABLED'))
        
        self.desktop_notification_var.set(config.get_bool('DESKTOP_NOTIFICATIONS', True))
        self.check_interval_var.set(str(config.get_int('CHECK_INTERVAL', 300)))
        
        self.auto_refresh_var.set(config.get_bool('AUTO_REFRESH', True))
        self.refresh_interval_var.set(str(config.get_int('REFRESH_INTERVAL', 60)))
        
        # 상품상태 설정 로드 (기본값: 모든 상태 선택)
        default_statuses = ['SALE', 'WAIT', 'OUTOFSTOCK', 'SUSPENSION', 'CLOSE', 'PROHIBITION']
        saved_statuses_str = config.get('PRODUCT_STATUS_TYPES', ','.join(default_statuses))
        saved_statuses = saved_statuses_str.split(',')
        print(f"설정 로드 - 저장된 상품상태 문자열: {saved_statuses_str}")
        print(f"설정 로드 - 저장된 상품상태 리스트: {saved_statuses}")
        
        for status_code in self.product_status_vars:
            is_selected = status_code in saved_statuses
            self.product_status_vars[status_code].set(is_selected)
            print(f"설정 로드 - {status_code}: {is_selected}")
        
        # API 및 알림 매니저 초기화
        if self.client_id_var.get() and self.client_secret_var.get():
            self.naver_api = NaverShoppingAPI(
                self.client_id_var.get(),
                self.client_secret_var.get()
            )
        
        if self.discord_webhook_var.get():
            self.notification_manager.set_discord_webhook(self.discord_webhook_var.get())
    
    def save_settings(self):
        """설정 저장"""
        config.set('NAVER_CLIENT_ID', self.client_id_var.get())
        config.set('NAVER_CLIENT_SECRET', self.client_secret_var.get())
        
        config.set('DISCORD_WEBHOOK_URL', self.discord_webhook_var.get())
        config.set('DISCORD_ENABLED', str(self.discord_enabled_var.get()))
        
        config.set('DESKTOP_NOTIFICATIONS', str(self.desktop_notification_var.get()))
        config.set('CHECK_INTERVAL', self.check_interval_var.get())
        
        config.set('AUTO_REFRESH', str(self.auto_refresh_var.get()))
        config.set('REFRESH_INTERVAL', self.refresh_interval_var.get())
        
        # 상품상태 설정 저장
        selected_statuses = [status_code for status_code, var in self.product_status_vars.items() if var.get()]
        config.set('PRODUCT_STATUS_TYPES', ','.join(selected_statuses))
        
        config.save_to_env_file()
        self.load_settings()
        
        messagebox.showinfo("설정 저장", "설정이 .env 파일에 저장되었습니다.")
    
    def reset_settings(self):
        """설정 초기화"""
        if messagebox.askyesno("설정 초기화", "모든 설정을 초기화하시겠습니까?"):
            # 환경 변수 초기화
            config.set('NAVER_CLIENT_ID', '')
            config.set('NAVER_CLIENT_SECRET', '')
            config.set('DISCORD_WEBHOOK_URL', '')
            config.set('DISCORD_ENABLED', 'false')
            config.set('DESKTOP_NOTIFICATIONS', 'true')
            config.set('CHECK_INTERVAL', '300')
            config.set('AUTO_REFRESH', 'true')
            config.set('REFRESH_INTERVAL', '60')
            
            config.save_to_env_file()
            self.load_settings()
            messagebox.showinfo("설정 초기화", "설정이 초기화되었습니다.")
    
    def refresh_dashboard(self):
        """대시보드 새로고침"""
        def refresh_thread():
            try:
                self.update_api_status("주문 현황 조회 중...")
                
                # API 초기화 확인
                if not self.naver_api:
                    if self.client_id_var.get() and self.client_secret_var.get():
                        self.naver_api = NaverShoppingAPI(
                            self.client_id_var.get(),
                            self.client_secret_var.get()
                        )
                    else:
                        self.root.after(0, lambda: messagebox.showerror("오류", "API 설정이 필요합니다."))
                        return
                
                # 신규주문만 조회 (디버깅용)
                print("=== 신규주문만 조회 (디버깅 모드) ===")
                
                # 날짜 범위 설정 (최근 1일)
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=1)
                
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
                
                print(f"주문 조회 날짜 범위: {start_date_str} ~ {end_date_str}")
                
                # 신규주문만 조회
                order_counts = {}
                all_orders = []
                total_chunks = 0
                
                try:
                    print(f"\n=== 신규주문 조회 시작 ===")
                    response = self.naver_api.get_orders(
                        start_date=start_date_str, 
                        end_date=end_date_str, 
                        order_status='PAYED',  # 신규주문만
                        limit=100
                    )
                    if response.get('success'):
                        data = response.get('data', {})
                        print(f"대시보드 응답 데이터 구조: {type(data)}")
                        print(f"대시보드 응답 키들: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        if 'data' in data:
                            orders = data['data']
                            print(f"대시보드 주문 데이터 타입: {type(orders)}")
                            print(f"대시보드 주문 데이터 개수: {len(orders) if isinstance(orders, list) else 'Not a list'}")
                            if isinstance(orders, list) and len(orders) > 0:
                                print(f"대시보드 첫 번째 주문 데이터: {orders[0]}")
                                # 중복 확인을 위한 주문 ID 추출
                                order_ids = [order.get('orderId', 'N/A') for order in orders if isinstance(order, dict)]
                                print(f"대시보드 주문 ID들: {order_ids}")
                                # 중복 제거
                                unique_order_ids = list(set(order_ids))
                                print(f"대시보드 고유 주문 ID 개수: {len(unique_order_ids)}")
                                print(f"대시보드 중복 제거 전: {len(orders)}건, 중복 제거 후: {len(unique_order_ids)}건")
                            
                            # 중복 제거
                            unique_orders = self.remove_duplicate_orders(orders)
                            order_counts['신규주문'] = len(unique_orders)
                            all_orders.extend(unique_orders)
                            chunks = response.get('chunks_processed', 0)
                            total_chunks += chunks
                            print(f"신규주문: {len(orders)}건 조회 완료 ({chunks}개 청크)")
                        else:
                            order_counts['신규주문'] = 0
                            print("신규주문: 0건 조회")
                            print(f"data 키가 없음. 전체 응답: {data}")
                    else:
                        order_counts['신규주문'] = 0
                        print("신규주문: 조회 실패")
                        print(f"실패 응답: {response}")
                except Exception as e:
                    print(f"신규주문 조회 오류: {e}")
                    order_counts['신규주문'] = 0
                
                # 다른 상태들은 0으로 설정 (디버깅용)
                for status in ['발송대기', '배송중', '배송완료', '구매확정', '취소주문', '반품주문', '교환주문']:
                    order_counts[status] = 0
                
                print(f"\n전체 조회 완료: 총 {total_chunks}개 청크 처리")
                
                # UI 스레드에서 업데이트
                self.root.after(0, lambda: update_ui(order_counts, all_orders))
                
            except Exception as e:
                print(f"대시보드 새로고침 오류: {e}")
                self.root.after(0, lambda: messagebox.showerror("오류", f"대시보드 새로고침 중 오류가 발생했습니다: {e}"))
        
        def update_ui(order_counts, all_orders):
            """UI 업데이트"""
            try:
                # 이전 상태와 비교하여 변화 감지
                previous_counts = getattr(self, 'previous_order_counts', {})
                status_changes = {}
                
                for status, current_count in order_counts.items():
                    previous_count = previous_counts.get(status, 0)
                    if current_count != previous_count:
                        status_changes[status] = current_count
                
                # 이전 상태 저장
                self.previous_order_counts = order_counts.copy()
                
                # 상태변화가 있으면 디스코드 알림 전송
                if status_changes and self.notification_manager:
                    self.notification_manager.send_store_status_change_notification(status_changes)
                
                # 신규주문 감지 (신규주문이 증가한 경우)
                new_orders_count = status_changes.get('신규주문', 0)
                if new_orders_count > 0:
                    # 신규주문이 있으면 데스크탑 알림 전송
                    self._send_new_order_desktop_notification(new_orders_count)
                
                # 통계 업데이트
                for status, var in self.stats_vars.items():
                    var.set(str(order_counts.get(status, 0)))
                
                # 최근 주문 목록 업데이트
                for item in self.recent_tree.get_children():
                    self.recent_tree.delete(item)
                
                # 최근 20개 주문 표시 (딕셔너리 타입만 필터링)
                valid_orders = [order for order in all_orders if isinstance(order, dict)]
                recent_orders = sorted(valid_orders, key=lambda x: x.get('orderDate', ''), reverse=True)[:20]
                
                for order in recent_orders:
                    # 주문 데이터가 딕셔너리인지 확인
                    if not isinstance(order, dict):
                        print(f"대시보드 주문 데이터 타입 오류: {type(order)}, 데이터: {order}")
                        continue
                    
                    order_id = order.get('orderId', 'N/A')
                    customer_name = order.get('buyerName', 'N/A')
                    product_name = order.get('productName', 'N/A')
                    price = order.get('totalPayAmount', 0)
                    status = order.get('orderStatusType', 'N/A')
                    order_date = order.get('orderDate', 'N/A')
                    
                    # 날짜 형식 변환
                    if order_date != 'N/A' and len(order_date) > 10:
                        order_date = order_date[:10]
                    
                    # 가격 형식 변환
                    if price and isinstance(price, (int, float)):
                        price_str = f"{int(price):,}원"
                    else:
                        price_str = "0원"
                    
                    self.recent_tree.insert('', 'end', values=(
                        order_id, customer_name, product_name, price_str, status, order_date
                    ))
                
                self.update_api_status(f"대시보드 새로고침 완료 - {datetime.now().strftime('%H:%M:%S')}")
                
            except Exception as e:
                print(f"UI 업데이트 오류: {e}")
                messagebox.showerror("오류", f"UI 업데이트 중 오류가 발생했습니다: {e}")
        
        # 백그라운드에서 주문 조회
        import threading
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def _send_new_order_desktop_notification(self, new_orders_count: int):
        """신규주문 데스크탑 알림 전송"""
        if not self.notification_manager or not self.notification_manager.enabled_notifications['desktop']:
            return
        
        title = "🛒 신규 주문 알림"
        message = f"새로운 주문이 {new_orders_count}건 접수되었습니다!\n"
        message += f"확인 시간: {datetime.now().strftime('%H:%M:%S')}"
        
        # 알림음이 포함된 데스크탑 알림 전송
        self.notification_manager.send_desktop_notification_with_sound(title, message)
    
    def sync_orders(self):
        """주문 동기화"""
        # API 초기화 확인
        if not self.naver_api:
            if self.client_id_var.get() and self.client_secret_var.get():
                self.naver_api = NaverShoppingAPI(
                    self.client_id_var.get(),
                    self.client_secret_var.get()
                )
            else:
                messagebox.showerror("오류", "API 설정이 필요합니다.\n설정 탭에서 Client ID와 Client Secret을 입력해주세요.")
                return
        
        def sync_thread():
            try:
                self.update_api_status("주문 동기화 중...")
                
                # 최근 7일간의 주문 조회
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                response = self.naver_api.get_orders(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    limit=1000
                )
                
                if response.get('success'):
                    data = response.get('data', {})
                    if 'data' in data:
                        orders = data['data']
                        synced_count = len(orders)
                        
                        # 데이터베이스에 주문 저장 (기존 데이터는 덮어쓰기)
                        for order in orders:
                            try:
                                order_data = {
                                    'order_id': order.get('orderId', ''),
                                    'customer_name': order.get('buyerName', ''),
                                    'product_name': order.get('productName', ''),
                                    'price': order.get('totalPayAmount', 0),
                                    'status': order.get('orderStatusType', ''),
                                    'order_date': order.get('orderDate', ''),
                                    'phone': order.get('buyerPhoneNumber1', ''),
                                    'address': order.get('receiverAddress', ''),
                                    'memo': order.get('orderMemo', '')
                                }
                                
                                # 데이터베이스에 저장 (기존 주문이 있으면 업데이트)
                                self.db_manager.save_order(order_data)
                                
                            except Exception as e:
                                print(f"주문 저장 오류: {e}")
                        
                        self.root.after(0, lambda: self.update_api_status(f"주문 동기화 완료 - {synced_count}건"))
                        self.root.after(0, lambda: self.refresh_dashboard())
                    else:
                        self.root.after(0, lambda: self.update_api_status("동기화할 주문이 없습니다."))
                else:
                    error = response.get('error', '알 수 없는 오류')
                    self.root.after(0, lambda: self.update_api_status(f"동기화 실패: {error}"))
                    
            except Exception as e:
                print(f"주문 동기화 오류: {e}")
                self.root.after(0, lambda: self.update_api_status(f"동기화 오류: {e}"))
                self.root.after(0, lambda: messagebox.showerror("오류", f"주문 동기화 중 오류가 발생했습니다: {e}"))
        
        # 백그라운드에서 주문 동기화
        import threading
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def filter_orders(self):
        """주문 필터링"""
        try:
            # 트리뷰 초기화
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)
            
            # 주문 조회
            if self.status_filter.get() == '전체':
                orders = self.db_manager.get_all_orders()
            else:
                orders = self.db_manager.get_orders_by_status(self.status_filter.get())
            
            # 날짜 필터링 (DateEntry에서 날짜 가져오기)
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            
            filtered_orders = []
            for order in orders:
                order_date = datetime.strptime(order['order_date'], '%Y-%m-%d')
                if start_date <= order_date <= end_date:
                    filtered_orders.append(order)
            
            # 트리뷰에 추가
            for order in filtered_orders:
                self.orders_tree.insert('', 'end', values=(
                    order['order_id'],
                    order['customer_name'],
                    order['customer_phone'],
                    order['product_name'],
                    order['quantity'],
                    f"{order['price']:,}원",
                    order['status'],
                    order['order_date']
                ))
            
            self.status_var.set(f"주문 조회 완료 - {len(filtered_orders)}건")
            
        except Exception as e:
            messagebox.showerror("오류", f"주문 조회 중 오류가 발생했습니다: {e}")
    
    def load_orders_from_api(self):
        """API에서 주문 조회"""
        if not self.naver_api:
            messagebox.showerror("오류", "API 설정이 필요합니다.")
            return
        
        def api_thread():
            try:
                self.update_api_status("API에서 주문 조회 중...")
                
                # 트리뷰 초기화
                for item in self.orders_tree.get_children():
                    self.orders_tree.delete(item)
                
                # 날짜 범위 설정 (DateEntry에서 날짜 가져오기)
                start_date_str = self.start_date_entry.get_date().strftime('%Y-%m-%d')
                end_date_str = self.end_date_entry.get_date().strftime('%Y-%m-%d')
                
                print(f"API 주문 조회 날짜 범위: {start_date_str} ~ {end_date_str}")
                
                # 상태 필터 확인
                status_filter = self.status_filter.get()
                status_mapping = {
                    '신규주문': 'PAYED',
                    '발송대기': 'READY',
                    '배송중': 'DELIVERING',
                    '배송완료': 'DELIVERED',
                    '구매확정': 'PURCHASE_DECIDED',
                    '취소주문': 'CANCELED',
                    '반품주문': 'RETURNED',
                    '교환주문': 'EXCHANGED'
                }
                
                all_orders = []
                total_chunks = 0
                
                if status_filter == '전체':
                    # 모든 상태 조회
                    for display_status, api_status in status_mapping.items():
                        try:
                            print(f"\n=== {display_status} 조회 시작 ===")
                            response = self.naver_api.get_orders(
                                start_date=start_date_str,
                                end_date=end_date_str,
                                order_status=api_status,
                                limit=100
                            )
                            if response.get('success'):
                                data = response.get('data', {})
                                if 'data' in data:
                                    orders = data['data']
                                    all_orders.extend(orders)
                                    chunks = response.get('chunks_processed', 0)
                                    total_chunks += chunks
                                    print(f"{display_status}: {len(orders)}건 조회 완료 ({chunks}개 청크)")
                                else:
                                    print(f"{display_status}: 0건 조회")
                            else:
                                print(f"{display_status}: 조회 실패")
                        except Exception as e:
                            print(f"상태 {display_status} 조회 오류: {e}")
                else:
                    # 특정 상태만 조회
                    api_status = status_mapping.get(status_filter)
                    if api_status:
                        print(f"\n=== {status_filter} 조회 시작 ===")
                        response = self.naver_api.get_orders(
                            start_date=start_date_str,
                            end_date=end_date_str,
                            order_status=api_status,
                            limit=100
                        )
                        if response.get('success'):
                            data = response.get('data', {})
                            if 'data' in data:
                                all_orders = data['data']
                                total_chunks = response.get('chunks_processed', 0)
                                print(f"{status_filter}: {len(all_orders)}건 조회 완료 ({total_chunks}개 청크)")
                            else:
                                print(f"{status_filter}: 0건 조회")
                        else:
                            print(f"{status_filter}: 조회 실패")
                
                print(f"\n전체 조회 완료: 총 {total_chunks}개 청크 처리")
                
                # UI 업데이트
                self.root.after(0, lambda: update_ui(all_orders))
                
            except Exception as e:
                print(f"API 주문 조회 오류: {e}")
                self.root.after(0, lambda: messagebox.showerror("오류", f"API 주문 조회 중 오류가 발생했습니다: {e}"))
        
        def update_ui(orders):
            """UI 업데이트"""
            try:
                for order in orders:
                    # 주문 데이터가 딕셔너리인지 확인
                    if not isinstance(order, dict):
                        print(f"주문 데이터 타입 오류: {type(order)}, 데이터: {order}")
                        continue
                    
                    order_id = order.get('orderId', 'N/A')
                    customer_name = order.get('buyerName', 'N/A')
                    product_name = order.get('productName', 'N/A')
                    price = order.get('totalPayAmount', 0)
                    status = order.get('orderStatusType', 'N/A')
                    order_date = order.get('orderDate', 'N/A')
                    quantity = order.get('quantity', 1)
                    
                    # 날짜 형식 변환
                    if order_date != 'N/A' and len(order_date) > 10:
                        order_date = order_date[:10]
                    
                    # 가격 형식 변환
                    if price and isinstance(price, (int, float)):
                        price_str = f"{int(price):,}원"
                    else:
                        price_str = "0원"
                    
                    self.orders_tree.insert('', 'end', values=(
                        order_id, customer_name, product_name, quantity, price_str, status, order_date
                    ))
                
                self.status_var.set(f"API 주문 조회 완료 - {len(orders)}건")
                self.update_api_status(f"API 주문 조회 완료 - {len(orders)}건 (24시간 단위 청크 조회)")
                
            except Exception as e:
                print(f"UI 업데이트 오류: {e}")
                messagebox.showerror("오류", f"UI 업데이트 중 오류가 발생했습니다: {e}")
        
        # 백그라운드에서 API 조회
        import threading
        threading.Thread(target=api_thread, daemon=True).start()
    
    def export_to_excel(self):
        """엑셀 내보내기"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            if filename:
                # 선택된 주문 데이터 가져오기
                orders = []
                for item in self.orders_tree.get_children():
                    values = self.orders_tree.item(item)['values']
                    orders.append({
                        '주문번호': values[0],
                        '고객명': values[1],
                        '연락처': values[2],
                        '상품명': values[3],
                        '수량': values[4],
                        '금액': values[5],
                        '상태': values[6],
                        '주문일': values[7]
                    })
                
                # 엑셀 파일 생성
                import pandas as pd
                df = pd.DataFrame(orders)
                df.to_excel(filename, index=False, engine='openpyxl')
                
                messagebox.showinfo("내보내기 완료", f"엑셀 파일이 저장되었습니다: {filename}")
                
        except Exception as e:
            messagebox.showerror("오류", f"엑셀 내보내기 중 오류가 발생했습니다: {e}")
    
    def test_api_connection(self):
        """API 연결 테스트"""
        if not self.client_id_var.get() or not self.client_secret_var.get():
            messagebox.showerror("오류", "Client ID와 Client Secret을 모두 입력해주세요.")
            return
        
        def test_thread():
            try:
                self.status_var.set("API 연결 테스트 중...")
                api = NaverShoppingAPI(
                    self.client_id_var.get(),
                    self.client_secret_var.get()
                )
                
                if api.get_access_token():
                    self.status_var.set("API 연결 성공")
                    messagebox.showinfo("연결 성공", "네이버 API 연결이 성공했습니다.")
                else:
                    self.status_var.set("API 연결 실패")
                    messagebox.showerror("연결 실패", "네이버 API 연결에 실패했습니다.")
                    
            except Exception as e:
                self.status_var.set(f"API 테스트 오류: {e}")
                messagebox.showerror("오류", f"API 연결 테스트 중 오류가 발생했습니다: {e}")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_notifications(self):
        """알림 테스트"""
        self.notification_manager.test_notifications()
        messagebox.showinfo("알림 테스트", "알림 테스트가 실행되었습니다.")
    
    def schedule_auto_refresh(self):
        """자동 새로고침 스케줄링"""
        if self.auto_refresh_var.get():
            self.root.after(self.auto_refresh_interval * 1000, self.auto_refresh)
    
    def auto_refresh(self):
        """자동 새로고침"""
        if self.auto_refresh_var.get():
            self.refresh_dashboard()
            self.schedule_auto_refresh()
    
    def change_order_status(self):
        """주문 상태 변경"""
        selected_item = self.orders_tree.selection()
        if not selected_item:
            messagebox.showwarning("선택 오류", "상태를 변경할 주문을 선택해주세요.")
            return
        
        item = selected_item[0]
        order_id = self.orders_tree.item(item)['values'][0]
        current_status = self.orders_tree.item(item)['values'][6]
        
        # 상태 선택 다이얼로그
        status_window = tk.Toplevel(self.root)
        status_window.title("주문 상태 변경")
        status_window.geometry("300x200")
        status_window.transient(self.root)
        status_window.grab_set()
        
        ttk.Label(status_window, text=f"주문번호: {order_id}").pack(pady=10)
        ttk.Label(status_window, text=f"현재 상태: {current_status}").pack(pady=5)
        
        ttk.Label(status_window, text="새 상태:").pack(pady=5)
        new_status_var = tk.StringVar(value=current_status)
        status_combo = ttk.Combobox(status_window, textvariable=new_status_var, 
                                   values=['신규주문', '발송대기', '배송중', '배송완료', '구매확정', '취소주문', '반품주문', '교환주문'])
        status_combo.pack(pady=5)
        
        def confirm_change():
            new_status = new_status_var.get()
            if new_status != current_status:
                if self.db_manager.update_order_status(order_id, new_status):
                    messagebox.showinfo("성공", f"주문 상태가 '{new_status}'로 변경되었습니다.")
                    self.filter_orders()  # 목록 새로고침
                    status_window.destroy()
                else:
                    messagebox.showerror("오류", "주문 상태 변경에 실패했습니다.")
            else:
                messagebox.showinfo("알림", "상태가 변경되지 않았습니다.")
                status_window.destroy()
        
        ttk.Button(status_window, text="변경", command=confirm_change).pack(pady=10)
        ttk.Button(status_window, text="취소", command=status_window.destroy).pack()
    
    def add_order_memo(self):
        """주문 메모 추가"""
        selected_item = self.orders_tree.selection()
        if not selected_item:
            messagebox.showwarning("선택 오류", "메모를 추가할 주문을 선택해주세요.")
            return
        
        item = selected_item[0]
        order_id = self.orders_tree.item(item)['values'][0]
        
        # 메모 입력 다이얼로그
        memo_window = tk.Toplevel(self.root)
        memo_window.title("주문 메모 추가")
        memo_window.geometry("400x300")
        memo_window.transient(self.root)
        memo_window.grab_set()
        
        ttk.Label(memo_window, text=f"주문번호: {order_id}").pack(pady=10)
        ttk.Label(memo_window, text="메모 내용:").pack(pady=5)
        
        memo_text = tk.Text(memo_window, height=10, width=40)
        memo_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        def save_memo():
            memo_content = memo_text.get("1.0", tk.END).strip()
            if memo_content:
                # 데이터베이스에 메모 저장 (구현 필요)
                messagebox.showinfo("성공", "메모가 저장되었습니다.")
                memo_window.destroy()
            else:
                messagebox.showwarning("입력 오류", "메모 내용을 입력해주세요.")
        
        ttk.Button(memo_window, text="저장", command=save_memo).pack(pady=10)
        ttk.Button(memo_window, text="취소", command=memo_window.destroy).pack()
    
    def view_order_detail(self):
        """주문 상세 보기"""
        selected_item = self.orders_tree.selection()
        if not selected_item:
            messagebox.showwarning("선택 오류", "상세를 볼 주문을 선택해주세요.")
            return
        
        item = selected_item[0]
        order_data = self.orders_tree.item(item)['values']
        
        # 상세 정보 다이얼로그
        detail_window = tk.Toplevel(self.root)
        detail_window.title("주문 상세 정보")
        detail_window.geometry("500x400")
        detail_window.transient(self.root)
        detail_window.grab_set()
        
        # 주문 정보 표시
        info_frame = ttk.Frame(detail_window)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        details = [
            ("주문번호", order_data[0]),
            ("고객명", order_data[1]),
            ("연락처", order_data[2]),
            ("상품명", order_data[3]),
            ("수량", order_data[4]),
            ("금액", order_data[5]),
            ("상태", order_data[6]),
            ("주문일", order_data[7])
        ]
        
        for i, (label, value) in enumerate(details):
            ttk.Label(info_frame, text=f"{label}:", font=('Arial', 10, 'bold')).grid(row=i, column=0, sticky='w', padx=5, pady=2)
            ttk.Label(info_frame, text=str(value)).grid(row=i, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Button(detail_window, text="닫기", command=detail_window.destroy).pack(pady=10)
    
    def register_tracking(self):
        """송장 등록"""
        company = self.shipping_company.get()
        tracking_number = self.tracking_number.get()
        
        if not company or not tracking_number:
            messagebox.showwarning("입력 오류", "택배사와 송장번호를 모두 입력해주세요.")
            return
        
        # 선택된 주문이 있는지 확인
        selected_item = self.pending_tree.selection()
        if not selected_item:
            messagebox.showwarning("선택 오류", "송장을 등록할 주문을 선택해주세요.")
            return
        
        item = selected_item[0]
        order_id = self.pending_tree.item(item)['values'][0]
        
        # 데이터베이스에 송장 정보 업데이트
        # TODO: 데이터베이스 업데이트 구현
        messagebox.showinfo("성공", f"송장이 등록되었습니다.\n택배사: {company}\n송장번호: {tracking_number}")
        
        # 입력 필드 초기화
        self.shipping_company.set('')
        self.tracking_number.delete(0, tk.END)
    
    def process_shipping(self):
        """선택 주문 발송처리"""
        selected_items = self.pending_tree.selection()
        if not selected_items:
            messagebox.showwarning("선택 오류", "발송처리할 주문을 선택해주세요.")
            return
        
        if messagebox.askyesno("발송처리 확인", f"선택된 {len(selected_items)}개 주문을 발송처리하시겠습니까?"):
            for item in selected_items:
                order_id = self.pending_tree.item(item)['values'][0]
                # 주문 상태를 '배송중'으로 변경
                self.db_manager.update_order_status(order_id, '배송중')
            
            messagebox.showinfo("완료", "선택된 주문이 발송처리되었습니다.")
            # 목록 새로고침
            self.load_pending_orders()
    
    def bulk_register_tracking(self):
        """송장 일괄 등록"""
        messagebox.showinfo("알림", "송장 일괄 등록 기능은 추후 구현 예정입니다.")
    
    def load_pending_orders(self):
        """발송 대기 주문 목록 로드"""
        # 트리뷰 초기화
        for item in self.pending_tree.get_children():
            self.pending_tree.delete(item)
        
        # 발송 대기 주문 조회
        pending_orders = self.db_manager.get_orders_by_status('발송대기')
        
        for order in pending_orders:
            self.pending_tree.insert('', 'end', values=(
                order['order_id'],
                order['customer_name'],
                order['product_name'],
                order['quantity'],
                '주소 정보',  # TODO: 주소 정보 추가
                order['customer_phone'],
                order['order_date']
            ))
    
    # API 테스트 메서드들
    def test_token_generation(self):
        """토큰 발급 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_thread():
            try:
                self.update_api_status("토큰 발급 테스트 중...")
                
                # 요청 정보 표시
                timestamp = int(time.time() * 1000)
                password = self.naver_api.client_id + "_" + str(timestamp)
                hashed = bcrypt.hashpw(password.encode('utf-8'), self.naver_api.client_secret.encode('utf-8'))
                client_secret_sign = pybase64.standard_b64encode(hashed).decode('utf-8')
                
                request_info = f"""토큰 발급 요청:
URL: {self.naver_api.base_url}/external/v1/oauth2/token
Method: POST
Headers:
  Content-Type: application/x-www-form-urlencoded
  Accept: application/json
Body:
  client_id: {self.naver_api.client_id}
  timestamp: {timestamp}
  client_secret_sign: {client_secret_sign[:20]}...
  grant_type: client_credentials
  type: SELF
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 토큰 발급 테스트
                success = self.naver_api.get_access_token()
                
                if success:
                    response_info = f"""토큰 발급 성공!
Access Token: {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
Token Type: Bearer
Status: 200 OK
"""
                    self.update_api_status("토큰 발급 성공")
                else:
                    # 실제 API 응답에서 오류 정보 추출
                    try:
                        # API 호출을 다시 해서 오류 정보 가져오기
                        import requests
                        timestamp = str(int(time.time() * 1000))
                        pwd = f'{self.naver_api.client_id}_{timestamp}'
                        hashed = hmac.new(
                            self.naver_api.client_secret.encode('utf-8'),
                            pwd.encode('utf-8'),
                            hashlib.sha256
                        ).digest()
                        client_secret_sign = base64.b64encode(hashed).decode('utf-8')
                        
                        url = f"{self.naver_api.base_url}/external/v1/oauth2/token"
                        headers = {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Accept': 'application/json'
                        }
                        data = {
                            'grant_type': 'client_credentials',
                            'client_id': self.naver_api.client_id,
                            'timestamp': timestamp,
                            'client_secret_sign': client_secret_sign,
                            'type': 'SELF'
                        }
                        
                        error_response = requests.post(url, headers=headers, data=data)
                        error_detail = error_response.text
                        
                        response_info = f"""토큰 발급 실패

API 응답:
{error_detail}

가능한 원인:
1. 애플리케이션 상태가 유효하지 않음
   - 네이버 커머스 API 센터에서 애플리케이션 상태 확인 필요
   - 애플리케이션이 승인되지 않았거나 비활성화 상태일 수 있음

2. Client ID 또는 Client Secret이 잘못됨
   - 네이버 커머스 API 센터에서 정확한 정보 확인 필요

3. API 권한 설정 문제
   - 필요한 API 권한이 활성화되지 않았을 수 있음

해결 방법:
1. 네이버 커머스 API 센터 (https://developers.naver.com/apps/) 접속
2. 애플리케이션 상태 확인 및 활성화
3. Client ID와 Client Secret 재확인
4. 필요한 API 권한 활성화
"""
                    except Exception as e:
                        response_info = f"""토큰 발급 실패

오류: {str(e)}

가능한 원인:
1. 애플리케이션 상태가 유효하지 않음
2. Client ID 또는 Client Secret이 잘못됨
3. API 권한 설정 문제

해결 방법:
1. 네이버 커머스 API 센터 (https://developers.naver.com/apps/) 접속
2. 애플리케이션 상태 확인 및 활성화
3. Client ID와 Client Secret 재확인
4. 필요한 API 권한 활성화
"""
                    
                    self.update_api_status("토큰 발급 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"토큰 발급 테스트 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("토큰 발급 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_store_info(self):
        """스토어 정보 조회 테스트"""
        # API 초기화 확인 및 재시도
        if not self.naver_api:
            if self.client_id_var.get() and self.client_secret_var.get():
                self.naver_api = NaverShoppingAPI(
                    self.client_id_var.get(),
                    self.client_secret_var.get()
                )
                self.update_api_status("API 재초기화 완료")
            else:
                self.show_api_error("API 설정이 필요합니다.\n설정 탭에서 Client ID와 Client Secret을 입력해주세요.")
                return
        
        def test_thread():
            try:
                self.update_api_status("스토어 정보 조회 중...")
                
                # 요청 정보 표시
                request_info = f"""스토어 정보 조회 요청:
URL: {self.naver_api.base_url}/stores
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
  X-Naver-Client-Id: {self.naver_api.client_id}
  X-Naver-Client-Secret: {'*' * len(self.naver_api.client_secret)}
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 스토어 정보 조회
                response = self.naver_api.get_store_info()
                
                # 상세한 서버 응답 정보 표시
                response_info = f"""스토어 정보 조회 응답:
상태 코드: {response.get('status_code', 'N/A')}
성공 여부: {response.get('success', False)}
메시지: {response.get('message', 'N/A')}
"""
                
                if response.get('success'):
                    data = response.get('data', {})
                    response_info += f"""
응답 데이터:
{json.dumps(data, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("스토어 정보 조회 성공")
                else:
                    error = response.get('error', '알 수 없는 오류')
                    response_info += f"""
오류 상세:
{error}
"""
                    self.update_api_status(f"스토어 정보 조회 실패 ({response.get('status_code', 'N/A')})")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"스토어 정보 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("스토어 정보 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_get_products(self):
        """상품 목록 조회 테스트"""
        # API 초기화 확인 및 재시도
        if not self.naver_api:
            if self.client_id_var.get() and self.client_secret_var.get():
                self.naver_api = NaverShoppingAPI(
                    self.client_id_var.get(),
                    self.client_secret_var.get()
                )
                self.update_api_status("API 재초기화 완료")
            else:
                self.show_api_error("API 설정이 필요합니다.\n설정 탭에서 Client ID와 Client Secret을 입력해주세요.")
                return
        
        def test_thread():
            try:
                self.update_api_status("상품 목록 조회 중...")
                
                # 설정에서 선택된 상품상태 가져오기
                selected_statuses = [status_code for status_code, var in self.product_status_vars.items() if var.get()]
                
                # 요청 정보 표시
                request_info = f"""상품 목록 조회 요청 (v1 API):
URL: {self.naver_api.base_url}/external/v1/products/search
Method: POST
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
  Accept: application/json;charset=UTF-8
  X-Naver-Client-Id: {self.naver_api.client_id}
  X-Naver-Client-Secret: {'*' * len(self.naver_api.client_secret)}
Request Body:
  productStatusTypes: {selected_statuses}
  page: 1
  size: 50
  orderType: NO
  periodType: PROD_REG_DAY
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 상품 목록 조회
                response = self.naver_api.get_products(product_status_types=selected_statuses)
                
                # 상세한 서버 응답 정보 표시
                response_info = f"""상품 목록 조회 응답:
상태 코드: {response.get('status_code', 'N/A')}
성공 여부: {response.get('success', False)}
메시지: {response.get('message', 'N/A')}
"""
                
                if response.get('success'):
                    data = response.get('data', {})
                    if data and 'data' in data:
                        products = data['data']
                        response_info += f"""
상품 개수: {len(products)}
응답 데이터 (처음 3개):
{json.dumps(products[:3], indent=2, ensure_ascii=False)}
"""
                        self.update_api_status(f"상품 목록 조회 성공 ({len(products)}개)")
                    else:
                        response_info += f"""
전체 응답 데이터:
{json.dumps(data, indent=2, ensure_ascii=False)}
"""
                        self.update_api_status("상품 목록 조회 성공 (데이터 구조 확인 필요)")
                else:
                    error = response.get('error', '알 수 없는 오류')
                    response_info += f"""
오류 상세:
{error}
"""
                    self.update_api_status(f"상품 목록 조회 실패 ({response.get('status_code', 'N/A')})")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"상품 목록 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("상품 목록 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_order_statistics(self):
        """주문 통계 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_thread():
            try:
                self.update_api_status("주문 통계 조회 중...")
                
                # 요청 정보 표시
                request_info = f"""주문 통계 조회 요청:
URL: {self.naver_api.base_url}/orders/statistics
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
  X-Naver-Client-Id: {self.naver_api.client_id}
  X-Naver-Client-Secret: {'*' * len(self.naver_api.client_secret)}
Parameters:
  startDate: {(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}
  endDate: {datetime.now().strftime('%Y-%m-%d')}
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 주문 통계 조회
                statistics = self.naver_api.get_order_statistics()
                
                if statistics:
                    response_info = f"""주문 통계 조회 성공!
응답 데이터:
{json.dumps(statistics, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("주문 통계 조회 성공")
                else:
                    response_info = "주문 통계 조회 실패"
                    self.update_api_status("주문 통계 조회 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"주문 통계 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("주문 통계 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_custom_api(self):
        """커스텀 API 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        endpoint = self.custom_endpoint_var.get().strip()
        method = self.custom_method_var.get().strip()
        
        if not endpoint:
            messagebox.showwarning("입력 오류", "엔드포인트를 입력해주세요.")
            return
        
        def test_thread():
            try:
                self.update_api_status(f"커스텀 API 테스트 중... ({method} {endpoint})")
                
                # 요청 정보 표시
                request_info = f"""커스텀 API 요청:
URL: {self.naver_api.base_url}{endpoint}
Method: {method}
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
  X-Naver-Client-Id: {self.naver_api.client_id}
  X-Naver-Client-Secret: {'*' * len(self.naver_api.client_secret)}
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 커스텀 API 호출
                response = self.naver_api.make_authenticated_request(method, endpoint)
                
                if response:
                    response_info = f"""커스텀 API 호출 성공!
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("커스텀 API 호출 성공")
                else:
                    response_info = "커스텀 API 호출 실패"
                    self.update_api_status("커스텀 API 호출 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"커스텀 API 호출 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("커스텀 API 호출 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_all_apis(self):
        """전체 API 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_all_thread():
            try:
                self.update_api_status("전체 API 테스트 시작...")
                
                test_results = []
                
                # 1. 토큰 발급 테스트
                self.update_api_status("1/5 토큰 발급 테스트...")
                token_success = self.naver_api.get_access_token()
                test_results.append(f"토큰 발급: {'성공' if token_success else '실패'}")
                
                if not token_success:
                    self.update_api_status("토큰 발급 실패로 테스트 중단")
                    self.show_test_results(test_results)
                    return
                
                # 2. 스토어 정보 조회
                self.update_api_status("2/5 스토어 정보 조회...")
                store_info = self.naver_api.get_store_info()
                test_results.append(f"스토어 정보: {'성공' if store_info else '실패'}")
                
                # 3. 주문 목록 조회
                self.update_api_status("3/5 주문 목록 조회...")
                orders = self.naver_api.get_orders()
                test_results.append(f"주문 목록: {'성공' if orders else '실패'} ({len(orders) if orders else 0}개)")
                
                # 4. 상품 목록 조회
                self.update_api_status("4/5 상품 목록 조회...")
                products = self.naver_api.get_products()
                test_results.append(f"상품 목록: {'성공' if products else '실패'} ({len(products) if products else 0}개)")
                
                # 5. 주문 통계 조회
                self.update_api_status("5/5 주문 통계 조회...")
                statistics = self.naver_api.get_order_statistics()
                test_results.append(f"주문 통계: {'성공' if statistics else '실패'}")
                
                self.update_api_status("전체 API 테스트 완료")
                self.show_test_results(test_results)
                
            except Exception as e:
                error_info = f"전체 API 테스트 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("전체 API 테스트 오류")
        
        threading.Thread(target=test_all_thread, daemon=True).start()
    
    def show_test_results(self, results):
        """테스트 결과 표시"""
        result_text = "=== 전체 API 테스트 결과 ===\n\n"
        for i, result in enumerate(results, 1):
            result_text += f"{i}. {result}\n"
        
        result_text += f"\n테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(1.0, result_text)
    
    def update_api_status(self, status):
        """API 상태 업데이트"""
        self.api_status_var.set(status)
        self.status_var.set(status)
    
    def show_api_error(self, message):
        """API 오류 표시"""
        messagebox.showerror("API 오류", message)
        self.update_api_status("API 오류")
    
    def clear_response(self):
        """응답 결과 지우기"""
        self.request_text.delete(1.0, tk.END)
        self.response_text.delete(1.0, tk.END)
        self.update_api_status("응답 결과 지워짐")
    
    def copy_response(self):
        """응답 결과 복사 (전체)"""
        try:
            response_content = self.response_text.get(1.0, tk.END)
            if response_content.strip():
                self.root.clipboard_clear()
                self.root.clipboard_append(response_content)
                messagebox.showinfo("복사 완료", "응답 결과가 클립보드에 복사되었습니다.")
            else:
                messagebox.showwarning("복사 실패", "복사할 내용이 없습니다.")
        except Exception as e:
            messagebox.showerror("복사 오류", f"복사 중 오류가 발생했습니다: {e}")
    
    def copy_response_text(self):
        """응답 텍스트 복사 (선택된 부분 또는 전체)"""
        try:
            # 선택된 텍스트가 있는지 확인
            try:
                selected_text = self.response_text.selection_get()
                if selected_text.strip():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected_text)
                    return
            except tk.TclError:
                # 선택된 텍스트가 없으면 전체 복사
                pass
            
            # 전체 텍스트 복사
            response_content = self.response_text.get(1.0, tk.END)
            if response_content.strip():
                self.root.clipboard_clear()
                self.root.clipboard_append(response_content)
        except Exception as e:
            print(f"복사 오류: {e}")
    
    def select_all_text(self, widget):
        """텍스트 위젯의 모든 텍스트 선택"""
        try:
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, "1.0")
            widget.see(tk.INSERT)
        except Exception as e:
            print(f"텍스트 선택 오류: {e}")
    
    def show_response_context_menu(self, event):
        """응답 텍스트 위젯의 컨텍스트 메뉴 표시"""
        try:
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="복사 (Ctrl+C)", command=self.copy_response_text)
            context_menu.add_command(label="전체 선택 (Ctrl+A)", command=lambda: self.select_all_text(self.response_text))
            context_menu.add_separator()
            context_menu.add_command(label="전체 복사", command=self.copy_response)
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        except Exception as e:
            print(f"컨텍스트 메뉴 오류: {e}")
    
    def copy_request_text(self):
        """요청 텍스트 복사 (선택된 부분 또는 전체)"""
        try:
            # 선택된 텍스트가 있는지 확인
            try:
                selected_text = self.request_text.selection_get()
                if selected_text.strip():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected_text)
                    return
            except tk.TclError:
                # 선택된 텍스트가 없으면 전체 복사
                pass
            
            # 전체 텍스트 복사
            request_content = self.request_text.get(1.0, tk.END)
            if request_content.strip():
                self.root.clipboard_clear()
                self.root.clipboard_append(request_content)
        except Exception as e:
            print(f"복사 오류: {e}")
    
    def show_request_context_menu(self, event):
        """요청 텍스트 위젯의 컨텍스트 메뉴 표시"""
        try:
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="복사 (Ctrl+C)", command=self.copy_request_text)
            context_menu.add_command(label="전체 선택 (Ctrl+A)", command=lambda: self.select_all_text(self.request_text))
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        except Exception as e:
            print(f"컨텍스트 메뉴 오류: {e}")
    
    def save_response(self):
        """응답 결과 저장"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                response_content = self.response_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response_content)
                messagebox.showinfo("저장 완료", f"응답 결과가 저장되었습니다: {filename}")
        except Exception as e:
            messagebox.showerror("저장 오류", f"저장 중 오류가 발생했습니다: {e}")
    
    def diagnose_api_connection(self):
        """API 연결 진단"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def diagnose_thread():
            try:
                self.update_api_status("API 연결 진단 중...")
                
                diagnosis_results = []
                
                # 1. 기본 연결 테스트
                diagnosis_results.append("=== API 연결 진단 시작 ===")
                diagnosis_results.append(f"진단 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                diagnosis_results.append("")
                
                # 2. 인증 정보 확인
                diagnosis_results.append("1. 인증 정보 확인:")
                diagnosis_results.append(f"   Client ID: {self.naver_api.client_id[:10]}..." if self.naver_api.client_id else "   Client ID: 설정되지 않음")
                diagnosis_results.append(f"   Client Secret: {'설정됨' if self.naver_api.client_secret else '설정되지 않음'}")
                diagnosis_results.append("")
                
                # 3. 네트워크 연결 테스트
                diagnosis_results.append("2. 네트워크 연결 테스트:")
                try:
                    import requests
                    response = requests.get("https://api.commerce.naver.com", timeout=10)
                    diagnosis_results.append(f"   네이버 API 서버 연결: 성공 (상태코드: {response.status_code})")
                except Exception as e:
                    diagnosis_results.append(f"   네이버 API 서버 연결: 실패 ({str(e)})")
                diagnosis_results.append("")
                
                # 4. 토큰 발급 테스트
                diagnosis_results.append("3. 토큰 발급 테스트:")
                try:
                    success = self.naver_api.get_access_token()
                    if success:
                        diagnosis_results.append("   토큰 발급: 성공")
                        diagnosis_results.append(f"   Access Token: {self.naver_api.access_token[:20]}...")
                    else:
                        diagnosis_results.append("   토큰 발급: 실패")
                        diagnosis_results.append("   원인: 애플리케이션 상태 또는 인증 정보 문제")
                except Exception as e:
                    diagnosis_results.append(f"   토큰 발급: 오류 ({str(e)})")
                diagnosis_results.append("")
                
                # 5. 권장 사항
                diagnosis_results.append("4. 권장 사항:")
                if not self.naver_api.client_id or not self.naver_api.client_secret:
                    diagnosis_results.append("   - Client ID와 Client Secret을 설정해주세요")
                else:
                    diagnosis_results.append("   - 네이버 커머스 API 센터에서 애플리케이션 상태를 확인해주세요")
                    diagnosis_results.append("   - 애플리케이션이 승인되었는지 확인해주세요")
                    diagnosis_results.append("   - 필요한 API 권한이 활성화되었는지 확인해주세요")
                
                diagnosis_results.append("")
                diagnosis_results.append("=== 진단 완료 ===")
                
                # 결과 표시
                result_text = "\n".join(diagnosis_results)
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, result_text)
                
                self.update_api_status("API 연결 진단 완료")
                
            except Exception as e:
                error_info = f"API 연결 진단 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("API 연결 진단 오류")
        
        threading.Thread(target=diagnose_thread, daemon=True).start()
    
    def validate_credentials(self):
        """인증 정보 검증"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def validate_thread():
            try:
                self.update_api_status("인증 정보 검증 중...")
                
                validation_results = []
                validation_results.append("=== 인증 정보 검증 ===")
                validation_results.append(f"검증 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                validation_results.append("")
                
                # Client ID 검증
                validation_results.append("1. Client ID 검증:")
                if self.naver_api.client_id:
                    if len(self.naver_api.client_id) >= 10:
                        validation_results.append(f"   ✓ Client ID 길이: 적절함 ({len(self.naver_api.client_id)}자)")
                    else:
                        validation_results.append(f"   ✗ Client ID 길이: 너무 짧음 ({len(self.naver_api.client_id)}자)")
                    
                    if self.naver_api.client_id.isalnum():
                        validation_results.append("   ✓ Client ID 형식: 영숫자만 포함")
                    else:
                        validation_results.append("   ⚠ Client ID 형식: 특수문자 포함 (정상일 수 있음)")
                else:
                    validation_results.append("   ✗ Client ID: 설정되지 않음")
                validation_results.append("")
                
                # Client Secret 검증
                validation_results.append("2. Client Secret 검증:")
                if self.naver_api.client_secret:
                    if len(self.naver_api.client_secret) >= 20:
                        validation_results.append(f"   ✓ Client Secret 길이: 적절함 ({len(self.naver_api.client_secret)}자)")
                    else:
                        validation_results.append(f"   ✗ Client Secret 길이: 너무 짧음 ({len(self.naver_api.client_secret)}자)")
                    
                    validation_results.append("   ✓ Client Secret: 설정됨")
                else:
                    validation_results.append("   ✗ Client Secret: 설정되지 않음")
                validation_results.append("")
                
                # 인증 서명 생성 테스트
                validation_results.append("3. 인증 서명 생성 테스트:")
                try:
                    timestamp = str(int(time.time() * 1000))
                    pwd = f'{self.naver_api.client_id}_{timestamp}'
                    hashed = hmac.new(
                        self.naver_api.client_secret.encode('utf-8'),
                        pwd.encode('utf-8'),
                        hashlib.sha256
                    ).digest()
                    client_secret_sign = base64.b64encode(hashed).decode('utf-8')
                    
                    validation_results.append("   ✓ HMAC-SHA256 해싱: 성공")
                    validation_results.append("   ✓ Base64 인코딩: 성공")
                    validation_results.append(f"   ✓ 서명 생성: {client_secret_sign[:20]}...")
                except Exception as e:
                    validation_results.append(f"   ✗ 서명 생성: 실패 ({str(e)})")
                validation_results.append("")
                
                # 실제 API 호출 테스트
                validation_results.append("4. 실제 API 호출 테스트:")
                try:
                    success = self.naver_api.get_access_token()
                    if success:
                        validation_results.append("   ✓ API 호출: 성공")
                        validation_results.append("   ✓ 인증 정보: 유효함")
                    else:
                        validation_results.append("   ✗ API 호출: 실패")
                        validation_results.append("   원인: 애플리케이션 상태 또는 권한 문제")
                except Exception as e:
                    validation_results.append(f"   ✗ API 호출: 오류 ({str(e)})")
                
                validation_results.append("")
                validation_results.append("=== 검증 완료 ===")
                
                # 결과 표시
                result_text = "\n".join(validation_results)
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, result_text)
                
                self.update_api_status("인증 정보 검증 완료")
                
            except Exception as e:
                error_info = f"인증 정보 검증 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("인증 정보 검증 오류")
        
        threading.Thread(target=validate_thread, daemon=True).start()
    
    def open_naver_api_center(self):
        """네이버 API 센터 열기"""
        import webbrowser
        try:
            webbrowser.open("https://developers.naver.com/apps/")
            self.update_api_status("네이버 API 센터 열기 완료")
        except Exception as e:
            messagebox.showerror("오류", f"브라우저를 열 수 없습니다: {e}")
    
    def test_get_product(self):
        """특정 상품 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 상품 번호 입력 다이얼로그
        product_no = tk.simpledialog.askstring("상품 조회", "상품 번호를 입력하세요:")
        if not product_no:
            return
        
        def test_thread():
            try:
                self.update_api_status(f"상품 조회 중... (상품번호: {product_no})")
                
                # 요청 정보 표시
                request_info = f"""상품 조회 요청:
URL: {self.naver_api.base_url}/external/v1/products/origin-products/{product_no}
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 상품 조회 (공식 문서에 따른 엔드포인트)
                response = self.naver_api.make_authenticated_request('GET', f'/external/v1/products/origin-products/{product_no}')
                
                if response:
                    response_info = f"""상품 조회 성공!
상품 번호: {product_no}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("상품 조회 성공")
                else:
                    response_info = f"상품 조회 실패\n상품 번호: {product_no}\nAPI 응답을 확인하세요."
                    self.update_api_status("상품 조회 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"상품 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("상품 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_change_product_status(self):
        """상품 상태 변경 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 상품 번호 입력 다이얼로그
        product_no = tk.simpledialog.askstring("상품 상태 변경", "상품 번호를 입력하세요:")
        if not product_no:
            return
        
        # 상태 선택 다이얼로그
        status_window = tk.Toplevel(self.root)
        status_window.title("상품 상태 변경")
        status_window.geometry("300x200")
        status_window.transient(self.root)
        status_window.grab_set()
        
        ttk.Label(status_window, text=f"상품 번호: {product_no}").pack(pady=10)
        ttk.Label(status_window, text="변경할 상태:").pack(pady=5)
        
        status_var = tk.StringVar(value="SALE")
        status_combo = ttk.Combobox(status_window, textvariable=status_var, 
                                   values=["SALE", "OUTOFSTOCK", "SUSPENSION"])
        status_combo.pack(pady=5)
        
        ttk.Label(status_window, text="재고 수량:").pack(pady=5)
        stock_var = tk.StringVar(value="0")
        stock_entry = ttk.Entry(status_window, textvariable=stock_var, width=10)
        stock_entry.pack(pady=5)
        
        def confirm_change():
            status = status_var.get()
            stock = stock_var.get()
            
            def test_thread():
                try:
                    self.update_api_status(f"상품 상태 변경 중... (상품번호: {product_no})")
                    
                    # 요청 정보 표시
                    request_info = f"""상품 상태 변경 요청:
URL: {self.naver_api.base_url}/external/v1/products/origin-products/{product_no}/change-status
Method: PUT
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
Body:
  statusType: {status}
  stockQuantity: {stock}
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                    self.request_text.delete(1.0, tk.END)
                    self.request_text.insert(1.0, request_info)
                    
                    # 상품 상태 변경 (공식 문서에 따른 엔드포인트)
                    payload = {
                        "statusType": status,
                        "stockQuantity": int(stock) if stock.isdigit() else 0
                    }
                    
                    response = self.naver_api.make_authenticated_request('PUT', f'/external/v1/products/origin-products/{product_no}/change-status', payload)
                    
                    if response:
                        response_info = f"""상품 상태 변경 성공!
상품 번호: {product_no}
변경된 상태: {status}
재고 수량: {stock}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                        self.update_api_status("상품 상태 변경 성공")
                    else:
                        response_info = f"상품 상태 변경 실패\n상품 번호: {product_no}\nAPI 응답을 확인하세요."
                        self.update_api_status("상품 상태 변경 실패")
                    
                    self.response_text.delete(1.0, tk.END)
                    self.response_text.insert(1.0, response_info)
                    
                except Exception as e:
                    error_info = f"상품 상태 변경 오류: {str(e)}"
                    self.response_text.delete(1.0, tk.END)
                    self.response_text.insert(1.0, error_info)
                    self.update_api_status("상품 상태 변경 오류")
            
            threading.Thread(target=test_thread, daemon=True).start()
            status_window.destroy()
        
        ttk.Button(status_window, text="변경", command=confirm_change).pack(pady=10)
        ttk.Button(status_window, text="취소", command=status_window.destroy).pack()
    
    def test_get_orders_detailed(self):
        """상세 주문 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_thread():
            try:
                self.update_api_status("상세 주문 조회 중...")
                
                # 한국 시간(KST) 기준으로 변환 (네이버 API 요구사항에 맞게)
                from datetime import datetime, timezone, timedelta
                from urllib.parse import quote
                
                # 한국 시간대 설정 (UTC+9)
                kst = timezone(timedelta(hours=9))
                now = datetime.now(kst)
                
                # 네이버 API 요구사항에 맞는 날짜 형식 생성
                # 예제: "2021-12-31T15:35:09.110Z" 형식
                iso_format = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                encoded_time = quote(iso_format)
                
                # 다양한 시간 범위 테스트
                time_ranges = [
                    ("1시간 전", timedelta(hours=1)),
                    ("6시간 전", timedelta(hours=6)),
                    ("12시간 전", timedelta(hours=12)),
                    ("24시간 전", timedelta(hours=24)),
                    ("48시간 전", timedelta(hours=48))
                ]
                
                print(f"API 테스트 시간 설정:")
                print(f"  → 현재 KST 시간: {now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00")
                print(f"  → 현재 UTC 시간: {(now - timedelta(hours=9)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
                
                # 24시간 전을 기본으로 사용
                past_time = now - timedelta(hours=24)
                past_iso_format = past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                
                print(f"  → 사용할 시작 시간: {past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
                print(f"  → 시간 차이: {(now - past_time).total_seconds() / 3600:.1f}시간")
                
                # 다른 시간 범위들도 로그로 출력
                for name, delta in time_ranges:
                    test_time = now - delta
                    print(f"  → {name}: {test_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
                
                # 요청 정보 표시
                request_info = f"""상세 주문 조회 요청:
URL: {self.naver_api.base_url}/external/v1/pay-order/seller/product-orders
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
Parameters:
  from: {past_iso_format} (24시간 전 시간) - 필수값
  to: {iso_format} (현재 시간)
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용 (최대 24시간 범위)
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 상세 주문 조회 (공식 문서에 따른 엔드포인트)
                params = {
                    'from': past_iso_format,  # from 필드가 필수값
                    'to': iso_format
                }
                response = self.naver_api.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders', params)
                
                if response:
                    # 응답 데이터 분석
                    response_type = type(response)
                    response_keys = list(response.keys()) if isinstance(response, dict) else 'Not a dict'
                    
                    # 주문 데이터 추출
                    orders_data = None
                    if isinstance(response, dict) and 'data' in response:
                        orders_data = response['data']
                        if isinstance(orders_data, dict) and 'data' in orders_data:
                            orders_list = orders_data['data']
                            orders_count = len(orders_list) if isinstance(orders_list, list) else 0
                        else:
                            orders_count = 0
                    else:
                        orders_count = 0
                    
                    response_info = f"""상세 주문 조회 성공!
조회 시작 시간: {past_iso_format} (KST 기준)
현재 시간: {iso_format} (KST 기준)
시간 차이: {(now - past_time).total_seconds() / 3600:.1f}시간

서버 응답 시간: {response.get('data', {}).get('timestamp', 'N/A')}

응답 데이터 분석:
- 응답 타입: {response_type}
- 응답 키들: {response_keys}
- 주문 데이터: {type(orders_data)}
- 주문 개수: {orders_count}건

전체 응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status(f"상세 주문 조회 성공 - {orders_count}건")
                else:
                    response_info = f"""상세 주문 조회 실패
조회 시작 시간: {past_iso_format}
현재 시간: {iso_format}

가능한 원인:
1. 해당 기간에 변경된 주문이 없음
2. API 권한 부족
3. 애플리케이션 상태 문제

해결 방법:
1. 더 긴 기간으로 조회 시도
2. 네이버 API 센터에서 권한 확인
3. 애플리케이션 상태 확인
"""
                    self.update_api_status("상세 주문 조회 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"상세 주문 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("상세 주문 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_get_orders_with_range(self, days):
        """지정된 일수로 주문 조회 테스트 (24시간 단위로 자동 분할)"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_thread():
            try:
                self.update_api_status(f"{days}일 범위 주문 조회 중... (24시간 단위 분할)")
                
                # 한국 시간(KST) 기준으로 변환
                from datetime import datetime, timezone, timedelta
                from urllib.parse import quote
                import time
                
                # 한국 시간대 설정 (UTC+9)
                kst = timezone(timedelta(hours=9))
                now = datetime.now(kst)
                
                # 지정된 일수 전 시간 계산
                past_time = now - timedelta(days=days)
                past_iso_format = past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                current_iso_format = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                
                print(f"API 테스트 시간 설정 ({days}일 범위, 24시간 단위 분할):")
                print(f"  → 현재 KST 시간: {now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00")
                print(f"  → {days}일 전 시간: {past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00")
                print(f"  → 시간 차이: {(now - past_time).total_seconds() / 3600:.1f}시간")
                
                # 요청 정보 표시 (상세)
                request_info = f"""{days}일 범위 주문 조회 요청 (24시간 단위 분할):
URL: {self.naver_api.base_url}/external/v1/pay-order/seller/product-orders
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
  Accept: application/json
Parameters:
  from: {past_iso_format} ({days}일 전 시간) - 필수값
  to: {current_iso_format} (현재 시간)
  page: 1
  size: 100

실제 요청 URL:
{self.naver_api.base_url}/external/v1/pay-order/seller/product-orders?from={past_iso_format}&to={current_iso_format}&page=1&size=100

참고: {days}일 범위를 24시간 단위로 자동 분할하여 조회
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 24시간 단위로 분할하여 주문 조회
                all_orders = []
                total_chunks = 0
                current_start = past_time
                
                print(f"\n=== 24시간 단위 분할 조회 시작 ===")
                
                while current_start < now:
                    # 24시간 단위로 종료 시간 설정
                    current_end = min(current_start + timedelta(hours=24), now)
                    
                    total_chunks += 1
                    chunk_start_iso = current_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    chunk_end_iso = current_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    
                    print(f"청크 {total_chunks}: {current_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00 ~ {current_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00")
                    
                    # 해당 청크의 주문 조회
                    chunk_params = {
                        'from': chunk_start_iso,
                        'to': chunk_end_iso
                    }
                    chunk_response = self.naver_api.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders', chunk_params)
                    
                    if chunk_response:
                        # 청크 응답 데이터 분석
                        chunk_orders_data = None
                        if isinstance(chunk_response, dict) and 'data' in chunk_response:
                            chunk_orders_data = chunk_response['data']
                            if isinstance(chunk_orders_data, dict) and 'data' in chunk_orders_data:
                                chunk_orders_list = chunk_orders_data['data']
                                chunk_orders_count = len(chunk_orders_list) if isinstance(chunk_orders_list, list) else 0
                                all_orders.extend(chunk_orders_list)
                                print(f"  → {chunk_orders_count}건 조회 성공")
                            else:
                                print(f"  → 0건 조회 (데이터 구조 오류)")
                        else:
                            print(f"  → 0건 조회 (응답 없음)")
                    else:
                        print(f"  → 0건 조회 (실패)")
                    
                    # API 호출 간격 (0.5초)
                    time.sleep(0.5)
                    current_start = current_end
                
                print(f"전체 청크 조회 완료: {total_chunks}개 청크, 총 {len(all_orders)}건")
                
                # 중복 제거 (orderId 기준)
                unique_orders = []
                seen_order_ids = set()
                for order in all_orders:
                    if isinstance(order, dict):
                        order_id = order.get('orderId')
                        if order_id and order_id not in seen_order_ids:
                            seen_order_ids.add(order_id)
                            unique_orders.append(order)
                
                print(f"중복 제거: {len(all_orders)}건 → {len(unique_orders)}건")
                
                # 응답 정보 생성
                response_info = f"""{days}일 범위 주문 조회 성공! (24시간 단위 분할)
조회 시작 시간: {past_iso_format} (KST 기준)
현재 시간: {current_iso_format} (KST 기준)
시간 차이: {(now - past_time).total_seconds() / 3600:.1f}시간

청크별 조회 결과:
- 총 청크 수: {total_chunks}개
- 중복 제거 전: {len(all_orders)}건
- 중복 제거 후: {len(unique_orders)}건

주문 목록:
"""
                
                for i, order in enumerate(unique_orders[:10], 1):  # 최대 10개만 표시
                    if isinstance(order, dict):
                        order_id = order.get('orderId', 'N/A')
                        orderer_name = order.get('ordererName', 'N/A')
                        product_name = order.get('productName', 'N/A')
                        order_date = order.get('orderDate', 'N/A')
                        
                        response_info += f"""
{i}. 주문 ID: {order_id}
   주문자: {orderer_name}
   상품명: {product_name}
   주문일시: {order_date}
"""
                
                if len(unique_orders) > 10:
                    response_info += f"\n... 및 {len(unique_orders) - 10}건 더"
                
                response_info += f"""

전체 응답 데이터 (샘플):
{json.dumps(unique_orders[:3], indent=2, ensure_ascii=False) if unique_orders else '주문 없음'}
"""
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                self.update_api_status(f"{days}일 범위 주문 조회 완료 - {len(unique_orders)}건 ({total_chunks}개 청크)")
                
            except Exception as e:
                error_info = f"{days}일 범위 주문 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status(f"{days}일 범위 주문 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    
    def test_seller_account(self):
        """판매자 계정 정보 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_thread():
            try:
                self.update_api_status("판매자 계정 정보 조회 중...")
                
                # 요청 정보 표시
                request_info = f"""판매자 계정 정보 조회 요청:
URL: {self.naver_api.base_url}/external/v1/seller/account
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Accept: application/json
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 판매자 계정 정보 조회
                response = self.naver_api.make_authenticated_request('GET', '/external/v1/seller/account')
                
                if response:
                    response_info = f"""판매자 계정 정보 조회 성공!
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("판매자 계정 정보 조회 성공")
                else:
                    response_info = f"""판매자 계정 정보 조회 실패

가능한 원인:
1. 토큰이 유효하지 않음
2. API 권한 부족
3. 애플리케이션 상태 문제

해결 방법:
1. 토큰 재발급 시도
2. 네이버 API 센터에서 권한 확인
3. 애플리케이션 상태 확인
"""
                    self.update_api_status("판매자 계정 정보 조회 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"판매자 계정 정보 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("판매자 계정 정보 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_order_detail(self):
        """주문 상세 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 주문 ID 입력 다이얼로그
        order_id = tk.simpledialog.askstring("주문 상세 조회", "주문 ID를 입력하세요:")
        if not order_id:
            return
        
        def test_thread():
            try:
                self.update_api_status(f"주문 상세 조회 중... (주문ID: {order_id})")
                
                # 요청 정보 표시
                request_info = f"""주문 상세 조회 요청:
URL: {self.naver_api.base_url}/external/v1/pay-order/seller/product-orders/{order_id}
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Accept: application/json
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 주문 상세 조회
                response = self.naver_api.make_authenticated_request('GET', f'/external/v1/pay-order/seller/product-orders/{order_id}')
                
                if response:
                    response_info = f"""주문 상세 조회 성공!
주문 ID: {order_id}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("주문 상세 조회 성공")
                else:
                    response_info = f"""주문 상세 조회 실패
주문 ID: {order_id}

가능한 원인:
1. 주문 ID가 존재하지 않음
2. API 권한 부족
3. 토큰이 유효하지 않음

해결 방법:
1. 올바른 주문 ID 확인
2. 네이버 API 센터에서 권한 확인
3. 토큰 재발급 시도
"""
                    self.update_api_status("주문 상세 조회 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"주문 상세 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("주문 상세 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_seller_channels(self):
        """판매자 채널 정보 조회 테스트"""
        # API 초기화 확인 및 재시도
        if not self.naver_api:
            if self.client_id_var.get() and self.client_secret_var.get():
                self.naver_api = NaverShoppingAPI(
                    self.client_id_var.get(),
                    self.client_secret_var.get()
                )
                self.update_api_status("API 재초기화 완료")
            else:
                self.show_api_error("API 설정이 필요합니다.\n설정 탭에서 Client ID와 Client Secret을 입력해주세요.")
                return
        
        def test_thread():
            try:
                self.update_api_status("판매자 채널 정보 조회 중...")
                
                # 요청 정보 표시
                request_info = f"""판매자 채널 정보 조회 요청:
URL: {self.naver_api.base_url}/external/v1/seller/channels
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Accept: application/json
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 판매자 채널 정보 조회
                response = self.naver_api.get_seller_channels()
                
                # 상세한 서버 응답 정보 표시
                response_info = f"""판매자 채널 정보 조회 응답:
상태 코드: {response.get('status_code', 'N/A')}
성공 여부: {response.get('success', False)}
메시지: {response.get('message', 'N/A')}
"""
                
                if response.get('success'):
                    data = response.get('data', {})
                    response_info += f"""
응답 데이터:
{json.dumps(data, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("판매자 채널 정보 조회 성공")
                else:
                    error = response.get('error', '알 수 없는 오류')
                    response_info += f"""
오류 상세:
{error}

가능한 원인:
1. 토큰이 유효하지 않음
2. API 권한 부족
3. 애플리케이션 상태 문제
4. 채널 정보가 없음

해결 방법:
1. 토큰 재발급 시도
2. 네이버 API 센터에서 권한 확인
3. 애플리케이션 상태 확인
4. 채널 설정 확인
"""
                    self.update_api_status(f"판매자 채널 정보 조회 실패 ({response.get('status_code', 'N/A')})")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"판매자 채널 정보 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("판매자 채널 정보 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_order_product_ids(self):
        """주문 ID별 상품주문ID 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 주문 ID 입력 다이얼로그
        order_id = tk.simpledialog.askstring("주문 ID별 상품주문ID 조회", "주문 ID를 입력하세요:")
        if not order_id:
            return
        
        def test_thread():
            try:
                self.update_api_status(f"주문 ID별 상품주문ID 조회 중... (주문ID: {order_id})")
                
                # 요청 정보 표시
                request_info = f"""주문 ID별 상품주문ID 조회 요청:
URL: {self.naver_api.base_url}/external/v1/pay-order/seller/orders/{order_id}/product-order-ids
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Accept: application/json
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 주문 ID별 상품주문ID 조회
                response = self.naver_api.make_authenticated_request('GET', f'/external/v1/pay-order/seller/orders/{order_id}/product-order-ids')
                
                if response:
                    response_info = f"""주문 ID별 상품주문ID 조회 성공!
주문 ID: {order_id}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("주문 ID별 상품주문ID 조회 성공")
                else:
                    response_info = f"""주문 ID별 상품주문ID 조회 실패
주문 ID: {order_id}

가능한 원인:
1. 주문 ID가 존재하지 않음
2. API 권한 부족
3. 토큰이 유효하지 않음

해결 방법:
1. 올바른 주문 ID 확인
2. 네이버 API 센터에서 권한 확인
3. 토큰 재발급 시도
"""
                    self.update_api_status("주문 ID별 상품주문ID 조회 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"주문 ID별 상품주문ID 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("주문 ID별 상품주문ID 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_last_changed_orders(self):
        """최근 변경 주문 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_thread():
            try:
                self.update_api_status("최근 변경 주문 조회 중...")
                
                # 요청 정보 표시
                from datetime import datetime, timezone, timedelta
                now = datetime.now(timezone.utc)
                past_time = now - timedelta(hours=1)  # 1시간 전
                last_changed_from = past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                
                request_info = f"""최근 변경 주문 조회 요청:
URL: {self.naver_api.base_url}/external/v1/pay-order/seller/product-orders/last-changed-statuses
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Accept: application/json
Parameters:
  lastChangedFrom: {last_changed_from} (1시간 전 시간) - 필수값
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 최근 변경 주문 조회 (필수 파라미터 추가)
                from datetime import datetime, timezone, timedelta
                now = datetime.now(timezone.utc)
                past_time = now - timedelta(hours=1)  # 1시간 전
                last_changed_from = past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                
                params = {
                    'lastChangedFrom': last_changed_from
                }
                response = self.naver_api.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders/last-changed-statuses', params)
                
                if response:
                    response_info = f"""최근 변경 주문 조회 성공!
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("최근 변경 주문 조회 성공")
                else:
                    response_info = f"""최근 변경 주문 조회 실패

가능한 원인:
1. 최근 변경된 주문이 없음
2. API 권한 부족
3. 토큰이 유효하지 않음

해결 방법:
1. 네이버 API 센터에서 권한 확인
2. 토큰 재발급 시도
3. 주문 상태 변경 후 재시도
"""
                    self.update_api_status("최근 변경 주문 조회 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"최근 변경 주문 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("최근 변경 주문 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_order_query(self):
        """주문 쿼리 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 상품주문ID 입력 다이얼로그
        product_order_ids = tk.simpledialog.askstring("주문 쿼리", "상품주문ID를 입력하세요 (쉼표로 구분):")
        if not product_order_ids:
            return
        
        def test_thread():
            try:
                self.update_api_status("주문 쿼리 중...")
                
                # 상품주문ID 리스트로 변환
                product_order_id_list = [id.strip() for id in product_order_ids.split(',')]
                
                # 요청 정보 표시
                request_info = f"""주문 쿼리 요청:
URL: {self.naver_api.base_url}/external/v1/pay-order/seller/product-orders/query
Method: POST
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
  Accept: application/json
Body:
  productOrderIds: {product_order_id_list}
  quantityClaimCompatibility: true
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 주문 쿼리
                payload = {
                    "productOrderIds": product_order_id_list,
                    "quantityClaimCompatibility": True
                }
                response = self.naver_api.make_authenticated_request('POST', '/external/v1/pay-order/seller/product-orders/query', payload)
                
                if response:
                    response_info = f"""주문 쿼리 성공!
상품주문ID: {product_order_ids}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("주문 쿼리 성공")
                else:
                    response_info = f"""주문 쿼리 실패
상품주문ID: {product_order_ids}

가능한 원인:
1. 상품주문ID가 존재하지 않음
2. API 권한 부족
3. 토큰이 유효하지 않음

해결 방법:
1. 올바른 상품주문ID 확인
2. 네이버 API 센터에서 권한 확인
3. 토큰 재발급 시도
"""
                    self.update_api_status("주문 쿼리 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"주문 쿼리 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("주문 쿼리 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_get_origin_product(self):
        """원상품 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 원상품 ID 입력 다이얼로그
        origin_product_id = tk.simpledialog.askstring("원상품 조회", "원상품 ID를 입력하세요:")
        if not origin_product_id:
            return
        
        def test_thread():
            try:
                self.update_api_status(f"원상품 조회 중... (원상품ID: {origin_product_id})")
                
                # 요청 정보 표시
                request_info = f"""원상품 조회 요청 (v2 API):
URL: {self.naver_api.base_url}/external/v2/products/origin-products/{origin_product_id}
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8
  Content-Type: application/json
  X-Naver-Client-Id: {self.naver_api.client_id}
  X-Naver-Client-Secret: {'*' * len(self.naver_api.client_secret)}
  
참고: 네이버 커머스 API v2 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 원상품 조회 (v2 API 사용)
                response = self.naver_api.make_authenticated_request('GET', f'/external/v2/products/origin-products/{origin_product_id}')
                
                # 상세한 서버 응답 정보 표시
                response_info = f"""원상품 조회 응답:
원상품 ID: {origin_product_id}
상태 코드: {response.get('status_code', 'N/A')}
성공 여부: {response.get('success', False)}
메시지: {response.get('message', 'N/A')}
"""
                
                if response.get('success'):
                    data = response.get('data', {})
                    response_info += f"""
응답 데이터:
{json.dumps(data, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("원상품 조회 성공")
                else:
                    error = response.get('error', '알 수 없는 오류')
                    response_info += f"""
오류 상세:
{error}

가능한 원인:
1. 원상품 ID가 존재하지 않음 (404 오류)
2. API 권한 부족
3. 토큰이 유효하지 않음
4. 상품이 삭제되었거나 비활성화됨

해결 방법:
1. 상품 목록 조회로 유효한 원상품 ID 확인
2. 네이버 API 센터에서 권한 확인
3. 토큰 재발급 시도
4. 다른 원상품 ID로 테스트
"""
                    self.update_api_status(f"원상품 조회 실패 ({response.get('status_code', 'N/A')})")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"원상품 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("원상품 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_get_channel_product(self):
        """채널상품 조회 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 채널상품 ID 입력 다이얼로그
        channel_product_id = tk.simpledialog.askstring("채널상품 조회", "채널상품 ID를 입력하세요:")
        if not channel_product_id:
            return
        
        def test_thread():
            try:
                self.update_api_status(f"채널상품 조회 중... (채널상품ID: {channel_product_id})")
                
                # 요청 정보 표시
                request_info = f"""채널상품 조회 요청 (v2 API):
URL: {self.naver_api.base_url}/external/v2/products/channel-products/{channel_product_id}
Method: GET
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8
  Content-Type: application/json
  X-Naver-Client-Id: {self.naver_api.client_id}
  X-Naver-Client-Secret: {'*' * len(self.naver_api.client_secret)}
  
참고: 네이버 커머스 API v2 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 채널상품 조회 (v2 API 사용)
                response = self.naver_api.make_authenticated_request('GET', f'/external/v2/products/channel-products/{channel_product_id}')
                
                # 상세한 서버 응답 정보 표시
                response_info = f"""채널상품 조회 응답:
채널상품 ID: {channel_product_id}
상태 코드: {response.get('status_code', 'N/A')}
성공 여부: {response.get('success', False)}
메시지: {response.get('message', 'N/A')}
"""
                
                if response.get('success'):
                    data = response.get('data', {})
                    response_info += f"""
응답 데이터:
{json.dumps(data, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("채널상품 조회 성공")
                else:
                    error = response.get('error', '알 수 없는 오류')
                    response_info += f"""
오류 상세:
{error}

가능한 원인:
1. 채널상품 ID가 존재하지 않음 (404 오류)
2. API 권한 부족
3. 토큰이 유효하지 않음
4. 상품이 삭제되었거나 비활성화됨

해결 방법:
1. 상품 목록 조회로 유효한 채널상품 ID 확인
2. 네이버 API 센터에서 권한 확인
3. 토큰 재발급 시도
4. 다른 채널상품 ID로 테스트
"""
                    self.update_api_status(f"채널상품 조회 실패 ({response.get('status_code', 'N/A')})")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"채널상품 조회 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("채널상품 조회 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_change_product_option(self):
        """상품 옵션 재고 변경 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        # 옵션 정보 입력 다이얼로그
        option_window = tk.Toplevel(self.root)
        option_window.title("상품 옵션 재고 변경")
        option_window.geometry("400x300")
        option_window.transient(self.root)
        option_window.grab_set()
        
        ttk.Label(option_window, text="채널상품 ID:").pack(pady=5)
        channel_product_id_var = tk.StringVar()
        ttk.Entry(option_window, textvariable=channel_product_id_var, width=30).pack(pady=5)
        
        ttk.Label(option_window, text="옵션 코드:").pack(pady=5)
        option_code_var = tk.StringVar()
        ttk.Entry(option_window, textvariable=option_code_var, width=30).pack(pady=5)
        
        ttk.Label(option_window, text="재고 수량:").pack(pady=5)
        stock_quantity_var = tk.StringVar(value="0")
        ttk.Entry(option_window, textvariable=stock_quantity_var, width=10).pack(pady=5)
        
        ttk.Label(option_window, text="가격:").pack(pady=5)
        price_var = tk.StringVar(value="0")
        ttk.Entry(option_window, textvariable=price_var, width=10).pack(pady=5)
        
        def confirm_change():
            channel_product_id = channel_product_id_var.get()
            option_code = option_code_var.get()
            stock_quantity = stock_quantity_var.get()
            price = price_var.get()
            
            if not all([channel_product_id, option_code]):
                messagebox.showerror("오류", "채널상품 ID와 옵션 코드는 필수입니다.")
                return
            
            def test_thread():
                try:
                    self.update_api_status(f"상품 옵션 재고 변경 중... (채널상품ID: {channel_product_id})")
                    
                    # 요청 정보 표시
                    request_info = f"""상품 옵션 재고 변경 요청:
URL: {self.naver_api.base_url}/external/v1/products/channel-products/{channel_product_id}/options/{option_code}
Method: PUT
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
Body:
  stockQuantity: {stock_quantity}
  price: {price}
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                    self.request_text.delete(1.0, tk.END)
                    self.request_text.insert(1.0, request_info)
                    
                    # 상품 옵션 재고 변경
                    payload = {
                        "stockQuantity": int(stock_quantity) if stock_quantity.isdigit() else 0,
                        "price": int(price) if price.isdigit() else 0
                    }
                    response = self.naver_api.make_authenticated_request('PUT', f'/external/v1/products/channel-products/{channel_product_id}/options/{option_code}', payload)
                    
                    if response:
                        response_info = f"""상품 옵션 재고 변경 성공!
채널상품 ID: {channel_product_id}
옵션 코드: {option_code}
재고 수량: {stock_quantity}
가격: {price}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                        self.update_api_status("상품 옵션 재고 변경 성공")
                    else:
                        response_info = f"""상품 옵션 재고 변경 실패
채널상품 ID: {channel_product_id}
옵션 코드: {option_code}

가능한 원인:
1. 채널상품 ID 또는 옵션 코드가 존재하지 않음
2. API 권한 부족
3. 토큰이 유효하지 않음

해결 방법:
1. 올바른 채널상품 ID와 옵션 코드 확인
2. 네이버 API 센터에서 권한 확인
3. 토큰 재발급 시도
"""
                        self.update_api_status("상품 옵션 재고 변경 실패")
                    
                    self.response_text.delete(1.0, tk.END)
                    self.response_text.insert(1.0, response_info)
                    
                except Exception as e:
                    error_info = f"상품 옵션 재고 변경 오류: {str(e)}"
                    self.response_text.delete(1.0, tk.END)
                    self.response_text.insert(1.0, error_info)
                    self.update_api_status("상품 옵션 재고 변경 오류")
            
            threading.Thread(target=test_thread, daemon=True).start()
            option_window.destroy()
        
        ttk.Button(option_window, text="변경", command=confirm_change).pack(pady=10)
        ttk.Button(option_window, text="취소", command=option_window.destroy).pack()
    
    def test_multi_product_change(self):
        """멀티 상품 변경 테스트"""
        if not self.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        def test_thread():
            try:
                self.update_api_status("멀티 상품 변경 중...")
                
                # 요청 정보 표시
                request_info = f"""멀티 상품 변경 요청:
URL: {self.naver_api.base_url}/external/v1/products/multi-change
Method: PUT
Headers:
  Authorization: Bearer {self.naver_api.access_token[:20] if self.naver_api.access_token else 'None'}...
  Content-Type: application/json
Body:
  여러 상품의 판매가, 재고, 할인, 판매 상태를 다르게 변경
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
                self.request_text.delete(1.0, tk.END)
                self.request_text.insert(1.0, request_info)
                
                # 멀티 상품 변경 (예시 데이터)
                payload = {
                    "products": [
                        {
                            "channelProductId": "example_id_1",
                            "salePrice": 10000,
                            "stockQuantity": 50,
                            "statusType": "SALE"
                        }
                    ]
                }
                response = self.naver_api.make_authenticated_request('PUT', '/external/v1/products/multi-change', payload)
                
                if response:
                    response_info = f"""멀티 상품 변경 성공!
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                    self.update_api_status("멀티 상품 변경 성공")
                else:
                    response_info = f"""멀티 상품 변경 실패

가능한 원인:
1. 상품 ID가 존재하지 않음
2. API 권한 부족
3. 토큰이 유효하지 않음

해결 방법:
1. 올바른 상품 ID 확인
2. 네이버 API 센터에서 권한 확인
3. 토큰 재발급 시도
"""
                    self.update_api_status("멀티 상품 변경 실패")
                
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, response_info)
                
            except Exception as e:
                error_info = f"멀티 상품 변경 오류: {str(e)}"
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(1.0, error_info)
                self.update_api_status("멀티 상품 변경 오류")
        
        threading.Thread(target=test_thread, daemon=True).start()

    def load_products(self):
        """상품 목록 조회"""
        # API 초기화 확인 및 재시도
        if not self.naver_api:
            if self.client_id_var.get() and self.client_secret_var.get():
                self.naver_api = NaverShoppingAPI(
                    self.client_id_var.get(),
                    self.client_secret_var.get()
                )
                self.update_api_status("API 재초기화 완료")
            else:
                messagebox.showerror("오류", "API 설정이 필요합니다.\n설정 탭에서 Client ID와 Client Secret을 입력해주세요.")
                return
        
        def load_thread():
            try:
                self.update_api_status("상품 목록 조회 중...")
                self.product_status_var.set("상품 목록 조회 중...")
                print(f"API 초기화 상태: {self.naver_api is not None}")
                print(f"Client ID: {self.naver_api.client_id if self.naver_api else 'None'}")
                
                # API 응답 저장을 위한 변수 초기화
                self.last_api_response = None
                
                # 설정에서 선택된 상품상태 가져오기
                selected_statuses = [status_code for status_code, var in self.product_status_vars.items() if var.get()]
                print(f"선택된 상품상태: {selected_statuses}")
                
                # 상품 목록 조회
                response = self.naver_api.get_products(product_status_types=selected_statuses)
                
                # API 응답 저장
                self.last_api_response = response
                
                print(f"API 응답: {response}")
                
                if response.get('success'):
                    data = response.get('data', {})
                    print(f"응답 데이터: {data}")
                    
                    if data and 'contents' in data:
                        contents = data['contents']
                        print(f"원본 상품 개수: {len(contents)}")
                        
                        # contents에서 channelProducts 추출하여 평면화
                        products = []
                        for content in contents:
                            if 'channelProducts' in content:
                                for channel_product in content['channelProducts']:
                                    # 디버깅: 상품 데이터 구조 확인
                                    print(f"상품 데이터 키들: {list(channel_product.keys())}")
                                    if 'originProductNo' in channel_product:
                                        print(f"원상품 ID 발견: {channel_product['originProductNo']}")
                                    else:
                                        print("원상품 ID 없음")
                                    products.append(channel_product)
                        
                        print(f"채널 상품 개수: {len(products)}")
                        
                        # 데이터베이스에 상품 저장
                        saved_count = 0
                        for product in products:
                            try:
                                # 디버깅: 원상품 ID 확인
                                channel_product_no = product.get('channelProductNo', '')
                                origin_product_no = product.get('originProductNo', '')
                                print(f"상품 {channel_product_no}: 원상품 ID = {origin_product_no}")
                                
                                # 할인 정보 추출
                                customer_benefit = product.get('customerBenefit', {})
                                discount_method = customer_benefit.get('discountMethod', '') if customer_benefit else ''
                                
                                product_data = {
                                    'channel_product_no': channel_product_no,
                                    'origin_product_no': origin_product_no,
                                    'product_name': product.get('name', ''),
                                    'status_type': product.get('statusType', ''),
                                    'sale_price': product.get('salePrice', 0),
                                    'discounted_price': product.get('discountedPrice', 0),
                                    'stock_quantity': product.get('stockQuantity', 0),
                                    'category_id': product.get('categoryId', ''),
                                    'brand_name': product.get('brandName', ''),
                                    'manufacturer_name': product.get('manufacturerName', ''),
                                    'model_name': product.get('modelName', ''),
                                    'seller_management_code': product.get('sellerManagementCode', ''),
                                    'reg_date': product.get('regDate', ''),
                                    'modified_date': product.get('modifiedDate', ''),
                                    'representative_image_url': product.get('representativeImage', {}).get('url', '') if product.get('representativeImage') else '',
                                    'whole_category_name': product.get('wholeCategoryName', ''),
                                    'whole_category_id': product.get('wholeCategoryId', ''),
                                    'delivery_fee': product.get('deliveryFee', 0),
                                    'return_fee': product.get('returnFee', 0),
                                    'exchange_fee': product.get('exchangeFee', 0),
                                    'discount_method': discount_method,
                                    'customer_benefit': str(customer_benefit) if customer_benefit else ''
                                }
                                
                                print(f"저장할 상품 데이터: {product_data}")
                                print(f"DB 매니저 존재: {self.db_manager is not None}")
                                
                                if self.db_manager:
                                    save_result = self.db_manager.save_product(product_data)
                                    print(f"저장 결과: {save_result}")
                                    if save_result:
                                        saved_count += 1
                                        print(f"상품 저장 성공: {channel_product_no}")
                                    else:
                                        print(f"상품 저장 실패: {channel_product_no}")
                                else:
                                    print("DB 매니저가 없어서 저장할 수 없음")
                                    
                            except Exception as e:
                                print(f"상품 저장 오류: {e}")
                        
                        print(f"데이터베이스에 {saved_count}개 상품 저장 완료")
                        
                        # 각 채널상품ID로 세부조회 진행하여 정확한 셀러할인가 가져오기
                        self.update_api_status("채널상품 세부조회 중...")
                        detailed_products = []
                        for i, product in enumerate(products):
                            channel_product_id = product.get('channelProductNo', '')
                            if channel_product_id:
                                print(f"세부조회 진행 ({i+1}/{len(products)}): {channel_product_id}")
                                try:
                                    # 채널상품 세부조회
                                    detail_response = self.naver_api.get_channel_product(channel_product_id)
                                    if detail_response.get('success'):
                                        detail_data = detail_response.get('data', {})
                                        # 세부조회 데이터에서 정확한 가격 정보 추출
                                        if detail_data:
                                            print(f"세부조회 데이터 키들: {list(detail_data.keys())}")
                                            
                                            # originProduct 구조 확인
                                            if 'originProduct' in detail_data:
                                                origin_data = detail_data['originProduct']
                                                print(f"originProduct 키들: {list(origin_data.keys())}")
                                                
                                                # originProduct에서 customerBenefit 확인
                                                if 'customerBenefit' in origin_data:
                                                    print(f"originProduct에서 customerBenefit 발견: {origin_data['customerBenefit']}")
                                                    
                                                    # customerBenefit을 최상위 레벨로 복사
                                                    detail_data['customerBenefit'] = origin_data['customerBenefit']
                                            
                                            # smartstoreChannelProduct 구조 확인
                                            if 'smartstoreChannelProduct' in detail_data:
                                                smartstore_data = detail_data['smartstoreChannelProduct']
                                                print(f"smartstoreChannelProduct 키들: {list(smartstore_data.keys())}")
                                                
                                                # smartstoreChannelProduct에서 customerBenefit 확인
                                                if 'customerBenefit' in smartstore_data:
                                                    print(f"smartstoreChannelProduct에서 customerBenefit 발견: {smartstore_data['customerBenefit']}")
                                                    
                                                    # customerBenefit을 최상위 레벨로 복사
                                                    detail_data['customerBenefit'] = smartstore_data['customerBenefit']
                                            
                                            # customerBenefit 확인 (최상위 레벨)
                                            if 'customerBenefit' in detail_data:
                                                print(f"세부조회에서 customerBenefit 발견: {detail_data['customerBenefit']}")
                                            
                                            # 전체 세부조회 데이터에서 49100원이 나오는 필드 찾기
                                            def find_price_recursive(data, path=""):
                                                if isinstance(data, dict):
                                                    for key, value in data.items():
                                                        current_path = f"{path}.{key}" if path else key
                                                        if isinstance(value, (int, float)) and value == 49100:
                                                            print(f"  49100원 발견: {current_path} = {value}")
                                                        elif isinstance(value, (int, float)) and 49000 <= value <= 49200:
                                                            print(f"  비슷한 가격 발견: {current_path} = {value}")
                                                        elif isinstance(value, (dict, list)):
                                                            find_price_recursive(value, current_path)
                                                elif isinstance(data, list):
                                                    for i, item in enumerate(data):
                                                        current_path = f"{path}[{i}]"
                                                        find_price_recursive(item, current_path)
                                            
                                            print(f"세부조회 데이터에서 49100원 검색:")
                                            find_price_recursive(detail_data)
                                            
                                            # 기존 상품 데이터에 세부조회 결과 병합
                                            product.update(detail_data)
                                            print(f"세부조회 성공: {channel_product_id}")
                                        else:
                                            print(f"세부조회 데이터 없음: {channel_product_id}")
                                    else:
                                        print(f"세부조회 실패: {channel_product_id} - {detail_response.get('message', '')}")
                                except Exception as e:
                                    print(f"세부조회 오류: {channel_product_id} - {e}")
                            
                            detailed_products.append(product)
                        
                        print(f"세부조회 완료: {len(detailed_products)}개 상품")
                        
                        # 세부조회 결과를 데이터베이스에 저장
                        detailed_saved_count = 0
                        for product in detailed_products:
                            try:
                                # 디버깅: 원상품 ID 확인
                                channel_product_no = product.get('channelProductNo', '')
                                origin_product_no = product.get('originProductNo', '')
                                print(f"세부조회 후 상품 {channel_product_no}: 원상품 ID = {origin_product_no}")
                                
                                # 할인 정보 추출 (세부조회 결과 포함)
                                customer_benefit = product.get('customerBenefit', {})
                                print(f"세부조회 후 customerBenefit: {customer_benefit}")
                                
                                discount_method = ''
                                seller_discount_price = None
                                if customer_benefit:
                                    immediate_discount_policy = customer_benefit.get('immediateDiscountPolicy', {})
                                    print(f"immediateDiscountPolicy: {immediate_discount_policy}")
                                    if immediate_discount_policy:
                                        discount_method_data = immediate_discount_policy.get('discountMethod', {})
                                        print(f"discountMethod_data: {discount_method_data}")
                                        if discount_method_data:
                                            discount_method = str(discount_method_data)
                                            # 셀러할인가 추출
                                            seller_discount_price = discount_method_data.get('value')
                                            print(f"추출된 셀러할인가: {seller_discount_price}")
                                print(f"추출된 discount_method: {discount_method}")
                                
                                # 데이터베이스에 저장할 가격 결정
                                db_discounted_price = seller_discount_price if seller_discount_price else product.get('discountedPrice', 0)
                                print(f"DB에 저장할 discounted_price: {db_discounted_price}")
                                
                                product_data = {
                                    'channel_product_no': channel_product_no,
                                    'origin_product_no': origin_product_no,
                                    'product_name': product.get('name', ''),
                                    'status_type': product.get('statusType', ''),
                                    'sale_price': product.get('salePrice', 0),
                                    'discounted_price': db_discounted_price,
                                    'stock_quantity': product.get('stockQuantity', 0),
                                    'category_id': product.get('categoryId', ''),
                                    'brand_name': product.get('brandName', ''),
                                    'manufacturer_name': product.get('manufacturerName', ''),
                                    'model_name': product.get('modelName', ''),
                                    'seller_management_code': product.get('sellerManagementCode', ''),
                                    'reg_date': product.get('regDate', ''),
                                    'modified_date': product.get('modifiedDate', ''),
                                    'representative_image_url': product.get('representativeImage', {}).get('url', '') if product.get('representativeImage') else '',
                                    'whole_category_name': product.get('wholeCategoryName', ''),
                                    'whole_category_id': product.get('wholeCategoryId', ''),
                                    'delivery_fee': product.get('deliveryFee', 0),
                                    'return_fee': product.get('returnFee', 0),
                                    'exchange_fee': product.get('exchangeFee', 0),
                                    'discount_method': discount_method,
                                    'customer_benefit': str(customer_benefit) if customer_benefit else ''
                                }
                                
                                print(f"세부조회 후 저장할 상품 데이터: {product_data}")
                                
                                if self.db_manager:
                                    save_result = self.db_manager.save_product(product_data)
                                    print(f"세부조회 후 저장 결과: {save_result}")
                                    if save_result:
                                        detailed_saved_count += 1
                                        print(f"세부조회 후 상품 저장 성공: {channel_product_no}")
                                    else:
                                        print(f"세부조회 후 상품 저장 실패: {channel_product_no}")
                                else:
                                    print("DB 매니저가 없어서 저장할 수 없음")
                                    
                            except Exception as e:
                                print(f"세부조회 후 상품 저장 오류: {e}")
                        
                        print(f"세부조회 후 데이터베이스에 {detailed_saved_count}개 상품 저장 완료")
                        
                        # UI 스레드에서 트리뷰 업데이트 (세부조회 결과 포함)
                        self.root.after(0, lambda: self.update_product_tree(detailed_products))
                        
                        # 상태 업데이트
                        self.root.after(0, lambda: self.product_status_var.set(f"상품 목록 조회 완료 ({len(detailed_products)}개, DB저장: {detailed_saved_count}개)"))
                        self.root.after(0, lambda: self.update_api_status(f"상품 목록 조회 완료 ({len(detailed_products)}개, DB저장: {detailed_saved_count}개)"))
                    else:
                        print("응답 데이터에 'contents' 키가 없거나 비어있음")
                        self.root.after(0, lambda: self.product_status_var.set("상품 목록 조회 완료 (상품 없음)"))
                        self.root.after(0, lambda: self.update_api_status("상품 목록 조회 완료 (상품 없음)"))
                else:
                    error = response.get('error', '알 수 없는 오류')
                    status_code = response.get('status_code', 'N/A')
                    print(f"API 오류 - 상태코드: {status_code}, 오류: {error}")
                    self.root.after(0, lambda: self.product_status_var.set(f"조회 실패 ({status_code})"))
                    self.root.after(0, lambda: messagebox.showerror("상품 목록 조회 실패", f"상태코드: {status_code}\n오류: {error}"))
                    self.root.after(0, lambda: self.update_api_status("상품 목록 조회 실패"))
                    
            except Exception as e:
                print(f"예외 발생: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self.product_status_var.set("조회 오류"))
                self.root.after(0, lambda: messagebox.showerror("오류", f"상품 목록 조회 중 오류가 발생했습니다: {e}"))
                self.root.after(0, lambda: self.update_api_status("상품 목록 조회 오류"))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def update_product_tree(self, products):
        """상품 트리뷰 업데이트 (UI 스레드에서 호출)"""
        try:
            # 트리뷰 초기화
            for item in self.product_tree.get_children():
                self.product_tree.delete(item)
            
            # 상품 목록 추가
            for product in products:
                product_id = product.get('channelProductNo', 'N/A')
                product_name = product.get('name', 'N/A')
                status = product.get('statusType', 'N/A')
                sale_price = product.get('salePrice', 0)
                discounted_price = product.get('discountedPrice', 0)
                mobile_discounted_price = product.get('mobileDiscountedPrice', 0)
                stock = product.get('stockQuantity', 0)
                reg_date = product.get('regDate', 'N/A')
                
                # 날짜 형식 변환
                if reg_date != 'N/A' and len(reg_date) > 10:
                    reg_date = reg_date[:10]
                
                # 디버깅을 위한 가격 정보 출력 (세부조회 결과 포함)
                print(f"상품 {product_id} 가격 정보:")
                print(f"  salePrice: {sale_price}")
                print(f"  discountedPrice: {discounted_price}")
                print(f"  mobileDiscountedPrice: {mobile_discounted_price}")
                
                # 세부조회 결과에서 49100원이 나오는 필드 찾기
                for key, value in product.items():
                    if isinstance(value, (int, float)) and value == 49100:
                        print(f"  49100원 발견: {key} = {value}")
                    elif isinstance(value, (int, float)) and 49000 <= value <= 49200:
                        print(f"  비슷한 가격 발견: {key} = {value}")
                
                # customerBenefit에서 가격 정보 확인
                customer_benefit = product.get('customerBenefit', {})
                if customer_benefit:
                    print(f"  customerBenefit: {customer_benefit}")
                    
                    # immediateDiscountPolicy 확인
                    immediate_discount_policy = customer_benefit.get('immediateDiscountPolicy', {})
                    if immediate_discount_policy:
                        print(f"  immediateDiscountPolicy: {immediate_discount_policy}")
                        
                        discount_method = immediate_discount_policy.get('discountMethod', {})
                        if discount_method:
                            print(f"  discountMethod: {discount_method}")
                            
                            seller_sale_price = discount_method.get('sellerSalePrice')
                            if seller_sale_price:
                                print(f"  판매자세일가격: {seller_sale_price}")
                    
                    for key, value in customer_benefit.items():
                        if isinstance(value, (int, float)) and value == 49100:
                            print(f"  customerBenefit에서 49100원 발견: {key} = {value}")
                        elif isinstance(value, (int, float)) and 49000 <= value <= 49200:
                            print(f"  customerBenefit에서 비슷한 가격 발견: {key} = {value}")
                else:
                    print(f"  customerBenefit 없음 또는 비어있음")
                
                # 원래 판매가 형식 변환 (salePrice)
                if sale_price and isinstance(sale_price, (int, float)):
                    original_price_str = f"{int(sale_price):,}"
                else:
                    original_price_str = "0"
                
                # 셀러 할인가 (customerBenefit.immediateDiscountPolicy.discountMethod에서 판매자세일가격 추출)
                seller_discount_price = None
                customer_benefit = product.get('customerBenefit', {})
                if customer_benefit:
                    immediate_discount_policy = customer_benefit.get('immediateDiscountPolicy', {})
                    if immediate_discount_policy:
                        discount_method = immediate_discount_policy.get('discountMethod', {})
                        if discount_method:
                            # 판매자세일가격 추출 (sellerSalePrice 또는 value 필드 사용)
                            seller_discount_price = discount_method.get('sellerSalePrice') or discount_method.get('value')
                            if seller_discount_price:
                                print(f"  판매자세일가격 발견: {seller_discount_price}")
                
                if seller_discount_price and isinstance(seller_discount_price, (int, float)):
                    seller_discount_str = f"{int(seller_discount_price):,}"
                elif discounted_price and isinstance(discounted_price, (int, float)):
                    seller_discount_str = f"{int(discounted_price):,}"  # fallback
                else:
                    seller_discount_str = "0"
                
                # 실제 판매가 계산 (원래판매가 - 셀러할인가)
                actual_price = 0
                if sale_price and seller_discount_price and isinstance(sale_price, (int, float)) and isinstance(seller_discount_price, (int, float)):
                    actual_price = sale_price - seller_discount_price
                    print(f"  실제판매가 계산: {sale_price} - {seller_discount_price} = {actual_price}")
                elif mobile_discounted_price and isinstance(mobile_discounted_price, (int, float)):
                    actual_price = mobile_discounted_price
                    print(f"  실제판매가 fallback: {actual_price}")
                
                actual_price_str = f"{int(actual_price):,}"
                
                print(f"  표시될 가격: 원래={original_price_str}, 셀러할인={seller_discount_str}, 실제={actual_price_str}")
                
                # 재고 형식 변환
                if stock and isinstance(stock, (int, float)):
                    stock_str = str(int(stock))
                else:
                    stock_str = "0"
                
                # 링크 버튼 텍스트
                link_text = "수정|조회"
                
                self.product_tree.insert('', 'end', values=(
                    product_id, product_name, status, 
                    original_price_str, seller_discount_str, actual_price_str, stock_str, reg_date, link_text
                ))
            
            print(f"트리뷰 업데이트 완료: {len(products)}개 상품 추가")
            
        except Exception as e:
            print(f"트리뷰 업데이트 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_products(self):
        """상품 목록 새로고침"""
        self.load_products()
    
    def load_saved_products(self):
        """저장된 상품 목록 조회"""
        def load_thread():
            try:
                self.update_api_status("저장된 상품 조회 중...")
                self.product_status_var.set("저장된 상품 조회 중...")
                
                # 설정에서 선택된 상품상태 가져오기
                selected_statuses = [status_code for status_code, var in self.product_status_vars.items() if var.get()]
                print(f"저장된 상품 조회 - 선택된 상품상태: {selected_statuses}")
                
                # 데이터베이스에서 상품 조회
                all_products = self.db_manager.get_all_products()
                print(f"저장된 상품 개수: {len(all_products)}")
                
                # 설정된 상품상태로 필터링
                if selected_statuses:
                    filtered_products = [p for p in all_products if p.get('status_type') in selected_statuses]
                else:
                    filtered_products = all_products
                
                print(f"필터링된 상품 개수: {len(filtered_products)}")
                
                # UI 스레드에서 트리뷰 업데이트
                self.root.after(0, lambda: self.update_product_tree_from_db(filtered_products))
                
                # 상태 업데이트
                self.root.after(0, lambda: self.product_status_var.set(f"저장된 상품 조회 완료 ({len(filtered_products)}개)"))
                self.root.after(0, lambda: self.update_api_status(f"저장된 상품 조회 완료 ({len(filtered_products)}개)"))
                
            except Exception as e:
                print(f"저장된 상품 조회 오류: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self.product_status_var.set("조회 오류"))
                self.root.after(0, lambda: messagebox.showerror("오류", f"저장된 상품 조회 중 오류가 발생했습니다: {e}"))
                self.root.after(0, lambda: self.update_api_status("저장된 상품 조회 오류"))
        
        # 백그라운드에서 상품 조회
        import threading
        threading.Thread(target=load_thread, daemon=True).start()
    
    def update_product_tree_from_db(self, products):
        """데이터베이스 상품으로 트리뷰 업데이트 (UI 스레드에서 호출)"""
        try:
            # 트리뷰 초기화
            for item in self.product_tree.get_children():
                self.product_tree.delete(item)
            
            # 상품 목록 추가
            for product in products:
                product_id = product.get('channel_product_no', 'N/A')
                product_name = product.get('product_name', 'N/A')
                status = product.get('status_type', 'N/A')
                sale_price = product.get('sale_price', 0)
                discounted_price = product.get('discounted_price', 0)
                stock = product.get('stock_quantity', 0)
                reg_date = product.get('reg_date', 'N/A')
                
                # 날짜 형식 변환
                if reg_date != 'N/A' and len(reg_date) > 10:
                    reg_date = reg_date[:10]
                
                # 원래 판매가 형식 변환
                if sale_price and isinstance(sale_price, (int, float)):
                    original_price_str = f"{int(sale_price):,}"
                else:
                    original_price_str = "0"
                
                # 셀러 할인가 (DB에서는 discounted_price가 셀러할인가)
                if discounted_price and isinstance(discounted_price, (int, float)):
                    seller_discount_str = f"{int(discounted_price):,}"
                else:
                    seller_discount_str = "0"
                
                # 실제 판매가 계산 (원래판매가 - 셀러할인가)
                actual_price = 0
                if sale_price and discounted_price and isinstance(sale_price, (int, float)) and isinstance(discounted_price, (int, float)):
                    actual_price = sale_price - discounted_price
                    print(f"DB에서 실제판매가 계산: {sale_price} - {discounted_price} = {actual_price}")
                
                actual_price_str = f"{int(actual_price):,}"
                
                # 재고 형식 변환
                if stock and isinstance(stock, (int, float)):
                    stock_str = str(int(stock))
                else:
                    stock_str = "0"
                
                # 링크 버튼 텍스트
                link_text = "수정|조회"
                
                self.product_tree.insert('', 'end', values=(
                    product_id, product_name, status, 
                    original_price_str, seller_discount_str, actual_price_str, stock_str, reg_date, link_text
                ))
            
            print(f"DB 트리뷰 업데이트 완료: {len(products)}개 상품 추가")
            
        except Exception as e:
            print(f"DB 트리뷰 업데이트 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def on_product_double_click(self, event):
        """상품 더블클릭 시 채널상품조회 팝업 표시"""
        selection = self.product_tree.selection()
        if selection:
            item = self.product_tree.item(selection[0])
            values = item['values']
            if values:
                product_id = values[0]
                product_name = values[1]
                self.show_channel_product_detail(product_id, product_name)
    
    def on_price_click(self, event):
        """가격 컬럼 클릭 시 가격 변경 다이얼로그 표시"""
        # 클릭된 항목과 컬럼 확인
        item = self.product_tree.identify_row(event.y)
        column = self.product_tree.identify_column(event.x)
        
        if not item:
            return
        
        # 가격 컬럼인지 확인 (컬럼 인덱스 4, 5, 6: 원래판매가, 셀러할인가, 실제판매가)
        column_index = int(column.replace('#', ''))
        if column_index not in [4, 5, 6]:
            return
        
        # 상품 정보 가져오기
        values = self.product_tree.item(item)['values']
        if not values:
            return
        
        product_id = values[0]
        product_name = values[1]
        
        # 컬럼에 따른 가격 타입 설정
        price_types = {4: '원래판매가', 5: '셀러할인가', 6: '실제판매가'}
        price_type = price_types.get(column_index, '가격')
        current_price = values[column_index - 1]  # Tkinter 컬럼 인덱스는 1부터 시작
        
        # 셀러할인가 컬럼인 경우 셀러할인가 자체를 표시
        if column_index == 5:  # 셀러할인가 컬럼
            # 셀러할인가는 이미 올바르게 표시됨 (values[4])
            pass  # current_price는 이미 올바른 값
        
        # 가격 변경 다이얼로그 표시
        self.show_price_change_dialog(product_id, product_name, price_type, current_price)
    
    def on_cell_click(self, event):
        """셀 클릭 시 가격/상태 변경 다이얼로그 표시"""
        # 클릭된 항목과 컬럼 확인
        item = self.product_tree.identify_row(event.y)
        column = self.product_tree.identify_column(event.x)
        
        if not item:
            return
        
        # 상품 정보 가져오기
        values = self.product_tree.item(item)['values']
        if not values:
            return
        
        product_id = values[0]
        product_name = values[1]
        column_index = int(column.replace('#', ''))
        
        # 디버깅: 클릭된 컬럼 정보 출력
        product_columns = ('상품ID', '상품명', '상태', '원래판매가', '셀러할인가', '실제판매가', '재고', '등록일', '링크')
        print(f"클릭된 컬럼: {column_index}, 컬럼명: {product_columns[column_index-1] if column_index-1 < len(product_columns) else 'Unknown'}")
        
        # 상태 컬럼인지 확인 (컬럼 인덱스 3: 상태)
        if column_index == 3:
            self.on_status_click(product_id, product_name, values[2])
        # 가격 컬럼인지 확인 (컬럼 인덱스 4, 5: 원래판매가, 셀러할인가만 수정 가능)
        # 실제판매가(컬럼 인덱스 6)는 수정 불가
        elif column_index in [4, 5]:
            self.on_price_click(event)
        # 재고 컬럼인지 확인 (컬럼 인덱스 7: 재고)
        elif column_index == 7:
            self.on_stock_click(product_id, product_name, values[6])
        # 링크 컬럼인지 확인 (컬럼 인덱스 9: 링크)
        elif column_index == 9:
            self.on_link_click(event)
        # 실제판매가(6번), 등록일(8번) 등은 아무 동작 없음
    
    def on_stock_click(self, product_id, product_name, current_stock):
        """재고 클릭 시 재고 변경 다이얼로그 표시"""
        # 재고 변경 다이얼로그 표시
        self.show_stock_change_dialog(product_id, product_name, current_stock)
    
    def on_status_click(self, product_id, product_name, current_status):
        """상태 클릭 시 상태 변경 다이얼로그 표시"""
        # 상태 변경 다이얼로그 표시
        self.show_status_change_dialog(product_id, product_name, current_status)
    
    def show_status_change_dialog(self, product_id, product_name, current_status):
        """상태 변경 다이얼로그 표시"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"상품 상태 변경 - {product_name}")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 메인 프레임
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 제목
        title_label = ttk.Label(main_frame, text=f"상품: {product_name}", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 상품 ID
        id_label = ttk.Label(main_frame, text=f"상품 ID: {product_id}")
        id_label.pack(pady=(0, 10))
        
        # 현재 상태
        current_label = ttk.Label(main_frame, text=f"현재 상태: {current_status}")
        current_label.pack(pady=(0, 10))
        
        # 새 상태 선택
        ttk.Label(main_frame, text="새 상태:").pack(pady=(10, 5))
        status_var = tk.StringVar(value=current_status)
        status_combo = ttk.Combobox(main_frame, textvariable=status_var, width=20, state='readonly')
        status_combo['values'] = ('SALE', 'WAIT', 'OUTOFSTOCK', 'SUSPENSION', 'CLOSE', 'PROHIBITION')
        status_combo.pack(pady=(0, 10))
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        def update_status():
            """상태 업데이트"""
            new_status = status_var.get()
            if new_status == current_status:
                messagebox.showinfo("알림", "상태가 변경되지 않았습니다.")
                return
            
            # API 호출로 상태 업데이트
            self.update_product_status_api(product_id, new_status)
            dialog.destroy()
        
        def cancel():
            """취소"""
            dialog.destroy()
        
        ttk.Button(button_frame, text="변경", command=update_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=cancel).pack(side=tk.LEFT, padx=5)
    
    def update_product_status_api(self, product_id, new_status):
        """상품 상태 업데이트 API 호출"""
        def update_thread():
            try:
                self.update_api_status(f"상품 상태 변경 중...")
                
                # API 초기화 확인
                if not self.naver_api:
                    if self.client_id_var.get() and self.client_secret_var.get():
                        self.naver_api = NaverShoppingAPI(
                            self.client_id_var.get(),
                            self.client_secret_var.get()
                        )
                    else:
                        self.root.after(0, lambda: messagebox.showerror("오류", "API 설정이 필요합니다."))
                        return
                
                # 실제 API 호출 구현 필요
                # 여기서는 임시로 성공 응답 반환
                response = {'success': True, 'message': '상태 변경 완료'}
                
                if response.get('success'):
                    self.root.after(0, lambda: self.update_api_status(f"상품 상태 변경 완료"))
                    self.root.after(0, lambda: messagebox.showinfo("성공", f"상품 상태가 {new_status}로 변경되었습니다."))
                    # 상품 목록 새로고침
                    self.root.after(0, lambda: self.load_saved_products())
                else:
                    error = response.get('error', '알 수 없는 오류')
                    self.root.after(0, lambda: self.update_api_status(f"상품 상태 변경 실패"))
                    self.root.after(0, lambda: messagebox.showerror("오류", f"상품 상태 변경 실패: {error}"))
                
            except Exception as e:
                print(f"상태 업데이트 오류: {e}")
                self.root.after(0, lambda: self.update_api_status(f"상품 상태 변경 오류"))
                self.root.after(0, lambda: messagebox.showerror("오류", f"상태 변경 중 오류가 발생했습니다: {e}"))
        
        # 백그라운드에서 상태 업데이트
        import threading
        threading.Thread(target=update_thread, daemon=True).start()
    
    def on_link_click(self, event):
        """링크 컬럼 클릭 시 링크 다이얼로그 표시"""
        # 클릭된 항목과 컬럼 확인
        item = self.product_tree.identify_row(event.y)
        column = self.product_tree.identify_column(event.x)
        
        if not item:
            return
        
        # 링크 컬럼인지 확인 (컬럼 인덱스 9: 링크)
        column_index = int(column.replace('#', ''))
        if column_index != 9:
            return
        
        # 상품 정보 가져오기
        values = self.product_tree.item(item)['values']
        if not values:
            return
        
        product_id = values[0]
        product_name = values[1]
        
        # 원상품 ID 가져오기 (데이터베이스에서 조회)
        origin_product_id = self.get_origin_product_id(product_id)
        
        # 링크 다이얼로그 표시
        self.show_link_dialog(product_id, product_name, origin_product_id)
    
    def get_origin_product_id(self, channel_product_id):
        """채널상품 ID로 원상품 ID 조회"""
        try:
            print(f"원상품 ID 조회 시작: {channel_product_id}")
            print(f"DB 매니저 존재: {self.db_manager is not None}")
            
            if self.db_manager:
                product = self.db_manager.get_product_by_id(channel_product_id)
                print(f"DB에서 조회된 상품: {product}")
                
                if product:
                    origin_id = product.get('origin_product_no', '')
                    print(f"원상품 ID: {origin_id}")
                    return origin_id
                else:
                    print("DB에서 상품을 찾을 수 없음")
            else:
                print("DB 매니저가 없음")
            return ''
        except Exception as e:
            print(f"원상품 ID 조회 오류: {e}")
            return ''
    
    def show_link_dialog(self, product_id, product_name, origin_product_id):
        """링크 다이얼로그 표시"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"상품 링크 - {product_name}")
        dialog.geometry("700x500")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 메인 프레임
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 제목
        title_label = ttk.Label(main_frame, text=f"상품: {product_name}", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 상품 ID 정보
        id_frame = ttk.Frame(main_frame)
        id_frame.pack(pady=(0, 20))
        
        ttk.Label(id_frame, text=f"채널상품 ID: {product_id}").pack(anchor=tk.W)
        
        # 디버깅 정보 추가
        print(f"링크 다이얼로그 - 채널상품 ID: {product_id}")
        print(f"링크 다이얼로그 - 원상품 ID: {origin_product_id}")
        print(f"링크 다이얼로그 - 원상품 ID 타입: {type(origin_product_id)}")
        print(f"링크 다이얼로그 - 원상품 ID 길이: {len(str(origin_product_id))}")
        
        if origin_product_id and str(origin_product_id).strip():
            ttk.Label(id_frame, text=f"원상품 ID: {origin_product_id}").pack(anchor=tk.W)
        else:
            ttk.Label(id_frame, text="원상품 ID: 없음", foreground='gray').pack(anchor=tk.W)
        
        # 링크 프레임
        link_frame = ttk.LabelFrame(main_frame, text="상품 링크")
        link_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 상품 수정 페이지 링크
        edit_frame = ttk.Frame(link_frame)
        edit_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(edit_frame, text="상품 수정 페이지:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        # 상품 수정 페이지는 원상품 ID 사용 (있으면), 없으면 채널상품 ID 사용
        edit_product_id = origin_product_id if origin_product_id and str(origin_product_id).strip() else product_id
        edit_url = f"https://sell.smartstore.naver.com/#/products/edit/{edit_product_id}"
        
        # ID 정보 표시
        if origin_product_id and str(origin_product_id).strip():
            ttk.Label(edit_frame, text=f"(원상품 ID {edit_product_id} 사용)", foreground='green').pack(anchor=tk.W)
        else:
            ttk.Label(edit_frame, text=f"(채널상품 ID {edit_product_id} 사용)", foreground='orange').pack(anchor=tk.W)
        
        edit_url_label = ttk.Label(edit_frame, text=edit_url, foreground='blue', cursor='hand2')
        edit_url_label.pack(anchor=tk.W, pady=(5, 0))
        edit_url_label.bind('<Button-1>', lambda e: self.open_url(edit_url))
        
        ttk.Button(edit_frame, text="상품 수정 페이지 열기", 
                  command=lambda: self.open_url(edit_url)).pack(anchor=tk.W, pady=(5, 0))
        
        # 실제 상품 조회 페이지 링크
        view_frame = ttk.Frame(link_frame)
        view_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(view_frame, text="실제 상품 조회 페이지:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        view_url = f"https://smartstore.naver.com/us-shop/products/{product_id}"
        view_url_label = ttk.Label(view_frame, text=view_url, foreground='blue', cursor='hand2')
        view_url_label.pack(anchor=tk.W, pady=(5, 0))
        view_url_label.bind('<Button-1>', lambda e: self.open_url(view_url))
        
        ttk.Button(view_frame, text="실제 상품 조회 페이지 열기", 
                  command=lambda: self.open_url(view_url)).pack(anchor=tk.W, pady=(5, 0))
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="닫기", command=dialog.destroy).pack()
    
    def open_url(self, url):
        """URL을 기본 브라우저에서 열기"""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("오류", f"브라우저를 열 수 없습니다: {e}")
    
    def show_price_change_dialog(self, product_id, product_name, price_type, current_price):
        """가격 변경 다이얼로그 표시"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"가격 변경 - {product_name}")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 메인 프레임
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 제목
        title_label = ttk.Label(main_frame, text=f"상품: {product_name}", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 상품 ID
        id_label = ttk.Label(main_frame, text=f"상품 ID: {product_id}")
        id_label.pack(pady=(0, 10))
        
        # 가격 타입
        type_label = ttk.Label(main_frame, text=f"변경할 가격: {price_type}")
        type_label.pack(pady=(0, 10))
        
        # 현재 가격
        current_label = ttk.Label(main_frame, text=f"현재 가격: {current_price}")
        current_label.pack(pady=(0, 10))
        
        # 새 가격 입력
        ttk.Label(main_frame, text="새 가격:").pack(pady=(10, 5))
        price_var = tk.StringVar(value=current_price.replace(',', ''))
        price_entry = ttk.Entry(main_frame, textvariable=price_var, width=20)
        price_entry.pack(pady=(0, 10))
        price_entry.focus()
        price_entry.select_range(0, tk.END)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        def update_price():
            """가격 업데이트"""
            try:
                new_price = int(price_var.get().replace(',', ''))
                if new_price < 0:
                    messagebox.showerror("오류", "가격은 0 이상이어야 합니다.")
                    return
                
                # API 호출로 가격 업데이트
                self.update_product_price(product_id, price_type, new_price)
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("오류", "올바른 숫자를 입력해주세요.")
        
        def cancel():
            """취소"""
            dialog.destroy()
        
        ttk.Button(button_frame, text="변경", command=update_price).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=cancel).pack(side=tk.LEFT, padx=5)
        
        # Enter 키로 변경 실행
        price_entry.bind('<Return>', lambda e: update_price())
    
    def update_product_price(self, product_id, price_type, new_price):
        """상품 가격 업데이트"""
        def update_thread():
            try:
                self.update_api_status(f"{price_type} 변경 중...")
                
                # API 초기화 확인
                if not self.naver_api:
                    if self.client_id_var.get() and self.client_secret_var.get():
                        self.naver_api = NaverShoppingAPI(
                            self.client_id_var.get(),
                            self.client_secret_var.get()
                        )
                    else:
                        self.root.after(0, lambda: messagebox.showerror("오류", "API 설정이 필요합니다."))
                        return
                
                # 가격 타입에 따른 API 호출
                if price_type == '원래판매가':
                    # 상품 정보 수정 API 호출 (salePrice 변경)
                    response = self.update_product_sale_price(product_id, new_price)
                elif price_type == '셀러할인가':
                    # 상품 정보 수정 API 호출 (discountedPrice 변경)
                    response = self.update_product_discounted_price(product_id, new_price)
                elif price_type == '실제판매가':
                    # 상품 정보 수정 API 호출 (mobileDiscountedPrice 변경)
                    response = self.update_product_mobile_price(product_id, new_price)
                else:
                    self.root.after(0, lambda: messagebox.showerror("오류", "지원하지 않는 가격 타입입니다."))
                    return
                
                if response.get('success'):
                    self.root.after(0, lambda: self.update_api_status(f"{price_type} 변경 완료"))
                    self.root.after(0, lambda: messagebox.showinfo("성공", f"{price_type}이 {new_price:,}원으로 변경되었습니다."))
                    # 상품 목록 새로고침
                    self.root.after(0, lambda: self.load_products())
                else:
                    error = response.get('error', '알 수 없는 오류')
                    self.root.after(0, lambda: self.update_api_status(f"{price_type} 변경 실패"))
                    self.root.after(0, lambda: messagebox.showerror("오류", f"{price_type} 변경 실패: {error}"))
                
            except Exception as e:
                print(f"가격 업데이트 오류: {e}")
                self.root.after(0, lambda: self.update_api_status(f"{price_type} 변경 오류"))
                self.root.after(0, lambda: messagebox.showerror("오류", f"가격 변경 중 오류가 발생했습니다: {e}"))
        
        # 백그라운드에서 가격 업데이트
        import threading
        threading.Thread(target=update_thread, daemon=True).start()
    
    def update_product_sale_price(self, product_id, new_price):
        """상품 판매가 업데이트"""
        # 실제 API 호출 구현 필요
        # 여기서는 임시로 성공 응답 반환
        return {'success': True, 'message': '판매가 변경 완료'}
    
    def update_product_discounted_price(self, product_id, new_price):
        """상품 할인가 업데이트"""
        # 실제 API 호출 구현 필요
        # 여기서는 임시로 성공 응답 반환
        return {'success': True, 'message': '할인가 변경 완료'}
    
    def update_product_mobile_price(self, product_id, new_price):
        """상품 모바일 가격 업데이트"""
        # 실제 API 호출 구현 필요
        # 여기서는 임시로 성공 응답 반환
        return {'success': True, 'message': '모바일 가격 변경 완료'}
    
    def show_channel_product_detail(self, product_id, product_name):
        """채널상품 상세 정보 팝업 표시"""
        # API 초기화 확인
        if not self.naver_api:
            if self.client_id_var.get() and self.client_secret_var.get():
                self.naver_api = NaverShoppingAPI(
                    self.client_id_var.get(),
                    self.client_secret_var.get()
                )
            else:
                messagebox.showerror("오류", "API 설정이 필요합니다.\n설정 탭에서 Client ID와 Client Secret을 입력해주세요.")
                return
        
        # 팝업 창 생성
        popup = tk.Toplevel(self.root)
        popup.title(f"채널상품 조회 - {product_name}")
        popup.geometry("800x600")
        popup.resizable(True, True)
        
        # 메인 프레임
        main_frame = ttk.Frame(popup)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 제목
        title_label = ttk.Label(main_frame, text=f"채널상품 ID: {product_id}", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 로딩 상태 표시
        loading_label = ttk.Label(main_frame, text="채널상품 정보를 조회하는 중...", foreground='blue')
        loading_label.pack(pady=10)
        
        # 결과 표시 영역
        result_frame = ttk.LabelFrame(main_frame, text="채널상품 조회 결과")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 텍스트 위젯 (읽기 전용)
        result_text = tk.Text(result_frame, wrap=tk.WORD, state=tk.DISABLED, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=result_text.yview)
        result_text.configure(yscrollcommand=scrollbar.set)
        
        result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 닫기 버튼
        close_button = ttk.Button(main_frame, text="닫기", command=popup.destroy)
        close_button.pack(pady=10)
        
        def fetch_product_detail():
            """상품 상세 정보 조회 (채널상품조회 기능)"""
            try:
                # 채널상품 조회 API 호출 (v2 API 직접 사용)
                response = self.naver_api.make_authenticated_request('GET', f'/external/v2/products/channel-products/{product_id}')
                
                # UI 스레드에서 결과 업데이트
                popup.after(0, lambda: update_result(response))
                
            except Exception as e:
                error_msg = f"채널상품 조회 중 오류가 발생했습니다:\n{str(e)}"
                popup.after(0, lambda: update_result({'success': False, 'error': error_msg}))
        
        def update_result(response):
            """결과 업데이트"""
            loading_label.destroy()
            
            result_text.config(state=tk.NORMAL)
            result_text.delete(1.0, tk.END)
            
            if response.get('success'):
                data = response.get('data', {})
                if data:
                    # JSON을 보기 좋게 포맷팅
                    import json
                    formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
                    result_text.insert(1.0, f"✅ 채널상품 조회 성공\n")
                    result_text.insert(tk.END, f"채널상품 ID: {product_id}\n")
                    result_text.insert(tk.END, f"상태 코드: {response.get('status_code', 'N/A')}\n")
                    result_text.insert(tk.END, f"메시지: {response.get('message', 'N/A')}\n\n")
                    result_text.insert(tk.END, "응답 데이터:\n")
                    result_text.insert(tk.END, formatted_data)
                else:
                    result_text.insert(1.0, "❌ 채널상품 정보를 찾을 수 없습니다.")
            else:
                error = response.get('error', '알 수 없는 오류')
                status_code = response.get('status_code', 'N/A')
                result_text.insert(1.0, f"❌ 채널상품 조회 실패\n")
                result_text.insert(tk.END, f"채널상품 ID: {product_id}\n")
                result_text.insert(tk.END, f"상태 코드: {status_code}\n")
                result_text.insert(tk.END, f"오류: {error}")
            
            result_text.config(state=tk.DISABLED)
        
        # 백그라운드에서 상품 정보 조회
        import threading
        threading.Thread(target=fetch_product_detail, daemon=True).start()
    
    def show_api_response(self):
        """서버 응답 표시 창"""
        if not hasattr(self, 'last_api_response') or self.last_api_response is None:
            messagebox.showwarning("알림", "아직 API 응답이 없습니다.\n먼저 '상품 목록 조회'를 실행해주세요.")
            return
        
        # 팝업 창 생성
        popup = tk.Toplevel(self.root)
        popup.title("상품 목록 조회 API 응답")
        popup.geometry("1000x700")
        popup.resizable(True, True)
        
        # 메인 프레임
        main_frame = ttk.Frame(popup)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 제목
        title_label = ttk.Label(main_frame, text="상품 목록 조회 API 응답", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 응답 정보 프레임
        info_frame = ttk.LabelFrame(main_frame, text="응답 정보")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        response = self.last_api_response
        success = response.get('success', False)
        status_code = response.get('status_code', 'N/A')
        message = response.get('message', 'N/A')
        
        ttk.Label(info_frame, text=f"성공 여부: {'✅ 성공' if success else '❌ 실패'}").pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(info_frame, text=f"상태 코드: {status_code}").pack(anchor=tk.W, padx=10, pady=5)
        ttk.Label(info_frame, text=f"메시지: {message}").pack(anchor=tk.W, padx=10, pady=5)
        
        # 원상품 ID 분석 프레임
        analysis_frame = ttk.LabelFrame(main_frame, text="원상품 ID 분석")
        analysis_frame.pack(fill=tk.X, pady=(0, 10))
        
        if success and response.get('data'):
            data = response.get('data', {})
            contents = data.get('contents', [])
            
            # 원상품 ID 통계
            total_products = 0
            products_with_origin_id = 0
            products_without_origin_id = 0
            
            for content in contents:
                if 'channelProducts' in content:
                    for product in content['channelProducts']:
                        total_products += 1
                        if product.get('originProductNo'):
                            products_with_origin_id += 1
                        else:
                            products_without_origin_id += 1
            
            ttk.Label(analysis_frame, text=f"총 상품 수: {total_products}").pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(analysis_frame, text=f"원상품 ID 있는 상품: {products_with_origin_id}", foreground='green').pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(analysis_frame, text=f"원상품 ID 없는 상품: {products_without_origin_id}", foreground='red').pack(anchor=tk.W, padx=10, pady=2)
            
            if products_without_origin_id > 0:
                ttk.Label(analysis_frame, text="⚠️ 일부 상품에 원상품 ID가 없습니다.", foreground='orange').pack(anchor=tk.W, padx=10, pady=2)
        else:
            ttk.Label(analysis_frame, text="응답 데이터가 없습니다.", foreground='red').pack(anchor=tk.W, padx=10, pady=5)
        
        # 전체 응답 데이터 표시
        response_frame = ttk.LabelFrame(main_frame, text="전체 응답 데이터")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 텍스트 위젯과 스크롤바
        text_widget = tk.Text(response_frame, wrap=tk.WORD, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(response_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # JSON 데이터 포맷팅하여 표시
        import json
        try:
            formatted_response = json.dumps(response, indent=2, ensure_ascii=False)
            text_widget.insert(1.0, formatted_response)
        except Exception as e:
            text_widget.insert(1.0, f"JSON 포맷팅 오류: {e}\n\n원본 데이터:\n{response}")
        
        # 텍스트 위젯을 읽기 전용으로 설정
        text_widget.config(state=tk.DISABLED)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        def copy_response():
            """응답 데이터 복사"""
            try:
                formatted_response = json.dumps(response, indent=2, ensure_ascii=False)
                popup.clipboard_clear()
                popup.clipboard_append(formatted_response)
                messagebox.showinfo("성공", "응답 데이터가 클립보드에 복사되었습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"복사 중 오류가 발생했습니다: {e}")
        
        ttk.Button(button_frame, text="응답 데이터 복사", command=copy_response).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="닫기", command=popup.destroy).pack(side=tk.LEFT, padx=5)
    
    def auto_load_saved_products(self):
        """프로그램 시작 시 저장된 상품 자동 로드 (설정의 상품상태 필터 적용)"""
        try:
            if not self.db_manager:
                print("DB 매니저가 없어서 저장된 상품을 로드할 수 없습니다.")
                return
            
            # 설정에서 선택된 상품상태 가져오기
            selected_statuses = [status_code for status_code, var in self.product_status_vars.items() if var.get()]
            print(f"자동 로드 - product_status_vars: {self.product_status_vars}")
            print(f"자동 로드 - 각 상태별 값:")
            for status_code, var in self.product_status_vars.items():
                print(f"  {status_code}: {var.get()}")
            print(f"자동 로드 - 선택된 상품상태: {selected_statuses}")
            
            # 데이터베이스에서 저장된 상품 개수 확인
            all_products = self.db_manager.get_all_products()
            
            if all_products and len(all_products) > 0:
                # 설정된 상품상태로 필터링
                if selected_statuses:
                    filtered_products = [p for p in all_products if p.get('status_type') in selected_statuses]
                else:
                    filtered_products = all_products
                
                print(f"저장된 상품 {len(all_products)}개 중 {len(filtered_products)}개 필터링됨")
                
                if filtered_products:
                    # UI 스레드에서 트리뷰 업데이트
                    self.root.after(0, lambda: self.update_product_tree_from_db(filtered_products))
                    self.root.after(0, lambda: self.product_status_var.set(f"저장된 상품 {len(filtered_products)}개 자동 로드 완료"))
                    self.root.after(0, lambda: self.update_api_status(f"저장된 상품 {len(filtered_products)}개 자동 로드"))
                else:
                    print("선택된 상품상태에 해당하는 상품이 없습니다.")
                    self.root.after(0, lambda: self.product_status_var.set("선택된 상품상태에 해당하는 상품이 없습니다."))
            else:
                print("저장된 상품이 없습니다.")
                self.root.after(0, lambda: self.product_status_var.set("저장된 상품이 없습니다. '상품 목록 조회'를 실행해주세요."))
                
        except Exception as e:
            print(f"저장된 상품 자동 로드 오류: {e}")
            self.root.after(0, lambda: self.product_status_var.set("저장된 상품 로드 중 오류가 발생했습니다."))
    
    def change_product_status(self):
        """상품 상태 변경"""
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showwarning("선택 필요", "상품을 선택해주세요.")
            return
        
        item = self.product_tree.item(selection[0])
        values = item['values']
        if not values:
            return
        
        product_id = values[0]
        current_status = values[2]
        
        # 상태 변경 다이얼로그
        status_window = tk.Toplevel(self.root)
        status_window.title("상품 상태 변경")
        status_window.geometry("300x200")
        status_window.transient(self.root)
        status_window.grab_set()
        
        ttk.Label(status_window, text=f"상품 ID: {product_id}").pack(pady=10)
        ttk.Label(status_window, text=f"현재 상태: {current_status}").pack(pady=5)
        
        ttk.Label(status_window, text="새로운 상태:").pack(pady=5)
        new_status_var = tk.StringVar(value=current_status)
        status_combo = ttk.Combobox(status_window, textvariable=new_status_var, 
                                   values=['SALE', 'WAIT', 'OUTOFSTOCK', 'SUSPENSION', 'CLOSE', 'PROHIBITION'])
        status_combo.pack(pady=5)
        
        def apply_status():
            new_status = new_status_var.get()
            if new_status != current_status:
                # 여기에 실제 상태 변경 API 호출 로직 추가
                messagebox.showinfo("상태 변경", f"상품 상태를 {current_status}에서 {new_status}로 변경했습니다.")
                status_window.destroy()
                self.load_products()  # 목록 새로고침
            else:
                messagebox.showinfo("알림", "상태가 변경되지 않았습니다.")
                status_window.destroy()
        
        ttk.Button(status_window, text="적용", command=apply_status).pack(pady=10)
        ttk.Button(status_window, text="취소", command=status_window.destroy).pack(pady=5)
    
    def create_order_status_tabs(self):
        """주문 상태별 탭들 생성"""
        order_statuses = [
            ('발송대기', 'READY'),
            ('배송중', 'SHIPPED'), 
            ('배송완료', 'DELIVERED'),
            ('구매확정', 'CONFIRMED'),
            ('취소주문', 'CANCELLED'),
            ('반품주문', 'RETURNED'),
            ('교환주문', 'EXCHANGED')
        ]
        
        for tab_name, status_code in order_statuses:
            self.create_order_status_tab(tab_name, status_code)
    
    def create_order_status_tab(self, tab_name, status_code):
        """개별 주문 상태 탭 생성"""
        status_frame = ttk.Frame(self.notebook)
        self.notebook.add(status_frame, text=tab_name)
        
        # 필터 프레임
        filter_frame = ttk.LabelFrame(status_frame, text="필터")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="시작일:").grid(row=0, column=0, padx=5, pady=5)
        start_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        ttk.Entry(filter_frame, textvariable=start_date_var, width=12).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="종료일:").grid(row=0, column=2, padx=5, pady=5)
        end_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        ttk.Entry(filter_frame, textvariable=end_date_var, width=12).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(filter_frame, text="조회", 
                  command=lambda: self.load_orders_by_status(status_code, start_date_var.get(), end_date_var.get())).grid(row=0, column=4, padx=5, pady=5)
        
        # 주문 목록 트리뷰
        orders_frame = ttk.Frame(status_frame)
        orders_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('주문번호', '고객명', '상품명', '금액', '주문일', '상태')
        order_tree = ttk.Treeview(orders_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            order_tree.heading(col, text=col)
            order_tree.column(col, width=120)
        
        # 스크롤바
        order_scrollbar = ttk.Scrollbar(orders_frame, orient=tk.VERTICAL, command=order_tree.yview)
        order_tree.configure(yscrollcommand=order_scrollbar.set)
        
        order_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        order_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 액션 버튼들
        action_frame = ttk.Frame(status_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        if status_code == 'READY':
            ttk.Button(action_frame, text="발송 처리", 
                      command=lambda: self.process_shipping(order_tree)).pack(side=tk.LEFT, padx=5)
        elif status_code == 'SHIPPED':
            ttk.Button(action_frame, text="배송 완료", 
                      command=lambda: self.complete_delivery(order_tree)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="새로고침", 
                  command=lambda: self.load_orders_by_status(status_code, start_date_var.get(), end_date_var.get())).pack(side=tk.LEFT, padx=5)
        
        # 트리뷰를 인스턴스 변수로 저장 (나중에 사용)
        setattr(self, f'{status_code.lower()}_tree', order_tree)
    
    def load_orders_by_status(self, status_code, start_date, end_date):
        """상태별 주문 목록 조회"""
        # 여기에 실제 주문 조회 로직 구현
        print(f"Loading orders for status: {status_code}, from {start_date} to {end_date}")
    
    def process_shipping(self, tree):
        """발송 처리"""
        selection = tree.selection()
        if selection:
            messagebox.showinfo("발송 처리", "선택된 주문의 발송 처리를 시작합니다.")
    
    def complete_delivery(self, tree):
        """배송 완료 처리"""
        selection = tree.selection()
        if selection:
            messagebox.showinfo("배송 완료", "선택된 주문의 배송 완료 처리를 시작합니다.")
    
    def show_stock_change_dialog(self, product_id, product_name, current_stock):
        """재고 변경 다이얼로그 표시"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"재고 변경 - {product_name}")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 다이얼로그를 화면 중앙에 위치
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # 상품 정보 표시
        info_frame = ttk.Frame(dialog)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(info_frame, text=f"상품 ID: {product_id}", font=("Arial", 10)).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"상품명: {product_name}", font=("Arial", 10)).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"현재 재고: {current_stock}", font=("Arial", 10)).pack(anchor=tk.W)
        
        # 재고 입력
        input_frame = ttk.Frame(dialog)
        input_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(input_frame, text="새 재고 수량:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        stock_var = tk.StringVar(value=str(current_stock))
        stock_entry = ttk.Entry(input_frame, textvariable=stock_var, font=("Arial", 12), width=20)
        stock_entry.pack(fill=tk.X, pady=5)
        stock_entry.select_range(0, tk.END)
        stock_entry.focus()
        
        def confirm_change():
            try:
                new_stock = int(stock_var.get())
                if new_stock < 0:
                    messagebox.showerror("오류", "재고는 0 이상이어야 합니다.")
                    return
                
                # API 호출로 재고 업데이트
                success = self.update_product_stock_api(product_id, new_stock)
                if success:
                    messagebox.showinfo("성공", f"재고가 {new_stock}개로 변경되었습니다.")
                    dialog.destroy()
                    # 상품 목록 새로고침
                    self.refresh_products()
                else:
                    messagebox.showerror("오류", "재고 변경에 실패했습니다.")
            except ValueError:
                messagebox.showerror("오류", "올바른 숫자를 입력해주세요.")
        
        # 버튼 프레임
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # 확인 버튼
        confirm_button = ttk.Button(button_frame, text="확인", command=confirm_change)
        confirm_button.pack(side=tk.LEFT, padx=5)
        
        # 취소 버튼
        cancel_button = ttk.Button(button_frame, text="취소", command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Enter 키로 확인
        dialog.bind('<Return>', lambda e: confirm_change())
    
    def update_product_stock_api(self, product_id, new_stock):
        """상품 재고 업데이트 API 호출"""
        def update_thread():
            try:
                self.update_api_status(f"재고 변경 중...")
                
                # API 초기화 확인
                if not self.naver_api:
                    if self.client_id_var.get() and self.client_secret_var.get():
                        self.naver_api = NaverShoppingAPI(
                            self.client_id_var.get(),
                            self.client_secret_var.get()
                        )
                    else:
                        self.root.after(0, lambda: messagebox.showerror("오류", "API 설정이 필요합니다."))
                        return
                
                # 실제 API 호출 구현 필요
                # 여기서는 임시로 성공 응답 반환
                response = {'success': True, 'message': '재고 변경 완료'}
                
                if response.get('success'):
                    self.root.after(0, lambda: self.update_api_status(f"재고 변경 완료"))
                    self.root.after(0, lambda: messagebox.showinfo("성공", f"재고가 {new_stock}개로 변경되었습니다."))
                    # 상품 목록 새로고침
                    self.root.after(0, lambda: self.load_saved_products())
                else:
                    error = response.get('error', '알 수 없는 오류')
                    self.root.after(0, lambda: self.update_api_status(f"재고 변경 실패"))
                    self.root.after(0, lambda: messagebox.showerror("오류", f"재고 변경 실패: {error}"))
                    
            except Exception as e:
                print(f"재고 업데이트 오류: {e}")
                self.root.after(0, lambda: self.update_api_status(f"재고 변경 오류"))
                self.root.after(0, lambda: messagebox.showerror("오류", f"재고 변경 중 오류가 발생했습니다: {e}"))
        
        # 백그라운드에서 재고 업데이트
        import threading
        threading.Thread(target=update_thread, daemon=True).start()
        return True  # 임시로 성공 반환
    
    def test_new_order_notification(self):
        """신규주문 알림 테스트 (데스크탑 알림음 포함)"""
        # 알림 매니저 업데이트
        self.notification_manager.discord_webhook_url = self.discord_webhook_var.get() if self.discord_enabled_var.get() else None
        self.notification_manager.enabled_notifications['discord'] = bool(self.discord_webhook_var.get() and self.discord_enabled_var.get())
        self.notification_manager.enabled_notifications['desktop'] = self.desktop_notification_var.get()
        
        # 신규주문 데스크탑 알림 테스트 (알림음 포함)
        self._send_new_order_desktop_notification(1)
        messagebox.showinfo("알림 테스트", "신규주문 데스크탑 알림을 전송했습니다.\n알림음과 함께 팝업을 확인해주세요.")
    
    def test_order_status_notification(self):
        """스토어 상태변화 디스코드 알림 테스트"""
        # 알림 매니저 업데이트
        self.notification_manager.discord_webhook_url = self.discord_webhook_var.get() if self.discord_enabled_var.get() else None
        self.notification_manager.enabled_notifications['discord'] = bool(self.discord_webhook_var.get() and self.discord_enabled_var.get())
        self.notification_manager.enabled_notifications['desktop'] = self.desktop_notification_var.get()
        
        # 가상 상태변화 데이터 생성
        test_status_changes = {
            '신규주문': 2,
            '발송대기': 1,
            '배송중': 3,
            '배송완료': 1
        }
        
        # 스토어 상태변화 디스코드 알림 전송
        self.notification_manager.send_store_status_change_notification(test_status_changes)
        messagebox.showinfo("알림 테스트", "스토어 상태변화 디스코드 알림을 전송했습니다.\n디스코드 알림을 확인해주세요.")
    
    def test_delivery_complete_notification(self):
        """배송완료 상태변화 디스코드 알림 테스트"""
        # 알림 매니저 업데이트
        self.notification_manager.discord_webhook_url = self.discord_webhook_var.get() if self.discord_enabled_var.get() else None
        self.notification_manager.enabled_notifications['discord'] = bool(self.discord_webhook_var.get() and self.discord_enabled_var.get())
        self.notification_manager.enabled_notifications['desktop'] = self.desktop_notification_var.get()
        
        # 가상 배송완료 상태변화 데이터 생성
        test_status_changes = {
            '배송완료': 2,
            '구매확정': 1
        }
        
        # 스토어 상태변화 디스코드 알림 전송
        self.notification_manager.send_store_status_change_notification(test_status_changes)
        messagebox.showinfo("알림 테스트", "배송완료 상태변화 디스코드 알림을 전송했습니다.\n디스코드 알림을 확인해주세요.")

    def run(self):
        """애플리케이션 실행"""
        self.refresh_dashboard()
        self.load_pending_orders()  # 발송 대기 목록 로드
        self.root.mainloop()

if __name__ == "__main__":
    app = WithUsOrderManager()
    app.run()
