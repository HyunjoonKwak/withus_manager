# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

이 파일은 Claude Code (claude.ai/code)가 이 저장소에서 작업할 때 필요한 가이드를 제공합니다.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run GUI application (for local development)
python main.py

# Run web server (for remote access/EC2 deployment)
python web_server.py
# Access via browser: http://localhost:8000
```

### Testing and Development
```bash
# Test Naver API connection
python -c "from naver_api import NaverShoppingAPI; from env_config import config; api = NaverShoppingAPI(config.get('NAVER_CLIENT_ID'), config.get('NAVER_CLIENT_SECRET')); print('Token success:', api.get_access_token())"

# Database inspection
sqlite3 orders.db
# SQLite commands: .tables, .schema orders, SELECT * FROM orders LIMIT 5;

# Background monitoring (optional standalone service)
python background_monitor.py
ps aux | grep background_monitor
```

### Development Workflow
```bash
# For new feature development that auto-syncs between GUI and Web:
# 1. Implement business logic in tabs/ directory
# 2. Add GUI interface in main.py
# 3. Add web API endpoints in web_server.py
# 4. Add web templates in templates/
# See DEVELOPMENT_GUIDE.md for detailed patterns
```

## Project Architecture

**Naver Shopping Order Management System** - A dual-interface e-commerce order management system. GUI app and web interface share common database and business logic for consistent user experience.

**네이버 쇼핑 주문관리 시스템** - 듀얼 인터페이스를 제공하는 전자상거래 주문 관리 시스템입니다. GUI 앱과 웹 인터페이스가 공통 데이터베이스와 비즈니스 로직을 공유하여 일관된 사용자 경험을 제공합니다.

### Key Architecture Principles

1. **Dual Interface System**: Two separate UIs (GUI + Web) sharing identical business logic
2. **Common Logic Layer**: All business logic centralized in `tabs/` directory classes
3. **Interface Independence**: GUI (`main.py`) and Web (`web_server.py`) handle only UI/UX
4. **Shared Data Layer**: Single SQLite database (`orders.db`) accessed by both interfaces
5. **Modular Tab System**: 18+ specialized tab modules for different order management functions

### 듀얼 시스템 구조

이 시스템은 두 가지 운영 방식을 지원합니다:

1. **GUI 앱**: Python Tkinter 기반 데스크탑 애플리케이션 (로컬 작업 최적화)
2. **웹 서버**: FastAPI 기반 경량 웹 인터페이스 (원격 접속 및 EC2 운영)

### Core Components

#### Common Business Logic Layer
- **database.py** - SQLite database manager with schemas for orders, products, settings, notifications
- **naver_api.py** - Naver Shopping API client with custom OAuth2 implementation using bcrypt + base64
- **notification_manager.py** - Multi-channel notification system (desktop + Discord webhooks)
- **env_config.py** - Type-safe environment configuration manager with .env file support
- **tabs/** - Modular business logic (18+ specialized tabs shared by GUI/Web)

#### GUI Interface (main.py)
- **main.py** - Main GUI application coordinating all tabs (Tkinter-based)
- **ui_utils.py** - GUI-specific utilities and context menus

#### Web Interface (web_server.py)
- **web_server.py** - Lightweight FastAPI web server with embedded background monitoring
- **templates/** - HTML templates for responsive web UI (Bootstrap-based)

#### Optional Components
- **background_monitor.py** - Standalone background monitoring service (optional)

### Tab System Architecture

The tabs/ directory contains specialized modules that implement core business logic:

**Order Management Tabs:**
- `home_tab.py` - Dashboard with real-time monitoring
- `new_order_tab.py` - New order processing
- `shipping_pending_tab.py` - Orders pending shipment
- `shipping_in_progress_tab.py` - Orders in transit
- `shipping_completed_tab.py` - Completed orders
- `cancel_tab.py` - Order cancellations
- `return_exchange_tab.py` - Returns and exchanges

**System Management:**
- `basic_settings_tab.py` - Basic application settings
- `condition_settings_tab.py` - Conditional logic settings
- `api_test_tab.py` - API connection testing
- `products_tab.py` - Product catalog management

Each tab class follows a standard pattern:
```python
class TabName:
    def __init__(self, db_manager, api_client):
        # Initialization

    def get_data(self, **filters):
        # Data retrieval logic

    def process_action(self, data):
        # Business logic processing
