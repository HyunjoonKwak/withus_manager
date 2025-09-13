"""
API 테스트 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta, timezone
import json
import threading
import time

from ui_utils import BaseTab, run_in_thread, enable_context_menu


class APITestTab(BaseTab):
    """API 테스트 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.selected_date_range = None  # 선택된 날짜 범위 저장
        self.create_api_test_tab()
        self.setup_copy_paste_bindings()
    
    def create_api_test_tab(self):
        """API 테스트 탭 UI 생성"""
        # 상품 관리 테스트
        product_group = ttk.LabelFrame(self.frame, text="상품 관리")
        product_group.pack(fill="x", padx=5, pady=5)
        
        product_frame = ttk.Frame(product_group)
        product_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(product_frame, text="GET /products (상품목록조회)", command=self.test_get_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_frame, text="GET /products/{id} (상품상세조회)", command=self.test_get_product_detail).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_frame, text="GET /products/channel-products/{id} (채널상품조회)", command=self.test_get_channel_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(product_frame, text="GET /products/origin-products/{id} (원상품조회)", command=self.test_get_origin_product).pack(side=tk.LEFT, padx=5)
        
        # 주문 관리 테스트
        order_group = ttk.LabelFrame(self.frame, text="주문 관리")
        order_group.pack(fill="x", padx=5, pady=5)
        
        # 시간 범위 테스트
        time_range_frame = ttk.Frame(order_group)
        time_range_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(time_range_frame, text="시간 범위:").pack(side=tk.LEFT, padx=5)
        
        # 시간 범위 버튼들 - 클릭 시 날짜 범위 저장
        self.btn_1day = ttk.Button(time_range_frame, text="1일", command=lambda: self.select_date_range_and_test(1))
        self.btn_1day.pack(side=tk.LEFT, padx=2)
        
        self.btn_2day = ttk.Button(time_range_frame, text="2일", command=lambda: self.select_date_range_and_test(2))
        self.btn_2day.pack(side=tk.LEFT, padx=2)
        
        self.btn_3day = ttk.Button(time_range_frame, text="3일", command=lambda: self.select_date_range_and_test(3))
        self.btn_3day.pack(side=tk.LEFT, padx=2)
        
        self.btn_7day = ttk.Button(time_range_frame, text="7일", command=lambda: self.select_date_range_and_test(7))
        self.btn_7day.pack(side=tk.LEFT, padx=2)
        
        # 선택된 범위 표시 라벨
        self.selected_range_label = ttk.Label(time_range_frame, text="", foreground="blue")
        self.selected_range_label.pack(side=tk.LEFT, padx=10)
        
        # 개별 주문 조회 테스트 버튼들 (기존 기능 유지)
        individual_test_frame = ttk.Frame(order_group)
        individual_test_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(individual_test_frame, text="개별 테스트:").pack(side=tk.LEFT, padx=5)
        ttk.Button(individual_test_frame, text="1일 조회", command=lambda: self.test_get_orders_with_range(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(individual_test_frame, text="2일 조회", command=lambda: self.test_get_orders_with_range(2)).pack(side=tk.LEFT, padx=2)
        ttk.Button(individual_test_frame, text="3일 조회", command=lambda: self.test_get_orders_with_range(3)).pack(side=tk.LEFT, padx=2)
        ttk.Button(individual_test_frame, text="7일 조회", command=lambda: self.test_get_orders_with_range(7)).pack(side=tk.LEFT, padx=2)
        
        order_frame2 = ttk.Frame(order_group)
        order_frame2.pack(fill=tk.X, pady=2)
        
        ttk.Button(order_frame2, text="GET /orders/{id}/product-order-ids", command=self.test_order_product_ids).pack(side=tk.LEFT, padx=5)
        ttk.Button(order_frame2, text="GET /product-orders/last-changed-statuses", command=self.test_last_changed_orders).pack(side=tk.LEFT, padx=5)
        
        # 주문 상태 관리
        order_status_frame = ttk.Frame(order_group)
        order_status_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(order_status_frame, text="PUT 주문상태변경", command=self.test_change_order_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(order_status_frame, text="PUT 배송정보업데이트", command=self.test_update_shipping_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(order_status_frame, text="GET 배송업체목록", command=self.test_delivery_companies).pack(side=tk.LEFT, padx=5)
        
        # 클레임 관리
        claim_frame = ttk.Frame(order_group)
        claim_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(claim_frame, text="GET 클레임조회", command=self.test_order_claims).pack(side=tk.LEFT, padx=5)
        ttk.Button(claim_frame, text="GET 상세통계", command=self.test_order_statistics).pack(side=tk.LEFT, padx=5)
        ttk.Button(claim_frame, text="📋 자동분석: 주문→상품목록", command=self.test_order_to_product_ids).pack(side=tk.LEFT, padx=5)
        
        # 기타 테스트
        other_group = ttk.LabelFrame(self.frame, text="기타")
        other_group.pack(fill="x", padx=5, pady=5)
        
        other_frame = ttk.Frame(other_group)
        other_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(other_frame, text="GET /seller/account (판매자계정조회)", command=self.test_seller_account).pack(side=tk.LEFT, padx=5)
        
        # 요청/응답 표시 영역 (탭 구조로 변경)
        request_response_frame = ttk.Frame(self.frame)
        request_response_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 탭 노트북 생성
        self.info_notebook = ttk.Notebook(request_response_frame)
        self.info_notebook.pack(fill="both", expand=True)
        
        # 요청 정보 탭
        request_tab = ttk.Frame(self.info_notebook)
        self.info_notebook.add(request_tab, text="📤 요청 정보")
        
        self.request_text = tk.Text(request_tab, height=12, wrap=tk.WORD, font=("Consolas", 12))
        request_scrollbar = ttk.Scrollbar(request_tab, orient="vertical", command=self.request_text.yview)
        self.request_text.configure(yscrollcommand=request_scrollbar.set)
        
        self.request_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        request_scrollbar.pack(side="right", fill="y", pady=5)
        
        # 응답 정보 탭
        response_tab = ttk.Frame(self.info_notebook)
        self.info_notebook.add(response_tab, text="📥 응답 요약")
        
        self.response_text = tk.Text(response_tab, height=12, wrap=tk.WORD, font=("Consolas", 12))
        response_scrollbar = ttk.Scrollbar(response_tab, orient="vertical", command=self.response_text.yview)
        self.response_text.configure(yscrollcommand=response_scrollbar.set)
        
        self.response_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        response_scrollbar.pack(side="right", fill="y", pady=5)
        
        # RAW 데이터 탭 (새로 추가)
        raw_tab = ttk.Frame(self.info_notebook)
        self.info_notebook.add(raw_tab, text="🔍 RAW 데이터")
        
        self.raw_data_text = tk.Text(raw_tab, height=12, wrap=tk.NONE, font=("Consolas", 11))
        raw_v_scrollbar = ttk.Scrollbar(raw_tab, orient="vertical", command=self.raw_data_text.yview)
        raw_h_scrollbar = ttk.Scrollbar(raw_tab, orient="horizontal", command=self.raw_data_text.xview)
        self.raw_data_text.configure(yscrollcommand=raw_v_scrollbar.set, xscrollcommand=raw_h_scrollbar.set)
        
        self.raw_data_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        raw_v_scrollbar.pack(side="right", fill="y", pady=5)
        raw_h_scrollbar.pack(side="bottom", fill="x", padx=5)
        
        # 터미널 로그 탭 (실시간 로그)
        log_tab = ttk.Frame(self.info_notebook)
        self.info_notebook.add(log_tab, text="🖥️ 터미널 로그")
        
        self.terminal_log_text = tk.Text(log_tab, height=12, wrap=tk.WORD, font=("Consolas", 11), bg="black", fg="green")
        terminal_scrollbar = ttk.Scrollbar(log_tab, orient="vertical", command=self.terminal_log_text.yview)
        self.terminal_log_text.configure(yscrollcommand=terminal_scrollbar.set)
        
        self.terminal_log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        terminal_scrollbar.pack(side="right", fill="y", pady=5)
        
        # 상태 표시
        self.api_status_var = tk.StringVar()
        self.api_status_var.set("대기 중...")
        status_label = ttk.Label(self.frame, textvariable=self.api_status_var)
        status_label.pack(pady=5)
        
        # 컨텍스트 메뉴 활성화 (모든 텍스트 위젯)
        enable_context_menu(self.request_text)
        enable_context_menu(self.response_text)
        enable_context_menu(self.raw_data_text)
        enable_context_menu(self.terminal_log_text)
    
    def update_api_status(self, message):
        """API 상태 업데이트"""
        self.api_status_var.set(message)
    
    def show_api_error(self, message):
        """API 오류 표시"""
        messagebox.showerror("API 오류", message)
    
    def update_raw_data(self, raw_response):
        """RAW 데이터 탭 업데이트"""
        if raw_response:
            raw_content = f"""=== RAW API 응답 데이터 ===
타임스탬프: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{json.dumps(raw_response, indent=2, ensure_ascii=False)}

=== 데이터 구조 분석 ===
응답 타입: {type(raw_response)}
"""
            if isinstance(raw_response, dict):
                raw_content += f"최상위 키들: {list(raw_response.keys())}\n"
                if 'data' in raw_response:
                    data_content = raw_response['data']
                    raw_content += f"data 타입: {type(data_content)}\n"
                    if isinstance(data_content, dict):
                        raw_content += f"data 키들: {list(data_content.keys())}\n"
            
            self.raw_data_text.delete(1.0, tk.END)
            self.raw_data_text.insert(1.0, raw_content)
            
    def add_terminal_log(self, message):
        """터미널 로그 탭에 로그 추가 (실시간)"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        # 자동 스크롤을 위해 맨 끝에 삽입
        self.terminal_log_text.insert(tk.END, log_entry)
        self.terminal_log_text.see(tk.END)
        
        # 너무 많은 로그가 쌓이지 않도록 제한 (최대 1000줄)
        lines = int(self.terminal_log_text.index(tk.END).split('.')[0])
        if lines > 1000:
            self.terminal_log_text.delete(1.0, "100.0")
    
    def clear_all_tabs(self):
        """모든 탭 내용 초기화"""
        self.request_text.delete(1.0, tk.END)
        self.response_text.delete(1.0, tk.END)
        self.raw_data_text.delete(1.0, tk.END)
        self.terminal_log_text.delete(1.0, tk.END)
    
    def select_date_range_and_test(self, days):
        """날짜 범위만 선택 (주문 조회는 실행하지 않음)"""
        # 날짜 범위 계산 및 저장
        kst = timezone(timedelta(hours=9))
        now = datetime.now(kst)
        past_time = now - timedelta(days=days)
        
        self.selected_date_range = {
            'days': days,
            'start_date': past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'end_date': now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'start_time': past_time,
            'end_time': now
        }
        
        # 선택된 범위 표시 업데이트
        range_text = f"✅ {days}일 선택됨 ({past_time.strftime('%m/%d %H:%M')} ~ {now.strftime('%m/%d %H:%M')})"
        self.selected_range_label.config(text=range_text)
        
        # 상태 메시지 업데이트
        self.update_api_status(f"📅 {days}일 범위 선택됨 - 자동분석 버튼을 눌러 주문을 조회하세요")
        
        # 요청 영역에 선택 정보 표시
        selection_info = f"""📅 날짜 범위 선택됨

선택된 범위: {days}일
시작 시간: {past_time.strftime('%Y-%m-%d %H:%M:%S')} (KST)
종료 시간: {now.strftime('%Y-%m-%d %H:%M:%S')} (KST)

다음 단계:
📋 '자동분석: 주문→상품목록' 버튼을 클릭하면 이 기간의 주문을 조회합니다.
{f"* 24시간 초과이므로 {days}개 청크로 분할 처리됩니다." if days > 1 else "* 24시간 이내이므로 단일 호출로 처리됩니다."}
"""
        self.request_text.delete(1.0, tk.END)
        self.request_text.insert(1.0, selection_info)
    
    def test_get_products(self):
        """상품 목록 조회 테스트"""
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_get_products_thread)
    
    def _test_get_products_thread(self):
        """상품 목록 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status("상품 목록 조회 중..."))
            
            # 요청 정보 표시
            request_info = f"""상품 목록 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/products
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8
Parameters:
  page: 1
  size: 100
  productStatusTypes: SALE,OUTOFSTOCK,CLOSE,SUSPENSION,PROHIBITION

참고: 상품 상태별 필터링 적용
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 상품 목록 조회
            response = self.app.naver_api.get_products()
            
            if response:
                response_info = f"""상품 목록 조회 성공!
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("상품 목록 조회 성공"))
            else:
                error_info = "상품 목록 조회 실패\n응답이 없습니다."
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("상품 목록 조회 실패"))
                
        except Exception as e:
            error_info = f"상품 목록 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("상품 목록 조회 오류"))
    
    def test_get_product_detail(self):
        """상품 상세 조회 테스트"""
        product_id = tk.simpledialog.askstring("상품 ID 입력", "조회할 상품 ID를 입력하세요:")
        if not product_id:
            return
        
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_get_product_detail_thread, product_id)
    
    def _test_get_product_detail_thread(self, product_id):
        """상품 상세 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status(f"상품 상세 조회 중... (ID: {product_id})"))
            
            # 요청 정보 표시
            request_info = f"""상품 상세 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/products/{product_id}
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8

