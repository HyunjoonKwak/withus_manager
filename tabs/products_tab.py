"""
상품관리 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import webbrowser

from ui_utils import BaseTab, run_in_thread, enable_context_menu


class ProductsTab(BaseTab):
    """상품관리 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.create_products_tab()
        self.setup_copy_paste_bindings()
        
        # 탭 생성 후 저장된 상품 데이터 우선 로드
        self.app.root.after(100, self.load_cached_products_on_init)
    
    def create_products_tab(self):
        """상품관리 탭 UI 생성"""
        # 상품 관리 섹션
        product_frame = ttk.LabelFrame(self.frame, text="상품 관리")
        product_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 상품 목록 조회
        product_query_frame = ttk.Frame(product_frame)
        product_query_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(product_query_frame, text="상품목록 조회", command=self.query_products).pack(side="left", padx=5)
        ttk.Button(product_query_frame, text="저장된 상품 조회", command=self.load_saved_products).pack(side="left", padx=5)
        
        # 상품 목록 트리뷰
        product_columns = ('변경', '조회', '상품ID', '상품명', '상태', '원래판매가', '셀러할인가', '실제판매가', '재고', '원상품ID')
        self.products_tree = ttk.Treeview(product_frame, columns=product_columns, show='headings', height=15)
        
        for col in product_columns:
            self.products_tree.heading(col, text=col)
            if col in ['변경', '조회']:
                self.products_tree.column(col, width=60, anchor='center')
            elif col == '상품명':
                self.products_tree.column(col, width=200, anchor='w')  # 상품명만 좌측 정렬
            else:
                self.products_tree.column(col, width=100, anchor='center')  # 나머지는 가운데 정렬
        
        product_scrollbar = ttk.Scrollbar(product_frame, orient="vertical", command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=product_scrollbar.set)
        
        # 버튼 스타일 설정 (제거)
        
        # Treeview 스타일 설정 (포커스 없을 때도 텍스트가 보이도록)
        style = ttk.Style()
        
        # 선택된 항목의 배경색과 텍스트색 설정 (포커스 있을 때)
        style.map('Treeview', 
                  background=[('selected', 'focus', '#0078d4'),    # 포커스 있을 때 파란색
                             ('selected', '!focus', '#e6f3ff')],   # 포커스 없을 때 연한 파란색
                  foreground=[('selected', 'focus', 'white'),     # 포커스 있을 때 흰색 텍스트
                             ('selected', '!focus', 'black')])     # 포커스 없을 때 검은색 텍스트
        
        self.products_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        product_scrollbar.pack(side="right", fill="y", pady=5)
        
        # 상품 트리뷰 이벤트 바인딩
        self.products_tree.bind("<Double-1>", self.on_product_double_click)
        
        # 변경/조회 버튼 기능을 위한 바인딩
        self.products_tree.bind("<ButtonRelease-1>", self.on_product_button_release)
        
        
        # 서버 응답 표시 창
        response_frame = ttk.LabelFrame(self.frame, text="서버 응답")
        response_frame.pack(fill="x", padx=5, pady=5)
        
        self.server_response_text = tk.Text(response_frame, height=6, wrap=tk.WORD)
        response_scrollbar = ttk.Scrollbar(response_frame, orient="vertical", command=self.server_response_text.yview)
        self.server_response_text.configure(yscrollcommand=response_scrollbar.set)
        
        self.server_response_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        response_scrollbar.pack(side="right", fill="y", pady=5)
        
        # 컨텍스트 메뉴 활성화
        enable_context_menu(self.server_response_text)
        
        
        # 상품 상태 표시 (탭 하단)
        self.products_status_var = tk.StringVar()
        self.products_status_var.set("대기 중...")
        status_label = ttk.Label(self.frame, textvariable=self.products_status_var)
        status_label.pack(side="bottom", pady=2)
    
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
                        "네이버 커머스 API가 설정되지 않았습니다.\n설정 탭에서 API 정보를 입력해주세요."
                    )
                    # 기본설정 탭으로 이동
                    self.app.notebook.select(5)
                
                self.app.root.after(0, show_api_error)
                return
            
            self.app.root.after(0, lambda: self.products_status_var.set("상품 목록 조회 중..."))
            
            # 상품 목록 조회
            response = self.app.naver_api.get_products()
            
            if response and response.get('success'):
                data = response.get('data', {})
                products = data.get('contents', [])
                
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
                print(f"조회 필터링 상태: {status_list}")
                
                filtered_products = []
                for product in products:
                    if isinstance(product, dict):
                        channel_products = product.get('channelProducts', [])
                        if channel_products:
                            channel_product = channel_products[0]
                            status = channel_product.get('statusType')
                            if status in status_list:
                                filtered_products.append(product)
                
                print(f"필터링: {len(products)}개 → {len(filtered_products)}개")
                
                # UI 업데이트
                self.app.root.after(0, self._update_products_tree, filtered_products)
                self.app.root.after(0, lambda: self.update_refresh_status_message(len(filtered_products), is_from_api=True))
                
                # 서버 응답 표시
                response_text = f"상품 목록 조회 성공!\n조회된 상품 수: {len(products)}개\n\n응답 데이터:\n{json.dumps(response, indent=2, ensure_ascii=False)}"
                self.app.root.after(0, lambda: self.server_response_text.delete(1.0, tk.END))
                self.app.root.after(0, lambda: self.server_response_text.insert(1.0, response_text))
            else:
                self.app.root.after(0, lambda: self.products_status_var.set("상품 목록 조회 실패"))
                
        except Exception as e:
            print(f"상품 조회 오류: {e}")
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
                
                print(f"저장된 상품 필터링: {len(products)}개 → {len(filtered_products)}개")
                
                # UI 업데이트
                self._update_products_tree(filtered_products)
                self.update_refresh_status_message(len(filtered_products), is_from_api=False)
            else:
                self.products_status_var.set("저장된 상품이 없습니다.")
                
        except Exception as e:
            print(f"저장된 상품 로드 오류: {e}")
            self.products_status_var.set(f"로드 오류: {str(e)}")
    
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
                        "⚙️ 변경", "🔍 조회", product_id, product_name, status, 
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
                            "⚙️ 변경", "🔍 조회", product_id, product_name, status, 
                            f"{sale_price:,}", f"{discount_amount:,}", f"{actual_price:,}",
                            stock, origin_product_id
                        ))
                    else:
                        # 채널 상품이 없는 경우
                        self.products_tree.insert('', 'end', values=(
                            "⚙️ 변경", "🔍 조회", 'N/A', 'N/A', 'N/A', '0', '0', '0', '0', origin_product_id
                        ))
    
    def on_product_double_click(self, event):
        """상품 더블클릭 이벤트"""
        try:
            selection = self.products_tree.selection()
            if not selection:
                return
                
            item = selection[0]
            values = self.products_tree.item(item, 'values')
            if values:
                product_id = values[0]
                print(f"상품 더블클릭: {product_id}")
                # 향후 상품 상세 조회 기능 구현 예정
        except Exception as e:
            print(f"상품 더블클릭 처리 오류: {e}")
    
    def on_product_button_release(self, event):
        """상품 버튼 릴리즈 이벤트 (변경/조회 기능)"""
        try:
            # 클릭한 위치 확인
            region = self.products_tree.identify_region(event.x, event.y)
            if region != "cell":
                return
                
            # 클릭한 컬럼 확인
            column = self.products_tree.identify_column(event.x)
            print(f"클릭한 컬럼: {column}")
            
            item = self.products_tree.identify_row(event.y)
            if item:
                values = self.products_tree.item(item, 'values')
                print(f"선택된 항목 값: {values}")
                
                if column == "#1":  # 첫 번째 컬럼 (변경)
                    if values and len(values) > 9:
                        origin_product_id = values[9]  # 원상품ID
                        product_name = values[3]  # 상품명
                        print(f"원상품 ID: {origin_product_id}")
                        
                        if origin_product_id != 'N/A':
                            self.open_product_edit(origin_product_id, product_name)
                        else:
                            print("유효하지 않은 원상품 ID")
                            
                elif column == "#2":  # 두 번째 컬럼 (조회)
                    if values and len(values) > 2:
                        product_id = values[2]  # 상품ID
                        product_name = values[3]  # 상품명
                        print(f"상품 ID: {product_id}")
                        
                        if product_id != 'N/A':
                            self.open_product_view(product_id, product_name)
                        else:
                            print("유효하지 않은 상품 ID")
                            
        except Exception as e:
            print(f"상품 버튼 릴리즈 처리 오류: {e}")

    def open_product_edit(self, origin_product_id, product_name=""):
        """스마트스토어 상품 수정 페이지 열기 (원상품ID 사용)"""
        try:
            # 스마트스토어 상품 수정 URL (원상품ID 포함)
            url = f"https://sell.smartstore.naver.com/#/products/edit/{origin_product_id}"
            webbrowser.open(url)
            print(f"상품 수정 페이지 열기: 원상품ID {origin_product_id} ({product_name})")
            
            # 상태 메시지 업데이트
            if hasattr(self, 'products_status_var'):
                self.products_status_var.set(f"상품 수정 페이지를 브라우저에서 열었습니다: {product_name}")
                
        except Exception as e:
            print(f"상품 수정 페이지 열기 오류: {e}")
            if hasattr(self, 'products_status_var'):
                self.products_status_var.set(f"페이지 열기 오류: {str(e)}")
    
    def open_product_view(self, product_id, product_name=""):
        """스마트스토어 상품 조회 페이지 열기 (상품ID 사용)"""
        try:
            # 스마트스토어 상품 조회 URL (상품ID 포함)
            url = f"https://smartstore.naver.com/us-shop/products/{product_id}"
            webbrowser.open(url)
            print(f"상품 조회 페이지 열기: 상품ID {product_id} ({product_name})")
            
            # 상태 메시지 업데이트
            if hasattr(self, 'products_status_var'):
                self.products_status_var.set(f"상품 조회 페이지를 브라우저에서 열었습니다: {product_name}")
                
        except Exception as e:
            print(f"상품 조회 페이지 열기 오류: {e}")
            if hasattr(self, 'products_status_var'):
                self.products_status_var.set(f"페이지 열기 오류: {str(e)}")
    
    def load_cached_products_on_init(self):
        """초기화 시 캐시된 상품 데이터 로드"""
        try:
            # 데이터베이스에서 저장된 상품 조회
            products = self.app.db_manager.get_products()
            
            if products and len(products) > 0:
                # 상품 상태 설정에 따른 필터링
                from env_config import config
                saved_statuses = config.get('PRODUCT_STATUS_TYPES', 'SALE,WAIT,OUTOFSTOCK')
                status_list = [s.strip() for s in saved_statuses.split(',')]
                
                # 상태별 필터링
                filtered_products = []
                for product in products:
                    if product.get('status_type') in status_list:
                        filtered_products.append(product)
                
                print(f"상품관리 탭 - 캐시된 상품 데이터 {len(products)}개 중 {len(filtered_products)}개 필터링됨")
                
                if filtered_products:
                    # UI 업데이트
                    self._update_products_tree(filtered_products)
                    
                    # 상태 메시지 설정
                    if hasattr(self, 'products_status_var'):
                        self.products_status_var.set(f"저장된 상품 {len(filtered_products)}개 표시 (기존 데이터)")
                        
                    print("상품관리 탭 - 저장된 상품 데이터 표시 완료")
                else:
                    if hasattr(self, 'products_status_var'):
                        self.products_status_var.set("설정된 상태 조건에 맞는 상품 없음 - 새로고침하여 최신 데이터 조회")
            else:
                print("상품관리 탭 - 저장된 상품 데이터 없음")
                if hasattr(self, 'products_status_var'):
                    self.products_status_var.set("저장된 상품 없음 - 새로고침하여 최신 데이터 조회")
                    
        except Exception as e:
            print(f"상품관리 탭 - 캐시된 상품 로드 오류: {e}")
            if hasattr(self, 'products_status_var'):
                self.products_status_var.set("저장된 데이터 로드 실패")
    
    def update_refresh_status_message(self, count, is_from_api=True):
        """새로고침 후 상태 메시지 업데이트"""
        try:
            if hasattr(self, 'products_status_var'):
                if is_from_api:
                    self.products_status_var.set(f"상품 {count}개 조회 완료 (최신 데이터)")
                else:
                    self.products_status_var.set(f"저장된 상품 {count}개 표시 (기존 데이터)")
        except Exception as e:
            print(f"상품관리 탭 - 상태 메시지 업데이트 오류: {e}")
