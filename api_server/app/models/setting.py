"""
설정 모델
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, func
from .base import Base

class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String, primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value[:50]}...')>"