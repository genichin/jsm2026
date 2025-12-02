# Redis Schema Design  

## Redis 7+ 인메모리 구조

**목적**: 실시간 자산 정보 관리 및 수익 계산 최적화

## 주요 역할

1. **실시간 자산 정보**: 현재 잔고, 평균 단가, 시세
2. **수익 계산 큐**: 매수 내역 추적 (FIFO/LIFO 계산용)
3. **캐시**: 자주 조회되는 집계 데이터

---

## Redis 키 구조

### 1. 자산별 실시간 데이터

```redis
# 키 구조: asset:{asset_id}:{field_name}
asset:123e4567-e89b-12d3-a456-426614174000:balance      # 현재 보유 수량
asset:123e4567-e89b-12d3-a456-426614174000:avg_price     # 평균 취득 단가
asset:123e4567-e89b-12d3-a456-426614174000:price        # 현재 시세

# 예시 값
GET asset:123e4567-e89b-12d3-a456-426614174000:balance
> "150.00000000"

GET asset:123e4567-e89b-12d3-a456-426614174000:avg_price  
> "62500.00"

GET asset:123e4567-e89b-12d3-a456-426614174000:current_price
> "68000.00"
```

**데이터 타입**: String (NUMERIC 호환)
**TTL**: 무제한 (영구 저장)
**동기화**: PostgreSQL과 양방향 동기화

### 2. 매수 내역 추적 큐

```redis
# 키 구조: purchase_queue:{asset_id}:{calc_method}
purchase_queue:123e4567-e89b-12d3-a456-426614174000:FIFO
purchase_queue:123e4567-e89b-12d3-a456-426614174000:LIFO
purchase_queue:123e4567-e89b-12d3-a456-426614174000:AVG

# FIFO/LIFO용 List 구조 (Sorted Set 사용)
# Score = transaction_date의 timestamp, Member = JSON 매수 정보
ZADD purchase_queue:123e4567-e89b-12d3-a456-426614174000:FIFO \
  1698739200 '{"transaction_id":"tx001","quantity":"100.00","price":"60000.00","remaining":"80.00"}'
  1698825600 '{"transaction_id":"tx002","quantity":"50.00","price":"65000.00","remaining":"50.00"}'

# AVG용 Hash 구조 (단순한 집계값)
HSET purchase_queue:123e4567-e89b-12d3-a456-426614174000:AVG \
  total_quantity "130.00" \
  total_cost "8250000.00" \
  avg_price "63461.54"
```

**FIFO/LIFO 큐 설계**:
- **타입**: Sorted Set (ZADD, ZRANGE 사용)
- **Score**: `transaction_date`의 Unix Timestamp
- **Member**: JSON 형태의 매수 정보
  ```json
  {
    "transaction_id": "거래 ID",
    "quantity": "원래 수량",
    "price": "매수 단가", 
    "remaining": "남은 수량"
  }
  ```

**AVG 큐 설계**:
- **타입**: Hash (HSET, HGET 사용)
- **필드**: `total_quantity`, `total_cost`, `avg_price`

### 3. 사용자별 집계 캐시

```redis
# 키 구조: user:{user_id}:summary:{timeframe}
user:user123:summary:total         # 전체 자산 요약
user:user123:summary:today         # 오늘 손익
user:user123:summary:this_month    # 이번 달 손익

# Hash 구조
HSET user:user123:summary:total \
  total_assets "12500000.00" \
  total_cash "2500000.00" \
  total_stocks_value "10000000.00" \
  unrealized_profit "1500000.00" \
  realized_profit "500000.00"

# TTL 설정 (5분)
EXPIRE user:user123:summary:total 300
```

**캐시 전략**:
- **TTL**: 5분 (실시간성과 성능의 균형)
- **갱신**: 거래 발생 시 즉시 삭제하여 재계산 유도
- **타입**: Hash (필드별 부분 조회 가능)

### 4. 시세 정보 캐시

