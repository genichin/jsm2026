"""Auto category assignment service with simple caching"""

from __future__ import annotations

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import CategoryAutoRule
from app.core.redis import redis_client


def _cache_key(user_id: str) -> str:
    return f"auto_rules:{user_id}"


def load_rules_from_db(db: Session, user_id: str) -> List[dict]:
    """Load active rules for user ordered by priority.
    Returns list of dicts to store in Redis (simple JSON-serializable).
    """
    rules = db.query(CategoryAutoRule).filter(
        CategoryAutoRule.user_id == user_id,
        CategoryAutoRule.is_active == True
    ).order_by(CategoryAutoRule.priority.asc()).all()

    result = []
    for r in rules:
        result.append({
            "id": r.id,
            "category_id": r.category_id,
            "pattern_type": r.pattern_type,
            "pattern_text": r.pattern_text,
            "priority": r.priority,
        })
    return result


def get_rules(db: Session, user_id: str) -> List[dict]:
    key = _cache_key(user_id)
    cached = None
    try:
        if hasattr(redis_client, 'json'):
            cached = redis_client.json().get(key)
        else:
            import json
            raw = redis_client.get(key)
            if raw:
                cached = json.loads(raw)
    except Exception:
        cached = None
    if cached is not None:
        return cached

    rules = load_rules_from_db(db, user_id)
    try:
        if hasattr(redis_client, 'json'):
            redis_client.json().set(key, '$', rules)
        else:
            import json
            redis_client.set(key, json.dumps(rules))
    except Exception:
        pass
    return rules


def invalidate_rules_cache(user_id: str) -> None:
    key = _cache_key(user_id)
    try:
        redis_client.delete(key)
    except Exception:
        pass


def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    # simple whitespace normalization
    return " ".join(t.split())


def match_category_by_rules(rules: List[dict], description: str) -> Optional[Tuple[str, str]]:
    """Return (category_id, rule_id) if match found.
    Specificity: exact > regex > contains (with same priority order already applied).
    """
    if not description:
        return None
    desc = normalize_text(description)
    if not desc:
        return None

    # Group by pattern_type preserving order
    exact = [r for r in rules if r['pattern_type'] == 'exact']
    regex = [r for r in rules if r['pattern_type'] == 'regex']
    contains = [r for r in rules if r['pattern_type'] == 'contains']

    # exact
    for r in exact:
        if desc == normalize_text(r['pattern_text']):
            return (r['category_id'], r['id'])

    # regex
    import re
    for r in regex:
        try:
            if re.search(r['pattern_text'], description):
                return (r['category_id'], r['id'])
        except re.error:
            continue

    # contains
    for r in contains:
        if normalize_text(r['pattern_text']) in desc:
            return (r['category_id'], r['id'])

    return None


def auto_assign_category(db: Session, user_id: str, description: str) -> Optional[str]:
    rules = get_rules(db, user_id)
    matched = match_category_by_rules(rules, description)
    if matched:
        return matched[0]
    return None
