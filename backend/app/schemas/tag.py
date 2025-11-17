"""
Tag schemas for request/response validation
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TaggableType(str, Enum):
    """태그 가능한 엔티티 타입"""
    ASSET = "asset"
    ACCOUNT = "account"
    TRANSACTION = "transaction"


class TagCreate(BaseModel):
    """태그 생성 요청"""
    name: str = Field(..., min_length=1, max_length=50, description="태그명")
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="색상 코드 (#RRGGBB)")
    description: Optional[str] = Field(None, description="태그 설명")
    allowed_types: Optional[List[TaggableType]] = Field(
        default=[TaggableType.ASSET, TaggableType.ACCOUNT, TaggableType.TRANSACTION],
        description="사용 가능한 엔티티 타입"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return v.strip()


class TagUpdate(BaseModel):
    """태그 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="태그명")
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="색상 코드")
    description: Optional[str] = Field(None, description="태그 설명")
    allowed_types: Optional[List[TaggableType]] = Field(None, description="사용 가능한 엔티티 타입")


class TagResponse(BaseModel):
    """태그 응답"""
    id: str
    user_id: str
    name: str
    color: Optional[str]
    description: Optional[str]
    allowed_types: List[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    """태그 목록 응답"""
    total: int
    tags: List[TagResponse]


class TagWithStats(TagResponse):
    """통계 정보가 포함된 태그 응답"""
    asset_count: int = 0
    account_count: int = 0
    transaction_count: int = 0
    total_count: int = 0


# ==================== 태그 연결 스키마 ====================

class TaggableCreate(BaseModel):
    """태그 연결 생성 요청"""
    tag_id: str = Field(..., description="태그 ID")
    taggable_type: TaggableType = Field(..., description="엔티티 타입")
    taggable_id: str = Field(..., description="엔티티 ID")


class TaggableBatchCreate(BaseModel):
    """태그 일괄 연결 요청"""
    tag_ids: List[str] = Field(..., description="태그 ID 목록")
    taggable_type: TaggableType = Field(..., description="엔티티 타입")
    taggable_id: str = Field(..., description="엔티티 ID")


class TaggableResponse(BaseModel):
    """태그 연결 응답"""
    id: str
    tag_id: str
    taggable_type: str
    taggable_id: str
    tagged_at: datetime
    tagged_by: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TaggableWithTag(TaggableResponse):
    """태그 정보가 포함된 연결 응답"""
    tag: TagResponse


class TaggableListResponse(BaseModel):
    """태그 연결 목록 응답"""
    total: int
    taggables: List[TaggableResponse]


class EntityTagsResponse(BaseModel):
    """엔티티에 연결된 태그 목록"""
    entity_type: str
    entity_id: str
    tags: List[TagResponse]
    total: int
