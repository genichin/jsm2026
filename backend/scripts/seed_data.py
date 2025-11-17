#!/usr/bin/env python3
"""
Seed initial data for J's Money database

Usage:
    python scripts/seed_data.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import (
    Category, User
)
from sqlalchemy import and_


# Legacy: 구(舊) TransactionCategory/AssetType/RealAssetType 테이블은 제거됨.
# 사용자별 `categories` 테이블만 사용합니다.


def seed_user_categories(db: Session):
    """Seed default categories for each active user into new categories table.
    The set is user-scoped and hierarchical-ready.
    """
    print("\n📝 Seeding user categories (new categories table)...")

    # 기본 카테고리 정의 (parent -> children 형태)
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

    users = db.query(User).filter(User.is_active == True).all()
    for user in users:
        print(f"  • User {user.id}: seeding categories")

        # 이름-유니크 제약: (user_id, name, parent_id)
        def ensure_category(name: str, flow: str, parent_id=None):
            existing = db.query(Category).filter(
                and_(Category.user_id == user.id,
                     Category.name == name,
                     Category.parent_id == parent_id)
            ).first()
            if existing:
                return existing
            cat = Category(user_id=user.id, name=name, flow_type=flow, parent_id=parent_id)
            db.add(cat)
            db.flush()  # get id
            return cat

        # 1차/2차 카테고리 생성
        for flow, parents in default_sets.items():
            for parent_name, children in parents:
                parent = ensure_category(parent_name, flow, None)
                for child_name in children:
                    ensure_category(child_name, flow, parent.id)

    db.commit()


def seed_asset_types(db: Session):
    """Deprecated placeholder: 자산 유형은 Enum로 코드에 정의됩니다."""
    print("\nℹ️ Asset types are defined as Enum in code. Skipping.")


def seed_real_asset_types(db: Session):
    """Deprecated placeholder: 실물 자산 유형 테이블은 사용하지 않습니다."""
    print("\nℹ️ Real asset types are not stored in DB. Skipping.")


def main():
    """Main seeding function"""
    print("=" * 60)
    print("🌱 J's Money - Seeding Initial Data")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        print("\n📝 Account/Asset/RealAsset types are defined as Enums in code (not DB)")
        seed_user_categories(db)        # user-scoped hierarchical categories
        seed_asset_types(db)            # no-op (informational)
        seed_real_asset_types(db)       # no-op (informational)

        print("\n" + "=" * 60)
        print("✅ Seeding completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
