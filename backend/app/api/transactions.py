"""
Transaction API endpoints
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, and_, or_, func
import pandas as pd
import io
from pathlib import Path

from app.core.database import get_db
from app.api.auth import get_current_user
from app.core.redis import calculate_and_update_balance, invalidate_user_cache
from app.models import User, Asset, AssetTransaction, Account, Category
from app.services.auto_category import auto_assign_category
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionResponse, TransactionWithAsset,
    TransactionListResponse, TransactionFilter, BulkTransactionCreate, BulkTransactionResponse,
    PortfolioSummary, AssetSummary, AssetType, TransactionType,
    FileUploadError, FileUploadResponse
)
from app.schemas.transaction import ExchangeCreate, BulkTransactionResponse as ExchangeResponse
from app.services.file_parser import parse_transaction_file

def find_cash_asset_in_account(db: Session, user_id: str, account_id: str):
    """계좌 내 현금 자산 찾기"""
    return db.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.account_id == account_id,
        Asset.asset_type == 'cash'
    ).first()

def create_linked_cash_transaction(db: Session, asset_transaction: AssetTransaction, cash_asset: Asset, description: str):
    """매수/매도와 연결된 현금 거래 생성"""
    
    # 매수: 현금 감소, 매도: 현금 증가
    is_buy = asset_transaction.type == 'buy'
    is_sell = asset_transaction.type == 'sell'
    
    if not (is_buy or is_sell):
        return None
        
    # 거래 금액 계산
    trade_amount = abs(asset_transaction.quantity) * asset_transaction.price
    
    if is_buy:
        # 매수: 현금 출금 (거래금액 + 수수료 + 세금)
        cash_quantity = -1 * (trade_amount + asset_transaction.fee + asset_transaction.tax)
        transaction_type = 'withdraw'
    else:
        # 매도: 현금 입금 (거래금액 - 수수료 - 세금)  
        cash_quantity = trade_amount - asset_transaction.fee - asset_transaction.tax
        transaction_type = 'deposit'
    
    # 현금 거래 생성
    cash_transaction = AssetTransaction(
        asset_id=cash_asset.id,
        type=transaction_type,
        quantity=cash_quantity,
        price=1.0,  # 현금은 항상 단가 1
        fee=0,  # 현금 거래에는 별도 수수료 없음
        tax=0,  # 현금 거래에는 별도 세금 없음
        realized_profit=0,
        transaction_date=asset_transaction.transaction_date,
        description=description,
        memo=f"연결거래: {asset_transaction.id}",
        related_transaction_id=asset_transaction.id,
        is_confirmed=asset_transaction.is_confirmed,
        external_id=asset_transaction.external_id
    )
    
    return cash_transaction

def create_cash_asset_if_needed(db: Session, user_id: str, account_id: str):
    """현금 자산이 없으면 자동 생성"""
    
    # 계좌 정보 조회
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.owner_id == user_id
    ).first()
    
    if not account:
        return None
    
    # 현금 자산 생성
    cash_asset = Asset(
        user_id=user_id,
        account_id=account_id,
        name=f"{account.name}(현금)",
        asset_type='cash',
        symbol=None,
        currency='KRW',
        asset_metadata={},
        is_active=True
    )
    
    db.add(cash_asset)
    db.commit()
    db.refresh(cash_asset)
    
    return cash_asset

router = APIRouter()


def serialize_transaction(tx: AssetTransaction):
    """단일 거래 직렬화 (카테고리 dict 포함)"""
    category_summary = None
    if getattr(tx, 'category_id', None) and getattr(tx, 'category', None):
        # relationship 객체가 dict로 기대되는 스키마에 맞게 변환
        category_summary = {
            "id": tx.category.id,
            "name": tx.category.name,
            "flow_type": tx.category.flow_type
        }
    return {
        "id": tx.id,
        "asset_id": tx.asset_id,
        "related_transaction_id": tx.related_transaction_id,
        "category_id": getattr(tx, 'category_id', None),
        "category": category_summary,
        "type": tx.type,
        "quantity": tx.quantity,
        "price": tx.price,
        "fee": tx.fee,
        "tax": tx.tax,
        "realized_profit": tx.realized_profit,
        "transaction_date": tx.transaction_date,
        "description": tx.description,
        "memo": tx.memo,
        "is_confirmed": tx.is_confirmed,
        "external_id": tx.external_id,
        "transaction_metadata": tx.transaction_metadata,
        "created_at": tx.created_at,
        "updated_at": tx.updated_at,
    }


@router.post("/exchange", response_model=ExchangeResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange(
    payload: ExchangeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """환전 거래 생성 (출발/도착 자산에 쌍 레코드 생성)

    - 두 자산 모두 현금(cash) 자산이어야 함
    - 출발 거래: quantity = -source_amount, fee = payload.fee, price = 1.0
    - 도착 거래: quantity = +target_amount, fee = 0, price = 1.0
    - 두 거래는 서로의 related_transaction_id로 연결
    """
    if payload.source_asset_id == payload.target_asset_id:
        raise HTTPException(status_code=400, detail="출발 자산과 도착 자산이 동일할 수 없습니다")

    # 자산 소유권 및 타입 검증
    source_asset = db.query(Asset).filter(Asset.id == payload.source_asset_id, Asset.user_id == current_user.id).first()
    target_asset = db.query(Asset).filter(Asset.id == payload.target_asset_id, Asset.user_id == current_user.id).first()

    if not source_asset or not target_asset:
        raise HTTPException(status_code=404, detail="자산을 찾을 수 없습니다")

    if source_asset.asset_type != 'cash' or target_asset.asset_type != 'cash':
        raise HTTPException(status_code=400, detail="환전은 현금 자산 간에만 가능합니다")

    # 같은 계좌 제약: 환전은 동일 계좌 내에서만 허용
    if source_asset.account_id != target_asset.account_id:
        raise HTTPException(status_code=400, detail="환전은 같은 계좌 내에서만 가능합니다")

    # 거래 생성
    source_tx = AssetTransaction(
        asset_id=source_asset.id,
        type='exchange',
        quantity=-abs(float(payload.source_amount)),
        price=1.0,
        fee=float(payload.fee or 0),
        tax=0.0,
        realized_profit=0.0,
        transaction_date=payload.transaction_date,
        description=payload.description or f"환전 출발 ({source_asset.currency}→{target_asset.currency})",
        memo=payload.memo,
        is_confirmed=payload.is_confirmed,
        external_id=payload.external_id
    )

    target_tx = AssetTransaction(
        asset_id=target_asset.id,
        type='exchange',
        quantity=abs(float(payload.target_amount)),
        price=1.0,
        fee=0.0,
        tax=0.0,
        realized_profit=0.0,
        transaction_date=payload.transaction_date,
        description=payload.description or f"환전 유입 ({source_asset.currency}→{target_asset.currency})",
        memo=payload.memo,
        is_confirmed=payload.is_confirmed,
        external_id=payload.external_id
    )

    db.add(source_tx)
    db.add(target_tx)
    db.commit()
    db.refresh(source_tx)
    db.refresh(target_tx)

    # 상호 연결
    source_tx.related_transaction_id = target_tx.id
    target_tx.related_transaction_id = source_tx.id
    db.commit()
    db.refresh(source_tx)
    db.refresh(target_tx)

    # 잔고 업데이트 및 캐시 무효화
    calculate_and_update_balance(db, source_asset.id)
    calculate_and_update_balance(db, target_asset.id)
    invalidate_user_cache(current_user.id)

    src_dict = serialize_transaction(source_tx)
    dst_dict = serialize_transaction(target_tx)
    return ExchangeResponse(
        created_count=2,
        transactions=[TransactionResponse.model_validate(src_dict), TransactionResponse.model_validate(dst_dict)],
        errors=[]
    )

# Transaction endpoints
def calculate_realized_profit(db: Session, transaction: TransactionCreate, asset: Asset) -> float:
    """매수/매도 거래의 realized_profit 계산"""
    
    try:
        if transaction.type.value == 'buy':
            # 매수: 수수료와 세금은 즉시 손실
            fee = float(transaction.fee or 0)
            tax = float(transaction.tax or 0)
            return -(fee + tax)
        
        elif transaction.type.value == 'sell':
            # 매도: 간단한 계산 (복잡한 FIFO는 나중에 구현)
            quantity = abs(float(transaction.quantity or 0))
            price = float(transaction.price or 0)
            fee = float(transaction.fee or 0)
            tax = float(transaction.tax or 0)
            
            # 매도 금액 - 수수료 - 세금
            sale_amount = quantity * price
            return sale_amount - fee - tax
        
        else:
            # 기타 거래는 기존 값 유지
            return float(transaction.realized_profit or 0)
            
    except Exception as e:
        # 계산 오류 시 0 반환
        print(f"Error calculating realized profit: {e}")
        return 0.0


def validate_transaction_business_rules(transaction: TransactionCreate, asset: Asset):
    """거래 비즈니스 규칙 검증"""
    
    # 현금 자산의 경우 특정 거래 타입만 허용
    if asset.asset_type == 'cash':
        allowed_cash_types = ['deposit', 'withdraw', 'transfer_in', 'transfer_out', 'interest', 'invest', 'fee', 'adjustment', 'exchange']
        if transaction.type.value not in allowed_cash_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"현금 자산에는 {', '.join(allowed_cash_types)} 거래만 허용됩니다"
            )
    
    # 주식/암호화폐 등 거래 가능한 자산의 경우 매수/매도 허용
    tradeable_types = ['stock', 'crypto', 'etf', 'fund', 'bond']
    if asset.asset_type in tradeable_types:
        if transaction.type.value in ['buy', 'sell', 'dividend']:
            # 매수/매도는 가격이 0보다 커야 함 (배당은 0 허용)
            if transaction.type.value in ['buy', 'sell'] and transaction.price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="매수/매도 거래의 가격은 0보다 커야 합니다"
                )
    else:
        # 거래 불가능한 자산에서 매수/매도 시도시 에러
        if transaction.type.value in ['buy', 'sell', 'dividend']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{asset.asset_type} 자산에는 매수/매도/배당이 허용되지 않습니다"
            )
    
    # 음수 가격/수수료/세금 검증
    if transaction.price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="거래 가격은 음수일 수 없습니다"
        )
    
    if transaction.fee < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수수료는 음수일 수 없습니다"
        )
    
    if transaction.tax < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="세금은 음수일 수 없습니다"
        )


def allowed_category_flow_types_for(tx_type: str) -> set:
    """거래 타입에 허용되는 카테고리 flow_type 집합 반환
    - buy/sell: 투자 또는 중립
    - deposit/interest/dividend: 수입, (입금은 이체도 가능), 중립
    - withdraw/fee: 지출, (출금은 이체도 가능), 중립
    - transfer_in/out: 이체, 중립
    - adjustment: 중립
    기타: 제한 없음 (모든 타입 허용)
    """
    tx_type = (tx_type or "").lower()
    if tx_type in {"buy", "sell"}:
        return {"investment", "neutral"}
    if tx_type in {"deposit", "interest", "dividend"}:
        return {"income", "transfer", "neutral"}
    if tx_type in {"withdraw", "fee"}:
        return {"expense", "transfer", "neutral"}
    if tx_type in {"transfer_in", "transfer_out"}:
        return {"transfer", "neutral"}
    if tx_type in {"exchange"}:
        return {"transfer", "neutral"}
    if tx_type in {"adjustment"}:
        return {"neutral"}
    # 알 수 없는 타입은 검증 생략 (향후 필요 시 추가)
    return {"expense", "income", "transfer", "investment", "neutral"}


def validate_category_flow_type_compatibility(tx_type: str, category: Category):
    """거래 타입과 카테고리 flow_type의 일관성 검증"""
    if not category:
        return
    allowed = allowed_category_flow_types_for(tx_type)
    if category.flow_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"거래 유형 '{tx_type}' 에는 카테고리 flow_type '{category.flow_type}' 를 사용할 수 없습니다. 허용: {', '.join(sorted(allowed))}"
        )

from sqlalchemy.exc import IntegrityError

@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """새 거래 생성"""
    
    # 환전(exchange) 거래 처리
    if transaction.type.value == 'exchange':
        if not transaction.target_asset_id or transaction.target_amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="환전 거래는 target_asset_id와 target_amount가 필수입니다"
            )
        
        # 출발/도착 자산 조회
        source_asset = db.query(Asset).filter(
            Asset.id == transaction.asset_id,
            Asset.user_id == current_user.id
        ).first()
        
        target_asset = db.query(Asset).filter(
            Asset.id == transaction.target_asset_id,
            Asset.user_id == current_user.id
        ).first()
        
        if not source_asset or not target_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="자산을 찾을 수 없습니다"
            )
        
        if source_asset.asset_type != 'cash' or target_asset.asset_type != 'cash':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="환전은 현금 자산 간에만 가능합니다"
            )
        
        if source_asset.account_id != target_asset.account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="환전은 같은 계좌 내에서만 가능합니다"
            )
        
        # 출발 거래 생성
        source_tx = AssetTransaction(
            asset_id=source_asset.id,
            type='exchange',
            quantity=-abs(transaction.quantity),  # 음수
            price=1.0,
            fee=transaction.fee,
            tax=0.0,
            realized_profit=0.0,
            transaction_date=transaction.transaction_date,
            description=transaction.description or f"환전 출발 ({source_asset.currency}→{target_asset.currency})",
            memo=transaction.memo,
            is_confirmed=transaction.is_confirmed,
            external_id=transaction.external_id,
            transaction_metadata=transaction.transaction_metadata
        )
        
        # 도착 거래 생성
        target_tx = AssetTransaction(
            asset_id=target_asset.id,
            type='exchange',
            quantity=abs(transaction.target_amount),  # 양수
            price=1.0,
            fee=0.0,
            tax=0.0,
            realized_profit=0.0,
            transaction_date=transaction.transaction_date,
            description=transaction.description or f"환전 유입 ({source_asset.currency}→{target_asset.currency})",
            memo=transaction.memo,
            is_confirmed=transaction.is_confirmed,
            external_id=transaction.external_id,
            transaction_metadata=transaction.transaction_metadata
        )
        
        db.add(source_tx)
        db.add(target_tx)
        db.flush()  # flush 먼저 (ID 생성)
        
        # 상호 연결
        source_tx.related_transaction_id = target_tx.id
        target_tx.related_transaction_id = source_tx.id
        db.commit()
        
        # 잔고 업데이트 및 캐시 무효화
        calculate_and_update_balance(db, source_asset.id)
        calculate_and_update_balance(db, target_asset.id)
        invalidate_user_cache(current_user.id)
        
        # 최종 조회하여 모든 필드 갱신
        source_tx_final = db.query(AssetTransaction).filter(AssetTransaction.id == source_tx.id).first()
        
        # 출발 거래 응답
        db.refresh(source_tx_final)
        return TransactionResponse.model_validate(serialize_transaction(source_tx_final))
        db.refresh(source_tx)
        return TransactionResponse.model_validate(serialize_transaction(source_tx))
    
    # 자산 소유권 확인
    asset = db.query(Asset).filter(
        Asset.id == transaction.asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )
    
    # 거래 비즈니스 규칙 검증
    validate_transaction_business_rules(transaction, asset)
    
    # 매수/매도의 경우 realized_profit 자동 계산
    calculated_realized_profit = None
    if transaction.type.value in ['buy', 'sell']:
        calculated_realized_profit = calculate_realized_profit(db, transaction, asset)
    else:
        calculated_realized_profit = transaction.realized_profit
    
    # category 소유권 및 flow_type 호환성 검증 (있을 경우)
    chosen_category_id = getattr(transaction, 'category_id', None)
    if not chosen_category_id:
        # 자동 분류 시도 (설명 기반) - 설정 플래그 도입 여지, 현재 항상 시도
        auto_cat_id = auto_assign_category(db, current_user.id, transaction.description or "")
        if auto_cat_id:
            chosen_category_id = auto_cat_id

    if chosen_category_id:
        cat = db.query(Category).filter(Category.id == chosen_category_id).first()
        if not cat or asset.user_id != current_user.id or cat.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
        validate_category_flow_type_compatibility(transaction.type.value, cat)

    # 거래 생성
    db_transaction = AssetTransaction(
        asset_id=transaction.asset_id,
        type=transaction.type.value,
        quantity=transaction.quantity,
        price=transaction.price,
        fee=transaction.fee,
        tax=transaction.tax,
        realized_profit=calculated_realized_profit,
        transaction_date=transaction.transaction_date,
        description=transaction.description,
        memo=transaction.memo,
        related_transaction_id=transaction.related_transaction_id,
        is_confirmed=transaction.is_confirmed,
        external_id=transaction.external_id,
        transaction_metadata=transaction.transaction_metadata,
        category_id=chosen_category_id
    )
    
    db.add(db_transaction)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # DB 제약 위반 등은 400으로 반환
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"거래 생성 제약 위반: {str(e.orig) if hasattr(e, 'orig') else str(e)}")
    db.refresh(db_transaction)
    
    # Redis에 자산 잔고 업데이트
    calculate_and_update_balance(db, transaction.asset_id)
    
    # 사용자 캐시 무효화
    invalidate_user_cache(current_user.id)
    
    # 매수/매도의 경우 현금 자산과 연결된 거래 자동 생성
    if transaction.type.value in ['buy', 'sell']:
        cash_asset = None
        
        # 1. 사용자가 지정한 현금 자산이 있으면 해당 자산 사용
        if transaction.cash_asset_id:
            cash_asset = db.query(Asset).filter(
                Asset.id == transaction.cash_asset_id,
                Asset.user_id == current_user.id,
                Asset.asset_type == 'cash'
            ).first()
            
            if not cash_asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="지정한 현금 자산을 찾을 수 없습니다"
                )
        else:
            # 2. 지정하지 않았으면 같은 계좌의 현금 자산 찾기
            cash_asset = find_cash_asset_in_account(db, current_user.id, asset.account_id)
            
            # 3. 현금 자산이 없으면 자동 생성
            if not cash_asset:
                cash_asset = create_cash_asset_if_needed(db, current_user.id, asset.account_id)
        
        if cash_asset:
            # 연결된 현금 거래 설명 생성
            action = '매수' if transaction.type.value == 'buy' else '매도'
            cash_description = f"{asset.name} {action} - 현금 {'지출' if transaction.type.value == 'buy' else '수령'}"
            
            # 현금 거래 생성
            cash_transaction = create_linked_cash_transaction(
                db, db_transaction, cash_asset, cash_description
            )
            
            if cash_transaction:
                db.add(cash_transaction)
                db.commit()
                db.refresh(cash_transaction)
                
                # 현금 자산 잔고도 Redis에 업데이트
                calculate_and_update_balance(db, cash_asset.id)
                
                # 원래 거래에 related_transaction_id 업데이트
                db_transaction.related_transaction_id = cash_transaction.id
                db.commit()
        else:
            # 계좌를 찾을 수 없는 경우 에러
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="연결된 계좌를 찾을 수 없습니다"
            )
    
    # 배당의 경우 수량이 0이고 가격이 0보다 클 때 현금 자산과 연결된 입금 거래 자동 생성
    if transaction.type.value == 'dividend' and db_transaction.quantity == 0 and db_transaction.price > 0:
        cash_asset = None
        
        # 1. 사용자가 지정한 현금 자산이 있으면 해당 자산 사용
        if transaction.cash_asset_id:
            cash_asset = db.query(Asset).filter(
                Asset.id == transaction.cash_asset_id,
                Asset.user_id == current_user.id,
                Asset.asset_type == 'cash'
            ).first()
            
            if not cash_asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="지정한 현금 자산을 찾을 수 없습니다"
                )
        else:
            # 2. 지정하지 않았으면 같은 계좌의 현금 자산 찾기
            cash_asset = find_cash_asset_in_account(db, current_user.id, asset.account_id)
            
            # 3. 현금 자산이 없으면 자동 생성
            if not cash_asset:
                cash_asset = create_cash_asset_if_needed(db, current_user.id, asset.account_id)
        
        if cash_asset:
            # 현금배당: 현금 거래의 수량 = 배당 거래의 가격 - 세금
            dividend_amount = db_transaction.price - db_transaction.tax
            
            # 연결된 현금 입금 거래 생성
            cash_transaction = AssetTransaction(
                asset_id=cash_asset.id,
                type='deposit',
                quantity=dividend_amount,
                price=1.0,
                fee=0,
                tax=0,
                realized_profit=0,
                transaction_date=db_transaction.transaction_date,
                description=f"{asset.name} 배당금 입금",
                memo=f"연결거래: {db_transaction.id}",
                related_transaction_id=db_transaction.id,
                is_confirmed=db_transaction.is_confirmed,
                external_id=db_transaction.external_id
            )
            
            db.add(cash_transaction)
            db.commit()
            db.refresh(cash_transaction)
            
            # 현금 자산 잔고도 Redis에 업데이트
            calculate_and_update_balance(db, cash_asset.id)
            
            # 원래 거래에 related_transaction_id 업데이트
            db_transaction.related_transaction_id = cash_transaction.id
            db.commit()
        else:
            # 계좌를 찾을 수 없는 경우 에러
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="연결된 계좌를 찾을 수 없습니다"
            )
    
    # 직렬화하여 일관된 응답 스키마 보장 (category dict 포함)
    try:
        # 카테고리 관계 로딩 보장
        db_transaction = db.query(AssetTransaction).options(joinedload(AssetTransaction.category)).get(db_transaction.id)
    except Exception:
        pass
    return TransactionResponse.model_validate(serialize_transaction(db_transaction))


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    asset_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    type: Optional[TransactionType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    is_confirmed: Optional[bool] = Query(None),
    category_id: Optional[str] = Query(None, description="카테고리 ID 필터"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """거래 목록 조회"""
    
    query = db.query(AssetTransaction).join(Asset).filter(
        Asset.user_id == current_user.id
    ).options(
        joinedload(AssetTransaction.asset),
        joinedload(AssetTransaction.category)
    )
    
    # 필터 적용
    if asset_id:
        query = query.filter(AssetTransaction.asset_id == asset_id)
    if account_id:
        query = query.filter(Asset.account_id == account_id)
    if type:
        query = query.filter(AssetTransaction.type == type.value)
    if start_date:
        query = query.filter(AssetTransaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(AssetTransaction.transaction_date <= end_date)
    if is_confirmed is not None:
        query = query.filter(AssetTransaction.is_confirmed == is_confirmed)
    if category_id:
        query = query.filter(AssetTransaction.category_id == category_id)
    
    # 최신 거래 먼저 정렬
    query = query.order_by(desc(AssetTransaction.transaction_date), desc(AssetTransaction.created_at))
    
    # 페이지네이션
    total = query.count()
    offset = (page - 1) * size
    transactions = query.offset(offset).limit(size).all()
    
    # Asset 객체를 dict로 변환
    def serialize_tx(tx: AssetTransaction):
        category_summary = None
        if getattr(tx, 'category_id', None) and getattr(tx, 'category', None):
            category_summary = {
                "id": tx.category.id,
                "name": tx.category.name,
                "flow_type": tx.category.flow_type
            }
        return {
            "id": tx.id,
            "asset_id": tx.asset_id,
            "related_transaction_id": tx.related_transaction_id,
            "category_id": getattr(tx, "category_id", None),
            "category": category_summary,
            "type": tx.type,
            "quantity": tx.quantity,
            "price": tx.price,
            "fee": tx.fee,
            "tax": tx.tax,
            "realized_profit": tx.realized_profit,
            "transaction_date": tx.transaction_date,
            "description": tx.description,
            "memo": tx.memo,
            "is_confirmed": tx.is_confirmed,
            "external_id": tx.external_id,
            "created_at": tx.created_at,
            "updated_at": tx.updated_at,
            "asset": {
                "id": tx.asset.id,
                "name": tx.asset.name,
                "asset_type": tx.asset.asset_type,
                "symbol": tx.asset.symbol,
                "currency": tx.asset.currency,
                "is_active": tx.asset.is_active,
            } if tx.asset else None
        }

    items = [serialize_tx(tx) for tx in transactions]

    return TransactionListResponse(
        items=[TransactionWithAsset.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


# Analytics endpoints (must be before /{transaction_id} to avoid path conflicts)
@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 요약 조회"""
    
    # 사용자의 모든 자산 조회
    assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    ).all()
    
    asset_summaries = []
    total_assets_value = 0
    total_cash = 0
    total_realized_profit = 0
    
    for asset in assets:
        # 각 자산별 거래 집계
        from sqlalchemy import func
        summary_query = db.query(
            func.sum(AssetTransaction.quantity).label('total_quantity'),
            func.sum(AssetTransaction.realized_profit).label('total_realized_profit')
        ).filter(
            AssetTransaction.asset_id == asset.id,
            AssetTransaction.is_confirmed == True
        ).first()
        
        current_quantity = summary_query.total_quantity or 0
        realized_profit = summary_query.total_realized_profit or 0
        
        # 취득원가 계산 (매수 거래만)
        cost_query = db.query(
            func.sum(AssetTransaction.quantity * AssetTransaction.price + AssetTransaction.fee + AssetTransaction.tax)
        ).filter(
            AssetTransaction.asset_id == asset.id,
            AssetTransaction.type == 'exchange',
            AssetTransaction.quantity > 0,
            AssetTransaction.is_confirmed == True
        ).scalar()
        
        total_cost = cost_query or 0
        
        # 현재가는 외부 API에서 가져와야 하므로 임시로 0 설정
        current_value = 0
        unrealized_profit = 0
        
        if asset.asset_type == 'cash':
            total_cash += current_quantity
        else:
            total_assets_value += current_value
        
        total_realized_profit += realized_profit
        
        asset_summaries.append(AssetSummary(
            asset_id=asset.id,
            asset_name=asset.name,
            asset_type=AssetType(asset.asset_type),
            symbol=asset.symbol,
            current_quantity=current_quantity,
            total_cost=total_cost,
            realized_profit=realized_profit,
            unrealized_profit=unrealized_profit,
            current_value=current_value
        ))
    
    return PortfolioSummary(
        total_assets_value=total_assets_value,
        total_cash=total_cash,
        total_realized_profit=total_realized_profit,
        total_unrealized_profit=0,  # 현재가 정보가 있을 때 계산
        asset_summaries=asset_summaries
    )


