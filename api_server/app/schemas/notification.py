"""
알림 관련 스키마
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class NotificationLogResponse(BaseModel):
    """알림 로그 응답 스키마"""
    id: int = Field(..., description="알림 로그 ID")
    order_id: Optional[str] = Field(None, description="주문 ID")
    notification_type: Optional[str] = Field(None, description="알림 타입")
    message: Optional[str] = Field(None, description="알림 메시지")
    sent_at: datetime = Field(..., description="발송 일시")
    
    class Config:
        from_attributes = True