```redis
# 키 구조: market_price:{symbol}
market_price:005930    # 삼성전자 현재가
market_price:BTC       # 비트코인 현재가

# Hash 구조 (상세 정보)
HSET market_price:005930 \
  current_price "68000" \
  prev_close "67500" \
  change_rate "0.74" \
  volume "12345678" \
  updated_at "1698825600"

# TTL: 30초 (실시간 시세)
EXPIRE market_price:005930 30
```

---

## 수익 계산 시스템

### 계산 방식별 구현

#### 1. FIFO (First In, First Out) 구현

```python
async def calculate_fifo_profit(asset_id: str, sell_quantity: float, sell_price: float):
    """FIFO 방식 수익 계산"""
    redis_key = f"purchase_queue:{asset_id}:FIFO"
    
    # 오래된 순서대로 매수 내역 조회
    purchases = await redis.zrange(redis_key, 0, -1, withscores=True)
    
    remaining_to_sell = sell_quantity
    total_cost = 0.0
    updated_purchases = []
    
    for purchase_json, timestamp in purchases:
        if remaining_to_sell <= 0:
            # 남은 매수 내역은 그대로 유지
            updated_purchases.append((purchase_json, timestamp))
            continue
            
        purchase = json.loads(purchase_json)
        available = float(purchase['remaining'])
        
        if available > remaining_to_sell:
            # 부분 매도: 해당 매수에서 일부만 차감
            cost = remaining_to_sell * float(purchase['price'])
            total_cost += cost
            
            # 남은 수량 업데이트
            purchase['remaining'] = str(available - remaining_to_sell)
            updated_purchases.append((json.dumps(purchase), timestamp))
            remaining_to_sell = 0
        else:
            # 전체 매도: 해당 매수 전량 소진
            cost = available * float(purchase['price'])
            total_cost += cost
            remaining_to_sell -= available
            # 이 매수 내역은 큐에서 제거 (updated_purchases에 추가하지 않음)
    
    # Redis 큐 업데이트
    await redis.delete(redis_key)
    if updated_purchases:
        # 남은 매수 내역을 다시 저장
        for purchase_json, timestamp in updated_purchases:
            await redis.zadd(redis_key, {purchase_json: timestamp})
    
    # 수익 계산
    sell_amount = sell_quantity * sell_price
    profit = sell_amount - total_cost
    
    return profit, total_cost
```

#### 2. LIFO (Last In, First Out) 구현

```python
async def calculate_lifo_profit(asset_id: str, sell_quantity: float, sell_price: float):
    """LIFO 방식 수익 계산"""
    redis_key = f"purchase_queue:{asset_id}:LIFO"
    
    # 최신 순서대로 매수 내역 조회 (ZREVRANGE 사용)
    purchases = await redis.zrevrange(redis_key, 0, -1, withscores=True)
    
    remaining_to_sell = sell_quantity
    total_cost = 0.0
    updated_purchases = []
    
    for purchase_json, timestamp in purchases:
        if remaining_to_sell <= 0:
            # 처리하지 않은 매수 내역은 그대로 유지 (오래된 순서로 다시 정렬)
            updated_purchases.append((purchase_json, timestamp))
            continue
            
        purchase = json.loads(purchase_json)
        available = float(purchase['remaining'])
        
        if available > remaining_to_sell:
            # 부분 매도
            cost = remaining_to_sell * float(purchase['price'])
            total_cost += cost
            
            purchase['remaining'] = str(available - remaining_to_sell)
            updated_purchases.append((json.dumps(purchase), timestamp))
            remaining_to_sell = 0
        else:
            # 전체 매도
            cost = available * float(purchase['price'])
            total_cost += cost
            remaining_to_sell -= available
            # 이 매수 내역은 큐에서 제거
    
    # Redis 큐 업데이트 (역순으로 처리했으므로 다시 정렬)
    await redis.delete(redis_key)
    if updated_purchases:
        # 시간순으로 다시 저장
        updated_purchases.reverse()  # 오래된 순서로 되돌림
        for purchase_json, timestamp in updated_purchases:
            await redis.zadd(redis_key, {purchase_json: timestamp})
    
    # 수익 계산
    sell_amount = sell_quantity * sell_price
    profit = sell_amount - total_cost
    
    return profit, total_cost
```

#### 3. AVG (Average Cost) 구현

