# Migration Guide

## 배포 및 마이그레이션 안내서

**대상**: 개발자, DevOps 엔지니어

---

## 사전 요구사항

### 시스템 요구사항

```yaml
# 최소 사양
- PostgreSQL: 15.0+
- Redis: 7.0+
- Python: 3.11+
- 메모리: 4GB+ (개발), 16GB+ (운영)
- 디스크: SSD 권장, 100GB+ (로그 및 백업 포함)

# 권장 사양 (운영 환경)
- PostgreSQL: 15.5+ (최신 LTS)
- Redis: 7.2+ (성능 개선 버전)
- Python: 3.11.x (안정성)
- CPU: 4 core+, 메모리: 32GB+
- 디스크: NVMe SSD 500GB+
```

### 필수 확장 모듈

```sql
-- PostgreSQL 확장 설치 (superuser 권한 필요)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID 생성 함수
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- 암호화 함수 (선택)
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- JSONB 인덱스 최적화 (선택)

-- 확장 설치 확인
SELECT * FROM pg_available_extensions 
WHERE name IN ('uuid-ossp', 'pgcrypto', 'btree_gin')
  AND installed_version IS NOT NULL;
```

---

## 데이터베이스 초기 설정

### 1. PostgreSQL 설정

#### 데이터베이스 생성

```sql
-- 데이터베이스 생성 (superuser로 실행)
CREATE DATABASE jsmoney 
    WITH ENCODING 'UTF8' 
    LC_COLLATE='ko_KR.UTF-8' 
    LC_CTYPE='ko_KR.UTF-8'
    TEMPLATE=template0;

-- 애플리케이션 사용자 생성
CREATE USER jsmoney_user WITH PASSWORD 'secure_password_here';

-- 권한 부여
GRANT CONNECT ON DATABASE jsmoney TO jsmoney_user;
GRANT USAGE ON SCHEMA public TO jsmoney_user;
GRANT CREATE ON SCHEMA public TO jsmoney_user;
```

#### 성능 튜닝 (postgresql.conf)

```ini
# 메모리 설정 (32GB 시스템 기준)
shared_buffers = 8GB                    # 전체 메모리의 25%
effective_cache_size = 24GB             # 전체 메모리의 75%
work_mem = 256MB                        # 정렬/해시 작업용
maintenance_work_mem = 2GB              # 인덱스 생성/VACUUM용

# WAL 설정
wal_buffers = 64MB                      # WAL 버퍼
max_wal_size = 4GB                      # WAL 최대 크기
min_wal_size = 1GB                      # WAL 최소 크기
checkpoint_completion_target = 0.9       # 체크포인트 분산

# 연결 설정
max_connections = 200                   # 최대 연결 수
shared_preload_libraries = 'pg_stat_statements'  # 쿼리 통계

# 로깅 설정
log_min_duration_statement = 1000       # 1초 이상 쿼리 로깅
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# 시간대 설정
timezone = 'UTC'                        # 애플리케이션에서 Asia/Seoul로 변환
```

### 2. Redis 설정

#### 메모리 설정 (redis.conf)

```ini
# 메모리 관리
maxmemory 8gb                          # 최대 메모리 사용량
maxmemory-policy allkeys-lru           # 메모리 부족 시 LRU 삭제

# 지속성 설정 (데이터 안전성)
save 900 1                             # 15분간 1개 이상 변경 시 저장
save 300 10                            # 5분간 10개 이상 변경 시 저장
save 60 10000                          # 1분간 10000개 이상 변경 시 저장

# AOF 활성화 (권장)
appendonly yes
appendfsync everysec                   # 매초 디스크 동기화

# 네트워크 설정
bind 127.0.0.1 192.168.1.100          # 허용 IP 제한
port 6379
timeout 300                            # 클라이언트 타임아웃

# 보안 설정
requirepass your_redis_password_here
rename-command FLUSHALL ""             # 위험한 명령어 비활성화
rename-command FLUSHDB ""
rename-command CONFIG "CONFIG_b835fc"  # 명령어 이름 변경
```

