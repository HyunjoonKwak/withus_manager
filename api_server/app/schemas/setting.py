"""
설정 관련 스키마
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SettingBase(BaseModel):
    """설정 기본 스키마"""
    key: str = Field(..., description="설정 키")
    value: str = Field(..., description="설정 값")

class SettingCreate(SettingBase):
    """설정 생성 스키마"""
    pass

class SettingResponse(SettingBase):
    """설정 응답 스키마"""
    updated_at: datetime = Field(..., description="수정 일시")
    
    class Config:
        from_attributes = True