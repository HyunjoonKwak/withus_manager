"""
환경 변수 설정 관리 모듈
"""

import os
from typing import Optional

class EnvConfig:
    """환경 변수 설정 클래스"""
    
    def __init__(self):
        self.load_env_file()
    
    def load_env_file(self):
        """환경 변수 파일 로드"""
        env_file_path = '.env'
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
    
    def get(self, key: str, default: str = '') -> str:
        """환경 변수 값 가져오기"""
        return os.environ.get(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """불린 환경 변수 값 가져오기"""
        value = os.environ.get(key, '').lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """정수 환경 변수 값 가져오기"""
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            return default
    
    def set(self, key: str, value: str):
        """환경 변수 설정"""
        os.environ[key] = value
    
    def save(self):
        """환경 변수를 파일에 저장 (save_to_env_file의 별칭)"""
        self.save_to_env_file()
    
    def save_to_env_file(self):
        """환경 변수를 .env 파일에 저장"""
        env_vars = {
            'NAVER_CLIENT_ID': self.get('NAVER_CLIENT_ID'),
            'NAVER_CLIENT_SECRET': self.get('NAVER_CLIENT_SECRET'),
            'DATABASE_PATH': self.get('DATABASE_PATH', 'orders.db'),
            'DISCORD_WEBHOOK_URL': self.get('DISCORD_WEBHOOK_URL'),
            'DISCORD_ENABLED': str(self.get_bool('DISCORD_ENABLED')).lower(),
            'DESKTOP_NOTIFICATIONS': str(self.get_bool('DESKTOP_NOTIFICATIONS', True)).lower(),
            'CHECK_INTERVAL': str(self.get_int('CHECK_INTERVAL', 300)),
            'AUTO_REFRESH': str(self.get_bool('AUTO_REFRESH', True)).lower(),
            'REFRESH_INTERVAL': str(self.get_int('REFRESH_INTERVAL', 60)),
            'PRODUCT_STATUS_TYPES': self.get('PRODUCT_STATUS_TYPES', 'SALE,WAIT,OUTOFSTOCK,SUSPENSION,CLOSE,PROHIBITION'),
            'ORDER_COLUMNS': self.get('ORDER_COLUMNS', '주문ID,상품주문ID,주문자,상품명,옵션정보,판매자상품코드,수량,단가,할인금액,금액,결제방법,배송지주소,배송예정일,주문일시,상태'),
            'ALLOWED_IPS': self.get('ALLOWED_IPS', '121.190.40.153,175.125.204.97'),
            'QUICK_PERIOD_SETTING': str(self.get_int('QUICK_PERIOD_SETTING', 7))
        }
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# 네이버 API 설정\n")
            f.write(f"NAVER_CLIENT_ID={env_vars['NAVER_CLIENT_ID']}\n")
            f.write(f"NAVER_CLIENT_SECRET={env_vars['NAVER_CLIENT_SECRET']}\n")
            f.write("\n# 데이터베이스 설정\n")
            f.write(f"DATABASE_PATH={env_vars['DATABASE_PATH']}\n")
            f.write("\n# 디스코드 알림 설정\n")
            f.write(f"DISCORD_WEBHOOK_URL={env_vars['DISCORD_WEBHOOK_URL']}\n")
            f.write(f"DISCORD_ENABLED={env_vars['DISCORD_ENABLED']}\n")
            f.write("\n# 알림 설정\n")
            f.write(f"DESKTOP_NOTIFICATIONS={env_vars['DESKTOP_NOTIFICATIONS']}\n")
            f.write(f"CHECK_INTERVAL={env_vars['CHECK_INTERVAL']}\n")
            f.write("\n# 자동 새로고침 설정\n")
            f.write(f"AUTO_REFRESH={env_vars['AUTO_REFRESH']}\n")
            f.write(f"REFRESH_INTERVAL={env_vars['REFRESH_INTERVAL']}\n")
            f.write("\n# 상품상태 조회 설정\n")
            f.write(f"PRODUCT_STATUS_TYPES={env_vars['PRODUCT_STATUS_TYPES']}\n")
            f.write("\n# 주문 컬럼 설정\n")
            f.write(f"ORDER_COLUMNS={env_vars['ORDER_COLUMNS']}\n")
            f.write("\n# IP 관리 설정\n")
            f.write(f"ALLOWED_IPS={env_vars['ALLOWED_IPS']}\n")
            f.write("\n# 기간 설정\n")
            f.write(f"QUICK_PERIOD_SETTING={env_vars['QUICK_PERIOD_SETTING']}\n")

# 전역 설정 인스턴스
config = EnvConfig()
