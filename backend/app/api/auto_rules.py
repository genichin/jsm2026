"""Category auto rules CRUD and simulation API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, CategoryAutoRule, Category
from app.schemas.auto_rule import (
    CategoryAutoRuleCreate, CategoryAutoRuleUpdate, CategoryAutoRuleResponse,
    RuleSimulationRequest, RuleSimulationResult
)
from app.services.auto_category import (
    invalidate_rules_cache, get_rules, match_category_by_rules
)

router = APIRouter()


def ensure_category(db: Session, user_id: str, category_id: str) -> Category:
    cat = db.query(Category).filter(Category.id == category_id, Category.user_id == user_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
    return cat


@router.get("", response_model=List[CategoryAutoRuleResponse])
def list_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rules = db.query(CategoryAutoRule).filter(CategoryAutoRule.user_id == current_user.id).order_by(CategoryAutoRule.priority.asc()).all()
    return rules


@router.post("", response_model=CategoryAutoRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(rule: CategoryAutoRuleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_category(db, current_user.id, rule.category_id)
    db_rule = CategoryAutoRule(
        user_id=current_user.id,
        category_id=rule.category_id,
        pattern_type=rule.pattern_type,
        pattern_text=rule.pattern_text,
        priority=rule.priority,
        is_active=rule.is_active
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    invalidate_rules_cache(current_user.id)
    return db_rule


@router.put("/{rule_id}", response_model=CategoryAutoRuleResponse)
def update_rule(rule_id: str, rule_update: CategoryAutoRuleUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_rule = db.query(CategoryAutoRule).filter(CategoryAutoRule.id == rule_id, CategoryAutoRule.user_id == current_user.id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다")

    if rule_update.category_id:
        ensure_category(db, current_user.id, rule_update.category_id)

    update_data = rule_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_rule, field, value)
    db.commit()
    db.refresh(db_rule)
    invalidate_rules_cache(current_user.id)
    return db_rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_rule = db.query(CategoryAutoRule).filter(CategoryAutoRule.id == rule_id, CategoryAutoRule.user_id == current_user.id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다")
    db.delete(db_rule)
    db.commit()
    invalidate_rules_cache(current_user.id)


@router.post("/simulate", response_model=RuleSimulationResult)
def simulate_rule(req: RuleSimulationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rules = get_rules(db, current_user.id)
    matched = match_category_by_rules(rules, req.description)
    if matched:
        return RuleSimulationResult(matched=True, category_id=matched[0], rule_id=matched[1], reason="Matched by rules")
    return RuleSimulationResult(matched=False, reason="No rule matched")
