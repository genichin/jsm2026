"""Pydantic schemas for category auto rules"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


PatternType = Literal['exact','contains','regex']


class CategoryAutoRuleBase(BaseModel):
    pattern_type: PatternType = Field(..., description="매칭 유형")
    pattern_text: str = Field(..., description="패턴 텍스트 또는 정규식")
    priority: int = Field(default=100, ge=0, le=100000)
    is_active: bool = Field(default=True)


class CategoryAutoRuleCreate(CategoryAutoRuleBase):
    category_id: str = Field(..., description="대상 카테고리 ID")


class CategoryAutoRuleUpdate(BaseModel):
    pattern_type: Optional[PatternType] = None
    pattern_text: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=100000)
    is_active: Optional[bool] = None
    category_id: Optional[str] = None


class CategoryAutoRuleResponse(CategoryAutoRuleBase):
    id: str
    user_id: str
    category_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class RuleSimulationRequest(BaseModel):
    description: str = Field(..., description="테스트할 설명/메모 문장")


class RuleSimulationResult(BaseModel):
    matched: bool
    rule_id: Optional[str] = None
    category_id: Optional[str] = None
    reason: Optional[str] = None