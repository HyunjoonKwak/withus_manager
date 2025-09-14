#!/usr/bin/env python3
"""데이터베이스 디버깅 스크립트"""

from database import DatabaseManager

# 데이터베이스 매니저 인스턴스 생성
db_manager = DatabaseManager()

# 모든 주문 조회
orders = db_manager.get_all_orders()

print(f"총 주문 수: {len(orders)}")

if orders:
    print(f"첫 번째 주문 예시:")
    first_order = orders[0]
    print(f"  타입: {type(first_order)}")
    print(f"  키: {list(first_order.keys()) if isinstance(first_order, dict) else 'dict 아님'}")
    print(f"  내용: {first_order}")

    print(f"\n취소 주문 찾기:")
    canceled_orders = [order for order in orders if order.get('status') == 'CANCELED']
    print(f"  취소 주문 수: {len(canceled_orders)}")

    if canceled_orders:
        print(f"  첫 번째 취소 주문:")
        print(f"    주문ID: {canceled_orders[0].get('order_id')}")
        print(f"    고객명: {canceled_orders[0].get('customer_name')}")
        print(f"    상품명: {canceled_orders[0].get('product_name')}")
        print(f"    상태: {canceled_orders[0].get('status')}")
        print(f"    주문일시: {canceled_orders[0].get('order_date')}")
else:
    print("주문 데이터가 없습니다.")