참고: 상품 ID {product_id}에 대한 상세 정보 조회
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 상품 상세 조회
            response = self.app.naver_api.get_product_detail(product_id)
            
            if response:
                response_info = f"""상품 상세 조회 성공!
상품 ID: {product_id}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("상품 상세 조회 성공"))
            else:
                error_info = f"상품 상세 조회 실패\n상품 ID: {product_id}\n응답이 없습니다."
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("상품 상세 조회 실패"))
                
        except Exception as e:
            error_info = f"상품 상세 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("상품 상세 조회 오류"))
    
    def test_get_channel_product(self):
        """채널상품 조회 테스트"""
        product_id = tk.simpledialog.askstring("채널상품 ID 입력", "조회할 채널상품 ID를 입력하세요:")
        if not product_id:
            return
        
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_get_channel_product_thread, product_id)
    
    def _test_get_channel_product_thread(self, product_id):
        """채널상품 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status(f"채널상품 조회 중... (ID: {product_id})"))
            
            # 요청 정보 표시
            request_info = f"""채널상품 조회 요청:
URL: {self.app.naver_api.base_url}/external/v2/products/channel-products/{product_id}
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8

참고: 채널상품 ID {product_id}에 대한 상세 정보 조회 (v2 API)
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 채널상품 조회
            response = self.app.naver_api.get_channel_product(product_id)
            
            if response:
                response_info = f"""채널상품 조회 성공!
