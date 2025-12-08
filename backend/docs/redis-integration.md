# Redis Integration Guide

## 개요

거래(`transactions`) 추가/수정/삭제 시 자동으로 Redis에 자산 잔고가 업데이트됩니다.

## Redis 키 구조

### 자산 잔고
```
asset:{asset_id}:balance
```

- **값**: 현재 보유 수량 (문자열 형태의 숫자)
- **업데이트 시점**: 거래 생성/수정/삭제 시 자동
- **계산 방식**: PostgreSQL의 모든 거래 `quantity` 합계 (flow_type과 무관)

### 사용자 캐시
```
user:{user_id}:summary:*
```

- **값**: 사용자 포트폴리오 요약 (미구현)
- **TTL**: 5분 (예정)
- **무효화**: 거래 생성/수정/삭제 시 자동 삭제

### 자산 가격 캐싱
```
asset:{asset_id}:current_price
```

- **값**: 자산의 최신 시세 (문자열 형태의 숫자)
- **업데이트 시점**: 외부 시세 API에서 주기적으로 갱신 또는 수동 업데이트
- **TTL**: 1분 (권장)
- **활용 예시**: 자산 목록/상세 조회 시 실시간 가격 제공

## 설정

### 환경 변수 (.env)

```bash
# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
```

## 사용 예시

### 자산 조회 시 잔고 포함

모든 자산 조회 API는 자동으로 Redis에서 잔고를 가져와 응답에 포함합니다:

```bash
# 자산 목록 조회
GET /api/v1/assets
Response:
{
  "items": [
    {
      "id": "asset-123",
      "name": "삼성전자",
      "asset_type": "stock",
      "symbol": "005930",
      "balance": 100.0,  # ← Redis에서 조회
      ...
    }
  ],
  ...
}

# 단일 자산 조회
GET /api/v1/assets/{asset_id}
Response:
{
  "id": "asset-123",
  "name": "삼성전자",
  "balance": 100.0,  # ← Redis에서 조회
  ...
}
```

### 자산 가격 포함 예시

자산 목록/상세 조회 시 Redis에서 가격을 함께 조회하여 응답에 포함할 수 있습니다:

```bash
# 자산 목록 조회 (가격 포함)
GET /api/v1/assets
Response:
{
  "items": [
    {
      "id": "asset-123",
      "name": "삼성전자",
      "asset_type": "stock",
      "symbol": "005930",
      "balance": 100.0,  # ← Redis에서 조회
      "current_price": 72000.0,  # ← Redis에서 조회
      ...
    }
  ],
  ...
}

# 단일 자산 조회 (가격 포함)
GET /api/v1/assets/{asset_id}
Response:
{
  "id": "asset-123",
  "name": "삼성전자",
  "balance": 100.0,  # ← Redis에서 조회
  "current_price": 72000.0,  # ← Redis에서 조회
  ...
}
```

### Python API에서 자동 처리

거래를 생성하면 자동으로 Redis가 업데이트됩니다:

```python
# 거래 생성
POST /api/v1/transactions
{
  "asset_id": "123e4567-e89b-12d3-a456-426614174000",
  "type": "buy",
  "quantity": 100,
  "price": 50000,
  ...
}

# 자동으로 Redis 업데이트:
# SET asset:123e4567-e89b-12d3-a456-426614174000:balance "100"
```

### Redis에서 직접 조회

```bash
# Redis CLI에서 잔고 조회
redis-cli
> GET asset:123e4567-e89b-12d3-a456-426614174000:balance
"100.50"
```

### Python 코드에서 사용

```python
from app.core.redis import get_asset_balance, update_asset_balance

# 잔고 조회
balance = get_asset_balance("123e4567-e89b-12d3-a456-426614174000")
print(f"Current balance: {balance}")

# 잔고 수동 업데이트 (일반적으로 자동 처리됨)
update_asset_balance("123e4567-e89b-12d3-a456-426614174000", 150.5)

# DB에서 재계산 후 업데이트
from app.core.database import SessionLocal
from app.core.redis import calculate_and_update_balance

db = SessionLocal()
balance = calculate_and_update_balance(db, "123e4567-e89b-12d3-a456-426614174000")
db.close()
```

### 가격 캐싱 사용 예시

```python
from app.core.redis import get_asset_price, set_asset_price

# 가격 조회
price = get_asset_price("123e4567-e89b-12d3-a456-426614174000")
print(f"Current price: {price}")

# 가격 수동 업데이트 (TTL 60초)
set_asset_price("123e4567-e89b-12d3-a456-426614174000", 72000.0)

# 가격 수동 업데이트 (TTL 5분)
set_asset_price("123e4567-e89b-12d3-a456-426614174000", 72000.0, ttl=300)
```

## API 함수

### `app/core/redis.py`

#### `update_asset_balance(asset_id: str, quantity: float)`
자산 잔고를 Redis에 업데이트

#### `get_asset_balance(asset_id: str) -> float`
Redis에서 자산 잔고 조회

#### `delete_asset_balance(asset_id: str)`
Redis에서 자산 잔고 삭제

#### `calculate_and_update_balance(db: Session, asset_id: str) -> float`
DB에서 거래 내역을 집계하여 잔고를 계산하고 Redis에 업데이트

#### `invalidate_user_cache(user_id: str)`
사용자 관련 캐시 무효화

#### `set_asset_price(asset_id: str, price: float, ttl: int = 60)`
자산의 현재 시세를 Redis에 저장 (기본 TTL 60초)

#### `get_asset_price(asset_id: str) -> float | None`
Redis에서 자산의 현재 시세 조회

## 트러블슈팅

### Redis 연결 오류

```python
redis.exceptions.ConnectionError: Error connecting to Redis
```

**해결 방법**:
1. Redis 서버가 실행 중인지 확인: `redis-cli ping`
2. 환경 변수 확인: `REDIS_HOST`, `REDIS_PORT`
3. 방화벽 설정 확인

### 잔고가 동기화되지 않음

**해결 방법**:
1. 해당 자산 거래가 정상적으로 커밋되었는지 확인 (flow_type과 무관하게 반영됨)
2. Redis에서 수동으로 재계산:
   ```python
   from app.core.redis import calculate_and_update_balance
   calculate_and_update_balance(db, asset_id)
   ```

## 성능 최적화

### 대량 거래 처리

대량 거래 생성 시 자동으로 중복 업데이트를 방지합니다:

```python
# 같은 자산에 대한 여러 거래를 한 번에 처리
POST /api/v1/transactions/bulk
{
  "transactions": [
    {"asset_id": "asset-1", ...},
    {"asset_id": "asset-1", ...},
    {"asset_id": "asset-2", ...}
  ]
}

# asset-1은 한 번만 업데이트됨
```

## 향후 계획

- [ ] 평균 취득 단가 (`asset:{asset_id}:avg_price`)
- [x] 현재 시세 캐싱 (`asset:{asset_id}:current_price`)
- [ ] FIFO/LIFO 매수 큐 구현
- [ ] 사용자 포트폴리오 캐싱
