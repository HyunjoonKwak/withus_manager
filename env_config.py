"""
환경 변수 설정 관리 모듈
"""

import os
from typing import Optional

class EnvConfig:
    """환경 변수 설정 클래스 - 성능 최적화된 캐싱 버전"""

    def __init__(self):
        self._cache = {}  # 설정값 캐시
        self._file_mtime = 0  # 파일 수정 시간 캐시
        self._loaded = False
        self.load_env_file()

    def load_env_file(self):
        """환경 변수 파일 로드 - 파일 변경 시에만 다시 로드"""
        env_file_path = '.env'

        try:
            if os.path.exists(env_file_path):
                current_mtime = os.path.getmtime(env_file_path)

                # 파일이 변경되지 않았으면 캐시 사용
                if self._loaded and current_mtime == self._file_mtime:
                    return

                # 파일 읽기 및 캐싱
                self._cache.clear()
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            self._cache[key] = value
                            os.environ[key] = value

                self._file_mtime = current_mtime
                self._loaded = True
                # 초기 로드 시에만 로그 출력
                if not hasattr(self, '_initial_loaded'):
                    print(f"env 파일 로드 완료: {len(self._cache)}개 설정")
                    self._initial_loaded = True

        except Exception as e:
            print(f"env 파일 로드 오류: {e}")
            self._loaded = True  # 오류가 있어도 다시 시도하지 않음

    def reload(self):
        """강제로 환경 변수 파일 다시 로드"""
        self._loaded = False
        self._file_mtime = 0
        self.load_env_file()
    
    def get(self, key: str, default: str = '') -> str:
        """환경 변수 값 가져오기 - 캐시 우선 사용"""
        # 캐시에서 먼저 찾기
        if key in self._cache:
            return self._cache[key]
        # os.environ에서 찾기
        return os.environ.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """불린 환경 변수 값 가져오기 - 캐시 우선 사용"""
        value = self.get(key, '').lower()
        return value in ('true', '1', 'yes', 'on')

    def get_int(self, key: str, default: int = 0) -> int:
        """정수 환경 변수 값 가져오기 - 캐시 우선 사용"""
        try:
            return int(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def set(self, key: str, value: str):
        """환경 변수 설정 - 캐시도 함께 업데이트"""
        os.environ[key] = value
        self._cache[key] = value
    
    def save(self):
        """환경 변수를 파일에 저장 (save_to_env_file의 별칭)"""
        self.save_to_env_file()
    
    def save_to_env_file(self):
        """환경 변수를 .env 파일에 저장"""
        env_vars = {
            'APP_VERSION': self.get('APP_VERSION', '1.0.0'),
            'APP_BUILD_DATE': self.get('APP_BUILD_DATE', '2025-09-14'),
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
            'QUICK_PERIOD_SETTING': str(self.get_int('QUICK_PERIOD_SETTING', 7)),
            'ORDER_STATUS_TYPES': self.get('ORDER_STATUS_TYPES', 'PAYMENT_WAITING,PAYED,DELIVERING,DELIVERED,PURCHASE_DECIDED,EXCHANGED,CANCELED,RETURNED,CANCELED_BY_NOPAYMENT'),
            'DASHBOARD_PERIOD_DAYS': str(self.get_int('DASHBOARD_PERIOD_DAYS', 1)),
            'NEW_ORDER_DEFAULT_DAYS': str(self.get_int('NEW_ORDER_DEFAULT_DAYS', 7)),
            'SHIPPING_PENDING_DEFAULT_DAYS': str(self.get_int('SHIPPING_PENDING_DEFAULT_DAYS', 7)),
            'SHIPPING_IN_PROGRESS_DEFAULT_DAYS': str(self.get_int('SHIPPING_IN_PROGRESS_DEFAULT_DAYS', 7)),
            'SHIPPING_COMPLETED_DEFAULT_DAYS': str(self.get_int('SHIPPING_COMPLETED_DEFAULT_DAYS', 7)),
            'PURCHASE_DECIDED_DEFAULT_DAYS': str(self.get_int('PURCHASE_DECIDED_DEFAULT_DAYS', 30)),
            'CANCEL_DEFAULT_DAYS': str(self.get_int('CANCEL_DEFAULT_DAYS', 30)),
            'RETURN_EXCHANGE_DEFAULT_DAYS': str(self.get_int('RETURN_EXCHANGE_DEFAULT_DAYS', 30)),
            'CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS': str(self.get_int('CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS', 30))
        }
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# 애플리케이션 버전 정보\n")
            f.write(f"APP_VERSION={env_vars['APP_VERSION']}\n")
            f.write(f"APP_BUILD_DATE={env_vars['APP_BUILD_DATE']}\n")
            f.write("\n# 네이버 API 설정\n")
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
            f.write("\n# 주문 상태 조회 설정\n")
            f.write(f"ORDER_STATUS_TYPES={env_vars['ORDER_STATUS_TYPES']}\n")
            f.write("\n# 대시보드 설정\n")
            f.write(f"DASHBOARD_PERIOD_DAYS={env_vars['DASHBOARD_PERIOD_DAYS']}\n")
            f.write("\n# 신규 탭 기본 기간 설정\n")
            f.write(f"NEW_ORDER_DEFAULT_DAYS={env_vars['NEW_ORDER_DEFAULT_DAYS']}\n")
            f.write(f"SHIPPING_PENDING_DEFAULT_DAYS={env_vars['SHIPPING_PENDING_DEFAULT_DAYS']}\n")
            f.write(f"SHIPPING_IN_PROGRESS_DEFAULT_DAYS={env_vars['SHIPPING_IN_PROGRESS_DEFAULT_DAYS']}\n")
            f.write(f"SHIPPING_COMPLETED_DEFAULT_DAYS={env_vars['SHIPPING_COMPLETED_DEFAULT_DAYS']}\n")
            f.write(f"PURCHASE_DECIDED_DEFAULT_DAYS={env_vars['PURCHASE_DECIDED_DEFAULT_DAYS']}\n")
            f.write(f"CANCEL_DEFAULT_DAYS={env_vars['CANCEL_DEFAULT_DAYS']}\n")
            f.write(f"RETURN_EXCHANGE_DEFAULT_DAYS={env_vars['RETURN_EXCHANGE_DEFAULT_DAYS']}\n")
            f.write(f"CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS={env_vars['CANCEL_RETURN_EXCHANGE_DEFAULT_DAYS']}\n")

# 전역 설정 인스턴스 (지연 로딩)
_global_config = None

def get_config():
    """전역 설정 인스턴스 반환 (싱글톤 패턴)"""
    global _global_config
    if _global_config is None:
        _global_config = EnvConfig()
    return _global_config

# 프록시 클래스를 통한 지연 로딩 (싱글톤 최적화)
class _ConfigProxy:
    def __init__(self):
        self._config_instance = None

    def _get_config_cached(self):
        """캐시된 설정 인스턴스 반환"""
        if self._config_instance is None:
            self._config_instance = get_config()
        return self._config_instance

    def __getattr__(self, name):
        return getattr(self._get_config_cached(), name)

    def __call__(self, *args, **kwargs):
        return self._get_config_cached()(*args, **kwargs)

# 하위 호환성을 위한 프록시
config = _ConfigProxy()
