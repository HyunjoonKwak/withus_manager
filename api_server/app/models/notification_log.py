"""
알림 로그 모델
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from .base import Base

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String)
    notification_type = Column(String)
    message = Column(Text)
    sent_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<NotificationLog(id={self.id}, order_id='{self.order_id}', type='{self.notification_type}')>"