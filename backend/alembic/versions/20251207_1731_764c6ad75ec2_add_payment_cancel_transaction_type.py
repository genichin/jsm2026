"""add payment_cancel transaction type

Revision ID: 764c6ad75ec2
Revises: c76e7307e524
Create Date: 2025-12-07 17:31:34.909523

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '764c6ad75ec2'
down_revision = 'c76e7307e524'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Modify CHECK constraint to add payment_cancel transaction type
    op.drop_constraint('valid_transaction_type', 'transactions', type_='check')
    op.create_check_constraint(
        'valid_transaction_type',
        'transactions',
        "type IN ('buy', 'sell', 'deposit', 'withdraw', 'cash_dividend', 'stock_dividend', 'interest', 'fee', "
        "'transfer_in', 'transfer_out', 'adjustment', 'invest', 'redeem', "
        "'internal_transfer', 'card_payment', 'promotion_deposit', 'auto_transfer', 'remittance', 'exchange', "
        "'out_asset', 'in_asset', 'payment_cancel')"
    )


def downgrade() -> None:
    # Restore original CHECK constraint without payment_cancel
    op.drop_constraint('valid_transaction_type', 'transactions', type_='check')
    op.create_check_constraint(
        'valid_transaction_type',
        'transactions',
        "type IN ('buy', 'sell', 'deposit', 'withdraw', 'cash_dividend', 'stock_dividend', 'interest', 'fee', "
        "'transfer_in', 'transfer_out', 'adjustment', 'invest', 'redeem', "
        "'internal_transfer', 'card_payment', 'promotion_deposit', 'auto_transfer', 'remittance', 'exchange', "
        "'out_asset', 'in_asset')"
    )
