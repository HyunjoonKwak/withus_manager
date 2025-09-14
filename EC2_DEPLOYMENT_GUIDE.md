# 🚀 EC2 배포 가이드

WithUs Order Management System을 AWS EC2 t2.micro에 배포하는 완벽한 가이드입니다.

## 📋 배포 전 준비사항

### 1. EC2 인스턴스 생성
- **인스턴스 타입**: t2.micro (프리 티어)
- **OS**: Amazon Linux 2 또는 Ubuntu 20.04/22.04
- **보안 그룹**: SSH(22), HTTP(8000) 포트 열기

### 2. GitHub에 소스코드 업로드
현재 로컬에서 작업 중인 소스코드를 GitHub에 push합니다:

```bash
# 현재 브랜치 확인
git branch

# GitHub에 push (main 또는 stage_2 브랜치)
git push origin stage_2
```

## 🛠️ EC2 배포 단계별 가이드

### Step 1: EC2 인스턴스 접속
```bash
# SSH로 EC2 접속 (키페어 파일 경로 수정 필요)
ssh -i "your-key.pem" ec2-user@your-ec2-public-ip
```

### Step 2: 시스템 업데이트
```bash
# Amazon Linux 2의 경우
sudo yum update -y

# Ubuntu의 경우
sudo apt update && sudo apt upgrade -y
```

### Step 3: 소스코드 클론
```bash
# 홈 디렉토리로 이동
cd ~

# GitHub에서 소스코드 클론 (실제 리포지토리 URL로 변경)
git clone https://github.com/YOUR_USERNAME/withus_manager.git

# 프로젝트 디렉토리로 이동
cd withus_manager

# 브랜치 확인 및 변경 (필요시)
git checkout stage_2
```

### Step 4: 자동 배포 스크립트 실행
```bash
# 배포 스크립트 권한 부여
chmod +x deploy.sh

# 배포 스크립트 실행 (자동으로 모든 설정 완료)
sudo ./deploy.sh
```

### Step 5: 환경 변수 설정
```bash
# 애플리케이션 디렉토리로 이동
cd /opt/withus-order-lightweight

# 환경 변수 파일 편집
sudo nano .env
```

**중요**: `.env` 파일에서 다음 항목들을 실제 값으로 변경하세요:
```env
# 네이버 API 설정 (필수)
NAVER_CLIENT_ID=your_actual_client_id
NAVER_CLIENT_SECRET=your_actual_client_secret

# Discord 웹훅 (선택사항)
DISCORD_WEBHOOK_URL=your_actual_discord_webhook_url
DISCORD_ENABLED=true

# 서버 설정
HOST=0.0.0.0
PORT=8000
```

### Step 6: 서비스 시작
```bash
# 서비스 시작
sudo systemctl start withus-order

# 부팅 시 자동 시작 활성화
sudo systemctl enable withus-order

# 서비스 상태 확인
sudo systemctl status withus-order
```

## 🔍 배포 확인 및 테스트

### 1. 서비스 상태 확인
```bash
# 서비스 로그 확인
sudo journalctl -u withus-order -f

# 프로세스 확인
ps aux | grep python

# 포트 확인
sudo netstat -tlnp | grep :8000
```

### 2. 웹 인터페이스 접속
브라우저에서 다음 URL에 접속:
```
http://YOUR_EC2_PUBLIC_IP:8000
```

### 3. API 헬스체크
```bash
curl http://localhost:8000/health
```

예상 응답:
```json
{"status": "healthy", "message": "WithUs Order Management System is running"}
```

## 🛠️ 문제 해결

### 일반적인 문제들

#### 1. 서비스가 시작되지 않는 경우
```bash
# 상세 로그 확인
sudo journalctl -u withus-order -n 50

# 수동으로 실행해보기
cd /opt/withus-order-lightweight
source venv/bin/activate
python web_server.py
```

#### 2. 의존성 설치 실패
```bash
# Python 버전 확인
python3 --version

# pip 업그레이드
sudo pip3 install --upgrade pip

# 의존성 재설치
cd /opt/withus-order-lightweight
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 포트 8000 접속 불가
```bash
# 방화벽 설정 확인
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-all  # Amazon Linux

# 보안 그룹 설정 확인 (AWS 콘솔에서)
# - 인바운드 규칙에 TCP 8000 포트가 0.0.0.0/0으로 열려있는지 확인
```

#### 4. 메모리 부족
```bash
# 메모리 사용량 확인
free -h

# 서비스 재시작
sudo systemctl restart withus-order

# 메모리 최적화 (필요시)
# .env 파일에서 다음 설정 조정:
# PYTHON_MEMORY_LIMIT=300
```

## 📊 모니터링 및 관리

### 서비스 관리 명령어
```bash
# 서비스 시작
sudo systemctl start withus-order

# 서비스 중지
sudo systemctl stop withus-order

# 서비스 재시작
sudo systemctl restart withus-order

# 서비스 상태 확인
sudo systemctl status withus-order

# 실시간 로그 보기
sudo journalctl -u withus-order -f
```

### 리소스 모니터링
```bash
# 시스템 리소스 확인
htop  # htop 설치 필요: sudo yum install htop

# 메모리 사용량
free -h

# 디스크 사용량
df -h

# 프로세스별 메모리 사용량
ps aux --sort=-%mem | head -10
```

## 🔄 코드 업데이트

새로운 기능이 추가되었을 때 EC2에서 업데이트하는 방법:

```bash
# 프로젝트 디렉토리로 이동
cd /opt/withus-order-lightweight

# 최신 코드 가져오기
sudo git pull origin stage_2

# 의존성 업데이트 (필요시)
source venv/bin/activate
sudo pip install -r requirements.txt

# 서비스 재시작
sudo systemctl restart withus-order

# 상태 확인
sudo systemctl status withus-order
```

## ⚠️ 보안 고려사항

### 1. 환경 변수 보안
```bash
# .env 파일 권한 제한
sudo chmod 600 /opt/withus-order-lightweight/.env

# 파일 소유자 확인
ls -la /opt/withus-order-lightweight/.env
```

### 2. 방화벽 설정
```bash
# Ubuntu의 경우
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8000

# Amazon Linux의 경우 (firewalld)
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## 🎯 성공 지표

배포가 성공적으로 완료되면:
- ✅ `http://YOUR_EC2_IP:8000`에서 웹 인터페이스 접속 가능
- ✅ 메모리 사용량 150MB 이하 유지
- ✅ 네이버 API 연결 정상
- ✅ Discord 알림 전송 정상 (설정한 경우)
- ✅ 백그라운드 모니터링 작동

---

💡 **팁**: 배포 중 문제가 발생하면 `sudo journalctl -u withus-order -f` 명령으로 실시간 로그를 확인하면서 문제를 해결하세요.