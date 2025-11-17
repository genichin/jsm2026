from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class CategoryFlowType(str, Enum):
    expense = 'expense'
    income = 'income'
    transfer = 'transfer'
    investment = 'investment'
    neutral = 'neutral'


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=50, description='카테고리명')
    parent_id: Optional[str] = Field(None, description='상위 카테고리 ID')
    flow_type: CategoryFlowType = Field(..., description='집계 분류: 지출/수입/이동/투자/중립')
    is_active: bool = Field(default=True)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[str] = None
    flow_type: Optional[CategoryFlowType] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        'from_attributes': True
    }


class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int
    page: int
    size: int
    pages: int


class CategoryTreeNode(BaseModel):
    id: str
    name: str
    flow_type: CategoryFlowType
    is_active: bool
    parent_id: Optional[str] = None
    children: List['CategoryTreeNode'] = []

    model_config = {
        'from_attributes': True
    }

# Forward reference resolution
CategoryTreeNode.model_rebuild()
