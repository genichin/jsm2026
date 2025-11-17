"""
계좌 공유 권한 검증 헬퍼
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.models import Account, AccountShare


def check_account_permission(
    db: Session,
    account_id: str,
    user_id: str,
    required_permission: str = "can_read"
) -> Account:
    """
    계좌에 대한 사용자 권한을 확인합니다.
    
    Args:
        db: 데이터베이스 세션
        account_id: 계좌 ID
        user_id: 사용자 ID
        required_permission: 필요한 권한 (can_read, can_write, can_delete, can_share)
    
    Returns:
        Account: 권한이 확인된 계좌 객체
    
    Raises:
        HTTPException: 계좌를 찾을 수 없거나 권한이 없는 경우
    """
    # 1. 계좌가 존재하는지 확인
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="계좌를 찾을 수 없습니다"
        )
    
    # 2. 소유자인 경우 모든 권한 허용
    if account.owner_id == user_id:
        return account
    
    # 3. account_shares에서 권한 확인
    share = db.query(AccountShare).filter(
        AccountShare.account_id == account_id,
        AccountShare.user_id == user_id
    ).first()
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 계좌에 접근 권한이 없습니다"
        )
    
    # 4. 요청된 권한 확인
    if required_permission != "can_read":
        has_permission = getattr(share, required_permission, False)
        if not has_permission:
            permission_names = {
                "can_write": "수정",
                "can_delete": "삭제",
                "can_share": "공유"
            }
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"이 계좌에 대한 {permission_names.get(required_permission, '해당')} 권한이 없습니다"
            )
    
    return account


def get_user_accessible_accounts(
    db: Session,
    user_id: str,
    account_type: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    사용자가 접근 가능한 모든 계좌를 조회합니다.
    (소유한 계좌 + 공유받은 계좌)
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        account_type: 계좌 유형 필터
        is_active: 활성화 상태 필터
    
    Returns:
        계좌 목록
    """
    # 기본 쿼리: 소유한 계좌 또는 공유받은 계좌
    query = db.query(Account).outerjoin(
        AccountShare,
        Account.id == AccountShare.account_id
    ).filter(
        or_(
            Account.owner_id == user_id,
            AccountShare.user_id == user_id
        )
    )
    
    # 필터 적용
    if account_type:
        query = query.filter(Account.account_type == account_type)
    
    if is_active is not None:
        query = query.filter(Account.is_active == is_active)
    
    # 중복 제거 및 최신순 정렬
    query = query.distinct().order_by(Account.created_at.desc())
    
    return query.all()


def get_account_role(db: Session, account_id: str, user_id: str) -> str:
    """
    계좌에 대한 사용자의 역할을 반환합니다.
    
    Args:
        db: 데이터베이스 세션
        account_id: 계좌 ID
        user_id: 사용자 ID
    
    Returns:
        str: 'owner', 'editor', 'viewer' 또는 None
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        return None
    
    # 소유자인 경우
    if account.owner_id == user_id:
        return "owner"
    
    # account_shares에서 역할 확인
    share = db.query(AccountShare).filter(
        AccountShare.account_id == account_id,
        AccountShare.user_id == user_id
    ).first()
    
    return share.role if share else None
