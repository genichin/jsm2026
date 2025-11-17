"""
Activity helpers: target validation, permissions, and editing rules
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from app.models import (
    Activity,
    ActivityType,
    TargetType,
    Asset,
    Account,
    AccountShare,
    AssetTransaction,
)


def validate_target(db: Session, user_id: str, target_type: TargetType, target_id: str):
    """대상 엔티티 존재 여부 및 접근 권한 검증"""
    if target_type == TargetType.ASSET:
        entity = db.query(Asset).filter(Asset.id == target_id, Asset.user_id == user_id).first()
    elif target_type == TargetType.ACCOUNT:
        entity = (
            db.query(Account)
            .outerjoin(AccountShare, AccountShare.account_id == Account.id)
            .filter(Account.id == target_id)
            .filter((Account.owner_id == user_id) | (AccountShare.user_id == user_id))
            .first()
        )
    else:  # TRANSACTION
        entity = (
            db.query(AssetTransaction)
            .join(Asset, Asset.id == AssetTransaction.asset_id)
            .outerjoin(Account, Account.id == Asset.account_id)
            .outerjoin(AccountShare, AccountShare.account_id == Account.id)
            .filter(AssetTransaction.id == target_id)
            .filter((Asset.user_id == user_id) | (Account.owner_id == user_id) | (AccountShare.user_id == user_id))
            .first()
        )
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대상을 찾을 수 없거나 접근 권한이 없습니다")
    return entity


def check_activity_exists(db: Session, activity_id: str) -> Activity:
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="활동을 찾을 수 없습니다")
    return activity


def ensure_editable_comment(activity: Activity, current_user_id: str):
    if activity.activity_type != ActivityType.COMMENT.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="로그는 수정/삭제할 수 없습니다")
    if activity.is_immutable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이 활동은 불변입니다")
    if activity.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 삭제된 댓글입니다")
    if activity.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인 댓글만 수정/삭제할 수 있습니다")


def soft_delete_comment(db: Session, activity: Activity):
    activity.is_deleted = True
    activity.deleted_at = datetime.utcnow()
    db.add(activity)
