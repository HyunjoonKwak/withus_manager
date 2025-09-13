"""
알림 관련 서비스 로직
"""
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.notification_log import NotificationLog

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification_log(
        self, 
        order_id: str, 
        notification_type: str, 
        message: str
    ) -> NotificationLog:
        """알림 로그 생성"""
        db_log = NotificationLog(
            order_id=order_id,
            notification_type=notification_type,
            message=message
        )
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return db_log

    def get_notifications_by_order(self, order_id: str) -> List[NotificationLog]:
        """주문 ID로 알림 로그 조회"""
        return self.db.query(NotificationLog).filter(
            NotificationLog.order_id == order_id
        ).order_by(NotificationLog.sent_at.desc()).all()

    def get_notifications_by_type(self, notification_type: str) -> List[NotificationLog]:
        """알림 타입별 로그 조회"""
        return self.db.query(NotificationLog).filter(
            NotificationLog.notification_type == notification_type
        ).order_by(NotificationLog.sent_at.desc()).all()

    def get_all_notifications(self) -> List[NotificationLog]:
        """모든 알림 로그 조회"""
        return self.db.query(NotificationLog).order_by(
            NotificationLog.sent_at.desc()
        ).all()