"""add savings and deposit asset types

Revision ID: add_savings_deposit
Revises: 8d87e874f830
Create Date: 2025-12-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_savings_deposit'
down_revision = '8d87e874f830'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Modify CHECK constraint to add new asset types
    # Initial schema uses CHECK constraint, not enum type
    op.drop_constraint('valid_asset_type', 'assets', type_='check')
    op.create_check_constraint(
        'valid_asset_type',
        'assets',
        "asset_type IN ('stock', 'crypto', 'bond', 'fund', 'etf', 'cash', 'savings', 'deposit')"
    )


def downgrade() -> None:
    # Restore original CHECK constraint
    op.drop_constraint('valid_asset_type', 'assets', type_='check')
    op.create_check_constraint(
        'valid_asset_type',
        'assets',
        "asset_type IN ('stock', 'crypto', 'bond', 'fund', 'etf', 'cash')"
    )
