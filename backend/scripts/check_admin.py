#!/usr/bin/env python3
"""Check admin user in database"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import User

def main():
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(User).all()
        
        print("=" * 80)
        print("📋 Users in Database")
        print("=" * 80)
        
        if not users:
            print("❌ No users found in database")
            return
        
        for user in users:
            print(f"\n👤 User: {user.username}")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Full Name: {user.full_name}")
            print(f"   Active: {'✅' if user.is_active else '❌'}")
            print(f"   Superuser: {'✅' if user.is_superuser else '❌'}")
            # Profit calculation method removed from schema
            print(f"   Created: {user.created_at}")
        
        print("\n" + "=" * 80)
        print(f"Total users: {len(users)}")
        print("=" * 80)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
