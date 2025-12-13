"""add_asset_review_tracking

Revision ID: d17a07f6daa6
Revises: 244902ea97c9
Create Date: 2025-12-13 11:07:35.878335

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd17a07f6daa6'
down_revision = '244902ea97c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add review tracking columns to assets table
    op.add_column('assets', sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('assets', sa.Column('review_interval_days', sa.Integer(), nullable=True, server_default='30'))
    op.add_column('assets', sa.Column('next_review_date', sa.DateTime(timezone=True), nullable=True))
    
    # Create function to automatically update next_review_date
    op.execute("""
        CREATE OR REPLACE FUNCTION update_next_review_date()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.last_reviewed_at IS NOT NULL AND NEW.review_interval_days IS NOT NULL THEN
                NEW.next_review_date := NEW.last_reviewed_at + (NEW.review_interval_days || ' days')::INTERVAL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger on assets table
    op.execute("""
        CREATE TRIGGER assets_update_next_review
        BEFORE INSERT OR UPDATE OF last_reviewed_at, review_interval_days ON assets
        FOR EACH ROW
        EXECUTE FUNCTION update_next_review_date();
    """)
    
    # Create index for efficient review queries
    op.create_index(
        'idx_assets_review_due',
        'assets',
        ['user_id', 'next_review_date'],
        postgresql_where=sa.text('is_active = true AND next_review_date IS NOT NULL')
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_assets_review_due', table_name='assets')
    
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS assets_update_next_review ON assets')
    
    # Drop function
    op.execute('DROP FUNCTION IF EXISTS update_next_review_date()')
    
    # Drop columns
    op.drop_column('assets', 'next_review_date')
    op.drop_column('assets', 'review_interval_days')
    op.drop_column('assets', 'last_reviewed_at')
