"""
기본설정 탭 관련 UI 및 로직
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import re
import requests
import webbrowser

from ui_utils import BaseTab, enable_context_menu, run_in_thread
from env_config import config


class BasicSettingsTab(BaseTab):
    """기본설정 탭 클래스"""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.setup_styles()
        self.create_basic_settings_tab()
        self.setup_copy_paste_bindings()
        self.load_settings()
        self.refresh_current_ip()
    
    def setup_styles(self):
        """스타일 설정"""
        try:
            style = ttk.Style()
            
            # 섹션 라벨프레임 스타일
            style.configure("Section.TLabelframe", 
                          borderwidth=2, 
                          relief="solid",
                          background="#f0f0f0")
            style.configure("Section.TLabelframe.Label", 
                          font=("", 10, "bold"),
                          foreground="#2c3e50")
                          
        except Exception as e:
            print(f"스타일 설정 오류: {e}")
    
    def add_separator(self):
        """구분선 추가"""
        separator_frame = ttk.Frame(self.scrollable_frame, height=1)
        separator_frame.pack(fill="x", padx=15, pady=10)
        
        separator = ttk.Separator(separator_frame, orient="horizontal")
        separator.pack(fill="x")
    
    def setup_scrollable_frame(self):
        """스크롤 가능한 프레임 설정"""
        # 캔버스와 스크롤바 생성
        self.canvas = tk.Canvas(self.frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        
        # 스크롤 가능한 내용을 담을 프레임
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 스크롤 영역 설정
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # 캔버스에 프레임 추가
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 캔버스와 스크롤바 배치
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 마우스 휠 스크롤 지원
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind("<MouseWheel>", on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))  # Linux
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))   # Linux
        
        # 캔버스 크기 조정 시 스크롤 프레임 너비 맞추기
        def configure_scroll_region(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas.find_all()[0], width=canvas_width)
        
        self.canvas.bind("<Configure>", configure_scroll_region)
    
    def create_basic_settings_tab(self):
        """기본설정 탭 UI 생성"""
        # 스크롤 가능한 프레임 설정
        self.setup_scrollable_frame()
        
        # API 설정
        api_frame = ttk.LabelFrame(self.scrollable_frame, text="🔑 API 설정", style="Section.TLabelframe")
        api_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # Client ID
        client_id_frame = ttk.Frame(api_frame)
        client_id_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(client_id_frame, text="Client ID:").pack(side="left", padx=5)
        self.client_id_var = tk.StringVar()
        self.client_id_entry = ttk.Entry(client_id_frame, textvariable=self.client_id_var, width=50)
        self.client_id_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Client Secret
        client_secret_frame = ttk.Frame(api_frame)
        client_secret_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(client_secret_frame, text="Client Secret:").pack(side="left", padx=5)
        self.client_secret_var = tk.StringVar()
        self.client_secret_entry = ttk.Entry(client_secret_frame, textvariable=self.client_secret_var, width=50, show="*")
        self.client_secret_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # API 설정 버튼
        api_buttons_frame = ttk.Frame(api_frame)
        api_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(api_buttons_frame, text="API 설정 저장", command=self.save_api_settings).pack(side="left", padx=5)
        ttk.Button(api_buttons_frame, text="API 연결 테스트", command=self.test_api_connection).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # 알림 설정
        notification_frame = ttk.LabelFrame(self.scrollable_frame, text="🔔 알림 설정", style="Section.TLabelframe")
        notification_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 데스크탑 알림
        desktop_notification_frame = ttk.Frame(notification_frame)
        desktop_notification_frame.pack(fill="x", padx=5, pady=2)
        
        self.desktop_notifications_var = tk.BooleanVar()
        self.desktop_notifications_cb = ttk.Checkbutton(
            desktop_notification_frame, 
            text="데스크탑 알림 활성화", 
            variable=self.desktop_notifications_var
        )
        self.desktop_notifications_cb.pack(side="left", padx=5)
        
        # 디스코드 알림
        discord_frame = ttk.Frame(notification_frame)
        discord_frame.pack(fill="x", padx=5, pady=2)
        
        self.discord_enabled_var = tk.BooleanVar()
        self.discord_enabled_cb = ttk.Checkbutton(
            discord_frame, 
            text="디스코드 알림 활성화", 
            variable=self.discord_enabled_var
        )
        self.discord_enabled_cb.pack(side="left", padx=5)
        
        # 디스코드 웹훅 URL
        webhook_frame = ttk.Frame(notification_frame)
        webhook_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(webhook_frame, text="디스코드 웹훅 URL:").pack(side="left", padx=5)
        self.discord_webhook_var = tk.StringVar()
        self.discord_webhook_entry = ttk.Entry(webhook_frame, textvariable=self.discord_webhook_var, width=50)
        self.discord_webhook_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # 알림 설정 저장 버튼
        notification_buttons_frame = ttk.Frame(notification_frame)
        notification_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(notification_buttons_frame, text="알림 설정 저장", command=self.save_notification_settings).pack(side="left", padx=5)
        ttk.Button(notification_buttons_frame, text="알림 테스트", command=self.test_notifications).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # 홈탭 리프레시 설정
        refresh_frame = ttk.LabelFrame(self.scrollable_frame, text="⚡ 홈탭 리프레시 설정", style="Section.TLabelframe")
        refresh_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 자동 리프레시 활성화
        auto_refresh_frame = ttk.Frame(refresh_frame)
        auto_refresh_frame.pack(fill="x", padx=5, pady=2)
        
        self.auto_refresh_var = tk.BooleanVar()
        self.auto_refresh_cb = ttk.Checkbutton(
            auto_refresh_frame, 
            text="자동 리프레시 활성화", 
            variable=self.auto_refresh_var
        )
        self.auto_refresh_cb.pack(side="left", padx=5)
        
        # 리프레시 간격 설정
        interval_frame = ttk.Frame(refresh_frame)
        interval_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(interval_frame, text="리프레시 간격 (초):").pack(side="left", padx=5)
        self.refresh_interval_var = tk.StringVar()
        self.refresh_interval_entry = ttk.Entry(interval_frame, textvariable=self.refresh_interval_var, width=10)
        self.refresh_interval_entry.pack(side="left", padx=5)
        
        ttk.Label(interval_frame, text="권장: 60초 이상 (너무 짧으면 API 제한에 걸릴 수 있습니다)").pack(side="left", padx=10, anchor="w")
        
        # 리프레시 설정 저장 버튼
        refresh_buttons_frame = ttk.Frame(refresh_frame)
        refresh_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(refresh_buttons_frame, text="리프레시 설정 저장", command=self.save_refresh_settings).pack(side="left", padx=5)
        ttk.Button(refresh_buttons_frame, text="지금 새로고침", command=self.manual_refresh).pack(side="left", padx=5)
        
        # 구분선 추가
        self.add_separator()
        
        # IP 관리 설정
        ip_management_frame = ttk.LabelFrame(self.scrollable_frame, text="🌐 허가된 공인 IP 관리", style="Section.TLabelframe")
        ip_management_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 현재 IP 상태 (한 줄)
        current_ip_frame = ttk.Frame(ip_management_frame)
        current_ip_frame.pack(fill="x", padx=5, pady=3)
        
        ttk.Label(current_ip_frame, text="현재 공인 IP:").pack(side="left", padx=5)
        self.current_ip_var = tk.StringVar()
        self.current_ip_var.set("확인 중...")
        self.current_ip_label = ttk.Label(current_ip_frame, textvariable=self.current_ip_var, foreground="blue", font=("", 9, "bold"))
        self.current_ip_label.pack(side="left", padx=5)
        
        self.ip_status_var = tk.StringVar()
        self.ip_status_var.set("")
        self.ip_status_label = ttk.Label(current_ip_frame, textvariable=self.ip_status_var, font=("", 9, "bold"))
        self.ip_status_label.pack(side="left", padx=5)
        
        ttk.Button(current_ip_frame, text="새로고침", command=self.refresh_current_ip).pack(side="right", padx=2)
        
        # IP 목록과 관리 (좌우로 배치)
        ip_manage_frame = ttk.Frame(ip_management_frame)
        ip_manage_frame.pack(fill="x", padx=5, pady=3)
        
        # 허가된 IP 목록 (좌측, 폭 50%)
        ip_list_container = ttk.Frame(ip_manage_frame)
        ip_list_container.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ttk.Label(ip_list_container, text="허가된 IP 목록 (최대 5개):").pack(anchor="w")
        self.ip_listbox = tk.Listbox(ip_list_container, height=5, font=("Consolas", 9), width=25)
        self.ip_listbox.pack(anchor="w", pady=(2, 5))
        
        # IP 관리 컨트롤 (우측)
        ip_control_container = ttk.Frame(ip_manage_frame)
        ip_control_container.pack(side="right", padx=(10, 0))
        
        # IP 관리 컨트롤을 한 줄로 배치
        ip_control_frame = ttk.Frame(ip_control_container)
        ip_control_frame.pack(anchor="w", pady=2)
        
        # IP 입력
        self.new_ip_var = tk.StringVar()
        self.new_ip_entry = ttk.Entry(ip_control_frame, textvariable=self.new_ip_var, width=15)
        self.new_ip_entry.pack(side="left", padx=(0, 5))
        
        # 모든 버튼을 한 줄로
        ttk.Button(ip_control_frame, text="현재IP", command=self.add_current_ip).pack(side="left", padx=2)
        ttk.Button(ip_control_frame, text="추가", command=self.add_ip).pack(side="left", padx=2)
        ttk.Button(ip_control_frame, text="삭제", command=self.delete_selected_ip).pack(side="left", padx=2)
        ttk.Button(ip_control_frame, text="저장", command=self.save_ip_settings).pack(side="left", padx=2)
        
        # 도움말 버튼을 맨 아래로
        help_frame = ttk.Frame(ip_management_frame)
        help_frame.pack(fill="x", padx=5, pady=(5, 3))
        ttk.Button(help_frame, text="도움말", command=self.show_ip_help).pack(anchor="w")
        
        # 컨텍스트 메뉴 활성화
        enable_context_menu(self.client_id_entry)
        enable_context_menu(self.client_secret_entry)
        enable_context_menu(self.discord_webhook_entry)
        enable_context_menu(self.new_ip_entry)
    
    def load_settings(self):
        """설정 로드"""
        try:
            # API 설정 로드
            self.client_id_var.set(config.get('NAVER_CLIENT_ID', ''))
            self.client_secret_var.set(config.get('NAVER_CLIENT_SECRET', ''))
            
            # 알림 설정 로드
            self.desktop_notifications_var.set(config.get('DESKTOP_NOTIFICATIONS', 'false').lower() == 'true')
            self.discord_enabled_var.set(config.get('DISCORD_ENABLED', 'false').lower() == 'true')
            self.discord_webhook_var.set(config.get('DISCORD_WEBHOOK_URL', ''))
            
            # 리프레시 설정 로드
            self.auto_refresh_var.set(config.get('AUTO_REFRESH', 'false').lower() == 'true')
            self.refresh_interval_var.set(config.get('REFRESH_INTERVAL', '60'))
            
            # IP 설정 로드
            self.load_ip_settings()
            
        except Exception as e:
            print(f"기본설정 로드 오류: {e}")
    
    def save_api_settings(self):
        """API 설정 저장"""
        try:
            client_id = self.client_id_var.get().strip()
            client_secret = self.client_secret_var.get().strip()
            
            if not client_id or not client_secret:
                messagebox.showwarning("경고", "Client ID와 Client Secret을 모두 입력해주세요.")
                return
            
            # .env 파일에 저장
            config.set('NAVER_CLIENT_ID', client_id)
            config.set('NAVER_CLIENT_SECRET', client_secret)
            config.save()
            
            # API 재초기화
            self.app.initialize_api()
            
            messagebox.showinfo("성공", "API 설정이 저장되었습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"API 설정 저장 실패: {str(e)}")
    
    def test_api_connection(self):
        """API 연결 테스트"""
        try:
            if not self.app.naver_api:
                messagebox.showwarning("API 설정 필요", "네이버 커머스 API가 설정되지 않았습니다.\nAPI 정보를 입력해주세요.")
                return
            
            # API 연결 테스트
            response = self.app.naver_api.get_seller_account()
            
            if response and response.get('success'):
                messagebox.showinfo("성공", "API 연결 테스트 성공!")
            else:
                error_msg = response.get('error', '알 수 없는 오류') if response else '응답 없음'
                messagebox.showerror("실패", f"API 연결 테스트 실패: {error_msg}")
                
        except Exception as e:
            messagebox.showerror("오류", f"API 연결 테스트 실패: {str(e)}")
    
    def save_notification_settings(self):
        """알림 설정 저장"""
        try:
            desktop_enabled = self.desktop_notifications_var.get()
            discord_enabled = self.discord_enabled_var.get()
            webhook_url = self.discord_webhook_var.get().strip()
            
            # .env 파일에 저장
            config.set('DESKTOP_NOTIFICATIONS', str(desktop_enabled).lower())
            config.set('DISCORD_ENABLED', str(discord_enabled).lower())
            config.set('DISCORD_WEBHOOK_URL', webhook_url)
            config.save()
            
            # 알림 매니저 재초기화
            self.app.initialize_notifications()
            
            messagebox.showinfo("성공", "알림 설정이 저장되었습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"알림 설정 저장 실패: {str(e)}")
    
    def test_notifications(self):
        """알림 테스트"""
        try:
            # 테스트 주문 데이터
            test_order = {
                'order_id': 'TEST_ORDER_001',
                'customer_name': '테스트 고객',
                'product_name': '테스트 상품',
                'quantity': 1,
                'price': 10000,
                'order_date': '2024-01-01 12:00:00'
            }
            
            # 데스크탑 알림 테스트
            if self.desktop_notifications_var.get():
                self.app.notification_manager.show_desktop_notification("테스트 알림", "테스트 메시지입니다.")
            
            # Discord 알림 테스트
            if self.discord_enabled_var.get():
                self.app.notification_manager.send_new_order_notification(test_order)
            
            messagebox.showinfo("성공", "알림 테스트가 완료되었습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"알림 테스트 실패: {str(e)}")
    
    # IP 관리 메서드들
    def load_ip_settings(self):
        """IP 설정 로드"""
        try:
            # 기본 허가된 IP들
            default_ips = "121.190.40.153,175.125.204.97"
            saved_ips = config.get('ALLOWED_IPS', default_ips)
            
            # IP 목록 파싱
            ip_list = [ip.strip() for ip in saved_ips.split(',') if ip.strip()]
            
            # 리스트박스 업데이트
            self.ip_listbox.delete(0, tk.END)
            for ip in ip_list:
                self.ip_listbox.insert(tk.END, ip)
                
            print(f"IP 설정 로드: {ip_list}")
            
        except Exception as e:
            print(f"IP 설정 로드 오류: {e}")
            # 기본값으로 설정
            self.ip_listbox.delete(0, tk.END)
            self.ip_listbox.insert(tk.END, "121.190.40.153")
            self.ip_listbox.insert(tk.END, "175.125.204.97")
    
    def get_current_public_ip(self):
        """현재 공인 IP 주소 가져오기"""
        try:
            services = [
                "https://api.ipify.org",
                "https://ipinfo.io/ip", 
                "https://ident.me",
                "https://checkip.amazonaws.com"
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        public_ip = response.text.strip()
                        if public_ip and '.' in public_ip and re.match(r'^[\d.]+$', public_ip):
                            return public_ip
                except Exception as e:
                    print(f"{service} 서비스 오류: {e}")
                    continue
            
            return None
        except Exception as e:
            print(f"공인 IP 확인 오류: {e}")
            return None
    
    def is_ip_allowed(self, ip):
        """IP가 허가된 목록에 있는지 확인"""
        try:
            allowed_ips = []
            for i in range(self.ip_listbox.size()):
                allowed_ips.append(self.ip_listbox.get(i))
            return ip in allowed_ips
        except Exception as e:
            print(f"IP 허가 확인 오류: {e}")
            return False
    
    def refresh_current_ip(self):
        """현재 IP 새로고침"""
        run_in_thread(self._refresh_current_ip_thread)
    
    def _refresh_current_ip_thread(self):
        """현재 IP 새로고침 스레드"""
        try:
            self.app.root.after(0, lambda: self.current_ip_var.set("확인 중..."))
            self.app.root.after(0, lambda: self.ip_status_var.set(""))
            
            current_ip = self.get_current_public_ip()
            
            if current_ip:
                self.app.root.after(0, lambda: self.current_ip_var.set(current_ip))
                
                # IP 허가 상태 확인
                if self.is_ip_allowed(current_ip):
                    self.app.root.after(0, lambda: self.ip_status_var.set("✓ 허가됨"))
                    self.app.root.after(0, lambda: self.ip_status_label.config(foreground="green"))
                else:
                    self.app.root.after(0, lambda: self.ip_status_var.set("✗ 허가되지 않음"))
                    self.app.root.after(0, lambda: self.ip_status_label.config(foreground="red"))
                    # 허가되지 않은 IP일 때 도움말 자동 표시
                    self.app.root.after(1000, self.show_ip_authorization_warning)
            else:
                self.app.root.after(0, lambda: self.current_ip_var.set("확인 실패"))
                self.app.root.after(0, lambda: self.ip_status_var.set(""))
                
        except Exception as e:
            print(f"IP 새로고침 오류: {e}")
            self.app.root.after(0, lambda: self.current_ip_var.set("오류"))
            self.app.root.after(0, lambda: self.ip_status_var.set(""))
    
    def validate_ip_format(self, ip):
        """IP 주소 형식 검증"""
        try:
            pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            return bool(re.match(pattern, ip))
        except:
            return False
    
    def add_ip(self):
        """새 IP 추가 (최대 5개 제한)"""
        try:
            # 5개 제한 확인
            if self.ip_listbox.size() >= 5:
                messagebox.showwarning("제한", "최대 5개의 IP만 관리할 수 있습니다.")
                return
            
            new_ip = self.new_ip_var.get().strip()
            
            if not new_ip:
                messagebox.showwarning("경고", "IP 주소를 입력해주세요.")
                return
            
            if not self.validate_ip_format(new_ip):
                messagebox.showerror("오류", "올바른 IP 주소 형식이 아닙니다.")
                return
            
            # 중복 확인
            for i in range(self.ip_listbox.size()):
                if self.ip_listbox.get(i) == new_ip:
                    messagebox.showwarning("경고", "이미 추가된 IP 주소입니다.")
                    return
            
            # IP 추가
            self.ip_listbox.insert(tk.END, new_ip)
            self.new_ip_var.set("")
            
            print(f"IP 추가: {new_ip} (총 {self.ip_listbox.size()}개)")
            
        except Exception as e:
            messagebox.showerror("오류", f"IP 추가 실패: {str(e)}")
    
    def delete_selected_ip(self):
        """선택된 IP 삭제"""
        try:
            selection = self.ip_listbox.curselection()
            if not selection:
                messagebox.showwarning("경고", "삭제할 IP를 선택해주세요.")
                return
            
            selected_ip = self.ip_listbox.get(selection[0])
            
            # 확인 대화상자
            result = messagebox.askyesno("확인", f"IP '{selected_ip}'를 삭제하시겠습니까?")
            if result:
                self.ip_listbox.delete(selection[0])
                print(f"IP 삭제: {selected_ip}")
                
        except Exception as e:
            messagebox.showerror("오류", f"IP 삭제 실패: {str(e)}")
    
    def add_current_ip(self):
        """현재 IP를 허가 목록에 추가 (최대 5개 제한)"""
        try:
            # 5개 제한 확인
            if self.ip_listbox.size() >= 5:
                messagebox.showwarning("제한", "최대 5개의 IP만 관리할 수 있습니다.")
                return
            
            current_ip = self.current_ip_var.get()
            
            if current_ip in ["확인 중...", "확인 실패", "오류"]:
                messagebox.showwarning("경고", "현재 IP를 먼저 확인해주세요.")
                return
            
            if not self.validate_ip_format(current_ip):
                messagebox.showerror("오류", "현재 IP 주소가 올바르지 않습니다.")
                return
            
            # 중복 확인
            for i in range(self.ip_listbox.size()):
                if self.ip_listbox.get(i) == current_ip:
                    messagebox.showinfo("정보", "현재 IP는 이미 허가 목록에 있습니다.")
                    return
            
            # IP 추가
            self.ip_listbox.insert(tk.END, current_ip)
            
            # 상태 업데이트
            self.ip_status_var.set("✓ 허가됨")
            self.ip_status_label.config(foreground="green")
            
            print(f"현재 IP 추가: {current_ip} (총 {self.ip_listbox.size()}개)")
            
        except Exception as e:
            messagebox.showerror("오류", f"현재 IP 추가 실패: {str(e)}")
    
    def save_ip_settings(self):
        """IP 설정 저장"""
        try:
            # 리스트박스에서 IP 목록 가져오기
            ip_list = []
            for i in range(self.ip_listbox.size()):
                ip_list.append(self.ip_listbox.get(i))
            
            if not ip_list:
                messagebox.showwarning("경고", "최소 하나의 IP 주소가 필요합니다.")
                return
            
            # 설정 저장
            ip_string = ','.join(ip_list)
            config.set('ALLOWED_IPS', ip_string)
            config.save()
            
            messagebox.showinfo("성공", f"IP 설정이 저장되었습니다.\n허가된 IP: {len(ip_list)}개")
            
            # 현재 IP 상태 다시 확인
            self.refresh_current_ip()
            
            print(f"IP 설정 저장: {ip_list}")
            
        except Exception as e:
            messagebox.showerror("오류", f"IP 설정 저장 실패: {str(e)}")
    
    def show_ip_help(self):
        """IP 관리 도움말 표시"""
        help_text = """
