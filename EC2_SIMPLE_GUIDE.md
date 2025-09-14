# 🚀 EC2 간단 테스트 가이드

WithUs Order Management System을 EC2에서 빠르게 테스트하는 간단한 가이드입니다.

## 📋 준비사항

- EC2 t2.micro 인스턴스 (Ubuntu 20.04/22.04)
- 보안 그룹에서 포트 8000 열기
- SSH 접속 가능

## 🛠️ 배포 단계 (5분 완료)

### Step 1: 기본 패키지 설치
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 및 필수 패키지 설치
sudo apt install -y python3 python3-pip git
```

### Step 2: 소스코드 다운로드
```bash
# GitHub에서 클론
git clone https://github.com/YOUR_USERNAME/withus_manager.git
cd withus_manager
```

### Step 3: 환경 설정
```bash
# 환경 변수 파일 생성
cp .env.example .env

# API 키 설정 (필수)
nano .env
# NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 실제 값으로 변경
# Ctrl + X, Y, Enter로 저장 후 나가기
```

### Step 4: 의존성 설치 및 실행
```bash
# Python 패키지 설치
pip3 install -r requirements.txt

# 웹서버 실행
python3 web_server.py
```

## 🎯 접속 확인

웹 브라우저에서 접속:
```
http://YOUR_EC2_PUBLIC_IP:8000
```

서버 상태 확인:
```bash
curl http://localhost:8000/health
```

## 🔧 문제 해결

**포트 접속 안될 때**:
1. EC2 보안 그룹에서 포트 8000 인바운드 규칙 추가
2. Ubuntu 방화벽 설정: `sudo ufw allow 8000`

**Python 패키지 오류**:
```bash
# pip 업그레이드
python3 -m pip install --upgrade pip

# 다시 설치
pip3 install -r requirements.txt
```

**백그라운드 실행** (선택사항):
```bash
# 세션이 끊어져도 계속 실행
nohup python3 web_server.py &

# 로그 확인
tail -f nohup.out

# 프로세스 중지
pkill -f web_server.py
```

---

💡 **테스트 완료 후**: 실제 서비스 운영 시에는 `deploy.sh`를 사용하여 systemd 서비스로 등록하세요.