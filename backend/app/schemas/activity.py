"""
Pydantic schemas for Activity (댓글 + 로그)
"""

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional
from datetime import datetime
from app.models import TargetType, ActivityType


class ActivityCreate(BaseModel):
    """활동 생성 스키마"""
    target_type: TargetType = Field(..., description="대상 엔티티 타입")
    target_id: str = Field(..., description="대상 엔티티 ID")
    activity_type: ActivityType = Field(ActivityType.COMMENT, description="활동 유형")
    content: Optional[str] = Field(None, description="댓글 본문 (comment)")
    payload: Optional[dict] = Field(None, description="로그 데이터 (log)")
    parent_id: Optional[str] = Field(None, description="부모 댓글 ID (스레드)")
    visibility: str = Field("private", description="가시성: private/shared/public")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v, info: ValidationInfo):
        at = info.data.get('activity_type')
        if at == ActivityType.COMMENT:
            if v is None or not str(v).strip():
                raise ValueError("댓글의 content는 비어 있을 수 없습니다")
        return v

    @field_validator('payload')
    @classmethod
    def validate_payload(cls, v, info: ValidationInfo):
        at = info.data.get('activity_type')
        if at == ActivityType.LOG and v is None:
            raise ValueError("로그의 payload는 필수입니다")
        return v

    @field_validator('visibility')
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        v = (v or '').strip()
        if v not in {"private", "shared", "public"}:
            raise ValueError("visibility는 private/shared/public 중 하나여야 합니다")
        return v


class ActivityUpdate(BaseModel):
    """활동 수정 스키마 (댓글 전용)"""
    content: Optional[str] = Field(None, description="댓글 본문")
    visibility: Optional[str] = Field(None, description="가시성: private/shared/public")

    @field_validator('visibility')
    @classmethod
    def validate_visibility(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if v not in {"private", "shared", "public"}:
            raise ValueError("visibility는 private/shared/public 중 하나여야 합니다")
        return v

    @field_validator('content')
    @classmethod
    def validate_content_nonempty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("content는 비어 있을 수 없습니다")
        return v


class ActivityResponse(BaseModel):
    """활동 응답 스키마"""
    id: str
    user_id: str
    target_type: TargetType
    target_id: str
    activity_type: ActivityType
    content: Optional[str]
    payload: Optional[dict]
    parent_id: Optional[str]
    thread_root_id: Optional[str]
    visibility: str
    is_immutable: bool
    is_deleted: bool
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
