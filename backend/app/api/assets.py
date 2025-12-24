"""
Asset API endpoints
"""

from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.database import get_db
from app.api.auth import get_current_user
from app.core.redis import (
    get_asset_balance,
    get_asset_price,
    get_asset_change,
    calculate_and_update_balance,
    update_asset_price,
    update_asset_price_by_symbol,
    update_asset_change_by_symbol,
    set_asset_need_trade,
    get_asset_need_trade,
    get_asset_avg_data,
)
from app.models import User, Asset, Transaction, Account, Tag, Taggable
from app.core.tag_helpers import (
    validate_taggable_exists,
    validate_tag_allowed_type,
    get_entity_tags,
)
from app.schemas.transaction import (
    AssetCreate, AssetUpdate, AssetResponse, AssetListResponse, AssetFilter,
    PortfolioSummary, AssetSummary, AssetType
)
from app.schemas.tag import (
    EntityTagsResponse,
    TaggableListResponse,
)

router = APIRouter()

# 간단한 잔고 응답 모델 (재계산 엔드포인트용)
from pydantic import BaseModel

class AssetBalanceResponse(BaseModel):
    asset_id: str
    balance: float


class AssetTagsBatch(BaseModel):
    """자산에 연결/갱신할 태그 ID 목록"""
    tag_ids: List[str]


class AssetNeedTradeUpdate(BaseModel):
    """수동 거래 필요 정보 업데이트 바디"""
    price: float
    quantity: float


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """새 자산 생성"""
    
    # 계좌 소유권 확인
    account = db.query(Account).filter(
        Account.id == asset.account_id,
        Account.owner_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="계좌를 찾을 수 없습니다"
        )
    
    # 자산 생성
    db_asset = Asset(
        user_id=current_user.id,
        account_id=asset.account_id,
        name=asset.name,
        asset_type=asset.asset_type.value,
        symbol=asset.symbol,
        market=asset.market,
        currency=asset.currency,
        asset_metadata=asset.asset_metadata,
        is_active=asset.is_active
    )
    
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    
    # Redis에서 잔고와 가격 조회
    balance = get_asset_balance(db_asset.id)

    # db_asset.asset_type 이 현금인 경우 가격은 항상 1.0 으로 설정
    price = 1.0 if db_asset.asset_type == AssetType.CASH.value else get_asset_price(db_asset.id, db_asset.symbol)
    change = None if db_asset.asset_type == AssetType.CASH.value else get_asset_change(db_asset.id, db_asset.symbol)
    
    # 응답 객체 생성
    asset_dict = {  
        "id": db_asset.id,
        "user_id": db_asset.user_id,
        "account_id": db_asset.account_id,
        "name": db_asset.name,
        "asset_type": db_asset.asset_type,
        "symbol": db_asset.symbol,
        "market": db_asset.market,
        "currency": db_asset.currency,
        "asset_metadata": db_asset.asset_metadata,
        "is_active": db_asset.is_active,
        "created_at": db_asset.created_at,
        "updated_at": db_asset.updated_at,
        "balance": balance,
        "price": price,
        "change": change
    }
    
    return asset_dict