---

## Alembic 마이그레이션 스크립트

### 1. 기본 테이블 생성

```python
# migrations/versions/001_create_base_tables.py
"""Create base tables: users, accounts, assets, transactions

Revision ID: 001_create_base_tables
Revises: 
Create Date: 2024-11-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_create_base_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # users 테이블
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
        # 수익 계산 방식은 DB 컬럼으로 보관하지 않습니다 (전역 기본값 또는 서비스 레이어에서 결정)
    )
    
    # 인덱스 생성
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    
    # accounts 테이블
    op.create_table('accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(100)),
        sa.Column('account_number', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('api_config', postgresql.JSONB()),
        sa.Column('daemon_config', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # 인덱스 생성
    op.create_index('idx_accounts_user', 'accounts', ['user_id'])
    op.create_index('idx_accounts_type', 'accounts', ['account_type'])
    op.create_index('idx_accounts_provider', 'accounts', ['provider'])
    
    # assets 테이블
    op.create_table('assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('symbol', sa.String(20)),
        sa.Column('currency', sa.String(3), server_default=sa.text("'KRW'")),
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE')
    )
    
    # 인덱스 생성
    op.create_index('idx_assets_user', 'assets', ['user_id'])
    op.create_index('idx_assets_account', 'assets', ['account_id'])
    op.create_index('idx_assets_type', 'assets', ['asset_type'])
    op.create_index('idx_assets_symbol', 'assets', ['symbol'])
    
    # transactions 테이블
    op.create_table('transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('quantity', sa.NUMERIC(20, 8), nullable=False),
        sa.Column('price', sa.NUMERIC(15, 2), nullable=False),
        sa.Column('fee', sa.NUMERIC(15, 2), server_default=sa.text('0')),
        sa.Column('tax', sa.NUMERIC(15, 2), server_default=sa.text('0')),
        sa.Column('realized_profit', sa.NUMERIC(15, 2)),
        sa.Column('transaction_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('memo', sa.Text()),
        sa.Column('related_transaction_id', postgresql.UUID(as_uuid=True)),
        sa.Column('is_confirmed', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('external_id', sa.String(100)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_transaction_id'], ['transactions.id'], ondelete='SET NULL'),
        sa.CheckConstraint("type IN ('buy', 'sell', 'deposit', 'withdraw', 'cash_dividend', 'stock_dividend', 'interest', 'fee', 'transfer_in', 'transfer_out', 'adjustment', 'invest', 'redeem', 'internal_transfer', 'card_payment', 'promotion_deposit', 'auto_transfer', 'remittance', 'exchange')", name='valid_transaction_type'),
        sa.CheckConstraint('fee >= 0 AND tax >= 0', name='non_negative_fees')
    )
    
    # 인덱스 생성
    op.create_index('idx_transactions_asset', 'transactions', ['asset_id'])
    op.create_index('idx_transactions_date', 'transactions', [sa.text('transaction_date DESC')])
    op.create_index('idx_transactions_type', 'transactions', ['type'])
    op.create_index('idx_transactions_external', 'transactions', ['external_id'])
    op.create_index('idx_transactions_profit', 'transactions', ['realized_profit'], 
                   postgresql_where=sa.text('realized_profit IS NOT NULL'))

def downgrade():
    # 테이블 삭제 (역순)
    op.drop_table('transactions')
    op.drop_table('assets')
    op.drop_table('accounts') 
    op.drop_table('users')
```

### 2. 복합 인덱스 추가

