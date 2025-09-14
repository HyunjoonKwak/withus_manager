# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소에서 작업할 때 필요한 가이드를 제공합니다.

## 개발 명령어

### 환경 설정
```bash
# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
python main.py
```

### 백그라운드 서비스 실행
```bash
# 백그라운드 모니터링 시작 (별도 프로세스로 실행)
python background_monitor.py

# 백그라운드 프로세스 확인
ps aux | grep background_monitor
```

### 듀얼 시스템 워크플로우
```bash
# 🖥️ GUI 앱으로 로컬 개발 (추천)
python main.py

# 🌐 웹 서버로 원격 운영
python web_server.py
# 웹 브라우저: http://localhost:8000

# API 연결 테스트 (독립 실행)
python -c "from naver_api import NaverShoppingAPI; from env_config import config; api = NaverShoppingAPI(config.get('NAVER_CLIENT_ID'), config.get('NAVER_CLIENT_SECRET')); print('Token success:', api.get_access_token())"

# 데이터베이스 검사
sqlite3 orders.db
# SQLite 명령어: .tables, .schema orders, SELECT * FROM orders LIMIT 5;

# 🛠️ 새 기능 개발 시 (GUI → 웹 자동 연동)
# DEVELOPMENT_GUIDE.md 참조하여 개발
```

## 프로젝트 아키텍처

**네이버 쇼핑 주문관리 시스템** - Python Tkinter로 구축된 데스크탑 애플리케이션과 FastAPI 기반 백엔드 API 서버로 구성된 전자상거래 주문 관리 시스템입니다.

### 듀얼 아키텍처 구조

이 시스템은 두 가지 운영 방식을 지원합니다:

1. **데스크탑 앱 (기존)**: Python Tkinter 기반 독립 실행형 애플리케이션
2. **웹 백엔드 (신규)**: FastAPI 기반 REST API 서버로 EC2 배포 가능

### 핵심 구성요소

#### 데스크탑 애플리케이션 (루트 디렉토리)
- **main.py** - 모든 탭과 핵심 서비스를 조정하는 메인 GUI 애플리케이션
- **database.py** - 포괄적인 스키마(주문, 상품, 설정, 알림)를 가진 SQLite 데이터베이스 매니저
- **naver_api.py** - bcrypt/base64 서명을 사용하는 커스텀 OAuth2 구현을 가진 네이버 쇼핑 API 클라이언트
- **notification_manager.py** - 다중 채널 알림 시스템 (데스크탑 + 디스코드)
- **background_monitor.py** - 주기적인 주문 모니터링 및 알림을 위한 백그라운드 서비스
- **env_config.py** - .env 파일 지원을 가진 타입 안전 환경 설정 매니저
- **ui_utils.py** - 공유 UI 유틸리티 함수 및 컨텍스트 메뉴 핸들러

#### FastAPI 백엔드 (api_server/ 디렉토리)
- **app/main.py** - FastAPI 애플리케이션 메인 엔트리포인트
- **app/models/** - SQLAlchemy ORM 모델 (기존 SQLite 스키마와 호환)
- **app/schemas/** - Pydantic 요청/응답 스키마 정의
- **app/services/** - 비즈니스 로직 서비스 레이어
- **app/api/v1/endpoints/** - REST API 엔드포인트 구현
- **app/db/database.py** - 데이터베이스 연결 및 세션 관리
- **app/core/config.py** - Pydantic 기반 설정 관리
- **run_server.py** - 개발용 서버 실행 스크립트
- **test_api.py** - API 기능 테스트 스크립트

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

### UI 아키텍처

메인 애플리케이션(`main.py`)은 모듈러 탭 구조를 가진 탭 인터페이스를 사용합니다:
- **홈 (Home)** - 주문 상태 개요를 보여주는 대시보드 (`tabs/home_tab.py`)
- **주문수집 (Orders)** - 주문 목록 및 관리 (`tabs/orders_tab.py`)
- **택배관리 (Shipping)** - 배송 및 추적 관리 (`tabs/shipping_tab.py`)
- **API 테스트 (API Test)** - API 연결 테스트 (`tabs/api_test_tab.py`)
- **설정 (Settings)** - API 및 알림 설정 (`tabs/settings_tab.py`)

### 모듈러 탭 시스템

애플리케이션은 모듈러 탭 아키텍처를 사용합니다:
- 각 탭은 `tabs/` 디렉토리에서 별도 클래스로 구현됩니다
- 탭들은 `tabs/__init__.py`를 통해 가져오고 관리됩니다
- 공통 UI 유틸리티는 `ui_utils.py`를 통해 공유됩니다
- 각 탭은 핵심 서비스를 공유하면서 자체 상태와 UI 로직을 유지합니다

### 백그라운드 처리

- `background_monitor.py`는 별도 프로세스로 실행됩니다
- 새로운 주문 및 상태 변경을 주기적으로 확인합니다
- 알림 매니저를 통해 알림을 전송합니다
- 환경 변수를 통해 확인 간격을 설정할 수 있습니다

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

### 데스크탑 애플리케이션 의존성
- **requests** - 네이버 API 호출을 위한 HTTP 클라이언트
- **bcrypt + pybase64** - 네이버 API OAuth2 서명 생성에 필요
- **plyer** - 크로스 플랫폼 데스크탑 알림
- **openpyxl + pandas** - 엑셀 내보내기 기능
- **schedule** - 백그라운드 작업 스케줄링

### FastAPI 백엔드 의존성
- **FastAPI** - 고성능 웹 API 프레임워크
- **uvicorn** - ASGI 서버 (개발 및 프로덕션)
- **SQLAlchemy** - ORM 및 데이터베이스 추상화
- **Pydantic** - 데이터 검증 및 설정 관리
- **structlog** - 구조화된 로깅
- **Celery + Redis** - 백그라운드 작업 처리 (향후 구현)
- **python-jose** - JWT 토큰 처리 (향후 구현)
- **pytest** - 테스트 프레임워크

## 중요한 파일 위치

- **orders.db** - SQLite 데이터베이스 (첫 실행 시 자동 생성)
- **.env** - 환경 설정 (API 키, 설정)
- **tabs/** - 모듈러 UI 컴포넌트 디렉토리 (비즈니스 로직)
- **templates/** - 웹 인터페이스 템플릿
- **DEVELOPMENT_GUIDE.md** - GUI → 웹 자동 연동 개발 가이드
- **__pycache__/** - Python 바이트코드 (개발 중 안전하게 삭제 가능)

## 🔧 새 기능 개발 가이드

**DEVELOPMENT_GUIDE.md를 반드시 참조하세요!**

새로운 기능을 개발할 때는 다음 원칙을 따르면 GUI와 웹에서 자동으로 연동됩니다:

1. **비즈니스 로직 분리**: 모든 기능을 `tabs/` 디렉토리의 독립 클래스로 구현
2. **인터페이스 독립성**: GUI와 웹은 오직 UI만 담당, 로직은 호출만
3. **표준 메서드 패턴**: `get_*()`, `process_*()`, `check_*()` 명명 규칙 준수
4. **공통 에러 처리**: 일관된 에러 반환 형식 사용

### 예시: 새 기능 "고객 분석" 추가 시
```bash
# 1. 비즈니스 로직 생성
tabs/customer_analytics_tab.py  # 핵심 로직 (GUI/웹 공통)

# 2. GUI 연동
main.py  # 새 탭 추가

# 3. 웹 연동
web_server.py  # API 엔드포인트 추가
templates/customer_analytics.html  # 웹 UI 템플릿

# 결과: 동일한 로직으로 GUI와 웹에서 모두 사용 가능!
```