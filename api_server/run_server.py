"""
FastAPI 서버 실행 스크립트
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Server will be available at: http://{settings.HOST}:{settings.PORT}")
    print("API Documentation: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,  # 개발 모드에서는 항상 reload 활성화
        log_level="info"
    )