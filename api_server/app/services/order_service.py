"""
주문 관련 서비스 로직
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.order import Order

class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, order_data: Dict) -> Order:
        """새 주문 생성"""
        db_order = Order(
            order_id=order_data.get('order_id'),
            order_date=order_data.get('order_date'),
            customer_name=order_data.get('customer_name'),
            customer_phone=order_data.get('customer_phone'),
            product_name=order_data.get('product_name'),
            quantity=order_data.get('quantity', 1),
            price=order_data.get('price', 0),
            status=order_data.get('status', '신규주문'),
            shipping_company=order_data.get('shipping_company'),
            tracking_number=order_data.get('tracking_number'),
            memo=order_data.get('memo')
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """주문 ID로 주문 조회"""
        return self.db.query(Order).filter(Order.order_id == order_id).first()

    def get_orders_by_status(self, status: str) -> List[Order]:
        """상태별 주문 조회"""
        return self.db.query(Order).filter(Order.status == status).order_by(Order.order_date.desc()).all()

    def get_all_orders(self) -> List[Order]:
        """모든 주문 조회"""
        return self.db.query(Order).order_by(Order.order_date.desc()).all()

    def get_orders_by_date_range(self, start_date: str, end_date: str) -> List[Order]:
        """날짜 범위로 주문 조회"""
        return self.db.query(Order).filter(
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).order_by(Order.order_date.desc()).all()

    def update_order_status(self, order_id: str, status: str) -> Optional[Order]:
        """주문 상태 업데이트"""
        db_order = self.get_order_by_id(order_id)
        if db_order:
            db_order.status = status
            db_order.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(db_order)
        return db_order

    def get_order_counts_by_status(self) -> Dict[str, int]:
        """주문 상태별 건수 조회"""
        orders = self.get_all_orders()
        counts = {}
        for order in orders:
            status = order.status or '신규주문'
            counts[status] = counts.get(status, 0) + 1
        return counts

    def upsert_order(self, order_data: Dict) -> Order:
        """주문 생성 또는 업데이트 (기존 add_order 로직)"""
        existing_order = self.get_order_by_id(order_data.get('order_id'))
        
        if existing_order:
            # 기존 주문 업데이트
            for key, value in order_data.items():
                if hasattr(existing_order, key):
                    setattr(existing_order, key, value)
            existing_order.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(existing_order)
            return existing_order
        else:
            # 새 주문 생성
            return self.create_order(order_data)