```python
# migrations/versions/002_add_composite_indexes.py
"""Add composite indexes for performance

Revision ID: 002_add_composite_indexes
Revises: 001_create_base_tables
Create Date: 2024-11-15 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_add_composite_indexes'
down_revision = '001_create_base_tables'
branch_labels = None
depends_on = None

def upgrade():
    # 사용자별 자산 조회 최적화
    op.create_index('idx_assets_user_account', 'assets', ['user_id', 'account_id', 'id'])
    
    # 거래 내역 조회 최적화
    op.create_index('idx_transactions_asset_date', 'transactions', 
                   ['asset_id', sa.text('transaction_date DESC')])
    
    # 수익 집계 최적화
    op.create_index('idx_transactions_asset_profit', 'transactions', 
                   ['asset_id', 'realized_profit'],
                   postgresql_where=sa.text('realized_profit IS NOT NULL'))

def downgrade():
    op.drop_index('idx_transactions_asset_profit')
    op.drop_index('idx_transactions_asset_date')
    op.drop_index('idx_assets_user_account')
```

### 3. 트리거 함수 추가

```python
# migrations/versions/003_add_triggers.py
"""Add trigger functions for updated_at

Revision ID: 003_add_triggers
Revises: 002_add_composite_indexes
Create Date: 2024-11-15 12:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_triggers'
down_revision = '002_add_composite_indexes'
branch_labels = None
depends_on = None

def upgrade():
    # updated_at 자동 업데이트 함수 생성
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # 각 테이블에 트리거 추가
    tables = ['users', 'accounts', 'assets', 'transactions']
    for table in tables:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at 
                BEFORE UPDATE ON {table}
                FOR EACH ROW 
                EXECUTE FUNCTION update_updated_at_column();
        """)

def downgrade():
    # 트리거 삭제
    tables = ['users', 'accounts', 'assets', 'transactions']
    for table in tables:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    # 함수 삭제
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
```

---

## 초기 데이터 시드

### 1. 관리자 계정 생성

```python
# scripts/create_admin.py
"""관리자 계정 생성 스크립트"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import User
from app.core.security import get_password_hash
import uuid

async def create_admin_user():
    """관리자 계정 생성"""
    DATABASE_URL = "postgresql+asyncpg://jsmoney_user:password@localhost/jsmoney"
    
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # 기존 관리자 확인
        existing_admin = await session.execute(
            "SELECT id FROM users WHERE email = 'admin@jsmoney.com'"
        )
        
        if existing_admin.fetchone():
            print("Admin user already exists!")
            return
        
        # 관리자 계정 생성
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@jsmoney.com",
            username="admin",
            hashed_password=get_password_hash("admin_password_change_me"),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True,
        )
        
        session.add(admin_user)
        await session.commit()
        
        print(f"Admin user created with ID: {admin_user.id}")
        print("⚠️ Please change the default password after first login!")

if __name__ == "__main__":
    asyncio.run(create_admin_user())
```

### 2. 샘플 데이터 생성

