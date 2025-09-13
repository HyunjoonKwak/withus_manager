"""
상품 관련 서비스 로직
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.product import Product

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, product_data: Dict) -> Product:
        """새 상품 생성"""
        db_product = Product(
            channel_product_no=product_data.get('channel_product_no'),
            origin_product_no=product_data.get('origin_product_no'),
            product_name=product_data.get('product_name'),
            status_type=product_data.get('status_type'),
            sale_price=product_data.get('sale_price', 0),
            discounted_price=product_data.get('discounted_price', 0),
            stock_quantity=product_data.get('stock_quantity', 0),
            category_id=product_data.get('category_id'),
            category_name=product_data.get('category_name'),
            brand_name=product_data.get('brand_name'),
            manufacturer_name=product_data.get('manufacturer_name'),
            model_name=product_data.get('model_name'),
            seller_management_code=product_data.get('seller_management_code'),
            reg_date=product_data.get('reg_date'),
            modified_date=product_data.get('modified_date'),
            representative_image_url=product_data.get('representative_image_url'),
            whole_category_name=product_data.get('whole_category_name'),
            whole_category_id=product_data.get('whole_category_id'),
            delivery_fee=product_data.get('delivery_fee', 0),
            return_fee=product_data.get('return_fee', 0),
            exchange_fee=product_data.get('exchange_fee', 0),
            discount_method=product_data.get('discount_method'),
            customer_benefit=product_data.get('customer_benefit')
        )
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def get_product_by_channel_no(self, channel_product_no: str) -> Optional[Product]:
        """채널 상품 번호로 상품 조회"""
        return self.db.query(Product).filter(
            Product.channel_product_no == channel_product_no
        ).first()

    def get_products_by_status(self, status: str) -> List[Product]:
        """상태별 상품 조회"""
        return self.db.query(Product).filter(
            Product.status_type == status
        ).order_by(Product.updated_at.desc()).all()

    def get_all_products(self) -> List[Product]:
        """모든 상품 조회"""
        return self.db.query(Product).order_by(Product.updated_at.desc()).all()

    def update_product(self, channel_product_no: str, product_data: Dict) -> Optional[Product]:
        """상품 정보 업데이트"""
        db_product = self.get_product_by_channel_no(channel_product_no)
        if db_product:
            for key, value in product_data.items():
                if hasattr(db_product, key):
                    setattr(db_product, key, value)
            db_product.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(db_product)
        return db_product

    def delete_product(self, channel_product_no: str) -> bool:
        """상품 삭제"""
        db_product = self.get_product_by_channel_no(channel_product_no)
        if db_product:
            self.db.delete(db_product)
            self.db.commit()
            return True
        return False

    def upsert_product(self, product_data: Dict) -> Product:
        """상품 생성 또는 업데이트 (기존 save_product 로직)"""
        existing_product = self.get_product_by_channel_no(
            product_data.get('channel_product_no')
        )
        
        if existing_product:
            # 기존 상품 업데이트
            for key, value in product_data.items():
                if hasattr(existing_product, key):
                    setattr(existing_product, key, value)
            existing_product.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(existing_product)
            return existing_product
        else:
            # 새 상품 생성
            return self.create_product(product_data)