```python
async def calculate_avg_profit(asset_id: str, sell_quantity: float, sell_price: float):
    """평균 단가 방식 수익 계산"""
    redis_key = f"purchase_queue:{asset_id}:AVG"
    
    # 현재 평균 정보 조회
    avg_data = await redis.hmget(redis_key, 'total_quantity', 'total_cost', 'avg_price')
    
    if not all(avg_data):
        raise ValueError(f"No average data found for asset {asset_id}")
    
    total_quantity = float(avg_data[0])
    total_cost = float(avg_data[1])
    avg_price = float(avg_data[2])
    
    # 수익 계산
    cost_basis = sell_quantity * avg_price
    sell_amount = sell_quantity * sell_price
    profit = sell_amount - cost_basis
    
    # 남은 수량과 비용 계산
    remaining_quantity = total_quantity - sell_quantity
    remaining_cost = total_cost - cost_basis
    new_avg_price = remaining_cost / remaining_quantity if remaining_quantity > 0 else 0
    
    # Redis 업데이트
    if remaining_quantity > 0:
        await redis.hmset(redis_key, {
            'total_quantity': str(remaining_quantity),
            'total_cost': str(remaining_cost),
            'avg_price': str(new_avg_price)
        })
    else:
        # 전량 매도 시 큐 삭제
        await redis.delete(redis_key)
    
    return profit, cost_basis
```

### 매수 시 큐 업데이트

```python
async def add_purchase_to_queue(asset_id: str, transaction_id: str, 
                               quantity: float, price: float, 
                               transaction_date: datetime, calc_method: str):
    """매수 시 큐에 추가
    
    참고: 자산 매수 시 복식부기로 2개의 거래가 생성됩니다:
    - buy 타입: 자산 수량 증가 (양수)
    - out_asset 타입: 현금 감소 (음수) - 연결된 현금 자산에 기록
    
    매수 큐에는 buy 타입 거래만 추가됩니다.
    """
    
    if calc_method in ['FIFO', 'LIFO']:
        # Sorted Set에 추가
        redis_key = f"purchase_queue:{asset_id}:{calc_method}"
        purchase_data = {
            "transaction_id": transaction_id,
            "quantity": str(quantity),
            "price": str(price),
            "remaining": str(quantity)  # 초기에는 전량 남음
        }
        timestamp = transaction_date.timestamp()
        
        await redis.zadd(redis_key, {json.dumps(purchase_data): timestamp})
        
    elif calc_method == 'AVG':
        # Hash 업데이트 (기존 값과 합산)
        redis_key = f"purchase_queue:{asset_id}:AVG"
        
        # 기존 데이터 조회
        existing = await redis.hmget(redis_key, 'total_quantity', 'total_cost')
        
        prev_quantity = float(existing[0]) if existing[0] else 0.0
        prev_cost = float(existing[1]) if existing[1] else 0.0
        
        # 새로운 집계값 계산
        new_quantity = prev_quantity + quantity
        new_cost = prev_cost + (quantity * price)
        new_avg_price = new_cost / new_quantity
        
        # Redis 업데이트
        await redis.hmset(redis_key, {
            'total_quantity': str(new_quantity),
            'total_cost': str(new_cost),
            'avg_price': str(new_avg_price)
        })
```

---

## 데이터 동기화

### PostgreSQL ↔ Redis 동기화

#### 1. Transaction 발생 시 (실시간 동기화)

