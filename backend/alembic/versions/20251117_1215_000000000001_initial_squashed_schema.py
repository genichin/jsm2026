"""initial_squashed_schema

Revision ID: 000000000001
Revises: 
Create Date: 2025-11-17 12:15:00

This migration squashes previous revisions into a single initial schema.
Includes: users (without profit_calc_method), accounts, account_shares,
assets, categories, category_auto_rules, asset_transactions (with 'exchange'),
tags, taggables, reminders, activities.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000000000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])

    # accounts
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('owner_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=100)),
        sa.Column('account_number', sa.String(length=50)),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('api_config', postgresql.JSONB()),
        sa.Column('daemon_config', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("account_type IN ('bank_account','securities','cash','debit_card','credit_card','savings','deposit','crypto_wallet')", name='valid_account_type')
    )
    op.create_index('ix_accounts_owner_id', 'accounts', ['owner_id'])

    # activities
    op.create_table(
        'activities',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_type', sa.String(length=20), nullable=False),
        sa.Column('target_id', sa.String(length=36), nullable=False),
        sa.Column('activity_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text()),
        sa.Column('payload', postgresql.JSONB()),
        sa.Column('parent_id', sa.String(length=36), sa.ForeignKey('activities.id', ondelete='CASCADE')),
        sa.Column('thread_root_id', sa.String(length=36), sa.ForeignKey('activities.id', ondelete='CASCADE')),
        sa.Column('visibility', sa.String(length=20), nullable=False, server_default='private'),
        sa.Column('is_immutable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("target_type IN ('asset','account','transaction')", name='check_target_type'),
        sa.CheckConstraint("activity_type IN ('comment','log')", name='check_activity_type'),
        sa.CheckConstraint("visibility IN ('private','shared','public')", name='check_visibility')
    )
    op.create_index('ix_activities_user_id', 'activities', ['user_id'])

    # categories
    op.create_table(
        'categories',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('parent_id', sa.String(length=36), sa.ForeignKey('categories.id', ondelete='SET NULL')),
        sa.Column('flow_type', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("flow_type IN ('expense','income','transfer','investment','neutral')", name='check_category_flow_type'),
        sa.UniqueConstraint('user_id','name','parent_id', name='uq_categories_per_user')
    )
    op.create_index('ix_categories_user_id', 'categories', ['user_id'])

    # reminders
    op.create_table(
        'reminders',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('remindable_type', sa.String(length=20), nullable=False),
        sa.Column('remindable_id', sa.String(length=36), nullable=False),
        sa.Column('reminder_type', sa.String(length=20), nullable=False, server_default='review'),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('remind_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('repeat_interval', sa.String(length=20)),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('dismissed_at', sa.DateTime(timezone=True)),
        sa.Column('snoozed_until', sa.DateTime(timezone=True)),
        sa.Column('last_notified_at', sa.DateTime(timezone=True)),
        sa.Column('auto_complete_on_view', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("remindable_type IN ('asset','account','transaction')", name='check_remindable_type'),
        sa.CheckConstraint("reminder_type IN ('review','dividend','rebalance','deadline','custom')", name='check_reminder_type'),
        sa.CheckConstraint("repeat_interval IS NULL OR repeat_interval IN ('daily','weekly','monthly','yearly')", name='check_repeat_interval')
    )
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'])

    # tags
    op.create_table(
        'tags',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=7)),
        sa.Column('description', sa.Text()),
        sa.Column('allowed_types', postgresql.JSONB(), server_default='["asset", "account", "transaction"]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id','name', name='uq_tag_per_user')
    )
    op.create_index('ix_tags_user_id', 'tags', ['user_id'])

    # accounts shares
    op.create_table(
        'account_shares',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='viewer'),
        sa.Column('can_read', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_write', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_delete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_share', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('shared_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('shared_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('account_id','user_id', name='uq_account_user_share'),
        sa.CheckConstraint("role IN ('owner','editor','viewer')", name='check_role')
    )
    op.create_index('ix_account_shares_account_id', 'account_shares', ['account_id'])
    op.create_index('ix_account_shares_user_id', 'account_shares', ['user_id'])

    # assets
    op.create_table(
        'assets',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_id', sa.String(length=36), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('symbol', sa.String(length=20)),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='KRW'),
        sa.Column('asset_metadata', postgresql.JSONB()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("asset_type IN ('stock','crypto','bond','fund','etf','cash')", name='valid_asset_type')
    )
    op.create_index('ix_assets_user_id', 'assets', ['user_id'])
    op.create_index('ix_assets_account_id', 'assets', ['account_id'])

    # category_auto_rules
    op.create_table(
        'category_auto_rules',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', sa.String(length=36), sa.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pattern_type', sa.String(length=20), nullable=False),
        sa.Column('pattern_text', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("pattern_type IN ('exact','contains','regex')", name='check_auto_rule_pattern_type'),
        sa.UniqueConstraint('user_id','pattern_type','pattern_text', name='uq_auto_rule_unique_per_user')
    )
    op.create_index('ix_category_auto_rules_user_id', 'category_auto_rules', ['user_id'])
    op.create_index('ix_category_auto_rules_category_id', 'category_auto_rules', ['category_id'])

    # taggables
    op.create_table(
        'taggables',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('tag_id', sa.String(length=36), sa.ForeignKey('tags.id', ondelete='CASCADE'), nullable=False),
        sa.Column('taggable_type', sa.String(length=20), nullable=False),
        sa.Column('taggable_id', sa.String(length=36), nullable=False),
        sa.Column('tagged_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tagged_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.CheckConstraint("taggable_type IN ('asset','account','transaction')", name='check_taggable_type'),
        sa.UniqueConstraint('tag_id','taggable_type','taggable_id', name='uq_tag_entity')
    )
    op.create_index('ix_taggables_tag_id', 'taggables', ['tag_id'])

    # asset_transactions
    op.create_table(
        'asset_transactions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('asset_id', sa.String(length=36), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False),
        sa.Column('price', sa.Numeric(15, 2), nullable=False),
        sa.Column('fee', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('tax', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('realized_profit', sa.Numeric(15, 2)),
        sa.Column('balance_after', sa.Numeric(20, 8)),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('memo', sa.Text()),
        sa.Column('related_transaction_id', sa.String(length=36), sa.ForeignKey('asset_transactions.id', ondelete='SET NULL')),
        sa.Column('category_id', sa.String(length=36), sa.ForeignKey('categories.id', ondelete='SET NULL')),
        sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('external_id', sa.String(length=100)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("type IN ('buy','sell','deposit','withdraw','dividend','interest','fee','transfer_in','transfer_out','adjustment','invest','redeem','internal_transfer','card_payment','promotion_deposit','auto_transfer','remittance','exchange')", name='valid_transaction_type'),
        sa.CheckConstraint('fee >= 0 AND tax >= 0', name='non_negative_fees')
    )
    op.create_index('ix_asset_transactions_asset_id', 'asset_transactions', ['asset_id'])
    op.create_index('ix_asset_transactions_transaction_date', 'asset_transactions', ['transaction_date'])


def downgrade() -> None:
    op.drop_index('ix_asset_transactions_transaction_date', table_name='asset_transactions')
    op.drop_index('ix_asset_transactions_asset_id', table_name='asset_transactions')
    op.drop_table('asset_transactions')
    op.drop_index('ix_taggables_tag_id', table_name='taggables')
    op.drop_table('taggables')
    op.drop_index('ix_category_auto_rules_category_id', table_name='category_auto_rules')
    op.drop_index('ix_category_auto_rules_user_id', table_name='category_auto_rules')
    op.drop_table('category_auto_rules')
    op.drop_index('ix_assets_account_id', table_name='assets')
    op.drop_index('ix_assets_user_id', table_name='assets')
    op.drop_table('assets')
    op.drop_index('ix_account_shares_user_id', table_name='account_shares')
    op.drop_index('ix_account_shares_account_id', table_name='account_shares')
    op.drop_table('account_shares')
    op.drop_index('ix_tags_user_id', table_name='tags')
    op.drop_table('tags')
    op.drop_index('ix_reminders_user_id', table_name='reminders')
    op.drop_table('reminders')
    op.drop_index('ix_categories_user_id', table_name='categories')
    op.drop_table('categories')
    op.drop_index('ix_activities_user_id', table_name='activities')
    op.drop_table('activities')
    op.drop_index('ix_accounts_owner_id', table_name='accounts')
    op.drop_table('accounts')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')