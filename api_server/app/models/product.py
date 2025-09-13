"""
상품 모델
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from .base import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_product_no = Column(String, unique=True, nullable=False, index=True)
    origin_product_no = Column(String)
    product_name = Column(String, nullable=False)
    status_type = Column(String)
    sale_price = Column(Integer, default=0)
    discounted_price = Column(Integer, default=0)
    stock_quantity = Column(Integer, default=0)
    category_id = Column(String)
    category_name = Column(String)
    brand_name = Column(String)
    manufacturer_name = Column(String)
    model_name = Column(String)
    seller_management_code = Column(String)
    reg_date = Column(String)
    modified_date = Column(String)
    representative_image_url = Column(Text)
    whole_category_name = Column(Text)
    whole_category_id = Column(String)
    delivery_fee = Column(Integer, default=0)
    return_fee = Column(Integer, default=0)
    exchange_fee = Column(Integer, default=0)
    discount_method = Column(Text)
    customer_benefit = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Product(id={self.id}, channel_product_no='{self.channel_product_no}', name='{self.product_name}')>"