"""
대시보드 관련 API 엔드포인트
"""
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.db.database import get_db
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.notification_service import NotificationService

logger = structlog.get_logger()

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """대시보드 통계 정보 조회"""
    logger.info("Get dashboard stats request")
    
    try:
        order_service = OrderService(db)
        product_service = ProductService(db)
        notification_service = NotificationService(db)
        
        # 주문 통계
        order_counts = order_service.get_order_counts_by_status()
        total_orders = sum(order_counts.values())
        
        # 상품 통계
        all_products = product_service.get_all_products()
        total_products = len(all_products)
        
        # 상품 상태별 통계
        product_status_counts = {}
        for product in all_products:
            status = product.status_type or '미분류'
            product_status_counts[status] = product_status_counts.get(status, 0) + 1
        
        # 최근 알림 수
        recent_notifications = notification_service.get_all_notifications()
        total_notifications = len(recent_notifications[:100])  # 최근 100개
        
        stats = {
            "orders": {
                "total": total_orders,
                "by_status": order_counts
            },
            "products": {
                "total": total_products,
                "by_status": product_status_counts
            },
            "notifications": {
                "recent_count": total_notifications
            }
        }
        
        logger.info("Dashboard stats retrieved successfully", 
                   total_orders=total_orders, 
                   total_products=total_products)
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get dashboard stats", error=str(e))
        raise HTTPException(status_code=500, detail="대시보드 통계 조회 중 오류가 발생했습니다")

@router.get("/recent-orders")
async def get_recent_orders(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """최근 주문 목록 조회"""
    logger.info("Get recent orders request", limit=limit)
    
    try:
        order_service = OrderService(db)
        recent_orders = order_service.get_all_orders()[:limit]
        
        return recent_orders
        
    except Exception as e:
        logger.error("Failed to get recent orders", error=str(e))
        raise HTTPException(status_code=500, detail="최근 주문 조회 중 오류가 발생했습니다")

@router.get("/recent-notifications")
async def get_recent_notifications(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """최근 알림 목록 조회"""
    logger.info("Get recent notifications request", limit=limit)
    
    try:
        notification_service = NotificationService(db)
        recent_notifications = notification_service.get_all_notifications()[:limit]
        
        return recent_notifications
        
    except Exception as e:
        logger.error("Failed to get recent notifications", error=str(e))
        raise HTTPException(status_code=500, detail="최근 알림 조회 중 오류가 발생했습니다")