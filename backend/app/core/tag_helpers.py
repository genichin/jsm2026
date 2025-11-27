"""
태그 관련 헬퍼 함수
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Optional, List
from app.models import Tag, Taggable, Asset, Account, Transaction, User


def validate_taggable_exists(
    db: Session,
    taggable_type: str,
    taggable_id: str,
    user_id: str
) -> bool:
    """
    엔티티가 존재하고 사용자에게 접근 권한이 있는지 확인
    
    Args:
        db: 데이터베이스 세션
        taggable_type: 엔티티 타입 (asset/account/transaction)
        taggable_id: 엔티티 ID
        user_id: 사용자 ID
    
    Returns:
        bool: 존재하고 접근 가능하면 True
    
    Raises:
        HTTPException: 엔티티를 찾을 수 없거나 접근 권한이 없는 경우
    """
    entity = None
    
    if taggable_type == "asset":
        entity = db.query(Asset).filter(
            Asset.id == taggable_id,
            Asset.user_id == user_id
        ).first()
    elif taggable_type == "account":
        # 계좌는 소유자이거나 공유받은 경우 접근 가능
        from app.core.permissions import check_account_permission
        try:
            entity = check_account_permission(
                db=db,
                account_id=taggable_id,
                user_id=user_id,
                required_permission="can_read"
            )
        except HTTPException:
            entity = None
    elif taggable_type == "transaction":
        # 거래는 자산을 통해 사용자 확인
        entity = db.query(Transaction).join(Asset).filter(
            Transaction.id == taggable_id,
            Asset.user_id == user_id
        ).first()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{taggable_type} {taggable_id}를 찾을 수 없거나 접근 권한이 없습니다"
        )
    
    return True


def validate_tag_allowed_type(
    db: Session,
    tag_id: str,
    taggable_type: str,
    user_id: str
) -> bool:
    """
    태그의 allowed_types에 해당 엔티티 타입이 허용되는지 확인
    
    Args:
        db: 데이터베이스 세션
        tag_id: 태그 ID
        taggable_type: 엔티티 타입
        user_id: 사용자 ID
    
    Returns:
        bool: 허용되면 True
    
    Raises:
        HTTPException: 태그를 찾을 수 없거나 타입이 허용되지 않는 경우
    """
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == user_id
    ).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="태그를 찾을 수 없습니다"
        )
    
    allowed_types = tag.allowed_types or ["asset", "account", "transaction"]
    
    if taggable_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이 태그는 {taggable_type}에 사용할 수 없습니다. 허용된 타입: {', '.join(allowed_types)}"
        )
    
    return True


def get_entity_tags(
    db: Session,
    taggable_type: str,
    taggable_id: str,
    user_id: str
) -> List[Tag]:
    """
    특정 엔티티에 연결된 모든 태그 조회
    
    Args:
        db: 데이터베이스 세션
        taggable_type: 엔티티 타입
        taggable_id: 엔티티 ID
        user_id: 사용자 ID
    
    Returns:
        태그 목록
    """
    tags = db.query(Tag).join(Taggable).filter(
        Taggable.taggable_type == taggable_type,
        Taggable.taggable_id == taggable_id,
        Tag.user_id == user_id
    ).order_by(Taggable.tagged_at.desc()).all()
    
    return tags


def get_tags_with_stats(db: Session, user_id: str) -> List[dict]:
    """
    사용자의 모든 태그와 통계 정보 조회
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
    
    Returns:
        태그 목록 (각 태그의 사용 통계 포함)
    """
    from sqlalchemy import func, case
    
    # 태그별 엔티티 개수 집계
    stats = db.query(
        Tag.id,
        Tag.user_id,
        Tag.name,
        Tag.color,
        Tag.description,
        Tag.allowed_types,
        Tag.created_at,
        Tag.updated_at,
        func.count(case((Taggable.taggable_type == 'asset', 1))).label('asset_count'),
        func.count(case((Taggable.taggable_type == 'account', 1))).label('account_count'),
        func.count(case((Taggable.taggable_type == 'transaction', 1))).label('transaction_count'),
        func.count(Taggable.id).label('total_count')
    ).outerjoin(Taggable).filter(
        Tag.user_id == user_id
    ).group_by(
        Tag.id, Tag.user_id, Tag.name, Tag.color, Tag.description, 
        Tag.allowed_types, Tag.created_at, Tag.updated_at
    ).order_by(func.count(Taggable.id).desc()).all()
    
    return stats


def check_tag_exists(
    db: Session,
    tag_id: str,
    user_id: str
) -> Tag:
    """
    태그 존재 여부 확인
    
    Args:
        db: 데이터베이스 세션
        tag_id: 태그 ID
        user_id: 사용자 ID
    
    Returns:
        Tag: 태그 객체
    
    Raises:
        HTTPException: 태그를 찾을 수 없는 경우
    """
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == user_id
    ).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="태그를 찾을 수 없습니다"
        )
    
    return tag