채널상품 ID: {product_id}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("채널상품 조회 성공"))
            else:
                error_info = f"채널상품 조회 실패\n채널상품 ID: {product_id}\n응답이 없습니다."
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("채널상품 조회 실패"))
                
        except Exception as e:
            error_info = f"채널상품 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("채널상품 조회 오류"))
    
    def test_get_origin_product(self):
        """원상품 조회 테스트"""
        product_id = tk.simpledialog.askstring("원상품 ID 입력", "조회할 원상품 ID를 입력하세요:")
        if not product_id:
            return
        
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_get_origin_product_thread, product_id)
    
    def _test_get_origin_product_thread(self, product_id):
        """원상품 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status(f"원상품 조회 중... (ID: {product_id})"))
            
            # 요청 정보 표시
            request_info = f"""원상품 조회 요청:
URL: {self.app.naver_api.base_url}/external/v2/products/origin-products/{product_id}
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8

참고: 원상품 ID {product_id}에 대한 상세 정보 조회 (v2 API)
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 원상품 조회
            response = self.app.naver_api.get_origin_product(product_id)
            
            if response:
                response_info = f"""원상품 조회 성공!
원상품 ID: {product_id}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("원상품 조회 성공"))
            else:
                error_info = f"원상품 조회 실패\n원상품 ID: {product_id}\n응답이 없습니다."
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("원상품 조회 실패"))
                
        except Exception as e:
            error_info = f"원상품 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("원상품 조회 오류"))
    
    def test_get_orders_with_range(self, days):
        """지정된 일수로 주문 조회 테스트 (24시간 단위로 자동 분할)"""
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_get_orders_with_range_thread, days)
    
    def _test_get_orders_with_range_thread(self, days):
        """지정된 일수로 주문 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status(f"{days}일 범위 주문 조회 중... (24시간 단위 분할)"))
            
            # 한국 시간(KST) 기준으로 변환
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
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/product-orders
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Content-Type: application/json
  Accept: application/json
Parameters:
  from: {past_iso_format} ({days}일 전 시간) - 필수값
  to: {current_iso_format} (현재 시간)
  page: 1
  size: 100

실제 요청 URL:
{self.app.naver_api.base_url}/external/v1/pay-order/seller/product-orders?from={past_iso_format}&to={current_iso_format}&page=1&size=100

참고: {days}일 범위를 24시간 단위로 자동 분할하여 조회
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
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
                chunk_response = self.app.naver_api.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders', chunk_params)
                
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
                    
                    product_order_id = order.get('productOrderId', 'N/A')
                    response_info += f"""
{i}. Order ID: {order_id}
   Product Order ID: {product_order_id}
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
            
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
            self.app.root.after(0, lambda: self.update_api_status(f"{days}일 범위 주문 조회 완료 - {len(unique_orders)}건 ({total_chunks}개 청크)"))
            
        except Exception as e:
            error_info = f"{days}일 범위 주문 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status(f"{days}일 범위 주문 조회 오류"))
    
    def test_order_product_ids(self):
        """주문 상품 ID 조회 테스트"""
        order_id = tk.simpledialog.askstring("주문 ID 입력", "조회할 주문 ID를 입력하세요:")
        if not order_id:
            return
        
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_order_product_ids_thread, order_id)
    
    def _test_order_product_ids_thread(self, order_id):
        """주문 상품 ID 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status(f"주문 상품 ID 조회 중... (주문 ID: {order_id})"))
            
            # 요청 정보 표시
            request_info = f"""주문 상품 ID 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/orders/{order_id}/product-order-ids
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8

참고: 주문 ID {order_id}에 대한 상품 주문 ID 목록 조회
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 주문 상품 ID 조회
            response = self.app.naver_api.get_order_product_ids(order_id)
            
            if response:
                response_info = f"""주문 상품 ID 조회 성공!
주문 ID: {order_id}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("주문 상품 ID 조회 성공"))
            else:
                error_info = f"주문 상품 ID 조회 실패\n주문 ID: {order_id}\n응답이 없습니다."
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("주문 상품 ID 조회 실패"))
                
        except Exception as e:
            error_info = f"주문 상품 ID 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("주문 상품 ID 조회 오류"))
    
    def test_last_changed_orders(self):
        """변경된 주문 조회 테스트"""
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_last_changed_orders_thread)
    
    def _test_last_changed_orders_thread(self):
        """변경된 주문 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status("변경된 주문 조회 중..."))
            
            # 한국 시간(KST) 기준으로 변환
            kst = timezone(timedelta(hours=9))
            now = datetime.now(kst)
            last_changed_from = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
            # 요청 정보 표시
            request_info = f"""변경된 주문 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/product-orders/last-changed-statuses
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8
Parameters:
  lastChangedFrom: {last_changed_from}
  lastChangedType: PAYED

