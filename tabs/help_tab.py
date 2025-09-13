"""
도움말 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import webbrowser

from ui_utils import BaseTab


class HelpTab(BaseTab):
    """도움말 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.create_help_tab()
    
    def create_help_tab(self):
        """도움말 탭 UI 생성"""
        # 메인 스크롤 가능한 프레임
        main_canvas = tk.Canvas(self.frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg='white')  # ttk.Frame을 tk.Frame으로 변경
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 레이아웃
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 제목
        title_label = tk.Label(scrollable_frame, text="WithUs 주문관리 시스템 도움말", 
                              font=("맑은 고딕", 16, "bold"), bg='white', fg='black')
        title_label.pack(pady=10)
        
        # 참고 링크 (최상단으로 이동)
        self.add_section(scrollable_frame, "📖 네이버 커머스 API 참고 링크", "")
        
        # API 문서 링크 버튼들
        link_frame = tk.Frame(scrollable_frame, bg='white')
        link_frame.pack(pady=10, padx=10, fill='x')
        
        # 메인 API 문서 버튼 (큰 버튼)
        main_api_btn = tk.Button(link_frame, text="📚 네이버 커머스 API 메인 문서", 
                                command=self.open_api_docs,
                                bg='lightblue', fg='black', relief='raised',
                                font=("맑은 고딕", 12, "bold"),
                                padx=30, pady=10)
        main_api_btn.pack(pady=5, fill='x')
        
        # 구분선
        separator = tk.Label(link_frame, text="── 세부 API 문서 ──", 
                           bg='white', fg='gray', font=("맑은 고딕", 10))
        separator.pack(pady=10)
        
        # 세부 API 링크 버튼들 (2열로 배치)
        buttons_data = [
            ("🔐 인증 (OAuth 2.0)", self.open_auth_docs),
            ("📊 API데이터솔루션(통계)", self.open_data_solution_docs),
            ("💬 문의 관리", self.open_inquiry_docs),
            ("📦 상품 관리", self.open_product_docs),
            ("💰 정산 관리", self.open_settlement_docs),
            ("📋 주문 관리", self.open_order_docs),
            ("🔄 교환보류해제", self.open_exchange_release_docs),
            ("❌ 교환거부(철회)", self.open_exchange_reject_docs),
            ("❓ 질문하기 (GitHub)", self.open_github_discussions),
            ("🏪 스마트스토어 센터", self.open_smartstore_center)
        ]
        
        # 2열로 버튼 배치
        for i in range(0, len(buttons_data), 2):
            row_frame = tk.Frame(link_frame, bg='white')
            row_frame.pack(fill='x', pady=2)
            
            # 첫 번째 버튼
            btn1_text, btn1_command = buttons_data[i]
            btn1 = tk.Button(row_frame, text=btn1_text, command=btn1_command,
                           bg='white', fg='black', relief='raised',
                           font=("맑은 고딕", 10), padx=15, pady=5)
            btn1.pack(side='left', fill='x', expand=True, padx=(0, 2))
            
            # 두 번째 버튼 (있는 경우)
            if i + 1 < len(buttons_data):
                btn2_text, btn2_command = buttons_data[i + 1]
                btn2 = tk.Button(row_frame, text=btn2_text, command=btn2_command,
                               bg='white', fg='black', relief='raised',
                               font=("맑은 고딕", 10), padx=15, pady=5)
                btn2.pack(side='left', fill='x', expand=True, padx=(2, 0))
        
        # 1. 시스템 소개
        self.add_section(scrollable_frame, "1. 시스템 소개", """
WithUs 주문관리 시스템은 네이버 쇼핑몰 운영자를 위한 통합 관리 도구입니다.
주문 조회, 상품 관리, 배송 처리 등의 기능을 제공합니다.

주요 기능:
• 실시간 주문 조회 및 관리
• 상품 정보 조회 및 상태 관리
• 배송 정보 관리
• 자동 알림 시스템
• 데이터 내보내기 (Excel)
        """)
        
        # 2. 네이버 커머스 API 정보
        self.add_section(scrollable_frame, "2. 네이버 커머스 API", """
이 시스템은 네이버 커머스 API를 사용합니다.

API 인증:
• Client ID와 Client Secret 필요
• OAuth 2.0 기반 인증 시스템
• bcrypt 해싱을 사용한 보안 서명

주요 API 엔드포인트:
• 주문 조회: GET /v1/products/orders
• 상품 조회: GET /v1/products
• 배송 정보 업데이트: PUT /v1/products/orders/{orderNo}/shipping-info
• 주문 상태 변경: PUT /v1/products/orders/{orderNo}/status

API 제한사항:
• 일일 API 호출 횟수 제한 있음
• 대용량 데이터는 페이징 처리 필요
• 시간 범위는 최대 24시간 단위로 조회 권장
        """)
        
        # 3. 탭별 사용법
        self.add_section(scrollable_frame, "3. 탭별 사용법", """
📊 홈 탭:
• 주문 현황 대시보드
• 상태별 주문 수 실시간 표시
• 대시보드 새로고침 및 기간 설정

📋 주문관리 탭:
• 주문 목록 조회 (날짜 범위 선택 가능)
• 주문 상세 정보 확인
• Excel 파일로 내보내기
• 주문 상태별 필터링

📦 상품관리 탭:
• 판매 중인 상품 목록 조회
• 상품 상태별 필터링 (판매중/대기/품절)
• 상품 정보 상세 보기

🚛 배송관리 탭:
• 배송 상태별 주문 조회
• 발송 처리 및 배송 완료 처리
• 송장 번호 입력 기능

⚙️ 설정 탭:
• API 연결 설정 (Client ID/Secret)
• 알림 설정 (데스크탑/디스코드)
• 새로고침 간격 설정
• 컬럼 표시 설정
        """)
        
        # 4. 설정 방법
        self.add_section(scrollable_frame, "4. 초기 설정 방법", """
1️⃣ API 설정:
• 네이버 커머스 센터에서 API 키 발급
• 기본설정 탭에서 Client ID, Client Secret 입력
• API 테스트 탭에서 연결 확인

2️⃣ 알림 설정:
• 데스크탑 알림 활성화/비활성화
• 디스코드 웹훅 URL 설정 (선택사항)
• 알림 확인 간격 설정

3️⃣ 표시 설정:
• 조건설정 탭에서 주문/상품 컬럼 선택
• 상품 상태 표시 범위 설정
• 대시보드 조회 기간 설정
        """)
        
        # 5. 문제해결
        self.add_section(scrollable_frame, "5. 문제해결", """
🔧 자주 발생하는 문제:

Q: API 연결이 안 됩니다.
A: • Client ID/Secret 확인
   • 네이버 커머스 센터에서 API 권한 확인
   • 네트워크 연결 상태 확인

Q: 주문이 조회되지 않습니다.
A: • 날짜 범위 확인 (너무 긴 기간 설정 시 오류)
   • API 호출 제한 확인
   • 주문 상태 필터 확인

Q: 데이터가 업데이트되지 않습니다.
A: • 새로고침 버튼 클릭
   • 자동 새로고침 설정 확인
   • 데이터베이스 연결 상태 확인

Q: 알림이 오지 않습니다.
A: • 알림 설정 활성화 확인
   • macOS 알림 권한 확인
   • 디스코드 웹훅 URL 확인
        """)
        
        # 6. 버전 정보
        self.add_section(scrollable_frame, "6. 버전 정보", """
WithUs 주문관리 시스템 v2.0
• Python 3.8+ 호환
• tkinter GUI 기반
• SQLite 로컬 데이터베이스
• 네이버 커머스 API 연동

개발: 2024년
최종 업데이트: 2024년 9월
        """)
        
        # 마우스 휠 스크롤 바인딩
        self.bind_mousewheel(main_canvas)
    
    def add_section(self, parent, title, content):
        """섹션 추가"""
        # 제목
        title_label = tk.Label(parent, text=title, font=("맑은 고딕", 12, "bold"), 
                              bg='white', fg='black', anchor='w')
        title_label.pack(fill='x', padx=10, pady=(10, 5))
        
        if content.strip():  # 내용이 있는 경우만
            # 내용
            content_label = tk.Label(parent, text=content.strip(), font=("맑은 고딕", 10), 
                                   bg='white', fg='black', anchor='nw', justify='left', wraplength=800)
            content_label.pack(fill='x', padx=20, pady=(0, 10))
    
    def open_api_docs(self):
        """메인 API 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current")
    
    def open_auth_docs(self):
        """인증 (OAuth 2.0) 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/o-auth-2-0")
    
    def open_data_solution_docs(self):
        """API데이터솔루션(통계) 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/%EA%B3%A0%EA%B0%9D-%EB%8D%B0%EC%9D%B4%ED%84%B0")
    
    def open_inquiry_docs(self):
        """문의 관리 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/%EA%B3%A0%EA%B0%9D-%EB%AC%B8%EC%9D%98-%EB%8B%B5%EB%B3%80-%EB%93%B1%EB%A1%9D-%EC%88%98%EC%A0%95")
    
    def open_product_docs(self):
        """상품 관리 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/%EA%B7%B8%EB%A3%B9%EC%83%81%ED%92%88")
    
    def open_settlement_docs(self):
        """정산 관리 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/%EB%B6%80%EA%B0%80%EC%84%B8-%EB%82%B4%EC%97%AD")
    
    def open_order_docs(self):
        """주문 관리 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/%EA%B5%90%ED%99%98")
    
    def open_exchange_release_docs(self):
        """교환보류해제 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/seller-release-exchange-holdback-pay-order-seller")
    
    def open_exchange_reject_docs(self):
        """교환거부(철회) 문서 열기"""
        webbrowser.open("https://apicenter.commerce.naver.com/docs/commerce-api/current/seller-reject-exchange-pay-order-seller")
    
    def open_github_discussions(self):
        """GitHub 질문하기 페이지 열기"""
        webbrowser.open("https://github.com/commerce-api-naver/commerce-api/discussions")
    
    def open_smartstore_center(self):
        """스마트스토어 센터 열기"""
        webbrowser.open("https://sell.smartstore.naver.com/#/home/dashboard")
    
    
    def bind_mousewheel(self, canvas):
        """마우스 휠 스크롤 바인딩"""
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)