# 🛠️ WithUs 주문관리 시스템 개발 가이드

## 📋 목적
이 가이드는 GUI 앱(`main.py`)에서 개발한 기능을 웹 서버(`web_server.py`)에도 자동으로 반영할 수 있도록 하는 개발 원칙과 절차를 제시합니다.

## 🏗️ 아키텍처 원칙

### 1. 공통 로직 분리 (Common Logic Separation)
모든 비즈니스 로직은 독립적인 모듈에 구현하고, GUI와 웹에서 공통으로 사용합니다.

```
📁 공통 로직 레이어
├── database.py          # 데이터베이스 로직
├── naver_api.py         # API 호출 로직
├── notification_manager.py # 알림 처리 로직
└── tabs/                # 비즈니스 로직 모듈
    ├── home_tab.py      # 대시보드 로직
    ├── orders_tab.py    # 주문 관리 로직
    └── ...

📁 인터페이스 레이어
├── main.py              # GUI 인터페이스
└── web_server.py        # 웹 인터페이스
```

### 2. 인터페이스 독립성 (Interface Independence)
GUI와 웹 인터페이스는 오직 UI/UX 처리만 담당하고, 비즈니스 로직은 호출만 합니다.

## 📝 개발 절차

### 🖥️ GUI 앱에서 새 기능 개발 시

#### Step 1: 비즈니스 로직을 독립 모듈로 구현
```python
# tabs/new_feature_tab.py 예시
class NewFeatureTab:
    def __init__(self, db_manager, api_client):
        self.db_manager = db_manager
        self.api_client = api_client

    def get_feature_data(self, **filters):
        """비즈니스 로직 - GUI/웹 공통 사용"""
        # 데이터 처리 로직
        return processed_data

    def process_feature_action(self, action_data):
        """액션 처리 로직 - GUI/웹 공통 사용"""
        # 액션 처리 로직
        return result
```

#### Step 2: GUI에서 UI 구현
```python
# main.py의 탭 추가 부분
from tabs.new_feature_tab import NewFeatureTab

class MainApp:
    def create_new_feature_tab(self):
        # UI 구성
        frame = ttk.Frame(self.notebook)

        # 비즈니스 로직 인스턴스
        self.new_feature = NewFeatureTab(self.db_manager, self.api_client)

        # UI 이벤트 -> 비즈니스 로직 호출
        def on_button_click():
            result = self.new_feature.process_feature_action(data)
            self.update_ui(result)
```

#### Step 3: 웹에서 동일 로직 재사용
```python
# web_server.py의 API 엔드포인트 추가
from tabs.new_feature_tab import NewFeatureTab

@app.get("/api/new-feature")
async def get_new_feature_data():
    new_feature = NewFeatureTab(db_manager, api_client)
    data = new_feature.get_feature_data()
    return {"success": True, "data": data}

@app.post("/api/new-feature/action")
async def process_new_feature_action(action_data: dict):
    new_feature = NewFeatureTab(db_manager, api_client)
    result = new_feature.process_feature_action(action_data)
    return {"success": True, "result": result}
```

#### Step 4: 웹 UI 템플릿 추가
```html
<!-- templates/new_feature.html -->
{% extends "base.html" %}
{% block content %}
<div id="new-feature-container">
    <!-- 웹 UI 구성 -->
</div>
<script>
    // JavaScript로 API 호출
    async function loadFeatureData() {
        const response = await fetch('/api/new-feature');
        const data = await response.json();
        updateUI(data);
    }
</script>
{% endblock %}
```

## 🔧 개발 체크리스트

### ✅ 새 기능 개발 시 필수 확인사항

#### 📋 비즈니스 로직 분리
- [ ] 모든 데이터 처리 로직이 `tabs/` 디렉토리의 독립 클래스에 구현되었는가?
- [ ] GUI 특화 코드(tkinter)가 비즈니스 로직에 포함되지 않았는가?
- [ ] 데이터베이스 접근이 `database.py`를 통해 이루어지는가?
- [ ] API 호출이 `naver_api.py`를 통해 이루어지는가?

#### 🌐 웹 연동 준비
- [ ] 비즈니스 로직 클래스가 웹에서도 사용 가능한가?
- [ ] 필요한 API 엔드포인트가 `web_server.py`에 추가되었는가?
- [ ] 웹 UI 템플릿이 `templates/`에 생성되었는가?
- [ ] 네비게이션 메뉴가 `base.html`에 추가되었는가?

#### 📊 테스트 및 문서화
- [ ] GUI와 웹 양쪽에서 동일한 결과가 나오는가?
- [ ] 에러 처리가 GUI/웹 양쪽에서 적절히 이루어지는가?
- [ ] `README.md`의 기능 목록이 업데이트되었는가?

## 🎯 코딩 표준

### 1. 비즈니스 로직 클래스 명명 규칙
```python
# 올바른 예시
class OrderManagementTab:      # 주문 관리
class ShippingStatusTab:       # 배송 상태
class CustomerAnalyticsTab:    # 고객 분석

# 잘못된 예시 (GUI 특화)
class OrderManagementTkinterTab:
class OrderGUIHandler:
```

### 2. 메서드 명명 규칙
```python
class FeatureTab:
    # 데이터 조회: get_*
    def get_orders(self, **filters): pass
    def get_statistics(self, period): pass

    # 데이터 처리: process_*
    def process_order_update(self, order_data): pass
    def process_bulk_action(self, action): pass

    # 상태 확인: check_*
    def check_api_connection(self): pass
    def check_data_validity(self, data): pass
```

### 3. 에러 처리 표준
```python
def get_feature_data(self):
    try:
        # 비즈니스 로직 실행
        data = self.process_data()
        return {"success": True, "data": data}
    except APIConnectionError as e:
        return {"success": False, "error": "API 연결 오류", "details": str(e)}
    except ValidationError as e:
        return {"success": False, "error": "데이터 검증 오류", "details": str(e)}
    except Exception as e:
        return {"success": False, "error": "예상치 못한 오류", "details": str(e)}
```

## 🚀 자동화 도구

### 개발 도우미 스크립트 (향후 구현)
```bash
# 새 기능 스캐폴딩 생성
python dev_tools/create_feature.py --name "customer_analytics"

# GUI -> 웹 연동 체크
python dev_tools/check_web_integration.py

# 코드 스타일 검사
python dev_tools/lint_business_logic.py
```

## 📋 예시 시나리오

### 시나리오: "고객 분석" 기능 추가

1. **비즈니스 로직 생성** (`tabs/customer_analytics_tab.py`)
2. **GUI 탭 추가** (`main.py`에 탭 등록)
3. **웹 API 추가** (`web_server.py`에 엔드포인트 추가)
4. **웹 템플릿 생성** (`templates/customer_analytics.html`)
5. **테스트 및 문서화**

### 결과
- GUI에서 클릭 한 번으로 고객 분석 데이터 조회
- 웹에서 동일한 API로 고객 분석 차트 표시
- 모바일에서도 반응형으로 동일한 기능 사용

## 🔍 품질 보증

### 개발 완료 전 최종 체크
1. **기능 일치성**: GUI와 웹에서 동일한 결과 출력
2. **에러 처리**: 모든 예외 상황에서 적절한 메시지 표시
3. **성능**: 대용량 데이터에서도 안정적 동작
4. **모바일 호환성**: 웹 인터페이스가 모바일에서 정상 작동

---

이 가이드를 따르면 **GUI에서 개발한 모든 기능이 자동으로 웹에서도 사용 가능**하며, **일관된 사용자 경험**을 제공할 수 있습니다.