"""
공통 스키마 정의
"""
from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginationResponse(BaseModel, Generic[T]):
    """페이징 응답 스키마"""
    data: List[T]
    page: int = Field(..., description="현재 페이지 번호")
    size: int = Field(..., description="페이지당 항목 수")
    total: int = Field(..., description="전체 항목 수")
    total_pages: int = Field(..., description="전체 페이지 수")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    has_prev: bool = Field(..., description="이전 페이지 존재 여부")

class SuccessResponse(BaseModel):
    """성공 응답 스키마"""
    success: bool = True
    message: str = "Operation completed successfully"

class ErrorResponse(BaseModel):
    """오류 응답 스키마"""
    success: bool = False
    message: str
    detail: str = None