```

### 데이터베이스 스키마

애플리케이션은 다음 주요 테이블을 가진 SQLite를 사용합니다:
- `orders` - 고객 정보, 상품 상세, 배송 상태, 송장번호를 포함한 주문 레코드
- `products` - 포괄적인 상품 데이터(가격, 재고, 카테고리, 이미지)를 가진 상품 카탈로그
- `settings` - 키-값 애플리케이션 설정 저장소
- `notification_logs` - 알림 히스토리 및 전달 추적

### API 통합

시스템은 다음과 통합됩니다:
- **네이버 쇼핑 API** - 주문 동기화 및 관리용
- **디스코드 웹훅** - 알림 전달용

### 설정

애플리케이션은 환경 기반 설정을 사용합니다:
- **주요 설정**: API 자격 증명 및 설정이 포함된 `.env` 파일
- **설정 관리**: `env_config.py`가 환경 변수에 대한 타입 안전 접근을 제공
- **핵심 설정**: API 자격 증명, 알림 환경설정, 새로고침 간격

### 듀얼 UI 아키텍처

시스템은 동일한 비즈니스 로직을 기반으로 두 가지 인터페이스를 제공합니다:

#### GUI 인터페이스 (`main.py`)
- **모듈러 탭 구조**: 18개 전문 탭으로 구성된 직관적 인터페이스
- **주요 탭들**: 홈 대시보드, 신규주문, 발송대기, 배송중, 배송완료, 설정 등
- **고급 기능**: Excel 내보내기, 고급 필터링, 데스크탑 알림

#### 웹 인터페이스 (`web_server.py`)
- **반응형 디자인**: Bootstrap 기반 모바일 호환 UI
- **RESTful API**: 동일한 비즈니스 로직 호출
- **실시간 업데이트**: JavaScript 기반 동적 콘텐츠

### 공통 비즈니스 로직 시스템

- **모듈화**: 각 기능이 `tabs/` 디렉토리에서 독립 클래스로 구현
- **재사용성**: GUI와 웹에서 동일한 로직 사용
- **일관성**: 동일한 데이터베이스와 API 호출
- **확장성**: 새 기능 추가 시 자동으로 GUI/웹에서 사용 가능

### 백그라운드 모니터링

시스템은 유연한 모니터링 옵션을 제공합니다:

#### 웹 서버 내장 모니터링 (권장)
- `web_server.py`에 Python threading 기반 백그라운드 모니터링 내장
- 경량화된 단일 프로세스 구조
- 웹 인터페이스에서 모니터링 상태 실시간 확인

#### 독립 모니터링 (선택사항)
- `background_monitor.py`를 별도 프로세스로 실행 가능
- GUI 앱 사용 시에도 독립적인 모니터링 가능
- 환경 변수를 통한 확인 간격 설정

## 개발 노트

### 인증 흐름
네이버 API는 클라이언트 시크릿 서명을 위해 bcrypt 해싱과 base64 인코딩을 사용하는 커스텀 OAuth2 구현을 사용합니다.

### 알림 시스템
설정 가능한 활성화/비활성화와 함께 이중 알림 채널(데스크탑 + 디스코드)을 지원합니다.

### 데이터 동기화
주문은 네이버 API에서 동기화되어 오프라인 접근과 더 빠른 UI 렌더링을 위해 로컬 SQLite에 저장됩니다.

### 오류 처리
애플리케이션은 API 실패, 네트워크 문제, 데이터베이스 작업에 대한 포괄적인 오류 처리를 포함합니다.

## 주요 의존성

### 공통 핵심 의존성
- **requests** - 네이버 API 호출을 위한 HTTP 클라이언트
- **bcrypt + pybase64** - 네이버 API OAuth2 서명 생성
- **sqlite3** - 내장 데이터베이스 (별도 설치 불필요)

### GUI 전용 의존성
- **tkinter** - Python 내장 GUI 프레임워크 (별도 설치 불필요)
- **plyer** - 크로스 플랫폼 데스크탑 알림
- **openpyxl + pandas** - Excel 내보내기 기능
- **schedule** - 백그라운드 작업 스케줄링 (background_monitor.py용)

### 웹 서버 전용 의존성
- **FastAPI** - 경량 웹 API 프레임워크
- **uvicorn** - ASGI 서버 (웹 서버 실행)
- **Jinja2** - HTML 템플릿 엔진
- **python-multipart** - 폼 데이터 처리

### 경량화 성과
- ❌ **제거된 무거운 의존성**: SQLAlchemy, Celery, Redis, Pydantic
- ✅ **Python 내장 모듈 활용**: sqlite3, threading, json
- ✅ **최소 의존성 원칙**: 필수 기능만 유지

## 중요한 파일 위치

- **orders.db** - SQLite 데이터베이스 (첫 실행 시 자동 생성)
- **.env** - 환경 설정 (API 키, 설정)
- **tabs/** - 모듈러 UI 컴포넌트 디렉토리 (비즈니스 로직)
- **templates/** - 웹 인터페이스 템플릿
- **DEVELOPMENT_GUIDE.md** - GUI → 웹 자동 연동 개발 가이드
- **__pycache__/** - Python 바이트코드 (개발 중 안전하게 삭제 가능)

## Development Guidelines

### New Feature Development Pattern

**ALWAYS refer to DEVELOPMENT_GUIDE.md for detailed patterns!**

When developing new features, follow this architecture to ensure automatic GUI/Web synchronization:

1. **Business Logic Separation**: Implement all functionality as independent classes in `tabs/` directory
2. **Interface Independence**: GUI and Web handle only UI/UX, business logic is called not implemented
3. **Standard Method Patterns**: Follow `get_*()`, `process_*()`, `check_*()` naming conventions
4. **Common Error Handling**: Use consistent error return formats

### Adding a New Feature Example
```bash
# 1. Create business logic module
tabs/new_feature_tab.py  # Core logic (shared by GUI/Web)

