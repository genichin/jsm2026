from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, Category
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse, CategoryFlowType, CategoryTreeNode
)

router = APIRouter()


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    parent_id: Optional[str] = Query(None),
    flow_type: Optional[CategoryFlowType] = Query(None),
    is_active: Optional[bool] = Query(True),
    q: Optional[str] = Query(None, description="이름 부분검색"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Category).filter(Category.user_id == current_user.id)

    if parent_id is not None:
        if parent_id == "root":
            query = query.filter(Category.parent_id == None)
        else:
            query = query.filter(Category.parent_id == parent_id)

    if flow_type is not None:
        query = query.filter(Category.flow_type == flow_type.value)

    if is_active is not None:
        query = query.filter(Category.is_active == is_active)

    if q:
        # simple ilike
        query = query.filter(Category.name.ilike(f"%{q}%"))

    total = query.count()
    if order == "asc":
        query = query.order_by(asc(Category.name))
    else:
        query = query.order_by(desc(Category.name))

    items = query.offset((page - 1) * size).limit(size).all()

    return CategoryListResponse(
        items=[CategoryResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get("/tree", response_model=List[CategoryTreeNode])
async def get_category_tree(
    flow_type: Optional[CategoryFlowType] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """카테고리 트리 조회 (부모-자식 구조)"""
    query = db.query(Category).filter(Category.user_id == current_user.id)
    if flow_type is not None:
        query = query.filter(Category.flow_type == flow_type.value)
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    cats: List[Category] = query.order_by(Category.name.asc()).all()

    # Build map
    by_id: Dict[str, CategoryTreeNode] = {}
    roots: List[CategoryTreeNode] = []

    for c in cats:
        by_id[c.id] = CategoryTreeNode(
            id=c.id,
            name=c.name,
            flow_type=CategoryFlowType(c.flow_type),
            is_active=c.is_active,
            parent_id=c.parent_id,
            children=[]
        )

    for node in list(by_id.values()):
        if node.parent_id and node.parent_id in by_id:
            by_id[node.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Parent ownership check
    if payload.parent_id:
        parent = db.query(Category).filter(
            Category.id == payload.parent_id,
            Category.user_id == current_user.id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="상위 카테고리를 찾을 수 없습니다")

    new_cat = Category(
        id=None,  # default uuid generator
        user_id=current_user.id,
        name=payload.name,
        parent_id=payload.parent_id,
        flow_type=payload.flow_type.value,
        is_active=payload.is_active,
    )
    db.add(new_cat)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="같은 상위에서 이름이 중복됩니다")

    db.refresh(new_cat)
    return CategoryResponse.model_validate(new_cat)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cat = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
    return CategoryResponse.model_validate(cat)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cat = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")

    # parent 변경 시 소유권 검증
    if payload.parent_id is not None:
        if payload.parent_id == "":
            cat.parent_id = None
        else:
            parent = db.query(Category).filter(
                Category.id == payload.parent_id,
                Category.user_id == current_user.id
            ).first()
            if not parent:
                raise HTTPException(status_code=404, detail="상위 카테고리를 찾을 수 없습니다")
            cat.parent_id = payload.parent_id

    if payload.name is not None:
        cat.name = payload.name
    if payload.flow_type is not None:
        cat.flow_type = payload.flow_type.value
    if payload.is_active is not None:
        cat.is_active = payload.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="같은 상위에서 이름이 중복됩니다")

    db.refresh(cat)
    return CategoryResponse.model_validate(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cat = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")

    db.delete(cat)
    db.commit()
    return None


@router.post("/seed", response_model=List[CategoryResponse])
async def seed_default_categories(
    overwrite: bool = Query(False, description="기본 카테고리 재생성. true면 기존 비활성화 후 재생성"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """현재 사용자에 대해 기본 카테고리를 시딩합니다 (idempotent)."""

    # 기본 셋 (scripts/seed_data.py와 유사)
    default_sets = {
        'expense': [
            ("식비", ["외식", "카페/간식", "식재료"]),
            ("교통", ["대중교통", "택시", "주유/주차"]),
            ("주거", ["월세/대출", "관리비", "공과금"]),
            ("통신", ["휴대폰", "인터넷/TV"]),
            ("의료", ["병원", "약국"]),
            ("쇼핑", ["의류", "생활용품"]),
            ("문화", ["영화/공연", "운동/취미"]),
            ("교육", ["학원", "도서"]),
            ("기타", []),
        ],
        'income': [
            ("급여", []),
            ("상여", []),
            ("이자/배당", []),
            ("환급/캐시백", []),
            ("기타수입", []),
        ],
        'transfer': [
            ("계좌이체", []),
            ("카드대금", []),
            ("저축/적금", []),
        ],
        'investment': [
            ("투자", ["매수", "매도", "입출금"]),
        ],
        'neutral': [
            ("조정", []),
        ],
    }

    created: List[Category] = []

    if overwrite:
        # 기존 것 비활성화
        db.query(Category).filter(Category.user_id == current_user.id).update({Category.is_active: False})
        db.commit()

    def ensure(name: str, flow: str, parent_id=None) -> Category:
        existing = db.query(Category).filter(
            Category.user_id == current_user.id,
            Category.name == name,
            Category.parent_id == parent_id
        ).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
            return existing
        obj = Category(user_id=current_user.id, name=name, flow_type=flow, parent_id=parent_id)
        db.add(obj)
        db.flush()
        created.append(obj)
        return obj

    for flow, parents in default_sets.items():
        for parent_name, children in parents:
            parent = ensure(parent_name, flow, None)
            for child in children:
                ensure(child, flow, parent.id)

    db.commit()
    return [CategoryResponse.model_validate(c) for c in created]
