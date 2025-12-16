"""drop idx_transactions_confirmed with if exists guard

Revision ID: a1b2c3d4e5f6
Revises: fceacb9aa017
Create Date: 2025-12-16 23:05:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fceacb9aa017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 일부 환경에서 이미 인덱스가 삭제되어 있는 경우를 대비한 방어적 처리
    op.execute("DROP INDEX IF EXISTS idx_transactions_confirmed")


def downgrade() -> None:
    # downgrade 시 인덱스를 복원
    op.create_index('idx_transactions_confirmed', 'transactions', ['confirmed'], unique=False)
