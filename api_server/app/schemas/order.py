"""
주문 관련 스키마
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class OrderBase(BaseModel):
    """주문 기본 스키마"""
    order_id: str = Field(..., description="주문 ID")
    order_date: str = Field(..., description="주문 일시")
    customer_name: Optional[str] = Field(None, description="고객 이름")
    customer_phone: Optional[str] = Field(None, description="고객 전화번호")
    product_name: Optional[str] = Field(None, description="상품명")
    quantity: Optional[int] = Field(1, description="수량")
    price: Optional[int] = Field(0, description="가격")
    status: Optional[str] = Field("신규주문", description="주문 상태")
    shipping_company: Optional[str] = Field(None, description="택배회사")
    tracking_number: Optional[str] = Field(None, description="송장번호")
    memo: Optional[str] = Field(None, description="메모")

class OrderCreate(OrderBase):
    """주문 생성 스키마"""
    pass

class OrderUpdate(BaseModel):
    """주문 업데이트 스키마"""
    order_date: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[int] = None
    status: Optional[str] = None
    shipping_company: Optional[str] = None
    tracking_number: Optional[str] = None
    memo: Optional[str] = None

class OrderResponse(OrderBase):
    """주문 응답 스키마"""
    id: int = Field(..., description="주문 DB ID")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    
    class Config:
        from_attributes = True