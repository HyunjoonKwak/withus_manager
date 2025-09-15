"""
버전 정보 유틸리티 - Git 태그와 환경변수를 통한 동적 버전 관리
"""
import subprocess
import os
from typing import Tuple, Optional
from env_config import config

# 캐시 변수들
_cached_version_info: Optional[Tuple[str, str]] = None
_cached_git_version: Optional[str] = None
_cached_git_build_date: Optional[str] = None

def get_git_version() -> Optional[str]:
    """Git 태그에서 버전 정보를 가져옴 (캐싱 적용)"""
    global _cached_git_version
    if _cached_git_version is not None:
        return _cached_git_version

    try:
        # 현재 HEAD의 태그를 찾기
        result = subprocess.run(
            ['git', 'describe', '--tags', '--exact-match', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            # v1.0.0 -> 1.0.0 형태로 변환 (v 제거)
            _cached_git_version = tag.lstrip('v')
            return _cached_git_version

        # 정확한 태그가 없으면 가장 최근 태그와 커밋 정보
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            desc = result.stdout.strip()
            # v1.0.0-3-g1234567 같은 형태를 처리
            if '-' in desc:
                parts = desc.split('-')
                if len(parts) >= 3:
                    tag = parts[0].lstrip('v')
                    commits = parts[1]
                    _cached_git_version = f"{tag}+{commits}"
                    return _cached_git_version
            _cached_git_version = desc.lstrip('v')
            return _cached_git_version

    except (subprocess.CalledProcessError, FileNotFoundError, Exception):
        pass

    return None

def get_git_build_date() -> Optional[str]:
    """Git에서 현재 커밋의 날짜를 가져옴 (캐싱 적용)"""
    global _cached_git_build_date
    if _cached_git_build_date is not None:
        return _cached_git_build_date
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%cd', '--date=short'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            _cached_git_build_date = result.stdout.strip()
            return _cached_git_build_date
    except (subprocess.CalledProcessError, FileNotFoundError, Exception):
        pass

    _cached_git_build_date = None
    return None

def get_app_version_info() -> Tuple[str, str]:
    """
    애플리케이션 버전과 빌드 날짜를 반환 (캐싱 적용)
    우선순위: Git 태그 > 환경변수 > 기본값
    """
    global _cached_version_info
    if _cached_version_info is not None:
        return _cached_version_info

    # Git에서 버전 정보 시도
    git_version = get_git_version()
    git_build_date = get_git_build_date()

    # 버전 결정
    if git_version:
        version = git_version
        print(f"Git 태그에서 버전 읽기: {version}")
    else:
        version = config.get('APP_VERSION', '1.0.0')
        print(f"환경변수에서 버전 읽기: {version}")

    # 빌드 날짜 결정
    if git_build_date:
        build_date = git_build_date
        print(f"Git에서 빌드 날짜 읽기: {build_date}")
    else:
        build_date = config.get('APP_BUILD_DATE', '2025-09-14')
        print(f"환경변수에서 빌드 날짜 읽기: {build_date}")

    _cached_version_info = (version, build_date)
    return _cached_version_info

def get_version_string() -> str:
    """표시용 버전 문자열 반환 (v1.0.0 형태)"""
    version, _ = get_app_version_info()
    return f"v{version}"

def get_full_title() -> str:
    """애플리케이션 전체 타이틀 반환"""
    version, build_date = get_app_version_info()
    return f"쇼핑몰 주문관리시스템 (v{version})"

def get_detailed_version_info() -> str:
    """상세 버전 정보 반환"""
    version, build_date = get_app_version_info()
    return f"쇼핑몰 주문관리시스템 v{version} - 빌드: {build_date}"

if __name__ == "__main__":
    # 테스트용
    print("=== 버전 정보 테스트 ===")
    print(f"Git 버전: {get_git_version()}")
    print(f"Git 빌드 날짜: {get_git_build_date()}")
    version, build_date = get_app_version_info()
    print(f"최종 버전: {version}")
    print(f"최종 빌드 날짜: {build_date}")
    print(f"버전 문자열: {get_version_string()}")
    print(f"전체 타이틀: {get_full_title()}")
    print(f"상세 정보: {get_detailed_version_info()}")