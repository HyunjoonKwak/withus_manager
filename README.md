# WithUs Order Management System

네이버 쇼핑몰 주문 관리를 위한 듀얼 시스템입니다. GUI 앱과 웹 인터페이스를 병행 운영하여 로컬에서는 빠른 작업을, 원격에서는 어디서든 접근 가능하며, EC2 t2.micro 인스턴스에서 안정적으로 운영할 수 있도록 최적화되었습니다.

## 🎯 주요 특징

- **듀얼 인터페이스**: GUI 앱과 웹 인터페이스 병행 지원으로 최적의 사용 환경 제공
- **t2.micro 최적화**: 웹서버 메모리 사용량 ~150MB로 EC2 무료 티어에서 안정 운영
- **실시간 모니터링**: 백그라운드에서 주문 상태 자동 감시
- **개선된 Discord 알림**: 상태변화 + 현재 총건수 + 조회기간 표시
- **공통 데이터**: 동일한 DB와 설정으로 GUI/웹에서 일관된 데이터 관리

## 🚀 빠른 시작

### 🖥️ GUI 앱으로 로컬 사용

```bash
# 1. 저장소 클론
git clone <your-repository-url>
cd withus_manager

# 2. 가상환경 및 의존성 설치
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에서 네이버 API 키, Discord 웹훅 등 실제 값으로 변경
# (환경 변수 설정 섹션 참조)

# 4. GUI 앱 실행 (로컬 작업용)
python main.py
```

### 🌐 웹 서버로 원격 운영

```bash
# 동일한 설정으로 웹 서버 실행
python web_server.py
```

웹 브라우저에서 `http://localhost:8000` 접속

### 💡 두 방식의 차이점

| 구분 | GUI 앱 (`main.py`) | 웹 서버 (`web_server.py`) |
|------|-------------------|------------------------|
| **용도** | 로컬 데스크탑 작업 | 원격 접속, EC2 운영 |
| **장점** | 빠른 반응속도, 네이티브 UI | 어디서든 접속 가능 |
| **적합한 상황** | 개발, 테스트, 일상 작업 | 서버 운영, 외부 접속 |
| **메모리 사용** | ~200MB | ~150MB |
| **리소스** | GUI 라이브러리 필요 | 브라우저만 있으면 됨 |

> 💡 **추천**: 로컬에서는 GUI 앱으로 작업하고, EC2 등 서버에서는 웹 서버로 운영

### EC2 배포 (원클릭)

```bash
# EC2 인스턴스에서 실행
# 1. 저장소 클론 후 배포 스크립트 실행
git clone <your-repository-url>
cd withus_manager
chmod +x deploy.sh
sudo ./deploy.sh

# 2. 코드 배포 후 서비스 시작
sudo systemctl start withus-order
sudo systemctl enable withus-order
```

## 📋 시스템 구성

### 🖥️ GUI 앱 구성 (`main.py`)
- **홈 대시보드**: 주문 현황 실시간 모니터링
- **주문 관리**: 신규주문, 발송대기, 배송중, 배송완료 등 상태별 탭
- **설정 관리**: API 키, Discord 알림, IP 관리 등
- **API 테스트**: 네이버 API 연결 테스트
- **데이터 내보내기**: Excel 파일 생성 및 관리

### 🌐 웹 인터페이스 구성 (`web_server.py`)
- **대시보드**: 주문 현황 실시간 모니터링 (GUI와 동일한 기능)
- **주문 관리**: 주문 목록 조회 및 관리
- **설정**: API 키 및 알림 설정
- **모바일 반응형**: 스마트폰, 태블릿에서도 사용 가능

### 🔄 공통 기능
- **데이터베이스**: 동일한 SQLite DB 공유 (`orders.db`)
- **네이버 API**: 동일한 API 키와 설정 사용
- **Discord 알림**: 상태변화 + 현재 총건수 + 조회기간 표시
- **백그라운드 모니터링**: 5분마다 자동 주문 상태 확인

### 🛠️ API 엔드포인트 (웹서버)
- `GET /health` - 헬스체크
- `GET /api/monitoring/status` - 모니터링 상태
- `POST /api/monitoring/force-check` - 수동 체크
- `GET /api/orders` - 주문 목록
- `GET /api/dashboard/refresh` - 대시보드 새로고침

## 🔧 환경 변수 설정

`.env` 파일에서 다음 항목들을 설정하세요:

```env
# 네이버 API (필수)
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret

# Discord 알림 (선택사항)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_ENABLED=true

# 모니터링 설정
CHECK_INTERVAL=300  # 5분마다 체크
AUTO_REFRESH=true
DASHBOARD_PERIOD_DAYS=5

# 웹서버 설정
HOST=0.0.0.0
PORT=8000
```

## 📊 리소스 사용량

### t2.micro 호환성
- **메모리 사용**: ~150MB (800MB 중)
- **CPU 사용**: 낮음 (백그라운드 스레드만)
- **디스크 사용**: ~100MB
- **네트워크**: 포트 8000만 사용