참고: 24시간 전부터 현재까지 변경된 주문 조회
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 변경된 주문 조회
            response = self.app.naver_api.get_last_changed_orders(last_changed_from)
            
            if response:
                response_info = f"""변경된 주문 조회 성공!
조회 시작 시간: {last_changed_from}
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("변경된 주문 조회 성공"))
            else:
                error_info = "변경된 주문 조회 실패\n응답이 없습니다."
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("변경된 주문 조회 실패"))
                
        except Exception as e:
            error_info = f"변경된 주문 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("변경된 주문 조회 오류"))
    
    def test_seller_account(self):
        """판매자 계정 정보 조회 테스트"""
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_seller_account_thread)
    
    def _test_seller_account_thread(self):
        """판매자 계정 정보 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status("판매자 계정 정보 조회 중..."))
            
            # 요청 정보 표시
            request_info = f"""판매자 계정 정보 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/seller/account
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8
  
참고: 네이버 커머스 API 공식 문서에 따른 정확한 엔드포인트 사용
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 판매자 계정 정보 조회
            response = self.app.naver_api.make_authenticated_request('GET', '/external/v1/seller/account')
            
            if response:
                # RAW 데이터 및 터미널 로그 업데이트
                response_copy = response.copy()
                self.app.root.after(0, lambda: self.update_raw_data(response_copy))
                if 'terminal_log' in response:
                    self.app.root.after(0, lambda: self.add_terminal_log(response['terminal_log']))
                
                response_info = f"""판매자 계정 정보 조회 성공!
응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("판매자 계정 정보 조회 성공"))
            else:
                error_info = f"""판매자 계정 정보 조회 실패

가능한 원인:
1. 토큰이 유효하지 않음
2. API 권한 부족
3. 애플리케이션 상태 문제

해결 방법:
1. 토큰 재발급 시도
2. 네이버 API 센터에서 권한 확인
3. 애플리케이션 상태 확인
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("판매자 계정 정보 조회 실패"))
                
        except Exception as e:
            error_info = f"판매자 계정 정보 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("판매자 계정 정보 조회 오류"))
    
    # 새로 추가된 주문관리 API 테스트 메서드들
    
    def test_change_order_status(self):
        """주문 상태 변경 테스트"""
        product_order_id = tk.simpledialog.askstring("상품주문 ID 입력", "상태를 변경할 상품주문 ID를 입력하세요:")
        if not product_order_id:
            return
        
        status = tk.simpledialog.askstring("상태 입력", "변경할 상태를 입력하세요 (예: READY, SHIPPED, DELIVERED):")
        if not status:
            return
        
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_change_order_status_thread, product_order_id, status)
    
    def _test_change_order_status_thread(self, product_order_id, status):
        """주문 상태 변경 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status(f"주문 상태 변경 중... (ID: {product_order_id}, 상태: {status})"))
            
            # 요청 정보 표시
            request_info = f"""주문 상태 변경 요청:
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/product-orders/{product_order_id}/status
Method: PUT
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Content-Type: application/json
Body:
  {{
    "status": "{status}"
  }}

참고: 상품주문 ID {product_order_id}의 상태를 {status}로 변경
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 주문 상태 변경
            response = self.app.naver_api.change_order_status(product_order_id, status)
            
            if response and response.get('success'):
                response_info = f"""주문 상태 변경 성공!
상품주문 ID: {product_order_id}
변경된 상태: {status}

응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("주문 상태 변경 성공"))
            else:
                error_info = f"주문 상태 변경 실패\n상품주문 ID: {product_order_id}\n오류: {response.get('error', '알 수 없는 오류') if response else '응답 없음'}"
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("주문 상태 변경 실패"))
                
        except Exception as e:
            error_info = f"주문 상태 변경 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("주문 상태 변경 오류"))
    
    def test_update_shipping_info(self):
        """배송 정보 업데이트 테스트"""
        product_order_id = tk.simpledialog.askstring("상품주문 ID 입력", "배송 정보를 업데이트할 상품주문 ID를 입력하세요:")
        if not product_order_id:
            return
        
        delivery_company = tk.simpledialog.askstring("배송업체 입력", "배송업체를 입력하세요 (예: CJ대한통운):")
        if not delivery_company:
            return
            
        tracking_number = tk.simpledialog.askstring("송장번호 입력", "송장번호를 입력하세요:")
        if not tracking_number:
            return
        
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_update_shipping_info_thread, product_order_id, delivery_company, tracking_number)
    
    def _test_update_shipping_info_thread(self, product_order_id, delivery_company, tracking_number):
        """배송 정보 업데이트 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status(f"배송 정보 업데이트 중... (ID: {product_order_id})"))
            
            # 요청 정보 표시
            request_info = f"""배송 정보 업데이트 요청:
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/product-orders/{product_order_id}/shipping
Method: PUT
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Content-Type: application/json
Body:
  {{
    "deliveryCompany": "{delivery_company}",
    "trackingNumber": "{tracking_number}"
  }}

참고: 상품주문 ID {product_order_id}의 배송 정보 업데이트
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 배송 정보 업데이트
            response = self.app.naver_api.update_shipping_info(product_order_id, delivery_company, tracking_number)
            
            if response and response.get('success'):
                response_info = f"""배송 정보 업데이트 성공!
상품주문 ID: {product_order_id}
배송업체: {delivery_company}
송장번호: {tracking_number}

응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("배송 정보 업데이트 성공"))
            else:
                error_info = f"배송 정보 업데이트 실패\n상품주문 ID: {product_order_id}\n오류: {response.get('error', '알 수 없는 오류') if response else '응답 없음'}"
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("배송 정보 업데이트 실패"))
                
        except Exception as e:
            error_info = f"배송 정보 업데이트 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("배송 정보 업데이트 오류"))
    
    def test_delivery_companies(self):
        """배송업체 목록 조회 테스트"""
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_delivery_companies_thread)
    
    def _test_delivery_companies_thread(self):
        """배송업체 목록 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status("배송업체 목록 조회 중..."))
            
            # 요청 정보 표시
            request_info = f"""배송업체 목록 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/delivery-companies
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8

참고: 사용 가능한 배송업체 목록 조회
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 배송업체 목록 조회
            response = self.app.naver_api.get_delivery_companies()
            
            if response and response.get('success'):
                response_info = f"""배송업체 목록 조회 성공!

