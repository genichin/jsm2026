"""
Pydantic schemas for Reminder (알림)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, UTC
from app.models import RemindableType, ReminderType, RepeatInterval


# ============================================================================
# Reminder Schemas
# ============================================================================

class ReminderCreate(BaseModel):
    """알림 생성 스키마"""
    remindable_type: RemindableType = Field(..., description="알림 대상 엔티티 타입")
    remindable_id: str = Field(..., description="알림 대상 엔티티 ID")
    reminder_type: ReminderType = Field(ReminderType.REVIEW, description="알림 유형")
    title: str = Field(..., min_length=1, max_length=100, description="알림 제목")
    description: Optional[str] = Field(None, description="알림 상세 설명")
    remind_at: datetime = Field(..., description="알림 시각 (UTC)")
    repeat_interval: Optional[RepeatInterval] = Field(None, description="반복 주기")
    priority: int = Field(0, ge=0, le=10, description="우선순위 (0=보통, 1=중요, 2=긴급)")
    auto_complete_on_view: bool = Field(False, description="조회 시 자동 완료")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """제목 검증 및 공백 제거"""
        v = v.strip()
        if not v:
            raise ValueError("알림 제목은 비어 있을 수 없습니다")
        return v


class ReminderUpdate(BaseModel):
    """알림 수정 스키마"""
    reminder_type: Optional[ReminderType] = None
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    remind_at: Optional[datetime] = None
    repeat_interval: Optional[RepeatInterval] = None
    priority: Optional[int] = Field(None, ge=0, le=10)
    auto_complete_on_view: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """제목 검증 및 공백 제거"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("알림 제목은 비어 있을 수 없습니다")
        return v


class ReminderResponse(BaseModel):
    """알림 응답 스키마"""
    id: str
    user_id: str
    remindable_type: RemindableType
    remindable_id: str
    reminder_type: ReminderType
    title: str
    description: Optional[str]
    remind_at: datetime
    repeat_interval: Optional[RepeatInterval]
    priority: int
    is_active: bool
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    snoozed_until: Optional[datetime]
    last_notified_at: Optional[datetime]
    auto_complete_on_view: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class ReminderSnooze(BaseModel):
    """알림 스누즈 스키마"""
    snooze_until: datetime = Field(..., description="스누즈 종료 시각 (UTC)")

    @field_validator('snooze_until')
    @classmethod
    def validate_snooze_time(cls, v: datetime) -> datetime:
        """스누즈 시각이 현재 시각 이후인지 검증"""
        # timezone-aware datetime으로 변환하여 비교
        now = datetime.now(UTC)
        # v가 naive datetime이면 UTC로 간주
        if v.tzinfo is None:
            v_aware = v.replace(tzinfo=UTC)
        else:
            v_aware = v
        
        if v_aware <= now:
            raise ValueError("스누즈 시각은 현재 시각 이후여야 합니다")
        return v


class ReminderWithEntity(ReminderResponse):
    """엔티티 정보 포함 알림 응답"""
    entity_name: Optional[str] = Field(None, description="엔티티 이름 (자산/계좌)")

    model_config = {
        "from_attributes": True
    }


class ReminderStats(BaseModel):
    """사용자 알림 통계"""
    total_reminders: int = Field(..., description="전체 알림 개수")
    pending_reminders: int = Field(..., description="대기 중 알림 개수")
    urgent_reminders: int = Field(..., description="긴급 알림 개수 (priority >= 2)")
    snoozed_reminders: int = Field(..., description="스누즈 중 알림 개수")
    
    model_config = {
        "from_attributes": True
    }
