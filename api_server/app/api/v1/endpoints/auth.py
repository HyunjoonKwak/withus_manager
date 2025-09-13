"""
인증 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
import structlog

from app.schemas.common import SuccessResponse

logger = structlog.get_logger()

router = APIRouter()
security = HTTPBearer()

@router.post("/login")
async def login():
    """로그인 API"""
    # TODO: JWT 토큰 발급 로직 구현
    logger.info("Login attempt")
    return {
        "access_token": "placeholder-token",
        "token_type": "bearer",
        "message": "Login endpoint - 향후 JWT 구현 예정"
    }

@router.post("/logout", response_model=SuccessResponse) 
async def logout():
    """로그아웃 API"""
    logger.info("Logout attempt")
    return SuccessResponse(message="로그아웃되었습니다")

@router.get("/me")
async def get_current_user():
    """현재 사용자 정보 조회"""
    # TODO: JWT 토큰 검증 및 사용자 정보 반환
    return {
        "user_id": "admin",
        "username": "관리자",
        "role": "admin",
        "message": "Get current user - 향후 JWT 인증 구현 예정"
    }