응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("배송업체 목록 조회 성공"))
            else:
                error_info = f"배송업체 목록 조회 실패\n오류: {response.get('error', '알 수 없는 오류') if response else '응답 없음'}"
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("배송업체 목록 조회 실패"))
                
        except Exception as e:
            error_info = f"배송업체 목록 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("배송업체 목록 조회 오류"))
    
    def test_order_claims(self):
        """클레임 조회 테스트"""
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_order_claims_thread)
    
    def _test_order_claims_thread(self):
        """클레임 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status("클레임 조회 중..."))
            
            # 한국 시간(KST) 기준으로 변환
            kst = timezone(timedelta(hours=9))
            now = datetime.now(kst)
            past_time = now - timedelta(days=7)
            
            start_date = past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            end_date = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
            # 요청 정보 표시
            request_info = f"""클레임 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/claims
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8
Parameters:
  from: {start_date} (7일 전)
  to: {end_date} (현재)

참고: 최근 7일간 클레임(취소/반품/교환) 조회
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 클레임 조회
            response = self.app.naver_api.get_order_claims(start_date, end_date)
            
            if response and response.get('success'):
                response_info = f"""클레임 조회 성공!
조회 기간: {start_date} ~ {end_date}

응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("클레임 조회 성공"))
            else:
                error_info = f"클레임 조회 실패\n오류: {response.get('error', '알 수 없는 오류') if response else '응답 없음'}"
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("클레임 조회 실패"))
                
        except Exception as e:
            error_info = f"클레임 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("클레임 조회 오류"))
    
    def test_order_statistics(self):
        """주문 통계 조회 테스트"""
        if not self.app.naver_api:
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        run_in_thread(self._test_order_statistics_thread)
    
    def _test_order_statistics_thread(self):
        """주문 통계 조회 테스트 스레드"""
        try:
            self.app.root.after(0, lambda: self.update_api_status("주문 통계 조회 중..."))
            
            # 7일간의 통계 조회
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 요청 정보 표시
            request_info = f"""주문 통계 조회 요청:
URL: {self.app.naver_api.base_url}/external/v1/statistics/orders/detailed
Method: GET
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Accept: application/json;charset=UTF-8
Parameters:
  startDate: {start_date}
  endDate: {end_date}

참고: 최근 7일간 상세 주문 통계 조회
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 주문 통계 조회
            response = self.app.naver_api.get_order_statistics_detailed(start_date, end_date)
            
            if response and response.get('success'):
                response_info = f"""주문 통계 조회 성공!
조회 기간: {start_date} ~ {end_date}

응답 데이터:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, response_info))
                self.app.root.after(0, lambda: self.update_api_status("주문 통계 조회 성공"))
            else:
                error_info = f"주문 통계 조회 실패\n오류: {response.get('error', '알 수 없는 오류') if response else '응답 없음'}"
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("주문 통계 조회 실패"))
                
        except Exception as e:
            error_info = f"주문 통계 조회 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("주문 통계 조회 오류"))
    
    def test_order_to_product_ids(self):
        """주문 조회 후 자동으로 상품 목록 조회하는 통합 테스트"""
        print(f"\n🖱️ [UI 이벤트] 자동분석 버튼 클릭됨 - {datetime.now().strftime('%H:%M:%S')}")
        
        if not self.app.naver_api:
            print("❌ [UI 오류] API가 초기화되지 않음")
            self.show_api_error("API 설정이 필요합니다.")
            return
        
        print("✅ [UI 확인] API 초기화 완료, 백그라운드 스레드 시작")
        run_in_thread(self._test_order_to_product_ids_thread)
    
    def _test_order_to_product_ids_thread(self):
        """주문→상품목록 자동 분석 테스트 스레드"""
        try:
            print(f"🔄 [스레드 시작] 자동분석 스레드 실행 중 - {datetime.now().strftime('%H:%M:%S')}")
            # 모든 탭 초기화
            self.app.root.after(0, self.clear_all_tabs)
            self.app.root.after(0, lambda: self.add_terminal_log("🚀 자동분석 시작"))
            self.app.root.after(0, lambda: self.update_api_status("📋 1단계: 주문 조회 중..."))
            print("✅ [UI 업데이트] 탭 초기화 및 상태 메시지 업데이트 완료")
            
            # 선택된 날짜 범위 사용, 없으면 기본값(24시간)
            if self.selected_date_range:
                start_date = self.selected_date_range['start_date']
                end_date = self.selected_date_range['end_date']
                days = self.selected_date_range['days']
                range_description = f"선택된 {days}일 범위"
                self.app.root.after(0, lambda: self.add_terminal_log(f"📅 사용할 날짜 범위: {range_description} ({start_date} ~ {end_date})"))
            else:
                # 기본값: 최근 24시간
                kst = timezone(timedelta(hours=9))
                now = datetime.now(kst)
                past_time = now - timedelta(hours=24)
                start_date = past_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                end_date = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                days = 1
                range_description = "기본 24시간 범위"
                self.app.root.after(0, lambda: self.add_terminal_log(f"📅 기본 날짜 범위 사용: {range_description}"))
            
            # 요청 정보 표시
            request_info = f"""📋 주문→상품목록 자동 분석 테스트

=== 1단계: 주문 조회 ({range_description}) ===
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/product-orders
Method: GET
Parameters:
  from: {start_date} ({days}일 전)
  to: {end_date} (현재)
  page: 1
  size: 10 (최대 10개만 조회)