### 듀얼 시스템 리소스 비교
| 구분 | GUI 앱 | 웹 서버 | 특징 |
|------|-------|---------|------|
| 메모리 | ~200MB | ~150MB | 웹서버가 더 경량 |
| 프로세스 | 1개 | 1개 | 각각 독립 실행 |
| 복잡도 | 중간 | 낮음 | 공통 로직 재사용 |
| 적합성 | 로컬 작업 | 원격 운영 | 상황별 최적화 |

## 🔄 듀얼 시스템 구조

### 🎯 최적화된 구조 (권장)
```
로컬 작업용: main.py (GUI 앱)
     ↓
빠른 반응속도, 네이티브 UI, 모든 기능 활용

원격 운영용: web_server.py (웹 서버)
     ↓
어디서든 접속 가능, EC2 최적화, 모바일 지원
```

### 📊 시스템 아키텍처
```
공통 인프라
├── orders.db (SQLite 데이터베이스)
├── .env (환경 설정 파일)
├── naver_api.py (네이버 API 클라이언트)
└── notification_manager.py (Discord 알림)

GUI 앱 (main.py)
├── 18개 전문 탭 (상태별 주문 관리)
├── 고급 필터링 및 검색
├── Excel 내보내기
└── 실시간 알림

웹 서버 (web_server.py)
├── 반응형 웹 인터페이스
├── REST API 엔드포인트
├── 백그라운드 모니터링 스레드
└── 모바일 최적화
```

## 📱 Discord 알림 예시

```
📊 주문 상태 변화 알림

🕐 확인 시간: 2025-09-14 16:30:25
📅 조회 기간: 최근 5일

📈 상태 변화 및 현재 총건수:
🆕 신규주문: +3건 → 총 15건
🚚 배송중: -2건 → 총 8건

📊 기타 현재 상태:
📦 발송대기: 12건
✅ 배송완료: 45건
```

## 🛠️ 개발 가이드

### 프로젝트 구조
```
withus_manager/
├── main.py               # 🖥️ GUI 애플리케이션 (로컬 작업용)
├── web_server.py         # 🌐 웹 서버 (원격 운영용)
├── background_monitor.py # 📊 별도 모니터링 (선택사항)
├── templates/            # 🎨 HTML 템플릿 (웹서버용)
│   ├── base.html         #     공통 레이아웃
│   └── home.html         #     대시보드 페이지
├── tabs/                # 📋 GUI 탭 모듈 (18개 전문 탭)
│   ├── home_tab.py       #     대시보드 탭
│   ├── orders_tab.py     #     주문 관리 탭
│   └── settings_tab.py   #     설정 탭 등...
├── database.py          # 💾 SQLite 데이터베이스 매니저
├── naver_api.py         # 🛒 네이버 쇼핑 API 클라이언트
├── notification_manager.py # 📢 Discord 알림 시스템
├── env_config.py        # ⚙️ 환경 설정 관리
└── deploy.sh           # 🚀 EC2 배포 스크립트
```

### 기능 추가 가이드

#### 🖥️ GUI 앱 확장
- **새로운 탭 추가**: `tabs/` 디렉토리에 새 탭 클래스 생성
- **기존 탭 수정**: `tabs/` 내 해당 탭 파일 편집
- **새로운 기능**: `main.py`에 메뉴/기능 추가

#### 🌐 웹 서버 확장
- **새로운 웹 페이지**: `templates/` 디렉토리에 HTML 템플릿 추가
- **새로운 API**: `web_server.py`에 FastAPI 엔드포인트 추가
- **기존 로직 재사용**: `tabs/` 디렉토리의 클래스 메서드 활용

#### 🔄 공통 기능 확장
- **데이터베이스**: `database.py`에 새 테이블/쿼리 추가
- **API 연동**: `naver_api.py`에 새 API 메서드 추가
- **알림 기능**: `notification_manager.py`에 새 알림 타입 추가

> 📖 **자세한 개발 가이드**: `DEVELOPMENT_GUIDE.md` 파일을 참조하여 GUI에서 개발한 기능이 웹에서도 자동으로 동작하도록 구현하세요.

## 🚨 문제 해결

### 일반적인 문제들

1. **서비스가 시작되지 않음**
   ```bash
   sudo journalctl -u withus-order -f
   ```

2. **메모리 부족**
   ```bash
   free -h  # 메모리 확인
   sudo systemctl restart withus-order
   ```

3. **Discord 알림이 오지 않음**
   - `.env` 파일의 `DISCORD_WEBHOOK_URL` 확인
   - 웹훅 URL 테스트

4. **네이버 API 연결 실패**
   - `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 확인
   - API 키 유효성 검사

## 📞 지원

- **이슈 신고**: GitHub Issues 탭 활용
- **개선 제안**: Pull Request 환영
- **문의사항**: README 업데이트를 통해 FAQ 제공

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

---

🎉 **WithUs Order Management System**으로 효율적인 쇼핑몰 운영하세요!