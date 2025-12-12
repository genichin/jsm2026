"""
API endpoints for Activities (댓글 + 로그)
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, Activity, ActivityType, TargetType
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse, ActivitiesListResponse
from app.core.activity_helpers import (
    validate_target,
    check_activity_exists,
    ensure_editable_comment,
    soft_delete_comment,
)

router = APIRouter()


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """활동 생성 (댓글/로그)"""
    # 권한/대상 검증
    validate_target(db, current_user.id, data.target_type, data.target_id)

    is_log = data.activity_type == ActivityType.LOG
    # 댓글/로그 상호 배타적 필드 보정
    content = data.content if not is_log else None
    payload = data.payload if is_log else None

    activity = Activity(
        user_id=current_user.id,
        target_type=data.target_type.value,
        target_id=data.target_id,
        activity_type=data.activity_type.value,
        content=content,
        payload=payload,
        parent_id=data.parent_id,
        visibility=data.visibility,
        is_immutable=True if is_log else False,
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.get("", response_model=ActivitiesListResponse)
def list_activities(
    target_type: TargetType = Query(..., description="대상 타입"),
    target_id: str = Query(..., description="대상 ID"),
    activity_type: Optional[ActivityType] = Query(None, description="활동 유형 필터"),
    include_deleted: bool = Query(False, description="삭제된 댓글 포함 여부"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="정렬 순서"),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대상별 활동 목록 (페이지네이션 응답, page/size 지원)"""
    validate_target(db, current_user.id, target_type, target_id)

    query = db.query(Activity).filter(
        Activity.target_type == target_type.value,
        Activity.target_id == target_id,
    )

    if not include_deleted:
        query = query.filter(Activity.is_deleted == False)

    if activity_type:
        query = query.filter(Activity.activity_type == activity_type.value)

    # 총 개수 계산
    total = query.count()

    query = query.order_by(Activity.created_at.asc() if order == 'asc' else Activity.created_at.desc())
    
    # page/size를 skip/limit로 변환
    skip = (page - 1) * size
    items = query.offset(skip).limit(size).all()

    # 총 페이지 수 계산
    pages = (total + size - 1) // size if total > 0 else 0

    return ActivitiesListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = check_activity_exists(db, activity_id)
    # 조회 권한: 대상 엔티티 접근 가능해야 함
    validate_target(db, current_user.id, TargetType(activity.target_type), activity.target_id)
    return activity


@router.get("/thread/{thread_root_id}", response_model=List[ActivityResponse])
def get_thread(
    thread_root_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    root = check_activity_exists(db, thread_root_id)
    # 권한 검증
    validate_target(db, current_user.id, TargetType(root.target_type), root.target_id)

    return db.query(Activity).filter(
        Activity.target_type == root.target_type,
        Activity.target_id == root.target_id,
        Activity.thread_root_id == thread_root_id,
        Activity.is_deleted == False,
    ).order_by(Activity.created_at.asc()).all()


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: str,
    data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = check_activity_exists(db, activity_id)
    ensure_editable_comment(activity, current_user.id)

    update_data = data.dict(exclude_unset=True)
    if 'visibility' in update_data and update_data['visibility'] is not None:
        activity.visibility = update_data['visibility']
    if 'content' in update_data and update_data['content'] is not None:
        activity.content = update_data['content']

    activity.updated_at = datetime.utcnow()
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = check_activity_exists(db, activity_id)
    ensure_editable_comment(activity, current_user.id)

    soft_delete_comment(db, activity)
    db.commit()
    return None
