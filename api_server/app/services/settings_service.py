"""
설정 관련 서비스 로직
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.setting import Setting

class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def save_setting(self, key: str, value: str) -> Setting:
        """설정 저장 또는 업데이트"""
        db_setting = self.get_setting_by_key(key)
        
        if db_setting:
            db_setting.value = value
            db_setting.updated_at = datetime.now()
        else:
            db_setting = Setting(
                key=key,
                value=value
            )
            self.db.add(db_setting)
        
        self.db.commit()
        self.db.refresh(db_setting)
        return db_setting

    def get_setting_by_key(self, key: str) -> Optional[Setting]:
        """키로 설정 조회"""
        return self.db.query(Setting).filter(Setting.key == key).first()

    def get_setting_value(self, key: str) -> Optional[str]:
        """키로 설정 값 조회"""
        setting = self.get_setting_by_key(key)
        return setting.value if setting else None

    def delete_setting(self, key: str) -> bool:
        """설정 삭제"""
        db_setting = self.get_setting_by_key(key)
        if db_setting:
            self.db.delete(db_setting)
            self.db.commit()
            return True
        return False