```python
# scripts/seed_sample_data.py
"""샘플 데이터 생성 (개발/테스트용)"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from app.models import User, Account, Asset, Transaction
from app.core.database import get_session
from app.core.security import get_password_hash

async def create_sample_data():
    """샘플 사용자와 거래 데이터 생성"""
    
    async with get_session() as session:
        # 샘플 사용자 생성
        sample_user = User(
            email="demo@jsmoney.com",
            username="demo_user",
            hashed_password=get_password_hash("demo123"),
            full_name="Demo User",
        )
        session.add(sample_user)
        await session.flush()  # ID 생성을 위해
        
        # 증권계좌 생성
        securities_account = Account(
            user_id=sample_user.id,
            name="NH투자증권 CMA",
            account_type="securities",
            provider="NH투자증권",
            account_number="12345-01-123456"
        )
        session.add(securities_account)
        await session.flush()
        
        # 현금 자산 생성
        cash_asset = Asset(
            user_id=sample_user.id,
            account_id=securities_account.id,
            name="CMA 예수금",
            asset_type="cash",
            currency="KRW"
        )
        
        # 삼성전자 주식 자산 생성
        samsung_asset = Asset(
            user_id=sample_user.id,
            account_id=securities_account.id,
            name="삼성전자",
            asset_type="stock",
            symbol="005930",
            metadata={"market": "KOSPI", "isin": "KR7005930003"}
        )
        
        session.add_all([cash_asset, samsung_asset])
        await session.flush()
        
        # 초기 현금 입금
        cash_deposit = Transaction(
            asset_id=cash_asset.id,
            type="income",
            quantity=Decimal("10000000.00"),  # 1천만원
            price=Decimal("1.00"),
            transaction_date=datetime.now() - timedelta(days=30),
            description="초기 투자금 입금"
        )
        
        # 삼성전자 매수 (100주 @ 67,000원)
        samsung_buy_cash = Transaction(
            asset_id=cash_asset.id,
            type="exchange",
            quantity=Decimal("-6703350.00"),
            price=Decimal("1.00"),
            fee=Decimal("3350.00"),
            realized_profit=Decimal("-3350.00"),
            transaction_date=datetime.now() - timedelta(days=25),
            description="삼성전자 매수 - 현금 출금"
        )
        
        samsung_buy_stock = Transaction(
            asset_id=samsung_asset.id,
            type="exchange",
            quantity=Decimal("100.00000000"),
            price=Decimal("67000.00"),
            fee=Decimal("3350.00"),
            realized_profit=Decimal("-3350.00"),
            transaction_date=datetime.now() - timedelta(days=25),
            description="삼성전자 100주 매수",
            related_transaction_id=samsung_buy_cash.id
        )
        
        # 일부 매도 (30주 @ 70,000원)
        samsung_sell_stock = Transaction(
            asset_id=samsung_asset.id,
            type="exchange",
            quantity=Decimal("-30.00000000"),
            price=Decimal("70000.00"),
            fee=Decimal("1050.00"),
            tax=Decimal("1387.50"),
            realized_profit=Decimal("87562.50"),  # FIFO 계산 결과
            transaction_date=datetime.now() - timedelta(days=15),
            description="삼성전자 30주 매도"
        )
        
        samsung_sell_cash = Transaction(
            asset_id=cash_asset.id,
            type="exchange",
            quantity=Decimal("2097562.50"),
            price=Decimal("1.00"),
            transaction_date=datetime.now() - timedelta(days=15),
            description="삼성전자 매도대금 입금",
            related_transaction_id=samsung_sell_stock.id
        )
        
        session.add_all([
            cash_deposit, 
            samsung_buy_cash, samsung_buy_stock,
            samsung_sell_stock, samsung_sell_cash
        ])
        
        await session.commit()
        print("Sample data created successfully!")

if __name__ == "__main__":
    asyncio.run(create_sample_data())
```

---

## 배포 스크립트

### 1. 전체 설치 스크립트

```bash
#!/bin/bash
# deploy.sh - 전체 환경 설치 스크립트

set -e  # 오류 발생 시 즉시 중단

echo "🚀 JSMoney Backend Deployment Started"

# 환경 변수 설정
export POSTGRES_DB=jsmoney
export POSTGRES_USER=jsmoney_user
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$(openssl rand -base64 32)}
export REDIS_PASSWORD=${REDIS_PASSWORD:-$(openssl rand -base64 32)}

echo "📋 Environment Variables Set"

# PostgreSQL 설치 및 설정
echo "🐘 Installing PostgreSQL..."
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# 데이터베이스 생성
sudo -u postgres psql <<EOF
CREATE DATABASE ${POSTGRES_DB};
CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};
ALTER USER ${POSTGRES_USER} CREATEDB;
\q
EOF

# Redis 설치
echo "🔴 Installing Redis..."
sudo apt install -y redis-server

# Redis 비밀번호 설정
sudo sed -i "s/# requirepass foobared/requirepass ${REDIS_PASSWORD}/" /etc/redis/redis.conf
sudo systemctl restart redis-server

# Python 의존성 설치
echo "🐍 Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# 환경 파일 생성
echo "📝 Creating .env file..."
cat > .env <<EOF
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost/${POSTGRES_DB}
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0
SECRET_KEY=$(openssl rand -base64 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
EOF

# 데이터베이스 마이그레이션
echo "🔄 Running database migrations..."
alembic upgrade head

# 관리자 계정 생성
echo "👤 Creating admin user..."
python scripts/create_admin.py

# Redis 초기 설정
echo "⚡ Initializing Redis..."
python scripts/init_redis.py

echo "✅ Deployment completed successfully!"
echo "🔐 Database Password: ${POSTGRES_PASSWORD}"
echo "🔐 Redis Password: ${REDIS_PASSWORD}"
echo "📋 Please save these passwords securely!"
```

