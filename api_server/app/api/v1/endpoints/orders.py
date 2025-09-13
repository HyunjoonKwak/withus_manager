"""
주문 관련 API 엔드포인트
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.db.database import get_db
from app.services.order_service import OrderService
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse
from app.schemas.common import PaginationResponse, SuccessResponse

logger = structlog.get_logger()

router = APIRouter()

@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    status: Optional[str] = Query(None, description="주문 상태 필터"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """주문 목록 조회 (페이징, 필터링 지원)"""
    logger.info("Get orders request", page=page, size=size, status=status, start_date=start_date, end_date=end_date)
    
    order_service = OrderService(db)
    
    try:
        if start_date and end_date:
            orders = order_service.get_orders_by_date_range(start_date, end_date)
        elif status:
            orders = order_service.get_orders_by_status(status)
        else:
            orders = order_service.get_all_orders()
        
        # 간단한 페이징 처리 (실제로는 데이터베이스 레벨에서 처리하는 것이 좋음)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_orders = orders[start_idx:end_idx]
        
        return paginated_orders
        
    except Exception as e:
        logger.error("Failed to get orders", error=str(e))
        raise HTTPException(status_code=500, detail="주문 조회 중 오류가 발생했습니다")

@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db)
):
    """새 주문 생성"""
    logger.info("Create order request", order_id=order.order_id)
    
    order_service = OrderService(db)
    
    try:
        # 기존 주문 존재 여부 확인
        existing_order = order_service.get_order_by_id(order.order_id)
        if existing_order:
            raise HTTPException(status_code=400, detail="이미 존재하는 주문 ID입니다")
        
        new_order = order_service.create_order(order.dict())
        logger.info("Order created successfully", order_id=new_order.order_id)
        return new_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create order", error=str(e))
        raise HTTPException(status_code=500, detail="주문 생성 중 오류가 발생했습니다")

@router.post("/sync", response_model=SuccessResponse)
async def sync_orders(db: Session = Depends(get_db)):
    """네이버 API에서 주문 동기화"""
    logger.info("Sync orders request")
    # TODO: 네이버 API 호출하여 주문 동기화 로직 구현
    return SuccessResponse(message="주문 동기화 기능 구현 예정")

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """특정 주문 상세 조회"""
    logger.info("Get order detail", order_id=order_id)
    
    order_service = OrderService(db)
    
    try:
        order = order_service.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get order detail", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail="주문 조회 중 오류가 발생했습니다")

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str, 
    order_update: OrderUpdate,
    db: Session = Depends(get_db)
):
    """주문 정보 업데이트"""
    logger.info("Update order request", order_id=order_id)
    
    order_service = OrderService(db)
    
    try:
        updated_order = order_service.update_order_status(
            order_id, order_update.status
        ) if order_update.status else None
        
        if not updated_order:
            # 다른 필드들도 업데이트 처리 (향후 구현)
            existing_order = order_service.get_order_by_id(order_id)
            if not existing_order:
                raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
            updated_order = existing_order
        
        return updated_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update order", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail="주문 업데이트 중 오류가 발생했습니다")

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str, 
    status: str = Query(..., description="새로운 주문 상태"),
    db: Session = Depends(get_db)
):
    """주문 상태 업데이트"""
    logger.info("Update order status", order_id=order_id, status=status)
    
    order_service = OrderService(db)
    
    try:
        updated_order = order_service.update_order_status(order_id, status)
        if not updated_order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        logger.info("Order status updated successfully", order_id=order_id, status=status)
        return updated_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update order status", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail="주문 상태 업데이트 중 오류가 발생했습니다")

@router.get("/stats/counts")
async def get_order_counts(db: Session = Depends(get_db)):
    """주문 상태별 건수 조회"""
    logger.info("Get order counts request")
    
    order_service = OrderService(db)
    
    try:
        counts = order_service.get_order_counts_by_status()
        return counts
        
    except Exception as e:
        logger.error("Failed to get order counts", error=str(e))
        raise HTTPException(status_code=500, detail="주문 통계 조회 중 오류가 발생했습니다")