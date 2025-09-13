"""
조건설정 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox

from ui_utils import BaseTab, enable_context_menu
from env_config import config


class ConditionSettingsTab(BaseTab):
    """조건설정 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.setup_styles()
        self.create_condition_settings_tab()
        self.setup_copy_paste_bindings()
        self.load_settings()
    
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
    
    def create_condition_settings_tab(self):
        """조건설정 탭 UI 생성"""
        # 스크롤 가능한 프레임 설정
        self.setup_scrollable_frame()
        
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
        
        # 상품 상태 설정
        product_status_frame = ttk.LabelFrame(self.scrollable_frame, text="📦 상품 상태 설정", style="Section.TLabelframe")
        product_status_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 상품 상태 체크박스들
        self.product_status_vars = {}
        product_status_options = [
            ('SALE', '판매중'),
            ('WAIT', '판매대기'),
            ('OUTOFSTOCK', '품절'),
            ('SUSPENSION', '판매중지'),
            ('CLOSE', '판매종료'),
            ('PROHIBITION', '판매금지')
        ]
        
        product_status_checkboxes_frame = ttk.Frame(product_status_frame)
        product_status_checkboxes_frame.pack(fill="x", padx=5, pady=2)
        
        for status, label in product_status_options:
            var = tk.BooleanVar()
            self.product_status_vars[status] = var
            
            cb = ttk.Checkbutton(product_status_checkboxes_frame, text=label, variable=var)
            cb.pack(side="left", padx=5, pady=2)
        
        # 상품 상태 저장 버튼
        product_status_buttons_frame = ttk.Frame(product_status_frame)
        product_status_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(product_status_buttons_frame, text="상품 상태 설정 저장", command=self.save_product_status_settings).pack(side="left", padx=5)
    
    def load_settings(self):
        """설정 로드"""
        try:
            # 대시보드 기간 설정 로드
            self.load_dashboard_settings()
            
            # 주문 상태 설정 로드
            self.load_order_status_settings()
            
            # 주문 컬럼 설정 로드
            self.load_order_column_settings()
            
            # 상품 상태 설정 로드
            self.load_product_status_settings()
            
        except Exception as e:
            print(f"조건설정 로드 오류: {e}")
    
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
    
    # 주문 상태 설정 메서드들
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
    
    # 주문 컬럼 설정 메서드들
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
    
    # 상품 상태 설정 메서드들
    def load_product_status_settings(self):
        """상품 상태 설정 로드"""
        try:
            # 환경 설정에서 상품 상태 조회
            saved_statuses = config.get('PRODUCT_STATUS_TYPES', 'SALE,WAIT,OUTOFSTOCK,SUSPENSION,CLOSE,PROHIBITION')
            status_list = [s.strip() for s in saved_statuses.split(',')]
            
            print(f"설정 로드 - 저장된 상품상태 문자열: {saved_statuses}")
            print(f"설정 로드 - 저장된 상품상태 리스트: {status_list}")
            
            for status, var in self.product_status_vars.items():
                is_checked = status in status_list
                var.set(is_checked)
                print(f"설정 로드 - {status}: {is_checked}")
            
        except Exception as e:
            print(f"상품 상태 설정 로드 오류: {e}")
            # 오류 시 기본값 설정
            for var in self.product_status_vars.values():
                var.set(True)
    
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