### 2. 서비스 등록 (systemd)

```ini
# /etc/systemd/system/jsmoney-api.service
[Unit]
Description=JSMoney API Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=jsmoney
Group=jsmoney
WorkingDirectory=/opt/jsmoney
Environment=PATH=/opt/jsmoney/venv/bin
ExecStart=/opt/jsmoney/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# 환경 파일 로드
EnvironmentFile=/opt/jsmoney/.env

# 보안 설정
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/jsmoney/logs

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable jsmoney-api
sudo systemctl start jsmoney-api

# 상태 확인
sudo systemctl status jsmoney-api
```

---

## 보안 설정

### 1. SSL/TLS 인증서 설정

```bash
# Let's Encrypt 인증서 발급
sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.com

# Nginx SSL 설정
sudo tee /etc/nginx/sites-available/jsmoney <<EOF
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://\$server_name\$request_uri;
}
EOF

sudo ln -s /etc/nginx/sites-available/jsmoney /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 2. 방화벽 설정

```bash
# UFW 방화벽 설정
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH, HTTP, HTTPS 허용
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 내부 서비스는 localhost만 허용 (PostgreSQL, Redis)
sudo ufw deny 5432
sudo ufw deny 6379

sudo ufw --force enable
sudo ufw status verbose
```

### 3. 데이터베이스 보안

```sql
-- PostgreSQL 보안 설정
-- 1. 기본 계정 정리
DROP ROLE IF EXISTS postgres;  -- 운영환경에서는 제거 고려

-- 2. 연결 제한 (pg_hba.conf)
-- local   all             all                     peer
-- host    jsmoney         jsmoney_user  127.0.0.1/32  md5
-- host    jsmoney         jsmoney_user  ::1/128        md5

-- 3. 감사 로깅 활성화 (postgresql.conf)
-- log_statement = 'mod'                    # DML/DDL 로깅
-- log_min_duration_statement = 1000       # 느린 쿼리 로깅
-- log_connections = on
-- log_disconnections = on
```

---

## 모니터링 및 백업

### 1. 헬스체크 스크립트

```python
# scripts/health_check.py
"""시스템 상태 모니터링"""
import asyncio
import psutil
import asyncpg
import redis.asyncio as redis
from datetime import datetime

