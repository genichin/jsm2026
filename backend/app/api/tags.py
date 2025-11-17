"""
Tags API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.core.tag_helpers import (
    validate_taggable_exists,
    validate_tag_allowed_type,
    get_entity_tags,
    get_tags_with_stats,
    check_tag_exists
)
from app.schemas.tag import (
    TagCreate,
    TagUpdate,
    TagResponse,
    TagListResponse,
    TagWithStats,
    TaggableCreate,
    TaggableBatchCreate,
    TaggableResponse,
    TaggableWithTag,
    TaggableListResponse,
    EntityTagsResponse,
    TaggableType
)
from app.models import User, Tag, Taggable

router = APIRouter()


# ==================== 태그 관리 API ====================

@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED, summary="태그 생성")
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    새로운 태그를 생성합니다.
    
    - 인증 필요: Bearer 토큰
    - **name**: 태그명 (필수, 사용자별 고유)
    - **color**: 색상 코드 (선택, #RRGGBB 형식)
    - **description**: 태그 설명 (선택)
    - **allowed_types**: 사용 가능한 엔티티 타입 (선택)
    """
    # 이름 중복 확인
    existing = db.query(Tag).filter(
        Tag.user_id == current_user.id,
        Tag.name == tag_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{tag_data.name}' 태그가 이미 존재합니다"
        )
    
    # allowed_types를 JSON 형식으로 변환
    allowed_types_json = [t.value for t in tag_data.allowed_types] if tag_data.allowed_types else ["asset", "account", "transaction"]
    
    new_tag = Tag(
        user_id=current_user.id,
        name=tag_data.name,
        color=tag_data.color,
        description=tag_data.description,
        allowed_types=allowed_types_json
    )
    
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    
    return new_tag


