"""
Asset API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.database import get_db
from app.api.auth import get_current_user
from app.core.redis import get_asset_balance, get_asset_price, calculate_and_update_balance
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
    price = 1.0 if db_asset.asset_type == AssetType.CASH.value else get_asset_price(db_asset.id)
    
    # 응답 객체 생성
    asset_dict = {  
        "id": db_asset.id,
        "user_id": db_asset.user_id,
        "account_id": db_asset.account_id,
        "name": db_asset.name,
        "asset_type": db_asset.asset_type,
        "symbol": db_asset.symbol,
        "currency": db_asset.currency,
        "asset_metadata": db_asset.asset_metadata,
        "is_active": db_asset.is_active,
        "created_at": db_asset.created_at,
        "updated_at": db_asset.updated_at,
        "balance": balance,
        "price": price
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
        price = 1.0 if asset.asset_type == AssetType.CASH.value else get_asset_price(asset.id)
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
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
            "balance": balance,
            "price": price,
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
        total_cost = 0
        total_realized_profit = 0
        total_current_value = 0
        
        from sqlalchemy import func
        
        for asset in assets:
            # 거래 집계
            summary_query = db.query(
                func.sum(Transaction.quantity).label('total_quantity'),
                func.sum(Transaction.realized_profit).label('total_realized_profit')
            ).filter(
                Transaction.asset_id == asset.id,
                Transaction.is_confirmed == True
            ).first()
            
            current_quantity = summary_query.total_quantity or 0
            realized_profit = summary_query.total_realized_profit or 0
            
            # 취득원가 계산 (매수 거래만)
            cost_query = db.query(
                func.sum(Transaction.quantity * Transaction.price + 
                        Transaction.fee + Transaction.tax)
            ).filter(
                Transaction.asset_id == asset.id,
                Transaction.type == 'exchange',
                Transaction.quantity > 0,
                Transaction.is_confirmed == True
            ).scalar()
            
            asset_cost = cost_query or 0
            
            # 현재가는 외부 API에서 가져와야 하므로 임시로 0 설정
            current_value = 0
            unrealized_profit = 0
            
            asset_summary = AssetSummary(
                asset_id=asset.id,
                asset_name=asset.name,
                asset_type=AssetType(asset.asset_type),
                symbol=asset.symbol,
                current_quantity=current_quantity,
                total_cost=asset_cost,
                realized_profit=realized_profit,
                unrealized_profit=unrealized_profit,
                current_value=current_value
            )
            
            asset_summaries.append(asset_summary)
            total_cost += asset_cost
            total_realized_profit += realized_profit
            total_current_value += current_value
        
        total_unrealized_profit = total_current_value - total_cost
        
        return PortfolioSummary(
            total_assets_value=total_current_value,
            total_cash=0,  # 현금은 별도 계산 필요
            total_realized_profit=total_realized_profit,
            total_unrealized_profit=total_unrealized_profit,
            asset_summaries=asset_summaries
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 조회 중 오류 발생: {str(e)}"
        )


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
    price = 1.0 if asset.asset_type == AssetType.CASH.value else get_asset_price(asset.id)
    
    # 응답 객체 생성
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
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
        "balance": balance,
        "price": price,
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
    price = 1.0 if asset.asset_type == AssetType.CASH.value else get_asset_price(asset.id)
    
    # 응답 객체 생성
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
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
        "balance": balance,
        "price": price
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
    
    # 거래 집계
    from sqlalchemy import func
    summary_query = db.query(
        func.sum(Transaction.quantity).label('total_quantity'),
        func.sum(Transaction.realized_profit).label('total_realized_profit')
    ).filter(
        Transaction.asset_id == asset_id,
        Transaction.is_confirmed == True
    ).first()
    
    current_quantity = summary_query.total_quantity or 0
    realized_profit = summary_query.total_realized_profit or 0
    
    # 취득원가 계산 (매수 거래만)
    cost_query = db.query(
        func.sum(Transaction.quantity * Transaction.price + Transaction.fee + Transaction.tax)
    ).filter(
        Transaction.asset_id == asset_id,
        Transaction.type == 'exchange',
        Transaction.quantity > 0,
        Transaction.is_confirmed == True
    ).scalar()
    
    total_cost = cost_query or 0
    
    # 현재가는 외부 API에서 가져와야 하므로 임시로 0 설정
    current_value = 0
    unrealized_profit = 0
    
    return AssetSummary(
        asset_id=asset.id,
        asset_name=asset.name,
        asset_type=AssetType(asset.asset_type),
        symbol=asset.symbol,
        current_quantity=current_quantity,
        total_cost=total_cost,
        realized_profit=realized_profit,
        unrealized_profit=unrealized_profit,
        current_value=current_value
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