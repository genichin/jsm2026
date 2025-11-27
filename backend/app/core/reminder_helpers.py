"""
Helper functions for Reminder (알림) operations
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import Optional, List
from dateutil.relativedelta import relativedelta

from app.models import (
    Reminder, RemindableType, RepeatInterval,
    Asset, Account, Transaction, AccountShare
)


def validate_remindable(
    db: Session,
    user_id: str,
    remindable_type: RemindableType,
    remindable_id: str
) -> bool:
    """
    엔티티 존재 여부 및 권한 검증
    
    Args:
        db: Database session
        user_id: 사용자 ID
        remindable_type: 엔티티 타입
        remindable_id: 엔티티 ID
    
    Returns:
        bool: 검증 성공 여부
    
    Raises:
        HTTPException: 엔티티를 찾을 수 없거나 권한이 없는 경우
    """
    if remindable_type == RemindableType.ASSET:
        # 자산 소유자 확인
        entity = db.query(Asset).filter(
            Asset.id == remindable_id,
            Asset.user_id == user_id
        ).first()
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"자산 {remindable_id}를 찾을 수 없거나 접근 권한이 없습니다"
            )
    
    elif remindable_type == RemindableType.ACCOUNT:
        # 계좌 소유자 또는 공유받은 사용자 확인
        entity = db.query(Account).join(AccountShare).filter(
            Account.id == remindable_id,
            AccountShare.user_id == user_id
        ).first()
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"계좌 {remindable_id}를 찾을 수 없거나 접근 권한이 없습니다"
            )
    
    elif remindable_type == RemindableType.TRANSACTION:
        # 거래의 자산 소유자 확인
        entity = db.query(Transaction).join(Asset).filter(
            Transaction.id == remindable_id,
            Asset.user_id == user_id
        ).first()
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"거래 {remindable_id}를 찾을 수 없거나 접근 권한이 없습니다"
            )
    
    return True


def calculate_next_reminder_time(
    current_time: datetime,
    interval: RepeatInterval
) -> datetime:
    """
    반복 알림의 다음 시간 계산
    
    Args:
        current_time: 현재 알림 시각
        interval: 반복 주기
    
    Returns:
        datetime: 다음 알림 시각
    """
    if interval == RepeatInterval.DAILY:
        return current_time + timedelta(days=1)
    
    elif interval == RepeatInterval.WEEKLY:
        return current_time + timedelta(weeks=1)
    
    elif interval == RepeatInterval.MONTHLY:
        # 정확한 월 단위 계산 (dateutil 사용)
        return current_time + relativedelta(months=1)
    
    elif interval == RepeatInterval.YEARLY:
        # 정확한 년 단위 계산 (윤년 고려)
        return current_time + relativedelta(years=1)
    
    return current_time


def get_entity_name(
    db: Session,
    remindable_type: RemindableType,
    remindable_id: str
) -> Optional[str]:
    """
    엔티티 이름 조회
    
    Args:
        db: Database session
        remindable_type: 엔티티 타입
        remindable_id: 엔티티 ID
    
    Returns:
        Optional[str]: 엔티티 이름 (없으면 None)
    """
    try:
        if remindable_type == RemindableType.ASSET:
            entity = db.query(Asset).filter(Asset.id == remindable_id).first()
            return entity.name if entity else None
        
        elif remindable_type == RemindableType.ACCOUNT:
            entity = db.query(Account).filter(Account.id == remindable_id).first()
            return entity.name if entity else None
        
        elif remindable_type == RemindableType.TRANSACTION:
            entity = db.query(Transaction).filter(
                Transaction.id == remindable_id
            ).first()
            return entity.description if entity else None
        
    except Exception:
        return None
    
    return None


def check_reminder_exists(
    db: Session,
    reminder_id: str,
    user_id: str
) -> Reminder:
    """
    알림 존재 여부 및 소유권 확인
    
    Args:
        db: Database session
        reminder_id: 알림 ID
        user_id: 사용자 ID
    
    Returns:
        Reminder: 알림 객체
    
    Raises:
        HTTPException: 알림을 찾을 수 없거나 소유자가 아닌 경우
    """
    reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == user_id
    ).first()
    
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"알림 {reminder_id}를 찾을 수 없거나 접근 권한이 없습니다"
        )
    
    return reminder


def get_due_reminders(
    db: Session,
    limit: int = 1000
) -> List[Reminder]:
    """
    발송 대기 중인 알림 조회 (배치 작업용)
    
    Args:
        db: Database session
        limit: 최대 조회 개수
    
    Returns:
        List[Reminder]: 발송 대기 알림 목록
    """
    now = datetime.utcnow()
    
    reminders = db.query(Reminder).filter(
        Reminder.is_active == True,
        Reminder.is_dismissed == False,
        Reminder.remind_at <= now,
        # 스누즈 중이 아니거나 스누즈가 끝난 경우
        (Reminder.snoozed_until.is_(None)) | (Reminder.snoozed_until <= now),
        # 아직 발송되지 않았거나, 마지막 발송이 알림 시각 이전인 경우
        (Reminder.last_notified_at.is_(None)) | (Reminder.last_notified_at < Reminder.remind_at)
    ).order_by(
        Reminder.priority.desc(),
        Reminder.remind_at
    ).limit(limit).all()
    
    return reminders


def update_reminder_after_notification(
    db: Session,
    reminder: Reminder
) -> None:
    """
    알림 발송 후 상태 업데이트
    
    Args:
        db: Database session
        reminder: 알림 객체
    """
    now = datetime.utcnow()
    
    # 반복 알림인 경우 다음 시간 계산
    if reminder.repeat_interval:
        next_time = calculate_next_reminder_time(
            reminder.remind_at,
            RepeatInterval(reminder.repeat_interval)
        )
        reminder.remind_at = next_time
    
    # 마지막 발송 시각 업데이트
    reminder.last_notified_at = now
    reminder.updated_at = now
    
    db.commit()
