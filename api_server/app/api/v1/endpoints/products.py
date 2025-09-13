"""
상품 관련 API 엔드포인트
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.db.database import get_db
from app.services.product_service import ProductService
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.common import SuccessResponse

logger = structlog.get_logger()

router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
async def get_products(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    status: Optional[str] = Query(None, description="상품 상태 필터"),
    db: Session = Depends(get_db)
):
    """상품 목록 조회 (페이징, 필터링 지원)"""
    logger.info("Get products request", page=page, size=size, status=status)
    
    product_service = ProductService(db)
    
    try:
        if status:
            products = product_service.get_products_by_status(status)
        else:
            products = product_service.get_all_products()
        
        # 간단한 페이징 처리
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_products = products[start_idx:end_idx]
        
        return paginated_products
        
    except Exception as e:
        logger.error("Failed to get products", error=str(e))
        raise HTTPException(status_code=500, detail="상품 조회 중 오류가 발생했습니다")

@router.post("/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """새 상품 생성"""
    logger.info("Create product request", channel_product_no=product.channel_product_no)
    
    product_service = ProductService(db)
    
    try:
        # 기존 상품 존재 여부 확인
        existing_product = product_service.get_product_by_channel_no(product.channel_product_no)
        if existing_product:
            raise HTTPException(status_code=400, detail="이미 존재하는 상품입니다")
        
        new_product = product_service.create_product(product.dict())
        logger.info("Product created successfully", channel_product_no=new_product.channel_product_no)
        return new_product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create product", error=str(e))
        raise HTTPException(status_code=500, detail="상품 생성 중 오류가 발생했습니다")

@router.post("/sync", response_model=SuccessResponse)
async def sync_products(db: Session = Depends(get_db)):
    """네이버 API에서 상품 동기화"""
    logger.info("Sync products request")
    # TODO: 네이버 API 호출하여 상품 동기화 로직 구현
    return SuccessResponse(message="상품 동기화 기능 구현 예정")

@router.get("/{channel_product_no}", response_model=ProductResponse)
async def get_product(channel_product_no: str, db: Session = Depends(get_db)):
    """특정 상품 상세 조회"""
    logger.info("Get product detail", channel_product_no=channel_product_no)
    
    product_service = ProductService(db)
    
    try:
        product = product_service.get_product_by_channel_no(channel_product_no)
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get product detail", channel_product_no=channel_product_no, error=str(e))
        raise HTTPException(status_code=500, detail="상품 조회 중 오류가 발생했습니다")

@router.put("/{channel_product_no}", response_model=ProductResponse)
async def update_product(
    channel_product_no: str, 
    product_update: ProductUpdate,
    db: Session = Depends(get_db)
):
    """상품 정보 업데이트"""
    logger.info("Update product request", channel_product_no=channel_product_no)
    
    product_service = ProductService(db)
    
    try:
        updated_product = product_service.update_product(
            channel_product_no, 
            product_update.dict(exclude_unset=True)
        )
        
        if not updated_product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
        logger.info("Product updated successfully", channel_product_no=channel_product_no)
        return updated_product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update product", channel_product_no=channel_product_no, error=str(e))
        raise HTTPException(status_code=500, detail="상품 업데이트 중 오류가 발생했습니다")

@router.delete("/{channel_product_no}", response_model=SuccessResponse)
async def delete_product(
    channel_product_no: str,
    db: Session = Depends(get_db)
):
    """상품 삭제"""
    logger.info("Delete product request", channel_product_no=channel_product_no)
    
    product_service = ProductService(db)
    
    try:
        deleted = product_service.delete_product(channel_product_no)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
        logger.info("Product deleted successfully", channel_product_no=channel_product_no)
        return SuccessResponse(message="상품이 성공적으로 삭제되었습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete product", channel_product_no=channel_product_no, error=str(e))
        raise HTTPException(status_code=500, detail="상품 삭제 중 오류가 발생했습니다")