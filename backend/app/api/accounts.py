"""
Accounts API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.auth import get_current_user
from app.core.permissions import (
    check_account_permission, 
    get_user_accessible_accounts,
    get_account_role
)
from app.schemas.account import (
    AccountCreate, 
    AccountUpdate, 
    AccountResponse, 
    AccountListResponse,
    AccountShareCreate,
    AccountShareUpdate,
    AccountShareResponse,
    AccountShareListResponse,
    ShareRole
)
from app.models import User, Account, Asset, AccountShare

router = APIRouter()


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED, summary="계좌 생성")
async def create_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    새로운 계좌를 생성합니다.
    
    - 인증 필요: Bearer 토큰
    - **name**: 계좌명 (필수)
    - **account_type**: 계좌 유형 (필수) - bank_account, securities, cash, debit_card, credit_card, savings, deposit, crypto_wallet
    - **provider**: 금융기관/거래소명 (선택)
    - **account_number**: 계좌번호 (선택)
    - **currency**: 통화 코드 (기본값: KRW)
    - **is_active**: 활성화 상태 (기본값: true)
    - **api_config**: API 연동 설정 (선택, JSONB)
    - **daemon_config**: Daemon 설정 (선택, JSONB)
    """
    # 트랜잭션으로 계좌와 현금 자산을 함께 생성
    try:
        # 계좌 생성
        new_account = Account(
            owner_id=current_user.id,
            name=account_data.name,
            account_type=account_data.account_type.value,
            provider=account_data.provider,
            account_number=account_data.account_number,
            currency=account_data.currency,
            is_active=account_data.is_active,
            api_config=account_data.api_config,
            daemon_config=account_data.daemon_config
        )
        
        db.add(new_account)
        db.flush()  # ID를 얻기 위해 flush (commit 전)
        
        # 소유자를 account_shares에 추가
        owner_share = AccountShare(
            account_id=new_account.id,
            user_id=current_user.id,
            role="owner",
            can_read=True,
            can_write=True,
            can_delete=True,
            can_share=True,
            shared_by=current_user.id
        )
        db.add(owner_share)
        
        # 현금 자산 자동 생성
        cash_asset = Asset(
            user_id=current_user.id,
            account_id=new_account.id,
            name=f"{new_account.name}(현금)",
            asset_type="cash",
            currency=new_account.currency,
            asset_metadata={
                "auto_created": True,
                "account_name": new_account.name
            },
            is_active=True
        )
        
        db.add(cash_asset)
        db.commit()
        db.refresh(new_account)
        
        return new_account
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"계좌 및 현금 자산 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("", response_model=AccountListResponse, summary="계좌 목록 조회")
async def get_accounts(
    account_type: Optional[str] = Query(None, description="계좌 유형으로 필터링"),
    is_active: Optional[bool] = Query(None, description="활성화 상태로 필터링"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자가 접근 가능한 모든 계좌 목록을 조회합니다.
    (소유한 계좌 + 공유받은 계좌 포함)
    
    - 인증 필요: Bearer 토큰
    - 쿼리 파라미터로 필터링 가능:
      - **account_type**: 특정 계좌 유형만 조회
      - **is_active**: 활성화된 계좌만 또는 비활성화된 계좌만 조회
    """
    # 권한 검증 헬퍼를 사용하여 접근 가능한 계좌 조회
    accounts = get_user_accessible_accounts(
        db=db,
        user_id=current_user.id,
        account_type=account_type,
        is_active=is_active
    )
    
    return AccountListResponse(
        total=len(accounts),
        accounts=accounts
    )


@router.get("/{account_id}", response_model=AccountResponse, summary="계좌 상세 조회")
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 계좌의 상세 정보를 조회합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 조회할 계좌 ID (UUID)
    - 소유한 계좌 또는 공유받은 계좌 조회 가능
    """
    # 권한 검증 (읽기 권한)
    account = check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_read"
    )
    
    return account


@router.patch("/{account_id}", response_model=AccountResponse, summary="계좌 수정")
async def update_account(
    account_id: str,
    account_data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    계좌 정보를 수정합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 수정할 계좌 ID (UUID)
    - 모든 필드는 선택사항이며, 제공된 필드만 업데이트됩니다
    - 수정 권한(can_write) 필요
    """
    # 권한 검증 (쓰기 권한)
    account = check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_write"
    )
    
    # 업데이트할 필드만 적용
    update_data = account_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "account_type" and value is not None:
            setattr(account, field, value.value)  # Enum 값 추출
        else:
            setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT, summary="계좌 삭제")
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    계좌를 삭제합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 삭제할 계좌 ID (UUID)
    - ⚠️ 관련된 모든 거래 내역도 함께 삭제됩니다 (CASCADE)
    - 삭제 권한(can_delete) 필요
    """
    # 권한 검증 (삭제 권한)
    account = check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_delete"
    )
    
    # 계좌 삭제
    db.delete(account)
    db.commit()
    
    return None


@router.post("/{account_id}/toggle-active", response_model=AccountResponse, summary="계좌 활성화/비활성화")
async def toggle_account_active(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    계좌의 활성화 상태를 토글합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 대상 계좌 ID (UUID)
    - 활성 상태이면 비활성으로, 비활성 상태이면 활성으로 변경
    - 수정 권한(can_write) 필요
    """
    # 권한 검증 (쓰기 권한)
    account = check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_write"
    )
    
    # 활성화 상태 토글
    account.is_active = not account.is_active
    
    db.commit()
    db.refresh(account)
    
    return account


# ==================== 계좌 공유 API ====================

@router.get("/{account_id}/shares", response_model=AccountShareListResponse, summary="계좌 공유 목록 조회")
async def get_account_shares(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 계좌의 공유 목록을 조회합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 계좌 ID (UUID)
    - 읽기 권한 필요
    """
    # 권한 검증 (읽기 권한)
    check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_read"
    )
    
    # 공유 목록 조회
    shares = db.query(AccountShare).filter(
        AccountShare.account_id == account_id
    ).order_by(AccountShare.created_at.desc()).all()
    
    return AccountShareListResponse(
        total=len(shares),
        shares=shares
    )


@router.post("/{account_id}/shares", response_model=AccountShareResponse, status_code=status.HTTP_201_CREATED, summary="계좌 공유 생성")
async def create_account_share(
    account_id: str,
    share_data: AccountShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    계좌를 다른 사용자와 공유합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 계좌 ID (UUID)
    - **user_email**: 공유할 사용자의 이메일
    - **role**: 공유 역할 (owner/editor/viewer)
    - 공유 권한(can_share) 필요
    """
    # 권한 검증 (공유 권한)
    check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_share"
    )
    
    # 공유받을 사용자 조회
    target_user = db.query(User).filter(User.email == share_data.user_email).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"이메일 '{share_data.user_email}'에 해당하는 사용자를 찾을 수 없습니다"
        )
    
    # 자기 자신과 공유 방지
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신과는 계좌를 공유할 수 없습니다"
        )
    
    # 이미 공유되어 있는지 확인
    existing_share = db.query(AccountShare).filter(
        AccountShare.account_id == account_id,
        AccountShare.user_id == target_user.id
    ).first()
    
    if existing_share:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 해당 사용자와 공유된 계좌입니다"
        )
    
    # 역할별 기본 권한 설정
    role_permissions = {
        ShareRole.OWNER: {"can_read": True, "can_write": True, "can_delete": True, "can_share": True},
        ShareRole.EDITOR: {"can_read": True, "can_write": True, "can_delete": False, "can_share": False},
        ShareRole.VIEWER: {"can_read": True, "can_write": False, "can_delete": False, "can_share": False},
    }
    
    permissions = role_permissions[share_data.role]
    
    # 새 공유 생성
    new_share = AccountShare(
        account_id=account_id,
        user_id=target_user.id,
        role=share_data.role.value,
        shared_by=current_user.id,
        **permissions
    )
    
    db.add(new_share)
    db.commit()
    db.refresh(new_share)
    
    return new_share


@router.patch("/{account_id}/shares/{share_id}", response_model=AccountShareResponse, summary="계좌 공유 수정")
async def update_account_share(
    account_id: str,
    share_id: str,
    share_data: AccountShareUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    계좌 공유 권한을 수정합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 계좌 ID (UUID)
    - **share_id**: 공유 ID (UUID)
    - 공유 권한(can_share) 필요
    """
    # 권한 검증 (공유 권한)
    check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_share"
    )
    
    # 공유 조회
    share = db.query(AccountShare).filter(
        AccountShare.id == share_id,
        AccountShare.account_id == account_id
    ).first()
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공유 정보를 찾을 수 없습니다"
        )
    
    # 소유자 역할은 수정 불가
    if share.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소유자의 권한은 변경할 수 없습니다"
        )
    
    # 업데이트
    update_data = share_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "role" and value is not None:
            setattr(share, field, value.value)
        else:
            setattr(share, field, value)
    
    db.commit()
    db.refresh(share)
    
    return share


@router.delete("/{account_id}/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT, summary="계좌 공유 삭제")
async def delete_account_share(
    account_id: str,
    share_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    계좌 공유를 삭제합니다.
    
    - 인증 필요: Bearer 토큰
    - **account_id**: 계좌 ID (UUID)
    - **share_id**: 공유 ID (UUID)
    - 공유 권한(can_share) 필요
    """
    # 권한 검증 (공유 권한)
    check_account_permission(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        required_permission="can_share"
    )
    
    # 공유 조회
    share = db.query(AccountShare).filter(
        AccountShare.id == share_id,
        AccountShare.account_id == account_id
    ).first()
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공유 정보를 찾을 수 없습니다"
        )
    
    # 소유자 역할은 삭제 불가
    if share.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소유자의 공유 정보는 삭제할 수 없습니다"
        )
    
    db.delete(share)
    db.commit()
    
    return None
