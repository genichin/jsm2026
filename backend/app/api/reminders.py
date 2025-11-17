"""
API endpoints for Reminder (알림) operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, Reminder, RemindableType, Asset, Account
from app.schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderSnooze,
    ReminderWithEntity,
    ReminderStats
)
from app.core.reminder_helpers import (
    validate_remindable,
    check_reminder_exists,
    get_entity_name
)


router = APIRouter()


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    reminder_data: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    알림 생성
    
    - 엔티티 존재 여부 및 권한 검증
    - 알림 생성
    """
    # 엔티티 존재 여부 및 권한 검증
    validate_remindable(
        db,
        current_user.id,
        reminder_data.remindable_type,
        reminder_data.remindable_id
    )
    
    # 알림 생성
    reminder = Reminder(
        user_id=current_user.id,
        remindable_type=reminder_data.remindable_type.value,
        remindable_id=reminder_data.remindable_id,
        reminder_type=reminder_data.reminder_type.value,
        title=reminder_data.title,
        description=reminder_data.description,
        remind_at=reminder_data.remind_at,
        repeat_interval=reminder_data.repeat_interval.value if reminder_data.repeat_interval else None,
        priority=reminder_data.priority,
        auto_complete_on_view=reminder_data.auto_complete_on_view
    )
    
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    
    return reminder


