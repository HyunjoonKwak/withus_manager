"""
홈 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta, timezone
import json
import threading
import socket
import requests

from ui_utils import BaseTab, run_in_thread, enable_context_menu
from env_config import config


class HomeTab(BaseTab):
    """홈 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.create_home_tab()
        self.setup_copy_paste_bindings()
        self.update_status_display()
    
    def create_home_tab(self):
        """홈 탭 UI 생성"""
        # 주문 현황 대시보드
        dashboard_frame = ttk.LabelFrame(self.frame, text="주문 현황")
        dashboard_frame.pack(fill="x", padx=5, pady=5)
        
        # 주문 상태 버튼들 (한 줄로 배치)
        status_frame = ttk.Frame(dashboard_frame)
        status_frame.pack(fill="x", padx=5, pady=5)
        status_frame.configure(height=60)  # 프레임 높이 고정
        status_frame.pack_propagate(False)  # 자식 위젯이 프레임 크기를 변경하지 못하도록 방지
        
        self.status_buttons = {}
        statuses = ['신규주문', '발송대기', '배송중', '배송완료', '구매확정', '취소주문', '반품주문', '교환주문']
        
        for i, status in enumerate(statuses):
            # 개별 프레임으로 감싸서 높이 제어
            btn_frame = ttk.Frame(status_frame)
            btn_frame.pack(side="left", padx=2, fill="both", expand=True)
            
            # 일반 tk.Button 사용하여 높이 제어
            btn = tk.Button(btn_frame, text=f"{status}\n0건", 
                          command=lambda s=status: self.show_orders_by_status(s),
                          height=3,  # 버튼 높이를 3줄로 설정
                          font=("맑은 고딕", 9),
                          relief="raised",
                          borderwidth=1)
            btn.pack(fill="both", expand=True, pady=2)
            self.status_buttons[status] = btn
        
        # 새로고침 버튼
        refresh_frame = ttk.Frame(dashboard_frame)
        refresh_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Button(refresh_frame, text="대시보드 새로고침", command=self.refresh_dashboard).pack(side="left", padx=2)
        ttk.Button(refresh_frame, text="수동 주문 조회", command=self.manual_order_query).pack(side="left", padx=2)
        
        # 대시보드 기간 설정
        ttk.Label(refresh_frame, text="조회 기간:").pack(side="left", padx=(10, 2))
        
        from env_config import config
        self.dashboard_period_var = tk.StringVar()
        current_period = config.get_int('DASHBOARD_PERIOD_DAYS', 1)
        self.dashboard_period_var.set(str(current_period))
        
        period_combo = ttk.Combobox(refresh_frame, textvariable=self.dashboard_period_var, 
                                   values=['1', '3', '7'], width=5, state="readonly")
        period_combo.pack(side="left", padx=2)
        period_combo.bind('<<ComboboxSelected>>', self.on_period_changed)
        
        ttk.Label(refresh_frame, text="일").pack(side="left", padx=(0, 5))
        
        
        # 상태 표시
        self.home_status_var = tk.StringVar()
        self.home_status_var.set("대기 중...")
        status_label = ttk.Label(dashboard_frame, textvariable=self.home_status_var)
        status_label.pack(pady=5)
        
        
        # 상품 조회 섹션
        products_frame = ttk.LabelFrame(self.frame, text="상품 조회")
        products_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 상품 조회 버튼
        products_button_frame = ttk.Frame(products_frame)
        products_button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(products_button_frame, text="상품목록 조회", command=self.query_products).pack(side="left", padx=2)
        ttk.Button(products_button_frame, text="저장된 상품 조회", command=self.load_saved_products).pack(side="left", padx=2)
        
        # 상품 상태 표시 (설정에서 가져온 상태만 표시)
        filter_frame = ttk.Frame(products_frame)
        filter_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(filter_frame, text="표시 상품 상태:").pack(side="left", padx=2)
        
        self.status_display_var = tk.StringVar()
        self.status_display_var.set("설정에서 상품 상태를 설정해주세요")
        self.status_display_label = ttk.Label(filter_frame, textvariable=self.status_display_var, foreground="blue")
        self.status_display_label.pack(side="left", padx=10)
        
        # 설정으로 이동 버튼
        ttk.Button(filter_frame, text="설정에서 상품상태 변경", 
                  command=self.go_to_settings).pack(side="right", padx=5)
        
        # 상품 목록 트리뷰
        product_columns = ('상품ID', '상품명', '상태', '원래판매가', '셀러할인가', '실제판매가', '재고', '원상품ID')
        self.products_tree = ttk.Treeview(products_frame, columns=product_columns, show='headings', height=8)
        
        for col in product_columns:
            self.products_tree.heading(col, text=col)
            self.products_tree.column(col, width=100)
        
        # 스크롤바
        products_scrollbar = ttk.Scrollbar(products_frame, orient="vertical", command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=products_scrollbar.set)
        
        self.products_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        products_scrollbar.pack(side="right", fill="y", pady=5)
        
        # 상품 상태 표시 (탭 하단)
        self.products_status_var = tk.StringVar()
        self.products_status_var.set("대기 중...")
        products_status_label = ttk.Label(self.frame, textvariable=self.products_status_var)
        products_status_label.pack(side="bottom", pady=2)
        
    
    def refresh_dashboard(self):
        """대시보드 새로고침"""
        run_in_thread(self._refresh_dashboard_thread)
    
    def _refresh_dashboard_thread(self):
        """대시보드 새로고침 스레드"""
        try:
            print("=== 대시보드 새로고침 - 전체 주문 상태 조회 ===")
            
            # 설정에서 대시보드 기간 가져오기 (기본값: 1일)
            from env_config import config
            dashboard_days = config.get_int('DASHBOARD_PERIOD_DAYS', 1)
            
            # 현재 시간 기준으로 설정된 기간 전부터 조회
            kst = timezone(timedelta(hours=9))
            now = datetime.now(kst)
            start_date = now - timedelta(days=dashboard_days)
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = now.strftime('%Y-%m-%d')
            
            print(f"주문 조회 날짜 범위: {start_date_str} ~ {end_date_str} ({dashboard_days}일)")
            
            # 홈탭에서는 모든 주문 상태를 조회 (설정과 무관하게)
            status_list = ['PAYED', 'DELIVERING', 'DELIVERED', 'PURCHASE_DECIDED', 'PAYMENT_WAITING', 'EXCHANGED', 'CANCELED', 'RETURNED', 'CANCELED_BY_NOPAYMENT']
            
            print(f"조회할 주문 상태: {status_list}")
            
            # 각 상태별 주문 수 집계
            order_counts = {}
            for status in status_list:
                order_counts[status] = 0
            
            all_orders = []
            total_chunks = 0
            
            # 다중 상태 조회 시도 (주문관리탭과 동일한 방식)
            print(f"다중 상태 조회 시도: {status_list}")
            try:
                response = self.app.naver_api.get_orders(
                    start_date=start_date_str,
                    end_date=end_date_str,
                    order_status=status_list,  # 리스트 전체 전달
                    limit=1000
                )
                
                multi_query_success = False
                if response.get('success'):
                    data = response.get('data', {})
                    if isinstance(data, dict) and 'data' in data:
                        orders_list = data.get('data', [])
                        if isinstance(orders_list, list) and len(orders_list) > 0:
                            print(f"다중 상태 조회 성공: 총 {len(orders_list)}건")
                            multi_query_success = True
                            
                            # 상태별로 분류
                            for order in orders_list:
                                if isinstance(order, dict) and 'content' in order:
                                    content = order['content']
                                    order_status = content.get('productOrderStatus')
                                    if order_status in order_counts:
                                        order_counts[order_status] += 1
                                elif isinstance(order, dict) and 'orderStatus' in order:
                                    order_status = order.get('orderStatus')
                                    if order_status in order_counts:
                                        order_counts[order_status] += 1
                            
                            print(f"다중 조회 결과: {order_counts}")
                        else:
                            print("다중 상태 조회: 주문 데이터 없음")
                            multi_query_success = True  # 빈 결과도 성공으로 처리
                    else:
                        print("다중 상태 조회: 데이터 구조 인식 실패")
                else:
                    error_msg = response.get('error', '알 수 없는 오류')
                    print(f"다중 상태 조회 실패: {error_msg}")
                
                # 다중 조회가 실패한 경우에만 개별 조회로 fallback
                if not multi_query_success:
                    print("다중 상태 조회 실패 → 개별 상태 조회로 fallback")
                    # 각 상태별로 개별 조회
                    for status in status_list:
                        try:
                            print(f"개별 주문 상태 '{status}' 조회 중...")
                            response = self.app.naver_api.get_orders(
                                start_date=start_date_str,
                                end_date=end_date_str,
                                order_status=status,
                                limit=1000
                            )
                            
                            if response.get('success'):
                                data = response.get('data', {})
                                
                                # 주문 수 계산
                                if isinstance(data, dict) and 'total' in data:
                                    count = data.get('total', 0)
                                    order_counts[status] = count
                                    print(f"개별 조회 - 주문 상태 '{status}': {count}건")
                                elif isinstance(data, dict) and 'data' in data:
                                    orders_list = data.get('data', [])
                                    count = len(orders_list) if isinstance(orders_list, list) else 0
                                    order_counts[status] = count
                                    print(f"개별 조회 - 주문 상태 '{status}': {count}건")
                                else:
                                    order_counts[status] = 0
                                    print(f"개별 조회 - 주문 상태 '{status}': 데이터 구조 인식 실패")
                            else:
                                order_counts[status] = 0
                                error_msg = response.get('error', '알 수 없는 오류')
                                print(f"개별 조회 - 주문 상태 '{status}' 조회 실패: {error_msg}")
                                
                        except Exception as e:
                            order_counts[status] = 0
                            print(f"개별 조회 - 주문 상태 '{status}' 조회 오류: {e}")
                            
            except Exception as e:
                print(f"다중 상태 조회 오류: {e}")
                # 예외 발생 시에도 개별 조회로 fallback
                for status in status_list:
                    order_counts[status] = 0
            
            print(f"대시보드 새로고침 결과: {order_counts}")
            
            # 버튼 텍스트 업데이트 (기존 status_buttons 딕셔너리 사용)
            def update_status_buttons():
                try:
                    # 상태 이름 매핑 (API 상태 코드 → 홈탭 버튼명)
                    status_name_mapping = {
                        'PAYED': '신규주문',
                        'DELIVERING': '발송대기',  # 버튼명과 일치시킴
                        'DELIVERED': '배송완료',
                        'PURCHASE_DECIDED': '구매확정',
                        'PAYMENT_WAITING': '신규주문',  # 결제대기도 신규주문으로 통합
                        'EXCHANGED': '교환주문',
                        'CANCELED': '취소주문',
                        'RETURNED': '반품주문',
                        'CANCELED_BY_NOPAYMENT': '취소주문'  # 미결제취소도 취소주문으로 통합
                    }
                    
                    # 버튼별로 상태 합계 계산
                    button_counts = {}
                    for button_name in self.status_buttons.keys():
                        button_counts[button_name] = 0
                    
                    # 각 API 상태를 해당 버튼에 합산
                    for status, count in order_counts.items():
                        korean_name = status_name_mapping.get(status, status)
                        
                        if korean_name in button_counts:
                            button_counts[korean_name] += count
                            print(f"상태 '{status}' ({count}건) → 버튼 '{korean_name}'에 합산")
                        else:
                            print(f"매핑되지 않은 상태: {status} -> {korean_name}")
                    
                    # 버튼 텍스트 업데이트
                    for button_name, total_count in button_counts.items():
                        if button_name in self.status_buttons:
                            new_text = f"{button_name}\n{total_count:,}건"
                            self.status_buttons[button_name].config(text=new_text)
                            print(f"버튼 업데이트: {button_name} -> {total_count:,}건")
                        else:
                            print(f"버튼을 찾을 수 없음: {button_name}")
                    
                    print(f"사용 가능한 버튼들: {list(self.status_buttons.keys())}")
                    print(f"최종 버튼 집계: {button_counts}")
                            
                except Exception as e:
                    print(f"상태 버튼 업데이트 오류: {e}")
                    import traceback
                    traceback.print_exc()
            
            # UI 업데이트를 메인 스레드에서 실행
            self.app.root.after(0, update_status_buttons)
            
            print(f"대시보드 새로고침 성공: {sum(order_counts.values())}건 조회 완료")
            
        except Exception as e:
            print(f"대시보드 새로고침 오류: {e}")
            self.app.root.after(0, lambda: messagebox.showerror("오류", f"대시보드 새로고침 실패: {str(e)}"))
    
    def on_period_changed(self, event=None):
        """대시보드 기간 변경 이벤트"""
        try:
            new_period = int(self.dashboard_period_var.get())
            from env_config import config
            config.set('DASHBOARD_PERIOD_DAYS', str(new_period))
            config.save()
            print(f"대시보드 조회 기간이 {new_period}일로 변경됨")
            
            # 자동으로 대시보드 새로고침
            self.refresh_dashboard()
            
        except Exception as e:
            print(f"기간 변경 오류: {e}")
    
    def _update_dashboard_ui(self, order_counts, all_orders, total_chunks):
        """대시보드 UI 업데이트"""
        try:
            # 주문 상태 버튼 업데이트 (중앙 정렬된 텍스트)
            for status, count in order_counts.items():
                if status in self.status_buttons:
                    # 버튼 텍스트를 중앙 정렬된 형태로 구성
                    button_text = f"{status}\n{count:,}건"  # 천단위 콤마 추가
                    self.status_buttons[status].config(text=button_text)
            
            # 전체 주문 저장
            self.app.all_orders = all_orders
            
            print(f"전체 조회 완료: 총 {total_chunks}개 청크 처리")
            
        except Exception as e:
            print(f"UI 업데이트 오류: {e}")
    
    
    def _query_new_orders_thread(self):
        """신규주문 조회 스레드"""
        try:
            # 기능이 주문수집 탭으로 이동됨
            pass
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            print(f"=== 홈탭 신규주문 조회 시작 ===")
            print(f"조회 기간: {start_date_str} ~ {end_date_str}")
            
            self.app.root.after(0, lambda: self.home_status_var.set("신규주문 조회 중..."))
            
            response = self.app.naver_api.get_orders(
                start_date=start_date_str,
                end_date=end_date_str,
                order_status='PAYED',
                limit=100
            )
            
            print(f"홈탭 응답 수신: {response is not None}")
            if response:
                print(f"홈탭 응답 키들: {list(response.keys())}")
            
            if response and response.get('success'):
                # 응답 구조 분석 및 디버깅
                api_data = response.get('data', {})
                print(f"홈탭 API 데이터 타입: {type(api_data)}")
                print(f"홈탭 API 데이터 키들: {list(api_data.keys()) if isinstance(api_data, dict) else 'Not a dict'}")
                
                # get_orders 함수의 반환 구조에 맞는 데이터 처리
                orders = []
                
                # get_orders 함수는 API contents 구조를 그대로 'data' 키로 반환
                if isinstance(api_data, dict) and 'data' in api_data:
                    raw_orders = api_data['data']
                    print(f"홈탭 get_orders 반환 주문 수: {len(raw_orders) if isinstance(raw_orders, list) else 'Not a list'}")
                    
                    # 첫 번째 항목의 구조 분석
                    if isinstance(raw_orders, list) and len(raw_orders) > 0:
                        first_item = raw_orders[0]
                        print(f"홈탭 첫 번째 주문 타입: {type(first_item)}")
                        if isinstance(first_item, dict):
                            print(f"홈탭 첫 번째 주문 키들: {list(first_item.keys())}")
                    
                    # get_orders는 API의 contents 배열을 그대로 반환하므로 contents 구조로 처리
                    for i, item in enumerate(raw_orders):
                        if isinstance(item, dict):
                            print(f"홈탭 주문 {i+1} 처리 중: 키들 = {list(item.keys())}")
                            
                            # contents 구조인 경우 (productOrderId + content)
                            if 'content' in item and 'productOrderId' in item:
                                content = item['content']
                                print(f"홈탭 주문 {i+1} content 키들: {list(content.keys()) if isinstance(content, dict) else 'Not a dict'}")
                                
                                if isinstance(content, dict) and 'order' in content:
                                    order_info = content['order']
                                    product_info = content.get('product', {})
                                    
                                    order_data = {
                                        'orderId': order_info.get('orderId'),
                                        'productOrderId': item.get('productOrderId'),
                                        'ordererName': order_info.get('ordererName'),
                                        'orderDate': order_info.get('orderDate'),
                                        'orderStatus': content.get('productOrderStatus', 'PAYED'),
                                        'productName': product_info.get('name', 'N/A') if isinstance(product_info, dict) else 'N/A'
                                    }
                                    orders.append(order_data)
                                    print(f"홈탭 주문 {i+1} 추출 성공: {order_data['orderId']}")
                                else:
                                    print(f"홈탭 주문 {i+1} content 구조 오류: order 키가 없음")
                            
                            # 이미 가공된 주문 데이터인 경우
                            elif 'orderId' in item:
                                orders.append(item)
                                print(f"홈탭 주문 {i+1} 직접 추출: {item.get('orderId')}")
                            
                            else:
                                print(f"홈탭 주문 {i+1} 알 수 없는 구조: {list(item.keys())}")
                                # 예상치 못한 구조 대응
                                if len(list(item.keys())) > 0:
                                    print(f"홈탭 주문 {i+1} 첫 번째 값 샘플: {list(item.values())[0] if item.values() else 'No values'}")
                
                # get_orders가 contents 구조로 직접 API 데이터를 반환하는 경우 대비
                elif isinstance(api_data, dict) and 'contents' in api_data:
                    contents = api_data['contents']
                    print(f"홈탭 contents 길이: {len(contents) if isinstance(contents, list) else 'Not a list'}")
                    
                    for item in contents:
                        if isinstance(item, dict) and 'content' in item:
                            content = item['content']
                            if 'order' in content:
                                order_info = content['order']
                                order_data = {
                                    'orderId': order_info.get('orderId'),
                                    'productOrderId': item.get('productOrderId'),
                                    'ordererName': order_info.get('ordererName'),
                                    'orderDate': order_info.get('orderDate'),
                                    'orderStatus': content.get('productOrderStatus', 'PAYED'),
                                    'productName': content.get('product', {}).get('name', 'N/A')
                                }
                                orders.append(order_data)
                
                print(f"홈탭 추출된 주문 수: {len(orders)}")
                
                # 중복 제거 - orderId 기준
                unique_orders = []
                seen_order_ids = set()
                
                for order in orders:
                    order_id = order.get('orderId')
                    if order_id and order_id not in seen_order_ids:
                        seen_order_ids.add(order_id)
                        unique_orders.append(order)
                
                print(f"홈탭 중복 제거: {len(orders)}건 → {len(unique_orders)}건")
                
                # UI 업데이트
                self.app.root.after(0, lambda: self._update_orders_tree(unique_orders))
                self.app.root.after(0, lambda: self.home_status_var.set(f"신규주문 {len(unique_orders)}건 조회 완료"))
            else:
                error_msg = f"신규주문 조회 실패: {response.get('error', '응답 없음') if response else '네트워크 오류'}"
                print(error_msg)
                self.app.root.after(0, lambda: self.home_status_var.set("신규주문 조회 실패"))
                
        except Exception as e:
            print(f"홈탭 신규주문 조회 오류: {e}")
            self.app.root.after(0, lambda: self.home_status_var.set(f"조회 오류: {str(e)}"))
    
    
    def manual_order_query(self):
        """수동 주문 조회"""
        messagebox.showinfo("수동 조회", "수동 주문 조회 기능입니다.")
    
    def query_products(self):
        """상품 목록 조회"""
        run_in_thread(self._query_products_thread)
    
    def _query_products_thread(self):
        """상품 목록 조회 스레드"""
        try:
            if not self.app.naver_api:
                def show_api_error():
                    messagebox.showwarning(
                        "API 설정 필요", 
                        "네이버 커머스 API가 설정되지 않았습니다.\n\n"
                        "설정 탭에서 API 정보를 입력해주세요."
                    )
                    # 설정 탭으로 이동
                    self.app.notebook.select(5)  # 설정 탭은 6번째 탭 (인덱스 5)
                
                self.app.root.after(0, show_api_error)
                return
            
            self.app.root.after(0, lambda: self.products_status_var.set("상품 목록 조회 중..."))
            
            # 상품 목록 조회
            response = self.app.naver_api.get_products()
            
            if response and response.get('success'):
                data = response.get('data', {})
                products = data.get('contents', [])
                
                print(f"홈탭 상품 조회 결과: {len(products)}개")
                
                # 상품 데이터를 데이터베이스에 저장
                for product in products:
                    if isinstance(product, dict):
                        # 상품 데이터 구조 변환
                        origin_product_no = product.get('originProductNo')
                        channel_products = product.get('channelProducts', [])
                        
                        if channel_products and len(channel_products) > 0:
                            channel_product = channel_products[0]
                            
                            # 데이터베이스 저장을 위한 플랫 구조로 변환
                            product_data = {
                                'origin_product_no': origin_product_no,
                                'channel_product_no': channel_product.get('channelProductNo'),
                                'product_name': channel_product.get('name'),
                                'status_type': channel_product.get('statusType'),
                                'sale_price': channel_product.get('salePrice', 0),
                                'discounted_price': channel_product.get('discountedPrice', 0),
                                'stock_quantity': channel_product.get('stockQuantity', 0),
                                'category_id': channel_product.get('categoryId'),
                                'category_name': channel_product.get('wholeCategoryName', '').split('>')[-1] if channel_product.get('wholeCategoryName') else '',
                                'brand_name': channel_product.get('brandName'),
                                'manufacturer_name': channel_product.get('manufacturerName'),
                                'model_name': channel_product.get('modelName'),
                                'seller_management_code': channel_product.get('sellerManagementCode'),
                                'reg_date': channel_product.get('regDate'),
                                'modified_date': channel_product.get('modifiedDate'),
                                'representative_image_url': channel_product.get('representativeImage', {}).get('url'),
                                'whole_category_name': channel_product.get('wholeCategoryName'),
                                'whole_category_id': channel_product.get('wholeCategoryId'),
                                'delivery_fee': channel_product.get('deliveryFee', 0),
                                'return_fee': channel_product.get('returnFee', 0),
                                'exchange_fee': channel_product.get('exchangeFee', 0),
                                'discount_method': '',
                                'customer_benefit': ''
                            }
                            
                            self.app.db_manager.save_product(product_data)
                
                # 상품 상태별 필터링
                from env_config import config
                saved_statuses = config.get('PRODUCT_STATUS_TYPES', 'SALE')
                status_list = [s.strip() for s in saved_statuses.split(',')]
                print(f"홈탭 조회 필터링 상태: {status_list}")
                
                filtered_products = []
                for product in products:
                    if isinstance(product, dict):
                        channel_products = product.get('channelProducts', [])
                        if channel_products:
                            channel_product = channel_products[0]
                            status = channel_product.get('statusType')
                            if status in status_list:
                                filtered_products.append(product)
                
                print(f"홈탭 필터링: {len(products)}개 → {len(filtered_products)}개")
                
                # UI 업데이트
                self.app.root.after(0, self._update_products_tree, filtered_products)
                self.app.root.after(0, lambda: self.products_status_var.set(f"상품 {len(filtered_products)}개 조회 완료 (필터링됨)"))
                
            else:
                error_msg = f"상품 조회 실패: {response.get('error', '응답 없음') if response else '네트워크 오류'}"
                print(error_msg)
                self.app.root.after(0, lambda: self.products_status_var.set("상품 조회 실패"))
                
        except Exception as e:
            print(f"홈탭 상품 조회 오류: {e}")
            self.app.root.after(0, lambda: self.products_status_var.set(f"조회 오류: {str(e)}"))
    
    def load_saved_products(self):
        """저장된 상품 조회"""
        try:
            # 상품 상태 설정 로드
            from env_config import config
            saved_statuses = config.get('PRODUCT_STATUS_TYPES', 'SALE,OUTOFSTOCK,CLOSE')
            status_list = [s.strip() for s in saved_statuses.split(',')]
            
            # 데이터베이스에서 상품 로드
            products = self.app.db_manager.get_products()
            
            if products:
                # 상태별 필터링 (데이터베이스 필드명: status_type)
                filtered_products = []
                for product in products:
                    if product.get('status_type') in status_list:
                        filtered_products.append(product)
                
                print(f"홈탭 저장된 상품 필터링: {len(products)}개 → {len(filtered_products)}개")
                
                # UI 업데이트
                self._update_products_tree(filtered_products)
                self.products_status_var.set(f"저장된 상품 {len(filtered_products)}개 로드 완료")
            else:
                self.products_status_var.set("저장된 상품이 없습니다.")
                
        except Exception as e:
            print(f"홈탭 저장된 상품 로드 오류: {e}")
            self.products_status_var.set(f"로드 오류: {str(e)}")
    
    def get_selected_product_statuses(self):
        """설정에서 선택된 상품 상태들 가져오기"""
        try:
            status_string = config.get('PRODUCT_STATUS_TYPES', 'SALE,WAIT')  # 기본값
            if status_string:
                return [status.strip() for status in status_string.split(',') if status.strip()]
            else:
                return ['SALE', 'WAIT']  # 기본값
        except Exception as e:
            print(f"상품 상태 설정 로드 오류: {e}")
            return ['SALE', 'WAIT']  # 기본값
    
    def update_status_display(self):
        """상품 상태 표시 업데이트"""
        try:
            selected_statuses = self.get_selected_product_statuses()
            status_names = {'SALE': '판매중', 'WAIT': '판매대기', 'OUTOFSTOCK': '품절', 
                           'SUSPENSION': '판매중지', 'CLOSE': '종료', 'PROHIBITION': '금지'}
            
            display_names = [status_names.get(status, status) for status in selected_statuses]
            display_text = ', '.join(display_names)
            
            if display_text:
                self.status_display_var.set(display_text)
            else:
                self.status_display_var.set("설정에서 상품 상태를 설정해주세요")
                
        except Exception as e:
            print(f"상품 상태 표시 업데이트 오류: {e}")
            self.status_display_var.set("상태 로드 오류")
    
    def go_to_settings(self):
        """설정 탭으로 이동"""
        try:
            # 탭 컨트롤에서 설정 탭 선택
            self.app.notebook.select(5)  # 설정 탭은 6번째 탭 (인덱스 5)
        except Exception as e:
            print(f"설정 탭 이동 오류: {e}")
            messagebox.showinfo("안내", "설정 탭에서 상품 상태를 변경해주세요.")
    
    
    def _update_products_tree(self, products):
        """상품 트리뷰 업데이트 (API 응답 및 데이터베이스 데이터 모두 처리)"""
        # 기존 데이터 삭제
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        
        # 새 데이터 추가
        for product in products:
            if isinstance(product, dict):
                # 데이터베이스에서 가져온 플랫 구조인지 확인
                if 'channel_product_no' in product:
                    # 데이터베이스 구조
                    product_id = product.get('channel_product_no', 'N/A')
                    product_name = product.get('product_name', 'N/A')
                    status = product.get('status_type', 'N/A')
                    sale_price = product.get('sale_price', 0)
                    discounted_price = product.get('discounted_price', 0)  # 할인된 최종 가격
                    discount_amount = sale_price - discounted_price if discounted_price else 0  # 실제 할인 금액
                    actual_price = discounted_price if discounted_price else sale_price
                    stock = product.get('stock_quantity', 0)
                    origin_product_id = product.get('origin_product_no', 'N/A')
                    
                    self.products_tree.insert('', 'end', values=(
                        product_id, product_name, status, 
                        f"{sale_price:,}", f"{discount_amount:,}", f"{actual_price:,}",
                        stock, origin_product_id
                    ))
                else:
                    # API 응답 구조
                    origin_product_id = product.get('originProductNo', 'N/A')
                    
                    # channelProducts 배열에서 첫 번째 채널 상품 정보 사용
                    channel_products = product.get('channelProducts', [])
                    if channel_products and len(channel_products) > 0:
                        channel_product = channel_products[0]
                        product_id = channel_product.get('channelProductNo', 'N/A')
                        product_name = channel_product.get('name', 'N/A')
                        status = channel_product.get('statusType', 'N/A')
                        sale_price = channel_product.get('salePrice', 0)
                        discounted_price = channel_product.get('discountedPrice', 0)  # 할인된 최종 가격
                        discount_amount = sale_price - discounted_price if discounted_price else 0  # 실제 할인 금액
                        actual_price = discounted_price if discounted_price else sale_price
                        stock = channel_product.get('stockQuantity', 0)
                        
                        self.products_tree.insert('', 'end', values=(
                            product_id, product_name, status, 
                            f"{sale_price:,}", f"{discount_amount:,}", f"{actual_price:,}",
                            stock, origin_product_id
                        ))
                    else:
                        # 채널 상품이 없는 경우
                        self.products_tree.insert('', 'end', values=(
                            'N/A', 'N/A', 'N/A', '0', '0', '0', '0', origin_product_id
                        ))
    
    
    def refresh_product_status_display(self):
        """상품 상태 표시 새로고침 (설정에서 호출)"""
        self.update_status_display()
        # 현재 표시된 상품들도 다시 필터링
        self.load_saved_products()
    
    def show_orders_by_status(self, status):
        """특정 상태의 주문 조회"""
        try:
            # 주문관리 탭으로 이동
            self.app.notebook.select(1)  # 주문관리 탭은 2번째 탭 (인덱스 1)
            messagebox.showinfo("안내", f"{status} 주문을 조회합니다.\n주문관리 탭에서 해당 상태로 필터링하여 조회해주세요.")
        except Exception as e:
            print(f"주문 상태별 조회 오류: {e}")
            messagebox.showinfo("안내", f"{status} 주문 조회 기능은 주문관리 탭에서 이용해주세요.")
    