목적: {range_description}에서 주문을 조회하여 orderId와 productOrderId 추출
"""
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
            
            # 24시간 이상인 경우 분할 처리
            if days > 1:
                self.app.root.after(0, lambda: self.update_api_status(f"📋 1단계: {days}일 범위를 24시간 단위로 분할 조회 중..."))
                self.app.root.after(0, lambda: self.add_terminal_log(f"🔄 {days}일 범위 분할 처리 시작 (24시간 단위)"))
                
                # 24시간 단위로 분할해서 조회
                all_orders = []
                total_chunks = 0
                
                if self.selected_date_range:
                    current_start = self.selected_date_range['start_time']
                    end_time = self.selected_date_range['end_time']
                else:
                    kst = timezone(timedelta(hours=9))
                    current_start = datetime.now(kst) - timedelta(days=days)
                    end_time = datetime.now(kst)
                
                self.app.root.after(0, lambda: self.add_terminal_log(f"📊 예상 청크 수: {days}개 (24시간 단위)"))
                
                while current_start < end_time:
                    # 24시간 단위로 종료 시간 설정
                    current_end = min(current_start + timedelta(hours=24), end_time)
                    
                    total_chunks += 1
                    chunk_start_iso = current_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    chunk_end_iso = current_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    
                    chunk_info = f"청크 {total_chunks}: {current_start.strftime('%Y-%m-%d %H:%M')} ~ {current_end.strftime('%Y-%m-%d %H:%M')}"
                    self.app.root.after(0, lambda msg=chunk_info: self.add_terminal_log(msg))
                    
                    # 청크별 상태 업데이트
                    self.app.root.after(0, lambda c=total_chunks: self.update_api_status(f"📋 1단계: 청크 {c}/{days} 처리 중..."))
                    
                    # 해당 청크의 주문 조회
                    chunk_params = {
                        'from': chunk_start_iso,
                        'to': chunk_end_iso,
                        'page': 1,
                        'size': 100
                    }
                    
                    self.app.root.after(0, lambda: self.add_terminal_log(f"🌐 API 호출: GET /external/v1/pay-order/seller/product-orders"))
                    self.app.root.after(0, lambda params=chunk_params: self.add_terminal_log(f"📋 파라미터: {params}"))
                    
                    chunk_response = self.app.naver_api.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders', chunk_params)
                    
                    if chunk_response and chunk_response.get('success'):
                        # 첫 번째 청크의 RAW 데이터 저장 (대표 샘플로)
                        if total_chunks == 1:
                            # 응답 복사본을 만들어 전달
                            response_copy = chunk_response.copy()
                            self.app.root.after(0, lambda: self.update_raw_data(response_copy))
                            # 터미널 로그도 업데이트
                            if 'terminal_log' in chunk_response:
                                self.app.root.after(0, lambda: self.add_terminal_log(chunk_response['terminal_log']))
                        
                        # 청크 응답 데이터 분석 (중첩된 구조에서 실제 네이버 API 응답 추출)
                        api_response = chunk_response.get('data', {})
                        chunk_data = api_response.get('data', {}) if isinstance(api_response, dict) else {}
                        print(f"  🔍 [청크 {total_chunks}] 데이터 구조 분석:")
                        print(f"    → chunk_response['data'] 키들: {list(api_response.keys()) if isinstance(api_response, dict) else 'Not a dict'}")
                        print(f"    → chunk_data 키들: {list(chunk_data.keys()) if isinstance(chunk_data, dict) else 'Not a dict'}")
                        chunk_orders = []
                        
                        response_time = chunk_response.get('response_details', {}).get('response_time', 'N/A')
                        self.app.root.after(0, lambda rt=response_time: self.add_terminal_log(f"⚡ 응답 시간: {rt}"))
                        
                        # 네이버 API 응답 구조 분석
                        if 'contents' in chunk_data:
                            # 새로운 API 구조 (contents 배열)
                            contents = chunk_data['contents']
                            for item in contents:
                                if isinstance(item, dict) and 'content' in item:
                                    content = item['content']
                                    if 'order' in content:
                                        order_info = content['order']
                                        chunk_orders.append({
                                            'orderId': order_info.get('orderId'),
                                            'productOrderId': item.get('productOrderId'),
                                            'ordererName': order_info.get('ordererName'),
                                            'orderDate': order_info.get('orderDate')
                                        })
                        elif 'data' in chunk_data and isinstance(chunk_data['data'], list):
                            # 기존 API 구조 (data 배열)
                            order_list = chunk_data['data']
                            for order in order_list:
                                if isinstance(order, dict):
                                    chunk_orders.append({
                                        'orderId': order.get('orderId'),
                                        'productOrderId': order.get('productOrderId'),
                                        'ordererName': order.get('ordererName', order.get('customerName')),
                                        'orderDate': order.get('orderDate')
                                    })
                        
                        all_orders.extend(chunk_orders)
                        success_msg = f"✅ 청크 {total_chunks} 성공: {len(chunk_orders)}건 조회"
                        self.app.root.after(0, lambda msg=success_msg: self.add_terminal_log(msg))
                    else:
                        error_msg = f"❌ 청크 {total_chunks} 실패"
                        if chunk_response:
                            error_msg += f": {chunk_response.get('error', '알 수 없는 오류')}"
                        self.app.root.after(0, lambda msg=error_msg: self.add_terminal_log(msg))
                    
                    # API 호출 간격 (0.5초)
                    time.sleep(0.5)
                    current_start = current_end
                
                summary_msg = f"🎉 전체 청크 조회 완료: {total_chunks}개 청크, 총 {len(all_orders)}건"
                self.app.root.after(0, lambda msg=summary_msg: self.add_terminal_log(msg))
                
                # 중복 제거 (orderId 기준)
                unique_orders = []
                seen_order_ids = set()
                for order in all_orders:
                    if isinstance(order, dict):
                        order_id = order.get('orderId')
                        if order_id and order_id not in seen_order_ids:
                            seen_order_ids.add(order_id)
                            unique_orders.append(order)
                
                orders = unique_orders
                dedup_msg = f"🔄 중복 제거: {len(all_orders)}건 → {len(orders)}건"
                self.app.root.after(0, lambda msg=dedup_msg: self.add_terminal_log(msg))
                
                # 분할 조회 결과를 request_info에 업데이트
                request_info += f"""
