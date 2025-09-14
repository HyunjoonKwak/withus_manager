"""
신규주문 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import json

from ui_utils import BaseTab, run_in_thread, enable_context_menu


class NewOrderTab(BaseTab):
    """신규주문 탭 클래스"""

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.last_orders_data = []  # 마지막으로 로드된 주문 데이터 저장
        self.last_api_orders = []  # 마지막 API 조회 결과 저장
        self.is_first_load = True  # 첫 로드 여부
        self.create_tab()
        self.setup_copy_paste_bindings()
        self.update_order_status_display()

        # 탭 생성 후 저장된 주문 데이터 우선 로드
        self.app.root.after(100, self.load_cached_orders_on_init)

    def create_tab(self):
        """신규주문 탭 UI 생성"""
        # 설명 라벨 추가
        desc_frame = ttk.Frame(self.frame)
        desc_frame.pack(fill="x", padx=5, pady=5)
        desc_label = ttk.Label(desc_frame,
                              text="신규주문이란 구매자가 결제완료후 판매자 주문확인 전 주문건입니다. [주문확인] 또는 [발송지연안내], [판매취소]를 할수 있습니다.",
                              font=("맑은 고딕", 14, "bold"),
                              foreground="#666666",
                              wraplength=800)
        desc_label.pack(anchor="w", padx=10)

        # 신규주문 관리 섹션
        collection_frame = ttk.LabelFrame(self.frame, text="신규주문 관리")
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
        period_values = ["1일", "3일", "7일", "15일", "30일"]
        self.period_combo = ttk.Combobox(date_frame, textvariable=self.period_var,
                                        values=period_values, width=8, state="readonly")
        self.period_combo.pack(side="left", padx=5)
        self.period_combo.bind("<<ComboboxSelected>>", self.on_period_selected)

        # 적용 버튼
        ttk.Button(date_frame, text="적용", command=self.apply_period_setting).pack(side="left", padx=5)

        # 주문 상태 필터
        status_frame = ttk.Frame(collection_frame)
        status_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(status_frame, text="주문상태:").pack(side="left", padx=5)
        self.order_status_var = tk.StringVar()
        self.order_status_var.set("PAYED")  # 신규주문은 PAYED 상태

        order_statuses = [
            ("결제완료 (신규주문)", "PAYED"),
        ]

        for text, value in order_statuses:
            ttk.Radiobutton(status_frame, text=text, variable=self.order_status_var,
                          value=value).pack(side="left", padx=5)

        # 버튼 프레임
        button_frame = ttk.Frame(collection_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(button_frame, text="신규주문 조회",
                  command=self.collect_orders).pack(side="left", padx=5)
        ttk.Button(button_frame, text="엑셀 저장",
                  command=self.save_to_excel).pack(side="left", padx=5)

        self.order_status_label = ttk.Label(button_frame, text="")
        self.order_status_label.pack(side="right", padx=5)

        # 주문 목록 프레임
        list_frame = ttk.LabelFrame(self.frame, text="신규주문 목록")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 주문 목록 Treeview
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 컬럼 정의 (환경설정에서 가져옴)
        from env_config import config
        order_columns_str = config.get('ORDER_COLUMNS',
            '주문ID,상품주문ID,주문자,상품명,옵션정보,판매자상품코드,수량,단가,할인금액,금액,결제방법,배송지주소,배송예정일,주문일시,상태')
        self.display_columns = [col.strip() for col in order_columns_str.split(',') if col.strip()]

        # Treeview 생성
        self.tree = ttk.Treeview(tree_frame, columns=self.display_columns, show="headings", height=15)

        # 컬럼 헤더 설정
        for col in self.display_columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c, False))
            self.tree.column(col, width=100, minwidth=50)

        # 스크롤바
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # 패킹
        self.tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # 컨텍스트 메뉴 활성화
        enable_context_menu(self.tree)

        # 기본 날짜 설정 (환경변수에서 가져옴)
        from env_config import config
        default_days = config.get_int('NEW_ORDER_DEFAULT_DAYS', 7)
        self.period_var.set(f"{default_days}일")
        self.set_date_period(default_days)

    def set_date_period(self, days):
        """기간 설정"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.start_date_entry.set_date(start_date.date())
        self.end_date_entry.set_date(end_date.date())

    def on_period_selected(self, event=None):
        """기간설정 콤보박스 선택 이벤트"""
        selected_period = self.period_var.get()
        print(f"신규주문 탭 기간설정 선택: {selected_period}")

    def apply_period_setting(self):
        """기간설정 적용"""
        selected_period = self.period_var.get()
        if not selected_period:
            return

        try:
            # 숫자 부분만 추출
            days = int(selected_period.replace('일', ''))

            # 환경변수에 저장
            from env_config import config
            config.set('NEW_ORDER_DEFAULT_DAYS', str(days))
            config.save()

            # 날짜 범위 설정
            self.set_date_period(days)

            print(f"신규주문 탭 기간설정 적용 및 저장: {days}일")
        except ValueError:
            print(f"잘못된 기간 형식: {selected_period}")

    def collect_orders(self):
        """신규주문 수집"""
        run_in_thread(self._collect_orders_thread)

    def _collect_orders_thread(self):
        """신규주문 수집 스레드"""
        try:
            self.app.root.after(0, lambda: self.order_status_label.config(text="신규주문 조회 중..."))

            # 날짜를 문자열로 변환
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')

            # PAYED 상태로 고정
            order_status = "PAYED"

            print(f"신규주문 탭 - API 조회 시작: {start_date_str} ~ {end_date_str}, 상태: {order_status}")

            # API 호출 (주문관리 탭과 동일한 방식)
            response = self.app.naver_api.get_orders(
                start_date=start_date_str,
                end_date=end_date_str,
                order_status=order_status,
                limit=100
            )

            if response and response.get('success'):
                data = response.get('data', {})
                print(f"신규주문 탭 - API 응답 데이터 구조: {list(data.keys()) if isinstance(data, dict) else type(data)}")

                if isinstance(data, dict) and 'data' in data:
                    raw_orders = data.get('data', [])
                else:
                    raw_orders = []

                print(f"신규주문 탭 - 처리할 주문 수: {len(raw_orders)}")

                if raw_orders:
                    # 주문관리 탭과 동일한 방식으로 데이터 변환
                    processed_orders = []

                    for i, item in enumerate(raw_orders):
                        print(f"신규주문 탭 - 주문 {i+1} 구조: {list(item.keys()) if isinstance(item, dict) else type(item)}")

                        if isinstance(item, dict) and 'content' in item:
                            content = item['content']
                            print(f"신규주문 탭 - 주문 {i+1} content 키들: {list(content.keys()) if isinstance(content, dict) else type(content)}")

                            if 'order' in content and 'productOrder' in content:
                                order_info = content['order']
                                product_order = content['productOrder']

                                # 상품 주문 상태 확인
                                product_order_status = product_order.get('productOrderStatus')
                                print(f"신규주문 탭 - 주문 {i+1} 상태 확인: {product_order_status}")

                                # PAYED 상태만 필터링
                                if product_order_status == 'PAYED':
                                    # 주문관리 탭과 동일한 데이터 구조로 변환
                                    order_data = {
                                        'orderId': order_info.get('orderId'),
                                        'productOrderId': item.get('productOrderId'),
                                        'ordererName': order_info.get('ordererName'),
                                        'productName': product_order.get('productName'),
                                        'productOption': product_order.get('productOption'),
                                        'sellerProductCode': product_order.get('sellerProductCode'),
                                        'quantity': product_order.get('quantity'),
                                        'unitPrice': product_order.get('unitPrice'),
                                        'productDiscountAmount': product_order.get('productDiscountAmount', 0),
                                        'totalPaymentAmount': product_order.get('totalPaymentAmount'),
                                        'paymentMeans': order_info.get('paymentMeans'),
                                        'shippingAddress': product_order.get('shippingAddress'),
                                        'shippingDueDate': product_order.get('shippingDueDate'),
                                        'orderDate': order_info.get('orderDate'),
                                        'orderStatus': product_order_status
                                    }
                                    processed_orders.append(order_data)
                                    print(f"신규주문 탭 - 주문 {i+1} PAYED 상태 확인, 변환 완료: {order_data.get('productName', 'N/A')}")
                                else:
                                    print(f"신규주문 탭 - 주문 {i+1} {product_order_status} 상태로 필터링 제외")

                    print(f"신규주문 탭 - 최종 처리된 주문 수: {len(processed_orders)}")

                    if processed_orders:
                        self.last_api_orders = processed_orders
                        self.app.root.after(0, lambda: self.display_orders(processed_orders))
                        self.app.root.after(0, lambda: self.order_status_label.config(text=f"신규주문 {len(processed_orders)}건 조회 완료"))
                    else:
                        self.app.root.after(0, lambda: self.order_status_label.config(text="신규주문이 없습니다"))
                        self.app.root.after(0, lambda: self.clear_tree())
                else:
                    self.app.root.after(0, lambda: self.order_status_label.config(text="신규주문이 없습니다"))
                    self.app.root.after(0, lambda: self.clear_tree())
            else:
                error_msg = response.get('message', '알 수 없는 오류') if response else '응답이 없습니다'
                self.app.root.after(0, lambda: self.order_status_label.config(text=f"조회 실패: {error_msg}"))
                self.app.root.after(0, lambda: self.clear_tree())

        except Exception as e:
            error_msg = f"신규주문 조회 오류: {str(e)}"
            print(error_msg)
            self.app.root.after(0, lambda: self.order_status_label.config(text=error_msg))

    def display_orders(self, orders):
        """주문 목록 표시"""
        # 기존 데이터 클리어
        self.clear_tree()

        for order in orders:
            # 주문 데이터를 표시 컬럼에 맞게 변환
            row_data = self.convert_order_to_row(order)
            self.tree.insert("", "end", values=row_data)

        self.last_orders_data = orders

    def convert_order_to_row(self, order):
        """주문 데이터를 행 데이터로 변환"""
        row_data = []
        for col in self.display_columns:
            if col == "주문ID":
                row_data.append(order.get('orderId', ''))
            elif col == "상품주문ID":
                row_data.append(order.get('productOrderId', ''))
            elif col == "주문자":
                row_data.append(order.get('ordererName', ''))
            elif col == "상품명":
                row_data.append(order.get('productName', ''))
            elif col == "옵션정보":
                row_data.append(order.get('productOption', ''))
            elif col == "판매자상품코드":
                row_data.append(order.get('sellerProductCode', ''))
            elif col == "수량":
                row_data.append(str(order.get('quantity', '')))
            elif col == "단가":
                row_data.append(f"{order.get('unitPrice', 0):,}")
            elif col == "할인금액":
                row_data.append(f"{order.get('productDiscountAmount', 0):,}")
            elif col == "금액":
                row_data.append(f"{order.get('totalPaymentAmount', 0):,}")
            elif col == "결제방법":
                row_data.append(order.get('paymentMeans', ''))
            elif col == "배송지주소":
                shipping_addr = order.get('shippingAddress', {})
                addr = f"{shipping_addr.get('baseAddress', '')} {shipping_addr.get('detailAddress', '')}"
                row_data.append(addr.strip())
            elif col == "배송예정일":
                shipping_due = order.get('shippingDueDate', '')
                if shipping_due:
                    try:
                        dt = datetime.fromisoformat(shipping_due.replace('Z', '+00:00'))
                        row_data.append(dt.strftime('%Y-%m-%d'))
                    except:
                        row_data.append(shipping_due)
                else:
                    row_data.append('')
            elif col == "주문일시":
                order_date = order.get('orderDate', '')
                if order_date:
                    try:
                        dt = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                        row_data.append(dt.strftime('%Y-%m-%d %H:%M'))
                    except:
                        row_data.append(order_date)
                else:
                    row_data.append('')
            elif col == "상태":
                row_data.append(order.get('productOrderStatus', ''))
            else:
                row_data.append('')

        return row_data

    def clear_tree(self):
        """트리뷰 클리어"""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def sort_treeview(self, col, reverse):
        """트리뷰 정렬"""
        try:
            data_list = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
            data_list.sort(reverse=reverse)

            for index, (val, child) in enumerate(data_list):
                self.tree.move(child, '', index)

            # 다음 클릭시 역순으로 정렬
            self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))
        except Exception as e:
            print(f"정렬 오류: {e}")

    def save_to_excel(self):
        """엑셀 파일로 저장"""
        if not self.last_orders_data:
            messagebox.showwarning("경고", "저장할 신규주문 데이터가 없습니다.")
            return

        try:
            from tkinter import filedialog
            import pandas as pd
            from datetime import datetime

            # 파일 저장 경로 선택
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"신규주문_{timestamp}.xlsx"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialname=default_filename
            )

            if file_path:
                # 데이터 변환
                excel_data = []
                for order in self.last_orders_data:
                    row_data = self.convert_order_to_row(order)
                    excel_data.append(dict(zip(self.display_columns, row_data)))

                # DataFrame 생성 및 저장
                df = pd.DataFrame(excel_data)
                df.to_excel(file_path, index=False, engine='openpyxl')

                messagebox.showinfo("완료", f"신규주문 데이터가 저장되었습니다.\n{file_path}")

        except Exception as e:
            messagebox.showerror("오류", f"엑셀 저장 중 오류가 발생했습니다: {str(e)}")

    def setup_copy_paste_bindings(self):
        """복사/붙여넣기 단축키 설정"""
        self.tree.bind('<Control-c>', self.copy_selection)
        self.tree.bind('<Control-C>', self.copy_selection)

    def copy_selection(self, event):
        """선택된 항목 복사"""
        try:
            selection = self.tree.selection()
            if not selection:
                return

            # 선택된 행들의 데이터를 탭으로 구분하여 클립보드에 복사
            copied_data = []
            for item in selection:
                values = []
                for col in self.display_columns:
                    values.append(str(self.tree.set(item, col)))
                copied_data.append('\t'.join(values))

            # 헤더도 포함
            header = '\t'.join(self.display_columns)
            clipboard_text = header + '\n' + '\n'.join(copied_data)

            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(clipboard_text)

        except Exception as e:
            print(f"복사 오류: {e}")

    def load_cached_orders_on_init(self):
        """초기화 시 캐시된 주문 데이터 로드"""
        try:
            print("신규주문 탭 - 캐시된 주문 로드 시도")
            # 데이터베이스에서 신규주문만 로드
            if hasattr(self.app.db_manager, 'get_orders'):
                cached_orders = self.app.db_manager.get_orders()
                # PAYED 상태만 필터링
                new_orders = [order for order in cached_orders if order.get('productOrderStatus') == 'PAYED']
                if new_orders:
                    print(f"신규주문 탭 - 캐시된 신규주문 {len(new_orders)}건 표시")
                    self.display_orders(new_orders)
                    self.order_status_label.config(text=f"저장된 신규주문 {len(new_orders)}건")
                else:
                    print("신규주문 탭 - 캐시된 신규주문 없음")
        except Exception as e:
            print(f"신규주문 탭 - 캐시된 주문 로드 오류: {e}")

    def update_order_status_display(self):
        """주문 상태 표시 업데이트"""
        # 기본 상태 표시
        self.order_status_label.config(text="신규주문 관리")