@router.get("", response_model=TagListResponse, summary="태그 목록 조회")
async def get_tags(
    include_stats: bool = Query(False, description="통계 정보 포함 여부"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자의 모든 태그를 조회합니다.
    
    - 인증 필요: Bearer 토큰
    - **include_stats**: true일 경우 각 태그의 사용 통계 포함
    """
    if include_stats:
        tags_with_stats = get_tags_with_stats(db, current_user.id)
        return TagListResponse(
            total=len(tags_with_stats),
            tags=[TagWithStats(**tag._asdict()) for tag in tags_with_stats]
        )
    else:
        tags = db.query(Tag).filter(
            Tag.user_id == current_user.id
        ).order_by(Tag.created_at.desc()).all()
        
        return TagListResponse(
            total=len(tags),
            tags=tags
        )


@router.get("/{tag_id}", response_model=TagResponse, summary="태그 상세 조회")
async def get_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 태그의 상세 정보를 조회합니다.
    
    - 인증 필요: Bearer 토큰
    - **tag_id**: 태그 ID (UUID)
    """
    tag = check_tag_exists(db, tag_id, current_user.id)
    return tag


@router.patch("/{tag_id}", response_model=TagResponse, summary="태그 수정")
async def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    태그 정보를 수정합니다.
    
    - 인증 필요: Bearer 토큰
    - **tag_id**: 태그 ID (UUID)
    - 모든 필드는 선택사항이며, 제공된 필드만 업데이트됩니다
    """
    tag = check_tag_exists(db, tag_id, current_user.id)
    
    # 이름 변경 시 중복 확인
    if tag_data.name and tag_data.name != tag.name:
        existing = db.query(Tag).filter(
            Tag.user_id == current_user.id,
            Tag.name == tag_data.name
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{tag_data.name}' 태그가 이미 존재합니다"
            )
    
    # 업데이트
    update_data = tag_data.model_dump(exclude_unset=True)
    
    # allowed_types 변환
    if 'allowed_types' in update_data and update_data['allowed_types']:
        update_data['allowed_types'] = [t.value for t in update_data['allowed_types']]
    
    for field, value in update_data.items():
        setattr(tag, field, value)
    
    db.commit()
    db.refresh(tag)
    
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, summary="태그 삭제")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    태그를 삭제합니다.
    
    - 인증 필요: Bearer 토큰
    - **tag_id**: 태그 ID (UUID)
    - ⚠️ 해당 태그가 연결된 모든 엔티티에서 태그가 제거됩니다
    """
    tag = check_tag_exists(db, tag_id, current_user.id)
    
    db.delete(tag)
    db.commit()
    
    return None


# ==================== 태그 연결 API ====================

@router.post("/attach", response_model=TaggableResponse, status_code=status.HTTP_201_CREATED, summary="태그 연결")
async def attach_tag(
    taggable_data: TaggableCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    엔티티에 태그를 연결합니다.
    
    - 인증 필요: Bearer 토큰
    - **tag_id**: 태그 ID
    - **taggable_type**: 엔티티 타입 (asset/account/transaction)
    - **taggable_id**: 엔티티 ID
    """
    # 검증
    validate_tag_allowed_type(db, taggable_data.tag_id, taggable_data.taggable_type.value, current_user.id)
    validate_taggable_exists(db, taggable_data.taggable_type.value, taggable_data.taggable_id, current_user.id)
    
    # 이미 연결되어 있는지 확인
    existing = db.query(Taggable).filter(
        Taggable.tag_id == taggable_data.tag_id,
        Taggable.taggable_type == taggable_data.taggable_type.value,
        Taggable.taggable_id == taggable_data.taggable_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 해당 엔티티에 태그가 연결되어 있습니다"
        )
    
    # 연결 생성
    new_taggable = Taggable(
        tag_id=taggable_data.tag_id,
        taggable_type=taggable_data.taggable_type.value,
        taggable_id=taggable_data.taggable_id,
        tagged_by=current_user.id
    )
    
    db.add(new_taggable)
    db.commit()
    db.refresh(new_taggable)
    
    return new_taggable


@router.post("/attach-batch", response_model=TaggableListResponse, status_code=status.HTTP_201_CREATED, summary="태그 일괄 연결")
async def attach_tags_batch(
    batch_data: TaggableBatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    엔티티에 여러 태그를 일괄 연결합니다.
    
    - 인증 필요: Bearer 토큰
    - **tag_ids**: 태그 ID 목록
    - **taggable_type**: 엔티티 타입
    - **taggable_id**: 엔티티 ID
    """
    # 엔티티 존재 확인
    validate_taggable_exists(db, batch_data.taggable_type.value, batch_data.taggable_id, current_user.id)
    
    created_taggables = []
    
    for tag_id in batch_data.tag_ids:
        # 검증
        validate_tag_allowed_type(db, tag_id, batch_data.taggable_type.value, current_user.id)
        
        # 이미 연결되어 있으면 스킵
        existing = db.query(Taggable).filter(
            Taggable.tag_id == tag_id,
            Taggable.taggable_type == batch_data.taggable_type.value,
            Taggable.taggable_id == batch_data.taggable_id
        ).first()
        
        if existing:
            continue
        
        # 연결 생성
        new_taggable = Taggable(
            tag_id=tag_id,
            taggable_type=batch_data.taggable_type.value,
            taggable_id=batch_data.taggable_id,
            tagged_by=current_user.id
        )
        
        db.add(new_taggable)
        created_taggables.append(new_taggable)
    
    db.commit()
    
    for taggable in created_taggables:
        db.refresh(taggable)
    
    return TaggableListResponse(
        total=len(created_taggables),
        taggables=created_taggables
    )


@router.delete("/detach/{taggable_id}", status_code=status.HTTP_204_NO_CONTENT, summary="태그 연결 해제")
async def detach_tag(
    taggable_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    엔티티에서 태그 연결을 해제합니다.
    
    - 인증 필요: Bearer 토큰
    - **taggable_id**: 태그 연결 ID (UUID)
    """
    taggable = db.query(Taggable).join(Tag).filter(
        Taggable.id == taggable_id,
        Tag.user_id == current_user.id
    ).first()
    
    if not taggable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="태그 연결을 찾을 수 없습니다"
        )
    
    db.delete(taggable)
    db.commit()
    
    return None


@router.get("/entity/{taggable_type}/{taggable_id}", response_model=EntityTagsResponse, summary="엔티티의 태그 조회")
async def get_entity_tags_endpoint(
    taggable_type: TaggableType,
    taggable_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 엔티티에 연결된 모든 태그를 조회합니다.
    
    - 인증 필요: Bearer 토큰
    - **taggable_type**: 엔티티 타입 (asset/account/transaction)
    - **taggable_id**: 엔티티 ID (UUID)
    """
    # 엔티티 존재 및 접근 권한 확인
    validate_taggable_exists(db, taggable_type.value, taggable_id, current_user.id)
    
    tags = get_entity_tags(db, taggable_type.value, taggable_id, current_user.id)
    
    return EntityTagsResponse(
        entity_type=taggable_type.value,
        entity_id=taggable_id,
        tags=tags,
        total=len(tags)
    )
