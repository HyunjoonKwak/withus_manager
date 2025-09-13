"""
애플리케이션 설정 관리
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 애플리케이션 정보
    APP_NAME: str = "WithUs Order Management API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 데이터베이스 설정
    DATABASE_URL: str = Field(
        default="sqlite:///./orders.db",
        description="Database URL (기존 SQLite 데이터베이스 호환)"
    )
    
    # 네이버 API 설정
    NAVER_CLIENT_ID: str = Field(default="", description="네이버 API 클라이언트 ID")
    NAVER_CLIENT_SECRET: str = Field(default="", description="네이버 API 클라이언트 시크릿")
    
    # JWT 설정
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis 설정
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 알림 설정
    DISCORD_WEBHOOK_URL: Optional[str] = None
    NOTIFICATION_ENABLED: bool = True
    
    # 배경 작업 설정
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()