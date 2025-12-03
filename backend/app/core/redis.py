"""
Redis client configuration
"""

import redis
from app.core.config import settings

# Redis 클라이언트 초기화
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    decode_responses=True  # 문자열로 자동 디코딩
)


def get_redis():
    """Redis 클라이언트 의존성"""
    return redis_client


def update_asset_balance(asset_id: str, quantity: float) -> None:
    """
    자산 잔고를 Redis에 업데이트
    
    Args:
        asset_id: 자산 ID
        quantity: 현재 보유 수량
    """
    key = f"asset:{asset_id}:balance"
    redis_client.set(key, str(quantity))


def get_asset_balance(asset_id: str) -> float:
    """
    Redis에서 자산 잔고 조회
    
    Args:
        asset_id: 자산 ID
    
    Returns:
        보유 수량 (없으면 0)
    """
    key = f"asset:{asset_id}:balance"
    balance = redis_client.get(key)
    return float(balance) if balance else 0.0


def update_asset_price(asset_id: str, price: float) -> None:
    """
    자산 가격을 Redis에 업데이트
    
    Args:
        asset_id: 자산 ID
        price: 현재 가격
    """
    key = f"asset:{asset_id}:price"
    redis_client.set(key, str(price))


def update_asset_price_by_symbol(symbol: str, price: float) -> None:
    """
    심볼 기반으로 자산 가격을 Redis에 업데이트
    
    Args:
        symbol: 자산 심볼 (예: "005930", "BTC")
        price: 현재 가격
    """
    key = f"asset:{symbol}:price"
    redis_client.set(key, str(price))


def update_asset_change_by_symbol(symbol: str, change_percent: float) -> None:
    """
    심볼 기반으로 자산 가격 변화량을 Redis에 업데이트
    
    Args:
        symbol: 자산 심볼 (예: "005930", "BTC")
        change_percent: 가격 변화량 퍼센트 (예: 2.5, -1.3)
    """
    key = f"asset:{symbol}:change"
    redis_client.set(key, str(change_percent))


def get_asset_price(asset_id: str, symbol: str = None) -> float | None:
    """
    Redis에서 자산 가격 조회
    
    우선순위:
    1) symbol이 있을 때 `asset:{symbol}:price`
    2) 그 외 또는 없을 때 `asset:{asset_id}:price`
    
    Args:
        asset_id: 자산 ID
        symbol: 자산 심볼 (있는 경우 symbol 키를 우선 사용)
    
    Returns:
        가격 (없으면 None)
    """
    # 1차 시도: symbol 우선 (공백/빈 문자열 방지)
    if symbol is not None and str(symbol).strip():
        key_symbol = f"asset:{str(symbol).strip()}:price"
        price_symbol = redis_client.get(key_symbol)
        if price_symbol:
            return float(price_symbol)

    # 2차 시도: asset_id 기반
    key_id = f"asset:{asset_id}:price"
    price_id = redis_client.get(key_id)
    if price_id:
        return float(price_id)

    return None


def get_asset_change(asset_id: str, symbol: str = None) -> float | None:
    """
    Redis에서 자산 가격 변화량 조회 (퍼센트)
    
    우선순위:
    1) symbol이 있을 때 `asset:{symbol}:change`
    2) 그 외 또는 없을 때 `asset:{asset_id}:change`
    
    Args:
        asset_id: 자산 ID
        symbol: 자산 심볼 (있는 경우 symbol 키를 우선 사용)
    
    Returns:
        변화량 퍼센트 (없으면 None)
    """
    # 1차 시도: symbol 우선 (공백/빈 문자열 방지)
    if symbol is not None and str(symbol).strip():
        key_symbol = f"asset:{str(symbol).strip()}:change"
        change_symbol = redis_client.get(key_symbol)
        if change_symbol:
            return float(change_symbol)

    # 2차 시도: asset_id 기반
    key_id = f"asset:{asset_id}:change"
    change_id = redis_client.get(key_id)
    if change_id:
        return float(change_id)

    return None


def delete_asset_price(asset_id: str) -> None:
    """
    Redis에서 자산 가격 삭제
    
    Args:
        asset_id: 자산 ID
    """
    key = f"asset:{asset_id}:price"
    redis_client.delete(key)


def delete_asset_balance(asset_id: str) -> None:
    """
    Redis에서 자산 잔고 삭제
    
    Args:
        asset_id: 자산 ID
    """
    key = f"asset:{asset_id}:balance"
    redis_client.delete(key)


def calculate_and_update_balance(db, asset_id: str) -> float:
    """
    DB에서 거래 내역을 집계하여 자산 잔고를 계산하고 Redis에 업데이트
    
    Args:
        db: 데이터베이스 세션
        asset_id: 자산 ID
    
    Returns:
        계산된 잔고
    """
    from app.models import Transaction
    from sqlalchemy import func
    
    # 모든 확정된 거래의 수량 합계
    total_quantity = db.query(func.sum(Transaction.quantity)).filter(
        Transaction.asset_id == asset_id
    ).scalar() or 0.0
    
    # Redis에 업데이트
    update_asset_balance(asset_id, total_quantity)
    
    return total_quantity


def invalidate_user_cache(user_id: str) -> None:
    """
    사용자 관련 캐시 무효화
    
    Args:
        user_id: 사용자 ID
    """
    # 사용자 요약 캐시 삭제
    pattern = f"user:{user_id}:summary:*"
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
