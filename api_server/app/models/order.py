"""
주문 모델
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from .base import Base

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, nullable=False, index=True)
    order_date = Column(String, nullable=False)
    customer_name = Column(String)
    customer_phone = Column(String)
    product_name = Column(String)
    quantity = Column(Integer)
    price = Column(Integer)
    status = Column(String, default='신규주문')
    shipping_company = Column(String)
    tracking_number = Column(String)
    memo = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_id='{self.order_id}', status='{self.status}')>"