@router.get("", response_model=List[ReminderWithEntity])
def get_reminders(
    remindable_type: Optional[RemindableType] = Query(None, description="엔티티 타입 필터"),
    reminder_type: Optional[str] = Query(None, description="알림 유형 필터"),
    is_active: bool = Query(True, description="활성 알림만 조회"),
    include_dismissed: bool = Query(False, description="무시된 알림 포함"),
    include_snoozed: bool = Query(True, description="스누즈된 알림 포함"),
    days_ahead: Optional[int] = Query(None, ge=1, le=365, description="향후 며칠 이내 알림"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    알림 목록 조회
    
    - 사용자별 알림 조회
    - 다양한 필터 옵션 지원
    - 엔티티 이름 포함
    """
    query = db.query(Reminder).filter(Reminder.user_id == current_user.id)
    
    # 필터 적용
    if remindable_type:
        query = query.filter(Reminder.remindable_type == remindable_type.value)
    
    if reminder_type:
        query = query.filter(Reminder.reminder_type == reminder_type)
    
    if is_active:
        query = query.filter(Reminder.is_active == True)
    
    if not include_dismissed:
        query = query.filter(Reminder.is_dismissed == False)
    
    if not include_snoozed:
        now = datetime.utcnow()
        query = query.filter(
            or_(
                Reminder.snoozed_until.is_(None),
                Reminder.snoozed_until <= now
            )
        )
    
    if days_ahead:
        from datetime import timedelta
        future_date = datetime.utcnow() + timedelta(days=days_ahead)
        query = query.filter(Reminder.remind_at <= future_date)
    
    # 정렬 및 페이지네이션
    reminders = query.order_by(
        Reminder.priority.desc(),
        Reminder.remind_at
    ).offset(skip).limit(limit).all()
    
    # 엔티티 이름 추가
    result = []
    for reminder in reminders:
        reminder_dict = ReminderResponse.from_orm(reminder).dict()
        reminder_dict['entity_name'] = get_entity_name(
            db,
            RemindableType(reminder.remindable_type),
            reminder.remindable_id
        )
        result.append(ReminderWithEntity(**reminder_dict))
    
    return result


@router.get("/pending", response_model=List[ReminderWithEntity])
def get_pending_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    대기 중인 알림 조회
    
    - 현재 시각 기준 발송 대기 중인 알림
    - 활성화, 미무시, 스누즈 해제 상태
    """
    now = datetime.utcnow()
    
    reminders = db.query(Reminder).filter(
        Reminder.user_id == current_user.id,
        Reminder.is_active == True,
        Reminder.is_dismissed == False,
        Reminder.remind_at <= now,
        or_(
            Reminder.snoozed_until.is_(None),
            Reminder.snoozed_until <= now
        )
    ).order_by(
        Reminder.priority.desc(),
        Reminder.remind_at
    ).all()
    
    # 엔티티 이름 추가
    result = []
    for reminder in reminders:
        reminder_dict = ReminderResponse.from_orm(reminder).dict()
        reminder_dict['entity_name'] = get_entity_name(
            db,
            RemindableType(reminder.remindable_type),
            reminder.remindable_id
        )
        result.append(ReminderWithEntity(**reminder_dict))
    
    return result


@router.get("/stats", response_model=ReminderStats)
def get_reminder_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    사용자 알림 통계
    
    - 전체/대기/긴급/스누즈 알림 개수
    """
    now = datetime.utcnow()
    
    stats = db.query(
        func.count(Reminder.id).label('total_reminders'),
        func.count(case(
            (and_(
                Reminder.is_dismissed == False,
                Reminder.remind_at <= now,
                or_(
                    Reminder.snoozed_until.is_(None),
                    Reminder.snoozed_until <= now
                )
            ), Reminder.id)
        )).label('pending_reminders'),
        func.count(case((Reminder.priority >= 2, Reminder.id))).label('urgent_reminders'),
        func.count(case(
            (and_(
                Reminder.snoozed_until.isnot(None),
                Reminder.snoozed_until > now
            ), Reminder.id)
        )).label('snoozed_reminders')
    ).filter(
        Reminder.user_id == current_user.id,
        Reminder.is_active == True
    ).first()
    
    return ReminderStats(
        total_reminders=stats.total_reminders or 0,
        pending_reminders=stats.pending_reminders or 0,
        urgent_reminders=stats.urgent_reminders or 0,
        snoozed_reminders=stats.snoozed_reminders or 0
    )


@router.get("/{reminder_id}", response_model=ReminderWithEntity)
def get_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    알림 상세 조회
    
    - auto_complete_on_view가 true인 경우 자동으로 무시 처리
    """
    reminder = check_reminder_exists(db, reminder_id, current_user.id)
    
    # 자동 완료 처리
    if reminder.auto_complete_on_view and not reminder.is_dismissed:
        reminder.is_dismissed = True
        reminder.dismissed_at = datetime.utcnow()
        db.commit()
        db.refresh(reminder)
    
    # 엔티티 이름 추가
    reminder_dict = ReminderResponse.from_orm(reminder).dict()
    reminder_dict['entity_name'] = get_entity_name(
        db,
        RemindableType(reminder.remindable_type),
        reminder.remindable_id
    )
    
    return ReminderWithEntity(**reminder_dict)


@router.patch("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: str,
    reminder_data: ReminderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """알림 수정"""
    reminder = check_reminder_exists(db, reminder_id, current_user.id)
    
    # 필드 업데이트
    update_data = reminder_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == 'reminder_type' and value:
            setattr(reminder, field, value.value)
        elif field == 'repeat_interval' and value:
            setattr(reminder, field, value.value)
        else:
            setattr(reminder, field, value)
    
    reminder.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(reminder)
    
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """알림 삭제"""
    reminder = check_reminder_exists(db, reminder_id, current_user.id)
    
    db.delete(reminder)
    db.commit()
    
    return None


@router.patch("/{reminder_id}/dismiss", response_model=ReminderResponse)
def dismiss_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    알림 무시 처리
    
    - is_dismissed = True
    - dismissed_at = 현재 시각
    """
    reminder = check_reminder_exists(db, reminder_id, current_user.id)
    
    if reminder.is_dismissed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 무시된 알림입니다"
        )
    
    reminder.is_dismissed = True
    reminder.dismissed_at = datetime.utcnow()
    reminder.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(reminder)
    
    return reminder


@router.patch("/{reminder_id}/snooze", response_model=ReminderResponse)
def snooze_reminder(
    reminder_id: str,
    snooze_data: ReminderSnooze,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    알림 스누즈
    
    - snoozed_until 시각까지 알림 발송 중단
    """
    reminder = check_reminder_exists(db, reminder_id, current_user.id)
    
    reminder.snoozed_until = snooze_data.snooze_until
    reminder.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(reminder)
    
    return reminder


@router.get("/entity/{remindable_type}/{remindable_id}", response_model=List[ReminderResponse])
def get_entity_reminders(
    remindable_type: RemindableType,
    remindable_id: str,
    include_dismissed: bool = Query(False, description="무시된 알림 포함"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    특정 엔티티의 알림 조회
    
    - 자산/계좌/거래별 알림 목록
    - 권한 검증 포함
    """
    # 엔티티 존재 여부 및 권한 검증
    validate_remindable(db, current_user.id, remindable_type, remindable_id)
    
    query = db.query(Reminder).filter(
        Reminder.user_id == current_user.id,
        Reminder.remindable_type == remindable_type.value,
        Reminder.remindable_id == remindable_id,
        Reminder.is_active == True
    )
    
    if not include_dismissed:
        query = query.filter(Reminder.is_dismissed == False)
    
    reminders = query.order_by(Reminder.remind_at).all()
    
    return reminders
