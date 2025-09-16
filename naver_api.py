import requests
import json
import hashlib
import hmac
import time
import base64
import bcrypt
import pybase64
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import configparser

class NaverShoppingAPI:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.commerce.naver.com"
        self.access_token = None
        
    def get_access_token(self) -> bool:
        """네이버 쇼핑 API 액세스 토큰 발급"""
        try:
            # 타임스탬프 생성 (현재 시간, 밀리초 단위)
            timestamp = int(time.time() * 1000)

            # 밑줄로 연결하여 password 생성
            password = self.client_id + "_" + str(timestamp)

            print(f"[DEBUG] 토큰 발급 시도 - client_id: {self.client_id}, timestamp: {timestamp}")
            print(f"[DEBUG] password: {password}")
            print(f"[DEBUG] client_secret: {self.client_secret}")

            try:
                # bcrypt salt 검증
                print(f"[DEBUG] bcrypt salt 검증 시작...")
                if not self.client_secret.startswith(('$2a$', '$2b$', '$2y$')):
                    print(f"[DEBUG] 경고: 클라이언트 시크릿이 bcrypt 형식이 아닙니다")

                # 테스트용 간단한 bcrypt 검증
                test_password = "test"
                try:
                    test_hashed = bcrypt.hashpw(test_password.encode('utf-8'), self.client_secret.encode('utf-8'))
                    print(f"[DEBUG] bcrypt salt 검증 성공 - salt가 유효함")
                except Exception as test_e:
                    print(f"[DEBUG] bcrypt salt 검증 실패: {test_e}")
                    return False

                # 실제 bcrypt 해싱 (사용자 제공 방식과 동일)
                hashed = bcrypt.hashpw(password.encode('utf-8'), self.client_secret.encode('utf-8'))
                # base64 인코딩
                client_secret_sign = pybase64.standard_b64encode(hashed).decode('utf-8')
                print(f"[DEBUG] bcrypt 해싱 성공")

            except Exception as e:
                print(f"[DEBUG] bcrypt 해싱 실패: {e}")
                print(f"[DEBUG] 클라이언트 시크릿 길이: {len(self.client_secret)}")
                print(f"[DEBUG] 클라이언트 시크릿 형식: {self.client_secret}")
                print(f"[DEBUG] password 길이: {len(password)}")
                return False

            # 인증
            url = "https://api.commerce.naver.com/external/v1/oauth2/token"

            data = {
                "client_id": str(self.client_id),
                "timestamp": timestamp,
                "client_secret_sign": str(client_secret_sign),
                "grant_type": "client_credentials ",  # 예제와 동일하게 공백 포함
                "type": "SELF"
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }

            print(f"[DEBUG] 토큰 발급 요청 전송")
            print(f"[DEBUG] URL: {url}")
            print(f"[DEBUG] Headers: {headers}")
            print(f"[DEBUG] Data: {data}")
            print(f"[DEBUG] client_secret_sign 길이: {len(client_secret_sign)}")

            response = requests.post(url, data=data, headers=headers, timeout=30)

            print(f"[DEBUG] 응답 상태코드: {response.status_code}")
            print(f"[DEBUG] 응답 헤더: {response.headers}")
            print(f"[DEBUG] 응답 내용: {response.text}")
            
            if response.status_code == 200:
                # 예제와 동일한 방식으로 JSON 파싱
                json_data = json.loads(response.text)
                self.access_token = json_data.get('access_token')
                print(f"[DEBUG] 토큰 발급 성공: {self.access_token[:10]}..." if self.access_token else "[DEBUG] access_token 없음")
                return True
            else:
                error_detail = response.text
                print(f"토큰 발급 실패: {response.status_code} - {error_detail}")
                
                # 오류 상세 정보 파싱
                try:
                    error_data = response.json()
                    if 'invalidInputs' in error_data:
                        for invalid_input in error_data['invalidInputs']:
                            print(f"오류 상세: {invalid_input.get('message', '알 수 없는 오류')}")
                except:
                    pass
                
                return False
                
        except Exception as e:
            print(f"토큰 발급 오류: {e}")
            return False
    
    def _generate_terminal_log(self, request_info: Dict, response_info: Dict, response_data: any) -> str:
        """터미널 로그 형식으로 요청/응답 정보 생성"""
        log_lines = []
        
        # 요청 정보
        log_lines.append("=== API 요청 상세 정보 ===")
        log_lines.append(f"메서드: {request_info['method']}")
        log_lines.append(f"URL: {request_info['url']}")
        log_lines.append(f"엔드포인트: {request_info['endpoint']}")
        if request_info.get('data'):
            log_lines.append(f"요청 데이터: {json.dumps(request_info['data'], indent=2, ensure_ascii=False) if isinstance(request_info['data'], dict) else str(request_info['data'])}")
        log_lines.append("========================")
        
        if request_info['method'].upper() == 'GET' and request_info.get('data'):
            log_lines.append(f"GET 요청 URL: {request_info['url']}?{request_info.get('params', '')}")
            log_lines.append(f"GET 요청 파라미터: {request_info['data']}")
        
        # 응답 정보 (응답 헤더 제거)
        log_lines.append("")
        log_lines.append("=== API 응답 상세 정보 ===")
        log_lines.append(f"응답 시간: {response_info['response_time']}")
        log_lines.append(f"상태 코드: {response_info['status_code']}")
        log_lines.append("=========================")
        
        # 응답 데이터 (timestamp, traceId 제거)
        if isinstance(response_data, dict):
            # timestamp, traceId 제거하고 data만 표시
            filtered_data = {k: v for k, v in response_data.items() if k not in ['timestamp', 'traceId']}
            log_lines.append(f"{json.dumps(filtered_data, indent=2, ensure_ascii=False)}")
        else:
            log_lines.append(f"{json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        return "\n".join(log_lines)
    
    def make_authenticated_request(self, method: str, endpoint: str, data: Dict = None, log_details: bool = True) -> Dict:
        """인증된 API 요청 - 상세 응답 정보 반환"""
        start_time = time.time()
        
        if not self.access_token:
            if not self.get_access_token():
                return {
                    'success': False,
                    'status_code': 401,
                    'message': '토큰 발급 실패',
                    'data': None,
                    'error': 'Access token not available',
                    'request_details': {
                        'method': method,
                        'endpoint': endpoint,
                        'data': data,
                        'timestamp': datetime.now().isoformat()
                    },
                    'terminal_log': f"토큰 발급 실패 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json;charset=UTF-8',
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret
        }
        
        # 요청 정보 상세 로깅
        request_info = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'url': url,
            'endpoint': endpoint,
            'headers': {k: v[:20] + '...' if k == 'Authorization' and len(str(v)) > 20 else v for k, v in headers.items()},
            'data': data,
            'data_size': len(str(data)) if data else 0
        }
        
        if log_details:
            print(f"🌐 API 호출: {method} {endpoint}")
        
        try:
            if method.upper() == 'GET':
                # 파라미터가 있는 경우 URL에 직접 추가
                if data:
                    param_string = '&'.join([f"{k}={v}" for k, v in data.items()])
                    url = f"{url}?{param_string}"
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            else:
                return {
                    'success': False,
                    'status_code': 400,
                    'message': '지원하지 않는 HTTP 메서드',
                    'data': None,
                    'error': f'Unsupported method: {method}'
                }
            
            # 요청 완료 시간 측정
            end_time = time.time()
            response_time = end_time - start_time
            
            # 응답 정보 상세 로깅
            response_info = {
                'timestamp': datetime.now().isoformat(),
                'status_code': response.status_code,
                'response_time': f"{response_time:.3f}s",
                'headers': dict(response.headers),
                'content_length': len(response.text) if hasattr(response, 'text') else 0
            }
            
            if log_details:
                status_icon = "✅" if response.status_code == 200 else "❌"
                print(f"   {status_icon} 응답: {response.status_code} ({response_info['response_time']})")
            
            # 응답 상태 코드에 따른 처리
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    # 터미널 로그 생성
                    terminal_log = self._generate_terminal_log(request_info, response_info, response_data)
                    
                    result = {
                        'success': True,
                        'status_code': response.status_code,
                        'message': '요청 성공',
                        'data': response_data,
                        'error': None,
                        'request_details': request_info,
                        'response_details': response_info,
                        'terminal_log': terminal_log
                    }
                    
                    # 별도 로그 출력 제거 (터미널 로그에 포함됨)
                    
                    return result
                except Exception as json_error:
                    terminal_log = self._generate_terminal_log(request_info, response_info, response.text)
                    result = {
                        'success': True,
                        'status_code': response.status_code,
                        'message': '요청 성공 (JSON 파싱 실패)',
                        'data': response.text,
                        'error': f'JSON 파싱 오류: {str(json_error)}',
                        'request_details': request_info,
                        'response_details': response_info,
                        'terminal_log': terminal_log
                    }
                    
                    if log_details:
                        print(f"JSON 파싱 실패: {str(json_error)}")
                        print(f"원본 응답 텍스트: {response.text[:200]}...")
                    
                    return result
            elif response.status_code == 401:
                # 토큰 만료 시 재발급
                if self.get_access_token():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    if method.upper() == 'GET':
                        # 파라미터가 있는 경우 URL에 직접 추가
                        if data:
                            param_string = '&'.join([f"{k}={v}" for k, v in data.items()])
                            url = f"{url}?{param_string}"
                        response = requests.get(url, headers=headers)
                    elif method.upper() == 'POST':
                        response = requests.post(url, headers=headers, json=data)
                    elif method.upper() == 'PUT':
                        response = requests.put(url, headers=headers, json=data)
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            # 재시도 응답 정보 업데이트
                            retry_response_info = response_info.copy()
                            retry_response_info.update({
                                'status_code': response.status_code,
                                'content_length': len(response.text) if hasattr(response, 'text') else 0
                            })
                            terminal_log = self._generate_terminal_log(request_info, retry_response_info, response_data)
                            return {
                                'success': True,
                                'status_code': response.status_code,
                                'message': '요청 성공 (토큰 재발급 후)',
                                'data': response_data,
                                'error': None,
                                'terminal_log': terminal_log
                            }
                        except:
                            return {
                                'success': True,
                                'status_code': response.status_code,
                                'message': '요청 성공 (토큰 재발급 후, JSON 파싱 실패)',
                                'data': response.text,
                                'error': None
                            }
                
                # 토큰 재발급 실패
                result = {
                    'success': False,
                    'status_code': 401,
                    'message': '인증 실패 (토큰 재발급 실패)',
                    'data': None,
                    'error': response.text,
                    'request_details': request_info,
                    'response_details': response_info
                }
                
                if log_details:
                    print(f"토큰 재발급 실패: {response.text}")
                
                return result
            else:
                # 기타 오류
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', '알 수 없는 오류')
                    if 'invalidInputs' in error_data:
                        invalid_inputs = error_data['invalidInputs']
                        error_details = []
                        for invalid_input in invalid_inputs:
                            field = invalid_input.get('field', '')
                            message = invalid_input.get('message', '')
                            error_details.append(f"{field}: {message}")
                        error_message += f" - {', '.join(error_details)}"
                    
                    if log_details:
                        print(f"API 오류 응답: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                        
                except Exception as parse_error:
                    error_message = response.text
                    if log_details:
                        print(f"오류 응답 파싱 실패: {str(parse_error)}")
                        print(f"원본 오류 응답: {response.text}")
                
                result = {
                    'success': False,
                    'status_code': response.status_code,
                    'message': f'요청 실패 ({response.status_code})',
                    'data': None,
                    'error': error_message,
                    'request_details': request_info,
                    'response_details': response_info
                }
                
                if log_details:
                    print(f"HTTP {response.status_code} 오류: {error_message}")
                
                return result
            
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            result = {
                'success': False,
                'status_code': 0,
                'message': '네트워크 오류',
                'data': None,
                'error': str(e),
                'request_details': request_info,
                'response_details': {
                    'timestamp': datetime.now().isoformat(),
                    'response_time': f"{response_time:.3f}s",
                    'error_type': type(e).__name__
                }
            }
            
            if log_details:
                print(f"\n=== API 요청 예외 발생 ===")
                print(f"예외 타입: {type(e).__name__}")
                print(f"예외 메시지: {str(e)}")
                print(f"요청 시간: {response_time:.3f}s")
                print(f"======================")
            
            return result
    
    
    def get_order_detail(self, order_id: str) -> Optional[Dict]:
        """주문 상세 조회"""
        response = self.make_authenticated_request('GET', f'/external/v1/pay-order/seller/product-orders/{order_id}')
        return response
    
    def get_last_changed_orders(self, last_changed_from: str, last_changed_to: str = None, last_changed_type: str = None) -> Dict:
        """변경된 주문 목록 조회 (last-changed-statuses)"""
        params = {
            'lastChangedFrom': last_changed_from
        }
        
        if last_changed_to:
            params['lastChangedTo'] = last_changed_to
        
        if last_changed_type:
            params['lastChangedType'] = last_changed_type
            
        response = self.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders/last-changed-statuses', params)
        return response
    
    def query_orders_by_ids(self, product_order_ids: list) -> Dict:
        """주문 ID 목록으로 상세 주문 정보 조회 (query)"""
        data = {
            'productOrderIds': product_order_ids
        }
        response = self.make_authenticated_request('POST', '/external/v1/pay-order/seller/product-orders/query', data)
        return response
    
    def get_changed_orders_with_chunking(self, start_time: str, end_time: str, last_changed_type: str = 'PAYED') -> Dict:
        """24시간 단위로 나누어 변경된 주문 조회"""
        from datetime import datetime, timezone, timedelta
        import time
        
        # 한국 시간대 설정 (UTC+9)
        kst = timezone(timedelta(hours=9))
        
        # 시간 문자열을 datetime 객체로 변환
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(kst)
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')).astimezone(kst)
        
        all_orders = []
        total_chunks = 0
        
        print(f"24시간 단위 청크 조회 시작:")
        print(f"  → 시작 시간: {start_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00")
        print(f"  → 종료 시간: {end_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00")
        
        # 24시간 단위로 쪼개서 조회
        current_start = start_dt
        while current_start < end_dt:
            # 24시간 후 또는 종료일 중 더 이른 시간
            current_end = min(current_start + timedelta(hours=24), end_dt)
            
            total_chunks += 1
            print(f"청크 {total_chunks}: {current_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00 ~ {current_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}+09:00")
            
            # ISO 형식으로 변환
            chunk_start = current_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            chunk_end = current_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
            # 해당 청크의 변경된 주문 조회
            print(f"  → 청크 {total_chunks} API 요청:")
            print(f"    - URL: {self.base_url}/external/v1/pay-order/seller/product-orders/last-changed-statuses")
            print(f"    - lastChangedFrom: {chunk_start}")
            print(f"    - lastChangedTo: {chunk_end}")
            print(f"    - lastChangedType: {last_changed_type}")
            
            response = self.get_last_changed_orders(
                last_changed_from=chunk_start,
                last_changed_to=chunk_end,
                last_changed_type=last_changed_type
            )
            
            if response and response.get('success'):
                data = response.get('data', {})
                if 'lastChangeStatuses' in data:
                    chunk_orders = data['lastChangeStatuses']
                    all_orders.extend(chunk_orders)
                    print(f"  → {len(chunk_orders)}건 조회 성공")
                else:
                    print(f"  → 0건 조회")
            else:
                print(f"  → 조회 실패: {response.get('error', '알 수 없는 오류') if response else '응답 없음'}")
            
            # 0.5초 딜레이 (참조 코드와 동일)
            time.sleep(0.5)
            
            # 다음 청크로 이동
            current_start = current_end
        
        print(f"전체 청크 조회 완료: {total_chunks}개 청크, 총 {len(all_orders)}건")
        
        return {
            'success': True,
            'data': {
                'count': len(all_orders),
                'lastChangeStatuses': all_orders,
                'chunks_processed': total_chunks
            }
        }
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """주문 상태 업데이트"""
        data = {
            'status': status
        }
        
        response = self.make_authenticated_request('PUT', f'/external/v1/pay-order/seller/product-orders/{order_id}/status', data)
        return response is not None
    
    def get_products(self, limit: int = 100, product_status_types: list = None) -> Dict:
        """상품 목록 조회 - 상세 응답 정보 반환"""
        if product_status_types is None:
            product_status_types = ["SALE", "WAIT", "OUTOFSTOCK", "SUSPENSION", "CLOSE", "PROHIBITION"]
        
        data = {
            "productStatusTypes": product_status_types,
            "page": 1,
            "size": min(limit, 50),  # 최대 50개로 제한
            "orderType": "NO",
            "periodType": "PROD_REG_DAY",
            "fromDate": "",
            "toDate": ""
        }
        return self.make_authenticated_request('POST', '/external/v1/products/search', data)
    
    def get_channel_product(self, channel_product_id: str) -> Dict:
        """채널상품 상세 조회 - 상세 응답 정보 반환"""
        return self.make_authenticated_request('GET', f'/external/v2/products/channel-products/{channel_product_id}')
    
    def get_orders(self, start_date: str = None, end_date: str = None, order_status: str = None, limit: int = 50) -> Dict:
        """주문 목록 조회 - 24시간 단위로 쪼개서 조회"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 한국 시간(KST) 기준으로 계산 (UTC+9)
        from datetime import timezone, timedelta
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        current_time = now_kst.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # 시작일과 종료일을 현재 시간 기준으로 계산 (KST 기준)
        if start_date == end_date:
            # 같은 날인 경우, 현재 시간에서 N일 전까지
            days_diff = (now_kst.date() - datetime.strptime(start_date, '%Y-%m-%d').date()).days
            start_dt = now_kst - timedelta(days=days_diff)
            end_dt = now_kst
        else:
            # 다른 날인 경우, 시작일 현재시간에서 종료일 현재시간까지
            start_base = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=kst)
            end_base = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=kst)
            
            # 현재 시간을 기준으로 시작/종료 시간 설정
            start_dt = start_base.replace(hour=now_kst.hour, minute=now_kst.minute, second=now_kst.second)
            end_dt = end_base.replace(hour=now_kst.hour, minute=now_kst.minute, second=now_kst.second)
            
            # 종료일이 현재 시간보다 미래인 경우 현재 시간으로 제한
            if end_dt > now_kst:
                end_dt = now_kst
        
        all_orders = []
        chunk_count = 0
        
        # 24시간 단위로 쪼개서 조회
        current_start = start_dt
        while current_start < end_dt:
            # 24시간 후 또는 종료일 중 더 이른 시간
            current_end = min(current_start + timedelta(hours=24), end_dt)
            
            chunk_count += 1
            print(f"청크 {chunk_count}: {current_start.strftime('%m-%d %H:%M')} ~ {current_end.strftime('%m-%d %H:%M')}")
            
            params = {
                'from': current_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                'to': current_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                'page': 1,
                'size': min(limit, 100)
            }
            
            if order_status:
                # 여러 상태가 전달된 경우 처리
                if isinstance(order_status, list):
                    # 리스트인 경우 콤마로 연결하여 다중 상태 조회 시도
                    params['orderStatusType'] = ','.join(order_status)
                    print(f"다중 상태 조회 시도: {params['orderStatusType']}")
                else:
                    params['orderStatusType'] = order_status
            
            # 재시도 로직 (최대 3회)
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    response = self.make_authenticated_request('GET', '/external/v1/pay-order/seller/product-orders', params, log_details=False)
                    
                    if response and response.get('success'):
                        # make_authenticated_request가 반환하는 응답 구조: {'success': True, 'data': {...}}
                        # 여기서 data는 네이버 API의 전체 응답이고, 실제 주문 데이터는 data['data']['contents']에 있음
                        api_response = response.get('data', {})
                        data = api_response.get('data', {})
                        
                        if 'contents' in data:
                            orders = data['contents']
                            all_orders.extend(orders)
                            print(f"  → {len(orders)}건 조회")
                        else:
                            print(f"  → 0건 조회")
                        success = True
                    else:
                        error_msg = response.get('error', '알 수 없는 오류') if response else '응답 없음'
                        
                        # 요청 제한 오류인 경우 재시도
                        if '요청이 많아' in error_msg or '일시적으로' in error_msg:
                            retry_count += 1
                            if retry_count < max_retries:
                                wait_time = retry_count * 2  # 2초, 4초, 6초 대기
                                print(f"  → 요청 제한 오류, {wait_time}초 후 재시도 ({retry_count}/{max_retries})")
                                time.sleep(wait_time)
                                continue
                        
                        print(f"  → 조회 실패: {error_msg}")
                        success = True  # 재시도하지 않고 다음 청크로
                        
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = retry_count * 2
                        print(f"  → 조회 오류, {wait_time}초 후 재시도 ({retry_count}/{max_retries}): {e}")
                        time.sleep(wait_time)
                    else:
                        print(f"  → 조회 오류 (최대 재시도 초과): {e}")
                        success = True  # 재시도하지 않고 다음 청크로
            
            # 다음 청크로 이동
            current_start = current_end
            
            # API 호출 제한을 고려한 대기 (요청 제한 오류 방지)
            import time
            time.sleep(1.0)  # 1초 대기로 증가
        
        print(f"전체 조회 완료: {chunk_count}개 청크, 총 {len(all_orders)}건")
        
        # 결과를 원래 형식으로 반환
        return {
            'success': True,
            'data': {
                'data': all_orders,
                'total': len(all_orders)
            },
            'chunks_processed': chunk_count
        }
    
    def get_store_info(self) -> Dict:
        """스토어 정보 조회 - 상세 응답 정보 반환"""
        return self.make_authenticated_request('GET', '/external/v1/seller/account')
    
    def get_seller_channels(self) -> Dict:
        """판매자 채널 정보 조회 - 상세 응답 정보 반환"""
        return self.make_authenticated_request('GET', '/external/v1/seller/channels')
    
    def get_order_statistics(self, start_date: str = None, end_date: str = None) -> Dict:
        """주문 통계 조회 (최대 24시간 범위)"""
        if not start_date:
            start_date = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        params = {
            'from': start_date,
            'to': end_date
        }
        
        response = self.make_authenticated_request('GET', '/external/v1/statistics/orders', params)
        return response or {}
    
    def sync_orders_to_database(self, db_manager, start_date: str = None, end_date: str = None) -> int:
        """네이버 API에서 주문 데이터를 가져와 데이터베이스에 동기화"""
        response = self.get_orders(start_date, end_date)
        synced_count = 0

        # get_orders 응답에서 실제 주문 데이터 추출
        if response and response.get('success'):
            orders = response.get('data', {}).get('data', [])
        else:
            orders = []

        for order in orders:
            # 네이버 API 응답은 { productOrderId, content: { order: {...}, productOrder: {...} } } 구조
            content = order.get('content', {})
            order_info = content.get('order', {})
            product_info = content.get('productOrder', {})

            order_data = {
                'order_id': order_info.get('orderId'),  # content.order.orderId
                'order_date': order_info.get('orderDate'),  # content.order.orderDate
                'customer_name': order_info.get('ordererName'),  # content.order.ordererName
                'customer_phone': order_info.get('ordererTel'),  # content.order.ordererTel
                'product_name': product_info.get('productName'),  # content.productOrder.productName
                'quantity': product_info.get('quantity', 1),  # content.productOrder.quantity
                'price': product_info.get('totalPaymentAmount', 0),  # content.productOrder.totalPaymentAmount
                'status': self._map_naver_status_to_local(product_info.get('productOrderStatus')),  # content.productOrder.productOrderStatus
                'shipping_company': product_info.get('expectedDeliveryCompany'),  # content.productOrder.expectedDeliveryCompany
                'tracking_number': '',  # 추후 배송 조회 API에서 가져와야 함
                'memo': ''  # 기본값
            }

            if db_manager.add_order(order_data):
                synced_count += 1
        
        return synced_count

    def save_orders_to_database(self, db_manager, orders_data) -> int:
        """이미 조회된 주문 데이터를 데이터베이스에 저장 (중복 API 호출 방지)"""
        synced_count = 0

        # orders_data는 get_orders 응답에서 data.data 부분
        if not orders_data:
            return synced_count

        for order in orders_data:
            # 네이버 API 응답은 { productOrderId, content: { order: {...}, productOrder: {...} } } 구조
            content = order.get('content', {})
            order_info = content.get('order', {})
            product_info = content.get('productOrder', {})

            order_data = {
                'order_id': order_info.get('orderId'),  # content.order.orderId
                'order_date': order_info.get('orderDate'),  # content.order.orderDate
                'customer_name': order_info.get('ordererName'),  # content.order.ordererName
                'customer_phone': order_info.get('ordererTel'),  # content.order.ordererTel
                'product_name': product_info.get('productName'),  # content.productOrder.productName
                'quantity': product_info.get('quantity', 1),  # content.productOrder.quantity
                'price': product_info.get('totalPaymentAmount', 0),  # content.productOrder.totalPaymentAmount
                'status': self._map_naver_status_to_local(
                    product_info.get('productOrderStatus'),
                    product_info.get('placeOrderStatusType')
                ),  # 두 개 상태 필드 모두 사용
                'place_order_status': self._get_place_order_status(product_info),  # 발주확인 상태 저장
                'shipping_company': product_info.get('expectedDeliveryCompany'),  # content.productOrder.expectedDeliveryCompany
                'tracking_number': '',  # 추후 배송 조회 API에서 가져와야 함
                'memo': ''  # 기본값
            }

            print(f"📝 주문 저장 시도: ID={order_data.get('order_id')}, 상태={order_data.get('status')}, 날짜={order_data.get('order_date')}")
            print(f"   🔍 원본 상태: productOrderStatus={product_info.get('productOrderStatus')}, placeOrderStatusType={product_info.get('placeOrderStatusType')}")

            if db_manager.add_order(order_data):
                synced_count += 1
                print(f"✅ 주문 저장 성공: {order_data.get('order_id')}")
            else:
                print(f"❌ 주문 저장 실패: {order_data.get('order_id')}")

        return synced_count

    def _get_place_order_status(self, product_info: dict) -> str:
        """발주확인 상태를 결정하는 메서드"""
        place_order_status = product_info.get('placeOrderStatusType')
        product_order_status = product_info.get('productOrderStatus')

        # placeOrderStatusType이 None인 경우 주문 상태에 따라 기본값 설정
        if place_order_status is None:
            if product_order_status in ['PAYMENT_WAITING', 'PAYED']:
                return 'NOT_YET'  # 신규주문은 발주 미확인 상태
            else:
                return None  # 다른 상태들은 발주확인 불필요
        else:
            return place_order_status

    def _map_naver_status_to_local(self, naver_status: str, place_order_status: str = None) -> str:
        """네이버 API 상태를 로컬 상태로 매핑 (대시보드와 일관성 유지)"""
        # PAYED 상태의 경우 placeOrderStatusType에 따라 구분
        if naver_status == 'PAYED':
            if place_order_status == 'NOT_YET':
                return 'PAYMENT_WAITING'  # 신규주문 (결제완료, 발주미확인)
            elif place_order_status == 'OK':
                return 'PAYED'            # 발송대기 (결제완료, 발주확인)
            else:
                # placeOrderStatusType이 없거나 예상하지 못한 값인 경우 기본값
                return 'PAYMENT_WAITING'

        # 기타 상태들은 기존 매핑 유지
        status_mapping = {
            'ORDERED': 'PAYMENT_WAITING',      # 신규주문
            'READY': 'PAYED',                  # 발송대기
            'SHIPPED': 'DELIVERING',           # 배송중
            'DELIVERED': 'DELIVERED',          # 배송완료
            'CONFIRMED': 'PURCHASE_DECIDED',   # 구매확정
            'CANCELED': 'CANCELED',            # 취소주문
            'CANCELLED': 'CANCELED',           # 취소주문
            'RETURNED': 'RETURNED',            # 반품주문
            'EXCHANGED': 'EXCHANGED'           # 교환주문
        }
        return status_mapping.get(naver_status, 'PAYMENT_WAITING')
    
    # 주문관리 핵심 API 메서드들
    
    def get_product_detail(self, product_id: str) -> Dict:
        """상품 상세 조회"""
        return self.make_authenticated_request('GET', f'/external/v1/products/{product_id}')
    
    def get_origin_product(self, origin_product_id: str) -> Dict:
        """원상품 상세 조회"""
        return self.make_authenticated_request('GET', f'/external/v2/products/origin-products/{origin_product_id}')
    
    def get_order_product_ids(self, order_id: str) -> Dict:
        """주문 상품 ID 목록 조회"""
        return self.make_authenticated_request('GET', f'/external/v1/pay-order/seller/orders/{order_id}/product-order-ids')
    
    def update_shipping_info(self, product_order_id: str, delivery_company: str, tracking_number: str) -> Dict:
        """배송 정보 업데이트"""
        data = {
            'deliveryCompany': delivery_company,
            'trackingNumber': tracking_number
        }
        return self.make_authenticated_request('PUT', f'/external/v1/pay-order/seller/product-orders/{product_order_id}/shipping', data)
    
    def change_order_status(self, product_order_id: str, status: str, reason: str = None) -> Dict:
        """주문 상태 변경"""
        data = {
            'status': status
        }
        if reason:
            data['reason'] = reason
        return self.make_authenticated_request('PUT', f'/external/v1/pay-order/seller/product-orders/{product_order_id}/status', data)
    
    def get_delivery_companies(self) -> Dict:
        """배송업체 목록 조회"""
        return self.make_authenticated_request('GET', '/external/v1/pay-order/seller/delivery-companies')
    
    def bulk_update_shipping(self, shipping_updates: list) -> Dict:
        """배송 정보 일괄 업데이트"""
        data = {
            'shippingUpdates': shipping_updates
        }
        return self.make_authenticated_request('POST', '/external/v1/pay-order/seller/product-orders/bulk-shipping', data)
    
    def get_order_claims(self, start_date: str = None, end_date: str = None) -> Dict:
        """클레임(취소/반품/교환) 조회"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        params = {
            'from': start_date,
            'to': end_date
        }
        return self.make_authenticated_request('GET', '/external/v1/pay-order/seller/claims', params)
    
    def process_claim(self, claim_id: str, action: str, reason: str = None) -> Dict:
        """클레임 처리 (승인/거부)"""
        data = {
            'action': action  # 'APPROVE', 'REJECT'
        }
        if reason:
            data['reason'] = reason
        return self.make_authenticated_request('POST', f'/external/v1/pay-order/seller/claims/{claim_id}/process', data)
    
    def get_order_statistics_detailed(self, start_date: str = None, end_date: str = None) -> Dict:
        """상세 주문 통계 조회"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'startDate': start_date,
            'endDate': end_date
        }
        return self.make_authenticated_request('GET', '/external/v1/statistics/orders/detailed', params)
    
    def search_orders(self, search_params: Dict) -> Dict:
        """주문 검색 (고급 검색)"""
        return self.make_authenticated_request('POST', '/external/v1/pay-order/seller/product-orders/search', search_params)
    
    def get_order_detail(self, product_order_id: str) -> Dict:
        """주문 상세 정보 조회"""
        data = {
            'productOrderIds': [product_order_id]
        }
        
        response = self.make_authenticated_request('POST', '/external/v1/pay-order/seller/product-orders/query', data, log_details=True)
        
        if response and isinstance(response, dict) and 'data' in response:
            data_list = response['data']
            if isinstance(data_list, list) and len(data_list) > 0:
                return data_list[0]
        
        return {}
    
    def get_multiple_order_details(self, product_order_ids: list) -> Dict:
        """여러 주문 상세 정보 일괄 조회"""
        data = {
            'productOrderIds': product_order_ids
        }

        response = self.make_authenticated_request('POST', '/external/v1/pay-order/seller/product-orders/query', data)
        return response or {}

    def confirm_orders(self, product_order_ids: list) -> Dict:
        """발주확인 API 호출 - 네이버 Commerce API"""
        import http.client
        import json

        try:
            # HTTPS 연결 생성
            conn = http.client.HTTPSConnection("api.commerce.naver.com")

            # 요청 페이로드
            payload = json.dumps({
                "productOrderIds": product_order_ids
            })

            # 요청 헤더
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }

            # API 호출
            conn.request("POST", "/external/v1/pay-order/seller/product-orders/confirm", payload, headers)
            res = conn.getresponse()
            data = res.read()

            # 연결 종료
            conn.close()

            # 응답 파싱
            response_text = data.decode("utf-8")

            if res.status == 200:
                try:
                    response_data = json.loads(response_text)
                    return {
                        'success': True,
                        'data': response_data,
                        'status_code': res.status
                    }
                except json.JSONDecodeError:
                    return {
                        'success': True,
                        'message': response_text,
                        'status_code': res.status
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: {res.status} - {response_text}',
                    'status_code': res.status,
                    'response': response_text
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'발주확인 API 호출 중 오류: {str(e)}',
                'error': str(e)
            }