```python
async def sync_transaction_to_redis(transaction: Transaction):
    """거래 발생 시 Redis 업데이트"""
    
    # 1. 현재 수량 업데이트
    quantity_key = f"asset:{transaction.asset_id}:quantity"
    await redis.incrbyfloat(quantity_key, float(transaction.quantity))
    
    # 2. 수익 계산 큐 업데이트
    if transaction.type == 'exchange' and transaction.quantity > 0:
        # 매수: 큐에 추가
        # 현재 시스템 전역 기본 계산 방식 (예: 'FIFO')
        calc_method = 'FIFO'
        await add_purchase_to_queue(
            transaction.asset_id,
            transaction.id,
            float(transaction.quantity),
            float(transaction.price),
            transaction.transaction_date,
            calc_method
        )
    elif transaction.type == 'exchange' and transaction.quantity < 0:
        # 매도: 수익 계산 및 큐 업데이트
        sell_quantity = abs(float(transaction.quantity))
        calc_method = 'FIFO'

        if calc_method == 'FIFO':
            profit, _ = await calculate_fifo_profit(
                transaction.asset_id, sell_quantity, float(transaction.price)
            )
        elif calc_method == 'LIFO':
            profit, _ = await calculate_lifo_profit(
                transaction.asset_id, sell_quantity, float(transaction.price)
            )
        elif calc_method == 'AVG':
            profit, _ = await calculate_avg_profit(
                transaction.asset_id, sell_quantity, float(transaction.price)
            )
    
    # 3. 사용자 요약 캐시 무효화
    user_id = await get_user_id_by_asset(transaction.asset_id)
    await redis.delete(f"user:{user_id}:summary:*")
    
    # 4. 평균 단가 재계산 (AVG 방식인 경우 이미 처리됨)
    if calc_method != 'AVG':
        await recalculate_avg_price(transaction.asset_id)
```

#### 2. 배치 동기화 (정합성 보장)

```python
async def full_sync_asset_to_redis(asset_id: str):
    """특정 자산의 전체 동기화"""
    
    # PostgreSQL에서 현재 상태 계산
    total_quantity = await calculate_total_quantity_from_db(asset_id)
    
    # Redis 업데이트
    quantity_key = f"asset:{asset_id}:quantity"
    await redis.set(quantity_key, str(total_quantity))
    
    # 매수 큐 재구성 (전역 기본 계산 방식 사용)
    calc_method = 'FIFO'
    await rebuild_purchase_queue(asset_id, calc_method)

async def rebuild_purchase_queue(asset_id: str, calc_method: str):
    """매수 큐 전체 재구성"""
    
    # 기존 큐 삭제
    redis_key = f"purchase_queue:{asset_id}:{calc_method}"
    await redis.delete(redis_key)
    
    # DB에서 미실현 매수 내역 조회
    purchase_transactions = await get_unrealized_purchases(asset_id)
    
    if calc_method in ['FIFO', 'LIFO']:
        # Sorted Set 재구성
        for tx in purchase_transactions:
            purchase_data = {
                "transaction_id": str(tx.id),
                "quantity": str(tx.quantity),
                "price": str(tx.price),
                "remaining": str(tx.remaining_quantity)  # 계산된 남은 수량
            }
            timestamp = tx.transaction_date.timestamp()
            await redis.zadd(redis_key, {json.dumps(purchase_data): timestamp})
            
    elif calc_method == 'AVG':
        # Hash 재구성
        total_quantity = sum(tx.remaining_quantity for tx in purchase_transactions)
        total_cost = sum(tx.remaining_quantity * tx.price for tx in purchase_transactions)
        avg_price = total_cost / total_quantity if total_quantity > 0 else 0
        
        await redis.hmset(redis_key, {
            'total_quantity': str(total_quantity),
            'total_cost': str(total_cost),
            'avg_price': str(avg_price)
        })
```

### 동기화 스케줄링

```python
# 정기 배치 동기화 (Celery 또는 APScheduler 사용)
@scheduler.scheduled_job('cron', hour=2)  # 매일 새벽 2시
async def nightly_sync_job():
    """전체 자산 동기화"""
    assets = await get_all_active_assets()
    
    for asset in assets:
        try:
            await full_sync_asset_to_redis(asset.id)
            logger.info(f"Synced asset {asset.id} to Redis")
        except Exception as e:
            logger.error(f"Failed to sync asset {asset.id}: {e}")

@scheduler.scheduled_job('interval', minutes=10)
async def health_check_redis():
    """Redis 상태 모니터링"""
    try:
        await redis.ping()
        # 샘플 자산의 정합성 검증
        sample_assets = await get_sample_assets(limit=10)
        for asset in sample_assets:
            db_quantity = await calculate_total_quantity_from_db(asset.id)
            redis_quantity = await redis.get(f"asset:{asset.id}:quantity")
            
            if abs(float(redis_quantity or 0) - db_quantity) > 0.00000001:
                logger.warning(f"Quantity mismatch for asset {asset.id}")
                await full_sync_asset_to_redis(asset.id)
                
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
```