=== 분할 조회 상세 정보 ===
- 총 청크 수: {total_chunks}개 (24시간 단위)
- 조회된 주문: {len(all_orders)}건
- 중복 제거 후: {len(orders)}건
- 처리 시간: 약 {total_chunks * 0.5:.1f}초
"""
                self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.request_text.insert(1.0, request_info))
                
            else:
                # 24시간 이하인 경우 단일 호출
                params = {
                    'from': start_date,
                    'to': end_date,
                    'page': 1,
                    'size': 10
                }
                response = self.app.naver_api.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders', params)
                
                if not response or not response.get('success'):
                    error_info = f"1단계 실패: 주문 조회 오류\n오류: {response.get('error', '알 수 없는 오류') if response else '응답 없음'}"
                    self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                    self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                    self.app.root.after(0, lambda: self.update_api_status("📋 자동 분석 실패"))
                    return
                
                # 응답에서 주문 데이터 추출
                data = response.get('data', {})
                orders = []
                
                # 네이버 API 응답 구조 분석
                if 'contents' in data:
                    # 새로운 API 구조 (contents 배열)
                    contents = data['contents']
                    for item in contents:
                        if isinstance(item, dict) and 'content' in item:
                            content = item['content']
                            if 'order' in content:
                                order_info = content['order']
                                orders.append({
                                    'orderId': order_info.get('orderId'),
                                    'productOrderId': item.get('productOrderId'),
                                    'ordererName': order_info.get('ordererName'),
                                    'orderDate': order_info.get('orderDate')
                                })
                elif 'data' in data and isinstance(data['data'], list):
                    # 기존 API 구조 (data 배열)
                    order_list = data['data']
                    for order in order_list:
                        if isinstance(order, dict):
                            orders.append({
                                'orderId': order.get('orderId'),
                                'productOrderId': order.get('productOrderId'),
                                'ordererName': order.get('ordererName', order.get('customerName')),
                                'orderDate': order.get('orderDate')
                            })
            
            if not orders:
                error_info = f"""1단계 완료: 주문이 없습니다
조회 범위: {range_description}
조회 기간: {start_date} ~ {end_date}
{f"분할 조회: {total_chunks}개 청크 처리" if days > 1 else "단일 조회"}

해당 기간에 주문이 없거나 API 응답에 문제가 있을 수 있습니다.
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("📋 주문 데이터 없음"))
                return
            
            # 첫 번째 주문 선택
            first_order = orders[0]
            order_id = first_order.get('orderId')
            
            if not order_id:
                error_info = f"1단계 완료: orderId를 찾을 수 없습니다\n주문 데이터: {json.dumps(first_order, indent=2, ensure_ascii=False)}"
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("📋 orderId 없음"))
                return
            
            # 1단계 결과 표시
            stage1_result = f"""📋 1단계 완료: 주문 조회 성공!
조회 범위: {range_description}
발견된 주문: {len(orders)}건
{f"처리 방식: 24시간 단위 분할 조회 ({total_chunks}개 청크)" if days > 1 else "처리 방식: 단일 API 호출"}

선택된 주문:
- 주문 ID: {order_id}
- 상품주문 ID: {first_order.get('productOrderId', 'N/A')}
- 주문자: {first_order.get('ordererName', 'N/A')}
- 주문일시: {first_order.get('orderDate', 'N/A')}

다음: 2단계로 진행 (상품 주문 상세 정보 조회)
"""
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, stage1_result))
            self.app.root.after(0, lambda: self.update_api_status("📋 2단계: 상품 주문 ID 목록 조회 중..."))
            
            # 짧은 대기 시간
            time.sleep(1)
            
            # 2단계: 상품 주문 상세 정보 조회 (query API 사용)
            product_order_id = first_order.get('productOrderId')
            
            if not product_order_id:
                error_info = f"""📋 2단계 실패: productOrderId를 찾을 수 없습니다
선택된 주문 데이터: {json.dumps(first_order, indent=2, ensure_ascii=False)}

productOrderId가 없으면 상세 조회를 할 수 없습니다.
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("📋 productOrderId 없음"))
                return
            
            stage2_request = f"""
=== 2단계: 상품 주문 상세 정보 조회 (query API) ===
URL: {self.app.naver_api.base_url}/external/v1/pay-order/seller/product-orders/query
Method: POST
Headers:
  Authorization: Bearer {self.app.naver_api.access_token[:20] if self.app.naver_api.access_token else 'None'}...
  Content-Type: application/json
Body:
  {{
    "productOrderIds": ["{product_order_id}"]
  }}

목적: 상품 주문 ID {product_order_id}에 대한 상세 정보 조회
"""
            
            current_request = request_info + stage2_request
            self.app.root.after(0, lambda: self.request_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.request_text.insert(1.0, current_request))
            
            # 상품 주문 상세 정보 조회 (query API 사용)
            self.app.root.after(0, lambda: self.add_terminal_log(f"🔍 2단계: query API 호출 시작"))
            self.app.root.after(0, lambda: self.add_terminal_log(f"📋 상품주문 ID: {product_order_id}"))
            
            query_response = self.app.naver_api.query_orders_by_ids([product_order_id])
            
            if query_response and query_response.get('success'):
                # RAW 데이터 업데이트 (query API 응답으로)
                query_copy = query_response.copy()
                self.app.root.after(0, lambda: self.update_raw_data(query_copy))
                # 터미널 로그도 업데이트
                if 'terminal_log' in query_response:
                    self.app.root.after(0, lambda: self.add_terminal_log(query_response['terminal_log']))
                
                # 응답 데이터 분석 (중첩된 구조에서 실제 네이버 API 응답 추출)
                api_response = query_response.get('data', {})
                query_data = api_response.get('data', {}) if isinstance(api_response, dict) else {}
                print(f"  🔍 [2단계 query] 데이터 구조 분석:")
                print(f"    → query_response['data'] 키들: {list(api_response.keys()) if isinstance(api_response, dict) else 'Not a dict'}")
                print(f"    → query_data 키들: {list(query_data.keys()) if isinstance(query_data, dict) else 'Not a dict'}")
                
                query_response_time = query_response.get('response_details', {}).get('response_time', 'N/A')
                self.app.root.after(0, lambda rt=query_response_time: self.add_terminal_log(f"⚡ query API 응답 시간: {rt}"))
                self.app.root.after(0, lambda: self.add_terminal_log(f"✅ 2단계 완료: 상품 주문 상세 정보 조회 성공"))
                
                # 최종 결과 표시
                # 주문 정보 테이블 생성
                order_table = self._create_order_summary_table(orders, days, total_chunks if days > 1 else 1)
                
                # ProductOrderId 별 상세 정보 테이블 생성  
                product_detail_table = self._create_product_order_detail_table(query_data, product_order_id)
                
                final_result = f"""📋 자동 분석 완료! ✅

=== 📊 주문 수집 요약 테이블 ===
{order_table}

=== 🔍 상품주문 상세 정보 테이블 ===
{product_detail_table}