@router.get(
    "/recent",
    response_model=TransactionListResponse,
    summary="최근 거래 목록 조회",
    description="사용자의 모든 자산에 대한 최근 거래 내역을 페이징하여 조회합니다."
)
async def get_recent_transactions(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    is_confirmed: Optional[bool] = Query(None, description="확정 상태 필터 (true/false/null)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    현재 사용자의 모든 자산에 대한 최근 거래 내역을 시간순으로 조회합니다.
    
    - **page**: 페이지 번호 (1부터 시작)
    - **size**: 페이지당 항목 수 (기본 20, 최대 100)
    - **is_confirmed**: 확정 거래만 필터링 (선택사항)
    """
    try:
        # 사용자 소유 자산 ID 목록 조회
        user_asset_ids = [asset.id for asset in db.query(Asset).filter(Asset.user_id == current_user.id).all()]
        
        if not user_asset_ids:
            # 자산이 없으면 빈 결과 반환
            return TransactionListResponse(
                items=[],
                total=0,
                page=page,
                size=size,
                pages=0
            )
        
        # 거래 내역 쿼리 (자산 정보와 조인)
        query = (
            db.query(AssetTransaction)
            .options(joinedload(AssetTransaction.asset))
            .filter(AssetTransaction.asset_id.in_(user_asset_ids))
        )
        
        # is_confirmed 필터 적용
        if is_confirmed is not None:
            query = query.filter(AssetTransaction.is_confirmed == is_confirmed)
        
        # 최신순 정렬
        query = query.order_by(desc(AssetTransaction.transaction_date), desc(AssetTransaction.id))
        
        # 전체 개수 조회
        total = query.count()
        
        # 페이징 적용
        offset = (page - 1) * size
        transactions = query.offset(offset).limit(size).all()
        
        # 페이지 수 계산
        pages = (total + size - 1) // size if total > 0 else 0
        
        # SQLAlchemy 객체를 dict로 명시적 변환 (asset 관계 포함)
        items = []
        for tx in transactions:
            item = {
                "id": tx.id,
                "asset_id": tx.asset_id,
                "category_id": getattr(tx, "category_id", None),
                "type": tx.type,
                "quantity": tx.quantity,
                "price": tx.price,
                "fee": tx.fee,
                "tax": tx.tax,
                "realized_profit": tx.realized_profit,
                "transaction_date": tx.transaction_date,
                "description": tx.description,
                "memo": tx.memo,
                "is_confirmed": tx.is_confirmed,
                "external_id": tx.external_id,
                "transaction_metadata": tx.transaction_metadata,
                "created_at": tx.created_at,
                "updated_at": tx.updated_at,
                "asset": {
                    "id": tx.asset.id,
                    "name": tx.asset.name,
                    "asset_type": tx.asset.asset_type,
                    "symbol": tx.asset.symbol,
                    "currency": tx.asset.currency,
                    "is_active": tx.asset.is_active,
                } if tx.asset else None
            }
            items.append(item)
        
        return TransactionListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"거래 내역 조회 중 오류: {str(e)}"
        )


@router.get("/{transaction_id}", response_model=TransactionWithAsset)
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """거래 상세 조회"""
    
    transaction = db.query(AssetTransaction).join(Asset).filter(
        AssetTransaction.id == transaction_id,
        Asset.user_id == current_user.id
    ).options(
        joinedload(AssetTransaction.asset),
        joinedload(AssetTransaction.category)
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="거래를 찾을 수 없습니다"
        )
    
    # Asset 객체를 dict로 변환
    category_summary = None
    if getattr(transaction, 'category_id', None) and getattr(transaction, 'category', None):
        category_summary = {
            "id": transaction.category.id,
            "name": transaction.category.name,
            "flow_type": transaction.category.flow_type
        }
    return {
        "id": transaction.id,
        "asset_id": transaction.asset_id,
        "category_id": getattr(transaction, "category_id", None),
        "category": category_summary,
        "type": transaction.type,
        "quantity": transaction.quantity,
        "price": transaction.price,
        "fee": transaction.fee,
        "tax": transaction.tax,
        "realized_profit": transaction.realized_profit,
        "transaction_date": transaction.transaction_date,
        "description": transaction.description,
        "memo": transaction.memo,
        "is_confirmed": transaction.is_confirmed,
        "external_id": transaction.external_id,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
        "asset": {
            "id": transaction.asset.id,
            "name": transaction.asset.name,
            "asset_type": transaction.asset.asset_type,
            "symbol": transaction.asset.symbol,
            "currency": transaction.asset.currency,
            "is_active": transaction.asset.is_active,
        } if transaction.asset else None
    }


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """거래 정보 수정"""
    
    transaction = db.query(AssetTransaction).join(Asset).filter(
        AssetTransaction.id == transaction_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="거래를 찾을 수 없습니다"
        )
    
    # 업데이트할 필드만 적용 (카테고리 변경 포함)
    update_data = transaction_update.model_dump(exclude_unset=True)

    # 카테고리 변경 검증 로직
    if 'category_id' in update_data:
        new_category_id = update_data.get('category_id') or None  # 빈 문자열 처리
        if new_category_id:
            cat = db.query(Category).filter(Category.id == new_category_id).first()
            if not cat or cat.user_id != current_user.id:
                raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
            # 거래 타입과 카테고리 flow_type 호환성 재검증
            validate_category_flow_type_compatibility(transaction.type, cat)
            transaction.category_id = new_category_id
        else:
            # 카테고리 해제 (None 지정)
            transaction.category_id = None
        # 이미 처리했으므로 일반 필드 적용에서 제거
        update_data.pop('category_id', None)

    # 나머지 일반 필드 적용
    for field, value in update_data.items():
        setattr(transaction, field, value)
    
    db.commit()
    # 카테고리 관계를 로드하여 직렬화 시 사용
    transaction = db.query(AssetTransaction).options(joinedload(AssetTransaction.category)).get(transaction.id)
    
    # Redis에 자산 잔고 업데이트
    calculate_and_update_balance(db, transaction.asset_id)
    
    # 사용자 캐시 무효화
    invalidate_user_cache(current_user.id)
    
    # 직렬화하여 응답 (category를 dict로 보장)
    return TransactionResponse.model_validate(serialize_transaction(transaction))


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """거래 삭제"""
    
    transaction = db.query(AssetTransaction).join(Asset).filter(
        AssetTransaction.id == transaction_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="거래를 찾을 수 없습니다"
        )
    
    # 삭제 전에 asset_id 저장
    asset_id = transaction.asset_id
    
    db.delete(transaction)
    db.commit()
    
    # Redis에 자산 잔고 업데이트
    calculate_and_update_balance(db, asset_id)
    
    # 사용자 캐시 무효화
    invalidate_user_cache(current_user.id)


# Bulk operations
@router.post("/bulk", response_model=BulkTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_bulk_transactions(
    bulk_request: BulkTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대량 거래 생성 (복식부기 지원)"""
    
    created_transactions = []
    errors = []
    
    try:
        for i, transaction_data in enumerate(bulk_request.transactions):
            try:
                # 자산 소유권 확인
                asset = db.query(Asset).filter(
                    Asset.id == transaction_data.asset_id,
                    Asset.user_id == current_user.id
                ).first()
                
                if not asset:
                    errors.append(f"거래 {i+1}: 자산을 찾을 수 없습니다")
                    continue
                
                # 거래 생성
                db_transaction = AssetTransaction(
                    asset_id=transaction_data.asset_id,
                    type=transaction_data.type.value,
                    quantity=transaction_data.quantity,
                    price=transaction_data.price,
                    fee=transaction_data.fee,
                    tax=transaction_data.tax,
                    realized_profit=transaction_data.realized_profit,
                    transaction_date=transaction_data.transaction_date,
                    description=transaction_data.description,
                    memo=transaction_data.memo,
                    related_transaction_id=transaction_data.related_transaction_id,
                    is_confirmed=transaction_data.is_confirmed,
                    external_id=transaction_data.external_id
                )
                
                db.add(db_transaction)
                created_transactions.append(db_transaction)
                
            except Exception as e:
                errors.append(f"거래 {i+1}: {str(e)}")
        
        if created_transactions:
            db.commit()
            for transaction in created_transactions:
                db.refresh(transaction)
            
            # Redis에 각 자산 잔고 업데이트 (중복 제거)
            affected_assets = set(t.asset_id for t in created_transactions)
            for asset_id in affected_assets:
                calculate_and_update_balance(db, asset_id)
            
            # 사용자 캐시 무효화
            invalidate_user_cache(current_user.id)
        
        return BulkTransactionResponse(
            created_count=len(created_transactions),
            transactions=created_transactions,
            errors=errors
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"대량 거래 생성 중 오류가 발생했습니다: {str(e)}"
        )


# Asset-specific transaction endpoints
@router.get("/assets/{asset_id}/transactions", response_model=TransactionListResponse)
async def get_asset_transactions(
    asset_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    type: Optional[TransactionType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    category_id: Optional[str] = Query(None, description="카테고리 ID 필터"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 자산의 거래 내역 조회"""
    
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
    
    # 거래 내역 쿼리
    query = db.query(AssetTransaction).filter(AssetTransaction.asset_id == asset_id).options(
        joinedload(AssetTransaction.category)
    )
    
    # 필터 적용
    if type:
        query = query.filter(AssetTransaction.type == type.value)
    if start_date:
        query = query.filter(AssetTransaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(AssetTransaction.transaction_date <= end_date)
    if category_id:
        query = query.filter(AssetTransaction.category_id == category_id)
    
    # 전체 개수 계산
    total = query.count()
    
    # 정렬 및 페이징
    transactions = query.order_by(desc(AssetTransaction.transaction_date))\
                      .offset((page - 1) * size)\
                      .limit(size).all()
    
    # 카테고리 포함 직렬화
    result_items = []
    for tx in transactions:
        category_summary = None
        if getattr(tx, 'category_id', None) and getattr(tx, 'category', None):
            category_summary = {"id": tx.category.id, "name": tx.category.name, "flow_type": tx.category.flow_type}
        result_items.append({
            "id": tx.id,
            "asset_id": tx.asset_id,
            "related_transaction_id": tx.related_transaction_id,
            "category_id": getattr(tx, 'category_id', None),
            "category": category_summary,
            "type": tx.type,
            "quantity": tx.quantity,
            "price": tx.price,
            "fee": tx.fee,
            "tax": tx.tax,
            "realized_profit": tx.realized_profit,
            "transaction_date": tx.transaction_date,
            "description": tx.description,
            "memo": tx.memo,
            "is_confirmed": tx.is_confirmed,
            "external_id": tx.external_id,
            "created_at": tx.created_at,
            "updated_at": tx.updated_at,
        })

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(i) for i in result_items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )

@router.post("/upload", response_model=FileUploadResponse)
async def upload_transactions_file(
    file: UploadFile = File(...),
    asset_id: str = Form(...),
    dry_run: bool = Form(default=False),
    password: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    거래 내역 파일 업로드 (CSV 또는 Excel)
    
    - **file**: CSV 또는 Excel 파일
    - **asset_id**: 자산 ID
    - **dry_run**: true면 미리보기만, false면 실제 저장
    - **password**: Excel 파일 암호 (선택, 암호화된 파일인 경우)
    
    업체별 거래 내역 파일 형식에 맞게 파싱하여 거래 내역을 추가합니다.
    지원하는 파일 형식: CSV (UTF-8, CP949), Excel (암호화 지원)
    지원하는 업체: 토스뱅크, 미래에셋증권, KB증권
    """
    
    # 자산 확인
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="자산을 찾을 수 없습니다"
        )
    
    # 파일 형식 확인
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.csv', '.xlsx', '.xls']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 파일 형식입니다. CSV 또는 Excel 파일만 가능합니다."
        )
    
    try:
        # 파일 읽기
        file_content = await file.read()
        
        # file_parser 서비스로 파일 파싱
        try:
            df = parse_transaction_file(
                file_content=file_content,
                file_extension=file_extension,
                password=password
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # 빈 파일 체크
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일에 데이터가 없습니다"
            )
        
        # 필수 컬럼 체크 (표준 형식으로 변환된 상태)
        required_columns = ['transaction_date', 'type', 'quantity', 'price']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"필수 컬럼이 없습니다: {', '.join(missing_columns)}"
            )
        
        # 거래 파싱 및 검증
        total = len(df)
        created = 0
        skipped = 0
        failed = 0
        errors = []
        preview_data = []
        created_transactions = []
        
        for idx, row in df.iterrows():
            row_num = idx + 2  # 헤더 포함하여 실제 행 번호
            
            try:
                # 거래일 파싱
                transaction_date = pd.to_datetime(row['transaction_date'])
                
                # 거래 유형 검증
                trans_type = str(row['type']).lower().strip()
                valid_types = [t.value for t in TransactionType]
                
                if trans_type not in valid_types:
                    raise ValueError(f"잘못된 거래 유형: {trans_type}. 지원하는 유형: {', '.join(valid_types)}")
                
                # 수량, 단가 검증
                quantity = float(row['quantity'])
                price = float(row['price'])
                fee = float(row.get('fee', 0))
                tax = float(row.get('tax', 0))
                realized_profit = float(row.get('realized_profit', 0))
                
                # 카테고리 매핑 (선택): category_id 또는 category 컬럼 지원
                category_id_value = None
                category_name_value = None
                if 'category_id' in df.columns and pd.notna(row.get('category_id')):
                    cat_id_raw = str(row.get('category_id')).strip()
                    cat_obj = db.query(Category).filter(Category.id == cat_id_raw, Category.user_id == current_user.id).first()
                    if not cat_obj:
                        raise ValueError(f"잘못된 카테고리 ID: {cat_id_raw}")
                    # 거래 타입과 카테고리 flow_type 일관성 검증
                    validate_category_flow_type_compatibility(trans_type, cat_obj)
                    category_id_value = cat_obj.id
                    category_name_value = cat_obj.name
                elif 'category' in df.columns and pd.notna(row.get('category')):
                    cat_name_raw = str(row.get('category')).strip()
                    cat_obj = db.query(Category).filter(Category.user_id == current_user.id, Category.name == cat_name_raw).first()
                    if not cat_obj:
                        raise ValueError(f"카테고리를 찾을 수 없습니다: {cat_name_raw}")
                    # 거래 타입과 카테고리 flow_type 일관성 검증
                    validate_category_flow_type_compatibility(trans_type, cat_obj)
                    category_id_value = cat_obj.id
                    category_name_value = cat_obj.name
                
                # 카테고리가 지정되지 않은 경우 자동 분류 시도 (description 기반)
                if not category_id_value:
                    description_text = str(row.get('description', '')) if pd.notna(row.get('description')) else ""
                    auto_cat_id = auto_assign_category(db, current_user.id, description_text)
                    if auto_cat_id:
                        cat_obj = db.query(Category).filter(Category.id == auto_cat_id).first()
                        if cat_obj:
                            # 거래 타입과 카테고리 flow_type 일관성 검증
                            try:
                                validate_category_flow_type_compatibility(trans_type, cat_obj)
                                category_id_value = auto_cat_id
                                category_name_value = cat_obj.name
                            except HTTPException:
                                # flow_type이 맞지 않으면 자동 분류 스킵
                                pass

                # 거래 데이터 생성
                transaction_data = {
                    'transaction_date': transaction_date.isoformat(),
                    'type': trans_type,
                    'quantity': quantity,
                    'price': price,
                    'fee': fee,
                    'tax': tax,
                    'realized_profit': realized_profit,
                    'description': str(row.get('description', '')) if pd.notna(row.get('description')) else None,
                    'memo': str(row.get('memo', '')) if pd.notna(row.get('memo')) else None,
                    'balance_after': float(row.get('balance_after', 0)) if pd.notna(row.get('balance_after')) else None,
                    'category_id': category_id_value,
                    'category_name': category_name_value,
                }
                
                # dry_run 모드면 미리보기에 추가
                if dry_run:
                    preview_data.append(transaction_data)
                    created += 1
                else:
                    # 실제 저장
                    db_transaction = AssetTransaction(
                        asset_id=asset_id,
                        type=trans_type,
                        quantity=quantity,
                        price=price,
                        fee=fee,
                        tax=tax,
                        realized_profit=realized_profit,
                        transaction_date=transaction_date,
                        description=transaction_data['description'],
                        memo=transaction_data['memo'],
                        is_confirmed=True,
                        category_id=category_id_value
                    )
                    
                    db.add(db_transaction)
                    created += 1
                    
            except ValueError as e:
                failed += 1
                errors.append(FileUploadError(
                    row=row_num,
                    error=str(e),
                    data=row.to_dict()
                ))
            except Exception as e:
                failed += 1
                errors.append(FileUploadError(
                    row=row_num,
                    error=f"처리 중 오류: {str(e)}",
                    data=row.to_dict()
                ))
        
        # 실제 저장 모드일 때 커밋
        if not dry_run and created > 0:
            try:
                db.commit()
                
                # 생성된 거래 조회 (카테고리 관계 포함)
                transactions = db.query(AssetTransaction).filter(
                    AssetTransaction.asset_id == asset_id
                ).options(
                    joinedload(AssetTransaction.category)
                ).order_by(desc(AssetTransaction.created_at)).limit(created).all()
                
                created_transactions = [
                    TransactionResponse.model_validate(serialize_transaction(t)) for t in transactions
                ]
                
                # Redis 캐시 갱신
                calculate_and_update_balance(db, asset_id)
                invalidate_user_cache(current_user.id)
                
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"데이터베이스 저장 실패: {str(e)}"
                )
        
        return FileUploadResponse(
            success=failed == 0,
            total=total,
            created=created,
            skipped=skipped,
            failed=failed,
            errors=errors,
            preview=preview_data if dry_run else None,
            transactions=created_transactions if not dry_run else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 처리 중 오류: {str(e)}"
        )
