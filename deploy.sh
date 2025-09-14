#!/bin/bash

# WithUs Order Management - 경량 웹서버 배포 스크립트 (t2.micro 최적화)

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

# 로깅 함수
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# 변수 설정
PROJECT_NAME="withus-order-lightweight"
APP_DIR="/opt/$PROJECT_NAME"
SERVICE_NAME="withus-order"
SERVICE_PORT=8000

echo "========================================"
echo "🚀 WithUs Order Management 경량 배포"
echo "   t2.micro 최적화 버전"
echo "========================================"

# 1. 시스템 업데이트 및 기본 패키지 설치
log "시스템 패키지 업데이트 중..."
if command -v yum &> /dev/null; then
    # Amazon Linux
    sudo yum update -y
    sudo yum install -y python3 python3-pip git curl
elif command -v apt &> /dev/null; then
    # Ubuntu/Debian
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv git curl
else
    error "지원되지 않는 운영체제입니다."
    exit 1
fi

# 2. 애플리케이션 디렉토리 생성
log "애플리케이션 디렉토리 설정 중..."
sudo mkdir -p $APP_DIR
sudo chown $(whoami):$(whoami) $APP_DIR
cd $APP_DIR

# 3. Python 가상환경 생성
log "Python 가상환경 설정 중..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 4. Python 패키지 설치 (경량화)
log "필수 Python 패키지 설치 중..."
pip install --upgrade pip

cat > requirements_light.txt << 'EOL'
# 경량 웹서버용 최소 의존성
fastapi==0.104.1
uvicorn[standard]==0.24.0
jinja2==3.1.2
requests==2.31.0
bcrypt==4.0.1
pybase64==1.3.1

# 기존 프로젝트 호환성
openpyxl>=3.0.0
pandas>=2.0.0
schedule>=1.2.0
plyer>=2.1.0

# 메모리 최적화를 위해 제외된 패키지들:
# - celery, redis (백그라운드 스레드로 대체)
# - sqlalchemy (SQLite 직접 사용)
# - structlog (기본 logging 사용)
EOL

pip install -r requirements_light.txt

# 5. 환경 변수 템플릿 생성
log "환경 변수 템플릿 생성 중..."
cat > .env.template << 'EOL'
# 애플리케이션 버전 정보
APP_VERSION=1.0.0
APP_BUILD_DATE=2025-09-14

# 네이버 API 설정 (필수 - 실제 값으로 변경 필요)
NAVER_CLIENT_ID=your_client_id_here
NAVER_CLIENT_SECRET=your_client_secret_here

# 데이터베이스 설정
DATABASE_PATH=orders.db

# 디스코드 알림 설정 (선택사항)
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
DISCORD_ENABLED=true

# 알림 설정
DESKTOP_NOTIFICATIONS=false  # 서버에서는 비활성화
CHECK_INTERVAL=300           # 5분 (300초)

# 자동 새로고침 설정
AUTO_REFRESH=true
REFRESH_INTERVAL=600

# 주문 관련 설정
PRODUCT_STATUS_TYPES=SALE,WAIT,OUTOFSTOCK
ORDER_COLUMNS=주문ID,주문자,상품명,옵션정보,수량,금액,배송지주소,배송예정일,주문일시,상태
ORDER_STATUS_TYPES=PAYMENT_WAITING,PAYED,DELIVERING

# 대시보드 설정
DASHBOARD_PERIOD_DAYS=5
QUICK_PERIOD_SETTING=3

# IP 관리 (서버에서는 모든 IP 허용)
ALLOWED_IPS=0.0.0.0

# 웹서버 설정
HOST=0.0.0.0
PORT=8000

# 메모리 최적화 설정
PYTHON_MEMORY_LIMIT=400  # MB (t2.micro 한도 내)
EOL

# 6. systemd 서비스 파일 생성
log "systemd 서비스 생성 중..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOL
[Unit]
Description=WithUs Order Management Lightweight Web Server
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=5
User=$(whoami)
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python web_server.py
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# 메모리 제한 (t2.micro 최적화)
MemoryMax=400M
MemoryHigh=350M

# 리소스 제한
TasksMax=20
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload

# 7. 방화벽 설정
log "방화벽 설정 중..."
if command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=${SERVICE_PORT}/tcp 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
elif command -v ufw &> /dev/null; then
    sudo ufw allow ${SERVICE_PORT} 2>/dev/null || true
fi

# 8. 로그 디렉토리 생성
log "로그 디렉토리 생성 중..."
mkdir -p logs
mkdir -p templates  # 템플릿 디렉토리가 없는 경우

# 9. 배포 완료 안내
log "경량 웹서버 배포 준비 완료!"

echo ""
echo "================================================"
echo "🎉 WithUs Order Management 경량 배포 완료!"
echo "================================================"
echo ""
echo "📋 다음 단계:"
echo "1. 코드 배포:"
echo "   - git clone 또는 rsync로 애플리케이션 파일들을 $APP_DIR에 복사"
echo "   - 특히 다음 파일들이 필요합니다:"
echo "     * web_server.py (메인 웹서버)"
echo "     * database.py, naver_api.py, notification_manager.py"
echo "     * env_config.py, version_utils.py"
echo "     * templates/ 디렉토리"
echo ""
echo "2. 환경 설정:"
echo "   cp .env.template .env"
echo "   vi .env  # 실제 API 키 등 설정"
echo ""
echo "3. 서비스 시작:"
echo "   sudo systemctl start $SERVICE_NAME"
echo "   sudo systemctl enable $SERVICE_NAME"
echo ""
echo "4. 상태 확인:"
echo "   sudo systemctl status $SERVICE_NAME"
echo "   curl http://localhost:${SERVICE_PORT}/health"
echo ""
echo "📡 웹 인터페이스 접속:"
echo "   http://YOUR_EC2_PUBLIC_IP:${SERVICE_PORT}"
echo ""
echo "📊 리소스 사용량 (예상):"
echo "   - 메모리: ~150MB (t2.micro 800MB 중)"
echo "   - CPU: 낮음 (백그라운드 스레드만)"
echo "   - 디스크: ~100MB"
echo ""
echo "🔧 관리 명령어:"
echo "   sudo systemctl start $SERVICE_NAME     # 시작"
echo "   sudo systemctl stop $SERVICE_NAME      # 중지"
echo "   sudo systemctl restart $SERVICE_NAME   # 재시작"
echo "   sudo journalctl -u $SERVICE_NAME -f   # 로그 확인"
echo ""
echo "⚠️  중요 사항:"
echo "   - .env 파일에서 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 설정 필수"
echo "   - DISCORD_WEBHOOK_URL 설정으로 알림 활성화"
echo "   - EC2 보안그룹에서 포트 $SERVICE_PORT 개방 필요"
echo "   - 도메인 연결 시 Route53 또는 DNS 설정"
echo ""
echo "💡 최적화 팁:"
echo "   - 메모리 사용량 모니터링: free -h"
echo "   - 프로세스 확인: ps aux | grep python"
echo "   - 서비스 상태: systemctl status $SERVICE_NAME"
echo "================================================"