=== 📈 처리 통계 ===
┌────────────────────────────────────────┬─────────────┐
│ 항목                                   │ 값          │
├────────────────────────────────────────┼─────────────┤
│ 조회 범위                              │ {range_description} │
│ 조회 기간                              │ {start_date[:10]} ~ {end_date[:10]} │
│ 발견된 주문                            │ {len(orders)}건 │
│ 처리 방식                              │ {"24시간 단위 분할" if days > 1 else "단일 API 호출"} │
│ 청크 수                                │ {total_chunks if days > 1 else 1}개 │
│ 선택된 주문 ID                         │ {order_id} │
│ 선택된 상품주문 ID                     │ {product_order_id} │
└────────────────────────────────────────┴─────────────┘

=== ✅ 분석 완료 ===
주문에서 상품 상세 정보까지 완전한 데이터 흐름 분석 완료!
• 단계별 처리: 주문 조회 → ProductOrderId 추출 → 상품 상세 조회
• 활용 가능: 주문 처리, 배송 관리, 상태 변경, 재고 관리 등
• 데이터 구조: 정규화된 테이블 형태로 정리됨
"""
                print(f"📝 [최종 결과] UI 업데이트 시작 - 텍스트 길이: {len(final_result)} characters")
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, final_result))
                self.app.root.after(0, lambda: self.update_api_status("📋 자동 분석 완료 ✅"))
                print("✅ [UI 완료] 최종 결과 UI 업데이트 완료")
            else:
                error_info = f"""📋 2단계 실패: 상품 주문 상세 정보 조회 오류
상품주문 ID: {product_order_id}
오류: {query_response.get('error', '알 수 없는 오류') if query_response else '응답 없음'}

사용한 API: POST /external/v1/pay-order/seller/product-orders/query
요청 데이터: {{"productOrderIds": ["{product_order_id}"]}}

1단계는 성공했으나 2단계 query API 호출에서 실패했습니다.
상품주문 ID가 유효하지 않거나 API 권한 문제일 수 있습니다.

전체 응답:
{json.dumps(query_response, indent=2, ensure_ascii=False) if query_response else 'None'}
"""
                self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
                self.app.root.after(0, lambda: self.update_api_status("📋 2단계 실패"))
                
        except Exception as e:
            error_info = f"📋 자동 분석 오류: {str(e)}"
            self.app.root.after(0, lambda: self.response_text.delete(1.0, tk.END))
            self.app.root.after(0, lambda: self.response_text.insert(1.0, error_info))
            self.app.root.after(0, lambda: self.update_api_status("📋 자동 분석 오류"))
    
    def _create_order_summary_table(self, orders, days, chunks):
        """주문 수집 요약 테이블 생성"""
        if not orders:
            return "📋 수집된 주문이 없습니다."
        
        # 테이블 헤더
        table = """┌──────┬──────────────────────┬──────────────────────┬─────────────────────┬──────────────┐
│ 순번 │ OrderId              │ ProductOrderId       │ 주문자              │ 주문일시     │
├──────┼──────────────────────┼──────────────────────┼─────────────────────┼──────────────┤"""
        
        # 주문 데이터 추가 (최대 10개)
        for i, order in enumerate(orders[:10], 1):
            order_id = str(order.get('orderId', 'N/A'))[:20]
            product_order_id = str(order.get('productOrderId', 'N/A'))[:20]
            orderer_name = str(order.get('ordererName', 'N/A'))[:19]
            order_date = str(order.get('orderDate', 'N/A'))[:12]
            
            # 각 필드를 고정 길이로 맞춤
            table += f"\n│ {i:4d} │ {order_id:20s} │ {product_order_id:20s} │ {orderer_name:19s} │ {order_date:12s} │"
        
        # 더 많은 주문이 있는 경우
        if len(orders) > 10:
            table += f"\n│ ...  │ ... ({len(orders)-10}건 더)      │                      │                     │              │"
        
        table += "\n└──────┴──────────────────────┴──────────────────────┴─────────────────────┴──────────────┘"
        
        # 수집 통계 추가
        stats = f"""
📊 수집 통계:
• 총 주문 건수: {len(orders)}건
• 처리 청크 수: {chunks}개 (24시간 단위)
• 처리 기간: {days}일
• ProductOrderId 수집: {len([o for o in orders if o.get('productOrderId')])}개"""
        
        return table + stats
    
    def _create_product_order_detail_table(self, query_data, product_order_id):
        """상품주문 상세 정보 테이블 생성"""
        if not query_data or not isinstance(query_data, dict):
            return f"📋 ProductOrderId {product_order_id}에 대한 상세 정보가 없습니다."
        
        # 기본 정보 테이블
        table = f"""┌─────────────────────────────────────────┬─────────────────────────────────┐
│ 항목                                    │ 값                              │
├─────────────────────────────────────────┼─────────────────────────────────┤
│ ProductOrderId                          │ {str(product_order_id)[:31]:31s} │"""
        
        # 주요 필드들 추가
        key_fields = [
            ('orderId', '주문 ID'),
            ('orderStatus', '주문 상태'),
            ('productName', '상품명'),
            ('optionCode', '옵션 코드'),
            ('quantity', '수량'),
            ('unitPrice', '단가'),
            ('totalPrice', '총 금액'),
            ('deliveryFee', '배송비'),
            ('ordererName', '주문자명'),
            ('receiverName', '수취인명'),
            ('receiverAddress', '배송주소'),
            ('receiverPhone', '연락처'),
            ('shippingCompany', '택배사'),
            ('trackingNumber', '송장번호')
        ]
        
        # query_data에서 실제 상품주문 정보 추출
        product_order_info = {}
        if 'data' in query_data and isinstance(query_data['data'], list):
            for item in query_data['data']:
                if isinstance(item, dict) and item.get('productOrderId') == product_order_id:
                    product_order_info = item
                    break
        elif isinstance(query_data, dict):
            product_order_info = query_data
        
        # 각 필드를 테이블에 추가
        for field_key, field_name in key_fields:
            value = product_order_info.get(field_key, 'N/A')
            if isinstance(value, (int, float)):
                value_str = f"{value:,}" if field_key in ['quantity', 'unitPrice', 'totalPrice', 'deliveryFee'] else str(value)
            else:
                value_str = str(value)[:31]
            
            table += f"\n│ {field_name:39s} │ {value_str:31s} │"
        
        table += "\n└─────────────────────────────────────────┴─────────────────────────────────┘"
        
        # 원시 데이터 요약 (키 값들만)
        raw_keys = list(product_order_info.keys()) if product_order_info else []
        if raw_keys:
            table += f"\n\n🔧 응답 데이터 키: {', '.join(raw_keys[:10])}"
            if len(raw_keys) > 10:
                table += f" ... ({len(raw_keys)}개 총)"
        
        return table
