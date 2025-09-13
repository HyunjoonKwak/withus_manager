"""
주문 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import json

from ui_utils import BaseTab, run_in_thread, enable_context_menu


class OrdersTab(BaseTab):
    """주문 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.last_orders_data = []  # 마지막으로 로드된 주문 데이터 저장
        self.last_api_orders = []  # 마지막 API 조회 결과 저장
        self.is_first_load = True  # 첫 로드 여부
        self.create_orders_tab()
        self.setup_copy_paste_bindings()
    
    def create_orders_tab(self):
        """주문 탭 UI 생성"""
        # 주문 수집 섹션
        collection_frame = ttk.LabelFrame(self.frame, text="주문 수집")
        collection_frame.pack(fill="x", padx=5, pady=5)
        
        # 날짜 선택
        date_frame = ttk.Frame(collection_frame)
        date_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(date_frame, text="시작일:").pack(side="left", padx=5)
        self.start_date_entry = DateEntry(date_frame, width=12, background='darkblue',
                                        foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_entry.pack(side="left", padx=5)
        
        ttk.Label(date_frame, text="종료일:").pack(side="left", padx=5)
        self.end_date_entry = DateEntry(date_frame, width=12, background='darkblue',
                                      foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_entry.pack(side="left", padx=5)
        
        # 기간 설정을 같은 줄에 추가
        ttk.Label(date_frame, text="기간설정:").pack(side="left", padx=(20, 5))
        
        # 기간 선택 콤보박스
        self.period_var = tk.StringVar()
        period_values = ["1일", "3일", "7일", "15일"]
        self.period_combo = ttk.Combobox(date_frame, textvariable=self.period_var, 
                                        values=period_values, width=8, state="readonly")
        self.period_combo.pack(side="left", padx=5)
        self.period_combo.bind("<<ComboboxSelected>>", self.on_period_selected)
        
        # 저장된 기간설정 로드
        from env_config import config
        saved_period = config.get_int('QUICK_PERIOD_SETTING', 7)
        self.period_var.set(f"{saved_period}일")
        
        # 적용 버튼
        ttk.Button(date_frame, text="적용", command=self.apply_period_setting).pack(side="left", padx=5)
        
        # 조회 버튼
        query_frame = ttk.Frame(collection_frame)
        query_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(query_frame, text="주문조회", command=self.query_orders_from_api).pack(side="left", padx=5)
        ttk.Button(query_frame, text="주문 재조회", command=self.refresh_orders).pack(side="left", padx=5)
        ttk.Button(query_frame, text="DB 조회", command=self.query_orders_from_db).pack(side="left", padx=5)
        
        # 주문 목록
        orders_frame = ttk.LabelFrame(self.frame, text="주문 목록")
        orders_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 전체 컬럼 정의
        self.all_columns = ['주문ID', '상품주문ID', '주문자', '상품명', '옵션정보', '판매자상품코드', '수량', '단가', '할인금액', '금액', '결제방법', '배송지주소', '배송예정일', '주문일시', '상태']
        
        # 현재 표시할 컬럼 가져오기
        columns = self.get_display_columns()
        
        # 스크롤바들을 위한 프레임 생성
        tree_frame = ttk.Frame(orders_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.orders_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # 컬럼별 너비 설정
        column_widths = {
            '주문ID': 120,
            '상품주문ID': 120,
            '주문자': 80,
            '상품명': 180,
            '옵션정보': 120,
            '판매자상품코드': 100,
            '수량': 50,
            '단가': 80,
            '할인금액': 80,
            '금액': 80,
            '결제방법': 80,
            '배송지주소': 200,
            '배송예정일': 100,
            '주문일시': 120,
            '상태': 60
        }
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
            width = column_widths.get(col, 120)
            self.orders_tree.column(col, width=width)
        
        # 세로 스크롤바
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # 가로 스크롤바
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.orders_tree.xview)
        self.orders_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 트리뷰와 스크롤바 배치 (grid 사용)
        self.orders_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # grid 가중치 설정
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        
        # 컬럼 드래그 앤 드롭 이벤트 바인딩
        self.orders_tree.bind('<ButtonPress-1>', self.on_column_drag_start)
        self.orders_tree.bind('<ButtonRelease-1>', self.on_column_drop)
        self.column_being_dragged = None
        
        # 컬럼 헤더 우클릭 메뉴 바인딩
        self.orders_tree.bind('<Button-3>', self.show_column_context_menu)  # 우클릭
        
        # 컬럼 너비 변경 감지 이벤트 바인딩
        self.orders_tree.bind('<ButtonRelease-1>', self.on_column_resize, add='+')  # 기존 이벤트에 추가
        
        # 상태 표시
        self.orders_status_var = tk.StringVar()
        self.orders_status_var.set("대기 중...")
        status_label = ttk.Label(self.frame, textvariable=self.orders_status_var)
        status_label.pack(pady=5)
        
        # 컨텍스트 메뉴 활성화
        enable_context_menu(self.start_date_entry)
        enable_context_menu(self.end_date_entry)
        
        # TreeView 태그 스타일 설정
        self.setup_treeview_tags()
        
        # 저장된 컬럼 순서 및 너비 불러오기
        self.load_column_order()
        self.load_column_widths()
        
        # 초기 날짜 범위 설정 (저장된 기간설정 사용)
        from env_config import config
        saved_period = config.get_int('QUICK_PERIOD_SETTING', 7)
        self.set_date_range(saved_period)
    
    def setup_treeview_tags(self):
        """TreeView 태그 스타일 설정"""
        try:
            # 긴급 (2일 이내) - 빨간색 배경
            self.orders_tree.tag_configure('urgent', background='#ffcccc', foreground='#cc0000')
            
            # 경고 (6일 이내) - 노란색 배경
            self.orders_tree.tag_configure('warning', background='#ffffcc', foreground='#996600')
            
            print("TreeView 태그 스타일 설정 완료")
            
        except Exception as e:
            print(f"TreeView 태그 스타일 설정 오류: {e}")
    
    def set_date_range(self, days):
        """날짜 범위 설정"""
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        self.start_date_entry.set_date(start_date.date())
        self.end_date_entry.set_date(end_date.date())
    
    def on_period_selected(self, event=None):
        """기간설정 콤보박스 선택 이벤트"""
        selected_period = self.period_var.get()
        print(f"기간설정 선택: {selected_period}")
    
    def apply_period_setting(self):
        """기간설정 적용"""
        selected_period = self.period_var.get()
        if not selected_period:
            return
        
        # "일" 제거하고 숫자만 추출
        try:
            days = int(selected_period.replace("일", ""))
            
            # 환경설정에 저장
            from env_config import config
            config.set('QUICK_PERIOD_SETTING', str(days))
            config.save()
            
            # 날짜 범위 설정
            self.set_date_range(days)
            
            print(f"기간설정 적용 및 저장: {days}일")
        except ValueError:
            print(f"잘못된 기간 형식: {selected_period}")
    
    def query_orders_from_api(self):
        """주문 조회 (첫 로드가 아니면 캐시된 데이터 표시)"""
        if not self.is_first_load and hasattr(self, 'last_api_orders') and self.last_api_orders:
            # 이미 조회한 적이 있으면 캐시된 데이터 표시
            self.show_cached_orders()
        else:
            # 첫 로드이거나 캐시된 데이터가 없으면 API 조회
            run_in_thread(self._query_orders_from_api_thread)
    
    def refresh_orders(self):
        """주문 재조회 (캐시된 데이터가 아닌 API에서 새로 조회)"""
        run_in_thread(self._query_orders_from_api_thread)
        
    def _query_orders_from_api_thread(self):
        """API에서 주문 조회 스레드"""
        try:
            if not self.app.naver_api:
                self.app.root.after(0, lambda: messagebox.showerror("오류", "API가 초기화되지 않았습니다."))
                return
            
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            self.app.root.after(0, lambda: self.orders_status_var.set("API에서 주문 조회 중..."))
            
            response = self.app.naver_api.get_orders(
                start_date=start_date_str,
                end_date=end_date_str,
                order_status='PAYED',
                limit=100
            )
            
            if response and response.get('success'):
                data = response.get('data', {})
                raw_orders = data.get('data', [])  # 실제 주문 리스트
                
                print(f"주문수집탭 raw_orders 타입: {type(raw_orders)}")
                print(f"주문수집탭 raw_orders 길이: {len(raw_orders) if isinstance(raw_orders, list) else 'Not a list'}")
                
                # raw_orders는 이미 contents에서 추출된 주문 데이터 배열
                processed_orders = []
                if isinstance(raw_orders, list):
                    for i, item in enumerate(raw_orders):
                        if isinstance(item, dict):
                            print(f"주문 {i+1} 원본 데이터: {json.dumps(item, ensure_ascii=False, indent=2)}")
                            # get_orders에서 반환하는 주문 데이터는 이미 contents 구조
                            if 'content' in item:
                                content = item['content']
                                if 'order' in content:
                                    order_info = content['order']
                                    # 주문 정보를 표준 형식으로 변환
                                    product_order = content.get('productOrder', {})
                                    
                                    # 배송예정일 포맷팅
                                    shipping_due_date = product_order.get('shippingDueDate', 'N/A')
                                    if shipping_due_date != 'N/A':
                                        try:
                                            if 'T' in str(shipping_due_date):
                                                dt = datetime.fromisoformat(str(shipping_due_date).replace('Z', '+00:00'))
                                                shipping_due_date = dt.strftime('%m-%d')
                                        except:
                                            pass
                                    
                                    # 배송지 주소 조합
                                    shipping_address = product_order.get('shippingAddress', {})
                                    base_address = shipping_address.get('baseAddress', '')
                                    detailed_address = shipping_address.get('detailedAddress', '')
                                    full_address = f"{base_address} {detailed_address}".strip()
                                    if not full_address:
                                        full_address = 'N/A'
                                    
                                    order_data = {
                                        'orderId': order_info.get('orderId'),
                                        'productOrderId': item.get('productOrderId'),
                                        'ordererName': order_info.get('ordererName'),
                                        'orderDate': order_info.get('orderDate'),
                                        'orderStatus': product_order.get('productOrderStatus', 'PAYED'),
                                        'productName': product_order.get('productName', 'N/A'),
                                        'totalAmount': product_order.get('totalPaymentAmount', 0),
                                        'productOption': product_order.get('productOption', 'N/A'),
                                        'sellerProductCode': product_order.get('sellerProductCode', 'N/A'),
                                        'quantity': product_order.get('quantity', 1),
                                        'unitPrice': product_order.get('unitPrice', 0),
                                        'discountAmount': product_order.get('productDiscountAmount', 0),
                                        'paymentMeans': order_info.get('paymentMeans', 'N/A'),
                                        'shippingAddress': full_address,
                                        'shippingDueDate': shipping_due_date
                                    }
                                    print(f"변환된 주문 데이터: {json.dumps(order_data, ensure_ascii=False, indent=2)}")
                                    processed_orders.append(order_data)
                            # 직접 orderId가 있는 경우 (다른 형식)
                            elif 'orderId' in item:
                                processed_orders.append(item)
                
                print(f"주문수집탭 변환된 주문 수: {len(processed_orders)}")
                
                # 중복 제거
                unique_orders = self.app.remove_duplicate_orders(processed_orders)
                
                # 데이터베이스에 저장
                saved_count = 0
                for order in unique_orders:
                    if isinstance(order, dict):
                        # API 데이터를 DB 스키마에 맞게 변환
                        order_data = self._convert_api_order_to_db_format(order)
                        if self.app.db_manager.save_order(order_data):
                            saved_count += 1
                            print(f"주문 저장 성공: {order_data.get('order_id', 'Unknown ID')}")
                        else:
                            print(f"주문 저장 실패: {order_data.get('order_id', 'Unknown ID')}")
                
                print(f"총 {len(unique_orders)}건 중 {saved_count}건 데이터베이스에 저장 완료")
                
                # 마지막 API 조회 결과 저장
                self.last_api_orders = unique_orders
                self.is_first_load = False
                
                # UI 업데이트
                self.app.root.after(0, self._update_orders_tree, unique_orders)
                self.app.root.after(0, lambda: self.orders_status_var.set(f"주문 {len(unique_orders)}건 조회 완료"))
            else:
                self.app.root.after(0, lambda: self.orders_status_var.set("주문 조회 실패"))
                
        except Exception as e:
            print(f"API 주문 조회 오류: {e}")
            self.app.root.after(0, lambda: self.orders_status_var.set(f"조회 오류: {str(e)}"))
    
    def query_orders_from_db(self):
        """데이터베이스에서 주문 조회"""
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            
            # 데이터베이스에서 주문 조회
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            print(f"DB 조회 기간: {start_date_str} ~ {end_date_str}")
            
            orders = self.app.db_manager.get_orders_by_date_range(start_date_str, end_date_str)
            print(f"DB에서 조회된 주문 수: {len(orders)}")
            
            if orders:
                # 조회된 주문 정보 출력
                for i, order in enumerate(orders[:3]):  # 처음 3건만 출력
                    print(f"DB 주문 {i+1}: ID={order.get('order_id')}, 상태={order.get('status')}, 고객={order.get('customer_name')}")
                
                # DB 데이터를 API 형식으로 변환하여 UI에 표시
                api_format_orders = self._convert_db_orders_to_api_format(orders)
                self._update_orders_tree(api_format_orders)
                self.orders_status_var.set(f"DB에서 주문 {len(orders)}건 조회 완료")
            else:
                print("해당 기간의 주문이 데이터베이스에 없습니다.")
                self.orders_status_var.set("해당 기간의 주문이 없습니다.")
                
        except Exception as e:
            print(f"DB 주문 조회 오류: {e}")
            self.orders_status_var.set(f"조회 오류: {str(e)}")
    
    def show_cached_orders(self):
        """캐시된 주문 데이터 표시 (API 호출 없이)"""
        if hasattr(self, 'last_api_orders') and self.last_api_orders:
            self._update_orders_tree(self.last_api_orders)
            self.orders_status_var.set(f"마지막 조회 결과 {len(self.last_api_orders)}건 표시 중")
        else:
            self.orders_status_var.set("이전 조회 결과가 없습니다. 주문조회를 먼저 실행해주세요.")
    
    def _update_orders_tree(self, orders):
        """주문 트리뷰 업데이트 (상세 정보 포함)"""
        # 마지막 주문 데이터 저장
        self.last_orders_data = orders
        
        # 기존 데이터 삭제
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        
        # 새 데이터 추가
        for i, order in enumerate(orders):
            if isinstance(order, dict):
                print(f"트리뷰 업데이트 - 주문 {i+1}: {json.dumps(order, ensure_ascii=False, indent=2)}")
                
                order_id = order.get('orderId', 'N/A')
                orderer_name = order.get('ordererName', 'N/A')
                product_name = order.get('productName', 'N/A')
                order_date = order.get('orderDate', 'N/A')
                status = order.get('orderStatus', 'N/A')
                amount = order.get('totalAmount', 0)
                product_order_id = order.get('productOrderId', 'N/A')
                product_option = order.get('productOption', 'N/A')
                seller_product_code = order.get('sellerProductCode', 'N/A')
                quantity = order.get('quantity', 1)
                unit_price = order.get('unitPrice', 0)
                discount_amount = order.get('discountAmount', 0)
                payment_means = order.get('paymentMeans', 'N/A')
                shipping_address = order.get('shippingAddress', 'N/A')
                shipping_due_date = order.get('shippingDueDate', 'N/A')
                
                print(f"트리뷰 - 추출된 정보: orderId={order_id}, ordererName={orderer_name}, productName={product_name}, productOption={product_option}")
                
                # 주문일시 포맷 변경 (보기 쉽게)
                if order_date != 'N/A':
                    try:
                        # ISO 형식을 파싱하여 보기 좋은 형식으로 변환
                        if 'T' in str(order_date):
                            dt = datetime.fromisoformat(str(order_date).replace('Z', '+00:00'))
                            order_date = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass  # 포맷 변경 실패 시 원본 그대로 사용
                
                print(f"트리뷰 - 최종 삽입 데이터: orderId={order_id}, productOrderId={product_order_id}, ordererName={orderer_name}, productName={product_name}, productOption={product_option}")
                
                # 동적 컬럼에 맞는 값들 추출
                current_columns = self.orders_tree['columns']
                order_data = {
                    'orderId': order_id,
                    'productOrderId': product_order_id,
                    'ordererName': orderer_name,
                    'productName': product_name,
                    'optionInfo': product_option,
                    'sellerProductCode': seller_product_code,
                    'quantity': quantity,
                    'unitPrice': unit_price,
                    'discountAmount': discount_amount,
                    'price': amount,
                    'payType': payment_means,
                    'shippingAddress': shipping_address,
                    'expectedDeliveryDate': shipping_due_date,
                    'shippingDueDate': shipping_due_date,  # 두 필드 모두 설정
                    'orderDate': order_date,
                    'claimStatus': status
                }
                
                values = self.get_order_values_for_columns(order_data, current_columns)
                item_id = self.orders_tree.insert('', 'end', values=values)
                
                # 배송예정일에 따른 색상 설정 (order_data에서 실제 배송예정일 값을 가져옴)
                actual_delivery_date = order_data.get('expectedDeliveryDate', '') or order_data.get('shippingDueDate', '')
                self.apply_delivery_date_color(item_id, actual_delivery_date, current_columns)
    
    def _convert_api_order_to_db_format(self, api_order: dict) -> dict:
        """API 주문 데이터를 DB 스키마에 맞게 변환"""
        return {
            'order_id': api_order.get('orderId', ''),
            'order_date': api_order.get('orderDate', ''),
            'customer_name': api_order.get('ordererName', ''),
            'customer_phone': api_order.get('ordererPhone', ''),
            'product_name': api_order.get('productName', ''),
            'quantity': api_order.get('quantity', 1),
            'price': api_order.get('totalAmount', 0),
            'status': api_order.get('orderStatus', '신규주문'),
            'shipping_company': api_order.get('shippingCompany', ''),
            'tracking_number': api_order.get('trackingNumber', ''),
            'memo': api_order.get('memo', ''),
            'product_order_id': api_order.get('productOrderId', ''),
            'shipping_due_date': api_order.get('shippingDueDate', ''),
            'product_option': api_order.get('productOption', '')
        }
    
    def _convert_db_orders_to_api_format(self, db_orders: list) -> list:
        """DB 주문 데이터를 API 형식으로 변환"""
        api_orders = []
        for db_order in db_orders:
            api_order = {
                'orderId': db_order.get('order_id', ''),
                'orderDate': db_order.get('order_date', ''),
                'ordererName': db_order.get('customer_name', ''),
                'ordererPhone': db_order.get('customer_phone', ''),
                'productName': db_order.get('product_name', ''),
                'quantity': db_order.get('quantity', 1),
                'totalAmount': db_order.get('price', 0),
                'orderStatus': db_order.get('status', '신규주문'),
                'shippingCompany': db_order.get('shipping_company', ''),
                'trackingNumber': db_order.get('tracking_number', ''),
                'memo': db_order.get('memo', ''),
                'productOrderId': db_order.get('product_order_id', ''),
                'shippingDueDate': db_order.get('shipping_due_date', ''),
                'productOption': db_order.get('product_option', '')
            }
            api_orders.append(api_order)
        return api_orders
    
    
    def on_column_drag_start(self, event):
        """컬럼 드래그 시작 이벤트"""
        try:
            # 헤더 영역에서만 드래그 허용 (y좌표가 작을 때)
            if event.y > 25:  # 헤더 높이 대략 25픽셀
                self.column_being_dragged = None
                return
                
            # 클릭한 컬럼 식별
            column_id = self.orders_tree.identify_column(event.x)
            if column_id:
                # #1, #2, ... 형태에서 숫자 추출하여 인덱스로 변환
                column_index = int(column_id[1:]) - 1
                self.column_being_dragged = column_index
                print(f"드래그 시작: 컬럼 {column_index}")
            else:
                self.column_being_dragged = None
        except Exception as e:
            print(f"컬럼 드래그 시작 오류: {e}")
            self.column_being_dragged = None
    
    def on_column_drop(self, event):
        """컬럼 드롭 이벤트"""
        try:
            if self.column_being_dragged is None:
                return
                
            # 헤더 영역에서만 드롭 허용
            if event.y > 25:
                self.column_being_dragged = None
                return
                
            # 드롭할 위치의 컬럼 식별
            drop_column_id = self.orders_tree.identify_column(event.x)
            if not drop_column_id:
                self.column_being_dragged = None
                return
                
            drop_column_index = int(drop_column_id[1:]) - 1
            
            # 같은 위치에 드롭하면 무시
            if self.column_being_dragged == drop_column_index:
                self.column_being_dragged = None
                return
                
            print(f"드롭: 컬럼 {self.column_being_dragged} -> {drop_column_index}")
            
            # 컬럼 순서 변경
            self.reorder_columns(self.column_being_dragged, drop_column_index)
            
            # 변경된 순서 저장
            self.save_column_order()
            
            self.column_being_dragged = None
            
        except Exception as e:
            print(f"컬럼 드롭 오류: {e}")
            self.column_being_dragged = None
    
    def reorder_columns(self, from_index, to_index):
        """컬럼 순서 변경"""
        try:
            # 현재 displaycolumns 가져오기
            current_columns = list(self.orders_tree["displaycolumns"])
            
            # #all인 경우 실제 컬럼 이름으로 변경
            if current_columns[0] == "#all":
                current_columns = list(self.orders_tree["columns"])
            
            print(f"현재 컬럼 순서: {current_columns}")
            
            # 컬럼 이동
            if from_index < to_index:
                # 오른쪽으로 이동
                moved_column = current_columns.pop(from_index)
                current_columns.insert(to_index, moved_column)
            else:
                # 왼쪽으로 이동
                moved_column = current_columns.pop(from_index)
                current_columns.insert(to_index, moved_column)
            
            print(f"변경된 컬럼 순서: {current_columns}")
            
            # 새 순서 적용
            self.orders_tree.config(displaycolumns=current_columns)
            
        except Exception as e:
            print(f"컬럼 순서 변경 오류: {e}")
    
    def save_column_order(self):
        """변경된 컬럼 순서를 DB에 저장"""
        try:
            current_columns = list(self.orders_tree["displaycolumns"])
            column_order_str = ",".join(current_columns)
            
            # DB에 저장
            if hasattr(self.app, 'db_manager'):
                self.app.db_manager.save_setting('orders_column_order', column_order_str)
                print(f"컬럼 순서 저장: {column_order_str}")
            
        except Exception as e:
            print(f"컬럼 순서 저장 오류: {e}")
    
    def load_column_order(self):
        """저장된 컬럼 순서를 DB에서 불러오기"""
        try:
            if hasattr(self.app, 'db_manager'):
                column_order_str = self.app.db_manager.get_setting('orders_column_order')
                if column_order_str:
                    saved_columns = column_order_str.split(',')
                    print(f"저장된 컬럼 순서 불러오기: {saved_columns}")
                    
                    # 저장된 컬럼이 현재 컬럼과 일치하는지 확인
                    current_columns = list(self.orders_tree["columns"])
                    if set(saved_columns) == set(current_columns):
                        self.orders_tree.config(displaycolumns=saved_columns)
                        print("저장된 컬럼 순서 적용 완료")
                    else:
                        print("저장된 컬럼 순서가 현재 컬럼과 일치하지 않아 기본 순서 사용")
                        
        except Exception as e:
            print(f"컬럼 순서 불러오기 오류: {e}")
    
    def show_column_context_menu(self, event):
        """컬럼 헤더 우클릭 컨텍스트 메뉴 표시"""
        try:
            # 헤더 영역에서만 메뉴 표시
            if event.y > 25:
                return
                
            # 컨텍스트 메뉴 생성
            context_menu = tk.Menu(self.orders_tree, tearoff=0)
            context_menu.add_command(label="컬럼 순서 초기화", command=self.reset_column_order)
            context_menu.add_command(label="컬럼 너비 초기화", command=self.reset_column_widths)
            context_menu.add_separator()
            context_menu.add_command(label="모든 설정 초기화", command=self.reset_all_column_settings)
            context_menu.add_separator()
            context_menu.add_command(label="취소")
            
            # 메뉴 표시
            context_menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            print(f"컨텍스트 메뉴 표시 오류: {e}")
    
    def reset_column_order(self):
        """컬럼 순서를 기본값으로 초기화"""
        try:
            # 기본 컬럼 순서 (원래 정의된 순서)
            default_columns = ('주문ID', '상품주문ID', '주문자', '상품명', '옵션정보', '판매자상품코드', 
                             '수량', '단가', '할인금액', '금액', '결제방법', '배송지주소', '배송예정일', '주문일시', '상태')
            
            # 컬럼 순서 초기화
            self.orders_tree.config(displaycolumns=default_columns)
            
            # DB에서 설정 삭제
            if hasattr(self.app, 'db_manager'):
                self.app.db_manager.save_setting('orders_column_order', '')
                print("컬럼 순서 초기화 완료")
                
            # 상태 메시지 표시
            self.orders_status_var.set("컬럼 순서가 초기화되었습니다.")
            
        except Exception as e:
            print(f"컬럼 순서 초기화 오류: {e}")
    
    def on_column_resize(self, event):
        """컬럼 너비 변경 감지 이벤트"""
        try:
            # 드래그 앤 드롭 중이면 무시
            if self.column_being_dragged is not None:
                return
            
            # 너비 변경 감지를 위해 약간의 지연 후 저장
            # (사용자가 여러 번 조정할 때 매번 저장하지 않도록)
            if hasattr(self, '_resize_timer'):
                self.orders_tree.after_cancel(self._resize_timer)
            
            self._resize_timer = self.orders_tree.after(500, self.save_column_widths)  # 0.5초 후 저장
            
        except Exception as e:
            print(f"컬럼 너비 변경 감지 오류: {e}")
    
    def save_column_widths(self):
        """현재 컬럼 너비들을 DB에 저장"""
        try:
            column_widths = {}
            
            # 모든 컬럼의 현재 너비 수집
            for column in self.orders_tree["columns"]:
                width = self.orders_tree.column(column, "width")
                column_widths[column] = width
            
            # JSON 형태로 저장
            import json
            widths_json = json.dumps(column_widths, ensure_ascii=False)
            
            # DB에 저장
            if hasattr(self.app, 'db_manager'):
                self.app.db_manager.save_setting('orders_column_widths', widths_json)
                print(f"컬럼 너비 저장: {column_widths}")
            
        except Exception as e:
            print(f"컬럼 너비 저장 오류: {e}")
    
    def load_column_widths(self):
        """저장된 컬럼 너비들을 DB에서 불러와서 적용"""
        try:
            if hasattr(self.app, 'db_manager'):
                widths_json = self.app.db_manager.get_setting('orders_column_widths')
                if widths_json:
                    import json
                    saved_widths = json.loads(widths_json)
                    print(f"저장된 컬럼 너비 불러오기: {saved_widths}")
                    
                    # 저장된 너비 적용
                    for column, width in saved_widths.items():
                        try:
                            # 컬럼이 존재하는지 확인 후 적용
                            if column in self.orders_tree["columns"]:
                                self.orders_tree.column(column, width=int(width))
                        except Exception as col_error:
                            print(f"컬럼 {column} 너비 적용 오류: {col_error}")
                    
                    print("저장된 컬럼 너비 적용 완료")
                        
        except Exception as e:
            print(f"컬럼 너비 불러오기 오류: {e}")
    
    def reset_column_widths(self):
        """컬럼 너비를 기본값으로 초기화"""
        try:
            # 기본 컬럼 너비 설정
            default_widths = {
                '주문ID': 120,
                '상품주문ID': 120,
                '주문자': 80,
                '상품명': 180,
                '옵션정보': 120,
                '판매자상품코드': 100,
                '수량': 50,
                '단가': 80,
                '할인금액': 80,
                '금액': 80,
                '결제방법': 80,
                '배송지주소': 200,
                '배송예정일': 100,
                '주문일시': 120,
                '상태': 60
            }
            
            # 기본 너비 적용
            for column, width in default_widths.items():
                if column in self.orders_tree["columns"]:
                    self.orders_tree.column(column, width=width)
            
            # DB에서 설정 삭제
            if hasattr(self.app, 'db_manager'):
                self.app.db_manager.save_setting('orders_column_widths', '')
                print("컬럼 너비 초기화 완료")
                
        except Exception as e:
            print(f"컬럼 너비 초기화 오류: {e}")
    
    def reset_all_column_settings(self):
        """컬럼 순서와 너비를 모두 기본값으로 초기화"""
        try:
            # 컬럼 순서 초기화
            self.reset_column_order()
            
            # 컬럼 너비 초기화
            self.reset_column_widths()
            
            # 상태 메시지 표시
            self.orders_status_var.set("모든 컬럼 설정이 초기화되었습니다.")
            
        except Exception as e:
            print(f"모든 컬럼 설정 초기화 오류: {e}")
    
    def get_display_columns(self):
        """설정에 따라 표시할 컬럼 목록 반환"""
        try:
            from env_config import config
            
            # 기본값: 모든 컬럼 선택
            default_columns = ','.join(self.all_columns)
            saved_columns = config.get('ORDER_COLUMNS', default_columns)
            column_list = [col.strip() for col in saved_columns.split(',')]
            
            # 설정된 컬럼 중 유효한 컬럼만 반환
            display_columns = [col for col in column_list if col in self.all_columns]
            
            # 최소 하나의 컬럼은 표시해야 함
            if not display_columns:
                display_columns = ['주문ID']
            
            print(f"표시할 컬럼: {display_columns}")
            return tuple(display_columns)
            
        except Exception as e:
            print(f"컬럼 설정 로드 오류: {e}")
            # 오류 시 기본 컬럼만 표시
            return ('주문ID', '주문자', '상품명', '금액', '주문일시', '상태')
    
    def update_column_display(self):
        """컬럼 표시 설정 업데이트"""
        try:
            # 새 컬럼 설정 가져오기
            new_columns = self.get_display_columns()
            
            # 현재 트리뷰가 이미 새 컬럼과 같다면 업데이트하지 않음
            current_columns = self.orders_tree['columns']
            if current_columns == new_columns:
                print("컬럼 구조가 동일하므로 업데이트하지 않음")
                return
            
            # 기존 데이터 백업
            current_data = self.last_orders_data if hasattr(self, 'last_orders_data') else []
            
            # 기존 트리뷰 제거
            tree_frame = self.orders_tree.master
            self.orders_tree.destroy()
            
            # 새 트리뷰 생성
            self.orders_tree = ttk.Treeview(tree_frame, columns=new_columns, show='headings', height=15)
            
            # 컬럼별 너비 설정
            column_widths = {
                '주문ID': 120,
                '상품주문ID': 120,
                '주문자': 80,
                '상품명': 180,
                '옵션정보': 120,
                '판매자상품코드': 100,
                '수량': 50,
                '단가': 80,
                '할인금액': 80,
                '금액': 80,
                '결제방법': 80,
                '배송지주소': 200,
                '배송예정일': 100,
                '주문일시': 120,
                '상태': 60
            }
            
            for col in new_columns:
                self.orders_tree.heading(col, text=col)
                width = column_widths.get(col, 120)
                self.orders_tree.column(col, width=width)
            
            # 스크롤바 재생성
            v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.orders_tree.yview)
            self.orders_tree.configure(yscrollcommand=v_scrollbar.set)
            
            h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.orders_tree.xview)
            self.orders_tree.configure(xscrollcommand=h_scrollbar.set)
            
            # 트리뷰와 스크롤바 배치 (grid 사용)
            self.orders_tree.grid(row=0, column=0, sticky="nsew")
            v_scrollbar.grid(row=0, column=1, sticky="ns")
            h_scrollbar.grid(row=1, column=0, sticky="ew")
            
            # grid 가중치 설정
            tree_frame.grid_rowconfigure(0, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
            
            # TreeView 태그 스타일 재설정
            self.setup_treeview_tags()
            
            # 이벤트 바인딩 재설정
            self.orders_tree.bind('<ButtonPress-1>', self.on_column_drag_start)
            self.orders_tree.bind('<ButtonRelease-1>', self.on_column_drop)
            self.orders_tree.bind('<Button-3>', self.show_column_context_menu)
            self.orders_tree.bind('<ButtonRelease-1>', self.on_column_resize, add='+')
            
            # 백업된 데이터가 있다면 다시 로드
            if current_data:
                self._update_orders_tree(current_data)
                print(f"기존 주문 데이터 {len(current_data)}건 다시 로드 완료")
            
            print(f"컬럼 표시 업데이트 완료: {len(new_columns)}개 컬럼")
            
        except Exception as e:
            print(f"컬럼 표시 업데이트 오류: {e}")
    
    def get_order_values_for_columns(self, order, columns):
        """주문 데이터에서 지정된 컬럼에 해당하는 값들 추출"""
        try:
            values = []
            for col in columns:
                if col == '주문ID':
                    values.append(order.get('orderId', ''))
                elif col == '상품주문ID':
                    values.append(order.get('productOrderId', ''))
                elif col == '주문자':
                    values.append(order.get('ordererName', ''))
                elif col == '상품명':
                    values.append(order.get('productName', ''))
                elif col == '옵션정보':
                    values.append(order.get('optionInfo', ''))
                elif col == '판매자상품코드':
                    values.append(order.get('sellerProductCode', ''))
                elif col == '수량':
                    values.append(str(order.get('quantity', 0)))
                elif col == '단가':
                    values.append(f"{order.get('unitPrice', 0):,}")
                elif col == '할인금액':
                    values.append(f"{order.get('discountAmount', 0):,}")
                elif col == '금액':
                    values.append(f"{order.get('price', 0):,}")
                elif col == '결제방법':
                    values.append(order.get('payType', ''))
                elif col == '배송지주소':
                    values.append(order.get('shippingAddress', ''))
                elif col == '배송예정일':
                    # shippingDueDate와 expectedDeliveryDate 둘 다 확인
                    delivery_date = order.get('expectedDeliveryDate', '') or order.get('shippingDueDate', '')
                    values.append(delivery_date)
                elif col == '주문일시':
                    values.append(order.get('orderDate', ''))
                elif col == '상태':
                    values.append(order.get('claimStatus', ''))
                else:
                    values.append('')
            
            return values
            
        except Exception as e:
            print(f"주문 값 추출 오류: {e}")
            return [''] * len(columns)
    
    def apply_delivery_date_color(self, item_id, delivery_date, columns):
        """배송예정일에 따른 색상 적용"""
        try:
            from datetime import datetime, timedelta
            
            print(f"색상 적용 시도 - item_id: {item_id}, delivery_date: {delivery_date}, columns: {columns}")
            
            # 배송예정일 컬럼이 있는지 확인
            if '배송예정일' not in columns:
                print("배송예정일 컬럼이 존재하지 않음")
                return
            
            # 배송예정일 컬럼의 인덱스 찾기
            delivery_col_index = list(columns).index('배송예정일')
            print(f"배송예정일 컬럼 인덱스: {delivery_col_index}")
            
            if not delivery_date or delivery_date == 'N/A':
                print(f"배송예정일이 유효하지 않음: {delivery_date}")
                return
            
            # 날짜 파싱
            today = datetime.now().date()
            due_date = None
            
            print(f"오늘 날짜: {today}, 파싱할 배송예정일: '{delivery_date}' (타입: {type(delivery_date)})")
            
            try:
                # 다양한 날짜 형식 처리
                if isinstance(delivery_date, str):
                    delivery_date = delivery_date.strip()
                    print(f"문자열 배송예정일 처리: '{delivery_date}'")
                    
                    # ISO 형식 (2025-09-16)
                    if '-' in delivery_date and len(delivery_date) >= 10:
                        due_date = datetime.strptime(delivery_date[:10], '%Y-%m-%d').date()
                        print(f"ISO 형식으로 파싱 성공: {due_date}")
                    # MM-DD 형식 (09-16) - 현재 연도로 처리
                    elif '-' in delivery_date and len(delivery_date.split('-')) == 2:
                        current_year = datetime.now().year
                        try:
                            month, day = delivery_date.split('-')
                            due_date = datetime.strptime(f"{current_year}-{month.zfill(2)}-{day.zfill(2)}", '%Y-%m-%d').date()
                            print(f"MM-DD 형식으로 파싱 성공: {due_date} (현재 연도 {current_year} 사용)")
                        except ValueError:
                            print(f"MM-DD 형식 파싱 실패: {delivery_date}")
                    # 슬래시 형식 (2025/09/16)
                    elif '/' in delivery_date:
                        if len(delivery_date.split('/')) == 3:
                            due_date = datetime.strptime(delivery_date, '%Y/%m/%d').date()
                            print(f"슬래시 형식으로 파싱 성공: {due_date}")
                    # 점 형식 (2025.09.16)
                    elif '.' in delivery_date:
                        if len(delivery_date.split('.')) == 3:
                            due_date = datetime.strptime(delivery_date, '%Y.%m.%d').date()
                            print(f"점 형식으로 파싱 성공: {due_date}")
                    # 숫자만 있는 경우 (20250916)
                    elif delivery_date.isdigit() and len(delivery_date) == 8:
                        due_date = datetime.strptime(delivery_date, '%Y%m%d').date()
                        print(f"숫자 형식으로 파싱 성공: {due_date}")
                elif hasattr(delivery_date, 'date'):
                    due_date = delivery_date.date()
                    print(f"날짜 객체로 파싱 성공: {due_date}")
                    
            except (ValueError, AttributeError) as e:
                print(f"날짜 파싱 실패: '{delivery_date}', 오류: {e}")
                return
            
            if not due_date:
                return
            
            # 오늘 날짜와의 차이 계산
            days_diff = (due_date - today).days
            print(f"날짜 차이 계산: 오늘({today}) vs 배송예정일({due_date}) = {days_diff}일")
            
            # 색상 설정 (전체 행에 적용)
            if days_diff <= 1:
                # 1일 이내: 빨간색 배경 (전체 행)
                self.orders_tree.item(item_id, tags=('urgent',))
                print(f"🔴 긴급 배송 색상 적용: {delivery_date} (D-{days_diff})")
            elif days_diff <= 3:
                # 3일 이내: 노란색 배경 (전체 행)
                self.orders_tree.item(item_id, tags=('warning',))
                print(f"🟡 경고 배송 색상 적용: {delivery_date} (D-{days_diff})")
            else:
                print(f"⚪ 일반 배송: {delivery_date} (D-{days_diff})")
            
            # 태그가 제대로 적용되었는지 확인
            applied_tags = self.orders_tree.item(item_id, 'tags')
            print(f"적용된 태그: {applied_tags}")
            
        except Exception as e:
            print(f"배송예정일 색상 적용 오류: {e}")
