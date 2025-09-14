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

**네이버 쇼핑 주문관리 시스템** - 듀얼 인터페이스를 제공하는 전자상거래 주문 관리 시스템입니다. GUI 앱과 웹 인터페이스가 공통 데이터베이스와 비즈니스 로직을 공유하여 일관된 사용자 경험을 제공합니다.

### 듀얼 시스템 구조

이 시스템은 두 가지 운영 방식을 지원합니다:

1. **GUI 앱**: Python Tkinter 기반 데스크탑 애플리케이션 (로컬 작업 최적화)
2. **웹 서버**: FastAPI 기반 경량 웹 인터페이스 (원격 접속 및 EC2 운영)

### 핵심 구성요소

#### 공통 비즈니스 로직 레이어
- **database.py** - SQLite 데이터베이스 매니저 (주문, 상품, 설정, 알림 스키마)
- **naver_api.py** - 네이버 쇼핑 API 클라이언트 (커스텀 OAuth2 구현)
- **notification_manager.py** - 다중 채널 알림 시스템 (데스크탑 + 디스코드)
- **env_config.py** - 타입 안전 환경 설정 매니저 (.env 파일 지원)
- **tabs/** - 비즈니스 로직 모듈 (18개 전문 탭, GUI/웹 공통 사용)

#### GUI 인터페이스 (main.py)
- **main.py** - 메인 GUI 애플리케이션 (모든 탭 조정)
- **ui_utils.py** - GUI 전용 유틸리티 함수 및 컨텍스트 메뉴

#### 웹 인터페이스 (web_server.py)
- **web_server.py** - 경량 FastAPI 웹 서버 (백그라운드 모니터링 포함)
- **templates/** - HTML 템플릿 (반응형 웹 UI)

#### 선택적 구성요소
- **background_monitor.py** - 독립적인 백그라운드 모니터링 서비스 (선택사항)

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