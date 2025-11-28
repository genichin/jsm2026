"""
Split dividend into cash_dividend and stock_dividend in transactions.type CHECK constraint

Revision ID: 3c1b2b2c9aa1
Revises: ad849388eb92
Create Date: 2025-11-28 00:01:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3c1b2b2c9aa1'
down_revision = '1f70eef705f1'
branch_labels = None
depends_on = None

def upgrade():
    # Update CHECK constraint: replace 'dividend' with 'cash_dividend' and 'stock_dividend'
    # Drop old constraint if exists, then add new
    conn = op.get_bind()
    # Find existing check constraint name (assuming 'valid_transaction_type')
    try:
        op.drop_constraint('valid_transaction_type', 'transactions', type_='check')
    except Exception:
        pass
    op.create_check_constraint(
        'valid_transaction_type',
        'transactions',
        "type IN ('buy','sell','deposit','withdraw','cash_dividend','stock_dividend','interest','fee','transfer_in','transfer_out','adjustment','invest','redeem','internal_transfer','card_payment','promotion_deposit','auto_transfer','remittance','exchange')"
    )


def downgrade():
    # Revert to original: 'dividend'
    try:
        op.drop_constraint('valid_transaction_type', 'transactions', type_='check')
    except Exception:
        pass
    op.create_check_constraint(
        'valid_transaction_type',
        'transactions',
        "type IN ('buy','sell','deposit','withdraw','dividend','interest','fee','transfer_in','transfer_out','adjustment','invest','redeem','internal_transfer','card_payment','promotion_deposit','auto_transfer','remittance','exchange')"
    )
