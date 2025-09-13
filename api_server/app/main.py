"""
WithUs Order Management API - 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.database import create_tables

# 로거 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def create_application() -> FastAPI:
    """FastAPI 애플리케이션 생성"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="네이버 쇼핑 주문 관리 시스템 API",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API 라우터 등록
    app.include_router(api_router, prefix="/api/v1")
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting WithUs Order Management API", version=settings.APP_VERSION)
        logger.info("Initializing database", database_url=settings.DATABASE_URL)
        
        try:
            create_tables()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down WithUs Order Management API")
    
    return app

# 애플리케이션 인스턴스 생성
app = create_application()

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "version": settings.APP_VERSION}