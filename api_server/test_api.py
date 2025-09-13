#!/usr/bin/env python3
"""
FastAPI 테스트 스크립트
"""
import requests
import json
import time
import subprocess
import sys
from pathlib import Path

def test_api():
    """API 기본 기능 테스트"""
    
    print("🚀 Starting FastAPI server...")
    
    # 서버 시작
    server_process = subprocess.Popen([
        sys.executable, "run_server.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # 서버가 시작될 때까지 대기
    time.sleep(5)
    
    base_url = "http://localhost:8000"
    
    try:
        # 1. 헬스 체크
        print("\n📊 Testing health endpoint...")
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # 2. 루트 엔드포인트
        print("\n🏠 Testing root endpoint...")
        response = requests.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # 3. 주문 목록 조회
        print("\n📦 Testing orders endpoint...")
        response = requests.get(f"{base_url}/api/v1/orders/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # 4. 대시보드 통계
        print("\n📈 Testing dashboard stats...")
        response = requests.get(f"{base_url}/api/v1/dashboard/stats")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        print("\n✅ All API tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to server")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # 서버 종료
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    test_api()