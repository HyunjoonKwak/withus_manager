import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "orders.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        try:
            print(f"데이터베이스 초기화 시작 - 경로: {self.db_path}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            print("데이터베이스 연결 성공")
            
            # 주문 테이블
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                order_date TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                product_name TEXT,
                quantity INTEGER,
                price INTEGER,
                status TEXT DEFAULT '신규주문',
                shipping_company TEXT,
                tracking_number TEXT,
                memo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
            # 설정 테이블
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
            # 상품 테이블
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_product_no TEXT UNIQUE NOT NULL,
                origin_product_no TEXT,
                product_name TEXT NOT NULL,
                status_type TEXT,
                sale_price INTEGER DEFAULT 0,
                discounted_price INTEGER DEFAULT 0,
                stock_quantity INTEGER DEFAULT 0,
                category_id TEXT,
                category_name TEXT,
                brand_name TEXT,
                manufacturer_name TEXT,
                model_name TEXT,
                seller_management_code TEXT,
                reg_date TEXT,
                modified_date TEXT,
                representative_image_url TEXT,
                whole_category_name TEXT,
                whole_category_id TEXT,
                delivery_fee INTEGER DEFAULT 0,
                return_fee INTEGER DEFAULT 0,
                exchange_fee INTEGER DEFAULT 0,
                discount_method TEXT,
                customer_benefit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
            # 알림 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    notification_type TEXT,
                    message TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 사용자 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    full_name TEXT,
                    is_admin BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 상품 옵션 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS product_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin_product_no TEXT NOT NULL,
                    option_id TEXT NOT NULL,
                    option_name TEXT,
                    option_name1 TEXT,
                    price INTEGER DEFAULT 0,
                    stock_quantity INTEGER DEFAULT 0,
                    status_type TEXT,
                    seller_manager_code TEXT,
                    usable BOOLEAN DEFAULT 1,
                    option_items TEXT,  -- JSON 형태로 저장
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(origin_product_no, option_id)
                )
            ''')

            # 기존 테이블에 누락된 컬럼들 추가
            self._add_missing_columns(cursor)

            conn.commit()
            conn.close()

            # 기본 관리자 계정 생성
            self.create_default_admin()

            print("데이터베이스 초기화 완료")
        except Exception as e:
            print(f"데이터베이스 초기화 오류: {e}")
            raise
    
    def _add_missing_columns(self, cursor):
        """기존 테이블에 누락된 컬럼들 추가"""
        try:
            # products 테이블에 누락된 컬럼들 추가
            missing_product_columns = [
                ('discount_method', 'TEXT'),
                ('customer_benefit', 'TEXT')
            ]
            
            for column_name, column_type in missing_product_columns:
                try:
                    cursor.execute(f'ALTER TABLE products ADD COLUMN {column_name} {column_type}')
                    print(f"상품 컬럼 추가 성공: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"컬럼 이미 존재: {column_name}")
                    else:
                        print(f"컬럼 추가 실패: {column_name} - {e}")
            
            # orders 테이블에 누락된 컬럼들 추가
            missing_order_columns = [
                ('product_order_id', 'TEXT'),
                ('shipping_due_date', 'TEXT'),
                ('product_option', 'TEXT'),
                ('place_order_status', 'TEXT'),
                ('product_number', 'TEXT'),
                ('buyer_name', 'TEXT'),
                ('buyer_phone', 'TEXT'),
                ('recipient_name', 'TEXT'),
                ('shipping_address', 'TEXT'),
                ('recipient_phone', 'TEXT')
            ]
            
            for column_name, column_type in missing_order_columns:
                try:
                    cursor.execute(f'ALTER TABLE orders ADD COLUMN {column_name} {column_type}')
                    print(f"주문 컬럼 추가 성공: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"컬럼 이미 존재: {column_name}")
                    else:
                        print(f"컬럼 추가 실패: {column_name} - {e}")
                        
        except Exception as e:
            print(f"컬럼 추가 중 오류: {e}")
    
    def add_order(self, order_data: Dict) -> bool:
        """새 주문 추가"""
        try:
            print(f"🗄️ DB 저장 시도: 주문 ID={order_data.get('order_id')}")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO orders
                (order_id, order_date, customer_name, customer_phone,
                 product_name, quantity, price, status, shipping_company,
                 tracking_number, memo, product_order_id, shipping_due_date,
                 product_option, place_order_status, product_number, buyer_name,
                 buyer_phone, recipient_name, shipping_address, recipient_phone, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_data.get('order_id'),
                order_data.get('order_date'),
                order_data.get('customer_name'),
                order_data.get('customer_phone'),
                order_data.get('product_name'),
                order_data.get('quantity', 1),
                order_data.get('price', 0),
                order_data.get('status', '신규주문'),
                order_data.get('shipping_company'),
                order_data.get('tracking_number'),
                order_data.get('memo'),
                order_data.get('product_order_id'),
                order_data.get('shipping_due_date'),
                order_data.get('product_option'),
                order_data.get('place_order_status'),
                order_data.get('product_number'),
                order_data.get('buyer_name'),
                order_data.get('buyer_phone'),
                order_data.get('recipient_name'),
                order_data.get('shipping_address'),
                order_data.get('recipient_phone'),
                datetime.now().isoformat()
            ))

            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()

            print(f"✅ DB 저장 성공: {rows_affected}개 행 영향받음")
            return True
        except Exception as e:
            print(f"❌ DB 저장 실패: {e}")
            return False
    
    def get_orders_by_status(self, status: str) -> List[Dict]:
        """상태별 주문 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders WHERE status = ? ORDER BY order_date DESC
        ''', (status,))
        
        columns = [description[0] for description in cursor.description]
        orders = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return orders
    
    def get_all_orders(self) -> List[Dict]:
        """모든 주문 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders ORDER BY order_date DESC
        ''')
        
        columns = [description[0] for description in cursor.description]
        orders = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return orders
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """주문 상태 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?
            ''', (status, datetime.now().isoformat(), order_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"주문 상태 업데이트 오류: {e}")
            return False
    
    def get_order_counts(self) -> Dict[str, int]:
        """주문 상태별 건수 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) as count FROM orders GROUP BY status
        ''')
        
        counts = {}
        for row in cursor.fetchall():
            counts[row[0]] = row[1]
        
        conn.close()
        return counts
    
    def save_setting(self, key: str, value: str) -> bool:
        """설정 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"설정 저장 오류: {e}")
            return False
    
    def get_setting(self, key: str) -> Optional[str]:
        """설정 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    
    def save_product(self, product_data: Dict) -> bool:
        """상품 정보 저장 (기존 상품이 있으면 업데이트)"""
        try:
            print(f"DB 저장 시작 - 상품 데이터: {product_data}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기존 상품 확인
            channel_product_no = product_data.get('channel_product_no')
            print(f"기존 상품 확인 - 채널상품 ID: {channel_product_no}")
            cursor.execute('SELECT id FROM products WHERE channel_product_no = ?', 
                          (channel_product_no,))
            existing = cursor.fetchone()
            print(f"기존 상품 확인 결과: {existing}")
            
            if existing:
                # 업데이트
                print(f"기존 상품 업데이트 - ID: {existing[0]}")
                cursor.execute('''
                    UPDATE products SET
                        origin_product_no = ?,
                        product_name = ?,
                        status_type = ?,
                        sale_price = ?,
                        discounted_price = ?,
                        stock_quantity = ?,
                        category_id = ?,
                        category_name = ?,
                        brand_name = ?,
                        manufacturer_name = ?,
                        model_name = ?,
                        seller_management_code = ?,
                        reg_date = ?,
                        modified_date = ?,
                        representative_image_url = ?,
                        whole_category_name = ?,
                        whole_category_id = ?,
                        delivery_fee = ?,
                        return_fee = ?,
                        exchange_fee = ?,
                        discount_method = ?,
                        customer_benefit = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE channel_product_no = ?
                ''', (
                    product_data.get('origin_product_no'),
                    product_data.get('product_name'),
                    product_data.get('status_type'),
                    product_data.get('sale_price', 0),
                    product_data.get('discounted_price', 0),
                    product_data.get('stock_quantity', 0),
                    product_data.get('category_id'),
                    product_data.get('category_name'),
                    product_data.get('brand_name'),
                    product_data.get('manufacturer_name'),
                    product_data.get('model_name'),
                    product_data.get('seller_management_code'),
                    product_data.get('reg_date'),
                    product_data.get('modified_date'),
                    product_data.get('representative_image_url'),
                    product_data.get('whole_category_name'),
                    product_data.get('whole_category_id'),
                    product_data.get('delivery_fee', 0),
                    product_data.get('return_fee', 0),
                    product_data.get('exchange_fee', 0),
                    product_data.get('discount_method'),
                    product_data.get('customer_benefit'),
                    product_data.get('channel_product_no')
                ))
            else:
                # 새로 삽입
                print(f"새 상품 삽입 - 채널상품 ID: {channel_product_no}")
                cursor.execute('''
                    INSERT INTO products (
                        channel_product_no, origin_product_no, product_name, status_type,
                        sale_price, discounted_price, stock_quantity, category_id, category_name,
                        brand_name, manufacturer_name, model_name, seller_management_code,
                        reg_date, modified_date, representative_image_url, whole_category_name,
                        whole_category_id, delivery_fee, return_fee, exchange_fee,
                        discount_method, customer_benefit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product_data.get('channel_product_no'),
                    product_data.get('origin_product_no'),
                    product_data.get('product_name'),
                    product_data.get('status_type'),
                    product_data.get('sale_price', 0),
                    product_data.get('discounted_price', 0),
                    product_data.get('stock_quantity', 0),
                    product_data.get('category_id'),
                    product_data.get('category_name'),
                    product_data.get('brand_name'),
                    product_data.get('manufacturer_name'),
                    product_data.get('model_name'),
                    product_data.get('seller_management_code'),
                    product_data.get('reg_date'),
                    product_data.get('modified_date'),
                    product_data.get('representative_image_url'),
                    product_data.get('whole_category_name'),
                    product_data.get('whole_category_id'),
                    product_data.get('delivery_fee', 0),
                    product_data.get('return_fee', 0),
                    product_data.get('exchange_fee', 0),
                    product_data.get('discount_method'),
                    product_data.get('customer_benefit')
                ))
            
            conn.commit()
            conn.close()
            print(f"상품 저장 완료 - 채널상품 ID: {channel_product_no}")
            return True
            
        except Exception as e:
            print(f"상품 저장 오류: {e}")
            print(f"오류 타입: {type(e)}")
            import traceback
            print(f"상세 오류 정보: {traceback.format_exc()}")
            return False
    
    def get_all_products(self) -> List[Dict]:
        """모든 상품 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT channel_product_no, origin_product_no, product_name, status_type,
                       sale_price, discounted_price, stock_quantity, category_id, category_name,
                       brand_name, manufacturer_name, model_name, seller_management_code,
                       reg_date, modified_date, representative_image_url, whole_category_name,
                       whole_category_id, delivery_fee, return_fee, exchange_fee,
                       discount_method, customer_benefit, created_at, updated_at
                FROM products
                ORDER BY updated_at DESC
            ''')

            columns = [description[0] for description in cursor.description]
            products = []

            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                products.append(product)

            conn.close()
            return products

        except Exception as e:
            print(f"상품 조회 오류: {e}")
            return []
    
    def get_products_by_status(self, status: str) -> List[Dict]:
        """상태별 상품 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT channel_product_no, origin_product_no, product_name, status_type,
                       sale_price, discounted_price, stock_quantity, category_id, category_name,
                       brand_name, manufacturer_name, model_name, seller_management_code,
                       reg_date, modified_date, representative_image_url, whole_category_name,
                       whole_category_id, delivery_fee, return_fee, exchange_fee,
                       discount_method, customer_benefit, created_at, updated_at
                FROM products
                WHERE status_type = ?
                ORDER BY updated_at DESC
            ''', (status,))
            
            columns = [description[0] for description in cursor.description]
            products = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                products.append(product)
            
            conn.close()
            return products
            
        except Exception as e:
            print(f"상태별 상품 조회 오류: {e}")
            return []
    
    def get_product_by_id(self, channel_product_no: str) -> Optional[Dict]:
        """채널상품 ID로 상품 조회"""
        try:
            print(f"DB 조회 시작 - 채널상품 ID: {channel_product_no}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT channel_product_no, origin_product_no, product_name, status_type,
                       sale_price, discounted_price, stock_quantity, category_id, category_name,
                       brand_name, manufacturer_name, model_name, seller_management_code,
                       reg_date, modified_date, representative_image_url, whole_category_name,
                       whole_category_id, delivery_fee, return_fee, exchange_fee,
                       discount_method, customer_benefit, created_at, updated_at
                FROM products
                WHERE channel_product_no = ?
            ''', (channel_product_no,))
            
            row = cursor.fetchone()
            print(f"DB 조회 결과 - row: {row}")
            conn.close()
            
            if row:
                columns = [description[0] for description in cursor.description]
                result = dict(zip(columns, row))
                print(f"DB 조회 결과 - dict: {result}")
                print(f"DB 조회 결과 - 원상품 ID: {result.get('origin_product_no', 'N/A')}")
                return result
            else:
                print("DB 조회 결과 - 상품을 찾을 수 없음")
            return None
            
        except Exception as e:
            print(f"상품 조회 오류: {e}")
            return None
    
    def delete_product(self, channel_product_no: str) -> bool:
        """상품 삭제"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM products WHERE channel_product_no = ?', 
                          (channel_product_no,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"상품 삭제 오류: {e}")
            return False
    
    def save_order(self, order_data: Dict) -> bool:
        """주문 저장 (add_order의 별칭)"""
        return self.add_order(order_data)
    
    def get_orders_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """날짜 범위로 주문 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM orders
                WHERE DATE(order_date) >= ? AND DATE(order_date) <= ?
                ORDER BY order_date DESC
            ''', (start_date, end_date[:10]))
            
            columns = [description[0] for description in cursor.description]
            orders = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return orders
            
        except Exception as e:
            print(f"날짜 범위 주문 조회 오류: {e}")
            return []
    
    def get_products(self) -> List[Dict]:
        """모든 상품 조회 (get_all_products의 별칭)"""
        return self.get_all_products()

    # ==================== 사용자 관리 메소드 ====================

    def create_user(self, username: str, password: str, email: str = None,
                   full_name: str = None, is_admin: bool = False) -> bool:
        """새 사용자 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 패스워드 해싱 (bcrypt 사용)
            import bcrypt
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            cursor.execute('''
                INSERT INTO users (username, password, email, full_name, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, hashed_password, email, full_name, is_admin))

            conn.commit()
            conn.close()
            return True

        except sqlite3.IntegrityError:
            print(f"사용자 생성 실패: 사용자명 '{username}'이 이미 존재합니다")
            return False
        except Exception as e:
            print(f"사용자 생성 오류: {e}")
            return False

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """사용자 인증 및 정보 반환"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM users
                WHERE username = ? AND is_active = 1
            ''', (username,))

            row = cursor.fetchone()
            conn.close()

            if row:
                columns = ['id', 'username', 'password', 'email', 'full_name',
                          'is_admin', 'is_active', 'created_at', 'updated_at']
                user = dict(zip(columns, row))

                # 패스워드 검증
                import bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    # 패스워드 필드 제거 후 반환
                    del user['password']
                    return user

            return None

        except Exception as e:
            print(f"사용자 인증 오류: {e}")
            return None

    def get_all_users(self) -> List[Dict]:
        """모든 사용자 조회 (관리자용)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, email, full_name, is_admin, is_active,
                       created_at, updated_at FROM users
                ORDER BY created_at DESC
            ''')

            columns = [description[0] for description in cursor.description]
            users = [dict(zip(columns, row)) for row in cursor.fetchall()]

            conn.close()
            return users

        except Exception as e:
            print(f"사용자 목록 조회 오류: {e}")
            return []

    def update_user_admin_status(self, username: str, is_admin: bool) -> bool:
        """사용자 관리자 권한 변경"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users SET is_admin = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (is_admin, username))

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows > 0

        except Exception as e:
            print(f"사용자 권한 변경 오류: {e}")
            return False

    def update_user_active_status(self, username: str, is_active: bool) -> bool:
        """사용자 활성 상태 변경"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (is_active, username))

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows > 0

        except Exception as e:
            print(f"사용자 상태 변경 오류: {e}")
            return False

    def delete_user(self, username: str) -> bool:
        """사용자 삭제"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM users WHERE username = ?', (username,))

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows > 0

        except Exception as e:
            print(f"사용자 삭제 오류: {e}")
            return False

    def create_default_admin(self) -> bool:
        """기본 관리자 계정 생성 (최초 설치시)"""
        try:
            # 관리자 계정이 이미 있는지 확인
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
            admin_count = cursor.fetchone()[0]
            conn.close()

            if admin_count == 0:
                # 기본 관리자 계정 생성
                return self.create_user("withus", "withus2023", "admin@example.com",
                                      "시스템 관리자", is_admin=True)
            return True

        except Exception as e:
            print(f"기본 관리자 생성 오류: {e}")
            return False

    def save_product_options(self, origin_product_no: str, options: List[Dict]) -> bool:
        """상품 옵션 정보 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 기존 옵션 정보 삭제 (새로 업데이트)
            cursor.execute('DELETE FROM product_options WHERE origin_product_no = ?', (origin_product_no,))

            if options:
                # 옵션이 있는 경우 실제 옵션 정보 저장
                for option in options:
                    option_items_json = json.dumps(option.get('optionItems', []), ensure_ascii=False)

                    cursor.execute('''
                        INSERT OR REPLACE INTO product_options (
                            origin_product_no, option_id, option_name, option_name1,
                            price, stock_quantity, status_type, seller_manager_code,
                            usable, option_items
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        origin_product_no,
                        option.get('id', ''),
                        option.get('optionName', ''),
                        option.get('optionName1', ''),
                        option.get('price', 0),
                        option.get('stockQuantity', 0),
                        option.get('statusType', ''),
                        option.get('sellerManagerCode', ''),
                        option.get('usable', True),
                        option_items_json
                    ))
            else:
                # 옵션이 없는 경우 더미 레코드 저장 (캐시됐음을 표시)
                cursor.execute('''
                    INSERT INTO product_options (
                        origin_product_no, option_id, option_name, option_name1,
                        price, stock_quantity, status_type, seller_manager_code,
                        usable, option_items
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    origin_product_no,
                    'NO_OPTIONS',  # 옵션 없음 표시용 더미 ID
                    'NO_OPTIONS',
                    '',
                    0,
                    0,
                    '',
                    '',
                    True,
                    '[]'
                ))

            conn.commit()
            conn.close()
            print(f"옵션 정보 저장 완료: {origin_product_no}, {len(options)}개 옵션")
            return True

        except Exception as e:
            print(f"옵션 정보 저장 오류: {e}")
            return False

    def get_product_options(self, origin_product_no: str) -> List[Dict]:
        """저장된 상품 옵션 정보 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM product_options
                WHERE origin_product_no = ? AND option_id != 'NO_OPTIONS'
                ORDER BY created_at ASC
            ''', (origin_product_no,))

            rows = cursor.fetchall()
            conn.close()

            options = []
            for row in rows:
                option_items = json.loads(row['option_items']) if row['option_items'] else []

                option = {
                    'id': row['option_id'],
                    'optionName': row['option_name'],
                    'optionName1': row['option_name1'],
                    'price': row['price'],
                    'stockQuantity': row['stock_quantity'],
                    'statusType': row['status_type'],
                    'sellerManagerCode': row['seller_manager_code'],
                    'usable': bool(row['usable']),
                    'optionItems': option_items
                }
                options.append(option)

            return options

        except Exception as e:
            print(f"옵션 정보 조회 오류: {e}")
            return []

    def has_cached_options(self, origin_product_no: str) -> bool:
        """해당 상품의 캐시된 옵션 정보가 있는지 확인 (빈 배열이라도 캐시됨)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # origin_product_no가 한 번이라도 조회되어 저장되었는지 확인
            # (옵션이 없어도 더미 레코드로 저장되므로 COUNT > 0이면 캐시됨)
            cursor.execute('SELECT COUNT(*) FROM product_options WHERE origin_product_no = ?', (origin_product_no,))
            count = cursor.fetchone()[0]
            conn.close()

            return count > 0

        except Exception as e:
            print(f"캐시된 옵션 확인 오류: {e}")
            return False