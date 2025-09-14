import requests
import json
from plyer import notification
from typing import Dict, List
import threading
import time
from datetime import datetime
import subprocess
import platform

class NotificationManager:
    def __init__(self, discord_webhook_url: str = None):
        self.discord_webhook_url = discord_webhook_url
        self.enabled_notifications = {
            'desktop': True,
            'discord': bool(discord_webhook_url)
        }
    
    def send_desktop_notification(self, title: str, message: str, timeout: int = 10):
        """데스크탑 푸시 알림 전송"""
        if not self.enabled_notifications['desktop']:
            return
        
        try:
            # macOS에서 osascript 사용
            if platform.system() == "Darwin":
                self._send_macos_notification(title, message)
            else:
                # 다른 OS에서는 plyer 사용
                notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout,
                    app_name="WithUs 주문관리"
                )
        except Exception as e:
            print(f"데스크탑 알림 전송 오류: {e}")
    
    def _send_macos_notification(self, title: str, message: str):
        """macOS 네이티브 알림 전송"""
        try:
            # osascript를 사용한 macOS 알림
            script = f'''
            display notification "{message}" with title "{title}" subtitle "WithUs 주문관리"
            '''
            
            subprocess.run(['osascript', '-e', script], 
                         check=True, 
                         capture_output=True, 
                         text=True)
            print(f"macOS 알림 전송 성공: {title}")
            
        except subprocess.CalledProcessError as e:
            print(f"macOS 알림 전송 실패: {e}")
            # fallback으로 plyer 시도
            try:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=10,
                    app_name="WithUs 주문관리"
                )
            except Exception as fallback_e:
                print(f"Fallback 알림도 실패: {fallback_e}")
        except Exception as e:
            print(f"macOS 알림 오류: {e}")
    
    def send_desktop_notification_with_sound(self, title: str, message: str, timeout: int = 10):
        """알림음이 포함된 데스크탑 알림 (신규주문용)"""
        if not self.enabled_notifications['desktop']:
            return
        
        try:
            # macOS에서 osascript 사용 (알림음 포함)
            if platform.system() == "Darwin":
                self._send_macos_notification_with_sound(title, message)
            else:
                # 다른 OS에서는 plyer 사용
                notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout,
                    app_name="WithUs 주문관리"
                )
        except Exception as e:
            print(f"데스크탑 알림 전송 오류: {e}")
    
    def _send_macos_notification_with_sound(self, title: str, message: str):
        """macOS 네이티브 알림 전송 (알림음 포함)"""
        try:
            # osascript를 사용한 macOS 알림 (알림음 포함)
            script = f'''
            display notification "{message}" with title "{title}" subtitle "WithUs 주문관리" sound name "Glass"
            '''
            
            subprocess.run(['osascript', '-e', script], 
                         check=True, 
                         capture_output=True, 
                         text=True)
            print(f"macOS 알림 전송 성공 (알림음 포함): {title}")
            
        except subprocess.CalledProcessError as e:
            print(f"macOS 알림 전송 실패: {e}")
            # fallback으로 일반 알림 시도
            try:
                self._send_macos_notification(title, message)
            except Exception as fallback_e:
                print(f"Fallback 알림도 실패: {fallback_e}")
        except Exception as e:
            print(f"macOS 알림 오류: {e}")
    
    def send_discord_notification(self, title: str, message: str, color: int = 0x00ff00):
        """디스코드 웹훅 알림 전송"""
        if not self.enabled_notifications['discord'] or not self.discord_webhook_url:
            return
        
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "WithUs 주문관리 시스템"
                }
            }
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(
                self.discord_webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 204:
                print(f"디스코드 알림 전송 실패: {response.status_code}")
                
        except Exception as e:
            print(f"디스코드 알림 전송 오류: {e}")
    
    def send_new_order_desktop_notification(self, order_data: Dict):
        """신규 주문 데스크탑 알림 (알림음 포함)"""
        title = "🛒 신규 주문 알림"
        message = f"주문번호: {order_data.get('order_id', 'N/A')}\n"
        message += f"고객명: {order_data.get('customer_name', 'N/A')}\n"
        message += f"상품명: {order_data.get('product_name', 'N/A')}\n"
        message += f"금액: {order_data.get('price', 0):,}원"

        # 데스크탑 알림 (알림음 포함)
        self.send_desktop_notification_with_sound(title, message)

    def send_new_order_discord_notification(self, order_data: Dict):
        """신규 주문 디스코드 알림"""
        title = "🛒 신규 주문 알림"

        discord_message = f"**새로운 주문이 접수되었습니다!**\n\n"
        discord_message += f"📋 주문번호: {order_data.get('order_id', 'N/A')}\n"
        discord_message += f"👤 고객명: {order_data.get('customer_name', 'N/A')}\n"
        discord_message += f"🛍️ 상품명: {order_data.get('product_name', 'N/A')}\n"
        discord_message += f"📦 수량: {order_data.get('quantity', 1)}개\n"
        discord_message += f"💰 금액: {order_data.get('price', 0):,}원\n"
        discord_message += f"📅 주문일시: {order_data.get('order_date', 'N/A')}"

        self.send_discord_notification(title, discord_message, 0x00ff00)

    def send_new_order_notification(self, order_data: Dict):
        """신규 주문 알림 (데스크탑 + 디스코드)"""
        # 데스크탑 알림 전송
        if self.enabled_notifications['desktop']:
            self.send_new_order_desktop_notification(order_data)

        # 디스코드 알림 전송
        if self.enabled_notifications['discord']:
            self.send_new_order_discord_notification(order_data)
    
    def send_status_change_notification(self, order_id: str, old_status: str, new_status: str):
        """주문 상태 변경 알림"""
        title = "📋 주문 상태 변경"
        message = f"주문번호: {order_id}\n"
        message += f"상태 변경: {old_status} → {new_status}"
        
        self.send_desktop_notification(title, message)
        
        discord_message = f"**주문 상태가 변경되었습니다**\n\n"
        discord_message += f"📋 주문번호: {order_id}\n"
        discord_message += f"🔄 상태 변경: `{old_status}` → `{new_status}`"
        
        self.send_discord_notification(title, discord_message, 0xffa500)
    
    def send_order_status_notification(self, order_data: Dict):
        """주문 상태 변경 알림 (주문 데이터 포함)"""
        title = "📋 주문 상태 변경"
        order_id = order_data.get('order_id', 'N/A')
        old_status = order_data.get('old_status', 'N/A')
        new_status = order_data.get('new_status', order_data.get('status', 'N/A'))
        customer_name = order_data.get('customer_name', 'N/A')
        product_name = order_data.get('product_name', 'N/A')
        
        message = f"주문번호: {order_id}\n"
        message += f"고객명: {customer_name}\n"
        message += f"상품명: {product_name}\n"
        message += f"상태 변경: {old_status} → {new_status}"
        
        self.send_desktop_notification(title, message)
        
        discord_message = f"**주문 상태가 변경되었습니다**\n\n"
        discord_message += f"📋 주문번호: {order_id}\n"
        discord_message += f"👤 고객명: {customer_name}\n"
        discord_message += f"🛍️ 상품명: {product_name}\n"
        discord_message += f"🔄 상태 변경: `{old_status}` → `{new_status}`"
        
        self.send_discord_notification(title, discord_message, 0xffa500)
    
    def send_delivery_complete_notification(self, order_data: Dict):
        """배송 완료 알림"""
        title = "🚚 배송 완료 알림"
        order_id = order_data.get('order_id', 'N/A')
        customer_name = order_data.get('customer_name', 'N/A')
        product_name = order_data.get('product_name', 'N/A')
        delivery_date = order_data.get('delivery_date', 'N/A')
        total_amount = order_data.get('total_amount', 0)
        
        message = f"주문번호: {order_id}\n"
        message += f"고객명: {customer_name}\n"
        message += f"상품명: {product_name}\n"
        message += f"배송완료일: {delivery_date}"
        
        self.send_desktop_notification(title, message)
        
        discord_message = f"**🚚 배송이 완료되었습니다!**\n\n"
        discord_message += f"📋 주문번호: {order_id}\n"
        discord_message += f"👤 고객명: {customer_name}\n"
        discord_message += f"🛍️ 상품명: {product_name}\n"
        discord_message += f"📦 수량: {order_data.get('quantity', 1)}개\n"
        discord_message += f"💰 금액: {total_amount:,}원\n"
        discord_message += f"📅 배송완료일: {delivery_date}"
        
        self.send_discord_notification(title, discord_message, 0x00ff00)
    
    def send_store_status_change_notification(self, status_changes: Dict):
        """스토어 상태변화 디스코드 알림 (대시보드 새로고침 시)"""
        if not self.enabled_notifications['discord'] or not self.discord_webhook_url:
            return
        
        if not status_changes:
            return
        
        title = "📊 스토어 상태변화 알림"
        
        discord_message = f"**스토어 상태가 변경되었습니다**\n\n"
        discord_message += f"🕐 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for status, count in status_changes.items():
            if count > 0:
                emoji_map = {
                    '신규주문': '🆕',
                    '발송대기': '📦',
                    '배송중': '🚚',
                    '배송완료': '✅',
                    '구매확정': '🎉',
                    '취소주문': '❌',
                    '반품주문': '🔄',
                    '교환주문': '🔄'
                }
                emoji = emoji_map.get(status, '📋')
                discord_message += f"{emoji} **{status}**: {count}건\n"
        
        self.send_discord_notification(title, discord_message, 0x0099ff)
    
    def send_urgent_inquiry_notification(self, inquiry_data: Dict):
        """긴급 문의 알림"""
        title = "🚨 긴급 문의 알림"
        message = f"고객명: {inquiry_data.get('customer_name', 'N/A')}\n"
        message += f"문의내용: {inquiry_data.get('content', 'N/A')[:50]}..."
        
        self.send_desktop_notification(title, message, timeout=15)
        
        discord_message = f"**🚨 긴급 문의가 접수되었습니다!**\n\n"
        discord_message += f"👤 고객명: {inquiry_data.get('customer_name', 'N/A')}\n"
        discord_message += f"📱 연락처: {inquiry_data.get('customer_phone', 'N/A')}\n"
        discord_message += f"📝 문의내용: {inquiry_data.get('content', 'N/A')}"
        
        self.send_discord_notification(title, discord_message, 0xff0000)
    
    def send_system_notification(self, title: str, message: str, notification_type: str = "info"):
        """시스템 알림"""
        colors = {
            "info": 0x0099ff,
            "success": 0x00ff00,
            "warning": 0xffa500,
            "error": 0xff0000
        }
        
        self.send_desktop_notification(title, message)
        self.send_discord_notification(title, message, colors.get(notification_type, 0x0099ff))
    
    def set_discord_webhook(self, webhook_url: str):
        """디스코드 웹훅 URL 설정"""
        self.discord_webhook_url = webhook_url
        self.enabled_notifications['discord'] = bool(webhook_url)
    
    def enable_notification(self, notification_type: str, enabled: bool):
        """알림 타입별 활성화/비활성화"""
        if notification_type in self.enabled_notifications:
            self.enabled_notifications[notification_type] = enabled
    
    def test_notifications(self):
        """알림 테스트"""
        test_data = {
            'order_id': 'TEST-001',
            'customer_name': '테스트 고객',
            'customer_phone': '010-1234-5678',
            'product_name': '테스트 상품',
            'quantity': 1,
            'price': 10000
        }
        
        self.send_new_order_notification(test_data)
        self.send_system_notification("테스트 알림", "알림 시스템이 정상적으로 작동합니다.", "success")