# 2. Add GUI interface
main.py  # Add new tab to GUI

# 3. Add web interface
web_server.py  # Add API endpoints
templates/new_feature.html  # Add web UI template

# Result: Same logic works in both GUI and Web interfaces!
```

### Critical Development Rules

1. **Never put business logic in main.py or web_server.py** - They are UI controllers only
2. **Always use dependency injection** - Pass db_manager and api_client to tab classes
3. **Follow the tab class pattern** - Initialize, get data, process actions
4. **Test both interfaces** - Ensure GUI and Web produce identical results
5. **Use type hints** - Especially for data exchange between components

## Important Development Notes

### Custom Naver API Authentication
The system uses a custom OAuth2 implementation with bcrypt + base64 encoding for client secret signing. This is specific to Naver Shopping API requirements and differs from standard OAuth2 flows.

### Database Schema Considerations
- **orders** table: Contains customer info, product details, shipping status, tracking numbers
- **products** table: Comprehensive product catalog with pricing, inventory, categories, images
- **settings** table: Key-value application configuration storage
- **notification_logs** table: Notification history and delivery tracking

### Notification System
Supports dual notification channels (desktop + Discord) with configurable enable/disable settings. Discord notifications include status changes, current counts, and query periods.

### Background Monitoring
Two approaches available:
1. **Embedded in web server** (recommended): Python threading in web_server.py
2. **Standalone service**: background_monitor.py as separate process

### Error Handling Patterns
The application includes comprehensive error handling for:
- API failures and network issues
- Database operation errors
- Configuration validation
- Background monitoring failures

### Memory Optimization
Web server optimized for EC2 t2.micro (~150MB memory usage) through:
- Minimal dependencies (no SQLAlchemy, Celery, Redis, Pydantic)
- Use of Python built-in modules (sqlite3, threading, json)
- Lightweight FastAPI instead of Django/Flask