---

## 성능 최적화

### Pipeline 사용

```python
async def batch_update_redis(updates: List[dict]):
    """배치 업데이트로 성능 향상"""
    pipe = redis.pipeline()
    
    for update in updates:
        if update['type'] == 'set':
            pipe.set(update['key'], update['value'])
        elif update['type'] == 'incr':
            pipe.incrbyfloat(update['key'], update['amount'])
        elif update['type'] == 'zadd':
            pipe.zadd(update['key'], update['mapping'])
    
    await pipe.execute()
```

### 메모리 최적화

```python
# JSON 압축 저장
import json
import gzip
import base64

def compress_json(data: dict) -> str:
    """JSON 데이터 압축"""
    json_str = json.dumps(data)
    compressed = gzip.compress(json_str.encode())
    return base64.b64encode(compressed).decode()

def decompress_json(compressed_str: str) -> dict:
    """압축된 JSON 데이터 해제"""
    compressed = base64.b64decode(compressed_str.encode())
    json_str = gzip.decompress(compressed).decode()
    return json.loads(json_str)
```

### 모니터링

```python
# Redis 메모리 사용량 모니터링
async def get_redis_memory_info():
    """Redis 메모리 정보 조회"""
    info = await redis.info('memory')
    return {
        'used_memory': info['used_memory'],
        'used_memory_human': info['used_memory_human'],
        'used_memory_peak': info['used_memory_peak'],
        'total_system_memory': info['total_system_memory']
    }

# 큐 크기 모니터링
async def monitor_queue_sizes():
    """매수 큐 크기 모니터링"""
    pattern = "purchase_queue:*"
    keys = await redis.keys(pattern)
    
    queue_info = {}
    for key in keys:
        key_type = await redis.type(key)
        if key_type == 'zset':
            size = await redis.zcard(key)
        elif key_type == 'hash':
            size = await redis.hlen(key)
        else:
            size = await redis.dbsize()  # fallback
            
        queue_info[key] = size
    
    return queue_info
```

---

## 에러 핸들링

### Redis 연결 실패 대응

```python
async def safe_redis_operation(operation, *args, **kwargs):
    """Redis 작업 안전 실행"""
    try:
        return await operation(*args, **kwargs)
    except redis.ConnectionError:
        logger.error("Redis connection lost, falling back to DB")
        # DB에서 계산하는 fallback 로직
        return await fallback_to_db_calculation(*args, **kwargs)
    except redis.TimeoutError:
        logger.warning("Redis timeout, retrying...")
        await asyncio.sleep(0.1)
        return await operation(*args, **kwargs)  # 1회 재시도
```

### 데이터 불일치 복구

```python
async def detect_and_fix_inconsistency(asset_id: str):
    """데이터 불일치 감지 및 복구"""
    
    # DB와 Redis 값 비교
    db_quantity = await calculate_total_quantity_from_db(asset_id)
    redis_quantity_str = await redis.get(f"asset:{asset_id}:quantity")
    redis_quantity = float(redis_quantity_str) if redis_quantity_str else 0.0
    
    tolerance = 0.00000001  # 부동소수점 오차 허용
    
    if abs(db_quantity - redis_quantity) > tolerance:
        logger.warning(f"Inconsistency detected for asset {asset_id}")
        logger.warning(f"DB: {db_quantity}, Redis: {redis_quantity}")
        
        # Redis를 DB 값으로 수정
        await redis.set(f"asset:{asset_id}:quantity", str(db_quantity))
        
        # 매수 큐도 재구성 (전역 기본 계산 방식 사용)
        calc_method = 'FIFO'
        await rebuild_purchase_queue(asset_id, calc_method)
        
        return True  # 수정됨
    
    return False  # 정상
```

---

## 보안 고려사항

- Redis AUTH 설정 필수
- TLS 연결 사용 권장
- 민감한 거래 정보는 암호화하여 저장
- Redis 메모리 덤프 파일 보안 관리