@router.get("", response_model=AssetListResponse)
async def list_assets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    account_id: Optional[str] = Query(None),
    asset_type: Optional[AssetType] = Query(None),
    is_active: Optional[bool] = Query(None),
    symbol: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산 목록 조회"""
    
    query = db.query(Asset).options(joinedload(Asset.account)).filter(Asset.user_id == current_user.id)
    
    # 필터 적용
    if account_id:
        query = query.filter(Asset.account_id == account_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type.value)
    if is_active is not None:
        query = query.filter(Asset.is_active == is_active)
    if symbol:
        query = query.filter(Asset.symbol.ilike(f"%{symbol}%"))
    if search:
        # Search in name, symbol, or account name
        query = query.outerjoin(Asset.account).filter(
            or_(
                Asset.name.ilike(f"%{search}%"),
                Asset.symbol.ilike(f"%{search}%"),
                Account.name.ilike(f"%{search}%")
            )
        )
    
    # 페이지네이션
    total = query.count()
    offset = (page - 1) * size
    items = query.offset(offset).limit(size).all()
    
    # 각 자산에 Redis 잔고와 가격 추가
    items_with_balance = []
    for asset in items:
        balance = get_asset_balance(asset.id)
        # db_asset.asset_type 이 현금인 경우 가격은 항상 1.0 으로 설정
        price = 1.0 if asset.asset_type == AssetType.CASH.value else get_asset_price(asset.id, asset.symbol)
        change = None if asset.asset_type == AssetType.CASH.value else get_asset_change(asset.id, asset.symbol)
        need_trade = get_asset_need_trade(asset.id)
        asset_dict = {
            "id": asset.id,
            "user_id": asset.user_id,
            "account_id": asset.account_id,
            "name": asset.name,
            "asset_type": asset.asset_type,
            "symbol": asset.symbol,
            "market": asset.market,
            "currency": asset.currency,
            "asset_metadata": asset.asset_metadata,
            "is_active": asset.is_active,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
            "balance": balance,
            "price": price,
            "change": change,
            "need_trade": need_trade,
            "account": {
                "id": asset.account.id,
                "name": asset.account.name,
                "account_type": asset.account.account_type,
            } if asset.account else None,
        }
        items_with_balance.append(asset_dict)
    
    return AssetListResponse(
        items=items_with_balance,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.put("/{asset_id}/need_trade")
async def update_asset_need_trade(
    asset_id: str,
    payload: AssetNeedTradeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산의 수동 거래 필요 정보를 Redis에 저장 (TTL=600초)

    - Redis Keys:
      - asset:{asset_id}:need_trade:price
      - asset:{asset_id}:need_trade:quantity
    """
    # 소유권 확인 및 자산 존재 확인
    db_asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id,
    ).first()
    if not db_asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="자산을 찾을 수 없습니다")

    # Redis 저장 (TTL 600초)
    set_asset_need_trade(asset_id=asset_id, price=float(payload.price), quantity=float(payload.quantity), ttl_seconds=600)

    return {
        "asset_id": asset_id,
        "need_trade": {
            "price": float(payload.price),
            "quantity": float(payload.quantity),
            "ttl": 600,
        },
        "updated": True,
    }


