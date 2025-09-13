"""
API v1 라우터 메인
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, orders, products, dashboard

api_router = APIRouter()

# 각 엔드포인트 라우터 등록
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])