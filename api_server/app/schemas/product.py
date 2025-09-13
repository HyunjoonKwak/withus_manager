"""
상품 관련 스키마
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    """상품 기본 스키마"""
    channel_product_no: str = Field(..., description="채널 상품 번호")
    origin_product_no: Optional[str] = Field(None, description="원본 상품 번호")
    product_name: str = Field(..., description="상품명")
    status_type: Optional[str] = Field(None, description="상품 상태")
    sale_price: Optional[int] = Field(0, description="판매 가격")
    discounted_price: Optional[int] = Field(0, description="할인 가격")
    stock_quantity: Optional[int] = Field(0, description="재고 수량")
    category_id: Optional[str] = Field(None, description="카테고리 ID")
    category_name: Optional[str] = Field(None, description="카테고리명")
    brand_name: Optional[str] = Field(None, description="브랜드명")
    manufacturer_name: Optional[str] = Field(None, description="제조사명")
    model_name: Optional[str] = Field(None, description="모델명")
    seller_management_code: Optional[str] = Field(None, description="판매자 관리 코드")
    reg_date: Optional[str] = Field(None, description="등록 일자")
    modified_date: Optional[str] = Field(None, description="수정 일자")
    representative_image_url: Optional[str] = Field(None, description="대표 이미지 URL")
    whole_category_name: Optional[str] = Field(None, description="전체 카테고리명")
    whole_category_id: Optional[str] = Field(None, description="전체 카테고리 ID")
    delivery_fee: Optional[int] = Field(0, description="배송비")
    return_fee: Optional[int] = Field(0, description="반품비")
    exchange_fee: Optional[int] = Field(0, description="교환비")
    discount_method: Optional[str] = Field(None, description="할인 방식")
    customer_benefit: Optional[str] = Field(None, description="고객 혜택")

class ProductCreate(ProductBase):
    """상품 생성 스키마"""
    pass

class ProductUpdate(BaseModel):
    """상품 업데이트 스키마"""
    origin_product_no: Optional[str] = None
    product_name: Optional[str] = None
    status_type: Optional[str] = None
    sale_price: Optional[int] = None
    discounted_price: Optional[int] = None
    stock_quantity: Optional[int] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    manufacturer_name: Optional[str] = None
    model_name: Optional[str] = None
    seller_management_code: Optional[str] = None
    reg_date: Optional[str] = None
    modified_date: Optional[str] = None
    representative_image_url: Optional[str] = None
    whole_category_name: Optional[str] = None
    whole_category_id: Optional[str] = None
    delivery_fee: Optional[int] = None
    return_fee: Optional[int] = None
    exchange_fee: Optional[int] = None
    discount_method: Optional[str] = None
    customer_benefit: Optional[str] = None

class ProductResponse(ProductBase):
    """상품 응답 스키마"""
    id: int = Field(..., description="상품 DB ID")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    
    class Config:
        from_attributes = True