@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary(
    account_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 요약 정보 조회"""
    
    try:
        # 기본 쿼리 - 사용자의 활성 자산들
        asset_query = db.query(Asset).filter(
            Asset.user_id == current_user.id,
            Asset.is_active == True
        )
        
        # 계좌 필터 적용
        if account_id:
            asset_query = asset_query.filter(Asset.account_id == account_id)
        
        assets = asset_query.all()
        
        # 각 자산의 요약 정보 계산
        asset_summaries = []
        from decimal import Decimal
        total_cost = Decimal(0)
        total_realized_profit = Decimal(0)
        total_current_value = Decimal(0)

        from sqlalchemy import func
        
        for asset in assets:
            # 거래 집계 (기본값)
            summary_query = db.query(
                func.sum(Transaction.quantity).label('total_quantity')
            ).filter(
                Transaction.asset_id == asset.id
            ).first()

            current_quantity = Decimal(summary_query.total_quantity or 0)
            # 자산별 실현손익: 거래 이력 기반 계산 (AVG 원가 방식)
            realized_profit = _calculate_realized_profit(db, asset.id)
            
            # 총취득원가: DB AVG 방식 계산
            asset_cost = _calculate_asset_cost(db, asset.id)

            # Redis 가격 기반 현재가 계산
            price = get_asset_price(asset.id, asset.symbol)
            current_value = Decimal(0)
            if price is not None:
                current_value = Decimal(current_quantity) * Decimal(str(price))
            unrealized_profit = Decimal(0)
            
            asset_summary = AssetSummary(
                asset_id=asset.id,
                asset_name=asset.name,
                asset_type=AssetType(asset.asset_type),
                symbol=asset.symbol,
                current_quantity=float(current_quantity),
                total_cost=float(asset_cost),
                realized_profit=float(realized_profit),
                unrealized_profit=float(unrealized_profit),
                current_value=float(current_value),
            )
            
            asset_summaries.append(asset_summary)
            total_cost += asset_cost
            total_realized_profit += realized_profit
            total_current_value += current_value
        
        total_unrealized_profit = Decimal(total_current_value) - Decimal(total_cost)
        
        return PortfolioSummary(
            total_assets_value=float(total_current_value),
            total_cash=float(Decimal(0)),  # 현금은 별도 계산 필요
            total_realized_profit=float(total_realized_profit),
            total_unrealized_profit=float(total_unrealized_profit),
            asset_summaries=asset_summaries
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 조회 중 오류 발생: {str(e)}"
        )


# ============================================================
# 자산 검토 관련 엔드포인트
# ============================================================

@router.get("/review-pending", response_model=List[AssetResponse])
async def get_assets_pending_review(
    limit: int = Query(10, ge=1, le=100, description="조회할 자산 개수"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    검토가 필요한 자산 목록 조회 (오래된 순)
    
    - 한 번도 검토하지 않은 자산 우선
    - 다음 검토 예정일이 도래한 자산
    - 오래된 순서로 정렬
    """
    from sqlalchemy import func, case
    from datetime import datetime, timezone
    
    query = (
        db.query(Asset)
        .filter(
            Asset.user_id == current_user.id,
            Asset.is_active == True,
            or_(
                Asset.last_reviewed_at.is_(None),  # 한 번도 검토 안 함
                Asset.next_review_date <= datetime.now(timezone.utc)  # 검토 기한 도래
            )
        )
        .order_by(
            # 한 번도 검토 안 한 자산 우선 (NULL이 먼저 오도록)
            case((Asset.last_reviewed_at.is_(None), 0), else_=1).asc(),
            # 그 다음 오래된 순
            Asset.last_reviewed_at.asc().nullsfirst()
        )
        .limit(limit)
    )
    
    assets = query.all()
    
    # Redis 데이터 추가
    result = []
    for asset in assets:
        asset_dict = {
            "id": asset.id,
            "user_id": asset.user_id,
            "account_id": asset.account_id,
            "name": asset.name,
            "asset_type": asset.asset_type,
            "symbol": asset.symbol,
            "currency": asset.currency,
            "asset_metadata": asset.asset_metadata,
            "is_active": asset.is_active,
            "review_interval_days": asset.review_interval_days,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
            "last_reviewed_at": asset.last_reviewed_at,
            "next_review_date": asset.next_review_date,
            "balance": get_asset_balance(asset.id),
            "price": get_asset_price(asset.id),
            "change": get_asset_change(asset.id),
        }
        result.append(AssetResponse(**asset_dict))
    
    return result


@router.post("/{asset_id}/mark-reviewed", response_model=AssetResponse)
async def mark_asset_reviewed(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    자산을 검토 완료로 표시
    
    - last_reviewed_at을 현재 시각으로 업데이트
    - next_review_date는 last_reviewed_at + review_interval_days로 계산
    """
    from datetime import datetime, timezone, timedelta
    
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="자산을 찾을 수 없습니다")
    
    now = datetime.now(timezone.utc)
    asset.last_reviewed_at = now
    
    # next_review_date 계산 (트리거가 없는 환경을 위해 수동 계산)
    if asset.review_interval_days:
        asset.next_review_date = now + timedelta(days=asset.review_interval_days)
    
    db.commit()
    db.refresh(asset)
    
    # Redis 데이터 추가
    asset_dict = {
        "id": asset.id,
        "user_id": asset.user_id,
        "account_id": asset.account_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "symbol": asset.symbol,
        "currency": asset.currency,
        "asset_metadata": asset.asset_metadata,
        "is_active": asset.is_active,
        "review_interval_days": asset.review_interval_days,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
        "last_reviewed_at": asset.last_reviewed_at,
        "next_review_date": asset.next_review_date,
        "balance": get_asset_balance(asset.id),
        "price": get_asset_price(asset.id),
        "change": get_asset_change(asset.id),
    }
    
    return AssetResponse(**asset_dict)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산 상세 조회"""
    
    asset = db.query(Asset).options(joinedload(Asset.account)).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )
    
    # Redis에서 잔고와 가격 조회
    balance = get_asset_balance(asset.id)
    # db_asset.asset_type 이 현금인 경우 가격은 항상 1.0 으로 설정
    price = 1.0 if asset.asset_type == AssetType.CASH.value else get_asset_price(asset.id, asset.symbol)
    change = None if asset.asset_type == AssetType.CASH.value else get_asset_change(asset.id, asset.symbol)
    
    # need_trade 조회 (TTL 포함)
    need_trade = get_asset_need_trade(asset.id)

    # 응답 객체 생성
    asset_dict = {
        "id": asset.id,
        "user_id": asset.user_id,
        "account_id": asset.account_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "symbol": asset.symbol,
        "market": asset.market,
        "currency": asset.currency,
        "asset_metadata": asset.asset_metadata,
        "is_active": asset.is_active,
        "review_interval_days": asset.review_interval_days,
        "last_reviewed_at": asset.last_reviewed_at,
        "next_review_date": asset.next_review_date,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
        "balance": balance,
        "price": price,
        "change": change,
        "need_trade": need_trade,
        "account": {
            "id": asset.account.id,
            "name": asset.account.name,
            "account_type": asset.account.account_type,
        } if asset.account else None,
    }
    
    return asset_dict


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    asset_update: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산 정보 수정"""
    
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )
    
    # 업데이트할 필드만 적용
    update_data = asset_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    db.commit()
    db.refresh(asset)
    
    # Redis에서 잔고와 가격 조회
    balance = get_asset_balance(asset.id)
    # db_asset.asset_type 이 현금인 경우 가격은 항상 1.0 으로 설정
    price = 1.0 if asset.asset_type == AssetType.CASH.value else get_asset_price(asset.id, asset.symbol)
    change = None if asset.asset_type == AssetType.CASH.value else get_asset_change(asset.id, asset.symbol)
    
    # 응답 객체 생성
    asset_dict = {
        "id": asset.id,
        "user_id": asset.user_id,
        "account_id": asset.account_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "symbol": asset.symbol,
        "market": asset.market,
        "currency": asset.currency,
        "asset_metadata": asset.asset_metadata,
        "is_active": asset.is_active,
        "review_interval_days": asset.review_interval_days,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
        "last_reviewed_at": asset.last_reviewed_at,
        "next_review_date": asset.next_review_date,
        "balance": balance,
        "price": price,
        "change": change
    }
    
    return asset_dict


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산 삭제"""
    
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )
    
    # 관련 거래가 있는지 확인
    transaction_count = db.query(Transaction).filter(
        Transaction.asset_id == asset_id
    ).count()
    
    if transaction_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="거래 내역이 있는 자산은 삭제할 수 없습니다"
        )
    
    db.delete(asset)
    db.commit()


