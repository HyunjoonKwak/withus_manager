#!/bin/bash
# FastAPI 수동 테스트 스크립트

echo "🚀 FastAPI 수동 테스트 시작"
echo "서버가 http://localhost:8000 에서 실행 중인지 확인하세요"
echo ""

# 기본 엔드포인트 테스트
echo "1️⃣ 헬스 체크 테스트"
curl -s http://localhost:8000/health | jq .
echo ""

echo "2️⃣ 루트 엔드포인트 테스트"  
curl -s http://localhost:8000/ | jq .
echo ""

echo "3️⃣ 주문 목록 조회 (빈 목록 예상)"
curl -s http://localhost:8000/api/v1/orders/ | jq .
echo ""

echo "4️⃣ 대시보드 통계 조회"
curl -s http://localhost:8000/api/v1/dashboard/stats | jq .
echo ""

echo "5️⃣ 상품 목록 조회 (빈 목록 예상)"
curl -s http://localhost:8000/api/v1/products/ | jq .
echo ""

echo "6️⃣ 새 주문 생성 테스트"
curl -s -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "TEST001", 
    "order_date": "2024-01-15T10:00:00",
    "customer_name": "테스트 고객",
    "product_name": "테스트 상품",
    "quantity": 1,
    "price": 10000
  }' | jq .
echo ""

echo "7️⃣ 생성된 주문 조회"
curl -s http://localhost:8000/api/v1/orders/TEST001 | jq .
echo ""

echo "8️⃣ 주문 상태 업데이트"
curl -s -X PUT "http://localhost:8000/api/v1/orders/TEST001/status?status=배송중" | jq .
echo ""

echo "9️⃣ 업데이트 후 주문 목록 재조회"
curl -s http://localhost:8000/api/v1/orders/ | jq .
echo ""

echo "✅ 모든 테스트 완료!"
echo "더 자세한 테스트는 http://localhost:8000/docs 에서 진행하세요"