💡 허가된 공인 IP 관리 도움말

🔹 현재 공인 IP
  - 앱이 실행되는 환경의 공인 IP 주소입니다
  - "새로고침" 버튼으로 최신 정보를 확인할 수 있습니다

🔹 허가된 IP 목록 (최대 5개)
  - 네이버 커머스 API 사용이 허가된 IP 주소 목록입니다
  - 기본값: 121.190.40.153, 175.125.204.97

🔹 IP 추가/삭제
  - "추가": 입력창에 IP 주소를 입력하여 추가
  - "현재IP": 현재 공인 IP를 허가 목록에 추가
  - "삭제": 목록에서 선택한 IP 삭제

🔹 허가되지 않은 IP로 실행 시
  - 빨간색 "✗ 허가되지 않음" 표시
  - 네이버 커머스 API 관리 페이지에서 IP 추가 필요

📋 네이버 커머스 API 관리 페이지
  - URL: https://apicenter.commerce.naver.com/ko/member/application/manage/list
  - 이 페이지에서 동일한 IP를 허가해야 API 사용 가능

⚠️ 주의사항
  - IP 변경 후 "저장" 버튼을 눌러 저장하세요
  - 네이버 커머스 API에서도 동일한 IP를 허가해야 합니다
  - 최대 5개의 IP만 관리할 수 있습니다
        """
        
        messagebox.showinfo("IP 관리 도움말", help_text)
    
    def show_ip_authorization_warning(self):
        """허가되지 않은 IP 경고 및 도움말"""
        try:
            current_ip = self.current_ip_var.get()
            
            if current_ip in ["확인 중...", "확인 실패", "오류"]:
                return
                
            if not self.is_ip_allowed(current_ip):
                result = messagebox.askyesno(
                    "IP 허가 필요", 
                    f"현재 공인 IP ({current_ip})가 허가되지 않았습니다.\n\n"
                    "네이버 커머스 API를 사용하려면 IP 허가가 필요합니다.\n\n"
                    "1. 현재 IP를 허가 목록에 추가하거나\n"
                    "2. 네이버 커머스 API 관리 페이지에서 IP를 추가하세요.\n\n"
                    "네이버 커머스 API 관리 페이지를 열시겠습니까?"
                )
                
                if result:
                    webbrowser.open("https://apicenter.commerce.naver.com/ko/member/application/manage/list")
                    
        except Exception as e:
            print(f"IP 허가 경고 표시 오류: {e}")
    
    def save_refresh_settings(self):
        """리프레시 설정 저장"""
        try:
            auto_refresh = self.auto_refresh_var.get()
            interval_str = self.refresh_interval_var.get().strip()
            
            # 간격 유효성 검사
            try:
                interval = int(interval_str)
                if interval < 30:
                    messagebox.showwarning("설정 오류", "리프레시 간격은 30초 이상이어야 합니다.")
                    return
                elif interval > 3600:
                    messagebox.showwarning("설정 오류", "리프레시 간격은 3600초(1시간) 이하여야 합니다.")
                    return
            except ValueError:
                messagebox.showwarning("설정 오류", "리프레시 간격은 숫자로 입력해주세요.")
                return
            
            # 설정 저장
            config.set('AUTO_REFRESH', str(auto_refresh).lower())
            config.set('REFRESH_INTERVAL', str(interval))
            config.save()  # .env 파일에 저장
            
            # 설정이 저장되었음을 알림
            if auto_refresh:
                messagebox.showinfo("설정 저장", f"리프레시 설정이 저장되었습니다.\n자동 리프레시: 활성화\n간격: {interval}초\n\n변경사항은 애플리케이션 재시작 후 적용됩니다.")
            else:
                messagebox.showinfo("설정 저장", "리프레시 설정이 저장되었습니다.\n자동 리프레시: 비활성화\n\n변경사항은 애플리케이션 재시작 후 적용됩니다.")
            
            print(f"리프레시 설정 저장: AUTO_REFRESH={auto_refresh}, REFRESH_INTERVAL={interval}")
            
        except Exception as e:
            print(f"리프레시 설정 저장 오류: {e}")
            messagebox.showerror("저장 오류", f"리프레시 설정 저장 중 오류가 발생했습니다: {str(e)}")
    
    def manual_refresh(self):
        """수동으로 홈탭 대시보드 새로고침"""
        try:
            if hasattr(self.app, 'home_tab') and hasattr(self.app.home_tab, 'refresh_dashboard'):
                self.app.home_tab.refresh_dashboard()
                messagebox.showinfo("새로고침", "홈탭 대시보드 새로고침을 실행했습니다.")
            else:
                messagebox.showwarning("새로고침 오류", "홈탭 대시보드 새로고침 기능을 찾을 수 없습니다.")
        except Exception as e:
            print(f"수동 새로고침 오류: {e}")
            messagebox.showerror("새로고침 오류", f"수동 새로고침 중 오류가 발생했습니다: {str(e)}")