@router.put("/{asset_id}/price", status_code=status.HTTP_200_OK)
async def update_asset_price_endpoint(
    asset_id: str,
    price: float = Query(..., description="현재 가격"),
    change: float = Query(None, description="가격 변화량 (퍼센트)"),
    use_symbol: bool = Query(False, description="심볼 기반으로 업데이트 (동일 심볼 자산 모두 적용)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산 가격 업데이트 (Redis)"""
    
    # 자산 소유권 확인
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )
    
    # 가격 업데이트
    if use_symbol and asset.symbol:
        # 심볼 기반 업데이트 (동일 심볼 자산 모두 적용)
        update_asset_price_by_symbol(asset.symbol, price)
        if change is not None:
            update_asset_change_by_symbol(asset.symbol, change)
    else:
        # 개별 자산 업데이트
        update_asset_price(asset_id, price)
        if change is not None:
            key = f"asset:{asset_id}:change"
            from app.core.redis import redis_client
            redis_client.set(key, str(change))
    
    return {
        "message": "가격이 업데이트되었습니다",
        "asset_id": asset_id,
        "symbol": asset.symbol,
        "price": price,
        "change": change,
        "use_symbol": use_symbol
    }


def _calculate_asset_cost(db: Session, asset_id: str) -> Decimal:
    """
    자산의 총취득원가를 AVG 방식으로 계산
    
    - 매수 거래(buy, deposit): 수량 × 단가 + 수수료 + 세금 누적
    - 매도 거래(sell, withdraw): 평균단가 기준으로 원가 차감
    
    Args:
        db: 데이터베이스 세션
        asset_id: 자산 ID
    
    Returns:
        Decimal: 총취득원가
    """
    txs = db.query(Transaction).filter(
        Transaction.asset_id == asset_id
    ).order_by(Transaction.transaction_date.asc()).all()
    
    if not txs:
        return Decimal(0)
    
    q_remain = Decimal(0)  # 보유 수량
    cost_remain = Decimal(0)  # 남은 취득원가
    
    for tx in txs:
        qty = Decimal(str(tx.quantity or 0))
        price = Decimal(str(tx.price)) if tx.price is not None else Decimal(0)
        fee = Decimal(str(tx.fee)) if tx.fee is not None else Decimal(0)
        tax = Decimal(str(tx.tax)) if tx.tax is not None else Decimal(0)
        
        if qty > 0:
            # ✅ 매수/유입: 취득원가 누적
            acquisition_cost = qty * price + fee + tax
            cost_remain += acquisition_cost
            q_remain += qty
        
        elif qty < 0:
            # ✅ 매도/유출: 평균단가 기준으로 원가 차감
            if q_remain > 0:
                avg_cost_per_unit = cost_remain / q_remain
                reduce_qty = -qty  # 음수를 양수로 변환
                reduction = reduce_qty * avg_cost_per_unit
                cost_remain = max(Decimal(0), cost_remain - reduction)
            
            q_remain += qty  # qty는 음수
    
    return max(Decimal(0), cost_remain)


def _calculate_realized_profit(db: Session, asset_id: str) -> Decimal:
    """
    자산의 누적 실현손익을 거래 이력으로 계산 (AVG 원가 기준)

    - 매수/유입: 원가와 수량만 갱신
    - 매도/유출: (매도가-수수료-세금)*수량 - 평균원가*수량 을 누적
    """
    txs = db.query(Transaction).filter(
        Transaction.asset_id == asset_id
    ).order_by(Transaction.transaction_date.asc()).all()

    if not txs:
        return Decimal(0)

    q_remain = Decimal(0)
    cost_remain = Decimal(0)
    realized = Decimal(0)

    for tx in txs:
        qty = Decimal(str(tx.quantity or 0))
        price = Decimal(str(tx.price)) if tx.price is not None else Decimal(0)
        fee = Decimal(str(tx.fee)) if tx.fee is not None else Decimal(0)
        tax = Decimal(str(tx.tax)) if tx.tax is not None else Decimal(0)

        if qty > 0:
            # 매수/유입: 원가 누적
            acquisition_cost = qty * price + fee + tax
            cost_remain += acquisition_cost
            q_remain += qty
        elif qty < 0:
            sell_qty = -qty
            if q_remain > 0 and sell_qty > 0:
                avg_cost_per_unit = cost_remain / q_remain
                proceeds = sell_qty * price - fee - tax
                cost_basis = sell_qty * avg_cost_per_unit
                realized += proceeds - cost_basis
                # 보유 원가 감소 및 수량 감소
                cost_remain = max(Decimal(0), cost_remain - cost_basis)
            q_remain += qty  # qty는 음수

    return realized


@router.get("/{asset_id}/summary", response_model=AssetSummary)
async def get_asset_summary(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 자산의 요약 정보 조회"""
    
    # 자산 소유권 확인
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )
    
    from sqlalchemy import func
    
    # 1️⃣ 현재 수량: 모든 거래(확정+미확정)의 수량 합계
    summary_query = db.query(
        func.coalesce(func.sum(Transaction.quantity), 0).label('total_quantity')
    ).filter(
        Transaction.asset_id == asset_id
    ).first()
    
    current_quantity = Decimal(str(summary_query.total_quantity or 0))
    
    # 2️⃣ 실현손익: 매도 거래의 realized_profit 합계
    # 실현손익: 거래 이력 기반 계산 (AVG 원가 방식)
    realized_profit = _calculate_realized_profit(db, asset_id)
    
    # 3️⃣ 총취득원가: DB 거래로 AVG 방식 계산
    total_cost = _calculate_asset_cost(db, asset_id)
    
    # 4️⃣ 현재가 및 평가액 계산
    price = None
    try:
        price = get_asset_price(asset.id, asset.symbol)
    except Exception:
        price = None
    
    foreign_value = None
    foreign_currency = None
    krw_value = None
    unrealized_profit = Decimal(0)
    
    if price is not None and current_quantity > 0:
        # 기준 통화 평가액
        base_value = current_quantity * Decimal(str(price))
        
        # 통화별 처리
        if asset.currency and asset.currency.upper() != "KRW":
            foreign_value = base_value
            foreign_currency = asset.currency.upper()
            # 환율 조회 (Redis: asset:{currency}:price)
            try:
                fx_rate = get_asset_price(asset.id, foreign_currency)
            except Exception:
                fx_rate = None
            
            if fx_rate is not None:
                krw_value = base_value * Decimal(str(fx_rate))
        else:
            # KRW 통화
            krw_value = base_value
        
        # 미실현손익 = 현재가 평가액 - 취득원가
        if total_cost > 0:
            unrealized_profit = base_value - total_cost
    
    return AssetSummary(
        asset_id=asset.id,
        asset_name=asset.name,
        asset_type=AssetType(asset.asset_type),
        symbol=asset.symbol,
        current_quantity=float(current_quantity),
        total_cost=float(total_cost),
        realized_profit=float(realized_profit),
        unrealized_profit=float(unrealized_profit),
        current_value=float(krw_value) if krw_value else None,
        foreign_value=float(foreign_value) if foreign_value else None,
        foreign_currency=foreign_currency,
        krw_value=float(krw_value) if krw_value else None
    )


@router.post("/{asset_id}/recalculate-balance", response_model=AssetBalanceResponse, status_code=status.HTTP_200_OK)
async def recalculate_asset_balance(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산의 잔고를 DB 거래 내역으로 재집계 후 Redis에 반영하고 반환.

    사용 시나리오:
      - 거래 대량 업로드 후 강제 동기화
      - Redis 캐시 불일치 의심 시 수동 재계산
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )

    try:
        new_balance = calculate_and_update_balance(db, asset_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"잔고 재계산 중 오류: {str(e)}"
        )

    return AssetBalanceResponse(asset_id=asset_id, balance=new_balance)


# ==================== Asset Tagging ====================

@router.get("/{asset_id}/tags", response_model=EntityTagsResponse, summary="자산에 연결된 태그 조회")
async def list_asset_tags(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 자산에 연결된 태그 목록을 조회합니다."""
    # 자산 존재/권한 확인
    validate_taggable_exists(db, "asset", asset_id, current_user.id)

    tags = get_entity_tags(db, "asset", asset_id, current_user.id)
    return EntityTagsResponse(
        entity_type="asset",
        entity_id=asset_id,
        tags=tags,
        total=len(tags),
    )


@router.post("/{asset_id}/tags", response_model=TaggableListResponse, status_code=status.HTTP_201_CREATED, summary="자산에 태그 연결")
async def attach_tags_to_asset(
    asset_id: str,
    payload: AssetTagsBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산에 하나 이상의 태그를 연결합니다."""
    # 자산 존재/권한 확인
    validate_taggable_exists(db, "asset", asset_id, current_user.id)

    created: List[Taggable] = []
    for tag_id in payload.tag_ids:
        # 태그 타입 허용 여부 확인
        validate_tag_allowed_type(db, tag_id, "asset", current_user.id)

        # 중복 연결 방지
        exists = db.query(Taggable).filter(
            Taggable.tag_id == tag_id,
            Taggable.taggable_type == "asset",
            Taggable.taggable_id == asset_id,
        ).first()
        if exists:
            continue

        link = Taggable(
            tag_id=tag_id,
            taggable_type="asset",
            taggable_id=asset_id,
            tagged_by=current_user.id,
        )
        db.add(link)
        created.append(link)

    db.commit()
    for link in created:
        db.refresh(link)

    return TaggableListResponse(total=len(created), taggables=created)


@router.delete("/{asset_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, summary="자산에서 태그 제거")
async def detach_tag_from_asset(
    asset_id: str,
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """자산에서 특정 태그 연결을 해제합니다."""
    # 자산 존재/권한 확인
    validate_taggable_exists(db, "asset", asset_id, current_user.id)

    # 본인 소유 태그 + 해당 자산에 연결된 레코드만 삭제 허용
    link = db.query(Taggable).join(Tag, Tag.id == Taggable.tag_id).filter(
        Taggable.taggable_type == "asset",
        Taggable.taggable_id == asset_id,
        Taggable.tag_id == tag_id,
        Tag.user_id == current_user.id,
    ).first()

    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="태그 연결을 찾을 수 없습니다")

    db.delete(link)
    db.commit()

    return None
