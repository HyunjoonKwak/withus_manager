"""
배송 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import json

from ui_utils import BaseTab, run_in_thread


class ShippingTab(BaseTab):
    """배송 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.create_shipping_tab()
        self.setup_copy_paste_bindings()
        self.app.root.after(100, self.load_cached_shipping_on_init)
    
    def create_shipping_tab(self):
        """배송 탭 UI 생성"""
        # 설명 라벨 추가
        desc_frame = ttk.Frame(self.frame)
        desc_frame.pack(fill="x", padx=5, pady=5)
        desc_label = ttk.Label(desc_frame,
                              text="배송중- 발송처리 이후 배송중인 주문을 조회하실수 있습니다. *[송장수정모드 켜기]를 클릭하면 배송중 주문의 송장번호를 수정할수 있습니다.\n배송완료 - 발송처리 이후 구매확정 대기중인 주문을 조회할수 있습니다.",
                              font=("맑은 고딕", 14, "bold"),
                              foreground="#666666",
                              wraplength=800)
        desc_label.pack(anchor="w", padx=10)

        # 배송 관리 섹션
        shipping_frame = ttk.LabelFrame(self.frame, text="배송 관리")
        shipping_frame.pack(fill="x", padx=5, pady=5)
        
        # 배송 상태별 조회
        status_frame = ttk.Frame(shipping_frame)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(status_frame, text="배송 상태:").pack(side="left", padx=5)
        
        self.shipping_status_var = tk.StringVar(value="발송대기")
        status_combo = ttk.Combobox(status_frame, textvariable=self.shipping_status_var, 
                                   values=["발송대기", "배송중", "배송완료"], state="readonly")
        status_combo.pack(side="left", padx=5)
        
        ttk.Button(status_frame, text="조회", command=self.query_shipping_orders).pack(side="left", padx=5)
        
        # 배송 주문 목록
        orders_frame = ttk.LabelFrame(self.frame, text="배송 주문 목록")
        orders_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 배송 주문 트리뷰
        columns = ('주문ID', '주문자', '상품명', '주문일시', '배송상태', '배송업체', '송장번호')
        self.shipping_tree = ttk.Treeview(orders_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.shipping_tree.heading(col, text=col)
            self.shipping_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(orders_frame, orient="vertical", command=self.shipping_tree.yview)
        self.shipping_tree.configure(yscrollcommand=scrollbar.set)
        
        self.shipping_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        # 배송 관리 버튼
        management_frame = ttk.Frame(self.frame)
        management_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(management_frame, text="발송 처리", command=self.process_shipping).pack(side="left", padx=5)
        ttk.Button(management_frame, text="배송 완료", command=self.complete_shipping).pack(side="left", padx=5)
        ttk.Button(management_frame, text="송장 번호 입력", command=self.input_tracking_number).pack(side="left", padx=5)
        
        # 상태 표시
        self.shipping_status_var = tk.StringVar()
        self.shipping_status_var.set("대기 중...")
        status_label = ttk.Label(self.frame, textvariable=self.shipping_status_var)
        status_label.pack(pady=5)
    
    def query_shipping_orders(self):
        """배송 주문 조회"""
        try:
            status = self.shipping_status_var.get()
            
            # 데이터베이스에서 해당 상태의 주문 조회
            orders = self.app.db_manager.get_orders_by_status(status)
            
            if orders:
                self._update_shipping_tree(orders)
                self.update_refresh_status_message(len(orders), is_from_api=True)
            else:
                self.shipping_status_var.set(f"{status} 주문이 없습니다.")
                
        except Exception as e:
            print(f"배송 주문 조회 오류: {e}")
            self.shipping_status_var.set(f"조회 오류: {str(e)}")
    
    def _update_shipping_tree(self, orders):
        """배송 트리뷰 업데이트"""
        # 기존 데이터 삭제
        for item in self.shipping_tree.get_children():
            self.shipping_tree.delete(item)
        
        # 새 데이터 추가
        for order in orders:
            if isinstance(order, dict):
                order_id = order.get('orderId', 'N/A')
                orderer_name = order.get('ordererName', 'N/A')
                product_name = order.get('productName', 'N/A')
                order_date = order.get('orderDate', 'N/A')
                shipping_status = order.get('shippingStatus', 'N/A')
                shipping_company = order.get('shippingCompany', 'N/A')
                tracking_number = order.get('trackingNumber', 'N/A')
                
                self.shipping_tree.insert('', 'end', values=(
                    order_id, orderer_name, product_name, order_date, 
                    shipping_status, shipping_company, tracking_number
                ))
    
    def process_shipping(self):
        """발송 처리"""
        try:
            selected_items = self.shipping_tree.selection()
            if not selected_items:
                messagebox.showwarning("경고", "발송 처리할 주문을 선택해주세요.")
                return
            
            # 선택된 주문들의 발송 처리
            for item in selected_items:
                values = self.shipping_tree.item(item, 'values')
                order_id = values[0]
                
                # 데이터베이스에서 주문 상태 업데이트
                self.app.db_manager.update_order_status(order_id, '배송중')
            
            messagebox.showinfo("성공", f"{len(selected_items)}건의 주문 발송 처리가 완료되었습니다.")
            
            # 목록 새로고침
            self.query_shipping_orders()
            
        except Exception as e:
            messagebox.showerror("오류", f"발송 처리 실패: {str(e)}")
    
    def complete_shipping(self):
        """배송 완료"""
        try:
            selected_items = self.shipping_tree.selection()
            if not selected_items:
                messagebox.showwarning("경고", "배송 완료할 주문을 선택해주세요.")
                return
            
            # 선택된 주문들의 배송 완료 처리
            for item in selected_items:
                values = self.shipping_tree.item(item, 'values')
                order_id = values[0]
                
                # 데이터베이스에서 주문 상태 업데이트
                self.app.db_manager.update_order_status(order_id, '배송완료')
            
            messagebox.showinfo("성공", f"{len(selected_items)}건의 주문 배송 완료 처리가 완료되었습니다.")
            
            # 목록 새로고침
            self.query_shipping_orders()
            
        except Exception as e:
            messagebox.showerror("오류", f"배송 완료 처리 실패: {str(e)}")
    
    def input_tracking_number(self):
        """송장 번호 입력"""
        try:
            selected_items = self.shipping_tree.selection()
            if not selected_items:
                messagebox.showwarning("경고", "송장 번호를 입력할 주문을 선택해주세요.")
                return
            
            if len(selected_items) > 1:
                messagebox.showwarning("경고", "송장 번호는 한 번에 하나의 주문만 입력할 수 있습니다.")
                return
            
            item = selected_items[0]
            values = self.shipping_tree.item(item, 'values')
            order_id = values[0]
            
            # 송장 번호 입력 다이얼로그
            tracking_number = tk.simpledialog.askstring("송장 번호 입력", f"주문 ID {order_id}의 송장 번호를 입력하세요:")
            
            if tracking_number:
                # 데이터베이스에서 송장 번호 업데이트
                self.app.db_manager.update_tracking_number(order_id, tracking_number)
                
                messagebox.showinfo("성공", "송장 번호가 입력되었습니다.")
                
                # 목록 새로고침
                self.query_shipping_orders()
            
        except Exception as e:
            messagebox.showerror("오류", f"송장 번호 입력 실패: {str(e)}")
    
    def load_cached_shipping_on_init(self):
        """초기화 시 캐시된 배송 데이터 로드"""
        try:
            orders = self.app.db_manager.get_orders()
            if orders and len(orders) > 0:
                print(f"배송관리 탭 - 캐시된 주문 데이터 {len(orders)}건 로드")
                self._update_shipping_tree(orders)
                if hasattr(self, 'shipping_status_var'):
                    self.shipping_status_var.set(f"저장된 주문 {len(orders)}건 표시 (기존 데이터)")
            else:
                if hasattr(self, 'shipping_status_var'):
                    self.shipping_status_var.set("저장된 주문 데이터가 없습니다.")
        except Exception as e:
            print(f"캐시된 배송 데이터 로드 오류: {e}")
            if hasattr(self, 'shipping_status_var'):
                self.shipping_status_var.set("데이터 로드 오류")
    
    def update_refresh_status_message(self, count, is_from_api=True):
        """새로고침 상태 메시지 업데이트"""
        if is_from_api:
            message = f"조회 완료: {count}건 (최신 데이터)"
        else:
            message = f"저장된 주문 {count}건 표시 (기존 데이터)"
        
        if hasattr(self, 'shipping_status_var'):
            self.shipping_status_var.set(message)
