# WithUs 주문관리 시스템

네이버 쇼핑몰 주문을 효율적으로 관리할 수 있는 데스크탑 애플리케이션입니다.

## 주요 기능

### 📊 대시보드
- 주문 상태별 실시간 현황 표시
- 신규주문, 발송대기, 배송중, 배송완료, 구매확정, 취소주문, 반품주문, 교환주문 건수
- 최근 주문 목록 조회

### 📦 주문 관리
- 네이버 쇼핑 API를 통한 실시간 주문 동기화
- 주문 상태별 필터링 및 조회
- 기간별 주문 현황 분석
- 엑셀 파일 내보내기 기능

### 🚚 택배 관리
- 택배사별 송장번호 등록
- 발송 대기 목록 관리
- 일괄 발송 처리

### ⚙️ 설정 관리
- 네이버 API 연동 설정 (Client ID, Client Secret, Store ID)
- 디스코드 웹훅 알림 설정
- 알림 옵션 설정 (데스크탑, 디스코드)
- 자동 새로고침 설정

### 🔔 알림 시스템
- 데스크탑 푸시 알림
- 디스코드 메신저 알림
- 신규 주문 알림
- 주문 상태 변경 알림
- 긴급 문의 알림

### 🔄 백그라운드 모니터링
- 주기적 주문 상태 체크
- 신규 주문 자동 감지
- 실시간 알림 발송

## 설치 및 실행

### 1. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 설정 파일 구성
`config.ini` 파일에서 다음 정보를 설정하세요:

```ini
[NAVER_API]
client_id = YOUR_CLIENT_ID
client_secret = YOUR_CLIENT_SECRET
store_id = YOUR_STORE_ID

[DISCORD]
webhook_url = YOUR_DISCORD_WEBHOOK_URL
enabled = true

[NOTIFICATIONS]
desktop_notifications = true
discord_notifications = true
check_interval = 300

[SETTINGS]
auto_refresh = true
refresh_interval = 60
```

### 3. 애플리케이션 실행
```bash
python main.py
```

## 네이버 쇼핑 API 설정

1. 네이버 쇼핑 API 개발자 센터에서 애플리케이션 등록
2. Client ID와 Client Secret 발급
3. Store ID 확인
4. 설정 탭에서 API 정보 입력 및 연결 테스트

## 디스코드 알림 설정

1. 디스코드 서버에서 웹훅 URL 생성
2. 설정 탭에서 웹훅 URL 입력
3. 디스코드 알림 활성화

## 사용법

### 홈 화면
- 주문 현황 대시보드 확인
- 새로고침 버튼으로 최신 데이터 업데이트
- 주문 동기화로 네이버 API에서 최신 주문 가져오기

### 주문수집 탭
- 상태별 주문 필터링
- 기간별 주문 조회
- 엑셀 파일로 주문 데이터 내보내기
- 주문 상태 변경 및 메모 추가

### 택배관리 탭
- 발송 대기 주문 목록 확인
- 택배사 및 송장번호 등록
- 일괄 발송 처리

### 설정 탭
- API 연동 설정
- 알림 옵션 설정
- 자동 새로고침 설정

## 파일 구조

```
withus_manager/
├── main.py                 # 메인 애플리케이션
├── database.py            # 데이터베이스 관리
├── naver_api.py           # 네이버 API 연동
├── notification_manager.py # 알림 관리
├── background_monitor.py   # 백그라운드 모니터링
├── config.ini             # 설정 파일
├── requirements.txt       # 필요한 패키지 목록
└── README.md             # 사용 설명서
```

## 주의사항

- 네이버 쇼핑 API 사용 시 API 호출 제한에 주의하세요
- 백그라운드 모니터링은 설정된 간격으로 API를 호출합니다
- 디스코드 웹훅 URL은 보안에 주의하여 관리하세요
- 정기적으로 데이터베이스를 백업하세요

## 문제 해결

### API 연결 오류
- Client ID, Client Secret, Store ID가 올바른지 확인
- 네이버 쇼핑 API 권한이 활성화되어 있는지 확인

### 알림이 오지 않는 경우
- 데스크탑 알림 권한 확인
- 디스코드 웹훅 URL이 올바른지 확인
- 방화벽 설정 확인

### 데이터 동기화 문제
- 네트워크 연결 상태 확인
- API 호출 제한 확인
- 로그 파일 확인

## 라이선스

이 프로젝트는 개인 및 상업적 용도로 자유롭게 사용할 수 있습니다.


