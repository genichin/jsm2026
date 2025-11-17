#!/usr/bin/env python3
"""
Database initialization script
Creates database if not exists and runs migrations

Usage:
    python scripts/init_db.py
"""

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


def create_database():
    """Create database if it doesn't exist"""
    # Parse DATABASE_URL
    # postgresql://user:password@host:port/database
    db_url = settings.DATABASE_URL
    parts = db_url.replace('postgresql://', '').split('/')
    connection_part = parts[0]
    database_name = parts[1] if len(parts) > 1 else 'jsmdb'
    
    user_pass, host_port = connection_part.split('@')
    user, password = user_pass.split(':')
    host, port = host_port.split(':')
    
    print(f"🔍 Checking database '{database_name}'...")
    
    # Connect to PostgreSQL server (not to specific database)
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database_name,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✅ Database '{database_name}' already exists")
        else:
            print(f"📝 Creating database '{database_name}'...")
            cursor.execute(f'CREATE DATABASE {database_name}')
            print(f"✅ Database '{database_name}' created successfully")
        
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"❌ Failed to connect to PostgreSQL server: {e}")
        print(f"\nConnection details:")
        print(f"  Host: {host}")
        print(f"  Port: {port}")
        print(f"  User: {user}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def check_tables():
    """Check if tables exist in database"""
    from app.core.database import engine
    
    print(f"\n🔍 Checking tables...")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = result.fetchall()
            
            if not tables:
                print("📭 No tables found in database")
                print("💡 Run: alembic upgrade head")
                return False
            else:
                print(f"✅ Found {len(tables)} tables:")
                for table in tables:
                    print(f"  - {table[0]}")
                return True
                
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False


def run_migrations():
    """Run Alembic migrations"""
    import subprocess
    
    print(f"\n🔄 Running database migrations...")
    
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print("✅ Migrations completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e.stderr}")
        return False
    except FileNotFoundError:
        print("⚠️  Alembic not found. Skipping migrations.")
        print("💡 Run manually: alembic upgrade head")
        return False


def create_admin_user():
    """Create default admin user if not exists"""
    from app.core.database import SessionLocal
    from app.models import User
    import bcrypt
    
    print(f"\n👤 Checking admin user...")
    
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.email == "admin@jsmoney.com").first()
        
        if admin:
            print("✅ Admin user already exists")
            return
        
        print("📝 Creating admin user...")
        
        # Hash password with bcrypt
        password = "admin123"
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create admin user
        admin_user = User(
            email="admin@jsmoney.com",
            username="admin",
            hashed_password=hashed_password,
            full_name="System Administrator",
            is_active=True,
            is_superuser=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully")
        print("\n📝 Admin credentials:")
        print(f"  Email: admin@jsmoney.com")
        print(f"  Password: {password}")
        print("  ⚠️  Please change the password after first login!")
        
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization flow"""
    print("=" * 60)
    print("🚀 J's Money Database Initialization")
    print("=" * 60)
    
    # Step 1: Create database
    create_database()
    
    # Step 2: Check if tables exist
    tables_exist = check_tables()
    
    # Step 3: Run migrations if needed
    if not tables_exist:
        user_input = input("\n❓ Run migrations now? (y/n): ").lower()
        if user_input == 'y':
            run_migrations()
            tables_exist = check_tables()  # Verify tables were created
    
    # Step 4: Create admin user
    if tables_exist:
        create_admin_user()
    
    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    
    print("\n📝 Next steps:")
    if not tables_exist:
        print("  1. Create migration: alembic revision --autogenerate -m 'Initial schema'")
        print("  2. Run migration: alembic upgrade head")
        print("  3. Seed data: python scripts/seed_data.py")
        print("  4. Create admin: Re-run this script")
    else:
        print("  1. Seed data: python scripts/seed_data.py")
        print("  2. Start server: uvicorn app.main:app --reload")
        print("  3. Login with admin@jsmoney.com / admin123!")


if __name__ == "__main__":
    main()