async def check_postgresql():
    """PostgreSQL 연결 상태 확인"""
    try:
        conn = await asyncpg.connect("postgresql://jsmoney_user:password@localhost/jsmoney")
        await conn.execute("SELECT 1")
        await conn.close()
        return {"status": "healthy", "response_time": "< 100ms"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_redis():
    """Redis 연결 상태 확인"""
    try:
        r = redis.Redis(host='localhost', port=6379, password='redis_password')
        await r.ping()
        await r.close()
        return {"status": "healthy", "response_time": "< 50ms"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_system_resources():
    """시스템 리소스 확인"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu_usage": f"{cpu_percent}%",
        "memory_usage": f"{memory.percent}%",
        "disk_usage": f"{disk.percent}%",
        "memory_available": f"{memory.available / (1024**3):.1f}GB",
        "disk_free": f"{disk.free / (1024**3):.1f}GB"
    }

async def main():
    print(f"🔍 Health Check Report - {datetime.now()}")
    print("="*50)
    
    # 데이터베이스 상태
    pg_status = await check_postgresql()
    print(f"📊 PostgreSQL: {pg_status['status']}")
    
    # Redis 상태  
    redis_status = await check_redis()
    print(f"⚡ Redis: {redis_status['status']}")
    
    # 시스템 리소스
    resources = await check_system_resources()
    print(f"💻 CPU: {resources['cpu_usage']}, Memory: {resources['memory_usage']}, Disk: {resources['disk_usage']}")
    
    # 전체 상태 판단
    overall_status = "healthy" if all([
        pg_status["status"] == "healthy",
        redis_status["status"] == "healthy",
        float(resources["memory_usage"].rstrip('%')) < 90,
        float(resources["disk_usage"].rstrip('%')) < 90
    ]) else "unhealthy"
    
    print(f"🎯 Overall Status: {overall_status.upper()}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 백업 스크립트

```bash
#!/bin/bash
# backup.sh - 데이터베이스 백업 스크립트

set -e

# 설정
DB_NAME="jsmoney"
DB_USER="jsmoney_user"
BACKUP_DIR="/opt/backups/jsmoney"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

echo "🗄️ Starting backup at $(date)"

# PostgreSQL 백업
echo "📊 Backing up PostgreSQL..."
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/postgresql_${DATE}.sql.gz

# Redis 백업 (RDB 스냅샷)
echo "⚡ Backing up Redis..."
redis-cli --rdb $BACKUP_DIR/redis_${DATE}.rdb

# 설정 파일 백업
echo "📝 Backing up configuration..."
tar czf $BACKUP_DIR/config_${DATE}.tar.gz \
    /opt/jsmoney/.env \
    /etc/nginx/sites-available/jsmoney \
    /etc/systemd/system/jsmoney-api.service

# 오래된 백업 삭제
echo "🗑️ Cleaning old backups..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

# 백업 검증
echo "✅ Verifying backups..."
if [ -f $BACKUP_DIR/postgresql_${DATE}.sql.gz ] && [ -f $BACKUP_DIR/redis_${DATE}.rdb ]; then
    echo "✅ Backup completed successfully at $(date)"
else
    echo "❌ Backup failed!"
    exit 1
fi

# 백업 크기 정보
echo "📊 Backup sizes:"
ls -lh $BACKUP_DIR/*_${DATE}*
```

### 3. 로그 로테이션

```bash
# /etc/logrotate.d/jsmoney
/opt/jsmoney/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 jsmoney jsmoney
    postrotate
        systemctl reload jsmoney-api
    endscript
}
```

---

## 문제 해결

### 자주 발생하는 문제

#### 1. 데이터베이스 연결 오류

```bash
# 연결 상태 확인
sudo -u postgres psql -c "\l"  # 데이터베이스 목록
sudo -u postgres psql -c "\du" # 사용자 목록

# 연결 설정 확인
sudo cat /etc/postgresql/*/main/pg_hba.conf | grep jsmoney

# 서비스 상태 확인
sudo systemctl status postgresql
sudo journalctl -u postgresql -n 20
```

#### 2. Redis 메모리 부족

```bash
# Redis 메모리 사용량 확인
redis-cli info memory

# 메모리 정책 확인
redis-cli config get maxmemory*

# 캐시 클리어 (주의!)
redis-cli flushdb
```

#### 3. 성능 저하

```sql
-- 느린 쿼리 확인
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- 인덱스 사용 상황
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- 테이블 크기 확인
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 긴급 복구 절차

```bash
# 1. 서비스 중단
sudo systemctl stop jsmoney-api

# 2. 데이터베이스 복구
gunzip -c /opt/backups/jsmoney/postgresql_YYYYMMDD_HHMMSS.sql.gz | \
    psql -U jsmoney_user -h localhost jsmoney

# 3. Redis 복구
sudo systemctl stop redis-server
cp /opt/backups/jsmoney/redis_YYYYMMDD_HHMMSS.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo systemctl start redis-server

# 4. 서비스 재시작
sudo systemctl start jsmoney-api

# 5. 상태 확인
python scripts/health_check.py
```