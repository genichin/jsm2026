"""add_confirmed_field_to_transactions

Revision ID: 8d87e874f830
Revises: c1bdd90a015d
Create Date: 2025-12-04 16:44:00.822401

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d87e874f830'
down_revision = 'c1bdd90a015d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add confirmed column to transactions table with default value False
    op.add_column('transactions', sa.Column('confirmed', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    # Remove confirmed column from transactions table
    op.drop_column('transactions', 'confirmed')
