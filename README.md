# WithUs Order Management System

네이버 쇼핑몰 주문 관리를 위한 경량 웹 시스템입니다. 기존 GUI 기반 프로그램을 웹 인터페이스로 전환하여 어디서든 접근 가능하며, EC2 t2.micro 인스턴스에서 안정적으로 운영할 수 있도록 최적화되었습니다.

## 🎯 주요 특징

- **경량 웹 인터페이스**: 기존 tkinter GUI를 웹 버전으로 완전 전환
- **t2.micro 최적화**: 메모리 사용량 ~150MB로 EC2 무료 티어에서 안정 운영
- **실시간 모니터링**: 백그라운드에서 주문 상태 자동 감시
- **개선된 Discord 알림**: 상태변화 + 현재 총건수 + 조회기간 표시
- **단일 포트 운영**: 포트 8000 하나로 웹 + API 통합 서비스

## 🚀 빠른 시작

### 로컬 개발 환경

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/withus_manager.git
cd withus_manager

# 2. 가상환경 및 의존성 설치
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에서 네이버 API 키, Discord 웹훅 등 설정

# 4. 웹 서버 실행
python web_server.py
```

웹 브라우저에서 `http://localhost:8000` 접속

### EC2 배포 (원클릭)

```bash
# EC2 인스턴스에서 실행
curl -o deploy.sh https://raw.githubusercontent.com/your-username/withus_manager/main/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh

# 코드 배포 후 서비스 시작
sudo systemctl start withus-order
sudo systemctl enable withus-order
```

## 📋 시스템 구성

### 웹 인터페이스
- **대시보드**: 주문 현황 실시간 모니터링
- **주문 관리**: 주문 목록 조회 및 관리
- **설정**: API 키 및 알림 설정

### API 엔드포인트
- `GET /health` - 헬스체크
- `GET /api/monitoring/status` - 모니터링 상태
- `POST /api/monitoring/force-check` - 수동 체크
- `GET /api/orders` - 주문 목록
- `GET /api/dashboard/refresh` - 대시보드 새로고침

### 백그라운드 모니터링
- 5분마다 자동으로 주문 상태 확인
- 상태 변화 감지 시 Discord 알림 전송
- 단순한 Python threading으로 구현 (Celery/Redis 불필요)

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

### 기존 구조 대비 개선
| 항목 | 기존 (Celery) | 현재 (Thread) | 절약률 |
|------|-------------|-------------|--------|
| 메모리 | 520MB | 150MB | 71% ↓ |
| 프로세스 | 5개 | 1개 | 80% ↓ |
| 복잡도 | 높음 | 낮음 | 대폭 개선 |

## 🔄 이중 구조 → 단일 웹서버

### Before (문제가 있던 구조)
```
GUI 앱 (main.py) + background_monitor.py
       ↓
두 개의 별도 프로세스 → 혼동, 중복 알림
```

### After (개선된 구조)
```
web_server.py (단일 프로세스)
├── 웹 인터페이스 (기존 GUI → HTML)
├── REST API (네이버 API 호출)
└── 백그라운드 스레드 (모니터링)
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
├── web_server.py          # 메인 웹서버 (경량)
├── main.py               # GUI 버전 (레거시)
├── background_monitor.py # 별도 모니터링 (레거시)
├── templates/            # HTML 템플릿
│   ├── base.html
│   └── home.html
├── tabs/                # 기존 GUI 탭 로직
├── database.py          # SQLite 데이터베이스
├── naver_api.py         # 네이버 쇼핑 API
├── notification_manager.py # 알림 시스템
└── deploy.sh           # EC2 배포 스크립트
```

### 기능 추가
- 새로운 웹 페이지: `templates/` 디렉토리에 HTML 추가
- 새로운 API: `web_server.py`에 엔드포인트 추가
- 기존 로직 활용: `tabs/` 디렉토리의 클래스 메서드 재사용

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